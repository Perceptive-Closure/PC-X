"""Exact finite checks for the sealed governance candidates.

Run from the repository root with Python's standard library. These checks use
fresh mathematical examples and read no historical experiment data.
"""

from collections import defaultdict
from fractions import Fraction
from functools import cache
from itertools import combinations, product
from math import inf


def polytope_vertices(rows):
    """Intersect halfspace boundary pairs and independently validate all rows."""
    vertices = set()
    for (a, b, c), (x, y, z) in combinations(rows, 2):
        det = a * y - b * x
        if det == 0:
            continue
        point = ((c * y - b * z) / det, (a * z - c * x) / det)
        if all(u * point[0] + v * point[1] <= limit for u, v, limit in rows):
            vertices.add(point)
    return vertices


def check_monitor_bounds():
    checked = 0
    scale = 4
    for alarm_mass in range(scale + 1):
        silent_mass = scale - alarm_mass
        for lo_t, hi_t in combinations_with_equal(alarm_mass):
            for lo_m, hi_m in combinations_with_equal(silent_mass):
                l1, u1, l0, u0 = (
                    Fraction(value, scale) for value in (lo_t, hi_t, lo_m, hi_m)
                )
                for beta, false_floor, miss_cap in product(
                    (Fraction(0), Fraction(1, 3), Fraction(1, 2), Fraction(2, 3)),
                    range(alarm_mass + 2),
                    (Fraction(0), Fraction(1, 2), Fraction(1)),
                ):
                    floor = Fraction(false_floor, scale)
                    rows = [
                        (-1, 0, -l1), (1, 0, u1), (0, -1, -l0), (0, 1, u0),
                        (-beta, 1 - beta, Fraction(0)),
                        (1, 0, Fraction(alarm_mass, scale) - floor),
                        (0, 1, miss_cap),
                    ]
                    corners = polytope_vertices(rows)
                    u = min(u1, Fraction(alarm_mass, scale) - floor)
                    k = beta / (1 - beta)
                    top_m = min(u0, miss_cap)
                    feasible = u >= l1 and l0 <= k * u and l0 <= top_m
                    assert bool(corners) == feasible
                    if feasible:
                        upper_m = min(top_m, k * u)
                        lower_risk = l0 + (max(l1, l0 / k) if k else l1)
                        results = (
                            min(m for _, m in corners),
                            max(m for _, m in corners),
                            min(t + m for t, m in corners),
                            max(t + m for t, m in corners),
                        )
                        assert results == (l0, upper_m, lower_risk, u + upper_m)
                    checked += 1
    return checked


def combinations_with_equal(n):
    return ((left, right) for left in range(n + 1) for right in range(left, n + 1))


def two_state_risk(initial, rows, horizon):
    risk = initial
    for _ in range(horizon):
        risk = (1 - risk) * rows[0] + risk * rows[1]
    return risk


def probe_risk(initial, rows, horizon):
    # Index = 2 * projected state + recorder bit. The recorder bit toggles.
    mass = [1 - initial, Fraction(0), initial, Fraction(0)]
    for _ in range(horizon):
        next_mass = [Fraction(0)] * 4
        for index, (probability, present) in enumerate(zip(rows, mass, strict=True)):
            next_bit = 1 - index % 2
            next_mass[next_bit] += (1 - probability) * present
            next_mass[2 + next_bit] += probability * present
        mass = next_mass
    return sum(mass[2:])


