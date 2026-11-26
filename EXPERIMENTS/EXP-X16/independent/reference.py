"""EXP-X16 exact reference using whole installed paths and receipt histories."""

import argparse
from copy import deepcopy
from dataclasses import dataclass
from functools import cache
from itertools import combinations
import json
from pathlib import Path


SMALL_SCHEDULE_PROFILES = {
    "feedback-live", "feedback-suppressed", "meter-h3", "meter-h4",
    "intrinsic-gap", "gateway-2",
}


@dataclass(frozen=True)
class Installation:
    edges: tuple
    ids: tuple
    remaining: tuple
    verdict: str
    fastest_job_actions: tuple


def edge_flag(edge):
    return "stale" if edge["stale"] else "fresh"


def enumerate_paths(profile):
    """Follow the actual layer connections and accept only declared endpoints."""
    stages = profile["stages"]
    terminals = set(profile["accept"])
    paths = []

    def visit(vertex, prefix):
        stage = len(prefix)
        if stage == len(stages):
            if vertex in terminals:
                remaining = [0]
                actions = []
                for row, edge in reversed(tuple(zip(stages, prefix, strict=True))):
                    tariff = row["base"] + row["premium"] * edge["stale"]
                    remaining.append(remaining[-1] + tariff)
                    actions.append(
                        "job.slow" if edge["stale"] else edge.get("literal_fast", "job.fast")
                    )
                paths.append(Installation(
                    prefix, tuple(edge["id"] for edge in prefix),
                    tuple(reversed(remaining)),
                    "YES" if remaining[-1] <= profile["deadline"] else "NO",
                    tuple(reversed(actions)),
                ))
            return
        for edge in sorted(stages[stage]["edges"], key=lambda row: row["id"]):
            if edge["tail"] == vertex:
                visit(edge["head"], (*prefix, edge))

    visit(profile["start"], ())
    if not paths:
        raise ValueError(f"{profile['id']}: no accepting paths")
    return tuple(paths)


@dataclass(frozen=True)
class StaticQuery:
    id: str
    price: int
    answers: tuple


def static_panel(profile, paths):
    queries = []
    for index, stage in enumerate(profile["stages"]):
        for query in stage["statics"]:
            if query["field"] == "stale":
                answers = tuple(edge_flag(path.edges[index]) for path in paths)
            elif query["field"] == "edge":
                answers = tuple(path.ids[index] for path in paths)
            else:
                raise ValueError(f"unknown static field {query['field']!r}")
            queries.append(StaticQuery(query["id"], query["price"], answers))
    if len({query.id for query in queries}) != len(queries):
        raise ValueError(f"{profile['id']}: static query IDs must be unique")
    return tuple(queries)


def solve_static(panel, labels):
    """Find the cheapest subset covering every opposite-label path pair."""
    masks = set()
    for left, right in combinations(range(len(labels)), 2):
        if labels[left] == labels[right]:
            continue
        mask = sum(
            1 << index for index, query in enumerate(panel)
            if query.answers[left] != query.answers[right]
        )
        masks.add(mask)
    if 0 in masks:
        return {"worst_paid": None, "queries": None, "opposition_masks": len(masks)}

    best = (sum(query.price for query in panel), tuple(range(len(panel))))
    for size in range(len(panel) + 1):
        for indexes in combinations(range(len(panel)), size):
            price = sum(panel[index].price for index in indexes)
            if (price, len(indexes), indexes) >= (best[0], len(best[1]), best[1]):
                continue
            bought = sum(1 << index for index in indexes)
            if all(bought & mask for mask in masks):
                best = (price, indexes)
    return {
        "worst_paid": best[0],
        "queries": [panel[index].id for index in best[1]],
        "opposition_masks": len(masks),
    }


