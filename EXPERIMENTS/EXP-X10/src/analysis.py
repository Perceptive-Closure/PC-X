"""Exact finite monitor comparison, audit synthesis and held-out statistics."""
from collections import Counter
from fractions import Fraction as F
from itertools import combinations, permutations, product
from math import log, sqrt

from routing import Fixture, audit_card, execute, quality_label

METRICS = ("risk", "alarm", "miss", "false_alarm")


def candidates(spec, balanced=True):
    regimes = spec["regimes"]
    if balanced:
        assignments = permutations(regimes)
    else:
        assignments = product(regimes, repeat=len(spec["units"]))
    return [
        tuple(Fixture(regime, revision) for regime, revision in zip(order, stock))
        for order in assignments
        for stock in product(spec["revisions"], repeat=len(spec["units"]))
    ]


def visible_law(spec, stratum, control=False):
    return Counter(execute(stratum, ticket, control).transcript() for ticket in range(spec["tickets"]))


def exact_cells(spec, fixture):
    """Enumerate the reference card directly, using an independent tray/alarm formula."""
    n = spec["tickets"]
    by_stratum = {}
    for stratum in spec["strata"]:
        counters = Counter()
        card = spec["lane_reference"][fixture.regime][fixture.revision][stratum]
        for ticket, lane in enumerate(card):
            predicted_path = "EEWW"[ticket % 4]
            alarm = ticket in (0, 6, 12, 18)
            violation = predicted_path != lane
            counters.update(indicators(violation, alarm))
        by_stratum[stratum] = {metric: F(counters[metric], n) for metric in METRICS}
    return by_stratum


def indicators(violation, alarm):
    return {
        "risk": int(violation), "alarm": int(alarm),
        "miss": int(violation and not alarm), "false_alarm": int(alarm and not violation),
    }


def mixtures(spec, cells):
    return {
        context: {
            metric: sum(F(weight) * cells[stratum][metric] for stratum, weight in weights.items())
            for metric in METRICS
        }
        for context, weights in spec["contexts"].items()
    }


def targets(spec, fixture):
    context_values = mixtures(spec, exact_cells(spec, fixture)).values()
    return tuple(max(row[metric] for row in context_values) for metric in ("risk", "miss"))


def judge(spec, values):
    return tuple(bool(value <= F(spec[f"{metric}_threshold"])) for metric, value in zip(("violation", "miss"), values))


def signatures(spec, rows):
    fixture_cache = {
        Fixture(regime, rev): judge(spec, targets(spec, Fixture(regime, rev)))
        for regime, rev in product(spec["regimes"], spec["revisions"])
    }
    return {row: tuple(fixture_cache[fixture] for fixture in row) for row in rows}


def ask(spec, row, query):
    unit, kind = query
    return audit_card(spec, row[spec["units"].index(unit)], kind)


def partitions(spec, rows, queries):
    groups = {}
    for row in rows:
        answers = tuple(ask(spec, row, q) for q in queries)
        groups.setdefault(answers, []).append(row)
    return groups


def uniform_certificate(spec, rows, queries, outcomes):
    by_cost = []
    for amount in range(len(queries) + 1):
        for subset in combinations(queries, amount):
            cost = sum(spec["audit_costs"][query[1]] for query in subset)
            by_cost.append((cost, subset))
    for cost, subset in sorted(by_cost):
        if all(len({outcomes[row] for row in group}) == 1 for group in partitions(spec, rows, subset).values()):
            return cost, subset
    raise ValueError("The permitted interface does not identify the target")


def fixed_acquisition_cost(spec, rows, real, order, outcomes):
    cost = 0
    for query in order:
        if len({outcomes[row] for row in rows}) <= 1:
            break
        answer = ask(spec, real, query)
        rows = [row for row in rows if ask(spec, row, query) == answer]
        cost += spec["audit_costs"][query[1]]
    return cost


def target_pairs(rows, outcomes):
    return sum(outcomes[left] != outcomes[right] for left, right in combinations(rows, 2))


def greedy_cost(spec, rows, real, queries, outcomes):
    available = list(queries)
    total = 0
    while (pairs := target_pairs(rows, outcomes)):
        best = None
        for query in available:
            groups = partitions(spec, rows, (query,))
            worst = max(target_pairs(group, outcomes) for group in groups.values())
            choice = (-F(pairs - worst, spec["audit_costs"][query[1]]), query)
            if best is None or choice < best:
                best = choice
        _, query = best
        rows = partitions(spec, rows, (query,))[(ask(spec, real, query),)]
        total += spec["audit_costs"][query[1]]
        available.remove(query)
    return total


