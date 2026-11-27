"""Independently authenticate the exact X17 freeze and forecast before opening."""

import argparse
from datetime import datetime
from fractions import Fraction as F
import gzip
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import quote

from readback import before_round, readback, require, resource

EXPERIMENT = Path(__file__).resolve().parents[1]
PREFIX = "EXPERIMENTS/EXP-X17/"
BRANCH = "codex/exp-x17"
sys.path.insert(0, str(EXPERIMENT / "independent"))

from model import ARMS, COST_KEYS, Installation, forecast


def git_bytes(commit, path):
    return subprocess.check_output(["git", "show", commit + ":" + PREFIX + path])


def exact_digest(data):
    return sha256(data).hexdigest()


def frozen_table(domain, compressed):
    endpoints = domain["beta_endpoints"]
    betas = domain["interior_beta"]
    fixed = {
        "s01": (["1/4"], endpoints, domain["matched_depths"]),
        "s02": (["3/4"], endpoints, domain["matched_depths"]),
        "s03": (["1/8"], endpoints, domain["extreme_depths"]),
        "s04": (["7/8"], endpoints, domain["extreme_depths"]),
    }
    for i, grid in enumerate(domain["interior_theta_numerators"], 5):
        thetas = [str(F(n, domain["theta_denominator"])) for n in grid]
        fixed[f"s{i:02}"] = thetas, betas, domain["interior_depths"]
    remaining = set()
    for label, (grid, charges, depths) in fixed.items():
        remaining.update((label, F(theta), F(beta), m, k, n, arm)
                         for theta, beta, m, k, n, arm in product(grid, charges, (0, 1), ("L", "R"), depths, ARMS))
    snapshot = gzip.decompress(compressed)
    rows = 0
    for line in snapshot.splitlines():
        label, theta, beta, mode, route, n, arm, published = json.loads(line)
        theta, beta = F(theta), F(beta)
        key = label, theta, beta, mode, route, n, arm
        require(key in remaining, "unregistered or duplicate forecast case")
        remaining.remove(key)
        actual = forecast(Installation(label, theta, beta, mode, route, "good", n), arm)
        require(set(published) == set(COST_KEYS), "registered forecast metric family differs")
        require(all(F(published[endpoint]) == actual[endpoint] for endpoint in COST_KEYS),
                "independent exact forecast disparity")
        rows += 1
    require(not remaining, "incomplete forecast enumeration")
    return rows, exact_digest(snapshot)


