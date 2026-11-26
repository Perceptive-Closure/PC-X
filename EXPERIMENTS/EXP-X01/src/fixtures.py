
"""Constructed exact PC fixtures, frozen factorials, and deterministic workloads."""

from dataclasses import replace
from itertools import product
from math import inf
from random import Random

from .model import Action, Branch, Candidate, Contract, State

HISTORIES = ("unknown", "reviewed", "fallback", "contrast", "alternate")
COMPATIBILITY = (
    frozenset({0, 1, 2}),
    frozenset({0, 1, 2, 4}),
    frozenset({0, 3}),
)
TARGETS = ("allow", "allow", "deny")
FINE = ("u", "f", "b", "d", "x")
COARSE = ("u", "p", "b", "p", "x")
LOCAL = frozenset({"local"})


def candidate(name, *branches):
    """A source candidate with an explicit positive-support outcome relation."""
    return Candidate(name, tuple(Branch(checkpoint, outcome) for checkpoint, outcome in branches))


def state(history, representation=FINE, observation="ready", rows=(), authority=LOCAL):
    return State(history, representation, authority, observation, rows)


def fixture(name, actions, states, *, source=None):
    return Contract(name, source or name, HISTORIES, TARGETS, COMPATIBILITY, 0, actions, states)


def only_e(value):
    return value, inf, value, value, inf, inf, value, inf


def source_boundary(fast_role: str, fallback_cost: int | None, representation_index: int) -> Contract:
    """One public graph supports either pure-E or pure-R classification of its fast action."""
    actions = (Action("fast", "local", 1), Action("backup", "local", 99 if fallback_cost is None else fallback_cost))
    rows = (candidate("fast", (1, "settled")),)
    if fallback_cost is not None:
        rows += (candidate("backup", (2, "settled")),)
    if fast_role == "E":
        states = (
            state(0, rows=rows),
            state(1, observation="settled"),
            state(2, observation="settled"),
        )
    elif fast_role == "R":
        states = (
            state(1, COARSE, rows=rows),
            state(1, observation="settled"),
            state(2, COARSE, observation="settled"),
        )
    else:
        raise ValueError("fast_role must be E or R")
    if representation_index:
        states = tuple(replace(s, representation=tuple("renamed_" + label for label in s.representation))
                       for s in states)
    return fixture(
        f"boundary/{fast_role}/{fallback_cost}/{representation_index}",
        actions,
        states,
        source="source/fast-check-or-backup",
    )


def boundary_expected(role, backup):
    if role == "E":
        return only_e(1)
    fallback = inf if backup is None else backup
    return 1, 1, fallback, 1, inf, 1, fallback, inf


def hidden_case(visibility, shared_fallback, classify_cost):
    actions = (
        Action("classify", "local", classify_cost),
        Action("left", "local", 2),
        Action("right", "local", 2),
        Action("shared", "local", 5),
    )
    alternative = (candidate("shared", (3, "settled")),) if shared_fallback else ()
    return fixture(
        f"hidden/{visibility}/{int(shared_fallback)}/{classify_cost}",
        actions,
        (
            state(0, rows=(candidate(
                "classify", (1, "seen"), (2, "other" if visibility == "outcome" else "seen")
            ),)),
            state(0, observation="maybe", rows=(candidate("left", (3, "settled")),) + alternative),
            state(0, observation="other" if visibility == "observation" else "maybe",
                  rows=(candidate("right", (3, "settled")),) + alternative),
            state(2, observation="settled"),
        ),
    )


def hidden_expected(visibility, backup, classify_cost):
    value = classify_cost + 2
    if visibility == "merged":
        value = classify_cost + 5 if backup else inf
    return only_e(value)


