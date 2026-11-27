"""Exact finite checks for G01/G02. The algebraic example also uses z3-solver."""

from collections import Counter
from fractions import Fraction as F
from itertools import combinations, product

EPSILON = F(3, 19)
UTILITY = F(17, 19)
FLOOR = F(17, 20)
TAGS = (12, 4, 1, 1, 2)
COSTS = (1, 2)
REPORTS = tuple(product((0, 1), repeat=2))
PARAMETERS = tuple(F(i, 20) for i in range(21))


def two_draws(first, second):
    return {
        (0, 0): (1 - first) * (1 - second),
        (0, 1): (1 - first) * second,
        (1, 0): first * (1 - second),
        (1, 1): first * second,
    }


def check_linked_laws():
    laws = {theta: two_draws(theta, theta) for theta in PARAMETERS}
    for target, law in laws.items():
        assert sum(law.values()) == 1
        assert law[0, 1] + law[1, 0] == F(1, 2) - 2 * (target - F(1, 2)) ** 2
        support_values = {
            theta: candidate[1, 1] - 2 * target * (candidate[1, 0] + candidate[1, 1])
            for theta, candidate in laws.items()
        }
        assert [theta for theta in support_values
                if support_values[theta] == min(support_values.values())] == [target]
    assert max(law[0, 1] + law[1, 0] for law in laws.values()) == F(1, 2)
    assert (laws[0][0, 1], laws[1][0, 1], two_draws(F(0), F(1))[0, 1]) == (0, 0, 1)


def check_algebraic_policy():
    from z3 import Real, SolverFor, sat, unsat

    a, theta, x = (Real(name) for name in ("a", "t", "x"))
    solver = SolverFor("QF_NRA")
    root = (0 < a, a < 1, 2 * a * a == 1)
    region = (0 <= theta, theta <= 1, 2 * theta * theta >= 1)
    solver.add(*root)
    assert solver.check() == sat
    alpha = solver.model().eval(a)
    assert alpha.is_int() is False

    for violation in (a > theta, 2 * theta * a < 1):
        solver.push()
        solver.add(*region, violation)
        assert solver.check() == unsat
        solver.pop()

    for deviation, witness in ((x < a, 2 * a * x >= 1), (x > a, x <= a)):
        solver.push()
        solver.add(deviation, witness)
        assert solver.check() == unsat
        solver.pop()

    # Every nonzero finite mesh permits a strictly positive false candidate.
    mesh = (F(0), F(1, 4), F(1, 2), F(1))
    candidate = min(theta for theta in mesh if theta > 0)
    assert all(theta * candidate <= theta**2 for theta in mesh)
    theta = candidate / 2
    assert theta * candidate > theta**2
    # Identity for g(t) = -t^2/2 > 0, encoded by f = 1 + t^2 z^2/2 = 0.
    # The polynomial has just the monomials 1 and t^2*z^2.
    square_one = {(2, 2): F(1, 4)}
    square_two = {(2, 2): F(1, 4)}
    negative_f = {(0, 0): F(-1), (2, 2): F(-1, 2)}
    coefficients = Counter()
    for polynomial in (square_one, square_two, negative_f):
        for powers, coefficient in polynomial.items():
            coefficients[powers] += coefficient
    assert {powers: value for powers, value in coefficients.items() if value} == {(0, 0): -1}
    return alpha.sexpr()


def check_cut_reduction():
    def value(theta, edges):
        return sum(
            two_draws(theta[i], theta[j])[0, 1] + two_draws(theta[i], theta[j])[1, 0]
            for i, j in edges
        ) / len(edges)

    graph_list = [
        ((0, 1), (1, 2), (0, 2)),
        ((0, 1), (1, 2), (2, 3), (0, 3)),
        tuple(combinations(range(4), 2)),
    ]
    answers = []
    for edges in graph_list:
        n = 1 + max(max(edge) for edge in edges)
        vertices = tuple(product((F(0), F(1)), repeat=n))
        cuts = {theta: sum(theta[i] != theta[j] for i, j in edges) for theta in vertices}
        for theta in vertices:
            assert value(theta, edges) == F(cuts[theta], len(edges))
        maximum = F(max(cuts.values()), len(edges))
        for theta in product((F(0), F(1, 3), F(2, 3), F(1)), repeat=n):
            assert value(theta, edges) <= maximum
        answers.append(maximum)
    assert answers == [F(2, 3), F(1), F(2, 3)]


