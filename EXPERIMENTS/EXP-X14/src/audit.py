"""Exact observation-only acquisition for the sealed installation."""

from collections import defaultdict
from fractions import Fraction
from functools import cache
from itertools import combinations, permutations
from random import Random

from common import HELD, PROFILES, canonical, fields
from engine import calibration

PORTS = tuple(HELD["ports"])
MODES = tuple(HELD["profiles"])
COMPLETIONS = tuple((assignment, signature) for assignment in permutations(MODES)
                    for signature in (False, True))
CATALOG = {f"{kind}-{port}": HELD["query_cost"][kind]
           for kind in ("layout", "viewer") for port in PORTS}
CATALOG.update({kind: HELD["query_cost"][kind] for kind in ("nameplate", "roster")})


def pack(candidate):
    assignment, signature = candidate
    return {"profiles": dict(zip(PORTS, assignment, strict=True)), "signature": signature}


def model_read(candidate, query):
    assignment, signature = candidate
    if query == "roster":
        return signature
    if query == "nameplate":
        return "two-slots"
    kind, port = query.split("-")
    profile = PROFILES[assignment[PORTS.index(port)]]
    return profile["entry" if kind == "layout" else "panel"]


def measured_read(candidate, query):
    assignment, signature = candidate
    kind, _, port = query.partition("-")
    return calibration(assignment[PORTS.index(port)] if port else assignment[0], signature, kind)


def outcome_key(answer):
    return canonical(answer).decode("ascii").strip()


def label(candidate, full):
    return candidate if full else candidate[0]


def partition(ids, query, reader=model_read):
    cells = defaultdict(list)
    for index in ids:
        cells[outcome_key(reader(COMPLETIONS[index], query))].append(index)
    return {key: tuple(values) for key, values in sorted(cells.items())}


def homogeneous(ids, full=False):
    return len({label(COMPLETIONS[index], full) for index in ids}) == 1


def optimum(catalog):
    queries = tuple(sorted(catalog))
    initial = tuple(range(len(COMPLETIONS)))

    @cache
    def solve(ids):
        if homogeneous(ids):
            return 0, None
        best_cost, best_query = None, None
        for query in queries:
            children = partition(ids, query)
            if len(children) <= 1:
                continue
            costs = [solve(child)[0] for child in children.values()]
            if None not in costs:
                cost = catalog[query] + max(costs)
                if best_cost is None or cost < best_cost:
                    best_cost, best_query = cost, query
        return best_cost, best_query

    def tree(ids):
        cost, query = solve(ids)
        if cost == 0:
            return {"resolved": True}
        return {"query": query, "branches": {
            answer: tree(child) for answer, child in partition(ids, query).items()
        }}

    minimum, _ = solve(initial)
    return minimum, tree(initial) if minimum is not None else None


def verify_exact(cost, policy):
    """Check support and the strict cheaper budget using measured partitions."""
    start = tuple(range(len(COMPLETIONS)))

    @cache
    def find(ids, cap):
        if homogeneous(ids):
            return True
        for query, amount in CATALOG.items():
            if amount > cap:
                continue
            observation_cells = partition(ids, query, measured_read)
            if len(observation_cells) > 1 and all(
                find(branch, cap - amount) for branch in observation_cells.values()
            ):
                return True
        return False

    def check(ids, tree):
        if tree == {"resolved": True}:
            if not homogeneous(ids):
                raise ValueError("External audit resolves heterogeneous predictions")
            return 0
        fields(tree, ("query", "branches"))
        query = tree["query"]
        splits = partition(ids, query, measured_read)
        fields(tree["branches"], splits)
        if len(splits) == 1:
            raise ValueError("External minimum audit uses a constant query")
        return CATALOG[query] + max(check(child, tree["branches"][value])
                                   for value, child in splits.items())

    if check(start, policy) != cost or find(start, cost - 1) or not find(start, cost):
        raise ValueError("External acquisition failed the independent exact budget check")


def receipt_reads(candidate, policy):
    reads = []
    while policy != {"resolved": True}:
        query = policy["query"]
        value = measured_read(candidate, query)
        reads.append({"query": query, "value": value})
        policy = policy["branches"][outcome_key(value)]
    return reads


