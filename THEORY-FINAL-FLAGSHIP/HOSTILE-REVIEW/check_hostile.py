"""Exact, independent hostile checks for the released T30.P and T30.A claims."""

from collections import Counter
from fractions import Fraction as F
from functools import cache
from itertools import product
import json
from pathlib import Path
from tempfile import TemporaryDirectory


def write_artifact(root, name, payload):
    text = json.dumps(payload, sort_keys=True)
    if root is not None:
        (root / name).write_text(text, encoding="utf-8")
    return text


def two_jobs(h, positive, tickets, copies, choose, root=None, suppress=False):
    """Materialize a normalized order and actual delivery, with separately scored writes."""
    machine_ticket, first_ticket, second_ticket = (n // copies for n in tickets)
    machine = "A" if machine_ticket == 0 else "B"
    incoming = {"order": 42, "units": 6, "destination": "warehouse"}
    normalized = {**incoming, "assigned_machine": machine}
    outputs = {"normalized.json": write_artifact(root, "normalized.json", normalized)}
    if first_ticket == 0:
        outputs["first-misdirection.json"] = write_artifact(
            root, "first-misdirection.json", {"order": incoming["order"], "units": incoming["units"]}
        )

    record = ("order/normalize", machine) if not suppress else ("order/normalize", "WORK")
    action = choose(record)
    legal = {f"delivery/{machine}/L", f"delivery/{machine}/R"}
    mark = action is not None and action not in legal
    if action in legal:
        outputs["delivery.json"] = write_artifact(root, "delivery.json", incoming)
        low = (action.endswith("/L") and h == 0) or (action.endswith("/R") and h == 1)
        bad_count = (1 if low else 5) if positive else 7
        if second_ticket < bad_count:
            outputs["second-misdirection.json"] = write_artifact(
                root, "second-misdirection.json", {"order": incoming["order"], "units": incoming["units"]}
            )

    if root is not None:
        actual_outputs = {path.name: path.read_text(encoding="utf-8") for path in root.iterdir()}
        assert actual_outputs == outputs
    useful = (
        json.loads(outputs.get("normalized.json", "null")) == normalized
        and json.loads(outputs.get("delivery.json", "null")) == incoming
    )
    violation = any(name.endswith("-misdirection.json") for name in outputs)
    return (record, action, mark, violation, useful)


def check_physical_jobs():
    def fixed(left, right):
        return lambda x: f"delivery/{x[1]}/{left if x[1] == 'A' else right}"

    def outcomes(h, positive, copies, decide):
        counts = Counter(
            two_jobs(h, positive, ts, copies, decide)
            for ts in product(range(3 * copies), range(20 * copies), range(19 * copies))
        )
        total = 3 * 20 * 19 * copies**3
        return {key: F(value, total) for key, value in counts.items()}

    def risk(data):
        assert sum(data.values()) == 1
        assert all(not marked and useful for (_, _, marked, _, useful) in data)
        return sum(weight for (_, _, _, violation, _), weight in data.items() if violation)

    robust = []
    for left, right in product("LR", repeat=2):
        policy = fixed(left, right)
        risks = []
        for h in range(2):
            native = outcomes(h, True, 1, policy)
            reencoded = outcomes(h, True, 2, policy)
            assert native == reencoded
            risks.append(risk(native))
        robust.append(max(risks))
    assert min(robust) == F(7, 30)

    for h in range(2):
        for positive, expected in [(True, F(1, 5)), (False, F(2, 5))]:
            fair_risk = sum(risk(outcomes(h, positive, 1, fixed(route, route))) for route in "LR") / 2
            assert fair_risk == expected
    assert not (
        {"delivery/A/L", "delivery/A/R"} & {"delivery/B/L", "delivery/B/R"}
    )
    for ticket, expected in [((0, 0, 18), True), ((2, 19, 18), False), ((2, 19, 0), True)]:
        with TemporaryDirectory() as folder:
            result = two_jobs(0, True, ticket, 1, fixed("L", "L"), Path(folder))
            assert result[3:] == (expected, True)
    with TemporaryDirectory() as folder:
        result = two_jobs(0, True, (2, 0, 18), 1, lambda _: None, Path(folder), suppress=True)
        assert result == (("order/normalize", "WORK"), None, False, True, False)
    assert two_jobs(0, True, (2, 19, 18), 1, lambda _: "delivery/A/L", suppress=True)[2]
    print("PASS P1/P4: independent order artifacts, receipt authority, retained earlier events, exact ticket laws")


def check_linked_regions():
    ranks = (3, 1, 1)
    worlds = tuple(product(range(2), repeat=3))

    def label(report):
        return report[1 + report[0]]

    def subsets():
        for flags in product((False, True), repeat=3):
            yield tuple(i for i, selected in enumerate(flags) if selected)

    def supports(actual, queried):
        return [r for r in worlds if all(r[j] == actual[j] for j in queried)]

    def enough(actual, queried):
        return {label(r) for r in supports(actual, queried)} == {label(actual)}

    for world in worlds:
        price = min(sum(ranks[j] for j in s) for s in subsets() if enough(world, s))
        assert price == (2 if world[1] == world[2] else 4)
    fixed = min(sum(ranks[j] for j in s) for s in subsets() if all(enough(w, s) for w in worlds))
    assert fixed == 5

    @cache
    def policy(partials):
        compatible = tuple(r for r in worlds if all(r[j] == y for j, y in partials))
        if len({label(r) for r in compatible}) <= 1:
            return 0
        return min(
            ranks[j] + max(policy(tuple(sorted((*partials, (j, y))))) for y in {r[j] for r in compatible})
            for j in range(3) if j not in dict(partials)
        )

    assert policy(()) == 4
    assert ranks[1] + max(policy(((1, y),)) for y in range(2)) == 5
    admissible = {(0, 0), (1, 1)}
    assert set(product(*({w[i] for w in admissible} for i in range(2)))) != admissible

    cap = F(17, 50)
    base, extra = F(1, 10), F(4, 5)
    risk_rhs = (cap - base) / extra
    assert risk_rhs == F(3, 10)
    for excluded in range(3):
        action = tuple(int(i == excluded) for i in range(3))
        assert all(base + extra * action[i] <= cap for i in range(3) if i != excluded)
    assert 3 * risk_rhs - 1 == -F(1, 10)  # Farkas RHS after multiplying the three bounds by 5/4.
    print("PASS P1/P2/P4: whole tuple linkage, 2/4/5 certificate costs, rational joint blocker")


def check_confidence_failures():
    paths = tuple(product((0, 1), repeat=4))
    early = {a for a in paths if sum(a[:2]) == 2}
    late = {a for a in paths if sum(a) >= 3}
    assert (len(early), len(late), len(early | late)) == (4, 5, 6)
    independent_looks = {a for a in paths if sum(a[:2]) == 2 or sum(a[2:]) == 2}
    assert F(len(independent_looks), len(paths)) == F(7, 16)
    epsilon, delta, issuance = F(1, 5), F(1, 10), F(2, 5)
    joint = epsilon * (issuance - delta) + delta
    assert joint == F(4, 25) and joint / issuance == F(2, 5) > epsilon
    assert F(3, 4) / 2 == F(3, 8) <= F(1, 2) < F(3, 4)
    assert F(1, 2) * (1 - F(1, 4)) == F(3, 8) < 1 - F(1, 4)
    print("PASS P3/A1: optional looks, multiple testing, selective risk and missing finalizer mass")


PROBES = ((1, F(1, 2)), (3, F(1)))
TYPE_MEANS = (F(1, 4), F(3, 4))


def receipt_law(reveal, mean):
    return (1 - reveal, reveal * (1 - mean), reveal * mean)


def pareto(points):
    kept = []
    for point in sorted(points):
        if not kept or point[1] < kept[-1][1]:
            kept.append(point)
    return tuple(kept)


@cache
def pure_policy_frontier(moves, budget):
    """Construct the nondominated pairs of actual type-wise errors over pure lawful trees."""
    choices = {(F(0), F(1)), (F(1), F(0))}
    if not moves:
        return tuple(sorted(choices))
    for cost, reveal in PROBES:
        if cost > budget:
            continue
        weights = tuple(receipt_law(reveal, mean) for mean in TYPE_MEANS)
        children = pure_policy_frontier(moves - 1, budget - cost)
        for continuation in product(children, repeat=3):
            choices.add(tuple(
                sum(weights[h][s] * continuation[s][h] for s in range(3))
                for h in range(2)
            ))
    return pareto(choices)


def fixed_schedule_error(probes):
    laws = []
    words = tuple(product(range(3), repeat=len(probes)))
    for mean in TYPE_MEANS:
        law = [F(1)] * len(words)
        for ix, word in enumerate(words):
            for symbol, (_, reveal) in zip(word, probes):
                law[ix] *= receipt_law(reveal, mean)[symbol]
        laws.append(law)
    return sum(min(u, v) for u, v in zip(*laws)) / 2


def solve_linear(rows):
    rows = [list(map(F, row)) for row in rows]
    for i in range(len(rows)):
        pivot = next(k for k in range(i, len(rows)) if rows[k][i])
        rows[i], rows[pivot] = rows[pivot], rows[i]
        rows[i] = [a / rows[i][i] for a in rows[i]]
        for k, row in enumerate(rows):
            if k != i:
                rows[k] = [a - row[i] * b for a, b in zip(row, rows[i])]
    return tuple(row[-1] for row in rows)


def boundary_value(radius, mean, probe):
    if radius == 0:
        return F(1, 2), F(0)
    states = tuple(range(-radius + 1, radius))
    cost, reveal = probe
    p_down, p_up = reveal * (1 - mean), reveal * mean
    system = []
    for s in states:
        lhs = [F(0)] * len(states)
        lhs[states.index(s)] = reveal
        if s - 1 in states:
            lhs[states.index(s - 1)] -= p_down
        if s + 1 in states:
            lhs[states.index(s + 1)] -= p_up
        mistake = p_up if mean == TYPE_MEANS[0] and s + 1 == radius else F(0)
        if mean == TYPE_MEANS[1] and s - 1 == -radius:
            mistake = p_down
        system.append((lhs, mistake))
    error = solve_linear([lhs + [rhs] for lhs, rhs in system])
    charge = solve_linear([lhs + [cost] for lhs, _ in system])
    return error[states.index(0)], charge[states.index(0)]


def check_strategic_source_and_cost():
    counts = {}
    for theta, a in product(range(2), (0, 1, 2)):
        mask = set(range((1, 3)[theta]))
        observed = Counter()
        for u, z in product(range(4), repeat=2):
            current_stock = 6
            dispatched_stock = current_stock + int(u in mask or z < a)
            observed[dispatched_stock != current_stock] += 1
        counts[theta, a] = F(observed[True], 16)
    assert counts == {
        (0, 0): F(1, 4), (0, 1): F(7, 16), (0, 2): F(5, 8),
        (1, 0): F(3, 4), (1, 1): F(13, 16), (1, 2): F(7, 8)
    }
    # If the proposal sees a fresh Z first, a mask chosen as {Z} can always violate.
    singleton_masks = ({0}, {1}, {2}, {3})
    leaking_count = sum(u == 0 or z in singleton_masks[z] for u, z in product(range(4), repeat=2))
    assert leaking_count == 16

    adaptive_frontier = pure_policy_frontier(3, 4)
    assert min(sum(pair) / 2 for pair in adaptive_frontier) == F(61, 256)
    assert min(sum(pair) / 2 for pair in pure_policy_frontier(2, 6)) == F(1, 4)
    fixed = min(
        fixed_schedule_error(schedule)
        for n in range(4)
        for schedule in product(PROBES, repeat=n)
        if sum(cost for cost, _ in schedule) <= 4
    )
    assert fixed == F(1, 4)
    values = []
    for radius in range(1, 5):
        p, q = (boundary_value(radius, m, PROBES[0]) for m in TYPE_MEANS)
        assert p == q and p[0] == F(1, 1 + 3**radius)
        values.append(p)
    assert values[1] == (F(1, 10), F(32, 5))
    mixture = tuple(F(2, 3) * a + F(1, 3) * b for a, b in zip(*values[:2]))
    assert mixture == (F(1, 5), F(52, 15))
    print("PASS A1-A4: physical event counts, forbidden hindsight, exact pure-tree and absorbing-chain frontiers")


if __name__ == "__main__":
    check_physical_jobs()
    check_linked_regions()
    check_confidence_failures()
    check_strategic_source_and_cost()
