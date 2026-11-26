"""Finite boundary replays for the PC-X hostile review. Python standard library only."""

from collections import Counter
from fractions import Fraction
from itertools import combinations, product
from math import inf, log


def subsets(items):
    items = tuple(items)
    for size in range(len(items) + 1):
        yield from combinations(items, size)


def check_common_command():
    def projected(menu):
        return {classes[command] for command in menu}

    def common_price(left, right):
        return min((prices[command] for command in left & right), default=inf)

    classes = {"L": "fast", "R": "fast", "F": "fast", "S": "slow"}
    prices = {"L": 1, "R": 1, "F": 1, "S": 2}
    left, right = {"L"}, {"R"}
    assert projected(left) == projected(right) == {"fast"}
    assert common_price(left, right) == inf
    assert common_price({"F"}, {"F"}) == 1

    # Both stage-1 actions reach the two aliased stage-2 checkpoints.
    left, right = left | {"S"}, right | {"S"}
    assert projected(left) == projected(right) == {"fast", "slow"}
    assert 1 + common_price(left, right) == 3
    assert 1 + common_price({"F", "S"}, {"F", "S"}) == 2


def check_blockers():
    # Look reveals one of two still-open states. Slow and the two revealed
    # repairs are the only subsequent successful action choices.
    slow = frozenset({"enter", "left-slow", "right-slow"})
    look = frozenset({"enter", "left-look", "right-look", "left-finish", "right-finish"})
    ground = slow | look
    all_masks = [frozenset(mask) for mask in subsets(sorted(ground))]

    def physical_replay(mask, budget):
        if "enter" in mask:
            return False
        if budget >= 4 and "left-slow" not in mask and "right-slow" not in mask:
            return True
        for side in ("left", "right"):
            if f"{side}-look" in mask or f"{side}-finish" in mask:
                return False
        return budget >= 2

    for budget, supports in ((1, ()), (2, (look,)), (4, (look, slow))):
        destructive = [mask for mask in all_masks if not physical_replay(mask, budget)]
        assert destructive == [mask for mask in all_masks if all(mask & edge for edge in supports)]
        blockers = [mask for mask in destructive if not any(other < mask for other in destructive)]
        blockers_again = [mask for mask in all_masks if all(mask & edge for edge in blockers)]
        assert set(supports) == {
            mask for mask in blockers_again if not any(other < mask for other in blockers_again)
        }
    assert not [mask for mask in all_masks if mask & frozenset()]
    return len(all_masks) * 3


def check_width_join():
    bits = (0, 1)
    tuples = list(product(bits, repeat=3))
    weights = (2, 3, 4)
    scores = {row: sum(weight * bit for weight, bit in zip(weights, row)) for row in tuples}
    relations = [set(relation) for relation in subsets(product(bits, repeat=2))]
    checks = double_charge_failures = 0

    for left, right in product(relations, repeat=2):
        admitted = [row for row in tuples if (row[0], row[1]) in left and (row[1], row[2]) in right]
        for selected in subsets(range(3)):
            paired = [
                (scores[first], scores[second])
                for first, second in product(admitted, repeat=2)
                if all(first[index] == second[index] for index in selected)
            ]
            for budget in range(sum(weights) + 1):
                cap = budget + 1
                passing_pair = any(low <= budget < high for low, high in paired)
                correct = doubled = False
                for center, other_center in product(bits, repeat=2):
                    if 1 in selected and center != other_center:
                        continue
                    left_pairs = [
                        (weights[0] * value, weights[0] * other)
                        for value, other in product(bits, repeat=2)
                        if (value, center) in left and (other, other_center) in left
                        and (0 not in selected or value == other)
                    ]
                    right_pairs = [
                        (weights[2] * value, weights[2] * other)
                        for value, other in product(bits, repeat=2)
                        if (center, value) in right and (other_center, other) in right
                        and (2 not in selected or value == other)
                    ]
                    for (lo_left, hi_left), (lo_right, hi_right) in product(left_pairs, right_pairs):
                        lo = min(cap, lo_left + lo_right + weights[1] * center)
                        hi = min(cap, hi_left + hi_right + weights[1] * other_center)
                        correct |= lo <= budget < hi
                        doubled |= lo + weights[1] * center <= budget < hi + weights[1] * other_center
                assert correct == passing_pair
                double_charge_failures += doubled != passing_pair
                checks += 1
    assert double_charge_failures > 0
    return checks, double_charge_failures


