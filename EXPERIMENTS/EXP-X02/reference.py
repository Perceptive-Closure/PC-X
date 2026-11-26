"""Independent Cartesian evidence and explicit policy-tree enumeration."""

from functools import lru_cache
from itertools import combinations, product
from math import inf


def evidence_holds(case, assignment):
    if len(assignment) != len(case.features) or any(type(bit) is not bool for bit in assignment):
        return False
    literal_truth = {index: answer for index, answer in enumerate(assignment, 1)}
    literal_truth.update({-index: not answer for index, answer in enumerate(assignment, 1)})
    return all(any(literal_truth[literal] for literal in clause) for clause in case.clauses)


def truth_table(case):
    return tuple(assignment for assignment in product([False, True], repeat=len(case.features))
                 if evidence_holds(case, assignment))


def target_classes(contract, state):
    current_class = state.representation[state.history]
    return {label
            for label, histories in zip(contract.targets, contract.compatibility, strict=True)
            if any(state.representation[h] == current_class for h in histories)}


def extensional_touch(contract):
    """Compare the represented equality relation pairwise, including on unused histories."""
    pairs = tuple(combinations(range(len(contract.histories)), 2))
    profiles = {}
    for index, state in enumerate(contract.states):
        for candidate in state.candidates:
            resources = set()
            for branch in candidate.support:
                successor = contract.states[branch.state]
                if state.history != successor.history:
                    resources.add("E")
                if any((state.representation[a] == state.representation[b])
                       != (successor.representation[a] == successor.representation[b])
                       for a, b in pairs):
                    resources.add("R")
                if state.authority != successor.authority:
                    resources.add("A")
            profiles[index, candidate.name.split(":", 1)[1]] = frozenset(resources)
    return profiles


def policy_catalog(contract):
    """Each proper policy contributes its whole action support and worst path cost."""
    actions = {action.name: action for action in contract.actions}

    @lru_cache(maxsize=None)
    def closing_policies(checkpoint):
        state = contract.states[checkpoint]
        if len(target_classes(contract, state)) == 1:
            return frozenset({(0, frozenset())})
        policies = set()
        for candidate in state.candidates:
            action = actions[candidate.name]
            if action.interface not in state.authority:
                continue
            locator = (checkpoint, candidate.name.split(":", 1)[1])
            children = [closing_policies(branch.state) for branch in candidate.support]
            for continuation in product(*children):
                cost = action.cost + max(cost for cost, _ in continuation)
                support = frozenset({locator}).union(*(support for _, support in continuation))
                policies.add((cost, support))
        return frozenset(policies)

    return closing_policies(contract.initial)


def reference_cost(policies, blocked):
    return min((cost for cost, support in policies if blocked.isdisjoint(support)), default=inf)
