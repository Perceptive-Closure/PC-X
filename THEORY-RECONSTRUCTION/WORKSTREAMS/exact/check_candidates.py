"""Finite controls for the T04–T14 constructor claims.

This standalone standard-library script never imports experiment solvers and does
not read or execute a native fixture. The calculations test small explicit cases
and are supplementary to the quantified proofs.
"""

from collections import defaultdict
from dataclasses import dataclass, replace
from functools import cache
from itertools import combinations, product
from math import inf
import json


OPEN = (0, 0, 1, 2)
FINE = (0, 1, 2, 3)
JOINED = (0, 0, 1, 0)
WORLD = ("permit", "deny", "permit", "permit")
BASE_ROLE = frozenset({"workflow"})


@dataclass(frozen=True)
class Profile:
    history: int
    representation: tuple
    rights: frozenset


@dataclass(frozen=True)
class Move:
    cost: int
    successor: str
    right: str = "workflow"
    ordinary_guard: bool = True


START = Profile(0, OPEN, BASE_ROLE)
E_GOAL = Profile(2, OPEN, BASE_ROLE)
R_GOAL = Profile(0, FINE, BASE_ROLE)


def partition(labels):
    return frozenset(
        frozenset(i for i, value in enumerate(labels) if value == label)
        for label in set(labels)
    )


def evaluate(profiles, moves, initial, freeze):
    """Independent fully observed evaluator for the acyclic proof fixtures."""
    @cache
    def cost(name):
        source = profiles[name]
        cell = next(group for group in partition(source.representation) if source.history in group)
        if len({WORLD[index] for index in cell}) == 1:
            return 0
        candidates = []
        old = source.history, partition(source.representation), source.rights
        for move in moves.get(name, ()):
            if not move.ordinary_guard or move.right not in source.rights:
                continue
            successor = profiles[move.successor]
            new = successor.history, partition(successor.representation), successor.rights
            touches = {tag for tag, before, after in zip("ERA", old, new, strict=True) if before != after}
            if touches.isdisjoint(freeze):
                candidates.append(move.cost + cost(move.successor))
        return min(candidates, default=inf)

    return cost(initial)


def review_workflow(primary, reviews):
    """T07 shared-entry transfer with consequential authority settings."""
    last = str(len(reviews))
    profiles = {
        "root": START,
        "fast": replace(E_GOAL if primary else R_GOAL, rights=BASE_ROLE | {"receipt"}),
        "receipt": replace(E_GOAL if primary else R_GOAL, rights=BASE_ROLE | {"receipt"}),
        "closed": E_GOAL,
        last: START,
    }
    moves = {
        "root": (Move(1, "fast"), Move(2, "0")),
        "fast": (Move(0, "receipt", right="receipt"),),
        last: (Move(1, "closed"),),
    }
    for i, enabled in enumerate(reviews):
        begin, end, transit, escalated = str(i), str(i + 1), f"transit-{i}", f"escalated-{i}"
        profiles[begin] = START
        rights = BASE_ROLE | {"escalate"} if enabled else BASE_ROLE
        profiles[transit] = replace(START, rights=rights)
        profiles[escalated] = replace(E_GOAL, rights=rights)
        moves[begin] = Move(1, transit), Move(2, end)
        moves[transit] = Move(0, end), Move(1, escalated, right="escalate")
    return profiles, moves


def routed_workflow(address, route_bits, *, fallback):
    """T09 ordinary route selection, or all routes exposed as in T10.a."""
    profiles = {"root": START}
    moves = []
    for site, bit in enumerate(route_bits):
        name = f"site-{site}"
        profiles[name] = E_GOAL if bit else R_GOAL
        moves.append(Move(1, name, ordinary_guard=address is None or site == address))
    if fallback:
        profiles["fallback"] = E_GOAL
        moves.append(Move(2, "fallback"))
    return profiles, {"root": tuple(moves)}


def serial_workflow(bits, weights):
    """T10.b matched-entry local R changes and the fixed E suffix."""
    profiles = {"closed": E_GOAL, str(len(bits)): START}
    moves = {str(len(bits)): (Move(1, "closed"),)}
    for i, (bit, weight) in enumerate(zip(bits, weights, strict=True)):
        begin, end, transit = str(i), str(i + 1), f"transit-{i}"
        profiles[begin] = START
        profiles[transit] = replace(START, representation=JOINED if bit else OPEN)
        moves[begin] = Move(1, transit), Move(1 + weight, end)
        moves[transit] = (Move(0, end),)
    return profiles, moves


