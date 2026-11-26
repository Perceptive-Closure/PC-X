"""Versioned source syntax and frozen authorization workload."""

from dataclasses import dataclass
from itertools import product
import random


FRAGMENT = "observable-serial-authority-dag-v1"
FREEZES = ("none", "E", "R", "A", "ER", "EA", "RA", "ERA")
HISTORIES = ("request", "review", "approved", "service", "exception")
CLASSES = (("permit", (0, 1, 2, 3)), ("deny", (1, 4)))
INTERFACES = ("route", "reserve")
OPEN_PARTITION = (0, 0, 1, 2, 2)


class Unsupported(ValueError):
    """The semantics are outside the admitted source fragment."""


@dataclass(frozen=True)
class Branch:
    outcome: str
    successor: int


@dataclass(frozen=True)
class Action:
    name: str
    price: int
    support: tuple[Branch, ...]
    interface: str = "route"


@dataclass(frozen=True)
class Node:
    name: str
    observation: str
    history: int = 0
    labels: tuple[int, ...] = OPEN_PARTITION
    authority: tuple[str, ...] = ("route",)
    effects: tuple[int | None, int | None, int | None] = (None, None, None)
    actions: tuple[Action, ...] = ()


@dataclass(frozen=True)
class Graph:
    nodes: tuple[Node, ...]
    join: int | None


@dataclass(frozen=True)
class Query:
    name: str
    facts: int
    price: int


@dataclass(frozen=True)
class Stage:
    width: int
    clauses: tuple[tuple[int, ...], ...]
    queries: tuple[Query, ...]
    graph: Graph


@dataclass(frozen=True)
class Case:
    name: str
    stratum: str
    seed: int
    correlation: str
    threshold: str
    stages: tuple[Stage, ...]
    terminal: Graph
    freeze: str
    budget: int
    step_cap: int | None = None
    deadline: int | None = None
    fragment: str = FRAGMENT


def node(name, **attributes):
    return Node(name, name, **attributes)


def final_graph():
    return Graph(
        (
            node("decision", actions=(
                Action("commit-approved-history", 1, (Branch("approved", 1),)),
                Action("commit-refined-certificate", 1, (Branch("certified", 2),)),
            )),
            node("approved", history=2),
            node("certified", labels=(0, 4, 1, 2, 2)),
        ),
        None,
    )


def stage_graph(width, surcharge, offsets, fallback, unreachable, alias):
    route_count = width - int(unreachable)
    route_numbers = tuple(range(route_count)) + ((width,) if fallback else ())
    join = 1 + 2 * len(route_numbers) + int(unreachable)
    starts = []
    arms = []
    for i, ordinal in enumerate(route_numbers):
        route = f"route-{ordinal}"
        first = 1 + 2 * i
        starts.append(Action(
            route, 1 + surcharge + 2 * ordinal,
            (Branch("standard", first), Branch("review", first + 1)),
        ))
        effects = (None, None, None) if ordinal == width else (
            (ordinal + offsets[0]) % route_count, ordinal,
            (ordinal + offsets[1]) % route_count,
        )
        primary = f"{route}-standard"
        secondary = f"{route}-review"
        arms.append(node(primary, actions=(
            Action("finish-standard", 1, (Branch("joined", join),)),
        )))
        arms.append(Node(
            secondary, primary if alias and i == 0 else secondary,
            effects=effects,
            actions=(Action("finish-reviewed", 2, (Branch("joined", join),)),),
        ))
    if unreachable:
        arms.append(node("unreached-review", effects=(None, width - 1, None), actions=(
            Action("finish-unreached", 1, (Branch("joined", join),)),
        )))
    return Graph((node("entry", actions=tuple(starts)), *arms, node("join")), join)


def make_case(spec, stratum):
    rng = random.Random(spec["seed"])
    width = spec["width"]
    correlation = spec["correlation"]
    stages = []
    public_floor = 1
    for i in range(spec["stages"]):
        surcharge = rng.randrange(2)
        offsets = (rng.randrange(width), rng.randrange(width))
        correlate_as_xor = rng.randrange(2)
        prices = tuple(rng.randint(1, 7) for _ in range(width + 1))
        public_floor += 3 + surcharge
        clauses = ()
        if correlation in {"xor", "dense"} or (correlation == "half" and i % 2 == 0):
            xor = correlation == "xor" or correlate_as_xor
            clauses = ((1, 2), (-1, -2)) if xor else ((1, -2), (-1, 2))
        elif correlation == "contradiction" and i == 0:
            clauses = ((1,), (-1,))
        hidden = set(spec.get("hidden", ()))
        queries = tuple(
            Query(f"fact-{fact}", 1 << fact, prices[fact])
            for fact in range(width) if fact not in hidden
        )
        if not spec.get("omit_parity", False):
            available = sum(query.facts for query in queries)
            queries += (Query("parity", available, prices[-1]),)
        stages.append(Stage(
            width, clauses, queries,
            stage_graph(width, surcharge, offsets, spec.get("fallback", True),
                        spec.get("unreachable", False), spec.get("alias_observations", False)),
        ))
    slack = {
        "tight": 0, "middle": len(stages), "top": 2 * width * len(stages), "below": -1,
    }[spec["threshold"]]
    return Case(
        spec["name"], stratum, spec["seed"], correlation, spec["threshold"],
        tuple(stages), final_graph(), spec["freeze"], public_floor + slack,
        spec.get("symbolic_step_cap"), spec.get("symbolic_deadline_seconds"),
    )


