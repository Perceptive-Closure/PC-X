"""Static acquisition costs and source-calibrated compatible completions."""

from fractions import Fraction
from functools import cache
from itertools import combinations, permutations, product

from common import DESIGN, MODES, PORTS, TIES
from model import mode_key
from sandbox import Workshop

COMPLETIONS = tuple(product(permutations(MODES), TIES))
CATALOG = {"nameplate": ("nameplate", None), "roster": ("roster", None)}
CATALOG.update({f"{kind}.{port}": (kind, idx)
                for kind in ("allocator", "view") for idx, port in enumerate(PORTS)})
QUERIES = tuple(sorted(CATALOG))


def query_cost(query):
    return DESIGN["query_costs"][CATALOG[query][0]]


def audit_read(completion, query):
    assignment, tie_order = completion
    kind, port = CATALOG[query]
    mode = MODES[0] if port is None else assignment[port]
    return Workshop(*mode, tie_order).probe(kind)


def expected_read(completion, query):
    assignment, tie_order = completion
    kind, port = CATALOG[query]
    if kind == "nameplate":
        return {"displayed_time_quanta_per_turn": 2}
    if kind == "roster":
        return {"first_on_tie": tie_order}
    allocator, view = assignment[port]
    if kind == "allocator":
        exclusive = int(allocator == "exclusive")
        return {"submitted_shared": 2, "granted_shared": 2 - exclusive,
                "granted_private": exclusive}
    return {"sentinel_demands": [2, 2], "displayed_in_isolation": [2, 2],
            "displayed_jointly": [2, 2] if view == "faithful" else [1, 1]}


def target(completion, table):
    mapping, _ = completion
    keys = ("event_containment", "local_bounds_carried_over",
            "global_threshold_met", "qualified_work")
    return tuple(tuple(table[mode_key(mode)]["judgments"][key] for key in keys)
                 for mode in mapping)


def posterior(reads):
    return [completion for completion in COMPLETIONS
            if all(expected_read(completion, query) == observed
                   for query, observed in reads.items())]


def study_costs(table):
    labels = {
        "composition": [target(candidate, table) for candidate in COMPLETIONS],
        "risk_threshold_only": [
            tuple(table[mode_key(mode)]["judgments"]["global_threshold_met"]
                  for mode in candidate[0]) for candidate in COMPLETIONS],
        "full_installation": list(COMPLETIONS),
    }
    signatures = [tuple(repr(expected_read(candidate, name)) for name in QUERIES)
                  for candidate in COMPLETIONS]
    options = list(range(1 << len(QUERIES)))
    subsets = {mask: tuple(query for idx, query in enumerate(QUERIES) if mask & 1 << idx)
               for mask in options}
    positions = {mask: [idx for idx in range(len(QUERIES)) if mask & 1 << idx]
                 for mask in options}
    costs = {mask: sum(query_cost(query) for query in subsets[mask]) for mask in options}

    results = {}
    for name, values in labels.items():
        target_pairs = [
            sum(1 << k for k, (left, right) in enumerate(zip(signatures[i], signatures[j], strict=True))
                if left != right)
            for i, j in combinations(range(len(values)), 2) if values[i] != values[j]
        ]
        pair_masks = set(target_pairs)
        sufficient = {mask for mask in options if all(mask & difference for difference in pair_masks)}
        # Independently construct answer partitions, rather than trusting
        # witness-pair coverage to compute query-set sufficiency.
        partition_sufficient = set()
        for mask in options:
            partition = {}
            for signature, value in zip(signatures, values, strict=True):
                answers = tuple(signature[pos] for pos in positions[mask])
                if answers in partition and partition[answers] != value:
                    break
                partition[answers] = value
            else:
                partition_sufficient.add(mask)
        if sufficient != partition_sufficient or not sufficient:
            raise ValueError(f"Disagreement checking identifying sets: {name}")
        best = min(sufficient, key=lambda mask: (costs[mask], subsets[mask]))

        def cheapest_first():
            selected = 0
            for pos in sorted(range(len(QUERIES)), key=lambda p: (query_cost(QUERIES[p]), QUERIES[p])):
                selected |= 1 << pos
                if selected in sufficient:
                    return selected
            raise ValueError("Cheapest-first did not close")

        greedy = 0
        while greedy not in sufficient:
            choices = [p for p in range(len(QUERIES)) if not greedy & 1 << p]
            pos = max(choices, key=lambda p: (
                Fraction(sum(bool(d & 1 << p) for d in target_pairs if not greedy & d),
                         query_cost(QUERIES[p])), -p))
            greedy |= 1 << pos

        @cache
        def random_cost(mask):
            if mask in sufficient:
                return Fraction(0)
            remaining = [p for p in range(len(QUERIES)) if not mask & 1 << p]
            return sum(query_cost(QUERIES[p]) + random_cost(mask | 1 << p)
                       for p in remaining) / len(remaining)

        results[name] = {
            "selected": list(subsets[best]), "minimum_cost": costs[best],
            "minimum_set_count": sum(costs[mask] == costs[best] for mask in sufficient),
            "subsets_checked": len(options), "target_distinct_pairs": len(target_pairs),
            "cheapest_first_cost": costs[cheapest_first()],
            "pair_greedy_cost": costs[greedy],
            "random_order_expected_cost": str(random_cost(0)),
            "all_queries_cost": max(costs.values())
        }
    return results


def verify_ports():
    checked = 0
    for candidate in COMPLETIONS:
        for query in QUERIES:
            if audit_read(candidate, query) != expected_read(candidate, query):
                raise ValueError("Sentinel/source disagreement")
            checked += 1
    return checked
