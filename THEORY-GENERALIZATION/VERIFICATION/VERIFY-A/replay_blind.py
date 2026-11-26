"""Proof-blind finite replay for the M07 exact/noisy bounds and M08 graph model."""

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from functools import cache
from itertools import combinations, product
from math import inf


def check_identity():
    checked = 0
    for size in (2, 4, 8):
        universe = (1 << (2 * size)) - 1
        gateway_truths = universe ^ ((1 << size) - 1)
        query_truths = (gateway_truths,) + tuple(
            (1 << key) | (1 << (size + key)) for key in range(size)
        )

        @cache
        def maximum_correct(cell, remaining):
            if not cell:
                return 0
            best = 1
            if remaining:
                for truths in query_truths:
                    yes, no = cell & truths, cell & ~truths
                    if yes and no:
                        best = max(
                            best,
                            maximum_correct(yes, remaining - 1)
                            + maximum_correct(no, remaining - 1),
                        )
            return best

        for calls in range(size + 2):
            expected = 1 if calls == 0 else min(2 * calls, 2 * size)
            assert maximum_correct(universe, calls) == expected
            checked += 1
    return checked


def walk_exit(prob_up, lower, upper):
    """Return the upper-exit probability and mean time by gambler's ruin."""
    ratio = (1 - prob_up) / prob_up
    hit_upper = (1 - ratio**lower) / (1 - ratio ** (lower + upper))
    mean_time = ((lower + upper) * hit_upper - lower) / (2 * prob_up - 1)
    return hit_upper, mean_time


def check_noisy_bounds():
    checked = 0
    for size, eta, risk in product(
        (2, 4, 8, 16),
        map(Fraction, ("1/10", "1/4", "2/5", "9/20")),
        map(Fraction, ("1/3", "1/10", "1/100")),
    ):
        ratio, drift = (1 - eta) / eta, 1 - 2 * eta
        lower = 1
        while ratio**lower < 3 / risk:
            lower += 1
        upper = lower
        while ratio**upper < 3 * size / risk:
            upper += 1
        false_accept, false_time = walk_exit(eta, lower, upper)
        true_accept, true_time = walk_exit(1 - eta, lower, upper)
        gateway_risk, gateway_time = walk_exit(eta, lower, lower)
        assert false_accept <= ratio**-upper and false_time <= lower / drift
        assert 1 - true_accept <= ratio**-lower and true_time <= upper / drift
        assert gateway_risk <= risk / 3 and gateway_time <= lower / drift
        assert gateway_risk + (1 - true_accept) + (size - 1) * false_accept <= risk
        assert gateway_time + (size - 1) * false_time + true_time <= (
            size * lower + upper
        ) / drift
        checked += 1
    return checked


@dataclass(frozen=True)
class Edge:
    index: int
    tail: str
    head: str
    bit: int


LAYERS = (
    (Edge(0, "s", "a", 0), Edge(1, "s", "b", 1), Edge(2, "s", "b", 0)),
    (
        Edge(3, "a", "c", 1),
        Edge(4, "a", "d", 0),
        Edge(5, "b", "c", 0),
        Edge(6, "b", "d", 1),
    ),
    (Edge(7, "c", "t", 0), Edge(8, "c", "t", 1), Edge(9, "d", "t", 1)),
)
PATHS = tuple(
    path
    for path in product(*LAYERS)
    if all(left.head == right.tail for left, right in zip(path, path[1:]))
)
BASE, EXTRA = (1, 2, 1), (2, 1, 3)
COMMANDS = ("fast", "slow", "read", "inspect")
JOBS = ("fast", "slow")


def tariff(stage, edge):
    return BASE[stage] + EXTRA[stage] * edge.bit


def public_records(edge, meter, command):
    if command == "fast" and edge.bit:
        return ()
    if command in JOBS:
        return (("done", (meter + edge.index) % 3), ("receipt", meter))
    if command == "read":
        return (("quiet", (meter + 1) % 3), (str(edge.bit), (meter + edge.bit + 1) % 3))
    if (edge.index + meter) % 3 == 0:
        return ()
    return ((str(edge.index % 2), 0),)


def costs(stage, meter, command):
    if command in JOBS:
        return 0, BASE[stage] + (command == "slow") * EXTRA[stage]
    if command == "read":
        return Fraction(meter + 1, 3), 0
    return Fraction(meter + 2, 5), 0