def workload(protocol):
    grid = protocol["grid"]
    cases = [make_case(control, "control") for control in protocol["controls"]]
    for stratum in ("small", "bridge", "large", "large-matched", "probes"):
        if stratum in {"bridge", "probes"}:
            specs = grid[stratum]
        else:
            design = grid[stratum]
            specs = [
                {
                    "width": width, "stages": length, "correlation": correlation,
                    "seed": design["seed"] + i,
                    "freeze": design.get("freeze", grid["freeze_cycle"][i % len(grid["freeze_cycle"])]),
                    "threshold": design.get("threshold", grid["threshold_cycle"][
                        i % len(grid["threshold_cycle"])
                    ]),
                }
                for i, (width, length, correlation) in enumerate(product(
                    design["widths"], design["stages"], design["correlations"],
                ))
            ]
        for spec in specs:
            name = f"{stratum}-w{spec['width']}-n{spec['stages']}-{spec['correlation']}"
            if stratum == "probes":
                name += f"-{spec['freeze']}-{spec['threshold']}"
            cases.append(make_case({**spec, "name": name}, stratum))
    return tuple(cases)


def _check_graph(graph, width, is_terminal):
    if not graph.nodes or (graph.join is None) != is_terminal:
        raise Unsupported("missing stage join or terminal graph")
    if not is_terminal and (
        graph.join != len(graph.nodes) - 1 or graph.nodes[graph.join].actions
    ):
        raise Unsupported("stage needs a single last join")
    if len({item.name for item in graph.nodes}) != len(graph.nodes):
        raise Unsupported("duplicate checkpoint")
    observations = [item.observation for item in graph.nodes]
    if not all(observations) or len(set(observations)) != len(observations):
        raise Unsupported("checkpoint observations must be distinct")
    for origin, item in enumerate(graph.nodes):
        if (
            type(item.history) is not int or not 0 <= item.history < len(HISTORIES)
            or len(item.labels) != len(HISTORIES)
            or any(type(label) is not int for label in item.labels)
            or len(item.effects) != 3
            or any(fact is not None and (type(fact) is not int or not 0 <= fact < width)
                   for fact in item.effects)
            or len(set(item.authority)) != len(item.authority)
            or not set(item.authority) <= set(INTERFACES)
        ):
            raise Unsupported("invalid semantic profile")
        if len({action.name for action in item.actions}) != len(item.actions):
            raise Unsupported("duplicate source candidate")
        for action in item.actions:
            if not action.name or action.interface != "route" or action.interface not in item.authority:
                raise Unsupported("ordinary availability must be fixed and declared")
            if type(action.price) is not int or not 0 <= action.price <= 10000:
                raise Unsupported("invalid action cost")
            outcomes = [branch.outcome for branch in action.support]
            if not outcomes or not all(outcomes) or len(set(outcomes)) != len(outcomes):
                raise Unsupported("invalid positive support")
            if any(
                type(branch.successor) is not int
                or not origin < branch.successor < len(graph.nodes)
                for branch in action.support
            ):
                raise Unsupported("source edges must advance within the DAG")


def validate_source(case):
    if case.fragment != FRAGMENT or not 1 <= len(case.stages) <= 64:
        raise Unsupported("unrecognized fragment or stage count")
    if case.freeze not in FREEZES or type(case.budget) is not int or not 0 <= case.budget <= 10000:
        raise Unsupported("unsupported freeze or budget")
    _check_graph(case.terminal, 0, True)
    for stage in case.stages:
        if type(stage.width) is not int or not 1 <= stage.width <= 3:
            raise Unsupported("stage width outside the frozen limit")
        if any(
            not clause or any(type(lit) is not int or not 1 <= abs(lit) <= stage.width
                              for lit in clause)
            for clause in stage.clauses
        ):
            raise Unsupported("evidence must consist of stage-local Boolean clauses")
        names = [query.name for query in stage.queries]
        if not all(names) or len(set(names)) != len(names):
            raise Unsupported("invalid query names")
        for query in stage.queries:
            if (
                type(query.facts) is not int or not 1 <= query.facts < 1 << stage.width
                or type(query.price) is not int or not 1 <= query.price <= 10000
            ):
                raise Unsupported("queries must be positive-cost local parity readings")
        _check_graph(stage.graph, stage.width, False)
