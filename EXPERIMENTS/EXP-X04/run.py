"""Run or independently replay the frozen EXP-X04 corpus using Python's standard library."""

import argparse
from collections import Counter
from dataclasses import asdict
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import platform
import time
import tracemalloc

from src.audit import fixed_policy, greedy_policy, solve
from src.cases import address, address_bounds, controls, routed, sampled
from src.predecessor import load_predecessor
from src.reference import adaptive_budget_optimum, certificate_optima, measure, replay, verify_witness


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "configs" / "protocol.json"
RESULTS = ROOT / "results"


def _encode(obj, *, indent=None):
    return json.dumps(obj, sort_keys=True, indent=indent, separators=None if indent else (",", ":"))


def _json(obj):
    return (_encode(obj, indent=2) + "\n").encode("utf-8")


def _jsonl(rows):
    return "".join(_encode(row) + "\n" for row in rows).encode("utf-8")


def _status(case, cost):
    if not case.rows:
        return "INCONSISTENT"
    return "CERTIFIED" if cost is not None else "AUDIT_INACCESSIBLE"


def _trial(case, tree):
    decisions = replay(case, tree)
    return measure(decisions), decisions


def _check_predecessor(case, uniform, locals_, scopes):
    comparisons = {"": uniform[0] if uniform else None, **locals_}
    for identity, cost in comparisons.items():
        known = scopes.pop((case.name, identity))
        if known != (_status(case, cost), cost):
            raise AssertionError((case.name, identity, known, cost))
    return len(comparisons)


def _random_summary(measures, exact):
    if not measures:
        return None
    if any(item["certified"] != measures[0]["certified"] for item in measures):
        raise AssertionError("every complete informative policy must cover the same completions")
    worst = [value["worst_cost"] for value in measures]
    return {
        "trials": len(worst),
        "minimum_worst_cost": min(worst),
        "maximum_worst_cost": max(worst),
        "mean_worst_cost": str(Fraction(sum(worst), len(worst))),
        "mean_expected_cost": str(
            sum((Fraction(value["expected_cost"]) for value in measures), Fraction()) / len(worst)
        ),
        "certified": measures[0]["certified"],
        "completions": measures[0]["completions"],
        "optimal_runs": sum(cost == exact for cost in worst) if exact is not None else None,
    }


