"""Run and verify the frozen nonrectangular identification experiment."""

from argparse import ArgumentParser
from collections import Counter
from dataclasses import asdict, replace
from hashlib import sha256
from itertools import product
from math import inf, prod
from pathlib import Path
import json

from cases import all_cases, control_cases
from model import (
    FREEZE_NAMES, FREEZES, UnsupportedKernel, blocked_actions, compatible_assignments,
    cost_after_removal, kernel_key, locators, materialize, signature, touch_profile,
    validate_case, x01,
)
from reference import evidence_holds, extensional_touch, policy_catalog, reference_cost, truth_table

HERE = Path(__file__).resolve().parent
SCRATCH = HERE.parents[1] / "scratch"
RESULTS = HERE / "results"


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False)
            + "\n").encode("ascii")


def coded(value):
    return "inf" if value == inf else value


def has_witness(case, assignment, claimed):
    """Rebuild the assignment and check its declared target against the policy reference."""
    if not evidence_holds(case, assignment):
        return False
    contract = materialize(case, assignment)
    kernel_key(contract, case)
    touches = extensional_touch(contract)
    policies = policy_catalog(contract)
    return tuple(reference_cost(policies, blocked_actions(touches, freeze))
                 for freeze in FREEZES) == claimed


def rectangular(case, row_profiles, policies, limit):
    """Enumerate independent extensional options at common action locators."""
    locations = locators(case)
    entries = [tuple(sorted({profile[key] for profile in row_profiles},
                            key=lambda mask: tuple(sorted(mask)))) for key in locations]
    count = prod(map(len, entries))
    if count > limit:
        raise UnsupportedKernel("The frozen limit on rectangular profiles was exceeded.")
    options = dict(zip(locations, entries, strict=True))
    joint = {
        signature(case, dict(zip(locations, profile, strict=True)))
        for profile in product(*entries)
    }
    # Every locator can attain each permitted endpoint blocking status independently.
    for index, freeze in enumerate(FREEZES):
        definite = {loc for loc, masks in options.items() if all(mask & freeze for mask in masks)}
        possible = {loc for loc, masks in options.items() if any(mask & freeze for mask in masks)}
        expected = reference_cost(policies, definite), reference_cost(policies, possible)
        values = {item[index] for item in joint}
        if (min(values), max(values)) != expected:
            raise AssertionError(f"Rectangle endpoint disagreement: {case.name} {FREEZE_NAMES[index]}")
    return joint, count


def bit_string(assignment):
    return "".join("1" if bit else "0" for bit in assignment)


def as_signature(target):
    return [coded(value) for value in target]


def verify_refinements(case, rows, base_signatures):
    decompose = [(literal,) for literal in (1, -1)]
    constraints = [(clause,) for clause in decompose]
    if len(case.features) >= 2:
        constraints += [(first, (second,)) for first, in constraints for second in (2, -2)]
    lookup = dict(rows)
    refinements = []
    for added in constraints:
        refined = replace(case, clauses=case.clauses + added)
        smaller = compatible_assignments(refined)
        if smaller != truth_table(refined) or not set(smaller) <= lookup.keys():
            raise AssertionError(f"Nested domain refinement failed: {case.name} {added}")
        identified = {lookup[row] for row in smaller}
        parent = base_signatures
        if len(added) == 2:
            first = replace(case, clauses=case.clauses + added[:1])
            parent = {lookup[row] for row in truth_table(first)}
        if not identified <= parent:
            raise AssertionError(f"Nested target refinement failed: {case.name} {added}")
        refinements.append({
            "added_clauses": added,
            "compatible_rows": len(smaller),
            "joint_signatures": [as_signature(target) for target in sorted(identified)],
            "strict_target_refinement": identified < parent,
        })
    return refinements


