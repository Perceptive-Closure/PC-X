"""Exact conditional-law, cost and design checks before custody."""

from collections import defaultdict
from copy import copy
from fractions import Fraction
from functools import cache
from itertools import combinations, product
from math import comb, exp, inf, log

import audit
from contract import ADMITTED, LEFT, RECIPES, RIGHT, ROSTER, SPEC, TICKETS, UNITS, digest
from model import THRESHOLD, right_probability, risks, target
from sandbox import RecheckStation, SortingPolicy


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


def replay_policy(fixture, history):
    policy = SortingPolicy(fixture)
    for reset, cue, context, trim, tray in history:
        if reset:
            policy.reset()
        ticket = 0 if tray == RIGHT else TICKETS - 1
        actual = policy.place(cue, context, trim, ticket)
        require(actual == tray, "Claimed positive-support history is unreachable")
    return policy


def runtime_right(fixture, history, action):
    reset, cue, context, trim = action
    policy = replay_policy(fixture, history)
    if reset:
        policy.reset()
    return sum(copy(policy).place(cue, context, trim, ticket) == RIGHT for ticket in range(TICKETS))


def check_conditional(fixture, history, action):
    reset, cue, context, _ = action
    previous = None if reset or not history else history[-1][-1]
    observed_count = runtime_right(fixture, history, action)
    require(Fraction(observed_count, TICKETS) == right_probability(fixture, cue, context, previous),
            "Runtime and analytical conditional laws differ")
    require(0 < observed_count < TICKETS, "A declared positive outcome is impossible")
    return observed_count


def law_signature(fixture, regime):
    cues = [SPEC["comparison_cue"]] if regime == "fixed_blue" else SPEC["cues"]
    reset_choices = (False,) if regime == "carry" else (False, True)
    actions = list(product(reset_choices, cues, SPEC["contexts"], SPEC["trims"]))
    signature = bytearray()
    frontier = [()]
    if regime == "carry":
        warm_up = (False, *SPEC["warm_up"])
        signature.append(check_conditional(fixture, (), warm_up))
        frontier = [((*warm_up, tray),) for tray in (LEFT, RIGHT)]
    for index in range(SPEC["horizon"]):
        following = []
        for history in frontier:
            for action in actions:
                signature.append(check_conditional(fixture, history, action))
                if index + 1 < SPEC["horizon"]:
                    following.extend(history + ((*action, tray),) for tray in (LEFT, RIGHT))
        frontier = following
    return bytes(signature)


def fixture_id(fixture):
    return f"{fixture.mode}:{fixture.name}"


def law_report():
    all_regimes = {}
    for regime in ("fixed_blue", "full", "carry"):
        signatures = {fixture: law_signature(fixture, regime) for fixture in ROSTER}
        partitions = defaultdict(list)
        for fixture, signature in signatures.items():
            partitions[signature].append(fixture)
        witnesses = []
        for first, second in combinations(ADMITTED, 2):
            if signatures[first] == signatures[second] and target(first) != target(second):
                witnesses.append([fixture_id(first), fixture_id(second)])
        for fixture in ROSTER:
            if fixture.mode == "shift":
                anchor = next(item for item in ADMITTED if item.name == fixture.name)
                require(signatures[anchor] == signatures[fixture], f"Transfer shift changed {regime} law")
                require(target(anchor) != target(fixture), "Transfer shift failed to change the target")
        require(len(witnesses) == (0 if regime == "full" else len(SPEC["contexts"])),
                f"Unexpected target-class partition for {regime}")
        all_regimes[regime] = {
            "checked_conditional_laws": sum(len(signature) for signature in signatures.values()),
            "partitions": [
                {"members": [fixture_id(fixture) for fixture in fixtures], "law_sha256": digest(signature)}
                for signature, fixtures in partitions.items()
            ],
            "admitted_target_distinct_witnesses": witnesses,
        }
    return all_regimes


def runtime_risk(fixture, cue, recipe):
    station = RecheckStation(fixture, cue)
    accept = {
        tray: sum(not station.score(tray, ticket) for ticket in range(TICKETS))
        for tray in (LEFT, RIGHT)
    }
    counts = {(): 1}
    for context in recipe:
        action = (False, cue, context, "plain")
        following = {}
        for history, mass in counts.items():
            right = runtime_right(fixture, history, action)
            for tray, count in ((LEFT, TICKETS - right), (RIGHT, right)):
                following[history + ((*action, tray),)] = mass * count * accept[tray]
        counts = following
    return 1 - Fraction(sum(counts.values()), TICKETS ** (2 * len(recipe)))


