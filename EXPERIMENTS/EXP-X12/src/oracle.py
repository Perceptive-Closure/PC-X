"""Finite reference calculations independent of the policies' score and sampler."""

from collections import Counter
from dataclasses import replace
from fractions import Fraction
from itertools import product
from math import prod

import measure
import runtime as rt


BIT_VECTORS = tuple(product((0, 1), repeat=len(rt.STAGES)))


def violation(family, context, stratum, bits):
    if family == "sorter":
        mount, first, second, third = bits
        return bool(mount != first or second or third)
    pending = bits[0]
    for tick, slower in enumerate(bits[1:]):
        large_batch = (context, stratum, tick) == ("busy", "priority", 0)
        arrived = 3 if large_batch else 2
        extra_capacity = large_batch or (tick > 0 and pending > 0)
        pending = max(0, pending + arrived + slower - 2 - int(extra_capacity))
    return pending > 0


def conditional_risk(family, context, stratum, limits):
    numerator = sum(
        prod(limit if bit else rt.TICKET_SPACE - limit for limit, bit in zip(limits, bits))
        for bits in BIT_VECTORS
        if violation(family, context, stratum, bits)
    )
    return Fraction(numerator, rt.TICKET_SPACE ** len(rt.STAGES))


def exact_contexts(installation):
    family = installation.family
    return {
        context: sum(
            Fraction(count, rt.ENROLLMENT_SPACE)
            * conditional_risk(family, context, stratum, rt.limits_for(installation, context, stratum))
            for count, stratum in zip(installation.enrollment[context], rt.STRATA)
        )
        for context in rt.CONTEXTS
    }


def exact_step_disagreement(source, destination):
    return [Fraction(abs(a - b), rt.TICKET_SPACE) for a, b in zip(source, destination)]


def assert_transport(installation):
    """Check risk gaps against the exact paired-uniform coupling on valid covered seams."""
    for context in rt.CONTEXTS:
        if installation.probe_overwrites:
            raise ValueError("Unfaithful comparison")
        for stratum in rt.COVERED:
            source = rt.REFERENCES[installation.bank][context][stratum]
            target = rt.limits_for(installation, context, stratum)
            args = (installation.family, context, stratum)
            gap = abs(conditional_risk(*args, source) - conditional_risk(*args, target))
            disagreements = exact_step_disagreement(source, target)
            independent_union = 1 - prod(1 - p for p in disagreements)
            if not gap <= independent_union <= min(1, sum(disagreements)):
                raise ValueError("Transport implication failed")


def evaluation_law(installation, context, stratum):
    # Every authorized evaluation uses the installed original nominal environment.
    # Include the full native evaluation record in the observed law.
    limits = rt.REFERENCES["nominal"][context][stratum]
    counts = Counter()
    for bits in BIT_VECTORS:
        weight = prod(limit if bit else rt.TICKET_SPACE - limit for limit, bit in zip(limits, bits))
        initial, ledger = rt.episode(installation.family, context, stratum, bits)
        counts[(initial, tuple(tuple(row) for row in ledger))] += weight
    return counts


def exact_preflight():
    epsilon = Fraction(str(rt.CONFIG["risk_threshold"]))
    cases = {}
    path_checks = 0
    coupling_checks = 0
    for family in rt.FAMILIES:
        for context, stratum, bits in product(rt.CONTEXTS, rt.STRATA, BIT_VECTORS):
            initial, ledger = rt.episode(family, context, stratum, bits)
            label, _, _ = rt.score(family, initial, ledger)
            if label != violation(family, context, stratum, bits):
                raise ValueError("Executed policy differs from the independent event oracle")
            path_checks += 1

        safe = rt.install(family, "identical", 0)
        unsafe = rt.install(family, "changed_verdict", 0)
        equal_evaluations = sum(
            evaluation_law(safe, context, stratum) == evaluation_law(unsafe, context, stratum)
            for context, stratum in product(rt.CONTEXTS, rt.COVERED)
        )
        safe_risk = max(exact_contexts(safe).values())
        unsafe_risk = max(exact_contexts(unsafe).values())
        if equal_evaluations != len(rt.CONTEXTS) * len(rt.COVERED):
            raise ValueError("Evaluation equivalence witness is invalid")
        if not safe_risk <= epsilon < unsafe_risk:
            raise ValueError("Witnesses are threshold-equivalent")

        partial = rt.install(family, "missing_support", 0)
        partial_other = replace(partial, novel_limit=rt.TICKET_SPACE)
        always_good = exact_contexts(partial)
        always_bad = exact_contexts(partial_other)
        gaps = {context: always_bad[context] - always_good[context] for context in rt.CONTEXTS}
        if gaps != {
            context: Fraction(partial.enrollment[context][-1], rt.ENROLLMENT_SPACE)
            for context in rt.CONTEXTS
        }:
            raise ValueError("Uncovered support witness is invalid")
        if not max(always_good.values()) <= epsilon < max(always_bad.values()):
            raise ValueError("Uncovered support does not alter this witness verdict")

        for control, variant in product(rt.CONTROLS, (0, 1)):
            if control != "fidelity_violation":
                assert_transport(rt.install(family, control, variant))
                coupling_checks += len(rt.CONTEXTS) * len(rt.COVERED)
        cases[family] = {
            "exact_equal_full_eval_laws": equal_evaluations,
            "safe_worst": str(safe_risk),
            "unsafe_worst": str(unsafe_risk),
            "uncovered_risk_gap_by_context": {context: str(gap) for context, gap in gaps.items()},
        }

    costs = rt.CONFIG["unit_cost"]
    query_cost = {
        "registry": costs["registry"],
        "pulse": costs["pulse"],
        "paired": len(rt.CONTEXTS) * len(rt.COVERED) * len(rt.STAGES)
        * rt.CONFIG["samples"]["paired"] * costs["paired_repetition"],
    }
    required = {
        "identical": {"registry", "pulse"},
        "ordinary": {"registry", "pulse", "paired"},
        "unfaithful": {"registry", "pulse"},
    }
    subsets = [
        {name for name, take in zip(query_cost, mask) if take}
        for mask in product((False, True), repeat=len(query_cost))
    ]
    minimum = {
        stage: min(sum(query_cost[name] for name in options) for options in subsets if needed <= options)
        for stage, needed in required.items()
    }
    return {
        "development": measure.development(),
        "paths_checked": path_checks,
        "covered_transport_checks": coupling_checks,
        "witnesses": cases,
        "query_subset_checks": len(subsets) * len(required),
        "minimum_structural_batch_cost": minimum,
        "nonadaptive_batch_cost": sum(query_cost.values()),
    }
