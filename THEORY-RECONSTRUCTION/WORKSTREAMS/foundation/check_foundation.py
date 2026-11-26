"""Run finite falsification checks for reconstructed D-35 claims.

All fixtures are inert tables. This runner uses Python's standard library.
"""
from collections import defaultdict, deque
from collections.abc import Hashable, Iterator
from dataclasses import dataclass
from functools import cache
from itertools import product
import json
from math import inf
from random import Random

Partition = frozenset[frozenset[Hashable]]
Support = tuple[tuple[Hashable, Hashable], ...]
Belief = frozenset[Hashable]
FREEZES = ("", "E", "R", "A", "ER", "EA", "RA", "ERA")


@dataclass(frozen=True)
class State:
    history: Hashable
    partition: Partition
    authority: frozenset[str]
    observation: Hashable
    menu: dict[str, Support]


@dataclass(frozen=True)
class Game:
    root: Hashable
    closed: dict[Hashable, Hashable]
    observations: dict[Hashable, Hashable]
    menus: dict[Hashable, dict[str, tuple[frozenset[str], Support]]]
    costs: dict[str, int]


def cell_partition(history_carrier, *blocks) -> Partition:
    block_set = {frozenset(block) for block in blocks}
    covered = set().union(*block_set)
    assert covered <= set(history_carrier)
    return frozenset(block_set | {frozenset({h}) for h in history_carrier if h not in covered})


def compile_pc(states, root, costs, compatibility, labels) -> Game:
    closed = {}
    menus = {}
    for name, state in states.items():
        carrier = set().union(*state.partition)
        assert carrier == compatibility.keys()
        assert sum(map(len, state.partition)) == len(carrier)
        cell, = (block for block in state.partition if state.history in block)
        world_image = set().union(*(compatibility[h] for h in cell))
        assert world_image
        values = {labels[w] for w in world_image}
        if len(values) == 1:
            closed[name] = next(iter(values))
        menus[name] = {}
        for action, support in state.menu.items():
            assert support and costs[action] >= 0 and "run" in state.authority
            touch = set()
            for destination, _ in support:
                endpoint = states[destination]
                for bit, field in (("E", "history"), ("R", "partition"), ("A", "authority")):
                    if getattr(state, field) != getattr(endpoint, field):
                        touch.add(bit)
            menus[name][action] = (frozenset(touch), support)
    return Game(root, closed, {name: s.observation for name, s in states.items()}, menus, costs)


def belief_graph(game: Game, freeze: str):
    allowed = {
        s: {a: support for a, (touch, support) in options.items() if not touch.intersection(freeze)}
        for s, options in game.menus.items()
    }
    root = frozenset({game.root})
    graph: dict[Belief, list[tuple[int, tuple[Belief, ...]]]] = {}
    agenda = deque([root])
    discovered = {root}
    while agenda:
        belief = agenda.popleft()
        options = []
        graph[belief] = options
        if belief.issubset(game.closed):
            continue
        common = set.intersection(*(set(allowed[s]) for s in belief))
        for action in sorted(common):
            groups = defaultdict(set)
            for s in belief:
                for destination, outcome in allowed[s][action]:
                    groups[(outcome, game.observations[destination])].add(destination)
            children = tuple(frozenset(group) for group in groups.values())
            options.append((game.costs[action], children))
            for child in children:
                if child not in discovered:
                    discovered.add(child)
                    agenda.append(child)
    return root, graph


def value(game: Game, freeze: str) -> float:
    root, graph = belief_graph(game, freeze)
    previous = {b: 0 if b.issubset(game.closed) else inf for b in graph}
    for _ in graph:
        updated = {
            b: 0 if b.issubset(game.closed) else min(
                (cost + max(previous[child] for child in children)
                 for cost, children in actions),
                default=inf,
            )
            for b, actions in graph.items()
        }
        if updated == previous:
            break
        previous = updated
    return previous[root]