def subsets(size):
    for count in range(size + 1):
        yield from combinations(range(size), count)


def mixed_fiber(rows, selected):
    labels = {}
    for values, target in rows:
        answers = tuple(values[query] for query in selected)
        if labels.setdefault(answers, target) != target:
            return True
    return False


def static_cost(rows, size):
    return min((len(selected) for selected in subsets(size) if not mixed_fiber(rows, selected)), default=inf)


def adaptive_cost(rows, size):
    @cache
    def value(remaining):
        if len({rows[i][1] for i in remaining}) == 1:
            return 0
        candidates = []
        for j in range(size):
            partition = defaultdict(list)
            for i in remaining:
                partition[rows[i][0][j]].append(i)
            if len(partition) > 1:
                candidates.append(1 + max(value(tuple(cell)) for cell in partition.values()))
        return min(candidates, default=inf)

    return value(tuple(range(len(rows))))


def realized_costs(rows, size):
    result = []
    for actual, target in rows:
        result.append(min((
            len(selected)
            for selected in subsets(size)
            if all(
                other_target == target or any(other[j] != actual[j] for j in selected)
                for other, other_target in rows
            )
        ), default=inf))
    return result


def check_workflows():
    rows_checked = 0
    for width in range(1, 5):
        targets = []
        identities = []
        for primary, *reviews in product(range(2), repeat=width + 1):
            profiles, moves = review_workflow(primary, reviews)
            target = evaluate(profiles, moves, "root", {"R"}) <= 1
            assert target == bool(primary)
            assert evaluate(profiles, moves, "root", {"A"}) == 3 + width + sum(reviews)
            identity = (primary, *reviews)
            targets.append((identity, target))
            identities.append((identity, identity))
            rows_checked += 1
        assert static_cost(targets, width + 1) == 1
        assert static_cost(identities, width + 1) == width + 1
        assert mixed_fiber(identities, tuple(range(width)))
        assert not mixed_fiber(targets, tuple(range(width)))

    routed_values = {}
    for width in range(3):
        routes = 2**width
        rows = []
        for bits in product(range(2), repeat=width + routes):
            address = sum(bit << i for i, bit in enumerate(bits[:width]))
            route_bits = bits[width:]
            profiles, moves = routed_workflow(address, route_bits, fallback=True)
            target = evaluate(profiles, moves, "root", {"R"}) <= 1
            assert target == bool(route_bits[address])
            rows.append((bits, target))
            rows_checked += 1
        adaptive, static = adaptive_cost(rows, len(bits)), static_cost(rows, len(bits))
        assert (adaptive, static) == (width + 1, width + routes)
        routed_values[width] = [adaptive, static]
        if width == 1:
            one_bit_address_rows = rows

    one_hot = tuple((bits, i) for i, bits in enumerate(((0, 0, 1), (0, 1, 0), (1, 0, 0))))
    joint = tuple(
        (first_bits + second_bits, (first_value, second_value))
        for (first_bits, first_value), (second_bits, second_value) in product(one_hot, one_bit_address_rows)
    )
    hierarchy = [max(realized_costs(joint, 6)), adaptive_cost(joint, 6), static_cost(joint, 6)]
    assert hierarchy == [3, 4, 5]
    return {"canonical_rows": rows_checked, "routed_adaptive_static": routed_values, "strict_hierarchy": hierarchy}


def check_hitting_embedding():
    edges = [frozenset(edge) for edge in subsets(3) if edge]
    checked = 0
    for edge_indices in subsets(len(edges)):
        family = [edges[i] for i in edge_indices]
        vectors = [(0, 0, 0)] + [tuple(int(i in edge) for i in range(3)) for edge in family]
        rows = []
        for vector in vectors:
            profiles, moves = routed_workflow(None, vector, fallback=False)
            target = evaluate(profiles, moves, "root", {"R"}) <= 1
            assert target == any(vector)
            rows.append((vector, target))
        optimum = min(len(chosen) for chosen in subsets(3) if all(not edge.isdisjoint(chosen) for edge in family))
        assert optimum == static_cost(rows, 3)
        checked += 1
    return checked