def mixed_case(reverse_support, fallback_cost):
    branches = ((1, "settled"), (2, "settled"))
    if reverse_support:
        branches = branches[::-1]
    fallback = () if fallback_cost is None else (candidate("fallback", (1, "settled")),)
    return fixture(
        f"mixed/{int(reverse_support)}/{fallback_cost}",
        (Action("atomic", "local", 1), Action("fallback", "local", 99 if fallback_cost is None else fallback_cost)),
        (
            state(0, COARSE, rows=(candidate("atomic", *branches),) + fallback),
            state(2, COARSE, observation="settled"),
            state(1, FINE, observation="settled"),
        ),
        source="source/mixed-all-supports",
    )


def mixed_expected(backup):
    return 1, inf, inf if backup is None else backup, 1, inf, inf, inf if backup is None else backup, inf


def hand_cases():
    anchored = source_boundary("E", 4, 0)
    genuine = replace(
        anchored,
        name="hand/anchored-alternate-history",
        states=(anchored.states[0], replace(anchored.states[1], history=4), anchored.states[2]),
    )
    yield genuine, only_e(1)

    both = LOCAL | {"approved"}
    authority = fixture(
        "hand/authority-gate",
        (Action("review", "local", 2), Action("finish", "approved", 3)),
        (
            state(0, rows=(candidate("review", (1, "admitted")), candidate("finish", (2, "done")))),
            state(0, rows=(candidate("finish", (2, "done")),), authority=both),
            state(2, observation="settled", authority=both),
        ),
    )
    yield authority, (5, inf, 5, inf, inf, inf, inf, inf)

    relative = fixture(
        "hand/target-relative-closed", (),
        (state(2, authority=frozenset()),),
    )
    yield relative, (0,) * 8

    for label, loop_cost, exit_cost, hopeful in (
        ("zero-loop-exit", 0, 3, False),
        ("positive-loop-exit", 2, 3, False),
        ("loop-without-exit", 0, None, False),
        ("hopeful-loop-fallback", 0, 4, True),
    ):
        support = ((0, "pending"), (1, "done")) if hopeful else ((0, "pending"),)
        rows = (candidate("loop", *support),)
        if exit_cost is not None:
            rows += (candidate("deterministic", (1, "done")),)
        control = fixture(
            "hand/" + label,
            (Action("loop", "local", loop_cost), Action("deterministic", "local", exit_cost or 9)),
            (state(0, rows=rows), state(2, observation="settled")),
        )
        yield control, only_e(inf if exit_cost is None else exit_cost)

    mixed_access = fixture(
        "hand/support-union-reduces-actions",
        (Action("enter", "local", 1), Action("fast", "local", 2), Action("backup", "local", 6)),
        (
            state(0, COARSE, rows=(candidate("enter", (1, "open"), (2, "open")),)),
            state(0, COARSE, rows=(candidate("fast", (3, "done")), candidate("backup", (3, "done")))),
            state(0, COARSE, rows=(candidate("fast", (4, "done")), candidate("backup", (3, "done")))),
            state(2, COARSE, "settled"),
            state(1, FINE, "settled"),
        ),
    )
    yield mixed_access, (3, inf, 7, 3, inf, inf, 7, inf)

    batched = fixture(
        "hand/split-vs-batched/atomic",
        (Action("all", "local", 2),),
        (state(0, COARSE, rows=(candidate("all", (1, "done")),)), state(2, FINE, "settled")),
    )
    yield batched, (2, inf, inf, 2, inf, inf, inf, inf)
    split = fixture(
        "hand/split-vs-batched/checkpoint",
        (Action("admit", "local", 1), Action("refresh", "local", 1)),
        (
            state(0, COARSE, rows=(candidate("admit", (1, "reviewed")),)),
            state(2, COARSE, rows=(candidate("refresh", (2, "done")),)),
            state(2, FINE, "settled"),
        ),
    )
    yield split, only_e(1)

    concentrated = fixture(
        "hand/observable-support-shrink",
        (Action("mix", "local", 1), Action("refine", "local", 1), Action("finish", "local", 2)),
        (
            state(0, rows=(candidate("mix", (1, "open"), (2, "open")),)),
            state(0, rows=(candidate("refine", (1, "open"), (3, "done")), candidate("finish", (3, "done")))),
            state(0, rows=(candidate("refine", (1, "open")),)),
            state(2, observation="settled"),
        ),
    )
    yield concentrated, only_e(4)


