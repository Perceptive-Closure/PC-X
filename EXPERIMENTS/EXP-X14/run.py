"""EXP-X14 entry points for GitHub source archives."""

import argparse
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from common import canonical, read, utc_now, write
from custody import make_forecast, manifest, open_installation, replay, seal
from preflight import bounded_study, measured_run, pre_audit


def prepare(destination):
    destination = Path(destination)
    destination.mkdir(parents=False, exist_ok=True)
    exact_path = destination / "exact.json"
    audit_path = destination / "pre-audit.json"
    runtime_path = destination / "runtime-observed.json"
    if any(path.exists() for path in (exact_path, audit_path, runtime_path)):
        raise ValueError("Preparation requires new evidence paths")
    exact, exact_timing = measured_run(bounded_study)
    audit, audit_timing = measured_run(pre_audit)
    write(exact_path, canonical(exact))
    write(audit_path, canonical(audit))
    write(runtime_path, canonical({
        "python": platform.python_version(), "os": platform.system(),
        "bounded_study": exact_timing, "external_pre_audit": audit_timing,
    }))
    return {"bounded": exact["checks"],
            "minimum_external_audit_cost": audit["audit"]["minimum_worst_cost"]}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    commands.add_parser("prepare").add_argument("--out-dir", required=True)
    reserve = commands.add_parser("seal")
    for field in ("protocol-commit", "source-commit", "sealed", "receipt"):
        reserve.add_argument(f"--{field}", required=True)
    forecast = commands.add_parser("forecast")
    forecast.add_argument("--receipt", required=True)
    forecast.add_argument("--out", required=True)
    outcome = commands.add_parser("open")
    for field in ("sealed", "receipt", "forecast", "forecast-commit",
                  "remote-tip", "verified-at-utc", "out-dir"):
        outcome.add_argument(f"--{field}", required=True)
    commands.add_parser("manifest").add_argument("--out", required=True)
    commands.add_parser("replay")
    args = cli.parse_args()
    if args.command == "prepare":
        result = prepare(args.out_dir)
    elif args.command == "seal":
        result = {"commitment": seal(args.protocol_commit, args.source_commit, args.sealed, args.receipt)}
    elif args.command == "forecast":
        result = make_forecast(read(args.receipt), utc_now())
        write(args.out, canonical(result))
        result = {"policy_sha256": result["policy_sha256"], "ports": len(result["policies"])}
    elif args.command == "open":
        result = open_installation(args.sealed, args.receipt, args.forecast, args.forecast_commit,
                                   args.remote_tip, args.verified_at_utc, args.out_dir)
    elif args.command == "manifest":
        result = manifest()
        write(args.out, canonical(result))
        result = {"files": len(result)}
    else:
        result = replay()
    print(canonical(result).decode("ascii"), end="")


if __name__ == "__main__":
    main()