def check_stopped_statistics():
    delta = Fraction(1, 10)
    gap = Fraction(1, 2)
    draws = 32
    assert draws > 2 * log(4 / delta) / gap**2
    weight = Fraction(1, 2 ** (draws + 1))
    for count in range(draws + 1):
        fair_zero_path = Fraction(1, 2**count)
        mixture = weight + (1 - weight) * fair_zero_path
        assert mixture < 1 / delta and mixture / fair_zero_path < 1 / delta

    same_bit = {(0, 0), (1, 1)}
    opposite_bit = {(0, 1), (1, 0)}
    assert not (same_bit & opposite_bit)
    assert [{pair[index] for pair in same_bit} for index in (0, 1)] == [
        {pair[index] for pair in opposite_bit} for index in (0, 1)
    ]


def check_transport():
    # The seed is allowed controller memory. The preceding hidden score is
    # correlated with the seed differently in the two implementations.
    first = [(seed, seed) for seed in (0, 1)]
    second = [(1 - seed, seed) for seed in (0, 1)]
    for index in (0, 1):
        assert Counter(pair[index] for pair in first) == Counter(pair[index] for pair in second)
    assert [int(score != action) for score, action in first] == [0, 0]
    assert [int(score != action) for score, action in second] == [1, 1]

    # Even exact primitive lower envelopes can be weaker than canonical overlap.
    source_primitive = (1, 0)
    deployed_primitive = (0, 1)
    assert sum(map(min, source_primitive, deployed_primitive)) == 0
    assert sum(source_primitive) == sum(deployed_primitive) == 1


def check_readiness():
    checked = 0
    for count in range(2, 8):
        modes = set(range(count))
        menus = {mode: modes - {mode} for mode in modes}
        for members in subsets(sorted(modes)):
            if members:
                common = set.intersection(*(menus[mode] for mode in members))
                assert bool(common) == (len(members) < count)
                checked += 1
    return checked


def check_serial_deadline():
    bits = (0, 1)
    domains = ((0,), (1,), bits)
    checks = 0

    def price(schedule, weights):
        return len(weights) + sum(weight * action for weight, action in zip(weights, schedule))

    for weights in product((1, 2, 3), repeat=3):
        for cell in product(domains, repeat=3):
            modes = list(product(*cell))
            choices = [
                schedule for schedule in product(bits, repeat=3)
                if all(all(required <= selected for required, selected in zip(mode, schedule)) for mode in modes)
            ]
            common = min(price(schedule, weights) for schedule in choices)
            assert common == max(price(mode, weights) for mode in modes)
            for budget in range(3 + sum(weights) + 1):
                verdict = {mode: price(mode, weights) <= budget for mode in modes}
                for read in subsets(range(3)):
                    global_collision = any(
                        verdict[first] != verdict[second] and all(first[i] == second[i] for i in read)
                        for first, second in combinations(modes, 2)
                    )
                    local_collision = any(
                        verdict[first] != verdict[second]
                        and sum(u != v for u, v in zip(first, second)) == 1
                        and all(first[i] == second[i] for i in read)
                        for first, second in combinations(modes, 2)
                    )
                    assert global_collision == local_collision
                    checks += 1

    correlated = ((0, 1), (1, 0))
    weights = (1, 1)
    assert max(price(mode, weights) for mode in correlated) == 3
    assert price((1, 1), weights) == 4
    # With unit reads, the installed enabled menu itself exposes the same bit.
    menu = {0: {"fast", "slow"}, 1: {"slow"}}
    assert all(("fast" in menu[mode]) == (price((mode,), (1,)) <= 1) for mode in bits)
    return checks


if __name__ == "__main__":
    check_common_command()
    print(f"T12 physical removal masks checked: {check_blockers()}")
    checks, failures = check_width_join()
    print(f"T14.c paired join checks: {checks}. Wrong under duplicate charge: {failures}")
    check_transport()
    check_stopped_statistics()
    print(f"T29 nonempty readiness cells checked: {check_readiness()}")
    print(f"T30 product cell, deadline and query cases checked: {check_serial_deadline()}")
    print("Common-action, anchor-leakage, correlated-cell and statistical countermodels reproduced.")
