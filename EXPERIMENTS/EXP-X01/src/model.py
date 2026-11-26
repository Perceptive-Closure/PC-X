
"""Explicit finite Perceptive Closure contracts and a worst-support solver."""

from collections import defaultdict, deque
from dataclasses import dataclass
from hashlib import sha256
from heapq import heappop, heappush
from itertools import count
from math import inf
import json

FREEZE_NAMES = ("none", "E", "R", "A", "ER", "EA", "RA", "ERA")
FREEZES = tuple(frozenset() if name == "none" else frozenset(name) for name in FREEZE_NAMES)

type Signature = tuple[int | float, ...]
type Belief = frozenset[int]
type Partition = frozenset[frozenset[int]]


class ContractError(ValueError):
    """The input cannot be evaluated within the declared finite fragment."""


@dataclass(frozen=True)
class Action:
    name: str
    interface: str
    cost: int


@dataclass(frozen=True)
class Branch:
    state: int
    outcome: str


@dataclass(frozen=True)
class Candidate:
    name: str
    support: tuple[Branch, ...]


@dataclass(frozen=True)
class State:
    history: int
    representation: tuple[str, ...]
    authority: frozenset[str]
    observation: str
    candidates: tuple[Candidate, ...] = ()


@dataclass(frozen=True)
class Contract:
    name: str
    source: str
    histories: tuple[str, ...]
    targets: tuple[str, ...]
    compatibility: tuple[frozenset[int], ...]
    initial: int
    actions: tuple[Action, ...]
    states: tuple[State, ...]


@dataclass(frozen=True)
class Fact:
    checkpoint: int
    coordinate: str
    value: int | Partition | frozenset[str]


@dataclass(frozen=True)
class Evidence:
    source_sha256: str
    facts: tuple[Fact, ...] = ()


@dataclass(frozen=True)
class Certificate:
    verdict: str
    compatible: tuple[str, ...]
    signatures: tuple[Signature, ...]
    witnesses: tuple[tuple[str, Signature], ...]


@dataclass(frozen=True)
class Evaluation:
    cost: int | float
    reachable_beliefs: int
    policy_options: int
    finite_beliefs: int


def partition(representation: tuple[str, ...]) -> Partition:
    cells = defaultdict(set)
    for history, label in enumerate(representation):
        cells[label].add(history)
    return frozenset(frozenset(cell) for cell in cells.values())


def checkpoint_target_classes(contract: Contract, checkpoint: int) -> frozenset[str]:
    state = contract.states[checkpoint]
    current_label = state.representation[state.history]
    represented = {i for i, label in enumerate(state.representation) if label == current_label}
    return frozenset(
        target
        for target, compatible in zip(contract.targets, contract.compatibility, strict=True)
        if represented.intersection(compatible)
    )


def available_candidates(state: State, actions: dict[str, Action]) -> dict[str, tuple[Branch, ...]]:
    return {
        candidate.name: candidate.support
        for candidate in state.candidates
        if actions[candidate.name].interface in state.authority
    }


