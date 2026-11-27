"""Read exact public X17 evidence and independently check primary trial provenance."""

import argparse
import gzip
import hmac
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from fractions import Fraction as F
from hashlib import sha256
from math import lcm
from pathlib import Path
from random import Random

from review_development import accepted
from verify_freeze import ARMS, FREEZE, ROOT, independent_expected


PRIMARY = "3110f43916eb4d0f617ae44e117a9e45a041c821"
AUTH = "19c9bc68a9f9f98d99a96a6fb662ded73d50e75c"
OPENING = "b9840c50a4e409446ed97a335c7179c48f08b596"
N = 4096
PUBLIC_TEST_KEY = b"PCX EXP-X17 PUBLIC SYNTHETIC SOURCE KEY V1"
TARIFFS = {"skip": 0, "low": 3, "high": 8, "direct": 4}
ROLE_CHARGES = {
    "pcx": {3, 8}, "high_skip": {0, 8}, "low_only": {3},
    "always_high": {8}, "no_paid": {0},
}
RUN_FIELDS = ("world", "arm", "index", "wrong", "I", "V", "VI", "G2", "cost8",
              "intake", "finish", "proposal", "operations", "record_sha256")


def blob(path, rev=PRIMARY):
    return subprocess.check_output(["git", "cat-file", "blob", rev + ":" + ROOT + path])


def document(path, rev=PRIMARY):
    return json.loads(blob(path, rev))


def hash_bytes(body):
    return sha256(body).hexdigest()


