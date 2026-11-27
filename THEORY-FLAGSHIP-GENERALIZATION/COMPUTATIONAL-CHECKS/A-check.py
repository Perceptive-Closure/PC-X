"""Exact certificate checks for the G03 and G04 mathematical fixtures."""

from fractions import Fraction
from itertools import combinations, product


F = Fraction
LABELS = ("+", "-", "abstain")
ROUTES = ("L", "R")


def one_read_errors(profiles, probe, labels):
    zero, one = labels
    return tuple(
        (1 - signals[probe]) * (zero != sign) + signals[probe] * (one != sign)
        for sign, signals in profiles
    )


def audit_errors(profiles):
    for label in LABELS[:2]:
        yield tuple(F(label != sign) for sign, _ in profiles)
    for probe, labels in product(range(2), product(LABELS[:2], repeat=2)):
        yield one_read_errors(profiles, probe, labels)


def prior_error(errors, prior):
    return sum(w * e for w, e in zip(prior, errors, strict=True))


def check_complete_laws():
    confounded = (
        ("+", (F(1, 4), F(3, 4))),
        ("+", (F(3, 4), F(1, 4))),
        ("-", (F(1, 8), F(1, 8))),
        ("-", (F(7, 8), F(7, 8))),
    )
    plus_1, plus_2, minus_1, minus_2 = (signals for _, signals in confounded)
    for index in range(2):
        plus = (plus_1[index], plus_2[index])
        minus = (minus_1[index], minus_2[index])
        assert not set(plus) & set(minus)
        assert sum(plus) / 2 == sum(minus) / 2 == F(1, 2)
    assert min(
        prior_error(errors, (F(1, 4),) * 4) for errors in audit_errors(confounded)
    ) == F(1, 2)

    cross_design = (
        ("+", (F(1, 2), F(1, 2))),
        ("-", (F(1, 2), F(1))),
        ("-", (F(1), F(1, 2))),
    )
    prior = (F(3, 5), F(1, 5), F(1, 5))
    assert min(prior_error(errors, prior) for errors in audit_errors(cross_design)) == F(2, 5)
    profile_errors = []
    for probe in range(2):
        always_plus = one_read_errors(cross_design, probe, ("+", "+"))
        minus_after_one = one_read_errors(cross_design, probe, ("+", "-"))
        profile_errors.append(tuple(
            a / 5 + 4 * b / 5 for a, b in zip(always_plus, minus_after_one, strict=True)
        ))
    assert tuple((a + b) / 2 for a, b in zip(*profile_errors, strict=True)) == (F(2, 5),) * 3

    # An opposite profile fabricated by pasting individual action rows.
    pasted_negative = ("-", (cross_design[1][1][0], cross_design[2][1][1]))
    assert pasted_negative[1] == cross_design[0][1]
    assert pasted_negative not in cross_design


def report_metrics(sign, label):
    return F(label != "abstain"), F(label not in (sign, "abstain"))


def branch_options():
    yield from ((False, (label,)) for label in LABELS)
    yield from ((True, labels) for labels in product(LABELS, repeat=2))


def branch_metrics(option, sign, q, price):
    buy, labels = option
    if not buy:
        covered, wrong = report_metrics(sign, labels[0])
        return covered, wrong, F(0)

    bit_one = q if sign == "+" else 1 - q
    covered_zero, wrong_zero = report_metrics(sign, labels[0])
    covered_one, wrong_one = report_metrics(sign, labels[1])
    covered = (1 - bit_one) * covered_zero + bit_one * covered_one
    wrong = (1 - bit_one) * wrong_zero + bit_one * wrong_one
    return covered, wrong, F(price)


def matched_policy_metrics(left, right):
    result = []
    for sign in LABELS[:2]:
        l_metrics = branch_metrics(left, sign, F(3, 4), 1)
        r_metrics = branch_metrics(right, sign, F(7, 8), 3)
        result.append(tuple((a + b) / 2 for a, b in zip(l_metrics, r_metrics, strict=True)))
    return result


