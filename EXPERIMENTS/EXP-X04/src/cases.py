"""Frozen finite workload and authorization fixtures for EXP-X04."""

from dataclasses import dataclass
from functools import cache
from itertools import product
from random import Random

from .audit import Case, Completion


FREEZES = ("", "E", "R", "A", "ER", "EA", "RA", "ERA")
ROLES = ("admission", "representation", "authority")
COMPATIBLE_WORLDS = {
    "current": ("ordinary",),
    "alias": ("restricted",),
    "verified": ("verified-ordinary",),
}
WORLD_TARGETS = {"ordinary": "approve", "restricted": "deny", "verified-ordinary": "approve"}
BASE_EQUIVALENCE = frozenset((frozenset(("current", "alias")), frozenset(("verified",))))
REFINED_EQUIVALENCE = frozenset(frozenset((history,)) for history in COMPATIBLE_WORLDS)


def _case(name, family, queries, costs, records):
    return Case(name, family, tuple(queries), tuple(costs), tuple(records))


def _record_rows(items):
    return [
        Completion(f"c{index:03d}", tuple(answers), str(target))
        for index, (answers, target) in enumerate(items)
    ]


def controls(names):
    bits = tuple(product("01", repeat=3))
    majority = _record_rows((row, int(row.count("1") >= 2)) for row in bits)
    parity = _record_rows((row, row.count("1") % 2) for row in bits)
    query_ids = ("first", "second", "third")
    cases = {
        "empty_domain": _case("empty_domain", "control", ("q",), (1,), ()),
        "constant_target": _case(
            "constant_target", "control", ("fact",), (3,),
            _record_rows(((("0",), "approve"), (("1",), "approve"))),
        ),
        "no_queries": _case(
            "no_queries", "control", (), (),
            _record_rows((((), "approve"), ((), "deny"))),
        ),
        "full_answer_alias": _case(
            "full_answer_alias", "control", ("flag", "kind"), (1, 2),
            _record_rows((
                (("0", "A"), "approve"), (("0", "A"), "deny"), (("1", "B"), "approve"),
            )),
        ),
        "majority_of_three": _case("majority_of_three", "control", query_ids, (1, 1, 1), majority),
        "categorical_weighted": _case(
            "categorical_weighted", "control", ("route", "left", "right"), (2, 1, 3),
            _record_rows(
                ((route, left, right), right if route == "gray" else left)
                for route, left, right in product(("red", "blue", "gray"), "01", "01")
            ),
        ),
        "all_queries_required": _case("all_queries_required", "control", query_ids, (1, 2, 3), parity),
        "cost_scale_three": _case("cost_scale_three", "control", query_ids, (3, 3, 3), majority),
    }
    return [cases[name] for name in names]


def address(width, unit_cost):
    size = 2 ** width
    queries = [f"address_{index}" for index in range(width)]
    queries += [f"data_{index}" for index in range(size)]
    rows = _record_rows(
        ((*f"{selected:0{width}b}", *data), data[selected])
        for selected in range(size)
        for data in product("01", repeat=size)
    )
    return _case(f"address_{width}", "address", queries, [unit_cost] * len(queries), rows)


def address_bounds(width, unit_cost):
    size = 2 ** width
    lower = min(t + 2 ** (width - t) for t in range(width + 1))
    if lower != width + 1:
        raise AssertionError("address lower bound arithmetic failed")
    return {
        "width": width, "mode": "derived", "query_count": width + size,
        "domain_size": 2 ** (width + size), "minimax_cost": unit_cost * lower,
        "max_local_cost": unit_cost * lower, "static_cost": unit_cost * (width + size),
    }


@dataclass(frozen=True)
class Checkpoint:
    history: str
    equivalence: frozenset
    authority: frozenset


def _closed(state):
    cell = next(group for group in state.equivalence if state.history in group)
    labels = {WORLD_TARGETS[world] for history in cell for world in COMPATIBLE_WORLDS[history]}
    return len(labels) == 1


def _touch(start, end):
    compared = zip(
        "ERA",
        (start.history, start.equivalence, start.authority),
        (end.history, end.equivalence, end.authority),
        strict=True,
    )
    return {name for name, origin, destination in compared if origin != destination}


