"""Rescore native and sandbox ledgers without importing the original runners."""

from collections import Counter, defaultdict
from fractions import Fraction as F
from functools import cache
import gzip
from hashlib import sha256
from itertools import product
import json
from math import exp
from random import Random

from falsify import radius
from verify_exact import adaptive_value, ensure, partition, partition_costs, read

TOLERANCE = 1e-12


def matches(a, b):
    return abs(float(a) - float(b)) <= TOLERANCE


def interval(value, half, low=0, high=1):
    return [max(low, value - half), min(high, value + half)]


def overlap(first, second):
    return max(first[0], second[0]) <= min(first[1], second[1])


def threshold(bounds, limit):
    return True if max(b[1] for b in bounds) <= limit else False if max(b[0] for b in bounds) > limit else None


def load_ledger(path):
    contents = path.read_bytes()
    data = gzip.decompress(contents) if path.suffix == ".gz" else contents
    return sha256(data).hexdigest(), (json.loads(line) for line in data.splitlines())


def mark_index(seen, cell, index, n):
    key = (*cell, index)
    ensure(type(index) is int and 0 <= index < n and key not in seen, (cell, "duplicate/invalid index", index))
    seen.add(key)


def opa_decision(raw, request):
    user, method, subject = request
    expected_stdin = {"user": user, "method": method, "path": ["finance", "salary", subject]}
    ensure(json.loads(raw["stdin"]) == expected_stdin, ("OPA input", request))
    staff = {"bob": {"alice"}, "betty": {"charlie"}}
    expected = method == "GET" and (subject == user or subject in staff.get(user, ()))
    output = json.loads(raw["stdout"])["result"][0]["expressions"][0]
    ensure(raw["returncode"] == 0 and not raw["stderr"] and output["value"] is expected
           and raw["decision"] is expected, ("OPA scoring", request))
    return expected


def x06_fiber(checkpoint, targets):
    histories = ((), ("ticket:0",), ("ticket:1",), ("review:0",), ("review:1",),
                 ("ticket:0", "review:0"), ("ticket:1", "review:1"))
    worlds = ({0, 1, 3, 5}, {0, 2, 4, 6})
    selected = checkpoint["PR"][histories.index(tuple(checkpoint["H"]))]
    represented = {index for index, label in enumerate(checkpoint["PR"]) if label == selected}
    return {target for compatible, target in zip(worlds, targets, strict=True) if compatible & represented}


