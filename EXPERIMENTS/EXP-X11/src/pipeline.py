"""The prospective custody, opening, and archive replay stages."""

import hashlib
import secrets
from pathlib import Path

from common import (ROOT, canonical, digest, read_json, require_hex, runner_files, runner_sha,
                    text_sha, write_json)
from measure import produce_observations, summarized_observations
from model import envelope, pre_audit
from sandbox import calibrate
from verify import verify_pulse


RESULTS = ROOT / "results"
TRACE = "observations.jsonl.gz"
OPENING = "opening.json"
MANIFEST = "manifest.json"
PUBLISHED_RESULTS = ("pre-audit.json", "audit-receipt.json", "forecast.json", OPENING, TRACE)


def validate_pre_audit(protocol, prior):
    if prior["source_pins"] != protocol["sources"] or prior["runner_sha256"] != runner_sha():
        raise ValueError("Source does not match the frozen pre-audit")


def validate_reveal(protocol, prior, sealed):
    source_refs = {"protocol_commit", "source_commit", "pre_audit_sha256", "runner_sha256"}
    if set(sealed) != source_refs | {"disturbed_port", "measurement_seed", "nonce"}:
        raise ValueError("Invalid sealed record")
    validate_pre_audit(protocol, prior)
    for key in ("protocol_commit", "source_commit"):
        require_hex(sealed[key], 40, key)
    require_hex(sealed["measurement_seed"], 64, "measurement seed")
    require_hex(sealed["nonce"], 32, "nonce")
    if (sealed["disturbed_port"] not in protocol["ports"]
            or sealed["pre_audit_sha256"] != digest(prior)
            or sealed["runner_sha256"] != prior["runner_sha256"]):
        raise ValueError("Revealed data outside the declared assignment or source")


def build_receipt(protocol, prior, sealed):
    validate_reveal(protocol, prior, sealed)
    query, = prior["audit"]["selected"]
    calibration = calibrate(protocol, query, sealed["disturbed_port"])
    verify_pulse(protocol, query, calibration)
    return {
        "assignment_commitment_sha256": digest(sealed), "query": query,
        "raw": calibration, "protocol_commit": sealed["protocol_commit"],
        "source_commit": sealed["source_commit"], "runner_sha256": sealed["runner_sha256"],
        "pre_audit_sha256": sealed["pre_audit_sha256"],
    }


def seal(protocol, prior, protocol_commit, source_commit, sealed_path, receipt_path):
    sealed_path = Path(sealed_path)
    receipt_path = Path(receipt_path)
    if sealed_path.resolve() == receipt_path.resolve() or sealed_path.exists() or receipt_path.exists():
        raise ValueError("Custody paths must be distinct and new")
    sealed = {
        "protocol_commit": protocol_commit, "source_commit": source_commit,
        "pre_audit_sha256": digest(prior), "runner_sha256": prior["runner_sha256"],
        "disturbed_port": secrets.choice(protocol["ports"]),
        "measurement_seed": secrets.token_hex(32), "nonce": secrets.token_hex(16),
    }
    receipt = build_receipt(protocol, prior, sealed)
    write_json(sealed_path, sealed)
    write_json(receipt_path, receipt)
    return receipt["assignment_commitment_sha256"]


def make_forecast(protocol, prior, receipt):
    validate_pre_audit(protocol, prior)
    for key in ("protocol_commit", "source_commit"):
        require_hex(receipt[key], 40, key)
    require_hex(receipt["assignment_commitment_sha256"], 64, "assignment commitment")
    query, = prior["audit"]["selected"]
    if (receipt["query"] != query or receipt["pre_audit_sha256"] != digest(prior)
            or receipt["runner_sha256"] != prior["runner_sha256"]):
        raise ValueError("Audit receipt does not bind the declared source and selected query")
    anchor = verify_pulse(protocol, query, receipt["raw"])
    candidates = prior["exact_predictions"]
    retained = {
        case: predictions for case, predictions in candidates.items()
        if anchor == prior["calibration_controls"][case][query]["value"]
    }
    if len(retained) != 1:
        raise ValueError("Anchor is inconsistent or insufficient in this finite class")
    placement, = retained
    bounds = envelope(protocol, retained)
    queried_arm = query.removesuffix("_capacity")
    peer, = [arm for arm in protocol["ports"] if arm != queried_arm]
    return {
        "source_commit": receipt["source_commit"], "runner_sha256": receipt["runner_sha256"],
        "pre_audit_sha256": receipt["pre_audit_sha256"],
        "assignment_commitment_sha256": receipt["assignment_commitment_sha256"],
        "audit_receipt_sha256": digest(receipt), "retained_completions": list(retained),
        "independent_pulse_capacity": anchor, "arm_predictions": retained[placement],
        "sharp_bounds": bounds, "without_anchor": prior["not_queried"],
        "without_balanced_enrollment": {
            "queried_port": queried_arm, "queried_bounds": bounds[queried_arm],
            "unqueried_port": peer, "unqueried_bounds": prior["not_queried"][peer]},
        "coupling_bounds": prior["coupling_support"][placement],
        "predicted_naive_transfer_error_ports": [
            arm for arm in protocol["ports"]
            if bounds[arm]["threshold_decision"] != bounds["original"]["threshold_decision"]],
    }


