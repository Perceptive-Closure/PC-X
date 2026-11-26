"""Nonce-backed archive stages and independently scored held-out replay."""

import secrets
from collections import Counter
from pathlib import Path

from audit import CATALOG, COMPLETIONS, MODES, PORTS, pack, posterior, receipt_reads
from common import (EVIDENCE, PROTECTED, RESULTS, canonical, digest, fields, file_hashes, read,
                    require_hex, utc, utc_now, write)
from engine import play, score, tickets
from preflight import bounded_study, held_scope, pre_audit

BOUND = ("protocol_commit", "source_commit", "source_manifest_sha256", "pre_audit_sha256",
         "exact_sha256", "reserved_at_utc")
PRIVATE = ("profiles", "signature", "ticket_order_seed", "nonce")


def pinned_evidence():
    return {
        "source_manifest_sha256": digest(canonical(file_hashes(PROTECTED))),
        "pre_audit_sha256": digest((RESULTS / "pre-audit.json").read_bytes()),
        "exact_sha256": digest((RESULTS / "exact.json").read_bytes()),
    }


def assignment(sealed):
    fields(sealed, (*BOUND, *PRIVATE))
    fields(sealed["profiles"], PORTS)
    value = tuple(sealed["profiles"][port] for port in PORTS), sealed["signature"]
    if type(value[1]) is not bool or value not in COMPLETIONS:
        raise ValueError("The opening violates the registered port enrollment")
    require_hex(sealed["ticket_order_seed"], 64, "ticket order seed")
    require_hex(sealed["nonce"], 32, "nonce")
    return value


def seal(protocol_commit, source_commit, sealed_file, receipt_file):
    require_hex(protocol_commit, 40, "protocol commit")
    require_hex(source_commit, 40, "source commit")
    if protocol_commit == source_commit:
        raise ValueError("Protocol freeze and executable registration need distinct revisions")
    paths = [Path(path).resolve() for path in (sealed_file, receipt_file)]
    if paths[0] == paths[1] or any(path.exists() or not path.parent.is_dir() for path in paths):
        raise ValueError("Use two new file paths with existing parent directories")
    registered = read(RESULTS / "pre-audit.json")
    random = secrets.SystemRandom()
    candidate = tuple(random.sample(MODES, len(MODES))), random.choice((False, True))
    sealed = {"protocol_commit": protocol_commit, "source_commit": source_commit,
              "reserved_at_utc": utc_now(), **pinned_evidence(), **pack(candidate),
              "ticket_order_seed": secrets.token_hex(32), "nonce": secrets.token_hex(16)}
    reads = receipt_reads(assignment(sealed), registered["audit"]["policy"])
    receipt = {key: sealed[key] for key in BOUND}
    receipt.update({"commitment": digest(canonical(sealed)), "reads": reads,
                    "cost": sum(CATALOG[event["query"]] for event in reads),
                    "issued_at_utc": utc_now()})
    validate_receipt(receipt, registered)
    write(paths[0], canonical(sealed))
    write(paths[1], canonical(receipt))
    return receipt["commitment"]


def validate_receipt(receipt, registered):
    fields(receipt, (*BOUND, "commitment", "reads", "cost", "issued_at_utc"))
    for key in ("protocol_commit", "source_commit"):
        require_hex(receipt[key], 40, key)
    if receipt["protocol_commit"] == receipt["source_commit"]:
        raise ValueError("Invalid stage revisions")
    require_hex(receipt["commitment"], 64, "commitment")
    for key, expected in pinned_evidence().items():
        if receipt[key] != expected:
            raise ValueError(f"Archived evidence mismatch for {key}")
    if not utc(receipt["reserved_at_utc"]) <= utc(receipt["issued_at_utc"]) <= utc(utc_now()):
        raise ValueError("Invalid audit chronology")
    candidates = posterior(receipt["reads"], registered["audit"]["policy"])
    charge = sum(CATALOG[event["query"]] for event in receipt["reads"])
    if type(receipt["cost"]) is not int or receipt["cost"] != charge or (
        charge > registered["audit"]["minimum_worst_cost"]
    ):
        raise ValueError("Audit receipt cost is inconsistent")
    return candidates


