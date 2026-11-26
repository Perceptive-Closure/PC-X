"""The frozen simultaneous inference and matching rules."""

from fractions import Fraction
from math import log, sqrt


def interval_family(protocol):
    comparisons = len(protocol["contexts"]) * (2 * len(protocol["arms"]) - 1)
    alpha = float(Fraction(protocol["family_alpha"]))
    trials = protocol["paired_episodes_per_context"]
    width = sqrt(log(2 * comparisons / alpha) / (2 * trials))
    return comparisons, width, 2 * width


def interval(value, width, minimum, maximum):
    return [max(minimum, value - width), min(maximum, value + width)]


def threshold_verdict(intervals, threshold):
    if all(high <= threshold for _, high in intervals):
        return "within_threshold"
    if any(low > threshold for low, _ in intervals):
        return "above_threshold"
    return "abstain"


def fidelity_verdict(intervals, margin):
    if all(low >= -margin and high <= margin for low, high in intervals):
        return "equivalent"
    if any(low > margin or high < -margin for low, high in intervals):
        return "disturbed"
    return "abstain"


def clearance(protocol, candidate):
    """On the simultaneous coverage event, an interval endpoint is within 2 widths."""
    comparisons, risk_width, contrast_width = interval_family(protocol)
    threshold = Fraction(protocol["risk_threshold"])
    margin = Fraction(protocol["fidelity_margin"])
    for arm, predictions in candidate.items():
        risks = [Fraction(p) for p in predictions["risk"].values()]
        status = threshold_verdict([interval(p, 2 * risk_width, 0, 1) for p in risks], threshold)
        if status != predictions["threshold"]:
            raise ValueError(f"Insufficient preregistered threshold clearance for {arm}")
        if arm != "original":
            differences = [Fraction(p) for p in predictions["contrast"].values()]
            status = fidelity_verdict(
                [interval(p, 2 * contrast_width, -1, 1) for p in differences], margin
            )
            if status != predictions["fidelity"]:
                raise ValueError(f"Insufficient preregistered fidelity clearance for {arm}")
    return {"comparisons": comparisons, "risk_half_width": round(risk_width, 12),
            "paired_half_width": round(contrast_width, 12), "all_verdicts_resolve_on_coverage": True}