def verify_open_inputs(protocol, prior, sealed, receipt, forecast, forecast_commit):
    require_hex(forecast_commit, 40, "custodian-verified forecast commit")
    if forecast_commit in (receipt["protocol_commit"], receipt["source_commit"]):
        raise ValueError("Forecast must be a distinct later revision")
    if receipt != build_receipt(protocol, prior, sealed):
        raise ValueError("Reveal or recorded audit differs from the committed receipt")
    if canonical(forecast) != canonical(make_forecast(protocol, prior, receipt)):
        raise ValueError("Forecast differs from the frozen audit computation")


def trace_result(protocol, sealed, forecast, forecast_commit, trace_path):
    return {
        "reveal": sealed, "assignment_commitment_sha256": digest(sealed),
        "verified_forecast_commit": forecast_commit, "forecast_sha256": digest(forecast),
        "observations": TRACE,
        "analysis": summarized_observations(protocol, sealed, forecast, trace_path),
    }


def open_holdout(protocol, prior, sealed, receipt, forecast, forecast_commit, out_dir):
    verify_open_inputs(protocol, prior, sealed, receipt, forecast, forecast_commit)
    out_dir.mkdir()
    trace_path = out_dir / TRACE
    try:
        produce_observations(protocol, sealed, trace_path)
        result = trace_result(protocol, sealed, forecast, forecast_commit, trace_path)
    except (OSError, ValueError) as exc:
        write_json(out_dir / "invalid-opening.json", {
            "verified_forecast_commit": forecast_commit, "reveal": sealed,
            "assignment_commitment_sha256": digest(sealed), "error": str(exc),
        })
        raise
    write_json(out_dir / OPENING, result)
    return result


def package_fingerprints():
    tests = [path.relative_to(ROOT).as_posix() for path in sorted((ROOT / "tests").glob("test_*.py"))]
    text_files = ["WorkPlan.md", "Protocol.md", "Path.md", "README.md", *runner_files(), *tests,
                  *(f"results/{name}" for name in PUBLISHED_RESULTS if name != TRACE)]
    hashes = {name: text_sha(ROOT / name) for name in text_files}
    trace_name = f"results/{TRACE}"
    with (ROOT / trace_name).open("rb") as trace:
        hashes[trace_name] = hashlib.file_digest(trace, "sha256").hexdigest()
    return hashes


def build_manifest():
    result = read_json(RESULTS / OPENING)
    manifest = {
        "sha_algorithm": "SHA-256",
        "text_hash_normalization": "CRLF to LF",
        "raw_observations": {
            "archive": TRACE, "uncompressed_sha256": result["analysis"]["raw_sha256"],
            "blocks": result["analysis"]["blocks"], "episodes": result["analysis"]["episodes"],
        },
        "stages": {"protocol_commit": result["reveal"]["protocol_commit"],
                   "pre_audit_runner_commit": result["reveal"]["source_commit"],
                   "forecast_commit": result["verified_forecast_commit"],
                   "assignment_commitment_sha256": result["assignment_commitment_sha256"],
                   "canonical_forecast_sha256": result["forecast_sha256"]},
        "files": package_fingerprints(),
    }
    write_json(RESULTS / MANIFEST, manifest)
    return manifest


def replay(protocol, out_dir):
    manifest = read_json(RESULTS / MANIFEST)
    if manifest["files"] != package_fingerprints():
        raise ValueError("Package file hashes differ from the manifest")
    prior = read_json(RESULTS / "pre-audit.json")
    receipt = read_json(RESULTS / "audit-receipt.json")
    forecast = read_json(RESULTS / "forecast.json")
    reference = read_json(RESULTS / OPENING)
    sealed = reference["reveal"]
    commit = reference["verified_forecast_commit"]
    if canonical(prior) != canonical(pre_audit(protocol)):
        raise ValueError("Exact pre-audit evidence did not reproduce")
    from_archive = trace_result(protocol, sealed, forecast, commit, RESULTS / TRACE)
    if canonical(from_archive) != canonical(reference):
        raise ValueError("Archived independent scores did not reproduce")
    if manifest["raw_observations"]["uncompressed_sha256"] != reference["analysis"]["raw_sha256"]:
        raise ValueError("Raw observation digest differs from the manifest")
    result = open_holdout(protocol, prior, sealed, receipt, forecast, commit, out_dir)
    if canonical(result) != canonical(reference):
        raise ValueError("Fresh deterministic opening differs from the retained result")
    return result