def validate(contract: Contract) -> None:
    if type(contract.initial) is not int or not 0 <= contract.initial < len(contract.states):
        raise ContractError("initial checkpoint outside source graph")
    history_range = set(range(len(contract.histories)))
    if not history_range or len(history_range) != len(set(contract.histories)):
        raise ContractError("history IDs must form a nonempty distinct domain")
    if not contract.targets or len(contract.targets) != len(contract.compatibility):
        raise ContractError("sealed target must cover exactly the latent world domain")
    if any(not world <= history_range for world in contract.compatibility):
        raise ContractError("world compatibility uses undeclared histories")

    actions = {action.name: action for action in contract.actions}
    if len(actions) != len(contract.actions):
        raise ContractError("duplicate action ID")
    if any(
        not action.name or not action.interface or type(action.cost) is not int or action.cost < 0
        for action in actions.values()
    ):
        raise ContractError("action identity, interface or nonnegative integer cost missing")
    interfaces = {action.interface for action in actions.values()}
    for state in contract.states:
        if type(state.history) is not int or state.history not in history_range:
            raise ContractError("admitted history outside declared domain")
        if len(state.representation) != len(history_range):
            raise ContractError("representation must label every declared history")
        if not state.authority <= interfaces:
            raise ContractError("authority uses undeclared interface")
        if not isinstance(state.observation, str) or not state.observation:
            raise ContractError("controller observation missing")
        candidate_names = {candidate.name for candidate in state.candidates}
        if len(candidate_names) != len(state.candidates) or not candidate_names <= actions.keys():
            raise ContractError("duplicate or undeclared source candidate")
        for candidate in state.candidates:
            if not candidate.support or len(set(candidate.support)) != len(candidate.support):
                raise ContractError("support must provide distinct positive outcome records")
            for branch in candidate.support:
                if (
                    not isinstance(branch.outcome, str)
                    or not branch.outcome
                    or type(branch.state) is not int
                    or not 0 <= branch.state < len(contract.states)
                ):
                    raise ContractError("branch has invalid outcome or successor")

    frontier = [contract.initial]
    seen = {contract.initial}
    while frontier:
        state_id = frontier.pop()
        if not checkpoint_target_classes(contract, state_id):
            raise ContractError("reachable checkpoint has empty certificate-compatible fiber")
        for support in available_candidates(contract.states[state_id], actions).values():
            for branch in support:
                if branch.state not in seen:
                    seen.add(branch.state)
                    frontier.append(branch.state)


def touched(
    contract: Contract, state_id: int, support: tuple[Branch, ...]
) -> frozenset[str]:
    current = contract.states[state_id]
    current_partition = partition(current.representation)
    effects = set()
    for branch in support:
        successor = contract.states[branch.state]
        if current.history != successor.history:
            effects.add("E")
        if current_partition != partition(successor.representation):
            effects.add("R")
        if current.authority != successor.authority:
            effects.add("A")
    return frozenset(effects)


def source_sha256(contract: Contract) -> str:
    """Hash governing public source facts, including canonicalized support and IDs."""
    source_projection = {
        "raw_description": contract.source,
        "histories": contract.histories,
        "targets": contract.targets,
        "compatibility": [sorted(world) for world in contract.compatibility],
        "initial": contract.initial,
        "actions": sorted(
            (action.name, action.interface, action.cost) for action in contract.actions
        ),
        "checkpoints": [
            [
                state.observation,
                sorted(
                    (
                        candidate.name,
                        sorted((branch.state, branch.outcome) for branch in candidate.support),
                    )
                    for candidate in state.candidates
                ),
            ]
            for state in contract.states
        ],
    }
    source_bytes = json.dumps(source_projection, ensure_ascii=True, sort_keys=True).encode("ascii")
    return sha256(source_bytes).hexdigest()


def _belief_graph(
    contract: Contract,
    freeze: frozenset[str],
    closed: tuple[bool, ...],
    actions: dict[str, Action],
    representative_only: bool,
) -> dict[Belief, list[tuple[int, tuple[Belief, ...]]]]:
    usable = tuple(
        {
            name: support
            for name, support in available_candidates(state, actions).items()
            if not (
                touched(contract, state_id, support[:1] if representative_only else support) & freeze
            )
        }
        for state_id, state in enumerate(contract.states)
    )
    initial = frozenset({contract.initial})
    frontier = deque([initial])
    discovered = {initial}
    graph = {}
    while frontier:
        belief = frontier.popleft()
        options = []
        graph[belief] = options
        if all(closed[state_id] for state_id in belief):
            continue
        visible_actions = set.intersection(*(set(usable[state_id]) for state_id in belief))
        for action in sorted(visible_actions):
            groups = defaultdict(set)
            for state_id in sorted(belief):
                for branch in usable[state_id][action]:
                    signal = (branch.outcome, contract.states[branch.state].observation)
                    groups[signal].add(branch.state)
            children = tuple(sorted(
                {frozenset(group) for group in groups.values()},
                key=lambda group: tuple(sorted(group)),
            ))
            options.append((actions[action].cost, children))
            for child in children:
                if child not in discovered:
                    discovered.add(child)
                    frontier.append(child)
    return graph


