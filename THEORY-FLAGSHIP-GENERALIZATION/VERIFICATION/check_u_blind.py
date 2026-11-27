"""Exact theorem-adjacent tests written only from the advanced U statement seal."""

from fractions import Fraction as F
from itertools import product


def check_flow():
    for theta in (F(1, 8), F(3, 16), F(1, 4)):
        # Distinct letters A and B use the same likelihood factor and state transition.
        native = {"A": theta, "B": theta, "C": 1 - 2 * theta}
        flow_to_merge = 1 + 1
        assert flow_to_merge * theta + native["C"] == 1
        assert theta + native["C"] != 1
        # Full-history choice accepts after A apart from B. Lift via aggregated ratios.
        full_expected_reward = native["A"]
        aggregate_expected_reward = flow_to_merge * theta * F(1, flow_to_merge)
        assert full_expected_reward == aggregate_expected_reward
    scalar_likelihood = (1, 1)
    complete_letter_likelihood = ((1, 0), (0, 1))
    assert scalar_likelihood != complete_letter_likelihood[0]


def check_margin():
    # g_R=1-x+w/10, g_D=g_R+1/20, c=x, w in [0,1].
    b, d, radius, lipschitz = F(1, 2), F(1, 20), F(1, 4), F(1, 10)
    alpha = radius * lipschitz
    model_extreme = 1 + lipschitz
    lower = model_extreme - (b + d)
    actual = model_extreme + d - b
    upper = model_extreme - (b - d - alpha)
    gamma = b - (lipschitz + d)
    t = (2 * d + alpha) / gamma
    mixed = (1 - t) * lower + t
    assert lower <= actual <= upper <= mixed
    assert upper - lower <= t


def check_family():
    prices = [
        3 * l / 8 + h
        for numerator_l, numerator_h in product(range(13), repeat=2)
        if (l := F(numerator_l, 12)) + (h := F(numerator_h, 12)) <= 1 and l + 2 * h >= F(4, 3)
    ]
    assert min(prices) == F(7, 12)
    for theta in (F(1, 8), F(1, 4), F(3, 4), F(7, 8)):
        q = F(2, 3) * (1 - (F(1, 4) + theta / 2)) + F(1, 3) * (1 - theta)
        assert q == F(5, 6) - 2 * theta / 3 and q >= F(1, 4)
        for proposal in (0, 1):
            nominal = theta / 4 + F(proposal, 16)
            actual = nominal + F(1, 32)
            # For endpoint theta these thresholds have a common 32-ticket realization.
            ref_count = sum(F(u, 32) < nominal for u in range(32))
            dep_count = sum(F(u, 32) < actual for u in range(32))
            assert (F(ref_count, 32), F(dep_count, 32)) == (nominal, actual)
            assert q * (actual - nominal) == q / 32
            assert actual <= F(5, 16)
            if theta <= F(1, 4):
                assert 1 - q <= F(1, 3) and q >= F(2, 3)
                assert actual <= F(5, 32)
                assert F(1, 2) + q * (1 - actual) / 2 >= F(25, 32)
            else:
                assert q <= F(1, 3)

    for depth in range(8):
        records = tuple(product((0, 1), repeat=depth))
        count_states = {(sum(history), (depth - sum(history)) % 2) for history in records}
        assert len(records) == 2**depth and len(count_states) == depth + 1


def check_tails():
    stops = {0: F(1, 4), 1: F(1, 4), 3: F(1, 8), 6: F(3, 8)}
    cutoff = 2
    expected_extra = sum(p * max(0, steps - cutoff) for steps, p in stops.items())
    tail_sum = sum(p for n in range(cutoff, max(stops)) for steps, p in stops.items() if steps > n)
    assert expected_extra == tail_sum == F(13, 8)


if __name__ == "__main__":
    check_flow()
    check_margin()
    check_family()
    check_tails()
    print("PASS U.G1-G4: distinct edge multiplicity, exact LP interval, guarded fixture and integer tails")