def verify_x06(package):
    spec = read(package / "config" / "protocol.json")
    results = package / "results"
    raw, summary, forecast, preaudit = (read(results / name) for name in
        ("native.json", "summary.json", "forecast.json", "preaudit.json"))
    queries = dict(preaudit["queries"])
    query_names = list(queries)
    tables = [{
        "identity": row["id"], "answers": [row["answers"][q] for q in query_names],
        "target": tuple(row["prediction"][unit]["holds"] for unit in sorted(row["prediction"])),
    } for row in preaudit["completions"]]
    outcome_set = {"".join(str(int(v)) for v in row["target"]) for row in tables}
    ensure(len(outcome_set) == len(preaudit["joint_identified_set"]), "X06 exact target cardinality")
    status, optimum, choices = partition_costs(tables, tuple(queries.values()))
    ensure(status == "CERTIFIED" and optimum == preaudit["audit_cost"], "X06 target partition optimum")
    ensure(tuple(sorted(query_names.index(q) for q in preaudit["selected"])) in choices, "X06 selected queries")
    count = Counter()
    predictions = {}
    for stratum in spec["strata"]:
        fields = stratum["requests"]
        for member in (1, 2):
            name = f"{stratum['id']}-{member}"
            unit = raw["units"][name]
            decisions = [opa_decision(row, request)
                         for row, request in zip(unit["unrestricted"], fields, strict=True)]
            count.update({"allow": sum(decisions), "deny": len(decisions) - sum(decisions)})
            ensure(all(x06_fiber(node, decisions) == {True, False} for node in unit["received"]),
                   (name, "initial ambiguity"))
            costs = []
            for freeze in spec["freeze_order"]:
                finite = []
                for action in unit["freeze_conditions"][freeze]:
                    cost = 1 if action["action"] == "publish" else stratum["backup_cost"]
                    ensure(action["cost"] == cost, (name, action, "cost"))
                    touched = set()
                    for before, after in zip(unit["received"], action["staged"], strict=True):
                        if set(before["H"]) != set(after["H"]):
                            touched.add("E")
                        if partition(before["PR"]) != partition(after["PR"]):
                            touched.add("R")
                        if set(before["authority"]) != set(after["authority"]):
                            touched.add("A")
                    enabled = not touched.intersection(freeze)
                    ensure(enabled is action["committed"] and touched == set(action["touch"]),
                           (name, freeze, "atomic resource footprint"))
                    if enabled:
                        observed = [opa_decision(row, request) for row, request in
                                    zip(action["native"], fields, strict=True)]
                        count.update({"allow": sum(observed), "deny": len(observed) - sum(observed)})
                        if all(len(x06_fiber(node, observed)) == 1 for node in action["staged"]):
                            finite.append(cost)
                    else:
                        ensure(not action["native"], (name, freeze, "blocked atom executed"))
                        count["blocked"] += 1
                costs.append(min(finite) if finite else "inf")
            r_cost = costs[spec["freeze_order"].index("R")]
            verdict = type(r_cost) is int and r_cost <= spec["primary_budget"]
            predictions[name] = {"holds": verdict, "signature": costs}
    ensure(predictions == summary["measured"] == forecast["predictions"], "X06 exact cost/forecast vector")
    ensure(count["blocked"] == summary["atomic_actions_blocked"]
           and count["allow"] == summary["heldout_native_allow"]
           and count["deny"] == summary["heldout_native_deny"], "X06 aggregate")
    failures = [unit for unit, value in predictions.items() if not value["holds"]]
    ensure(set(failures) == set(summary["conventional_errors"]), "X06 terminal-only controls")
    for row, frozen in zip(raw["development"][:-1], spec["development_controls"], strict=True):
        ensure(opa_decision(row["native"], frozen["request"]) is frozen["expected"], "X06 development")
    invalid = raw["development"][-1]["native"]
    ensure(invalid["returncode"] != 0 and invalid["decision"] is None, "X06 input diagnostic")
    return {
        "native_trace_sha256": sha256((results / "native.json").read_bytes()).hexdigest(),
        "native_counts": dict(count), "development_outcomes": len(raw["development"]),
        "predictions": predictions, "minimum_target_audit_cost": optimum,
        "finite_target_signature_count": len(outcome_set), "terminal_only_false_certifications": failures,
    }


def parcel_limits(spec, selection, site, request, retried):
    profile, feeder = selection
    policy = spec[site]
    base = policy["base_manual"][profile] if site == "floor" else policy["base_manual"]
    count = base + (request == "normal") * policy["normal_bonus"] + retried * policy["retry_bonus"]
    deliveries = policy["delivery"][feeder] if site == "floor" else policy["delivery"]
    return count, deliveries


def parcel_route(spec, selection, site, recipe, draws):
    retries = []
    previous = False
    for action, (policy, facility) in zip(recipe, draws, strict=True):
        limit, deliver = parcel_limits(spec, selection, site, action, previous)
        lane = "manual" if policy < limit else "belt"
        previous = facility >= deliver[lane]
        retries.append([action, lane, previous, policy, facility])
    return retries


def parcel_risk(spec, selection, recipe):
    states = {(False, 0): F(1)}
    tickets = spec["tickets"]
    for request in recipe:
        next_states = defaultdict(F)
        for (last, count), mass in states.items():
            manual, deliver = parcel_limits(spec, selection, "floor", request, last)
            fail = F(manual * (tickets - deliver["manual"])
                     + (tickets - manual) * (tickets - deliver["belt"]), tickets ** 2)
            next_states[True, count + 1] += mass * fail
            next_states[False, count] += mass * (1 - fail)
        states = next_states
    return sum(prob for (_, retries), prob in states.items() if retries >= spec["violation_minimum_retry_rounds"])