def run_case(case, index, protocol, scopes):
    tracemalloc.start()
    started = time.perf_counter_ns()
    try:
        exact = solve(case)
        elapsed = time.perf_counter_ns() - started
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    budget, budget_states = adaptive_budget_optimum(case)
    uniform, locals_ = certificate_optima(case)
    if exact.cost != budget or exact.status != _status(case, budget):
        raise AssertionError((case.name, "independent adaptive budget disagreement", exact.cost, budget))
    if exact.status != _status(case, uniform[0] if uniform else None):
        raise AssertionError((case.name, "uniform and adaptive identifiability disagreement"))

    predecessor_scopes = 0
    if case.family == "predecessor_x03":
        predecessor_scopes = _check_predecessor(case, uniform, locals_, scopes)

    if exact.status == "AUDIT_INACCESSIBLE":
        verify_witness(case, exact.witness)

    metrics = {}
    histories = {"case": case.name, "policies": {}}

    def add(name, tree):
        observed, decisions = _trial(case, tree)
        if observed is not None and exact.cost is not None:
            observed["worst_cost_gap"] = observed["worst_cost"] - exact.cost
            if observed["certified"] != len(case.rows) or observed["worst_cost_gap"] < 0:
                raise AssertionError((case.name, name, "comparator violates the exact bound"))
        metrics[name] = observed
        histories["policies"][name] = decisions

    if exact.tree is not None:
        add("adaptive_optimum", exact.tree)
        if metrics["adaptive_optimum"]["worst_cost"] != exact.cost:
            raise AssertionError((case.name, "emitted optimal policy has unexpected replay cost"))

    if uniform is not None:
        add("uniform_static", fixed_policy(case, uniform[1]))
        if metrics["uniform_static"]["worst_cost"] != uniform[0]:
            raise AssertionError((case.name, "emitted uniform policy has unexpected replay cost"))
    add("full_acquisition", fixed_policy(case, tuple(range(len(case.queries)))))
    add("greedy_partition", greedy_policy(case, "partition"))
    add("edge_cut", greedy_policy(case, "edge_cut"))

    random_runs = []
    random_policies = protocol["random_baseline"]
    if case.rows:
        for trial in range(random_policies["trials"]):
            seed = random_policies["seed"] + index * random_policies["trials"] + trial
            name = f"random_{trial:02d}"
            add(name, greedy_policy(case, "random", seed))
            random_runs.append(metrics.pop(name))

    local_max = None if not locals_ or None in locals_.values() else max(locals_.values())
    if exact.cost is not None and not (local_max <= exact.cost <= uniform[0]):
        raise AssertionError((case.name, "cost hierarchy violated"))

    fully_resolved = Counter(row.answers for row in case.rows)
    result = {
        "case": case.name,
        "family": case.family,
        "rows": len(case.rows),
        "questions": len(case.queries),
        "status": exact.status,
        "minimax_cost": exact.cost,
        "static_cost": uniform[0] if uniform else None,
        "max_local_cost": local_max,
        "local_costs": locals_,
        "static_queries": [case.queries[index] for index in uniform[1]] if uniform else None,
        "static_minus_minimax": uniform[0] - exact.cost if uniform else None,
        "inaccessibility_witness": exact.witness,
        "minimax_beliefs": exact.states,
        "independent_budget_states": budget_states,
        "predecessor_scopes": predecessor_scopes,
        "full_identity_certified_by_exhaustion": sum(size == 1 for size in fully_resolved.values()),
        "policies": metrics,
        "random": _random_summary(random_runs, exact.cost),
    }
    timing = {"case": case.name, "solver_elapsed_ns": elapsed, "solver_peak_python_bytes": peak}
    histories["optimal_tree"] = exact.tree
    return result, histories, timing


def _all_cases(protocol, predecessor_cases):
    address_spec = protocol["address"]
    routed_spec = protocol["routed"]
    return [
        *controls(protocol["controls"]),
        *(address(width, address_spec["query_cost"]) for width in address_spec["explicit_widths"]),
        *(routed(routed_spec, condition) for condition in routed_spec["conditions"]),
        *predecessor_cases,
        *sampled(protocol["seeded"]),
    ]


def _report_groups(results):
    families = sorted({row["family"] for row in results})
    return {
        family: {
            "cases": len(group),
            "statuses": dict(Counter(row["status"] for row in group)),
            "strict_minimax_savings": sum(
                row["static_minus_minimax"] is not None and row["static_minus_minimax"] > 0
                for row in group
            ),
            "tied_minimax_static": sum(row["static_minus_minimax"] == 0 for row in group),
        }
        for family in families
        if (group := [row for row in results if row["family"] == family])
    }


def _check_controls(results, protocol):
    named = {row["case"]: row for row in results}
    expected = {
        "empty_domain": ("INCONSISTENT", None, None, None),
        "constant_target": ("CERTIFIED", 0, 0, 0),
        "no_queries": ("AUDIT_INACCESSIBLE", None, None, None),
        "full_answer_alias": ("AUDIT_INACCESSIBLE", None, None, None),
        "majority_of_three": ("CERTIFIED", 2, 3, 3),
        "categorical_weighted": ("CERTIFIED", 5, 5, 6),
        "all_queries_required": ("CERTIFIED", 6, 6, 6),
        "cost_scale_three": ("CERTIFIED", 6, 9, 9),
    }
    for width in protocol["address"]["explicit_widths"]:
        bound = address_bounds(width, protocol["address"]["query_cost"])
        expected[f"address_{width}"] = (
            "CERTIFIED", bound["max_local_cost"], bound["minimax_cost"], bound["static_cost"],
        )
    for name, known in expected.items():
        row = named[name]
        actual = tuple(row[key] for key in ("status", "max_local_cost", "minimax_cost", "static_cost"))
        if actual != known:
            raise AssertionError((name, "analytical control disagreement", actual, known))


