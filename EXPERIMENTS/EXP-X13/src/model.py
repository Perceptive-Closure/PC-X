"""Independent finite reference for trajectories, labels and composition gates."""

from fractions import Fraction

from common import AGENTS, CONTEXTS, DESIGN, MODES, TIES, canonical, digest, tickets


def reference(context, ticket, mode, first, agents):
    """Derive each expected row and score directly from the frozen transition rules."""
    load, tempo = ticket
    exclusive = mode[0] == "exclusive"
    compress = mode[1] == "shared_summary" and len(agents) == 2
    previous = dict.fromkeys(agents, 1)
    local = dict.fromkeys(agents, False)
    qualified = dict.fromkeys(agents, 0)
    processed = dict.fromkeys(agents, 0)
    conflict = False
    rows = []
    for turn, (alpha, beta) in enumerate(DESIGN["contexts"][context][load]):
        demands = dict(zip(AGENTS, (alpha, beta), strict=True))
        shared_demand = compress and alpha == beta == 2
        twin_request = len(agents) == 2 and tempo < 4
        collision_this_turn = twin_request and not exclusive
        conflict |= collision_this_turn
        for name in agents:
            staggered_bench = (turn % 2 == 0) == (name == AGENTS[0])
            seeks_shared = tempo < 4 or staggered_bench
            redirect = exclusive and twin_request and name != first
            own_bench = f"private-{name}"
            view = 1 if shared_demand else demands[name]
            fast_override = previous[name] == 1 and tempo == 0
            steps = 2 - int(view == 1 or fast_override)
            short = steps < demands[name]
            local[name] |= short
            processed[name] += 1
            qualified[name] += int(not short and not collision_this_turn)
            rows.append({
                "turn": turn, "agent": name, "seen": view, "previous": previous[name],
                "preferred": "shared" if seeks_shared else own_bench, "requested": steps,
                "station": "shared" if seeks_shared and not redirect else own_bench,
                "quanta": list(range(steps))
            })
            previous[name] = view
    violation = any(local.values())
    summary = {"local": local, "global": violation or conflict,
               "collision": conflict, "outside_union": conflict and not violation,
               "processed": processed, "qualified": qualified}
    return rows, summary


def local_history(rows, name):
    # Promised local duration depends on local input, memory, intent and actual
    # elapsed service. Station identity is absent from this policy and event.
    return [tuple(row[key] for key in ("turn", "seen", "previous", "preferred",
                                      "requested", "quanta"))
            for row in rows if row["agent"] == name]


def empty_counts():
    return {
        "episodes": 0, "isolated_local": dict.fromkeys(AGENTS, 0),
        "joint_local": dict.fromkeys(AGENTS, 0), "history_mismatch": dict.fromkeys(AGENTS, 0),
        "global": 0, "outside_union": 0, "collision": 0, "both_local": 0, "local_union": 0,
        "processed": dict.fromkeys(AGENTS, 0), "qualified": dict.fromkeys(AGENTS, 0)
    }


def accumulate(counts, isolated, joint, mismatched):
    counts["episodes"] += 1
    counts["both_local"] += int(all(joint["local"].values()))
    counts["local_union"] += int(any(joint["local"].values()))
    for key in ("global", "outside_union", "collision"):
        counts[key] += int(joint[key])
    for name in AGENTS:
        counts["isolated_local"][name] += int(isolated[name]["local"][name])
        counts["joint_local"][name] += int(joint["local"][name])
        counts["history_mismatch"][name] += int(mismatched[name])
        for key in ("processed", "qualified"):
            counts[key][name] += joint[key][name]


def decide(counts):
    limits = DESIGN["thresholds"]
    local_limit = Fraction(limits["local_episode_risk"])
    global_limit = Fraction(limits["global_episode_risk"])
    utility_minimum = Fraction(limits["minimum_qualified_fraction_per_agent"])
    isolated = all(Fraction(cell["isolated_local"][name], cell["episodes"]) <= local_limit
                   for cell in counts.values() for name in AGENTS)
    preserved = all(cell["history_mismatch"][name] == 0
                    for cell in counts.values() for name in AGENTS)
    carryover = all(Fraction(cell["joint_local"][name], cell["episodes"]) <= local_limit
                    for cell in counts.values() for name in AGENTS)
    containment = all(cell["outside_union"] == 0 for cell in counts.values())
    utility = all(
        cell["processed"][name] == 2 * cell["episodes"] and
        Fraction(cell["qualified"][name], 2 * cell["episodes"]) >= utility_minimum
        for cell in counts.values() for name in AGENTS
    )
    risk = max(Fraction(cell["global"], cell["episodes"]) for cell in counts.values())
    bound = min(Fraction(1), len(AGENTS) * local_limit) if containment and carryover else None
    return {"isolated_certificates_valid": isolated, "local_history_preserved": preserved,
            "local_bounds_carried_over": carryover, "event_containment": containment,
            "qualified_work": utility, "global_threshold_met": risk <= global_limit,
            "worst_global_risk": str(risk),
            "composed_bound": str(bound) if bound is not None else None,
            "useful_certificate": (isolated and bound is not None and bound <= global_limit
                                   and utility)}


def scenario(mode, first):
    cells = {}
    isolation_rows = []
    witnesses = {}
    for context in CONTEXTS:
        counts = empty_counts()
        for ticket in tickets(context):
            isolated = {}
            alone = {}
            for name in AGENTS:
                alone[name], isolated[name] = reference(context, ticket, mode, first, (name,))
                isolation_rows.append([context, ticket, name, alone[name], isolated[name]])
            joint, score = reference(context, ticket, mode, first, AGENTS)
            mismatch = {name: local_history(alone[name], name) != local_history(joint, name)
                        for name in AGENTS}
            accumulate(counts, isolated, score, mismatch)
            support_row = {"context": context, "ticket": list(ticket), "joint": joint,
                           "isolated": alone, "scored_joint": score}
            if score["outside_union"]:
                witnesses.setdefault("outside_union", support_row)
            if any(score["local"][name] and not isolated[name]["local"][name] for name in AGENTS):
                witnesses.setdefault("new_local_violation", support_row)
            if all(score["local"].values()):
                witnesses.setdefault("both_local", support_row)
        cells[context] = counts
    return {"contexts": cells, "judgments": decide(cells), "witnesses": witnesses,
            "isolated_evidence_sha256": digest(canonical(isolation_rows))}


def mode_key(mode):
    return "/".join(mode)


def scenario_table():
    table = {}
    for mode in MODES:
        variants = [scenario(mode, first) for first in TIES]
        if any(row["contexts"] != variants[0]["contexts"] or
               row["judgments"] != variants[0]["judgments"] for row in variants[1:]):
            raise ValueError("Tie-roster nuisance changes a frozen target")
        table[mode_key(mode)] = variants[0]
    if len({row["isolated_evidence_sha256"] for row in table.values()}) != 1:
        raise ValueError("Compatible completions change admitted isolated evidence")
    return table
