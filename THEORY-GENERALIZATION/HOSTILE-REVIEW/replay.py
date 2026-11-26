"""Small exact controls for the hostile mathematical review."""

from collections import defaultdict
from fractions import Fraction as F
from functools import cache
from itertools import product
from math import inf


def online_value(paths, premiums, budget, horizon, initial, rows, prices, identity=False):
    """Enumerate exact path cells in the online supported service protocol."""
    stages = len(premiums)
    targets = {
        path: stages + sum(bit * premium for bit, premium in zip(path, premiums)) <= budget
        for path in paths
    }

    @cache
    def solve(cell, stage, meter, work, moves):
        labels = {targets[path] for path in cell}
        if not cell:
            raise ValueError("The initial evidence is inconsistent.")
        if not identity or len(cell) == 1:
            if labels == {False} or (labels == {True} and stage == stages):
                return F(0)
        if moves == 0 or stage == stages:
            return inf

        values = []
        for command in ("fast", "slow", "read", "prepare"):
            tariff = {"fast": 1, "slow": 1 + premiums[stage]}.get(command, 0)
            if tariff > work:
                continue
            supported = [
                rows.get((stage, path[stage], meter, command), ())
                for path in cell
            ]
            if not all(supported):
                continue
            groups = defaultdict(set)
            for path, replies in zip(cell, supported):
                for observation in replies:
                    groups[observation].add(path)

            next_stage = stage + (command in ("fast", "slow"))
            quote = prices.get((stage, meter, command), F(0))
            continuation = max(
                solve(frozenset(group), next_stage, next_meter, work - tariff, moves - 1)
                for (_, next_meter), group in groups.items()
            )
            values.append(quote + continuation)
        return min(values, default=inf)

    return solve(frozenset(paths), 0, initial, budget, horizon)


def meter_control():
    """The same receipt code carries two observed meters with different legal quotes."""
    paths = ((0, 0), (0, 1))
    rows = {
        (0, 0, "initial", "fast"): (("ready", "discount"), ("ready", "standard")),
        (0, 0, "initial", "slow"): (("ready", "discount"), ("ready", "standard")),
    }
    prices = {(1, "standard", "prepare"): F(1, 3)}
    for meter, quote in (("discount", F(1, 3)), ("standard", F(3, 2))):
        rows[1, 0, meter, "fast"] = (("served", "done"),)
        prices[1, meter, "read"] = quote
        for bit in (0, 1):
            rows[1, bit, meter, "read"] = ((bit, meter),)
            rows[1, bit, meter, "slow"] = (("served", "done"),)
            rows[1, bit, "standard", "prepare"] = (("ready", "discount"),)
    short = online_value(paths, (1, 1), 2, 3, "initial", rows, prices)
    longer = online_value(paths, (1, 1), 2, 4, "initial", rows, prices)
    assert (short, longer) == (F(3, 2), F(2, 3))

    optimistic = rows.copy()
    for command in ("fast", "slow"):
        optimistic[0, 0, "initial", command] = (("ready", "discount"),)
    omitted_branch = online_value(paths, (1, 1), 2, 3, "initial", optimistic, prices)
    assert omitted_branch == F(1, 3) < short
    print(f"Meter-sensitive optimum: H=3 -> {short}, H=4 -> {longer}, omitted support -> {omitted_branch}.")


def service_rows(stages, include_reads):
    rows = {}
    prices = {}
    for stage in range(stages):
        rows[stage, 0, "open", "fast"] = (("served", "open"),)
        for bit in (0, 1):
            rows[stage, bit, "open", "slow"] = (("served", "open"),)
            if include_reads:
                rows[stage, bit, "open", "read"] = ((bit, "open"),)
                prices[stage, "open", "read"] = F(1)
    return rows, prices


def correlated_control():
    paths = ((0, 1), (1, 0))
    rows, prices = service_rows(2, include_reads=False)
    assert {2 + sum(path) for path in paths} == {3}
    assert online_value(paths, (1, 1), 3, 2, "open", rows, prices) == inf
    assert online_value(paths, (1, 1), 4, 2, "open", rows, prices) == 0
    print("Correlated fixture: empty static identification, no joint service at D=3, service at D=4.")


def matched_identity_control():
    for n in range(1, 5):
        stages = n + 1
        paths = tuple(product((0, 1), repeat=stages))
        premiums = (1,) * n + (n + 1,)
        rows, prices = service_rows(stages, include_reads=True)
        budget, horizon = 2 * n + 1, 2 * n + 2
        target = online_value(paths, premiums, budget, horizon, "open", rows, prices)
        identity = online_value(paths, premiums, budget, horizon, "open", rows, prices, identity=True)
        assert (target, identity) == (1, n + 1)
        assert n + (n + 2) > budget
        assert 2 * n + 1 <= budget and 2 * n <= budget
        assert 2 * n + 2 <= horizon and 2 * n + 1 <= horizon
    print("Matched in-class target/identity costs 1 versus n+1 for n=1,2,3,4.")


def safety_and_law_controls():
    # The only supported edge is marked safe but leads to an unsafe useful terminal.
    # Both endpoints have a positive target tag. Only the target terminal is marked useful.
    unsafe_child = {"positive": True, "useful": True, "safe": False}
    edge_safe = True
    stop_only = unsafe_child["positive"] and unsafe_child["useful"]
    validated = edge_safe and unsafe_child["safe"] and stop_only
    assert stop_only and not validated

    same_law = (F(1, 2), F(1, 2))
    pass_pure = ((F(1), F(0)), (F(0), F(1)))
    assert same_law not in pass_pure
    mixed_pass = tuple((left + right) / 2 for left, right in zip(*pass_pure))
    assert mixed_pass == same_law
    for pass_probability in (F(0), F(1, 4), F(1, 2), F(3, 4), F(1)):
        pass_error, fail_error = 1 - pass_probability, pass_probability
        assert max(pass_error, fail_error) >= F(1, 2)

    equal = {(0, 0): F(1, 2), (1, 1): F(1, 2)}
    opposite = {(0, 1): F(1, 2), (1, 0): F(1, 2)}
    for index in (0, 1):
        assert sum(weight for pair, weight in equal.items() if pair[index]) == F(1, 2)
        assert sum(weight for pair, weight in opposite.items() if pair[index]) == F(1, 2)
    assert set(equal).isdisjoint(opposite)

    # A prior omitting a compatible failure path can mask supported failure.
    failure = (F(0), F(1))
    assert sum(mass * event for mass, event in zip((F(1), F(0)), failure)) == 0
    assert sum(mass * event for mass, event in zip((F(1, 2), F(1, 2)), failure)) == F(1, 2)
    print("Unsafe-terminal, full-mixture alias, joint-record separation, and omitted-path controls passed.")


if __name__ == "__main__":
    meter_control()
    correlated_control()
    matched_identity_control()
    safety_and_law_controls()