def verify_x08(package, run):
    spec = read(package / "configs" / "protocol.json")
    official = read(package / "results" / "opening.json")
    forecast = read(package / "results" / "forecast.json")
    settings = official["sealed_configuration"]
    recipes = spec["deployment_recipes"]
    units = spec["enrollment"]["units"]
    selection = {unit: (settings["profiles"][unit], settings["feeders"][unit]) for unit in units}
    n = spec["fixed_sampling"]["trials_per_unit_recipe"]
    k = len(units) * len(recipes)
    alpha = F(spec["fixed_sampling"]["familywise_alpha"])
    half = radius(n, k, alpha)
    cutoff = F(spec["risk_threshold"])
    minimum_retries = spec["violation_minimum_retry_rounds"]
    data_hash, records = load_ledger(run / "replay" / "episodes.jsonl")
    ensure(data_hash == official["measurements"]["episodes_sha256"], "X08 native bytes")
    cells = defaultdict(Counter)
    seen = set()
    for row in records:
        unit, site, recipe = row["unit"], row["site"], row["recipe"]
        key = (site, unit, recipe)
        mark_index(seen, key, row["episode"], n)
        trace = row["trace"]
        ensure(all(0 <= ticket < spec["tickets"] for step in trace for ticket in step[3:]), ("X08 tickets", key))
        reconstructed = parcel_route(spec, selection[unit], site, recipes[recipe], [step[3:] for step in trace])
        ensure(trace == reconstructed, ("X08 routing/ticket readback", key))
        cells[key]["events"] += sum(step[2] for step in reconstructed) >= minimum_retries
        cells[key]["n"] += 1
    ensure(len(cells) == 2 * k and all(row["n"] == n for row in cells.values()), "X08 coverage")
    verdicts = {}
    bands = 0
    fresh = {}
    seed = "79b1ac6f701f7fc4aa748815a0b7c8f9a893303c"
    for unit in units:
        bounds = []
        for recipe, requests in recipes.items():
            row = cells[("floor", unit, recipe)]
            bound = interval(row["events"] / n, half)
            bands += overlap(bound, tuple(map(F, forecast["risk_bands"][unit][recipe])))
            bounds.append(bound)
            exact = parcel_risk(spec, selection[unit], requests)
            rng = Random(int.from_bytes(sha256(f"{seed}/{unit}/{recipe}".encode()).digest()))
            positives = 0
            for _ in range(n):
                draws = [(rng.randrange(spec["tickets"]), rng.randrange(spec["tickets"])) for _ in requests]
                trace = parcel_route(spec, selection[unit], "floor", requests, draws)
                positives += sum(step[2] for step in trace) >= minimum_retries
            fresh[f"{unit}/{recipe}"] = {
                "events": positives, "n": n, "exact_model_risk": str(exact),
                "interval": interval(positives / n, half),
                "exact_risk_in_interval": overlap(interval(positives / n, half), [exact, exact]),
            }
        verdicts[unit] = threshold(bounds, cutoff)
    for expected in official["measurements"]["measurement"]:
        cell = cells[(expected["site"], expected["unit"], expected["recipe"])]
        ensure(cell["events"] == expected["violations"] and cell["n"] == expected["trials"], "X08 raw cells")
    false = sum(not verdicts[unit] and forecast["benchmark_only_forecast"][unit] for unit in units)
    ensure(verdicts == forecast["forecast"] == official["measurements"]["native_verdict"]
           and bands == k and matches(half, official["measurements"]["half_width"])
           and false == official["measurements"]["benchmark_false_certifications"], "X08 inference")
    return {
        "raw_sha256": data_hash, "episodes": len(seen), "half_width": half, "verdicts": verdicts,
        "forecast_interval_overlaps": bands, "benchmark_only_false_certifications": false,
        "cells": {"/".join(key): dict(value) for key, value in cells.items()},
        "fresh_seed_simulation_exploratory": fresh,
    }


def sorting_limit(spec, fixture, cue, surface, previous):
    mode, key, variant = fixture
    law = spec["policy"]
    if previous is not None:
        return (law["warm_right_base"] + (cue == "gold") * law["warm_gold_bonus"]
                + (surface == "ribbed") * law["warm_ribbed_bonus"]
                + previous * law["warm_previous_right_bonus"])
    if cue == "blue":
        return law["blue_key_right"] if key == surface else law["blue_other_right"]
    if mode == "midpoint":
        return law["midpoint_gold_right"]
    return law["gold_variant_one_key_right"] if variant == 1 and key == surface else law["gold_other_right"]


