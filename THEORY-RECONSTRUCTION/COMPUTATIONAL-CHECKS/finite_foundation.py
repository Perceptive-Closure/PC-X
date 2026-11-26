"""Exhaustive finite checks of visible-history policy transport.

Run from the repository root with Python 3.13. This oracle rebuilds reachable
information sets from action-labelled support. No EXP-X01 solver is imported.
"""

from collections import defaultdict
from functools import cache
from itertools import product
from math import inf


def horizon_value(steps, observation, closed, costs, touches, start, freeze, depth):
    """Minimum supported worst cost within depth, starting with public knowledge of start."""

    @cache
    def visit(belief, remaining):
        if belief <= closed:
            return 0
        if not remaining:
            return inf
        feasible = []
        for action, price in enumerate(costs):
            if touches[action] & freeze:
                continue
            if not all(steps.get((state, action)) for state in belief):
                continue
            observed = defaultdict(set)
            for state in belief:
                for label, successor in steps[state, action]:
                    observed[label, observation[successor]].add(successor)
            continuation = [
                visit(frozenset(states), remaining - 1)
                for states in observed.values()
            ]
            feasible.append(price + max(continuation))
        return min(feasible, default=inf)

    return visit(frozenset({start}), depth)


def all_quotient_pairs():
    """Enumerate two open states and one closed state with two action masks."""

    obs = ("open", "open", "closed")
    doubled_obs = tuple(obs[s // 2] for s in range(6))
    keys = tuple(product(range(2), range(2)))
    for case, masks in enumerate(product(range(8), repeat=4)):
        steps = {
            key: tuple((0, t) for t in range(3) if mask & (1 << t))
            for key, mask in zip(keys, masks, strict=True)
        }
        # Each hidden member has the same projected support, with different
        # successor copies. The two copies need not be behaviorally identical
        # as raw physical states.
        doubled = {
            (2*s+copy, a): tuple(
                (label, 2*t + ((s+a+t+copy+case) % 2))
                for label, t in successors
            )
            for (s, a), successors in steps.items()
            for copy in range(2)
        }
        costs = (case % 2, 1)
        for freeze in range(4):
            reduced_value = horizon_value(
                steps, obs, frozenset({2}), costs, (1, 2), 0, freeze, 7
            )
            inflated_value = horizon_value(
                doubled, doubled_obs, frozenset({4, 5}), costs, (1, 2), 0, freeze, 7
            )
            assert reduced_value == inflated_value, (case, freeze, reduced_value, inflated_value)
            yield reduced_value


def distinguishing_boundary_values():
    # Identical first visible label and checkpoint observation leave both open
    # hidden branches possible. State-indexed renaming can match the raw
    # one-action sets; a shared observable-history renaming cannot.
    lost = {(0, 0): ((0, 1), (0, 2)), (1, 1): ((0, 3),), (2, 2): ((0, 3),)}
    shared = dict(lost)
    del shared[2, 2]
    shared[2, 1] = ((0, 3),)
    obs = ("entry", "aliased", "aliased", "terminal")
    args = (obs, frozenset({3}), (0, 1, 1), (0, 0, 0), 0, 0, 3)
    first = horizon_value(lost, *args), horizon_value(shared, *args)

    # Per-state relabeling of the readback would erase which visible child
    # group is present. Keeping Y separate from checkpoint O is necessary.
    separate = {
        (0, 0): ((0, 1), (0, 2)), (1, 1): ((1, 3),), (2, 1): ((2, 4),),
        (3, 2): ((0, 5),), (4, 3): ((0, 5),),
    }
    merged = dict(separate)
    merged[2, 1] = ((1, 4),)
    observed = ("entry", "shared", "shared", "post", "post", "terminal")
    args = (observed, frozenset({5}), (0, 0, 1, 1), (0, 0, 0, 0), 0, 0, 4)
    second = horizon_value(separate, *args), horizon_value(merged, *args)

    loop = {(0, 0): ((0, 0),)}
    third = horizon_value(loop, ("open",), frozenset(), (0,), (0,), 0, 0, 8)
    return first, second, third


if __name__ == "__main__":
    values = tuple(all_quotient_pairs())
    first, second, third = distinguishing_boundary_values()
    assert len(values) == 16384
    assert (first, second, third) == ((inf, 1), (1, inf), inf)
    print(f"{len(values)} base/lift comparisons; {sum(v < inf for v in values)} finite")
    print(f"state-local action renaming: {first}; state-local outcome renaming: {second}")
    print(f"open zero-cost loop: {third}")
