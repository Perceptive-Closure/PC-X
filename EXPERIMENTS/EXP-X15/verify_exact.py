"""Independent finite, optimization and timing checks for EXP-X01–X05."""

from collections import Counter, defaultdict
import csv
from fractions import Fraction
from functools import cache
from hashlib import sha256
from itertools import combinations, product
import json
from math import inf, prod
from statistics import median
import subprocess
import sys

FREEZES = ("none", "E", "R", "A", "ER", "EA", "RA", "ERA")
MASKS = tuple(frozenset(label) if label != "none" else frozenset() for label in FREEZES)

# These subprocesses expose raw generated inputs. The validators below only receive JSON.
X01_EXPORT = """
import json
from dataclasses import asdict
from pathlib import Path
from src.fixtures import factorial_cases, generated_cases, hand_cases
config = json.loads(Path('configs/protocol.json').read_bytes())
rows = [model for model, _ in (*factorial_cases(config), *hand_cases())]
rows.extend(generated_cases(config))
print(json.dumps([asdict(row) for row in rows], default=sorted))
"""
X03_EXPORT = """
import json
from dataclasses import asdict
from pathlib import Path
from src.corpus import cases
config = json.loads(Path('configs/protocol.json').read_bytes())
print(json.dumps([asdict(problem) for _, _, problem in cases(config)]))
"""


def ensure(condition, context):
    if not condition:
        raise AssertionError(context)


def read(path):
    return json.loads(path.read_bytes())


def jsonl(path):
    with path.open(encoding="utf-8") as stream:
        for row in stream:
            yield json.loads(row)


def csv_rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def export(package, script, destination):
    data = subprocess.check_output([sys.executable, "-B", "-c", script], cwd=package)
    destination.write_bytes(data)
    return json.loads(data)


def partition(labels):
    cells = defaultdict(list)
    for index, label in enumerate(labels):
        cells[label].append(index)
    return sorted(cells.values())


def history_class(model, state):
    label = state["representation"][state["history"]]
    admitted = {
        i for i, value in enumerate(state["representation"]) if value == label
    }
    return {
        target for target, compatible in zip(model["targets"], model["compatibility"], strict=True)
        if admitted.intersection(compatible)
    }


def source_digest(model):
    projection = {
        "raw_description": model["source"],
        "histories": model["histories"],
        "targets": model["targets"],
        "compatibility": model["compatibility"],
        "initial": model["initial"],
        "actions": sorted((a["name"], a["interface"], a["cost"]) for a in model["actions"]),
        "checkpoints": [
            [state["observation"],
             sorted((candidate["name"], sorted((b["state"], b["outcome"]) for b in candidate["support"]))
                    for candidate in state["candidates"])]
            for state in model["states"]
        ],
    }
    return sha256(json.dumps(projection, ensure_ascii=True, sort_keys=True).encode("ascii")).hexdigest()


def finite_horizon_cost(model, freeze, ablation=None):
    """Discover observable beliefs, then solve the bounded-depth Bellman recurrence."""
    states = model["states"]
    coords = [(state["history"], partition(state["representation"]), state["authority"]) for state in states]
    actions = {action["name"]: action for action in model["actions"]}
    choices = []
    for index, state in enumerate(states):
        allowed = {}
        for candidate in state["candidates"]:
            action = actions[candidate["name"]]
            if action["interface"] not in state["authority"]:
                continue
            for_touch = candidate["support"][:1] if ablation == "first" else candidate["support"]
            if any(
                left != right
                for branch in for_touch
                for resource, left, right in zip("ERA", coords[index], coords[branch["state"]], strict=True)
                if resource in freeze
            ):
                continue
            allowed[candidate["name"]] = candidate["support"]
        choices.append(allowed)

    closed = {i for i, state in enumerate(states) if len(history_class(model, state)) == 1}
    initial = (model["initial"],)
    discovered = {initial}
    graph = {}
    frontier = [initial]
    while frontier:
        belief = frontier.pop()
        outgoing = []
        graph[belief] = outgoing
        if set(belief) <= closed:
            continue
        for name in set.intersection(*(set(choices[i]) for i in belief)):
            possible = defaultdict(set)
            for index in belief:
                for branch in choices[index][name]:
                    endpoint = branch["state"]
                    observation = endpoint if ablation == "oracle" else states[endpoint]["observation"]
                    possible[(branch["outcome"], observation)].add(endpoint)
            children = [tuple(sorted(group)) for group in possible.values()]
            outgoing.append((actions[name]["cost"], children))
            for child in children:
                if child not in discovered:
                    discovered.add(child)
                    frontier.append(child)

    values = {belief: 0 if set(belief) <= closed else inf for belief in graph}
    for _ in range(len(graph)):
        next_values = {
            belief: min([values[belief], *(
                cost + max(values[child] for child in children)
                for cost, children in options
            )])
            for belief, options in graph.items()
        }
        if next_values == values:
            break
        values = next_values
    return "inf" if values[initial] == inf else values[initial]