def recheck_limit(spec, fixture, cue, tray):
    score = spec["station"]
    if tray == 1:
        return score["right_recheck"]
    if fixture[0] == "shift" and cue == spec["deployment_cue"]:
        return score["shift_gold_left_recheck"]
    return score["left_recheck"]


def exact_sorting_risk(spec, fixture, cue, recipe):
    @cache
    def survive(round_index, previous):
        if round_index == len(recipe):
            return F(1)
        size = spec["tickets"]
        p_right = F(sorting_limit(spec, fixture, cue, recipe[round_index], previous), size)
        return sum(
            weight * (1 - F(recheck_limit(spec, fixture, cue, tray), size)) * survive(round_index + 1, tray)
            for tray, weight in ((0, 1 - p_right), (1, p_right))
        )
    return 1 - survive(0, None)


def verify_x09(package):
    spec = read(package / "configs" / "protocol.json")
    results = package / "results"
    report = read(results / "summary.json")
    assignment = read(results / "opening.json")["private_record"]["assignment"]
    forecast = read(results / "forecast.json")["units"]
    raw_hash, raw = load_ledger(results / "raw-native.jsonl.gz")
    factor_hash, factors = load_ledger(results / "raw-factorial.jsonl.gz")
    ensure(raw_hash == report["raw"]["native"]["raw_sha256"]
           and factor_hash == report["raw"]["factorial"]["raw_sha256"], "X09 raw hashes")
    n = spec["native"]["episodes"]
    radius_native = F(spec["native"]["radius"])
    cutoff = F(spec["threshold"])
    arms = {recipe[0]: recipe for recipe in spec["recipes"]}
    seen = set()
    cells = defaultdict(Counter)
    for unit, cue, name, index, turns in raw:
        key = unit, cue, name
        mark_index(seen, key, index, n)
        previous = None
        failures = 0
        for surface, (policy, tray, station, recheck) in zip(arms[name], turns, strict=True):
            ensure(int(policy < sorting_limit(spec, assignment[unit], cue, surface, previous)) == tray
                   and int(station < recheck_limit(spec, assignment[unit], cue, tray)) == recheck,
                   (key, index, "X09 measured law"))
            previous = tray
            failures += recheck
        cells[key].update(n=1, episodes_failed=int(failures > 0), rechecks=failures)
    ensure(len(cells) == len(assignment) * len(spec["cues"]) * len(arms)
           and all(row["n"] == n for row in cells.values()), "X09 native denominators")

    factorial = defaultdict(Counter)
    factorial_n = spec["factorial"]["episodes"]
    factor_indices = set()
    width = 2 * len(spec["cues"]) * len(spec["contexts"]) * len(spec["trims"])
    for unit, index, mode, cue, surface, trim, prefix, prefix_tray, policy, tray in factors:
        mark_index(factor_indices, (unit,), index, factorial_n * width)
        previous = None
        if mode == "carry":
            first_cue, first_surface, _ = spec["warm_up"]
            previous = int(prefix < sorting_limit(spec, assignment[unit], first_cue, first_surface, None))
        else:
            ensure(mode == "reset" and prefix is None, ("X09 factorial case", mode))
        ensure(prefix_tray == previous and tray == int(policy < sorting_limit(spec, assignment[unit], cue, surface, previous)),
               (unit, index, "X09 factorial intervention"))
        factorial[unit, mode, cue, surface, trim].update(n=1, right=tray)
    ensure(len(factorial) == len(assignment) * width and all(cell["n"] == factorial_n for cell in factorial.values()),
           "X09 factorial denominators")

    factorial_half = F(spec["factorial"]["radius"])
    for (unit, *mode), observed in factorial.items():
        documented = report["factorial"][unit]["cells"]["/".join(mode)]
        bound = list(map(F, documented["interval"]))
        ensure(observed["right"] == documented["right"]
               and bound == interval(F(observed["right"], observed["n"]), factorial_half), (unit, mode, "factorial"))
    statuses = Counter()
    native = {}
    interval_overlaps = 0
    for unit, fixture in assignment.items():
        unit_report = report["native"][unit]
        native[unit] = {}
        for cue in spec["cues"]:
            bounds = []
            for recipe, requests in arms.items():
                cell = cells[unit, cue, recipe]
                expected = unit_report[cue]["conditions"][recipe]
                bound = interval(F(cell["episodes_failed"], n), radius_native)
                bounds.append(bound)
                ensure(cell["episodes_failed"] == expected["failures"] and cell["rechecks"] == expected["rechecks"]
                       and list(map(F, expected["interval"])) == bound, (unit, cue, recipe, "X09 counts"))
                ensure(exact_sorting_risk(spec, fixture, cue, requests) == F(expected["reference_risk"]),
                       (unit, cue, recipe, "exact native risk"))
                if fixture[0] == "anchored" and cue == spec["deployment_cue"]:
                    interval_overlaps += overlap(bound, list(map(F, forecast[unit]["risk_bands"][recipe])))
            decision = {True: "MEETS", False: "FAILS", None: "INCONCLUSIVE"}[threshold(bounds, cutoff)]
            ensure(decision == unit_report[cue]["verdict"], (unit, cue, "X09 verdict"))
            native[unit][cue] = decision
        actual = native[unit][spec["deployment_cue"]]
        audit = forecast[unit]["audit"]
        if fixture[0] == "anchored":
            ensure(audit["verdict"] == actual, (unit, "admitted forecast"))
            statuses["admitted_confirmed"] += 1
        elif fixture[0] == "midpoint":
            ensure(audit["status"] == "INCONSISTENT", (unit, "midpoint control"))
            statuses["detected_out_of_family"] += 1
        else:
            ensure(audit["verdict"] == "MEETS" and actual == "FAILS", (unit, "transport control"))
            statuses["false_safe_shift"] += 1

    alpha = float(F(spec["alpha"]))
    coverage = {
        "audit": 2 * len(assignment) * len(spec["queries"]) * exp(
            -2 * spec["audit"]["episodes"] * float(F(spec["audit"]["radius"])) ** 2),
        "native": 2 * len(cells) * exp(-2 * n * float(radius_native) ** 2),
        "factorial": 2 * len(factorial) * exp(-2 * factorial_n * float(factorial_half) ** 2),
    }
    ensure(all(error < alpha for error in coverage.values()), "X09 simultaneous bound")
    admitted_profiles = [fixture for fixture in spec["roster"] if fixture[0] == "anchored"]
    query_costs = [query["cost"] for query in spec["queries"]]
    rows = [{
        "identity": str(fixture),
        "answers": [sorting_limit(spec, fixture, query["cue"], query["context"], None) for query in spec["queries"]],
        "target": all(exact_sorting_risk(spec, fixture, spec["deployment_cue"], recipe) <= cutoff
                      for recipe in spec["recipes"]),
    } for fixture in admitted_profiles]
    static = partition_costs(rows, query_costs)[1]
    return {
        "native_episodes": len(seen), "factorial_draws": len(factor_indices),
        "native_raw_sha256": raw_hash, "factorial_raw_sha256": factor_hash,
        "native_verdicts": native, "gates": dict(statuses),
        "admitted_interval_overlaps": interval_overlaps, "family_error_upper_bounds": coverage,
        "model_minimax_query_cost": adaptive_value(rows, query_costs), "model_static_query_cost": static,
    }