def risk_report():
    report = {}
    clearance_required = 2 * Fraction(SPEC["native"]["radius"])
    for fixture in ROSTER:
        report[fixture_id(fixture)] = {}
        for cue in SPEC["cues"]:
            theoretical = risks(fixture, cue)
            for name, recipe in RECIPES.items():
                require(theoretical[name] == runtime_risk(fixture, cue, recipe), "Independent risk mismatch")
            clearance = abs(max(theoretical.values()) - THRESHOLD)
            if fixture in ADMITTED:
                require(clearance > clearance_required, "Prespecified power check failed")
            if cue == SPEC["comparison_cue"] and fixture in ADMITTED:
                require(target(fixture, cue) == "MEETS", "The fixed-cue extrapolation control changed")
            report[fixture_id(fixture)][cue] = {
                "risks": {name: str(risk) for name, risk in theoretical.items()},
                "threshold_clearance": str(clearance),
                "target": target(fixture, cue),
            }
    return report


def static_cost():
    pairs = [(i, j) for i, j in combinations(audit.CANDIDATES, 2) if audit.TARGETS[i] != audit.TARGETS[j]]
    sufficient = []
    for size in range(len(audit.ALL) + 1):
        for subset in combinations(audit.ALL, size):
            signatures = defaultdict(set)
            for i in audit.CANDIDATES:
                signatures[tuple(audit.CHANCES[i][q] for q in subset)].add(audit.TARGETS[i])
            by_partition = all(len(values) == 1 for values in signatures.values())
            by_pairs = all(any(audit.CHANCES[i][q] != audit.CHANCES[j][q] for q in subset) for i, j in pairs)
            require(by_partition == by_pairs, "Static law certificates disagree")
            if by_partition:
                sufficient.append((sum(audit.QUERIES[q].cost for q in subset), subset))
    return min(sufficient)


def affordable(history, budget):
    possible = [
        i for i in audit.CANDIDATES
        if all(audit.CHANCES[i][q] == response for q, response in history)
    ]
    if not possible:
        return False
    labels = {audit.TARGETS[i] for i in possible}
    if len(labels) == 1:
        return True
    acquired = {query for query, _ in history}
    for q, query in enumerate(audit.QUERIES):
        if q in acquired or query.cost > budget:
            continue
        answers = {audit.CHANCES[i][q] for i in possible}
        if all(affordable(history + ((q, response),), budget - query.cost) for response in answers):
            return True
    return False


def law_costs():
    optimum, first = audit.minimax(audit.CANDIDATES, audit.ALL)
    static, subset = static_cost()
    require(affordable((), optimum) and not affordable((), optimum - 1), "Independent minimax check failed")
    fixed_blue, _ = audit.minimax(audit.CANDIDATES, audit.BLUE)
    require(fixed_blue == inf, "A fixed-cue law identified the target")
    per_profile = {}
    for profile, fixture in enumerate(ADMITTED):
        candidates, remaining = audit.CANDIDATES, audit.ALL
        path = []
        while choices := audit.query_choices("primary", candidates, remaining):
            q = choices[0]
            p = audit.CHANCES[profile][q]
            path.append([audit.QUERIES[q].name, str(p)])
            candidates = tuple(i for i in candidates if audit.CHANCES[i][q] == p)
            remaining = audit.exclude(remaining, q)
        require(audit.decision(candidates)[1] == target(fixture), "Exact replay gave an invalid target")
        cost_by_name = {query.name: query.cost for query in audit.QUERIES}
        per_profile[fixture.name] = {"path": path, "cost": sum(cost_by_name[name] for name, _ in path)}
    return {
        "minimum_static": static,
        "static_queries": [audit.QUERIES[q].name for q in subset],
        "adaptive_minimax": optimum,
        "adaptive_uniform_expected": str(Fraction(sum(row["cost"] for row in per_profile.values()), len(ADMITTED))),
        "maximum_acquisition_cost_per_unit": optimum * audit.N,
        "first_action": audit.QUERIES[first].name,
        "per_profile": per_profile,
    }


@cache
def binomial_classes(profile, query):
    p = audit.CHANCES[profile][query]
    numerator, denominator = p.numerator, p.denominator
    counts = defaultdict(int)
    for right in range(audit.N + 1):
        compatible = audit.retained(audit.CANDIDATES, query, right)
        counts[compatible] += comb(audit.N, right) * numerator**right * (denominator - numerator)**(audit.N - right)
    return {
        compatible: Fraction(weight, denominator**audit.N)
        for compatible, weight in counts.items()
    }


@cache
def cost_distribution(profile, method, candidates, remaining):
    choices = audit.query_choices(method, candidates, remaining)
    if not choices:
        status, verdict = audit.decision(candidates)
        return {(status, verdict, 0): Fraction(1)}
    distribution = defaultdict(Fraction)
    for q in choices:
        rest = audit.exclude(remaining, q)
        for allowed, probability in binomial_classes(profile, q).items():
            updated = tuple(i for i in candidates if i in allowed)
            for (status, verdict, future), mass in cost_distribution(profile, method, updated, rest).items():
                cost = future + audit.N * audit.QUERIES[q].cost
                distribution[status, verdict, cost] += mass * probability / len(choices)
    return dict(distribution)


