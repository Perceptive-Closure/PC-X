"""Freeze, reserve, forecast, open, and reproduce EXP-X12 without Git metadata."""

import argparse
from datetime import datetime, timezone
from hashlib import file_digest, sha256
import json
from pathlib import Path
import re
from secrets import token_hex

import analysis
import measure
import oracle
import outcomes
import runtime as rt


RESULTS = rt.ROOT / "results"
OPENED_NAMES = ("opening.json", "observations.jsonl.gz", "summary.json")
REQUIRED_RESULTS = (
    "preflight.json", "calibration.json", "audit-receipt.json", "forecast.json", *OPENED_NAMES,
)
FROZEN_PATHS = (
    "Protocol.md", "configs/protocol.json", "results/calibration.json", "results/preflight.json",
    "src/analysis.py", "src/measure.py", "src/oracle.py", "src/outcomes.py", "src/runtime.py",
    "src/x12.py", "tests/test_x12.py",
)
ROSTER = {
    f"{family[0].upper()}{index + 1:02}": family
    for family in rt.FAMILIES
    for index in range(len(rt.CONTROLS))
}
SEED_NAMES = ("assignment", "paired", "full", "holdout")


def digest(blob):
    return sha256(blob).hexdigest()


def digest_file(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def canonical(record):
    return (json.dumps(record, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")


def load(path):
    return json.loads(path.read_bytes())


def write_bytes(path, body):
    with path.open("xb") as target:
        target.write(body)


def write_json(path, record):
    write_bytes(path, canonical(record))


def read_canonical(path):
    raw = path.read_bytes()
    value = json.loads(raw)
    if canonical(value) != raw:
        raise ValueError(f"{path.name} does not match the frozen JSON encoding")
    return value, digest(raw)


def git_sha(value):
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{40}", value) is None:
        raise ValueError("Supply a full lowercase Git commit SHA")
    return value


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def as_utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("Supply an ISO 8601 UTC timestamp ending in Z")
    return datetime.fromisoformat(value)


def frozen_paths():
    return {name: digest_file(rt.ROOT / name) for name in FROZEN_PATHS}


def recreate_assignment(seed):
    assignment = {}
    for family in rt.FAMILIES:
        labels = list(rt.CONTROLS)
        rng = rt.random_stream(seed, "assignment", family)
        rng.shuffle(labels)
        slots = [unit for unit, expected in ROSTER.items() if expected == family]
        for unit, control in zip(slots, labels):
            assignment[unit] = {"family": family, "control": control, "variant": rng.randrange(2)}
    return assignment


def installations(assignment):
    return {
        unit: rt.install(coordinates["family"], coordinates["control"], coordinates["variant"])
        for unit, coordinates in sorted(assignment.items())
    }


def selected_audit(private):
    return measure.audit(
        installations(private["assignment"]), private["seeds"]["paired"], private["seeds"]["full"],
    )


def make_receipt(private):
    return {
        "protocol": rt.CONFIG["id"],
        "source_commit": private["source_commit"],
        "reserved_at_utc": private["reserved_at_utc"],
        "private_commitment": digest(canonical(private)),
        "frozen_sha256": private["frozen_sha256"],
        "units": selected_audit(private),
    }


def preflight_records():
    return oracle.exact_preflight(), measure.calibration()


def preflight(args):
    record, reference = preflight_records()
    write_json(args.exact, record)
    write_json(args.calibration, reference)


def validate_public(receipt):
    if receipt["protocol"] != rt.CONFIG["id"] or receipt["frozen_sha256"] != frozen_paths():
        raise ValueError("Public receipt differs from the frozen protocol or calibration")
    git_sha(receipt["source_commit"])
    as_utc(receipt["reserved_at_utc"])
    if re.fullmatch("[0-9a-f]{64}", receipt["private_commitment"]) is None:
        raise ValueError("Invalid reservation commitment")


def reserve(args):
    if args.private.exists() or args.receipt.exists() or args.private.resolve() == args.receipt.resolve():
        raise ValueError("Specify distinct, fresh reservation paths")
    seeds = {name: token_hex(32) for name in SEED_NAMES}
    private = {
        "protocol": rt.CONFIG["id"],
        "source_commit": git_sha(args.source_commit),
        "reserved_at_utc": utc_now(),
        "nonce": token_hex(32),
        "seeds": seeds,
        "assignment": recreate_assignment(seeds["assignment"]),
        "frozen_sha256": frozen_paths(),
    }
    public = make_receipt(private)
    write_json(args.private, private)
    write_json(args.receipt, public)
    print(public["private_commitment"])


def forecast_record(receipt, receipt_hash):
    validate_public(receipt)
    return {
        "protocol": rt.CONFIG["id"],
        "source_commit": receipt["source_commit"],
        "private_commitment": receipt["private_commitment"],
        "audit_receipt_sha256": receipt_hash,
        "confidence": analysis.confidence_design(),
        "threshold": rt.CONFIG["risk_threshold"],
        "units": analysis.forecast_units(receipt["units"], load(RESULTS / "calibration.json"), ROSTER),
    }


def forecast(args):
    receipt, receipt_hash = read_canonical(args.receipt)
    write_json(args.out, forecast_record(receipt, receipt_hash))


def validate_opening(opening, receipt, receipt_hash, forecast_seal, forecast_hash):
    private = opening["private"]
    if (
        private["protocol"] != rt.CONFIG["id"]
        or private["assignment"] != recreate_assignment(private["seeds"]["assignment"])
        or set(private["seeds"]) != set(SEED_NAMES)
        or any(re.fullmatch("[0-9a-f]{64}", seed) is None for seed in private["seeds"].values())
        or re.fullmatch("[0-9a-f]{64}", private["nonce"]) is None
        or receipt["private_commitment"] != digest(canonical(private))
        or receipt["source_commit"] != private["source_commit"]
    ):
        raise ValueError("Private reservation does not open the forecast commitment")
    if forecast_record(receipt, receipt_hash) != forecast_seal:
        raise ValueError("Forecast differs from the allowed audit inputs")
    if (
        opening["forecast_commit"] != opening["verified_remote_tip"]
        or git_sha(opening["forecast_commit"]) == private["source_commit"]
        or opening["receipt_sha256"] != receipt_hash
        or opening["forecast_sha256"] != forecast_hash
        or not (
            as_utc(private["reserved_at_utc"]) < as_utc(opening["verified_at_utc"])
            <= as_utc(opening["opened_at_utc"])
        )
    ):
        raise ValueError("GitHub forecast verification or time order is invalid")
    if make_receipt(private) != receipt:
        raise ValueError("Independent audit receipt cannot be reconstructed")


def write_opened(output, opening, sealed_forecast, receipt_path, forecast_path):
    output.mkdir()
    private = opening["private"]
    installed = installations(private["assignment"])
    raw_path = output / "observations.jsonl.gz"
    raw_hash = outcomes.write_records(raw_path, measure.holdout_records(installed, private["seeds"]["holdout"]))
    write_json(output / "opening.json", opening)
    summary = outcomes.summarize(raw_path, installed, sealed_forecast["units"])
    write_json(output / "summary.json", summary)

    known = {
        "preflight.json": RESULTS / "preflight.json",
        "calibration.json": RESULTS / "calibration.json",
        "audit-receipt.json": receipt_path,
        "forecast.json": forecast_path,
        **{name: output / name for name in OPENED_NAMES},
    }
    manifest = {
        "files_sha256": {name: digest_file(path) for name, path in sorted(known.items())},
        "raw_jsonl_sha256": raw_hash,
        "frozen_sha256": frozen_paths(),
        "all_preregistered_outcome_gates": all(summary["gates"].values()),
    }
    write_json(output / "manifest.json", manifest)
    print(json.dumps({"native_episodes": summary["native_episodes"], "gates": summary["gates"],
                      "manifest_sha256": digest_file(output / "manifest.json")}, sort_keys=True))


def release(args):
    if args.out_dir.exists() or not args.out_dir.parent.is_dir():
        raise ValueError("Release needs a new output directory with an existing parent")
    private, _ = read_canonical(args.private)
    receipt, receipt_hash = read_canonical(args.receipt)
    sealed_forecast, forecast_hash = read_canonical(args.forecast)
    opening = {
        "private": private,
        "receipt_sha256": receipt_hash,
        "forecast_sha256": forecast_hash,
        "forecast_commit": git_sha(args.forecast_commit),
        "verified_remote_tip": git_sha(args.remote_tip),
        "verified_at_utc": args.verified_at_utc,
        "opened_at_utc": utc_now(),
    }
    validate_opening(opening, receipt, receipt_hash, sealed_forecast, forecast_hash)
    write_opened(args.out_dir, opening, sealed_forecast, args.receipt, args.forecast)


def replay(args):
    manifest, _ = read_canonical(RESULTS / "manifest.json")
    expected = manifest["files_sha256"]
    if set(expected) != set(REQUIRED_RESULTS) or any(
        expected[name] != digest_file(RESULTS / name) for name in REQUIRED_RESULTS
    ) or manifest["frozen_sha256"] != frozen_paths():
        raise ValueError("Committed evidence digest mismatch")
    preflight_result, reference = preflight_records()
    if preflight_result != load(RESULTS / "preflight.json") or reference != load(RESULTS / "calibration.json"):
        raise ValueError("Exact preflight or separate calibration does not reproduce")

    opening, _ = read_canonical(RESULTS / "opening.json")
    receipt_path = RESULTS / "audit-receipt.json"
    forecast_path = RESULTS / "forecast.json"
    receipt, receipt_hash = read_canonical(receipt_path)
    sealed_forecast, forecast_hash = read_canonical(forecast_path)
    validate_opening(opening, receipt, receipt_hash, sealed_forecast, forecast_hash)
    scoring = outcomes.summarize(
        RESULTS / "observations.jsonl.gz", installations(opening["private"]["assignment"]), sealed_forecast["units"],
    )
    if scoring != load(RESULTS / "summary.json"):
        raise ValueError("Independent score of the original machine ledger differs")

    write_opened(args.out_dir, opening, sealed_forecast, receipt_path, forecast_path)
    if manifest != load(args.out_dir / "manifest.json"):
        raise ValueError("Regenerated evidence differs from the opened record")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    stages = parser.add_subparsers(required=True)

    phase = stages.add_parser("preflight")
    phase.add_argument("--exact", type=Path, required=True)
    phase.add_argument("--calibration", type=Path, required=True)
    phase.set_defaults(run=preflight)

    phase = stages.add_parser("reserve")
    phase.add_argument("--source-commit", required=True)
    phase.add_argument("--private", type=Path, required=True)
    phase.add_argument("--receipt", type=Path, required=True)
    phase.set_defaults(run=reserve)

    phase = stages.add_parser("forecast")
    phase.add_argument("--receipt", type=Path, required=True)
    phase.add_argument("--out", type=Path, required=True)
    phase.set_defaults(run=forecast)

    phase = stages.add_parser("release")
    phase.add_argument("--private", type=Path, required=True)
    phase.add_argument("--receipt", type=Path, required=True)
    phase.add_argument("--forecast", type=Path, required=True)
    phase.add_argument("--forecast-commit", required=True)
    phase.add_argument("--remote-tip", required=True)
    phase.add_argument("--verified-at-utc", required=True)
    phase.add_argument("--out-dir", type=Path, required=True)
    phase.set_defaults(run=release)

    phase = stages.add_parser("replay")
    phase.add_argument("--out-dir", type=Path, required=True)
    phase.set_defaults(run=replay)

    args = parser.parse_args()
    args.run(args)


if __name__ == "__main__":
    main()