def verify_exact(spec):
    rows = candidates(spec)
    outcomes = signatures(spec, rows)
    queries = tuple(sorted(product(spec["units"], spec["audit_costs"])))
    cost, chosen = uniform_certificate(spec, rows, queries, outcomes)
    full_cost, full_queries = uniform_certificate(spec, rows, queries, {row: row for row in rows})
    seen = 0
    law_summary = {}
    for stratum in spec["strata"]:
        base_law = visible_law(spec, stratum)
        control_law = visible_law(spec, stratum, True)
        assert base_law != control_law, "Reader control did not change the visible law"
        law_summary[stratum] = {
            "support": len(base_law), "tickets": sum(base_law.values()),
            "alarm": str(F(sum(n for trace, n in base_law.items() if trace[-1]), spec["tickets"])),
            "control_alarm": str(F(sum(n for trace, n in control_law.items() if trace[-1]), spec["tickets"])),
            "trace_counts": [[list(trace), n] for trace, n in sorted(base_law.items())],
        }
        for row in rows:
            for fixture in row:
                observed = Counter()
                integrated = Counter()
                card = spec["lane_reference"][fixture.regime][fixture.revision][stratum]
                for ticket in range(spec["tickets"]):
                    visible = execute(stratum, ticket)
                    observed[visible.transcript()] += 1
                    integrated.update(indicators(quality_label(visible.tray, card[ticket]), visible.alarm))
                    seen += 1
                assert observed == base_law
                assert {key: F(integrated[key], spec["tickets"]) for key in METRICS} == exact_cells(spec, fixture)[stratum]
    witness_left = rows[0]
    witness_right = next(row for row in rows if outcomes[row] != outcomes[witness_left])
    cheapest = tuple(sorted(queries, key=lambda q: (spec["audit_costs"][q[1]], q)))
    cf_cost = max(fixed_acquisition_cost(spec, rows, real, cheapest, outcomes) for real in rows)
    random_costs = [
        fixed_acquisition_cost(spec, rows, real, order, outcomes)
        for order in permutations(queries)
        for real in rows
    ]
    greedy = max(greedy_cost(spec, rows, real, queries, outcomes) for real in rows)
    stock_queries = tuple(query for query in queries if query[1] == "label_revision")
    stock_groups = partitions(spec, rows, stock_queries).values()
    assert all(len({outcomes[row] for row in group}) > 1 for group in stock_groups)
    return {
        "candidate_count": len(rows), "checked_traces": seen, "monitor_visible_equivalent": True,
        "law": law_summary, "query_subsets_considered": 2 ** len(queries),
        "initial_joint_threshold_signatures": sorted(set(outcomes.values())),
        "witness": [{
            "installation": {unit: [f.regime, f.revision] for unit, f in zip(spec["units"], row)},
            "targets": {unit: [str(value) for value in targets(spec, f)] for unit, f in zip(spec["units"], row)},
            "threshold_signature": outcomes[row],
        } for row in (witness_left, witness_right)],
        "minimum_audit": {"cost": cost, "queries": chosen},
        "full_contract": {"cost": full_cost, "queries": full_queries},
        "baseline_costs": {"cheapest_first_worst": cf_cost,
                           "random_order_mean": str(F(sum(random_costs), len(random_costs))),
                           "random_order_worst": max(random_costs), "greedy_worst": greedy,
                           "exhaustive": sum(spec["audit_costs"][query[1]] for query in queries)},
        "stock_only_groups_unresolved": len(stock_groups),
    }


def interval(values):
    return [str(min(values)), str(max(values))]


