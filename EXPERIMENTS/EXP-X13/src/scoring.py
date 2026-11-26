"""Independent local and global scores from the physical trace and work order."""

from common import AGENTS, DESIGN, tickets


def score(context, ticket, rows, agents):
    """Use measured station/clock fields and the upstream workload only."""
    if tuple(ticket) not in tickets(context):
        raise ValueError("Invalid ticket in measurement")
    plan = DESIGN["contexts"][context][ticket[0]]
    expected = {(turn, name) for turn in range(len(plan)) for name in agents}
    observed = {}
    for row in rows:
        key = (row["turn"], row["agent"])
        if type(key[0]) is not int or key not in expected or key in observed:
            raise ValueError("Unexpected or duplicate event in physical ledger")
        station, quanta = row["station"], row["quanta"]
        if (station not in ("shared", f"private-{key[1]}") or quanta not in ([0], [0, 1])
                or any(type(step) is not int for step in quanta)):
            raise ValueError("Invalid physical placement or clock ticks")
        observed[key] = (station, set(quanta))
    if observed.keys() != expected:
        raise ValueError("Incomplete physical ledger")

    local = dict.fromkeys(agents, False)
    qualified = dict.fromkeys(agents, 0)
    processed = dict.fromkeys(agents, 0)
    conflict = False
    for (turn, name), (station, quanta) in observed.items():
        short = len(quanta) < plan[turn][AGENTS.index(name)]
        overlap = any(other_turn == turn and other_name != name and
                      station == other_station and bool(quanta & other_quanta)
                      for (other_turn, other_name), (other_station, other_quanta)
                      in observed.items())
        local[name] |= short
        conflict |= overlap
        processed[name] += 1
        qualified[name] += int(not short and not overlap)
    monitor = any(local.values())
    return {"local": local, "global": monitor or conflict,
            "collision": conflict, "outside_union": conflict and not monitor,
            "processed": processed, "qualified": qualified}
