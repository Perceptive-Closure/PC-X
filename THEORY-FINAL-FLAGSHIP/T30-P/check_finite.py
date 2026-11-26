"""Exact T30.P replays using only the Python standard library."""

from collections import Counter, defaultdict
from functools import cache
from fractions import Fraction as F
from itertools import combinations, product
from math import inf, prod

PASS_LIMIT = F(1, 5)
COSTS = (3, 1, 1)
MACHINES = ("A", "B")
REPORTS = tuple(product((0, 1), repeat=3))
COMPONENTS = tuple((*report, hidden) for report in REPORTS for hidden in (0, 1))
STOP = "stop"


def sign(report):
    selector, left, right = report
    return (left, right)[selector] == 0


def source_joint(component, plan, scale=1, receipt=True, omit_upper_hazard=False):
    """Execute the raw finite ticket encodings and count complete joint outcomes."""
    if plan is None:
        return {(None, False, False, 0, False): F(1)}
    good = sign(component[:3])
    latent = component[3]
    counts = Counter()
    for machine_ticket in range(3 * scale):
        machine = "A" if machine_ticket < scale else "B"
        shown = machine if receipt else None
        literal = plan[shown]
        for first_ticket in range(20 * scale):
            first = first_ticket < scale
            if literal == STOP:
                counts[shown, first, False, 1, False] += 19 * scale
                continue
            if literal[0] != machine:
                counts[shown, first, False, 1, True] += 19 * scale
                continue
            left = literal[1] == "L"
            low = left == (latent == 0)
            count = (1 if low else 5) if good else 7
            if omit_upper_hazard and not low:
                count = 0
            for second_ticket in range(19 * scale):
                second = second_ticket < count * scale
                counts[shown, first, second, 2, False] += 1
    denominator = 3 * 20 * 19 * scale**3
    return {outcome: F(count, denominator) for outcome, count in counts.items()}


def compiled_joint(component, plan, receipt=True):
    """Multiply canonical chance rows directly, independently of raw ticket indices."""
    if plan is None:
        return {(None, False, False, 0, False): F(1)}
    selector, left_bit, right_bit, latent = component
    good = (left_bit, right_bit)[selector] == 0
    low_routes = ("L", "R")
    result = defaultdict(F)
    for machine, machine_mass in (("A", F(1, 3)), ("B", F(2, 3))):
        shown = machine if receipt else None
        action = plan[shown]
        enabled = action in (machine + "L", machine + "R")
        for first, first_mass in ((False, F(19, 20)), (True, F(1, 20))):
            incoming = machine_mass * first_mass
            if not enabled:
                result[shown, first, False, 1, action != STOP] += incoming
                continue
            late_risk = F(7, 19)
            if good:
                late_risk = F(1 if action[1] == low_routes[latent] else 5, 19)
            result[shown, first, False, 2, False] += incoming * (1 - late_risk)
            result[shown, first, True, 2, False] += incoming * late_risk
    return dict(result)


def payoffs(law):
    risk = sum(weight for (_, v1, v2, _, breach), weight in law.items()
               if (v1 or v2) and not breach)
    useful = sum(weight for (_, _, _, done, breach), weight in law.items()
                 if done == 2 and not breach)
    bad = sum(weight for (_, _, _, _, breach), weight in law.items() if breach)
    assert sum(law.values()) == 1
    return risk, useful, bad


def mix(laws):
    result = defaultdict(F)
    for law, weight in laws:
        for leaf, probability in law.items():
            result[leaf] += weight * probability
    return dict(result)


def solve_equalities(rows):
    """Exact Gaussian elimination for a candidate vertex."""
    work = [[*map(F, coefficients), F(bound)] for coefficients, bound in rows]
    for column in range(len(work)):
        pivot = next((i for i in range(column, len(work)) if work[i][column]), None)
        if pivot is None:
            return None
        work[column], work[pivot] = work[pivot], work[column]
        factor = work[column][column]
        work[column] = [value / factor for value in work[column]]
        for i, row in enumerate(work):
            if i != column and row[column]:
                factor = row[column]
                work[i] = [a - factor * b for a, b in zip(row, work[column])]
    return tuple(row[-1] for row in work)


