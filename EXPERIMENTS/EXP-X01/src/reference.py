
"""Independent exhaustive policy-tree and source-compatibility reference."""

from functools import cache
from hashlib import sha256
from itertools import groupby, product
from math import inf
import json

from .model import Certificate, Contract, Evidence

REFERENCE_FREEZES = ("", "E", "R", "A", "ER", "EA", "RA", "ERA")


def _equivalence(representation):
    return frozenset(
        (i, j)
        for i, left in enumerate(representation)
        for j, right in enumerate(representation)
        if left == right
    )


def _class_sets(contract):
    answer = []
    for state in contract.states:
        answer.append({
            contract.targets[world]
            for world, histories in enumerate(contract.compatibility)
            if any(
                state.representation[history] == state.representation[state.history]
                for history in histories
            )
        })
    return answer


def _eligible(contract, by_name, checkpoint, chosen):
    state = contract.states[checkpoint]
    return [
        row
        for row in state.candidates
        if row.name == chosen and by_name[chosen].interface in state.authority
    ]


def _well_formed(contract):
    histories = frozenset(range(len(contract.histories)))
    if (
        not histories
        or len(set(contract.histories)) != len(histories)
        or not (type(contract.initial) is int and 0 <= contract.initial < len(contract.states))
        or len(contract.targets) == 0
        or len(contract.targets) != len(contract.compatibility)
        or any(history not in histories for world in contract.compatibility for history in world)
    ):
        return False

    names = [action.name for action in contract.actions]
    if len(names) != len(set(names)):
        return False
    by_name = {action.name: action for action in contract.actions}
    declared_interfaces = {action.interface for action in contract.actions}
    for action in contract.actions:
        if not action.name or not action.interface or type(action.cost) is not int or action.cost < 0:
            return False
    for state in contract.states:
        if (
            type(state.history) is not int
            or state.history not in histories
            or len(state.representation) != len(histories)
            or any(interface not in declared_interfaces for interface in state.authority)
            or not isinstance(state.observation, str)
            or not state.observation
        ):
            return False
        ids = [candidate.name for candidate in state.candidates]
        if len(ids) != len(set(ids)) or any(name not in by_name for name in ids):
            return False
        for candidate in state.candidates:
            if not candidate.support:
                return False
            seen = set()
            for branch in candidate.support:
                if (
                    not isinstance(branch.outcome, str)
                    or not branch.outcome
                    or type(branch.state) is not int
                    or not (0 <= branch.state < len(contract.states))
                    or (branch.state, branch.outcome) in seen
                ):
                    return False
                seen.add((branch.state, branch.outcome))

    classes = _class_sets(contract)
    known = {contract.initial}
    while True:
        next_known = known | {
            branch.state
            for checkpoint in known
            for name in names
            for candidate in _eligible(contract, by_name, checkpoint, name)
            for branch in candidate.support
        }
        if next_known == known:
            return all(classes[checkpoint] for checkpoint in known)
        known = next_known


def reference_signature(contract: Contract) -> tuple[int | float, ...]:
    if not _well_formed(contract):
        raise ValueError("reference contract validation failed")
    class_sets = _class_sets(contract)
    by_name = {action.name: action for action in contract.actions}
    equivalences = [_equivalence(state.representation) for state in contract.states]

    def enumerate_values(freeze):
        @cache
        def tree_costs(current, active_path):
            if all(len(class_sets[checkpoint]) == 1 for checkpoint in current):
                return frozenset({0})
            if current in active_path:
                return frozenset()
            subtree_ancestors = active_path | {current}
            costs = set()
            for action in contract.actions:
                trace_rows = []
                for checkpoint in current:
                    row = _eligible(contract, by_name, checkpoint, action.name)
                    if not row:
                        break
                    parent = contract.states[checkpoint]
                    for branch in row[0].support:
                        destination = contract.states[branch.state]
                        if (
                            ("E" in freeze and parent.history != destination.history)
                            or ("R" in freeze and equivalences[checkpoint] != equivalences[branch.state])
                            or ("A" in freeze and parent.authority != destination.authority)
                        ):
                            break
                        trace_rows.append((branch.outcome, destination.observation, branch.state))
                    else:
                        continue
                    break
                else:
                    per_branch_costs = []
                    for _, rows in groupby(sorted(trace_rows), key=lambda row: row[:2]):
                        successor = tuple(sorted({row[2] for row in rows}))
                        per_branch_costs.append(tree_costs(successor, subtree_ancestors))
                    # Cartesian products combine the independently attainable subtree costs.
                    for children in product(*per_branch_costs):
                        costs.add(action.cost + max(children))
            return frozenset(costs)

        return min(tree_costs((contract.initial,), frozenset()), default=inf)

    return tuple(enumerate_values(freeze) for freeze in REFERENCE_FREEZES)


def _independent_source_hash(contract):
    # Reconstruct the serialized public fields from the reference records.
    action_rows = [[row.name, row.interface, row.cost] for row in contract.actions]
    checkpoint_rows = []
    for state in contract.states:
        candidate_rows = []
        for candidate in state.candidates:
            pairs = [[branch.state, branch.outcome] for branch in candidate.support]
            candidate_rows.append([candidate.name, sorted(pairs)])
        checkpoint_rows.append([state.observation, sorted(candidate_rows)])
    source = dict(
        actions=sorted(action_rows),
        checkpoints=checkpoint_rows,
        compatibility=list(map(sorted, contract.compatibility)),
        histories=list(contract.histories),
        initial=contract.initial,
        raw_description=contract.source,
        targets=list(contract.targets),
    )
    return sha256(json.dumps(source, sort_keys=True, ensure_ascii=True).encode("ascii")).hexdigest()


def _matches(contract, evidence):
    if _independent_source_hash(contract) != evidence.source_sha256:
        return False
    for fact in evidence.facts:
        if (
            type(fact.checkpoint) is not int
            or not (0 <= fact.checkpoint < len(contract.states))
            or fact.coordinate not in ("H", "R", "A")
        ):
            raise ValueError("reference evidence points outside its schema")
        state = contract.states[fact.checkpoint]
        if fact.coordinate == "H":
            if state.history != fact.value:
                return False
        if fact.coordinate == "A":
            if sorted(state.authority) != sorted(fact.value):
                return False
        if fact.coordinate == "R":
            claimed = frozenset((i, j) for block in fact.value for i in block for j in block)
            if claimed != _equivalence(state.representation):
                return False
    return True


def verify_certificate(
    catalog: tuple[Contract, ...],
    evidence: Evidence,
    certificate: Certificate,
) -> bool:
    """Check exhaustive agreement and each witness against independent semantics."""
    if len({contract.name for contract in catalog}) != len(catalog):
        return False
    if any(not _well_formed(contract) for contract in catalog):
        return False
    matched = [contract for contract in catalog if _matches(contract, evidence)]
    expected = {
        contract.name: reference_signature(contract)
        for contract in matched
    }
    signature_set = frozenset(expected.values())
    if not signature_set:
        verdict = "INCONSISTENT"
    elif len(signature_set) == 1:
        verdict = "IDENTIFIED"
    else:
        verdict = "UNDERIDENTIFIED"
    return (
        certificate.verdict == verdict
        and tuple(sorted(expected)) == certificate.compatible
        and tuple(sorted(signature_set)) == certificate.signatures
        and len(certificate.witnesses) == len(signature_set)
        and {value for _, value in certificate.witnesses} == signature_set
        and all(name in expected and expected[name] == value for name, value in certificate.witnesses)
    )
