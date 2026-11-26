from dataclasses import dataclass
from functools import cache
from itertools import product
from math import inf
from random import Random


@dataclass(frozen=True)
class Edge:
    tail: int
    head: int
    stale: int
    fast_record: tuple[int, ...] = (0,)
    slow_record: tuple[int, ...] = (0,)
    read_mask: int = 0
    badge: int = 0


COMMANDS = ("fast", "slow", "read_stale", "read_badge")


def receipts(edge, meter, command):
    if command == "fast":
        return edge.fast_record if edge.stale == 0 else ()
    if command == "slow":
        return edge.slow_record
    if edge.read_mask & (1 << meter) == 0:
        return ()
    if command == "read_stale":
        return (edge.stale,)
    return (edge.badge,)


def charges(meter, command):
    if command == "fast":
        return 1, 0
    if command == "slow":
        return 2, 0
    return 0, 1 + meter


def all_paths(layers):
    paths = [(0, ())]
    for layer in layers:
        paths = [
            (edge.head, prior + (edge,))
            for node, prior in paths
            for edge in layer
            if edge.tail == node
        ]
    return tuple(path for _, path in paths)


def explicit_path_value(layers, deadline, moves):
    paths = all_paths(layers)
    if not paths:
        return None
    feasible = tuple(sum(1 + edge.stale for edge in path) <= deadline for path in paths)

    @cache
    def solve(stage, meter, work, remaining, live):
        if all(not feasible[model] for model in live):
            return 0
        if stage == len(layers):
            return 0 if all(feasible[model] for model in live) else inf
        if remaining == 0:
            return inf
        best = inf
        for command in COMMANDS:
            tariff, quote = charges(meter, command)
            if work + tariff > deadline:
                continue
            rows = {model: receipts(paths[model][stage], meter, command) for model in live}
            if any(not row for row in rows.values()):
                continue
            possible = {record for row in rows.values() for record in row}
            worst = max(
                solve(stage + (tariff > 0), record, work + tariff, remaining - 1,
                      tuple(model for model in live if record in rows[model]))
                for record in possible
            )
            best = min(best, quote + worst)
        return best

    return solve(0, 0, 0, moves, tuple(range(len(paths))))


def prune(layers):
    suffix = {edge.head for edge in layers[-1]}
    alive = []
    for layer in reversed(layers):
        usable = tuple(edge for edge in layer if edge.head in suffix)
        alive.append(usable)
        suffix = {edge.tail for edge in usable}
    active = {0}
    result = []
    for usable in reversed(alive):
        present = tuple(edge for edge in usable if edge.tail in active)
        active = {edge.head for edge in present}
        result.append(present)
    return result


def frontier_value(layers, deadline, moves):
    layers = prune(layers)
    if not layers[0]:
        return None
    stages = len(layers)

    def clip(value):
        return min(value, deadline + 1)

    @cache
    def suffix(stage, vertex):
        if stage == stages:
            return 0, 0
        branches = [
            (clip(1 + edge.stale + suffix(stage + 1, edge.head)[0]),
             clip(1 + edge.stale + suffix(stage + 1, edge.head)[1]))
            for edge in layers[stage]
            if edge.tail == vertex
        ]
        return min(low for low, _ in branches), max(high for _, high in branches)

    @cache
    def solve(stage, meter, work_left, remaining, frontier):
        if stage == stages:
            _, low, high = frontier[0]
            return 0 if low > deadline or high <= deadline else inf
        layer = layers[stage]
        if min(
            clip(low + 1 + layer[index].stale + suffix(stage + 1, layer[index].head)[0])
            for index, low, _ in frontier
        ) > deadline:
            return 0
        if remaining == 0:
            return inf
        best = inf
        for command in COMMANDS:
            tariff, quote = charges(meter, command)
            if tariff > work_left:
                continue
            rows = {index: receipts(layer[index], meter, command) for index, _, _ in frontier}
            if not all(rows.values()):
                continue
            by_record = {}
            for index, lo, hi in frontier:
                for record in rows[index]:
                    by_record.setdefault(record, []).append((index, lo, hi))
            worst = 0
            for record, active in by_record.items():
                if tariff == 0:
                    state = (stage, tuple(active))
                else:
                    reached = {}
                    for index, lo, hi in active:
                        edge = layer[index]
                        node = edge.head if stage + 1 < stages else 0
                        new_lo = clip(lo + 1 + edge.stale)
                        new_hi = clip(hi + 1 + edge.stale)
                        old = reached.get(node, (new_lo, new_hi))
                        reached[node] = (min(old[0], new_lo), max(old[1], new_hi))
                    if stage + 1 == stages:
                        state = (stages, ((0, *reached[0]),))
                    else:
                        state = (stage + 1, tuple(
                            (index, *reached[edge.tail])
                            for index, edge in enumerate(layers[stage + 1])
                            if edge.tail in reached
                        ))
                next_stage, summary = state
                worst = max(worst, solve(next_stage, record, work_left - tariff, remaining - 1, summary))
            best = min(best, quote + worst)
        return best

    return solve(0, 0, deadline, moves, tuple((i, 0, 0) for i in range(len(layers[0]))))


