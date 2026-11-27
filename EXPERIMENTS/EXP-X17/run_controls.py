"""Replay registered X17 perturbations on disjoint synthetic fixtures."""

import argparse
import json
import sys
from fractions import Fraction as Q
from pathlib import Path

from native import AuthorizationError, NativeService, NativeStore, World, score_attempt

sys.path.insert(0, str(Path(__file__).resolve().parent/"tests"))
from native_controls import (DEV, DEV_BAD, DEV_OPPOSITE, check_durable_and_transport,
                             check_private_boundary, check_read_and_authority_controls,
                             check_physical_controls, finish, install)


def failure(fn):
    try:
        fn()
    except AuthorizationError as exc:
        return exc.code
    raise AssertionError("expected unauthorized synthetic operation")


def release_evidence(store, row):
    score = score_attempt(store, row["attempt_id"])
    files = {}
    for key in ("source_digest", "intake_digest", "final_digest"):
        address = row[key]
        if address is not None:
            files[address] = store.read_artifact(address).decode("utf-8")
    return {"row": row, "score": score, "artifacts": files}


def read_evidence(store, key):
    return release_evidence(store, store.read_attempt(key))


def safe_altered_pair(store):
    nominal = install(store)
    changed = install(store, control="C09")
    for seed in range(256):
        key = f"c09-unshifted-{seed}"
        public, response = finish(nominal, key, seed)
        baseline = score_attempt(store, key)
        if baseline["finish_violation"]:
            continue
        altered = f"c09-mutation-{seed}"
        assert finish(changed, altered, seed) == (public, response)
        assert score_attempt(store, altered)["finish_violation"]
        return {"seed": seed, "public_matches": True, "actual_event_pair": [0, 1],
                "original": read_evidence(store, key), "mutated": read_evidence(store, altered)}
    raise AssertionError("no valid C09 baseline for declared deterministic witness search")


def monitor_controls(store):
    pos = World(DEV.theta, Q(1,32), DEV.m, DEV.k, DEV.B, DEV.N)
    monitor = NativeService(pos, store)
    for seed in range(2048):
        actual = monitor.monitor_record(seed, 2)
        if any(actual["observations"]):
            break
    else:
        raise AssertionError("no positive monitor witness for C15")
    mismatched = monitor.monitor_record(seed, 2, mechanism="nominal", matched=False)
    matched = monitor.monitor_record(seed, 2, mechanism="nominal", matched=True)
    assert not any(mismatched["observations"]) and matched == actual
    tv = 1 - Q(31,32)**2
    assert tv == Q(63,1024) and tv > Q(1,32)

    c16_rows = []
    for beta in (Q(0), Q(1,32)):
        world = World(Q(1,4), beta, DEV.m, DEV.k, DEV.B, 7)
        svc = install(store, world)
        record = svc.monitor_record(seed, 1)
        h = beta + (1-beta)*Q(29,93)
        q = (1-h)*(1-Q(1,4)-world.theta/2) + h*(1-world.theta)
        cost = Q(3,8)*(1-h)+h
        c16_rows.append({"beta":str(beta),"observed_monitor":record, "high_probability":str(h),
                         "issue_probability":str(q),"paid_price":str(cost)})
    assert Q(c16_rows[0]["issue_probability"]) == Q(247,372) < Q(2,3)
    assert c16_rows[1]["high_probability"] == "1/3"
    assert c16_rows[1]["paid_price"] == "7/12"
    return {
        "C15": {"actual_monitor": actual, "matched_monitor": matched, "mismatched_monitor": mismatched,
                "exact_TV_at_least": str(tv), "exact_finalizer_bound": "1/32"},
        "C16": {"rows": c16_rows, "source_theta": "1/4", "minimum_required_issue": "2/3"},
    }


