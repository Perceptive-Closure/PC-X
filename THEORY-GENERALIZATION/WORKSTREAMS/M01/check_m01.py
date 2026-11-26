"""Exact finite corroboration for the sealed M01 claims.

The recurrence and controller-tree reference share only the typed fixture data.
The file does not serve as a production compiler or a solver benchmark.
"""

from dataclasses import dataclass
from fractions import Fraction
from itertools import product
from math import inf


EVIDENCE, REPRESENTATION, AUTHORITY = 1, 2, 4


@dataclass(frozen=True)
class State:
    admitted: int
    cells: tuple[int, ...]
    rights: frozenset[str]
    public: str


@dataclass(frozen=True)
class Arm:
    destination: str
    reply: str
    weight: Fraction = Fraction(1)


@dataclass(frozen=True)
class Source:
    states: dict[str, State]
    bodies: dict[tuple[str, str], tuple[Arm, ...]]
    costs: dict[str, int]
    worlds: tuple[frozenset[int], ...]
    entry: str = "root"


@dataclass(frozen=True)
class Move:
    price: int
    touched: int
    children: tuple[frozenset[str], ...]


def extensional_mask(before, after):
    fields = (
        (EVIDENCE, before.admitted, after.admitted),
        (REPRESENTATION, before.cells, after.cells),
        (AUTHORITY, before.rights, after.rights),
    )
    return sum(bit for bit, old, new in fields if old != new)


def compile_rows(source):
    support = {}
    masks = {}
    for key, alternatives in source.bodies.items():
        state, action = key
        before = source.states[state]
        if action not in before.rights:
            continue
        support[key] = {arm for arm in alternatives if arm.weight > 0}
        mask = 0
        for arm in support[key]:
            mask |= extensional_mask(before, source.states[arm.destination])
        masks[key] = mask
    reachable = {source.entry}
    pending = [source.entry]
    closed = {}
    while pending:
        state = pending.pop()
        row = source.states[state]
        world_set = set()
        for candidate, worlds in enumerate(source.worlds):
            if row.cells[candidate] == row.cells[row.admitted]:
                world_set.update(worlds)
        if not world_set:
            raise ValueError("empty represented fiber")
        closed[state] = len(world_set) == 1
        for action in source.costs:
            key = (state, action)
            if key not in support:
                continue
            if not support[key]:
                raise ValueError("empty support at a callable occurrence")
            for arm in support[key]:
                if arm.destination not in reachable:
                    reachable.add(arm.destination)
                    pending.append(arm.destination)
    return support, masks, closed


def belief_graph(source, freeze=0, kept=None):
    support, masks, closed = compile_rows(source)
    initial = frozenset((source.entry,))
    graph = {}
    pending = [initial]
    while pending:
        belief = pending.pop()
        if belief in graph:
            continue
        moves = []
        for action, cost in source.costs.items():
            occurrences = {(state, action) for state in belief}
            if any(key not in support or masks[key] & freeze for key in occurrences):
                continue
            if kept is not None and not occurrences <= kept:
                continue
            next_states = {}
            touched = 0
            for key in occurrences:
                touched |= masks[key]
                for arm in support[key]:
                    label = (arm.reply, source.states[arm.destination].public)
                    next_states.setdefault(label, set()).add(arm.destination)
            children = tuple(frozenset(row) for row in next_states.values())
            moves.append(Move(cost, touched, children))
            pending.extend(children)
        graph[belief] = (all(closed[state] for state in belief), tuple(moves))
    return initial, graph


def depth_value(initial, graph, horizon):
    values = {belief: 0 if closed else inf for belief, (closed, _) in graph.items()}
    for _ in range(horizon):
        values = {
            belief: min([0 if closed else inf] + [
                move.price + max(values[child] for child in move.children)
                for move in moves
            ])
            for belief, (closed, moves) in graph.items()
        }
    return values[initial]


def reference(source, freeze, horizon, kept=None):
    """Direct bounded trees over full physical traces inside each visible branch."""

    def is_closed(last):
        state = source.states[last]
        included = [world for world, holds in product((0, 1), range(len(state.cells)))
                    if world in source.worlds[holds]
                    and state.cells[holds] == state.cells[state.admitted]]
        assert included
        return all(world == included[0] for world in included)

    def source_steps(last, action):
        before = source.states[last]
        key = (last, action)
        if action not in before.rights or key not in source.bodies:
            return {}
        if kept is not None and key not in kept:
            return {}
        possible = {}
        for arm in source.bodies[key]:
            if arm.weight <= 0:
                continue
            after = source.states[arm.destination]
            if freeze & EVIDENCE and before.admitted != after.admitted:
                return {}
            if freeze & REPRESENTATION and before.cells != after.cells:
                return {}
            if freeze & AUTHORITY and before.rights != after.rights:
                return {}
            possible.setdefault((after.public, arm.reply), []).append(arm.destination)
        return possible

    def tree(physical_paths, depth):
        if all(is_closed(path[-1]) for path in physical_paths):
            return 0
        if depth == 0:
            return inf
        best = inf
        for action in source.costs:
            next_paths = {}
            for path in physical_paths:
                possible = source_steps(path[-1], action)
                if not possible:
                    break
                for label, ends in possible.items():
                    next_paths.setdefault(label, []).extend(path + (end,) for end in ends)
            else:
                continuation = max(tree(tuple(paths), depth - 1) for paths in next_paths.values())
                best = min(best, source.costs[action] + continuation)
        return best

    return tree(((source.entry,),), horizon)


