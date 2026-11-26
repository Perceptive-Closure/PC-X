"""Independent controls with inputs stated directly and checked by exhaustive enumeration."""

from fractions import Fraction
from itertools import combinations, product
import json
from math import log, sqrt


def evidence_classes(worlds, queried):
    classes = {}
    for world in worlds:
        observation = tuple(world["answers"][query] for query in queried)
        classes.setdefault(observation, []).append(world)
    return classes.values()


def least_certificate(worlds, costs, local_world=None):
    queries = sorted(costs)
    sufficient = []
    for size in range(len(queries) + 1):
        for subset in combinations(queries, size):
            cells = evidence_classes(worlds, subset)
            if local_world is not None:
                cells = [cell for cell in cells if local_world in cell]
            if all(len({world["target"] for world in cell}) == 1 for cell in cells):
                sufficient.append((sum(costs[query] for query in subset), subset))
    return min(sufficient) if sufficient else None


def radius(n, family, alpha, support_width=1):
    if n < 1 or family < 1 or not 0 < alpha < 1 or support_width <= 0:
        raise ValueError("Invalid concentration-bound inputs")
    return support_width * sqrt(log(2 * family / alpha) / (2 * n))


def closure_control():
    before = {"E": 0, "R": 0}
    successors = [
        (Fraction(63, 64), {"E": 1, "R": 0}),
        (Fraction(1, 64), {"E": 1, "R": 1}),
        (Fraction(0), {"E": 9, "R": 9}),
    ]
    touch = {
        coordinate for coordinate in before
        if any(weight > 0 and after[coordinate] != before[coordinate]
               for weight, after in successors)
    }
    representative = {key for key in before if successors[0][1][key] != before[key]}
    unsupported_only = {"A": 0}
    unsupported_control = [(1, {"A": 0}), (0, {"A": 1})]
    assert not any(weight > 0 and row["A"] != unsupported_only["A"]
                   for weight, row in unsupported_control)
    assert touch == {"E", "R"} and representative == {"E"}
    return {
        "positive_support": ["63/64", "1/64"],
        "full_touch": sorted(touch),
        "representative_touch": sorted(representative),
        "complete_atomic_action_available_when_R_frozen": not bool(touch & {"R"}),
        "representative_ablation_available_when_R_frozen": not bool(representative & {"R"}),
        "zero_support_touch": [],
    }


def correlation_control():
    joint = {(-1, -1), (1, 1)}
    marginals = tuple({pair[i] for pair in joint} for i in range(2))
    rectangle = set(product(*marginals))
    functional = lambda pair: int(pair[0] != pair[1])
    exact = {functional(pair) for pair in joint}
    relaxed = {functional(pair) for pair in rectangle}
    assert exact == {0} and relaxed == {0, 1}
    return {
        "joint": sorted(joint), "relaxation_only": sorted(rectangle - joint),
        "joint_target": sorted(exact), "rectangle_target": sorted(relaxed),
    }


def certificate_control():
    worlds = [
        {"target": 0, "answers": {"x": 0, "y": 0, "z": 0, "forbidden": 0}},
        {"target": 1, "answers": {"x": 1, "y": 0, "z": 1, "forbidden": 1}},
        {"target": 2, "answers": {"x": 1, "y": 1, "z": 0, "forbidden": 2}},
    ]
    costs = {"x": 1, "y": 2, "z": 5}
    global_ = least_certificate(worlds, costs)
    local = least_certificate(worlds, costs, worlds[0])
    unrestricted = least_certificate(worlds, {**costs, "forbidden": 0})
    unresolved = least_certificate(worlds[1:], {"x": 1})
    assert global_ == (3, ("x", "y")) and local == (1, ("x",))
    assert unrestricted == (0, ("forbidden",)) and unresolved is None
    return {
        "global": global_, "local_at_first_world": local,
        "illegitimate_ablation": unrestricted, "one_query_interface": unresolved,
    }


def calibration_control():
    alpha = 0.05
    reference = radius(4, 12, alpha)
    duplicate = radius(8, 12, alpha)
    single = radius(4, 1, alpha)
    baseline, treatment = [0, 0, 1, 1], [0, 1, 1, 1]
    paired = [y - x for x, y in zip(baseline, treatment, strict=True)]
    permuted = [y - x for x, y in zip(baseline, reversed(treatment), strict=True)]
    assert duplicate < reference and single < reference
    assert sum(paired) == sum(permuted) == 1
    assert sum(value * value for value in paired) < sum(value * value for value in permuted)
    return {
        "bound_n4_k12": reference, "duplicate_denominator_n8": duplicate,
        "single_family_member": single,
        "paired_signed_block_differences": paired,
        "reordered_signed_block_differences": permuted,
        "bounded_paired_interval_half_width": radius(4, 12, alpha, 2),
        "independent_post_selection_family_false_positive_probability": 1 - (1 - alpha) ** 12,
    }


def deployment_control():
    evaluation = ["ok", "alarm", "ok", "ok"]
    alarm = [0, 1, 0, 0]
    violation = {"A": [1, 1, 1, 0], "B": [0, 1, 0, 0]}
    metrics = {}
    for world, events in violation.items():
        misses = sum(event and not raised for event, raised in zip(events, alarm, strict=True))
        metrics[world] = {
            "common_n": len(events),
            "alarm_count": sum(alarm),
            "trusted_event_count": sum(events),
            "miss_count": misses,
        }
    passive = violation["B"]
    disturbing = [1, 1, 1, 0]
    signed_effects = [b - a for a, b in zip(passive, disturbing, strict=True)]
    assert metrics["A"]["miss_count"] == 2 and metrics["B"]["miss_count"] == 0
    assert sum(signed_effects) == 2
    assert Fraction(sum(violation["B"]), 4) <= Fraction(1, 2) < Fraction(sum(violation["A"]), 4)
    joint_cases = [
        {"a_local": 0, "b_local": 0, "joint": 0},
        {"a_local": 0, "b_local": 0, "joint": 1},
    ]
    containment_violations = sum(
        row["joint"] and not (row["a_local"] or row["b_local"]) for row in joint_cases
    )
    assert containment_violations == 1
    return {
        "same_public_evaluation": evaluation,
        "deployment": metrics,
        "disturbing_probe_minus_passive": str(Fraction(sum(signed_effects), len(signed_effects))),
        "joint_cases_without_local_warning": containment_violations,
    }


def robust_game_control():
    worlds = ("left", "right")
    immediate_actions = ("left", "right", "refuse")

    def safe_and_useful(world, action):
        return action == world

    def winning_constant_policy(information_set):
        return [action for action in immediate_actions
                if all(safe_and_useful(world, action) for world in information_set)]

    individually = {world: winning_constant_policy([world]) for world in worlds}
    pooled = winning_constant_policy(worlds)
    audited = {observed: winning_constant_policy([observed]) for observed in worlds}
    assert all(individually.values()) and pooled == []
    assert all(audited.values())
    return {
        "each_completion": individually,
        "without_admitted_read": pooled,
        "with_admitted_discriminating_read": audited,
        "refusal_completion_count": 0,
        "safe_but_zero_utility": "refuse",
    }


def control_results():
    return {
        "extensional_atomic_touch": closure_control(),
        "nonrectangular_target": correlation_control(),
        "weighted_legitimate_queries": certificate_control(),
        "statistical_denominator_pairing_and_selection": calibration_control(),
        "evaluation_monitor_fidelity_containment": deployment_control(),
        "quantifier_order_utility": robust_game_control(),
    }
def main():
    print(json.dumps(control_results(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
