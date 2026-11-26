"""Confidence bands, admission checks, and preregistered benchmark comparisons."""

from itertools import permutations
from math import log, sqrt

import runtime as rt


SAMPLE_SIZES = rt.CONFIG["samples"]
ALPHA = rt.CONFIG["alpha"]
THRESHOLD = rt.CONFIG["risk_threshold"]
N_UNITS = len(rt.FAMILIES) * len(rt.CONTROLS)
N_CELLS = len(rt.CONTEXTS) * len(rt.COVERED)
MULTIPLICITY = {
    "reference": len(rt.FAMILIES) * len(rt.REFERENCES) * N_CELLS,
    "paired": N_UNITS * N_CELLS * len(rt.STAGES),
    "full": N_UNITS * N_CELLS,
    "holdout": N_UNITS * len(rt.CONTEXTS),
}
COST = rt.CONFIG["unit_cost"]
BATCH_COSTS = {
    "registry": COST["registry"],
    "pulse": COST["pulse"],
    "paired": N_CELLS * len(rt.STAGES) * SAMPLE_SIZES["paired"] * COST["paired_repetition"],
}
DIRECT_COST = N_CELLS * SAMPLE_SIZES["full"] * COST["direct_trajectory"]
METHODS = ("anchored", "eval_only", "full", "nonadaptive", "ignore_fidelity")


def radius(cohort):
    return sqrt(log(2 * MULTIPLICITY[cohort] / ALPHA[cohort]) / (2 * SAMPLE_SIZES[cohort]))


def proportion_band(successes, n, cohort):
    if n != SAMPLE_SIZES[cohort] or type(successes) is not int or not 0 <= successes <= n:
        raise ValueError(f"Invalid fixed-size {cohort} count")
    empirical = successes / n
    return [max(0.0, empirical - radius(cohort)), min(1.0, empirical + radius(cohort))]


def from_count(record, cohort):
    return proportion_band(record["events"], record["n"], cohort)


def verdict(lower, upper):
    if upper <= THRESHOLD:
        return "safe"
    if lower > THRESHOLD:
        return "unsafe"
    return "abstain"


def envelope(cells):
    lower = max(band[0] for band in cells.values())
    upper = max(band[1] for band in cells.values())
    return {"contexts": cells, "worst": [lower, upper], "verdict": verdict(lower, upper)}


def expanded(band, eta):
    return [max(0.0, band[0] - eta), min(1.0, band[1] + eta)]


def mixture(weights, supported):
    low = sum(weights[stratum] * band[0] for stratum, band in supported.items())
    high = sum(weights[stratum] * band[1] for stratum, band in supported.items())
    return [max(0.0, low), min(1.0, high + weights["novel"])]


def registry_check(record, family):
    expected_tape = rt.semantic_tape(family)
    if (
        record["family"] != family
        or record["source_semantics"] != expected_tape
        or record["deployed_semantics"] != expected_tape
        or record["bank"] not in rt.REFERENCES
        or type(record["shared_storage"]) is not bool
    ):
        raise ValueError("Registry correspondence is out of the declared class")
    weights = {}
    for context in rt.CONTEXTS:
        tape = record["enrollment_tapes"][context]
        if len(tape) != rt.ENROLLMENT_SPACE or set(tape) - set(rt.STRATA):
            raise ValueError("Registry enrollment tape is incomplete")
        weights[context] = {stratum: tape.count(stratum) / len(tape) for stratum in rt.STRATA}
    return weights


def faithful_pulse(raw):
    expected = [
        [int(ticket < limit)] * 3
        for limit, _, ticket in rt.CONFIG["pulse_cases"]
    ]
    return raw == expected


def reference_envelope(family, calibration):
    weights = {
        context: {
            stratum: count / rt.ENROLLMENT_SPACE
            for stratum, count in zip(rt.STRATA, rt.CONFIG["enrollment"]["covered"][context])
        }
        for context in rt.CONTEXTS
    }
    return envelope({
        context: mixture(weights[context], {
            stratum: from_count(calibration[family]["nominal"][context][stratum], "reference")
            for stratum in rt.COVERED
        })
        for context in rt.CONTEXTS
    })


def paired_bounds(raw):
    n = SAMPLE_SIZES["paired"]
    if len(raw) != len(rt.STAGES):
        raise ValueError("Missing initial or step comparison")
    bands = []
    for joint in raw:
        if len(joint) != 4 or any(type(value) is not int or value < 0 for value in joint) or sum(joint) != n:
            raise ValueError("Invalid paired evidence")
        bands.append(proportion_band(joint[1] + joint[2], n, "paired"))
    return bands