def execute(protocol):
    predecessor, scopes = load_predecessor(ROOT, protocol["x03"])
    expected_scopes = len(scopes)
    cases = _all_cases(protocol, predecessor)
    cap = protocol["sample_budget"]
    if any(
        len(case.queries) > cap["maximum_explicit_queries"] or
        len(case.rows) > cap["maximum_explicit_completions"]
        for case in cases
    ):
        raise ValueError("a measured case is outside the frozen explicit budget")

    partitions = [run_case(case, index, protocol, scopes) for index, case in enumerate(cases)]
    if scopes:
        raise AssertionError("unmatched published X03 scopes")
    results, histories, times = zip(*partitions, strict=True)
    _check_controls(results, protocol)
    address_spec = protocol["address"]
    summary = {
        "schema": "pcx.exp-x04.results.v1",
        "measured_cases": len(cases),
        "measured_completion_rows": sum(len(case.rows) for case in cases),
        "independent_reference_disagreements": 0,
        "x03_scope_agreements": expected_scopes,
        "routed_coordinate_checks": sum(
            len(condition["site_costs"]) ** 2 * 2 ** len(condition["site_costs"]) * 8
            for condition in protocol["routed"]["conditions"]
        ),
        "certified_minimax_policies": sum(row["status"] == "CERTIFIED" for row in results),
        "validated_inaccessibility_witnesses": sum(row["inaccessibility_witness"] is not None for row in results),
        "independently_replayed_policy_paths": sum(
            len(decisions) for history in histories for decisions in history["policies"].values()
        ),
        "family_summary": _report_groups(results),
        "derived_address_bounds": [
            address_bounds(width, address_spec["query_cost"])
            for width in address_spec["derived_widths"]
        ],
        "cases": results,
    }
    timings = {
        "metric": "Exact production optimizer including construction of the chosen policy",
        "clock": "time.perf_counter_ns",
        "memory": "tracemalloc Python allocator only",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cases": times,
    }
    payloads = {
        "summary.json": _json(summary),
        "tables.jsonl": _jsonl(asdict(case) for case in cases),
        "policy_replays.jsonl": _jsonl(histories),
    }
    return summary, payloads, _json(timings)


def _digest(payload):
    return sha256(payload).hexdigest()


def write_results(payloads, observations):
    RESULTS.mkdir(exist_ok=True)
    artifacts = {**payloads, "runtime_observed.json": observations}
    for name, payload in artifacts.items():
        (RESULTS / name).write_bytes(payload)
    manifest = {
        "configs/protocol.json": _digest(CONFIG.read_bytes()),
        **{f"results/{name}": _digest(payload) for name, payload in artifacts.items()},
    }
    rows = (f"{digest}  {name}" for name, digest in sorted(manifest.items()))
    (RESULTS / "manifest.sha256").write_bytes(("\n".join(rows) + "\n").encode("ascii"))


def check_results(payloads):
    manifest = dict(
        (name, digest)
        for digest, name in (
            line.split("  ", maxsplit=1)
            for line in (RESULTS / "manifest.sha256").read_text(encoding="ascii").splitlines()
        )
    )
    expected = {"configs/protocol.json", "results/runtime_observed.json"}
    expected.update(f"results/{name}" for name in payloads)
    if set(manifest) != expected:
        raise AssertionError("manifest must cover the exact configured artifacts")
    for name, recorded in manifest.items():
        if _digest((ROOT / name).read_bytes()) != recorded:
            raise AssertionError(f"manifest mismatch for {name}")
    for name, regenerated in payloads.items():
        if _digest(regenerated) != manifest[f"results/{name}"]:
            raise AssertionError(f"independent regeneration mismatch for {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--write", action="store_true", help="write frozen evidence and host observations")
    action.add_argument("--check", action="store_true", help="compare regenerated evidence and original manifest")
    options = parser.parse_args()
    protocol = json.loads(CONFIG.read_bytes())
    summary, payloads, observations = execute(protocol)
    if options.write:
        write_results(payloads, observations)
    else:
        check_results(payloads)
    print(_encode({
        key: value for key, value in summary.items() if key not in {"cases", "derived_address_bounds"}
    }, indent=2))


if __name__ == "__main__":
    main()
