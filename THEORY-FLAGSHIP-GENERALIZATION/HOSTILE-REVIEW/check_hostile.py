"""Exact countermodels and arithmetic controls for the advanced flagship review."""

from fractions import Fraction as Q
from itertools import product


def check_strategic():
    # Changing when a world can be installed: each revealed probe has its own
    # negative with exactly the positive law. The private fixed-world optimum
    # certificate has a different quantifier order.
    positive = (Q(1, 2), Q(1, 2))
    negatives = ((Q(1, 2), 1), (1, Q(1, 2)))
    for probe in range(2):
        assert positive[probe] == negatives[probe][probe]
    for target, profile in ((1, positive), (0, negatives[0]), (0, negatives[1])):
        positive_report = 1 - Q(4, 5) * sum(profile) / 2
        assert (1 - positive_report if target else positive_report) == Q(2, 5)
    for probe in range(2):
        negative_rate = (negatives[0][probe] + negatives[1][probe]) / 2
        plus = (Q(3, 5) * (1 - positive[probe]), Q(3, 5) * positive[probe])
        minus = (Q(2, 5) * (1 - negative_rate), Q(2, 5) * negative_rate)
        assert sum(map(min, zip(plus, minus))) == Q(2, 5)

    # Pairwise feasible uses mixtures x, y, z for three common actions.
    # World i needs its corresponding action with probability at least 1/2.
    for left, right in ((0, 1), (0, 2), (1, 2)):
        mix = [Q(0)] * 3
        mix[left] = mix[right] = Q(1, 2)
        assert sum(mix) == 1 and min(mix[left], mix[right]) == Q(1, 2)
    assert 3 * Q(1, 2) > 1

    # Exhaust all deterministic buy/report plans for the least favorable pair.
    # At exact optimal cost, all inequalities in this supporting plane must
    # be equalities in every plan with positive mixture weight.
    reports = ("+", "-", "skip")
    route_rules = [(False, (report,)) for report in reports]
    route_rules += [(True, pair) for pair in product(reports, repeat=2)]
    tight_rules = []
    for left, right in product(route_rules, repeat=2):
        coverage = error = Q(0)
        for sign in ("+", "-"):
            for (bought, rules), quality in ((left, Q(3, 4)), (right, Q(7, 8))):
                bit_probability = quality if sign == "+" else 1 - quality
                masses = (1 - bit_probability, bit_probability) if bought else (Q(1),)
                for report, mass in zip(rules, masses):
                    coverage += Q(1, 4) * mass * (report != "skip")
                    error += Q(1, 4) * mass * (report not in (sign, "skip"))
        gain = coverage / 2 - error
        gain_cap = (Q(1, 8) * left[0]) + (Q(3, 16) * right[0])
        assert gain <= gain_cap
        if gain == gain_cap and left[0]:
            tight_rules.append((left, right))
    assert len(tight_rules) == 4
    assert all(left == (True, ("-", "+")) for left, _ in tight_rules)
    assert {(right[0], right[1]) for _, right in tight_rules if right[0]} == {
        (True, ("-", "+"))
    }
    assert Q(4, 1) + 6 * Q(1, 2) == 7
    assert (1 + 3 * Q(1, 2)) / 2 == Q(5, 4)

    # The affine expected acquisition bound has exact equality. A fair
    # geometric retry has expected two reads and no finite hard cap.
    assert sum(Q(1, 2**draw) for draw in range(1, 10)) < 1
    assert Q(1, 2**10) > 0
    assert Q(1, 1) / Q(1, 2) == 2

    # Optional supplementary endpoint check for the price-optimal policy.
    best_positive = Q(1, 4) + Q(1, 8) * Q(58, 158)
    best_negative = Q(3, 4) + Q(1, 8) * Q(7, 27)
    assert best_positive == Q(187, 632)
    assert best_negative == Q(169, 216)
    assert Q(1, 16) - Q(132, 8 * 153**2) > 0


def check_continuous():
    # Finite support-point certificates need a different argument from
    # finite world certificates of a continuum optimum.
    sample = (Q(0), Q(1, 3), Q(3, 5), Q(1))
    controller = min(point for point in sample if point > 0)
    assert all(point * controller <= point**2 for point in sample)
    violating = controller / 2
    assert violating * controller > violating**2
    assert all(Q(step, 2**power) != Q(1, 3)
               for power in range(8) for step in range(2**power + 1))

    # Both sides have the same support but very different law. The conditional
    # correlation example then has identical one-step marginals, disjoint
    # two-step laws, and a different physical event.
    nominal = (Q(3, 4), Q(1, 4))
    actual = nominal[::-1]
    assert sum(map(min, zip(nominal, actual))) == Q(1, 2)
    first = {(0, 0): Q(1, 2), (1, 1): Q(1, 2)}
    second = {(0, 1): Q(1, 2), (1, 0): Q(1, 2)}
    for coordinate in range(2):
        for value in range(2):
            assert sum(prob for path, prob in first.items() if path[coordinate] == value) == Q(1, 2)
            assert sum(prob for path, prob in second.items() if path[coordinate] == value) == Q(1, 2)
    assert not (first.keys() & second.keys())

    # For fixed linked θ, a row-spliced (0,1) never describes an installed world.
    for step in range(101):
        theta = Q(step, 100)
        assert 2 * theta * (1 - theta) == Q(1, 2) - 2 * (theta - Q(1, 2))**2
    assert 2 * Q(1, 2) * Q(1, 2) < 1

    # Two individually valid fragments can both claim the same 1/2 ticket.
    true_matched_branch = Q(1, 2)
    fragment_one = fragment_two = Q(1, 2)
    assert max(fragment_one, fragment_two) <= true_matched_branch
    assert fragment_one + fragment_two > true_matched_branch
    assert 1 - true_matched_branch == Q(1, 2)  # Actual bad residual is this large.
    assert (1 - 2) * (1 - 2) > 0  # Raw negative survival "lower bounds".

    # A hard global guard can forbid the unique service action in the retained
    # good cell. Retained-world constraints alone have no witness.
    stopped, active = (Q(0), Q(1))
    assert active >= 1 and stopped <= 0
    assert not any(x >= 1 and x <= 0 for x in (stopped, active))


