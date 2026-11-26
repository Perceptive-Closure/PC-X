"""Seeded batch measurements, randomized controls and independent station outcomes."""

from collections import Counter
from fractions import Fraction
import gzip
from hashlib import sha256
from itertools import product

import audit
from contract import RECIPES, ROSTER, SPEC, UNITS, document, file_digest, save, stream
from model import MEETS, FAILS, THRESHOLD, factor_probability, risks, target
from sandbox import factor_observation, native_episode, reset_batch


NATIVE_FIELDS = ["unit", "cue", "recipe", "episode", "turns"]
TURN_FIELDS = ["policy_ticket", "right_tray", "station_ticket", "recheck"]
FACTOR_FIELDS = [
    "unit", "randomized_order", "mode", "cue", "context", "trim",
    "prefix_ticket", "prefix_right", "policy_ticket", "right_tray",
]
FACTOR_AXES = tuple(product(("reset", "carry"), SPEC["cues"], SPEC["contexts"], SPEC["trims"]))
NATIVE_RADIUS = Fraction(SPEC["native"]["radius"])
FACTOR_RADIUS = Fraction(SPEC["factorial"]["radius"])
INCONCLUSIVE = "INCONCLUSIVE"


def observe(fixture, unit, seed, query):
    rng = stream(seed, "audit", unit, query.name)
    return reset_batch(fixture, query.cue, query.context, audit.N, rng)


def selected_measurements(fixture, unit, seed):
    observations = []

    def measure(query):
        trays = observe(fixture, unit, seed, query)
        observations.append({"query": query.name, "trays": trays})
        return trays

    audit.run("primary", measure)
    return observations


def all_batches(fixture, unit, seed):
    return {query.name: observe(fixture, unit, seed, query) for query in audit.QUERIES}


def compare_methods(batches, unit, seed):
    return {
        method: audit.run(
            method,
            lambda query: batches[query.name],
            stream(seed, "comparator-order", unit),
        )
        for method in audit.METHODS
    }


def method_metrics(rows, methods):
    """Report fixed-roster counts with explicit denominators."""
    summary = {}
    for stratum in ("anchored", "midpoint", "shift"):
        included = [row for row in rows if row["fixture"][0] == stratum]
        summary[stratum] = {}
        for method in methods:
            pairs = [(row["reference_target"], row["methods"][method]) for row in included]
            correct = sum(truth == entry["verdict"] for truth, entry in pairs)
            certificates = sum(entry["status"] == audit.CERTIFIED for _, entry in pairs)
            costs = [entry["cost"] for _, entry in pairs if entry["cost"] is not None]
            has_cost = bool(costs)
            summary[stratum][method] = {
                "units": len(pairs),
                "certified": certificates,
                "correct": correct,
                "wrong": certificates - correct,
                "false_meets": sum(
                    truth == FAILS and entry["verdict"] == MEETS for truth, entry in pairs
                ),
                "abstained": sum(entry["status"] == audit.ABSTAIN for _, entry in pairs),
                "inconsistent": sum(entry["status"] == audit.INCONSISTENT for _, entry in pairs),
                "mean_acquisition_cost": str(Fraction(sum(costs), len(costs))) if has_cost else None,
                "max_realized_acquisition_cost": max(costs) if has_cost else None,
            }
    return summary


def development():
    plan = SPEC["development"]
    rows = []
    for seed in range(plan["seed_start"], plan["seed_start"] + plan["replicates"]):
        for unit, fixture in zip(UNITS, ROSTER, strict=True):
            batches = all_batches(fixture, unit, seed)
            rows.append({
                "seed": seed,
                "unit": unit,
                "fixture": list(fixture),
                "reference_target": target(fixture),
                "batches": batches,
                "methods": compare_methods(batches, unit, seed),
            })
    return {"rows": rows, "metrics": method_metrics(rows, audit.METHODS)}


