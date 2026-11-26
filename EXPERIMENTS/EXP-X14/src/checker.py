"""Independent replay, exhaustive budget search and counterproof validation."""

from collections import defaultdict
from functools import cache

from common import COST, JOBS, ORDER, SLIPS, canonical, digest, fields
from engine import Workshop, play, score


def worlds(scope):
    if scope["evidence"] != "two-slots":
        return ()
    return tuple(Workshop(profile, signature, slip)
                 for profile in sorted(scope["profiles"])
                 for signature in scope.get("signatures", [False, True])
                 for slip in SLIPS)


def successors(items, action, omniscient=False):
    rejected = []
    groups = defaultdict(list)
    for machine in items:
        successor, result, observation = machine.enact(action)
        if result != "ok":
            rejected.append((machine.wire(), result))
        else:
            signal = (observation, successor.slip) if (
                omniscient and successor.records and successor.works_open
            ) else observation
            groups[signal].append(successor)
    return rejected, {signal: tuple(machines) for signal, machines in groups.items()}


def full(items):
    return bool(items) and all(len(machine.records) == len(JOBS) for machine in items)


def budget_oracle(scope, omniscient=False):
    """Enumerate legal concrete history forks independently at each budget."""
    moves = tuple(sorted(scope["actions"]))

    @cache
    def reachable(items, remaining, budget):
        if full(items):
            return True
        if remaining <= 0 or any(machine.shuttered for machine in items):
            return False
        for action in moves:
            charge = COST.get(action, 0)
            if charge > budget:
                continue
            rejects, children = successors(items, action, omniscient)
            if not rejects and all(reachable(branch, remaining - 1, budget - charge)
                                   for branch in children.values()):
                return True
        return False

    return reachable


def reference_cost(scope, omniscient=False):
    start = worlds(scope)
    if not start:
        return None
    can_finish = budget_oracle(scope, omniscient=omniscient)
    ticks = scope["horizon"]
    for cap in range(ticks * max(COST.values()) + 1):
        if can_finish(start, ticks, cap):
            return cap
    return None


def verify_policy(scope, policy, expected_cost):
    if type(expected_cost) is not int or expected_cost < 0:
        raise ValueError("Expected a bounded nonnegative integer cost")
    start = worlds(scope)
    if not start:
        raise ValueError("A useful certificate needs nonempty support")

    def visit(items, tree, remaining):
        if full(items):
            fields(tree, ("complete",))
            if tree["complete"] is not True:
                raise ValueError("The policy lacks the required completion leaf")
            return 0
        if remaining <= 0 or any(machine.shuttered for machine in items):
            raise ValueError("A policy branch ran out of work time or refused")
        fields(tree, ("action", "branches"))
        action = tree["action"]
        if action not in scope["actions"]:
            raise ValueError("An action falls outside the declared interface")
        failed, children = successors(items, action)
        if failed:
            raise ValueError(f"An action violates concrete authorization or safety: {failed[0]}")
        fields(tree["branches"], children)
        return COST.get(action, 0) + max(
            visit(branch, tree["branches"][signal], remaining - 1)
            for signal, branch in children.items()
        )

    measured_cost = visit(start, policy, scope["horizon"])
    rows = []
    for machine in start:
        trace = play(machine.profile, machine.signature, machine.slip, scope, policy)
        result = score(machine.profile, machine.signature, machine.slip, scope, trace)
        if not result["useful"] or not result["safe"]:
            raise ValueError("Physical replay did not establish useful safe completion")
        rows.append({"profile": machine.profile, "signature": machine.signature,
                     "slip": machine.slip, "trace": trace, "score": result})
    if measured_cost != expected_cost or max(row["score"]["audit_cost"] for row in rows) != expected_cost:
        raise ValueError("Claimed audit cost diverges from the worst supported branch")
    return rows