def raw_source(reports, theta, nominal=False, start=True):
    """Enumerate the raw tagged tickets and the source's supported event marks."""
    if not start:
        return {("stop", False, False, False): F(1)}
    q = theta.denominator
    count = Counter()
    ticket_tags = tuple(tag for tag, count_ in enumerate(TAGS) for _ in range(count_))
    for tag in ticket_tags:
        for first_ticket, second_ticket in product(range(q), repeat=2):
            if tag in (0, 1):
                active = nominal or bool(reports[tag])
                violation, work = False, active
            elif tag == 2:
                active, violation, work = True, True, True
            elif tag == 3 or nominal:
                active, violation, work = False, False, False
            else:
                active = first_ticket < theta.numerator
                violation = active and second_ticket < theta.numerator
                work = False
            count[tag, active, violation, work] += 1
    return {outcome: F(n, len(ticket_tags) * q * q) for outcome, n in count.items()}


def score(law, payoff):
    return sum(mass * payoff(leaf) for leaf, mass in law.items())


def score_act(leaf):
    return int(leaf[1])


def score_risk(leaf):
    return int(leaf[1]) * (int(leaf[2]) - EPSILON)


def score_utility(leaf):
    return int(leaf[1]) * (int(leaf[3]) - UTILITY)


def matched_law(reports, selected):
    components = {(2, True, True, True): F(1, 20), (3, False, False, False): F(1, 20)}
    for j in selected:
        if reports[j]:
            components[j, True, False, True] = F(TAGS[j], 20)
    return components


def envelope(common, payoff, minimum, maximum):
    uncovered = 1 - sum(common.values())
    matched = score(common, payoff)
    return matched + uncovered * minimum, matched + uncovered * maximum


def check_transport():
    total = 0
    for reports, theta in product(REPORTS, PARAMETERS):
        actual = raw_source(reports, theta)
        nominal = raw_source(reports, theta, nominal=True)
        assert sum(actual.values()) == sum(nominal.values()) == 1
        for selected in ((), (0,), (1,), (0, 1)):
            common = matched_law(reports, selected)
            assert all(mass <= actual[leaf] and mass <= nominal[leaf]
                       for leaf, mass in common.items())
            payoffs = [(score_act, 0, 1), (score_risk, -EPSILON, 1 - EPSILON),
                       (score_utility, -UTILITY, 1 - UTILITY)]
            for payoff, low, high in payoffs:
                minimum, maximum = envelope(common, payoff, low, high)
                actual_score = score(actual, payoff)
                assert minimum <= actual_score <= maximum
                diff = actual_score - score(nominal, payoff)
                assert abs(diff) <= (high - low) * (1 - sum(common.values()))
            total += 1

    fully_checked = matched_law((1, 1), (0, 1))
    assert envelope(fully_checked, score_act, 0, 1)[0] == FLOOR
    assert envelope(fully_checked, score_risk, -EPSILON, 1 - EPSILON)[1] == 0
    assert envelope(fully_checked, score_utility, -UTILITY, 1 - UTILITY)[0] == 0
    attain = raw_source((1, 1), F(1))
    assert score(attain, score_risk) == score(attain, score_utility) == 0
    assert score(raw_source((1, 1), F(0)), score_act) == FLOOR
    assert F(3, 20) / FLOOR == F(3, 17) > EPSILON
    assert all(score(raw_source(report, F(1)), score_act) < FLOOR
               for report in REPORTS if report != (1, 1))
    return total


def check_matched_score_disagreement():
    # The paired receipt matches with mass 4/5, while its genuine event differs.
    matched = F(4, 5)
    remainder = 1 - matched
    nominal_matched_score, actual_matched_score = F(0), F(1)
    signed = matched * (actual_matched_score - nominal_matched_score)
    values = {
        signed + remainder * (residual_actual - residual_nominal)
        for residual_actual, residual_nominal in product((0, 1), repeat=2)
    }
    assert min(values) == signed - remainder == F(3, 5)
    assert max(values) == signed + remainder == F(1)