def verify_x01(package, run, output):
    records = read(run / "details.json")
    models = {row["name"]: row for row in export(package, X01_EXPORT, output / "x01-inputs.json")}
    source_classes = defaultdict(list)
    signatures = {}
    for row in records["signatures"]:
        name = row["id"]
        model = models[name]
        digest = source_digest(model)
        ensure(row["source_sha256"] == digest, (name, "public source digest"))
        source_classes[digest].append(model)
        signature = tuple(finite_horizon_cost(model, mask) for mask in MASKS)
        ensure(tuple(row["signature"]) == signature, (name, "finite horizon", signature))
        costs = tuple(inf if x == "inf" else x for x in signature)
        ensure(all(costs[i] <= costs[j] for i, a in enumerate(MASKS)
                   for j, b in enumerate(MASKS) if a <= b), (name, "monotone freezes"))
        signatures[name] = signature

    verdicts = Counter()
    for row in records["evidence_refinements"]:
        compatible = []
        for model in source_classes[row["source_sha256"]]:
            coordinates = [
                {"H": state["history"], "R": partition(state["representation"]), "A": state["authority"]}
                for state in model["states"]
            ]
            if all(coordinates[index][coordinate] == value for index, coordinate, value in row["facts"]):
                compatible.append(model["name"])
        sigs = {signatures[name] for name in compatible}
        status = "INCONSISTENT" if not sigs else "IDENTIFIED" if len(sigs) == 1 else "UNDERIDENTIFIED"
        ensure(set(row["compatible"]) == set(compatible), (row["source_sha256"], row["facts"], "facts"))
        ensure({tuple(sig) for sig in row["signatures"]} == sigs and row["verdict"] == status,
               (row["source_sha256"], row["facts"], "signature set"))
        for name, signature in row["witnesses"]:
            ensure(name in compatible and signatures[name] == tuple(signature), ("invalid witness", row))
        ensure(len(row["witnesses"]) == len(sigs), ("incomplete witnesses", row))
        verdicts[status] += 1
        verdicts["witnesses"] += len(row["witnesses"])

    ablations = Counter()
    for row in records["ablation_controls"]:
        name = row["id"]
        mode = "oracle" if row["ablation"] == "full-state oracle" else "first"
        index = FREEZES.index(row["coordinate"])
        value = finite_horizon_cost(models[name], MASKS[index], mode)
        ensure(value == row["ablation_result"] and signatures[name][index] == row["exact"],
               (name, "ablation", row))
        ablations[f"{mode}_tested"] += 1
        ablations[f"{mode}_wrong"] += value != signatures[name][index]
    return {
        "contracts": len(models), "exact_coordinates": len(signatures) * len(MASKS),
        "source_groups": len(source_classes), "evidence_cases": len(records["evidence_refinements"]),
        "verdicts": dict(verdicts), "ablations": dict(ablations),
    }


def bit_condition(bits, condition):
    return condition if type(condition) is bool else bool(bits[abs(condition) - 1] == (condition > 0))


def admitted(bits, clauses):
    return all(any(bit_condition(bits, literal) for literal in clause) for clause in clauses)


