"""Independent transport, composition and realizability checks for X12–X14."""

from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from fractions import Fraction as F
from functools import cache
from itertools import permutations, product
from math import prod

from falsify import radius
from verify_benchmarks import interval, load_ledger, mark_index, matches, overlap, threshold
from verify_exact import adaptive_value, ensure, partition_costs, read


def installation(spec, control, variant):
    origin = "stress" if control in {"changed_verdict", "fidelity_violation"} else "nominal"
    reference = spec["references"][origin]
    shifts = (0,) * (spec["horizon"] + 1) if control == "identical" else spec["shift_candidates"][control][variant]
    strata = spec["strata"]
    enroll = spec["enrollment"]["partial" if control == "missing_support" else "covered"]
    limits = {}
    for context, bases in reference.items():
        limits[context] = {
            stratum: tuple(value + shift for value, shift in zip(bases[stratum], shifts, strict=True))
            if stratum in bases else (spec["ticket_space"] * variant,) * len(shifts)
            for stratum in strata
        }
    return enroll, limits


def x12_violation(family, context, stratum, bits):
    first, *conditions = bits
    if family == "sorter":
        return bool(first ^ conditions[0] or any(conditions[1:]))
    pending = first
    for i, lost in enumerate(conditions):
        priority = i == 0 and context == "busy" and stratum == "priority"
        pending += lost + int(priority)
        # A larger incoming batch gets an extra unit of service; after the first
        # tick a preexisting queue gets a boost.
        boost = priority or (i > 0 and pending - lost > 0)
        pending = max(0, pending - boost)
    return pending > 0


def x12_risk(spec, family, context, stratum, limits):
    side = spec["ticket_space"]
    numerator = 0
    for bits in product((0, 1), repeat=len(limits)):
        if x12_violation(family, context, stratum, bits):
            numerator += prod(edge if bit else side - edge for edge, bit in zip(limits, bits, strict=True))
    return F(numerator, side ** len(limits))


def x12_score(family, ledger, initial):
    if family == "sorter":
        correct = 0
        for printed, _, sent, received in ledger:
            ensure(sent == received and received in (0, 1), "X12 sorter dispatch")
            correct += printed == received
        return correct < len(ledger), correct, len(ledger)
    pending = initial
    offered, served = initial, 0
    for arrivals, old, boost, completed, new in ledger:
        ensure(old == pending and boost in (0, 1) and 0 <= completed <= old + arrivals,
               "X12 queue supports")
        pending += arrivals - completed
        ensure(new == pending, "X12 queue ledger conservation")
        offered += arrivals
        served += completed
    return pending > 0, served, offered


