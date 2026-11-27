"""Apply the predeclared simultaneous analysis to durable native trial totals."""

import argparse
import json
from collections import Counter
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction as Q
from pathlib import Path

from controller.forecast import forecast


ETA = Q(1, 20)
K = 640
RHO = Q(1, 25)
TOLERANCE = Q(2, 25)
N = 4096
ARMS = ("pcx", "high_skip", "low_only", "always_high", "no_paid")
OUTPUT_TICK = Decimal("0.000000001")
FIXED_RANGES = {key: (Q(0), Q(1)) for key in ("wrong", "I", "V", "VI", "G", "cost")}
FIXED_RANGES["Z"] = (Q(-3, 8), Q(5, 8))
FIXED_RANGES["G"] = (Q(1, 2), Q(1))


def load(path):
    return json.loads(path.read_bytes())


def dec(value):
    f = Q(value)
    return Decimal(f.numerator) / Decimal(f.denominator)


def clip_interval(value, radius, bounds):
    low, high = (dec(bound) for bound in bounds)
    with localcontext() as context:
        context.prec = 60
        lower = max(low, dec(value) - radius).quantize(OUTPUT_TICK, rounding=ROUND_FLOOR)
        upper = min(high, dec(value) + radius).quantize(OUTPUT_TICK, rounding=ROUND_CEILING)
    return str(lower), str(upper)


def normalized(tally, n):
    return {"wrong": Q(tally.get("wrong", 0), n),
            "I": Q(tally.get("I", 0), n),
            "V": Q(tally.get("V", 0), n),
            "VI": Q(tally.get("VI", 0), n),
            "G": Q(tally.get("G2", 0), 2*n),
            "cost": Q(tally.get("cost8", 0), 8*n),
            "Z": Q(8*tally.get("VI", 0) - 3*tally.get("I", 0), 8*n)}


def equivalent(expected, interval):
    lower, upper = map(Q, interval)
    if not lower <= expected <= upper:
        return "EMPIRICALLY_CONTRADICTED"
    if expected-TOLERANCE <= lower and upper <= expected+TOLERANCE:
        return "EMPIRICALLY_SUPPORTED"
    return "EMPIRICALLY_INCONCLUSIVE"


def threshold(interval, bound, direction):
    if interval is None:
        return "EMPIRICALLY_INCONCLUSIVE"
    low, high = map(Q, interval)
    if direction == "upper":
        return ("EMPIRICALLY_SUPPORTED" if high <= bound else
                "EMPIRICALLY_CONTRADICTED" if low > bound else "EMPIRICALLY_INCONCLUSIVE")
    return ("EMPIRICALLY_SUPPORTED" if low >= bound else
            "EMPIRICALLY_CONTRADICTED" if high < bound else "EMPIRICALLY_INCONCLUSIVE")


def each_cell(role, item, world):
    counts = item["counts"]
    attempts = counts["attempts"]
    arm = item["arm"]
    base = {"role": role, "world": item["world"], "arm": arm,
            "sample": attempts, "counts": counts}
    if attempts != N or counts.get("invalid", 0) or counts.get("valid") != N:
        return {**base, "disposition": "INVALID_EXPERIMENTAL_EVIDENCE"}
    if not (0 <= counts.get("VI",0) <= counts.get("I",0) <= N and counts.get("V",0) == counts.get("VI",0)
            and 0 <= counts.get("wrong",0) <= N and N <= counts.get("G2",0) <= 2*N
            and 0 <= counts.get("cost8",0) <= 8*N):
        raise ValueError("durable tally violates the registered scoring domains")
    params = [Q(world["theta"]), Q(world["beta"]), world["m"], world["N"]]
    predicted = forecast(*params, arm)
    actual = normalized(counts, attempts)
    specs = {name: clip_interval(value, dec(RHO), FIXED_RANGES[name])
             for name, value in actual.items()}
    if actual["I"] > 0:
        actual["selected_risk"] = actual["VI"]/actual["I"]
        predicted["selected_risk"] = predicted["VI"]/predicted["I"]
        with localcontext() as context:
            context.prec = 60
            radius = ((dec(2*K/ETA)).ln() / (2*counts["I"])).sqrt()
        specs["selected_risk"] = clip_interval(actual["selected_risk"], radius, (0, 1))
    else:
        specs["selected_risk"] = None

    tests = {}
    if arm in ("pcx", "always_high"):
        tests["wrong_at_most_1/3"] = threshold(specs["wrong"], Q(1,3), "upper")
        tests["signed_risk_at_most_3/8"] = threshold(specs["Z"], Q(0), "upper")
        for cap in (Q(3,8), Q(5,16)):
            tests[f"selected_risk_at_most_{cap}"] = threshold(specs["selected_risk"], cap, "upper")
        if arm == "pcx":
            tests["issuance_at_least_1/4"] = threshold(specs["I"], Q(1,4), "lower")
        if params[0] < Q(1,2):
            tests["positive_issuance_at_least_2/3"] = threshold(specs["I"], Q(2,3), "lower")
            tests["positive_utility_at_least_25/32"] = threshold(specs["G"], Q(25,32), "lower")
            tests["positive_selected_risk_at_most_5/32"] = threshold(specs["selected_risk"], Q(5,32), "upper")
    return {**base, "disposition":"valid", "means":{key:str(value) for key,value in actual.items()},
            "forecasts":{key:str(value) for key,value in predicted.items()}, "intervals": specs,
            "equivalence": {key: equivalent(predicted[key], interval) if interval else "EMPIRICALLY_INCONCLUSIVE"
                            for key, interval in specs.items()},
            "thresholds":tests}