def check_frontier(deadline, horizon):
    last = len(LAYERS)
    cap = deadline + 1
    prefixes = tuple(
        tuple(
            min(cap, sum(tariff(stage, edge) for stage, edge in enumerate(path[:length])))
            for length in range(last + 1)
        )
        for path in PATHS
    )

    def summarize(stage, cell):
        if stage == last:
            final = [prefixes[path][last] for path in cell]
            return ((min(final), max(final)),)
        terms = defaultdict(list)
        for path in cell:
            terms[PATHS[path][stage]].append(prefixes[path][stage])
        return tuple((min(terms[e]), max(terms[e])) if e in terms else None for e in LAYERS[stage])

    @cache
    def suffix(stage, vertex):
        if stage == last:
            return 0, 0
        lower, upper = [], []
        for edge in LAYERS[stage]:
            if edge.tail == vertex:
                lo, hi = suffix(stage + 1, edge.head)
                lower.append(min(cap, tariff(stage, edge) + lo))
                upper.append(min(cap, tariff(stage, edge) + hi))
        return min(lower), max(upper)

    def compressed_score(stage, frontier):
        if stage == last:
            return frontier[0]
        lower, upper = [], []
        for edge, interval in zip(LAYERS[stage], frontier):
            if interval is not None:
                lo, hi = suffix(stage + 1, edge.head)
                lower.append(min(cap, interval[0] + tariff(stage, edge) + lo))
                upper.append(min(cap, interval[1] + tariff(stage, edge) + hi))
        return min(lower), max(upper)

    def combine(intervals):
        return min(lo for lo, _ in intervals), max(hi for _, hi in intervals)

    def update(stage, frontier, meter, command):
        rows = {}
        for edge, interval in zip(LAYERS[stage], frontier):
            if interval is None:
                continue
            records = public_records(edge, meter, command)
            if not records:
                return {}
            rows[edge] = records
        result = {}
        for record in {record for records in rows.values() for record in records}:
            edges = {edge for edge, records in rows.items() if record in records}
            if command not in JOBS:
                result[record] = tuple(
                    interval if edge in edges else None
                    for edge, interval in zip(LAYERS[stage], frontier)
                )
                continue
            shifted = defaultdict(list)
            for edge, interval in zip(LAYERS[stage], frontier):
                if edge in edges:
                    lo, hi = interval
                    weight = tariff(stage, edge)
                    shifted[edge.head].append((min(cap, lo + weight), min(cap, hi + weight)))
            if stage + 1 == last:
                result[record] = (combine([item for items in shifted.values() for item in items]),)
            else:
                result[record] = tuple(
                    combine(shifted[edge.tail]) if edge.tail in shifted else None
                    for edge in LAYERS[stage + 1]
                )
        return result

    @cache
    def compressed_value(stage, frontier, meter, moves, remaining):
        lo, hi = compressed_score(stage, frontier)
        if lo == cap or (stage == last and hi < cap):
            return 0
        if stage == last or moves == 0:
            return inf
        best = inf
        for command in COMMANDS:
            price, work = costs(stage, meter, command)
            if work > remaining:
                continue
            branches = update(stage, frontier, meter, command)
            if branches:
                next_stage = stage + (command in JOBS)
                worst = max(
                    compressed_value(next_stage, summary, p, moves - 1, remaining - work)
                    for (_, p), summary in branches.items()
                )
                best = min(best, price + worst)
        return best

    @cache
    def enumerated_value(stage, cell, meter, moves, remaining):
        frontier = summarize(stage, cell)
        scores = {prefixes[path][last] for path in cell}
        assert compressed_score(stage, frontier) == (min(scores), max(scores))
        if scores == {cap} or (stage == last and cap not in scores):
            best = 0
        elif stage == last or moves == 0:
            best = inf
        else:
            best = inf
            for command in COMMANDS:
                price, work = costs(stage, meter, command)
                if work > remaining:
                    continue
                by_path = [
                    (path, public_records(PATHS[path][stage], meter, command)) for path in cell
                ]
                branches = defaultdict(set)
                if all(records for _, records in by_path):
                    for path, records in by_path:
                        for record in records:
                            branches[record].add(path)
                next_stage = stage + (command in JOBS)
                assert update(stage, frontier, meter, command) == {
                    record: summarize(next_stage, paths) for record, paths in branches.items()
                }
                if branches:
                    worst = max(
                        enumerated_value(
                            next_stage, tuple(sorted(paths)), p, moves - 1, remaining - work
                        )
                        for (_, p), paths in branches.items()
                    )
                    best = min(best, price + worst)
        assert best == compressed_value(stage, frontier, meter, moves, remaining)
        return best

    enumerated_value(0, tuple(range(len(PATHS))), 0, horizon, deadline)
    return enumerated_value.cache_info().currsize


def check_static():
    queries = tuple(product(range(len(LAYERS)), ("bit", "parity")))

    def answer(edge, kind):
        return edge.bit if kind == "bit" else edge.index % 2

    def paired_witness(deadline, selected):
        cap = deadline + 1
        states = {("s", "s", 0, 0): ((), ())}
        for stage, edges in enumerate(LAYERS):
            next_states = {}
            for (v1, v2, s1, s2), (p1, p2) in states.items():
                for e1, e2 in product(edges, repeat=2):
                    if e1.tail != v1 or e2.tail != v2:
                        continue
                    if any(
                        answer(e1, kind) != answer(e2, kind) for i, kind in selected if i == stage
                    ):
                        continue
                    key = (
                        e1.head,
                        e2.head,
                        min(cap, s1 + tariff(stage, e1)),
                        min(cap, s2 + tariff(stage, e2)),
                    )
                    next_states.setdefault(key, (p1 + (e1,), p2 + (e2,)))
            states = next_states
        return next(
            (paths for (_, _, lo, hi), paths in states.items() if (lo == cap) != (hi == cap)),
            None,
        )

    checked = 0
    for deadline in range(11):
        is_positive = {
            path: sum(tariff(i, e) for i, e in enumerate(path)) <= deadline for path in PATHS
        }
        for count in range(len(queries) + 1):
            for menu in combinations(queries, count):
                def disagree(pair):
                    p1, p2 = pair
                    return is_positive[p1] != is_positive[p2] and all(
                        answer(p1[i], kind) == answer(p2[i], kind) for i, kind in menu
                    )

                explicit = any(disagree(pair) for pair in combinations(PATHS, 2))
                witness = paired_witness(deadline, menu)
                assert (witness is not None) == explicit
                if witness is not None:
                    assert disagree(witness)
                checked += 1
    return checked


if __name__ == "__main__":
    print(f"Exact identity cap checks: {check_identity()}")
    print(f"Exact noisy boundary calculations: {check_noisy_bounds()}")
    histories = sum(check_frontier(d, h) for d, h in product(range(11), range(3, 7)))
    print(f"Explicit history states checked against frontiers: {histories}")
    print(f"Paired-graph oracle checks: {check_static()}")
