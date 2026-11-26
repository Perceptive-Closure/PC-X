"""Exact finite audit and governed service forecasts for the registered X16 catalogue."""
import argparse
from functools import cache
from itertools import product
import json
from math import inf
from pathlib import Path


JOBS = ("job.fast", "job.slow")
OPEN_LOOP = frozenset((
    "feedback-live", "feedback-suppressed", "meter-h3", "meter-h4",
    "intrinsic-gap", "gateway-2",
))


def dump(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n",
                    encoding="utf-8", newline="\n")


def accepting_paths(profile):
    paths = [(profile["start"], ())]
    for stage in profile["stages"]:
        paths = [(edge["head"], prefix + (edge,))
                 for tail, prefix in paths for edge in stage["edges"]
                 if edge["tail"] == tail]
    return sorted((prefix for tail, prefix in paths if tail in profile["accept"]),
                  key=lambda prefix: tuple(edge["id"] for edge in prefix))


def intrinsic_work(profile, path):
    return sum(stage["base"] + stage["premium"] * edge["stale"]
               for stage, edge in zip(profile["stages"], path, strict=True))


def static_answer(item, edge):
    if item["field"] == "edge":
        return edge["id"]
    return "stale" if edge["stale"] else "fresh"


def allowed_stage_row(stage, edge, meter, command):
    """Projected, local rows of the valid T30.CG fragment."""
    if command in JOBS:
        if command == "job.fast" and edge["stale"]:
            return None
        work = stage["base"] + (stage["premium"] if command == "job.slow" else 0)
        return work, 0, tuple((record["obs"], record["meter"]) for record in edge["gives"])
    spec = stage["reads"].get(meter, {}).get(command)
    if spec is None:
        return None
    obs = ("stale" if edge["stale"] else "fresh") if spec["observe"] == "stale" else "prepared"
    meter = meter if spec["next"] == "same" else spec["next"]
    return 0, spec["price"], ((obs, meter),)


def command_names(stage, meter):
    return JOBS + tuple(sorted(stage["reads"].get(meter, {})))


def branch_key(obs, meter):
    return f"{obs}|{meter}"


def minimax(initial, terminal, choices, horizon):
    @cache
    def visit(state):
        verdict = terminal(state)
        if verdict is not None:
            return 0, None, verdict
        if horizon(state) == 0:
            return inf, None, None
        best = inf
        preferred = None
        for command, price, children in choices(state):
            continuation = max(visit(child)[0] for _, child in children)
            value = price + continuation
            if value < best:
                best = value
                preferred = command
        return best, preferred, None

    def policy(state):
        _, command, verdict = visit(state)
        if verdict is not None:
            return {"verdict": verdict}
        for label, _, children in choices(state):
            if label == command:
                return {"act": command,
                        "next": {key: policy(child) for key, child in children}}
        raise ValueError("losing state has no policy")

    def refute(state):
        if horizon(state) == 0:
            return {"state": state, "reason": "moves-exhausted", "blocked": []}
        blocked = []
        for command, price, children in choices(state):
            record, child = next((record, child) for record, child in children
                                 if visit(child)[0] == inf)
            blocked.append({"act": command, "paid": price,
                            "receipt": record, "losing_child": refute(child)})
        return {"state": state, "reason": "all-lawful-affordable-choices-lose",
                "blocked": blocked}

    value = visit(initial)[0]
    if value == inf:
        return {"value": None, "policy": None, "refutation": refute(initial),
                "states": visit.cache_info().currsize}
    tree = policy(initial)
    return {"value": value, "policy": tree, "refutation": None,
            "states": visit.cache_info().currsize}


