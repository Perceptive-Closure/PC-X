"""Independent finite record and occupation checks for T30.U."""

from collections import defaultdict
from fractions import Fraction as F
from itertools import product


PRIOR = (F(2, 3), F(1, 3))


def probe_rate(world, action):
    return F(3 if world == action else 1, 4)


def information_state(record):
    if len(record) == 1:
        return (0, PRIOR[1])
    _, operation, datum = record
    weights = tuple(PRIOR[w] * (probe_rate(w, operation) if datum else 1 - probe_rate(w, operation))
                    for w in range(2))
    return (1, weights[1] / sum(weights))


def history_policy(record):
    if len(record) == 1:
        return F(1 + 2 * record[0], 4)
    return F(1 + sum(record), 5)


def measure(policy):
    """Compute worldwise metrics by explicit history expansion."""
    occupations = defaultdict(lambda: [F(0), F(0)])
    exact = []
    for world, prior_weight in enumerate(PRIOR):
        current = [((c,), F(1, 2)) for c in (0, 1)]
        scores = [F(0) for _ in range(6)]
        for step in (0, 1):
            future = []
            for record, mass in current:
                chance = policy(record)
                state = information_state(record)
                for action, fraction in enumerate((1 - chance, chance)):
                    branch = mass * fraction
                    occupations[state][action] += prior_weight * branch
                    if step == 0:
                        scores[0] += branch * action
                        rate = probe_rate(world, action)
                        future.extend((record + (action, datum), branch * outcome)
                                      for datum, outcome in enumerate((1 - rate, rate)))
                    else:
                        scores[1] += branch * (action != world)
                        scores[2] += branch * action
                        scores[3] += branch * action * F(1 + 2 * world, 4)
                        scores[4] += branch * action * (world == 0)
                        scores[5] += branch * action * F(1 + world, 2)
            current = future
        exact.append(tuple(scores))
    return tuple(exact), occupations


def compressed_check():
    exact, original_flow = measure(history_policy)

    def compressed(record):
        flow = original_flow[information_state(record)]
        return flow[1] / sum(flow)

    compressed_exact, reproduced_flow = measure(compressed)
    assert compressed_exact == exact
    assert reproduced_flow == original_flow
    assert history_policy((0,)) != history_policy((1,))
    assert compressed((0,)) == compressed((1,))
    return exact


def bit_likelihood(bits, m):
    likelihood = F(1)
    v = 0
    for y in bits:
        rate = F(1 + (m ^ v), 3)
        likelihood *= rate if y else 1 - rate
        v = y
    return likelihood


def likelihood_count():
    for horizon in range(13):
        groups = set()
        totals = [F(0), F(0)]
        for bits in product((0, 1), repeat=horizon):
            p, q = (bit_likelihood(bits, m) for m in (0, 1))
            assert p > 0 and q > 0
            totals[0] += p
            totals[1] += q
            previous = 0
            flips = 0
            for bit in bits:
                flips += bit != previous
                previous = bit
            assert q / p == F(2)**(2 * flips - horizon)
            groups.add((q / p, previous))
        assert totals == [F(1), F(1)]
        assert len(groups) == horizon + 1


def routing_optima():
    for cap in (F(1, 4), F(1, 3), F(2, 5), F(49, 100)):
        paid = 2 - 4 * cap
        assert 0 < paid <= 1
        for actual_minus in (False, True):
            dry_rate = F(3 if actual_minus else 1, 4)
            activation = paid * (1 - dry_rate) + (1 - paid) / 2
            error = activation if actual_minus else 1 - activation
            assert error == cap
            risk = dry_rate * activation
            assert risk <= F(2, 5)
            assert activation >= 1 - cap or actual_minus
            assert activation > 0
            if actual_minus:
                assert risk / activation == F(3, 4)
        assert (1 - paid) / 2 + paid / 4 == cap


def selective_and_authority():
    q, miss, eps = F(1, 4), F(1, 10), F(2, 5)
    bad_mass = min(q, miss)
    risk = (q - bad_mass) * eps + bad_mass
    assert risk / q == eps + (1 - eps) * miss / q

    legal = ({"route.left"}, {"route.right"})
    assert all(len(actions) == 1 for actions in legal) and not legal[0] & legal[1]

    for fixed_action in (0, 1):
        assert sum(F(z == fixed_action, 2) for z in (0, 1)) == F(1, 2)
    assert sum(F(z == z, 2) for z in (0, 1)) == 1  # Same draw reused after selection.


if __name__ == "__main__":
    compressed_check()
    likelihood_count()
    routing_optima()
    selective_and_authority()
    print("U.1-U.4 exact: six moments in each of two worlds preserved; all bit histories "
          "through horizon 12; four routing frontiers; selective, scope and calibration controls.")
