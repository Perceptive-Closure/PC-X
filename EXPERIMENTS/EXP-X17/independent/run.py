"""Fresh independent X17 native trials with a durable, independently decoded audit."""

import argparse
from collections import defaultdict
from fractions import Fraction as F
from gzip import GzipFile
from hashlib import sha256
import json
from math import isqrt
from pathlib import Path
from random import Random
import sys
from time import perf_counter

from evidence import Evidence, EvidenceError, canonical, certify_admitted, checked_draw, decoded
from model import ARMS, COST_KEYS, Installation, final_probability, forecast
from seed import role_root, trial_stream


EXPERIMENT = Path(__file__).resolve().parents[1]
TRIALS = 4096
ORDINARY_DIAGNOSTICS = 64
PAIRED_DIAGNOSTICS = 128
FAMILY_SIZE = 640
CONFIDENCE_ERROR = F(1, 20)
MAIN_RADIUS = F(1, 25)
EQUIVALENCE_TOLERANCE = F(2, 25)
RANGES = {key: (F(0), F(1)) for key in COST_KEYS} | {"Z": (F(-3, 8), F(5, 8))}


def choose_offer(arm, rng):
    if arm == "pcx":
        return "high" if rng.randrange(3) == 0 else "low"
    if arm == "high_skip":
        return "skip" if rng.randrange(3) == 0 else "high"
    return {"low_only": "low", "always_high": "high", "no_paid": "skip"}[arm]


def play(service, world, arm, attempt_id, native_seed, policy_seed, mechanism="actual"):
    lottery = Random(int(policy_seed, 16))
    attempt = service.new_attempt(attempt_id, native_seed, mechanism=mechanism)
    try:
        public = attempt.intake()
        if set(public) != {"prelude", "route_receipt"}:
            raise EvidenceError("ineligible public controller input")
        receipt = public["route_receipt"]
        if set(receipt) != {"route", "intake_digest", "signature"} or receipt["route"] not in ("L", "R"):
            raise EvidenceError("ineligible route receipt")
        offer = choose_offer(arm, lottery)
        command = offer + ":" + receipt["route"]
        response = attempt.probe(command, receipt)
        if offer == "skip":
            if response is not None:
                raise EvidenceError("skip disclosed a read")
            decision = lottery.randrange(2) == 1
        else:
            if type(response) is not int or response not in (0, 1):
                raise EvidenceError("paid response outside the registered word alphabet")
            decision = response == 0
        attempt.declare(decision)
    except (KeyError, ValueError, RuntimeError, TypeError):
        try:
            attempt.abort()
        except (KeyError, ValueError, RuntimeError, TypeError):
            # The stored exception and any existing committed state still enter the raw index.
            pass
        raise
    return command, decision


