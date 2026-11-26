"""Observation-only minimax synthesis over sets of compatible concrete states."""

from dataclasses import astuple, dataclass, replace
from functools import cache

from common import COST, JOBS, ORDER, PROFILES, SLIPS, canonical, digest

OPPOSITE = {"left": "right", "right": "left", "both": "both", "closed": "closed"}


@dataclass(frozen=True, order=True)
class State:
    profile: str
    signed: bool
    slip: int
    jobs: int = 0
    buffered: bool = False
    stopped: bool = False
    licensed: bool = False
    refined: bool = False
    layout_seen: bool = False
    plate_seen: bool = False

    def wire(self):
        return list(astuple(self))


def initial(scope):
    if scope["evidence"] != "two-slots":
        return frozenset()
    return frozenset(State(profile, signed, slip)
                     for profile in scope["profiles"]
                     for signed in scope.get("signatures", [False, True])
                     for slip in SLIPS)


def enabled(state):
    if state.stopped or state.jobs == len(JOBS):
        return frozenset()
    actions = {"refuse", "layout", "refine"}
    if not state.buffered:
        actions.update(("left", "right"))
        if not state.jobs:
            actions.add("buffer")
        if state.licensed:
            actions.add("relief")
    if state.signed:
        actions.add("plate")
    if PROFILES[state.profile]["relief"]:
        actions.add("grant")
    return frozenset(actions)


def projection(state):
    return tuple(f"offer-{slip}" for slip in SLIPS) if (
        state.refined or PROFILES[state.profile]["panel"] == "indexed"
    ) else ("queued", "queued")


def semantic_kernel(state):
    return (
        frozenset(tag for tag, seen in (("layout", state.layout_seen), ("plate", state.plate_seen))
                  if seen),
        projection(state),
        enabled(state),
    )


def step(state, action):
    if action not in enabled(state):
        return "unauthorized", None, state
    if action == "refuse":
        return "ok", "stopped", replace(state, stopped=True)
    if action == "buffer":
        return "ok", "buffered", replace(state, jobs=1, buffered=True)
    if action == "layout":
        return "ok", f"layout-{PROFILES[state.profile]['entry']}", replace(state, layout_seen=True)
    if action == "plate":
        return "ok", "two-slots", replace(state, plate_seen=True)
    if action == "refine":
        successor = replace(state, refined=True)
        observed = projection(successor)[state.slip] if state.jobs and not state.buffered else "reindexed"
        return "ok", observed, successor
    if action == "grant":
        return "ok", "granted", replace(state, licensed=True)
    if action != "relief":
        lane = PROFILES[state.profile]["entry"]
        if state.jobs and state.slip:
            lane = OPPOSITE[lane]
        if lane not in ("both", action):
            return "unsafe", None, state
    successor = replace(state, jobs=state.jobs + 1)
    return "ok", "complete" if successor.jobs == len(JOBS) else projection(successor)[state.slip], successor


class Game:
    def __init__(self, scope, omniscient=False):
        self.scope = scope
        self.actions = tuple(action for action in ORDER if action in scope["actions"])
        self.root = initial(scope)
        self.omniscient = omniscient
        self.transitions = cache(self.transitions)
        self.value = cache(self.value)

    def transitions(self, belief, action):
        by_observation = {}
        for state in sorted(belief):
            status, obs, successor = step(state, action)
            if status != "ok":
                return {"reason": status, "state": state.wire()}, {}
            if self.omniscient and successor.jobs and not successor.buffered:
                obs = f"{obs}:{successor.slip}"
            by_observation.setdefault(obs, set()).add(successor)
        return None, {observation: frozenset(states)
                      for observation, states in sorted(by_observation.items())}

    def value(self, belief, ticks):
        if not belief:
            return None, None
        if all(state.jobs == len(JOBS) for state in belief):
            return 0, None
        if ticks == 0 or any(state.stopped for state in belief):
            return None, None
        best_cost, best_action = None, None
        for action in self.actions:
            blocked, next_beliefs = self.transitions(belief, action)
            if blocked is not None:
                continue
            future = [self.value(states, ticks - 1)[0] for states in next_beliefs.values()]
            if any(cost is None for cost in future):
                continue
            worst = COST.get(action, 0) + max(future)
            if best_cost is None or worst < best_cost:
                best_cost, best_action = worst, action
        return best_cost, best_action

    def policy(self, belief, ticks):
        cost, action = self.value(belief, ticks)
        if cost is None:
            raise ValueError("Cannot extract a winning policy for this belief")
        if action is None:
            return {"complete": True}
        _, successors = self.transitions(belief, action)
        return {"action": action, "branches": {
            obs: self.policy(states, ticks - 1) for obs, states in successors.items()
        }}

    def losing_witness(self, budget):
        nodes = {}

        def visit(belief, ticks, cap):
            cost, _ = self.value(belief, ticks)
            if not belief or (cost is not None and cost <= cap):
                raise ValueError("Cannot certify a supported winning or empty belief as losing")
            info = {"belief": [state.wire() for state in sorted(belief)],
                    "ticks": ticks, "budget": cap}
            pointer = digest(canonical(info))
            if pointer in nodes:
                return pointer
            if ticks == 0 or any(state.stopped for state in belief):
                nodes[pointer] = {"decision": info, "terminal": "utility-shortfall"}
                return pointer
            rejections = {}
            for action in self.actions:
                charge = COST.get(action, 0)
                if charge > cap:
                    rejections[action] = {"reason": "budget"}
                    continue
                blocked, next_beliefs = self.transitions(belief, action)
                if blocked is not None:
                    rejections[action] = blocked
                    continue
                for obs, successor in next_beliefs.items():
                    future, _ = self.value(successor, ticks - 1)
                    if future is None or future + charge > cap:
                        rejections[action] = {"reason": "losing-observation", "observation": obs,
                                              "next": visit(successor, ticks - 1, cap - charge)}
                        break
            nodes[pointer] = {"decision": info, "rejections": rejections}
            return pointer

        root = visit(self.root, self.scope["horizon"], budget)
        return {"root": root, "nodes": nodes}

    def certificate(self):
        ticks = self.scope["horizon"]
        cost, _ = self.value(self.root, ticks)
        if not self.root:
            return {"status": "inconsistent", "cost": None, "immediate": [],
                    "policy": None, "lower_bound": None, "counterproof": None}
        immediate = [action for action in self.actions if not self.transitions(self.root, action)[0]]
        if cost is None:
            budget = ticks * max(COST.values())
            status, policy = "infeasible", None
        else:
            budget = cost - 1 if cost else None
            status, policy = "winning", self.policy(self.root, ticks)
        return {"status": status, "cost": cost, "policy": policy, "immediate": immediate,
                "lower_bound": budget,
                "counterproof": self.losing_witness(budget) if budget is not None else None}