def verify(freeze, draw_commit, deps):
    draw_path = "custody/draw-plan.json"
    anchor_path = "custody/registered-freeze-readback.json"
    manifest_path = "manifests/frozen-inputs.json"
    domain_path = "custody/roster-domain.json"
    forecast_path = "manifests/forecast-domain.ndjson.gz"
    candidate_summary = "manifests/forecast-domain-summary.json"
    design = "manifests/registered-design.json"
    method = "independent/registered-method.json"
    draw_bytes = git_bytes(draw_commit, draw_path)
    draw = json.loads(draw_bytes)
    require(draw["source_commit"] == freeze, "frozen source differs from draw")
    schedule = datetime.fromisoformat(draw["scheduled_utc"])
    source_paths = (manifest_path, domain_path, forecast_path, candidate_summary, design, method,
                    "custody/primary-seed-commitment.json", "custody/independent-seed-commitment.json",
                    "PREREGISTRATION.md", "independent/model.py")
    frozen = {path: git_bytes(freeze, path) for path in source_paths}
    primary = git_bytes(draw_commit, anchor_path)
    read_spec = {"objects": [
        {"name": "exact-published-draw", "commit": draw_commit, "branch": BRANCH, "require_activity": True,
         "files": {draw_path: exact_digest(draw_bytes), anchor_path: exact_digest(primary)}},
        {"name": "exact-frozen-source", "commit": freeze,
         "files": {name: exact_digest(data) for name, data in frozen.items()}},
    ]}
    server = readback(read_spec, draw)
    require(server["objects"][0]["parents"] == [freeze], "published draw lacks immediate freeze parent")
    for obj in server["objects"]:
        local_tree = subprocess.check_output(["git", "rev-parse", obj["commit"] + "^{tree}"]).decode().strip()
        require(obj["tree"] == local_tree, "local copy does not match authenticated GitHub tree")
    activity, activity_witness = resource("activity?ref=" + quote("refs/heads/" + BRANCH, safe=""))
    require(before_round(activity_witness, schedule), "late activity read")
    freeze_activity = next((row for row in activity if row.get("after") == freeze), None)
    require(freeze_activity and datetime.fromisoformat(freeze_activity["timestamp"]) < schedule,
            "missing authenticated before-round source publication activity")
    primary_anchor = json.loads(primary)
    require(primary_anchor["round"] == draw["round"] and
            primary_anchor["draw_sha256"] == exact_digest(draw_bytes), "primary readback differs")
    for obj in primary_anchor["objects"]:
        for witness in list(obj["github"].values()) + [r["github"] for r in obj["files"].values()]:
            require(before_round(witness, schedule), "late prerecorded primary witness")

    require(draw["frozen_manifest_sha256"] == exact_digest(frozen[manifest_path]), "manifest not tied to draw")
    require(draw["domain_sha256"] == exact_digest(frozen[domain_path]), "roster not tied to draw")
    manifest = json.loads(frozen[manifest_path])
    for path, entry in manifest["files"].items():
        data = git_bytes(freeze, path)
        require(len(data) == entry["bytes"] and exact_digest(data) == entry["sha256"],
                "frozen artifact differs: " + path)
    current_model = (EXPERIMENT / "independent/model.py").read_bytes().replace(b"\r\n", b"\n")
    require(current_model == frozen["independent/model.py"], "independent predictor differs from its frozen bytes")
    rows, forecast_digest = frozen_table(json.loads(frozen[domain_path]), frozen[forecast_path])
    summary = json.loads(frozen[candidate_summary])
    require(summary["forecast_records"] == rows and
            summary["decompressed_forecasts_sha256"] == forecast_digest and
            summary["stored_forecasts_sha256"] == exact_digest(frozen[forecast_path]), "frozen forecast hashes differ")
    with TemporaryDirectory(prefix="x17-preopening-") as temp:
        directory = Path(temp)
        plan, pending = directory / "plan.json", directory / "pending.json"
        plan.write_bytes(draw_bytes)
        subprocess.run(["node", str(EXPERIMENT / "custody/beacon.mjs"), "pending", str(deps),
                        str(plan), str(pending)], check=True)
        pending_receipt = json.loads(pending.read_bytes())
    return {
        "schema": 1, "role": "independent", "phase": "before-opening",
        "freeze_commit": freeze, "draw_commit": draw_commit, "round": draw["round"],
        "scheduled_utc": draw["scheduled_utc"], "draw_sha256": exact_digest(draw_bytes),
        "registered_freeze_readback_sha256": exact_digest(primary),
        "registered_manifest_sha256": exact_digest(frozen[manifest_path]),
        "registered_domain_sha256": exact_digest(frozen[domain_path]),
        "manifest_files_verified": len(manifest["files"]),
        "forecasts_verified": rows, "uncompressed_forecasts_sha256": forecast_digest,
        "github": server, "freeze_activity": freeze_activity,
        "activity_witness": activity_witness, "pending": pending_receipt,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("freeze")
    parser.add_argument("draw")
    parser.add_argument("dependencies", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    result = verify(args.freeze, args.draw, args.dependencies)
    with args.receipt.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(f"Verified {result['manifest_files_verified']} frozen files, "
          f"{result['forecasts_verified']} exact forecasts and two pending-round relays.")


if __name__ == "__main__":
    main()
