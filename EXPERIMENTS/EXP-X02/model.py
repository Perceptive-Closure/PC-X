"""Source-anchored finite semantic completions and exact worst-support costs."""

from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
from math import inf
from pathlib import Path
import sys

FREEZE_NAMES = ("none", "E", "R", "A", "ER", "EA", "RA", "ERA")
FREEZES = (frozenset(), *(frozenset(name) for name in FREEZE_NAMES[1:]))
HISTORIES = ("draft", "verified", "contrary")
TARGETS = ("permit", "deny")
COMPATIBILITY = (frozenset({0, 1}), frozenset({2}))
COARSE = ("aliased", "verified", "aliased")
FINE = ("draft", "verified", "contrary")
X01_MODEL_HASH = "6a2b78ea1284ac7ccba1edc0ecc80a9cdbc2d9f2de57a06a6fa216b93a357a2e"

type Condition = bool | int
type Assignment = tuple[bool, ...]
type Locator = tuple[int, str]
type Touch = frozenset[str]
type Signature = tuple[int | float, ...]


class UnsupportedKernel(ValueError):
    """The comparison does not have the required finite, fixed source kernel."""


@dataclass(frozen=True)
class Checkpoint:
    terminal: bool = False
    admit: Condition = False
    refine: Condition = False
    expand_authority: Condition = False


@dataclass(frozen=True)
class Route:
    name: str
    cost: int
    successors: tuple[int, ...]


@dataclass(frozen=True)
class Case:
    name: str
    stratum: str
    features: tuple[str, ...]
    clauses: tuple[tuple[int, ...], ...]
    checkpoints: tuple[Checkpoint, ...]
    routes: tuple[tuple[Route, ...], ...]


def validate_case(case: Case, limits: dict[str, int]) -> None:
    variables = len(case.features)
    if not 0 < variables <= limits["boolean_variables"] or len(set(case.features)) != variables:
        raise UnsupportedKernel("Feature names must be distinct within the finite domain.")
    if any(type(literal) is not int or not 1 <= abs(literal) <= variables
           for clause in case.clauses for literal in clause):
        raise UnsupportedKernel("A clause uses a literal outside the declared feature domain.")
    states = len(case.checkpoints)
    if not 0 < states <= limits["checkpoints"] or states != len(case.routes):
        raise UnsupportedKernel("Checkpoints and source route tables must align.")
    if sum(map(len, case.routes)) > limits["action_locators"]:
        raise UnsupportedKernel("Too many source action locators for this fragment.")
    for index, (checkpoint, routes) in enumerate(zip(case.checkpoints, case.routes, strict=True)):
        conditions = (checkpoint.admit, checkpoint.refine, checkpoint.expand_authority)
        if any(type(condition) is not bool and
               (type(condition) is not int or not 1 <= abs(condition) <= variables)
               for condition in conditions):
            raise UnsupportedKernel("Checkpoint semantics use an undeclared feature.")
        if checkpoint.terminal and routes:
            raise UnsupportedKernel("Terminal checkpoints must have no further protocol routes.")
        if len({route.name for route in routes}) != len(routes):
            raise UnsupportedKernel("A source action locator occurs twice.")
        for route in routes:
            if (not route.name or type(route.cost) is not int or route.cost < 0
                    or not route.successors
                    or len(set(route.successors)) != len(route.successors)
                    or any(type(child) is not int or not index < child < states
                           for child in route.successors)):
                raise UnsupportedKernel("Each route needs cost and forward positive-support successors.")


def value(condition: Condition, assignment: Assignment) -> bool:
    if type(condition) is bool:
        return condition
    bit = assignment[abs(condition) - 1]
    return bit if condition > 0 else not bit


def compatible_assignments(case: Case) -> tuple[Assignment, ...]:
    """Reject impossible partial assignments as soon as a complete clause is false."""
    result = []

    def visit(prefix: Assignment) -> None:
        if any(all(abs(literal) <= len(prefix) and not value(literal, prefix)
                   for literal in clause) for clause in case.clauses):
            return
        if len(prefix) == len(case.features):
            result.append(prefix)
        else:
            visit(prefix + (False,))
            visit(prefix + (True,))

    visit(())
    return tuple(result)