def verify_counterproof(scope, proof, bound):
    fields(proof, ("root", "nodes"))
    seen = set()
    moves = set(scope["actions"])

    def visit(pointer, items, remaining, budget):
        expected = {"belief": sorted(machine.wire() for machine in items),
                    "ticks": remaining, "budget": budget}
        if pointer != digest(canonical(expected)) or pointer not in proof["nodes"]:
            raise ValueError("Missing or mismatched proof node")
        node = proof["nodes"][pointer]
        if canonical(node["decision"]) != canonical(expected) or not items or full(items):
            raise ValueError("Invalid losing decision")
        if pointer in seen:
            return
        seen.add(pointer)
        if remaining == 0 or any(machine.shuttered for machine in items):
            fields(node, ("decision", "terminal"))
            if node["terminal"] != "utility-shortfall":
                raise ValueError("Wrong terminal reason")
            return
        fields(node, ("decision", "rejections"))
        fields(node["rejections"], moves)
        for action in moves:
            witness = node["rejections"][action]
            reason = witness.get("reason")
            charge = COST.get(action, 0)
            if reason == "budget":
                fields(witness, ("reason",))
                if charge <= budget:
                    raise ValueError("The purported over-budget action is affordable")
                continue
            rejects, children = successors(items, action)
            if reason in ("unsafe", "unauthorized"):
                fields(witness, ("reason", "state"))
                if not any(canonical(witness["state"]) == canonical(state) and reason == status
                           for state, status in rejects):
                    raise ValueError("The purported concrete rejection is unsupported")
                continue
            fields(witness, ("reason", "next", "observation"))
            observation = witness["observation"]
            if (reason != "losing-observation" or charge > budget or rejects
                    or observation not in children):
                raise ValueError("The purported losing successor is unsupported")
            visit(witness["next"], children[observation], remaining - 1, budget - charge)

    visit(proof["root"], worlds(scope), scope["horizon"], bound)
    if seen != set(proof["nodes"]):
        raise ValueError("Proof contains unreachable entries")
    return len(seen)


def verify_certificate(scope, cert):
    fields(cert, ("status", "cost", "immediate", "policy", "lower_bound", "counterproof"))
    items = worlds(scope)
    reference = reference_cost(scope)
    expected = "inconsistent" if not items else "infeasible" if reference is None else "winning"
    if cert["status"] != expected or cert["cost"] != reference:
        raise ValueError("Certificate disagrees with exhaustive concrete budget search")
    immediate = [action for action in ORDER
                 if items and action in scope["actions"] and not successors(items, action)[0]]
    if cert["immediate"] != immediate:
        raise ValueError("Immediate action intersection disagrees with concrete support")
    if reference is None:
        bound = scope["horizon"] * max(COST.values()) if items else None
        replays = []
        if cert["policy"] is not None:
            raise ValueError("A nonwinning certificate contains a policy")
    else:
        bound = reference - 1 if reference > 0 else None
        replays = verify_policy(scope, cert["policy"], cert["cost"])
    if canonical(cert["lower_bound"]) != canonical(bound) or (
        (bound is None) != (cert["counterproof"] is None)
    ):
        raise ValueError("The lower-bound budget or proof is inconsistent")
    nodes = 0 if bound is None else verify_counterproof(scope, cert["counterproof"], bound)
    return {"world_replays": replays, "proof_nodes": nodes, "reference_cost": reference}


def exhaustive_baseline(scope):
    """Try the full positive-cost interface in cost order, then solve for production."""
    start = worlds(scope)
    audits = sorted((action for action in scope["actions"] if action in COST), key=COST.__getitem__)
    production = {**scope, "actions": [action for action in scope["actions"] if action not in COST]}
    finish = budget_oracle(production)

    def attempt(items, ticks, index):
        if index == len(audits):
            return "complete" if finish(items, ticks, 0) else "no-safe-continuation"
        if ticks == 0:
            return "deadline"
        rejected, branches = successors(items, audits[index])
        if rejected:
            return "unauthorized"
        statuses = {attempt(branch, ticks - 1, index + 1) for branch in branches.values()}
        return statuses.pop() if len(statuses) == 1 else "mixed"

    return {"audit_order": audits, "cost_if_exhausted": sum(COST[action] for action in audits),
            "status": attempt(start, scope["horizon"], 0) if start else "inconsistent"}