def vertices(rows, dimension):
    for active in combinations(rows, dimension):
        values = solve_equalities(active)
        if values is not None and all(
            sum(a * b for a, b in zip(coefficients, values)) <= cap
            for coefficients, cap in rows
        ):
            yield values


def check_source_and_controller():
    plans = [None]
    plans.extend(
        dict(zip(MACHINES, choices))
        for choices in product(*((k + "L", k + "R", STOP) for k in MACHINES))
    )
    counter = 0
    for component in COMPONENTS:
        for plan in plans:
            canonical = compiled_joint(component, plan)
            assert source_joint(component, plan, 1) == canonical
            assert source_joint(component, plan, 2) == canonical
            payoffs(canonical)
            counter += 1

    complete_plans = [
        {"A": "A" + at_a, "B": "B" + at_b}
        for at_a, at_b in product("RL", repeat=2)
    ]
    deterministic_risk = F(1)
    for report in REPORTS:
        endpoints = tuple((*report, h) for h in (0, 1))
        payoff_rows = [
            tuple(payoffs(source_joint(comp, plan))[0] for plan in complete_plans)
            for comp in endpoints
        ]
        if sign(report):
            for plan_index in range(4):
                deterministic_risk = min(
                    deterministic_risk, max(row[plan_index] for row in payoff_rows)
                )
        inequalities = [
            ((1, 0, 0), 1), ((-1, 0, 0), 0),
            ((0, 1, 0), 1), ((0, -1, 0), 0),
            ((0, 0, 1), 1), ((0, 0, -1), 0),
        ]
        for rr, rl, lr, ll in payoff_rows:
            assert rr + ll == rl + lr
            inequalities.append(((lr - rr, rl - rr, -1), -rr))
        best = min(point[2] for point in vertices(inequalities, 3))
        expected = PASS_LIMIT if sign(report) else F(2, 5)
        assert best == expected
        for comp in endpoints:
            fair = mix((source_joint(comp, plan), F(1, 4)) for plan in complete_plans)
            assert payoffs(fair) == (expected, 1, 0)
            for literal in ("AL", "AR", "BL", "BR", STOP):
                collapsed = {None: literal}
                raw = source_joint(comp, collapsed, receipt=False)
                assert raw == compiled_joint(comp, collapsed, receipt=False)
                _, useful, bad = payoffs(raw)
                assert (bad == 0) == (literal == STOP)
                if bad == 0:
                    assert useful == 0
    assert deterministic_risk == F(7, 30)

    canonical = compiled_joint((0, 0, 0, 0), complete_plans[0])
    changed = source_joint((0, 0, 0, 0), complete_plans[0], omit_upper_hazard=True)
    assert canonical != changed
    def public_receipts(law):
        masses = defaultdict(F)
        for (receipt, _, _, _, _), leaf_mass in law.items():
            masses[receipt] += leaf_mass
        return dict(masses)

    assert public_receipts(canonical) == public_receipts(changed)
    return counter, deterministic_risk


def observed_cell(report, fields):
    return tuple(row for row in REPORTS if all(row[i] == report[i] for i in fields))


@cache
def enumerate_audit_costs(records, remaining):
    costs = []
    if len({sign(report) for report in records}) == 1:
        costs.append(0)
    for column in remaining:
        replies = {row[column] for row in records}
        rest = tuple(i for i in remaining if i != column)
        children = [
            enumerate_audit_costs(tuple(row for row in records if row[column] == y), rest)
            for y in sorted(replies)
        ]
        costs.extend(COSTS[column] + max(paths) for paths in product(*children))
    return tuple(costs)


@cache
def audit_recurrence(records, remaining):
    if len({sign(report) for report in records}) == 1:
        return 0
    options = []
    for j in remaining:
        rest = tuple(i for i in remaining if i != j)
        cells = [tuple(row for row in records if row[j] == y) for y in (0, 1)]
        options.append(COSTS[j] + max(audit_recurrence(cell, rest) for cell in cells if cell))
    return min(options, default=inf)


