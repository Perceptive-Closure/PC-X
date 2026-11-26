"""Weighted pair coverage, deletion, exhaustive and random acquisition."""

from dataclasses import dataclass
from fractions import Fraction
from random import Random

from .certificates import disagreement_edges
from .reference import conflict


@dataclass(frozen=True)
class Baseline:
    certified: bool
    attempted_cost: Fraction


def cost_of(problem, queries):
    return sum(problem.costs[q] for q in queries)


def greedy_cover(problem, realized):
    remaining = [mask for mask, _ in disagreement_edges(problem, realized)]
    available = set(range(len(problem.costs)))
    selected = []
    while remaining and available:
        marginal = {q: sum(bool(mask & (1 << q)) for mask in remaining) for q in available}
        query = min(
            available,
            key=lambda q: (-Fraction(marginal[q], problem.costs[q]), problem.costs[q], q),
        )
        if marginal[query] == 0:
            # No separation remains possible. Charge a use-all audit attempt
            # for the infeasible-scope comparison; do not report an optimum.
            return tuple(range(len(problem.costs)))
        selected.append(query)
        available.remove(query)
        remaining = [mask for mask in remaining if not mask & (1 << query)]
    return tuple(sorted(selected))


def deletion(problem, realized):
    selected = list(range(len(problem.costs)))
    for query in range(len(problem.costs)):
        trial = tuple(q for q in selected if q != query)
        if conflict(problem, trial, realized) is None:
            selected = list(trial)
    return tuple(selected)


def evaluate(problem, realized, *, random_seed, permutations):
    if not problem.completions:
        absent = Baseline(False, Fraction(0))
        return {name: absent for name in ("greedy", "deletion", "exhaustive", "random")}
    all_queries = tuple(range(len(problem.costs)))
    feasible = conflict(problem, all_queries, realized) is None
    comparisons = {"exhaustive": Baseline(feasible, Fraction(cost_of(problem, all_queries)))}
    for name, selection in (("greedy", greedy_cover), ("deletion", deletion)):
        queries = selection(problem, realized)
        comparisons[name] = Baseline(
            conflict(problem, queries, realized) is None, Fraction(cost_of(problem, queries))
        )
    rng = Random(random_seed)
    total = 0
    for _ in range(permutations):
        order = list(all_queries)
        rng.shuffle(order)
        acquired = []
        for query in order:
            if conflict(problem, tuple(acquired), realized) is None:
                break
            acquired.append(query)
        total += cost_of(problem, acquired)
    comparisons["random"] = Baseline(feasible, Fraction(total, permutations))
    return comparisons
