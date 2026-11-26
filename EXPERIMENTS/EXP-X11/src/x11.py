"""No-Git CLI for EXP-X11. Custody roles use separate ordered stages."""

import argparse
from pathlib import Path

from common import CONFIG, digest, read_json, write_json
from model import pre_audit
from pipeline import RESULTS, build_manifest, make_forecast, open_holdout, replay, seal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="stage", required=True)
    prepare = commands.add_parser("pre-audit")
    prepare.add_argument("--out", required=True, type=Path)
    custody = commands.add_parser("seal")
    custody.add_argument("--protocol-commit", required=True)
    custody.add_argument("--source-commit", required=True)
    custody.add_argument("--sealed", required=True, type=Path)
    custody.add_argument("--receipt", required=True, type=Path)
    forecast = commands.add_parser("forecast")
    forecast.add_argument("--receipt", required=True, type=Path)
    forecast.add_argument("--out", required=True, type=Path)
    opening = commands.add_parser("open")
    opening.add_argument("--sealed", required=True, type=Path)
    opening.add_argument("--receipt", required=True, type=Path)
    opening.add_argument("--forecast", required=True, type=Path)
    opening.add_argument("--forecast-commit", required=True)
    opening.add_argument("--out-dir", required=True, type=Path)
    commands.add_parser("manifest")
    reproduction = commands.add_parser("replay")
    reproduction.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    protocol = read_json(CONFIG)

    if args.stage == "pre-audit":
        result = pre_audit(protocol)
        write_json(args.out, result)
        print(digest(result))
    elif args.stage == "manifest":
        print(digest(build_manifest()))
    elif args.stage == "replay":
        print(replay(protocol, args.out_dir)["analysis"]["raw_sha256"])
    else:
        prior = read_json(RESULTS / "pre-audit.json")
        if args.stage == "seal":
            print(seal(protocol, prior, args.protocol_commit, args.source_commit,
                       args.sealed, args.receipt))
        elif args.stage == "forecast":
            result = make_forecast(protocol, prior, read_json(args.receipt))
            write_json(args.out, result)
            print(digest(result))
        elif args.stage == "open":
            result = open_holdout(protocol, prior, read_json(args.sealed), read_json(args.receipt),
                                  read_json(args.forecast), args.forecast_commit, args.out_dir)
            print(result["analysis"]["raw_sha256"])


if __name__ == "__main__":
    main()
