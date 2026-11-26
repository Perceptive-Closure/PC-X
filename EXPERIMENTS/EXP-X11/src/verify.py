"""Read the external ledger and verify observations against an independent transition rule."""

from collections import Counter
from itertools import product

from common import digest
from sandbox import calibrate, run_sequence


def score_ledger(ledger, horizon, backlogged_rounds):
    """Score machine-reported inputs and outputs without policy or simulator state."""
    if len(ledger) != horizon:
        raise ValueError("Incomplete service ledger")
    balance = 0
    late = 0
    for arrivals, completions in ledger:
        if (type(arrivals) is not int or type(completions) is not int
                or arrivals < 0 or completions < 0 or completions > balance + arrivals):
            raise ValueError("Invalid service ledger")
        balance += arrivals - completions
        late += balance > 0
    return int(late >= backlogged_rounds)


def verify_pulse(protocol, query, raw):
    if not isinstance(raw, dict):
        raise ValueError("Invalid isolated capacity readback")
    if query == "display_slots":
        if raw != {"display_slots": protocol["advertised_slots"]}:
            raise ValueError("Impossible display readback")
        return raw["display_slots"]
    supplied = protocol["pulse_work"]
    done = raw.get("completed")
    if (query not in protocol["query_costs"] or type(done) is not int
            or done not in (protocol["disturbed_capacity"], protocol["normal_capacity"])
            or raw != {"start": [0, 0], "supplied": supplied, "completed": done,
                       "end": [1, supplied - done]}):
        raise ValueError("Invalid isolated capacity readback")
    if query == "original_capacity" and done != protocol["normal_capacity"]:
        raise ValueError("Invalid original capacity")
    return done


def verify_path(protocol, arm, measured_capacity, steps, frames):
    """Reconstruct public and retained private events without calling the sandbox."""
    if len(steps) != len(frames):
        raise ValueError("Incomplete trajectory")
    prior_surge = False
    backlog = 0
    for tick, ((request, actor_ticket, workload_ticket), frame) in enumerate(
            zip(steps, frames, strict=True), 1):
        if (request not in protocol["requests"] or tick > protocol["horizon"]
                or any(type(ticket) is not int or ticket not in range(protocol["tickets"])
                       for ticket in (actor_ticket, workload_ticket))):
            raise ValueError("Invalid trajectory input")
        current_surge = request == "surge"
        preparation = "standard" if actor_ticket > current_surge + prior_surge else "bulk"
        arrivals = (3 if current_surge else 2) + (1, 1, 0, 0)[workload_ticket]
        if preparation == "bulk":
            arrivals -= 1
        available = backlog + arrivals
        remaining = max(0, available - measured_capacity)
        public = [request, protocol["advertised_slots"], preparation, "accepted"]
        side = None
        if arm in protocol["ports"]:
            side = ["copy", public]
        if arm == "placebo":
            side = ["lamp", tick % 2]
        expected = [public, [arrivals, available - remaining], [tick, request, remaining], side]
        if frame != expected:
            raise ValueError(f"Unexpected {arm} event at tick {tick}")
        prior_surge = current_surge
        backlog = remaining


def pulse_controls(protocol):
    calibrations = {}
    for placement in protocol["ports"]:
        answers = {}
        for query in protocol["query_costs"]:
            raw = calibrate(protocol, query, placement)
            answers[query] = {"raw": raw, "value": verify_pulse(protocol, query, raw)}
        calibrations[placement] = answers
    return calibrations


def step_tickets(protocol):
    return tuple(product(range(protocol["tickets"]), repeat=2))


def exhaustive_public_support(protocol, calibrations):
    """Use one native prefix per reachable joint state and check all outgoing tickets."""
    cases = tuple(product(protocol["ports"], protocol["arms"]))
    capacities = [
        calibrations[placement]["original_capacity" if arm == "placebo" else f"{arm}_capacity"]["value"]
        for placement, arm in cases
    ]
    prefixes = {(): ()}
    states_by_depth = [1]
    rows = []
    witness = None
    private_deltas = 0
    for _ in range(protocol["horizon"]):
        successors = {}
        for state, prefix in prefixes.items():
            for request in protocol["requests"]:
                for actor_ticket, workload_ticket in step_tickets(protocol):
                    steps = prefix + ((request, actor_ticket, workload_ticket),)
                    terminals = []
                    for (placement, arm), capacity in zip(cases, capacities, strict=True):
                        frames = run_sequence(protocol, arm, placement, steps)
                        verify_path(protocol, arm, capacity, steps, frames)
                        terminals.append(frames[-1])
                    public = terminals[0][0]
                    if any(frame[0] != public for frame in terminals):
                        raise ValueError("Unexpected public distinction between completions or arms")
                    next_state = tuple(tuple(frame[2]) for frame in terminals)
                    successors.setdefault(next_state, steps)
                    rows.append([state, steps, public, next_state, [frame[1] for frame in terminals]])
                    if any(frame[1] != terminals[0][1] for frame in terminals):
                        private_deltas += 1
                        if witness is None:
                            witness = {
                                "steps": steps,
                                "same_public": public,
                                "cases": cases,
                                "machine_events": [frame[1] for frame in terminals],
                                "resulting_states": next_state,
                            }
        prefixes = successors
        states_by_depth.append(len(prefixes))
    if witness is None:
        raise ValueError("Service-count positive control did not distinguish a supported transition")
    return {"depth_state_counts": states_by_depth, "checked_rows": len(rows),
            "public_mismatches": 0, "private_event_distinctions": private_deltas,
            "rows_sha256": digest(rows), "observation_held_constant_witness": witness}


def paired_support(protocol, placement, arm, recipe):
    """Bound unmatched histories by max first divergence among matched prefixes."""
    prefixes = {(): ()}
    maxima = []
    support_rows = []
    for request in recipe:
        successors = {}
        mismatch_counts = []
        for matched_state, prefix in prefixes.items():
            mismatches = 0
            for policy_ticket, load_ticket in step_tickets(protocol):
                steps = prefix + ((request, policy_ticket, load_ticket),)
                original = run_sequence(protocol, "original", placement, steps)[-1]
                probe = run_sequence(protocol, arm, placement, steps)[-1]
                mismatch = original[:3] != probe[:3]
                mismatches += mismatch
                if not mismatch:
                    next_state = tuple(original[2])
                    successors.setdefault(next_state, steps)
                support_rows.append([matched_state, steps, original[:3], probe[:3], mismatch])
            mismatch_counts.append(mismatches)
        maxima.append(max(mismatch_counts, default=0))
        prefixes = successors
    return {"initial_mismatch": 0, "max_first_mismatch_counts": maxima,
            "tickets_per_state": len(step_tickets(protocol)), "checked_rows": len(support_rows),
            "rows_sha256": digest(support_rows)}


def exhaustive_scored_counts(protocol, recipe, placement, arm):
    """Count externally scored outcomes by physically executing the finite ticket bank."""
    positives = Counter()
    for tickets in product(step_tickets(protocol), repeat=protocol["horizon"]):
        steps = [(request, *pair) for request, pair in zip(recipe, tickets, strict=True)]
        frames = run_sequence(protocol, arm, placement, steps)
        label = score_ledger([frame[1] for frame in frames], protocol["horizon"],
                             protocol["label_backlogged_rounds"])
        positives[label] += 1
    return positives[1], positives.total()
