"""Exact finite mathematical fixtures for the M04 strategic-audit statements."""

from fractions import Fraction as F
from functools import cache
from itertools import combinations, product
import json
import math


def solve_equations(rows):
    """Return the exact solution to a square system, or None if singular."""
    system = [list(map(F, row)) for row in rows]
    size = len(system)
    for col in range(size):
        pivot = next((i for i in range(col, size) if system[i][col]), None)
        if pivot is None:
            return None
        system[col], system[pivot] = system[pivot], system[col]
        divider = system[col][col]
        system[col] = [value / divider for value in system[col]]
        for row in range(size):
            if row != col:
                factor = system[row][col]
                system[row] = [a - factor * b for a, b in zip(system[row], system[col])]
    return tuple(row[-1] for row in system)


def exact_minimax(classes):
    """Minimize maximum error on a two-symbol record by vertex enumeration."""
    positives, negatives = classes
    bounds = [(1, 0, 0, 1), (-1, 0, 0, 0), (0, 1, 0, 1), (0, -1, 0, 0),
              (0, 0, 1, 1), (0, 0, -1, 0)]
    bounds += [(-p0, -p1, -1, -1) for p0, p1 in positives]
    bounds += [(q0, q1, -1, 0) for q0, q1 in negatives]
    solutions = []
    for tight in combinations(bounds, 3):
        candidate = solve_equations(tight)
        if candidate is None:
            continue
        x, y, e = candidate
        if all(a * x + b * y + c * e <= d for a, b, c, d in bounds):
            solutions.append(candidate)
    return min(solutions, key=lambda vertex: vertex[2])


def overlap(positive, negative, prior):
    return sum(min(prior * p, (1 - prior) * q) for p, q in zip(positive, negative))


def composite_cases():
    positive = [(F(1), F(0)), (F(0), F(1))]
    negative = [(F(1, 2), F(1, 2))]
    assert all(sum(abs(a - b) for a, b in zip(p, negative[0])) / 2 == F(1, 2)
               for p in positive)
    assert exact_minimax((positive, negative))[2] == F(1, 2)
    assert overlap(negative[0], negative[0], F(1, 2)) == F(1, 2)

    p, q = (F(1), F(0)), (F(1, 3), F(2, 3))
    assert exact_minimax(([p], [q])) == (F(3, 4), F(0), F(1, 4))
    breakpoints = {F(0), F(1)} | {q_i / (p_i + q_i) for p_i, q_i in zip(p, q)}
    values = [(overlap(p, q, prior), prior) for prior in breakpoints]
    assert max(values) == (F(1, 4), F(1, 4))
    assert overlap(p, q, F(1, 2)) == F(1, 6)

    support = [{(0, mode), (1, 1 - mode)} for mode in (0, 1)]
    assert not support[0] & support[1]
    for coordinate in (0, 1):
        assert {row[coordinate] for row in support[0]} == {row[coordinate] for row in support[1]}
    return {"intersection_minimax": "1/2", "disjoint_minimax": "1/4",
            "disjoint_equal_prior": "1/6", "full_record_supports_disjoint": True}


