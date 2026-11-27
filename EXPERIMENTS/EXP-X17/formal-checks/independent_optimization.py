"""Replay the independent finite LP and exact actual guarded mesh certificates."""

import argparse
from collections import Counter, defaultdict
from fractions import Fraction as F
from itertools import product
import json
from math import comb
from pathlib import Path
import sys

import z3

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "independent"))
from model import Installation, RISK_CAP, stay_probability
from reference import MENUS, exact_lp, histories

PRICES = {"skip": F(0), "low": F(3, 8), "high": F(1), "direct": F(1, 2)}
GAPS = {"skip": F(0), "low": F(1, 4), "high": F(1, 2), "direct": F(1)}


def optimize(worlds):
    results = []
    scopes = (("selected-eight", worlds), ("matched-pair", worlds[:2]))
    for label, group in scopes:
        for floor, (menu_label, menu) in product((F(0), F(1, 4)), MENUS.items()):
            outcome = exact_lp(group, menu, exposure_floor=floor)
            wanted = {"full": "7/12", "high_skip": "2/3"}.get(menu_label)
            assert (outcome["status"], outcome.get("cost")) == (
                "optimal" if wanted else "infeasible", wanted)
            results.append({"scope": label, "exposure_floor": str(floor), "menu": menu_label,
                            "hard_cap": "1", "result": outcome})
    for label, group in scopes:
        for cap in (F(0), F(3, 8)):
            outcome = exact_lp(group, MENUS["full"], hard_cap=cap, exposure_floor=F(0))
            assert outcome["status"] == "infeasible"
            results.append({"scope": label, "exposure_floor": "0", "menu": "full",
                            "hard_cap": str(cap), "result": outcome})
    return {"schema": 1, "optimizer": "Z3 " + z3.get_version_string(), "lookup": results}


def counted_equivalence(worlds):
    rows = []
    for world in worlds:
        count = Counter()
        mass = defaultdict(F)
        for (_, word), word_mass in histories(world):
            stays = sum(a == b for a, b in zip((0,) + word, word))
            assert word[-1] == (world.N - stays) % 2
            count[stays] += 1
            mass[stays] += word_mass
        for stays, n in count.items():
            p = stay_probability(world)
            assert n == comb(world.N, stays)
            assert mass[stays] == n * p**stays * (1 - p)**(world.N - stays)
        assert sum(mass.values()) == 1
        rows.append({"id": world.id, "N": world.N, "per_route_count_states": len(mass),
                     "per_route_complete_histories": sum(count.values())})
    return rows


def mean_scores(theta, tag, n, high):
    low = 1 - high
    issue = high * (1 - theta) + low * (F(3, 4) - theta / 2)
    price = high + low * F(3, 8)
    persistence = (1 if tag == 0 else -1) * theta * (1 - theta)
    odd = (1 - persistence**n) / 2
    p_proposal = odd if tag == 0 else 1 - odd
    cut = theta / 4 + p_proposal / 16 + F(1, 32)
    violation = issue * cut
    return (1 - issue if theta < F(1, 2) else issue), issue, violation, price


def grid_check(n, refinement):
    intervals = (4 * n + 10) * refinement
    lo_bands = (F(1, 8), F(3, 4))
    increment = F(1, 8 * intervals)
    radius = increment / 2
    alpha = (F(n, 2) + F(5, 4)) * radius
    assert alpha == F(1, 128 * refinement)
    scores_min = {}
    for label, high, tightening in (("lower", F(1, 3), F(0)), ("upper", F(1, 3) + 8 * alpha, alpha)):
        assert 0 <= high <= 1
        margins = defaultdict(list)
        for base in lo_bands:
            strip = tuple(base + offset * increment for offset in range(intervals + 1))
            assert strip[-1] - strip[0] == F(1, 8)
            assert max((b - a) / 2 for a, b in zip(strip, strip[1:])) == radius
            for theta, tag, route in product(strip, (0, 1), ("L", "R")):
                error, issue, violation, price = mean_scores(theta, tag, n, high)
                assert price == F(7, 12) + 5 * tightening
                assert route in ("L", "R")
                margins["error"].append(F(1, 3) - error)
                margins["signed_risk"].append(RISK_CAP * issue - violation)
                if theta < F(1, 2):
                    margins["positive_exposure"].append(issue - F(2, 3))
                    margins["positive_utility"].append(F(1, 2) + (issue - violation) / 2 - F(25, 32))
        assert all(min(values) >= tightening for values in margins.values())
        scores_min[label] = {key: str(min(values)) for key, values in margins.items()}
    assert -F(1, 4) + F(5, 2) * (F(1, 3) + 2 * alpha) == F(7, 12) + 5 * alpha
    return {"N": n, "refinement": refinement, "worlds": 8 * (intervals + 1), "alpha": str(alpha),
            "mesh_radius": str(radius), "minimum_slack": scores_min, "lower": "7/12",
            "upper_epigraph": str(F(7, 12) + 6 * alpha), "explicit_upper_price": str(F(7, 12) + 5 * alpha)}


def grids(worlds):
    for offer in ("skip", "low", "high"):
        assert PRICES[offer] >= -F(1, 4) + F(5, 2) * GAPS[offer]
    for offer in ("skip", "high"):
        assert PRICES[offer] >= 2 * GAPS[offer]
    for offer in PRICES:
        assert PRICES[offer] >= GAPS[offer] / 2
    assert GAPS["low"] < F(1, 3)
    assert PRICES["direct"] / 3 == F(1, 6)
    return {"schema": 1, "scope": "base uncalibrated, positive-only coverage", "matched_sign_gap_floor": "1/3",
            "direct_changed_menu_optimum": "1/6", "reduction": counted_equivalence(worlds),
            "grid_certificates": [grid_check(n, r) for n, r in
                                  product(sorted({w.N for w in worlds}), (1, 2))]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("opening", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    worlds = tuple(Installation.from_row(row) for row in json.loads(args.opening.read_bytes())["worlds"])
    assert len(worlds) == 8
    matched = worlds[:2]
    assert (matched[0].theta, matched[1].theta) == (F(1, 4), F(3, 4))
    assert (matched[0].beta, matched[0].m, matched[0].k, matched[0].N) == (
        matched[1].beta, matched[1].m, matched[1].k, matched[1].N)
    assert tuple(histories(matched[0])) == tuple(histories(matched[1]))
    for name, exhibit in (("independent-optimization.json", optimize), ("independent-grid-check.json", grids)):
        with (args.output / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(exhibit(worlds), sort_keys=True, indent=2) + "\n")
    print("Certified 20 exact LPs and eight actual mesh certificates.")


if __name__ == "__main__":
    main()
