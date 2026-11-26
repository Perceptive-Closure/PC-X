"""Exact theorem-adjacent checks for the stated finite unified scope."""

from collections import Counter
from fractions import Fraction as F
from itertools import product
import json
from pathlib import Path
from tempfile import TemporaryDirectory


def check_acquisition_frontier():
    def rates(pay, decisions):
        skip, seen_zero, seen_one = decisions
        return tuple(
            (1 - pay) * skip + pay * ((1 - p) * seen_zero + p * seen_one)
            for p in (F(1, 4), F(3, 4))
        )

    for p in (F(0), F(1, 4), F(1, 2), F(2, 3), F(3, 4), F(1)):
        attainable = [rates(p, decisions) for decisions in product((0, 1), repeat=3)]
        optimum = min((1 - q_plus + q_minus) / 2 for q_plus, q_minus in attainable)
        assert optimum == (1 - p) / 2 + p / 4
        for q_plus, q_minus in attainable:
            assert q_plus / 3 <= q_minus
            assert 3 * q_plus - 2 <= q_minus

    for q_plus in (F(1, 5), F(1, 2), F(3, 4), F(4, 5), F(1)):
        if q_plus <= F(3, 4):
            decisions = (F(0), 4 * q_plus / 3, F(0))
        else:
            decisions = (F(0), F(1), 4 * q_plus - 3)
        q_actual, q_minus = rates(F(1), decisions)
        assert q_actual == q_plus
        assert q_minus == max(q_plus / 3, 3 * q_plus - 2)

    for error in (F(1, 4), F(1, 3), F(2, 5), F(9, 20)):
        paid = 2 - 4 * error
        q_plus, q_minus = rates(paid, (F(1, 2), F(1), F(0)))
        assert (q_plus, q_minus) == (1 - error, error)
        assert max(q_plus / 4, 3 * q_minus / 4) <= F(2, 5)
        assert (F(3, 4) - F(2, 5)) * q_minus >= F(7, 60) * q_plus
    print("PASS U.4: exact one-call acquisition, selective ROC and slack lower bound")


def prelude_history_law(history, m):
    previous = 0
    likelihood = F(1)
    for letter in history:
        mean = F(1 + (m ^ previous), 3)
        likelihood *= mean if letter else 1 - mean
        previous = letter
    return likelihood, previous


def count_posteriors():
    worlds = tuple(product(range(2), repeat=3))
    prior = {w: F(j + 1, 36) for j, w in enumerate(worlds)}
    assert sum(prior.values()) == 1
    for length in range(10):
        graph_layer = set()
        for history in product(range(2), repeat=length):
            w0, hidden = prelude_history_law(history, 0)
            w1, _ = prelude_history_law(history, 1)
            weights = tuple(prior[w] * (w0, w1)[w[2]] for w in worlds)
            graph_layer.add((tuple(prob / sum(weights) for prob in weights), hidden))
        assert len(graph_layer) == length + 1

    # Public fair token and previous spend are omitted by one candidate state encoding.
    lawful = {"L": {"finish/L", "stop"}, "R": {"finish/R", "stop"}}
    assert lawful["L"] & lawful["R"] == {"stop"}
    factual = [("token/L", 2), ("token/R", 0)]
    assert sum(F(int(spent + (2 if token == "token/R" else 0) > 2), 2)
               for token, spent in factual) == 0
    q_policy_buy = F(1, 2)
    assert q_policy_buy * F(1, 2) == F(1, 4)  # Unauthorized over-cap mass if previous spend is lost.

    # Selection bits and actual violation bits have the same marginals but different intersection.
    aligned = ((1, 1), (0, 0))
    disjoint = ((1, 0), (0, 1))
    assert all(sum(a[j] for a in aligned) == sum(a[j] for a in disjoint) for j in range(2))
    assert sum(i * v for i, v in aligned) == 1
    assert sum(i * v for i, v in disjoint) == 0
    print("PASS U.1/U.2: exact posteriors, authorization, earlier spend and actual joint-event flags")


def finish_routing(b, route, m, v, via_verdict, u, z, literal, output=None):
    if literal != f"finish/{route}":
        raise ValueError("unavailable route")
    proposal = m ^ v ^ int(via_verdict)
    live_failure = (u <= (1, 3)[b]) or z <= proposal
    expected_count = 6
    body = {"route": route, "units": expected_count - int(live_failure), "note": proposal}
    if output is not None:
        output.write_text(json.dumps(body), encoding="utf-8")
        body = json.loads(output.read_text(encoding="utf-8"))
    true_violation = body["units"] != expected_count
    true_completion = body["route"] == route and not true_violation
    return proposal, true_violation, true_completion


def check_compatibility():
    risks = {}
    for b, route, m, v, via_verdict in product(range(2), "LR", range(2), range(2), (False, True)):
        counts = Counter(
            finish_routing(b, route, m, v, via_verdict, u, z, f"finish/{route}")
            for u, z in product(range(1, 5), repeat=2)
        )
        proposal = m ^ v ^ int(via_verdict)
        fail = sum(n for (a, violated, _), n in counts.items() if a == proposal and violated)
        q = F(fail, 16)
        assert q == F((1, 3)[b], 4) + (1 - F((1, 3)[b], 4)) * proposal / 4
        risks[b, route, m, v, via_verdict] = q

    assert risks[0, "L", 0, 0, False] == F(1, 4)
    assert risks[0, "L", 0, 0, True] == F(7, 16)
    assert risks[1, "R", 0, 0, True] == F(13, 16)
    with TemporaryDirectory() as folder:
        product_file = Path(folder) / "routed.json"
        assert finish_routing(0, "L", 0, 0, False, 2, 1, "finish/L", product_file) == (0, False, True)
        assert finish_routing(0, "L", 0, 0, True, 2, 1, "finish/L", product_file) == (1, True, False)

    q_plus, q_minus = F(2, 3), F(1, 3)
    assert q_plus * (1 - F(7, 16)) == F(3, 8)
    assert max(q_plus * F(7, 16), q_minus * F(13, 16)) == F(7, 24)
    print("PASS U compatibility: actual post-verdict proposal, file effect and guarded safe utility")


def check_calibration():
    # Every calibrated live row is correct marginally. Reusing the data bit invalidates it conditionally.
    for action in (0, 1):
        assert sum(F(int(action == live), 2) for live in (0, 1)) == F(1, 2)
    assert sum(F(int(data == live), 2) for data, live in ((0, 0), (1, 1))) == 1
    # A rare coverage miss can absorb all selected positive issuance.
    eta, issuance, epsilon = F(1, 10), F(1, 10), F(1, 5)
    assert (epsilon * issuance + (1 - epsilon) * min(eta, issuance)) / issuance == 1
    print("PASS U.3: conditional kernel, calibration error and rare issuance boundary")


if __name__ == "__main__":
    check_acquisition_frontier()
    count_posteriors()
    check_calibration()
    check_compatibility()