def simple_tree_minimum(game: Game, freeze: str) -> float:
    """Reference enumeration of every simple belief path branch choice."""
    root, graph = belief_graph(game, freeze)

    @cache
    def descend(belief: Belief, ancestors: frozenset[Belief]) -> float:
        if belief.issubset(game.closed):
            return 0
        if belief in ancestors:
            return inf
        totals = []
        for price, children in graph[belief]:
            suffixes = [descend(child, ancestors | {belief}) for child in children]
            totals.append(price + max(suffixes))
        return min(totals, default=inf)

    return descend(root, frozenset())


def paired_witness(role: str, gap: int, backup: bool) -> Game:
    compatibility = {"u": {0, 1}, "star": set(), "h0": {0}, "h1": {1}, "b0": {0}, "b1": {1}}
    identity = cell_partition(compatibility)
    shared = cell_partition(compatibility, {"h0", "h1"})
    refinement_start = cell_partition(compatibility, {"star", "h0", "h1"})
    start_history, start_partition = "u", identity
    if role == "ER":
        start_partition = shared
    elif role == "R":
        start_history, start_partition = "star", refinement_start
    authority = frozenset({"run"})
    menu = {"q": (("s0", 0), ("s1", 1))}
    costs = {"q": 1}
    if backup:
        menu["backup"] = (("b0", 0), ("b1", 1))
        costs["backup"] = 1 + gap
    states = {"entry": State(start_history, start_partition, authority, "entry", menu)}
    for i in (0, 1):
        if role == "R":
            history, paired = "star", cell_partition(compatibility, {"star", f"h{i}"})
        else:
            history, paired = f"h{i}", identity
        states[f"s{i}"] = State(history, paired, authority, "finished", {})
        if backup:
            states[f"b{i}"] = State(f"b{i}", start_partition, authority, "finished", {})
    return compile_pc(states, "entry", costs, compatibility, {0: 0, 1: 1})


def visible_projection(game: Game):
    return game.root, game.closed, game.observations, game.costs, {
        s: {q: support for q, (_, support) in menu.items()} for s, menu in game.menus.items()
    }


def repair_game(reveal_in_probe: bool, *, rename=False, duplicate=False) -> Game:
    """Two hidden states with a repair that must depend on their test signal."""
    none = frozenset()
    e = frozenset({"E"})
    menus = {"root": {"setup": (none, (("u0", "start"), ("u1", "start")))}}
    observations = {"root": "root", "trap": "terminal"}
    closed = {"done0": 0, "done1": 1}
    menus["trap"] = {}
    for i in (0, 1):
        observed_i = i if reveal_in_probe else 0
        options = ((f"v{i}", observed_i),)
        if i == 0 and duplicate:
            options += (("v0-copy", observed_i),)
        menus[f"u{i}"] = {"probe": (none, options)}
        menus[f"v{i}"] = {
            f"repair{i}": (e, ((f"done{i}", "end"),)),
            f"repair{1-i}": (none, (("trap", "end"),)),
        }
        menus[f"done{i}"] = {}
        observations[f"u{i}"] = "setup"
        observations[f"v{i}"] = "probed"
        observations[f"done{i}"] = "terminal"
    if duplicate:
        menus["v0-copy"] = dict(menus["v0"])
        observations["v0-copy"] = "probed"
    costs = {"setup": 1, "probe": 1, "repair0": 1, "repair1": 1}
    if rename:
        menus = {
            s: {f"mate-{a}": (touch, tuple((u, ("mate", o)) for u, o in support))
                for a, (touch, support) in menu.items()}
            for s, menu in menus.items()
        }
        costs = {f"mate-{a}": cost for a, cost in costs.items()}
    return Game("root", closed, observations, menus, costs)


def statewise_attractor(game: Game, freeze: str):
    result = set(game.closed)
    while True:
        update = result | {
            s for s, menu in game.menus.items()
            if any(
                not touch.intersection(freeze)
                and all(endpoint in result for endpoint, _ in support)
                for touch, support in menu.values()
            )
        }
        if update == result:
            return result
        result = update


def partitions(size: int) -> Iterator[tuple[int, ...]]:
    if size == 1:
        yield (0,)
        return
    for prior in partitions(size - 1):
        for label in range(max(prior) + 2):
            yield prior + (label,)