def posterior(reads, policy):
    support = tuple(range(len(COMPLETIONS)))
    for event in reads:
        fields(event, ("query", "value"))
        query = event["query"]
        if policy.get("query") != query:
            raise ValueError("The receipt departed from the registered audit")
        key = outcome_key(event["value"])
        support = partition(support, query).get(key, ())
        if not support or key not in policy["branches"]:
            raise ValueError("Impossible audit observation")
        policy = policy["branches"][key]
    if policy != {"resolved": True} or not homogeneous(support):
        raise ValueError("The receipt cannot establish the frozen target")
    return tuple(COMPLETIONS[index] for index in support)


def static_minimum(full):
    pairs = [(a, b) for a, b in combinations(range(len(COMPLETIONS)), 2)
             if label(COMPLETIONS[a], full) != label(COMPLETIONS[b], full)]
    queries = tuple(sorted(CATALOG))
    remaining = (1 << len(pairs)) - 1
    cover = {}
    for query in queries:
        answers = [measured_read(candidate, query) for candidate in COMPLETIONS]
        mask = 0
        for bit, (a, b) in enumerate(pairs):
            if answers[a] != answers[b]:
                mask |= 1 << bit
        cover[query] = mask
    best = (sum(CATALOG.values()) + 1, ())
    for size in range(len(queries) + 1):
        for subset in combinations(queries, size):
            cost = sum(CATALOG[query] for query in subset)
            if (cost, subset) >= best:
                continue
            uncovered = remaining
            for query in subset:
                uncovered &= ~cover[query]
            if not uncovered:
                best = (cost, subset)
    if not best[1]:
        raise ValueError("Static baseline could not distinguish its declared target")
    return {"cost": best[0], "queries": list(best[1]), "distinct_pairs": len(pairs),
            "subsets_considered": 2 ** len(queries)}


def inaccessible_witness(queries):
    observed = {}
    for candidate in COMPLETIONS:
        signature = tuple(measured_read(candidate, query) for query in queries)
        prior = observed.setdefault(signature, candidate)
        if prior[0] != candidate[0]:
            return {
                "status": "unattainable", "assignments": [pack(prior), pack(candidate)],
                "shared_readbacks": dict(zip(queries, signature, strict=True)),
            }
    raise ValueError("Removed interface unexpectedly identifies the target")


def summarize_costs(costs):
    return {"worst": max(costs), "minimum": min(costs), "total": sum(costs), "support": len(costs)}


def compare_baselines():
    start = tuple(range(len(COMPLETIONS)))

    def costs_in_order(order):
        costs = []
        for index in start:
            ids = start
            spent = 0
            for query in order:
                if homogeneous(ids):
                    break
                observed = outcome_key(model_read(COMPLETIONS[index], query))
                ids = partition(ids, query)[observed]
                spent += CATALOG[query]
            if not homogeneous(ids):
                raise ValueError("Ordered baseline failed to resolve full query support")
            costs.append(spent)
        return summarize_costs(costs)

    @cache
    def greedy(ids):
        if homogeneous(ids):
            return [0 for _ in ids]
        scores = {}
        outputs = {}
        for query, cost in CATALOG.items():
            children = partition(ids, query)
            if len(children) == 1:
                continue
            counts = {index: obs for obs, child in children.items() for index in child}
            removed = sum(COMPLETIONS[a][0] != COMPLETIONS[b][0] and counts[a] != counts[b]
                          for a, b in combinations(ids, 2))
            scores[query] = Fraction(removed, cost)
            outputs[query] = children
        choice = min(scores, key=lambda name: (-scores[name], name))
        return [CATALOG[choice] + cost for child in outputs[choice].values() for cost in greedy(child)]

    order = sorted(CATALOG, key=lambda query: (CATALOG[query], query))
    random_runs = {}
    for seed in HELD["random_baselines_seeds"]:
        randomized = sorted(CATALOG)
        Random(seed).shuffle(randomized)
        random_runs[str(seed)] = costs_in_order(randomized)
    return {
        "exhaustive": sum(CATALOG.values()),
        "cheapest_first": costs_in_order(order),
        "random_order": random_runs,
        "greedy_distinguished_target_pairs_per_cost": summarize_costs(greedy(start)),
        "static_target": static_minimum(full=False),
        "static_full_identity": static_minimum(full=True),
    }
