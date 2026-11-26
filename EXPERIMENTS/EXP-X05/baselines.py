"""Capped explicit-table baselines for weighted uniform audit synthesis."""

from fractions import Fraction
from heapq import heappop, heappush
from itertools import product
from math import prod
from random import Random
from time import perf_counter

from domain import FREEZES
from reference import (
    RejectedSource, compatible_modes, completion_cost, independent_rows, policy_signature, source_ok,
)


class BaselineLimit(RuntimeError):
    pass


def time_check(deadline):
    if deadline is not None and perf_counter() >= deadline:
        raise BaselineLimit("deadline")


def encode(indices):
    return sum(2 ** index for index in indices)


def materialize(case, budgets, stats, deadline):
    source_ok(case)
    modes = tuple(tuple(compatible_modes(stage)) for stage in case.stages)
    count = prod(map(len, modes))
    stats["compatible_count"] = count
    time_check(deadline)
    if not count:
        return (), ()
    if count > budgets["explicit_completions"]:
        raise BaselineLimit("completion-cap")
    freeze = FREEZES.index(case.freeze)
    terminal = policy_signature(case.terminal, ())
    stages = tuple(independent_rows(stage, group) for stage, group in zip(
        case.stages, modes, strict=True,
    ))
    stats["compiled_modes"] = sum(map(len, stages))
    rows = []
    for choices in product(*stages):
        time_check(deadline)
        amount = completion_cost(choices, terminal, freeze)
        target = amount is not None and amount <= case.budget
        answers = encode(i for i, answer in enumerate(
            answer for row in choices for answer in row.answers
        ) if answer)
        rows.append((tuple(row.mode for row in choices), target, answers))
        stats["materialized_completions"] += 1
        stats["explicit_rows"] += 1
    return tuple(rows), tuple(len(stage.queries) for stage in case.stages)


def collision(rows, mask, state, budgets, deadline):
    cells = {}
    for row in rows:
        if state["row_visits"] >= budgets["partition_row_visits"]:
            raise BaselineLimit("partition-row-cap")
        state["row_visits"] += 1
        if state["row_visits"] % 128 == 0:
            time_check(deadline)
        observed = row[2] & mask
        prior = cells.setdefault(observed, row)
        if prior[1] != row[1]:
            return prior[0], row[0]
    return None


def subsets_by_price(prices):
    """Enumerate each subset once in increasing total acquisition price."""
    ranked = sorted(range(len(prices)), key=lambda i: (prices[i], i))
    queue = [(0, 0, -1)]
    while queue:
        price, mask, last = heappop(queue)
        yield price, mask
        following = last + 1
        if following >= len(prices):
            continue
        q = ranked[following]
        heappush(queue, (price + prices[q], mask | 1 << q, following))
        if last >= 0:
            added = ranked[last]
            heappush(queue, (price + prices[q] - prices[added],
                             (mask ^ (1 << added)) | (1 << q), following))


def subset_indices(mask, width):
    return tuple(q for q in range(width) if mask & (1 << q))


def direct_optimum(rows, prices, stats, budgets, deadline):
    for price, mask in subsets_by_price(prices):
        time_check(deadline)
        if stats["query_subsets"] >= budgets["query_subsets"]:
            raise BaselineLimit("query-subset-cap")
        stats["query_subsets"] += 1
        if collision(rows, mask, stats, budgets, deadline) is None:
            return price, subset_indices(mask, len(prices))
    raise AssertionError("whole-interface acceptance was already checked")


def eager_optimum(rows, prices, widths, stats, budgets, deadline):
    positive = tuple(row for row in rows if row[1])
    negative = tuple(row for row in rows if not row[1])
    unique = set()
    for left in positive:
        for right in negative:
            if stats["opposite_pairs"] >= budgets["eager_opposite_pairs"]:
                raise BaselineLimit("opposite-pair-cap")
            stats["opposite_pairs"] += 1
            if stats["opposite_pairs"] % 128 == 0:
                time_check(deadline)
            edge = left[2] ^ right[2]
            if not edge:
                return None, (), (left[0], right[0])
            unique.add(edge)
    stats["distinct_pair_edges"] = len(unique)

    # Recombination gives a necessary single-stage edge inside every global edge.
    chosen = []
    offset = 0
    for width in widths:
        time_check(deadline)
        local_mask = ((1 << width) - 1) << offset
        local_edges = {edge >> offset for edge in unique if edge & local_mask == edge}
        if local_edges:
            patterns = prices[offset:offset + width]
            _, selected = next(
                (price, choice) for price, choice in subsets_by_price(patterns)
                if all(choice & edge for edge in local_edges)
            )
            chosen.extend(offset + q for q in subset_indices(selected, width))
        offset += width
    indices = tuple(chosen)
    return sum(prices[q] for q in indices), indices, None