def verify_x10(package):
    spec = read(package / "configs" / "protocol.json")
    results = package / "results"
    opening, forecast = (read(results / file) for file in ("opening.json", "forecast.json"))
    declared = opening["measurement"]
    assignment = opening["assignment"]["fixture"]
    raw_hash, observations = load_ledger(results / "episodes.jsonl.gz")
    ensure(raw_hash == declared["episode_data_sha256"], "X10 raw hash")
    n = spec["heldout_per_unit_stratum"]
    cells = defaultdict(Counter)
    seen = set()
    for row in observations:
        unit, stratum, ticket = row["unit"], row["stratum"], row["ticket"]
        mark_index(seen, (unit, stratum), row["index"], n)
        regime, revision = assignment[unit]
        alarm = ticket % 6 == 0
        actual = "E" if ticket % 4 < 2 else "W"
        reference = spec["lane_reference"][regime][revision][stratum][ticket]
        risk = actual != reference
        ensure(row["trusted_lane"] == reference and row["trusted_label"] is risk
               and row["visible"] == [stratum, ticket % 6, int(ticket % 4 >= 2), alarm, actual, alarm],
               (unit, stratum, ticket, "X10 independent label"))
        cells[unit, stratum].update(n=1, risk=risk, alarm=alarm, miss=risk and not alarm,
                                    false_alarm=alarm and not risk)
    metrics = ("risk", "alarm", "miss", "false_alarm")
    k = len(spec["units"]) * len(spec["strata"]) * len(metrics)
    half = radius(n, k, F(spec["familywise_alpha"]))
    ensure(len(cells) == len(spec["units"]) * len(spec["strata"])
           and k == declared["cell_indicator_family_size"] and matches(half, declared["hoeffding_half_width"]),
           "X10 confidence family")
    true_false = 0
    confirmed = 0
    intersections = 0
    units = {}
    for unit in spec["units"]:
        udata = declared["units"][unit]
        contexts = {}
        empirical = {}
        for context, weights in spec["contexts"].items():
            w = {name: F(weight) for name, weight in weights.items()}
            bands = {}
            empirical[context] = {}
            for metric in metrics:
                for stratum in weights:
                    recorded = udata["cells"][stratum]["counts"]
                    ensure(cells[unit, stratum] == recorded and recorded["n"] == n, (unit, stratum, "X10 count"))
                bands[metric] = [
                    sum(float(w[stratum]) * interval(cells[unit, stratum][metric] / n, half)[side]
                        for stratum in weights) for side in (0, 1)
                ]
                empirical[context][metric] = float(sum(w[stratum] * F(cells[unit, stratum][metric], n)
                                                        for stratum in weights))
                ensure(all(matches(a, b) for a, b in zip(bands[metric],
                       udata["contexts"][context]["intervals"][metric], strict=True)), (unit, context, metric))
                if metric in ("risk", "miss"):
                    predicted = forecast["prediction"][unit]["contexts"][context][f"{metric}_envelope"]
                    intersections += overlap(bands[metric], list(map(F, predicted)))
            ensure(empirical[context]["miss"] <= empirical[context]["risk"]
                   <= empirical[context]["alarm"] + empirical[context]["miss"] + TOLERANCE,
                   (unit, context, "X10 event bounds"))
            contexts[context] = bands
        decisions = {}
        for metric, name in (("risk", "violation_threshold"), ("miss", "miss_threshold")):
            verdict = threshold([value[metric] for value in contexts.values()], F(spec[name]))
            ensure(verdict is udata["threshold_decisions"][metric]["meets_threshold"], (unit, metric))
            confirmed += verdict is forecast["judgments"][unit][metric]
            decisions[metric] = verdict
        alarm_naive = threshold([row["alarm"] for row in contexts.values()], F(spec["violation_threshold"]))
        true_false += alarm_naive is True and decisions["risk"] is False
        units[unit] = {"verdicts": decisions, "context_rates": empirical}
    ensure(confirmed == declared["threshold_confirmations"] and intersections == declared["forecast_envelope_overlaps"]
           and true_false == declared["alarm_only_false_certifications"], "X10 forecast controls")
    return {
        "raw_sha256": raw_hash, "episodes": len(seen), "half_width": half, "interval_family": k,
        "confirmed": confirmed, "overlaps": intersections, "alarm_only_false_certifications": true_false,
        "units": units,
    }