def p1_check() -> int:
    target = (0, 1, 0, 1)  # h0, h1, w0, w1.
    tested = 0
    for quotient in partitions(len(target)):
        fibers = [
            {y for i, y in enumerate(target) if quotient[i] == cell}
            for cell in quotient
        ]
        faithful = fibers[:2] == [{0, 1}, {0, 1}] and fibers[2:] == [{0}, {1}]
        discriminating = quotient[0] != quotient[1]
        assert not (faithful and discriminating)
        tested += 1
    assert tested == 15
    return tested


def parity_game(dimension: int, target=None) -> Game:
    histories = tuple(product((None, 0, 1), repeat=dimension))
    worlds = tuple(product((0, 1), repeat=dimension))
    compatibility = {
        h: {x for x in worlds if all(v is None or v == x[j] for j, v in enumerate(h))}
        for h in histories
    }
    labels = {w: (sum(w) % 2 if target is None else target(w)) for w in worlds}
    authorities = frozenset({"run"})
    count_masks = 1 << dimension
    representations = {}
    for mask in range(count_masks):
        grouped = defaultdict(set)
        for history in histories:
            key = tuple((v is not None, v if mask & (1 << j) else None)
                        for j, v in enumerate(history))
            grouped[key].add(history)
        representations[mask] = frozenset(frozenset(cell) for cell in grouped.values())

    states = {}
    costs = {f"{resource}{j}": 1 for resource in ("e", "r") for j in range(dimension)}
    for h, mask in product(histories, range(count_masks)):
        menu = {}
        for j, bit in enumerate(h):
            if bit is None:
                menu[f"e{j}"] = tuple(((h[:j] + (v,) + h[j + 1:], mask), v) for v in (0, 1))
            if not mask & (1 << j):
                menu[f"r{j}"] = (((h, mask | (1 << j)), "exposed"),)
        states[(h, mask)] = State(h, representations[mask], authorities, (h, mask), menu)
    return compile_pc(states, ((None,) * dimension, 0), costs, compatibility, labels)


def mixed_support_game() -> Game:
    compatibility = {"u": {0, 1}, "h0": {0}, "h1": {1}, "d0": set(), "d1": set()}
    partition = cell_partition(compatibility)
    authority = frozenset({"run"})
    changed = cell_partition(compatibility, {"d0", "d1"})
    states = {
        "entry": State("u", partition, authority, "entry", {"q": (("e", "ok"), ("er", "ok"))}),
        "e": State("h0", partition, authority, "finished", {}),
        "er": State("h1", changed, authority, "finished", {}),
    }
    return compile_pc(states, "entry", {"q": 1}, compatibility, {0: 0, 1: 1})


def generated_games(seed=528, instances=120):
    rng = Random(seed)
    for _ in range(instances):
        physical = (0, 1, 2)
        menus = {}
        for state in physical:
            rows = {}
            for action in ("a", "b"):
                if rng.getrandbits(1):
                    touch = frozenset(r for r in "ER" if rng.getrandbits(1))
                    support = tuple((target, rng.randrange(2))
                                    for target in rng.sample(physical, rng.randint(1, len(physical))))
                    rows[action] = (touch, support)
            menus[state] = rows
        yield Game(
            0,
            {s: s for s in physical if rng.getrandbits(1)},
            {s: rng.randrange(2) for s in physical},
            menus,
            {"a": rng.randrange(3), "b": rng.randrange(3)},
        )


