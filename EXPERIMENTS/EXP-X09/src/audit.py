"""Observation-only audits over compatible model sets."""

from collections import defaultdict
from fractions import Fraction
from functools import cache
from itertools import combinations
from math import inf
from typing import NamedTuple

from contract import ADMITTED, SPEC
from model import right_probability, target


class Query(NamedTuple):
    name: str
    cue: str
    context: str
    cost: int


QUERIES = tuple(Query(**query) for query in SPEC["queries"])
ALL = tuple(range(len(QUERIES)))
BLUE = tuple(query for query in ALL if QUERIES[query].cue == SPEC["comparison_cue"])
CANDIDATES = tuple(range(len(ADMITTED)))
TARGETS = tuple(target(fixture) for fixture in ADMITTED)
CHANCES = tuple(
    tuple(right_probability(fixture, query.cue, query.context) for query in QUERIES)
    for fixture in ADMITTED
)
N = SPEC["audit"]["episodes"]
RADIUS = Fraction(SPEC["audit"]["radius"])
METHODS = ("primary", "fixed_blue", "exhaustive", "random", "greedy")
CERTIFIED, ABSTAIN, INCONSISTENT = "CERTIFIED", "ABSTAIN", "INCONSISTENT"


def names(candidates):
    return [ADMITTED[i].name for i in candidates]


def decision(candidates):
    labels = {TARGETS[i] for i in candidates}
    if not labels:
        return INCONSISTENT, None
    if len(labels) == 1:
        return CERTIFIED, next(iter(labels))
    return ABSTAIN, None


def groups(candidates, query):
    answers = defaultdict(list)
    for i in candidates:
        answers[CHANCES[i][query]].append(i)
    return tuple(tuple(group) for group in answers.values())


def exclude(remaining, query):
    return tuple(i for i in remaining if i != query)


@cache
def minimax(candidates, remaining):
    if decision(candidates)[0] != ABSTAIN:
        return 0, None
    possible = []
    for query in remaining:
        partition = groups(candidates, query)
        if len(partition) > 1:
            rest = exclude(remaining, query)
            cost = QUERIES[query].cost + max(minimax(group, rest)[0] for group in partition)
            if cost < inf:
                possible.append((cost, query))
    return min(possible, default=(inf, None))


def edge_mass(candidates):
    return sum(TARGETS[i] != TARGETS[j] for i, j in combinations(candidates, 2))


def greedy_score(candidates, query):
    remaining_edges = sum(len(group) * edge_mass(group) for group in groups(candidates, query))
    return (edge_mass(candidates) - Fraction(remaining_edges, len(candidates))) / QUERIES[query].cost


def query_choices(method, candidates, remaining):
    if not remaining:
        return ()
    if method in ("fixed_blue", "exhaustive"):
        return remaining[:1]
    if decision(candidates)[0] != ABSTAIN:
        return ()
    if method == "primary":
        _, query = minimax(candidates, remaining)
        return () if query is None else (query,)
    if method == "greedy":
        chosen = max(remaining, key=lambda query: (greedy_score(candidates, query), -query))
        return (chosen,)
    if method == "random":
        return remaining
    raise ValueError(f"Unknown audit method {method!r}")


def starting_queries(method):
    if method not in METHODS:
        raise ValueError(f"Unknown audit method {method!r}")
    return BLUE if method == "fixed_blue" else ALL


def retained(candidates, query, right_count):
    if type(right_count) is not int or not 0 <= right_count <= N:
        raise ValueError("Invalid audit count")
    observed = Fraction(right_count, N)
    return tuple(i for i in candidates if abs(CHANCES[i][query] - observed) <= RADIUS)


def run(method, observe, chooser=None):
    candidates = CANDIDATES
    remaining = starting_queries(method)
    path = []
    while choices := query_choices(method, candidates, remaining):
        query = choices[0] if len(choices) == 1 else chooser.choice(choices)
        specification = QUERIES[query]
        trays = observe(specification)
        if not isinstance(trays, str) or len(trays) != N or set(trays) - {"0", "1"}:
            raise ValueError(f"Invalid reset batch for {specification.name}")
        right_count = trays.count("1")
        candidates = retained(candidates, query, right_count)
        path.append({
            "query": specification.name,
            "right": right_count,
            "episodes": N,
            "cost": N * specification.cost,
            "compatible": names(candidates),
        })
        remaining = exclude(remaining, query)
    status, verdict = decision(candidates)
    return {
        "status": status,
        "verdict": verdict,
        "compatible": names(candidates),
        "episodes": N * len(path),
        "cost": sum(step["cost"] for step in path),
        "path": path,
    }


def verify_selected(records):
    """Re-derive every selected action from its publicly observed predecessors."""
    if not isinstance(records, list):
        raise ValueError("Expected an ordered audit record")
    ordered = iter(records)

    def next_record(query):
        entry = next(ordered, None)
        if (
            not isinstance(entry, dict)
            or set(entry) != {"query", "trays"}
            or entry["query"] != query.name
        ):
            raise ValueError(f"Missing or unauthorized selected action: {query.name}")
        return entry["trays"]

    report = run("primary", next_record)
    if next(ordered, None) is not None:
        raise ValueError("Extra observations after stopping")
    if len(report["path"]) != len(records):
        raise ValueError("Malformed extra observation")
    return report


def model_members(report):
    retained_names = set(report["compatible"])
    return tuple(fixture for fixture in ADMITTED if fixture.name in retained_names)