class Frontier:
    """One public state, with summaries of genuinely attained prefix scores."""

    def __init__(self, profile, full_scores=False):
        self.profile = profile
        self.cap = profile["deadline"] + 1
        self.full_scores = full_scores
        self.n = len(profile["stages"])
        self.layers = self.prune(profile)
        self.suffix = self.suffix_extrema()
        self.initial = (0, profile["initial_meter"], profile["deadline"],
                        profile["horizon"], tuple((i, self.summarize((0,)))
                                                  for i in range(len(self.layers[0]))))

    @staticmethod
    def prune(profile):
        active = set(profile["accept"])
        backward = []
        for stage in reversed(profile["stages"]):
            viable = tuple(edge for edge in stage["edges"] if edge["head"] in active)
            active = {edge["tail"] for edge in viable}
            backward.append(viable)
        active = {profile["start"]}
        layers = []
        for viable in reversed(backward):
            accepted = tuple(edge for edge in viable if edge["tail"] in active)
            layers.append(accepted)
            active = {edge["head"] for edge in accepted}
        return layers

    def summarize(self, values):
        values = tuple(values)
        return tuple(sorted(set(values))) if self.full_scores else (min(values), max(values))

    def clip(self, number):
        return min(number, self.cap)

    def kappa(self, i, edge):
        stage = self.profile["stages"][i]
        return stage["base"] + stage["premium"] * edge["stale"]

    def suffix_extrema(self):
        out = [{} for _ in range(self.n)] + [
            {vertex: (0, 0) for vertex in self.profile["accept"]}
        ]
        for i in reversed(range(self.n)):
            by_tail = {}
            for edge in self.layers[i]:
                add = self.kappa(i, edge)
                successor = out[i + 1][edge["head"]]
                by_tail.setdefault(edge["tail"], []).extend(self.clip(add + x)
                                                           for x in successor)
            out[i] = {tail: (min(scores), max(scores)) for tail, scores in by_tail.items()}
        return out

    def bounds(self, state):
        i, _, _, _, present = state
        if i == self.n:
            _, scores = present[0]
            return scores[0], scores[-1]
        lower = inf
        upper = -1
        for j, scores in present:
            edge = self.layers[i][j]
            shift = self.kappa(i, edge)
            suffix_low, suffix_high = self.suffix[i + 1][edge["head"]]
            lower = min(lower, self.clip(scores[0] + shift + suffix_low))
            upper = max(upper, self.clip(scores[-1] + shift + suffix_high))
        return lower, upper

    def terminal(self, state):
        lower, upper = self.bounds(state)
        if lower >= self.cap:
            return "NO"
        if state[0] == self.n and upper < self.cap:
            return "YES"
        return None

    def advance(self, stage, active):
        by_vertex = {}
        for j, scores in active:
            edge = self.layers[stage][j]
            vertex = edge["head"] if stage + 1 < self.n else None
            by_vertex.setdefault(vertex, []).extend(
                self.clip(score + self.kappa(stage, edge)) for score in scores
            )
        if stage + 1 == self.n:
            return ((0, self.summarize(by_vertex[None])),)
        return tuple((j, self.summarize(by_vertex[edge["tail"]]))
                     for j, edge in enumerate(self.layers[stage + 1])
                     if edge["tail"] in by_vertex)

    def choices(self, state):
        i, meter, work_left, remaining, present = state
        if i == self.n or remaining == 0:
            return
        stage = self.profile["stages"][i]
        for command in command_names(stage, meter):
            rows = tuple(allowed_stage_row(stage, self.layers[i][j], meter, command)
                         for j, _ in present)
            if any(row is None for row in rows):
                continue
            work, price = rows[0][:2]
            if work > work_left:
                continue
            if any(row[:2] != (work, price) for row in rows):
                raise ValueError("quotes differ within one public state")
            by_receipt = {}
            for entry, row in zip(present, rows, strict=True):
                for obs, next_meter in row[2]:
                    by_receipt.setdefault((obs, next_meter), []).append(entry)
            children = []
            for (obs, following), active in sorted(by_receipt.items()):
                new_belief = self.advance(i, active) if work else tuple(active)
                child = (i + bool(work), following, work_left - work, remaining - 1, new_belief)
                children.append((branch_key(obs, following), child))
            yield command, price, tuple(children)

    def solve(self):
        if not self.layers[0]:
            return {"value": None, "policy": None, "states": 0,
                    "refutation": {"reason": "empty-compatible-class"}}
        return minimax(self.initial, self.terminal, self.choices, lambda state: state[3])

    def fixed_schedule(self):
        """Single ordinal command on every live branch. A legal stop may finish a branch."""
        @cache
        def choose(live):
            completed = 0
            remaining = {}
            for state, already in live:
                if self.terminal(state) is not None:
                    completed = max(completed, already)
                    continue
                options = dict((act, (price, children)) for act, price, children in self.choices(state))
                if not options:
                    return inf, ()
                remaining[state] = (already, options)
            if not remaining:
                return completed, ()
            common = set.intersection(*(set(options) for _, options in remaining.values()))
            best = inf
            sequence = ()
            for act in sorted(common):
                accrued = {}
                for already, options in remaining.values():
                    price, children = options[act]
                    for _, child in children:
                        accrued[child] = max(accrued.get(child, 0), already + price)
                future, suffix = choose(tuple(sorted(accrued.items())))
                value = max(completed, future)
                if value < best:
                    best, sequence = value, (act,) + suffix
            return best, sequence

        def expand(state, ordinal):
            verdict = self.terminal(state)
            if verdict:
                return {"verdict": verdict}
            act = sequence[ordinal]
            for name, _, branches in self.choices(state):
                if name == act:
                    return {"act": act, "next": {key: expand(child, ordinal + 1)
                                                 for key, child in branches}}
            raise ValueError("invalid fixed schedule")

        value, sequence = choose(((self.initial, 0),))
        return {"value": None if value == inf else value, "sequence": list(sequence),
                "policy": None if value == inf else expand(self.initial, 0),
                "states": choose.cache_info().currsize}