def solve_adaptive(panel, labels):
    """Choose pure predeploy queries by exact minimax over answer cells."""
    @cache
    def visit(worlds):
        if all(labels[index] == labels[worlds[0]] for index in worlds):
            return 0, {"label": labels[worlds[0]]}

        best_price, best_tree = None, None
        for query in panel:
            branches = {}
            for index in worlds:
                branches.setdefault(query.answers[index], []).append(index)
            if len(branches) == 1:
                continue
            next_nodes = {}
            worst = 0
            for answer, branch in sorted(branches.items()):
                price, node = visit(tuple(branch))
                if price is None:
                    break
                worst = max(worst, price)
                next_nodes[answer] = node
            else:
                price = query.price + worst
                if best_price is None or price < best_price:
                    best_price, best_tree = price, {"query": query.id, "next": next_nodes}
        return best_price, best_tree

    price, tree = visit(tuple(range(len(labels))))
    states = visit.cache_info().currsize
    visit.cache_clear()
    return {"worst_paid": price, "tree": tree, "cells": states}


def receipt_key(obs, meter):
    return f"{obs}|{meter}"


def initial_receipt(profile, path):
    obs = edge_flag(path.edges[1]) if profile["variant"] == "free-guard" else "start"
    return {"stage": 0, "obs": obs, "meter": profile["initial_meter"]}


@dataclass(frozen=True)
class Command:
    kind: str
    work: int
    paid: int
    outcomes: tuple

    @property
    def allowed(self):
        # The full occurrence is removed if any supported receipt changes R.
        return not any(changed for _, _, changed in self.outcomes)


def command_row(profile, path, stage, meter):
    """Interpret the declared raw source support, including disallowed fast atoms."""
    if stage == len(path.ids):
        return {}
    edge = path.edges[stage]
    task = profile["stages"][stage]
    supported = tuple((branch["obs"], branch["meter"]) for branch in edge["gives"])
    raw_fast = tuple(
        (obs, next_meter, bool(edge["stale"] and index == len(supported) - 1))
        for index, (obs, next_meter) in enumerate(supported)
    )
    row = {
        edge.get("literal_fast", "job.fast"): Command("job", task["base"], 0, raw_fast),
        "job.slow": Command(
            "job", task["base"] + task["premium"], 0,
            tuple((obs, next_meter, False) for obs, next_meter in supported),
        ),
    }
    for act, read in task["reads"].get(meter, {}).items():
        if read["observe"] == "stale":
            obs = edge_flag(edge)
        elif read["observe"] == "prepared":
            obs = "prepared"
        else:
            raise ValueError(f"unknown read observation {read['observe']!r}")
        paid = read["price"]
        if (profile["variant"] == "hidden-carry" and act == "ask.flag"
                and any(previous.get("carry") for previous in path.edges[:stage])):
            paid += 4
        next_meter = meter if read["next"] == "same" else read["next"]
        row[act] = Command("read", 0, paid, ((obs, next_meter, False),))
    return row


@dataclass(frozen=True)
class History:
    stage: int
    meter: str
    work: int
    # Each world is an index into the accepting-path catalogue with its own paid total.
    worlds: tuple
    # Each move is a literal command and the full receipt that actually followed it.
    moves: tuple = ()
    disturbed: bool = False

    def receipt_stutter(self, child):
        # With the same worlds, stage, meter and instrument, additional nonnegative
        # charges and one fewer move cannot improve a continuation.
        return (
            self.stage == child.stage
            and self.meter == child.meter
            and self.work == child.work
            and self.disturbed == child.disturbed
            and tuple(index for index, _ in self.worlds)
            == tuple(index for index, _ in child.worlds)
        )