def pack(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def verify_order(ancestor, later):
    subprocess.run(["git", "merge-base", "--is-ancestor", ancestor, later], check=True)


def utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def signed_record(kind, receipt):
    unsigned = {key: value for key, value in receipt.items() if key != "signature"}
    material = kind.encode("ascii") + b"\x00" + pack(unsigned)
    expected = hmac.new(PUBLIC_TEST_KEY, material, sha256).hexdigest()
    return hmac.compare_digest(receipt["signature"], expected)


def check_registered_readbacks(schedule, round_id, draw_hash):
    confirmed = 0
    for name in ("registered-freeze-readback.json", "registered-readback.json",
                 "registered-independence-readback.json"):
        receipt = document("custody/" + name, AUTH)
        assert receipt["round"] == round_id and receipt["draw_sha256"] == draw_hash
        for item in receipt["objects"]:
            commit = item["commit"]
            tree = subprocess.check_output(
                ["git", "rev-parse", commit + "^{tree}"], text=True
            ).strip()
            assert tree == item["tree"]
            activity = item["server_activity"]
            assert activity["after"] == commit and utc(activity["timestamp"]) < schedule
            responses = list(item["github"].values())
            for path, attested in item["files"].items():
                assert path.startswith(ROOT)
                relative = path.removeprefix(ROOT)
                content = blob(relative, commit)
                assert hash_bytes(content) == attested["sha256"] and len(content) == attested["bytes"]
                responses.append(attested["github"])
                confirmed += 1
            for response in responses:
                assert response["status"] == 200 and response["request_id"]
                assert parsedate_to_datetime(response["http_date"]) < schedule
                assert utc(response["observed_utc"]) < schedule
    return confirmed


def load_release():
    gate_body = blob("custody/run-authorization.json", AUTH)
    gate = json.loads(gate_body)
    assert gate["freeze_commit"] == FREEZE and gate["opening_commit"] == OPENING
    assert gate["phase"] == "PH-06-VERIFIED"
    chain = [FREEZE, gate["draw_commit"], gate["preopening_commit"], OPENING, AUTH, PRIMARY]
    for older, newer in zip(chain, chain[1:]):
        verify_order(older, newer)
    for name, expected in gate["files"].items():
        original = blob("custody/" + name, AUTH)
        assert hash_bytes(original) == expected and blob("custody/" + name) == original, name
    manifest = document("manifests/frozen-inputs.json", FREEZE)
    diff = subprocess.check_output(
        ["git", "diff", "--name-only", FREEZE, PRIMARY, "--", ROOT], text=True
    ).splitlines()
    assert not any(ROOT + path in diff for path in manifest["files"])
    draw_body = blob("custody/draw-plan.json", AUTH)
    opening_body = blob("custody/opening-roster.json", AUTH)
    beacon_body = blob("custody/verified-beacon.json", AUTH)
    draw, opening, verified = map(json.loads, (draw_body, opening_body, beacon_body))
    beacon = verified["beacon"]
    round_id = gate["round"]
    assert draw["round"] == opening["round"] == beacon["round"] == round_id
    assert opening["draw_sha256"] == hash_bytes(draw_body)
    assert opening["beacon_sha256"] == hash_bytes(beacon_body)
    assert hash_bytes(bytes.fromhex(beacon["signature"])) == beacon["randomness"]
    assert draw["frozen_manifest_sha256"] == hash_bytes(blob("manifests/frozen-inputs.json", FREEZE))
    domain_body = blob("custody/roster-domain.json", FREEZE)
    assert opening["domain_sha256"] == draw["domain_sha256"] == hash_bytes(domain_body)
    schedule = utc(draw["scheduled_utc"])
    start = draw["chain"]["genesis_time"] + (round_id - 1) * draw["chain"]["period"]
    assert schedule == datetime.fromtimestamp(start, timezone.utc)

    before = document("custody/pre-opening-pending.json", AUTH)
    assert before["round"] == round_id
    for group in (draw["still_unavailable_at_commitment"], before["receipts"]):
        assert [record["status"] for record in group] == [425, 404]
        assert all(parsedate_to_datetime(row["http_date"]) < schedule and utc(row["observed_utc"]) < schedule
                   for row in group)
    assert utc(verified["verified_utc"]) >= schedule
    assert all(record["status"] == 200 and parsedate_to_datetime(record["http_date"]) >= schedule
               and utc(record["observed_utc"]) >= schedule for record in verified["fetched"])

    readback_files = check_registered_readbacks(schedule, round_id, hash_bytes(draw_body))
    selection = reproduce_selection(json.loads(domain_body), beacon["randomness"])
    assert selection == opening["worlds"]
    table = document("custody/selected-forecasts.json", AUTH)
    assert table["opening_sha256"] == hash_bytes(opening_body) and table["verified_selected_rows"] == 40
    worlds = {row["id"]: row for row in selection}
    assert set(table["predictions"]) == set(worlds)
    for slot, world in worlds.items():
        assert set(table["predictions"][slot]) == set(ARMS)
        for arm in ARMS:
            predictions = table["predictions"][slot][arm]
            assert set(predictions) == {"actual", "nominal"}
            for name, beta in (("actual", F(world["beta"])), ("nominal", F(0))):
                expected = independent_expected(F(world["theta"]), beta, world["m"], world["N"], arm)
                expected["conditional_risk"] = expected["VI"] / expected["I"]
                assert {key: F(value) for key, value in predictions[name].items()} == expected
    reveal = document("custody/primary-seed-reveal.json", AUTH)
    private = bytes.fromhex(reveal["seed_hex"])
    pin = document("custody/primary-seed-commitment.json", FREEZE)["sha256"]
    assert len(private) == 32 and hash_bytes(private) == reveal["commitment_sha256"] == pin
    key = sha256(b"PC-X/EXP-X17/primary/v1\0" + private + bytes.fromhex(beacon["randomness"])).digest()
    return gate, hash_bytes(gate_body), worlds, key, readback_files


def reproduce_selection(domain, entropy):
    assert domain["selector"] == "PCX-X17-draw-v1"

    def pick(domain_name, choices):
        limit = len(choices)
        cutoff = (1 << 256) // limit * limit
        for nonce in range(64):
            raw = sha256(f"PCX-X17-draw-v1\n{entropy}\n{domain_name}\n{nonce}\n".encode("ascii")).digest()
            integer = int.from_bytes(raw, "big")
            if integer < cutoff:
                return choices[integer % limit]
        raise AssertionError("selection did not finish in the replay bound")

    def row(index, theta, beta, tag, route, depth):
        return {"id": f"s{index:02}", "theta": str(F(theta)), "beta": str(F(beta)),
                "m": tag, "B": "good", "k": route, "N": depth}

    beta_values = domain["beta_endpoints"]
    mode, route = pick("matched/m", (0, 1)), pick("matched/k", "LR")
    beta = pick("matched/beta", beta_values)
    depth = pick("matched/N", domain["matched_depths"])
    extreme_depth = pick("extreme/N", domain["extreme_depths"])
    other_beta = beta_values[1 - beta_values.index(beta)]
    other_route = "R" if route == "L" else "L"
    rows = [row(1, "1/4", beta, mode, route, depth), row(2, "3/4", beta, mode, route, depth),
            row(3, "1/8", other_beta, 1 - mode, other_route, extreme_depth),
            row(4, "7/8", other_beta, 1 - mode, other_route, extreme_depth)]
    for index, options in enumerate(domain["interior_theta_numerators"], 5):
        label = f"s{index:02}/"
        rows.append(row(
            index, F(pick(label + "theta", options), domain["theta_denominator"]),
            pick(label + "beta", domain["interior_beta"]), pick(label + "m", (0, 1)),
            pick(label + "k", "LR"), pick(label + "N", domain["interior_depths"]),
        ))
    return rows


def decode_artifacts(example, stock_by_route):
    row, artifacts = example["row"], example["artifacts"]
    trace = row["trace"]
    expected_route = trace["world"]["k"]
    for address, text in artifacts.items():
        assert hash_bytes(text.encode()) == address
    assert artifacts[row["source_digest"]].encode() == stock_by_route[expected_route]
    stock = json.loads(artifacts[row["source_digest"]])
    assert stock["routing"][stock["zone"]] == stock["expected_route"] == expected_route
    inventory = dict.fromkeys(stock["book"], 0)
    lots = set()
    for scan in stock["scans"]:
        assert scan["lot"] not in lots and scan["sku"] in inventory and scan["quantity"] >= 0
        lots.add(scan["lot"])
        inventory[scan["sku"]] += scan["quantity"]
    variance = {sku: units - stock["book"][sku] for sku, units in inventory.items()}
    intake = json.loads(artifacts[row["intake_digest"]]) if row["intake_digest"] else None
    intake_good = bool(intake is not None and intake["source_digest"] == row["source_digest"]
                       and intake["inventory"] == inventory and intake["variance"] == variance)
    early = bool(intake is not None and (not intake_good or intake["staging_destination"] != expected_route))
    final = json.loads(artifacts[row["final_digest"]]) if row["final_digest"] else None
    late = bool(final is not None and (
        not intake_good or final["destination"] != expected_route
        or final["intake_digest"] != row["intake_digest"] or final["inventory"] != inventory
    ))
    issued = trace["declaration"] is True
    positive = F(trace["world"]["theta"]) < F(1, 2)
    extra = bool(row["mechanism"] != "ordinary" and positive and issued and final is not None and not late)
    result = {
        "target_positive": positive, "issued": issued,
        "wrong_declaration": trace["declaration"] is not None and issued != positive,
        "violation": early or late, "violating_issue": issued and (early or late),
        "intake_complete": intake_good, "intake_violation": early, "finish_violation": late,
        "finalized": final is not None, "expected_route": expected_route,
        "actual_destination": final["destination"] if final is not None else None,
        "utility_halves": int(intake_good) + int(extra), "paid_eighths": trace["paid_eighths"],
    }
    assert result == example["score"], row["attempt_id"]
    return row, result


def validate_witness(key, example, stock_by_route, worlds):
    row, result = decode_artifacts(example, stock_by_route)
    identifier, trace = row["attempt_id"], row["trace"]
    phase, slot, *suffix = identifier.split("/")
    world = worlds[slot]
    theta, beta = F(world["theta"]), F(world["beta"])
    assert {k: value for k, value in world.items() if k != "id"} == trace["world"]
    installation = json.loads(example["artifacts"][trace["installation_digest"]])
    assert installation["world"] == trace["world"]
    assert installation["ordinary_reference"] == {
        "operation": "ordinary-routing-v1", "defect_probability": str(theta), "cutoff": "1/2"
    }
    [guard] = trace["source_checks"]
    assert signed_record("source", guard) and guard["revision"] == "good" and guard["charge_eighths"] == 2
    pair_id = "/".join(identifier.split("/")[:3])
    expected_seed = sha256(key + pack({
        "main": ["plant", identifier], "pair": ["paired-plant", pair_id],
        "ordinary": ["ordinary", identifier],
    }[phase])).digest()
    seed = {"bytes_hex": expected_seed.hex()}
    assert trace["seed"] == seed and trace["status"] == "completed" and not trace["denials"]
    draws = iter(trace["draws"])

    def word(domain, index, upper):
        n, rejected = accepted(seed, domain, index, upper)
        assert next(draws) == {"domain": domain, "index": index, "upper": upper,
                               "word": n, "rejected": rejected}
        return n

    if phase == "ordinary":
        defect = word("ordinary", 0, theta.denominator) < theta.numerator
        assert result["violation"] is defect and not result["issued"] and result["finalized"]
        assert next(draws, None) is None
        return
    assert result["intake_complete"] and not result["intake_violation"]
    state = 0
    prefix = []
    stay = (1 + (-1) ** world["m"] * theta * (1 - theta)) / 2
    for index in range(world["N"]):
        state ^= int(word("prelude", index, stay.denominator) >= stay.numerator)
        prefix.append(state)
    public = trace["public_intake"]
    assert set(public) == {"prelude", "route_receipt"} and public["prelude"] == prefix
    receipt = public["route_receipt"]
    assert signed_record("route", receipt) and receipt["route"] == world["k"]
    assert receipt["intake_digest"] == row["intake_digest"]

    arm = suffix[0] if phase == "main" else "pcx"
    material = pack(["controller", identifier] if phase == "main" else ["paired-policy", pair_id])
    rng = Random(sha256(key + material).digest())
    if arm == "pcx":
        quality = "low" if rng.randrange(3) < 2 else "high"
    elif arm == "high_skip":
        quality = "high" if rng.randrange(3) < 2 else "skip"
    else:
        quality = {"low_only": "low", "always_high": "high", "no_paid": "skip"}[arm]
    assert trace["command"] == quality + ":" + world["k"] and trace["paid_eighths"] == TARIFFS[quality]
    response = None
    if quality != "skip":
        mean = theta if quality == "high" else F(1, 4) + theta / 2
        response = int(word("probe", 0, mean.denominator) < mean.numerator)
    assert trace["response"] == response
    issue = rng.randrange(2) == 0 if response is None else response == 0
    events = ["opened", "prelude", "reconciled", "receipt-delivered", "probe", "declaration"]
    assert result["issued"] is issue and result["finalized"] is issue
    if issue:
        proposal = world["m"] ^ state
        assert trace["proposal"] == proposal and trace["authorized_route"] == world["k"]
        r0 = theta / 4 + F(proposal, 16)
        upper = lcm(r0.denominator, (r0 + beta).denominator)
        cut = r0 + (beta if row["mechanism"] == "actual" else 0)
        assert result["violation"] == (F(word("final", 0, upper), upper) < cut)
        events += ["finalizer-authorized", "finalizer-invoked", "proposal", "final-draw", "finalizer-committed"]
    assert trace["events"] == events and next(draws, None) is None


def reduce_primary(worlds, key, gate, gate_hash, stock_by_route):
    report = document("results/primary/report.json")
    config = report["configuration"]
    assert config["release_sha256"] == gate_hash and config["round"] == gate["round"]
    assert report["sample_per_cell"] == N and report["fields"] == list(RUN_FIELDS)
    assert report["failure_count"] == 0 and document("results/primary/invalid-attempts.json") == {}
    compressed = blob("results/primary/rows.jsonl.gz")
    assert hash_bytes(compressed) == report["compressed_rows_sha256"]
    raw = gzip.decompress(compressed)
    assert hash_bytes(raw) == report["uncompressed_rows_sha256"]
    running = defaultdict(Counter)
    row_hashes = defaultdict(sha256)
    example_index = {}
    for line in raw.splitlines():
        slot, arm, sequence, wrong, issue, violation, joint, utility, cost, intake, finish, proposal, ops, trace = json.loads(line)
        world = worlds[slot]
        positive = F(world["theta"]) < F(1, 2)
        k = slot, arm
        totals = running[k]
        assert sequence == totals["valid"] and arm in ARMS
        assert issue in (0, 1) and wrong == int(bool(issue) != positive)
        assert joint == violation <= issue and violation in (0, 1)
        assert utility == 1 + int(positive and issue and not violation)
        assert cost in ROLE_CHARGES[arm] and intake == 1 and finish == issue
        assert ops == 6 + 5 * issue and (proposal in (0, 1) if issue else proposal is None)
        checksum = bytes.fromhex(trace)
        assert len(checksum) == 32
        row_hashes[k].update(checksum)
        totals.update(dict(zip(RUN_FIELDS[3:11], (wrong, issue, violation, joint, utility, cost, intake, finish))))
        totals.update({"valid": 1, "operations": ops, "proposal_zero": int(proposal == 0),
                       "proposal_one": int(proposal == 1)})
        totals["max_cost8"] = max(totals["max_cost8"], cost)
        if sequence == 0:
            example_index[f"main/{slot}/{arm}/{sequence:05d}"] = trace
    assert set(running) == {(slot, arm) for slot in worlds for arm in ARMS}
    for each in report["cells"]:
        k = each["world"], each["arm"]
        totals = running[k]
        totals["attempts"] = totals["valid"]
        assert totals["valid"] == N and each["counts"] == dict(totals)
        assert row_hashes[k].hexdigest() == each["record_chain_sha256"]
        world = worlds[k[0]]
        expected = independent_expected(F(world["theta"]), F(world["beta"]), world["m"], world["N"], k[1])
        assert {m: F(v) for m, v in each["forecast"].items()} == expected
    assert len(report["setup"]) == len(worlds)
    assert all(
        signed_record("source", row["verified_guard"]) and row["verified_guard"]["charge_eighths"] == 2
        and row["verified_guard"]["revision"] == "good"
        for row in report["setup"]
    )
    examples = document("results/primary/artifact-examples.json")
    assert len(examples) == 64
    for identifier, example in examples.items():
        assert example["row"]["attempt_id"] == identifier
        validate_witness(key, example, stock_by_route, worlds)
        if identifier.startswith("main/"):
            assert hash_bytes(pack(example["row"])) == example_index[identifier]
    pairs = Counter()
    for each in report["source_pairs"]:
        assert each["paired"] == 128 and each["ordinary"] == 64
        assert each["actual_violations"] - each["nominal_violations"] == each["strip"]
        pairs.update({key: each[key] for key in ("paired", "paired_issues", "strip", "ordinary")})
        name = each["world"]
        actual = examples[f"pair/{name}/0000/actual"]["row"]
        nominal = examples[f"pair/{name}/0000/nominal"]["row"]
        assert actual["trace"] == nominal["trace"] and actual["intake_digest"] == nominal["intake_digest"]
    db = document("results/primary/native-db-manifest.json")
    assert db["attempts"] == sum(row["valid"] for row in running.values()) + 2 * pairs["paired"] + pairs["ordinary"]
    return running, {
        "cells": len(running), "fixed_rows_checked": sum(row["valid"] for row in running.values()),
        "actual_artifact_witnesses_checked": len(examples), "paired_witness_counts": dict(pairs),
        "pcx_actual_paid_cap": str(F(max(row["max_cost8"] for (slot, arm), row in running.items()
                                        if arm == "pcx"), 8)),
    }


def review_controls(stock_by_route):
    source = document("results/controls/observations.json")
    cases = {f"C{number:02}" for number in range(1, 20)}
    assert cases == set(source)
    records = {}
    for line in blob("results/controls/complete-native-control-records.jsonl").splitlines():
        record = json.loads(line)
        row, score = decode_artifacts(record["data"], stock_by_route)
        assert record["id"] == row["attempt_id"] and record["id"] not in records
        records[record["id"]] = (row, score)
    assert len(records) == 261
    assert source["C01"]["rejection"] == source["C02"]["rejection"] == "good_guard_required"
    assert source["C01"]["guard"]["revision"] == "bad"
    assert source["C02"]["ordinary"]["charge_eighths"] == 1 and "revision" not in source["C02"]["ordinary"]
    for case, denial in (("C03", "wrong_route"), ("C04", "repeated_probe")):
        trace = source[case]["row"]["trace"]
        assert trace["denials"] == [denial] and trace["events"].count("probe") == 1
        assert trace["paid_eighths"] == 3
    assert source["C05"]["row"]["trace"]["denials"] == ["missing_route_receipt", "missing_finish_authority"]
    assert source["C05"]["score"]["intake_complete"]
    assert all(not x["score"]["wrong_declaration"] and x["score"]["paid_eighths"] == 0
               for x in source["C06"]["valid_zero_paid"])
    public = [x["row"]["trace"]["public_intake"] for x in source["C07"]["opposite_delivered_records"]]
    assert public[0]["intake_batch_class"] != public[1]["intake_batch_class"]
    assert all(public[0][name] == public[1][name] for name in ("prelude", "route_receipt"))
    for row, score in records.values():
        trace = row["trace"]
        if trace["control"] == "C08":
            assert trace["events"].index("final-draw") < trace["events"].index("proposal")
            draw = trace["draws"][-1]
            assert score["violation"] == (F(draw["word"], draw["upper"]) < F(source["C08"]["exact_altered_cut"]))
    c09 = source["C09"]
    assert c09["original"]["row"]["trace"]["public_intake"] == c09["mutated"]["row"]["trace"]["public_intake"]
    assert c09["original"]["row"]["trace"]["response"] == c09["mutated"]["row"]["trace"]["response"]
    assert [c09[x]["score"]["violation"] for x in ("original", "mutated")] == [False, True]
    assert source["C10"]["actual_omitted_destination"] not in source["C10"]["represented_destinations"]
    assert source["C10"]["witness"]["score"]["violation"]
    early = source["C11"]["score"]
    assert early["intake_violation"] and not early["issued"] and early["utility_halves"] == 1
    reset = source["C12"]["carry_changed"]["row"]["trace"]
    assert reset["public_intake"]["prelude"][-1] == 1 and reset["proposal"] == reset["world"]["m"]
    cancelled = source["C13"]["score"]
    assert cancelled["issued"] and not cancelled["finalized"] and cancelled["utility_halves"] == 1
    assert source["C14"]["normal_rejection"] == "source_correspondence_failed" and F(source["C14"]["actual_excess"]) == F(1, 8)
    changed = source["C15"]
    assert changed["actual_monitor"] == changed["matched_monitor"]
    assert any(changed["actual_monitor"]["observations"]) and not any(changed["mismatched_monitor"]["observations"])
    assert F(changed["exact_TV_at_least"]) == 1 - F(31, 32)**2 == F(63, 1024) > F(1, 32)
    assert F(source["C16"]["rows"][0]["issue_probability"]) == F(247, 372) < F(2, 3)
    assert F(source["C16"]["rows"][1]["paid_price"]) == F(7, 12)
    direct = source["C17"]["admitted_direct"]
    assert [x["row"]["trace"]["response"] for x in direct] == [0, 1]
    assert all(signed_record("direct", x["row"]["trace"]["direct_attestation"]) for x in direct)
    assert F(source["C17"]["exact_mixed_optimum"]) == F(1, 6)
    assert source["C18"]["native_guard"]["row"]["trace"]["denials"] == ["wrong_route"]
    assert F(source["C18"]["countermodel"]["its_probability"]) == 0
    assert F(source["C19"]["unconditional_failure"]) == F(1, 20)
    assert source["C19"]["issued"] == source["C19"]["violating_issue"] == source["C19"]["invalid_calibration"]
    assert F(source["C19"]["risk_given_issuance"]) == 1
    return {"controls_checked": len(cases), "control_artifact_rows_checked": len(records)}


def check_primary_release():
    gate, gate_hash, worlds, key, readback_files = load_release()
    stock = {route: blob(f"native/fixtures/stock-{route}.json", FREEZE).replace(b"\r\n", b"\n")
             for route in ("L", "R")}
    cells, summary = reduce_primary(worlds, key, gate, gate_hash, stock)
    control_counts = review_controls(stock)
    return worlds, cells, {"authorized_round": gate["round"], "primary_commit": PRIMARY,
                           "authorization_commit": AUTH, "opening_commit": OPENING,
                           "release_files": len(gate["files"]), "prerelease_git_file_receipts_checked": readback_files,
                           "actual_and_nominal_selected_forecasts_checked": 80, **summary, **control_counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    _, _, summary = check_primary_release()
    text = json.dumps(summary, sort_keys=True, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