def check_serial_reduction():
    instances = 0
    for weights in product(range(1, 5), repeat=3):
        rows = []
        for x in product(range(2), repeat=3):
            for hidden in range(2):
                profiles, moves = serial_workflow((*x, hidden), (*weights, 1))
                observed = evaluate(profiles, moves, "0", {"R"})
                assert observed == 5 + sum(weight * bit for weight, bit in zip(weights, x, strict=True)) + hidden
                rows.append((x, observed))
        witness_sums = {sum(weight * bit for weight, bit in zip(weights, x, strict=True)) for x, _ in rows}
        for requested in range(1 + sum(weights)):
            verdicts = [(x, observed <= 5 + requested) for x, observed in rows]
            assert mixed_fiber(verdicts, (0, 1, 2)) == (requested in witness_sums)
            instances += 1
    return instances


def clutter(family):
    candidates = frozenset(family)
    return frozenset(edge for edge in candidates if not any(other < edge for other in candidates))


def blocker(ground, family):
    hitting_sets = []
    for indices in subsets(len(ground)):
        candidate = frozenset(ground[i] for i in indices)
        if all(not edge.isdisjoint(candidate) for edge in family):
            hitting_sets.append(candidate)
    return clutter(hitting_sets)


def check_support_dual():
    ground = ("a", "b", "c")
    all_edges = tuple(frozenset(ground[i] for i in indices) for indices in subsets(3))
    examples = 0
    for indexes in subsets(len(all_edges)):
        family = clutter(frozenset(all_edges[i] for i in indexes))
        minimal_blockers = blocker(ground, family)
        assert blocker(ground, minimal_blockers) == family
        for mask in all_edges:
            assert (not any(edge.isdisjoint(mask) for edge in family)) == any(
                candidate <= mask for candidate in minimal_blockers
            )
        examples += 1
    return examples


def local_crosses(scores, budget, stage):
    outside = {
        sum(values)
        for values in product(*(row for i, row in enumerate(scores) if i != stage))
    }
    return any((total + scores[stage][0] <= budget) != (total + scores[stage][1] <= budget) for total in outside)


def check_crossing():
    budgets_checked = 0
    for values in product((0, 1, 2, inf), repeat=4):
        scores = (values[:2], values[2:])
        for budget in range(5):
            rows = [
                (bits, sum(scores[i][bit] for i, bit in enumerate(bits)) <= budget)
                for bits in product(range(2), repeat=2)
            ]
            local_pivots = {i for i in range(2) if local_crosses(scores, budget, i)}
            for subset in subsets(2):
                assert mixed_fiber(rows, subset) == bool(local_pivots.difference(subset))
            budgets_checked += 1
    return budgets_checked


@dataclass(frozen=True)
class Node:
    """Small nice-decomposition control structure with explicit relation tests."""

    operation: str
    bag: tuple
    children: tuple = ()
    variable: int | None = None
    allowed: frozenset = frozenset()


def paired_tree_conflict(root, costs, selected, budget, terminal):
    """Saturated-score DP on paired two-mode controls."""
    top = budget + 1
    mode_pairs = tuple(product(range(2), repeat=2))

    def add(first, second):
        return tuple(min(top, a + b) for a, b in zip(first, second, strict=True))

    def visit(node):
        if node.operation == "leaf":
            return {(): {(0, 0)}}
        first = visit(node.children[0])
        child_bag = node.children[0].bag
        if node.operation == "introduce":
            index = node.bag.index(node.variable)
            return {
                old[:index] + (pair,) + old[index:]: scores
                for old, scores in first.items()
                for pair in mode_pairs
                if node.variable not in selected or pair[0] == pair[1]
            }
        if node.operation == "check":
            return {
                assignment: scores
                for assignment, scores in first.items()
                if all(tuple(bit[side] for bit in assignment) in node.allowed for side in (0, 1))
            }
        if node.operation == "forget":
            index = child_bag.index(node.variable)
            result = defaultdict(set)
            for assignment, scores in first.items():
                tag = assignment[:index] + assignment[index + 1:]
                contribution = tuple(costs[node.variable][mode] for mode in assignment[index])
                result[tag].update(add(score, contribution) for score in scores)
            return result
        if node.operation == "join":
            second = visit(node.children[1])
            return {
                tag: {add(left, right) for left, right in product(first[tag], second[tag])}
                for tag in first.keys() & second.keys()
            }
        raise ValueError(f"Unexpected control node {node.operation}")

    return any(
        left + terminal <= budget < right + terminal
        for left, right in visit(root).get((), ())
    )


