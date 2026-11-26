"""Minimax acquisition and deterministic comparator policies."""

from dataclasses import dataclass
from fractions import Fraction
from functools import cache
from random import Random


@dataclass(frozen=True)
class Completion:
    identity: str
    answers: tuple[str, ...]
    target: str
    weight: int = 1


@dataclass(frozen=True)
class Case:
    name: str
    family: str
    queries: tuple[str, ...]
    costs: tuple[int, ...]
    rows: tuple[Completion, ...]

    def __post_init__(self):
        if len(self.queries) != len(self.costs) or len(set(self.queries)) != len(self.queries):
            raise ValueError("each distinct query needs one cost")
        if any(not isinstance(query, str) or not query for query in self.queries):
            raise ValueError("query names must be nonempty strings")
        if any(type(cost) is not int or cost <= 0 for cost in self.costs):
            raise ValueError("costs must be positive integers")
        if len({row.identity for row in self.rows}) != len(self.rows):
            raise ValueError("completion identities must be distinct")
        for row in self.rows:
            if len(row.answers) != len(self.queries):
                raise ValueError("each completion must answer every query")
            if not all(isinstance(value, str) and value for value in (row.identity, row.target, *row.answers)):
                raise ValueError("identity, targets and answers must be nonempty strings")
            if type(row.weight) is not int or row.weight <= 0:
                raise ValueError("prior weights must be positive integers")


@dataclass(frozen=True)
class Result:
    status: str
    cost: int | None = None
    tree: dict | None = None
    witness: tuple[str, str] | None = None
    states: int = 0


def solve(case):
    if not case.rows:
        return Result("INCONSISTENT")

    signatures = {}
    for row in case.rows:
        prior = signatures.setdefault(row.answers, row)
        if prior.target != row.target:
            return Result("AUDIT_INACCESSIBLE", witness=(prior.identity, row.identity))

    targets = {}
    partitions = [{} for _ in case.queries]
    for index, row in enumerate(case.rows):
        bit = 1 << index
        targets[row.target] = targets.get(row.target, 0) | bit
        for cells, answer in zip(partitions, row.answers, strict=True):
            cells[answer] = cells.get(answer, 0) | bit

    @cache
    def choose(belief):
        if any(belief & target == belief for target in targets.values()):
            return 0, None
        candidates = []
        for index, cells in enumerate(partitions):
            successors = [belief & part for part in cells.values() if belief & part]
            if len(successors) > 1:
                worst = max(choose(successor)[0] for successor in successors)
                candidates.append((case.costs[index] + worst, index))
        return min(candidates)

    def build(belief):
        _, query = choose(belief)
        if query is None:
            return {"target": next(target for target, mask in targets.items() if mask & belief)}
        children = {
            answer: build(mask & belief)
            for answer, mask in sorted(partitions[query].items())
            if mask & belief
        }
        return {"query": case.queries[query], "answers": children}

    full = (1 << len(case.rows)) - 1
    cost, _ = choose(full)
    tree = build(full)
    states = choose.cache_info().currsize
    choose.cache_clear()
    return Result("CERTIFIED", cost, tree, states=states)


def _partition(rows, query):
    groups = {}
    for row in rows:
        groups.setdefault(row.answers[query], []).append(row)
    return groups


def _leaf(rows):
    values = {row.target for row in rows}
    if len(values) == 1:
        return {"target": next(iter(values))}
    return {"abstain": True}


def fixed_policy(case, query_indices):
    """Acquire the frozen query subset on every path, including homogeneous prefixes."""
    if not case.rows:
        return None

    def build(rows, step):
        if step == len(query_indices):
            return _leaf(rows)
        query = query_indices[step]
        children = {
            answer: build(group, step + 1)
            for answer, group in sorted(_partition(rows, query).items())
        }
        return {"query": case.queries[query], "answers": children}

    return build(case.rows, 0)


def _weight(rows):
    return sum(row.weight for row in rows)


def _edge_mass(rows):
    # Each pair of rows with different targets contributes the product of its prior weights.
    by_target = {}
    for row in rows:
        by_target[row.target] = by_target.get(row.target, 0) + row.weight
    return (_weight(rows) ** 2 - sum(weight * weight for weight in by_target.values())) // 2


def _score(rows, groups, cost, statistic):
    incoming = statistic(rows)
    total_weight = _weight(rows)
    remaining = sum(_weight(group) * statistic(group) for group in groups.values())
    return Fraction(incoming * total_weight - remaining, total_weight * cost)


def greedy_policy(case, method, seed=None):
    if not case.rows:
        return None
    if method == "partition":
        statistic = len
    elif method == "edge_cut":
        statistic = _edge_mass
    elif method == "random":
        rng = Random(seed)
    else:
        raise ValueError(f"unknown comparator {method}")

    def build(rows):
        if len({row.target for row in rows}) == 1:
            return _leaf(rows)
        choices = [
            (index, groups)
            for index in range(len(case.queries))
            if len(groups := _partition(rows, index)) > 1
        ]
        if not choices:
            return _leaf(rows)
        if method == "random":
            query, groups = rng.choice(choices)
        else:
            query, groups = max(
                choices,
                key=lambda choice: (
                    _score(rows, choice[1], case.costs[choice[0]], statistic),
                    -choice[0],
                ),
            )
        children = {answer: build(group) for answer, group in sorted(groups.items())}
        return {"query": case.queries[query], "answers": children}

    return build(case.rows)
