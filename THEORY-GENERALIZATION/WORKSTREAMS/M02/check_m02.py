"""Deterministic finite controls for the M02 statements."""

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from functools import cache
from itertools import product
from math import inf, prod


BITS = (0, 1)
BAGS = (("a", "t"), ("a", "b", "t"), ("b", "c", "t"))
FULL_SCOPE = ("a", "b", "c", "t")


@dataclass(frozen=True)
class Factor:
    scope: tuple[str, ...]
    allowed: frozenset[tuple[int, ...]]


@dataclass(frozen=True)
class Query:
    name: str
    column: str | None
    price: int
    next_state: tuple[str, ...]


def project(row, scope, selected):
    return tuple(row[scope.index(key)] for key in selected)


def every_row(scope):
    return set(product(BITS, repeat=len(scope)))


def reply(query, row, bag):
    if query.column is None:
        return 0
    return row[bag.index(query.column)]


def explicit_graph():
    return {
        "entry": (0, (
            Query("route", "a", 1, ("low", "high")),
            Query("advance", None, 0, ("last",)),
        )),
        "low": (1, (
            Query("local", "b", 1, ("read-c", "read-c")),
            Query("advance", None, 0, ("last",)),
        )),
        "high": (1, (
            Query("local", "b", (1 << 45) + 3, ("read-c", "read-c")),
            Query("advance", None, 0, ("last",)),
        )),
        "last": (2, (
            Query("b", "b", 9, ("read-c", "read-c")),
            Query("c", "c", 2, ("read-b", "read-b")),
        )),
        "read-c": (2, (Query("c", "c", 1, ("end", "end")),)),
        "read-b": (2, (Query("b", "b", 5, ("end", "end")),)),
        "end": (2, ()),
    }


def factor_model(first, second):
    target = Factor(("b", "c", "t"), frozenset((b, c, b ^ c) for b, c in product(BITS, repeat=2)))
    return ((), (Factor(("a", "b"), first),), (Factor(("b", "c"), second), target))


def exact_tables(factors):
    local = [
        frozenset(
            row for row in every_row(bag)
            if all(project(row, bag, factor.scope) in factor.allowed for factor in group)
        )
        for bag, group in zip(BAGS, factors)
    ]

    def agree(i, row, other):
        keys = tuple(key for key in BAGS[i] if key in BAGS[i + 1])
        return project(row, BAGS[i], keys) == project(other, BAGS[i + 1], keys)

    suffix = [set() for _ in BAGS]
    suffix[-1] = every_row(BAGS[-1])
    for i in reversed(range(len(BAGS) - 1)):
        suffix[i] = {
            row for row in every_row(BAGS[i])
            if any(agree(i, row, candidate) for candidate in local[i + 1] & suffix[i + 1])
        }

    def advance(i, j, rows):
        for stage in range(i, j):
            rows = frozenset(
                candidate for candidate in local[stage + 1]
                if any(agree(stage, row, candidate) for row in rows)
            )
        return rows

    return local, suffix, advance


def factor_solver(factors, graph, kept=None):
    local, suffix, advance = exact_tables(factors)
    if not local[0] & suffix[0]:
        return None

    @cache
    def evaluate(public, prefix_rows):
        i, queries = graph[public]
        current = prefix_rows & suffix[i]
        assert current
        if len({row[BAGS[i].index("t")] for row in current}) == 1:
            return 0
        scores = []
        for query in queries:
            if kept is not None and (public, query.name) not in kept:
                continue
            replies = {reply(query, row, BAGS[i]) for row in current}
            continuations = []
            for heard in replies:
                next_state = query.next_state[heard]
                j, _ = graph[next_state]
                subset = frozenset(row for row in prefix_rows if reply(query, row, BAGS[i]) == heard)
                continuations.append(evaluate(next_state, advance(i, j, subset)))
            scores.append(query.price + max(continuations))
        return min(scores, default=inf)

    return evaluate("entry", local[0])


