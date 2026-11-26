"""Score disclosed machine ledgers and compare them with sealed forecasts."""

from fractions import Fraction
import gzip
from hashlib import sha256
import json
from math import prod

import analysis as an
import oracle
import runtime as rt


EXPECTED_PRIMARY = {
    "identical": "safe",
    "bounded_drift": "safe",
    "changed_verdict": "unsafe",
    "missing_support": "abstain",
    "fidelity_violation": "abstain",
    "vacuous": "abstain",
}


def write_records(path, records):
    digest = sha256()
    with path.open("xb") as target:
        with gzip.GzipFile(fileobj=target, filename="", mode="wb", compresslevel=6, mtime=0) as archive:
            for record in records:
                line = (json.dumps(record, separators=(",", ":")) + "\n").encode("ascii")
                digest.update(line)
                archive.write(line)
    return digest.hexdigest()


def records_from(path):
    with gzip.open(path, "rb") as archive:
        for line in archive:
            yield json.loads(line)


def count_ledger(family, ledger, initial):
    """Reconstruct the label from trusted measurements without using runtime.score."""
    if family == "sorter":
        if any(dispatched != received or received not in (0, 1) for _, _, dispatched, received in ledger):
            raise ValueError("Station received an invalid action")
        losses = len([row for row in ledger if row[0] != row[3]])
        return int(losses > 0), len(ledger) - losses, len(ledger)

    pending = initial
    served = 0
    requests = initial
    for arrived, observed, mode, completed, after in ledger:
        if observed != pending or mode not in (0, 1) or not 0 <= completed <= pending + arrived:
            raise ValueError("Invalid trusted queue telemetry")
        pending += arrived - completed
        if pending != after:
            raise ValueError("Queue ledger violates job conservation")
        requests += arrived
        served += completed
    return int(pending > 0), served, requests


def tally(records, installations):
    result = {
        unit: {
            context: {"n": 0, "events": 0, "completed": 0, "offered": 0,
                      "enrollment_n": {stratum: 0 for stratum in rt.STRATA}}
            for context in rt.CONTEXTS
        }
        for unit in installations
    }
    for unit, context, index, enrollment_ticket, tickets, initial, ledger in records:
        cell = result[unit][context]
        installed = installations[unit]
        enrollment = installed.enrollment[context]
        if (
            index != cell["n"] or not 0 <= enrollment_ticket < rt.ENROLLMENT_SPACE
            or len(tickets) != len(rt.STAGES)
            or any(not 0 <= ticket < rt.TICKET_SPACE for ticket in tickets)
            or len(ledger) != len(rt.STAGES) - 1
        ):
            raise ValueError("Invalid holdout coordinate")
        stratum = rt.STRATA[sum(enrollment_ticket >= sum(enrollment[:stage]) for stage in (1, 2))]
        settings = rt.limits_for(installed, context, stratum)
        bits = tuple(int(ticket < threshold) for ticket, threshold in zip(tickets, settings))
        event, completed, offered = count_ledger(installed.family, ledger, initial)
        if initial != bits[0] or event != oracle.violation(installed.family, context, stratum, bits):
            raise ValueError("Trusted machine label differs from the independent exact model")
        cell["n"] += 1
        cell["events"] += event
        cell["completed"] += completed
        cell["offered"] += offered
        cell["enrollment_n"][stratum] += 1
    if any(cell["n"] != an.SAMPLE_SIZES["holdout"] for by_context in result.values() for cell in by_context.values()):
        raise ValueError("Holdout missing a frozen trial count")
    return result


def exact_coupling(installation, primary):
    if primary["admission"] != "valid":
        return {}, True
    verified = True
    output = {}
    for context in rt.CONTEXTS:
        output[context] = {}
        for stratum in rt.COVERED:
            source = rt.REFERENCES[installation.bank][context][stratum]
            target = rt.limits_for(installation, context, stratum)
            steps = oracle.exact_step_disagreement(source, target)
            cell = primary["conditional"][context][stratum]
            verified &= all(
                band[0] <= float(value) <= band[1]
                for value, band in zip(steps, cell["initial_and_step_bands"])
            )
            union = 1 - prod(1 - value for value in steps)
            verified &= float(union) <= cell["eta"]
            transport_gap = abs(
                oracle.conditional_risk(installation.family, context, stratum, source)
                - oracle.conditional_risk(installation.family, context, stratum, target)
            )
            output[context][stratum] = {
                "step_mismatch": [str(value) for value in steps],
                "probability_of_any_seam_mismatch": str(union),
                "conditional_risk_gap": str(transport_gap),
            }
    return output, bool(verified)


def overlap(first, second):
    return max(first[0], second[0]) <= min(first[1], second[1])


