"""Command line entry point. Run python -B src/x08.py --help."""

import argparse
import json
from pathlib import Path

import pipeline


def cli():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    exact = commands.add_parser("exact")
    exact.add_argument("--output", type=Path, required=True)
    reserve = commands.add_parser("reserve")
    reserve.add_argument("--pre-audit-commit", required=True)
    reserve.add_argument("--private", type=Path, required=True)
    reserve.add_argument("--receipt", type=Path, required=True)
    predict = commands.add_parser("predict")
    predict.add_argument("--receipt", type=Path, required=True)
    predict.add_argument("--output", type=Path, required=True)
    release = commands.add_parser("release")
    release.add_argument("--private", type=Path, required=True)
    release.add_argument("--receipt", type=Path, required=True)
    release.add_argument("--forecast-commit", required=True)
    release.add_argument("--output", type=Path, required=True)
    replay = commands.add_parser("replay")
    replay.add_argument("--source", type=Path, default=pipeline.ROOT / "results")
    replay.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = pipeline.load_json(pipeline.ROOT / "configs/protocol.json")
    if args.command == "exact":
        result = pipeline.exact_analysis(spec)
        pipeline.save_json(args.output, result)
    elif args.command == "reserve":
        result = pipeline.reserve(spec, args.pre_audit_commit, args.private, args.receipt)
    elif args.command == "predict":
        receipt = pipeline.load_json(args.receipt)
        prior = pipeline.load_json(pipeline.ROOT / "results/pre-audit.json")
        result = pipeline.make_forecast(spec, receipt, prior)
        pipeline.save_json(args.output, result)
    elif args.command == "release":
        result = pipeline.release(spec, args.private, args.receipt, args.forecast_commit, args.output)
    else:
        result = pipeline.replay(spec, args.source, args.output)
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    cli()