def radius_selected(issued):
    # log(25600) < 51/5. Round the indicated square root outward exactly.
    scale = 10**8
    numerator = 51 * scale * scale
    denominator = 10 * issued
    units = isqrt(numerator // denominator)
    if units * units * denominator < numerator:
        units += 1
    return F(units, scale)


def interval(value, radius, score_range):
    return max(score_range[0], value - radius), min(score_range[1], value + radius)


def endpoint_report(total, count, prediction, score_range, radius, infer):
    point = total / count if count else None
    if point is None:
        return {"estimate": None, "forecast": str(prediction), "status": "unresolved"}
    if not infer:
        return {"estimate": str(point), "forecast": str(prediction), "status": "descriptive_only"}
    lo, hi = interval(point, radius, score_range)
    compatible = lo <= prediction <= hi
    equivalent = lo >= prediction - EQUIVALENCE_TOLERANCE and hi <= prediction + EQUIVALENCE_TOLERANCE
    return {"estimate": str(point), "forecast": str(prediction), "interval": [str(lo), str(hi)],
            "radius": str(radius), "forecast_in_interval": compatible,
            "interval_inside_equivalence_band": equivalent, "status": "analyzed"}


def file_digest(path):
    with path.open("rb") as stream:
        return _stream_digest(stream)


def _stream_digest(stream):
    state = sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        state.update(block)
    return state.hexdigest()


def bound_summary(world, arm, score_sum, valid, invalid, trials):
    predicted = forecast(world, arm)
    infer = not invalid and trials == TRIALS
    report = {
        key: endpoint_report(score_sum[key], valid, predicted[key], RANGES[key], MAIN_RADIUS, infer)
        for key in COST_KEYS
    }
    issued = int(score_sum["I"])
    has_mass_cert = infer and issued > 0 and F(issued, trials) > MAIN_RADIUS
    report["conditional_risk"] = endpoint_report(
        score_sum["VI"], issued, predicted["conditional_risk"], (F(0), F(1)),
        radius_selected(issued) if issued else F(1), has_mass_cert,
    )
    counts = {key: int(score_sum[key]) for key in ("I", "V", "VI", "wrong")}
    counts.update(G_halves=int(2 * score_sum["G"]), cost_eighths=int(8 * score_sum["cost"]),
                  Z_eighths=int(8 * score_sum["Z"]))
    return {"id": world.id, "arm": arm, "planned": trials, "valid": valid, "invalid": invalid,
            "issued": issued, "counts": counts, "endpoint": report}


def run_diagnostics(service, store, reader, world, seed_root, zipped):
    ordinary = []
    paired = []
    for trial in range(ORDINARY_DIAGNOSTICS):
        name = f"{world.id}-ordinary-{trial:03}"
        stream = trial_stream(seed_root, world.id, "ordinary", trial, "native")
        service.ordinary(name, stream)
        ordinary.append((name, stream))
    for trial in range(PAIRED_DIAGNOSTICS):
        name = f"{world.id}-paired-{trial:03}"
        stream = trial_stream(seed_root, world.id, "paired", trial, "native")
        policy = trial_stream(seed_root, world.id, "paired", trial, "policy")
        actual = play(service, world, "pcx", name + "-actual", stream, policy, "actual")
        nominal = play(service, world, "pcx", name + "-nominal", stream, policy, "nominal")
        if actual != nominal:
            raise EvidenceError("paired controls or declarations differ")
        paired.append((name, stream, actual))
    store.flush()
    ordinary_bad, disagreement, strip_count, issued = 0, 0, 0, 0
    examples = []
    for name, stream in ordinary:
        row = reader.attempt(name)
        result = decoded(reader, row, world)
        trace = row["trace"]
        if trace["seed"] != stream or row["mechanism"] != "ordinary" or trace["declaration"] is not None:
            raise EvidenceError("ordinary role or seed differs")
        if trace["events"] != ["opened", "reconciled", "ordinary-invoked", "ordinary-committed"]:
            raise EvidenceError("ordinary durable order differs")
        if len(trace["draws"]) != 1 or not result["intake_ok"] or not result["finalized"]:
            raise EvidenceError("ordinary raw support differs")
        word = checked_draw(trace["draws"][0], stream, "ordinary", 0, world.theta.denominator)
        if result["V"] != int(word < world.theta.numerator):
            raise EvidenceError("ordinary physical score differs")
        ordinary_bad += result["V"]
        zipped.write(canonical({"id": name, "kind": "ordinary", "V": result["V"],
                                "trace_sha256": row["trace_sha256"], "final_digest": row["final_digest"]}) + b"\n")
    for name, stream, command in paired:
        actual, nominal = (reader.attempt(name + "-" + side) for side in ("actual", "nominal"))
        values_actual, values_nominal = (certify_admitted(reader, row, world, stream, *command)
                                           for row in (actual, nominal))
        trace, original = actual["trace"], nominal["trace"]
        same_fields = ("public_intake", "draws", "response", "authorized_route", "proposal", "declaration")
        if any(trace[key] != original[key] for key in same_fields):
            raise EvidenceError("matched paired record changed before the terminal event")
        in_strip = 0
        if values_actual["I"]:
            issued += 1
            last = trace["public_intake"]["prelude"][-1]
            final = trace["draws"][-1]
            word = F(final["word"], final["upper"])
            in_strip = int(final_probability(world, last, "nominal") <= word < final_probability(world, last))
        delta = values_actual["VI"] - values_nominal["VI"]
        if delta != in_strip or (actual["final_digest"] != nominal["final_digest"]) != bool(in_strip):
            raise EvidenceError("actual routed artifact disagreement outside the declared surcharge strip")
        disagreement += delta
        strip_count += in_strip
        entry = {"id": name, "kind": "paired", "I": values_actual["I"], "actual_V": values_actual["V"],
                 "nominal_V": values_nominal["V"], "in_strip": in_strip,
                 "actual_trace": actual["trace_sha256"], "nominal_trace": nominal["trace_sha256"],
                 "actual_final": actual["final_digest"], "nominal_final": nominal["final_digest"]}
        if in_strip and not examples:
            examples.append(entry)
        zipped.write(canonical(entry) + b"\n")
    return {"id": world.id, "ordinary_count": len(ordinary), "ordinary_violation": ordinary_bad,
            "paired_count": len(paired), "paired_issued": issued, "paired_disagreement": disagreement,
            "strip_count": strip_count, "strip_examples": examples}


def setup_native():
    if str(EXPERIMENT) not in sys.path:
        sys.path.insert(0, str(EXPERIMENT))
    from native import NativeService, NativeStore, World
    return NativeService, NativeStore, World


def run(out_dir, worlds, root, commitment, details, trials=TRIALS, arms=ARMS):
    NativeService, NativeStore, World = setup_native()
    out_dir.mkdir(parents=True, exist_ok=False)
    database = out_dir / "independent.sqlite"
    index = out_dir / "independent-index.ndjson.gz"
    status = []
    diagnostics = []
    setup_receipts = []
    start = perf_counter()
    with NativeStore(database) as store, index.open("xb") as raw, GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as zipped:
        with Evidence(database) as reader:
            for world in worlds:
                service = NativeService(World(world.theta, world.beta, world.m, world.k, world.B, world.N), store)
                setup_receipts.append({"id": world.id, "receipt": service.check_source("guard")})
                for arm in arms:
                    sums = defaultdict(F)
                    invalid, valid = 0, 0
                    for batch_start in range(0, trials, 128):
                        staged = []
                        for trial in range(batch_start, min(batch_start + 128, trials)):
                            attempt = f"{world.id}-{arm}-{trial:05}"
                            native_seed = trial_stream(root, world.id, arm, trial, "native")
                            policy_seed = trial_stream(root, world.id, arm, trial, "policy")
                            try:
                                command, decision = play(service, world, arm, attempt, native_seed, policy_seed)
                                staged.append((attempt, native_seed, (command, decision)))
                            except (KeyError, ValueError, RuntimeError, TypeError) as error:
                                staged.append((attempt, native_seed, error))
                        store.flush()
                        for attempt, native_seed, played in staged:
                            item = {"id": attempt}
                            if isinstance(played, Exception):
                                item["execution_error"] = {"kind": type(played).__name__, "message": str(played)}
                            try:
                                row = reader.attempt(attempt)
                                item.update({key: row[key] for key in
                                             ("source_digest", "intake_digest", "final_digest", "trace_sha256")})
                                if isinstance(played, Exception):
                                    raise EvidenceError(str(played))
                                values = certify_admitted(reader, row, world, native_seed, *played)
                                item["outcome"] = {key: str(values[key]) for key in COST_KEYS}
                                item["logical_moves"] = world.N + 3 + values["I"]
                                for key in COST_KEYS:
                                    sums[key] += values[key]
                                valid += 1
                            except (KeyError, ValueError, RuntimeError, TypeError, StopIteration) as error:
                                item["invalid"] = {"message": str(error), "kind": type(error).__name__}
                                invalid += 1
                            zipped.write(canonical(item) + b"\n")
                    status.append(bound_summary(world, arm, sums, valid, invalid, trials))
                    print(f"{world.id} {arm}: {valid}/{trials} independently verified.", flush=True)
                if trials == TRIALS:
                    try:
                        diagnostics.append(run_diagnostics(service, store, reader, world, root, zipped))
                    except (KeyError, ValueError, RuntimeError, TypeError, StopIteration) as error:
                        store.flush()
                        diagnostics.append({"id": world.id, "invalid": str(error)})
    document = {
        "schema": 1, "role": "independent", "planned_per_cell": trials, "family_size": FAMILY_SIZE,
        "confidence_error": str(CONFIDENCE_ERROR), "fixed_radius": str(MAIN_RADIUS),
        "equivalence_tolerance": str(EQUIVALENCE_TOLERANCE), "auth_inputs": details,
        "seed_commitment": commitment, "duration_s": perf_counter() - start,
        "raw_db_sha256": file_digest(database), "raw_index_sha256": file_digest(index), "cells": status,
        "diagnostics": diagnostics, "setup_receipts": setup_receipts, "python": sys.version,
    }
    with (out_dir / "independent-summary.json").open("x", encoding="utf-8", newline="\n") as out:
        out.write(json.dumps(document, sort_keys=True, indent=2) + "\n")
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authorization", type=Path, required=True)
    parser.add_argument("--draw", type=Path, required=True)
    parser.add_argument("--beacon", type=Path, required=True)
    parser.add_argument("--opening", type=Path, required=True)
    parser.add_argument("--independent-seed", type=Path, required=True)
    parser.add_argument("--seed-commitment", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    draw_bytes = args.draw.read_bytes()
    beacon_bytes = args.beacon.read_bytes()
    selected_bytes = args.opening.read_bytes()
    draw, beacon, selected = map(json.loads, (draw_bytes, beacon_bytes, selected_bytes))
    gate_bytes = args.authorization.read_bytes()
    gate = json.loads(gate_bytes)
    files = {"draw-plan.json": draw_bytes, "verified-beacon.json": beacon_bytes,
             "opening-roster.json": selected_bytes}
    if (gate["schema"] != 1 or gate["phase"] != "PH-06-VERIFIED" or gate["round"] != draw["round"]
            or gate["freeze_commit"] != draw["source_commit"]
            or any(gate["files"].get(name) != sha256(body).hexdigest() for name, body in files.items())):
        raise ValueError("PH-06 authorization does not bind the actual draw and roster")
    if (draw["round"] != beacon["beacon"]["round"] or draw["round"] != selected["round"]
            or sha256(draw_bytes).hexdigest() != selected["draw_sha256"]
            or sha256(beacon_bytes).hexdigest() != selected["beacon_sha256"]):
        raise ValueError("opening links differ")
    worlds = tuple(Installation.from_row(w) for w in selected["worlds"])
    if [w.id for w in worlds] != [f"s{i:02}" for i in range(1, 9)]:
        raise ValueError("registered roster order differs")
    commitment = json.loads(args.seed_commitment.read_bytes())["sha256"]
    root = role_root(args.independent_seed.read_bytes(), commitment, beacon["beacon"]["randomness"],
                     draw["source_commit"])
    result = run(args.output, worlds, root, commitment,
                 {"draw_sha256": selected["draw_sha256"], "beacon_sha256": selected["beacon_sha256"],
                  "opening_sha256": sha256(selected_bytes).hexdigest(), "source_commit": draw["source_commit"],
                  "authorization_sha256": sha256(gate_bytes).hexdigest()})
    print(f"Independent evidence completed for {len(result['cells'])} cells.")


if __name__ == "__main__":
    main()
