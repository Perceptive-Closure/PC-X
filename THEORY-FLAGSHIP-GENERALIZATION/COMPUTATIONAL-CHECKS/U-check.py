"""Exact finite corroboration for U.G1–G4, with no empirical samples."""
from collections import defaultdict
from fractions import Fraction as Q
from itertools import combinations, product
from math import comb

PRICES = {"skip": Q(0), "low": Q(3, 8), "high": Q(1)}
RETURNS = {
    "skip": lambda theta: Q(0),
    "low": lambda theta: Q(1, 4) + theta / 2,
    "high": lambda theta: theta,
}


def policy(word, route, kind):
    if kind == "optimal":
        return {"low": (Q(2, 3), Q(1), Q(0)), "high": (Q(1, 3), Q(1), Q(0))}
    if kind == "high":
        return {"high": (Q(1), Q(1), Q(0))}
    code = sum((index + 1) * flip for index, flip in enumerate(word)) + (route == "R")
    low = Q(code % 5, 6)
    high = Q((code + 1) % 3, 6)
    return {
        "low": (low, Q(4, 5), Q(1, 4)),
        "high": (high, Q(5, 6), Q(1, 5)),
        "skip": (1 - low - high, Q(code % 3, 3), Q(0)),
    }


def local_scores(theta, beta, mode, parity, offer, prob_zero, prob_one):
    bit = RETURNS[offer](theta)
    issue = (1 - bit) * prob_zero + bit * prob_one
    violation = issue * (theta / 4 + Q(mode ^ parity, 16) + beta)
    pos = theta < Q(1, 2)
    err = (1 - issue) if pos else issue
    utility = Q(1, 2) + ((issue - violation) / 2 if pos else 0)
    return issue, violation, err, utility, PRICES[offer]


def separate_paths(n, theta, beta, mode, route, kind):
    stay = Q(1, 2) + (-1)**mode * theta * (1 - theta) / 2
    totals = [Q(0)] * 5
    for word in product((0, 1), repeat=n):
        prefix = Q(1)
        parity = 0
        for flip in word:
            prefix *= (1 - stay) if flip else stay
            parity ^= flip
        for offer, (choose, prob_zero, prob_one) in policy(word, route, kind).items():
            local = local_scores(theta, beta, mode, parity, offer, prob_zero, prob_one)
            for index, score in enumerate(local):
                totals[index] += prefix * choose * score
    return tuple(totals)


def compressed_paths(n, theta, beta, mode, route, kind):
    action_sums = defaultdict(lambda: [Q(0), Q(0), Q(0)])
    for word in product((0, 1), repeat=n):
        flips = sum(word)
        for offer, (choose, prob_zero, prob_one) in policy(word, route, kind).items():
            weights = action_sums[flips, offer]
            weights[0] += choose
            weights[1] += choose * prob_zero
            weights[2] += choose * prob_one
    stay = Q(1, 2) + (-1)**mode * theta * (1 - theta) / 2
    totals = [Q(0)] * 5
    for (flips, offer), (choose, zero, one) in action_sums.items():
        if choose == 0:
            continue
        prefix = stay**(n - flips) * (1 - stay)**flips
        local = local_scores(theta, beta, mode, flips % 2, offer, zero / choose, one / choose)
        for index, score in enumerate(local):
            totals[index] += prefix * choose * score
    return tuple(totals)


def acquisition_vertex_check():
    # Boundaries in low, high coordinates. The positive/negative pair forces the last.
    boundaries = [(1, 0, Q(0)), (0, 1, Q(0)), (1, 1, Q(1)), (1, 2, Q(4, 3))]
    vertices = set()
    for (a, b, c), (d, e, f) in combinations(boundaries, 2):
        determinant = a * e - b * d
        if determinant == 0:
            continue
        low = (c * e - f * b) / determinant
        high = (a * f - d * c) / determinant
        if low >= 0 and high >= 0 and low + high <= 1 and low + 2 * high >= Q(4, 3):
            vertices.add((Q(3, 8) * low + high, low, high))
    assert min(vertices) == (Q(7, 12), Q(2, 3), Q(1, 3))
    assert min(price for price, low, high in vertices if low == 0) == Q(2, 3)
    assert all(high > 0 for price, low, high in vertices)


