"""Frozen exhaustive, seeded, and adversarial workloads for EXP-X03."""

from itertools import combinations, product
from random import Random

from . import authorization
from .certificates import Completion, Problem


def make_problem(name, costs, rows, *, queries=None):
    if queries is None:
        queries = tuple(f"q{index}" for index in range(len(costs)))
    completions = tuple(
        Completion(f"c{index}", tuple(str(answer) for answer in answers), str(target))
        for index, (answers, target) in enumerate(rows)
    )
    return Problem(name, tuple(queries), tuple(costs), completions)


def hand_controls():
    weighted = [((0, 0, 0), 0), ((1, 0, 1), 1), ((0, 1, 1), 1)]
    categorical = [(("red", 0), "A"), (("green", 0), "B"), (("blue", 0), "C")]
    return {
        "empty_evidence": make_problem("empty_evidence", (3,), []),
        "homogeneous_distinct_contracts": make_problem(
            "homogeneous_distinct_contracts", (2, 3), [((0, 0), 1), ((0, 1), 1), ((1, 0), 1)],
        ),
        "no_queries_heterogeneous": make_problem("no_queries_heterogeneous", (), [((), 0), ((), 1)]),
        "localized_inaccessibility": make_problem(
            "localized_inaccessibility", (2,), [((0,), 0), ((0,), 1), ((1,), 2)],
        ),
        "weighted_deletion_trap": make_problem("weighted_deletion_trap", (2, 2, 9), weighted),
        "greedy_cover_trap": make_problem(
            "greedy_cover_trap", (1, 1, 1),
            [((0, 0, 0), 0)]
            + [((int(i in (0, 1, 3, 4)), int(i < 3), int(i >= 3)), 1) for i in range(6)],
        ),
        "strict_local_global": make_problem(
            "strict_local_global", (1, 1, 1, 1),
            [(tuple(int(i == j) for i in range(4)), int(j > 1)) for j in range(4)],
        ),
        "categorical_query": make_problem("categorical_query", (3, 1), categorical),
        "equal_cost_ties": make_problem("equal_cost_ties", (2, 2), [((0, 1), 0), ((1, 0), 1)]),
        "cost_perturbation": make_problem("cost_perturbation", (2, 2, 1), weighted),
        "missing_query_perturbation": make_problem(
            "missing_query_perturbation", (1,), [((row[0][1],), row[1]) for row in categorical],
        ),
        "answer_perturbation": make_problem(
            "answer_perturbation", (3, 1), [(("green", 0), "A"), *categorical[1:]],
        ),
    }


def exhaustive(config):
    profiles = config["answer_profiles"]
    for size in range(1, len(profiles) + 1):
        for ids in combinations(range(len(profiles)), size):
            for targets in product("01", repeat=size):
                rows = [(profiles[i], target) for i, target in zip(ids, targets, strict=True)]
                for ordinal, costs in enumerate(config["distinct_profile_costs"]):
                    profile_ids = "".join(str(i) for i in ids)
                    yield make_problem(f"distinct-{profile_ids}-{''.join(targets)}-{ordinal}", costs, rows)
    for ids in product(range(len(profiles)), repeat=3):
        for targets in product("01", repeat=3):
            rows = [(profiles[i], target) for i, target in zip(ids, targets, strict=True)]
            profile_ids = "".join(str(i) for i in ids)
            yield make_problem(f"alias-{profile_ids}-{''.join(targets)}", config["three_slot_alias_costs"], rows)


def seeded(config):
    for family_index, family in enumerate(config["strata"]):
        for case in range(config["cases_per_stratum"]):
            seed = config["base_seed"] + family_index * config["cases_per_stratum"] + case
            rng = Random(seed)
            n = rng.randint(config["completion_min"], config["completion_max"])
            width = rng.randint(config["query_min"], config["query_max"])
            costs = tuple(rng.randint(config["cost_min"], config["cost_max"]) for _ in range(width))
            rows = []
            for _ in range(n):
                if family == "binary_sparse":
                    answers = tuple(int(rng.randrange(5) == 0) for _ in range(width))
                    target = rng.randrange(2)
                elif family == "categorical":
                    answers = tuple(rng.randrange(3) for _ in range(width))
                    target = rng.randrange(3)
                elif family == "forced_alias":
                    answers = tuple(rng.randrange(2) for _ in range(width))
                    target = rng.randrange(2)
                elif family == "correlated":
                    x, y = rng.randrange(2), rng.randrange(2)
                    values = (x, y, x ^ y, x | y)
                    answers = tuple(values[q % len(values)] for q in range(width))
                    target = x + y
                else:
                    raise ValueError(f"unsupported seeded stratum: {family}")
                rows.append((answers, target))
            if family == "forced_alias":
                rows[1] = (rows[0][0], 1 - rows[0][1])
            yield family, seed, make_problem(f"{family}-{seed}", costs, rows)


def cases(config):
    controls = hand_controls()
    for name in config["controls"]:
        yield "control", None, controls[name]
    for case in exhaustive(config["exhaustive"]):
        yield "exhaustive_distinct" if case.name.startswith("distinct") else "exhaustive_alias", None, case
    yield from seeded(config["seeded"])
    for case in authorization.cases(config["authorization"]):
        yield "pc_authorization", None, case