def check_acquisition():
    def available(actual, selected):
        return [r for r in REPORTS if all(r[j] == actual[j] for j in selected)]

    def can_stop(scopes, selected):
        if (1, 1) not in scopes:
            return True
        if len(scopes) > 1:
            return False
        flow = matched_law((1, 1), selected)
        return (envelope(flow, score_act, 0, 1)[0] >= FLOOR
                and envelope(flow, score_risk, -EPSILON, 1 - EPSILON)[1] <= 0)

    def cost(selected):
        return sum(COSTS[j] for j in selected)

    candidates = ((), (0,), (1,), (0, 1))
    fixed = min(cost(s) for s in candidates
                if all(can_stop(available(r, s), s) for r in REPORTS))
    realized = min(cost(s) for s in candidates if can_stop(available((1, 1), s), s))

    def prospective(scopes, selected):
        if can_stop(scopes, selected):
            return 0
        options = []
        for j in (0, 1):
            if j in selected:
                continue
            cells = ([r for r in scopes if r[j] == val] for val in (0, 1))
            options.append(COSTS[j] + max(
                prospective(cell, (*selected, j)) for cell in cells if cell
            ))
        return min(options)

    assert fixed == realized == prospective(list(REPORTS), ()) == 3
    # A source read can add required paired evidence at unchanged compatible worlds.
    fixed_reports = [(1, 1)]
    assert not can_stop(fixed_reports, ())
    assert can_stop(fixed_reports, (0, 1))


def check_fixed_guard_report_cell():
    # The report retains only w0 for performance. The compiled guard still uses w1.
    guard = ("w0", "w1")
    retained = ("w0",)
    marker_coefficients = {
        "w0": {"A": F(0), "stop": F(0)},
        "w1": {"A": F(1), "stop": F(0)},
    }
    forbidden = {
        action for action in ("A", "stop")
        if any(marker_coefficients[world][action] > 0 for world in guard)
    }
    assert forbidden == {"A"}
    assert all(marker_coefficients[world]["A"] == 0 for world in retained)
    floor = F(1, 2)
    always_a = {"A": F(1), "stop": F(0)}
    assert all(sum(marker_coefficients[world][a] * mass for a, mass in always_a.items()) == 0
               for world in retained)
    assert sum(marker_coefficients["w1"][a] * mass for a, mass in always_a.items()) == 1
    assert always_a["A"] >= floor  # In w0 precisely A activates.

    # Fixed guard row x_A <= 0 plus retained-world coverage -x_A <= -floor.
    fixed_row, coverage_row = (F(1), F(0)), (F(-1), -floor)
    coefficient, bound = tuple(a + b for a, b in zip(fixed_row, coverage_row))
    assert coefficient == 0 and bound < 0

    # Inclusive normalized score ranges cover zero; arbitrary thresholds need min/max.
    for threshold in (F(-1, 2), F(0), F(1, 2), F(1), F(3, 2)):
        possible = {active * (event - threshold) for active, event in product((0, 1), repeat=2)}
        assert min(possible) == min(0, -threshold)
        assert max(possible) == max(0, 1 - threshold)


def check_calibration_limits():
    # Same unconditional mean on each draw, but one hidden bit is then retained forever.
    # The observed average stays 0 or 1 with equal prior masses, not near 1/2.
    laws = {tuple([z] * 8): F(1, 2) for z in (0, 1)}
    for column in range(8):
        assert sum(prob * row[column] for row, prob in laws.items()) == F(1, 2)
    assert sum(pr for row, pr in laws.items() if abs(F(sum(row), 8) - F(1, 2)) > F(1, 4)) == 1
    # Separate risks from the confidence level in a rare-activated failure example.
    eps, eta, activation = F(1, 5), F(1, 20), F(1, 20)
    assert eps * activation + (1 - eps) * min(eta, activation) == activation
    assert sum(F(1, n * (n + 1)) for n in range(1, 101)) == 1 - F(1, 101)


def main():
    check_linked_laws()
    root = check_algebraic_policy()
    check_cut_reduction()
    cases = check_transport()
    check_matched_score_disagreement()
    check_acquisition()
    check_fixed_guard_report_cell()
    check_calibration_limits()
    print("PASS: nonpolyhedral example, false endpoint mesh, and linked box cut examples")
    print(f"PASS: exact nonlinear algebraic policy and polynomial certificate {root}")
    print(f"PASS: {cases} raw source/fragment checks, sharp selective rates, optimal audit cost three")
    print("PASS: source-evidence refinement and dependent-calibration counterexamples")
    print("PASS: fixed guard survives a narrower report, with exact linear refutation")


if __name__ == "__main__":
    main()
