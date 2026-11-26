"""Two-role, archive-based prospective measurement and offline verification."""

from collections import Counter
from datetime import datetime, timezone
import platform
import re
import secrets
import sys
import zlib

import audit
from contract import (
    Fixture, ROOT, ROSTER, UNITS, canonical, digest, document, file_digest, fingerprint, read, save,
)
from exact import baseline
from measure import collect, development, selected_measurements
from model import risks


RESULTS = ROOT / "results"
STUDY_ARTIFACTS = ("summary.json", "raw-audits.json", "raw-native.jsonl.gz", "raw-factorial.jsonl.gz")
PREREQUISITE_ARTIFACTS = ("pre-audit.json", "development.json")


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_utc(value):
    timestamp = datetime.fromisoformat(value)
    if timestamp.utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError("Expected a UTC timestamp")
    return timestamp


def require_hex(value, length):
    if not isinstance(value, str) or not re.fullmatch(f"[0-9a-f]{{{length}}}", value):
        raise ValueError(f"Expected {length} lowercase hexadecimal digits")


def evidence_context(source):
    require_hex(source, 40)
    return {
        "format": 1,
        "pre_audit_commit": source,
        "executable_sha256": fingerprint(),
        "pre_audit_sha256": file_digest(RESULTS / "pre-audit.json"),
    }


def reserve(source, private_path, receipt_path):
    if private_path.resolve() == receipt_path.resolve() or private_path.exists() or receipt_path.exists():
        raise ValueError("Private record and audit receipt require separate fresh paths")
    context = evidence_context(source)
    roster = list(ROSTER)
    secrets.SystemRandom().shuffle(roster)
    assignment = dict(zip(UNITS, roster, strict=True))
    private = {
        **context,
        "reserved_utc": now(),
        "assignment": {unit: list(fixture) for unit, fixture in assignment.items()},
        "seed": secrets.token_hex(32),
        "nonce": secrets.token_hex(16),
    }
    save(private_path, private)
    observations = {
        unit: selected_measurements(assignment[unit], unit, private["seed"])
        for unit in UNITS
    }
    receipt = {
        **context,
        "assignment_commitment_sha256": digest(canonical(private)),
        "observed_utc": now(),
        "measurements": observations,
    }
    save(receipt_path, receipt)
    return receipt


def predict(receipt):
    context = evidence_context(receipt["pre_audit_commit"])
    if any(receipt[field] != expected for field, expected in context.items()):
        raise ValueError("Receipt does not bind to this pre-audit executable")
    if set(receipt) != {*context, "observed_utc", "assignment_commitment_sha256", "measurements"}:
        raise ValueError("Unexpected receipt fields")
    require_hex(receipt["assignment_commitment_sha256"], 64)
    parse_utc(receipt["observed_utc"])
    measurements = receipt["measurements"]
    if set(measurements) != set(UNITS):
        raise ValueError("Incorrect verification roster")
    predictions = {}
    for unit in UNITS:
        report = audit.verify_selected(measurements[unit])
        candidates = audit.model_members(report)
        bands = {}
        if candidates:
            profile_risks = [risks(candidate) for candidate in candidates]
            for name in profile_risks[0]:
                values = [entry[name] for entry in profile_risks]
                bands[name] = [str(min(values)), str(max(values))]
        predictions[unit] = {"audit": report, "risk_bands": bands}
    return {
        **context,
        "assignment_commitment_sha256": receipt["assignment_commitment_sha256"],
        "audit_receipt_sha256": digest(document(receipt)),
        "units": predictions,
    }


def validate_opening(private, receipt, forecast):
    if digest(canonical(private)) != receipt["assignment_commitment_sha256"]:
        raise ValueError("Disclosure does not open the reserved assignment commitment")
    context = evidence_context(receipt["pre_audit_commit"])
    if any(private[field] != expected for field, expected in context.items()):
        raise ValueError("Disclosure is bound to a different executable")
    require_hex(private["seed"], 64)
    require_hex(private["nonce"], 32)
    if parse_utc(private["reserved_utc"]) > parse_utc(receipt["observed_utc"]):
        raise ValueError("Reservation follows the audit")
    assignment = {unit: Fixture(*fields) for unit, fields in private["assignment"].items()}
    if set(assignment) != set(UNITS) or Counter(assignment.values()) != Counter(ROSTER):
        raise ValueError("Disclosure does not satisfy the frozen enrollment")
    if predict(receipt) != forecast:
        raise ValueError("Forecast differs from recomputation on the committed receipt")
    for unit in UNITS:
        expected = selected_measurements(assignment[unit], unit, private["seed"])
        if receipt["measurements"][unit] != expected:
            raise ValueError(f"Selected measurements did not replay for {unit}")
    return assignment


