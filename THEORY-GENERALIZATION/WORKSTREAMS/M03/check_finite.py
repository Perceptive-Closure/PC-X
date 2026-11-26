"""Exact mathematical fixtures for the M03 transport and anchor statements."""

from fractions import Fraction as F
from functools import cache
from itertools import combinations, product
import json
import math


def vertices(halfspaces):
    """Enumerate 2-D vertices by intersecting each pair of boundary lines."""
    points = set()
    for (a, b, c), (d, e, f) in combinations(halfspaces, 2):
        determinant = a * e - b * d
        if determinant:
            x = (c * e - b * f) / determinant
            y = (a * f - c * d) / determinant
            if all(u * x + v * y <= w for u, v, w in halfspaces):
                points.add((x, y))
    return points


def risk_range(probabilities):
    return min(probabilities), max(probabilities)


def calibration_and_transport():
    batches = ((50, 200, F(1, 8)), (768, 4096, F(1, 32)), (640, 1024, F(1, 16)))
    for _, size, radius in batches:
        assert math.sqrt(math.log(120) / (2 * size)) < radius

    reference = tuple(F(i, 8) for i in range(1, 4))
    deployment = tuple(F(i, 8) for i in range(9))
    supported = [
        p for p in deployment if any(abs(p - ref) <= F(1, 8) for ref in reference)
    ]
    assert risk_range(supported) == (F(0), F(1, 2))
    low_rate = (F(1, 8), F(1, 4))
    high_rate = (F(1, 2), F(3, 4))
    risks = [
        (1 - p) * low + p * high
        for p, low, high in product(supported, low_rate, high_rate)
    ]
    covered = risk_range(risks)
    assert covered == (F(1, 8), F(1, 2))
    mixture = risk_range([
        (1 - weight) * risk + weight * unseen
        for weight, risk, unseen in product((F(0), F(1, 5)), risks, (0, 1))
    ])
    assert mixture == (F(1, 10), F(3, 5))

    roster = [(F(i, 8), 1 - F(i, 8)) for i in range(9)]
    assert min(row[0] for row in roster) == min(row[1] for row in roster) == 0
    assert risk_range([max(row) for row in roster]) == (F(1, 2), F(1))
    left = (F(1, 4), F(0), F(0))
    right = (F(3, 4), F(3, 4), F(1, 4))
    w, a, b = [(x + y) / 2 for x, y in zip(left, right)]
    assert a / w == F(3, 4) and b / (1 - w) == F(1, 4)

    return {
        "covered": list(map(str, covered)),
        "unseen_at_most_one_fifth": list(map(str, mixture)),
        "coupled_worst_run_minimum": "1/2",
    }


def retrospective_anchors():
    common = [(1, 0, F(1, 2)), (0, 1, F(1, 2)), (-1, 0, F(0)),
              (0, -1, F(0)), (1, 1, F(3, 4))]
    facts = ((1, 0, F(1, 8)), (0, 1, F(1, 8)), (1, 1, F(1, 4)))
    costs = (1, 1, 3)
    threshold = F(1, 4)
    candidates = [item for size in range(4) for item in combinations(range(3), size)]
    estimates = {}
    for selected in candidates:
        halfspaces = common + [facts[i] for i in selected]
        corners = vertices(halfspaces)
        # This grid hits every vertex of these specific rational halfspaces.
        grid = [
            (F(i, 8), F(j, 8))
            for i, j in product(range(5), repeat=2)
            if all(a * i + b * j <= 8 * c for a, b, c in halfspaces)
        ]
        estimates[selected] = max(map(sum, corners))
        assert estimates[selected] == max(map(sum, grid))
    assert estimates[()] == F(3, 4)
    feasible = [item for item in candidates if estimates[item] <= threshold]
    price = lambda item: sum(costs[i] for i in item)
    exact = min(feasible, key=price)
    assert exact == (0, 1) and price(exact) == 2

    patterns = []
    while True:
        selected = min(
            (item for item in candidates if all(set(item) & edge for edge in patterns)),
            key=price,
        )
        if estimates[selected] <= threshold:
            break
        corners = vertices(common + [facts[i] for i in selected])
        x, y = max(corners, key=lambda point: (sum(point), point))
        edge = {i for i, (a, b, c) in enumerate(facts) if a * x + b * y > c}
        assert edge and edge not in patterns and not set(selected) & edge
        patterns.append(edge)
    assert selected == exact
    return {
        "base_risk_max": "3/4",
        "threshold": str(threshold),
        "patterns_in_order": [sorted(edge) for edge in patterns],
        "optimum": price(exact),
    }


def prospective_anchors():
    modes = tuple(product((0, 1), repeat=2))
    costs = (1, 2, 2)

    def outcome(mode, query):
        selector, label = mode
        if query == 0:
            return selector
        return label if selector == query - 1 else "*"

    @cache
    def optimum(current, unread):
        if len({mode[1] for mode in current}) == 1:
            return 0
        choices = []
        for query in unread:
            child_queries = tuple(i for i in unread if i != query)
            symbols = {outcome(mode, query) for mode in current}
            branches = (
                tuple(mode for mode in current if outcome(mode, query) == symbol)
                for symbol in symbols
            )
            choices.append(costs[query] + max(optimum(child, child_queries) for child in branches))
        return min(choices, default=math.inf)

    fixed = []
    for size in range(4):
        for reads in combinations(range(3), size):
            seen = {}
            for mode in modes:
                transcript = tuple(outcome(mode, query) for query in reads)
                seen.setdefault(transcript, set()).add(mode[1])
            if all(len(labels) == 1 for labels in seen.values()):
                fixed.append(sum(costs[query] for query in reads))
    exact = optimum(modes, (0, 1, 2))
    assert exact == 3 and min(fixed) == 4
    assert min(F(7, 2), exact) == 3 and min(F(5, 2), exact) == F(5, 2)
    assert 1 + F(1, 10) * 5 == F(3, 2)
    return {"adaptive_worst": exact, "fixed_worst": min(fixed)}


def main():
    result = {
        "calibration_and_transport": calibration_and_transport(),
        "retrospective_anchors": retrospective_anchors(),
        "prospective_anchors": prospective_anchors(),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