def evaluate(case, limits):
    validate_case(case, limits)
    assignments = compatible_assignments(case)
    if assignments != truth_table(case):
        raise AssertionError(f"Correlated evidence enumeration failed: {case.name}")

    profiles, row_targets, witness_index = [], [], {}
    anchor, policies = None, None
    for row in assignments:
        contract = materialize(case, row)
        key = kernel_key(contract, case)
        if anchor is None:
            anchor, policies = key, policy_catalog(contract)
        elif key != anchor:
            raise UnsupportedKernel(f"Common source kernel changes within {case.name}")
        independent_policies = policy_catalog(contract)
        if independent_policies != policies:
            raise UnsupportedKernel(f"Proper-policy envelope changes within {case.name}")
        profile = touch_profile(case, contract)
        if profile != extensional_touch(contract):
            raise AssertionError(f"Extensional touch disagreement: {case.name} {row}")
        target = signature(case, profile)
        independent = tuple(reference_cost(policies, blocked_actions(profile, freeze))
                            for freeze in FREEZES)
        if target != x01().signature(contract) or target != independent:
            raise AssertionError(f"Three-way freeze disagreement: {case.name} {row}")
        if any(target[i] > target[j] for i, freeze in enumerate(FREEZES)
               for j, larger in enumerate(FREEZES) if freeze <= larger):
            raise AssertionError(f"Freeze costs failed monotonicity: {case.name} {row}")
        profiles.append(profile)
        row_targets.append((row, target))
        witness_index.setdefault(target, row)

    exact = set(witness_index)
    details = {
        "case": asdict(case),
        "status": "inconsistent" if not exact else "point" if len(exact) == 1 else "partial",
        "compatible_rows": len(assignments),
        "scope_sha256": anchor[0] if anchor else None,
        "refinements": verify_refinements(case, row_targets, exact),
    }
    if not exact:
        details.update(joint_signatures=[], witnesses=[], coordinate_results=[], rectangular_signatures=[])
        return details
    rectangle, rectangular_count = rectangular(case, profiles, policies, limits["rectangular_profiles"])
    if not exact <= rectangle:
        raise AssertionError(f"Rectangle omitted an admissible joint signature: {case.name}")

    def witness(target):
        row = witness_index[target]
        if not has_witness(case, row, target):
            raise AssertionError(f"Invalid attainment witness: {case.name} {row} {target}")
        return {"assignment": bit_string(row), "signature": as_signature(target)}

    certified = {target: witness(target) for target in sorted(exact)}
    coordinates = []
    for index, freeze in enumerate(FREEZE_NAMES):
        projection = {target[index] for target in exact}
        outer = {target[index] for target in rectangle}
        lower, upper = min(projection), max(projection)
        lower_signature = min(exact, key=lambda target: (target[index], target))
        upper_signature = min(target for target in exact if target[index] == upper)
        finite = sorted(value for value in projection if value != inf)
        holes = finite[-1] - finite[0] + 1 - len(finite) if finite else 0
        for endpoint, target in ((lower, lower_signature), (upper, upper_signature)):
            if target[index] != endpoint or not has_witness(case, witness_index[target], target):
                raise AssertionError(f"Endpoint witness failed: {case.name} {freeze}")
        coordinates.append({
            "freeze": freeze,
            "exact_values": list(map(coded, sorted(projection))),
            "rectangular_values": list(map(coded, sorted(outer))),
            "exact_bounds": [coded(lower), coded(upper)],
            "rectangular_bounds": [coded(min(outer)), coded(max(outer))],
            "lower_witness": certified[lower_signature],
            "upper_witness": certified[upper_signature],
            "finite_integer_holes": holes,
        })

    details.update({
        "case_profiles": [
            {"assignment": bit_string(row), "signature": as_signature(target),
             "touches": [sorted(profile[locator]) for locator in locators(case)]}
            for (row, target), profile in zip(row_targets, profiles, strict=True)
        ],
        "joint_signatures": [as_signature(target) for target in sorted(exact)],
        "witnesses": list(certified.values()),
        "rectangular_profiles": rectangular_count,
        "rectangular_signatures": [as_signature(target) for target in sorted(rectangle)],
        "coordinate_results": coordinates,
        "marginal_product_count": prod(len(item["exact_values"]) for item in coordinates),
        "policy_support_count": len(policies),
    })
    if len(exact) > 1:
        first, second = tuple(sorted(exact))[:2]
        differences = [name for name, a, b in zip(
            case.features, witness_index[first], witness_index[second], strict=True) if a != b]
        if not differences:
            raise AssertionError(f"Target-distinct evidence witness has no differing facts: {case.name}")
        details["target_disagreement"] = {
            "completions": [certified[first], certified[second]], "differing_facts": differences
        }
    return details


