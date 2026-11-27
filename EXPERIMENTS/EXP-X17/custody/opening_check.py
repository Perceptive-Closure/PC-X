"""Verify the immutable PH-06 records and prepare a committed role seed reveal."""

import argparse
from datetime import datetime, timezone
from fractions import Fraction as F
import gzip
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

from readback import require
from selector import SELECTOR, canonical, select_worlds

EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT / "independent"))

from model import COST_KEYS, forecast_roster

FREEZE = "be574f4eaba8a52b50c5604e87075ab4cac81b79"
DRAW = "43c1f0c8f90a87b3f5f0e66b1a0722816b9cac1c"
PREOPEN = "bae5fd2832a9d7ff7d43678b2d166d943335062f"
OPENING = "b9840c50a4e409446ed97a335c7179c48f08b596"
AUTHORIZATION = "19c9bc68a9f9f98d99a96a6fb662ded73d50e75c"
INDEPENDENT_BEFORE_OPENING = "0c4d02f1444200a377a382f6ed628e2239960fdf"
SEED_COMMIT = "15ced39e31514bdded53c8e68ef256b05498d374"
PREFIX = "EXPERIMENTS/EXP-X17/"


def git(*args):
    return subprocess.check_output(["git", *args])


def digest(data):
    return sha256(data).hexdigest()


def artifact(commit, name):
    return git("show", f"{commit}:{PREFIX}{name}")


def write_json(path, record):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(record, indent=2, sort_keys=True) + "\n")


def verify(official, deps, private):
    for parent, child in zip((FREEZE, DRAW, PREOPEN, OPENING), (DRAW, PREOPEN, OPENING, AUTHORIZATION)):
        require(git("rev-parse", child + "^").decode().strip() == parent, "authorized ancestry differs")
    frozen = (official / "manifests/frozen-inputs.json").read_bytes()
    require(frozen == artifact(FREEZE, "manifests/frozen-inputs.json"), "frozen manifest bytes differ")
    all_frozen = json.loads(frozen)["files"]
    for rel, entry in all_frozen.items():
        data = (official / rel).read_bytes()
        require(len(data) == entry["bytes"] and digest(data) == entry["sha256"],
                "authorized checkout changed its frozen artifact: " + rel)

    c = official / "custody"
    gate_bytes = (c / "run-authorization.json").read_bytes()
    require(gate_bytes == artifact(AUTHORIZATION, "custody/run-authorization.json"), "authorization bytes differ")
    gate = json.loads(gate_bytes)
    require((gate["schema"], gate["phase"], gate["round"], gate["freeze_commit"], gate["draw_commit"],
             gate["preopening_commit"], gate["opening_commit"])
            == (1, "PH-06-VERIFIED", 34323065, FREEZE, DRAW, PREOPEN, OPENING), "wrong gate identity")
    require(all(digest((c / name).read_bytes()) == expected for name, expected in gate["files"].items()),
            "gate file checksum mismatch")
    require((c / "independent-prerelease.json").read_bytes()
            == artifact(INDEPENDENT_BEFORE_OPENING, "custody/independent-prerelease.json"),
            "official gate does not retain exact independent-before-opening bytes")

    draw_bytes = (c / "draw-plan.json").read_bytes()
    beacon_bytes = (c / "verified-beacon.json").read_bytes()
    opening_bytes = (c / "opening-roster.json").read_bytes()
    domain_bytes = (c / "roster-domain.json").read_bytes()
    subprocess.run(["node", str(EXPERIMENT / "custody/beacon.mjs"), "verify", str(deps),
                    str(c / "draw-plan.json"), str(c / "pre-opening-pending.json"),
                    str(c / "verified-beacon.json")], check=True)
    opening = json.loads(opening_bytes)
    draw = json.loads(draw_bytes)
    beacon = json.loads(beacon_bytes)["beacon"]
    require(draw["round"] == beacon["round"] and draw["domain_sha256"] == digest(domain_bytes), "opening input links differ")
    reconstructed = {"schema": 1, "selector": SELECTOR, "round": beacon["round"],
                     "domain_sha256": digest(domain_bytes), "draw_sha256": digest(draw_bytes),
                     "beacon_sha256": digest(beacon_bytes),
                     "worlds": select_worlds(json.loads(domain_bytes), beacon["randomness"])}
    require(canonical(reconstructed) == opening_bytes, "independent deterministic roster differs")

    expected = json.loads((c / "selected-forecasts.json").read_bytes())
    independent = forecast_roster(opening)["predictions"]
    require(expected["predictions"] == independent and expected["verified_selected_rows"] == 40
            and expected["opening_sha256"] == digest(opening_bytes), "actual or nominal selected forecast differs")
    lookup = {(r["id"], F(r["theta"]), F(r["beta"]), r["m"], r["k"], r["N"]) for r in opening["worlds"]}
    table = official / "manifests/forecast-domain.ndjson.gz"
    covered = set()
    with gzip.open(table, "rt", encoding="utf-8") as stream:
        for row in map(json.loads, stream):
            label, theta, beta, mode, route, n, arm, metrics = row
            if (label, F(theta), F(beta), mode, route, n) not in lookup:
                continue
            require((label, arm) not in covered and all(F(metrics[k]) == F(independent[label][arm]["actual"][k])
                                                        for k in COST_KEYS), "frozen forecast row differs")
            covered.add((label, arm))
    require(len(covered) == 40, "not every selected actual forecast was present before opening")

    commitment_bytes = (c / "independent-seed-commitment.json").read_bytes()
    require(commitment_bytes == artifact(SEED_COMMIT, "custody/independent-seed-commitment.json"),
            "seed commitment differs from immutable pre-draw record")
    commitment = json.loads(commitment_bytes)
    seed = private.read_bytes()
    require(commitment["role"] == "independent" and len(seed) == commitment["bytes"] == 32
            and digest(seed) == commitment["sha256"], "role seed commitment does not match")
    primary = json.loads((c / "primary-seed-reveal.json").read_bytes())
    primary_commitment = json.loads((c / "primary-seed-commitment.json").read_bytes())
    require(digest(bytes.fromhex(primary["seed_hex"])) == primary["commitment_sha256"] == primary_commitment["sha256"]
            and seed.hex() != primary["seed_hex"], "primary role commitment or stream separation differs")
    reveal = {"schema": 1, "role": "independent", "commitment_sha256": commitment["sha256"],
              "commitment_commit": SEED_COMMIT, "opening_commit": OPENING, "authorization_commit": AUTHORIZATION,
              "seed_hex": seed.hex()}
    checks = {"schema": 1, "role": "independent", "authorization_commit": AUTHORIZATION,
              "authorization_sha256": digest(gate_bytes), "opening_commit": OPENING,
              "round": gate["round"], "bls_quicknet_verified": True,
              "registered_roster_matches": True, "frozen_artifacts_verified": len(all_frozen),
              "authorization_files_verified": len(gate["files"]), "actual_forecasts_compared_to_frozen_table": len(covered),
              "actual_and_nominal_predictions_verified": 2 * len(covered),
              "seed_commitment_matches": True, "roles_have_distinct_seed_bytes": True,
              "observed_utc": datetime.now(timezone.utc).isoformat()}
    return checks, reveal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ("official", "deps", "private", "checks", "reveal"):
        parser.add_argument(argument, type=Path)
    args = parser.parse_args()
    checks, reveal = verify(args.official, args.deps, args.private)
    write_json(args.checks, checks)
    write_json(args.reveal, reveal)
    print("PH-06 verified, including 40 prior selected forecasts and both role seed commitments.")


if __name__ == "__main__":
    main()