def opposed_pair(layers, queries, deadline):
    reachable = {(0, 0, 0, 0)}
    for stage, layer in enumerate(layers):
        updated = set()
        for left, right in product(layer, repeat=2):
            if (stage, "stale") in queries and left.stale != right.stale:
                continue
            if (stage, "badge") in queries and left.badge != right.badge:
                continue
            for u, v, a, b in reachable:
                if (left.tail, right.tail) == (u, v):
                    updated.add((left.head, right.head, min(deadline + 1, a + 1 + left.stale),
                                 min(deadline + 1, b + 1 + right.stale)))
        reachable = updated
    return any((a <= deadline) != (b <= deadline) for _, _, a, b in reachable)


def explicit_disagreement(paths, queries, deadline):
    answers = {}
    for path in paths:
        row = tuple(getattr(path[stage], field) for stage, field in queries)
        target = sum(1 + edge.stale for edge in path) <= deadline
        if row in answers and answers[row] != target:
            return True
        answers[row] = target
    return False


def check_examples():
    linked_later = (
        (Edge(0, 0, 0), Edge(0, 1, 0, fast_record=(1,))),
        (Edge(0, 0, 0), Edge(1, 1, 1)),
        (Edge(0, 0, 1), Edge(1, 1, 0)),
    )
    with_no_receipt = ((Edge(0, 0, 0), Edge(0, 1, 0)), *linked_later[1:])
    paid = ((Edge(0, 0, 0, fast_record=(1,)),),
            (Edge(0, 0, 0, read_mask=2), Edge(0, 0, 1, read_mask=2)))
    two_correlated = ((Edge(0, 0, 0), Edge(0, 1, 1)),
                      (Edge(0, 0, 0), Edge(1, 0, 1)))
    for data, deadline, moves, expected in [
        (linked_later, 4, 3, 0),
        (with_no_receipt, 4, 3, inf),
        (paid, 2, 3, 2),
        (two_correlated, 1, 2, 0),
    ]:
        assert explicit_path_value(data, deadline, moves) == expected
        assert frontier_value(data, deadline, moves) == expected
    assert opposed_pair(two_correlated, set(), 3)
    assert not opposed_pair(two_correlated, {(1, "stale")}, 3)


def main():
    rng = Random(3621)
    joint = static = 0
    records = [(0,), (1,), (0, 1)]
    for trial in range(100):
        length = 2 + (trial % 3)
        layers = tuple(tuple(Edge(
            rng.randrange(2) if stage else 0, rng.randrange(2), rng.randrange(2),
            rng.choice(records), rng.choice(records), rng.randrange(4), rng.randrange(2)
        ) for _ in range(rng.randint(2, 4))) for stage in range(length))
        paths = all_paths(layers)
        for deadline in range(length - 1, 2 * length + 1):
            for moves in (length, length + 2):
                assert frontier_value(layers, deadline, moves) == explicit_path_value(layers, deadline, moves)
                joint += 1
            menu = [(stage, field) for stage in range(length) for field in ("stale", "badge")]
            for bits in range(2 ** len(menu)):
                chosen = {item for index, item in enumerate(menu) if bits >> index & 1}
                assert opposed_pair(layers, chosen, deadline) == explicit_disagreement(paths, chosen, deadline)
                static += 1
    check_examples()
    print(f"{joint} compressed-vs-explicit governed optima; {static} static pair queries")
    print("Correlated work receipts 0 versus infeasible without them; dynamic paid read 2; early negative 0")


if __name__ == "__main__":
    main()
