"""Finite authorization fixtures with extensional touch and native PC coordinates.

These controls describe mathematical contracts for a local authorization task.
They do not query a production system or require a product-specific engine.
"""

from dataclasses import dataclass
from functools import cache
from itertools import product
from json import dumps

from .certificates import Completion, Problem


COMPATIBILITY = {"current": {"parcel-a"}, "alias": {"parcel-b"}, "verified": {"parcel-a", "parcel-c"}}
AUTHORIZATION_TARGET = {"parcel-a": "approve", "parcel-b": "deny", "parcel-c": "approve"}
BASE_PARTITION = frozenset((frozenset(("current", "alias")), frozenset(("verified",))))
REFINED_PARTITION = frozenset(frozenset((name,)) for name in COMPATIBILITY)
BASE_AUTHORITY = frozenset(("fast", "archive", "grant"))
GRANTED_AUTHORITY = BASE_AUTHORITY | {"certified"}


@dataclass(frozen=True)
class Coordinates:
    history: str
    equivalence: frozenset[frozenset[str]]
    authority: frozenset[str]


@dataclass(frozen=True)
class SemanticCompletion:
    fast: str
    archive: str
    certified_at_entry: bool

    @property
    def identity(self):
        return f"{self.fast}/{self.archive}/{int(self.certified_at_entry)}"

    def query_answers(self):
        license_status = "entry" if self.certified_at_entry else "after-grant"
        return {
            "fast_admission": self.fast,
            "archive_mapping": self.archive,
            "entry_license": license_status,
            "fast_and_license": f"{self.fast}:{license_status}",
        }


def closed(coordinates):
    cell = next(block for block in coordinates.equivalence if coordinates.history in block)
    worlds = set().union(*(COMPATIBILITY[history] for history in cell))
    possible_targets = {AUTHORIZATION_TARGET[world] for world in worlds}
    return len(possible_targets) == 1


def touch(before, after):
    coordinates = (
        ("E", before.history, after.history),
        ("R", before.equivalence, after.equivalence),
        ("A", before.authority, after.authority),
    )
    return frozenset(name for name, prior, later in coordinates if prior != later)


def evaluate(completion, costs, freezes):
    """Evaluate all frozen optimal costs on a state-visible deterministic DAG."""
    entry_authority = GRANTED_AUTHORITY if completion.certified_at_entry else BASE_AUTHORITY
    coordinates = {
        "entry": Coordinates("current", BASE_PARTITION, entry_authority),
        "granted": Coordinates("current", BASE_PARTITION, GRANTED_AUTHORITY),
    }
    offered = {"entry": ("grant", "fast", "archive", "certified"),
               "granted": ("fast", "archive", "certified")}
    edges = {"entry": {}, "granted": {}}
    modes = {"fast": completion.fast, "archive": completion.archive, "certified": "E"}
    for state, actions in offered.items():
        current = coordinates[state]
        for action in actions:
            if action not in current.authority:
                continue
            if action == "grant":
                edges[state][action] = "granted"
                continue
            terminal = f"{state}/{action}"
            mode = modes[action]
            coordinates[terminal] = Coordinates(
                "verified" if mode == "E" else current.history,
                REFINED_PARTITION if mode == "R" else current.equivalence,
                current.authority,
            )
            edges[state][action] = terminal

    @cache
    def cost_to_close(state, frozen):
        if closed(coordinates[state]):
            return 0
        candidates = []
        for action, successor in edges.get(state, {}).items():
            if frozen & touch(coordinates[state], coordinates[successor]):
                continue
            continuation = cost_to_close(successor, frozen)
            if continuation is not None:
                candidates.append(costs[action] + continuation)
        return min(candidates, default=None)

    return tuple(
        cost_to_close("entry", frozenset() if freeze == "none" else frozenset(freeze))
        for freeze in freezes
    )


def independent_path_costs(completion, costs, freezes):
    """Enumerate legitimate action sequences directly from underlying source facts."""
    path_specs = [
        (completion.fast, ("fast",)),
        (completion.archive, ("archive",)),
    ]
    if completion.certified_at_entry:
        path_specs.append(("E", ("certified",)))
    else:
        path_specs.append(("AE", ("grant", "certified")))
    # Waiting until after an optional grant to use fast/archive cannot improve
    # either path. Grant has strictly positive cost and adds no available
    # closer other than certified. This argument is specific to this fixture.
    values = []
    for freeze in freezes:
        valid = (
            sum(costs[name] for name in path)
            for resources, path in path_specs
            if freeze == "none" or all(resource not in freeze for resource in resources)
        )
        values.append(min(valid, default=None))
    return tuple(values)


def cases(config):
    freezes = config["freeze_order"]
    factual_costs = config["action_costs"]
    query_costs = config["query_costs"]
    all_queries = tuple(query_costs)
    support = list(SemanticCompletion(*assignment) for assignment in product("ER", "ER", (False, True)))
    assessed = {}
    for completion in support:
        signature = evaluate(completion, factual_costs, freezes)
        if signature != independent_path_costs(completion, factual_costs, freezes):
            raise AssertionError(("PC signature disagreement", completion.identity, signature))
        assessed[completion] = signature

    condition = {
        "pc_grid_rfreeze": (lambda completion: True, all_queries, "R"),
        "pc_grid_signature": (lambda completion: True, all_queries, "all"),
        "pc_correlated_rfreeze": (lambda completion: completion.fast != completion.archive, all_queries, "R"),
        "pc_missing_fast_rfreeze": (lambda completion: True, ("archive_mapping", "entry_license"), "R"),
        "pc_homogeneous_rfreeze": (lambda completion: completion.fast == "E", all_queries, "R"),
    }
    for name in config["fixtures"]:
        admit, queries, target = condition[name]
        rows = []
        for completion, signature in assessed.items():
            if not admit(completion):
                continue
            value = signature if target == "all" else signature[freezes.index(target)]
            signature_token = dumps(value, separators=(",", ":"))
            answers = completion.query_answers()
            rows.append(Completion(completion.identity, tuple(answers[query] for query in queries), signature_token))
        yield Problem(name, queries, tuple(query_costs[query] for query in queries), tuple(rows))
