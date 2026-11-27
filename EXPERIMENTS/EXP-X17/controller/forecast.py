"""Exact pre-opening forecasts for the five detached X17 controllers."""

import argparse
import json
from fractions import Fraction

F = Fraction
THRESHOLD = F(3, 8)
POSITIVE_BAND = (F(1, 8), F(1, 4))
NEGATIVE_BAND = (F(3, 4), F(7, 8))
ARM_MIX = {
    "pcx": (F(2, 3), F(1, 3), F(0)),
    "high_skip": (F(0), F(2, 3), F(1, 3)),
    "low_only": (F(1), F(0), F(0)),
    "always_high": (F(0), F(1), F(0)),
    "no_paid": (F(0), F(0), F(1)),
}


def rational(value: int | str | Fraction) -> Fraction:
    if type(value) is int or isinstance(value, (str, Fraction)):
        return Fraction(value)
    raise TypeError("use an exact rational input or its string encoding")


def positive_label(theta: Fraction) -> bool:
    if POSITIVE_BAND[0] <= theta <= POSITIVE_BAND[1]:
        return True
    if NEGATIVE_BAND[0] <= theta <= NEGATIVE_BAND[1]:
        return False
    raise ValueError("theta is outside the registered source strata")


def stay_probability(theta: Fraction, m: int) -> Fraction:
    return F(1, 2) + (-1 if m else 1) * theta * (1 - theta) / 2


def proposal_probability(theta: Fraction, m: int, N: int) -> Fraction:
    """Probability m XOR v is one, with v the final public flip parity."""
    contrast = 2 * stay_probability(theta, m) - 1
    return (1 - (-1 if m else 1) * contrast**N) / 2


def forecast(
    theta: int | str | Fraction,
    beta: int | str | Fraction,
    m: int,
    N: int,
    arm: str = "pcx",
) -> dict[str, Fraction]:
    """Return exact per-attempt predictions. The law here counts safe intake."""
    theta, beta = rational(theta), rational(beta)
    positive = positive_label(theta)
    if type(m) is not int or m not in (0, 1):
        raise ValueError("m must be the fixed responder tag 0 or 1")
    if type(N) is not int or N < 0:
        raise ValueError("N must be a nonnegative integer")
    if beta < 0 or theta / 4 + F(1, 16) + beta > 1:
        raise ValueError("surcharge gives an invalid finalizer probability")
    if arm not in ARM_MIX:
        raise ValueError("unknown registered policy")

    low, high, skip = ARM_MIX[arm]
    issue = low * (F(3, 4) - theta / 2) + high * (1 - theta) + skip / 2
    issued_risk = theta / 4 + proposal_probability(theta, m, N) / 16 + beta
    violation = issue * issued_risk
    useful = F(1, 2) + (issue * (1 - issued_risk) / 2 if positive else 0)
    return {
        "I": issue,
        "V": violation,
        "VI": violation,
        "wrong": 1 - issue if positive else issue,
        "G": useful,
        "cost": F(3, 8) * low + high,
        "Z": violation - THRESHOLD * issue,
    }


def encoded(metrics: dict[str, Fraction]) -> dict[str, str]:
    """JSON-compatible canonical exact fractions."""
    return {name: str(value) for name, value in metrics.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("theta", help="exact fraction")
    parser.add_argument("beta", help="exact fraction, or 0 for the nominal finalizer")
    parser.add_argument("m", type=int, choices=(0, 1))
    parser.add_argument("N", type=int)
    parser.add_argument("arm", choices=tuple(ARM_MIX), nargs="?", default="pcx")
    args = parser.parse_args()
    print(json.dumps(encoded(forecast(args.theta, args.beta, args.m, args.N, args.arm)),
                     sort_keys=True))


if __name__ == "__main__":
    main()