def x02_signature(case, profile):
    signature = []
    for mask in MASKS:
        costs = {}
        for index in range(len(case["checkpoints"]) - 1, -1, -1):
            node = case["checkpoints"][index]
            costs[index] = 0 if node["terminal"] else min(
                (route["cost"] + max(costs[i] for i in route["successors"])
                 for route in case["routes"][index]
                 if not mask.intersection(profile[(index, route["name"])])),
                default=inf,
            )
        signature.append("inf" if costs[0] == inf else costs[0])
    return tuple(signature)


def verify_x02(package, run):
    source = package.parents[1]
    details = read(source / "scratch" / "x15-replay" / run.parent.name / "details.json")
    counts = Counter()
    for row in details["cases"]:
        case = row["case"]
        name = case["name"]
        locations = [(index, route["name"]) for index, routes in enumerate(case["routes"]) for route in routes]
        reported = {r["assignment"]: r for r in row.get("case_profiles", [])}
        exact = {}
        options = defaultdict(set)
        for bits in product((0, 1), repeat=len(case["features"])):
            if not admitted(bits, case["clauses"]):
                continue
            coordinate_rows = [
                tuple(bit_condition(bits, node[field]) for field in ("admit", "refine", "expand_authority"))
                for node in case["checkpoints"]
            ]
            ensure(all((e or r) == node["terminal"]
                       for (e, r, _), node in zip(coordinate_rows, case["checkpoints"], strict=True)),
                   (name, bits, "semantic closure boundary"))
            profile = {}
            for index, routes in enumerate(case["routes"]):
                for route in routes:
                    key = index, route["name"]
                    touch = frozenset(
                        resource for column, resource in enumerate("ERA")
                        if any(coordinate_rows[index][column] != coordinate_rows[branch][column]
                               for branch in route["successors"])
                    )
                    options[key].add(touch)
                    profile[key] = touch
            signature = x02_signature(case, profile)
            key = "".join(map(str, bits))
            exact[key] = signature
            ensure(tuple(reported[key]["signature"]) == signature, (name, bits, "irregular exact"))
            ensure([sorted(profile[loc]) for loc in locations] == reported[key]["touches"],
                   (name, bits, "touches"))
        joint = set(exact.values())
        rectangular = {
            x02_signature(case, dict(zip(locations, profile, strict=True)))
            for profile in product(*(options[loc] for loc in locations))
        } if exact else set()
        ensure(set(exact) == set(reported) and len(exact) == row["compatible_rows"], (name, "CNF domain"))
        ensure({tuple(s) for s in row["joint_signatures"]} == joint <= rectangular,
               (name, "joint inclusion"))
        ensure({tuple(s) for s in row["rectangular_signatures"]} == rectangular, (name, "rectangular set"))
        counts["cases"] += 1
        counts["compatible"] += len(exact)
        counts["nonempty"] += bool(exact)
        counts["strict_joint_relaxations"] += joint < rectangular
        if exact:
            counts["independent_marginal_overcoverage_cases"] += prod(
                len({sig[i] for sig in joint}) for i in range(len(MASKS))
            ) > len(joint)
            for i, evidence in enumerate(row["coordinate_results"]):
                true_values = {sig[i] for sig in joint}
                outer = {sig[i] for sig in rectangular}
                ordered = sorted(true_values, key=lambda value: inf if value == "inf" else value)
                expanded = sorted(outer, key=lambda value: inf if value == "inf" else value)
                ensure(ordered == evidence["exact_values"] and expanded == evidence["rectangular_values"],
                       (name, i, "coordinate sets"))
                endpoints = [ordered[0], ordered[-1]]
                ensure(endpoints == evidence["exact_bounds"] and [expanded[0], expanded[-1]] ==
                       evidence["rectangular_bounds"], (name, i, "bounds"))
                for endpoint, witness in zip(endpoints, ("lower_witness", "upper_witness"), strict=True):
                    answer = evidence[witness]
                    signature = exact[answer["assignment"]]
                    ensure(tuple(answer["signature"]) == signature and signature[i] == endpoint,
                           (name, i, "endpoint witness"))
                counts["false_coordinate_ambiguity"] += len(true_values) == 1 and len(outer) > 1
                counts["wider_coordinate_bounds"] += evidence["exact_bounds"] != evidence["rectangular_bounds"]
        for proof in row["witnesses"]:
            ensure(exact[proof["assignment"]] == tuple(proof["signature"]), (name, "joint witness"))
        for refinement in row["refinements"]:
            small = [sig for bits, sig in exact.items()
                     if admitted(tuple(map(int, bits)), refinement["added_clauses"])]
            ensure(len(small) == refinement["compatible_rows"]
                   and set(small) == {tuple(s) for s in refinement["joint_signatures"]}, (name, "refinement"))
    return dict(counts)