def verify_x12(package):
    spec = read(package / "configs" / "protocol.json")
    results = package / "results"
    report, opening, forecast = (read(results / file) for file in ("summary.json", "opening.json", "forecast.json"))
    assignment = opening["private"]["assignment"]
    structure = {unit: installation(spec, row["control"], row["variant"]) for unit, row in assignment.items()}
    side, enrollment_space = spec["ticket_space"], spec["enrollment_space"]
    n = spec["samples"]["holdout"]
    raw_hash, raw = load_ledger(results / "observations.jsonl.gz")
    seen = set()
    counts = defaultdict(Counter)
    populations = defaultdict(Counter)
    for unit, context, index, selection, tickets, initial, ledger in raw:
        key = unit, context
        mark_index(seen, key, index, n)
        ensure(len(ledger) == spec["horizon"] and 0 <= selection < enrollment_space
               and all(0 <= draw < side for draw in tickets), (key, "X12 support"))
        enroll, limits = structure[unit]
        tape = [stratum for stratum, weight in zip(spec["strata"], enroll[context], strict=True)
                for _ in range(weight)]
        stratum = tape[selection]
        populations[key][stratum] += 1
        family = assignment[unit]["family"]
        bits = [int(draw < cutoff) for draw, cutoff in zip(tickets, limits[context][stratum], strict=True)]
        event, served, offered = x12_score(family, ledger, initial)
        ensure(initial == bits[0] and event is x12_violation(family, context, stratum, bits),
               (key, index, "X12 native-vs-risk vector"))
        counts[key].update(n=1, events=event, completed=served, offered=offered)

    units, context_count = len(assignment), len(spec["contexts"])
    covered = spec["strata"][:-1]
    family = {
        "reference": len(spec["families"]) * len(spec["references"]) * context_count * len(covered),
        "paired": units * context_count * len(covered) * (spec["horizon"] + 1),
        "full": units * context_count * len(covered),
        "holdout": units * context_count,
    }
    ensure(family == report["confidence"]["multiplicity"], "X12 interval family")
    half = {name: radius(spec["samples"][name], k, spec["alpha"][name]) for name, k in family.items()}
    ensure(all(matches(value, report["confidence"]["hoeffding_radius"][name]) for name, value in half.items()),
           "X12 confidence width")
    ensure(matches(sum(spec["alpha"].values()), report["confidence"]["simultaneous_alpha_budget"]),
           "X12 alpha allocation")

    counts_by_comparator = defaultdict(Counter)
    costs = Counter()
    coverage = 0
    coupling_records = 0
    for unit, row in assignment.items():
        published = report["units"][unit]
        enroll, limits = structure[unit]
        bounds = {}
        exact = {}
        for context in spec["contexts"]:
            key = unit, context
            cell = counts[key]
            combined = dict(cell, enrollment_n={s: populations[key][s] for s in spec["strata"]})
            ensure(cell["n"] == n and combined == published["observed"][context], (key, "X12 denominators"))
            bounds[context] = interval(cell["events"] / n, half["holdout"])
            ensure(all(matches(a, b) for a, b in zip(bounds[context], published["native"]["contexts"][context], strict=True)),
                   (key, "X12 holdout bound"))
            exact[context] = sum(F(weight, enrollment_space)
                * x12_risk(spec, row["family"], context, stratum, limits[context][stratum])
                for stratum, weight in zip(spec["strata"], enroll[context], strict=True))
            ensure(exact[context] == F(published["exact_context_risk"][context]), (key, "X12 exact risk"))
            if row["control"] != "fidelity_violation":
                bank = "stress" if row["control"] == "changed_verdict" else "nominal"
                for stratum in covered:
                    prior = spec["references"][bank][context][stratum]
                    posterior = limits[context][stratum]
                    shifts = [F(abs(a - b), side) for a, b in zip(prior, posterior, strict=True)]
                    gap = abs(x12_risk(spec, row["family"], context, stratum, prior)
                              - x12_risk(spec, row["family"], context, stratum, posterior))
                    ensure(gap <= 1 - prod(1 - p for p in shifts) <= min(1, sum(shifts)),
                           (key, stratum, "X12 union coupling"))
                    coupling_records += 1

        exact_verdict = "safe" if max(exact.values()) <= F(str(spec["risk_threshold"])) else "unsafe"
        measured = {True: "safe", False: "unsafe", None: "abstain"}[threshold(
            list(bounds.values()), spec["risk_threshold"],
        )]
        ensure(exact_verdict == published["exact_verdict"] and measured == published["native"]["verdict"],
               (unit, "X12 exact and native decisions"))
        for method, registered in published["comparators"].items():
            decision = forecast["units"][unit][method]["verdict"]
            ensure(registered["verdict"] == decision, (unit, method, "X12 forecast"))
            counter = counts_by_comparator[method]
            counter["certified"] += decision != "abstain"
            counter["abstained"] += decision == "abstain"
            counter["native_confirmed"] += decision == measured and decision != "abstain"
            counter["false_safe"] += decision == "safe" and exact_verdict == "unsafe"
            counter["false_unsafe"] += decision == "unsafe" and exact_verdict == "safe"
        for context, bound in forecast["units"][unit]["anchored"]["contexts"].items():
            coverage += max(bound[0], bounds[context][0]) <= min(bound[1], bounds[context][1])
            ensure(overlap(bound, [exact[context], exact[context]]),
                   (unit, context, "X12 transported envelope"))
            uncovered = F(enroll[context][-1], enrollment_space)
            ensure(matches(uncovered, published["uncovered_mass"][context]), (unit, context, "X12 uncovered mass"))
        costs.update(published["cost"])

    ensure(len(seen) == report["native_episodes"] and coverage == family["holdout"], "X12 coverage")
    for method, observed in counts_by_comparator.items():
        ensure(all(report["metrics"][method][name] == count for name, count in observed.items()),
               (method, "X12 measured comparators"))
    ensure(all(matches(total, report["unit_cost_totals"][name]) for name, total in costs.items()), "X12 cost totals")
    return {
        "native_episodes": len(seen), "raw_sha256": raw_hash, "native_radius": half["holdout"],
        "interval_family": family, "anchored_interval_overlaps": coverage, "exact_coupling_cases": coupling_records,
        "cost_totals": dict(costs), "comparators": {key: dict(value) for key, value in counts_by_comparator.items()},
    }


