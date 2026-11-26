"""Exact supplemental checks from the authorized post-release comparison."""

from fractions import Fraction as F
from itertools import product
from pathlib import Path
import runpy


def guarded_ticket_risk(cutoff, proposal, copies):
    words = range(4 * copies)
    return sum(
        F(u // copies + 1 <= cutoff or z // copies + 1 <= proposal, len(words)**2)
        for u, z in product(words, repeat=2)
    )


def prelude(n, mode):
    distribution = [F(1), F(0)]
    for _ in range(n):
        nxt = [F(0), F(0)]
        for previous, current in product((0, 1), repeat=2):
            rate = F(1 + (previous ^ mode), 3)
            nxt[current] += distribution[previous] * (rate if current else 1 - rate)
        distribution = nxt
    assert sum(distribution) == 1
    return distribution


def shared_fixture():
    local = {(label, proposal): guarded_ticket_risk(cutoff, proposal, 1)
             for label, cutoff in enumerate((1, 3)) for proposal in (0, 1)}
    for label, cutoff in enumerate((1, 3)):
        for proposal in (0, 1):
            assert local[label, proposal] == guarded_ticket_risk(cutoff, proposal, 2)
    assert list(local.values()) == [F(1, 4), F(7, 16), F(3, 4), F(13, 16)]
    price = F(2, 3)
    error_cap = F(1, 3)
    assert (1 - price) / 2 + price / 4 == error_cap
    worst_positive_risk = F(0)
    worst_negative_risk = F(0)
    least_positive_safe_utility = F(1)
    for n, mode, label in product(range(9), (0, 1), (0, 1)):
        dry = F(1 + 2 * label, 4)
        issue = price * (1 - dry) + (1 - price) / 2
        assert (issue if label else 1 - issue) == error_cap
        v_distribution = prelude(n, mode)
        direct_risk = sum(mass * local[label, mode ^ v]
                          for v, mass in enumerate(v_distribution))
        assert (direct_risk > F(1, 2)) == bool(label)
        issued_risk = sum(mass * local[label, mode ^ v ^ 1]
                          for v, mass in enumerate(v_distribution))
        violation = issue * issued_risk
        if label:
            worst_negative_risk = max(worst_negative_risk, violation)
        else:
            worst_positive_risk = max(worst_positive_risk, violation)
            least_positive_safe_utility = min(least_positive_safe_utility, issue - violation)
    assert (worst_positive_risk, worst_negative_risk, least_positive_safe_utility) == (
        F(7, 24), F(13, 48), F(3, 8)
    )


def likelihood_envelope():
    grid = tuple(F(i, 8) for i in range(9))
    for pay, dry_zero, dry_one, skip in product(grid, repeat=4):
        qp = pay * (F(3, 4) * dry_zero + F(1, 4) * dry_one) + (1 - pay) * skip
        qm = pay * (F(1, 4) * dry_zero + F(3, 4) * dry_one) + (1 - pay) * skip
        assert qm >= max(qp / 3, 3 * qp - 2)
        assert F(3, 4) * qm >= qp / 4
        assert F(7, 20) * qm >= F(7, 60) * qp

    for qp in tuple(F(i, 32) for i in range(33)):
        if qp <= F(3, 4):
            dry_zero, dry_one = 4 * qp / 3, F(0)
        else:
            dry_zero, dry_one = F(1), 4 * qp - 3
        assert F(3, 4) * dry_zero + F(1, 4) * dry_one == qp
        assert F(1, 4) * dry_zero + F(3, 4) * dry_one == max(qp / 3, 3 * qp - 2)


def additional_boundaries():
    verifier = Path(__file__).resolve().parent
    mod_a = runpy.run_path(str(verifier / "T30-A" / "check_receipts.py"))
    risk = mod_a["count_posterior_risk"]
    probes = ((1, F(1, 2)), (3, F(1)))
    assert risk(F(3, 4), probes, 4, 3) == F(61, 256)
    assert F(2, 3) * 2 + F(1, 3) * F(32, 5) == F(52, 15)
    assert F(1, 2) * F(3, 4) == F(3, 8) < F(1, 2)

    mod_p = runpy.run_path(str(verifier / "T30-P" / "check_transport.py"))
    stopped = mod_p["adaptive_law"]
    fixed = stopped((F(1, 2), F(1, 2)), 6)
    for n in (3, 5, 10, 20, 50, 100):
        near = stopped((F(1, 2) + F(1, n),) * 2, 6)
        tv = sum(abs(fixed[key] - near[key]) for key in fixed) / 2
        assert tv <= F(6, n)


if __name__ == "__main__":
    shared_fixture()
    likelihood_envelope()
    additional_boundaries()
    print("Post-release exact arithmetic: shared guarded source, ROC sharp pieces, "
          "A cap/expected/cancellation controls and P truncated continuity examples.")
