"""Independent exact forecasts for the accepted X17 declared source laws."""

import argparse
from dataclasses import dataclass
from fractions import Fraction as F
import json
from pathlib import Path


ARMS = ("pcx", "high_skip", "low_only", "always_high", "no_paid")
PRICES = {"low": F(3, 8), "high": F(1), "skip": F(0)}
RISK_CAP = F(3, 8)
COST_KEYS = ("I", "V", "VI", "wrong", "G", "cost", "Z")


@dataclass(frozen=True)
class Installation:
    id: str
    theta: F
    beta: F
    m: int
    k: str
    B: str
    N: int

    @classmethod
    def from_row(cls, row):
        return cls(row["id"], F(row["theta"]), F(row["beta"]), row["m"], row["k"], row["B"], row["N"])

    def check_good(self):
        if (self.B != "good" or not 0 <= self.beta <= F(1, 32)
                or not (F(1, 8) <= self.theta <= F(1, 4) or F(3, 4) <= self.theta <= F(7, 8))
                or self.m not in (0, 1) or self.k not in ("L", "R") or self.N < 1):
            raise ValueError("forecast requires a good admitted installation")


def bit_one(theta, offer):
    if offer == "low":
        return F(1, 4) + theta / 2
    if offer == "high":
        return theta
    raise ValueError("skip has no bit")


def stay_probability(world):
    return (1 + (1 if world.m == 0 else -1) * world.theta * (1 - world.theta)) / 2


def final_probability(world, last_bit, mechanism="actual"):
    surcharge = world.beta if mechanism == "actual" else F(0)
    return world.theta / 4 + F(world.m ^ last_bit, 16) + surcharge


def offer_weights(arm):
    return {
        "pcx": {"low": F(2, 3), "high": F(1, 3)},
        "high_skip": {"high": F(2, 3), "skip": F(1, 3)},
        "low_only": {"low": F(1)},
        "always_high": {"high": F(1)},
        "no_paid": {"skip": F(1)},
    }[arm]


def prelude_distribution(world):
    stay = stay_probability(world)
    mass = (F(1), F(0))
    for _ in range(world.N):
        mass = (stay * mass[0] + (1 - stay) * mass[1], (1 - stay) * mass[0] + stay * mass[1])
    return mass


def forecast(world, arm, mechanism="actual"):
    world.check_good()
    positive = world.theta < F(1, 2)
    issue, violation, price = F(0), F(0), F(0)
    for bit, mass in enumerate(prelude_distribution(world)):
        for offer, choose in offer_weights(arm).items():
            accept = F(1, 2) if offer == "skip" else 1 - bit_one(world.theta, offer)
            activated = mass * choose * accept
            issue += activated
            violation += activated * final_probability(world, bit, mechanism)
            price += mass * choose * PRICES[offer]
    return {"I": issue, "V": violation, "VI": violation, "wrong": 1 - issue if positive else issue,
            "G": F(1, 2) + ((issue - violation) / 2 if positive else 0),
            "cost": price, "Z": violation - RISK_CAP * issue,
            "conditional_risk": violation / issue if issue else None}


def forecast_roster(roster):
    predictions = {}
    for entry in roster["worlds"]:
        world = Installation.from_row(entry)
        predictions[world.id] = {}
        for arm in ARMS:
            predictions[world.id][arm] = {
                mechanism: {key: str(value) if value is not None else None for key, value in
                            forecast(world, arm, mechanism).items()}
                for mechanism in ("actual", "nominal")
            }
    return {"schema": 1, "predictions": predictions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("verified_roster", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(forecast_roster(json.loads(args.verified_roster.read_bytes())),
                                sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