def overlapping(one, other):
    if not one or not other:
        return None
    left, right = map(Q, one)
    low, high = map(Q, other)
    return max(left, low) <= min(right, high)


def aggregate(rows):
    output = {}
    for role in ("primary","independent"):
        for arm in ARMS:
            subset = [x for x in rows if (x["role"],x["arm"],x["disposition"])==(role,arm,"valid")]
            if not subset:
                continue
            totals = Counter()
            threshold_totals = {}
            equivalence_totals = Counter()
            for x in subset:
                totals.update(x["counts"])
                equivalence_totals.update(x["equivalence"].values())
                for endpoint, disposition in x["thresholds"].items():
                    threshold_totals.setdefault(endpoint, Counter())[disposition] += 1
            values = normalized(totals, totals["attempts"])
            risk = [Q(x["means"]["selected_risk"]) for x in subset if "selected_risk" in x["means"]]
            intervals = [x["intervals"]["selected_risk"] for x in subset if x["intervals"]["selected_risk"]]
            output[f"{role}/{arm}"] = {
                "aggregate_counts": dict(totals),
                "descriptive_means": {k:str(v) for k,v in values.items()},
                "descriptive_pooled_selected": str(Q(totals["VI"],totals["I"])) if totals["I"] else None,
                "max_sampled_selected_risk": str(max(risk)) if risk else None,
                "selected_interval_upper_max": str(max(Q(i[1]) for i in intervals)) if intervals else None,
                "separate_valid_cells": len(subset),
                "forecast_equivalence": dict(equivalence_totals),
                "thresholds": {k:dict(v) for k,v in threshold_totals.items()},
            }
    return output


def independent_cells(report):
    rows = []
    for raw in report["cells"]:
        totals = raw["counts"]
        translated = {k: totals.get(k, 0) for k in ("wrong", "I", "V", "VI")}
        translated.update({"G2": totals.get("G_halves",0), "cost8": totals.get("cost_eighths",0),
                           "attempts": raw["planned"], "valid": raw["valid"], "invalid": raw["invalid"]})
        if translated["I"] != raw["issued"] or 8*translated["VI"]-3*translated["I"] != totals.get("Z_eighths",0):
            raise ValueError("independent sufficient statistics disagree")
        rows.append({"world": raw["id"], "arm": raw["arm"], "counts": translated})
    return {"cells": rows}


def analyze(opening, primary, independent):
    independent = independent_cells(independent)
    world_by_id = {row["id"]:row for row in opening["worlds"]}
    expected = {(world, arm) for world in world_by_id for arm in ARMS}
    matrices = {}
    for name, report in (("primary",primary),("independent",independent)):
        keys = [(row["world"],row["arm"]) for row in report["cells"]]
        if len(keys)!=len(expected) or set(keys)!=expected:
            raise ValueError(f"{name} data do not match the preregistered cells")
        matrices[name] = {(record["world"],record["arm"]):each_cell(name, record, world_by_id[record["world"]])
                          for record in report["cells"]}
    connections = []
    for ident in sorted(expected):
        p, r = matrices["primary"][ident], matrices["independent"][ident]
        if p["disposition"] != "valid" or r["disposition"] != "valid":
            connections.append({"world":ident[0],"arm":ident[1],"invalid":True})
        else:
            connections.append({"world":ident[0],"arm":ident[1],
                                "overlap":{key:overlapping(val,r["intervals"][key])
                                           for key,val in p["intervals"].items()}})
    all_rows = [row for keyed in matrices.values() for row in keyed.values()]
    return {"study_round":opening["round"], "K":K, "eta":str(ETA), "absolute_radius":str(RHO),
            "equivalence_tolerance":str(TOLERANCE), "cells":all_rows, "independent_overlaps":connections,
            "aggregates":aggregate(all_rows)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("opening",type=Path)
    parser.add_argument("primary",type=Path)
    parser.add_argument("independent",type=Path)
    parser.add_argument("output",type=Path)
    args = parser.parse_args()
    answer = analyze(load(args.opening), load(args.primary), load(args.independent))
    with args.output.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(answer, handle, indent=2, sort_keys=True)
        handle.write("\n")