def negative_kernel_checks():
    cases = {case.name: case for case in control_cases()}
    source = cases["mixed-support"]
    row = (True, False)
    contract = materialize(source, row)
    changed_source = materialize(cases["mixed-first-only"], row)
    no_local = replace(contract, states=(replace(contract.states[0], authority=frozenset()),
                                         *contract.states[1:]))
    moved_action = replace(contract, states=(
        replace(contract.states[0], candidates=contract.states[0].candidates[1:]),
        replace(contract.states[1], candidates=contract.states[0].candidates[:1]),
        *contract.states[2:],
    ))
    changed_classes = replace(contract, states=(replace(contract.states[0], history=1),
                                                *contract.states[1:]))
    mutations = {
        "positive-support-boundary": changed_source, "action-availability": no_local,
        "action-locator": moved_action, "checkpoint-closure": changed_classes,
    }
    refused = []
    for label, mutated in mutations.items():
        try:
            kernel_key(mutated, source)
        except UnsupportedKernel:
            refused.append(label)
        else:
            raise AssertionError(f"Changed kernel was silently accepted: {label}")
    return refused


def summarize(details, refusals):
    totals = Counter()
    strata = {}
    controls = {}
    for case in details:
        name = case["case"]["name"]
        stratum = case["case"]["stratum"]
        subtotal = strata.setdefault(stratum, Counter())
        exact = case["joint_signatures"]
        rectangle = case["rectangular_signatures"]
        counts = Counter(cases=1, compatible_completions=case["compatible_rows"])
        counts[f"status_{case['status']}"] = 1
        counts["three_way_freeze_cells"] = 8 * case["compatible_rows"]
        counts["joint_signature_witnesses"] = len(case["witnesses"])
        counts["verified_refinements"] = len(case["refinements"])
        counts["strict_refinements"] = sum(item["strict_target_refinement"]
                                          for item in case["refinements"])
        if exact:
            counts["endpoint_witnesses"] = 16
            counts["same_joint_rectangle"] = int(exact == rectangle)
            counts["strict_joint_rectangle"] = int(exact != rectangle)
            counts["added_joint_signatures"] = len(rectangle) - len(exact)
            counts["unattained_marginal_combinations"] = case["marginal_product_count"] - len(exact)
            counts["joint_marginal_overcoverage_cases"] = int(case["marginal_product_count"] > len(exact))
            for coordinate in case["coordinate_results"]:
                bounds, relax = coordinate["exact_bounds"], coordinate["rectangular_bounds"]
                counts["defined_coordinates"] += 1
                counts["strict_rectangle_bounds"] += bounds != relax
                counts["strict_attainable_value_overcoverage"] += (
                    coordinate["exact_values"] != coordinate["rectangular_values"]
                )
                counts["false_coordinate_ambiguity"] += (bounds[0] == bounds[1] and relax[0] != relax[1])
                counts["finite_upper_relaxed_to_infinity"] += bounds[1] != "inf" and relax[1] == "inf"
                counts["attained_integer_holes"] += coordinate["finite_integer_holes"]
                if isinstance(bounds[1], int) and isinstance(relax[1], int):
                    counts["finite_upper_gap_sum"] += relax[1] - bounds[1]
            if stratum == "control":
                r = case["coordinate_results"][FREEZE_NAMES.index("R")]
                controls[name] = {
                    "status": case["status"],
                    "completions": case["compatible_rows"],
                    "exact_signature_count": len(exact),
                    "rectangle_signature_count": len(rectangle),
                    "R_values": r["exact_values"],
                    "rectangular_R_values": r["rectangular_values"],
                    "R_bounds": r["exact_bounds"],
                    "rectangular_R_bounds": r["rectangular_bounds"],
                    "marginal_product_count": case["marginal_product_count"],
                    "R_extrema_witnesses": [r["lower_witness"], r["upper_witness"]],
                }
        elif stratum == "control":
            controls[name] = {"status": case["status"], "completions": 0}
        totals.update(counts)
        subtotal.update(counts)
    return {
        "schema": "pcx-exp-x02-summary-v1", "freeze_order": FREEZE_NAMES, "totals": dict(totals),
        "strata": {name: dict(counts) for name, counts in strata.items()},
        "controls": controls, "unsupported_kernel_changes_refused": refusals,
    }


