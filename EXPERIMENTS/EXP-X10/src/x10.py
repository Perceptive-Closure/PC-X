"""Command-line stages for the EXP-X10 blinded monitorability experiment."""
import argparse
import gzip
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import random
import re
import secrets

from analysis import candidates, checked_measurement, predict, verify_exact
from routing import Fixture, audit_card, trial

ROOT = Path(__file__).resolve().parent.parent


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def value_digest(value):
    return digest(canonical(value))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_new(path, data):
    with Path(path).open("xb") as stream:
        stream.write(data)


def write_record(path, value):
    write_new(path, canonical(value) + b"\n")


def parse_commit(value):
    if not re.fullmatch(r"[a-f0-9]{40}", value):
        raise ValueError("Expected an exact Git commit")
    return value


def iso_utc(value):
    stamp = datetime.fromisoformat(value)
    if stamp.utcoffset() != timezone.utc.utcoffset(stamp):
        raise ValueError("Verification time must carry a UTC offset")
    return stamp


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def load_spec():
    spec = read_json(ROOT / "configs" / "protocol.json")
    if spec["tickets"] != 24 or spec["strata"] != ["routine", "oversize"] or len(spec["units"]) != 2:
        raise ValueError("Unsupported finite protocol dimensions")
    for regime in spec["regimes"]:
        for revision in spec["revisions"]:
            for stratum in spec["strata"]:
                card = spec["lane_reference"][regime][revision][stratum]
                if len(card) != spec["tickets"] or set(card) != {"E", "W"}:
                    raise ValueError("Invalid reference card")
    return spec


def read_preaudit(spec):
    result = read_json(ROOT / "results" / "pre-audit.json")
    if result["protocol_sha256"] != value_digest(spec):
        raise ValueError("Pre-audit analysis does not match the frozen protocol")
    return result


def reserve(spec, preaudit, pre_audit_commit, private_path, receipt_path):
    """Select randomized conditions and release only the authorized read."""
    parse_commit(pre_audit_commit)
    chosen = secrets.choice(candidates(spec))
    private = {
        "fixture": {unit: [fixture.regime, fixture.revision] for unit, fixture in zip(spec["units"], chosen)},
        "trial_seed": secrets.token_hex(32), "nonce": secrets.token_hex(32),
        "protocol_sha256": value_digest(spec), "pre_audit_commit": pre_audit_commit,
    }
    queries = preaudit["minimum_audit"]["queries"]
    assignment = dict(zip(spec["units"], chosen))
    receipt = {
        "queries": queries,
        "answers": [audit_card(spec, assignment[unit], kind) for unit, kind in queries],
        "assignment_commitment_sha256": value_digest(private), "protocol_sha256": value_digest(spec),
        "pre_audit_commit": pre_audit_commit, "issued_at_utc": now(),
    }
    if Path(private_path).resolve() == Path(receipt_path).resolve():
        raise ValueError("Custody and public files must be separate")
    write_record(private_path, private)
    write_record(receipt_path, receipt)
    return receipt


def verify_open(spec, receipt, private, preaudit, forecast):
    if private["pre_audit_commit"] != receipt["pre_audit_commit"]:
        raise ValueError("Pre-audit revision mismatch")
    if value_digest(private) != receipt["assignment_commitment_sha256"]:
        raise ValueError("Assignment does not open the commitment")
    if receipt["protocol_sha256"] != value_digest(spec) or private["protocol_sha256"] != value_digest(spec):
        raise ValueError("Frozen protocol mismatch")
    parse_commit(receipt["pre_audit_commit"])
    iso_utc(receipt["issued_at_utc"])
    for kind in ("trial_seed", "nonce"):
        if not re.fullmatch(r"[0-9a-f]{64}", private[kind]):
            raise ValueError(f"Invalid {kind}")
    assignment = {unit: Fixture(*private["fixture"][unit]) for unit in spec["units"]}
    if tuple(assignment.values()) not in candidates(spec):
        raise ValueError("Assignment falls outside the enrolled population")
    answers = [audit_card(spec, assignment[unit], kind) for unit, kind in receipt["queries"]]
    if answers != receipt["answers"]:
        raise ValueError("Independent calibration answer mismatch")
    if canonical(make_forecast(spec, preaudit, receipt)) != canonical(forecast):
        raise ValueError("Committed forecast is inconsistent with the sealed audit receipt")
    return assignment


