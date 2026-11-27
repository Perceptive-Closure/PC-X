"""Independent exact checks for the generalized A neutral statement."""

from fractions import Fraction as F
from itertools import combinations, product


def one_read_error(profile, is_positive, choice, reports):
    if choice is None:
        return F(int(reports[0] != is_positive))
    mean = profile[choice]
    return (1 - mean) * int(reports[0] != is_positive) + mean * int(reports[1] != is_positive)


def check_complete_laws():
    pure_plans = [(None, (d,)) for d in (False, True)] + [
        (probe, verdicts) for probe in range(2) for verdicts in product((False, True), repeat=2)
    ]
    first = (
        ((F(1, 4), F(3, 4)), True, F(1, 4)),
        ((F(3, 4), F(1, 4)), True, F(1, 4)),
        ((F(1, 8), F(1, 8)), False, F(1, 4)),
        ((F(7, 8), F(7, 8)), False, F(1, 4)),
    )
    second = (
        ((F(1, 2), F(1, 2)), True, F(3, 5)),
        ((F(1, 2), F(1)), False, F(1, 5)),
        ((F(1), F(1, 2)), False, F(1, 5)),
    )
    for worlds, expected in ((first, F(1, 2)), (second, F(2, 5))):
        errors = [
            sum(weight * one_read_error(p, sign, choice, verdicts) for p, sign, weight in worlds)
            for choice, verdicts in pure_plans
        ]
        assert min(errors) == expected
    for profile, pos, _ in second:
        pos_issue = sum(1 - mean + mean / 5 for mean in profile) / 2
        assert (1 - pos_issue if pos else pos_issue) == F(2, 5)


def route_stats(plan, correct_rate, is_positive):
    verdict = 1 if is_positive else -1
    returns = {verdict: correct_rate, -verdict: 1 - correct_rate} if plan[0] else {0: 1}
    reports = {1: plan[1], -1: plan[2]} if plan[0] else {0: plan[1]}
    coverage = sum(mass for bit, mass in returns.items() if reports[bit])
    wrong = sum(mass for bit, mass in returns.items() if reports[bit] == -verdict)
    return F(coverage), F(wrong)


def check_joint_fixture():
    pure_routes = [(False, d) for d in (-1, 0, 1)] + [
        (True, r1, r0) for r1, r0 in product((-1, 0, 1), repeat=2)
    ]
    for route_l, route_r in product(pure_routes, repeat=2):
        class_rows = [
            tuple(sum(pair) / 2 for pair in zip(
                route_stats(route_l, F(3, 4), sign),
                route_stats(route_r, F(7, 8), sign),
            ))
            for sign in (False, True)
        ]
        coverage, error = (sum(pair) / 2 for pair in zip(*class_rows))
        x, y = int(route_l[0]), int(route_r[0])
        assert error >= coverage / 2 - F(x, 8) - F(3 * y, 16)

    for s, j_l, j_r, a_l, a_r, sign in product(
        (F(0), F(1, 2), F(1)), (0, 1), (0, 1), (0, 1), (0, 1), (False, True)
    ):
        kappa = 1 if sign else 2
        q_l = F(3, 4) + (s + kappa * j_l) / 32
        q_r = F(7, 8) + (s + kappa * j_r) / 64
        wrong = (1 - q_l) / 2 + (1 - q_r) / 4
        assert wrong <= F(5, 32)
        l_issued, r_issued = (q_l / 2, q_r / 4) if sign else ((1 - q_l) / 2, (1 - q_r) / 4)
        l_risk = (F(1, 8) if sign else F(5, 8)) + (s + a_l) / 16
        r_risk = (F(1, 4) if sign else F(3, 4)) + (s + a_r) / 16
        issuance = l_issued + r_issued
        joint_bad = l_issued * l_risk + r_issued * r_risk
        assert joint_bad <= F(1, 4)
        if sign:
            assert issuance >= F(19, 32)
            assert joint_bad <= F(3, 8) * issuance
            assert issuance - joint_bad >= F(95, 256)

    cuts = (({1, 2}, 2), ({2, 3}, 3), ({1, 3}, 4))
    costs = [
        sum(cost for _, cost in selection)
        for n in range(1, 4)
        for selection in combinations(cuts, n)
        if set.union(*(branch for branch, _ in selection)) == {1, 2, 3}
    ]
    assert min(costs) == 5


if __name__ == "__main__":
    check_complete_laws()
    check_joint_fixture()
    print("PASS A.G1-G3: complete-law Bayes values, matched acquisition, actual finish bounds and fact cost")