def _solve(
    graph: dict[Belief, list[tuple[int, tuple[Belief, ...]]]],
    initial: Belief,
    closed: tuple[bool, ...],
) -> Evaluation:
    incoming = defaultdict(list)
    parents = []
    costs = []
    remaining = []
    worst_child = []
    labels = {}
    ready = []
    serial = count()
    for parent, options in graph.items():
        if all(closed[state_id] for state_id in parent):
            heappush(ready, (0, next(serial), parent))
        for cost, children in options:
            option_id = len(parents)
            parents.append(parent)
            costs.append(cost)
            remaining.append(len(children))
            worst_child.append(0)
            for child in children:
                incoming[child].append(option_id)

    while ready:
        value, _, belief = heappop(ready)
        if belief in labels:
            continue
        labels[belief] = value
        for option_id in incoming[belief]:
            remaining[option_id] -= 1
            worst_child[option_id] = max(worst_child[option_id], value)
            if remaining[option_id] == 0:
                heappush(ready, (
                    costs[option_id] + worst_child[option_id],
                    next(serial),
                    parents[option_id],
                ))
    return Evaluation(labels.get(initial, inf), len(graph), len(parents), len(labels))


def profiles(contract: Contract, *, representative_only: bool = False) -> tuple[Evaluation, ...]:
    """Solve all eight original PC interventions in manuscript order."""
    validate(contract)
    actions = {action.name: action for action in contract.actions}
    closed = tuple(
        len(checkpoint_target_classes(contract, state_id)) == 1
        for state_id in range(len(contract.states))
    )
    initial = frozenset({contract.initial})
    return tuple(
        _solve(_belief_graph(contract, freeze, closed, actions, representative_only), initial, closed)
        for freeze in FREEZES
    )


def signature(contract: Contract) -> Signature:
    return tuple(evaluation.cost for evaluation in profiles(contract))


def semantic_fact(contract: Contract, checkpoint: int, coordinate: str):
    if not 0 <= checkpoint < len(contract.states):
        raise ContractError("evidence points outside the declared checkpoints")
    state = contract.states[checkpoint]
    if coordinate == "H":
        return state.history
    if coordinate == "R":
        return partition(state.representation)
    if coordinate == "A":
        return state.authority
    raise ContractError("unknown evidence coordinate")


def _check_facts(evidence: Evidence) -> None:
    for fact in evidence.facts:
        if type(fact.checkpoint) is not int or fact.checkpoint < 0:
            raise ContractError("invalid evidence checkpoint")
        if fact.coordinate not in {"H", "R", "A"}:
            raise ContractError("unknown evidence coordinate")


def identify(
    catalog: tuple[Contract, ...],
    evidence: Evidence,
) -> Certificate:
    """Enumerate the compatible finite catalog and return signatures with witnesses."""
    _check_facts(evidence)
    if len({contract.name for contract in catalog}) != len(catalog):
        raise ContractError("completion IDs must be distinct")
    compatible = []
    witnesses = {}
    for contract in sorted(catalog, key=lambda contract: contract.name):
        validate(contract)
        if source_sha256(contract) != evidence.source_sha256:
            continue
        answers = [semantic_fact(contract, fact.checkpoint, fact.coordinate) for fact in evidence.facts]
        if any(answer != fact.value for answer, fact in zip(answers, evidence.facts, strict=True)):
            continue
        compatible.append(contract.name)
        value = signature(contract)
        witnesses.setdefault(value, contract.name)

    values = tuple(sorted(witnesses))
    verdict = {
        0: "INCONSISTENT",
        1: "IDENTIFIED",
    }.get(len(values), "UNDERIDENTIFIED")
    return Certificate(verdict, tuple(compatible), values, tuple((witnesses[v], v) for v in values))