def x13_history(events, agent):
    return [tuple(row[k] for k in ("turn", "seen", "previous", "preferred", "requested", "quanta"))
            for row in events if row["agent"] == agent]


def x13_physics(spec, context, ticket, events, agents):
    work = spec["contexts"][context][ticket[0]]
    observed = {(event["agent"], event["turn"]): event for event in events}
    ensure(len(observed) == len(events) == len(work) * len(agents), (context, ticket, "X13 row coverage"))
    occupancy = defaultdict(set)
    shortages = Counter()
    feasible = {}

    for turn, needs in enumerate(work):
        for name in agents:
            row = observed[name, turn]
            ensure(row["station"] in {"shared", f"private-{name}"} and row["quanta"] in ([0], [0, 1]),
                   (context, ticket, name, "X13 station"))
            enough = len(row["quanta"]) >= needs[spec["agents"].index(name)]
            shortages[name] += not enough
            feasible[name, turn] = enough
            for instant in row["quanta"]:
                occupancy[turn, row["station"], instant].add(name)
    colliding_jobs = {(agent, tick) for (tick, _, _), names in occupancy.items()
                      if len(names) > 1 for agent in names}
    qualified = {name: sum(feasible[name, tick] and (name, tick) not in colliding_jobs
                           for tick in range(len(work))) for name in agents}
    return shortages, qualified, bool(colliding_jobs)


