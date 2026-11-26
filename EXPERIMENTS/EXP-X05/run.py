"""Freeze-aware replay, independent proof checks, and raw resource measurements."""

from argparse import ArgumentParser
from collections import Counter
import csv
from dataclasses import asdict
import hashlib
from itertools import product
import json
import os
from pathlib import Path
import platform
from statistics import median
import sys
from time import perf_counter_ns
import tracemalloc

from baselines import baseline_queries, solve_explicit
from domain import FREEZES, workload
from engine import Guard, compile_contract, cost_at, empty_counters, solve_symbolic
from reference import (
    RejectedSource, compatible_modes, completion, completion_cost, interpret, optimum,
    policy_signature, reference,
    require, sufficient, target_set, verify_symbolic,
)


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SYMBOLIC = {"lazy", "dominance-off"}
AFFIRMATIVE = {"IDENTIFIED", "CERTIFIED"}


def canonical(data):
    return (json.dumps(data, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_json(destination, data):
    destination.write_bytes(canonical(data))


def run_method(case, method, budgets, seconds=None):
    if method in SYMBOLIC:
        return solve_symbolic(case, budgets, dominance=method == "lazy", seconds=seconds)
    if method in {"direct-partition", "eager-disagreement"}:
        return solve_explicit(case, budgets, eager=method == "eager-disagreement", seconds=seconds)
    raise ValueError(f"unknown method {method}")


def verify_explicit(ref, result):
    status = result["status"]
    counters = result["counters"]
    require(counters["compatible_count"] in {None, ref.count}, "explicit count mismatch")
    if status == "UNRESOLVED":
        require(result["reason"] in {
            "deadline", "completion-cap", "opposite-pair-cap", "partition-row-cap",
            "query-subset-cap",
        }, "unexplained explicit baseline refusal")
        require(result["cost"] is None and not result["selected"], "partial catalog certified")
        return 0
    require(counters["explicit_rows"] == ref.count, "used incomplete explicit catalog")
    outcomes = target_set(ref)
    if status == "INCONSISTENT":
        require(not outcomes, "false baseline inconsistency")
    elif status == "AUDIT_INACCESSIBLE":
        first, second = (completion(ref, modes) for modes in result["witness"])
        first_cost = completion_cost(first, ref.terminal, ref.index)
        second_cost = completion_cost(second, ref.terminal, ref.index)
        targets = {amount is not None and amount <= ref.case.budget
                   for amount in (first_cost, second_cost)}
        require(targets == {False, True} and tuple(row.answers for row in first)
                == tuple(row.answers for row in second), "invalid explicit inaccessible pair")
        require(optimum(ref.queries, ref.edges) is None, "incorrect baseline inaccessibility")
        return 1
    else:
        expected = "IDENTIFIED" if len(outcomes) == 1 else "CERTIFIED"
        require(status == expected, "false baseline identification status")
        indices = result["selected"]
        require(tuple(indices) == tuple(sorted(set(indices)))
                and all(type(i) is int and 0 <= i < len(ref.queries) for i in indices),
                "invalid explicit query subset")
        cost = sum(ref.queries[q] for q in indices)
        require(sufficient(set(indices), ref.edges), "false baseline sufficiency")
        require(cost == result["cost"] == result["lower_bound"] == result["upper_bound"]
                == optimum(ref.queries, ref.edges), "explicit optimality gap")
        if status == "IDENTIFIED":
            require(outcomes == {result["value"]}, "incorrect explicit point identification")
    return 0


def check_one(ref, method, result):
    if ref is None:
        require(result["status"] == "UNRESOLVED" and result["reason"] == "unsupported"
                and result["cost"] is None and not result["selected"],
                "unsupported source escaped refusal")
        return {"witness_pairs": 0, "unsat_rounds": 0}
    if method in SYMBOLIC:
        return verify_symbolic(ref, result)
    return {"witness_pairs": verify_explicit(ref, result), "unsat_rounds": 0}


def check_signatures(ref, local_cap, check_full):
    counters = empty_counters()
    stages, terminal = compile_contract(ref.case, Guard(local_cap, None), counters)
    require(terminal == ref.terminal, "terminal policy catalog disagreement")
    comparisons = len(FREEZES)
    whole_comparisons = 0
    for actual, expected in zip(stages, ref.stages, strict=True):
        require(
            {row.facts: row.signature for row in actual.rows}
            == {row.mode: row.costs for row in expected},
            "local signature or evidence disagreement",
        )
        require({row.facts: row.answers for row in actual.rows} == {
            row.mode: sum(int(answer) << i for i, answer in enumerate(row.answers))
            for row in expected
        }, "query implementation disagreement")
        comparisons += len(actual.rows) * len(FREEZES)
    if check_full:
        for choices in product(*ref.stages):
            modes = tuple(row.mode for row in choices)
            for index in range(len(FREEZES)):
                independent = completion_cost(choices, ref.terminal, index)
                require(cost_at(stages, modes, terminal[index], index) == independent,
                        "full completion freeze disagreement")
                whole_comparisons += 1
    return comparisons, whole_comparisons


def control_checks(case, ref, result):
    expected = {
        "correlated-point": ("IDENTIFIED", None),
        "blocked-but-consistent": ("IDENTIFIED", None),
        "contradictory-evidence": ("INCONSISTENT", "empty-local-evidence"),
        "missing-fast-fact": ("AUDIT_INACCESSIBLE", "whole-interface-collision"),
        "full-positive-support": ("CERTIFIED", None),
        "worst-branch-cost": ("IDENTIFIED", None),
        "unreachable-locator": ("CERTIFIED", None),
        "correlation-pair-excluded": ("CERTIFIED", None),
        "forced-work-refusal": ("UNRESOLVED", "step-cap"),
        "forced-deadline-refusal": ("UNRESOLVED", "deadline"),
        "unsupported-observation": ("UNRESOLVED", "unsupported"),
    }
    status = result["status"], result["reason"]
    require(status == expected[case.name], f"control {case.name} returned {status}")
    if case.name == "correlated-point":
        require(result["value"] is True and len(ref.costs) > 1, "threshold/cost control failed")
    elif case.name == "blocked-but-consistent":
        require(result["value"] is False and ref.infinity and not ref.costs,
                "infinity/compatibility control failed")
    elif case.name in {"full-positive-support", "worst-branch-cost"}:
        touch = case.name == "full-positive-support"
        stage = case.stages[0]
        changes = []
        missed_touch = []
        touch_only_changes = []
        for mode, assignment in compatible_modes(stage):
            expected_cost = completion_cost(completion(ref, (mode,)), ref.terminal, ref.index)
            altered = policy_signature(stage.graph, assignment, first_touch=touch,
                                       first_cost=True)[ref.index]
            if touch:
                root = stage.graph.nodes[0]
                before = interpret(root, assignment)[1]
                destinations = root.actions[0].support
                first, second = (interpret(stage.graph.nodes[b.successor], assignment)[1]
                                 for b in destinations)
                if before == first and before != second:
                    missed_touch.append(mode)
                touch_only = policy_signature(stage.graph, assignment, first_touch=True)[ref.index]
                touch_only = None if touch_only is None else touch_only + ref.terminal[ref.index]
                if touch_only != expected_cost:
                    touch_only_changes.append(mode)
            perturbed_cost = None if altered is None else altered + ref.terminal[ref.index]
            true_value = expected_cost is not None and expected_cost <= case.budget
            perturbed = perturbed_cost is not None and perturbed_cost <= case.budget
            if true_value != perturbed:
                changes.append({
                    "mode": mode, "exact_cost": expected_cost, "perturbed_cost": perturbed_cost,
                    "exact_target": true_value, "perturbed_target": perturbed,
                })
        require(changes, "support perturbation failed to expose a target error")
        if touch:
            require(missed_touch, "root action fails to exercise later-support touch")
        return {"changed_modes": changes, "tested_modes": ref.count,
                "missed_root_r_touch_modes": missed_touch,
                "touch_only_cost_change_modes": touch_only_changes}
    elif case.name == "unreachable-locator":
        rows = {row.mode: row.costs for row in ref.stages[0]}
        require(all(rows[i] == rows[i + 4] for i in range(4)), "unreachable effect propagated")
        return {"irrelevant_fact": 2, "matched_pairs": 4}
    elif case.name == "correlation-pair-excluded":
        require({row.mode for row in ref.stages[0]} == {1, 2}, "incompatible modes present")
        return {"excluded_assignments": [0, 3]}
    return {"expected_status": status[0], "expected_reason": status[1]}


def case_evidence(case, protocol):
    budgets = protocol["budgets"]
    try:
        ref = reference(case)
    except RejectedSource:
        ref = None
    except Exception as error:
        raise RuntimeError(f"independent source check failed for {case.name}") from error
    methods = {}
    checks = {}
    for method in protocol["methods"]:
        result = run_method(case, method, budgets)
        methods[method] = result
        try:
            checks[method] = check_one(ref, method, result)
        except AssertionError as error:
            raise RuntimeError(f"{case.name}, {method}: {error}") from error

    signatures = (0, 0)
    comparators = None
    projection = None
    if ref is not None:
        check_full = case.stratum in {"control", "small"} and ref.count <= budgets["explicit_completions"]
        signatures = check_signatures(ref, budgets["symbolic_steps"], check_full)
        selected_optimum = optimum(ref.queries, ref.edges)
        all_queries = set(range(len(ref.queries)))
        projection = {
            "compatible_count": ref.count,
            "stage_domain_sizes": tuple(len(group) for group in ref.stages),
            "target_values": tuple(sorted(target_set(ref))),
            "attainable_finite_costs": tuple(sorted(ref.costs)),
            "attainable_infinity": ref.infinity,
            "known_local_edges": tuple(len(edges) for edges in ref.edges),
            "pivotal_independent_facts": ref.pivotal_facts,
            "minimum_audit_cost": selected_optimum,
            "query_all_cost": sum(ref.queries),
            "query_all_sufficient": bool(ref.count and sufficient(all_queries, ref.edges)),
        }
        if check_full and ref.count:
            comparators = baseline_queries(ref, protocol["sampling"]["random_query_permutations"],
                                           protocol["sampling"]["random_query_seed"])
            for outcome in [comparators["greedy"], *comparators["random"]]:
                actual = sufficient(set(outcome["selected"]), ref.edges)
                require(actual == (outcome["cost"] is not None), "acquisition comparator unchecked")
                if actual:
                    require(selected_optimum <= outcome["cost"]
                            == sum(ref.queries[q] for q in outcome["selected"]),
                            "acquisition cost discrepancy")
        if case.stratum == "small":
            for method, result in methods.items():
                require(result["status"] != "UNRESOLVED", f"small scope unexplained refusal: {method}")
    control = control_checks(case, ref, methods["lazy"]) if case.stratum == "control" else None
    return {
        "case": case.name, "stratum": case.stratum, "seed": case.seed, "freeze": case.freeze,
        "width": case.stages[0].width, "stages": len(case.stages), "threshold": case.threshold,
        "correlation": case.correlation, "budget": case.budget,
        "raw_assignment_count": 2 ** sum(stage.width for stage in case.stages),
        "queries": tuple(f"{i}:{query.name}" for i, stage in enumerate(case.stages)
                         for query in stage.queries),
        "query_prices": tuple(query.price for stage in case.stages for query in stage.queries),
        "source_sha256": sha256(canonical(asdict(case))),
        "reference": projection, "methods": methods, "checks": checks, "control": control,
        "local_and_terminal_signature_checks": signatures[0],
        "whole_completion_signature_checks": signatures[1],
        "acquisition_comparators": comparators,
    }


def summarize(cases, protocol):
    method_counts = {}
    for method in protocol["methods"]:
        statuses = Counter(entry["methods"][method]["status"] for entry in cases)
        reasons = Counter(entry["methods"][method]["reason"] for entry in cases
                          if entry["methods"][method]["status"] == "UNRESOLVED")
        method_counts[method] = {"status": dict(statuses), "unresolved_reasons": dict(reasons)}
    certified = [entry for entry in cases if entry["methods"]["lazy"]["status"] in AFFIRMATIVE]
    large = [entry for entry in certified
             if entry["reference"]["compatible_count"] > protocol["budgets"]["explicit_completions"]]
    winner = max(large, key=lambda entry: entry["reference"]["compatible_count"], default=None)
    return {
        "protocol_version": protocol["protocol_version"],
        "cases": len(cases), "strata": dict(Counter(entry["stratum"] for entry in cases)),
        "methods": method_counts,
        "local_and_terminal_signature_checks": sum(entry["local_and_terminal_signature_checks"]
                                                   for entry in cases),
        "whole_completion_signature_checks": sum(entry["whole_completion_signature_checks"]
                                                 for entry in cases),
        "checked_witness_pairs": sum(check["witness_pairs"] for entry in cases
                                     for check in entry["checks"].values()),
        "checked_symbolic_unsat_rounds": sum(check["unsat_rounds"] for entry in cases
                                            for check in entry["checks"].values()),
        "zero_gap_primary_cases": len(certified),
        "unexplained_discrepancies": 0,
        "false_certifications": 0,
        "beyond_explicit_cap_certified": len(large),
        "largest_verified_case": None if winner is None else {
            "case": winner["case"],
            "compatible_count": winner["reference"]["compatible_count"],
            "pivotal_independent_facts": winner["reference"]["pivotal_independent_facts"],
            "audit_cost": winner["methods"]["lazy"]["cost"],
            "oracle_calls": winner["methods"]["lazy"]["counters"]["oracle_calls"],
            "materialized_completions": winner["methods"]["lazy"]["counters"]["materialized_completions"],
            "witness_completions": winner["methods"]["lazy"]["counters"]["witness_completions"],
        },
    }


def side_metadata():
    return {
        "python": platform.python_implementation() + " " + platform.python_version(),
        "system": platform.system(), "release": platform.release(),
        "version": platform.version(), "machine": platform.machine(),
        "logical_processors": os.cpu_count(), "hash_seed": os.environ.get("PYTHONHASHSEED"),
    }


def measure(cases, evidence, protocol, output):
    budgets = protocol["budgets"]
    controls = protocol["sampling"]
    keys = (
        "case", "method", "run", "measurement", "status", "reason", "cost", "wall_ns", "peak_bytes",
        "compiled_modes", "materialized_completions", "witness_completions", "oracle_calls",
        "pair_transitions", "state_prunes", "peak_pair_states", "optimizer_calls",
        "optimizer_searches", "row_visits", "opposite_pairs", "query_subsets", "work_steps",
    )
    timed = {}
    with (output / "measurements.csv").open("w", encoding="ascii", newline="") as file:
        csv_writer = csv.DictWriter(file, fieldnames=keys, lineterminator="\n")
        csv_writer.writeheader()
        for case, entry in zip(cases, evidence, strict=True):
            timed[case.name] = {}
            for method in protocol["methods"]:
                timings = []
                peaks = []
                statuses = Counter()
                losses = 0
                for label, runs, seconds in (
                    ("time", controls["time_repetitions"], budgets["run_wall_seconds"]),
                    ("allocation", controls["allocation_repetitions"], budgets["traced_run_wall_seconds"]),
                ):
                    for i in range(runs):
                        traced = label == "allocation"
                        if traced:
                            tracemalloc.start()
                        start = perf_counter_ns()
                        try:
                            result = run_method(case, method, budgets, seconds)
                            wall = perf_counter_ns() - start
                            peak = tracemalloc.get_traced_memory()[1] if traced else None
                        finally:
                            if traced:
                                tracemalloc.stop()
                        final = entry["methods"][method]
                        if result["reason"] == "deadline" and final["reason"] != "deadline":
                            require(result["status"] == "UNRESOLVED", "deadline produced a certificate")
                            losses += 1
                        else:
                            require(result == final, f"measurement disagrees with checked replay: {case.name} {method}")
                        statuses[result["status"]] += 1
                        if traced:
                            peaks.append(peak)
                        else:
                            timings.append(wall)
                        fields = {key: result["counters"].get(key) for key in keys}
                        fields.update(
                            case=case.name, method=method, run=i + 1, measurement=label,
                            status=result["status"], reason=result["reason"], cost=result["cost"],
                            wall_ns=wall, peak_bytes=peak,
                        )
                        csv_writer.writerow(fields)
                        file.flush()
                timed[case.name][method] = {
                    "median_wall_ns": median(timings), "peak_python_bytes": max(peaks),
                    "status_counts": dict(statuses), "extra_deadline_refusals": losses,
                }
            print(f"Measured {case.name}", flush=True)
    write_json(output / "performance.json", {"host": side_metadata(), "cases": timed})


def scratch_destination(path):
    path = path.resolve()
    if not path.is_relative_to((ROOT / "scratch").resolve()):
        raise ValueError("output directory must be inside the checkout's ignored scratch directory")
    path.mkdir(parents=True, exist_ok=True)
    return path


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify committed stable and archived evidence.")
    parser.add_argument("--measure", action="store_true", help="Collect fresh wall/peak measurements.")
    parser.add_argument("--out", type=Path, default=ROOT / "scratch" / "x05" / "replay")
    args = parser.parse_args()
    protocol = json.loads((HERE / "protocol.json").read_text(encoding="utf-8"))
    if side_metadata()["python"] != protocol["environment"]["python"]:
        parser.error(f"frozen environment uses {protocol['environment']['python']}")
    output = scratch_destination(args.out)
    cases = workload(protocol)
    evidence = []
    for case in cases:
        evidence.append(case_evidence(case, protocol))
        print(f"Checked {case.name}", flush=True)
    summary = summarize(evidence, protocol)
    stable = {"summary.json": canonical(summary), "invariants.json": canonical(evidence)}
    for name, blob in stable.items():
        (output / name).write_bytes(blob)
        print(f"{sha256(blob)}  {name}", flush=True)
    if args.measure:
        measure(cases, evidence, protocol, output)
    else:
        print(json.dumps(summary, sort_keys=True), flush=True)
    if args.check:
        stored = HERE / "results"
        manifest = json.loads((stored / "manifest.json").read_text(encoding="ascii"))
        for name, blob in stable.items():
            require((stored / name).read_bytes() == blob, f"stable byte mismatch: {name}")
            require(manifest["stable"][name] == sha256(blob), f"stable hash mismatch: {name}")
        for name in ("measurements.csv", "performance.json"):
            require(manifest["archived"][name] == sha256((stored / name).read_bytes()),
                    f"archive hash mismatch: {name}")
        print("Committed evidence verified.", flush=True)


if __name__ == "__main__":
    main()