def solve_explicit(case, budgets, *, eager, seconds=None):
    deadline = None if seconds is None else perf_counter() + seconds
    stats = {
        "compiled_modes": 0, "materialized_completions": 0, "explicit_rows": 0,
        "row_visits": 0, "opposite_pairs": 0, "query_subsets": 0,
        "distinct_pair_edges": None, "compatible_count": None,
    }
    result = {
        "status": "UNRESOLVED", "initial": None, "reason": None, "value": None,
        "cost": None, "selected": (), "witness": None,
        "lower_bound": None, "upper_bound": None,
        "counters": stats,
    }
    try:
        rows, widths = materialize(case, budgets, stats, deadline)
        if not rows:
            return {**result, "status": "INCONSISTENT", "initial": "INCONSISTENT"}
        if all(row[1] == rows[0][1] for row in rows):
            return {
                **result, "status": "IDENTIFIED", "initial": "IDENTIFIED",
                "cost": 0, "value": rows[0][1], "lower_bound": 0, "upper_bound": 0,
            }
        result["initial"] = "UNDERIDENTIFIED"
        prices = tuple(query.price for stage in case.stages for query in stage.queries)
        if eager:
            optimum, selected, witness = eager_optimum(rows, prices, widths, stats, budgets, deadline)
        else:
            witness = collision(rows, (1 << len(prices)) - 1, stats, budgets, deadline)
            if witness is None:
                optimum, selected = direct_optimum(rows, prices, stats, budgets, deadline)
        if witness is not None:
            return {**result, "status": "AUDIT_INACCESSIBLE", "witness": witness}
        return {
            **result, "status": "CERTIFIED", "cost": optimum, "selected": selected,
            "lower_bound": optimum, "upper_bound": optimum,
        }
    except BaselineLimit as error:
        return {**result, "reason": str(error)}
    except RejectedSource as error:
        return {**result, "reason": "unsupported", "note": str(error)}


def unresolved_pairs(rows, mask):
    cells = {}
    for _, target, answers in rows:
        counts = cells.setdefault(answers & mask, [0, 0])
        counts[int(target)] += 1
    return sum(low * high for low, high in cells.values())


def baseline_queries(ref, permutations, seed):
    """Additional information-acquisition comparisons on an already enumerated small table."""
    rows = []
    for choices in product(*ref.stages):
        amount = completion_cost(choices, ref.terminal, ref.index)
        rows.append((
            (), amount is not None and amount <= ref.case.budget,
            encode(j for j, answer in enumerate(answer for row in choices for answer in row.answers)
                   if answer),
        ))
    weights = ref.queries
    if not rows:
        return None
    unresolved = unresolved_pairs(rows, 0)
    mask = 0
    greedy = []
    while unresolved and len(greedy) < len(weights):
        choices = []
        for q, cost in enumerate(weights):
            if mask & 1 << q:
                continue
            remaining = unresolved_pairs(rows, mask | 1 << q)
            choices.append((-Fraction(unresolved - remaining, cost), cost, q, remaining))
        _, _, q, unresolved = min(choices)
        greedy.append(q)
        mask |= 1 << q
    rng = Random(seed + ref.case.seed)
    orders = []
    for _ in range(permutations):
        sequence = list(range(len(weights)))
        rng.shuffle(sequence)
        selected = []
        for q in sequence:
            if not unresolved_pairs(rows, encode(selected)):
                break
            selected.append(q)
        orders.append({
            "selected": tuple(selected),
            "cost": sum(weights[q] for q in selected)
            if not unresolved_pairs(rows, encode(selected)) else None,
        })
    return {
        "greedy": {"selected": tuple(greedy),
                   "cost": sum(weights[q] for q in greedy) if not unresolved else None},
        "random": tuple(orders),
        "query_all": {
            "cost": sum(weights),
            "sufficient": not unresolved_pairs(rows, (1 << len(weights)) - 1),
        },
    }
