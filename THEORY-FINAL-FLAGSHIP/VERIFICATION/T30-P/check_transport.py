"""Independent exact calculations for the linked probability and anchor claims."""

from fractions import Fraction as F
from functools import cache
from itertools import combinations, product
import math


def expected_violations(mode, route, mismatched=False):
    result = F(0)
    completion = F(0)
    for phase, observed, choose_left, later in product(range(2), repeat=4):
        first_chance = (F(19, 20), F(1, 20))[phase]
        observation_chance = (F(1, 3), F(2, 3))[observed]
        route_chance = route[observed] if choose_left else 1 - route[observed]
        later_rate = F(7 if mismatched else 1 if choose_left != mode else 5, 19)
        later_chance = later_rate if later else 1 - later_rate
        path = first_chance * observation_chance * route_chance * later_chance
        result += path * bool(phase or later)
        completion += path
    assert completion == 1
    return result


def routing():
    deterministic = [
        max(expected_violations(mode, (left_a, left_b)) for mode in (0, 1))
        for left_a, left_b in product((0, 1), repeat=2)
    ]
    assert min(deterministic) == F(7, 30)
    policies = tuple(product((F(0), F(1, 4), F(1, 2), F(3, 4), F(1)), repeat=2))
    best = F(1)
    for policy in policies:
        rows = tuple(expected_violations(mode, policy) for mode in (0, 1))
        alpha = policy[0] / 3 + 2 * policy[1] / 3
        assert rows == ((6 - 4 * alpha) / 20, (2 + 4 * alpha) / 20)
        assert expected_violations(0, policy, mismatched=True) == F(2, 5)
        best = min(best, max(rows))
    assert best == F(1, 5)
    assert not {"L_A", "R_A"} & {"L_B", "R_B"}


def acquisition():
    candidates = tuple(product((0, 1), repeat=3))
    costs = (3, 1, 1)
    all_subsets = [subset for size in range(4) for subset in combinations(range(3), size)]

    def label(row):
        return row[row[0] + 1]

    def selects_label(cell):
        return len({label(row) for row in cell}) == 1

    def partial(current, chosen):
        return tuple((j, current[j]) for j in chosen)

    def compatible(target):
        return tuple(row for row in candidates if all(row[j] == bit for j, bit in target))

    @cache
    def future(known):
        cell = compatible(known)
        if selects_label(cell):
            return 0
        options = []
        for j in range(3):
            if any(j == key for key, _ in known):
                continue
            branches = [tuple(sorted(known + ((j, bit),))) for bit in (0, 1)]
            options.append(costs[j] + max(future(branch) for branch in branches
                                          if compatible(branch)))
        return min(options, default=math.inf)

    for row in candidates:
        price = min(sum(costs[j] for j in chosen) for chosen in all_subsets
                    if selects_label(compatible(partial(row, chosen))))
        assert price == (2 if row[1] == row[2] else 4)
    fixed = min(sum(costs[j] for j in chosen) for chosen in all_subsets
                if all(selects_label(compatible(partial(row, chosen))) for row in candidates))
    assert fixed == 5 and future(()) == 4
    assert F(2, 5) - F(1, 10) == F(3, 10)


def blockers_and_hard_guard():
    low, high, limit = F(1, 10), F(9, 10), F(17, 50)
    allowance = (limit - low) / (high - low)
    assert allowance == F(3, 10)
    assertions = tuple(range(3))
    for pair in combinations(assertions, 2):
        unused = next(j for j in assertions if j not in pair)
        assert all((high if i == unused else low) <= limit for i in pair)
    # Sum the three constraints with multiplier one and use sum of route weights = 1.
    assert sum(allowance for _ in assertions) < 1

    full_guard = ((F(1), F(0)), (F(0), F(1)))
    apparent_guard = (full_guard[0],)
    markers = (F(0), F(1))
    assert max(sum(a * b for a, b in zip(row, markers)) for row in apparent_guard) == 0
    assert max(sum(a * b for a, b in zip(row, markers)) for row in full_guard) == 1

    # Scaled robust-dual certificate multipliers must recover a point in the stated region.
    alpha, beta = (F(1, 4), F(1, 4)), F(1, 2)
    assert sum(alpha) == beta and alpha[1] <= F(3, 5) * beta
    normalized = tuple(entry / beta for entry in alpha)
    assert normalized == (F(1, 2), F(1, 2))


def adaptive_law(probabilities, horizon):
    def branch(prefix, mass):
        if not horizon - len(prefix) or (len(prefix) >= 2 and prefix[-2:] == (0, 0)):
            return {prefix: mass}
        slope = probabilities[int(bool(prefix and prefix[-1]))]
        return (branch(prefix + (0,), mass * (1 - slope))
                | branch(prefix + (1,), mass * slope))
    return branch((), F(1))


def calibration_boundaries():
    first = (F(1, 5), F(2, 5))
    second = (F(1, 4), F(1, 2))
    delta = max(abs(a - b) for a, b in zip(first, second))
    for h in range(8):
        p, q = adaptive_law(first, h), adaptive_law(second, h)
        assert sum(p.values()) == sum(q.values()) == 1
        tv = sum(abs(p[t] - q[t]) for t in p) / 2
        assert tv <= 1 - (1 - delta)**h <= h * delta

    # Same support of a free initial bit can retain the exact candidate set and still inform.
    assert abs(F(3, 4) - F(1, 4)) == F(1, 2)
    # A model that admits only one binary sample need not achieve a small error.
    assert (1 - abs(F(2, 5) - F(1, 10))) / 2 == F(7, 20)

    activation = F(1, 4)
    miss = F(1, 10)
    risk_cap, utility_floor = F(1, 5), F(3, 5)
    assert risk_cap * (activation - miss) + miss == F(13, 100)
    assert utility_floor * (activation - miss) == F(9, 100)


if __name__ == "__main__":
    routing()
    acquisition()
    blockers_and_hard_guard()
    calibration_boundaries()
    print("P1-P4 exact: 25 routing mixtures; all 8 report tuples and subsets; "
          "three-way blocker; hard guard; 8 adaptive stopped-law comparisons; "
          "calibration boundary fixtures.")