def subsets(width):
    return tuple(group for size in range(width + 1) for group in combinations(range(width), size))


def partition_costs(rows, costs, *, identity=False, realized=None):
    """Enumerate complete answer partitions and compute each feasible query subset."""
    if not rows:
        return "INCONSISTENT", None, set()
    minimum = inf
    ties = set()
    for group in subsets(len(costs)):
        cost = sum(costs[index] for index in group)
        if realized is None:
            cells = defaultdict(set)
            for row in rows:
                cells[tuple(row["answers"][i] for i in group)].add(row["identity"] if identity else row["target"])
            sufficient = all(len(cell) == 1 for cell in cells.values())
        else:
            actual = next(row for row in rows if row["identity"] == realized)
            conflicting = (
                row for row in rows
                if (row["identity"] if identity else row["target"]) !=
                   (actual["identity"] if identity else actual["target"])
            )
            sufficient = all(any(actual["answers"][i] != row["answers"][i] for i in group)
                             for row in conflicting)
        if sufficient:
            if cost < minimum:
                minimum = cost
                ties.clear()
            if cost == minimum:
                ties.add(group)
    return ("CERTIFIED", minimum, ties) if ties else ("AUDIT_INACCESSIBLE", None, set())


def verify_x03(package, output):
    data = {row["name"]: row for row in export(package, X03_EXPORT, output / "x03-inputs.json")}
    scopes = csv_rows(package / "results" / "scopes.csv")
    counts = Counter()
    comparator_costs = defaultdict(list)
    for row in scopes:
        case = data[row["case"]]
        rows = case["completions"]
        local = row["completion"] or None
        status, cost, choices = partition_costs(rows, case["costs"], realized=local)
        full_status, full_cost, _ = partition_costs(rows, case["costs"], identity=True, realized=local)
        ensure(status == row["status"] and (str(cost) if cost is not None else "") == row["optimum"],
               (row["case"], local, "certificate"))
        ensure(full_status == row["full_contract_status"] and
               (str(full_cost) if full_cost is not None else "") == row["full_contract_optimum"],
               (row["case"], local, "full contract"))
        ensure(len(choices) == int(row["optimum_ties"]), (row["case"], local, "optimum ties"))
        if status == "CERTIFIED":
            named = tuple(sorted(case["query_names"].index(q) for q in row["selected_queries"].split("|") if q))
            ensure(named in choices, (row["case"], local, "selected queries"))
            for comparator in ("greedy", "deletion", "exhaustive", "random"):
                attempted = Fraction(row[f"{comparator}_attempted_cost"])
                ensure(attempted >= cost, (row["case"], local, comparator))
                if local is None:
                    comparator_costs[comparator].append(attempted)
            if local is None:
                comparator_costs["minimum"].append(Fraction(cost))
        if status == "AUDIT_INACCESSIBLE":
            names = row["witness"].split("|")
            first, second = (next(item for item in rows if item["identity"] == name) for name in names)
            ensure(first["target"] != second["target"] and first["answers"] == second["answers"]
                   and (local is None or local in names), (row["case"], local, "collision witness"))
        counts[status] += 1
        counts["all_subset_domain_checks"] += (1 << len(case["costs"])) if rows else 0
    return {
        "domains": len(data), "scopes": len(scopes), "checks": dict(counts),
        "mean_finite_uniform_costs": {name: round(float(sum(values) / len(values)), 6)
                                      for name, values in sorted(comparator_costs.items())},
    }


