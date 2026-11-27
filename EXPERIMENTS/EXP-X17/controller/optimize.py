"""Exact X17 grid optimization with a checked local-column price certificate."""

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction

from .factor_flow import (Group, PLANS, ROUTES, World, evaluate, local_vertex,
                          paid_mix, world_weights)
from .forecast import NEGATIVE_BAND, POSITIVE_BAND, positive_label
from .policy import PrivateRng

F = Fraction
DELTA = F(1, 3)
COVERAGE = F(2, 3)
UTILITY = F(25, 32)
BETA_END = F(1, 32)
MARGIN = F(1, 128)


@dataclass(frozen=True, slots=True)
class Net:
    subdivisions: int
    radius: F
    modulus: F
    alpha: F
    points: tuple[F, ...]


def build_net(N: int, refinement: int = 1) -> Net:
    if type(N) is not int or N < 1 or type(refinement) is not int or refinement < 1:
        raise ValueError("certified mesh uses positive integer depth and refinement")
    modulus = F(N, 2) + F(5, 4)
    subdivisions = (4 * N + 10) * refinement
    radius = F(1, 16 * subdivisions)
    points = tuple(
        lo + (hi - lo) * F(i, subdivisions)
        for lo, hi in (POSITIVE_BAND, NEGATIVE_BAND)
        for i in range(subdivisions + 1)
    )
    stride = subdivisions + 1
    for band, (lo, hi) in enumerate((POSITIVE_BAND, NEGATIVE_BAND)):
        values = points[band * stride:(band + 1) * stride]
        if values[0] != lo or values[-1] != hi:
            raise AssertionError("net endpoints changed")
        if any((b - a) / 2 > radius for a, b in zip(values, values[1:])):
            raise AssertionError("net gap exceeds twice its radius")
    alpha = modulus * radius
    if alpha > MARGIN:
        raise AssertionError("mesh exceeds the independently established slack")
    return Net(subdivisions, radius, modulus, alpha, points)


def price_certificate(N: int) -> tuple[F, ...]:
    """Return the exact nonnegative dual slack of every local plan."""
    positive = World(F(1, 4), BETA_END, 0, "L")
    negative = World(F(3, 4), BETA_END, 0, "L")
    assert world_weights(N, positive) == world_weights(N, negative)
    slacks = []
    for plan in PLANS:
        plus = local_vertex(positive, 0, plan)
        minus = local_vertex(negative, 0, plan)
        difference = plus[0] - minus[0]
        slack = plus[5] - F(5, 2) * difference + F(1, 4)
        assert slack >= 0
        slacks.append(slack)
    return tuple(slacks)


def tightened_high_probability(alpha: F) -> F:
    if not 0 <= alpha <= MARGIN:
        raise ValueError("outside certified tightened margin")
    return F(1, 3) + 8 * alpha


def choose_tightened_probe(
    alpha: F, route_receipt: dict[str, object], rng: PrivateRng
) -> str:
    """Implement the U.G2 upper witness, which is not an extra native arm."""
    route = route_receipt.get("route")
    if route not in ROUTES:
        raise ValueError("upper witness requires a genuine route")
    high = tightened_high_probability(alpha)
    quality = "high" if rng.randrange(high.denominator) < high.numerator else "low"
    return f"{quality}:{route}"


def grid_scores(
    N: int, groups: Sequence[Group], net: Net, alpha: F
) -> tuple[dict[str, F], dict[str, World]]:
    """Exact extremal verification of the chosen grid primal against every world.

    Pass alpha=0 for the relaxed lower program, or net.alpha for the tightened one.
    """
    probabilities = paid_mix(tightened_high_probability(alpha))
    choices = (probabilities,) * len(groups)
    maxima = {}
    worlds = {}
    for theta in net.points:
        positive = positive_label(theta)
        for tag in (0, 1):
            for route in ROUTES:
                world = World(theta, BETA_END, tag, route)
                values = evaluate(N, groups, choices, world)
                tests = {"Z": values["Z"], "wrong": values["wrong"],
                         "cost": values["cost"], "negative_utility_all": -values["G"],
                         "negative_coverage_all": -values["I"]}
                if positive:
                    tests["negative_coverage_positive"] = -values["I"]
                    tests["negative_utility_positive"] = -values["G"]
                for metric, value in tests.items():
                    if metric not in maxima or value > maxima[metric]:
                        maxima[metric], worlds[metric] = value, world
    assert maxima["negative_utility_all"] <= -F(1, 2)
    assert maxima["wrong"] <= DELTA - alpha
    assert maxima["negative_coverage_positive"] <= -COVERAGE - alpha
    assert maxima["negative_utility_positive"] <= -UTILITY - alpha
    assert maxima["Z"] <= -alpha
    return maxima, worlds


def optimize(
    N: int, groups: Sequence[Group], refinement: int = 1
) -> dict[str, object]:
    """Solve both finite grid LPs exactly by primal and local-column certificates."""
    net = build_net(N, refinement)
    slacks = price_certificate(N)
    lower, lower_witnesses = grid_scores(N, groups, net, F(0))
    tightened, upper_witnesses = grid_scores(N, groups, net, net.alpha)
    lower_dual = F(5, 2) * (1 - 2 * DELTA) - F(1, 4)
    upper_dual = F(5, 2) * (1 - 2 * (DELTA - net.alpha)) - F(1, 4)
    assert lower["cost"] == lower_dual == F(7, 12)
    assert tightened["cost"] == upper_dual == F(7, 12) + 5 * net.alpha
    return {
        "net": net,
        "lower": lower_dual,
        "upper": upper_dual + net.alpha,
        "tightened_actual_policy_cost": upper_dual,
        "tightened_high": tightened_high_probability(net.alpha),
        "lower_extrema": lower,
        "lower_worlds": lower_witnesses,
        "tightened_extrema": tightened,
        "tightened_worlds": upper_witnesses,
        "column_slacks": slacks,
    }