def audit_bounds(spec, rows):
    result = {}
    for index, unit in enumerate(spec["units"]):
        models = [mixtures(spec, exact_cells(spec, row[index])) for row in rows]
        contexts = {}
        for context in spec["contexts"]:
            values = [model[context] for model in models]
            eta = max(row["miss"] for row in values)
            beta = max(row["miss"] / row["risk"] if row["risk"] else F(1) for row in values)
            alarm = max(row["alarm"] for row in values)
            additive = min(F(1), alarm + eta)
            conditional = min(F(1), alarm / (1 - beta)) if beta < 1 else None
            assert all(row["risk"] <= additive and (conditional is None or row["risk"] <= conditional) for row in values)
            contexts[context] = {
                "risk_envelope": interval([row["risk"] for row in values]),
                "miss_envelope": interval([row["miss"] for row in values]),
                "eta": str(eta), "beta": str(beta), "alarm": str(alarm),
                "additive_upper": str(additive),
                "conditional_upper": str(conditional) if conditional is not None else None,
            }
        max_values = [targets(spec, row[index]) for row in rows]
        result[unit] = {
            "contexts": contexts,
            "max_risk_values": [str(x) for x in sorted({row[0] for row in max_values})],
            "max_miss_values": [str(x) for x in sorted({row[1] for row in max_values})],
        }
    return result


def predict(spec, pre_audit, receipt):
    chosen = tuple(tuple(query) for query in receipt["queries"])
    if chosen != tuple(tuple(query) for query in pre_audit["minimum_audit"]["queries"]):
        raise ValueError("Receipt is not for the frozen minimum audit")
    answers = tuple(receipt["answers"])
    rows = partitions(spec, candidates(spec), chosen).get(answers, [])
    if not rows:
        raise ValueError("No admissible compatible installation")
    witnesses = signatures(spec, rows)
    distinct = set(witnesses.values())
    if len(distinct) != 1:
        raise ValueError("The acquired evidence does not identify the target")
    signature = next(iter(distinct))
    ablation = partitions(spec, candidates(spec, balanced=False), chosen)[answers]
    return {
        "assignment_commitment_sha256": receipt["assignment_commitment_sha256"],
        "pre_audit_commit": receipt["pre_audit_commit"],
        "queries": chosen,
        "answers": answers,
        "compatible_installations": len(rows),
        "judgments": {unit: dict(zip(("risk", "miss"), signature[index]))
                      for index, unit in enumerate(spec["units"])},
        "prediction": audit_bounds(spec, rows),
        "without_balanced_enrollment": {
            "compatible_installations": len(ablation),
            "joint_signatures": sorted(set(signatures(spec, ablation).values())),
        },
    }


