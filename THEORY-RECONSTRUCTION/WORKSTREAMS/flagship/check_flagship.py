"""Independently replay T30's finite target and acquisition claims.

This checker tests declared finite tables. It does not authenticate a physical
deployment's input inventory. Run with CPython 3.13 or a compatible version.
"""

from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations, product
from math import inf


@dataclass(frozen=True)
class Mode:
    stale: int
    replies: tuple[int, ...]


@dataclass(frozen=True)
class Stage:
    base: int
    extra: int
    prices: tuple[Fraction, ...]
    modes: tuple[Mode, ...]


def mode_cost(stage, mode):
    return stage.base + stage.extra * stage.modes[mode].stale


def total_cost(stages, modes):
    return sum(mode_cost(s, row) for s, row in zip(stages, modes, strict=True))


def extrema(stages):
    if not stages or any(not site.modes for site in stages):
        raise ValueError("Inconsistent input")
    choices = tuple(tuple(range(len(site.modes))) for site in stages)
    low = tuple(min(ids, key=lambda i: mode_cost(site, i))
                for site, ids in zip(stages, choices, strict=True))
    high = tuple(max(ids, key=lambda i: mode_cost(site, i))
                 for site, ids in zip(stages, choices, strict=True))
    return (total_cost(stages, low), low), (total_cost(stages, high), high)


@dataclass(frozen=True)
class Predecessor:
    previous: object
    stage: int
    mode: int


def capped_outside(stages, excluded, limit):
    attainable = {0: None}
    for i, site in enumerate(stages):
        if i == excluded:
            continue
        updated = {}
        for old, parent in attainable.items():
            for row, mode in enumerate(site.modes):
                s = min(limit + 1, old + site.extra * mode.stale)
                if s not in updated:
                    updated[s] = Predecessor(parent, i, row)
        attainable = updated
    return attainable


def make_pair(parent, n, excluded, left, right):
    prefix = [None] * n
    while parent is not None:
        prefix[parent.stage] = parent.mode
        parent = parent.previous
    prefix[excluded] = left
    a = tuple(prefix)
    prefix[excluded] = right
    return a, tuple(prefix)


def cost_of_mask(prices, mask):
    return sum((p for j, p in enumerate(prices) if (mask >> j) & 1), Fraction())


def best_audit(stages, budget):
    extrema(stages)
    limit = budget - sum(stage.base for stage in stages)
    if limit < 0:
        return Fraction(), tuple(0 for _ in stages), None

    masks = []
    for i, stage in enumerate(stages):
        outside = capped_outside(stages, i, limit)
        edges = set()
        for (l, left), (r, right) in combinations(enumerate(stage.modes), 2):
            low, high = stage.extra * left.stale, stage.extra * right.stale
            if low == high:
                continue
            for s, witness in outside.items():
                if (s + low <= limit) != (s + high <= limit):
                    break
            else:
                continue
            edge = sum(1 << j for j, (x, y) in
                       enumerate(zip(left.replies, right.replies, strict=True)) if x != y)
            if not edge:
                return inf, None, make_pair(witness, len(stages), i, l, r)
            edges.add(edge)
        local = min(
            (mask for mask in range(1 << len(stage.prices))
             if all(mask & edge for edge in edges)),
            key=lambda mask: cost_of_mask(stage.prices, mask),
        )
        masks.append(local)
    cost = sum((cost_of_mask(site.prices, mask) for site, mask in
                zip(stages, masks, strict=True)), Fraction())
    return cost, tuple(masks), None


def exhaustive_cost(stages, budget):
    rows = tuple(product(*(range(len(x.modes)) for x in stages)))
    costs = tuple(total_cost(stages, row) <= budget for row in rows)

    def label(row, masks):
        answer_parts = []
        for stage, index, mask in zip(stages, row, masks, strict=True):
            answer = stage.modes[index].replies
            answer_parts.extend(a for j, a in enumerate(answer) if mask & (1 << j))
        return tuple(answer_parts)

    best = inf
    for masks in product(*(range(1 << len(x.prices)) for x in stages)):
        cells = {}
        for row, label_value in zip(rows, costs, strict=True):
            key = label(row, masks)
            if key in cells and cells[key] != label_value:
                break
            cells[key] = label_value
        else:
            amount = sum(cost_of_mask(s.prices, mask)
                         for s, mask in zip(stages, masks, strict=True))
            best = min(best, amount)
    return best


def exhaustive_common_cost(stages):
    jobs = tuple(product(*(range(len(x.modes)) for x in stages)))
    best = inf
    for actions in product((0, 1), repeat=len(stages)):
        if any(any(not a and s.modes[j].stale for a, s, j in
                   zip(actions, stages, mode, strict=True)) for mode in jobs):
            continue
        cost = sum(s.base + a * s.extra for s, a in zip(stages, actions, strict=True))
        best = min(best, cost)
    return best


def case(weight, accessible):
    replies = ((0,), (1,)) if accessible else ((), ())
    return Stage(1, weight, (Fraction(2, 3),) if accessible else (),
                 tuple(Mode(x, label) for x, label in enumerate(replies)))


def assert_witness(stages, budget, witness):
    a, b = witness
    assert (total_cost(stages, a) <= budget) != (total_cost(stages, b) <= budget)
    assert all(s.modes[i].replies == s.modes[j].replies
               for s, i, j in zip(stages, a, b, strict=True))


def main():
    count = 0
    for weights in product(range(1, 4), repeat=3):
        for accessible in product((False, True), repeat=3):
            stages = tuple(case(w, q) for w, q in zip(weights, accessible, strict=True))
            _, (max_cost, maximizing) = extrema(stages)
            assert exhaustive_common_cost(stages) == max_cost == total_cost(stages, maximizing)
            for cap in range(13):
                cost, plan, witness = best_audit(stages, cap)
                assert cost == exhaustive_cost(stages, cap)
                if witness:
                    assert cost == inf and plan is None
                    assert_witness(stages, cap, witness)
                count += 1

    g = 64
    bits = (Mode(0, (0,)), Mode(1, (1,)))
    ordinary = Stage(1, 1, (Fraction(1),), bits)
    gateway = Stage(1, g+1, (Fraction(1),), bits)
    network = (gateway,) + (ordinary,) * g
    cost, plan, witness = best_audit(network, 2*g+1)
    assert (cost, plan, witness) == (1, (1,) + (0,) * g, None)
    initial = (0,) * len(network)
    for i, stage in enumerate(network):
        other = initial[:i] + (1,) + initial[i+1:]
        assert total_cost(network, other) - total_cost(network, initial) == stage.extra
        assert all(network[j].modes[initial[j]].replies == network[j].modes[other[j]].replies
                   for j in range(len(network)) if i != j)
    known_good = (Stage(1, g+1, (Fraction(1),), bits[:1]),) + (ordinary,) * g
    assert extrema(known_good)[1][0] == 2*g+1

    try:
        best_audit((Stage(1, 1, (), ()),), 2)
    except ValueError:
        pass
    else:
        raise AssertionError("Empty evidence must be rejected")
    print(f"{count} static-certificate crosschecks; product of 2^{len(network)} modes checked structurally")
    print("Gateway target minimum 1, minimum full identity reads 65, robust positive deadline 129")


if __name__ == "__main__":
    main()