def complete_rows(factors):
    return tuple(
        row for row in product(BITS, repeat=len(FULL_SCOPE))
        if all(tuple(row[FULL_SCOPE.index(key)] for key in factor.scope) in factor.allowed
               for stage in factors for factor in stage)
    )


def direct_audit(graph, rows, kept=None):
    """Trace-recursive reference using original complete assignments exclusively."""
    if not rows:
        return None

    def evaluate(state, models):
        if len({row[-1] for row in models}) == 1:
            return 0
        minimum = inf
        for query in graph[state][1]:
            if kept is not None and (state, query.name) not in kept:
                continue
            branches = defaultdict(list)
            for row in models:
                index = FULL_SCOPE.index(query.column) if query.column else None
                branches[0 if index is None else row[index]].append(row)
            maximum = max(evaluate(query.next_state[answer], cases) for answer, cases in branches.items())
            minimum = min(minimum, query.price + maximum)
        return minimum

    return evaluate("entry", rows)


def graph_checks():
    graph = explicit_graph()
    binary_pairs = tuple(product(BITS, repeat=2))
    possible = [
        frozenset(pair for pair, keep in zip(binary_pairs, bits) if keep)
        for bits in product(BITS, repeat=4)
    ]
    for first, second in product(possible, repeat=2):
        factors = factor_model(first, second)
        assert factor_solver(factors, graph) == direct_audit(graph, complete_rows(factors))

    factors = factor_model(frozenset(binary_pairs) - {(1, 1)}, frozenset(binary_pairs))
    rows = complete_rows(factors)
    occurrences = tuple((state, query.name) for state, (_, queries) in graph.items() for query in queries)
    masks = []
    optimum = {}
    budget = 3
    for bits in product(BITS, repeat=len(occurrences)):
        keep = frozenset(occurrence for bit, occurrence in zip(bits, occurrences) if bit)
        value = factor_solver(factors, graph, keep)
        assert value == direct_audit(graph, rows, keep)
        optimum[keep] = value
        masks.append(keep)
    minimal = [
        keep for keep in masks if optimum[keep] <= budget
        and all(optimum[keep - {occurrence}] > budget for occurrence in keep)
    ]
    for keep in masks:
        assert (optimum[keep] > budget) == all(not support <= keep for support in minimal)
    assert minimal
    return len(possible) ** 2, len(masks)


def routing_reference(n):
    models = tuple(product(range(1, n + 1), range(n + 1)))
    commands = [("route", 0)] + [(kind, i) for kind in ("archive", "inspection") for i in range(1, n + 1)]
    costs = {q: 4 if q[0] == "route" else 2 + q[1] if q[0] == "archive" else 2 for q in commands}

    def target(model):
        route, blocked = model
        return int(route != blocked)

    def read(q, model):
        route, blocked = model
        return route if q[0] == "route" else int(q[1] == blocked)

    def legal(q, active_site):
        return q[0] != "inspection" or active_site == q[1]

    fixed_costs = []
    for bits in product(BITS, repeat=len(commands)):
        wanted = [q for q, bit in zip(commands, bits) if bit]
        route_requested = ("route", 0) in wanted
        reachable_sites = {m[0] if route_requested else None for m in models}
        if any(not legal(q, site) for q in wanted for site in reachable_sites):
            continue
        by_answer = defaultdict(set)
        for model in models:
            by_answer[tuple(read(q, model) for q in wanted)].add(target(model))
        if all(len(cell) == 1 for cell in by_answer.values()):
            fixed_costs.append(sum(costs[q] for q in wanted))

    @cache
    def adaptive(cases, active_site, seen):
        if len({target(row) for row in cases}) == 1:
            return 0
        scores = []
        for q in commands:
            if q in seen or not legal(q, active_site):
                continue
            by_answer = defaultdict(list)
            for case in cases:
                by_answer[read(q, case)].append(case)
            continuations = [
                adaptive(tuple(group), answer if q[0] == "route" else active_site, seen | {q})
                for answer, group in by_answer.items()
            ]
            scores.append(costs[q] + max(continuations))
        return min(scores, default=inf)

    assert min(fixed_costs) == 4 + sum(2 + i for i in range(1, n + 1))
    assert adaptive(models, None, frozenset()) == 6