def check_matched_price_certificate():
    checked = 0
    for left, right in product(branch_options(), repeat=2):
        metrics = matched_policy_metrics(left, right)
        coverage, wrong, price = tuple((a + b) / 2 for a, b in zip(*metrics, strict=True))
        gain = coverage / 2 - wrong
        # Affine dual inequality checked for every deterministic policy.
        assert price >= 4 * coverage - 8 * wrong - F(1, 2)
        if not right[0]:
            assert gain <= F(1, 8)
        if not (left[0] and right[0]):
            assert gain <= F(3, 16)
        checked += 1
    assert checked == 144
    assert 4 * F(3, 4) - 8 * F(5, 32) - F(1, 2) == F(5, 4)
    read = (True, ("-", "+"))
    skip = (False, ("abstain",))
    for all_reads, only_left in zip(
        matched_policy_metrics(read, read), matched_policy_metrics(read, skip), strict=True
    ):
        mixture = tuple((a + b) / 2 for a, b in zip(all_reads, only_left, strict=True))
        assert mixture == (F(3, 4), F(5, 32), F(5, 4))
    return checked


def correctness(sign, k, s, proposal):
    base = {"L": F(3, 4), "R": F(7, 8)}[k]
    scale = {"L": 32, "R": 64}[k]
    return base + (s + (1 if sign == "+" else 2) * proposal) / scale


def defect_rate(sign, k, s, proposal):
    base = {"+": {"L": F(1, 8), "R": F(1, 4)}, "-": {"L": F(5, 8), "R": F(3, 4)}}[sign][k]
    return base + (s + proposal) / 16


def policy_slacks(sign, s, dry, live, direct):
    reference = sum(defect_rate(sign, k, s, a) / 2 for k, a in zip(ROUTES, direct, strict=True))
    reference_slack = F(5, 16) - reference if sign == "+" else reference - F(11, 16)
    issue, wrong, risk, good = F(0), F(0), F(0), F(0)
    for k, j, a, purchase_mass in zip(ROUTES, dry, live, (F(1, 2), F(1, 4)), strict=True):
        q = correctness(sign, k, s, j)
        issued = purchase_mass * (q if sign == "+" else 1 - q)
        r = defect_rate(sign, k, s, a)
        wrong += purchase_mass * (1 - q)
        issue += issued
        risk += issued * r
        good += issued * (1 - r)
    slacks = (reference_slack, F(5, 32) - wrong, F(1, 4) - risk)
    if sign == "+":
        slacks += (issue - F(19, 32), F(3, 8) * issue - risk, good - F(95, 256))
    return slacks


def check_continuous_performance_bounds():
    # Each slack has degree at most two in s. Nonnegative coefficients
    # in the degree-two Bernstein basis certify the entire closed interval.
    checked = 0
    for sign in LABELS[:2]:
        for choices in product((0, 1), repeat=6):
            dry, live, direct = choices[:2], choices[2:4], choices[4:]
            samples = [
                policy_slacks(sign, s, dry, live, direct)
                for s in (F(0), F(1, 2), F(1))
            ]
            for first, midpoint, last in zip(*samples, strict=True):
                coefficients = first, 2 * midpoint - (first + last) / 2, last
                assert all(value >= 0 for value in coefficients), (sign, choices, coefficients)
            checked += 1
    return checked


def check_safeguards():
    fact_cuts = ({1, 2}, {2, 3}, {1, 3})
    costs = (2, 3, 4)
    feasible = []
    for size in range(len(fact_cuts) + 1):
        for selected in combinations(range(len(fact_cuts)), size):
            uncovered = {1, 2, 3} - set().union(*(fact_cuts[i] for i in selected))
            if uncovered:
                assert 2 * F(5, 32) < F(3, 4)
            else:
                feasible.append((sum(costs[i] for i in selected), selected))
    assert min(feasible) == (5, (0, 1))


if __name__ == "__main__":
    check_complete_laws()
    policies = check_matched_price_certificate()
    response_tables = check_continuous_performance_bounds()
    check_safeguards()
    print("Complete-law examples verified at 1/2 and 2/5.")
    print(f"Exact matched-price certificate checked on {policies} deterministic policies.")
    print(f"Continuous upper bounds checked by exact Bernstein coefficients for {response_tables} tables.")
    print("Expected price 5/4, supported price 3, realized fact certificate price 5.")
