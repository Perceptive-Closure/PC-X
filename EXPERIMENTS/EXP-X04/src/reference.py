"""Independent budget, certificate and policy checks over explicit tables."""

from fractions import Fraction
from functools import cache
from itertools import combinations


def adaptive_budget_optimum(case):
    """Find the least feasible integer budget using explicit answer histories."""
    if not case.rows:
        return None, 0

    @cache
    def can_identify(history, money):
        possible = [
            row for row in case.rows
            if all(row.answers[index] == answer for index, answer in history)
        ]
        if len({row.target for row in possible}) == 1:
            return True
        observed = {index for index, _ in history}
        for index, cost in enumerate(case.costs):
            if index in observed or cost > money:
                continue
            answers = {row.answers[index] for row in possible}
            if len(answers) < 2:
                continue
            if all(
                can_identify(tuple(sorted((*history, (index, answer)))), money - cost)
                for answer in sorted(answers)
            ):
                return True
        return False

    maximum = sum(case.costs)
    if not can_identify((), maximum):
        states = can_identify.cache_info().currsize
        can_identify.cache_clear()
        return None, states
    low, high = 0, maximum
    while low < high:
        candidate = (low + high) // 2
        if can_identify((), candidate):
            high = candidate
        else:
            low = candidate + 1
    states = can_identify.cache_info().currsize
    can_identify.cache_clear()
    return low, states


def certificate_optima(case):
    """Enumerate every query subset, evaluating uniform and realized answer cells."""
    if not case.rows:
        return None, {}
    uniform = None
    local = {row.identity: None for row in case.rows}
    for count in range(len(case.queries) + 1):
        for queries in combinations(range(len(case.queries)), count):
            cost = sum(case.costs[index] for index in queries)
            groups = {}
            for row in case.rows:
                answer = tuple(row.answers[index] for index in queries)
                groups.setdefault(answer, []).append(row)
            all_cells = True
            for group in groups.values():
                if len({row.target for row in group}) != 1:
                    all_cells = False
                    continue
                for row in group:
                    if local[row.identity] is None or cost < local[row.identity]:
                        local[row.identity] = cost
            proposal = (cost, queries)
            if all_cells and (uniform is None or proposal < uniform):
                uniform = proposal
    return uniform, local


def verify_witness(case, witness):
    if not isinstance(witness, tuple) or len(witness) != 2:
        raise ValueError("inaccessibility witness must contain two completion identities")
    positions = {row.identity: row for row in case.rows}
    if any(identity not in positions for identity in witness):
        raise ValueError("witness is outside the admitted domain")
    left, right = (positions[identity] for identity in witness)
    if not (left.answers == right.answers and left.target != right.target):
        raise ValueError("witness must agree on all queries and disagree in target")


def replay(case, tree):
    """Replay the same observation-only tree for each admitted completion."""
    if not case.rows:
        if tree is not None:
            raise ValueError("an inconsistent domain cannot have a policy")
        return []
    names = {query: index for index, query in enumerate(case.queries)}
    decisions = []

    def visit(node, belief, history, acquired, total):
        if not isinstance(node, dict):
            raise ValueError("policy node must be a mapping")
        keys = set(node)
        if keys == {"query", "answers"}:
            query = node["query"]
            if not isinstance(query, str) or query not in names or query in acquired:
                raise ValueError("policy selected an unavailable or repeated query")
            index = names[query]
            children = node["answers"]
            possible_answers = {row.answers[index] for row in belief}
            if not isinstance(children, dict) or set(children) != possible_answers:
                raise ValueError("reachable answer branches must match exactly")
            for answer in sorted(possible_answers):
                remaining = [row for row in belief if row.answers[index] == answer]
                visit(
                    children[answer],
                    remaining,
                    (*history, (query, answer)),
                    acquired | {query},
                    total + case.costs[index],
                )
            return

        targets = {row.target for row in belief}
        if keys == {"target"} and targets == {node["target"]}:
            verdict = "CERTIFIED"
        elif keys == {"abstain"} and node["abstain"] is True:
            if len(targets) < 2 or len({row.answers for row in belief}) != 1:
                raise ValueError("abstention requires a mixed full-answer equivalence class")
            verdict = "AUDIT_INACCESSIBLE"
        else:
            raise ValueError("unjustified leaf or completion-dependent policy")
        for row in belief:
            decisions.append({
                "completion": row.identity,
                "status": verdict,
                "certified_target": node.get("target"),
                "actual_target": row.target,
                "weight": row.weight,
                "cost": total,
                "history": history,
            })

    visit(tree, case.rows, (), frozenset(), 0)
    if sorted(item["completion"] for item in decisions) != sorted(row.identity for row in case.rows):
        raise ValueError("the policy must reach one leaf per completion")
    return sorted(decisions, key=lambda item: item["completion"])


def measure(decisions):
    if not decisions:
        return None
    weight = sum(row["weight"] for row in decisions)
    expected = Fraction(sum(row["weight"] * row["cost"] for row in decisions), weight)
    complete = sum(row["status"] == "CERTIFIED" for row in decisions)
    return {
        "worst_cost": max(row["cost"] for row in decisions),
        "expected_cost": str(expected),
        "certified": complete,
        "completions": len(decisions),
    }
