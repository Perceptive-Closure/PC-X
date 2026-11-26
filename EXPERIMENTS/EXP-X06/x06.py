"""Staged interface for EXP-X06. The preaudit and audit stages never launch OPA."""

import argparse
from datetime import datetime
from pathlib import Path
import sys

from common import RESULTS, ROOT, canonical, file_digest, read, require, utc, write_once


def staged_native(binary, temp, directory):
    from custody import validate_release
    from native import OPA, measure
    from verify import verify_native

    assignment = read(directory / "assignment.json")
    authorization = read(directory / "authorization.json")
    forecast = validate_release(assignment, authorization)
    opened = utc()
    require(datetime.fromisoformat(authorization["verified_utc"]) <= datetime.fromisoformat(opened),
            "native opening predates forecast verification")
    for name in ("native.json", "summary.json", "release.json", "failure.json"):
        require(not (directory / name).exists(), f"refusing repeated native opening in {directory}")
    try:
        trace = measure(OPA(binary, temp), assignment)
        write_once(directory / "native.json", trace)
        summary = verify_native(trace, assignment, forecast)
        write_once(directory / "summary.json", summary)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        write_once(directory / "failure.json", {
            "opened_utc": opened, "recorded_utc": utc(), "type": type(error).__name__,
            "reason": str(error), "authorization": authorization,
        })
        raise
    record = {
        "assignment": assignment,
        "authorization": authorization,
        "opened_utc": opened,
        "completed_utc": utc(),
        "native_sha256": file_digest(directory / "native.json"),
        "summary_sha256": file_digest(directory / "summary.json"),
    }
    write_once(directory / "release.json", record)
    return summary


def recorded():
    from custody import validate_release
    from verify import verify_native

    release = read(RESULTS / "release.json")
    forecast = validate_release(release["assignment"], release["authorization"])
    require(datetime.fromisoformat(release["authorization"]["verified_utc"])
            <= datetime.fromisoformat(release["opened_utc"])
            <= datetime.fromisoformat(release["completed_utc"]), "opening dates out of order")
    for name in ("native", "summary"):
        require(release[name + "_sha256"] == file_digest(RESULTS / f"{name}.json"),
                f"stored {name} differs from opening seal")
    summary = verify_native(read(RESULTS / "native.json"), release["assignment"], forecast)
    require(canonical(summary) == (RESULTS / "summary.json").read_bytes(), "measured summary differs")
    return release, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    stages = parser.add_subparsers(dest="stage", required=True)
    pre = stages.add_parser("preaudit")
    pre.add_argument("--deps", type=Path, default=ROOT / "scratch/deps")
    mode = pre.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    for stage_name in ("seal", "audit", "authorize", "open"):
        stage = stages.add_parser(stage_name)
        stage.add_argument("--dir", dest="directory", type=Path, required=True)
        if stage_name == "seal":
            stage.add_argument("--freeze-commit", required=True)
        if stage_name == "authorize":
            stage.add_argument("--forecast-commit", required=True)
            stage.add_argument("--frozen-root", type=Path, required=True)
    predict = stages.add_parser("forecast")
    predict.add_argument("--receipt", type=Path, required=True)
    for stage_name in ("development", "replay"):
        stages.add_parser(stage_name)
    stages.add_parser("check-evidence")
    for stage_name in ("development", "open", "replay"):
        stage = stages.choices[stage_name]
        stage.add_argument("--opa", type=Path, required=True)
        stage.add_argument("--temp", type=Path, default=ROOT / "scratch/tmp")
    args = parser.parse_args()

    if args.stage == "preaudit":
        from contract import preaudit
        result = preaudit(args.deps)
        target = RESULTS / "preaudit.json"
        if args.write:
            write_once(target, result)
        else:
            require(canonical(result) == target.read_bytes(), "frozen preaudit differs")
        result = {
            "preaudit_sha256": file_digest(target),
            "completions": len(result["completions"]),
            "queries": result["selected"],
            "audit_cost": result["audit_cost"],
            "lazy_rounds": len(result["lazy_transcript"]),
        }
    elif args.stage == "seal":
        from custody import seal
        require(not (ROOT.parent.parent / ".git").exists(), "use an exact GitHub archive for the holdout")
        result = seal(args.directory, args.freeze_commit)
    elif args.stage == "audit":
        from custody import audit
        result = audit(args.directory)
    elif args.stage == "forecast":
        from custody import forecast
        result = forecast(args.receipt, RESULTS / "forecast.json")
    elif args.stage == "authorize":
        from custody import authorize
        result = authorize(args.directory, args.frozen_root, args.forecast_commit)
    elif args.stage == "development":
        from native import OPA, development
        from verify import verify_development
        engine = OPA(args.opa, args.temp)
        controls = development(engine)
        verify_development(controls)
        result = {"engine": engine.version, "development": controls}
    elif args.stage == "open":
        result = staged_native(args.opa, args.temp, args.directory)
    elif args.stage == "check-evidence":
        _, result = recorded()
    else:
        from native import OPA, measure
        release, summary = recorded()
        trace = measure(OPA(args.opa, args.temp), release["assignment"])
        require(canonical(trace) == (RESULTS / "native.json").read_bytes(), "fresh native trace differs")
        result = {"native_sha256": release["native_sha256"], "reproduced": summary}
    sys.stdout.buffer.write(canonical(result))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        sys.exit(f"EXP-X06 {type(error).__name__}: {error}")
