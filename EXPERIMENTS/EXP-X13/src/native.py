"""Produce physical logs and compare independent scores with prospective predictions."""

import gzip
import json

from common import AGENTS, CONTEXTS, PORTS, canonical, digest, tickets
from model import accumulate, decide, empty_counts, local_history, reference
from sandbox import Workshop
from scoring import score


def schedule(seed):
    for port in PORTS:
        for context in CONTEXTS:
            order = sorted(tickets(context), key=lambda t: (digest(canonical([seed, context, *t])), t))
            for ticket in order:
                yield port, context, ticket


def execute(assignment, first, seed):
    plants = {port: Workshop(*assignment[port], first) for port in PORTS}
    for port, context, ticket in schedule(seed):
        workshop = plants[port]
        yield {"port": port, "context": context, "ticket": list(ticket),
               "isolated": {name: workshop.execute(context, ticket, (name,)) for name in AGENTS},
               "joint": workshop.execute(context, ticket, AGENTS)}


def evaluate(raw, assignment, first, seed, forecast):
    lines = raw.splitlines(keepends=True)
    counts = {port: {context: empty_counts() for context in CONTEXTS} for port in PORTS}
    witnesses = {}
    episodes = 0
    model_disagreements = []
    for (port, context, ticket), line in zip(schedule(seed), lines, strict=True):
        row = json.loads(line)
        if canonical(row) != line or (row["port"], row["context"], row["ticket"]) != (
                port, context, list(ticket)):
            raise ValueError("The physical ledger changed the committed ticket order or format")
        if set(row["isolated"]) != set(AGENTS):
            raise ValueError("Incomplete isolated executions")
        joint = row["joint"]
        isolated_score = {name: score(context, ticket, row["isolated"][name], (name,))
                          for name in AGENTS}
        joint_score = score(context, ticket, joint, AGENTS)
        mode = assignment[port]
        expected_joint = reference(context, ticket, mode, first, AGENTS)
        expected_isolated = {name: reference(context, ticket, mode, first, (name,))
                             for name in AGENTS}
        if ((joint, joint_score) != expected_joint or
                any((row["isolated"][name], isolated_score[name]) != expected_isolated[name]
                    for name in AGENTS)):
            model_disagreements.append({"port": port, "context": context, "ticket": list(ticket)})
        mismatch = {name: local_history(row["isolated"][name], name) != local_history(joint, name)
                    for name in AGENTS}
        accumulate(counts[port][context], isolated_score, joint_score, mismatch)
        evidence = {"context": context, "ticket": list(ticket), "joint": joint,
                    "isolated": row["isolated"], "scored_joint": joint_score}
        saved = witnesses.setdefault(port, {})
        if joint_score["outside_union"]:
            saved.setdefault("outside_union", evidence)
        if any(joint_score["local"][name] and not isolated_score[name]["local"][name]
               for name in AGENTS):
            saved.setdefault("new_local_violation", evidence)
        if all(joint_score["local"].values()):
            saved.setdefault("both_local", evidence)
        episodes += 1

    cells = {port: {"contexts": counts[port], "judgments": decide(counts[port])} for port in PORTS}
    wrong_ports = [port for port in PORTS if cells[port] != forecast["prediction"][port]]
    naive_errors = [port for port in PORTS if not cells[port]["judgments"]["global_threshold_met"]]
    supported = [port for port in PORTS if cells[port]["judgments"]["useful_certificate"]]
    if any(cells[port]["judgments"]["useful_certificate"] and
           not cells[port]["judgments"]["global_threshold_met"] for port in PORTS):
        raise ValueError("Invalid composition certificate")
    return {"joint_episodes": episodes, "isolated_episodes": episodes * len(AGENTS),
            "ports": cells, "witnesses": witnesses, "forecast_mismatch_ports": wrong_ports,
            "reference_disagreements": model_disagreements, "useful_certified_ports": supported,
            "naive_false_certifications": naive_errors,
            "confirmed": not wrong_ports and not model_disagreements and len(supported) == 1}


def render(assignment, first, seed, forecast):
    raw = b"".join(canonical(row) for row in execute(assignment, first, seed))
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    summary = evaluate(raw, assignment, first, seed, forecast)
    summary.update({"raw_sha256": digest(raw), "gzip_sha256": digest(compressed)})
    return compressed, summary
