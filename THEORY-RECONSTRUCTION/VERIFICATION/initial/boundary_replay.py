"""Replay the small boundary constructions in the independent verification."""

from functools import cache
from itertools import product
from math import inf


def enumerate_witness_trees(graph, observations, goals, costs, entry):
    """Enumerate costs and physical supports for these acyclic witness graphs."""

    @cache
    def continuations(belief):
        if belief <= goals:
            return {(0, frozenset())}

        records = set()
        common_actions = set.intersection(*(set(graph[state]) for state in belief))
        for action in common_actions:
            child_states = {}
            for state in belief:
                for outcome, successor in graph[state][action]:
                    signal = (outcome, observations[successor])
                    child_states.setdefault(signal, set()).add(successor)

            child_records = [
                continuations(frozenset(states)) for states in child_states.values()
            ]
            occurrences = frozenset((state, action) for state in belief)
            for subtree_choices in product(*child_records):
                cost = costs[action] + max(cost for cost, _ in subtree_choices)
                support = occurrences.union(*(used for _, used in subtree_choices))
                records.add((cost, support))
        return records

    return continuations(frozenset({entry}))


def minimal_support_records(records, budget):
    feasible = {(cost, support) for cost, support in records if cost <= budget}
    return {
        (cost, support)
        for cost, support in feasible
        if all(not other < support for _, other in feasible)
    }


def check_observable_action_injection():
    shared = {"s": {"setup": (("split", "u"), ("split", "v"))}, "g": {}}
    repair = (("finish", "g"),)
    source = shared | {"u": {"left": repair}, "v": {"right": repair}}
    target = shared | {"u": {"go": repair}, "v": {"go": repair}}
    observations = {"s": "entry", "u": "hidden", "v": "hidden", "g": "goal"}
    costs = {"setup": 0, "left": 1, "right": 1, "go": 1}

    merged_action_name = {"left": "go", "right": "go"}
    for state in ("u", "v"):
        assert {merged_action_name[action] for action in source[state]} == set(target[state])

    assert enumerate_witness_trees(source, observations, {"g"}, costs, "s") == set()
    assert {cost for cost, _ in enumerate_witness_trees(
        target, observations, {"g"}, costs, "s"
    )} == {1}
    print("T03 weaker per-menu relabeling: +infinity versus 1")


def check_residual_budget_pruning():
    graph = {
        "s": {"prefix": (("ok", "h"),)},
        "h": {"fork": (("left", "p"), ("right", "q"))},
        "p": {"prepare_pair": (("ok", "r"), ("ok", "t"))},
        "q": {"prepare_singleton": (("ok", "r"),)},
        "r": {"slow": (("end", "g"),), "fast": (("end", "g"),)},
        "t": {"slow": (("end", "g"),)},
        "g": {},
    }
    observations = {state: state for state in graph} | {"r": "hidden", "t": "hidden"}
    costs = dict(prefix=4, fork=0, prepare_pair=0, prepare_singleton=4, slow=5, fast=1)
    local = enumerate_witness_trees(graph, observations, {"g"}, costs, "h")
    ((slow_cost, small_support),) = minimal_support_records(local, 9)
    ((fast_cost, large_support),) = minimal_support_records(local, 5)
    assert (slow_cost, fast_cost) == (9, 5)
    assert large_support == small_support | {("r", "fast")}

    root = enumerate_witness_trees(graph, observations, {"g"}, costs, "s")
    assert {cost for cost, _ in root} == {9, 13}
    assert minimal_support_records(root, 9) == {
        (9, large_support | {("s", "prefix")})
    }
    print("T12 residual budget: supports at local costs 5 and 9; root optimum 9")


def check_serial_binary_encoding():
    count = 0
    families = list(product(range(1, 5), repeat=3))
    families.append((2**40 + 1, 2**39 + 2, 2**30 + 4))
    for weights in families:
        sums = {sum(w * bit for w, bit in zip(weights, bits))
                for bits in product((0, 1), repeat=len(weights))}
        thresholds = {subtotal + offset for subtotal in sums for offset in (-1, 0, 1)}
        base = len(weights) + 2
        for threshold in thresholds:
            if threshold < 0:
                continue
            crosses = any(
                base + subtotal <= base + threshold < base + subtotal + 1
                for subtotal in sums
            )
            assert crosses == (threshold in sums)
            count += 1
    print(f"T10.b binary subset-sum equivalence: {count} thresholds")


def check_capped_join():
    values = (0, 1, 2, 7, 2**40, inf)
    for budget in (0, 1, 6, 2**40):
        bound = budget + 1
        for a, b, c in product(values, repeat=3):
            assert min(bound, min(bound, a + b) + c) == min(bound, a + b + c)
            assert min(bound, a + min(bound, b + c)) == min(bound, a + b + c)

    # Both child leaf modes must equal the shared bag mode. The center is charged at forget.
    scores = (1, 2)
    mode_pairs = set(product((0, 1), repeat=2))
    for probe_left_leaf in (False, True):
        left_child = {(l, r): (0, 0) for l, r in mode_pairs if not probe_left_leaf or l == r}
        right_child = {pair: (0, 0) for pair in mode_pairs}
        root_pairs = {
            (min(2, left_child[l, r][0] + right_child[l, r][0] + scores[l]),
             min(2, left_child[l, r][1] + right_child[l, r][1] + scores[r]))
            for l, r in left_child.keys() & right_child.keys()
        }
        assert ((1, 2) in root_pairs) == (not probe_left_leaf)
    print("T14.c saturated costs and shared-bag charging: 864 triples and two paired queries")


if __name__ == "__main__":
    check_observable_action_injection()
    check_residual_budget_pruning()
    check_serial_binary_encoding()
    check_capped_join()
