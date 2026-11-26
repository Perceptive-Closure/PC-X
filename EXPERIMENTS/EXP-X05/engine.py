"""Paired budget analysis and lazy exact minimum-cost semantic audits."""

from dataclasses import dataclass, field
from itertools import combinations
from math import prod
from time import perf_counter

from domain import CLASSES, FREEZES, HISTORIES, Unsupported, validate_source


class Limit(RuntimeError):
    """A guarded search ended before it could establish its conclusion."""


@dataclass
class Guard:
    cap: int
    deadline: float | None
    steps: int = 0

    def charge(self, count=1):
        if self.deadline is not None and perf_counter() >= self.deadline:
            raise Limit("deadline")
        if self.steps + count > self.cap:
            raise Limit("step-cap")
        self.steps += count


@dataclass(frozen=True)
class Variant:
    facts: int
    answers: int
    signature: tuple[int | None, ...]


@dataclass
class Local:
    rows: tuple[Variant, ...]
    costs: tuple[int, ...]
    query_offset: int
    options: dict = field(default_factory=dict)


def bit_positions(mask):
    while mask:
        bit = mask & -mask
        yield bit.bit_length() - 1
        mask ^= bit


def with_bits(indices):
    return sum(1 << index for index in indices)


def finite_key(cost):
    return cost is None, 0 if cost is None else cost


def active(facts, fact):
    return fact is not None and bool(facts & (1 << fact))


def partition(labels):
    classes = {}
    for history, label in enumerate(labels):
        classes.setdefault(label, []).append(history)
    return frozenset(tuple(class_) for class_ in classes.values())


def profile(node, facts):
    gain_e, gain_r, gain_a = (active(facts, fact) for fact in node.effects)
    history = 1 if gain_e else node.history
    labels = (0, 0, 1, 2, 3) if gain_r else node.labels
    authority = frozenset((*node.authority, "reserve")) if gain_a else frozenset(node.authority)
    return history, partition(labels), authority


def kernel(graph, facts):
    profiles = tuple(profile(node, facts) for node in graph.nodes)
    closure = []
    for history, certificate, _ in profiles:
        fiber = next(set(cell) for cell in certificate if history in cell)
        classes = {name for name, compatible in CLASSES if fiber.intersection(compatible)}
        if not classes:
            raise Unsupported("empty compatible class fiber")
        closure.append(len(classes) == 1)
    if graph.join is not None and any(closure):
        raise Unsupported("an internal stage closes before the common join")

    compiled = []
    for origin, node in enumerate(graph.nodes):
        actions = []
        for action in node.actions:
            successors = tuple(branch.successor for branch in action.support)
            difference = frozenset(
                resource for position, resource in enumerate("ERA")
                if any(profiles[origin][position] != profiles[dest][position] for dest in successors)
            )
            actions.append((action.price, successors, difference))
        compiled.append(tuple(actions))
    return tuple(closure), tuple(compiled)


def graph_signature(graph, facts):
    closed, nodes = kernel(graph, facts)
    costs = []
    for freeze in FREEZES:
        values = [None] * len(nodes)
        removed = frozenset() if freeze == "none" else frozenset(freeze)
        for origin in reversed(range(len(nodes))):
            if closed[origin] or origin == graph.join:
                values[origin] = 0
                continue
            viable = []
            for price, successors, touch in nodes[origin]:
                options = tuple(values[dest] for dest in successors)
                if not touch & removed and all(cost is not None for cost in options):
                    viable.append(price + max(options))
            if viable:
                values[origin] = min(viable)
        costs.append(values[0])
    return tuple(costs)


def local_mode(stage, facts):
    return all(any(
        bool(facts & (1 << (abs(literal) - 1))) == (literal > 0) for literal in clause
    ) for clause in stage.clauses)


def compile_contract(case, guard, counters):
    validate_source(case)
    guard.charge()
    stages = []
    offset = 0
    terminal = graph_signature(case.terminal, 0)
    for stage in case.stages:
        for boundary in (stage.graph.nodes[0], stage.graph.nodes[stage.graph.join]):
            if any(fact is not None for fact in boundary.effects):
                raise Unsupported("stage boundary profiles must be fixed")
            if profile(boundary, 0) != profile(case.terminal.nodes[0], 0):
                raise Unsupported("stage boundaries must share the terminal entry profile")
        rows = []
        for facts in range(1 << stage.width):
            guard.charge()
            if not local_mode(stage, facts):
                continue
            signature = graph_signature(stage.graph, facts)
            answers = with_bits(
                i for i, query in enumerate(stage.queries)
                if (query.facts & facts).bit_count() % 2
            )
            rows.append(Variant(facts, answers, signature))
            counters["compiled_modes"] += 1
        stages.append(Local(tuple(rows), tuple(query.price for query in stage.queries), offset))
        offset += len(stage.queries)
    return tuple(stages), terminal