def release(private_path, receipt_path, forecast_path, forecast_commit, github_verified_utc, output):
    """Use the pinned pre-audit archive and the exact GitHub-retrieved forecast."""
    require_hex(forecast_commit, 40)
    private, receipt, forecast = (read(path) for path in (private_path, receipt_path, forecast_path))
    opened_utc = now()
    if not (
        parse_utc(receipt["observed_utc"])
        <= parse_utc(github_verified_utc)
        <= parse_utc(opened_utc)
    ):
        raise ValueError("Expected GitHub readback after receipt and before execution")
    assignment = validate_opening(private, receipt, forecast)
    opening = {
        "private_record": private,
        "assignment_commitment_sha256": receipt["assignment_commitment_sha256"],
        "audit_receipt_sha256": file_digest(receipt_path),
        "forecast_sha256": file_digest(forecast_path),
        "forecast_commit": forecast_commit,
        "github_verified_utc": github_verified_utc,
        "opened_utc": opened_utc,
        "execution_environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "zlib": zlib.ZLIB_RUNTIME_VERSION,
        },
    }
    report = collect(output, assignment, private["seed"], forecast)
    save(output / "opening.json", opening)
    files = {
        **{name: RESULTS / name for name in PREREQUISITE_ARTIFACTS},
        **{name: output / name for name in (*STUDY_ARTIFACTS, "opening.json")},
        "audit-receipt.json": receipt_path,
        "forecast.json": forecast_path,
    }
    save(output / "manifest.json", {
        "executable_sha256": fingerprint(),
        "assignment_commitment_sha256": opening["assignment_commitment_sha256"],
        "sha256": {name: file_digest(path) for name, path in files.items()},
    })
    return report


def replay(output):
    package = read(RESULTS / "manifest.json")
    expected = package["sha256"]
    required = {*PREREQUISITE_ARTIFACTS, *STUDY_ARTIFACTS, "opening.json", "audit-receipt.json", "forecast.json"}
    if set(expected) != required or package["executable_sha256"] != fingerprint():
        raise ValueError("Evidence manifest does not bind the complete frozen package")
    for name, checksum in expected.items():
        if file_digest(RESULTS / name) != checksum:
            raise ValueError(f"Committed evidence hash failed for {name}")
    receipt = read(RESULTS / "audit-receipt.json")
    forecast = read(RESULTS / "forecast.json")
    opening = read(RESULTS / "opening.json")
    value = receipt["assignment_commitment_sha256"]
    if value != opening["assignment_commitment_sha256"] or value != package["assignment_commitment_sha256"]:
        raise ValueError("Evidence layers do not agree on the original assignment commitment")
    if (
        opening["audit_receipt_sha256"] != expected["audit-receipt.json"]
        or opening["forecast_sha256"] != expected["forecast.json"]
    ):
        raise ValueError("Opening does not bind the published receipt and forecast")
    require_hex(opening["forecast_commit"], 40)
    if not (
        parse_utc(receipt["observed_utc"])
        <= parse_utc(opening["github_verified_utc"])
        <= parse_utc(opening["opened_utc"])
    ):
        raise ValueError("Original run chronology is invalid")
    private = opening["private_record"]
    assignment = validate_opening(private, receipt, forecast)
    for name, compute in (("pre-audit.json", baseline), ("development.json", development)):
        if digest(document(compute())) != expected[name]:
            raise ValueError(f"Model/code replay differs for {name}")
    report = collect(output, assignment, private["seed"], forecast)
    for name in STUDY_ARTIFACTS:
        if file_digest(output / name) != expected[name]:
            raise ValueError(f"Sample replay differs for {name}")
    return report
