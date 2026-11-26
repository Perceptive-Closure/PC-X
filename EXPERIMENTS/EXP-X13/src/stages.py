"""Nonce-backed, archive-safe custody and evidence verification."""

import gzip
import secrets
from pathlib import Path

from audit import CATALOG, COMPLETIONS, audit_read, posterior, query_cost
from common import (MODES, PORTS, RESULTS, TIES, assert_canonical, canonical, digest,
                    file_hashes, protected_files, require_hex, source_hashes, utc, utc_now, write)
from model import mode_key
from native import evaluate, render
from preflight import run as run_pre_audit

RECEIPT_METADATA = ("protocol_commit", "source_commit", "source_sha256",
                    "pre_audit_sha256", "reserved_at_utc")
EVIDENCE = ("pre-audit.json", "audit-receipt.json", "forecast.json",
            "opening.json", "summary.json", "episodes.jsonl.gz")


def pre_audit():
    return assert_canonical(RESULTS / "pre-audit.json")


def sealed_assignment(sealed):
    mapping = sealed["modes"]
    if set(mapping) != set(PORTS):
        raise ValueError("Invalid sealed port labels")
    completion = (tuple(tuple(mapping[port]) for port in PORTS), sealed["tie_order"])
    if completion not in COMPLETIONS:
        raise ValueError("Sealed installation violates the frozen enrollment")
    require_hex(sealed["ticket_order_seed"], 64, "ticket-order seed")
    require_hex(sealed["nonce"], 32, "nonce")
    return completion


def reserve(protocol_commit, source_commit, sealed_path, receipt_path):
    require_hex(protocol_commit, 40, "protocol commit")
    require_hex(source_commit, 40, "pre-audit commit")
    if protocol_commit == source_commit:
        raise ValueError("Protocol and executable stages must be separately registered")
    outputs = [Path(name).resolve() for name in (sealed_path, receipt_path)]
    if len(set(outputs)) != 2 or any(path.exists() or not path.parent.is_dir()
                                     for path in outputs):
        raise ValueError("Each custody output needs its own new file and existing parent")

    verified_preaudit = pre_audit()
    random = secrets.SystemRandom()
    sealed = {
        "protocol_commit": protocol_commit, "source_commit": source_commit,
        "source_sha256": digest(canonical(source_hashes())),
        "pre_audit_sha256": digest((RESULTS / "pre-audit.json").read_bytes()),
        "reserved_at_utc": utc_now(),
        "modes": dict(zip(PORTS, random.sample(MODES, len(MODES)), strict=True)),
        "tie_order": random.choice(TIES),
        "ticket_order_seed": secrets.token_hex(32), "nonce": secrets.token_hex(16),
    }
    completion = sealed_assignment(sealed)
    selection = verified_preaudit["audit"]["composition"]
    reads = {name: audit_read(completion, name) for name in selection["selected"]}
    receipt = {key: sealed[key] for key in RECEIPT_METADATA}
    receipt.update({"commitment": digest(canonical(sealed)), "reads": reads,
                    "cost": selection["minimum_cost"], "issued_at_utc": utc_now()})
    validate_receipt(receipt, verified_preaudit)
    write(outputs[0], canonical(sealed))
    write(outputs[1], canonical(receipt))
    return receipt["commitment"]


def validate_receipt(receipt, verified_preaudit):
    if set(receipt) != (set(RECEIPT_METADATA) | {"commitment", "reads", "cost", "issued_at_utc"}):
        raise ValueError("Unexpected public audit receipt fields")
    for key in ("protocol_commit", "source_commit"):
        require_hex(receipt[key], 40, key)
    if receipt["protocol_commit"] == receipt["source_commit"]:
        raise ValueError("Invalid stage revision")
    for key in ("commitment", "source_sha256", "pre_audit_sha256"):
        require_hex(receipt[key], 64, key)
    if receipt["source_sha256"] != digest(canonical(source_hashes())):
        raise ValueError("Source diverged from the sealed revision")
    if receipt["pre_audit_sha256"] != digest((RESULTS / "pre-audit.json").read_bytes()):
        raise ValueError("Pre-audit diverged from the sealed revision")
    if not utc(receipt["reserved_at_utc"]) <= utc(receipt["issued_at_utc"]) <= utc(utc_now()):
        raise ValueError("Invalid calibration chronology")
    choice = verified_preaudit["audit"]["composition"]
    if set(receipt["reads"]) != set(choice["selected"]):
        raise ValueError("Receipt diverged from the frozen query set")
    if receipt["cost"] != choice["minimum_cost"] or receipt["cost"] != sum(
            query_cost(name) for name in receipt["reads"]):
        raise ValueError("Receipt diverged from the frozen query cost")
    if not posterior(receipt["reads"]):
        raise ValueError("Readbacks are inconsistent with all frozen completions")