def make_forecast(spec, preaudit, receipt):
    if receipt["protocol_sha256"] != value_digest(spec):
        raise ValueError("Receipt belongs to a different protocol")
    parse_commit(receipt["pre_audit_commit"])
    iso_utc(receipt["issued_at_utc"])
    if not re.fullmatch(r"[0-9a-f]{64}", receipt["assignment_commitment_sha256"]):
        raise ValueError("Malformed assignment commitment")
    return {"protocol_sha256": value_digest(spec), "receipt_sha256": value_digest(receipt),
            "thresholds": {name: spec[name] for name in ("violation_threshold", "miss_threshold")},
            **predict(spec, preaudit, receipt)}


def outcome_bytes(spec, assignment, trial_seed):
    payload = []
    for unit, fixture in assignment.items():
        for stratum in spec["strata"]:
            rng = random.Random(int(digest(canonical([trial_seed, unit, stratum])), 16))
            for index in range(spec["heldout_per_unit_stratum"]):
                ticket = rng.randrange(spec["tickets"])
                payload.append(canonical(trial(spec, fixture, unit, stratum, index, ticket)))
    return b"\n".join(payload) + b"\n"


def evidence_result(spec, raw, assignment, forecast):
    rows = (json.loads(line) for line in raw.splitlines())
    summary = checked_measurement(spec, rows, assignment, forecast)
    return {"episode_data_sha256": digest(raw), **summary}


def release(spec, preaudit, private, receipt, forecast, forecast_commit, remote_tip, remote_time, output):
    """Run only after the custodian checks the exact forecast and ancestry on GitHub."""
    parse_commit(forecast_commit)
    if remote_tip != forecast_commit or forecast_commit == receipt["pre_audit_commit"]:
        raise ValueError("The GitHub branch tip must be the later forecast revision")
    verified_time = iso_utc(remote_time)
    if verified_time < iso_utc(receipt["issued_at_utc"]) or verified_time > iso_utc(now()):
        raise ValueError("Forecast verification outside the custody window")
    assignment = verify_open(spec, receipt, private, preaudit, forecast)
    output.mkdir()
    raw = outcome_bytes(spec, assignment, private["trial_seed"])
    summary = evidence_result(spec, raw, assignment, forecast)
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    opening = {
        "forecast_commit": forecast_commit, "github_branch": "codex/exp-x10",
        "remote_tip_verified_at_utc": remote_time, "forecast_sha256": value_digest(forecast),
        "receipt_sha256": value_digest(receipt), "episode_gzip_sha256": digest(compressed),
        "released_at_utc": now(), "assignment": private, "measurement": summary,
    }
    write_new(output / "episodes.jsonl.gz", compressed)
    write_record(output / "opening.json", opening)
    return opening


