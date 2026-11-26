"""Retrieve and authenticate fixed GitHub inputs for the X15 audit."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
from datetime import datetime, timezone
from urllib.parse import quote
from zipfile import ZipFile

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[1]
SCRATCH = ROOT / "scratch" / "audit"
API = "repos/Perceptive-Closure/PC-X"
EXPERIMENT = re.compile(r"X(?:0[1-9]|1[0-4])")
COMMIT = re.compile("[0-9a-f]{40}")
RESERVED = {"CON", "PRN", "AUX", "NUL", *(
    f"{prefix}{index}" for prefix in ("COM", "LPT") for index in range(1, 10)
)}


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def gh(endpoint):
    result = subprocess.run(
        ["gh", "api", "--method", "GET", endpoint],
        cwd=ROOT,
        env={
            **os.environ,
            "GH_NO_UPDATE_NOTIFIER": "1",
            "TMP": str(SCRATCH / "tmp"),
            "TEMP": str(SCRATCH / "tmp"),
        },
        check=True, capture_output=True,
    )
    return result.stdout


def remote_sha(branch):
    endpoint = f"{API}/branches/{quote(branch, safe='')}"
    return json.loads(gh(endpoint))["commit"]["sha"]


def read_manifest():
    initial = json.loads((PACKAGE / "inputs.initial.json").read_text("utf-8"))
    late = PACKAGE / "inputs.late.jsonl"
    inputs = initial["pins"]
    if late.is_file():
        inputs += [json.loads(line) for line in late.read_text("utf-8").splitlines()]
    pins = {}
    for pin in inputs:
        experiment = pin["experiment"]
        if not EXPERIMENT.fullmatch(experiment) or not COMMIT.fullmatch(pin["sha"]):
            raise ValueError(f"Invalid pin {pin!r}")
        if experiment in pins or pin["branch"] != f"codex/exp-{experiment.lower()}":
            raise ValueError(f"Conflicting pin {pin!r}")
        pins[experiment] = pin
    return pins


def git_blob(content):
    return hashlib.sha1(f"blob {len(content)}\0".encode("ascii") + content).hexdigest()


def safe_segments(path):
    for segment in path.split("/"):
        if (
            segment in {"", ".", ".."} or segment.casefold() == ".git"
            or segment[-1] in " ." or segment.split(".")[0].upper() in RESERVED
            or any(character in '<>:"\\|?*' or ord(character) < 32 for character in segment)
        ):
            raise ValueError(f"Nonportable archive path {path!r}")
    return PurePosixPath(path).parts


def archived_files(data, revision, expected):
    """Return verified path-to-bytes mapping; reject links and untracked files."""
    with ZipFile(io.BytesIO(data)) as archive:
        roots = set()
        files = {}
        folded = set()
        for member in archive.infolist():
            root, _, path = member.filename.rstrip("/").partition("/")
            roots.add(root)
            if not re.fullmatch(r"(?i:Perceptive-Closure-PC-X)-(?:[0-9a-f]{7}|[0-9a-f]{40})", root):
                raise ValueError(f"Unexpected zip root {root!r}")
            if root.rsplit("-", 1)[1] not in {revision, revision[:7]}:
                raise ValueError(f"Unexpected zip revision {root!r}")
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError(f"Symlink member {member.filename!r}")
            if path:
                safe_segments(path)
            if member.is_dir():
                continue
            if path.casefold() in folded:
                raise ValueError(f"Repeated zip member {path!r}")
            if path not in expected:
                raise ValueError(f"Archive member absent from Git tree {path!r}")
            content = archive.read(member)
            blob = expected[path]
            if len(content) != blob["size"] or git_blob(content) != blob["sha"]:
                raise ValueError(f"Blob mismatch for {path!r}")
            folded.add(path.casefold())
            files[path] = content
        if len(roots) != 1 or set(files) != set(expected):
            raise ValueError(f"Incomplete archive, missing {sorted(set(expected) - set(files))}")
        return roots.pop(), files


def retrieve(pin):
    experiment, branch, revision = (pin[key] for key in ("experiment", "branch", "sha"))
    actual = remote_sha(branch)
    if actual != revision:
        raise ValueError(f"{experiment} remote tip {actual} differs from pinned {revision}")
    commit = json.loads(gh(f"{API}/git/commits/{revision}"))
    if commit["sha"] != revision:
        raise ValueError(f"{experiment} returned commit differs from pin")
    tree_sha = commit["tree"]["sha"]
    tree = json.loads(gh(f"{API}/git/trees/{tree_sha}?recursive=1"))
    if tree["sha"] != tree_sha or tree["truncated"]:
        raise ValueError(f"{experiment} Git tree mismatch or truncation")
    expected = {}
    for entry in tree["tree"]:
        if entry["mode"] == "040000":
            continue
        if entry["mode"] not in {"100644", "100755"} or entry["type"] != "blob":
            raise ValueError(f"Unexpected Git tree member {entry['path']!r}")
        expected[entry["path"]] = entry

    data = gh(f"{API}/zipball/{revision}")
    archive_name, files = archived_files(data, revision, expected)
    destination = SCRATCH / "inputs" / experiment / revision
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "source.zip").write_bytes(data)
    directory = destination / "source"
    for path, content in files.items():
        target = directory.joinpath(*safe_segments(path))
        if not target.resolve().is_relative_to(directory.resolve()):
            raise ValueError(f"Extraction path escaped root {path!r}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target.read_bytes() != content:
            raise ValueError(f"Prior replay changed {target.name}. Use fresh scratch.")
        target.write_bytes(content)

    scoped = f"EXPERIMENTS/EXP-{experiment}/"
    file_hashes = {
        path.removeprefix(scoped): sha256(content)
        for path, content in files.items() if path.startswith(scoped)
    }
    if "WorkPlan.md" not in file_hashes or "README.md" not in file_hashes:
        raise ValueError(f"Expected package pages missing for {experiment}")
    receipt = {
        "experiment": experiment,
        "branch": branch,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "commit": revision,
        "parents": [parent["sha"] for parent in commit["parents"]],
        "tree": tree_sha,
        "archive_root": archive_name,
        "archive_sha256": sha256(data),
        "tracked_blobs_verified": len(files),
        "package_file_sha256": dict(sorted(file_hashes.items())),
    }
    (destination / "receipt.json").write_text(
        json.dumps(receipt, indent=2) + "\n", encoding="utf-8",
    )
    print(f"{experiment} {revision} {len(files)} verified files; {sha256(data)}", flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiments", nargs="*", help="e.g. X01 X08; defaults to all pinned inputs")
    parser.add_argument("--jobs", default=4, type=int)
    options = parser.parse_args()
    (SCRATCH / "tmp").mkdir(parents=True, exist_ok=True)
    pins = read_manifest()
    chosen = [pins[experiment] for experiment in (options.experiments or sorted(pins))]
    with ThreadPoolExecutor(max_workers=options.jobs) as pool:
        futures = [pool.submit(retrieve, pin) for pin in chosen]
        failures = []
        for pin, future in zip(chosen, futures):
            try:
                future.result()
            except (ValueError, OSError, subprocess.CalledProcessError) as exc:
                failures.append(pin["experiment"])
                details = exc.stderr.decode("utf-8", errors="replace") if isinstance(
                    exc, subprocess.CalledProcessError
                ) else str(exc)
                print(f"{pin['experiment']} retrieval failed: {details.strip()}", flush=True)
    if failures:
        raise SystemExit(f"Unverified inputs: {', '.join(failures)}")


if __name__ == "__main__":
    main()