def binomial_report():
    summary = {}
    for method in audit.METHODS:
        expected = []
        worst = []
        rows = {}
        for i, fixture in enumerate(ADMITTED):
            dist = cost_distribution(i, method, audit.CANDIDATES, audit.starting_queries(method))
            require(sum(dist.values()) == 1, "Non-normalized acquisition cost law")
            mean = sum(cost * mass for (_, _, cost), mass in dist.items())
            maximum = max(cost for (_, _, cost), mass in dist.items() if mass > 0)
            correct = sum(mass for (_, verdict, _), mass in dist.items() if verdict == audit.TARGETS[i])
            wrong = sum(mass for (_, verdict, _), mass in dist.items() if verdict not in (None, audit.TARGETS[i]))
            inconsistent = sum(mass for (status, _, _), mass in dist.items() if status == audit.INCONSISTENT)
            abstain = 1 - correct - wrong - inconsistent
            rows[fixture.name] = {
                "expected": float(mean), "expected_exact": str(mean), "worst": maximum,
                "p_correct_certificate": float(correct), "p_wrong_certificate": float(wrong),
                "p_inconsistent": float(inconsistent), "p_abstain": float(abstain),
            }
            expected.append(mean)
            worst.append(maximum)
        summary[method] = {
            "uniform_expected": float(sum(expected) / len(expected)),
            "worst_positive_support": max(worst),
            "per_profile": rows,
        }
    return summary


def binary_kl(p, q):
    return float(p) * log(float(p / q)) + float(1 - p) * log(float((1 - p) / (1 - q)))


def vertex_minimum(gaps, required, costs):
    """A two-constraint nonnegative LP has a minimizing support of at most two."""
    values = []
    for q, (left, right) in enumerate(zip(*gaps, strict=True)):
        if left > 0 and right > 0:
            values.append(costs[q] * max(required / left, required / right))
    for i, j in combinations(range(len(costs)), 2):
        a, b = gaps[0][i], gaps[0][j]
        c, d = gaps[1][i], gaps[1][j]
        determinant = a * d - b * c
        if abs(determinant) > 1e-12:
            x = required * (d - b) / determinant
            y = required * (a - c) / determinant
            if x >= 0 and y >= 0:
                values.append(costs[i] * x + costs[j] * y)
    return min(values)


def information_bounds():
    costs = [q.cost for q in audit.QUERIES]
    delta = Fraction(SPEC["alpha"])
    required = binary_kl(1 - delta, delta)
    result = {}
    for i, fixture in enumerate(ADMITTED):
        same, other = sorted(
            (j for j in audit.CANDIDATES if audit.TARGETS[j] != audit.TARGETS[i]),
            key=lambda j: ADMITTED[j].key != fixture.key,
        )
        gaps = [
            [binary_kl(p, q) for p, q in zip(audit.CHANCES[i], audit.CHANCES[rival], strict=True)]
            for rival in (same, other)
        ]
        informative, = [q for q, part in enumerate(gaps[0]) if part > 0]
        must_buy = required / gaps[0][informative]
        missing = max(0, required - must_buy * gaps[1][informative])
        best_value = max(part / cost for part, cost in zip(gaps[1], costs, strict=True))
        formula = costs[informative] * must_buy + missing / best_value
        # In this menu, increasing the required action cannot improve the closed form.
        require(missing < 1e-12 or gaps[1][informative] == 0, "Unexpected overlapping KL constraint")
        independently = vertex_minimum(gaps, required, costs)
        require(abs(formula - independently) < 1e-9, "Information allocation vertices disagree")
        result[fixture.name] = {
            "required_binary_kl": required, "expected_cost_lower_bound": independently,
            "rivals": [ADMITTED[j].name for j in (same, other)], "kl_per_action": gaps,
        }
    return result


def confidence_design():
    cells = {
        "audit": len(UNITS) * len(audit.ALL),
        "native": len(UNITS) * len(RECIPES) * len(SPEC["cues"]),
        "factorial": len(UNITS) * len(SPEC["contexts"]) * len(SPEC["cues"]) * len(SPEC["trims"]) * 2,
    }
    report = {}
    for kind, count in cells.items():
        n = SPEC[kind]["episodes"]
        radius = Fraction(SPEC[kind]["radius"])
        bound = 2 * count * exp(-2 * n * float(radius)**2)
        require(bound < Fraction(SPEC["alpha"]), f"Invalid simultaneous coverage for {kind}")
        report[kind] = {"n": n, "cells": count, "radius": str(radius), "union_bound": bound}
    separations = {
        abs(audit.CHANCES[i][q] - audit.CHANCES[j][q])
        for i, j in combinations(audit.CANDIDATES, 2)
        for q in audit.ALL
        if audit.CHANCES[i][q] != audit.CHANCES[j][q]
    }
    minimum = min(separations)
    require(minimum > 2 * audit.RADIUS, "Different admitted means can share one confidence interval")
    report["smallest_distinct_reset_gap"] = str(minimum)
    return report


def baseline():
    return {
        "coverage": confidence_design(),
        "risks": risk_report(),
        "conditional": law_report(),
        "exact_law_acquisition": law_costs(),
        "binomial_acquisition": binomial_report(),
        "t21_forced_decision_error_lower_bound_fixed_and_carry": "1/2",
        "t22_independent_reset_information": information_bounds(),
    }