@lru_cache(maxsize=1)
def x01():
    """Import only the byte-verified model from the frozen X01 commit archive."""
    root = Path(__file__).resolve().parents[2]
    model = root / "scratch/x01/EXPERIMENTS/EXP-X01/src/model.py"
    if not model.is_file():
        raise FileNotFoundError("Prepare the pinned X01 source with prepare-x01.ps1.")
    if sha256(model.read_bytes()).hexdigest() != X01_MODEL_HASH:
        raise ValueError("The X01 model does not match the frozen source digest.")
    spec = spec_from_file_location("pcx_x01_a52d45f_model", model)
    if spec is None or spec.loader is None:
        raise ImportError("Could not load the pinned X01 model.")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def materialize(case: Case, assignment: Assignment):
    """Resolve semantics first, then convert the common source graph into an X01 contract."""
    if len(assignment) != len(case.features) or any(type(bit) is not bool for bit in assignment):
        raise ValueError("A completion needs one Boolean per declared feature.")
    api = x01()
    states = []
    actions = [api.Action("local-interface", "local", 0),
               api.Action("reserve-interface", "reserve", 0)]
    for index, (checkpoint, routes) in enumerate(zip(case.checkpoints, case.routes, strict=True)):
        rows = []
        for route in routes:
            name = f"{index}:{route.name}"
            actions.append(api.Action(name, "local", route.cost))
            support = tuple(api.Branch(child, f"outcome-{pos}")
                            for pos, child in enumerate(route.successors))
            rows.append(api.Candidate(name, support))
        history = int(value(checkpoint.admit, assignment))
        representation = FINE if value(checkpoint.refine, assignment) else COARSE
        authority = frozenset({"local", "reserve"} if value(checkpoint.expand_authority, assignment)
                              else {"local"})
        states.append(api.State(history, representation, authority, f"checkpoint-{index}", tuple(rows)))
    identity = "".join(str(int(bit)) for bit in assignment)
    return api.Contract(identity, case.name, HISTORIES, TARGETS, COMPATIBILITY, 0,
                        tuple(actions), tuple(states))


def kernel_key(contract, case: Case) -> tuple:
    """Anchor ordinary availability, closure, observations and complete source support."""
    api = x01()
    api.validate(contract)
    actions = {action.name: action for action in contract.actions}
    state_keys = []
    if len(contract.states) != len(case.checkpoints) or contract.initial != 0:
        raise UnsupportedKernel("The completion moved a source checkpoint.")
    for index, (state, checkpoint) in enumerate(zip(contract.states, case.checkpoints, strict=True)):
        classes = api.checkpoint_target_classes(contract, index)
        expected_classes = frozenset({"permit"}) if checkpoint.terminal else frozenset(TARGETS)
        if classes != expected_classes:
            raise UnsupportedKernel("A completion changed the frozen target classes at a checkpoint.")
        enabled = api.available_candidates(state, actions)
        source_available = {
            f"{index}:{route.name}": tuple((child, f"outcome-{pos}")
                                          for pos, child in enumerate(route.successors))
            for route in case.routes[index]
        }
        actual = {name: tuple((branch.state, branch.outcome) for branch in support)
                  for name, support in enabled.items()}
        if actual != source_available or len(state.candidates) != len(source_available):
            raise UnsupportedKernel("A completion changed action availability or fixed positive support.")
        if state.observation != f"checkpoint-{index}":
            raise UnsupportedKernel("A completion changed the observable checkpoint names.")
        state_keys.append((state.observation, tuple(sorted(classes)), tuple(actual.items())))
    return api.source_sha256(contract), tuple(state_keys)


def locators(case: Case) -> tuple[Locator, ...]:
    return tuple((index, route.name) for index, routes in enumerate(case.routes) for route in routes)


def touch_profile(case: Case, contract) -> dict[Locator, Touch]:
    """Use the frozen X01 extensional touch rule on complete atomic supports."""
    return {
        (index, route.name): x01().touched(contract, index, candidate.support)
        for index, routes in enumerate(case.routes)
        for route, candidate in zip(routes, contract.states[index].candidates, strict=True)
    }


def cost_after_removal(case: Case, blocked: set[Locator]) -> int | float:
    values = [inf] * len(case.checkpoints)
    for index in reversed(range(len(values))):
        if case.checkpoints[index].terminal:
            values[index] = 0
            continue
        values[index] = min(
            (route.cost + max(values[child] for child in route.successors)
             for route in case.routes[index] if (index, route.name) not in blocked),
            default=inf,
        )
    return values[0]


def blocked_actions(profile: dict[Locator, Touch], freeze: frozenset[str]) -> set[Locator]:
    return {locator for locator, touched in profile.items() if touched & freeze}


def signature(case: Case, profile: dict[Locator, Touch]) -> Signature:
    return tuple(cost_after_removal(case, blocked_actions(profile, freeze)) for freeze in FREEZES)