def verify_x13(package):
    spec = read(package / "configs" / "protocol.json")
    results = package / "results"
    published = read(results / "summary.json")
    predicted = read(results / "forecast.json")["prediction"]
    agents = spec["agents"]
    raw_hash, raw = load_ledger(results / "episodes.jsonl.gz")
    seen = set()
    counts = {}
    for row in raw:
        port, context, ticket = row["port"], row["context"], tuple(row["ticket"])
        key = port, context, ticket
        ensure(key not in seen and 0 <= ticket[0] < len(spec["contexts"][context])
               and 0 <= ticket[1] < spec["tempo_tickets"], (key, "X13 ticket support"))
        seen.add(key)
        c = counts.setdefault(port, {}).setdefault(context, {
            **dict.fromkeys(("episodes", "global", "outside_union", "collision", "both_local", "local_union"), 0),
            **{name: dict.fromkeys(agents, 0) for name in
               ("isolated_local", "joint_local", "history_mismatch", "processed", "qualified")},
        })
        shortages, qualified, collision = x13_physics(spec, context, ticket, row["joint"], agents)
        c["episodes"] += 1
        c["local_union"] += bool(sum(shortages.values()))
        c["both_local"] += all(shortages[agent] > 0 for agent in agents)
        c["collision"] += collision
        c["global"] += collision or bool(sum(shortages.values()))
        c["outside_union"] += collision and not bool(sum(shortages.values()))
        for agent in agents:
            isolated, _, _ = x13_physics(spec, context, ticket, row["isolated"][agent], [agent])
            c["isolated_local"][agent] += isolated[agent] > 0
            c["joint_local"][agent] += shortages[agent] > 0
            c["history_mismatch"][agent] += x13_history(row["isolated"][agent], agent) != x13_history(row["joint"], agent)
            c["processed"][agent] += len(spec["contexts"][context][ticket[0]])
            c["qualified"][agent] += qualified[agent]
    ensure(len(seen) == published["joint_episodes"] and raw_hash == published["raw_sha256"], "X13 raw identity")
    local = F(spec["thresholds"]["local_episode_risk"])
    global_ = F(spec["thresholds"]["global_episode_risk"])
    needed = F(spec["thresholds"]["minimum_qualified_fraction_per_agent"])
    judgments = {}
    for port, contexts in counts.items():
        for context, row in contexts.items():
            ensure(row["episodes"] == len(spec["contexts"][context]) * spec["tempo_tickets"], (port, context))
        ensure(contexts == published["ports"][port]["contexts"] == predicted[port]["contexts"],
               (port, "X13 physical aggregate"))
        denominators = [(cell, agent) for cell in contexts.values() for agent in agents]
        isolated = all(F(cell["isolated_local"][agent], cell["episodes"]) <= local for cell, agent in denominators)
        carried = all(F(cell["joint_local"][agent], cell["episodes"]) <= local for cell, agent in denominators)
        contained = all(cell["outside_union"] == 0 for cell in contexts.values())
        useful = all(F(cell["qualified"][agent], cell["processed"][agent]) >= needed for cell, agent in denominators)
        worst = max(F(cell["global"], cell["episodes"]) for cell in contexts.values())
        bound = min(F(1), len(agents) * local) if carried and contained else None
        j = {
            "isolated_certificates_valid": isolated,
            "local_history_preserved": all(cell["history_mismatch"][agent] == 0 for cell, agent in denominators),
            "local_bounds_carried_over": carried, "event_containment": contained,
            "qualified_work": useful, "global_threshold_met": worst <= global_,
            "worst_global_risk": str(worst), "composed_bound": str(bound) if bound is not None else None,
            "useful_certificate": isolated and bound is not None and bound <= global_ and useful,
        }
        ensure(j == published["ports"][port]["judgments"] == predicted[port]["judgments"], (port, "X13 judgment"))
        judgments[port] = j
    return {
        "raw_sha256": raw_hash, "joint_episodes": len(seen), "isolated_episodes": len(seen) * len(agents),
        "ports": judgments, "naive_false_certifications": [name for name, j in judgments.items()
                                                         if not j["global_threshold_met"]],
    }


@dataclass(frozen=True)
class Bench:
    profile: str
    signed: bool
    slip: int
    jobs: tuple = ()
    refined: bool = False
    licensed: bool = False
    stopped: bool = False


def bench_authority(spec, state):
    if state.stopped or len(state.jobs) == len(spec["jobs"]):
        return set()
    room = spec["profiles"][state.profile]
    actions = {"refuse", "refine", "layout"}
    if room["relief"]:
        actions.add("grant")
    if state.signed:
        actions.add("plate")
    if "buffer" not in state.jobs:
        actions.update(("left", "right"))
        if not state.jobs:
            actions.add("buffer")
        if state.licensed:
            actions.add("relief")
    return actions


def bench_step(spec, state, action):
    if action not in bench_authority(spec, state):
        return "unauthorized", None, state
    room = spec["profiles"][state.profile]
    panel = f"offer-{state.slip}" if state.refined or room["panel"] == "indexed" else "queued"
    if action == "refuse":
        return "ok", "stopped", replace(state, stopped=True)
    if action == "layout":
        return "ok", f"layout-{room['entry']}", state
    if action == "plate":
        return "ok", "two-slots", state
    if action == "grant":
        return "ok", "granted", replace(state, licensed=True)
    if action == "refine":
        panel = f"offer-{state.slip}" if state.jobs and "buffer" not in state.jobs else "reindexed"
        return "ok", panel, replace(state, refined=True)
    if action in {"left", "right"}:
        entry = room["entry"]
        legal = entry == "both" or (entry in {"left", "right"} and (action == entry) != bool(state.jobs and state.slip))
        if not legal:
            return "unsafe", None, state
    successor = replace(state, jobs=state.jobs + (action,))
    observation = "complete" if len(successor.jobs) == len(spec["jobs"]) else "buffered" if action == "buffer" else panel
    return "ok", observation, successor


