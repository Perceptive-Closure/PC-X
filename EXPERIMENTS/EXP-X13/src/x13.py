"""CLI for the frozen X13 protocol and clean-archive replay."""

import argparse

from common import assert_canonical, canonical, utc_now, write
from preflight import run as run_pre_audit
from stages import make_forecast, manifest, open_outcome, replay, reserve


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="stage", required=True)
    commands.add_parser("pre-audit").add_argument("--out", required=True)
    seal = commands.add_parser("seal")
    for flag in ("protocol-commit", "source-commit", "sealed", "receipt"):
        seal.add_argument(f"--{flag}", required=True)
    forecast = commands.add_parser("forecast")
    forecast.add_argument("--receipt", required=True)
    forecast.add_argument("--out", required=True)
    opening = commands.add_parser("open")
    for flag in ("sealed", "receipt", "forecast", "forecast-commit", "remote-tip",
                 "verified-at-utc", "out-dir"):
        opening.add_argument(f"--{flag}", required=True)
    commands.add_parser("manifest").add_argument("--out", required=True)
    commands.add_parser("replay")
    args = parser.parse_args()

    if args.stage == "pre-audit":
        write(args.out, canonical(run_pre_audit()))
    elif args.stage == "seal":
        print(reserve(args.protocol_commit, args.source_commit, args.sealed, args.receipt))
    elif args.stage == "forecast":
        receipt = assert_canonical(args.receipt)
        write(args.out, canonical(make_forecast(receipt, utc_now())))
    elif args.stage == "open":
        result = open_outcome(args.sealed, args.receipt, args.forecast, args.forecast_commit,
                              args.remote_tip, args.verified_at_utc, args.out_dir)
        print(canonical(result).decode("ascii"), end="")
    elif args.stage == "manifest":
        write(args.out, canonical(manifest()))
    elif args.stage == "replay":
        print(canonical(replay()).decode("ascii"), end="")


if __name__ == "__main__":
    main()