def checked_measurement(spec, rows, assignment, prediction):
    """Recompute both instruments from the recorded route inputs and validate trial coverage."""
    counts, unknown, seen = {}, Counter(), set()
    for row in rows:
        unit, stratum, index = row["unit"], row["stratum"], row["index"]
        key = unit, stratum
        if unit not in assignment or stratum not in spec["strata"]:
            raise ValueError("Unregistered held-out cell")
        if type(index) is not int or not 0 <= index < spec["heldout_per_unit_stratum"] or (*key, index) in seen:
            raise ValueError("Invalid or duplicate held-out index")
        seen.add((*key, index))
        ticket = row["ticket"]
        if type(ticket) is not int or not 0 <= ticket < spec["tickets"]:
            raise ValueError("Invalid ticket")
        orientation = int(ticket % 4 >= 2)
        alarm = ticket in (0, 6, 12, 18)
        actual = "EEWW"[ticket % 4]
        expected = spec["lane_reference"][assignment[unit].regime][assignment[unit].revision][stratum][ticket]
        if row["visible"] != [stratum, ticket % 6, orientation, alarm, actual, alarm]:
            raise ValueError("Invalid monitor-visible route")
        if row["trusted_lane"] != expected or row["trusted_label"] is not (actual != expected):
            raise ValueError("Invalid independently scored route")
        cell = counts.setdefault(key, Counter())
        cell.update(indicators(actual != expected, alarm))
        cell["n"] += 1
        if stratum == "oversize":
            # The missing-coverage ablation removes the independent label only.
            # The optical monitor and complete-condition record remain unchanged.
            assert quality_label(actual, None) is None
            unknown[(unit, alarm)] += 1

    n = spec["heldout_per_unit_stratum"]
    expected_cells = set(product(spec["units"], spec["strata"]))
    if set(counts) != expected_cells or any(cell["n"] != n for cell in counts.values()):
        raise ValueError("Incomplete held-out coverage")
    alpha = float(F(spec["familywise_alpha"]))
    half_width = sqrt(log(2 * len(expected_cells) * len(METRICS) / alpha) / (2 * n))
    unit_results = {}
    for unit in spec["units"]:
        cell_records = {}
        for stratum in spec["strata"]:
            tally = counts[(unit, stratum)]
            values = {metric: tally[metric] / n for metric in METRICS}
            bounds = {metric: [max(0, p - half_width), min(1, p + half_width)] for metric, p in values.items()}
            if tally["risk"] > tally["alarm"] + tally["miss"]:
                raise ValueError("Event decomposition failed")
            cell_records[stratum] = {"counts": dict(tally), "rates": values, "intervals": bounds,
                                     "false_negative_denominator": tally["risk"],
                                     "conditional_false_negative": tally["miss"] / tally["risk"] if tally["risk"] else None}

        contexts = {}
        for context, weights in spec["contexts"].items():
            estimate = {
                metric: sum(float(F(weight)) * cell_records[stratum]["rates"][metric] for stratum, weight in weights.items())
                for metric in METRICS
            }
            bounds = {
                metric: [sum(float(F(weight)) * cell_records[stratum]["intervals"][metric][side]
                             for stratum, weight in weights.items()) for side in (0, 1)]
                for metric in METRICS
            }
            m_lo, m_hi = bounds["miss"]
            r_lo, r_hi = bounds["risk"]
            overlaps = {}
            for metric in ("risk", "miss"):
                fore_lo, fore_hi = map(F, prediction["prediction"][unit]["contexts"][context][f"{metric}_envelope"])
                overlaps[metric] = float(fore_lo) <= bounds[metric][1] and bounds[metric][0] <= float(fore_hi)
            routine_weight = float(F(weights["routine"]))
            excess_weight = float(F(weights["oversize"]))
            abstain_bounds = [
                routine_weight * cell_records["routine"]["intervals"]["risk"][0],
                routine_weight * cell_records["routine"]["intervals"]["risk"][1] + excess_weight,
            ]
            contexts[context] = {
                "rates": estimate, "intervals": bounds,
                "conditional_false_negative": estimate["miss"] / estimate["risk"] if estimate["risk"] else None,
                "conditional_interval": [m_lo / r_hi if r_hi else 0, min(1, m_hi / r_lo) if r_lo else 1],
                "forecast_overlap": overlaps,
                "missing_oversize_risk_interval": abstain_bounds,
                "missing_oversize_conditional_false_negative": None,
                "missing_oversize_miss_interval": [
                    routine_weight * cell_records["routine"]["intervals"]["miss"][0],
                    routine_weight * cell_records["routine"]["intervals"]["miss"][1]
                    + excess_weight * (1 - cell_records["oversize"]["intervals"]["alarm"][0]),
                ],
            }
        decisions = {}
        for metric, threshold_key in (("risk", "violation_threshold"), ("miss", "miss_threshold")):
            worst = [max(result["intervals"][metric][side] for result in contexts.values()) for side in (0, 1)]
            threshold = float(F(spec[threshold_key]))
            decision = True if worst[1] <= threshold else False if worst[0] > threshold else None
            decisions[metric] = {
                "maximum_context_interval": worst, "meets_threshold": decision,
                "forecast_confirmed": decision is prediction["judgments"][unit][metric],
            }
        unit_results[unit] = {
            "cells": cell_records, "contexts": contexts, "threshold_decisions": decisions,
            "missing_oversize_labels": {"alarms": unknown[(unit, True)], "no_alarm": unknown[(unit, False)]},
            "alarm_only_meets_risk": max(row["intervals"]["alarm"][1] for row in contexts.values()) <= float(F(spec["violation_threshold"])),
            "routine_only_meets_risk": cell_records["routine"]["intervals"]["risk"][1] <= float(F(spec["violation_threshold"])),
            "routine_only_point_meets_risk": cell_records["routine"]["rates"]["risk"] <= float(F(spec["violation_threshold"])),
        }
    return {
        "heldout_trials": len(seen), "cell_indicator_family_size": len(expected_cells) * len(METRICS),
        "alpha": alpha, "hoeffding_half_width": half_width, "units": unit_results,
        "threshold_confirmations": sum(item["forecast_confirmed"] for unit in unit_results.values()
                                       for item in unit["threshold_decisions"].values()),
        "forecast_envelope_overlaps": sum(agree for unit in unit_results.values()
                                          for context in unit["contexts"].values()
                                          for agree in context["forecast_overlap"].values()),
        "alarm_only_false_certifications": sum(unit["alarm_only_meets_risk"] and unit["threshold_decisions"]["risk"]["meets_threshold"] is False
                                               for unit in unit_results.values()),
    }