def run(directory):
    directory.mkdir(parents=True, exist_ok=False)
    with NativeStore(directory/"controls.sqlite") as store:
        check_durable_and_transport(store)
        check_private_boundary(store)
        check_read_and_authority_controls(store)
        check_physical_controls(store)
        bad = install(store, DEV_BAD, "C01")
        missing = install(store, control="C02", guard=False)
        ordinary = missing.check_source("ordinary")
        c06 = []
        for index, world in enumerate((DEV, DEV_OPPOSITE)):
            service = install(store, world, "C06")
            key = f"disclosed-skip-{index}"
            attempt = service.new_attempt(key, index)
            public = attempt.intake()
            field = public["source_fact"]
            # The explicit signed label is a different input channel.
            positive = field in ("+", "positive", True, 1)
            if positive != world.target:
                raise ValueError("unexpected registered C06 target field semantics")
            receipt = public["route_receipt"]
            attempt.probe(f"skip:{receipt['route']}", receipt)
            attempt.declare(positive)
            outcome = read_evidence(store, key)
            assert not outcome["score"]["wrong_declaration"] and outcome["score"]["paid_eighths"] == 0
            c06.append(outcome)
        controls = {
            "C01": {"rejection":failure(lambda: bad.new_attempt("extra-bad",0)),
                    "guard":bad.check_source("guard"), "lab":read_evidence(store,"bad-lab")},
            "C02": {"ordinary":ordinary, "rejection":failure(lambda: missing.new_attempt("extra-no-guard",0)),
                    "guard":failure(lambda: missing.check_source("guard"))},
            "C03": read_evidence(store,"C03"),
            "C04": read_evidence(store,"C04"),
            "C05": read_evidence(store,"C05"),
            "C06": {"valid_zero_paid": c06},
            "C07": {"opposite_delivered_records": [read_evidence(store,"C07+"),read_evidence(store,"C07-")]},
            "C08": {"exact_altered_cut":str(DEV.theta/4+DEV.beta+Q(1,16)),
                    "witness":read_evidence(store,"C08-0")},
            "C09": safe_altered_pair(store),
            "C10": {"represented_destinations":["L"], "actual_omitted_destination":"R",
                    "witness":next(release_evidence(store,row) for row in store.iter_attempts()
                                   if row["trace"]["control"]=="C10"
                                   and score_attempt(store,row["attempt_id"])["actual_destination"]=="R")},
            "C11": read_evidence(store,"C11"),
            "C12": {"carry_changed":next(release_evidence(store,row) for row in store.iter_attempts()
                                        if row["trace"]["control"]=="C12"
                                        and row["trace"]["public_intake"]["prelude"][-1]==1)},
            "C13": read_evidence(store,"C13"),
            "C14": {"normal_rejection":failure(lambda: install(store,control="C14").new_attempt("extra-excess",0)),
                    "actual_excess":"1/8","lab":read_evidence(store,"C14")},
            "C17": {"admitted_direct": [read_evidence(store,"direct-0"),read_evidence(store,"direct-1")],
                    "base_denial":read_evidence(store,"direct-forbidden"),
                    "direct_price":"1/2", "exact_mixed_optimum":"1/6", "binary_target_error":"1/3"},
            "C18": {"native_guard":read_evidence(store,"C18"),
                    "countermodel":{"law":"Uniform[0,1]", "forbidden_topological_support_point":"1/2",
                                    "its_probability":"0"}},
            "C19": {"tickets":list(range(20)), "invalid_calibration":[0],"issued":[0],"violating_issue":[0],
                    "unconditional_failure":"1/20","risk_given_issuance":"1"},
        }
        controls.update(monitor_controls(store))
        store.flush()
        rows = [{"id":row["attempt_id"],"data":release_evidence(store,row)}
                for row in store.iter_attempts()]
    assert set(controls)=={f"C{i:02}" for i in range(1,20)}
    (directory/"observations.json").write_text(json.dumps(controls,sort_keys=True,indent=2)+"\n",
                                               encoding="utf-8",newline="\n")
    (directory/"complete-native-control-records.jsonl").write_text(
        "".join(json.dumps(row,sort_keys=True,separators=(",",":"))+"\n" for row in rows),
        encoding="utf-8",newline="\n")
    print(f"19 predetermined controls with {len(rows)} durable native control records")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    run(parser.parse_args().output)
