"""Paired sandbox measurement over an independently scored external work ledger."""

import gzip
import hashlib
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path

from analysis import fidelity_verdict, interval, interval_family, threshold_verdict
from common import canonical
from sandbox import run_sequence
from verify import score_ledger, verify_path


def block_steps(protocol, context, index, seed):
    value = hashlib.sha256(
        b"PC-X11/paired/v1\0" + bytes.fromhex(seed) + context.encode("ascii")
        + b"\0" + index.to_bytes(8, "big")
    ).digest()
    return [(request, byte & 3, (byte >> 2) & 3)
            for request, byte in zip(protocol["contexts"][context], value[:protocol["horizon"]], strict=True)]


def produce_observations(protocol, secret, trace_path):
    with Path(trace_path).open("xb") as output, gzip.GzipFile(
            filename="", mode="wb", fileobj=output, mtime=0) as trace:
        for context in protocol["contexts"]:
            for index in range(protocol["paired_episodes_per_context"]):
                steps = block_steps(protocol, context, index, secret["measurement_seed"])
                record = {
                    "context": context, "index": index, "steps": steps,
                    "arms": {arm: run_sequence(protocol, arm, secret["disturbed_port"], steps)
                             for arm in protocol["arms"]},
                }
                trace.write(canonical(record) + b"\n")


def summarized_observations(protocol, secret, forecast, trace_path):
    """Reconstruct stored results without executing the sandbox policy."""
    arms = protocol["arms"]
    contexts = protocol["contexts"]
    trials = protocol["paired_episodes_per_context"]
    arm_forecasts = forecast["arm_predictions"]
    counts = {context: {arm: Counter() for arm in arms} for context in contexts}
    trace_hash = hashlib.sha256()
    trace_records = 0
    with gzip.open(trace_path, "rb") as trace:
        for context in contexts:
            for index in range(trials):
                line = trace.readline()
                if not line:
                    raise ValueError("Missing held-out block")
                trace_hash.update(line)
                trace_records += 1
                rows = json.loads(line)
                steps = block_steps(protocol, context, index, secret["measurement_seed"])
                if (rows["context"] != context or rows["index"] != index
                        or rows["steps"] != [list(step) for step in steps] or set(rows["arms"]) != set(arms)
                        or line != canonical(rows) + b"\n"):
                    raise ValueError("Noncorresponding held-out block")
                original = rows["arms"]["original"]
                reference = score_ledger([frame[1] for frame in original], protocol["horizon"],
                                         protocol["label_backlogged_rounds"])
                for arm in arms:
                    frames = rows["arms"][arm]
                    capacity = protocol["disturbed_capacity"] if arm == secret["disturbed_port"] \
                        else protocol["normal_capacity"]
                    verify_path(protocol, arm, capacity, steps, frames)
                    if any(a[0] != b[0] for a, b in zip(original, frames, strict=True)):
                        raise ValueError("The public evaluation tape changed within a held-out block")
                    label = score_ledger([frame[1] for frame in frames], protocol["horizon"],
                                         protocol["label_backlogged_rounds"])
                    first = next((tick for tick, (a, b) in enumerate(zip(original, frames, strict=True), 1)
                                  if a[:3] != b[:3]), 0)
                    counter = counts[context][arm]
                    counter["events"] += label
                    counter["positive_pair_diff"] += label > reference
                    counter["negative_pair_diff"] += label < reference
                    counter[f"first_transition_difference_tick_{first}"] += 1
        if trace.readline():
            raise ValueError("Extra held-out observations")

    threshold = Fraction(protocol["risk_threshold"])
    margin = Fraction(protocol["fidelity_margin"])
    comparisons, risk_width, contrast_width = interval_family(protocol)
    runs = {}
    outcomes_met = 0
    contrasts_met = 0
    arm_verdicts_met = 0
    paired_verdicts_met = 0
    for arm in arms:
        cells = {}
        risk_intervals = []
        contrast_intervals = []
        paired = arm != "original"
        for context in contexts:
            counter = counts[context][arm]
            positives = counter["events"]
            rate = Fraction(positives, trials)
            band = interval(rate, risk_width, 0, 1)
            predicted = Fraction(arm_forecasts[arm]["risk"][context])
            covers = band[0] <= predicted <= band[1]
            outcomes_met += covers
            risk_intervals.append(band)
            cells[context] = {
                "events": positives, "trials": trials, "rate": float(rate),
                "risk_interval": band, "contains_forecast_risk": covers,
                "matching_trajectory_blocks": counter["first_transition_difference_tick_0"],
                "first_transition_difference_by_tick": [
                    counter[f"first_transition_difference_tick_{tick}"]
                    for tick in range(1, protocol["horizon"] + 1)],
                "public_agreement_blocks": trials,
            }
            if paired:
                higher = counter["positive_pair_diff"]
                lower = counter["negative_pair_diff"]
                delta = Fraction(higher - lower, trials)
                delta_band = interval(delta, contrast_width, -1, 1)
                predicted_delta = Fraction(arm_forecasts[arm]["contrast"][context])
                covers_delta = delta_band[0] <= predicted_delta <= delta_band[1]
                contrasts_met += covers_delta
                contrast_intervals.append(delta_band)
                cells[context].update({
                    "probe_only_events": higher, "original_only_events": lower,
                    "matched_labels": trials - higher - lower,
                    "paired_risk_difference": float(delta), "paired_interval": delta_band,
                    "contains_forecast_contrast": covers_delta,
                })
        measured_fidelity = fidelity_verdict(contrast_intervals, margin) if paired else "reference"
        if measured_fidelity == "equivalent" and any(
                Fraction(case["union_risk_bound"]) > margin
                for case in forecast["coupling_bounds"][arm].values()):
            measured_fidelity = "abstain"
        measured_threshold = threshold_verdict(risk_intervals, threshold)
        arm_verdicts_met += measured_threshold == arm_forecasts[arm]["threshold"]
        paired_verdicts_met += paired and measured_fidelity == arm_forecasts[arm]["fidelity"]
        runs[arm] = {"intervention": arm_forecasts[arm]["intervention"], "contexts": cells,
                     "threshold_verdict": measured_threshold, "fidelity_verdict": measured_fidelity}

    original_verdict = runs["original"]["threshold_verdict"]
    transfer = {
        arm: {"naive_original_verdict": runs[arm]["threshold_verdict"],
              "independent_original_verdict": original_verdict,
              "disagrees": runs[arm]["threshold_verdict"] != original_verdict}
        for arm in protocol["ports"]
    }
    cells_risk = len(contexts) * len(arms)
    cells_paired = len(contexts) * (len(arms) - 1)
    return {
        "blocks": trace_records, "episodes": trace_records * len(arms),
        "confidence_family": comparisons, "risk_half_width": risk_width,
        "paired_half_width": contrast_width, "arms": runs, "naive_transfer": transfer,
        "risk_intervals_containing_forecast": [outcomes_met, cells_risk],
        "paired_intervals_containing_forecast": [contrasts_met, cells_paired],
        "threshold_verdicts_agreeing": [arm_verdicts_met, len(arms)],
        "fidelity_verdicts_agreeing": [paired_verdicts_met, len(arms) - 1],
        "holdout_succeeded": (
            outcomes_met == cells_risk and contrasts_met == cells_paired
            and arm_verdicts_met == len(arms) and paired_verdicts_met == len(arms) - 1),
        "invalid_blocks": 0, "raw_sha256": trace_hash.hexdigest(),
    }