def replay(spec, result_root, output):
    preaudit = read_json(result_root / "pre-audit.json")
    expected_preaudit = {"protocol_sha256": value_digest(spec), **verify_exact(spec)}
    if canonical(preaudit) != canonical(expected_preaudit):
        raise ValueError("Pre-audit evidence differs from exact replay")
    forecast = read_json(result_root / "forecast.json")
    receipt = read_json(result_root / "audit-receipt.json")
    opening = read_json(result_root / "opening.json")
    private = opening["assignment"]
    parse_commit(opening["forecast_commit"])
    if opening["forecast_commit"] == private["pre_audit_commit"]:
        raise ValueError("Forecast did not follow executable freeze")
    if not iso_utc(receipt["issued_at_utc"]) <= iso_utc(opening["remote_tip_verified_at_utc"]) <= iso_utc(opening["released_at_utc"]):
        raise ValueError("Stored custody timestamps are out of order")
    if opening["forecast_sha256"] != value_digest(forecast) or opening["receipt_sha256"] != value_digest(receipt):
        raise ValueError("Stored forecast or audit receipt hash mismatch")
    confirmation = read_json(result_root / "manifest.json")
    for filename, expected in confirmation["result_file_sha256"].items():
        if filename not in {"pre-audit.json", "audit-receipt.json", "forecast.json", "opening.json", "episodes.jsonl.gz"}:
            raise ValueError("Unexpected manifest path")
        if digest((result_root / filename).read_bytes()) != expected:
            raise ValueError(f"Stored file hash mismatch for {filename}")
    if len(confirmation["result_file_sha256"]) != 5:
        raise ValueError("Manifest must cover all five original evidence files")
    assignment = verify_open(spec, receipt, private, preaudit, forecast)
    compressed = (result_root / "episodes.jsonl.gz").read_bytes()
    if digest(compressed) != opening["episode_gzip_sha256"]:
        raise ValueError("Compressed observation artifact hash mismatch")
    original = gzip.decompress(compressed)
    replayed = outcome_bytes(spec, assignment, private["trial_seed"])
    if original != replayed:
        raise ValueError("Held-out episodes did not replay byte-for-byte")
    summary = evidence_result(spec, original, assignment, forecast)
    if canonical(summary) != canonical(opening["measurement"]):
        raise ValueError("Recomputed measurement differs from the stored analysis")
    if output:
        write_record(output, summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    stages = parser.add_subparsers(dest="stage", required=True)
    exact = stages.add_parser("exact")
    exact.add_argument("--output", type=Path, required=True)
    reserve_cli = stages.add_parser("reserve")
    reserve_cli.add_argument("--pre-audit-commit", required=True)
    reserve_cli.add_argument("--private", type=Path, required=True)
    reserve_cli.add_argument("--receipt", type=Path, required=True)
    predict_cli = stages.add_parser("predict")
    predict_cli.add_argument("--receipt", type=Path, required=True)
    predict_cli.add_argument("--output", type=Path, required=True)
    release_cli = stages.add_parser("release")
    release_cli.add_argument("--private", type=Path, required=True)
    release_cli.add_argument("--receipt", type=Path, required=True)
    release_cli.add_argument("--forecast", type=Path, required=True)
    release_cli.add_argument("--forecast-commit", required=True)
    release_cli.add_argument("--remote-tip", required=True)
    release_cli.add_argument("--verified-at-utc", required=True)
    release_cli.add_argument("--output", type=Path, required=True)
    replay_cli = stages.add_parser("replay")
    replay_cli.add_argument("--results", type=Path, default=ROOT / "results")
    replay_cli.add_argument("--output", type=Path)
    args = parser.parse_args()
    spec = load_spec()
    if args.stage == "exact":
        result = {"protocol_sha256": value_digest(spec), **verify_exact(spec)}
        write_record(args.output, result)
        print(json.dumps({"checked_traces": result["checked_traces"], "minimum_audit": result["minimum_audit"],
                          "full_contract": result["full_contract"]}, indent=2))
    elif args.stage == "reserve":
        receipt = reserve(spec, read_preaudit(spec), args.pre_audit_commit, args.private, args.receipt)
        print(json.dumps(receipt, indent=2))
    elif args.stage == "predict":
        result = make_forecast(spec, read_preaudit(spec), read_json(args.receipt))
        write_record(args.output, result)
        print(json.dumps(result["judgments"], indent=2))
    elif args.stage == "release":
        opening = release(spec, read_preaudit(spec), read_json(args.private), read_json(args.receipt),
                          read_json(args.forecast), args.forecast_commit, args.remote_tip, args.verified_at_utc, args.output)
        print(json.dumps({key: opening["measurement"][key] for key in ("heldout_trials", "threshold_confirmations",
                                                                           "forecast_envelope_overlaps", "episode_data_sha256")}, indent=2))
    else:
        summary = replay(spec, args.results, args.output)
        print(json.dumps({key: summary[key] for key in ("heldout_trials", "threshold_confirmations",
                                                       "forecast_envelope_overlaps", "episode_data_sha256")}, indent=2))


if __name__ == "__main__":
    main()