def _workflow(role, favorable, cfg):
    direct = role != "authority" or favorable
    first_authority = frozenset(("fallback", "fast" if direct else "grant"))
    later_authority = frozenset(("fallback", "fast"))
    states = {
        # The route changes the visible control location only.
        "dispatch": Checkpoint("current", BASE_EQUIVALENCE, first_authority),
        "site": Checkpoint("current", BASE_EQUIVALENCE, first_authority),
        "granted": Checkpoint("current", BASE_EQUIVALENCE, later_authority),
    }
    edges = {"dispatch": [("site", cfg["dispatch_cost"])]}
    for checkpoint, state in tuple(states.items())[1:]:
        outgoing = []
        for action in sorted(state.authority):
            if action == "grant":
                outgoing.append(("granted", cfg["grant_cost"]))
                continue
            admit = action == "fallback" or role != "admission" or favorable
            remap = action == "fast" and role in ("admission", "representation") and not favorable
            destination = f"{checkpoint}/{action}"
            states[destination] = Checkpoint(
                "verified" if admit else state.history,
                REFINED_EQUIVALENCE if remap else state.equivalence,
                state.authority,
            )
            outgoing.append((destination, cfg[f"{action}_cost"]))
        edges[checkpoint] = outgoing

    @cache
    def value(checkpoint, freeze):
        if _closed(states[checkpoint]):
            return 0
        costs = []
        for successor, cost in edges.get(checkpoint, ()):
            if _touch(states[checkpoint], states[successor]).intersection(freeze):
                continue
            continuation = value(successor, freeze)
            if continuation is not None:
                costs.append(cost + continuation)
        return min(costs, default=None)

    signature = tuple(value("dispatch", freeze) for freeze in FREEZES)
    value.cache_clear()
    return signature


def _independent_route_paths(role, favorable, cfg):
    paths = [(frozenset("E"), cfg["fallback_cost"])]
    if favorable:
        paths.append((frozenset("E"), cfg["fast_cost"]))
    elif role == "admission":
        paths.append((frozenset("R"), cfg["fast_cost"]))
    elif role == "representation":
        paths.append((frozenset("ER"), cfg["fast_cost"]))
    else:
        paths.append((frozenset("EA"), cfg["grant_cost"] + cfg["fast_cost"]))
    return tuple(
        min(
            (cfg["dispatch_cost"] + cost for touched, cost in paths if touched.isdisjoint(freeze)),
            default=None,
        )
        for freeze in FREEZES
    )


def routed(cfg, condition):
    site_costs = condition["site_costs"]
    sites = range(len(site_costs))
    if condition["route_cost"] is None:
        query_names, costs = [], []
    else:
        query_names, costs = ["dispatch_endpoint"], [condition["route_cost"]]
    permitted = [
        (site, f"site_{site}_{ROLES[site % len(ROLES)]}")
        for site, cost in enumerate(site_costs) if cost is not None
    ]
    query_names.extend(name for _, name in permitted)
    costs.extend(site_costs[site] for site, _ in permitted)

    prior = condition.get("route_prior_weights", [1] * len(site_costs))
    facts = {
        "admission": ("certificate-refinement", "verified-history"),
        "representation": ("remap", "stable"),
        "authority": ("grant-required", "entry-licensed"),
    }
    rows = []
    for site, switches in product(sites, product((False, True), repeat=len(site_costs))):
        signatures = []
        for index, favorable in enumerate(switches):
            role = ROLES[index % len(ROLES)]
            signature = _workflow(role, favorable, cfg)
            if signature != _independent_route_paths(role, favorable, cfg):
                raise AssertionError((condition["name"], role, favorable, signature))
            signatures.append(signature)

        answers = [] if condition["route_cost"] is None else [f"checkpoint-{site}"]
        answers.extend(
            facts[ROLES[index % len(ROLES)]][switches[index]] for index, _ in permitted
        )
        identity = f"{site}/" + "".join(str(int(switch)) for switch in switches)
        target = str(signatures[site][FREEZES.index("R")])
        rows.append(Completion(identity, tuple(answers), target, prior[site]))

    return _case(condition["name"], "routed_pc", query_names, costs, rows)


def sampled(cfg):
    for stratum, family in enumerate(cfg["conditions"]):
        for trial in range(cfg["cases_per_condition"]):
            seed = cfg["seed"] + stratum * cfg["cases_per_condition"] + trial
            rng = Random(seed)
            width = rng.randint(cfg["minimum_queries"], cfg["maximum_queries"])
            size = rng.randint(cfg["minimum_completions"], cfg["maximum_completions"])
            costs = [rng.randint(cfg["minimum_cost"], cfg["maximum_cost"]) for _ in range(width)]
            rows = []
            for index in range(size):
                if family == "correlated":
                    first, second, third = (rng.randrange(2) for _ in range(3))
                    basis = (first, second, third, first ^ second, second & third)
                    answers = tuple(str(basis[query % len(basis)]) for query in range(width))
                else:
                    alphabet = 3 if family == "categorical" else 2
                    answers = tuple(str(rng.randrange(alphabet)) for _ in range(width))
                target = str(rng.randrange(3 if family == "categorical" else 2))
                weight = rng.randint(cfg["minimum_prior_weight"], cfg["maximum_prior_weight"])
                if family == "aliased" and index == size - 1:
                    answers = rows[0].answers
                    target = str(1 - int(rows[0].target))
                rows.append(Completion(f"c{index:03d}", answers, target, weight))

            yield _case(
                f"seeded_{family}_{trial:02d}", f"seeded_{family}",
                (f"fact_{query}" for query in range(width)), costs, rows,
            )
