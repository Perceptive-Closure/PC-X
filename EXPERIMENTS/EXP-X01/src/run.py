
"""Run and reproduce the frozen EXP-X01 exact finite workload."""

from argparse import ArgumentParser
from collections import Counter, defaultdict
from dataclasses import replace
from hashlib import sha256
from itertools import combinations
from math import inf
from pathlib import Path
from time import perf_counter
import json
import platform
import tracemalloc

from .fixtures import (
    factorial_cases, generated_cases, hand_cases, malformed_cases, source_boundary,
)
from .model import (
    ContractError, Evidence, Fact, FREEZE_NAMES, FREEZES, identify, profiles,
    semantic_fact, source_sha256,
)
from .reference import reference_signature, verify_certificate

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "protocol.json"
RESULTS = ROOT / "results"


def encoded(value):
    return ["inf" if cost == inf else cost for cost in value]


def canonical_json(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def canonical_fact(fact):
    if fact.coordinate == "R":
        value = sorted(sorted(cell) for cell in fact.value)
    elif fact.coordinate == "A":
        value = sorted(fact.value)
    else:
        value = fact.value
    return [fact.checkpoint, fact.coordinate, value]


def evidence_conditions(group, source, names):
    cases = {}
    for contract in group:
        initial = contract.initial
        anchors = tuple(
            Fact(initial, coordinate, semantic_fact(contract, initial, coordinate))
            for coordinate in ("H", "R", "A")
        )
        full = anchors + tuple(
            Fact(checkpoint, coordinate, semantic_fact(contract, checkpoint, coordinate))
            for checkpoint in range(len(contract.states))
            if checkpoint != initial
            for coordinate in ("H", "R", "A")
        )
        patterns = {
            "source only": (),
            "initial history": anchors[:1],
            "initial representation": anchors[1:2],
            "initial anchors": anchors,
            "initial and source semantic anchors": full,
            "contradict initial history": (Fact(initial, "H", len(contract.histories)),),
        }
        for condition in names:
            evidence = Evidence(source, patterns[condition])
            cases.setdefault(evidence, []).append((condition, contract.name))
    return cases


def monotonic(signature):
    return all(
        signature[lo] <= signature[hi]
        for lo, lower in enumerate(FREEZES)
        for hi, upper in enumerate(FREEZES)
        if lower < upper
    )


def finite_checkpoints(contract):
    """Independently expose all supported target classes and enabled source labels."""
    return tuple(
        (
            {
                target
                for target, compatible in zip(contract.targets, contract.compatibility, strict=True)
                if any(state.representation[h] == state.representation[state.history] for h in compatible)
            },
            {
                candidate.name
                for candidate in state.candidates
                if any(
                    row.name == candidate.name and row.interface in state.authority
                    for row in contract.actions
                )
            },
        )
        for state in contract.states
    )


def _refuses(operation):
    try:
        operation()
    except (ContractError, ValueError):
        return True
    return False


def collect(config):
    factors = list(factorial_cases(config))
    hand = list(hand_cases())
    random_cases = list(generated_cases(config))
    all_contracts = [contract for contract, _ in factors + hand] + random_cases
    expected = {contract.name: signature for contract, signature in factors + hand}
    groups = defaultdict(list)
    signatures = {}
    records = []
    failures = []
    stratum_stats = defaultdict(Counter)
    stats = Counter()

    for contract in all_contracts:
        evaluations = profiles(contract)
        actual = tuple(result.cost for result in evaluations)
        reference = reference_signature(contract)
        signatures[contract.name] = actual
        source = source_sha256(contract)
        groups[source].append(contract)
        stratum = "/".join(contract.name.split("/")[:2]) if contract.name.startswith("generated/") else contract.name.split("/")[0]
        stratum_stats[stratum].update({
            "contracts": 1,
            "finite_unrestricted": int(actual[0] != inf),
            "finite_coordinates": sum(cost != inf for cost in actual),
            "maximum_beliefs": 0,
        })
        stratum_stats[stratum]["maximum_beliefs"] = max(
            stratum_stats[stratum]["maximum_beliefs"],
            max(result.reachable_beliefs for result in evaluations),
        )
        if actual != reference:
            failures.append({"reference_disagreement": contract.name})
        if contract.name in expected and actual != expected[contract.name]:
            failures.append({"hand_calculation_disagreement": contract.name})
        if not monotonic(actual) or not monotonic(reference):
            failures.append({"freeze_monotonicity": contract.name})
        records.append({
            "id": contract.name,
            "source_sha256": source,
            "signature": encoded(actual),
            "exhaustive_reference": encoded(reference),
            "precalculated": encoded(expected[contract.name]) if contract.name in expected else None,
            "reachable_beliefs": [r.reachable_beliefs for r in evaluations],
            "policy_options": [r.policy_options for r in evaluations],
            "finite_beliefs": [r.finite_beliefs for r in evaluations],
        })

    consistent_behaviors = 0
    invariance_pairs = 0
    for group in groups.values():
        for first, second in combinations(group, 2):
            if first.name.startswith("boundary/") and second.name.startswith("boundary/"):
                if finite_checkpoints(first) != finite_checkpoints(second):
                    failures.append({"behavior_projection_changed": [first.name, second.name]})
                elif first.name.split("/")[1] != second.name.split("/")[1]:
                    consistent_behaviors += 1
            renaming_pair = (
                first.name.startswith("boundary/")
                and second.name.startswith("boundary/")
                and first.name.rsplit("/", 1)[0] == second.name.rsplit("/", 1)[0]
            )
            anchored_pair = first.name == "boundary/E/4/0" and second.name == "hand/anchored-alternate-history"
            if renaming_pair or anchored_pair:
                invariance_pairs += 1
                if signatures[first.name] != signatures[second.name]:
                    failures.append({"anchor_invariance_failed": [first.name, second.name]})

    evidence_records = []
    for source, group in groups.items():
        local = {}
        condition_set = evidence_conditions(group, source, config["evidence"])
        # Include a source-incompatible completion as an explicit non-admission control.
        distractor = next(contract for contract in all_contracts if contract not in group)
        catalog = tuple(group) + (distractor,)
        for evidence, triggers in condition_set.items():
            certificate = identify(catalog, evidence)
            verified = verify_certificate(catalog, evidence, certificate)
            if not verified:
                failures.append({"unverified_certificate": source, "triggers": triggers})
            local[evidence] = certificate
            stats[certificate.verdict] += 1
            stats["witnesses"] += len(certificate.witnesses)
            if certificate.verdict == "IDENTIFIED" and len(certificate.compatible) > 1:
                stats["point_with_multiple_contract_ids"] += 1
            evidence_records.append({
                "source_sha256": source,
                "facts": [canonical_fact(fact) for fact in evidence.facts],
                "trigger_conditions": triggers,
                "verdict": certificate.verdict,
                "compatible": certificate.compatible,
                "signatures": [encoded(v) for v in certificate.signatures],
                "witnesses": [(name, encoded(v)) for name, v in certificate.witnesses],
                "independently_verified": verified,
            })
        for coarse, refined in combinations(local, 2):
            first, second = set(coarse.facts), set(refined.facts)
            if second < first:
                coarse, refined = refined, coarse
                first, second = second, first
            if first < second:
                stats["strict_nested_evidence_checks"] += 1
                if (
                    not set(local[refined].compatible) <= set(local[coarse].compatible)
                    or not set(local[refined].signatures) <= set(local[coarse].signatures)
                ):
                    failures.append({"evidence_refinement_not_nested": source})

    controls = []
    for contract, _ in factors:
        if contract.name.startswith("hidden/"):
            privileged = replace(contract, states=tuple(
                replace(state, observation=f"hidden-state-{index}")
                for index, state in enumerate(contract.states)
            ))
            observed = profiles(privileged)[0].cost
            exact = signatures[contract.name][0]
            violated = observed != exact
            expected_violation = contract.name.startswith("hidden/merged/")
            stats["hidden_state_oracle_examples"] += 1
            stats["hidden_state_oracle_wrong"] += violated
            controls.append({
                "id": contract.name,
                "ablation": "full-state oracle",
                "coordinate": "none",
                "exact": encoded((exact,))[0],
                "ablation_result": encoded((observed,))[0],
            })
            if violated != expected_violation or observed > exact:
                failures.append({"unexpected_hidden_oracle_control": contract.name})

        if contract.name.startswith("mixed/"):
            observed = profiles(contract, representative_only=True)[2].cost
            exact = signatures[contract.name][2]
            violated = observed != exact
            expected_violation = contract.name.startswith("mixed/0/")
            stats["representative_touch_examples"] += 1
            stats["representative_touch_wrong"] += violated
            controls.append({
                "id": contract.name,
                "ablation": "first-supported-successor touch",
                "coordinate": "R",
                "exact": encoded((exact,))[0],
                "ablation_result": encoded((observed,))[0],
            })
            if violated != expected_violation or observed > exact:
                failures.append({"unexpected_representative_touch_control": contract.name})

    rejection_records = []
    for reason, bad in malformed_cases():
        rejected_main = _refuses(lambda: profiles(bad))
        rejected_independent = _refuses(lambda: reference_signature(bad))
        rejection_records.append({"condition": reason, "main_rejected": rejected_main, "reference_rejected": rejected_independent})
    base = source_boundary("E", 4, 0)
    bad_anchor = Evidence(source_sha256(base), (Fact(-1, "H", 0),))
    rejection_records.append({
        "condition": "invalid evidence anchor",
        "main_rejected": _refuses(lambda: identify((base,), bad_anchor)),
        "reference_rejected": _refuses(lambda: verify_certificate((base,), bad_anchor, identify((base,), Evidence(source_sha256(base))))),
    })
    for row in rejection_records:
        if not row["main_rejected"] or not row["reference_rejected"]:
            failures.append({"malformed_input_not_rejected": row["condition"]})
    if {row["condition"] for row in rejection_records} != set(config["invalid_inputs"]):
        failures.append({"missing_frozen_invalid_condition": True})

    thresholds = config["acceptance"]
    if stats["hidden_state_oracle_wrong"] < thresholds["required_hidden_oracle_failures"]:
        failures.append({"missing_hidden_state_control_signal": True})
    if stats["representative_touch_wrong"] < thresholds["required_representative_ablation_failures"]:
        failures.append({"missing_successor_union_control_signal": True})
    if thresholds["required_inconsistent_point_and_multi_signature"] and not (
        stats["INCONSISTENT"] and stats["UNDERIDENTIFIED"] and stats["point_with_multiple_contract_ids"]
    ):
        failures.append({"missing_identification_verdict_control": True})

    summary = {
        "protocol": config["protocol"],
        "freeze_order": FREEZE_NAMES,
        "factorial_contracts": len(factors),
        "hand_controls": len(hand),
        "generated_contracts": len(random_cases),
        "total_contracts": len(all_contracts),
        "signature_coordinate_comparisons": len(all_contracts) * len(FREEZE_NAMES),
        "hand_and_factorial_precalculated_comparisons": len(expected) * len(FREEZE_NAMES),
        "strict_nested_freeze_checks": len(all_contracts) * sum(a < b for a in FREEZES for b in FREEZES),
        "public_source_groups": len(groups),
        "evidence_cases": len(evidence_records),
        "unrestricted_behavior_identity_pairs": consistent_behaviors,
        "anchor_or_label_invariance_pairs": invariance_pairs,
        "intentionally_malformed_conditions": len(rejection_records),
        "strata": {key: dict(values) for key, values in sorted(stratum_stats.items())},
        "counts": dict(stats),
        "unexpected_discrepancies": len(failures),
    }
    detailed = {
        "protocol": config["protocol"],
        "freeze_order": FREEZE_NAMES,
        "signatures": records,
        "evidence_refinements": evidence_records,
        "ablation_controls": controls,
        "rejection_cases": rejection_records,
        "discrepancies": failures,
    }
    return summary, detailed


def main():
    parser = ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="compare against committed evidence digests")
    mode.add_argument("--record", action="store_true", help="write summary and digest manifest")
    parser.add_argument("--details", type=Path, help="write regenerated complete evidence to a file")
    parser.add_argument("--timing", action="store_true", help="report wall time separately from frozen evidence")
    parser.add_argument("--memory", action="store_true", help="also measure peak traced Python allocations")
    args = parser.parse_args()
    config_bytes = CONFIG.read_bytes()
    config = json.loads(config_bytes)
    if platform.python_version() != config["python"]:
        parser.error(f"protocol requires Python {config['python']}")
    if tuple(config["freeze_order"]) != FREEZE_NAMES:
        parser.error("protocol freeze order disagrees with the original PC target encoding")

    if args.memory:
        tracemalloc.start()
    start = perf_counter()
    summary, detailed = collect(config)
    duration = perf_counter() - start
    peak = tracemalloc.get_traced_memory()[1] if args.memory else None
    if args.memory:
        tracemalloc.stop()

    summary_bytes = canonical_json(summary)
    evidence_bytes = canonical_json(detailed)
    manifest = canonical_json({
        "format": "canonical UTF-8 JSON with sorted keys, indentation 2, LF and no BOM",
        "protocol_canonical_sha256": sha256(canonical_json(config)).hexdigest(),
        "summary_sha256": sha256(summary_bytes).hexdigest(),
        "complete_evidence_sha256": sha256(evidence_bytes).hexdigest(),
    })
    if args.details:
        args.details.write_bytes(evidence_bytes)
    if args.record:
        (RESULTS / "summary.json").write_bytes(summary_bytes)
        (RESULTS / "manifest.json").write_bytes(manifest)
    elif args.check:
        for name, contents in (("summary.json", summary_bytes), ("manifest.json", manifest)):
            existing = (RESULTS / name).read_bytes().replace(b"\r\n", b"\n")
            if existing != contents:
                raise SystemExit(f"reproduction discrepancy for {name}")

    print(summary_bytes.decode("ascii"), end="")
    if args.timing or args.memory:
        print(f"Wall seconds: {duration:.3f}")
        if peak is not None:
            print(f"Peak traced Python bytes: {peak}")
    if summary["unexpected_discrepancies"] > config["acceptance"]["unexpected_discrepancies"]:
        for finding in detailed["discrepancies"]:
            print(finding)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