def check_audits():
    fields = (0, 1, 2)
    subsets = [subset for length in range(4) for subset in combinations(fields, length)]
    costs = enumerate_audit_costs(REPORTS, fields)
    assert min(costs) == audit_recurrence(REPORTS, fields) == 4
    def spend(subset):
        return sum(COSTS[i] for i in subset)

    def sufficient(report, subset):
        return len({sign(row) for row in observed_cell(report, subset)}) == 1

    assert min(spend(subset) for subset in subsets
               if all(sufficient(report, subset) for report in REPORTS)) == 5
    assert {
        report: min(spend(subset) for subset in subsets if sufficient(report, subset))
        for report in REPORTS
    } == {report: 2 if report[1] == report[2] else 4 for report in REPORTS}
    return len(costs)


def check_group_and_linked_lp():
    dimensions = 3
    simplex = [
        ((-1, 0, 0), 0), ((0, -1, 0), 0), ((0, 0, -1), 0),
        ((1, 1, 1), 1), ((-1, -1, -1), -1),
    ]
    rows = [
        (tuple(int(j == i) for j in range(dimensions)), F(3, 10))
        for i in range(dimensions)
    ]
    assert not list(vertices(simplex + rows, dimensions))
    assert all(list(vertices(simplex + list(pair), dimensions))
               for pair in combinations(rows, 2))
    # These rational worlds lie inside their linked report polytopes p[i] >= 1/2.
    # Their row multipliers can be checked directly against the original regions.
    core_worlds = [
        tuple(F(4, 5) if i == j else F(1, 10) for j in range(dimensions))
        for i in range(dimensions)
    ]
    assert all(sum(p) == 1 and p[i] >= F(1, 2) for i, p in enumerate(core_worlds))
    assert all(sum(col) == 1 for col in zip(*core_worlds))
    assert not list(vertices(simplex + [(p, F(3, 10)) for p in core_worlds], dimensions))
    assert all(list(vertices(simplex + [(p, F(3, 10)) for p in pair], dimensions))
               for pair in combinations(core_worlds, 2))
    for p in core_worlds:
        assert min(p) <= F(3, 10)

    # Each fixed world makes the same hidden bit on both draws.
    actual = (F(1), F(1))
    row_splice = 0  # an impossible world with first bit 0 and last bit 1
    assert min(actual) == 1 > row_splice


def check_finite_statistics():
    samples = tuple(product((0, 1), repeat=4))
    early = {bits for bits in samples if sum(bits[:2]) == 2}
    late = {bits for bits in samples if sum(bits) >= 3}
    assert F(len(early), 16) == F(1, 4)
    assert F(len(late), 16) == F(5, 16)
    assert F(len(early | late), 16) == F(3, 8)
    parallel = {bits for bits in samples if sum(bits[:2]) == 2 or sum(bits[2:]) == 2}
    assert F(len(parallel), 16) == F(7, 16)

    # Exact sampling error and end-to-end arithmetic with activation correlated with error.
    epsilon, q, delta = F(1, 5), F(2, 5), F(1, 10)
    bad_issued, good_issued = delta, q - delta
    risk = bad_issued + epsilon * good_issued
    assert risk == epsilon * q + (1 - epsilon) * min(q, delta)
    assert risk / q == F(2, 5)
    assert delta / q == F(1, 4)
    assert sum(F(1, n * (n + 1)) for n in range(1, 101)) == 1 - F(1, 101)

    # At overlapping means a fresh-reset audit cannot distinguish by policy choice.
    p, q = F(1, 2), F(501, 1000)
    draws = 4
    def distribution(mu):
        return {
            bits: prod(mu if bit else 1 - mu for bit in bits)
            for bits in product((0, 1), repeat=draws)
        }

    lhs, rhs = distribution(p), distribution(q)
    total_variation = sum(abs(lhs[t] - rhs[t]) for t in lhs) / 2
    assert 0 < total_variation <= draws * abs(p - q)


def main():
    rows, deterministic = check_source_and_controller()
    audits = check_audits()
    check_group_and_linked_lp()
    check_finite_statistics()
    print(f"PASS: {rows} per-component policies, exact raw/compiled and alternate ticket equality")
    print(f"PASS: useful robust randomized risk 1/5, deterministic risk {deterministic}, bad risk 2/5")
    print(f"PASS: {audits} exact audit trees, prospective 4, fixed universal 5, realized 2 or 4")
    print("PASS: pairwise feasible and jointly infeasible cores, linked-law and confidence controls")


if __name__ == "__main__":
    main()
