"""Exact finite checks for the sealed U.1–U.4 result. Standard library only."""

from collections import defaultdict
from fractions import Fraction as F
from itertools import product
import json


def observed_probability(mode, previous, bit):
    one = F(1 + (mode ^ previous), 3)
    return one if bit else 1 - one


def likelihood(mode, bits):
    value, previous = F(1), 0
    for bit in bits:
        value *= observed_probability(mode, previous, bit)
        previous = bit
    return value


def recorded_state(bits):
    low, high = (likelihood(mode, bits) for mode in range(2))
    return bits[-1] if bits else 0, low / (low + high)


def compact_layers(horizon):
    state = {(0, F(1, 2))}
    counts = [1]
    for _ in range(horizon):
        state = {
            (bit, left / (left + right))
            for previous, posterior in state
            for bit in range(2)
            for left, right in [(
                posterior * observed_probability(0, previous, bit),
                (1 - posterior) * observed_probability(1, previous, bit),
            )]
        }
        counts.append(len(state))
    return counts


def event_probability(threshold):
    return F(sum(word <= threshold for word in (1, 2, 3, 4)), 4)


def live_rows(world, previous, pay, declarations):
    positive, route, mode = world
    hazard = event_probability(1 if positive else 3)
    no_read, after_zero, after_one = declarations
    activation = (1 - pay) * no_read + pay * ((1 - hazard) * after_zero + hazard * after_one)
    wrong = 1 - activation if positive else activation
    # The physical route is selected using the preceding trusted receipt.
    actual_record = (route, mode ^ previous ^ 1)
    return (pay, wrong, activation * hazard, activation,
            activation if actual_record[1] else F(0))


def planning_rule(bits, route):
    """Deliberately history-sensitive private randomization used in the comparison."""
    pattern = sum((index + 1) * bit for index, bit in enumerate(bits))
    return F((pattern + route) % 5, 4), (
        F((pattern * 3 + route + 1) % 5, 4),
        F((pattern + route * 3 + 2) % 5, 4),
        F((pattern * 2 + route + 3) % 5, 4),
    )


def policy_projection(bits_family):
    """Reference normalized action occupancies, without observing the installed mode."""
    grouped = defaultdict(lambda: [F(0) for _ in range(5)])
    for bits, route in product(bits_family, range(2)):
        mixture_weight = (likelihood(0, bits) + likelihood(1, bits)) / 4
        buy, (skip_plus, dry_zero_plus, dry_one_plus) = planning_rule(bits, route)
        row = grouped[recorded_state(bits), route]
        row[0] += mixture_weight
        row[1] += mixture_weight * buy
        row[2] += mixture_weight * (1 - buy) * skip_plus
        row[3] += mixture_weight * buy * dry_zero_plus
        row[4] += mixture_weight * buy * dry_one_plus
    policy = {}
    for key, (mass, paid, skip_plus, zero_plus, one_plus) in grouped.items():
        skip = mass - paid
        policy[key] = paid / mass, (skip_plus / skip if skip else F(0),
                                    zero_plus / paid if paid else F(0),
                                    one_plus / paid if paid else F(0))
    return policy


def metrics(world, bits_family, policy):
    total = [F(0) for _ in range(5)]
    _, route, mode = world
    for bits in bits_family:
        weight = likelihood(mode, bits)
        choice = policy(bits, route)
        observed = live_rows(world, bits[-1] if bits else 0, *choice)
        for index, value in enumerate(observed):
            total[index] += weight * value
    return tuple(total)


def check_projection():
    checks = 0
    for depth in range(8):
        family = list(product(range(2), repeat=depth))
        compact = policy_projection(family)
        assert len(compact) == 2 * (depth + 1)
        for world in product((False, True), range(2), range(2)):
            expanded = metrics(world, family, planning_rule)
            projected = metrics(world, family, lambda bits, route: compact[recorded_state(bits), route])
            assert expanded == projected, (depth, world, expanded, projected)
            checks += 1
    return checks


def sharp_routing():
    results = []
    # All pure score/skip tests satisfy the same supporting line under a balanced
    # matched opposite pair. Averaging before this choice preserves that line.
    pure_rules = [(F(0), (F(bit), F(0), F(0))) for bit in range(2)]
    pure_rules += [(F(1), (F(0), F(a), F(b))) for a, b in product(range(2), repeat=2)]
    for pay, decisions in pure_rules:
        e = sum(live_rows((positive, 0, 0), 0, pay, decisions)[1]
                for positive in (True, False)) / 2
        assert e >= F(1, 2) - pay / 4
    for error in (F(1, 4), F(3, 10), F(1, 3), F(2, 5), F(9, 20)):
        paid = 2 - 4 * error
        for world in product((False, True), range(2), range(2)):
            values = live_rows(world, 1, paid, (F(1, 2), F(1), F(0)))
            assert values[0] == paid and values[1] == error and values[2] <= F(2, 5)
            if world[0]:
                assert values[3] == 1 - error and values[2] / values[3] == F(1, 4)
            else:
                assert values[3] == error and values[2] / values[3] == F(3, 4)
        results.append({"error": str(error), "worst_expected_paid": str(paid),
                        "worst_supported_paid": 1, "positive_utility": str(1 - error),
                        "uniform_whole_attempt_risk": str(max((1 - error) / 4, 3 * error / 4))})
    return results


def main():
    layers = compact_layers(64)
    assert layers == list(range(1, 66)), layers
    print(json.dumps({
        "matched_world_vectors": check_projection(),
        "matched_coordinates_per_vector": 5,
        "prelude_depth": 64,
        "full_history_count_at_depth": 2**64,
        "compact_states_at_depth": layers[-1],
        "compact_prelude_total": sum(layers),
        "routing": sharp_routing(),
    }, indent=2))


if __name__ == "__main__":
    main()