def acquisition_costs(selected):
    def prefix_cost(order):
        tested = set()
        cost = 0
        for item in order:
            tested.add(item)
            cost += BATCH_COSTS[item]
            if selected <= tested:
                return cost
        raise ValueError("Audit batch is outside the frozen menu")

    options = [prefix_cost(order) for order in permutations(BATCH_COSTS)]
    return {
        "anchored": sum(BATCH_COSTS[item] for item in selected),
        "nonadaptive": sum(BATCH_COSTS.values()),
        "uniform_order_mean": sum(options) / len(options),
        "uniform_order_worst": max(options),
        "cheapest_first": prefix_cost(sorted(BATCH_COSTS, key=BATCH_COSTS.get)),
        "restricted_minimum": min(options),
        "full": COST["registry"] + DIRECT_COST,
        "eval_only": 0,
    }


def anchored_envelope(source, record, weights, accepted, shared):
    if not accepted:
        return envelope({context: [0.0, 1.0] for context in rt.CONTEXTS}), {}
    contexts = {}
    breakdown = {}
    for context in rt.CONTEXTS:
        bounds = {}
        breakdown[context] = {}
        for stratum in rt.COVERED:
            stage_bands = (
                [[0.0, 0.0] for _ in rt.STAGES]
                if shared else paired_bounds(record[context][stratum])
            )
            eta = min(1.0, sum(interval[1] for interval in stage_bands))
            bounds[stratum] = expanded(from_count(source[context][stratum], "reference"), eta)
            breakdown[context][stratum] = {
                "initial_and_step_bands": stage_bands,
                "eta": eta,
                "supported_risk": bounds[stratum],
            }
        contexts[context] = mixture(weights[context], bounds)
    return envelope(contexts), breakdown


def direct_envelope(weights, direct):
    return envelope({
        context: mixture(weights[context], {
            stratum: from_count(direct[context][stratum], "full")
            for stratum in rt.COVERED
        })
        for context in rt.CONTEXTS
    })


def forecast_units(units, calibration, roster_families):
    output = {}
    if set(units) != set(roster_families):
        raise ValueError("Audit roster differs from the declared slots")
    for unit in sorted(units):
        family = roster_families[unit]
        record = units[unit]
        registered = record["registry"]
        reference_only = reference_envelope(family, calibration)
        try:
            weights = registry_check(registered, family)
        except (KeyError, TypeError, ValueError):
            abstain = envelope({context: [0.0, 1.0] for context in rt.CONTEXTS})
            output[unit] = {
                "family": family, "admission": "semantic_mismatch",
                "anchored": abstain, "eval_only": reference_only, "full": abstain,
                "nonadaptive": abstain, "ignore_fidelity": abstain,
                "cost": acquisition_costs({"registry", "pulse"}), "uncovered": {},
                "conditional": {}, "shared_storage": False,
            }
            continue

        source = calibration[family][registered["bank"]]
        shared = registered["shared_storage"]
        faithful = faithful_pulse(record["pulse"])
        selection = {"registry", "pulse"}
        if faithful and not shared:
            selection.add("paired")
        anchored, breakdown = anchored_envelope(source, record["paired"], weights, faithful, shared)
        ungated, _ = anchored_envelope(source, record["paired"], weights, True, shared)
        output[unit] = {
            "family": family,
            "admission": "valid" if faithful else "fidelity_violation",
            "reference_bank": registered["bank"],
            "shared_storage": shared,
            "queries": sorted(selection),
            "uncovered": {context: weights[context]["novel"] for context in rt.CONTEXTS},
            "weights": weights,
            "conditional": breakdown,
            "anchored": anchored,
            "nonadaptive": anchored,
            "ignore_fidelity": ungated,
            "full": direct_envelope(weights, record["direct"]),
            "eval_only": reference_only,
            "cost": acquisition_costs(selection),
        }
    return output


def confidence_design():
    return {
        "simultaneous_alpha_budget": sum(ALPHA.values()),
        "alpha_by_cohort": ALPHA,
        "multiplicity": MULTIPLICITY,
        "n_per_primitive": {cohort: SAMPLE_SIZES[cohort] for cohort in MULTIPLICITY},
        "hoeffding_radius": {cohort: radius(cohort) for cohort in MULTIPLICITY},
    }
