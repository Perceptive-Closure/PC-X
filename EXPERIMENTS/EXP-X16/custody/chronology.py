"""Capture exact independent GitHub and pending-drand custody receipts."""

import argparse
from base64 import b64decode
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha1, sha256
import json
from pathlib import Path
import subprocess
import tempfile


REPO = "repos/Perceptive-Closure/PC-X"
EXPERIMENT = "EXPERIMENTS/EXP-X16"
BRANCH = "codex/exp-x16"


def ensure(condition, message):
    if not condition:
        raise ValueError(message)


def json_file(path):
    return json.loads(path.read_bytes())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def write(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n", encoding="utf-8", newline="\n")


def scheduled(draw):
    return datetime.fromisoformat(draw["scheduled_utc"])


def verify_pending(receipt, draw):
    ensure(receipt["schema"] == 1 and receipt["round"] == draw["round"], "pending round differs")
    prefix = "/" + draw["chain"]["hash"] + "/public/" + str(draw["round"])
    expected = {"https://api.drand.sh" + prefix, "https://drand.cloudflare.com" + prefix}
    ensure(len(receipt["receipts"]) == 2
           and {row["url"] for row in receipt["receipts"]} == expected, "missing exact-round relays")
    for row in receipt["receipts"]:
        status = (row["status"] == 425 and row.get("reason", "").startswith("Requested future beacon")
                  if row["url"].startswith("https://api.drand.sh/") else row["status"] == 404)
        ensure(status and parsedate_to_datetime(row["http_date"]) < scheduled(draw)
               and datetime.fromisoformat(row["observed_utc"]) < scheduled(draw),
               "round was not confirmed pending before the lock")


def gh_resource(resource):
    raw = subprocess.check_output([
        "gh", "api", "-i", "-H", "Cache-Control: no-cache", "-H", "Accept: application/vnd.github+json",
        f"{REPO}/{resource}",
    ])
    blocks = raw.split(b"\r\n\r\n", 1) if b"\r\n\r\n" in raw else raw.split(b"\n\n", 1)
    headers, data = blocks
    header_lines = headers.decode("latin-1").splitlines()
    ensure(header_lines[0].split()[1] == "200", "GitHub readback not successful")
    values = {}
    for line in header_lines[1:]:
        label, _, value = line.partition(":")
        values[label.lower()] = value.strip()
    ensure(values.get("date") and values.get("x-github-request-id"), "incomplete GitHub receipt")
    receipt = {"resource": resource, "status": 200, "http_date": values["date"],
               "request_id": values["x-github-request-id"],
               "observed_utc": datetime.now(timezone.utc).isoformat()}
    return json.loads(data), receipt


def commit(ref):
    return gh_resource("git/commits/" + ref)


def files_at(ref, wanted):
    obj, _ = commit(ref)
    tree, _ = gh_resource("git/trees/" + obj["tree"]["sha"] + "?recursive=1")
    ensure(not tree["truncated"], "truncated GitHub tree")
    rows = {row["path"]: row["sha"] for row in tree["tree"] if row["type"] == "blob"}
    result = {}
    for name in wanted:
        blob = rows[EXPERIMENT + "/" + name]
        item, _ = gh_resource("git/blobs/" + blob)
        content = b64decode(item["content"])
        ensure(sha1(f"blob {len(content)}\0".encode("ascii") + content).hexdigest() == blob,
               f"remote Git object bytes differ for {name}")
        result[name] = (blob, content)
    return result


def pending_read(root, deps, draw_path):
    with tempfile.TemporaryDirectory(prefix="pcx-x16-pending-") as tmp:
        target = Path(tmp, "pending.json")
        subprocess.run(["node", str(root / "custody/beacon.mjs"), "pending", str(deps),
                        str(draw_path), str(target)], check=True)
        return json_file(target)


def forecast_readback(root, deps, source, commitment, forecast, draw_path):
    draw = json_file(draw_path)
    ensure(draw["source_commit"] == source, "draw committed different source")
    ref, ref_witness = gh_resource("git/ref/heads/" + BRANCH)
    remote_tip = ref["object"]["sha"]
    if remote_tip != forecast:
        tip_obj, _ = commit(remote_tip)
        ensure([parent["sha"] for parent in tip_obj["parents"]] == [forecast],
               "forecast is not the current branch or direct parent")
        files_at(remote_tip, ["results/forecast-receipt.json"])
    f_commit, f_witness = commit(forecast)
    g_commit, _ = commit(commitment)
    ensure([parent["sha"] for parent in f_commit["parents"]] == [commitment]
           and [parent["sha"] for parent in g_commit["parents"]] == [source],
           "source, commitment and forecast commits not in required immediate order")
    wanted = ["custody/draw-plan.json", "custody/authority.json",
              "custody/draw-signature.json", "results/forecast.json"]
    remote = files_at(forecast, wanted)
    for name in wanted[:3]:
        ensure(remote[name][1] == (root / name).read_bytes(), "role and official bytes differ " + name)
    forecast_file = remote[wanted[-1]]
    content = json.loads(forecast_file[1])
    ensure(content["source_commit"] == source and content["draw_sha256"] == digest(draw_path),
           "forecast is not bound to the approved draw")
    for receipt in (ref_witness, f_witness):
        ensure(parsedate_to_datetime(receipt["http_date"]) < scheduled(draw)
               and datetime.fromisoformat(receipt["observed_utc"]) < scheduled(draw),
               "GitHub confirmation is too late")
    probe = pending_read(root, deps, draw_path)
    verify_pending(probe, draw)
    return {
        "schema": 1, "source_commit": source, "commitment_commit": commitment,
        "forecast_commit": forecast, "forecast_git_blob": forecast_file[0],
        "forecast_sha256": sha256(forecast_file[1]).hexdigest(),
        "draw_sha256": digest(draw_path), "authority_sha256": digest(root / "custody/authority.json"),
        "round": draw["round"], "scheduled_utc": draw["scheduled_utc"],
        "github_tip": remote_tip, "github_ref": ref_witness, "github_forecast": f_witness,
        "before_opening": probe,
    }


def verify_forecast_receipt(receipt, draw):
    ensure(receipt["round"] == draw["round"] and receipt["scheduled_utc"] == draw["scheduled_utc"],
           "forecast receipt round differs")
    for name in ("github_ref", "github_forecast"):
        item = receipt[name]
        ensure(item["status"] == 200 and bool(item["request_id"])
               and parsedate_to_datetime(item["http_date"]) < scheduled(draw)
               and datetime.fromisoformat(item["observed_utc"]) < scheduled(draw),
               "forecast readback not proven before the fixed round")
    verify_pending(receipt["before_opening"], draw)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root", type=lambda value: Path(value).resolve())
    cli.add_argument("deps", type=lambda value: Path(value).resolve())
    cli.add_argument("source")
    cli.add_argument("commitment")
    cli.add_argument("forecast")
    cli.add_argument("out", type=Path)
    args = cli.parse_args()
    receipt = forecast_readback(args.root, args.deps, args.source, args.commitment, args.forecast,
                                args.root / "custody/draw-plan.json")
    write(args.out, receipt)
    print(f"Verified forecast {receipt['forecast_commit']} before round {receipt['round']}.")


if __name__ == "__main__":
    main()
