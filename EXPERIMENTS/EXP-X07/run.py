"""EXP-X07 offline verification and prospective custody entry points."""

import argparse
from pathlib import Path

from src.evaluate import forecast, load_pre_outcome, score, sealed_prediction
from src.fixtures import audit, check_inventory, check_reveal, seed
from src.model import validate_x03
from src.native import OpenSSL, native_outcomes, stage_initial
from src.records import check_git_sha, file_digest, parse_utc, protocol, read_json, require, utc_now, write_json


def engine(args, spec):
    return OpenSSL(spec, args.openssl, args.evidence / "public", args.temp)


def command_seed(args, spec):
    commitment = seed(spec, args.run_dir, args.protocol_commit, args.protocol_registered_at)
    print(f"Custody commitment {commitment['reveal_sha256']}")


def command_solve(args, spec):
    checked = validate_x03(spec, args.x03_source)
    write_json(args.out, checked)
    print(f"Uniform cost {checked['uniform']['cost']}, saved {file_digest(args.out)}")


def command_diagnose(args, spec):
    public = args.evidence / "public"
    commitment = read_json(args.evidence / "commitment.json")
    check_inventory(spec, public, commitment)
    write_json(args.evidence / "audit.json", audit(spec, public))
    write_json(args.evidence / "diagnostics.json", stage_initial(spec, engine(args, spec)))
    print(f"Initial diagnostics and independent audit for {commitment['reveal_sha256']}")


def command_predict(args, spec):
    _, observed, diagnostics = load_pre_outcome(spec, args.evidence)
    path = args.evidence / "prediction.json"
    write_json(path, forecast(spec, args.evidence, observed, diagnostics))
    print(f"Pre-outcome prediction {file_digest(path)}")


def check_receipt(receipt, commitment, prediction_path):
    check_git_sha(receipt["forecast_commit"])
    require(receipt["repository"] == "Perceptive-Closure/PC-X", "Unexpected forecast repository")
    require(receipt["prediction_sha256"] == file_digest(prediction_path), "Forecast digest differs")
    require(
        parse_utc(commitment["created_at"]) <= parse_utc(receipt["forecast_verified_at"])
        <= parse_utc(receipt["native_started_at"]),
        "Forecast verification must follow fixture commitment and precede native start",
    )


def command_open(args, spec):
    commitment, observed, diagnostics = load_pre_outcome(spec, args.evidence)
    prediction = sealed_prediction(spec, args.evidence, observed, diagnostics)
    reveal = read_json(args.reveal)
    check_reveal(spec, commitment, reveal, observed)
    receipt = {
        "repository": "Perceptive-Closure/PC-X",
        "forecast_commit": args.verified_forecast_commit,
        "forecast_verified_at": args.forecast_verified_at,
        "prediction_sha256": args.verified_prediction_sha256,
        "native_started_at": utc_now(),
    }
    check_receipt(receipt, commitment, args.evidence / "prediction.json")
    verifier = engine(args, spec)
    require(verifier.identity == diagnostics["openssl"], "Native binary differs from initial diagnostics")
    args.post.mkdir()
    write_json(args.post / "receipt.json", receipt)
    write_json(args.post / "reveal.json", reveal)
    actual = native_outcomes(spec, verifier)
    actual["completed_at"] = utc_now()
    write_json(args.post / "native.json", actual)
    check_inventory(spec, args.evidence / "public", commitment)
    scored = score(spec, prediction, actual)
    write_json(args.post / "results.json", scored)
    print(scored["verdict"])


def command_check(args, spec):
    commitment, observed, diagnostics = load_pre_outcome(spec, args.evidence)
    prediction = sealed_prediction(spec, args.evidence, observed, diagnostics)
    if args.post is None:
        require(not args.replay, "Replay needs --post")
        print("Pre-outcome evidence and frozen forecast verified")
        return
    post = args.post
    reveal = read_json(post / "reveal.json")
    check_reveal(spec, commitment, reveal, observed)
    receipt = read_json(post / "receipt.json")
    check_receipt(receipt, commitment, args.evidence / "prediction.json")
    actual = read_json(post / "native.json")
    require(
        parse_utc(receipt["native_started_at"]) <= parse_utc(actual["completed_at"]),
        "Outcome completion predates native start",
    )
    require(actual["openssl"] == diagnostics["openssl"], "Recorded OpenSSL identities differ")
    scored = score(spec, prediction, actual)
    require(scored == read_json(post / "results.json"), "Stored score differs")
    if args.replay:
        require(args.temp is not None and args.openssl is not None, "Replay needs --openssl and --temp")
        verifier = engine(args, spec)
        require(verifier.identity["sha256"] == actual["openssl"]["sha256"], "Replay verifier differs")
        initial = stage_initial(spec, verifier)
        for field in ("cases", "approved_issuer_fields"):
            require(initial[field] == diagnostics[field], f"Initial native replay differs: {field}")
        require(native_outcomes(spec, verifier)["cases"] == actual["cases"], "Outcome native replay differs")
    print(f"{scored['verdict']}. Custody, native records and scores verified.")


def add_engine_args(parser, *, required=True):
    parser.add_argument("--openssl", type=Path, required=required)
    parser.add_argument("--temp", type=Path, required=required)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    step = actions.add_parser("solve", help="Compare exact uniform and realized costs with pinned X03")
    step.add_argument("--x03-source", type=Path, required=True)
    step.add_argument("--out", type=Path, required=True)
    step.set_defaults(handler=command_solve)

    step = actions.add_parser("seed", help="Custodian generates fixtures after remote registration")
    step.add_argument("--run-dir", type=Path, required=True)
    step.add_argument("--protocol-commit", required=True)
    step.add_argument("--protocol-registered-at", required=True)
    step.set_defaults(handler=command_seed)

    for action, handler in (
        ("diagnose", command_diagnose), ("predict", command_predict),
        ("open", command_open), ("check", command_check),
    ):
        step = actions.add_parser(action)
        step.add_argument("--evidence", type=Path, required=True)
        step.set_defaults(handler=handler)
        if action in {"diagnose", "open", "check"}:
            add_engine_args(step, required=action != "check")
        if action in {"open", "check"}:
            step.add_argument("--post", type=Path, required=action == "open")
        if action == "open":
            step.add_argument("--reveal", type=Path, required=True)
            step.add_argument("--verified-forecast-commit", required=True)
            step.add_argument("--forecast-verified-at", required=True)
            step.add_argument("--verified-prediction-sha256", required=True)
        if action == "check":
            step.add_argument("--replay", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    args.handler(args, protocol())


if __name__ == "__main__":
    main()