def attainable_costs(stages, terminal_cost, freeze_index):
    if not all(stage.rows for stage in stages):
        return (), False
    if terminal_cost is None:
        return (), True
    totals = 1 << terminal_cost
    has_inf = False
    for stage in stages:
        costs = {row.signature[freeze_index] for row in stage.rows}
        has_inf |= None in costs
        following = 0
        for cost in costs - {None}:
            following |= totals << cost
        totals = following
    return tuple(bit_positions(totals)), has_inf


def cost_at(stages, facts, terminal, index):
    if terminal is None:
        return None
    total = terminal
    for stage, mode in zip(stages, facts, strict=True):
        row = next(row for row in stage.rows if row.facts == mode)
        cost = row.signature[index]
        if cost is None:
            return None
        total += cost
    return total


def paired_options(stage, selected, freeze_index, cap):
    local_mask = (selected >> stage.query_offset) & ((1 << len(stage.costs)) - 1)
    if local_mask not in stage.options:
        cells = {}
        for row in stage.rows:
            cells.setdefault(row.answers & local_mask, []).append(row)
        options = {}
        for rows in cells.values():
            lo = min(rows, key=lambda row: finite_key(row.signature[freeze_index]))
            hi = max(rows, key=lambda row: finite_key(row.signature[freeze_index]))
            low_cost, high_cost = lo.signature[freeze_index], hi.signature[freeze_index]
            left = cap if low_cost is None else min(cap, low_cost)
            right = cap if high_cost is None else min(cap, high_cost)
            options.setdefault((left, right), (lo, hi))
        stage.options[local_mask] = tuple(
            (left, right, lo, hi) for (left, right), (lo, hi) in options.items()
        )
    return stage.options[local_mask]


def dominance_prune(states, counters):
    if len(states) < 2:
        return states
    frontier = {}
    highest = -1
    for pair in sorted(states, key=lambda pair: (pair[0], -pair[1])):
        if pair[1] > highest:
            frontier[pair] = states[pair]
            highest = pair[1]
    counters["state_prunes"] += len(states) - len(frontier)
    return frontier


def localize(stages, path, case, terminal, freeze_index, counters):
    full = []
    while path is not None:
        path, lo, hi = path
        full.append((lo, hi))
    full.reverse()
    counters["reconstructed_completions"] += 2
    before = [lo.facts for lo, _ in full]
    current = terminal + sum(lo.signature[freeze_index] for lo, _ in full)
    for stage_index, (lo, hi) in enumerate(full):
        local_high = hi.signature[freeze_index]
        after = (None if local_high is None
                 else current + local_high - lo.signature[freeze_index])
        if after is None or after > case.budget:
            previous, changed = tuple(before), list(before)
            changed[stage_index] = hi.facts
            edge = (lo.answers ^ hi.answers) << stages[stage_index].query_offset
            counters["reconstructed_completions"] += 2
            return {
                "stage": stage_index,
                "left": previous,
                "right": tuple(changed),
                "edge": tuple(bit_positions(edge)),
                "costs": (current, after),
            }
        before[stage_index] = hi.facts
        current = after
    raise AssertionError("a paired disagreement must cross the threshold")


def disagreement(case, stages, terminal, freeze_index, selected, guard, counters, dominance):
    counters["oracle_calls"] += 1
    guard.charge()
    if terminal is None or terminal > case.budget:
        return None
    cap = case.budget + 1
    options = tuple(paired_options(stage, selected, freeze_index, cap) for stage in stages)
    if all(left == right for table in options for left, right, _, _ in table):
        return None
    frontier = {(terminal, terminal): None}
    for table in options:
        next_states = {}
        for (spent_left, spent_right), path in frontier.items():
            guard.charge(len(table))
            counters["pair_transitions"] += len(table)
            for left, right, lo, hi in table:
                total_left = spent_left + left
                if total_left <= case.budget:
                    pair = (total_left, min(cap, spent_right + right))
                    if pair not in next_states:
                        next_states[pair] = (path, lo, hi)
        counters["peak_pair_states"] = max(counters["peak_pair_states"], len(next_states))
        if not next_states:
            return None
        frontier = dominance_prune(next_states, counters) if dominance else next_states
    for (_, high), path in frontier.items():
        if high == cap:
            return localize(stages, path, case, terminal, freeze_index, counters)
    return None


