"""Audit X05's source-mode costs, certificate lower bounds, and matched workload."""

from collections import Counter
from itertools import combinations
from math import inf, prod
from statistics import median

from verify_exact import MASKS, FREEZES, admitted, csv_rows, ensure, export, hit_cost, partition, read

EXPORT = """
import json
from dataclasses import asdict
from pathlib import Path
from domain import workload
protocol = json.loads(Path('protocol.json').read_bytes())
print(json.dumps([asdict(case) for case in workload(protocol)]))
"""


def graph_costs(graph, flags):
    nodes = graph["nodes"]
    classes = ({0, 1, 2, 3}, {1, 4})
    coordinates = []
    closed = []
    for node in nodes:
        e, r, a = (fact is not None and flags[fact] for fact in node["effects"])
        history = 1 if e else node["history"]
        labels = (0, 0, 1, 2, 3) if r else node["labels"]
        authority = set(node["authority"]) | ({"reserve"} if a else set())
        coordinates.append((history, partition(labels), authority))
        cell = next(set(cell) for cell in coordinates[-1][1] if history in cell)
        fiber = sum(bool(cell & compatible) for compatible in classes)
        ensure(fiber > 0 and (graph["join"] is None or fiber > 1), "X05 semantic boundary")
        closed.append(fiber == 1)

    signatures = []
    for freeze in MASKS:
        values = {}
        for index in range(len(nodes) - 1, -1, -1):
            options = []
            for action in nodes[index]["actions"]:
                if action["interface"] not in coordinates[index][2]:
                    continue
                support = [branch["successor"] for branch in action["support"]]
                touched = {
                    letter for successor in support
                    for letter, before, after in zip("ERA", coordinates[index], coordinates[successor], strict=True)
                    if before != after
                }
                if touched.isdisjoint(freeze):
                    options.append(action["price"] + max(values[successor] for successor in support))
            terminal = closed[index] or index == graph["join"]
            values[index] = 0 if terminal else min(options, default=inf)
        signatures.append(values[0])
    return signatures


def combine(groups, start=0):
    attainable = {start}
    for group in groups:
        attainable = {x + y for x in attainable for y in group}
    return attainable


def split_edges(local, totals, terminal, budget):
    all_edges = set()
    start = 0
    for i, stage in enumerate(local):
        outside = combine(totals[:i] + totals[i + 1:], terminal)
        for first, second in combinations(stage.values(), 2):
            low, high = sorted((first[0], second[0]))
            if not any(low + total <= budget < high + total for total in outside):
                continue
            edge = frozenset(start + index for index, (a, b) in enumerate(zip(first[1], second[1], strict=True))
                             if a != b)
            all_edges.add(edge)
        start += len(next(iter(stage.values()))[1])
    return all_edges


def recompute_case(case, evidence, largest_stage_minima):
    freeze = FREEZES.index(case["freeze"])
    terminal = graph_costs(case["terminal"], [])[freeze]
    local = []
    signatures = 8
    for stage in case["stages"]:
        observations = [node["observation"] for node in stage["graph"]["nodes"]]
        if len(observations) != len(set(observations)):
            ensure(evidence["methods"]["lazy"]["status"] == "UNRESOLVED", (case["name"], "observation alias"))
            return {"unsupported_observation_alias": 1}
        values = {}
        for mode in range(2 ** stage["width"]):
            bits = [(mode >> index) & 1 for index in range(stage["width"])]
            if admitted(bits, stage["clauses"]):
                signature = graph_costs(stage["graph"], bits)
                answers = tuple((mode & q["facts"]).bit_count() % 2 for q in stage["queries"])
                values[mode] = (signature[freeze], answers)
                signatures += 8
        local.append(values)
    total_count = prod(map(len, local))
    ref = evidence["reference"]
    ensure(ref["compatible_count"] == total_count, (case["name"], "X05 source-compatible count"))
    if total_count == 0:
        return {"empty_evidence_domain": 1, "local_freeze_coordinates": signatures}
    costs = [{row[0] for row in domain.values()} for domain in local]
    all_values = combine(costs, terminal)
    finite_values = sorted(all_values - {inf})
    ensure(finite_values == ref["attainable_finite_costs"] and (inf in all_values) == ref["attainable_infinity"],
           (case["name"], "X05 exact finite costs"))
    target = {amount <= case["budget"] for amount in all_values}
    ensure(sorted(target) == ref["target_values"], (case["name"], "X05 exact target set"))
    finite = [entries - {inf} for entries in costs]
    edges = split_edges(local, finite, terminal, case["budget"])
    prices = evidence["query_prices"]
    optimum = hit_cost(edges, prices)
    ensure(optimum == ref["minimum_audit_cost"], (case["name"], "X05 complete pivotal stage cost", optimum))
    identity_edges = set()
    start = 0
    for domain in local:
        for first, second in combinations(domain.values(), 2):
            identity_edges.add(frozenset(start + i for i, (a, b) in enumerate(zip(first[1], second[1], strict=True))
                                         if a != b))
        start += len(next(iter(domain.values()))[1])
    full_identity = hit_cost(identity_edges, prices)
    samples = Counter(local_freeze_coordinates=signatures)
    if case["name"] == "large-matched-w3-n64-free":
        samples["largest_target_minimum"] = optimum
        samples["largest_full_identity_minimum"] = full_identity
        first = 0
        for index, stage in enumerate(case["stages"]):
            last = first + len(stage["queries"])
            position = set(range(first, last))
            largest_stage_minima.append({
                "stage": index,
                "target": hit_cost([edge for edge in edges if edge <= position], prices),
                "full_identity": hit_cost([edge for edge in identity_edges if edge <= position], prices),
            })
            first = last
        ensure(sum(stage["target"] for stage in largest_stage_minima) == optimum
               and sum(stage["full_identity"] for stage in largest_stage_minima) == full_identity,
               "X05 largest scope weighted stage optima")
    for method in ("direct-partition", "eager-disagreement"):
        reference = evidence["methods"][method]
        if reference["status"] != "AUDIT_INACCESSIBLE":
            continue
        pairs = [[domain[mode] for domain, mode in zip(local, modes, strict=True)]
                 for modes in reference["witness"]]
        lower, higher = [terminal + sum(row[0] for row in values) for values in pairs]
        ensure((lower <= case["budget"]) != (higher <= case["budget"])
               and all(a[1] == b[1] for a, b in zip(*pairs, strict=True)),
               (case["name"], method, "X05 explicit interface collision"))
        samples["explicit_interface_collisions"] += 1
    for method in ("lazy", "dominance-off"):
        record = evidence["methods"][method]
        for round_ in record.get("rounds", []):
            witness = round_["witness"]
            if witness is None:
                ensure(all(set(round_["selected"]).intersection(edge) for edge in edges),
                       (case["name"], method, "X05 invalid no-disagreement claim"))
                samples["rounds_without_disagreement"] += 1
                continue
            pairs = [[domain[mode] for domain, mode in zip(local, witness[key], strict=True)]
                     for key in ("left", "right")]
            derived = [terminal + sum(row[0] for row in values) for values in pairs]
            ensure([None if x == inf else x for x in derived] == witness["costs"],
                   (case["name"], method, "X05 witness cost against original source"))
            differences = [i for i, (a, b) in enumerate(zip(
                [answer for pair in pairs[0] for answer in pair[1]],
                [answer for pair in pairs[1] for answer in pair[1]], strict=True,
            )) if a != b]
            ensure(differences == witness["edge"] and frozenset(differences) in edges,
                   (case["name"], method, "X05 independently reconstructed witness edge"))
            samples["round_witness_costs_and_edges"] += 1
    return samples


