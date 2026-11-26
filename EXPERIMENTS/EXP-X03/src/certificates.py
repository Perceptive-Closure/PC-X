"""Exact weighted certificates for finite deterministic semantic tables."""

from dataclasses import dataclass
from functools import cache
from itertools import combinations


CERTIFIED = "CERTIFIED"
INACCESSIBLE = "AUDIT_INACCESSIBLE"
INCONSISTENT = "INCONSISTENT"


@dataclass(frozen=True)
class Completion:
    identity: str
    answers: tuple[str, ...]
    target: str


@dataclass(frozen=True)
class Problem:
    name: str
    query_names: tuple[str, ...]
    costs: tuple[int, ...]
    completions: tuple[Completion, ...]

    def __post_init__(self):
        if len(self.query_names) != len(self.costs):
            raise ValueError("every query needs one acquisition cost")
        if not all(isinstance(name, str) and name for name in self.query_names):
            raise ValueError("query names must be nonempty strings")
        if len(set(self.query_names)) != len(self.query_names):
            raise ValueError("query names must be distinct")
        if not all(type(cost) is int and cost > 0 for cost in self.costs):
            raise ValueError("query costs must be positive integers")
        known = set()
        for row in self.completions:
            if not isinstance(row.identity, str) or not row.identity or row.identity in known:
                raise ValueError("completion identities must be distinct nonempty strings")
            if len(row.answers) != len(self.query_names):
                raise ValueError("each completion must answer each available query")
            if not isinstance(row.target, str) or not all(isinstance(a, str) for a in row.answers):
                raise ValueError("query answers and targets must be string tokens")
            known.add(row.identity)


@dataclass(frozen=True)
class Certificate:
    status: str
    cost: int | None = None
    queries: tuple[int, ...] = ()
    witness: tuple[str, str] | None = None
    pair_count: int = 0
    edge_count: int = 0
    reduced_edges: int = 0
    search_states: int = 0


def rows_for(problem: Problem, realized: str | None) -> tuple[Completion, ...]:
    if realized is None:
        return problem.completions
    for row in problem.completions:
        if row.identity == realized:
            return (row,)
    raise ValueError(f"unknown realized completion: {realized}")


def disagreement_edges(problem: Problem, realized: str | None = None):
    """Return one query mask per target-distinct pair, with pair provenance."""
    if realized is None:
        pairs = combinations(problem.completions, 2)
    else:
        actual = rows_for(problem, realized)[0]
        pairs = ((actual, other) for other in problem.completions)
    edges = []
    for left, right in pairs:
        if left.target == right.target:
            continue
        mask = sum(
            1 << q
            for q, (first, second) in enumerate(zip(left.answers, right.answers, strict=True))
            if first != second
        )
        edges.append((mask, (left.identity, right.identity)))
    return tuple(edges)


def _minimal_edges(masks: set[int]) -> tuple[int, ...]:
    minimal = []
    for mask in sorted(masks, key=lambda edge: (edge.bit_count(), edge)):
        if not any((subset & mask) == subset for subset in minimal):
            minimal.append(mask)
    return tuple(minimal)


def solve(problem: Problem, realized: str | None = None) -> Certificate:
    """Return one exact optimum or a witness against the declared interface."""
    pairs = disagreement_edges(problem, realized)
    if not problem.completions:
        return Certificate(INCONSISTENT)
    witnesses = dict(pairs)
    if 0 in witnesses:
        return Certificate(
            INACCESSIBLE, witness=witnesses[0], pair_count=len(pairs),
            edge_count=len(witnesses), reduced_edges=1,
        )
    edges = _minimal_edges(set(witnesses))

    @cache
    def search(remaining: tuple[int, ...]) -> tuple[int, tuple[int, ...]]:
        if not remaining:
            return 0, ()
        # Every feasible certificate includes at least one query in this edge.
        required = remaining[0]
        candidates = []
        for query, cost in enumerate(problem.costs):
            bit = 1 << query
            if required & bit:
                suffix_cost, suffix = search(tuple(edge for edge in remaining if not edge & bit))
                candidates.append((cost + suffix_cost, tuple(sorted((query, *suffix)))))
        return min(candidates)

    cost, queries = search(edges)
    stats = search.cache_info()
    search.cache_clear()
    return Certificate(
        CERTIFIED, cost, queries, pair_count=len(pairs), edge_count=len(witnesses),
        reduced_edges=len(edges), search_states=stats.misses,
    )