def assert_named_controls(details):
    cases = {result["case"]["name"]: result for result in details}
    expected = {
        "complementary": ([1], [1, "inf"]),
        "independent": ([1, "inf"], [1, "inf"]),
        "co-occurrence": ([1, "inf"], [1, 3, "inf"]),
        "joint-tradeoff": ([1, 3], [1, 3, "inf"]),
        "finite-fallback": ([1, 2], [1, 2, 5]),
        "mixed-support": ([1, 3], [1, 3, 6]),
        "mixed-first-only": ([1], [1]),
        "branched-policy": ([7, 8], [5, 7, 8]),
    }
    for name, (exact, rectangular_values) in expected.items():
        r = cases[name]["coordinate_results"][FREEZE_NAMES.index("R")]
        if (r["exact_values"], r["rectangular_values"]) != (exact, rectangular_values):
            raise AssertionError(f"Preregistered R control failed: {name} {r}")
    trade = cases["joint-tradeoff"]
    costs = {(target[1], target[2]) for target in trade["joint_signatures"]}
    if costs != {(1, 3), (3, 1)} or trade["marginal_product_count"] != 16:
        raise AssertionError("Joint trade-off lost its E/R coupling.")
    if cases["independent"]["joint_signatures"] != cases["independent"]["rectangular_signatures"]:
        raise AssertionError("Rectangular equality control failed.")
    if cases["dependency-chain"]["compatible_rows"] != 4:
        raise AssertionError("Dependency chain found the wrong number of assignments.")
    if cases["infeasible"]["status"] != "inconsistent":
        raise AssertionError("Contradictory CNF did not return inconsistent evidence.")


def main():
    parser = ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--record", action="store_true", help="write frozen aggregate and manifest")
    action.add_argument("--check", action="store_true", help="check frozen aggregate and manifest")
    parser.add_argument("--details", type=Path, help="save regenerated full row and witness evidence")
    args = parser.parse_args()
    protocol_file = HERE / "protocol.json"
    protocol = json.loads(protocol_file.read_text(encoding="utf-8"))
    if tuple(protocol["freeze_order"]) != FREEZE_NAMES or x01().FREEZE_NAMES != FREEZE_NAMES:
        raise ValueError("The freeze order differs from the frozen specification.")
    details = [evaluate(case, protocol["finite_limits"]) for case in all_cases(protocol)]
    assert_named_controls(details)
    refusals = negative_kernel_checks()
    summary = canonical(summarize(details, refusals))
    raw = canonical({"schema": "pcx-exp-x02-details-v1", "cases": details})
    manifest = canonical({
        "schema": "pcx-exp-x02-evidence-v1",
        "protocol_sha256": sha256(canonical(protocol)).hexdigest(),
        "summary_sha256": sha256(summary).hexdigest(),
        "details_sha256": sha256(raw).hexdigest(),
        "details_bytes": len(raw),
        "x01_commit": protocol["x01_commit"],
    })
    blobs = {"manifest.json": manifest, "summary.json": summary}
    if args.record:
        RESULTS.mkdir(exist_ok=True)
        for name, blob in blobs.items():
            (RESULTS / name).write_bytes(blob)
    else:
        for name, blob in blobs.items():
            if (RESULTS / name).read_bytes() != blob:
                raise ValueError(f"Regenerated evidence differs from {name}.")
    if args.details:
        destination = args.details.resolve()
        if SCRATCH not in destination.parents:
            raise ValueError("Full regenerated evidence belongs in the experiment's scratch directory.")
        destination.parent.mkdir(exist_ok=True, parents=True)
        destination.write_bytes(raw)
    print(manifest.decode("ascii"), end="")


if __name__ == "__main__":
    main()