def best_transversal(stages, edges, guard, counters):
    found = 0
    total = 0
    counters["optimizer_calls"] += 1
    for stage, discovered in zip(stages, edges, strict=True):
        if not discovered:
            continue
        width = len(stage.costs)
        best = None
        for size in range(1, width + 1):
            for indices in combinations(range(width), size):
                guard.charge()
                counters["optimizer_searches"] += 1
                mask = with_bits(indices)
                if all(mask & edge for edge in discovered):
                    prospect = sum(stage.costs[i] for i in indices), indices
                    if best is None or prospect < best:
                        best = prospect
        cost, indices = best
        found |= with_bits(indices) << stage.query_offset
        total += cost
    return found, total


def empty_counters():
    return dict.fromkeys((
        "compiled_modes", "materialized_completions", "witness_completions",
        "reconstructed_completions", "oracle_calls", "pair_transitions", "state_prunes",
        "peak_pair_states", "optimizer_calls", "optimizer_searches", "explicit_rows",
        "opposite_pairs", "query_subsets",
    ), 0)


def solve_symbolic(case, budgets, *, dominance=True, seconds=None):
    step_cap = budgets["symbolic_steps"] if case.step_cap is None else case.step_cap
    wall_seconds = seconds if case.deadline is None else case.deadline
    deadline = None if wall_seconds is None else perf_counter() + wall_seconds
    guard = Guard(step_cap, deadline)
    counters = empty_counters()
    result = {
        "status": "UNRESOLVED", "initial": None, "reason": None,
        "value": None, "cost": None, "lower_bound": None, "upper_bound": None,
        "selected": (), "rounds": [], "feasibility": None,
        "compatible_count": None, "finite_costs": None, "infinity": None,
        "counters": counters,
    }
    witnesses = set()
    try:
        stages, terminal = compile_contract(case, guard, counters)
        result["compatible_count"] = prod(len(stage.rows) for stage in stages)
        if not result["compatible_count"]:
            result.update(status="INCONSISTENT", initial="INCONSISTENT",
                          reason="empty-local-evidence",
                          empty_stage=next(i for i, stage in enumerate(stages) if not stage.rows))
            return result
        representative = tuple(stage.rows[0].facts for stage in stages)
        result["feasibility"] = representative
        witnesses.add(representative)
        freeze_index = FREEZES.index(case.freeze)
        terminal_cost = terminal[freeze_index]
        result["finite_costs"], result["infinity"] = attainable_costs(
            stages, terminal_cost, freeze_index,
        )
        edges = [set() for _ in stages]
        while True:
            selected, cost = best_transversal(stages, edges, guard, counters)
            result["lower_bound"] = cost
            witness = disagreement(
                case, stages, terminal_cost, freeze_index, selected, guard, counters, dominance,
            )
            indices = tuple(bit_positions(selected))
            result["rounds"].append({"selected": indices, "bound": cost, "witness": witness})
            if witness is None:
                if result["initial"] is None:
                    actual = cost_at(stages, representative, terminal_cost, freeze_index)
                    result.update(status="IDENTIFIED", initial="IDENTIFIED",
                                  value=actual is not None and actual <= case.budget)
                else:
                    result["status"] = "CERTIFIED"
                result.update(cost=cost, upper_bound=cost, selected=indices)
                return result
            witnesses.update((witness["left"], witness["right"]))
            result["initial"] = "UNDERIDENTIFIED"
            if not witness["edge"]:
                result.update(status="AUDIT_INACCESSIBLE", reason="whole-interface-collision")
                return result
            i = witness["stage"]
            edge = with_bits(witness["edge"]) >> stages[i].query_offset
            if edge & (selected >> stages[i].query_offset) or edge in edges[i]:
                raise AssertionError("the oracle must discover a fresh unhit edge")
            edges[i].add(edge)
    except Limit as error:
        result["reason"] = str(error)
        return result
    except Unsupported as error:
        result.update(reason="unsupported", note=str(error))
        return result
    finally:
        counters["witness_completions"] = len(witnesses)
        counters["work_steps"] = guard.steps
