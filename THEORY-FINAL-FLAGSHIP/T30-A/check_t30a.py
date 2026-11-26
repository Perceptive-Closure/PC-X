"""Exact checks for the guarded T30.A source fixture and acquisition formulas."""

from collections import Counter
from dataclasses import dataclass, replace
from fractions import Fraction
from functools import cache
from itertools import product
from math import comb


F = Fraction
SCORE_PRIOR = F(3, 4)
PROBES = ((1, F(1, 2)), (3, F(1)))
PROBE_LITERALS = ("stock/economy", "stock/full")
MONITOR = "monitor/report"
WORD = tuple(range(4))
ERASURE = "*"


@dataclass(frozen=True)
class Type:
    binding: str
    bad_words: frozenset[int]
    namespace: str


TYPES = (
    Type("positive", frozenset({0}), "k0"),
    Type("negative", frozenset({0, 1, 2}), "k1"),
)


@dataclass(frozen=True)
class State:
    kind: Type
    memory: int = 0
    stage: int = 0
    phase: str = "evaluation"
    paid: int = 0
    stock_orders_done: int = 0

    def frozen_projection(self):
        return (self.kind.binding, self.kind.namespace, ("count", "dispatch"))


def inventory_count(stage):
    return 10 + stage % 7


def audit_source(state, literal, flag, private_nonce, reveal_word, u):
    assert state.phase == "evaluation"
    memory = state.memory ^ private_nonce ^ flag
    advanced = replace(state, memory=memory, stage=state.stage + 1)
    nuisance = (advanced.stage, flag)
    if literal == MONITOR:
        return advanced, None, nuisance
    i = PROBE_LITERALS.index(literal)
    price, _ = PROBES[i]
    after = replace(
        advanced,
        paid=state.paid + price,
        stock_orders_done=state.stock_orders_done + 1,
    )
    actual_stock_record = (state.stage, inventory_count(state.stage))
    reveal = (literal == "stock/full" or reveal_word == 1)
    authenticated = int(u in state.kind.bad_words) if reveal else ERASURE
    return after, authenticated, (nuisance, actual_stock_record)


def activate(state, direct=False):
    assert state.phase == "evaluation"
    return replace(state, phase="direct" if direct else "issued")


def deploy_source(state, proposal, u, z, *, wider=False):
    assert state.phase in ("direct", "issued")
    allowed = (0, 1, 2) if wider and state.kind == TYPES[0] else (0, 1)
    if proposal not in allowed:
        raise ValueError("proposal outside the checked physical guard")
    actual_order = state.stage
    intended = inventory_count(actual_order)
    finalize_correct = u not in state.kind.bad_words and z >= proposal
    written = intended if finalize_correct else intended + 1
    return replace(state, phase="finished"), (actual_order, written)


def genuine_event(artifact):
    order, written = artifact
    completed = int(written == inventory_count(order))
    return (1 - completed, completed)


def paired_audit_shapes(kind, memory, literal, flag):
    """Compile actual local rows and conditional ordinary successor records."""
    receipt_mass = Counter()
    conditional = {}
    start = State(kind, memory)
    for private_nonce, reveal_word, u in product(range(2), range(2), WORD):
        after, receipt, record = audit_source(
            start, literal, flag, private_nonce, reveal_word, u
        )
        receipt_mass[receipt] += 1
        observable_and_carry = (
            record, after.memory, after.stage, after.paid, after.stock_orders_done
        )
        conditional.setdefault(receipt, Counter())[observable_and_carry] += 1
        assert after.frozen_projection() == start.frozen_projection()
        assert after.phase == "evaluation"
        if literal in PROBE_LITERALS:
            assert record[1] == (start.stage, inventory_count(start.stage))
            assert after.stock_orders_done == start.stock_orders_done + 1
    conditional = {
        y: {row: F(count, receipt_mass[y]) for row, count in mass.items()}
        for y, mass in conditional.items()
    }
    return {y: F(count, 16) for y, count in receipt_mass.items()}, conditional