class ReceiptSearch:
    """Explore public command/receipt histories without merging them by state."""

    def __init__(self, profile, paths, identity):
        self.profile = profile
        self.paths = paths
        self.identity = identity
        self.depth = len(profile["stages"])
        self.horizon = profile["horizon"]
        self.deadline = profile["deadline"]
        self.rows = {}
        self.states = 0
        self.action_trials = 0

    def starts(self):
        groups = {}
        for index, path in enumerate(self.paths):
            initial = initial_receipt(self.profile, path)
            key = receipt_key(initial["obs"], initial["meter"])
            groups.setdefault(key, []).append((index, 0))
        return {
            key: History(0, self.profile["initial_meter"], 0, tuple(worlds))
            for key, worlds in sorted(groups.items())
        }

    def stop(self, history):
        if self.identity and len(history.worlds) != 1:
            return None
        labels = {self.paths[index].verdict for index, _ in history.worlds}
        if labels == {"NO"}:
            return "NO"
        if labels == {"YES"} and history.stage == self.depth and not history.disturbed:
            return "YES"
        return None

    def exhausted(self, history):
        if len(history.moves) >= self.horizon:
            return True
        positive = [
            self.paths[index] for index, _ in history.worlds
            if self.paths[index].verdict == "YES"
        ]
        return bool(positive) and (
            history.stage + self.horizon - len(history.moves) < self.depth
            or history.work + max(path.remaining[history.stage] for path in positive)
            > self.deadline
        )

    def choices(self, history):
        world_rows = []
        common = None
        for index, _ in history.worlds:
            key = (index, history.stage, history.meter)
            if key not in self.rows:
                self.rows[key] = command_row(
                    self.profile, self.paths[index], history.stage, history.meter
                )
            row = self.rows[key]
            world_rows.append(row)
            legal = {
                act for act, command in row.items()
                if command.allowed and history.work + command.work <= self.deadline
            }
            common = legal if common is None else common & legal
            if not common:
                return {}
        return {act: tuple(row[act] for row in world_rows) for act in sorted(common)}

    def successors(self, history, act, commands):
        tariff = {(command.kind, command.work) for command in commands}
        if len(tariff) != 1:
            raise ValueError(f"{act!r} has no common unambiguous stage/work effect")
        kind, work = next(iter(tariff))
        groups = {}
        for (index, paid), command in zip(history.worlds, commands, strict=True):
            for obs, meter, _ in command.outcomes:
                key = receipt_key(obs, meter)
                group = groups.setdefault(key, {})
                group[index] = paid + command.paid
        disturbed = history.disturbed or (
            self.profile["variant"] == "changed-instrument" and act == "ask.flag"
        )
        return {
            key: History(
                history.stage + (kind == "job"), key.split("|", 1)[1],
                history.work + work, tuple(group.items()),
                (*history.moves, (act, key)), disturbed,
            )
            for key, group in sorted(groups.items())
        }

    @staticmethod
    def paid(history):
        return max(paid for _, paid in history.worlds)

    def adaptive(self, history):
        self.states += 1
        verdict = self.stop(history)
        if verdict:
            return self.paid(history), {"verdict": verdict}
        if self.exhausted(history):
            return None, None
        best_paid, best_node = None, None
        for act, commands in self.choices(history).items():
            self.action_trials += 1
            children = self.successors(history, act, commands)
            if len(children) == 1 and history.receipt_stutter(next(iter(children.values()))):
                continue
            worst = max(map(self.paid, children.values()))
            if best_paid is not None and worst >= best_paid:
                continue
            next_nodes = {}
            for key, child in children.items():
                child_paid, node = self.adaptive(child)
                if child_paid is None or (best_paid is not None and child_paid >= best_paid):
                    break
                worst = max(worst, child_paid)
                next_nodes[key] = node
            else:
                best_paid, best_node = worst, {"act": act, "next": next_nodes}
        return best_paid, best_node

    def scheduled(self, histories):
        """One literal command per ordinal across every branch still running."""
        self.states += 1
        live = []
        stopped_paid = 0
        for history in histories:
            if self.stop(history):
                stopped_paid = max(stopped_paid, self.paid(history))
            elif self.exhausted(history):
                return None, None
            else:
                live.append(history)
        if not live:
            return stopped_paid, ()

        choices = [self.choices(history) for history in live]
        possible = set.intersection(*(set(row) for row in choices))
        best_paid, best_schedule = None, None
        for act in sorted(possible):
            self.action_trials += 1
            successors = [
                self.successors(history, act, row[act])
                for history, row in zip(live, choices, strict=True)
            ]
            if all(
                len(children) == 1 and history.receipt_stutter(next(iter(children.values())))
                for history, children in zip(live, successors, strict=True)
            ):
                continue
            price, tail = self.scheduled(tuple(
                child for children in successors for child in children.values()
            ))
            if price is not None:
                price = max(price, stopped_paid)
                if best_paid is None or price < best_paid:
                    best_paid, best_schedule = price, (act, *tail)
        return best_paid, best_schedule

    def schedule_tree(self, history, schedule):
        verdict = self.stop(history)
        if verdict:
            return {"verdict": verdict}
        act = schedule[len(history.moves)]
        children = self.successors(history, act, self.choices(history)[act])
        return {
            "act": act,
            "next": {key: self.schedule_tree(child, schedule) for key, child in children.items()},
        }