def joint_identity(profile, paths, labels):
    n = len(profile["stages"])

    def terminal(state):
        i, _, _, _, live = state
        if len(live) != 1:
            return None
        if labels[live[0]] == "NO":
            return "NO"
        if i == n:
            return "YES"
        return None

    def choices(state):
        i, meter, work_left, steps, live = state
        if i == n or steps == 0:
            return
        stage = profile["stages"][i]
        for command in command_names(stage, meter):
            rows = tuple(allowed_stage_row(stage, paths[j][i], meter, command) for j in live)
            if any(row is None for row in rows):
                continue
            work, price = rows[0][:2]
            if work > work_left:
                continue
            observations = sorted({event for row in rows for event in row[2]})
            children = tuple((branch_key(*event), (i + bool(work), event[1], work_left - work, steps - 1,
                                                   tuple(j for j, row in zip(live, rows, strict=True)
                                                         if event in row[2])))
                             for event in observations)
            yield command, price, children

    start = (0, profile["initial_meter"], profile["deadline"], profile["horizon"],
             tuple(range(len(paths))))
    return minimax(start, terminal, choices, lambda state: state[3])


def stage_panels(stage):
    options = {}
    menu = stage["statics"]
    for mask in range(1 << len(menu)):
        chosen = tuple(item for i, item in enumerate(menu) if mask & (1 << i))
        rows = [tuple(static_answer(item, edge) for item in chosen) for edge in stage["edges"]]
        same = tuple(a == b for a, b in product(rows, repeat=2))
        price = sum(item["price"] for item in chosen)
        ordering = tuple(item["id"] for item in chosen)
        if same not in options or (price, ordering) < options[same][:2]:
            options[same] = price, ordering, chosen
    return sorted(options.values(), key=lambda opt: opt[:2])


def paired_witness(profile, selection, identity=False):
    """Two-copy serial graph, with accepting route witnesses and clipped costs."""
    cap = profile["deadline"] + 1
    initial = profile["start"]
    reachable = {(initial, initial, 0, 0, False): ((), ())}
    for stage, reads in zip(profile["stages"], selection, strict=True):
        next_states = {}
        edge_pairs = []
        for left, right in product(stage["edges"], repeat=2):
            if all(static_answer(item, left) == static_answer(item, right) for item in reads):
                edge_pairs.append((left, right))
        for (l, r, a, b, distinct), (witness_l, witness_r) in reachable.items():
            for left, right in edge_pairs:
                if (left["tail"], right["tail"]) != (l, r):
                    continue
                first = min(cap, a + stage["base"] + stage["premium"] * left["stale"])
                second = min(cap, b + stage["base"] + stage["premium"] * right["stale"])
                split = distinct or left["id"] != right["id"]
                key = left["head"], right["head"], first, second, split
                next_states.setdefault(key, (witness_l + (left["id"],), witness_r + (right["id"],)))
        reachable = next_states
    for (left, right, a, b, distinct), witness in reachable.items():
        if left in profile["accept"] and right in profile["accept"]:
            if (identity and distinct) or (not identity and (a < cap) != (b < cap)):
                return witness
    return None