def adaptive_value(rows, costs):
    @cache
    def solve(belief):
        if len({rows[i]["target"] for i in belief}) < 2:
            return 0
        options = []
        for query, cost in enumerate(costs):
            groups = defaultdict(list)
            for idx in belief:
                groups[rows[idx]["answers"][query]].append(idx)
            if len(groups) > 1:
                options.append(cost + max(solve(tuple(group)) for group in groups.values()))
        return min(options, default=inf)
    value = solve(tuple(range(len(rows)))) if rows else inf
    return None if value == inf else value


def verify_paths(case, replay):
    rows = case["rows"]
    names = {row["identity"]: row for row in rows}
    queries, costs = case["queries"], case["costs"]
    checked = 0
    for policy, traces in replay["policies"].items():
        ensure({row["completion"] for row in traces} == set(names) and len(traces) == len(names),
               (case["name"], policy, "trace coverage"))
        next_steps = {}
        for trace in traces:
            world = names[trace["completion"]]
            history = []
            belief = rows
            steps = set()
            spent = 0
            tree = replay.get("optimal_tree") if policy == "adaptive_optimum" else None
            for query, answer in trace["history"]:
                seen = tuple(history)
                ensure(next_steps.setdefault(seen, query) == query and query not in steps,
                       (case["name"], policy, "unobservable or repeated action"))
                query_index = queries.index(query)
                ensure(world["answers"][query_index] == answer, (case["name"], policy, "answer"))
                if tree is not None:
                    ensure(tree["query"] == query, (case["name"], policy, "tree action"))
                    tree = tree["answers"][answer]
                belief = [other for other in belief if other["answers"][query_index] == answer]
                steps.add(query)
                history.append((query, answer))
                spent += costs[query_index]
            ensure(next_steps.setdefault(tuple(history), None) is None, (case["name"], policy, "stop"))
            targets = {other["target"] for other in belief}
            if trace["status"] == "CERTIFIED":
                ensure(targets == {trace["certified_target"]} and trace["certified_target"] == world["target"],
                       (case["name"], policy, "false certificate"))
                if tree is not None:
                    ensure(tree == {"target": world["target"]}, (case["name"], policy, "tree target"))
            else:
                ensure(trace["certified_target"] is None, (case["name"], policy, "false favorable value"))
            ensure(spent == trace["cost"] and trace["actual_target"] == world["target"]
                   and trace["weight"] == world["weight"], (case["name"], policy, "cost, score, weight"))
            checked += 1
    return checked


def verify_x04(package):
    results = package / "results"
    summaries = {row["case"]: row for row in read(results / "summary.json")["cases"]}
    verified = Counter()
    routed = {}
    for case, replay in zip(jsonl(results / "tables.jsonl"), jsonl(results / "policy_replays.jsonl"), strict=True):
        name, rows, costs = case["name"], case["rows"], case["costs"]
        expected = summaries[name]
        ensure(replay["case"] == name, (name, "join"))
        value = adaptive_value(rows, costs)
        status, static, _ = partition_costs(rows, costs)
        ensure(value == expected["minimax_cost"] and static == expected["static_cost"]
               and status == expected["status"], (name, "minimax/static", value, static, status, expected))
        for row in rows:
            _, value_local, _ = partition_costs(rows, costs, realized=row["identity"])
            ensure(value_local == expected["local_costs"].get(row["identity"]), (name, "local optimum"))
        verified[status] += 1
        verified["policy_paths"] += verify_paths(case, replay)
        witness = expected["inaccessibility_witness"]
        if witness:
            a, b = [next(row for row in rows if row["identity"] == name) for name in witness]
            ensure(a["target"] != b["target"] and a["answers"] == b["answers"], (name, "interface collision"))
        if case["family"] == "routed_pc":
            routed[name] = {"adaptive": value, "static": static}
    return {"verified": dict(verified), "routed": routed}


