"""Independent rational checks for the guarded receipt contract."""

from fractions import Fraction as F
from functools import cache
from itertools import product
from math import comb


def receipt_row(p, reveal):
    return (reveal * (1 - p), reveal * p, 1 - reveal)


def all_pure_errors(q, probes, budget, moves):
    """Enumerate error pairs of every deterministic conditional receipt plan."""
    @cache
    def enumerate_pairs(money, time):
        pairs = {(F(0), F(1)), (F(1), F(0))}
        for cost, reveal in probes:
            if not time or cost > money:
                continue
            rows = receipt_row(1 - q, reveal), receipt_row(q, reveal)
            support = [j for j in range(3) if rows[0][j] > 0]
            continuations = enumerate_pairs(money - cost, time - 1)
            for children in product(continuations, repeat=len(support)):
                pairs.add(tuple(
                    sum(rows[label][j] * child[label] for j, child in zip(support, children))
                    for label in range(2)
                ))
        return pairs

    return enumerate_pairs(budget, moves)


def count_posterior_risk(q, probes, budget, moves):
    """An independent normalized-posterior recurrence on score differences."""
    ratio = q / (1 - q)

    @cache
    def run(money, time, s):
        neg = ratio**s / (1 + ratio**s)
        immediate = min(neg, 1 - neg)
        options = [immediate]
        for cost, reveal in probes:
            if time and cost <= money:
                prob_one = neg * q + (1 - neg) * (1 - q)
                nxt = money - cost, time - 1
                options.append(
                    (1 - reveal) * run(*nxt, s)
                    + reveal * (
                        prob_one * run(*nxt, s + 1)
                        + (1 - prob_one) * run(*nxt, s - 1)
                    )
                )
        return min(options)

    return run(budget, moves, 0)


def solve(rows):
    """Solve a finite absorbing Markov chain's linear equations exactly."""
    rows = [list(map(F, row)) for row in rows]
    dimension = len(rows)
    for col in range(dimension):
        pivot = next(i for i in range(col, dimension) if rows[i][col])
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = rows[col][col]
        rows[col] = [value / scale for value in rows[col]]
        for i in range(dimension):
            if i != col:
                weight = rows[i][col]
                rows[i] = [u - weight * v for u, v in zip(rows[i], rows[col])]
    return [row[-1] for row in rows]


def absorbed_walk(p, reveal, price, boundary, wrong_boundary):
    states = list(range(-boundary + 1, boundary))
    payoff_systems = ([], [])
    for s in states:
        coefficients = [F(s == t) for t in states]
        wrong_exit = F(0)
        for next_s, mass in zip((s - 1, s + 1, s), receipt_row(p, reveal)):
            if next_s in states:
                coefficients[states.index(next_s)] -= mass
            elif next_s == wrong_boundary:
                wrong_exit += mass
        payoff_systems[0].append(coefficients + [price])
        payoff_systems[1].append(coefficients + [wrong_exit])
    return tuple(solve(system)[states.index(0)] for system in payoff_systems)


def independent_controls():
    # A proposal chosen before a uniform Z hits one selected singleton
    # with mass 1/2. Observing Z first lets the proposal always contain it.
    z_values = (0, 1)
    assert sum(F(z == 0, 2) for z in z_values) == F(1, 2)
    policy_that_reads_z = {0: {0}, 1: {1}}
    assert sum(F(z in policy_that_reads_z[z], 2) for z in z_values) == 1

    agree = {(0, 0), (1, 1)}
    disagree = {(0, 1), (1, 0)}
    for coordinate in (0, 1):
        assert {p[coordinate] for p in agree} == {p[coordinate] for p in disagree}
    assert not agree & disagree

    p = F(1, 4)
    fractions = (F(0), F(1, 2))
    local = [p + (1 - p) * fraction for fraction in fractions]
    assert local == [F(1, 4), F(5, 8)]
    assert sum(local) / 2 == F(7, 16)  # Forced equal mixture of cuts.


def main():
    q = F(3, 4)
    proposals = (F(0), F(1, 4))
    ranges = tuple(tuple(p + (1 - p) * d for d in proposals) for p in (1 - q, q))
    assert ranges == ((F(1, 4), F(7, 16)), (F(3, 4), F(13, 16)))

    probes = ((1, F(1, 2)), (3, F(1)))
    for paid in range(7):
        for time in range(3):
            pairs = all_pure_errors(q, probes, paid, time)
            avg = min((a + b) / 2 for a, b in pairs)
            assert avg == count_posterior_risk(q, probes, paid, time)
    assert count_posterior_risk(q, probes, 6, 2) == F(1, 4)

    equal_cost = ((1, F(1, 4)), (1, F(2, 3)))
    max_reveal = max(rate for _, rate in equal_cost)
    for n in range(7):
        bin_risk = F(0)
        for reveals in range(n + 1):
            reveal_mass = comb(n, reveals) * max_reveal**reveals * (1 - max_reveal)**(n - reveals)
            for correct in range(reveals + 1):
                bit_mass = comb(reveals, correct) * q**correct * (1 - q)**(reveals - correct)
                multiplier = F(1) if 2 * correct < reveals else F(1, 2) if 2 * correct == reveals else F(0)
                bin_risk += reveal_mass * bit_mass * multiplier
        assert bin_risk == count_posterior_risk(q, equal_cost, n, n)

    for accuracy in (F(3, 4), F(2, 3)):
        for boundary in range(1, 8):
            ratio = accuracy / (1 - accuracy)
            mu = 2 * accuracy - 1
            error = 1 / (1 + ratio**boundary)
            paid = 2 * boundary * (1 - 2 * error) / mu
            for p, wrong in ((accuracy, -boundary), (1 - accuracy, boundary)):
                assert absorbed_walk(p, F(1, 2), F(1), boundary, wrong) == (paid, error)

    one = absorbed_walk(q, F(1, 2), F(1), 1, -1)
    two = absorbed_walk(q, F(1, 2), F(1), 2, -2)
    assert two == (F(32, 5), F(1, 10))
    t = (F(1, 6) - two[1]) / (one[1] - two[1])
    assert t == F(4, 9)
    assert t * one[0] + (1 - t) * two[0] == F(40, 9)
    independent_controls()
    print("A.1-A.4 exact: guard endpoints; 21 hard-cap cases; 7 binomial cases; "
          "28 absorbing walks; cost 32/5 at 1/10; mixed cost 40/9 at 1/6; boundary controls.")


if __name__ == "__main__":
    main()