def envelope_check():
    # gR = w/2-x, gD = gR+1/20, cap 0. cR=x+w/5, cD=cR+1/50.
    net = [Q(0), Q(1, 2), Q(1)]
    radius = Q(1, 4)
    d_risk, d_cost = Q(1, 20), Q(1, 50)
    alpha_risk, alpha_cost = radius/2, radius/5
    low_x = max(w/2 - d_risk for w in net)
    high_x = max(w/2 + d_risk + alpha_risk for w in net)
    bounds = (
        max(low_x + w/5 - d_cost for w in net),
        Q(11, 20) + Q(1, 5) + d_cost,
        max(high_x + w/5 + d_cost + alpha_cost for w in net),
    )
    assert bounds == (Q(63, 100), Q(77, 100), Q(189, 200))
    t = (2 * d_risk + alpha_risk) / Q(9, 20)
    assert t == Q(1, 2)
    assert bounds[2] - bounds[0] <= t * Q(6, 5) + 2*d_cost + alpha_cost


def scope_controls():
    # Two distinct letters with the same factor and abstract destination.
    assert sum([Q(1), Q(1)]) * Q(1, 2) == 1
    assert Q(1) * Q(1, 2) != 1
    # A complete letter can be impossible at one tag even if every nominal letter exists.
    actual = (Q(1), Q(0))
    assert sum(actual) == 1 and actual[1] == 0
    assert sum((Q(1), Q(1))) == 2
    # A finite uniform approximation to stop at n is never forced by pointwise stopping.
    for n in (1, 12, 50):
        tau = n + 1
        assert (1 if tau > n else 0) == 1
    # Exact geometric cutoff identities on a finite integer distribution.
    masses = {1: Q(1, 2), 3: Q(1, 4), 6: Q(1, 4)}
    cutoff = 2
    difference = sum(max(tau - cutoff, 0) * mass for tau, mass in masses.items())
    tail_sum = sum(sum(mass for tau, mass in masses.items() if tau > h) for h in range(cutoff, 6))
    assert difference == tail_sum == Q(5, 4)
    # The same horizon can have no common prefixes but perfect identification if startup reveals Y.
    initial_laws = ((Q(1), Q(0)), (Q(0), Q(1)))
    assert sum(abs(x-y) for x, y in zip(*initial_laws))/2 == 1


def main():
    acquisition_vertex_check()
    envelope_check()
    scope_controls()
    points = [Q(1, 8), Q(3, 16), Q(1, 4), Q(3, 4), Q(13, 16), Q(7, 8)]
    cases = 0
    for n, theta, mode, route, kind in product(range(1, 7), points, (0, 1), ("L", "R"),
                                               ("optimal", "high", "history")):
        for beta in (Q(0), Q(1, 64), Q(1, 32)):
            explicit = separate_paths(n, theta, beta, mode, route, kind)
            assert compressed_paths(n, theta, beta, mode, route, kind) == explicit
            issue, violation, err, utility, price = explicit
            nominal = separate_paths(n, theta, Q(0), mode, route, kind)
            assert violation - nominal[1] == beta * issue
            assert price == nominal[4] and err == nominal[2]
            if kind == "optimal":
                assert Q(1, 4) <= issue <= Q(3, 4) and err <= Q(1, 3)
                assert Q(0) < violation <= Q(5, 16) * issue and price == Q(7, 12)
                assert utility >= Q(1, 2)
                if theta < Q(1, 2):
                    assert issue >= Q(2, 3) and utility >= Q(25, 32)
            if kind == "high":
                assert err <= Q(1, 4)
                assert Q(3, 8) * issue - violation >= Q(1, 128)
                if theta < Q(1, 2):
                    assert utility >= Q(209, 256)
            cases += 1
    n = 64
    assert sum(comb(n, i) for i in range(n + 1)) == 2**n
    assert sum(t + 1 for t in range(n + 1)) == 2145
    print(f"PASS: {cases} expanded/controlled count-flow metrics, price 7/12, upper/lower interval and scope controls.")
    print("PASS: 65 sufficient states at depth 64, 2145 through the prelude, 2^64 full histories.")


if __name__ == "__main__":
    main()
