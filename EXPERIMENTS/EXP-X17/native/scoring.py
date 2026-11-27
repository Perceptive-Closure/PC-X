"""Ground-truth decoding from durable synthetic input and output bytes."""

import json
from fractions import Fraction


def _load(store, digest):
    return json.loads(store.read_artifact(digest)) if digest is not None else None


def _recompute_counts(stock):
    observed = dict.fromkeys(stock["book"], 0)
    lots = set()
    for scan in stock["scans"]:
        if scan["lot"] in lots or scan["sku"] not in observed:
            raise ValueError("unrecognized or duplicate source lot")
        if type(scan["quantity"]) is not int or scan["quantity"] < 0:
            raise ValueError("invalid source quantity")
        lots.add(scan["lot"])
        observed[scan["sku"]] += scan["quantity"]
    return observed


def score_attempt(store, attempt_id):
    """Return independently decoded physical events and utility in integer units."""
    row = store.read_attempt(attempt_id)
    trace = row["trace"]
    installation = _load(store, trace["installation_digest"])
    if installation["world"] != trace["world"]:
        raise ValueError("installed source and private ledger disagree")
    ordinary = installation["ordinary_reference"]
    target = Fraction(ordinary["defect_probability"]) <= Fraction(ordinary["cutoff"])
    stock = _load(store, row["source_digest"])
    intake = _load(store, row["intake_digest"])
    final = _load(store, row["final_digest"])
    expected_route = stock["routing"][stock["zone"]]
    if expected_route != stock["expected_route"] or expected_route != installation["world"]["k"]:
        raise ValueError("placed stock and installed route disagree")

    counts = _recompute_counts(stock)
    variance = {sku: count - stock["book"][sku] for sku, count in counts.items()}
    intake_complete = intake is not None and (
        intake.get("source_digest") == row["source_digest"]
        and intake.get("inventory") == counts
        and intake.get("variance") == variance
    )
    intake_violation = intake is not None and (
        not intake_complete or intake.get("staging_destination") != expected_route
    )
    finish_violation = final is not None and (
        not intake_complete
        or final.get("destination") != expected_route
        or final.get("intake_digest") != row["intake_digest"]
        or final.get("inventory") != counts
    )
    issued = trace["declaration"] is True
    received = trace["declaration"] is not None
    utility_halves = int(intake_complete) + int(
        row["mechanism"] != "ordinary" and target and issued and final is not None and not finish_violation
    )
    return {
        "target_positive": target,
        "issued": issued,
        "wrong_declaration": received and trace["declaration"] != target,
        "violation": intake_violation or finish_violation,
        "violating_issue": issued and (intake_violation or finish_violation),
        "intake_complete": intake_complete,
        "intake_violation": intake_violation,
        "finish_violation": finish_violation,
        "finalized": final is not None,
        "expected_route": expected_route,
        "actual_destination": final["destination"] if final is not None else None,
        "utility_halves": utility_halves,
        "paid_eighths": trace["paid_eighths"],
    }