def possibility_report(completions, table):
    properties = ("event_containment", "local_bounds_carried_over", "global_threshold_met",
                  "qualified_work", "useful_certificate")
    ports = {}
    for index, port in enumerate(PORTS):
        viable_modes = sorted({mode_key(candidate[0][index]) for candidate in completions})
        ports[port] = {
            "modes": viable_modes,
            "decisions": {key: sorted({table[mode]["judgments"][key] for mode in viable_modes})
                          for key in properties}
        }
    return {"compatible_installations": len(completions), "ports": ports}


def make_forecast(receipt, timestamp):
    verified_preaudit = pre_audit()
    validate_receipt(receipt, verified_preaudit)
    if not utc(receipt["issued_at_utc"]) <= utc(timestamp) <= utc(utc_now()):
        raise ValueError("Forecast must follow the issued audit")
    reads = receipt["reads"]
    completions = posterior(reads)
    table = verified_preaudit["reference_modes"]
    identified = possibility_report(completions, table)
    if any(len(info["modes"]) != 1 for info in identified["ports"].values()):
        raise ValueError("Authorized audit did not establish a unique mode per port")
    prediction = {}
    for port, info in identified["ports"].items():
        model = table[info["modes"][0]]
        prediction[port] = {key: model[key] for key in ("contexts", "judgments")}
    ablations = {"nameplate_only": posterior({"nameplate": {"displayed_time_quanta_per_turn": 2}})}
    for withdrawn in ("allocator", "view"):
        ablations[f"withheld_{withdrawn}"] = posterior({
            name: value for name, value in reads.items() if CATALOG[name][0] != withdrawn
        })
    return {"forecast_at_utc": timestamp, "commitment": receipt["commitment"],
            "receipt_sha256": digest(canonical(receipt)), "after_audit": identified,
            "ablation": {name: possibility_report(values, table) for name, values in ablations.items()},
            "naive_baseline": {"assumed_global_bound": "1/4", "certified_ports": list(PORTS)},
            "zero_work_baseline": {"global_event_risk": "0", "qualified_fraction": "0",
                                   "useful_certificate": False},
            "prediction": prediction}


def validate_opening(sealed, receipt, forecast, verification):
    completion = sealed_assignment(sealed)
    protected_fields = set(RECEIPT_METADATA) | {"modes", "tie_order", "ticket_order_seed", "nonce"}
    if set(sealed) != protected_fields:
        raise ValueError("Unexpected sealed assignment fields")
    if digest(canonical(sealed)) != receipt["commitment"]:
        raise ValueError("Opening fails the prior commitment")
    if any(sealed[key] != receipt[key] for key in RECEIPT_METADATA):
        raise ValueError("Custody metadata mismatch")
    if make_forecast(receipt, forecast["forecast_at_utc"]) != forecast:
        raise ValueError("Forecast has changed or extrapolated beyond the authorized receipt")
    if completion not in posterior(receipt["reads"]):
        raise ValueError("The opening is inconsistent with the authorized reads")
    if any(audit_read(completion, name) != value for name, value in receipt["reads"].items()):
        raise ValueError("The current calibration does not reproduce the receipt")
    for key in ("forecast_commit", "remote_tip"):
        require_hex(verification[key], 40, key)
    tip = verification["remote_tip"]
    if tip != verification["forecast_commit"] or tip in (sealed["source_commit"], sealed["protocol_commit"]):
        raise ValueError("Independent GitHub forecast verification is missing")
    if not (utc(forecast["forecast_at_utc"]) <= utc(verification["verified_at_utc"]) <=
            utc(verification["opened_at_utc"]) <= utc(utc_now())):
        raise ValueError("Forecast verification must precede opening")
    return dict(zip(PORTS, completion[0], strict=True)), completion[1]