def winning_minimum(spec, scope, omniscient=False):
    if scope["evidence"] != "two-slots":
        return None
    root = frozenset(Bench(profile, signed, slip)
        for profile, signed, slip in product(scope["profiles"], scope.get("signatures", [False, True]), spec["slips"]))

    @cache
    def feasible(belief, ticks, budget):
        if all(len(state.jobs) == len(spec["jobs"]) for state in belief):
            return True
        if not ticks or any(state.stopped or "buffer" in state.jobs for state in belief):
            return False
        for action in scope["actions"]:
            price = spec["cost"].get(action, 0)
            if price > budget:
                continue
            outcomes = defaultdict(set)
            for state in belief:
                status, observation, successor = bench_step(spec, state, action)
                if status != "ok":
                    break
                signal = (observation, state.slip) if omniscient and successor.jobs else observation
                outcomes[signal].add(successor)
            else:
                if all(feasible(frozenset(b), ticks - 1, budget - price) for b in outcomes.values()):
                    return True
        return False

    upper = scope["horizon"] * max(spec["cost"].values())
    for budget in range(upper + 1):
        if feasible(root, scope["horizon"], budget):
            return budget
    return None


def x14_event_score(spec, scope, state, trace, policy):
    cost = 0
    finished = None
    for tick, row in enumerate(trace["events"], 1):
        ensure(finished is None and tick == row["tick"] <= scope["horizon"], ("X14 tick", tick))
        action = row["action"]
        if policy is not None:
            ensure(action == policy["action"], ("X14 sealed policy selection", tick))
        available = bench_authority(spec, state)
        ensure(sorted(available) == row["authorized_before"], ("X14 pre-action authority", tick))
        status, signal, after = bench_step(spec, state, action) if action in scope["actions"] else (
            "unauthorized", None, state,
        )
        physical = {"order": spec["jobs"][len(state.jobs)], "bench": action} if len(after.jobs) > len(state.jobs) else None
        ensure((status, signal, physical) == (row["status"], row["observation"], row["physical_job"]),
               ("X14 physical ticket", tick))
        if status == "ok":
            cost += spec["cost"].get(action, 0)
        finished = status if status != "ok" else (
            "refused" if after.stopped else "complete" if len(after.jobs) == len(spec["jobs"]) else None
        )
        if finished is None and policy is not None:
            ensure(signal in policy["branches"], ("X14 sealed branch not defined", signal))
            policy = policy["branches"][signal]
        state = after
    if finished is None:
        ensure(len(trace["events"]) == scope["horizon"] and trace["finish"] == "deadline", "X14 deadline")
        finished = "deadline"
    ensure(trace["finish"] == finished, "X14 terminal score")
    return {
        "finish": finished, "qualified": len(state.jobs), "audit_cost": cost,
        "safe": finished not in {"unsafe", "unauthorized"}, "useful": finished == "complete",
    }