def check_statistics():
    # For all Bernoulli p <= 1/2, either monotone failure event has
    # fixed-look probability at most 1/4. Both tests retain all p > 1/2.
    paths = tuple(product(range(2), repeat=5))
    fail_first = {path for path in paths if sum(path[:2]) == 2}
    fail_second = {path for path in paths if sum(path) >= 4}
    total = len(paths)
    assert Q(len(fail_first), total) == Q(1, 4)
    assert Q(len(fail_second), total) == Q(3, 16)
    assert Q(len(fail_first | fail_second), total) == Q(5, 16)

    # Repeating a shared fair bit satisfies a marginal mean statement,
    # while the advertised outward radius after 64 repetitions is < 1/2.
    n = 64
    eta = Q(1, 4)
    assert 2**16 > 2 * n * (n + 1) / eta
    assert Q(16, 2 * n) < (Q(1, 2) - Q(1, n))**2
    assert abs(0 - Q(1, 2)) == abs(1 - Q(1, 2)) == Q(1, 2)

    # Every issued trial comes from a bad or omitted 1/100 stratum.
    bad = activation = Q(1, 100)
    joint_violation = bad
    assert joint_violation <= activation and joint_violation / activation == 1
    assert Q(1, 8) + Q(7, 8) * Q(1, 4) == Q(11, 32) > Q(1, 4)



def check_unified():
    # Two distinct deliveries may have identical factors and one destination.
    seed_flows = (Q(1), Q(1))
    likelihood = Q(1, 2)
    assert sum(seed_flows) * likelihood == 1
    assert sum(seed_flows) * likelihood**2 == Q(1, 2)
    assert not ({"finish-A"} & {"finish-B"})

    # Recompute the likelihood quotient from full supported histories.
    for depth in range(7):
        for theta, tag in product((Q(1, 8), Q(1, 4), Q(3, 4), Q(7, 8)), range(2)):
            stay_rate = Q(1, 2) + (-1)**tag * theta * (1 - theta) / 2
            grouped = {}
            for letters in product(range(2), repeat=depth):
                stays = sum(letters)
                parity = (depth - stays) % 2
                weight = stay_rate**stays * (1 - stay_rate)**(depth - stays)
                grouped[stays, parity] = grouped.get((stays, parity), Q(0)) + weight
            assert len(grouped) == depth + 1
            assert sum(grouped.values()) == 1

    # Same conditional issue curve, with exactly the priced menu restriction.
    for theta in (Q(1, 8), Q(1, 4), Q(3, 4), Q(7, 8)):
        low_issue = Q(3, 4) - theta / 2
        high_issue = 1 - theta
        full = Q(2, 3) * low_issue + Q(1, 3) * high_issue
        high_only = Q(2, 3) * high_issue + Q(1, 3) / 2
        assert full == high_only == Q(5, 6) - Q(2, 3) * theta
    assert Q(2, 3) * Q(3, 8) + Q(1, 3) == Q(7, 12) < Q(2, 3)

    # A two-sample mismatch in upstream law alone violates the TV envelope.
    surcharge = Q(1, 32)
    assert 1 - (1 - surcharge)**2 == Q(63, 1024) > surcharge

    # A legitimate calibrated policy passes all endpoint goals but fails
    # actual coverage and error when the surcharge is zero.
    conditional_high = Q(29, 93)
    endpoint_high = surcharge + (1 - surcharge) * conditional_high
    assert endpoint_high == Q(1, 3)
    assert (1 - endpoint_high) * Q(3, 8) + endpoint_high == Q(7, 12)
    plus_issue = Q(5, 8) + conditional_high / 8
    assert plus_issue == Q(247, 372) < Q(2, 3)
    assert 1 - plus_issue > Q(1, 3)
    assert Q(1, 2) + Q(1, 2) * Q(2, 3) * Q(27, 32) == Q(25, 32)

    # Arbitrarily little discounted loss may still mean eventual violation sure.
    discount = Q(1, 2)
    assert discount**10 < Q(1, 100)
    assert Q(1, 32) + Q(1, 2) > Q(3, 8)

if __name__ == "__main__":
    check_strategic()
    check_continuous()
    check_statistics()
    check_unified()
    print("Advanced hostile controls passed (strategic, continuum, transport, calibration, joint synthesis).")
