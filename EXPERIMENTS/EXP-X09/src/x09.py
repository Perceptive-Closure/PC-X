"""Command-line entry points for the frozen EXP-X09 study."""

import argparse
from pathlib import Path

import custody
from contract import read, save
from exact import baseline
from measure import development


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    for name in ("exact", "develop", "predict", "release", "replay"):
        command = subcommands.add_parser(name)
        command.add_argument("--output", required=True, type=Path)
        if name in ("predict", "release"):
            command.add_argument("--receipt", required=True, type=Path)
        if name == "release":
            command.add_argument("--private", required=True, type=Path)
            command.add_argument("--forecast", required=True, type=Path)
            command.add_argument("--forecast-commit", required=True)
            command.add_argument("--github-verified-utc", required=True)
    reserve = subcommands.add_parser("reserve")
    reserve.add_argument("--source-commit", required=True)
    reserve.add_argument("--private", required=True, type=Path)
    reserve.add_argument("--receipt", required=True, type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.command == "exact":
        save(args.output, baseline())
    elif args.command == "develop":
        save(args.output, development())
    elif args.command == "reserve":
        receipt = custody.reserve(args.source_commit, args.private, args.receipt)
        print(receipt["assignment_commitment_sha256"])
    elif args.command == "predict":
        save(args.output, custody.predict(read(args.receipt)))
    elif args.command == "release":
        report = custody.release(
            args.private, args.receipt, args.forecast, args.forecast_commit,
            args.github_verified_utc, args.output,
        )
        print(f"Preregistered unit gates passed: {report['all_frozen_unit_gates_passed']}")
    elif args.command == "replay":
        report = custody.replay(args.output)
        print(f"Verified {report['raw']['native']['rows']} native episodes and "
              f"{report['raw']['factorial']['rows']} factorial draws")


if __name__ == "__main__":
    main()