def summarize(raw, installations, forecast):
    observed = tally(records_from(raw), installations)
    by_unit = {}
    scorecard = {method: {
        "certified": 0, "abstained": 0, "native_confirmed": 0, "native_opposed": 0,
        "native_inconclusive_among_certified": 0, "false_safe": 0, "false_unsafe": 0,
        "exact_contexts_inside": 0, "native_contexts_overlap": 0, "worst_width_sum": 0.0,
    } for method in an.METHODS}
    checked_bounds = True
    cost_totals = {}
    for unit, installation in sorted(installations.items()):
        prediction = forecast[unit]
        contexts = observed[unit]
        native = an.envelope({context: an.from_count(cell, "holdout") for context, cell in contexts.items()})
        exact = oracle.exact_contexts(installation)
        exact_worst = max(exact.values())
        exact_verdict = "safe" if exact_worst <= Fraction(str(an.THRESHOLD)) else "unsafe"
        coupling, valid_coupling = exact_coupling(installation, prediction)
        checked_bounds &= valid_coupling
        for name, cost in prediction["cost"].items():
            cost_totals[name] = cost_totals.get(name, 0) + cost

        cells = {}
        for name in an.METHODS:
            comparison = prediction[name]
            decision = comparison["verdict"]
            bands = comparison["contexts"]
            inside = sum(bands[context][0] <= float(exact[context]) <= bands[context][1] for context in rt.CONTEXTS)
            intersects = sum(overlap(bands[context], native["contexts"][context]) for context in rt.CONTEXTS)
            width = comparison["worst"][1] - comparison["worst"][0]
            cells[name] = {
                "verdict": decision,
                "native_confirmed": decision != "abstain" and decision == native["verdict"],
                "native_opposed": decision != "abstain" and native["verdict"] not in (decision, "abstain"),
                "exact_contexts_inside": inside,
                "native_contexts_overlap": intersects,
                "worst_width": width,
                "worst_interval": comparison["worst"],
            }
            metrics = scorecard[name]
            metrics["certified"] += decision != "abstain"
            metrics["abstained"] += decision == "abstain"
            metrics["native_confirmed"] += cells[name]["native_confirmed"]
            metrics["native_opposed"] += cells[name]["native_opposed"]
            metrics["native_inconclusive_among_certified"] += (
                decision != "abstain" and native["verdict"] == "abstain"
            )
            metrics["false_safe"] += decision == "safe" and exact_verdict == "unsafe"
            metrics["false_unsafe"] += decision == "unsafe" and exact_verdict == "safe"
            metrics["exact_contexts_inside"] += inside
            metrics["native_contexts_overlap"] += intersects
            metrics["worst_width_sum"] += width

        by_unit[unit] = {
            "family": installation.family,
            "control": installation.control,
            "admission": prediction["admission"],
            "observed": contexts,
            "native": native,
            "exact_context_risk": {context: str(value) for context, value in exact.items()},
            "exact_worst": str(exact_worst),
            "exact_verdict": exact_verdict,
            "exact_covered_coupling": coupling,
            "uncovered_mass": prediction["uncovered"],
            "comparators": cells,
            "cost": prediction["cost"],
        }

    n_units = len(installations)
    for metrics in scorecard.values():
        metrics["mean_worst_width"] = metrics.pop("worst_width_sum") / n_units
        metrics["certification_rate"] = metrics["certified"] / n_units
        metrics["abstention_rate"] = metrics["abstained"] / n_units
        metrics["native_confirmation_rate_among_certified"] = (
            metrics["native_confirmed"] / metrics["certified"] if metrics["certified"] else None
        )
    primary_scores = scorecard["anchored"]
    gates = {
        "preregistered_primary_control_decisions": all(
            row["comparators"]["anchored"]["verdict"] == EXPECTED_PRIMARY[row["control"]]
            for row in by_unit.values()
        ),
        "native_confirmation_of_each_anchored_decision": primary_scores["certified"] == primary_scores["native_confirmed"],
        "every_exact_risk_and_native_interval_covered": (
            primary_scores["exact_contexts_inside"] == primary_scores["native_contexts_overlap"]
            == n_units * len(rt.CONTEXTS)
        ),
        "independent_exact_covered_mismatch_check": checked_bounds,
        "correct_fidelity_refusals": all(
            (row["admission"] == "fidelity_violation") == (row["control"] == "fidelity_violation")
            for row in by_unit.values()
        ),
        "full_uncovered_mass_retained": all(
            all(
                forecast[unit]["anchored"]["contexts"][context][1] >= rho
                and row["uncovered_mass"][context] == (
                    installations[unit].enrollment[context][-1] / rt.ENROLLMENT_SPACE
                )
                for context, rho in row["uncovered_mass"].items()
            )
            for unit, row in by_unit.items()
        ),
    }
    return {
        "trace_schema": ["unit", "context", "index", "enrollment_ticket", "primitive_tickets", "initial", "machine_ledger"],
        "sorter_row_schema": ["printed_tray", "shown_tray", "dispatched_tray", "received_tray"],
        "queue_row_schema": ["arrivals", "observed_pending", "boost", "completed", "pending_after"],
        "confidence": an.confidence_design(),
        "native_episodes": sum(cell["n"] for by_context in observed.values() for cell in by_context.values()),
        "gates": gates,
        "unit_cost_totals": cost_totals,
        "metrics": scorecard,
        "units": by_unit,
    }
