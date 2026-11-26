"""Pre-outcome checks using isolated trials and direct component readbacks."""

from itertools import product

from audit import COMPLETIONS, study_costs, target, verify_ports
from common import AGENTS, CONTEXTS, MODES, TIES, canonical, digest, tickets
from model import reference, scenario_table
from sandbox import Dispatcher, Workshop
from scoring import score


def check_components():
    card_checks = claim_checks = policy_checks = 0
    for mode, first in product(MODES, TIES):
        plant = Workshop(*mode, first)
        for agents in (AGENTS, *((name,) for name in AGENTS)):
            for demands in product((1, 2), repeat=len(agents)):
                written = dict(zip(agents, demands, strict=True))
                should_compress = mode[1] == "shared_summary" and demands == (2, 2)
                expected = dict.fromkeys(agents, 1) if should_compress else written
                if plant.show_cards(written) != expected:
                    raise ValueError("Presentation invariant failed")
                card_checks += 1
            for choices in product((False, True), repeat=len(agents)):
                requests = [{"agent": name, "preferred": "shared" if shared else f"private-{name}"}
                            for name, shared in zip(agents, choices, strict=True)]
                expected = {order["agent"]: order["preferred"] for order in requests}
                if mode[0] == "exclusive" and choices == (True, True):
                    other = next(name for name in agents if name != first)
                    expected[other] = f"private-{other}"
                if plant.grant(requests) != expected:
                    raise ValueError("Bench authority invariant failed")
                claim_checks += 1

    for name, previous, seen, preferred, expedited in product(
            AGENTS, (1, 2), (1, 2), (False, True), (False, True)):
        policy = Dispatcher(name)
        policy.submit(previous, False, False)
        actual = policy.submit(seen, preferred, expedited)
        expected = {"agent": name, "seen": seen, "previous": previous,
                    "preferred": "shared" if preferred else f"private-{name}",
                    "requested": 1 if seen == 1 or (previous == 1 and expedited) else 2}
        if actual != expected:
            raise ValueError("Scheduler transition disagrees with the declared contract")
        policy_checks += 1
    return {"card_cases": card_checks, "grant_cases": claim_checks, "policy_cases": policy_checks}


def check_isolation(table):
    isolated_trials = 0
    evidence = {}
    for mode, first in product(MODES, TIES):
        plant = Workshop(*mode, first)
        samples = []
        for context in CONTEXTS:
            for ticket in tickets(context):
                for name in AGENTS:
                    trace = plant.execute(context, ticket, (name,))
                    observed = score(context, ticket, trace, (name,))
                    expected_trace, expected_score = reference(context, ticket, mode, first, (name,))
                    if trace != expected_trace or observed != expected_score:
                        raise ValueError("Executed isolated certificate check failed")
                    samples.append([context, ticket, name, trace, observed])
                    isolated_trials += 1
        evidence["/".join((*mode, first))] = digest(canonical(samples))

    declared = {candidate["isolated_evidence_sha256"] for candidate in table.values()}
    if set(evidence.values()) != declared:
        raise ValueError("Local-only evaluator distinguishes compatible installations")
    return {"native_trials": isolated_trials, "evidence_sha256": evidence}


def run():
    table = scenario_table()
    minimum = study_costs(table)
    left = COMPLETIONS[0]
    right = next(candidate for candidate in COMPLETIONS
                 if target(left, table)[0] != target(candidate, table)[0])
    if not all(entry["judgments"]["isolated_certificates_valid"] for entry in table.values()):
        raise ValueError("The declared local certificates do not hold in isolation")

    observed_gates = {
        mode: (entry["judgments"]["event_containment"],
               entry["judgments"]["local_bounds_carried_over"],
               entry["judgments"]["useful_certificate"])
        for mode, entry in table.items()
    }
    if observed_gates != {
        "exclusive/faithful": (True, True, True),
        "exclusive/shared_summary": (True, False, False),
        "parallel/faithful": (False, True, False),
        "parallel/shared_summary": (False, False, False),
    }:
        raise ValueError("The planned controls did not separate the two premises")

    return {"candidates": len(COMPLETIONS),
            "witness_pair": {
                "left_assignment": left, "right_assignment": right,
                "left_target": target(left, table), "right_target": target(right, table)},
            "isolation": check_isolation(table), "component_checks": check_components(),
            "sentinel_checks": verify_ports(), "audit": minimum, "reference_modes": table}
