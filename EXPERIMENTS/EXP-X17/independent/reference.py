"""Exact explicit-history reference LP for finite declared good installations."""

import argparse
from fractions import Fraction as F
from itertools import product
import json
from pathlib import Path
import time

from model import Installation, PRICES, RISK_CAP, bit_one, final_probability, stay_probability


MENUS = {
    "full": ("skip", "low", "high"),
    "high_skip": ("skip", "high"),
    "low_skip": ("skip", "low"),
    "no_paid": ("skip",),
}


def histories(world):
    stay = stay_probability(world)
    for word in product((0, 1), repeat=world.N):
        last, chance = 0, F(1)
        for v in word:
            chance *= stay if v == last else 1 - stay
            last = v
        yield (world.k, word), chance


def observation_law(world, offer):
    if offer == "skip":
        return ((None, F(1)),)
    p1 = bit_one(world.theta, offer)
    return ((0, 1 - p1), (1, p1))


def independent_evaluate(world, plan):
    issue, violation, cost = F(0), F(0), F(0)
    positive = world.theta < F(1, 2)
    for record, mass in histories(world):
        for offer, (choose, accepts) in plan[record].items():
            if not 0 <= choose <= 1 or any(not 0 <= value <= choose for value in accepts.values()):
                raise ValueError("invalid explicit realizations")
            cost += mass * choose * PRICES[offer]
            for bit, likelihood in observation_law(world, offer):
                activated = mass * likelihood * accepts[bit]
                issue += activated
                violation += activated * final_probability(world, record[1][-1])
    return {"I": issue, "VI": violation, "wrong": 1 - issue if positive else issue,
            "G": F(1, 2) + ((issue - violation) / 2 if positive else 0), "cost": cost}


def passes(world, values, exposure_floor=F(1, 4)):
    return (
        values["wrong"] <= F(1, 3) and values["I"] >= exposure_floor
        and values["VI"] <= RISK_CAP * values["I"]
        and (world.theta > F(1, 2)
             or values["I"] >= F(2, 3) and values["G"] >= F(25, 32))
    )


def exact_lp(worlds, menu, hard_cap=F(1), verify_optimum=True, exposure_floor=F(1, 4)):
    from z3 import Optimize, Real, RealVal, Solver, Sum, sat, unsat

    if not worlds or not menu or max(w.N for w in worlds) > 9:
        raise ValueError("reference explicit expansion requires nonempty data and depths at most nine")
    for world in worlds:
        world.check_good()
    menus = tuple(a for a in menu if PRICES[a] <= hard_cap)
    if not menus:
        return {"status": "infeasible", "histories": 0}
    start = time.perf_counter()

    def num(value):
        return RealVal(str(F(value)))

    by_world = {w: tuple(histories(w)) for w in worlds}
    records = sorted({record for items in by_world.values() for record, _ in items})
    paid, activated = {}, {}
    constraints = []
    for index, record in enumerate(records):
        for act in menus:
            key = (record, act)
            paid[key] = Real(f"x{index}_{act}")
            constraints.append(paid[key] >= 0)
            bits = (None,) if act == "skip" else (0, 1)
            for bit in bits:
                y = Real(f"i{index}_{act}_{bit}")
                activated[key, bit] = y
                constraints.extend((y >= 0, y <= paid[key]))
        constraints.append(Sum(*(paid[record, act] for act in menus)) == 1)

    cap = Real("maximum_expected_cost")
    constraints.extend((cap >= 0, cap <= 1))
    for world in worlds:
        masses = []
        violations = []
        charges = []
        for record, chance in by_world[world]:
            for act in menus:
                charges.append(num(chance * PRICES[act]) * paid[record, act])
                for bit, likelihood in observation_law(world, act):
                    issue = num(chance * likelihood) * activated[(record, act), bit]
                    masses.append(issue)
                    violations.append(num(final_probability(world, record[1][-1])) * issue)
        i, v, c = Sum(*masses), Sum(*violations), Sum(*charges)
        constraints.extend((i >= num(exposure_floor), v <= num(RISK_CAP) * i, c <= cap))
        if world.theta < F(1, 2):
            constraints.extend((i >= num(F(2, 3)), (i - v) / 2 + num(F(1, 2)) >= num(F(25, 32))))
        else:
            constraints.append(i <= num(F(1, 3)))

    setup = time.perf_counter() - start
    begin = time.perf_counter()
    optimizer = Optimize()
    optimizer.add(*constraints)
    optimizer.minimize(cap)
    result = optimizer.check()
    if result == unsat:
        return {"status": "infeasible", "histories": len(records), "setup_s": setup,
                "solver_s": time.perf_counter() - begin}
    if result != sat:
        raise RuntimeError(optimizer.reason_unknown())
    witness = optimizer.model()

    def value(term):
        rational = witness.eval(term, model_completion=True)
        return F(rational.numerator_as_long(), rational.denominator_as_long())

    optimum = value(cap)
    for record in records:
        if sum(value(paid[record, a]) for a in menus) != 1:
            raise ValueError("compiled flow witness does not normalize")
    plan = {
        record: {offer: (value(paid[record, offer]),
                         {bit: value(activated[(record, offer), bit])
                          for bit in ((None,) if offer == "skip" else (0, 1))})
                 for offer in menus}
        for record in records
    }
    metrics = {world.id: independent_evaluate(world, plan) for world in worlds}
    assert all(passes(world, metrics[world.id], exposure_floor) for world in worlds)
    assert max(row["cost"] for row in metrics.values()) == optimum
    if verify_optimum:
        certificate_check = Solver()
        certificate_check.add(*constraints, cap < num(optimum))
        if certificate_check.check() != unsat:
            raise ValueError("strictly lower cost was not refuted")
    return {"status": "optimal", "cost": str(optimum), "histories": len(records),
            "variables": len(paid) + len(activated) + 1, "setup_s": setup,
            "solver_and_verify_s": time.perf_counter() - begin,
            "metrics": {key: {metric: str(value) for metric, value in row.items()} for key, row in metrics.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("verified_roster", type=Path)
    parser.add_argument("menu", choices=tuple(MENUS))
    parser.add_argument("--hard-cap", type=F, default=F(1))
    parser.add_argument('--exposure-floor', type=F, default=F(1, 4))
    args = parser.parse_args()
    worlds = tuple(Installation.from_row(w) for w in json.loads(args.verified_roster.read_bytes())["worlds"])
    print(json.dumps(exact_lp(worlds, MENUS[args.menu], args.hard_cap, exposure_floor=args.exposure_floor), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