def rectangular_and_target_checks() -> tuple[int, int]:
    actions = {"left", "middle", "right"}
    price = {"left": 1, "middle": 3, "right": 4}
    order = sorted(actions)
    masks = [
        frozenset(q for q, blocked in zip(order, flags, strict=True) if blocked)
        for flags in product((False, True), repeat=len(actions))
    ]
    one_step = {mask: min((price[q] for q in actions - mask), default=inf) for mask in masks}
    families = 0
    for flags in product((False, True), repeat=len(masks)):
        family = [m for m, included in zip(masks, flags, strict=True) if included]
        if not family:
            continue
        definite = frozenset.intersection(*family)
        possible = frozenset.union(*family)
        attained = {one_step[m] for m in family}
        assert one_step[definite] <= min(attained) <= max(attained) <= one_step[possible]
        if definite in family:
            assert one_step[definite] == min(attained)
        if possible in family:
            assert one_step[possible] == max(attained)
        families += 1
    xor_family = [frozenset({"left", "right"}), frozenset({"middle", "right"})]
    assert max(one_step[m] for m in xor_family) == 3
    assert one_step[frozenset.union(*xor_family)] == inf

    constant = parity_game(2, lambda w: 0)
    first_bit = parity_game(2, lambda w: w[0])
    complete = parity_game(2, lambda w: w)
    relabeled = parity_game(2, lambda w: tuple(1 - bit for bit in w))
    for freeze in FREEZES:
        assert value(constant, freeze) <= value(first_bit, freeze) <= value(complete, freeze)
        assert value(complete, freeze) == value(relabeled, freeze)
    return families, len(FREEZES)


def main() -> None:
    pair_coordinates = 0
    for role in ("ER", "R"):
        for gap, backup in product((1, 4, 7), (False, True)):
            base, changed = (paired_witness(tag, gap, backup) for tag in ("E", role))
            assert visible_projection(base) == visible_projection(changed)
            assert base.menus["entry"]["q"][0] == {"E"}
            assert changed.menus["entry"]["q"][0] == set(role)
            assert value(base, "R") == 1
            assert value(changed, "R") == (1 + gap if backup else inf)
            assert value(base, "") == value(changed, "") == 1
            for variant in (base, changed):
                for freeze in FREEZES:
                    assert simple_tree_minimum(variant, freeze) == value(variant, freeze)
                    pair_coordinates += 1

    reveal, alias = repair_game(True), repair_game(False)
    mate = repair_game(True, rename=True, duplicate=True)
    assert value(reveal, "") == 3 and value(alias, "") == inf
    assert "root" in statewise_attractor(alias, "R") and value(alias, "R") == inf
    for freeze in FREEZES:
        assert value(reveal, freeze) == value(mate, freeze)

    quotient_count = p1_check()
    mixed = mixed_support_game()
    assert mixed.menus["entry"]["q"][0] == {"E", "R"}
    assert value(mixed, "") == 1 and value(mixed, "R") == inf

    loop = Game("s", {}, {"s": 0}, {"s": {"wait": (frozenset(), (("s", 0),))}}, {"wait": 0})
    assert value(loop, "") == simple_tree_minimum(loop, "") == inf

    parity_count = 0
    parity_states = 0
    for d in (1, 2, 3):
        game = parity_game(d)
        parity_states += len(game.menus)
        for menu in game.menus.values():
            assert all(touch == {name[0].upper()} for name, (touch, _) in menu.items())
        for freeze in FREEZES:
            answer = inf if set(freeze) & {"E", "R"} else 2 * d
            assert value(game, freeze) == answer
            parity_count += 1

    random_coords = 0
    for game in generated_games():
        for freeze in FREEZES:
            assert value(game, freeze) == simple_tree_minimum(game, freeze)
            random_coords += 1

    rectangular_families, target_freezes = rectangular_and_target_checks()
    print(json.dumps({
        "paired_witness_freeze_coordinates": pair_coordinates,
        "equivariant_history_transport_freezes": len(FREEZES),
        "single_history_quotients_checked": quotient_count,
        "parity_states": parity_states,
        "mask_families_checked": rectangular_families,
        "target_refinement_and_relabeling_freezes": target_freezes,
        "parity_freeze_coordinates": parity_count,
        "finite_game_coordinates": random_coords,
        "nonuniform_outcome_renaming_refuted": True,
        "statewise_attractor_without_policy_sufficiency_refuted": True,
        "same_signal_hidden_touch_blocks_whole_action": True,
        "open_zero_cost_cycle_has_no_proper_closer": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