def open_outcome(sealed_path, receipt_path, forecast_path, forecast_commit, remote_tip,
                 verified_at, directory):
    sealed, receipt, forecast = (assert_canonical(path) for path in
                                (sealed_path, receipt_path, forecast_path))
    output = Path(directory)
    if output.exists() or not output.parent.is_dir():
        raise ValueError("Opening output requires a new directory with an existing parent")
    verification = {"forecast_commit": forecast_commit, "remote_tip": remote_tip,
                    "verified_at_utc": verified_at, "opened_at_utc": utc_now()}
    assignment, tie_order = validate_opening(sealed, receipt, forecast, verification)
    archive, summary = render(assignment, tie_order, sealed["ticket_order_seed"], forecast)
    opening = {
        "assignment": sealed, "verification": verification, "commitment": receipt["commitment"],
        "receipt_sha256": digest(canonical(receipt)), "forecast_sha256": digest(canonical(forecast)),
        "summary_sha256": digest(canonical(summary)), "raw_sha256": summary["raw_sha256"],
        "gzip_sha256": summary["gzip_sha256"],
    }
    output.mkdir()
    write(output / "episodes.jsonl.gz", archive)
    write(output / "summary.json", canonical(summary))
    write(output / "opening.json", canonical(opening))
    return {"confirmed": summary["confirmed"], "joint_episodes": summary["joint_episodes"],
            "raw_sha256": summary["raw_sha256"], "gzip_sha256": summary["gzip_sha256"]}


def manifest():
    paths = protected_files() + [f"results/{name}" for name in EVIDENCE]
    return {"experiment": "EXP-X13", "sha256": file_hashes(paths)}


def replay():
    if assert_canonical(RESULTS / "manifest.json") != manifest():
        raise ValueError("Evidence manifest mismatch")
    if canonical(run_pre_audit()) != (RESULTS / "pre-audit.json").read_bytes():
        raise ValueError("Pre-audit does not reproduce")
    receipt, forecast, opening, published = (
        assert_canonical(RESULTS / name)
        for name in ("audit-receipt.json", "forecast.json", "opening.json", "summary.json"))
    sealed = opening["assignment"]
    assignment, tie_order = validate_opening(sealed, receipt, forecast, opening["verification"])
    archive = (RESULTS / "episodes.jsonl.gz").read_bytes()
    raw = gzip.decompress(archive)
    actual = evaluate(raw, assignment, tie_order, sealed["ticket_order_seed"], forecast)
    actual.update({"raw_sha256": digest(raw), "gzip_sha256": digest(archive)})
    expected_digests = {
        "commitment": receipt["commitment"], "receipt_sha256": digest(canonical(receipt)),
        "forecast_sha256": digest(canonical(forecast)), "summary_sha256": digest(canonical(actual)),
        "raw_sha256": actual["raw_sha256"], "gzip_sha256": actual["gzip_sha256"],
    }
    if actual != published or any(opening[key] != value for key, value in expected_digests.items()):
        raise ValueError("Independent ledger scores or opening hashes disagree")
    regenerated, summary = render(assignment, tie_order, sealed["ticket_order_seed"], forecast)
    if gzip.decompress(regenerated) != raw or summary["raw_sha256"] != published["raw_sha256"]:
        raise ValueError("Native replay does not reproduce the sealed rows")
    return {"confirmed": actual["confirmed"], "joint_episodes": actual["joint_episodes"],
            "isolated_episodes": actual["isolated_episodes"], "raw_sha256": digest(raw),
            "stored_gzip_sha256": digest(archive), "regenerated_gzip_sha256": digest(regenerated),
            "useful_certified_ports": actual["useful_certified_ports"],
            "naive_false_certifications": actual["naive_false_certifications"]}
