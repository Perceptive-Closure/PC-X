"""Verify a byte-exact X16 freeze or an authenticated post-round opening."""

import argparse
from datetime import datetime
from email.utils import parsedate_to_datetime
from hashlib import sha1, sha256
import json
from pathlib import Path
import re
import subprocess

from chronology import (EXPERIMENT, commit, digest, ensure, files_at, json_file,
                        scheduled, verify_forecast_receipt, write)
from selector import select_installations


MANIFEST = "custody/frozen-manifest.json"
FUTURE = (
    "custody/authority.json", "custody/beacon.json", "custody/commitment-receipt.json",
    "custody/draw-plan.json", "custody/draw-signature.json", "custody/frozen-manifest.json",
    "custody/heldout.json", "custody/opening.json", "custody/prerelease-receipt.json",
)


def make_manifest(repository):
    names = subprocess.check_output([
        "git", "-C", str(repository), "ls-files", "-z", "--", EXPERIMENT,
    ]).decode("utf-8").split("\0")
    files = {}
    for name in filter(None, names):
        relative = name.removeprefix(EXPERIMENT + "/")
        if relative in (*FUTURE, "Path.md") or relative.startswith("results/"):
            continue
        blob = subprocess.check_output(["git", "-C", str(repository), "show", ":" + name])
        files[relative] = sha256(blob).hexdigest()
    ensure(len(files) >= 25, "incomplete staged registration source")
    frozen = {"schema": 1, "files": files}
    write(repository / EXPERIMENT / MANIFEST, frozen)
    return frozen


def verify_frozen(root):
    manifest = json_file(root / MANIFEST)
    ensure(manifest["schema"] == 1 and len(manifest["files"]) >= 25, "incomplete freeze manifest")
    for name, expected in manifest["files"].items():
        file = (root / name).resolve()
        ensure(file.is_relative_to(root) and file.is_file() and digest(file) == expected,
               "frozen path hash differs: " + name)
    return manifest