def greatest_cover(source_graph, receiving_graph):
    pairs = {
        (left, right)
        for left, right in product(source_graph, receiving_graph)
        if not source_graph[left][0] or receiving_graph[right][0]
    }
    while True:
        next_pairs = set()
        for left, right in pairs:
            if all(
                any(
                    receiving.price <= source.price
                    and receiving.touched & ~source.touched == 0
                    and all(
                        any((u, v) in pairs for u in source.children)
                        for v in receiving.children
                    )
                    for receiving in receiving_graph[right][1]
                )
                for source in source_graph[left][1]
            ):
                next_pairs.add((left, right))
        if next_pairs == pairs:
            return pairs
        pairs = next_pairs


def mixed_source(second_weight, permission):
    rights = frozenset(("send",)) if permission else frozenset()
    rows = {
        "root": State(0, (0, 1, 2), rights, "open"),
        "good": State(1, (0, 1, 2), rights, "done"),
        "mixed": State(1, (0, 1, 1), rights, "done"),
    }
    return Source(rows, {("root", "send"): (
        Arm("good", "ok"), Arm("mixed", "ok", second_weight),
    )}, {"send": 1}, (frozenset((0, 1)), frozenset((0,)), frozenset()))


def interpretation(mode):
    rights = frozenset(("visit",))
    if mode == "E":
        root = State(0, (0, 1), rights, "open")
        post = State(1, (0, 1), rights, "done")
        worlds = (frozenset((0, 1)), frozenset((0,)))
    else:
        root = State(0, (0, 0), rights, "open")
        post = State(0, (0, 1), rights, "done")
        worlds = (frozenset((0,)), frozenset((1,)))
    return Source({"root": root, "post": post}, {("root", "visit"): (Arm("post", "ok"),)},
                  {"visit": 1}, worlds)


def routing(reveal, same_repair, duplicate, idle):
    actions = {"setup": 1, "repair-left": 1, "repair-right": 1}
    if duplicate:
        actions["duplicate"] = 2
    if idle:
        actions["idle"] = 0
    rights = frozenset(actions)
    rows = {
        name: State(int(name == "closed"), (0, 1), rights, "done" if name == "closed" else "open")
        for name in ("root", "left", "right", "closed")
    }
    bodies = {("root", "setup"): (Arm("left", "left"), Arm("right", "right" if reveal else "left"))}
    bodies["left", "repair-left"] = (Arm("closed", "ok"),)
    bodies["right", "repair-left" if same_repair else "repair-right"] = (Arm("closed", "ok"),)
    if duplicate:
        bodies["left", "duplicate"] = (Arm("closed", "ok"),)
    if idle:
        bodies["root", "idle"] = (Arm("root", "wait"),)
    return Source(rows, bodies, actions, (frozenset((0, 1)), frozenset((0,))))


def main():
    scalar_replays = 0
    for weight, permitted in product((Fraction(0), Fraction(1, 7)), (False, True)):
        fixed = mixed_source(weight, permitted)
        support, masks, _ = compile_rows(fixed)
        if permitted:
            expected = EVIDENCE | (REPRESENTATION if weight > 0 else 0)
            assert masks["root", "send"] == expected
        else:
            assert not support
        for freeze in range(8):
            initial, graph = belief_graph(fixed, freeze)
            expected = 1 if permitted and masks["root", "send"] & freeze == 0 else inf
            assert depth_value(initial, graph, 1) == reference(fixed, freeze, 1) == expected
            scalar_replays += 1

    image = set()
    for mode in ("E", "R"):
        values = []
        for freeze in (EVIDENCE, REPRESENTATION):
            fixed = interpretation(mode)
            initial, graph = belief_graph(fixed, freeze)
            value = depth_value(initial, graph, 1)
            assert value == reference(fixed, freeze, 1)
            values.append(value)
            scalar_replays += 1
        image.add(tuple(values))
    assert image == {(inf, 1), (1, inf)}
    assert len(set(product(*[set(column) for column in zip(*image)])) - image) == 2

    kernels = [routing(*bits) for bits in product((False, True), repeat=4)]
    signature = []
    keep_replays = 0
    for source in kernels:
        values = []
        for freeze in range(8):
            initial, graph = belief_graph(source, freeze)
            value = depth_value(initial, graph, len(graph))
            assert value == reference(source, freeze, 3)
            values.append(value)
            scalar_replays += 1
        signature.append(tuple(values))
        admitted = tuple(compile_rows(source)[0])
        for bits in product((False, True), repeat=len(admitted)):
            kept = frozenset(key for key, bit in zip(admitted, bits) if bit)
            initial, graph = belief_graph(source, kept=kept)
            assert depth_value(initial, graph, len(graph)) == reference(source, 0, 3, kept)
            keep_replays += 1

    graphs = [belief_graph(source) for source in kernels]
    cover_count = 0
    for i, j in product(range(len(graphs)), repeat=2):
        left, left_graph = graphs[i]
        right, right_graph = graphs[j]
        if (left, right) in greatest_cover(left_graph, right_graph):
            assert all(r <= l for l, r in zip(signature[i], signature[j]))
            cover_count += 1

    def covered(left, right):
        start, lhs = belief_graph(left)
        end, rhs = belief_graph(right)
        return (start, end) in greatest_cover(lhs, rhs)

    shared = routing(True, True, False, False)
    history_local = routing(True, False, False, False)
    hidden_alias = routing(False, False, False, False)
    nonprogress = routing(True, True, False, True)
    assert covered(shared, history_local) and covered(history_local, shared)
    assert not covered(shared, hidden_alias)
    assert not covered(nonprogress, shared)
    for freeze in range(8):
        assert reference(nonprogress, freeze, 3) == reference(shared, freeze, 3)

    print(f"verified {scalar_replays} exact freeze values, {keep_replays} occurrence masks, "
          f"and {cover_count} directed covers across {len(kernels) ** 2} candidate graph pairs")


if __name__ == "__main__":
    main()