def make_forecast(receipt, stamp):
    registered = read(RESULTS / "pre-audit.json")
    candidates = validate_receipt(receipt, registered)
    if not utc(receipt["issued_at_utc"]) <= utc(stamp) <= utc(utc_now()):
        raise ValueError("A forecast must follow its issued audit")
    if len(candidates) != 2 or {candidate[1] for candidate in candidates} != {False, True}:
        raise ValueError("Unexpected support after the registered audit")
    profiles = dict(zip(PORTS, candidates[0][0], strict=True))
    references = {port: registered["profiles"][profile] for port, profile in profiles.items()}
    policies = {port: row["policies"] for port, row in references.items()}
    return {
        "forecast_at_utc": stamp, "commitment": receipt["commitment"],
        "receipt_sha256": digest(canonical(receipt)), "source_commit": receipt["source_commit"],
        "remaining_compatible_installations": len(candidates), "profiles": profiles,
        "scope": held_scope(MODES), "policies": policies,
        "policy_sha256": digest(canonical(policies)),
        "in_task_audit_unit_cost_by_port": {
            port: row["certificate"]["cost"] for port, row in references.items()
        },
        "infeasible_port_proof_sha256": {
            port: digest(canonical(row["certificate"]["counterproof"]))
            for port, row in references.items() if row["certificate"]["status"] == "infeasible"
        },
        "prediction": {port: row["predicted"] for port, row in references.items()},
    }


def validate_opening(sealed, receipt, forecast, verification):
    candidate = assignment(sealed)
    if digest(canonical(sealed)) != receipt["commitment"]:
        raise ValueError("The opening does not match the reservation")
    if any(sealed[key] != receipt[key] for key in BOUND):
        raise ValueError("Opening and receipt stage metadata differ")
    regenerated = make_forecast(receipt, forecast["forecast_at_utc"])
    if canonical(regenerated) != canonical(forecast):
        raise ValueError("The policy or forecast differs from the authorized inference")
    registered = read(RESULTS / "pre-audit.json")
    if candidate not in validate_receipt(receipt, registered) or (
        receipt_reads(candidate, registered["audit"]["policy"]) != receipt["reads"]
    ):
        raise ValueError("The independent audit does not reproduce the receipt")
    fields(verification, ("forecast_commit", "remote_tip", "verified_at_utc", "opened_at_utc"))
    for key in ("forecast_commit", "remote_tip"):
        require_hex(verification[key], 40, key)
    if verification["forecast_commit"] != verification["remote_tip"] or (
        verification["forecast_commit"] in (receipt["protocol_commit"], receipt["source_commit"])
    ):
        raise ValueError("A distinct forecast revision must be verified before the open")
    if not (utc(forecast["forecast_at_utc"]) <= utc(verification["verified_at_utc"]) <=
            utc(verification["opened_at_utc"]) <= utc(utc_now())):
        raise ValueError("Invalid independent opening chronology")
    return candidate


def make_native_records(sealed, forecast):
    rows = []
    for port, slip, arm in tickets(sealed["ticket_order_seed"]):
        profile = sealed["profiles"][port]
        signature = sealed["signature"]
        scope = forecast["scope"]
        record = play(profile, signature, slip, scope, forecast["policies"][port][arm])
        result = score(profile, signature, slip, scope, record)
        rows.append({"port": port, "slip": slip, "arm": arm, "trace": record, "score": result})
    return rows


