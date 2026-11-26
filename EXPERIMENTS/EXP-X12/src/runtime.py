"""Executable offline task policies and independently exposed machine records."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from random import Random


ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "configs" / "protocol.json").read_bytes())
FAMILIES = tuple(CONFIG["families"])
CONTEXTS = tuple(CONFIG["contexts"])
STRATA = tuple(CONFIG["strata"])
COVERED = STRATA[:2]
CONTROLS = tuple(CONFIG["controls"])
STAGES = range(CONFIG["horizon"] + 1)
TICKET_SPACE = CONFIG["ticket_space"]
ENROLLMENT_SPACE = CONFIG["enrollment_space"]
REFERENCES = {
    bank: {
        context: {stratum: tuple(values) for stratum, values in by_stratum.items()}
        for context, by_stratum in by_context.items()
    }
    for bank, by_context in CONFIG["references"].items()
}


@dataclass(frozen=True)
class Installation:
    family: str
    control: str
    bank: str
    limits: dict
    enrollment: dict
    novel_limit: int
    probe_overwrites: bool


def random_stream(seed, domain, *coordinates):
    key = json.dumps([seed, domain, *coordinates], separators=(",", ":"), ensure_ascii=True)
    return Random(int.from_bytes(sha256(key.encode("ascii")).digest(), "big"))


def install(family, control, variant):
    if family not in FAMILIES or control not in CONTROLS or variant not in (0, 1):
        raise ValueError("Unknown frozen installation")
    bank = "stress" if control == "changed_verdict" else "nominal"
    origin = "stress" if control in ("changed_verdict", "fidelity_violation") else "nominal"
    limits = REFERENCES[origin]
    if control != "identical":
        change = CONFIG["shift_candidates"][control][variant]
        limits = {
            context: {
                stratum: tuple(value + delta for value, delta in zip(limits[context][stratum], change))
                for stratum in COVERED
            }
            for context in CONTEXTS
        }
    enrollment_key = "partial" if control == "missing_support" else "covered"
    return Installation(
        family, control, bank, limits, CONFIG["enrollment"][enrollment_key],
        TICKET_SPACE * variant, control == "fidelity_violation",
    )


def enrollment_tape(counts):
    return [stratum for stratum, count in zip(STRATA, counts) for _ in range(count)]


def limits_for(installation, context, stratum):
    if stratum == "novel":
        return (installation.novel_limit,) * len(STAGES)
    return installation.limits[context][stratum]


def read_primitive(ticket, limit):
    return int(ticket < limit)


def probe(installation, ticket, limit, reference_limit, port):
    """The diagnostic may replace a setting before the machine reads its ticket."""
    active_limit = reference_limit if port == "audited" and installation.probe_overwrites else limit
    return read_primitive(ticket, active_limit)


def semantic_tape(family):
    """Readback of the fixed task and authority interface installed on both sides."""
    mappings = {
        "sorter": {
            "observation": ["display_tray"],
            "action": ["tray_0", "tray_1"],
            "decision": "reactive-display",
            "transition": "start-crosswire-then-independent-scans",
            "trusted_record": ["printed_tray", "received_tray"],
            "event": "any-received-tray-differs-from-printed-tray",
        },
        "queue": {
            "observation": ["new_jobs", "pending_jobs", "last_tick_pressure"],
            "action": ["single", "boost"],
            "decision": "arrival-or-prior-pressure",
            "transition": "initial-work-then-independent-capacity-losses",
            "trusted_record": ["initial_jobs", "arrivals", "completed"],
            "event": "jobs-left-at-close",
        },
    }
    return {
        **mappings[family],
        "protocol": "reset-and-run-three-ticks",
        "authority": ["covered-reset", "read-only-ticket-comparison", "independent-native-readback"],
        "covered": list(COVERED),
        "context_mapping": list(CONTEXTS),
        "monitor": "display-and-dispatch",
        "intervention": ["passive", "placebo-lamp", "audited"],
        "uncovered": "novel-enrollment-without-audit-authority",
    }


def episode(family, context, stratum, primitive_bits):
    """Run the policy against the three-tick machine and retain its ledger."""
    if family == "sorter":
        initial = primitive_bits[0]
        rows = []
        for tick, scan_error in enumerate(primitive_bits[1:]):
            printed = (tick + int(context == "busy") + int(stratum == "priority")) % 2
            shown = printed ^ scan_error ^ (initial if tick == 0 else 0)
            action = shown
            received = action
            rows.append([printed, shown, action, received])
        return initial, rows

    if family != "queue":
        raise ValueError("Unknown task family")
    initial = primitive_bits[0]
    pending = initial
    prior_pressure = False
    rows = []
    for tick, capacity_loss in enumerate(primitive_bits[1:]):
        arrival = 3 if context == "busy" and stratum == "priority" and tick == 0 else 2
        boost = int(prior_pressure or arrival == 3)
        completed = min(pending + arrival, 2 + boost - capacity_loss)
        after = pending + arrival - completed
        rows.append([arrival, pending, boost, completed, after])
        pending = after
        prior_pressure = after > 0
    return initial, rows


def execute(family, context, stratum, limits, tickets):
    bits = [read_primitive(ticket, limit) for ticket, limit in zip(tickets, limits)]
    return episode(family, context, stratum, bits)


def draw_tickets(rng):
    return [rng.randrange(TICKET_SPACE) for _ in STAGES]


def score(family, initial, ledger):
    """Use receiving or machine records only. Return event, outputs, jobs."""
    if family == "sorter":
        correctly_received = sum(row[0] == row[3] for row in ledger)
        return int(correctly_received < len(ledger)), correctly_received, len(ledger)
    jobs = initial + sum(row[0] for row in ledger)
    finished = sum(row[3] for row in ledger)
    if finished > jobs:
        raise ValueError("Invalid machine ledger")
    return int(finished < jobs), finished, jobs
