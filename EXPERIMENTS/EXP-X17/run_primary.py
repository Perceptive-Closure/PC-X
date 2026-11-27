"""Execute the registered primary native experiment and preserve exact replay evidence."""

import argparse
import gzip
import json
import random
import time
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from pathlib import Path

from controller.forecast import forecast
from controller.policy import choose_probe, declare
from native import NativeService, NativeStore, World, score_attempt, verify_receipt
from native.service import verify_source_receipt


ARMS = ("pcx", "high_skip", "low_only", "always_high", "no_paid")
N_NORMAL = 4096
N_ORDINARY = 64
N_PAIRED = 128
FIELDS = ("world", "arm", "index", "wrong", "I", "V", "VI", "G2", "cost8",
          "intake", "finish", "proposal", "operations", "record_sha256")


def packed(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()


def load(path):
    return json.loads(path.read_bytes())


def digest(data):
    return sha256(data).hexdigest()


def write(path, value):
    with path.open("xb") as handle:
        handle.write((json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def exact_json(scores):
    return {key: str(value) for key, value in scores.items()}


def seed_of(key, purpose, identifier):
    return sha256(key + packed([purpose, identifier])).digest()


def make_world(row):
    return World(Fraction(row["theta"]), Fraction(row["beta"]), row["m"],
                 row["k"], row["B"], row["N"])


def play(service, identifier, plant_seed, policy_seed, arm, mechanism="actual"):
    attempt = service.new_attempt(identifier, plant_seed, mechanism)
    try:
        public = attempt.intake()
        if set(public) != {"prelude", "route_receipt"}:
            raise ValueError("unexpected public fields in primary admitted intake")
        route_receipt = public["route_receipt"]
        if not verify_receipt(route_receipt):
            raise ValueError("invalid native route receipt")
        rng = random.Random(policy_seed)
        command = choose_probe(arm, public["prelude"], route_receipt, rng)
        response = attempt.probe(command, route_receipt)
        verdict = declare(arm, public["prelude"], route_receipt, command, response, rng)
        attempt.declare(verdict)
    except (RuntimeError, ValueError, AssertionError, TypeError, KeyError):
        attempt.abort()
        raise


def example(store, row, scores):
    digests = {row["source_digest"], row["intake_digest"], row["final_digest"],
               row["trace"]["installation_digest"]}
    return {
        "row": row,
        "score": scores,
        "artifacts": {key: store.read_artifact(key).decode() for key in sorted(digests - {None})},
    }


def summarize_row(store, identifier, world):
    row = store.read_attempt(identifier)
    t = row["trace"]
    s = score_attempt(store, identifier)
    issued = s["issued"]
    if (t["control"] is not None or t["denials"] or not t["guard_required"]
            or t["world"] != world.raw() or not s["intake_complete"] or s["intake_violation"]
            or type(t["declaration"]) is not bool or s["paid_eighths"] not in (0, 3, 8)
            or s["finalized"] != issued or t["events"].count("finalizer-invoked") != issued
            or t["events"].count("finalizer-committed") != issued):
        raise ValueError("unexpected durable governed record")
    if issued:
        if (t["proposal"] != (world.m ^ t["public_intake"]["prelude"][-1])
                or t["authorized_route"] != world.k
                or t["events"].index("proposal") >= t["events"].index("final-draw")):
            raise ValueError("reached finalizer violates installed carry, timing or actual authority")
    return row, s


def append_record(stream, content_hash, record):
    line = packed(record) + b"\n"
    stream.write(line)
    content_hash.update(line)


def cell(store, service, world_row, world, arm, n, key, stream, contents, examples, failures):
    started = time.perf_counter()
    name = world_row["id"]
    counts = Counter()
    hashes = sha256()
    for index in range(n):
        identifier = f"main/{name}/{arm}/{index:05d}"
        try:
            play(service, identifier, seed_of(key, "plant", identifier),
                 seed_of(key, "controller", identifier), arm)
        except (RuntimeError, ValueError, AssertionError, TypeError, KeyError) as error:
            failures[identifier] = {"reason": str(error), "phase": "native execution"}
    store.flush()
    for index in range(n):
        identifier = f"main/{name}/{arm}/{index:05d}"
        try:
            if identifier in failures:
                raise ValueError(failures[identifier]["reason"])
            row, s = summarize_row(store, identifier, world)
            p = row["trace"]["proposal"]
            record = [name, arm, index, int(s["wrong_declaration"]), int(s["issued"]),
                      int(s["violation"]), int(s["violating_issue"]), s["utility_halves"],
                      s["paid_eighths"], int(s["intake_complete"]), int(s["finalized"]), p,
                      len(row["trace"]["events"]), digest(packed(row))]
            for field, value in zip(FIELDS[3:11], record[3:11]):
                counts[field] += value
            counts["proposal_zero"] += p == 0
            counts["proposal_one"] += p == 1
            counts["operations"] += record[-2]
            counts["max_cost8"] = max(counts["max_cost8"], s["paid_eighths"])
            counts["valid"] += 1
            hashes.update(bytes.fromhex(record[-1]))
            if index == 0:
                examples[identifier] = example(store, row, s)
        except (KeyError, RuntimeError, ValueError, TypeError, AssertionError) as error:
            failure = failures.setdefault(identifier, {"reason": str(error), "phase": "durable readback"})
            try:
                row = store.read_attempt(identifier)
                failure["retained"] = example(store, row, {})
            except KeyError:
                failure["retained"] = None
            record = [name, arm, index, {"invalid": identifier}]
            counts["invalid"] += 1
        append_record(stream, contents, record)
    counts["attempts"] = n
    return {"world": name, "arm": arm, "counts": dict(counts), "record_chain_sha256": hashes.hexdigest(),
            "seconds": time.perf_counter() - started}


def source_pairs(store, service, world, name, key, nominal_count, ordinary_count, examples):
    began = time.perf_counter()
    hashes = sha256()
    n_issue = n_actual = n_nominal = strip = ordinary_violations = 0
    for index in range(nominal_count):
        key_id = f"pair/{name}/{index:04d}"
        ids = [key_id + "/actual", key_id + "/nominal"]
        plant, policy = seed_of(key, "paired-plant", key_id), seed_of(key, "paired-policy", key_id)
        play(service, ids[0], plant, policy, "pcx", mechanism="actual")
        play(service, ids[1], plant, policy, "pcx", mechanism="nominal")
        store.flush()
        actual, actual_score = summarize_row(store, ids[0], world)
        nominal, nominal_score = summarize_row(store, ids[1], world)
        ac, no = actual["trace"], nominal["trace"]
        for field in ("source_checks", "world", "events", "public_intake", "draws", "command", "response",
                      "paid_eighths", "declaration", "authorized_route", "proposal"):
            if ac[field] != no[field]:
                raise ValueError(f"paired source differs at preserved field {field}")
        if actual["intake_digest"] != nominal["intake_digest"]:
            raise ValueError("paired reconciliation commits differ")
        change = int(actual_score["violation"]) - int(nominal_score["violation"])
        predicted_change = 0
        if actual_score["issued"]:
            word = next(item for item in ac["draws"] if item["domain"] == "final")
            u = Fraction(word["word"], word["upper"])
            nominal_cut = world.theta/4 + Fraction(ac["proposal"], 16)
            predicted_change = int(nominal_cut <= u < nominal_cut + world.beta)
            n_issue += 1
        if change != predicted_change:
            raise ValueError("paired physical event difference is outside the accepted surcharge strip")
        if (actual["final_digest"] != nominal["final_digest"]) != bool(change):
            raise ValueError("paired physical durable outputs violate the declared effect comparison")
        n_actual += actual_score["violation"]
        n_nominal += nominal_score["violation"]
        strip += predicted_change
        for entry in (actual, nominal):
            hashes.update(bytes.fromhex(digest(packed(entry))))
        if index == 0:
            examples[ids[0]] = example(store, actual, actual_score)
            examples[ids[1]] = example(store, nominal, nominal_score)
    for index in range(ordinary_count):
        identifier = f"ordinary/{name}/{index:04d}"
        service.ordinary(identifier, seed_of(key, "ordinary", identifier))
    store.flush()
    for index in range(ordinary_count):
        identifier = f"ordinary/{name}/{index:04d}"
        row = store.read_attempt(identifier)
        outcome = score_attempt(store, identifier)
        if row["mechanism"] != "ordinary" or outcome["issued"] or not outcome["finalized"]:
            raise ValueError("ordinary reference was not separately executed")
        ordinary_violations += outcome["violation"]
        hashes.update(bytes.fromhex(digest(packed(row))))
        if index == 0:
            examples[identifier] = example(store, row, outcome)
    return {"world": name, "paired": nominal_count, "paired_issues": n_issue,
            "actual_violations": n_actual, "nominal_violations": n_nominal, "strip": strip,
            "ordinary": ordinary_count, "ordinary_violations": ordinary_violations,
            "record_chain_sha256": hashes.hexdigest(), "seconds": time.perf_counter() - began}


def run(worlds, directory, key, configuration, sample, paired, ordinary):
    began = time.perf_counter()
    directory.mkdir(parents=True, exist_ok=False)
    data = directory / "rows.jsonl.gz"
    contents = sha256()
    cells, pair_rows, setup, failures, examples = [], [], [], {}, {}
    with NativeStore(directory/"native.sqlite") as store, data.open("xb") as binary:
        with gzip.GzipFile(filename="", fileobj=binary, mode="wb", compresslevel=5, mtime=0) as stream:
            for row in worlds:
                world = make_world(row)
                start = time.perf_counter()
                service = NativeService(world, store)
                guard = service.check_source("guard")
                if (not verify_source_receipt(guard) or guard["revision"] != "good"
                        or guard["charge_eighths"] != 2 or guard["surcharge_bounds"] != ["0", "1/32"]):
                    raise ValueError("invalid independent guard evidence for registered good run")
                setup.append({"world": row["id"], "verified_guard": guard,
                              "seconds": time.perf_counter() - start})
                for arm in ARMS:
                    entry = cell(store, service, row, world, arm, sample, key, stream, contents,
                                 examples, failures)
                    entry["forecast"] = exact_json(forecast(world.theta, world.beta, world.m, world.N, arm))
                    cells.append(entry)
                    print(f"{row['id']} {arm} {entry['counts'].get('valid', 0)}/{sample}", flush=True)
                pair_rows.append(source_pairs(store, service, world, row["id"], key, paired,
                                              ordinary, examples))
    report = {
        "schema": 1, "role": "primary", "configuration": configuration, "fields": list(FIELDS),
        "sample_per_cell": sample, "cells": cells, "setup": setup, "source_pairs": pair_rows,
        "failure_count": len(failures), "uncompressed_rows_sha256": contents.hexdigest(),
        "compressed_rows_sha256": digest(data.read_bytes()),
        "operation_seconds": time.perf_counter() - began,
    }
    write(directory/"report.json", report)
    write(directory/"artifact-examples.json", examples)
    write(directory/"invalid-attempts.json", failures)
    print(f"primary {sum(c['counts'].get('valid', 0) for c in cells)} valid, {len(failures)} invalid",
          flush=True)


def study_inputs(release_dir):
    gate = load(release_dir/"run-authorization.json")
    if gate.get("phase") != "PH-06-VERIFIED":
        raise ValueError("no authenticated prospective release")
    for name, expected in gate["files"].items():
        if Path(name).name != name or digest((release_dir/name).read_bytes()) != expected:
            raise ValueError(f"wrong prospective receipt/file bytes: {name}")
    needed = {"opening-roster.json", "verified-beacon.json", "primary-seed-reveal.json"}
    if not needed.issubset(gate["files"]):
        raise ValueError("incomplete frozen release binding")
    opening = load(release_dir/"opening-roster.json")
    beacon = load(release_dir/"verified-beacon.json")["beacon"]
    reveal = load(release_dir/"primary-seed-reveal.json")
    entropy = bytes.fromhex(reveal["seed_hex"])
    if len(entropy) != 32 or digest(entropy) != reveal["commitment_sha256"]:
        raise ValueError("seed opening differs from commitment")
    pin = load(Path(__file__).resolve().parent/"custody/primary-seed-commitment.json")
    if pin["sha256"] != reveal["commitment_sha256"] or opening["round"] != beacon["round"]:
        raise ValueError("seed or signed round differs from registered release")
    worlds = opening["worlds"]
    if [row["id"] for row in worlds] != [f"s{i:02d}" for i in range(1, 9)]:
        raise ValueError("installed roster shape differs from fixed design")
    key = sha256(b"PC-X/EXP-X17/primary/v1\0"+entropy+bytes.fromhex(beacon["randomness"])).digest()
    return worlds, key, {"release_sha256": digest((release_dir/"run-authorization.json").read_bytes()),
                         "primary_seed_commitment": pin["sha256"], "round": opening["round"]}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    mode = cli.add_mutually_exclusive_group(required=True)
    mode.add_argument("--release", type=Path)
    mode.add_argument("--development", action="store_true")
    args = cli.parse_args()
    if args.development:
        dev = [{"id":"development-l","theta":"33/256","beta":"3/512","m":0,"k":"L","B":"good","N":7},
               {"id":"development-r","theta":"223/256","beta":"3/512","m":1,"k":"R","B":"good","N":7}]
        run(dev, args.output, sha256(b"fixed development X17").digest(), {"development":True},
            96, 24, 12)
    else:
        worlds, key, configuration = study_inputs(args.release)
        run(worlds, args.output, key, configuration, N_NORMAL, N_PAIRED, N_ORDINARY)


if __name__ == "__main__":
    main()
