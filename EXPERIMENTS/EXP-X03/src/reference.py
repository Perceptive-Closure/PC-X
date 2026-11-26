"""Independent direct-partition implementation and proof verification."""

from dataclasses import dataclass
from itertools import combinations

from .certificates import Certificate, Problem


def subsets(width: int):
    for size in range(width + 1):
        yield from combinations(range(width), size)


def conflict(problem: Problem, selected: tuple[int, ...], realized: str | None = None):
    """Find target disagreement within an attainable selected-answer cell."""
    cells = {}
    actual = None
    if realized is not None:
        actual = next((row for row in problem.completions if row.identity == realized), None)
        if actual is None:
            raise ValueError(f"unknown realized completion: {realized}")
        answer = tuple(actual.answers[index] for index in selected)
        cells[answer] = actual
    for row in problem.completions:
        key = tuple(row.answers[index] for index in selected)
        if actual is not None and key != answer:
            continue
        representative = cells.setdefault(key, row)
        if representative.target != row.target:
            return representative.identity, row.identity
    return None


@dataclass(frozen=True)
class PartitionOptimum:
    status: str
    cost: int | None
    optima: tuple[tuple[int, ...], ...]
    subsets_checked: int
    cheaper_subsets_rejected: int


def exact_by_partition(problem: Problem, realized: str | None = None) -> PartitionOptimum:
    if not problem.completions:
        if realized is not None:
            raise ValueError(f"unknown realized completion: {realized}")
        return PartitionOptimum("INCONSISTENT", None, (), 0, 0)
    checked = []
    for selected in subsets(len(problem.costs)):
        cost = sum(problem.costs[index] for index in selected)
        checked.append((cost, selected, conflict(problem, selected, realized) is None))
    feasible_costs = [cost for cost, _, valid in checked if valid]
    if not feasible_costs:
        return PartitionOptimum("AUDIT_INACCESSIBLE", None, (), len(checked), len(checked))
    best = min(feasible_costs)
    return PartitionOptimum(
        "CERTIFIED", best,
        tuple(selected for cost, selected, valid in checked if valid and cost == best),
        len(checked), sum(cost < best for cost, _, _ in checked),
    )


def verify_witness(problem: Problem, witness, selected: tuple[int, ...], realized=None):
    if not isinstance(witness, tuple) or len(witness) != 2:
        return False
    if not all(isinstance(identity, str) for identity in witness):
        return False
    if realized is not None and realized not in witness:
        return False
    if any(type(index) is not int or index < 0 or index >= len(problem.costs) for index in selected):
        return False
    by_id = {row.identity: row for row in problem.completions}
    left, right = (by_id.get(identity) for identity in witness)
    return (
        left is not None and right is not None
        and left.target != right.target
        and all(left.answers[q] == right.answers[q] for q in selected)
    )


def verify_proof(problem: Problem, proof: Certificate, realized=None):
    """Validate submitted cost, witness and direct-partition optimality."""
    if realized is not None and all(row.identity != realized for row in problem.completions):
        return False
    if proof.status == "INCONSISTENT":
        return not problem.completions and proof.cost is None and not proof.queries and proof.witness is None
    if proof.status == "AUDIT_INACCESSIBLE":
        return (
            proof.cost is None and not proof.queries
            and verify_witness(problem, proof.witness, tuple(range(len(problem.costs))), realized)
        )
    if proof.status != "CERTIFIED" or not problem.completions or proof.witness is not None:
        return False
    if type(proof.cost) is not int or not isinstance(proof.queries, tuple):
        return False
    if any(type(q) is not int or not 0 <= q < len(problem.costs) for q in proof.queries):
        return False
    if tuple(sorted(set(proof.queries))) != proof.queries:
        return False
    if sum(problem.costs[q] for q in proof.queries) != proof.cost:
        return False
    if conflict(problem, proof.queries, realized) is not None:
        return False
    checked = exact_by_partition(problem, realized)
    return checked.cost == proof.cost and proof.queries in checked.optima