def correlation_tree(left_relation, right_relation):
    def branch(peer, allowed):
        leaf = Node("leaf", ())
        shared = Node("introduce", (1,), (leaf,), variable=1)
        bag = tuple(sorted((1, peer)))
        together = Node("introduce", bag, (shared,), variable=peer)
        test = Node("check", bag, (together,), allowed=allowed)
        return Node("forget", (1,), (test,), variable=peer)

    joined = Node("join", (1,), (branch(0, left_relation), branch(2, right_relation)))
    return Node("forget", (), (joined,), variable=1)


def check_treewidth():
    binary_rows = tuple(product(range(2), repeat=2))
    relations = tuple(frozenset(binary_rows[i] for i in indices) for indices in subsets(4))
    costs = ((0, 2), (1, inf), (0, 3))
    selected_menus = ((), (0,), (0, 2), (0, 1, 2))
    checked = 0
    for left, right in product(relations, repeat=2):
        root = correlation_tree(left, right)
        compatible = tuple(
            row for row in product(range(2), repeat=3)
            if row[:2] in left and row[1:] in right
        )
        for budget in range(5):
            table = [
                (row, 1 + sum(costs[i][bit] for i, bit in enumerate(row)) <= budget)
                for row in compatible
            ]
            for selected in selected_menus:
                actual = paired_tree_conflict(root, costs, selected, budget, terminal=1)
                assert actual == mixed_fiber(table, selected)
                checked += 1
    return checked


def check_kernel_boundaries():
    moves = {
        "root": (Move(1, "intermediate"), Move(3, "c"), Move(3, "d")),
        "intermediate": (Move(1, "b"),),
    }
    first = {
        "root": START,
        "intermediate": replace(START, representation=JOINED),
        "b": replace(E_GOAL, representation=JOINED),
        "c": R_GOAL,
        "d": E_GOAL,
    }
    second = {
        "root": START,
        "intermediate": START,
        "b": replace(E_GOAL, representation=FINE),
        "c": E_GOAL,
        "d": R_GOAL,
    }
    assert evaluate(first, moves, "root", set()) == 2
    assert evaluate(first, moves, "root", {"R"}) == 3
    assert evaluate(second, moves, "root", {"R"}) == 3
    assert evaluate(first, {}, "root", set()) == inf

    def fork_value(revealed):
        actions = {
            "root": {"fork": ((0, "left"), (int(revealed), "right"))},
            "left": {"go-left": ((0, "closed"),)},
            "right": {"go-right": ((0, "closed"),)},
            "closed": {},
        }

        @cache
        def value(belief):
            if belief == frozenset({"closed"}):
                return 0
            legal = set.intersection(*(set(actions[state]) for state in belief))
            candidates = []
            for action in legal:
                support = defaultdict(set)
                for state in belief:
                    for observation, successor in actions[state][action]:
                        support[observation].add(successor)
                candidates.append(1 + max(value(frozenset(branch)) for branch in support.values()))
            return min(candidates, default=inf)

        return value(frozenset({"root"}))

    assert fork_value(False) == inf
    assert fork_value(True) == 2

    valid_modes = tuple(product(range(2), repeat=2))
    correlated = [(bits, not any(bits)) for bits in valid_modes if bits[0] == bits[1]]
    assert mixed_fiber(correlated, ())
    assert all(
        sum(a != b for a, b in zip(first_mode, second_mode, strict=True)) == 2
        for (first_mode, first_target), (second_mode, second_target) in combinations(correlated, 2)
        if first_target != second_target
    )
    parity = [((sum(bits) % 2,), not any(bits)) for bits in valid_modes]
    assert mixed_fiber(parity, (0,))
    for left, right in combinations(range(len(valid_modes)), 2):
        distance = sum(a != b for a, b in zip(valid_modes[left], valid_modes[right], strict=True))
        if parity[left][1] != parity[right][1] and distance == 1:
            assert parity[left][0] != parity[right][0]
    return {"correlated_envelope": [2, 3, "infinity"], "resource_and_query_boundary_controls": 5}


def main():
    verdicts = {
        "T07_T09": check_workflows(),
        "T10a": check_hitting_embedding(),
        "T10b": check_serial_reduction(),
        "T11_T12_T14_boundaries": check_kernel_boundaries(),
        "T12": check_support_dual(),
        "T14b": check_crossing(),
        "T14c": check_treewidth(),
    }
    print(json.dumps(verdicts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
