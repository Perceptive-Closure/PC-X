"""Reproduce the exact public study and the registered acquisition choice."""

from collections import Counter, defaultdict
from itertools import combinations
from time import perf_counter
import tracemalloc

from audit import (CATALOG, COMPLETIONS, MODES, compare_baselines, inaccessible_witness,
                   measured_read, model_read, optimum, pack, receipt_reads, summarize_costs,
                   verify_exact)
from checker import exhaustive_baseline, reference_cost, verify_certificate, worlds
from common import CONFIG, COST, HELD, JOBS, ORDER, PROFILES, SLIPS, canonical
from engine import Workshop, play, score
from game import Game, State, semantic_kernel, step

ALPHABET = ("offer-0", "offer-1", "queued")
DONE = {"complete": True}
REFUSE = {"action": "refuse", "branches": {"stopped": {"complete": False}}}
MOVE_LEFT = {"action": "left", "branches": {"complete": DONE}}
MOVE_RIGHT = {"action": "right", "branches": {"complete": DONE}}
FIXED_LEFT = {"action": "left", "branches": dict.fromkeys(ALPHABET, MOVE_LEFT)}
SINGLE_CONTRACT = {"action": "left", "branches": {
    "offer-0": MOVE_LEFT, "offer-1": MOVE_RIGHT, "queued": REFUSE,
}}


def held_scope(profiles):
    return {"profiles": list(profiles), "horizon": HELD["horizon"],
            "actions": HELD["actions"], "evidence": "two-slots"}


def expected(profile, signature, slip, scope, policy):
    """Forecast by stepping the symbolic model while the native installation is sealed."""
    state = State(profile, signature, slip)
    spent = 0
    why = "deadline"
    for _ in range(scope["horizon"]):
        action = policy["action"]
        status, observation, state = step(state, action)
        if status != "ok":
            why = status
            break
        spent += COST.get(action, 0)
        if state.stopped or state.jobs == len(JOBS):
            why = "refused" if state.stopped else "complete"
            break
        if observation not in policy["branches"]:
            why = "unsupported"
            break
        policy = policy["branches"][observation]
    return {"finish": why, "qualified": state.jobs, "audit_cost": spent,
            "safe": why not in ("unsafe", "unauthorized"),
            "useful": why == "complete" and state.jobs == len(JOBS)}


def held_profile(profile):
    scope = held_scope([profile])
    certificate = Game(scope).certificate()
    verification = verify_certificate(scope, certificate)
    policies = {"governed": certificate["policy"] or REFUSE, "fixed-left": FIXED_LEFT,
                "single-contract": SINGLE_CONTRACT, "refuse": REFUSE}
    outcome = {}
    for arm, policy in policies.items():
        rows = {}
        for slip in SLIPS:
            negative = expected(profile, False, slip, scope, policy)
            positive = expected(profile, True, slip, scope, policy)
            if negative != positive:
                raise ValueError("The frozen target depends on the withheld signature")
            rows[str(slip)] = negative
        outcome[arm] = rows
    return {"certificate": certificate, "policies": policies, "predicted": outcome,
            "checked_worlds": len(verification["world_replays"]),
            "checked_proof_nodes": verification["proof_nodes"]}


def verify_transitions(ticks):
    states = {(State(profile, signature, slip), Workshop(profile, signature, slip))
              for profile in PROFILES for signature in (False, True) for slip in SLIPS}
    checked = 0
    touch = defaultdict(Counter)
    for _ in range(ticks):
        future = set()
        for state, machine in states:
            for action in ORDER:
                checked += 1
                status, observe, next_state = step(state, action)
                next_machine, result, signal = machine.enact(action)
                if (status, observe, next_state.wire()) != (result, signal, next_machine.wire()):
                    raise ValueError("The two workshop implementations diverged")
                if status != "ok":
                    continue
                future.add((next_state, next_machine))
                if action not in COST:
                    continue
                source, target = semantic_kernel(state), semantic_kernel(next_state)
                symbolic = [tag for tag, before, after in zip("ERA", source, target, strict=True)
                            if before != after]
                independent = []
                if machine.receipts != next_machine.receipts:
                    independent.append("E")
                if any(machine.panel(slip) != next_machine.panel(slip) for slip in SLIPS):
                    independent.append("R")
                if machine.authorization() != next_machine.authorization():
                    independent.append("A")
                if symbolic != independent:
                    raise ValueError("Extensional semantic touch diverged")
                touch[action]["".join(symbolic) or "empty"] += 1
        states = future
    return {"transition_checks": checked, "audit_touch_counts": dict(touch)}


def work_items():
    yield from CONFIG["controls"].items()
    for size in range(1, CONFIG["matrix"]["max_profiles"] + 1):
        for names in combinations(sorted(PROFILES), size):
            for horizon in CONFIG["matrix"]["horizons"]:
                yield f"matrix-{horizon}-" + "+".join(names), {
                    "profiles": list(names), "horizon": horizon,
                    "actions": list(ORDER), "evidence": "two-slots",
                }


