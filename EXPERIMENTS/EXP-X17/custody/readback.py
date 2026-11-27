"""Authenticated GitHub readback receipts for the X17 preregistration gate."""

import argparse
from base64 import b64decode
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha1, sha256
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import quote


REPOSITORY = "repos/Perceptive-Closure/PC-X"
PREFIX = "EXPERIMENTS/EXP-X17/"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def resource(path):
    raw = subprocess.check_output([
        "gh", "api", "-i", "-H", "Cache-Control: no-cache", "-H", "Accept: application/vnd.github+json",
        f"{REPOSITORY}/{path}",
    ])
    sep = b"\r\n\r\n" if b"\r\n\r\n" in raw else b"\n\n"
    headers, body = raw.split(sep, 1)
    lines = headers.decode("latin-1").splitlines()
    require(lines[0].split()[1] == "200", "GitHub readback must return HTTP 200")
    fields = {}
    for line in lines[1:]:
        name, _, value = line.partition(":")
        fields[name.lower()] = value.strip()
    require(fields.get("date") and fields.get("x-github-request-id"), "missing GitHub witness fields")
    witness = {
        "resource": path, "status": 200, "http_date": fields["date"],
        "request_id": fields["x-github-request-id"], "observed_utc": datetime.now(timezone.utc).isoformat(),
    }
    return json.loads(body), witness


def before_round(witness, schedule):
    return (
        witness["status"] == 200
        and parsedate_to_datetime(witness["http_date"]) < schedule
        and datetime.fromisoformat(witness["observed_utc"]) < schedule
    )


def verify_blob(identifier):
    require(re.fullmatch(r"[0-9a-f]{40}", identifier), "expected exact Git blob object")
    obj, witness = resource("git/blobs/" + identifier)
    require(obj.get("sha") == identifier and obj.get("encoding") == "base64", "GitHub blob metadata differs")
    content = b64decode(obj["content"])
    require(sha1(f"blob {len(content)}\0".encode("ascii") + content).hexdigest() == identifier,
            "GitHub blob bytes differ")
    return content, witness


def readback(spec, draw=None):
    outputs = []
    schedule = datetime.fromisoformat(draw["scheduled_utc"]) if draw is not None else None
    for item in spec["objects"]:
        commit = item["commit"]
        require(re.fullmatch(r"[0-9a-f]{40}", commit), "expected an exact commit ID")
        commit_row, observed_commit = resource("git/commits/" + commit)
        require(commit_row.get("sha") == commit, "GitHub did not return the requested commit")
        witnesses = {"commit": observed_commit}
        if branch := item.get("branch"):
            require(branch.startswith("codex/exp-x17") and ".." not in branch.split("/"),
                    "branch outside the X17 registration")
            branch_ref, witnesses["ref"] = resource("git/ref/heads/" + quote(branch, safe="/-"))
            require(branch_ref.get("object", {}).get("sha") == commit, "published branch does not point to exact commit")
        activity_record = None
        if item.get("require_activity"):
            require(branch, "the activity verification requires a registered branch")
            activity, witnesses["activity"] = resource("activity?ref=" + quote("refs/heads/" + branch, safe=""))
            activity_record = next((entry for entry in activity if entry.get("after") == commit), None)
            require(activity_record is not None, "missing server-side branch activity for exact commit")
            if schedule is not None:
                require(datetime.fromisoformat(activity_record["timestamp"]) < schedule,
                        "publication activity occurred too late")
        tree_sha = commit_row["tree"]["sha"]
        tree, witnesses["tree"] = resource("git/trees/" + tree_sha + "?recursive=1")
        require(tree.get("sha") == tree_sha and not tree.get("truncated"), "incomplete GitHub tree readback")
        blobs = {row["path"]: row["sha"] for row in tree["tree"] if row["type"] == "blob"}
        receipt_files = {}
        for name, wanted in item["files"].items():
            rel = PurePosixPath(name)
            require(not rel.is_absolute() and ".." not in rel.parts and "\\" not in name, "invalid experiment path")
            name = PREFIX + name
            data, witness = verify_blob(blobs[name])
            digest = sha256(data).hexdigest()
            require(wanted is None or digest == wanted, "frozen SHA-256 differs: " + name)
            receipt_files[name] = {"blob": blobs[name], "sha256": digest, "bytes": len(data), "github": witness}
        if schedule is not None:
            require(
                all(before_round(witness, schedule)
                    for witness in list(witnesses.values()) + [f["github"] for f in receipt_files.values()]),
                "exact GitHub witnesses arrived after the prospective window",
            )
        outputs.append({"name": item["name"], "commit": commit, "tree": tree_sha,
                        "parents": [p["sha"] for p in commit_row["parents"]],
                        "github": witnesses, "server_activity": activity_record, "files": receipt_files})
    return {"schema": 1, "repository": REPOSITORY, "round": draw["round"] if draw else None,
            "draw_schedule": draw["scheduled_utc"] if draw else None, "objects": outputs}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("specification", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--before-draw", type=Path)
    args = parser.parse_args()
    spec = json.loads(args.specification.read_bytes())
    draw = json.loads(args.before_draw.read_bytes()) if args.before_draw else None
    result = readback(spec, draw)
    if args.before_draw:
        result["draw_sha256"] = sha256(args.before_draw.read_bytes()).hexdigest()
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(f"Authenticated {len(result['objects'])} exact GitHub commits.")


if __name__ == "__main__":
    main()