def hit_cost(edges, prices):
    """A second weighted hitting-set optimizer for recorded refinement edges."""
    if any(not edge for edge in edges):
        return None
    reduced = tuple(sorted(set(frozenset(edge) for edge in edges), key=lambda s: (len(s), sorted(s))))
    reduced = tuple(edge for i, edge in enumerate(reduced) if not any(old <= edge for old in reduced[:i]))
    forced = {next(iter(edge)) for edge in reduced if len(edge) == 1}
    residual = tuple(edge for edge in reduced if not edge.intersection(forced))

    @cache
    def minimum(remaining):
        if not remaining:
            return 0
        return min(prices[q] + minimum(tuple(edge for edge in remaining if q not in edge))
                   for q in remaining[0])
    return sum(prices[q] for q in forced) + minimum(residual)


def verify_timing(package, fresh):
    stored = package / "results"
    performance = read(stored / "performance.json")["cases"]
    measured = defaultdict(list)
    for row in csv_rows(stored / "measurements.csv"):
        measured[(row["case"], row["method"], row["measurement"])].append(row)
    for (case, method, measurement), rows in measured.items():
        expected = performance[case][method]
        if measurement == "time":
            ensure(median(int(row["wall_ns"]) for row in rows) == expected["median_wall_ns"],
                   (case, method, "archived median"))
        else:
            ensure(max(int(row["peak_bytes"]) for row in rows) == expected["peak_python_bytes"],
                   (case, method, "archived memory"))
    run = {
        "archived_timing_observations": sum(len(rows) for key, rows in measured.items() if key[2] == "time"),
        "archived_memory_observations": sum(len(rows) for key, rows in measured.items() if key[2] == "allocation"),
    }
    if fresh is not None and fresh.is_file():
        fresh_performance = read(fresh)
        run["fresh_largest_lazy"] = fresh_performance["cases"]["large-matched-w3-n64-free"]["lazy"]
    return run


def verify_x05(package, fresh=None):
    rows = read(package / "results" / "invariants.json")
    checks = Counter()
    largest = {}
    for row in rows:
        name, budget, prices = row["case"], row["budget"], row["query_prices"]
        lazy = row["methods"]["lazy"]
        checks[lazy["status"]] += 1
        for method in ("lazy", "dominance-off"):
            record = row["methods"][method]
            edges = []
            for step in record.get("rounds", []):
                optimum = hit_cost(edges, prices)
                ensure(step["bound"] == optimum == sum(prices[q] for q in step["selected"]),
                       (name, method, "known-edge lower bound"))
                ensure(all(set(step["selected"]).intersection(edge) for edge in edges),
                       (name, method, "chosen subset hits known edges"))
                witness = step.get("witness")
                if witness is not None:
                    left, right = witness["costs"]
                    ensure((left is not None and left <= budget) != (right is not None and right <= budget),
                           (name, method, "threshold crossing"))
                    ensure(not set(step["selected"]).intersection(witness["edge"]),
                           (name, method, "selected answers agree"))
                    ensure(sum(a != b for a, b in zip(witness["left"], witness["right"], strict=True)) == 1,
                           (name, method, "single-stage perturbation"))
                    edges.append(witness["edge"])
                    checks["threshold_crossing_rounds"] += 1
                checks["refinement_round_bounds"] += 1
        if lazy["status"] in {"IDENTIFIED", "CERTIFIED"}:
            ensure(lazy["cost"] == row["reference"]["minimum_audit_cost"]
                   and lazy["cost"] == sum(prices[q] for q in lazy["selected"]), (name, "minimum audit"))
        if lazy["status"] == "UNRESOLVED":
            ensure(lazy["cost"] is None and lazy["value"] is None, (name, "refusal"))
        expected = (row["control"] or {}).get("expected_status")
        if expected is not None:
            ensure(expected == lazy["status"], (name, "frozen control", expected, lazy["status"]))
        if name == "large-matched-w3-n64-free":
            counts = lazy["counters"]
            ensure(lazy["compatible_count"] == 2 ** (64 * 3) and counts["materialized_completions"] == 0,
                   (name, "combinatorial count"))
            largest = {
                "case": name, "compatible_count": lazy["compatible_count"],
                "audit_cost": lazy["cost"], "all_query_cost": sum(prices),
                "materialized_completions": counts["materialized_completions"],
            }
    return {"cases": len(rows), "checks": dict(checks), "largest": largest, **verify_timing(package, fresh)}