def check_fidelity():
    checked = 0
    grid = (Fraction(0), Fraction(1, 2), Fraction(1))
    for p0, q0, a, b, c, d, e, f in product(grid, repeat=8):
        p, q = (a, b), (c, d, e, f)
        eta = max(abs(p[index // 2] - row) for index, row in enumerate(q))
        for horizon in (0, 1, 3):
            bound = 1 - (1 - abs(p0 - q0)) * (1 - eta) ** horizon
            assert abs(two_state_risk(p0, p, horizon) - probe_risk(q0, q, horizon)) <= bound
            checked += 1
    hazards = (Fraction(1, 4), Fraction(1, 2), Fraction(1, 3))
    after = hazards[0]
    for hazard in hazards[1:]:
        after += (1 - after) * hazard
    assert after == 1 - Fraction(3, 4) * Fraction(1, 2) * Fraction(2, 3)
    return checked


def compositions(total, size):
    if size == 1:
        yield (total,)
        return
    for first in range(total + 1):
        for rest in compositions(total - first, size - 1):
            yield (first, *rest)


def check_composition():
    # Enumerate all four-ticket laws on (global, local_1, local_2) bits.
    bits = tuple(product(range(2), repeat=3))
    event_rows = []
    for law in compositions(4, len(bits)):
        outside = sum(n for (g, first, second), n in zip(bits, law) if g and not (first or second))
        local_first = sum(n for (_, first, _), n in zip(bits, law) if first)
        local_second = sum(n for (_, _, second), n in zip(bits, law) if second)
        global_event = sum(n for (g, _, _), n in zip(bits, law) if g)
        event_rows.append((outside, local_first, local_second, global_event))

    checked = 0
    for e, p1, d1, p2, d2 in product(range(5), repeat=5):
        caps = (e, min(4, p1 + d1), min(4, p2 + d2))
        witnessed_max = max(
            r[3] for r in event_rows if all(actual <= cap for actual, cap in zip(r, caps))
        )
        assert witnessed_max == min(4, sum(caps))
        checked += 1
    return checked


OBSERVATION = (0, 0, 1, 1)
GOAL = 2
UNSAFE = 3


@cache
def trees(depth):
    """Enumerate whole contingent policies before examining any plant."""
    if depth == 0:
        return (None,)
    return (None,) + tuple(
        (action, branches)
        for action in range(2)
        for branches in product(trees(depth - 1), repeat=2)
    )


def physical_path_score(tree, state, rows, costs):
    """Brute reference follows concrete outcomes separately, without belief grouping."""
    if state == UNSAFE:
        return inf
    if tree is None:
        return 0 if state == GOAL else inf
    action, branches = tree
    support = rows.get((state, action), ())
    if not support:
        return inf
    return costs[action] + max(
        physical_path_score(branches[OBSERVATION[next_state]], next_state, rows, costs)
        for next_state in support
    )


def supported_children(belief, action, rows):
    children = defaultdict(set)
    for state in belief:
        support = rows.get((state, action), ())
        if not support or UNSAFE in support:
            return None
        for successor in support:
            children[OBSERVATION[successor]].add(successor)
    return {o: frozenset(states) for o, states in children.items()}


def minimax_solver(rows, costs):
    @cache
    def minimum(belief, horizon):
        if UNSAFE in belief:
            return inf
        if belief == frozenset((GOAL,)):
            return 0
        if horizon == 0:
            return inf
        choices = []
        for action, cost in enumerate(costs):
            children = supported_children(belief, action, rows)
            if children is not None:
                choices.append(cost + max(minimum(b, horizon - 1) for b in children.values()))
        return min(choices, default=inf)

    return minimum


def check_game():
    checked = 0
    offers = ((), (0,), (1,), (GOAL,), (0, GOAL), (GOAL, UNSAFE))
    starts = tuple(map(frozenset, ((0,), (1,), (0, 1))))
    for options in product(offers, repeat=4):
        rows = dict(zip(product(range(2), repeat=2), options, strict=True))
        for costs in ((0, 1), (2, 1)):
            value = minimax_solver(rows, costs)
            for depth, start in product(range(3), starts):
                reference = min(
                    max(physical_path_score(tree, state, rows, costs) for state in start)
                    for tree in trees(depth)
                )
                assert value(start, depth) == reference
                checked += 1

    lane_rows = {(0, 0): (GOAL,), (1, 1): (GOAL,)}
    lane_value = minimax_solver(lane_rows, (0, 0))
    assert lane_value(starts[0], 1) == lane_value(starts[1], 1) == 0
    assert lane_value(starts[2], 1) == inf
    assert supported_children(starts[2], 0, lane_rows) is None
    return checked


def subsets(count):
    return range(1 << count)


def indices(mask, count):
    return [i for i in range(count) if mask & (1 << i)]


def cells(chosen, queries):
    groups = defaultdict(int)
    for mode in range(3):
        pattern = tuple(queries[q][mode] for q in indices(chosen, len(queries)))
        groups[pattern] |= 1 << mode
    return tuple(groups.values())


def split_queries(obstruction, queries):
    surviving = indices(obstruction, 3)
    return sum(
        1 << q
        for q, values in enumerate(queries)
        if len({values[mode] for mode in surviving}) > 1
    )


def minimum_cover(menu, edges, costs):
    covers = (
        mask
        for mask in subsets(len(costs))
        if mask & menu == mask and all(mask & edge for edge in edges)
    )
    return min(covers, key=lambda mask: sum(costs[q] for q in indices(mask, len(costs))), default=None)


def delayed_audit(menu, readiness, queries, costs):
    edges = set()
    while True:
        selected = minimum_cover(menu, edges, costs)
        if selected is None:
            return inf
        failure = next((cell for cell in cells(selected, queries) if not readiness(cell)), None)
        if failure is None:
            return sum(costs[q] for q in indices(selected, len(costs)))
        for mode in indices(failure, 3):
            reduced = failure & ~(1 << mode)
            if reduced and not readiness(reduced):
                failure = reduced
        edge = split_queries(failure, queries)
        assert edge not in edges
        edges.add(edge)


def check_external_audit():
    checked = 0
    queries = ((0, 0, 1), (0, 1, 0), (1, 0, 0))
    costs = (1, 2, 3)
    full_action_set = (1 << 3) - 1
    for offers in product(subsets(3), repeat=3):
        for allow_uniform_failure in (False, True):
            def ready(cell):
                possible = indices(cell, 3)
                common = full_action_set
                for mode in possible:
                    common &= offers[mode]
                return bool(common) or (allow_uniform_failure and all(not offers[mode] for mode in possible))

            obstruction_masks = [
                cell
                for cell in range(1, 8)
                if not ready(cell) and all(
                    reduced == 0 or ready(reduced)
                    for reduced in (cell & ~(1 << k) for k in indices(cell, 3))
                )
            ]
            edges = {split_queries(obstruction, queries) for obstruction in obstruction_masks}
            for selected in subsets(3):
                assert all(ready(cell) for cell in cells(selected, queries)) == all(
                    selected & edge for edge in edges
                )
                checked += 1
            for menu in (0, 1, 3, 7):
                reference = min(
                    (
                        sum(costs[q] for q in indices(selected, 3))
                        for selected in subsets(3)
                        if selected & menu == selected and all(ready(cell) for cell in cells(selected, queries))
                    ),
                    default=inf,
                )
                assert delayed_audit(menu, ready, queries, costs) == reference
                checked += 1

    # Every proper subset has a common action, and the full one does not.
    for n in range(2, 8):
        full = (1 << n) - 1
        for belief in range(1, full + 1):
            common = full
            for mode in indices(belief, n):
                common &= ~(1 << mode)
            assert bool(common) == (belief != full)
    return checked


if __name__ == "__main__":
    print(f"T25 monitor polytopes: {check_monitor_bounds()}")
    print(f"T26 exact kernel/horizon comparisons: {check_fidelity()}")
    print(f"T27 sharp joint-budget grid cases: {check_composition()}")
    print(f"T28–T29 bounded belief/brute-tree comparisons: {check_game()}")
    print(f"T29 fixed coverage and minimum-cost comparisons: {check_external_audit()}")