def adaptive_cases():
    worlds = tuple(product((0, 1), repeat=2))

    def reply(label, cue, query):
        return label if query == cue else 2

    # A plan gives a probe per cue and a label per cue/response pair.
    plans = list(product((0, 1), repeat=8))

    def correct(plan, label, cue):
        query = plan[cue]
        return plan[2 + 3 * cue + reply(label, cue, query)] == label

    winning = [plan for plan in plans if all(correct(plan, *world) for world in worlds)]
    assert winning and all(plan[:2] == (0, 1) for plan in winning)

    # Exact sequence weights from a private mixture, and an independent leaf computation.
    mixture = ((F(1, 3), (0, 1, 0, 1, 0, 0, 1, 0)),
               (F(2, 3), (1, 0, 0, 1, 1, 0, 1, 1)))

    def probe_weight(cue, query):
        return sum(w for w, plan in mixture if plan[cue] == query)

    def choice_weight(cue, query, outcome, decision):
        return sum(
            w for w, plan in mixture
            if plan[cue] == query and plan[2 + 3 * cue + outcome] == decision
        )

    for label, cue in worlds:
        assert sum(probe_weight(cue, q) for q in (0, 1)) == 1
        for query, outcome in product((0, 1), range(3)):
            assert sum(choice_weight(cue, query, outcome, d) for d in (0, 1)) == (
                probe_weight(cue, query)
            )
        direct = sum(w for w, plan in mixture if correct(plan, label, cue))
        via_flow = sum(choice_weight(cue, q, reply(label, cue, q), label) for q in (0, 1))
        assert direct == via_flow

    blind_priors = [F(i, 8) for i in range(9)]
    blind_errors = [max(p, 1 - p) / 2 for p in blind_priors]
    assert min(blind_errors) == F(1, 4)

    fair_bits = (0, 1)
    chance_failures = [F(sum(coin == guess for coin in fair_bits), 2) for guess in fair_bits]
    assert max(chance_failures) / 2 == F(1, 4)
    anticipating_guesses = {0: 0, 1: 1}
    assert F(sum(coin == anticipating_guesses[coin] for coin in fair_bits), 2) == 1
    return {"winning_adaptive_pure_plans": len(winning), "open_loop_minimax": "1/4",
            "nonanticipating_minimax": "1/4", "anticipating_minimax": "1/2"}


def interval_cases():
    prefixes = [prefix for n in range(3) for prefix in product((0, 1), repeat=n)]
    worst_errors = []
    for label, extremes in ((0, (F(0), F(1, 4))), (1, (F(3, 4), F(1)))):
        def error(prefix):
            return int(int(sum(prefix) >= 2) != label)

        worst_by_enumeration = F(0)
        for endpoints in product(extremes, repeat=len(prefixes)):
            means = dict(zip(prefixes, endpoints))
            chance = F(0)
            for bits in product((0, 1), repeat=3):
                chance += error(bits) * math.prod(
                    means[bits[:i]] if bit else 1 - means[bits[:i]]
                    for i, bit in enumerate(bits)
                )
            worst_by_enumeration = max(worst_by_enumeration, chance)

        @cache
        def recurrence(prefix):
            if len(prefix) == 3:
                return error(prefix)
            return max((1 - p) * recurrence(prefix + (0,)) + p * recurrence(prefix + (1,))
                       for p in extremes)

        assert recurrence(()) == worst_by_enumeration == F(5, 32)
        worst_errors.append(str(worst_by_enumeration))
    return {"history_contingent_plans_per_class": 128, "class_errors": worst_errors}


def stopped_cases():
    p = F(1, 3)
    geometric = {}
    survival = F(1)
    for horizon in range(1, 13):
        survival *= 1 - p
        optimal = (1 - p) ** horizon / 2
        assert optimal == survival / 2 > 0
        assert optimal <= F(3, horizon + 1)
        geometric[str(horizon)] = str(optimal)

    prior = F(1, 2**33)
    mixture_ratio = 1 + prior * (2**32 - 1)
    assert mixture_ratio < F(3, 2) < 10
    histogram_radius = math.sqrt(math.log(40) / 64)
    assert 2 * histogram_radius < 0.5

    required_probe_probability = 6 * (F(1, 2) - F(2, 5))
    assert required_probe_probability == F(3, 5)
    assert (1 - required_probe_probability) / 2 + required_probe_probability / 3 == F(2, 5)
    kl_lower_bound = (F(1, 5) * math.log(1.5)) / (F(1, 3) * math.log(2))
    assert kl_lower_bound < required_probe_probability
    return {
        "one_probe_worst_expected_optimum": str(required_probe_probability),
        "geometric_expected_probes": "3",
        "geometric_cap_errors": geometric,
        "mixture_ratio_at_histogram_deadline": str(mixture_ratio),
    }


def main():
    result = {"adaptive": adaptive_cases(), "composite": composite_cases(),
              "intervals": interval_cases(), "stopped": stopped_cases()}
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