def proportion_interval(count, total, radius):
    mean = Fraction(count, total)
    return [str(max(0, mean - radius)), str(min(1, mean + radius))]


def threshold_verdict(conditions):
    limits = [[Fraction(value) for value in cell["interval"]] for cell in conditions.values()]
    if all(upper <= THRESHOLD for _, upper in limits):
        return MEETS
    if any(lower > THRESHOLD for lower, _ in limits):
        return FAILS
    return INCONCLUSIVE


def trace_file(path, rows, fields):
    checksum = sha256()
    count = 0
    with path.open("xb") as handle:
        with gzip.GzipFile(filename="", mode="wb", compresslevel=6, fileobj=handle, mtime=0) as compressed:
            for row in rows:
                encoded = document(row)
                checksum.update(encoded)
                compressed.write(encoded)
                count += 1
    return {
        "fields": fields,
        "rows": count,
        "raw_sha256": checksum.hexdigest(),
        "gzip_sha256": file_digest(path),
    }


def native_rows(assignment, seed, sections):
    episodes = SPEC["native"]["episodes"]
    for unit in UNITS:
        fixture = assignment[unit]
        sections[unit] = {}
        for cue in SPEC["cues"]:
            cells = {}
            for name, recipe in RECIPES.items():
                rng = stream(seed, "native", unit, cue, name)
                failures = rechecks = 0
                for index in range(episodes):
                    trace = native_episode(fixture, cue, recipe, rng)
                    episode_rechecks = sum(turn[-1] for turn in trace)
                    failures += episode_rechecks > 0
                    rechecks += episode_rechecks
                    yield [unit, cue, name, index, trace]
                placements = episodes * len(recipe)
                cells[name] = {
                    "episodes": episodes,
                    "completed_episodes": episodes,
                    "failures": failures,
                    "rechecks": rechecks,
                    "placements": placements,
                    "accepted_placements": placements - rechecks,
                    "risk": str(Fraction(failures, episodes)),
                    "interval": proportion_interval(failures, episodes, NATIVE_RADIUS),
                    "reference_risk": str(risks(fixture, cue)[name]),
                }
            sections[unit][cue] = {"conditions": cells, "verdict": threshold_verdict(cells)}


def contrast(a, b):
    difference = Fraction(a["proportion"]) - Fraction(b["proportion"])
    return {
        "difference": str(difference),
        "interval": [
            str(max(-1, difference - 2 * FACTOR_RADIUS)),
            str(min(1, difference + 2 * FACTOR_RADIUS)),
        ],
        "reference_difference": str(Fraction(a["reference"]) - Fraction(b["reference"])),
    }


def factorial_rows(assignment, seed, sections):
    repeats = SPEC["factorial"]["episodes"]
    for unit in UNITS:
        fixture = assignment[unit]
        order = list(FACTOR_AXES) * repeats
        stream(seed, "factor-order", unit).shuffle(order)
        rng = stream(seed, "factor-tickets", unit)
        counts = Counter()
        for index, condition in enumerate(order):
            draw = factor_observation(fixture, *condition, rng)
            counts[condition] += draw[-1]
            yield [unit, index, *condition, *draw]

        cells = {
            condition: {
                "episodes": repeats,
                "right": counts[condition],
                "proportion": str(Fraction(counts[condition], repeats)),
                "interval": proportion_interval(counts[condition], repeats, FACTOR_RADIUS),
                "reference": str(factor_probability(fixture, *condition[:3])),
            }
            for condition in FACTOR_AXES
        }
        color = {}
        for mode, context, trim in product(("reset", "carry"), SPEC["contexts"], SPEC["trims"]):
            color["/".join((mode, context, trim))] = contrast(
                cells[mode, "gold", context, trim], cells[mode, "blue", context, trim]
            )
        trim_effect = {}
        for mode, cue, context in product(("reset", "carry"), SPEC["cues"], SPEC["contexts"]):
            trim_effect["/".join((mode, cue, context))] = contrast(
                cells[mode, cue, context, "dotted"], cells[mode, cue, context, "plain"]
            )
        sections[unit] = {
            "cells": {"/".join(condition): result for condition, result in cells.items()},
            "gold_minus_blue": color,
            "dotted_minus_plain": trim_effect,
        }


