"""Regenerate and independently check the EXP-X03 evidence bundle."""

import argparse
from collections import Counter, defaultdict
import csv
from dataclasses import replace
from fractions import Fraction
from hashlib import sha256
from io import StringIO
import json
from pathlib import Path
import platform
from time import perf_counter

from src.baselines import evaluate
from src.certificates import CERTIFIED, INACCESSIBLE, disagreement_edges, solve
from src.corpus import cases
from src.reference import conflict, exact_by_partition, subsets, verify_proof, verify_witness


BASE = Path(__file__).resolve().parent
COMPARATORS = ("greedy", "deletion", "exhaustive", "random")


def amount(value):
    return "" if value is None else str(value)


def check_subset_characterization(problem, realized):
    pairs = disagreement_edges(problem, realized)
    multiple_target_cells = 0
    for selected in subsets(len(problem.costs)):
        mask = sum(1 << query for query in selected)
        exact_conflict = conflict(problem, selected, realized)
        if (exact_conflict is not None) != any(not (edge & mask) for edge, _ in pairs):
            raise AssertionError(("subset characterization", problem.name, realized, selected))
        if exact_conflict is not None:
            if not verify_witness(problem, exact_conflict, selected, realized):
                raise AssertionError(("partition witness", problem.name, realized, selected))
            multiple_target_cells += 1
    return multiple_target_cells


def run_scope(problem, full_problem, realized, baseline_seed, n_permutations):
    optimized = solve(problem, realized)
    brute = exact_by_partition(problem, realized)
    if optimized.status != brute.status or optimized.cost != brute.cost:
        raise AssertionError(("optimum mismatch", problem.name, realized, optimized, brute))
    if not verify_proof(problem, optimized, realized):
        raise AssertionError(("invalid certificate or witness", problem.name, realized, optimized))
    conflict_checks = 0
    if problem.completions:
        conflict_checks = check_subset_characterization(problem, realized)
    if optimized.status == CERTIFIED:
        for query in optimized.queries:
            retained = tuple(q for q in optimized.queries if query != q)
            opposing_pair = conflict(problem, retained, realized)
            if not verify_witness(problem, opposing_pair, retained, realized):
                raise AssertionError(("false minimality", problem.name, realized, query))

    full = exact_by_partition(full_problem, realized)
    if full.cost is not None and (optimized.cost is None or optimized.cost > full.cost):
        raise AssertionError(("target identification more costly than full", problem.name, realized))
    baselines = evaluate(problem, realized, random_seed=baseline_seed, permutations=n_permutations)
    for name, baseline in baselines.items():
        if baseline.certified != (optimized.status == CERTIFIED):
            raise AssertionError(("false certification or false abstention", name, problem.name, realized))
        if optimized.cost is not None and baseline.attempted_cost < optimized.cost:
            raise AssertionError(("baseline appears below independent optimum", name, problem.name, realized))
    row = {
        "scope": "uniform" if realized is None else "realized",
        "completion": realized or "",
        "domainsize": len(problem.completions),
        "query_count": len(problem.query_names),
        "status": optimized.status,
        "optimum": amount(optimized.cost),
        "selected_queries": "|".join(problem.query_names[q] for q in optimized.queries),
        "optimum_ties": len(brute.optima),
        "witness": "|".join(optimized.witness or ()),
        "full_contract_status": full.status,
        "full_contract_optimum": amount(full.cost),
        "partitions_checked": brute.subsets_checked,
        "cheaper_partitions_rejected": brute.cheaper_subsets_rejected if brute.cost is not None else "",
        "partitions_with_verified_conflict": conflict_checks,
        "distinguishing_pairs": optimized.pair_count,
        "distinct_edges": optimized.edge_count,
        "reduced_edges": optimized.reduced_edges,
        "optimizer_search_states": optimized.search_states,
    }
    row.update({name + "_attempted_cost": amount(metric.attempted_cost) for name, metric in baselines.items()})
    row.update({name + "_certified": int(metric.certified) for name, metric in baselines.items()})
    return row


def numeric_mean(values):
    return round(float(sum(values) / len(values)), 6) if values else None


def summarize(rows):
    feasible = [row for row in rows if row["status"] == CERTIFIED]
    unavailable = [row for row in rows if row["status"] == INACCESSIBLE]
    optima = [int(row["optimum"]) for row in feasible]
    baseline_summary = {}
    for comparator in COMPARATORS:
        costs = [Fraction(row[comparator + "_attempted_cost"]) for row in feasible]
        excess = [cost - ideal for cost, ideal in zip(costs, optima, strict=True)]
        attempted = [Fraction(row[comparator + "_attempted_cost"]) for row in unavailable]
        baseline_summary[comparator] = {
            "mean_finite_cost": numeric_mean(costs),
            "mean_absolute_gap": numeric_mean(excess),
            "above_optimum": sum(gap > 0 for gap in excess),
            "worst_gap": float(max(excess)) if excess else None,
            "mean_attempt_cost_when_inaccessible": numeric_mean(attempted),
            "certified": sum(row[comparator + "_certified"] for row in rows),
        }
    comparable_full = [row for row in feasible if row["full_contract_optimum"] != ""]
    return {
        "scopes": len(rows),
        "outcomes": dict(Counter(row["status"] for row in rows)),
        "mean_finite_optimum": numeric_mean([Fraction(cost) for cost in optima]),
        "feasible_with_multiple_optima": sum(row["optimum_ties"] > 1 for row in feasible),
        "same_scope_full_contract_finite": len(comparable_full),
        "target_strictly_cheaper_than_finite_full_contract": sum(
            int(row["optimum"]) < int(row["full_contract_optimum"]) for row in comparable_full
        ),
        "target_only_identifiable": sum(row["full_contract_optimum"] == "" for row in feasible),
        "mean_attempt_cost_inaccessible": {
            name: baseline_summary[name]["mean_attempt_cost_when_inaccessible"] for name in COMPARATORS
        },
        "baselines": baseline_summary,
    }