def queue_arm(frames, backlog_threshold):
    balance = 0
    backlogged = 0
    for tick, frame in enumerate(frames, 1):
        arrived, served = frame[1]
        ensure(0 <= served <= balance + arrived, ("X11 invalid service", tick))
        balance = balance + arrived - served
        ensure(frame[2][0] == tick and frame[2][2] == balance, ("X11 job conservation", tick))
        backlogged += balance > 0
    return backlogged >= backlog_threshold


def verify_x11(package):
    spec = read(package / "configs" / "protocol.json")
    results = package / "results"
    opening, forecast = (read(results / name) for name in ("opening.json", "forecast.json"))
    expected = opening["analysis"]
    raw_hash, observations = load_ledger(results / "observations.jsonl.gz")
    ensure(raw_hash == expected["raw_sha256"], "X11 raw hash")
    n = spec["paired_episodes_per_context"]
    arms, contexts = spec["arms"], spec["contexts"]
    counts = defaultdict(Counter)
    seen = set()
    for block in observations:
        context = block["context"]
        mark_index(seen, (context,), block["index"], n)
        ensure(len(block["steps"]) == spec["horizon"] and set(block["arms"]) == set(arms),
               (context, "X11 arm inventory"))
        base = block["arms"]["original"]
        label = queue_arm(base, spec["label_backlogged_rounds"])
        for arm, frames in block["arms"].items():
            ensure([frame[0] for frame in base] == [frame[0] for frame in frames],
                   (context, arm, "X11 public transcript"))
            treated = queue_arm(frames, spec["label_backlogged_rounds"])
            first = next((i for i, (a, b) in enumerate(zip(base, frames, strict=True), 1)
                          if a[:3] != b[:3]), 0)
            counts[context, arm].update(n=1, events=treated, higher=treated and not label,
                                         lower=label and not treated)
            counts[context, arm][f"first_{first}"] += 1
    k = len(contexts) * (2 * len(arms) - 1)
    half = radius(n, k, F(spec["family_alpha"]))
    limit, margin = F(spec["risk_threshold"]), F(spec["fidelity_margin"])
    ensure(k == expected["confidence_family"] and matches(half, expected["risk_half_width"])
           and matches(2 * half, expected["paired_half_width"]), "X11 confidence family")
    results = {}
    for arm in arms:
        risk_bands, contrast_bands = [], []
        contrasts = {}
        for context in contexts:
            observed = counts[context, arm]
            published = expected["arms"][arm]["contexts"][context]
            ensure(observed["n"] == n and observed["events"] == published["events"]
                   and [observed[f"first_{i}"] for i in range(1, spec["horizon"] + 1)] ==
                       published["first_transition_difference_by_tick"]
                   and observed["first_0"] == published["matching_trajectory_blocks"],
                   (arm, context, "X11 ledger aggregate"))
            risk_band = interval(F(observed["events"], n), half)
            risk_bands.append(risk_band)
            predicted = F(forecast["arm_predictions"][arm]["risk"][context])
            ensure(overlap(risk_band, [predicted, predicted]), (arm, context, "X11 risk cover"))
            if arm != "original":
                delta = F(observed["higher"] - observed["lower"], n)
                band = interval(delta, 2 * half, -1, 1)
                contrast_bands.append(band)
                predicted = F(forecast["arm_predictions"][arm]["contrast"][context])
                ensure(overlap(band, [predicted, predicted]) and matches(delta, published["paired_risk_difference"])
                       and observed["higher"] == published["probe_only_events"]
                       and observed["lower"] == published["original_only_events"],
                       (arm, context, "X11 paired effect"))
                contrasts[context] = float(delta)
        risk = {True: "within_threshold", False: "above_threshold", None: "abstain"}[threshold(risk_bands, limit)]
        if not contrast_bands:
            fidelity = "reference"
        elif any(a > margin or b < -margin for a, b in contrast_bands):
            fidelity = "disturbed"
        elif all(-margin <= a and b <= margin for a, b in contrast_bands) and all(
                F(case["union_risk_bound"]) <= margin for case in forecast["coupling_bounds"][arm].values()):
            fidelity = "equivalent"
        else:
            fidelity = "abstain"
        ensure(risk == expected["arms"][arm]["threshold_verdict"]
               and fidelity == expected["arms"][arm]["fidelity_verdict"], (arm, "X11 verdict"))
        results[arm] = {"threshold": risk, "fidelity": fidelity, "paired_risk_difference": contrasts}
    return {
        "raw_sha256": raw_hash, "blocks": len(seen), "episodes": len(seen) * len(arms),
        "risk_half_width": half, "paired_half_width": 2 * half, "family_size": k, "arms": results,
        "naive_transfer_errors": [arm for arm in spec["ports"]
                                  if results[arm]["threshold"] != results["original"]["threshold"]],
    }