def bands_intersect(forecast, measured):
    limits = [Fraction(bound) for bound in measured["interval"]]
    band = [Fraction(bound) for bound in forecast]
    return max(limits[0], band[0]) <= min(limits[1], band[1])


def summarize_unit(unit, fixture, methods, forecast, native):
    anchor_verdict = target(fixture)
    gold = native[SPEC["deployment_cue"]]
    blue = native[SPEC["comparison_cue"]]
    blue_verdict = None if blue["verdict"] == INCONCLUSIVE else blue["verdict"]
    methods["blue_extrapolation"] = {
        "status": audit.CERTIFIED if blue_verdict else audit.ABSTAIN,
        "verdict": blue_verdict,
        "cost": None,
    }
    methods["carry_structural"] = {
        "status": audit.ABSTAIN,
        "verdict": None,
        "cost": None,
        "target_distinct_alias": [f"{fixture.key}/0", f"{fixture.key}/1"],
    }
    checks = {}
    if forecast["status"] == audit.CERTIFIED:
        checks = {
            name: bands_intersect(forecast["risk_bands"][name], cell)
            for name, cell in gold["conditions"].items()
        }
    if fixture.mode == "anchored":
        gate = (
            forecast["verdict"] == anchor_verdict == gold["verdict"]
            and len(checks) == len(RECIPES) and all(checks.values())
            and methods["fixed_blue"]["status"] == audit.ABSTAIN
        )
    elif fixture.mode == "midpoint":
        gate = forecast["status"] == audit.INCONSISTENT
    else:
        gate = forecast["verdict"] == MEETS and gold["verdict"] == FAILS
    return {
        "unit": unit,
        "fixture": list(fixture),
        "reference_target": anchor_verdict,
        "sealed": forecast["verdict"],
        "native_gold": gold["verdict"],
        "blue_extrapolation": blue_verdict,
        "cell_band_intersection": checks,
        "gate_passed": gate,
        "methods": methods,
    }


def collect(output, assignment, seed, forecast):
    """Run the sealed outcomes and full control cohorts once custody opens."""
    output.mkdir()
    batches = {unit: all_batches(assignment[unit], unit, seed) for unit in UNITS}
    save(output / "raw-audits.json", {
        "schema": {"0": "left", "1": "right"},
        "episodes_per_batch": audit.N,
        "units": batches,
    })
    native = {}
    native_trace = trace_file(
        output / "raw-native.jsonl.gz", native_rows(assignment, seed, native), NATIVE_FIELDS
    )
    native_trace["turn_fields"] = TURN_FIELDS
    factorial = {}
    factorial_trace = trace_file(
        output / "raw-factorial.jsonl.gz", factorial_rows(assignment, seed, factorial), FACTOR_FIELDS
    )
    rows = []
    for unit in UNITS:
        methods = compare_methods(batches[unit], unit, seed)
        parameters = forecast["units"][unit]
        if methods["primary"] != parameters["audit"]:
            raise ValueError("Unchanged audit must replay its sealed path")
        prediction = {**parameters["audit"], "risk_bands": parameters["risk_bands"]}
        rows.append(summarize_unit(unit, assignment[unit], methods, prediction, native[unit]))
    report = {
        "threshold": str(THRESHOLD),
        "unit_results": rows,
        "all_frozen_unit_gates_passed": all(row["gate_passed"] for row in rows),
        "method_metrics": method_metrics(rows, (*audit.METHODS, "blue_extrapolation", "carry_structural")),
        "native": native,
        "factorial": factorial,
        "raw": {"native": native_trace, "factorial": factorial_trace},
    }
    save(output / "summary.json", report)
    return report
