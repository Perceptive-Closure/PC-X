"""Run the preregistered EXP-X16 forecast and native validation."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter_ns

from controls import check_controls
from evidence import (Native, digest, fastest_jobs, read_json, require, traverse,
                      verify_artifacts, verify_inventory)
from measure import compare
from planner import accepting_paths, dump, forecast, static_answer


EXPERIMENT = Path(__file__).resolve().parent
PURE = ("static_target", "static_identity", "static_all",
        "adaptive_pure_target", "adaptive_pure_identity")
ONLINE = ("online", "online_identity", "online_fixed", "structured_scores")
REJECTED_SCOPE = {
    "cartesian": "A disconnected stale/stale suffix would add a false negative path with work 5",
    "suppressed-receipt": "Both known modes cost 4 and complete separately, with common online completion infeasible",
    "split-calls": "Projected job.fast is absent; only the two mode-specific literals meet the deadline",
    "free-guard": "The initial observation discloses the label; the changed interface needs zero paid audit",
    "missing-long": "Short-only audit priced 1 lacks the genuine LONG branch; exact audit costs 3 or 2",
    "hidden-carry": "The same stage, suffix and meter quote 1 or 5 from different earlier histories",
    "changed-instrument": "An identical paid transcript and verdict can accompany an incorrectly routed file",
}


def register(catalogue, source, draw_path):
    value = forecast(catalogue)
    return {"schema": 1, "source_commit": source, "draw_sha256": digest(draw_path.read_bytes()),
            "control_forecasts": REJECTED_SCOPE, **value}


def audit_source(native, profiles, forecasts):
    tasks = []
    paths = []
    start = perf_counter_ns()
    for name, profile in profiles.items():
        for index, path in enumerate(accepting_paths(profile)):
            ids = [edge["id"] for edge in path]
            tasks.append({"id": f"anchor-{name}-{index}", "op": "inventory", "profile": name, "path": ids})
            paths.append(path)
    compilation_ns = perf_counter_ns() - start
    start = perf_counter_ns()
    answers = native.batch(tasks)
    native_ns = perf_counter_ns() - start
    inventories = {}
    ledger = []
    start = perf_counter_ns()
    for task, path, result in zip(tasks, paths, answers, strict=True):
        name = task["profile"]
        rows, guards = verify_inventory(profiles[name], path, result)
        cheapest, actions = fastest_jobs(rows, len(path))
        theoretical = next(target for target in forecasts[name]["targets"] if target["path"] == task["path"])
        require(cheapest == theoretical["known_work"], "native minimum lawful job tariff disagrees")
        inventories[name, tuple(task["path"])] = result, rows, actions
        ledger.append({"profile": name, "path": task["path"], "initial": result["initial"],
                       "cheapest_known_work": cheapest, "direct_actions": actions, "guards": guards})
    elapsed = {"source_request_compile_ns": compilation_ns, "signed_native_inventory_batch_ns": native_ns,
               "external_row_verification_ns": perf_counter_ns() - start}
    return inventories, ledger, elapsed


def pure_comparisons(native, valid, profiles, forecasts):
    tasks = []
    assignment = []
    for name in valid:
        result = forecasts[name]
        for target in result["targets"]:
            for treatment in PURE:
                plan = result[treatment]
                configuration = ({"queries": plan["queries"]} if "queries" in plan
                                 else {"static_policy": plan["policy"]})
                tasks.append({"id": f"pure-{len(tasks)}", "op": "static", "profile": name,
                              "path": target["path"], **configuration})
                assignment.append((treatment, target))
    answers = native.batch(tasks)
    groups = defaultdict(list)
    logs = []
    for task, (treatment, target), outcome in zip(tasks, assignment, answers, strict=True):
        require(outcome["status"] == "stopped", "static treatment failed")
        name = task["profile"]
        expected = {}
        for stage, edge_id in zip(profiles[name]["stages"], task["path"], strict=True):
            edge = next(edge for edge in stage["edges"] if edge["id"] == edge_id)
            expected.update({q["id"]: {"id": q["id"], "paid": q["price"], "answer": static_answer(q, edge)}
                             for q in stage["statics"]})
        history = tuple((turn["id"], turn["answer"]) for turn in outcome["steps"])
        require(outcome["steps"] == [expected[query] for query in outcome["sequence"]]
                and dict(history) == outcome["answers"]
                and sum(turn["paid"] for turn in outcome["steps"]) == outcome["paid"],
                "static quote or answer trace mismatch")
        if "queries" in task:
            require(task["queries"] == outcome["sequence"], "static panel not executed exactly")
        else:
            node = task["static_policy"]
            for query, answer in history:
                require(node["ask"] == query, "wrong pure adaptive query")
                node = node["next"][answer]
            require(outcome["verdict"] == node["verdict"] == target["label"], "pure adaptive verdict")
        groups[name, treatment].append((history, target, outcome["paid"]))
        logs.append({"treatment": treatment, "task": task, "native": outcome})
    for (name, treatment), results in groups.items():
        classes = defaultdict(set)
        for history, target, _ in results:
            key = tuple(target["path"]) if treatment.endswith("identity") else target["label"]
            classes[history].add(key)
        require(all(len(cell) == 1 for cell in classes.values()), "pure query collision separates no target")
        require(max(paid for _, _, paid in results) == forecasts[name][treatment]["value"],
                "pure comparator worst price disagrees with optimum")
    return logs


def online_roster(valid, forecasts, inventories, profiles):
    schedules = {}
    report = {}
    for name in valid:
        result = forecasts[name]
        report[name] = {}
        for treatment in ONLINE:
            plan = result[treatment]
            if plan is None:
                continue
            if plan["value"] is None:
                require(plan.get("refutation") or (treatment == "online_fixed" and plan["states"] > 0),
                        "infeasible optimum lacks certificate")
                report[name][treatment] = {"value": None, "native_support_paths": 0}
                continue
            cells = defaultdict(set)
            total = 0
            worst = 0
            for target in result["targets"]:
                path = tuple(target["path"])
                inventory, rows, _ = inventories[name, path]
                leaves = traverse(plan["policy"], rows, inventory["initial"])
                schedules[name, path, treatment] = leaves
                total += len(leaves)
                for leaf in leaves:
                    label = target["label"]
                    require(leaf["verdict"] == label
                            and (leaf["done"] == len(path) if label == "YES" else leaf["done"] < len(path))
                            and leaf["work"] <= profiles[name]["deadline"]
                            and len(leaf["tape"]) <= profiles[name]["horizon"],
                            "registered policy violates target or useful obligation")
                    worst = max(worst, leaf["paid"])
                    cells[tuple(leaf["receipt_trace"])].add(path if treatment == "online_identity" else label)
            require(worst == plan["value"] and all(len(cell) == 1 for cell in cells.values()),
                    "online maximum or identity trace differs")
            report[name][treatment] = {"value": worst, "native_support_paths": total}
    return schedules, report


def execute(native, valid, profiles, forecasts, heldouts, inventories, schedules):
    tasks = []
    expected = []
    logs = []
    examples = {}
    direct = {}
    for item in heldouts:
        name = item["profile"]
        path = tuple(item["path"])
        before, _, actions = inventories[name, path]
        target = next(target for target in forecasts[name]["targets"] if target["path"] == item["path"])
        base = {"op": "run", "profile": name, "path": item["path"], "document": item["document"]}
        tasks.append({**base, "id": "direct-" + item["id"], "actions": actions})
        expected.append(("direct", item, before["initial"], target, None))
        if name in valid:
            for treatment in ONLINE:
                for index, leaf in enumerate(schedules.get((name, path, treatment), [])):
                    policy = forecasts[name][treatment]["policy"]
                    tasks.append({**base, "id": f"{treatment}-{item['id']}-{index}",
                                  "policy": policy, "tape": leaf["tape"]})
                    expected.append((treatment, item, before["initial"], target, leaf))
    answers = native.batch(tasks)
    for task, (treatment, item, initial, target, leaf), answer in zip(tasks, expected, answers, strict=True):
        profile = profiles[item["profile"]]
        full = verify_artifacts(native, task, profile, answer)
        yes = target["label"] == "YES"
        require(initial == answer["initial"] and answer["truth"]["complete"] == yes,
                "native useful truth differs from frozen intrinsic target")
        if treatment == "direct":
            direct[item["id"]] = answer
            require(answer["paid"] == 0 and
                    ((yes and answer["status"] == "manual-done" and answer["work"] == target["known_work"])
                     or (not yes and answer["status"] == "denied" and answer["reason"] == "work-deadline"
                         and target["known_work"] > profile["deadline"])), "trusted direct native check failed")
        else:
            trace = [f"{step['obs']}|{step['next_meter']}" for step in answer["steps"]]
            require(answer["status"] == "stopped" and
                    (answer["verdict"], answer["paid"], answer["work"], answer["truth"]["done"], trace)
                    == (target["label"], leaf["paid"], leaf["work"], leaf["done"], leaf["receipt_trace"]),
                    "native run differs from registered full-support policy")
        if yes and full is not None and treatment == "direct":
            examples.setdefault(item["profile"], full)
        logs.append({"treatment": treatment, "installation": item["id"], "task": task, "native": answer})
    return logs, examples, direct


def run(catalogue, forecasts, heldouts, authority, scratch, out, training):
    out.mkdir(parents=True, exist_ok=False)
    profiles = {profile["id"]: profile for profile in catalogue["profiles"]}
    valid = catalogue["valid_profiles"]
    native = Native(EXPERIMENT, authority, scratch)
    pins = forecasts["profiles"]
    inventory, ledger, source_times = audit_source(native, profiles, pins)
    start = perf_counter_ns()
    pure = pure_comparisons(native, valid, profiles, pins)
    source_times["native_static_all_trials_and_readback_ns"] = perf_counter_ns() - start
    start = perf_counter_ns()
    schedules, policy_scope = online_roster(valid, pins, inventory, profiles)
    source_times["full_support_policy_checks_ns"] = perf_counter_ns() - start
    start = perf_counter_ns()
    logs, examples, direct = execute(native, valid, profiles, pins, heldouts, inventory, schedules)
    source_times["native_heldout_work_and_file_verification_ns"] = perf_counter_ns() - start
    start = perf_counter_ns()
    controls, control_runs, examples_extra = check_controls(native, profiles, forecasts, heldouts, inventory, direct)
    source_times["native_control_trials_and_verification_ns"] = perf_counter_ns() - start
    dumps = logs + pure + control_runs
    cases = defaultdict(dict)
    for name in valid:
        group = [item for item in heldouts if item["profile"] == name]
        report = pins[name]
        counts = {label: sum(item["nominal_stratum"] == label for item in group) for label in ("YES", "NO")}
        for treatment in ONLINE:
            applicable = [row["native"] for row in logs
                          if row["treatment"] == treatment and row["task"]["profile"] == name]
            if treatment in policy_scope[name]:
                policy_scope[name][treatment].update({
                    "heldout_runs": len(applicable),
                    "heldout_worst_paid": max((row["paid"] for row in applicable), default=None),
                })
        guards = [row for row in ledger if row["profile"] == name]
        cases[name] = {
            "eligible_paths": len(guards), "heldout_targets": counts,
            "known_work_window": [min(row["cheapest_known_work"] for row in guards),
                                  max(row["cheapest_known_work"] for row in guards)],
            "pure": {treatment: report[treatment]["value"] for treatment in PURE},
            "online": policy_scope[name],
        }
    measurement = compare([profiles[name] for name in valid])
    dump(out / "summary.json", {
        "schema": 1, "source_commit": forecasts["source_commit"], "training": training,
        "profiles": cases, "controls": controls,
        "counts": {
            "source_paths": len(ledger), "valid_source_paths": sum(row["profile"] in valid for row in ledger),
            "literal_command_rows": sum(len(row["guards"]) for row in ledger),
            "supported_source_successor_checks": sum(len(guard["support"]) for row in ledger for guard in row["guards"]),
            "diagnostic_stage_guard_pairs": sum(len(row["path"]) for row in ledger),
            "heldout_installations": len(heldouts),
            "valid_heldout_installations": sum(item["profile"] in valid for item in heldouts),
            "pure_native_runs": len(pure), "native_heldout_work_runs": len(logs),
            "deliberate_control_runs": len(control_runs) + 1, "native_batch_processes": native.calls,
            "native_tasks": native.task_count,
            "artifacts_read_back": sum(row["native"].get("truth", {}).get("done", 0) for row in dumps),
        },
    })
    dump(out / "anchor-ledger.json", ledger)
    dump(out / "artifact-examples.json", {**examples, **examples_extra})
    dump(out / "raw-benchmarks.json", {"source": source_times, **measurement})
    with (out / "runs.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for row in dumps:
            stream.write(json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n")
    print(f"Verified {len(ledger)} source installations, {len(heldouts)} selected installations "
          f"and {len(dumps)} recorded native calls.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="operation", required=True)
    forward = modes.add_parser("forecast")
    forward.add_argument("source")
    forward.add_argument("draw", type=Path)
    forward.add_argument("out", type=Path)
    execution = modes.add_parser("run")
    for name in ("forecast", "heldout", "authority", "scratch", "out"):
        execution.add_argument(name, type=Path)
    execution.add_argument("--training", action="store_true")
    execution.add_argument("--deps", type=Path)
    args = parser.parse_args()
    catalogue = read_json(EXPERIMENT / "cases/catalogue.json")
    if args.operation == "forecast":
        dump(args.out, register(catalogue, args.source, args.draw))
    else:
        forecasts = read_json(args.forecast)
        seal = read_json(args.authority)
        require(forecasts["source_commit"] == seal["source_commit"], "forecast and native authority differ")
        if args.training:
            require(seal["source_commit"] == "0" * 40, "training requires marked dummy source")
        else:
            require(seal["source_commit"] != "0" * 40 and args.deps is not None,
                    "official runs require verified published source and pinned beacon dependencies")
            expected = (EXPERIMENT / "results/forecast.json", EXPERIMENT / "custody/heldout.json",
                        EXPERIMENT / "custody/authority.json")
            actual = tuple(path.resolve() for path in (args.forecast, args.heldout, args.authority))
            require(actual == expected, "official inputs must be the opened, co-located repository snapshot")
            subprocess.run([sys.executable, "-B", str(EXPERIMENT / "custody/releasecheck.py"),
                            "opening", str(EXPERIMENT), str(args.deps.resolve())], check=True)
        run(catalogue, forecasts, read_json(args.heldout), args.authority, args.scratch, args.out, args.training)


if __name__ == "__main__":
    main()