def static_optimum(profile, identity=False):
    best = inf
    best_menu = None
    checked = 0
    all_reads = tuple(stage["statics"] for stage in profile["stages"])
    full_witness = paired_witness(profile, all_reads, identity)
    if full_witness is not None:
        return {"value": None, "queries": None, "full_menu_witness": full_witness,
                "panels_checked": 1}
    options = tuple(stage_panels(stage) for stage in profile["stages"])
    for combination in product(*options):
        total = sum(choice[0] for choice in combination)
        ids = tuple(q for option in combination for q in option[1])
        if total > best or (total == best and ids >= best_menu):
            continue
        checked += 1
        if paired_witness(profile, tuple(option[2] for option in combination), identity) is None:
            best, best_menu = total, ids
    if best_menu is None:
        raise AssertionError("complete menu resolves and an optimized panel must exist")
    return {"value": best, "queries": best_menu, "panels_checked": checked}


def pure_adaptive(profile, paths, labels, identity=False):
    items = tuple((i, item) for i, stage in enumerate(profile["stages"]) for item in stage["statics"])
    answers = tuple(tuple(static_answer(item, path[stage]) for path in paths)
                    for stage, item in items)
    goal = tuple(range(len(paths))) if identity else labels

    def terminal(live):
        if len({goal[j] for j in live}) == 1:
            return labels[live[0]]
        return None

    def choices(live):
        for i, (_, item) in enumerate(items):
            groups = {}
            for model in live:
                groups.setdefault(answers[i][model], []).append(model)
            if len(groups) < 2:
                continue
            yield item["id"], item["price"], tuple((result, tuple(members))
                                                 for result, members in sorted(groups.items()))

    outcome = minimax(tuple(range(len(paths))), terminal, choices, len)
    def read_tree(tree):
        if tree is None or "verdict" in tree:
            return tree
        return {"ask": tree["act"], "next": {key: read_tree(v) for key, v in tree["next"].items()}}
    outcome["policy"] = read_tree(outcome["policy"])
    return outcome


def forecast_profile(profile):
    paths = accepting_paths(profile)
    if not paths:
        raise ValueError(f"registered profile is empty: {profile['id']}")
    known = tuple(intrinsic_work(profile, path) for path in paths)
    labels = tuple("YES" if work <= profile["deadline"] else "NO" for work in known)
    projected = Frontier(profile)
    online = projected.solve()
    full = Frontier(profile, full_scores=True).solve()
    if online["value"] != full["value"]:
        raise AssertionError(f"frontier representations disagree: {profile['id']}")
    fixed = projected.fixed_schedule() if profile["id"] in OPEN_LOOP else None
    return {
        "targets": tuple({"path": tuple(edge["id"] for edge in path),
                          "known_work": work, "label": label}
                         for path, work, label in zip(paths, known, labels, strict=True)),
        "static_target": static_optimum(profile),
        "static_identity": static_optimum(profile, identity=True),
        "static_all": {"value": sum(item["price"] for stage in profile["stages"] for item in stage["statics"]),
                       "queries": tuple(item["id"] for stage in profile["stages"] for item in stage["statics"])},
        "adaptive_pure_target": pure_adaptive(profile, paths, labels),
        "adaptive_pure_identity": pure_adaptive(profile, paths, labels, identity=True),
        "online": online,
        "structured_scores": full,
        "online_identity": joint_identity(profile, paths, labels),
        "online_fixed": fixed,
    }


def forecast(catalogue):
    profiles = {profile["id"]: profile for profile in catalogue["profiles"]}
    valid = {name: forecast_profile(profiles[name]) for name in catalogue["valid_profiles"]}
    for name in profiles.keys() - valid.keys():
        # This value is an intentionally projected forecast, rejected by a control gate.
        valid[name] = forecast_profile(profiles[name])
    metered = json.loads(json.dumps(profiles["meter-h3"]))
    metered["stages"][0]["edges"][0]["gives"] = [
        give for give in metered["stages"][0]["edges"][0]["gives"] if give["meter"] != "LONG"
    ]
    extra = {"missing-long": Frontier(metered).solve()}
    return {"profiles": valid, "controls": extra}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("catalogue", type=Path)
    cli.add_argument("out", type=Path)
    args = cli.parse_args()
    document = json.loads(args.catalogue.read_text(encoding="utf-8"))
    dump(args.out, forecast(document))


if __name__ == "__main__":
    main()