def details(rows):
    uniform = rows[0]
    local_costs = [int(row["optimum"]) for row in rows[1:] if row["optimum"] != ""]
    return {
        "uniform_status": uniform["status"],
        "uniform_cost": uniform["optimum"] or None,
        "uniform_optimal_count": uniform["optimum_ties"],
        "selected_queries": uniform["selected_queries"],
        "uniform_impossibility_witness": uniform["witness"] or None,
        "local_certified": len(local_costs),
        "local_cost_range": [min(local_costs), max(local_costs)] if local_costs else None,
        "local_unresolved": len(rows) - 1 - len(local_costs),
        "full_contract_cost": uniform["full_contract_optimum"] or None,
        "uniform_comparators": {name: uniform[name + "_attempted_cost"] for name in COMPARATORS},
    }


def generate(config, protocol_hash):
    if config["schema_version"] != 1:
        raise ValueError("unsupported protocol schema")
    comparator_config = config["comparators"]
    rows = []
    case_sets = defaultdict(list)
    control_results = {}
    for ordinal, (stratum, seed, problem) in enumerate(cases(config)):
        full_problem = replace(problem, completions=tuple(
            replace(row, target=row.identity) for row in problem.completions
        ))
        scopes = [None, *(row.identity for row in problem.completions)]
        measurements = []
        for scope_index, realized in enumerate(scopes):
            result = run_scope(
                problem, full_problem, realized,
                comparator_config["random_seed"] + ordinal * 32 + scope_index,
                comparator_config["random_permutations"],
            )
            measurements.append({"case": problem.name, "stratum": stratum, "seed": seed, **result})
        if stratum in ("control", "pc_authorization"):
            control_results[problem.name] = details(measurements)
        rows.extend(measurements)
        case_sets[stratum].extend(measurements)

    checks = {
        "scopes_with_verified_status_and_cost": len(rows),
        "certificate_sufficiency_and_minimality": sum(row["status"] == CERTIFIED for row in rows),
        "verified_complete_interface_impossibility_witnesses": sum(row["status"] == INACCESSIBLE for row in rows),
        "all_subsets_characterization_checks": sum(row["partitions_checked"] for row in rows),
        "verified_partition_conflicts": sum(row["partitions_with_verified_conflict"] for row in rows),
        "strict_uniform_worst_realized_gap": sum(
            int(row["optimum"]) > max(int(item["optimum"]) for item in group if item["scope"] == "realized")
            for group in group_cases(rows).values()
            for row in group
            if row["scope"] == "uniform" and row["status"] == CERTIFIED
        ),
    }
    summary = {
        "experiment": config["experiment"],
        "protocol_sha256": protocol_hash,
        "domains_by_stratum": {
            name: sum(row["scope"] == "uniform" for row in data) for name, data in case_sets.items()
        },
        "overall": {
            scope: summarize([row for row in rows if row["scope"] == scope])
            for scope in ("uniform", "realized")
        },
        "per_stratum": {
            name: {
                scope: summarize([row for row in data if row["scope"] == scope])
                for scope in ("uniform", "realized")
            }
            for name, data in case_sets.items()
        },
        "proof_checks": checks,
        "controls_and_structured": control_results,
    }
    return summary, rows


def group_cases(rows):
    by_case = defaultdict(list)
    for row in rows:
        by_case[row["case"]].append(row)
    return by_case


def render(summary, rows):
    csv_output = StringIO(newline="")
    writer = csv.DictWriter(csv_output, fieldnames=tuple(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return {
        "scopes.csv": csv_output.getvalue().encode("utf-8"),
        "summary.json": (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode("utf-8"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true", help="regenerate evidence files")
    mode.add_argument("--check", action="store_true", help="verify existing evidence files (default)")
    parser.add_argument("--output-dir", type=Path, default=BASE / "results")
    args = parser.parse_args()
    if not args.write and not args.output_dir.is_dir():
        parser.error("evidence directory is missing")
    started_at = perf_counter()
    protocol_bytes = (BASE / "configs" / "protocol.json").read_bytes()
    config = json.loads(protocol_bytes)
    summary, rows = generate(config, sha256(protocol_bytes).hexdigest())
    evidence = render(summary, rows)
    if args.write:
        args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in evidence.items():
        path = args.output_dir / name
        if args.write:
            path.write_bytes(payload)
        elif not path.is_file() or path.read_bytes() != payload:
            raise SystemExit(f"evidence mismatch: {name}")
        print(f"{sha256(payload).hexdigest()}  {name}")
    print(
        f"{sum(summary['domains_by_stratum'].values())} domains, {len(rows)} scopes, "
        f"{summary['proof_checks']['all_subsets_characterization_checks']} exact subset checks, "
        f"Python {platform.python_version()}, {perf_counter() - started_at:.3f}s"
    )


if __name__ == "__main__":
    main()