def check_opening(root, deps, remote):
    manifest = verify_frozen(root)
    draw_path = root / "custody/draw-plan.json"
    beacon_path = root / "custody/beacon.json"
    heldout = root / "custody/heldout.json"
    forecast_path = root / "results/forecast.json"
    authority_path = root / "custody/authority.json"
    catalogue = root / "cases/catalogue.json"
    draw = json_file(draw_path)
    forecast = json_file(forecast_path)
    opening = json_file(root / "custody/opening.json")
    forecast_receipt = json_file(root / "results/forecast-receipt.json")
    custody_receipt = json_file(root / "custody/prerelease-receipt.json")
    selected = json_file(beacon_path)
    ensure(opening["schema"] == 1 and opening["round"] == draw["round"] == selected["beacon"]["round"],
           "opening or BLS round differs")
    frozen_commit = draw["source_commit"]
    ensure(re.fullmatch("[a-f0-9]{40}", frozen_commit) is not None and frozen_commit != "0" * 40,
           "opening source identity malformed")
    forecast_blob = sha1(f"blob {forecast_path.stat().st_size}\0".encode("ascii") +
                         forecast_path.read_bytes()).hexdigest()
    required = {
        "source_commit": frozen_commit, "draw_sha256": digest(draw_path),
        "authority_sha256": digest(authority_path), "forecast_sha256": digest(forecast_path),
        "forecast_git_blob": forecast_blob, "heldout_sha256": digest(heldout),
        "beacon_sha256": digest(beacon_path),
    }
    for key, value in required.items():
        ensure(opening[key] == value, "opening digest differs " + key)
    for witness in (forecast_receipt, custody_receipt):
        verify_forecast_receipt(witness, draw)
        for key in ("source_commit", "commitment_commit", "forecast_commit", "forecast_sha256",
                    "forecast_git_blob", "draw_sha256", "authority_sha256"):
            ensure(witness[key] == opening[key], "independent custody and chronology differ: " + key)
    published_lock = opening["prerelease_github_ref"]
    ensure(published_lock["status"] == 200
           and published_lock["resource"] == "git/ref/heads/codex/exp-x16-custody"
           and parsedate_to_datetime(published_lock["http_date"]) < scheduled(draw)
           and datetime.fromisoformat(published_lock["observed_utc"]) < scheduled(draw)
           and len({published_lock["request_id"], forecast_receipt["github_ref"]["request_id"],
                    custody_receipt["github_ref"]["request_id"]}) == 3,
           "three distinct GitHub reads, including custody publication, required before opening")
    ensure(forecast["source_commit"] == frozen_commit and forecast["draw_sha256"] == required["draw_sha256"],
           "forecast metadata differs")
    ensure(datetime.fromisoformat(selected["verified_utc"]) >= scheduled(draw), "opening early")
    ensure(len(selected["fetched"]) == 2 and all(datetime.fromisoformat(row["observed_utc"]) >= scheduled(draw)
                                               and row["status"] == 200 for row in selected["fetched"]),
           "missing two post-round relay reads")
    subprocess.run(["node", str(root / "custody/authority.mjs"), "check", str(catalogue), frozen_commit,
                    str(root / MANIFEST), str(draw_path), str(authority_path),
                    str(root / "custody/draw-signature.json")], check=True)
    subprocess.run(["node", str(root / "custody/beacon.mjs"), "verify", str(deps),
                    str(draw_path), str(beacon_path)], check=True)
    expected = select_installations(json_file(catalogue), selected["beacon"]["randomness"])
    ensure(json.loads(json.dumps(expected)) == json_file(heldout), "selection differs from registered rule")
    if remote:
        f = files_at(frozen_commit, [MANIFEST])
        ensure(f[MANIFEST][1] == (root / MANIFEST).read_bytes(), "frozen GitHub manifest differs")
        names = ["results/forecast.json", "custody/draw-plan.json", "custody/authority.json",
                 "custody/draw-signature.json"]
        from_forecast = files_at(opening["forecast_commit"], names)
        ensure(all((root / name).read_bytes() == from_forecast[name][1] for name in names),
               "registered GitHub objects differ from local opening")
        pref = files_at(opening["prerelease_commit"], ["custody/prerelease-receipt.json"])
        ensure(pref["custody/prerelease-receipt.json"][1] ==
               (root / "custody/prerelease-receipt.json").read_bytes(), "custody prerelease GitHub object differs")
        g, _ = commit(opening["commitment_commit"])
        p, _ = commit(opening["forecast_commit"])
        k, _ = commit(opening["prerelease_commit"])
        ensure(len(k["parents"]) == 1, "custody registration must have one parent")
        receipt_commit = k["parents"][0]["sha"]
        r, _ = commit(receipt_commit)
        recorded = files_at(receipt_commit, ["results/forecast-receipt.json"])
        ensure(recorded["results/forecast-receipt.json"][1] == (root / "results/forecast-receipt.json").read_bytes(),
               "parent prerelease readback differs")
        ensure([item["sha"] for item in g["parents"]] == [frozen_commit]
               and [item["sha"] for item in p["parents"]] == [opening["commitment_commit"]]
               and [item["sha"] for item in r["parents"]] == [opening["forecast_commit"]], "tree lineage differs")
    print(f"Verified official opening of round {opening['round']} for {len(expected)} selected installations.")
    return opening


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_subparsers(dest="operation", required=True)
    for mode in ("make", "freeze", "opening"):
        step = operation.add_parser(mode)
        step.add_argument("root", type=lambda value: Path(value).resolve())
        if mode == "opening":
            step.add_argument("deps", type=lambda value: Path(value).resolve())
            step.add_argument("--remote", action="store_true")
    args = parser.parse_args()
    if args.operation == "make":
        manifest = make_manifest(args.root)
    elif args.operation == "freeze":
        manifest = verify_frozen(args.root)
    else:
        check_opening(args.root, args.deps, args.remote)
        return
    print(f"{len(manifest['files'])} frozen source files.")


if __name__ == "__main__":
    main()