def check_fixture():
    assert {(kind.binding, kind.namespace) for kind in TYPES} == {
        ("positive", "k0"), ("negative", "k1")
    }
    initial_mass = {kind.binding: (0, 0, 0) for kind in TYPES}
    assert len(set(initial_mass.values())) == 1

    case_count = 0
    for memory, literal, flag in product(range(2), (*PROBE_LITERALS, MONITOR), range(2)):
        rows = [paired_audit_shapes(kind, memory, literal, flag) for kind in TYPES]
        assert rows[0][1] == rows[1][1]
        for kind, (receipt_mass, _) in zip(TYPES, rows, strict=True):
            if literal == MONITOR:
                assert receipt_mass == {None: F(1)}
                continue
            i = PROBE_LITERALS.index(literal)
            p = F(len(kind.bad_words), len(WORD))
            _, r = PROBES[i]
            expected = {0: r * (1 - p), 1: r * p, ERASURE: 1 - r}
            assert receipt_mass == {y: mass for y, mass in expected.items() if mass}
        case_count += 1

    ranges = {}
    cuts = [(*cut, False) for cut in product(TYPES, ("direct", "issued"), range(2), range(2))]
    cuts.extend((TYPES[0], phase, memory, 2, True) for phase, memory in product(("direct", "issued"), range(2)))
    for kind, phase, memory, proposal, wider in cuts:
        source = activate(State(kind, memory), direct=(phase == "direct"))
        risk = 0
        for u, z in product(WORD, WORD):
            finalized, artifact = deploy_source(source, proposal, u, z, wider=wider)
            violation, completed = genuine_event(artifact)
            assert (violation, completed) in ((0, 1), (1, 0))
            assert finalized.frozen_projection() == source.frozen_projection()
            risk += violation
        fraction = F(risk, 16)
        p = F(len(kind.bad_words), 4)
        assert fraction == p + (1 - p) * F(proposal, 4)
        ranges.setdefault(kind.binding, set()).add(fraction)
    assert ranges["positive"] == {F(1, 4), F(7, 16), F(5, 8)}
    assert ranges["negative"] == {F(3, 4), F(13, 16)}
    try:
        deploy_source(activate(State(TYPES[0])), 2, 0, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("base fixture admitted the wider proposal")

    warm, _, _ = audit_source(State(TYPES[0]), MONITOR, 0, 1, 0, 0)
    assert warm.memory == 1
    direct = activate(State(TYPES[0]), direct=True)
    issued = activate(warm)
    assert issued.memory == 1
    risks = []
    for state in (direct, issued):
        proposal = state.memory if state.phase == "issued" else 0
        violations = sum(
            genuine_event(deploy_source(state, proposal, u, z)[1])[0]
            for u, z in product(WORD, WORD)
        )
        risks.append(F(violations, 16))
    assert risks == [F(1, 4), F(7, 16)]
    assert F(7, 16) < F(1, 2) < F(5, 8)
    print(f"source: {case_count} pair rows plus {len(cuts)} deployment-cut rows match exactly")


def protected_law(bit_mean, rate):
    return (rate * (1 - bit_mean), rate * bit_mean, 1 - rate)


def posterior_dp(q, catalog):
    ratio = q / (1 - q)

    @cache
    def value(budget, moves, score):
        odds = ratio ** score
        high_posterior = odds / (1 + odds)
        best = min(high_posterior, 1 - high_posterior)
        if moves == 0:
            return best
        next_binary_mean = high_posterior * q + (1 - high_posterior) * (1 - q)
        for price, rate in catalog:
            if price > budget:
                continue
            b = budget - price
            n = moves - 1
            option = (1 - rate) * value(b, n, score)
            option += rate * (
                next_binary_mean * value(b, n, score + 1)
                + (1 - next_binary_mean) * value(b, n, score - 1)
            )
            best = min(best, option)
        return best

    return value


def full_tree_value(q, catalog, budget, moves):
    """Enumerate full history branches using unnormalized joint law masses."""
    initial = (F(1, 2), F(1, 2))

    def expand(masses, remaining, depth):
        errors = [min(masses)]
        if depth == 0:
            return errors[0]
        for price, rate in catalog:
            if price > remaining:
                continue
            joint_lows = protected_law(1 - q, rate)
            joint_highs = protected_law(q, rate)
            losses = []
            for low, high in zip(joint_lows, joint_highs, strict=True):
                child = (low * masses[0], high * masses[1])
                if any(child):
                    losses.append(expand(child, remaining - price, depth - 1))
            errors.append(sum(losses))
        return min(errors)

    return expand(initial, budget, moves)


def enumerate_pure_vectors(q, catalog):
    """Enumerate deterministic terminal rules and probe trees as risk pairs."""

    @cache
    def vectors(budget, moves):
        results = {(F(0), F(1)), (F(1), F(0))}
        if not moves:
            return results
        for price, rate in catalog:
            if price > budget:
                continue
            child_vectors = vectors(budget - price, moves - 1)
            rows = tuple(
                (low, high)
                for low, high in zip(
                    protected_law(1 - q, rate), protected_law(q, rate), strict=True
                )
                if low or high
            )
            for children in product(child_vectors, repeat=len(rows)):
                result = tuple(
                    sum(row[k] * child[k] for row, child in zip(rows, children, strict=True))
                    for k in range(2)
                )
                results.add(result)
        return results

    return vectors


def binomial_mass(n, k, p):
    return comb(n, k) * p**k * (1 - p) ** (n - k)


def majority_error(q, n):
    errors = sum(binomial_mass(n, k, q) for k in range((n + 1) // 2))
    if not n % 2:
        errors += binomial_mass(n, n // 2, q) / 2
    return errors


def fixed_schedule_error(q, rates):
    reveal_count = [F(1)]
    for rate in rates:
        new = [F(0)] * (len(reveal_count) + 1)
        for count, mass in enumerate(reveal_count):
            new[count] += mass * (1 - rate)
            new[count + 1] += mass * rate
        reveal_count = new
    return sum(mass * majority_error(q, count) for count, mass in enumerate(reveal_count))


def check_finite():
    matched = 0
    for q, catalog in product(
        (F(2, 3), F(3, 4), F(4, 5)),
        (PROBES, ((1, F(0)), (2, F(0))), ((2, F(1, 3)), (2, F(3, 4)))),
    ):
        dp = posterior_dp(q, catalog)
        pure = enumerate_pure_vectors(q, catalog)
        for budget, moves in product(range(9), range(4)):
            exact = dp(budget, moves, 0)
            assert exact == full_tree_value(q, catalog, budget, moves)
            if moves <= 2:
                risks = pure(budget, moves)
                assert all((high, low) in risks for low, high in risks)
                best_bayes = min((low + high) / 2 for low, high in risks)
                assert exact == best_bayes
            if len({price for price, _ in catalog}) == 1:
                price = catalog[0][0]
                n = min(moves, budget // price)
                r_star = max(rate for _, rate in catalog)
                assert exact == fixed_schedule_error(q, (r_star,) * n)
            matched += 1

    dp = posterior_dp(SCORE_PRIOR, PROBES)
    assert dp(6, 2, 0) == F(1, 4)
    assert dp(4, 3, 0) == F(61, 256)
    schedules = [
        (F(1, 2),) * economy + (F(1),) * full
        for economy, full in product(range(4), range(2))
        if economy + full <= 3 and economy + 3 * full <= 4
    ]
    assert min(fixed_schedule_error(SCORE_PRIOR, r) for r in schedules) == F(1, 4)
    assert min(max(x) for x in enumerate_pure_vectors(SCORE_PRIOR, PROBES)(0, 0)) == 1
    assert dp(0, 0, 0) == F(1, 2)
    print(f"hard cost: {matched} tree comparisons, adaptive 61/256 vs static 1/4")


def solve_linear(rows):
    """Exact Gaussian elimination for the small absorbing hitting systems."""
    dimension = len(rows)
    for column in range(dimension):
        pivot = next(index for index in range(column, dimension) if rows[index][column])
        rows[column], rows[pivot] = rows[pivot], rows[column]
        divisor = rows[column][column]
        rows[column] = [entry / divisor for entry in rows[column]]
        for row_index in range(dimension):
            if row_index == column:
                continue
            multiplier = rows[row_index][column]
            if multiplier:
                rows[row_index] = [
                    current - multiplier * pivot_entry
                    for current, pivot_entry in zip(
                        rows[row_index], rows[column], strict=True
                    )
                ]
    return [row[-1] for row in rows]


def hitting_measure(q, r, radius, solve_for_time):
    states = tuple(range(-radius + 1, radius))
    rows = []
    for state in states:
        row = [F(int(position == state)) for position in states]
        right = F(int(solve_for_time))
        for destination, mass in (
            (state, 1 - r), (state + 1, r * q), (state - 1, r * (1 - q))
        ):
            if destination in states:
                row[states.index(destination)] -= mass
            elif not solve_for_time and destination == -radius:
                right += mass
        rows.append([*row, right])
    return solve_linear(rows)[states.index(0)]


def posterior_error(q, boundary):
    return 1 / (1 + (q / (1 - q)) ** boundary)


def boundary_receipts(q, boundary):
    return boundary * (1 - 2 * posterior_error(q, boundary)) / (2 * q - 1)


def check_expected():
    for q, r, radius in product(
        (F(2, 3), F(3, 4), F(4, 5)), (F(1, 3), F(1, 2), F(1)), range(1, 7)
    ):
        error = hitting_measure(q, r, radius, solve_for_time=False)
        time = hitting_measure(q, r, radius, solve_for_time=True)
        assert error == posterior_error(q, radius)
        assert r * time == boundary_receipts(q, radius)

    for q, radius in product((F(2, 3), F(3, 4), F(4, 5)), range(8)):
        e0 = posterior_error(q, radius)
        e1 = posterior_error(q, radius + 1)
        n0 = boundary_receipts(q, radius)
        n1 = boundary_receipts(q, radius + 1)
        slope = (n1 - n0) / (e1 - e0)
        assert slope < 0
        for other in range(13):
            bound = n0 + slope * (posterior_error(q, other) - e0)
            assert boundary_receipts(q, other) >= bound

    q = SCORE_PRIOR
    assert posterior_error(q, 2) == F(1, 10)
    assert 2 * boundary_receipts(q, 2) == F(32, 5)
    mixed = F(2, 3) * boundary_receipts(q, 1) + F(1, 3) * boundary_receipts(q, 2)
    assert 2 * mixed == F(52, 15)
    print("expected cost: 54 exact absorbing-chain checks plus adjacent secant tests")


def check_source_failures():
    for kind in TYPES:
        state = activate(State(kind))
        effective_outcomes = [
            genuine_event(deploy_source(state, 1, u, z)[1])[0]
            for u, z in product(WORD, WORD)
            if u not in kind.bad_words
        ]
        assert F(sum(effective_outcomes), len(effective_outcomes)) == F(1, 4)
        joint = [
            genuine_event(deploy_source(state, 1, u, z)[1])[0]
            for u, z in product(WORD, WORD)
        ]
        assert sum(joint) > 4
    safe_counterfeit = {ERASURE: F(1, 2), 1: F(1, 8), 0: F(3, 8)}
    low, _ = paired_audit_shapes(TYPES[0], 0, PROBE_LITERALS[0], 0)
    high, _ = paired_audit_shapes(TYPES[1], 0, PROBE_LITERALS[0], 0)
    assert safe_counterfeit == low and safe_counterfeit != high
    late_word_proposal = [z in {z} for z in WORD]
    assert all(late_word_proposal)
    print("controls: omitted support, replaced instrument, and proposal-after-draw")


if __name__ == "__main__":
    check_fixture()
    check_finite()
    check_expected()
    check_source_failures()