def noisy_controls():
    transcripts_checked = 0
    for d, eta in product(range(1, 5), (Fraction(1, 5), Fraction(1, 3))):
        exact_joint = defaultdict(dict)
        for theta in product(BITS, repeat=d):
            def branch(history, probability):
                if len(history) == 5 or (len(history) >= 2 and not history[0][1] and history[-1][1]):
                    exact_joint[history][theta] = probability
                    return
                index = (len(history) + sum(bit for _, bit in history)) % d
                for answer in BITS:
                    likelihood = 1 - eta if answer == theta[index] else eta
                    branch(history + ((index, answer),), probability * likelihood)
            branch((), Fraction(1, 2 ** d))

        assert sum(sum(distribution.values()) for distribution in exact_joint.values()) == 1
        for history, joint in exact_joint.items():
            total = sum(joint.values())
            posterior = {theta: p / total for theta, p in joint.items()}
            marginals = [
                sum(p for theta, p in posterior.items() if theta[i])
                for i in range(d)
            ]
            for theta, p in posterior.items():
                assert p == prod(q if bit else 1 - q for bit, q in zip(theta, marginals))
            marginal_errors = [min(p, 1 - p) for p in marginals]
            assert max(posterior.values()) == prod(1 - e for e in marginal_errors)
            count = [sum(q == i for q, _ in history) for i in range(d)]
            for error, n in zip(marginal_errors, count):
                odds = ((1 - eta) / eta) ** n
                assert error >= 1 / (1 + odds) >= Fraction(1, 2) / odds
            transcripts_checked += 1
    return transcripts_checked


def qbf_reference(gate, quantifiers):
    layer = list(gate)
    for universal in reversed(quantifiers):
        fold = all if universal else any
        layer = [fold(layer[i:i + 2]) for i in range(0, len(layer), 2)]
    return layer[0]


def gated_acquisition(gate, quantifiers, fallback):
    completions = tuple(product(BITS, repeat=sum(quantifiers) + 1))

    def search(public, rows, used_universal):
        if len({row[-1] for row in rows}) == 1:
            return 0
        if len(public) == len(quantifiers):
            gate_index = sum(bit << (len(public) - i - 1) for i, bit in enumerate(public))
            return min(fallback, 1 if gate[gate_index] else inf)
        if quantifiers[len(public)]:
            possible = defaultdict(list)
            for row in rows:
                possible[row[used_universal]].append(row)
            step = 1 + max(search(public + (bit,), group, used_universal + 1)
                           for bit, group in possible.items())
        else:
            step = 1 + min(search(public + (bit,), rows, used_universal) for bit in BITS)
        return min(fallback, step)

    return search((), completions, 0)


def complexity_controls():
    checked = 0
    for quantifiers in product(BITS, repeat=3):
        for gate in product(BITS, repeat=8):
            valid = qbf_reference(gate, quantifiers)
            assert gated_acquisition(gate, quantifiers, inf) == (4 if valid else inf)
            assert gated_acquisition(gate, quantifiers, 256) == (4 if valid else 256)
            checked += 1
    return checked


def main():
    correlated, masks = graph_checks()
    for n in range(2, 6):
        routing_reference(n)
    posterior_checks = noisy_controls()
    qbf_checks = complexity_controls()
    print(
        f"verified {correlated} factored audit instances, {masks} whole-query masks, "
        f"4 exact route cases, {posterior_checks} exact stopped posteriors, and {qbf_checks} QBF gates"
    )


if __name__ == "__main__":
    main()
