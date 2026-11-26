"""Frozen hand controls and deterministic case generation."""

from dataclasses import replace
from itertools import product
from random import Random

from model import Case, Checkpoint, Route


def closer(refine=False, *, mixed=False, authority=False):
    admit = True if mixed else (not refine if type(refine) is bool else -refine)
    return Checkpoint(terminal=True, admit=admit, refine=refine, expand_authority=authority)


def parallel(name, stratum, count, clauses, costs, *, fallback=False, authority=False):
    checkpoints = tuple(closer(i, authority=i if authority else False)
                        for i in range(1, count + 1))
    if fallback:
        checkpoints += (closer(),)
    root_routes = tuple(Route(f"finish-{i}", cost, (i,)) for i, cost in enumerate(costs, 1))
    return Case(name, stratum, feature_names(count), clauses, (Checkpoint(), *checkpoints),
                (root_routes, *((),) * len(checkpoints)))


def observable_fork(name, stratum, count, clauses, costs):
    first, left, left_fallback, right, right_fallback = costs
    checkpoints = (
        Checkpoint(), Checkpoint(), Checkpoint(),
        closer(1, authority=3 if count >= 3 else False), closer(),
        closer(2, authority=4 if count >= 4 else False), closer(),
    )
    return Case(name, stratum, feature_names(count), clauses, checkpoints, (
        (Route("inspect", first, (1, 2)),),
        (Route("left-fast", left, (3,)), Route("left-fallback", left_fallback, (4,))),
        (Route("right-fast", right, (5,)), Route("right-fallback", right_fallback, (6,))),
        (), (), (), (),
    ))


def feature_names(count):
    return tuple(f"semantic_fact_{i}" for i in range(1, count + 1))


def control_cases():
    xor = ((1, 2), (-1, -2))
    equal = ((-1, 2), (1, -2))
    implication_chain = ((-1, 2), (-2, 3))
    mixed = Case(
        "mixed-support", "control", feature_names(2), xor,
        (Checkpoint(), closer(), closer(1, mixed=True), closer(2), closer()),
        ((Route("atomic", 1, (1, 2)), Route("other", 3, (3,)), Route("fallback", 6, (4,))),
         (), (), (), ()),
    )
    ablated = replace(mixed, name="mixed-first-only",
                      routes=((replace(mixed.routes[0][0], successors=(1,)), *mixed.routes[0][1:]),
                              *mixed.routes[1:]))
    return (
        parallel("complementary", "control", 2, xor, (1, 1)),
        parallel("independent", "control", 2, (), (1, 1)),
        parallel("co-occurrence", "control", 2, equal, (1, 3)),
        parallel("joint-tradeoff", "control", 2, xor, (1, 3)),
        parallel("finite-fallback", "control", 2, xor, (1, 2, 5), fallback=True),
        parallel("dependency-chain", "control", 3, implication_chain, (1, 2, 4), authority=True),
        mixed,
        ablated,
        observable_fork("branched-policy", "control", 2, xor, (1, 2, 7, 4, 6)),
        parallel("infeasible", "control", 2, ((1,), (-1,)), (1, 1)),
    )


def exhaustive_cases(protocol):
    count = protocol["exhaustive_variables"]
    domain = tuple(product((False, True), repeat=count))
    for pair in protocol["exhaustive_cost_pairs"]:
        for mask in range(1 << len(domain)):
            # Each clause forbids exactly one full assignment omitted by this truth mask.
            clauses = tuple(tuple(-i if bit else i for i, bit in enumerate(row, 1))
                            for number, row in enumerate(domain) if not mask & (1 << number))
            name = f"truth-{pair[0]}-{pair[1]}-{mask:02d}"
            yield parallel(name, "exhaustive", count, clauses, pair)


def seeded_cases(protocol):
    for seed in protocol["generated_seed_schedule"]:
        rng = Random(seed)
        for index in range(protocol["generated_per_seed"]):
            count = protocol["generated_variables"][index % 2]
            topology = protocol["generated_topologies"][(index // 2) % 2]
            cost_count = count + 1 if topology == "parallel" else 5
            costs = tuple(rng.randint(*protocol["generated_cost_range"]) for _ in range(cost_count))
            clauses = []
            for _ in range(rng.randint(*protocol["generated_clause_count_range"])):
                width = rng.randint(*protocol["generated_clause_width_range"])
                variables = rng.sample(range(1, count + 1), width)
                clauses.append(tuple(i if rng.randrange(2) else -i for i in variables))
            name = f"seed-{seed}-{index:02d}"
            if topology == "parallel":
                yield parallel(name, topology, count, tuple(clauses), costs,
                               fallback=True, authority=index % 3 == 0)
            else:
                yield observable_fork(name, topology, count, tuple(clauses), costs)


def all_cases(protocol):
    hand = control_cases()
    if tuple(case.name for case in hand) != tuple(protocol["controls"]):
        raise ValueError("Hand-case sequence differs from the frozen protocol.")
    return (*hand, *exhaustive_cases(protocol), *seeded_cases(protocol))