def bounded_study():
    outcomes = {}
    for name, scope in work_items():
        game = Game(scope)
        certificate = game.certificate()
        verification = verify_certificate(scope, certificate)
        single, omniscient = {}, {}
        for profile in scope["profiles"]:
            for signature in (False, True):
                narrowed = {**scope, "profiles": [profile], "signatures": [signature]}
                key = f"{profile}:{int(signature)}"
                for comparator, truth in ((single, False), (omniscient, True)):
                    knowledge = Game(narrowed, omniscient=truth)
                    value = knowledge.value(knowledge.root, scope["horizon"])[0]
                    if value != reference_cost(narrowed, omniscient=truth):
                        raise ValueError(f"Comparator differs from the independent oracle for {name}")
                    comparator[key] = value
        refusal = []
        for machine in worlds(scope):
            trace = play(machine.profile, machine.signature, machine.slip, scope, REFUSE)
            refusal.append(score(machine.profile, machine.signature, machine.slip, scope, trace))
        outcomes[name] = {
            "scope": scope, "certificate": certificate, "check": verification,
            "all_contracts_have_a_policy": all(cost is not None for cost in single.values())
            if game.root else None,
            "single_contract_costs": single, "omniscient_costs": omniscient,
            "refusal": {"support": len(refusal), "safe": sum(row["safe"] for row in refusal),
                        "qualified_jobs": sum(row["qualified"] for row in refusal),
                        "useful": sum(row["useful"] for row in refusal)},
            "exhaustive_audit": exhaustive_baseline(scope),
        }
    counts = Counter(row["certificate"]["status"] for row in outcomes.values())
    checks = {
        "scenarios": len(outcomes), "verdicts": dict(counts),
        "invalid_positive_certificates": 0, "exact_reference_disagreements": 0,
        "certified_physical_replays": sum(len(row["check"]["world_replays"]) for row in outcomes.values()),
        "checked_counterproof_nodes": sum(row["check"]["proof_nodes"] for row in outcomes.values()),
        "all_contracts_but_no_common_policy": [
            name for name, row in outcomes.items() if row["all_contracts_have_a_policy"]
            and row["certificate"]["status"] == "infeasible"
        ],
    }
    transitions = verify_transitions(max(scope["horizon"] for _, scope in work_items()))
    return {"checks": checks, "semantics": transitions, "outcomes": outcomes}


def pre_audit():
    profiles = {mode: held_profile(mode) for mode in MODES}
    content = {canonical(row["predicted"]) for row in profiles.values()}
    if len(content) != len(MODES):
        raise ValueError("Profile identification does not equal prospective target resolution")
    for candidate in COMPLETIONS:
        for query in CATALOG:
            if model_read(candidate, query) != measured_read(candidate, query):
                raise ValueError("Structural anchor failed independent validation")
    cost, policy = optimum(CATALOG)
    verify_exact(cost, policy)
    costs = [sum(CATALOG[event["query"]] for event in receipt_reads(candidate, policy))
             for candidate in COMPLETIONS]
    witness_pair = next((COMPLETIONS[0], other) for other in COMPLETIONS
                        if profiles[COMPLETIONS[0][0][0]]["predicted"] != profiles[other[0][0]]["predicted"])
    blind = held_scope(MODES)
    witness = Game(blind).certificate()
    check = verify_certificate(blind, witness)
    removed = {
        "layout_withheld": tuple(query for query in CATALOG if not query.startswith("layout-")),
        "viewer_withheld": tuple(query for query in CATALOG if not query.startswith("viewer-")),
        "nameplate_only": ("nameplate",),
    }
    return {
        "valid_compatible_installations": len(COMPLETIONS),
        "independent_readback_checks": len(COMPLETIONS) * len(CATALOG),
        "initial_admission": "two-slots",
        "ambiguity_witness": {
            "assignments": [pack(candidate) for candidate in witness_pair],
            "distinguished_port": HELD["ports"][0],
            "prediction_vectors": [profiles[candidate[0][0]]["predicted"] for candidate in witness_pair],
        },
        "pre_read_common_certificate": witness,
        "pre_read_checked_proof_nodes": check["proof_nodes"],
        "profiles": profiles,
        "audit": {
            "policy": policy, "minimum_worst_cost": cost,
            "costs": summarize_costs(costs),
            "lower_budget_rejected": cost - 1,
            "minimum_adaptive_full_identity": cost + CATALOG["roster"],
            "full_identity_lower_bound": "Only the roster partitions otherwise identical signatures",
        },
        "comparators": compare_baselines(),
        "ablations": {name: inaccessible_witness(queries) for name, queries in removed.items()},
    }


def measured_run(operation):
    tracemalloc.start()
    started = perf_counter()
    try:
        result = operation()
        observation = {"seconds": round(perf_counter() - started, 6),
                       "traced_peak_bytes": tracemalloc.get_traced_memory()[1]}
    finally:
        tracemalloc.stop()
    return result, observation