def time_comparisons(rows, records):
    grouped = {}
    for row in rows:
        if row["measurement"] == "time":
            grouped.setdefault((row["case"], row["method"]), []).append(int(row["wall_ns"]))
    comparators = {}
    affirmative = {"CERTIFIED", "IDENTIFIED"}
    for name in ("direct-partition", "eager-disagreement", "dominance-off"):
        ratios = []
        for case, record in records.items():
            methods = record["methods"]
            if methods["lazy"]["status"] in affirmative and methods[name]["status"] in affirmative:
                ratios.append(median(grouped[(case, "lazy")]) / median(grouped[(case, name)]))
        comparators[name] = {
            "jointly_affirmative": len(ratios), "lazy_slower": sum(r > 1 for r in ratios),
            "maximum_lazy_slowdown": max(ratios),
        }
    return comparators


def verify_matched_grid(package, output):
    cases = {case["name"]: case for case in export(package, EXPORT, output / "x05-inputs.json")}
    records = {row["case"]: row for row in read(package / "results/invariants.json")}
    total = Counter()
    largest_stage_minima = []
    for name, row in records.items():
        total.update(recompute_case(cases[name], row, largest_stage_minima))
    old = [case for case in cases.values() if case["stratum"] == "large"]
    matched = {case["seed"]: case for case in cases.values() if case["stratum"] == "large-matched"}
    matched_duplicates = []
    for original in old:
        counterpart = matched[original["seed"]]
        ensure(original["stages"] == counterpart["stages"] and original["terminal"] == counterpart["terminal"],
               (original["name"], "X05 matched source graph or query inventory"))
        ensure(counterpart["freeze"] == "R" and counterpart["threshold"] == "middle",
               (counterpart["name"], "X05 matched freeze/cutoff rule"))
        if original["freeze"] == counterpart["freeze"] and original["budget"] == counterpart["budget"]:
            a, b = records[original["name"]], records[counterpart["name"]]
            ensure(a["reference"] == b["reference"] and a["methods"]["lazy"]["cost"] == b["methods"]["lazy"]["cost"],
                   (original["name"], "X05 repeated-scopes comparison"))
            matched_duplicates.append([original["name"], counterpart["name"]])
    probes = [case for case in cases.values() if case["stratum"] == "probes"]
    for probe in probes:
        ensure(probe["stages"] == matched[probe["seed"]]["stages"]
               and probe["terminal"] == matched[probe["seed"]]["terminal"], (probe["name"], "X05 probe source"))
    resources = csv_rows(package / "results/measurements.csv")
    return {
        "source_cases": len(cases), "third_oracle": dict(total),
        "same_source_seed_pairs": len(matched), "reused_source_target_scopes": matched_duplicates,
        "probe_count": len(probes), "archived_timing_comparisons": time_comparisons(resources, records),
        "largest_matched_stage_minima": largest_stage_minima,
        "resource_rows": dict(Counter(row["measurement"] for row in resources)),
    }