def factorial_cases(config):
    inputs = config["cross_products"]
    boundary = inputs["source_boundary"]
    for role, fallback, index in product(
        boundary["fast_role"], boundary["fallback_cost"], boundary["representation_index"]
    ):
        yield source_boundary(role, fallback, index), boundary_expected(role, fallback)
    hidden = inputs["hidden_successors"]
    for visible, backup, cost in product(hidden["visibility"], hidden["shared_fallback"], hidden["classify_cost"]):
        yield hidden_case(visible, backup, cost), hidden_expected(visible, backup, cost)
    mixed = inputs["mixed_action"]
    for reverse, fallback in product(mixed["reverse_support"], mixed["fallback_cost"]):
        yield mixed_case(reverse, fallback), mixed_expected(fallback)


def generated_cases(config):
    domains = config["random"]
    for seed, (stratum_id, stratum), index in product(
        domains["seeds"], enumerate(domains["strata"]), range(domains["cases_per_seed_per_stratum"])
    ):
        rng = Random(seed * 10000 + stratum_id * 100 + index)
        n = domains["states_per_case"]
        all_interfaces = frozenset({"local", "approved", "review"})
        acyclic = stratum == "observed_acyclic"
        actions = tuple(Action(name, interface, rng.choice(domains["costs"])) for name, interface in (
            ("probe", "local"), ("inspect", "approved"), ("route", "review"), ("retry", "local")
        ))
        states = []
        for checkpoint in range(n - 2):
            dest = tuple(range(checkpoint + 1, n) if acyclic else range(n))
            n_rows = rng.randint(1, domains["max_candidates_per_state"])
            selected = rng.sample(actions, n_rows)
            rows = []
            for action in selected:
                n_support = rng.randint(1, min(len(dest), domains["max_positive_outcomes"]))
                support = tuple(
                    (successor, "seen" if rng.random() < 0.8 else "alternate")
                    for successor in rng.sample(dest, n_support)
                )
                rows.append(candidate(action.name, *support))
            representation = COARSE if rng.random() < 0.5 else FINE
            history = rng.choice((0, 1, 3)) if representation == COARSE else 0
            if acyclic:
                observation = f"checkpoint-{checkpoint}"
            elif stratum == "split_cyclic":
                observation = f"group-{checkpoint % 2}"
            else:
                observation = "open"
            grants = all_interfaces
            if stratum == "gated_cyclic":
                grants = LOCAL | {other for other in sorted(all_interfaces - LOCAL) if rng.random() < 0.45}
            states.append(state(history, representation, observation, tuple(rows), frozenset(grants)))
        states.extend((
            state(2, FINE, "settled", authority=all_interfaces),
            state(3, FINE, "settled", authority=all_interfaces),
        ))
        name = f"generated/{stratum}/{seed}/{index:02d}"
        yield fixture(name, actions, tuple(states))


def malformed_cases():
    base = source_boundary("E", 4, 0)
    rows = base.states[0].candidates

    def change_start(**changes):
        return replace(base, states=(replace(base.states[0], **changes),) + base.states[1:])

    yield "missing initial state", replace(base, initial=len(base.states))
    yield "invalid partition extent", change_start(representation=("not-total",))
    yield "empty reachable fiber", replace(base, compatibility=(frozenset(),) * len(base.targets))
    yield "invalid outcome or successor", change_start(candidates=(candidate("fast", (99, "invalid")),))
    yield "empty support", change_start(candidates=(replace(rows[0], support=()),))
    yield "duplicate action ID", replace(base, actions=base.actions + (base.actions[0],))
    yield "negative cost", replace(base, actions=(replace(base.actions[0], cost=-1), base.actions[1]))
    yield "invalid authority interface", change_start(authority=frozenset({"undeclared"}))
