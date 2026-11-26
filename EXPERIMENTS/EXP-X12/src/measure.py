"""Independent reference, audit, and held-out measurement streams."""

import runtime as rt


def aggregate(family, context, stratum, limits, n, rng):
    events = 0
    completed = 0
    offered = 0
    for _ in range(n):
        initial, ledger = rt.execute(family, context, stratum, limits, rt.draw_tickets(rng))
        event, done, jobs = rt.score(family, initial, ledger)
        events += event
        completed += done
        offered += jobs
    return {"events": events, "n": n, "completed": completed, "offered": offered}


def calibration():
    n = rt.CONFIG["samples"]["reference"]
    seed = rt.CONFIG["seeds"]["reference"]
    return {
        family: {
            bank: {
                context: {
                    stratum: aggregate(
                        family, context, stratum, limits, n,
                        rt.random_stream(seed, "reference", family, bank, context, stratum),
                    )
                    for stratum, limits in by_stratum.items()
                }
                for context, by_stratum in cells.items()
            }
            for bank, cells in rt.REFERENCES.items()
        }
        for family in rt.FAMILIES
    }


def development():
    n = rt.CONFIG["samples"]["development"]
    return {
        family: aggregate(
            family, "routine", "standard", (137, 241, 317, 423), n,
            rt.random_stream(rt.CONFIG["seeds"]["development"], "development", family),
        )
        for family in rt.FAMILIES
    }


def registry(installation):
    family = installation.family
    return {
        "family": family,
        "bank": installation.bank,
        "shared_storage": installation.limits is rt.REFERENCES[installation.bank],
        "source_semantics": rt.semantic_tape(family),
        "deployed_semantics": rt.semantic_tape(installation.family),
        "enrollment_tapes": {
            context: rt.enrollment_tape(installation.enrollment[context])
            for context in rt.CONTEXTS
        },
    }


def pulse(installation):
    return [
        [
            rt.probe(installation, ticket, limit, comparison, port)
            for port in ("passive", "placebo", "audited")
        ]
        for limit, comparison, ticket in rt.CONFIG["pulse_cases"]
    ]


def compare_stage(installation, source_limit, destination_limit, n, rng):
    # Joint counts indexed by two * source bit + audited destination bit.
    joint = [0, 0, 0, 0]
    for _ in range(n):
        ticket = rng.randrange(rt.TICKET_SPACE)
        source_bit = rt.read_primitive(ticket, source_limit)
        audited_bit = rt.probe(installation, ticket, destination_limit, source_limit, "audited")
        joint[2 * source_bit + audited_bit] += 1
    return joint


def audit(installations, paired_seed, full_seed):
    paired_n = rt.CONFIG["samples"]["paired"]
    full_n = rt.CONFIG["samples"]["full"]
    units = {}
    for unit, installed in installations.items():
        registry_read = registry(installed)
        pulse_read = pulse(installed)
        source_bank = rt.REFERENCES[installed.bank]
        paired = {}
        direct = {}
        for context in rt.CONTEXTS:
            paired[context] = {}
            direct[context] = {}
            for stratum in rt.COVERED:
                destination = rt.limits_for(installed, context, stratum)
                source = source_bank[context][stratum]
                paired[context][stratum] = [
                    compare_stage(
                        installed, source[stage], destination[stage], paired_n,
                        rt.random_stream(paired_seed, "paired", unit, context, stratum, stage),
                    )
                    for stage in rt.STAGES
                ]
                direct[context][stratum] = aggregate(
                    installed.family, context, stratum, destination, full_n,
                    rt.random_stream(full_seed, "direct", unit, context, stratum),
                )
        units[unit] = {
            "registry": registry_read,
            "pulse": pulse_read,
            "paired": paired,
            "direct": direct,
        }
    return units


def holdout_records(installations, seed):
    n = rt.CONFIG["samples"]["holdout"]
    for unit, installed in sorted(installations.items()):
        for context in rt.CONTEXTS:
            enrollment = rt.enrollment_tape(installed.enrollment[context])
            rng = rt.random_stream(seed, "holdout", unit, context)
            for index in range(n):
                enrollment_ticket = rng.randrange(rt.ENROLLMENT_SPACE)
                stratum = enrollment[enrollment_ticket]
                tickets = rt.draw_tickets(rng)
                initial, ledger = rt.execute(
                    installed.family, context, stratum,
                    rt.limits_for(installed, context, stratum), tickets,
                )
                yield [unit, context, index, enrollment_ticket, tickets, initial, ledger]