def summarize(sealed, forecast, rows):
    expected_order = tickets(sealed["ticket_order_seed"])
    if [(row["port"], row["slip"], row["arm"]) for row in rows] != expected_order:
        raise ValueError("Held-out tickets are missing, repeated, or out of sealed order")
    totals, discrepancies = {}, []
    for row in rows:
        port, slip, arm = row["port"], row["slip"], row["arm"]
        observed = score(sealed["profiles"][port], sealed["signature"], slip,
                         forecast["scope"], row["trace"])
        if canonical(observed) != canonical(row["score"]):
            raise ValueError("Raw physical ledger does not reproduce the stored score")
        expected = forecast["prediction"][port][arm][str(slip)]
        if canonical(observed) != canonical(expected):
            discrepancies.append({"port": port, "slip": slip, "arm": arm,
                                  "predicted": expected, "observed": observed})
        total = totals.setdefault(arm, Counter())
        total.update({"tickets": 1, "safe": int(observed["safe"]), "useful": int(observed["useful"]),
                      "qualified_jobs": observed["qualified"], "job_opportunities": 2,
                      "sum_operational_audit_cost": observed["audit_cost"]})
        total["worst_operational_audit_cost"] = max(total["worst_operational_audit_cost"],
                                                    observed["audit_cost"])
        total[f"finish_{observed['finish']}"] += 1
    return {"tickets": len(rows), "exact_matches": len(rows) - len(discrepancies),
            "confirmed": not discrepancies, "discrepancies": discrepancies,
            "score_by_arm": dict(totals), "ledger_sha256": digest(b"".join(map(canonical, rows)))}


def open_installation(sealed_file, receipt_file, forecast_file, forecast_commit, remote_tip,
                      verified_at_utc, out_dir):
    sealed, receipt, forecast = map(read, (sealed_file, receipt_file, forecast_file))
    verification = {"forecast_commit": forecast_commit, "remote_tip": remote_tip,
                    "verified_at_utc": verified_at_utc, "opened_at_utc": utc_now()}
    validate_opening(sealed, receipt, forecast, verification)
    opening = {"sealed": sealed, "verification": verification,
               "forecast_sha256": digest(canonical(forecast)),
               "policy_sha256": forecast["policy_sha256"]}
    output = Path(out_dir)
    output.mkdir(exist_ok=False)
    write(output / "opening.json", canonical(opening))
    rows = make_native_records(sealed, forecast)
    write(output / "ledger.jsonl", b"".join(map(canonical, rows)))
    summary = summarize(sealed, forecast, rows)
    write(output / "summary.json", canonical(summary))
    return summary


def manifest():
    return file_hashes((*PROTECTED, *[f"results/{name}" for name in EVIDENCE]))


def replay():
    if read(RESULTS / "manifest.json") != manifest():
        raise ValueError("Terminal SHA-256 evidence manifest does not match archived bytes")
    for filename, operation in (("exact.json", bounded_study), ("pre-audit.json", pre_audit)):
        if canonical(operation()) != (RESULTS / filename).read_bytes():
            raise ValueError(f"Frozen evidence differs from independent replay for {filename}")
    receipt, forecast, opening = (read(RESULTS / filename)
                                  for filename in ("audit-receipt.json", "forecast.json", "opening.json"))
    fields(opening, ("sealed", "verification", "forecast_sha256", "policy_sha256"))
    if (opening["forecast_sha256"], opening["policy_sha256"]) != (
        digest(canonical(forecast)), forecast["policy_sha256"]
    ):
        raise ValueError("The opening does not bind the exact remote policy")
    sealed = opening["sealed"]
    validate_opening(sealed, receipt, forecast, opening["verification"])
    ledger = (RESULTS / "ledger.jsonl").read_bytes()
    new_records = make_native_records(sealed, forecast)
    if b"".join(map(canonical, new_records)) != ledger:
        raise ValueError("Exact archive execution differs from the retained native ledger")
    summary = summarize(sealed, forecast, new_records)
    if canonical(summary) != (RESULTS / "summary.json").read_bytes():
        raise ValueError("Summary differs from reproduced physical scores")
    return {"bounded": read(RESULTS / "exact.json")["checks"],
            "external_audit_cost": receipt["cost"], "heldout": summary}