def solve_online(profile, paths, identity=False):
    search = ReceiptSearch(profile, paths, identity)
    roots = {key: search.adaptive(root) for key, root in search.starts().items()}
    losing = [key for key, (price, _) in roots.items() if price is None]
    return {
        "worst_paid": None if losing else max(price for price, _ in roots.values()),
        "policy_by_initial": None if losing else {key: node for key, (_, node) in roots.items()},
        "losing_initial_receipts": losing,
        "histories": search.states,
        "action_trials": search.action_trials,
    }


def solve_schedule(profile, paths, identity=False):
    search = ReceiptSearch(profile, paths, identity)
    starts = search.starts()
    price, schedule = search.scheduled(tuple(starts.values()))
    return {
        "worst_paid": price,
        "schedule": schedule,
        "policy_by_initial": None if schedule is None else {
            key: search.schedule_tree(root, schedule) for key, root in starts.items()
        },
        "ordinal_states": search.states,
        "action_trials": search.action_trials,
    }


def solve_profile(profile, fixed=False):
    paths = enumerate_paths(profile)
    labels = {
        "target": tuple(path.verdict for path in paths),
        "identity": tuple(path.ids for path in paths),
    }
    panel = static_panel(profile, paths)
    result = {
        "paths": [
            {
                "edges": path.ids,
                "intrinsic_cost": path.remaining[0],
                "target": path.verdict,
                "fastest_job_actions": path.fastest_job_actions,
            }
            for path in paths
        ],
        "all_queries_paid": sum(query.price for query in panel),
        "static": {goal: solve_static(panel, values) for goal, values in labels.items()},
        "adaptive": {goal: solve_adaptive(panel, values) for goal, values in labels.items()},
        "online": {
            goal: solve_online(profile, paths, identity=goal == "identity")
            for goal in labels
        },
    }
    if fixed:
        result["fixed_schedule"] = {
            goal: solve_schedule(profile, paths, identity=goal == "identity")
            for goal in labels
        }
    return result


def abstract_profile(profile, control):
    """Construct only the two preregistered model-only exposures."""
    profile = deepcopy(profile)
    if control == "cartesian-relaxation":
        profile["start"] = "layer-0"
        profile["accept"] = [f"layer-{len(profile['stages'])}"]
        for index, stage in enumerate(profile["stages"]):
            for edge in stage["edges"]:
                edge["tail"] = f"layer-{index}"
                edge["head"] = f"layer-{index + 1}"
    elif control == "missing-long-support":
        for edge in profile["stages"][0]["edges"]:
            edge["gives"] = [branch for branch in edge["gives"] if branch["meter"] != "LONG"]
    else:
        raise ValueError(f"unknown abstract exposure {control!r}")
    return profile


def solve_catalogue(catalogue):
    profiles = {profile["id"]: profile for profile in catalogue["profiles"]}
    valid = set(catalogue["valid_profiles"])
    solved = {}
    for name, profile in profiles.items():
        solved[name] = solve_profile(profile, fixed=name in SMALL_SCHEDULE_PROFILES)
        solved[name]["scope"] = "valid-profile" if name in valid else "native-control"
    controls = {}
    for control in catalogue["controls"]:
        if control["id"] in {"cartesian-relaxation", "missing-long-support"}:
            profile = profiles[control["profile"]]
            model = abstract_profile(profile, control["id"])
            controls[control["id"]] = {
                "profile": profile["id"],
                "gate": control["gate"],
                "scope": "model-only-control",
                **solve_profile(model),
            }
    return {"schema": 1, "profiles": solved, "abstract_controls": controls}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalogue", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    catalogue = json.loads(args.catalogue.read_text(encoding="utf-8"))
    result = solve_catalogue(catalogue)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