def verify_x14(package):
    spec = read(package / "configs" / "protocol.json")
    results = package / "results"
    exact, preaudit, forecast, opening, reported, receipt = (read(results / file) for file in
        ("exact.json", "pre-audit.json", "forecast.json", "opening.json", "summary.json", "audit-receipt.json"))
    checked = Counter()
    controls = {}
    for name, row in exact["outcomes"].items():
        scope = row["scope"]
        optimum = winning_minimum(spec, scope)
        status = "inconsistent" if scope["evidence"] != "two-slots" else "infeasible" if optimum is None else "winning"
        ensure((status, optimum) == (row["certificate"]["status"], row["certificate"]["cost"]),
               (name, "X14 robust bounded minimum", status, optimum))
        if status != "inconsistent":
            for ident, cost in row["single_contract_costs"].items():
                profile, signed = ident.split(":")
                single = dict(scope, profiles=[profile], signatures=[bool(int(signed))])
                ensure(winning_minimum(spec, single) == cost
                       and winning_minimum(spec, single, True) == row["omniscient_costs"][ident],
                       (name, ident, "X14 single-contract and oracle"))
        checked[status] += 1
        if name in spec["controls"]:
            controls[name] = {"status": status, "cost": optimum}

    ports = spec["heldout"]["ports"]
    modes = spec["heldout"]["profiles"]
    fee = spec["heldout"]["query_cost"]
    costs = {f"{kind}-{port}": fee[kind] for kind in ("layout", "viewer") for port in ports}
    costs.update({name: fee[name] for name in ("nameplate", "roster")})
    names = sorted(costs)
    def answer(query, placements, signed):
        if query == "nameplate":
            return "two-slots"
        if query == "roster":
            return signed
        kind, port = query.split("-")
        return spec["profiles"][placements[ports.index(port)]]["entry" if kind == "layout" else "panel"]

    audit_table = [
        {"identity": str((placements, signed)), "target": placements,
         "answers": [answer(query, placements, signed) for query in names]}
        for placements, signed in product(permutations(modes), (False, True))
    ]
    prices = [costs[q] for q in names]
    adaptive = adaptive_value(audit_table, prices)
    static = partition_costs(audit_table, prices)[1]
    full = partition_costs(audit_table, prices, identity=True)[1]
    ensure(adaptive == preaudit["audit"]["minimum_worst_cost"]
           and static == preaudit["comparators"]["static_target"]["cost"]
           and full == preaudit["comparators"]["static_full_identity"]["cost"], "X14 external minima")
    surviving = audit_table
    for evidence in receipt["reads"]:
        index = names.index(evidence["query"])
        surviving = [row for row in surviving if row["answers"][index] == evidence["value"]]
    ensure(len(surviving) == forecast["remaining_compatible_installations"] and len({c["target"] for c in surviving}) == 1
           and sum(costs[q["query"]] for q in receipt["reads"]) == receipt["cost"],
           "X14 legitimate target posterior")

    raw_hash, raw = load_ledger(results / "ledger.jsonl")
    ensure(raw_hash == reported["ledger_sha256"], "X14 ledger hash")
    scores = defaultdict(Counter)
    seen = set()
    signatures = defaultdict(dict)
    for row in raw:
        port, arm, slip = (row[name] for name in ("port", "arm", "slip"))
        ensure((port, arm, slip) not in seen, (port, arm, slip, "X14 duplicate ticket"))
        seen.add((port, arm, slip))
        sealed = opening["sealed"]
        profile = sealed["profiles"][port]
        state = Bench(profile, sealed["signature"], slip)
        choices = forecast["policies"][port]
        policy = choices[arm] if arm in choices else None
        score = x14_event_score(spec, forecast["scope"], state, row["trace"], policy)
        ensure(score == row["score"] == forecast["prediction"][port][arm][str(slip)],
               (port, arm, slip, "X14 independently scored verdict"))
        counts = scores[arm]
        counts["tickets"] += 1
        counts["safe"] += score["safe"]
        counts["useful"] += score["useful"]
        counts["qualified_jobs"] += score["qualified"]
        counts["worst_audit_cost"] = max(counts["worst_audit_cost"], score["audit_cost"])
        counts[score["finish"]] += 1
        signatures[profile][arm, slip] = tuple(sorted(score.items()))
    ensure(seen == set(product(ports, spec["heldout"]["arms"], spec["slips"])) and len(seen) == reported["exact_matches"],
           "X14 complete frozen support")
    ensure(len({tuple(sorted(rows.items())) for rows in signatures.values()}) == len(modes),
           "X14 profile classes do not match deployment signatures")
    return {
        "exact_scenarios": len(exact["outcomes"]), "scenarios": dict(checked), "controls": controls,
        "compatible_installations": len(audit_table), "external_audit_worst": adaptive,
        "static_target_cost": static, "static_full_identity_cost": full, "realized_external_cost": receipt["cost"],
        "posterior": len(surviving), "native_tickets": len(seen), "raw_sha256": raw_hash,
        "scores": {arm: dict(score) for arm, score in scores.items()},
    }
