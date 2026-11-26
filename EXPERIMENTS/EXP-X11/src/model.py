"""Exact finite predictions and acquisition costs, separate from the exercised sandbox."""

from collections import defaultdict
from fractions import Fraction
from itertools import combinations, product
from random import Random

from analysis import clearance, fidelity_verdict, threshold_verdict
from common import runner_sha
from verify import (exhaustive_public_support, exhaustive_scored_counts, paired_support,
                    pulse_controls, verify_pulse)


def predicted_capacity(protocol, placement, arm):
    return protocol["disturbed_capacity" if placement == arm else "normal_capacity"]


def exact_risk(protocol, recipe, service):
    states = {(0, 0): 1}
    previous = "regular"
    for request in recipe:
        successors = defaultdict(int)
        count_bulk = 1 + int(request == "surge") + int(previous == "surge")
        base_load = 3 if request == "surge" else 2
        for (backlog, backlogged_ticks), count in states.items():
            for adjustment, action_count in ((-1, count_bulk), (0, protocol["tickets"] - count_bulk)):
                for jitter in (0, 1):
                    remaining = max(0, backlog + base_load + adjustment + jitter - service)
                    successors[remaining, backlogged_ticks + (remaining > 0)] += (
                        count * action_count * (protocol["tickets"] // 2)
                    )
        states = successors
        previous = request
    events = sum(count for (_, late), count in states.items()
                 if late >= protocol["label_backlogged_rounds"])
    return Fraction(events, sum(states.values()))


def candidate_predictions(protocol, calibration):
    forecasts = {}
    support = {}
    counts = {}
    for placement in protocol["ports"]:
        reference = {
            name: exact_risk(protocol, recipe, protocol["normal_capacity"])
            for name, recipe in protocol["contexts"].items()
        }
        forecasts[placement] = {}
        support[placement] = {}
        counts[placement] = {}
        for arm in protocol["arms"]:
            capacity = predicted_capacity(protocol, placement, arm)
            if arm in protocol["ports"] and capacity != calibration[placement][f"{arm}_capacity"]["value"]:
                raise ValueError("Model capacity differs from isolated pulse")
            arm_risk = {}
            paired_diff = {}
            support[placement][arm] = {}
            counts[placement][arm] = {}
            for name, recipe in protocol["contexts"].items():
                predicted = exact_risk(protocol, recipe, capacity)
                hits, total = exhaustive_scored_counts(protocol, recipe, placement, arm)
                if predicted != Fraction(hits, total):
                    raise ValueError("Model and independently scored exhaustive bank disagree")
                counts[placement][arm][name] = [hits, total]
                arm_risk[name] = predicted
                if arm == "original":
                    continue
                difference = predicted - reference[name]
                paired = paired_support(protocol, placement, arm, recipe)
                bound = min(Fraction(1), Fraction(sum(paired["max_first_mismatch_counts"]),
                                                   paired["tickets_per_state"]))
                if abs(difference) > bound or (capacity == protocol["normal_capacity"] and bound != 0):
                    raise ValueError("Invalid transport bound")
                support[placement][arm][name] = {**paired, "union_risk_bound": str(bound)}
                paired_diff[name] = difference
            status = fidelity_verdict([(d, d) for d in paired_diff.values()],
                                      Fraction(protocol["fidelity_margin"]))
            forecasts[placement][arm] = {
                "risk": {name: str(p) for name, p in arm_risk.items()},
                "contrast": {name: str(d) for name, d in paired_diff.items()},
                "threshold": threshold_verdict([(p, p) for p in arm_risk.values()],
                                               Fraction(protocol["risk_threshold"])),
                "fidelity": "reference" if arm == "original" else status,
                "intervention": ("disturbance" if arm == placement else "passive_logger")
                if arm in protocol["ports"] else arm,
            }
    return forecasts, support, counts


def acquisition(protocol, calibrations, forecasts):
    costs = protocol["query_costs"]
    queries = tuple(sorted(costs))
    candidates = tuple(protocol["ports"])
    targets = {
        case: tuple((arm, outcome["fidelity"], outcome["threshold"])
                    for arm, outcome in forecasts[case].items()) for case in candidates
    }

    def signature(case, fields):
        return tuple(calibrations[case][query]["value"] for query in fields)

    def partition_identifies(fields):
        parts = {}
        for case in candidates:
            observed = signature(case, fields)
            if observed in parts and targets[case] != parts[observed]:
                return False
            parts[observed] = targets[case]
        return True

    opposing = [(a, b) for a, b in combinations(candidates, 2) if targets[a] != targets[b]]
    if not opposing:
        raise ValueError("No verified ambiguity witness")

    feasible = []
    checked = 0
    for size in range(len(queries) + 1):
        for fields in combinations(queries, size):
            by_partition = partition_identifies(fields)
            by_pairs = all(any(signature(a, [query]) != signature(b, [query]) for query in fields)
                           for a, b in opposing)
            if by_partition != by_pairs:
                raise ValueError("Certificate verifiers disagree")
            checked += 1
            if by_partition:
                feasible.append((sum(costs[query] for query in fields), fields))
    minimum_cost, selected = min(feasible)

    def stopping(order):
        used = []
        for query in order:
            used.append(query)
            if partition_identifies(used):
                break
        return {"queried": used, "cost": sum(costs[query] for query in used),
                "identified": partition_identifies(used)}

    greedy = sorted(
        queries,
        key=lambda query: (-Fraction(sum(signature(a, [query]) != signature(b, [query])
                                         for a, b in opposing), costs[query]), costs[query], query),
    )
    baselines = {
        "display_only": stopping(["display_slots"]),
        "cheapest_first": stopping(sorted(queries, key=lambda query: (costs[query], query))),
        "seeded_random": stopping(Random(protocol["random_query_baseline_seed"]).sample(queries, len(queries))),
        "greedy_separation_per_cost": stopping(greedy),
        "all_queries": {"queried": queries, "cost": sum(costs.values()), "identified": True},
    }
    return {"selected": selected, "minimum_uniform_cost": minimum_cost, "subsets_checked": checked,
            "identifying_subsets": len(feasible), "opposite_verdict_candidate_pairs": opposing,
            "baselines": baselines}


def envelope(protocol, forecasts):
    result = {}
    for arm in protocol["arms"]:
        retained = [predict[arm] for predict in forecasts.values()]
        arm_bounds = {}
        for metric in ("risk", "contrast"):
            arm_bounds[metric] = {}
            for context in retained[0][metric]:
                values = [Fraction(arm_prediction[metric][context]) for arm_prediction in retained]
                arm_bounds[metric][context] = [str(min(values)), str(max(values))]
        result[arm] = {
            **arm_bounds,
            "compatible_fidelity": sorted({p["fidelity"] for p in retained}),
            "compatible_threshold": sorted({p["threshold"] for p in retained}),
        }
        for property_name in ("fidelity", "threshold"):
            possibilities = result[arm][f"compatible_{property_name}"]
            result[arm][f"{property_name}_decision"] = (
                possibilities[0] if len(possibilities) == 1 else "abstain"
            )
    return result


def pre_audit(protocol):
    calibrations = pulse_controls(protocol)
    public = exhaustive_public_support(protocol, calibrations)
    forecasts, support, counts = candidate_predictions(protocol, calibrations)
    clearances = [clearance(protocol, item) for item in forecasts.values()]
    impossible = {"start": [0, 0], "supplied": protocol["pulse_work"], "completed": 1,
                  "end": [1, protocol["pulse_work"] - 1]}
    try:
        verify_pulse(protocol, "probe_a_capacity", impossible)
    except ValueError:
        pass
    else:
        raise ValueError("Corrupt-anchor control was not rejected")
    return {
        "runner_sha256": runner_sha(),
        "source_pins": protocol["sources"],
        "calibration_controls": calibrations,
        "public_support": public,
        "coupling_support": support,
        "exact_predictions": forecasts,
        "exact_independently_scored_counts": counts,
        "audit": acquisition(protocol, calibrations, forecasts),
        "not_queried": envelope(protocol, forecasts),
        "measurement_clearance": clearances[0],
        "inconsistent_anchor_control": "rejected",
    }
