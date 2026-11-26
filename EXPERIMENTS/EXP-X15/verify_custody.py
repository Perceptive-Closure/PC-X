"""Verify prospective commitment openings and GitHub source/forecast ancestry."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from base64 import b64decode
import json
import re
import subprocess

from fetch_inputs import API, SCRATCH, gh, git_blob, read_manifest, sha256
from replay import source_root, OPENSSL_ASSET, OPENSSL_HASH, OPA_HASH
from verify_exact import ensure, read


def canonical(value, form):
    parameters = {"sort_keys": True, "ensure_ascii": True, "allow_nan": False}
    if form == "indented":
        return (json.dumps(value, indent=2, **parameters) + "\n").encode("ascii")
    text = json.dumps(value, separators=(",", ":"), **parameters)
    return (text + ("\n" if form == "line" else "")).encode("ascii")


def paths(experiment):
    if experiment == "X07":
        return "evidence/pre-outcome/commitment.json", "evidence/pre-outcome/prediction.json"
    return "results/audit-receipt.json", "results/forecast.json"


def stage_records(package, experiment):
    receipt_file, forecast_file = paths(experiment)
    receipt, forecast = read(package / receipt_file), read(package / forecast_file)
    if experiment == "X07":
        opening = read(package / "evidence/post-outcome/reveal.json")
        release = read(package / "evidence/post-outcome/receipt.json")
        return (
            receipt["protocol_commit"], release["forecast_commit"], release["forecast_verified_at"],
            release["native_started_at"], opening, receipt["reveal_sha256"], "compact",
        )
    results = package / "results"
    op = read(results / ("release.json" if experiment == "X06" else "opening.json"))
    if experiment == "X06":
        verification = op["authorization"]
        return (
            verification["freeze_commit"], verification["forecast_commit"], verification["verified_utc"],
            op["opened_utc"], op["assignment"], receipt["commitment"]["assignment_sha256"], "indented",
        )
    if experiment == "X08":
        return (
            receipt["pre_audit_commit"], op["forecast_commit"], op["forecast_remote_verified_at_utc"],
            op["measurements_finished_at_utc"], op["sealed_configuration"], receipt["commitment_sha256"], "compact",
        )
    if experiment == "X09":
        return (
            receipt["pre_audit_commit"], op["forecast_commit"], op["github_verified_utc"],
            op["opened_utc"], op["private_record"], receipt["assignment_commitment_sha256"], "compact",
        )
    if experiment == "X10":
        return (
            receipt["pre_audit_commit"], op["forecast_commit"], op["remote_tip_verified_at_utc"],
            op["released_at_utc"], op["assignment"], receipt["assignment_commitment_sha256"], "compact",
        )
    if experiment == "X11":
        return (
            forecast["source_commit"], op["verified_forecast_commit"], None, None,
            op["reveal"], receipt["assignment_commitment_sha256"], "compact",
        )
    if experiment == "X12":
        return (
            receipt["source_commit"], op["forecast_commit"], op["verified_at_utc"],
            op["opened_at_utc"], op["private"], receipt["private_commitment"], "indented",
        )
    verification = op["verification"]
    return (
        receipt["source_commit"], verification["forecast_commit"], verification["verified_at_utc"],
        verification["opened_at_utc"], op["sealed" if experiment == "X14" else "assignment"],
        receipt["commitment"], "line",
    )


def compare(start, end):
    evidence = json.loads(gh(f"{API}/compare/{start}...{end}?per_page=100"))
    ensure(evidence["base_commit"]["sha"] == start and evidence["merge_base_commit"]["sha"] == start
           and evidence["status"] == "ahead" and evidence["commits"][-1]["sha"] == end
           and len(evidence["files"]) < 300 and evidence["total_commits"] == len(evidence["commits"]),
           ("Incomplete or non-descendant stage comparison", start, end))
    return evidence


def verify_remote(pin):
    experiment = pin["experiment"]
    package_path = f"EXPERIMENTS/EXP-{experiment}/"
    package = source_root(pin) / package_path
    pre, forecast, verified, opened, reveal, commitment, form = stage_records(package, experiment)
    ensure(sha256(canonical(reveal, form)) == commitment, (experiment, "independent commitment hash"))
    before = compare(pre, forecast)
    after = compare(forecast, pin["sha"])
    ensure(before["ahead_by"] == 1 and before["commits"][0]["parents"][0]["sha"] == pre,
           (experiment, "forecast immediate descendant"))

    before_files = {row["filename"]: row for row in before["files"]}
    after_files = {row["filename"] for row in after["files"]}
    ensure(all(name.startswith(package_path) for name in [*before_files, *after_files]),
           (experiment, "stage path scope"))
    forecast_paths = paths(experiment)
    if experiment == "X07":
        approved = lambda name: name == "Path.md" or name.startswith("evidence/pre-outcome/")
    else:
        approved = lambda name: name in ("Path.md", *forecast_paths)
    ensure(all(approved(name.removeprefix(package_path)) for name in before_files),
           (experiment, "frozen executable/config changed before opening", sorted(before_files)))
    unchanged_after = set(before_files) - {package_path + "Path.md"}
    ensure(not unchanged_after.intersection(after_files), (experiment, "forecast/receipt became mutable"))
    allowed_after = ("results/",) if experiment != "X07" else ("evidence/post-outcome/", "evidence/manifest.sha256")
    ensure(all(name.removeprefix(package_path) in {"README.md", "Path.md"}
               or name.removeprefix(package_path).startswith(allowed_after) for name in after_files),
           (experiment, "frozen executable changed after opening", sorted(after_files)))
    for relative in forecast_paths:
        ensure(before_files[package_path + relative]["sha"] == git_blob((package / relative).read_bytes()),
               (experiment, relative, "published bytes at forecast"))
    for path, row in before_files.items():
        if path == package_path + "Path.md":
            continue
        ensure(row["sha"] == git_blob((package / path.removeprefix(package_path)).read_bytes()),
               (experiment, path, "pre-outcome bytes"))

    commit_time = before["commits"][0]["commit"]["committer"]["date"]
    declaration = "strict recorded order"
    if verified is None:
        declaration = "ledger attestation only; opening exposes no verification or opening timestamp"
    else:
        ensure(datetime.fromisoformat(commit_time) <= datetime.fromisoformat(verified)
               <= datetime.fromisoformat(opened), (experiment, "negative recorded order"))
        if datetime.fromisoformat(verified) == datetime.fromisoformat(opened):
            declaration = "same-second verification and completion; execution order relies on runner and custodian"
    return {
        "pre_audit_commit": pre, "forecast_commit": forecast, "terminal_commit": pin["sha"],
        "forecast_committer_utc": commit_time, "custodian_verification_utc": verified,
        "opening_or_completion_utc": opened, "time_evidence": declaration,
        "freeze_to_forecast_files": sorted(before_files), "forecast_to_terminal_files": sorted(after_files),
        "commitment_recomputed_sha256": commitment, "receipt_sha256": sha256((package / forecast_paths[0]).read_bytes()),
        "forecast_sha256": sha256((package / forecast_paths[1]).read_bytes()),
    }


def verify_amendment(pin):
    package = source_root(pin) / "EXPERIMENTS/EXP-X05"
    meta = read(package / "results/manifest.json")
    initial = meta["initial_protocol_revision"]
    executable = meta["pre_outcome_execution_revision"]
    middle = compare(initial, executable)
    final = compare(executable, pin["sha"])
    frozen = "EXPERIMENTS/EXP-X05/"
    modified = {row["filename"]: row for row in middle["files"]}
    published = {row["filename"]: row for row in final["files"]}
    ensure(not any(path.startswith(frozen + "results/") for path in modified), "X05 amendment leaked evidence")
    ensure(all(path in {frozen + "Path.md", frozen + "README.md"} or path.startswith(frozen + "results/")
               for path in published), "X05 frozen source changed after executable registration")
    protocol_sha = sha256((package / "protocol.json").read_bytes())
    ensure(modified[frozen + "protocol.json"]["sha"] == git_blob((package / "protocol.json").read_bytes())
           and protocol_sha == meta["protocol_sha256"], "X05 amended protocol bytes")
    return {
        "initial_protocol_commit": initial, "pre_outcome_execution_commit": executable,
        "terminal_commit": pin["sha"], "registered_protocol_sha256": protocol_sha,
        "pre_outcome_execution_committer_utc": middle["commits"][-1]["commit"]["committer"]["date"],
        "earliest_post_freeze_committer_utc": final["commits"][0]["commit"]["committer"]["date"],
        "post_freeze_files": sorted(published),
    }


def verify_opa(pin):
    package = source_root(pin) / "EXPERIMENTS/EXP-X06"
    vendor = read(package / "config/provenance.json")["opa"]
    api = "repos/open-policy-agent/opa"
    release = json.loads(gh(f"{api}/releases/tags/v{vendor['version']}"))
    asset = next(asset for asset in release["assets"] if asset["browser_download_url"] == vendor["asset"])
    version = json.loads(gh(f"{api}/commits/v{vendor['version']}"))
    ensure(version["sha"] == vendor["commit"] and asset["digest"] == "sha256:" + OPA_HASH,
           "OPA official asset version")
    document = vendor["document"]
    upstream = json.loads(gh(f"{api}/contents/{document['path']}?ref={vendor['commit']}"))
    doc = b64decode(upstream["content"])
    ensure(sha256(doc) == document["sha256"], "OPA official tutorial bytes")
    # The named fence belongs to the numbered tutorial section in the frozen provenance.
    block = re.search(rb'\x60\x60\x60rego title="example\.rego"\n(.*?)\x60\x60\x60', doc, re.DOTALL)
    ensure(block is not None and block[1] == (package / "vendor/example.rego").read_bytes(),
           "OPA exact upstream policy")
    upstream_license = json.loads(gh(f"{api}/license?ref={vendor['commit']}"))
    ensure(b64decode(upstream_license["content"]) == (package / "vendor/LICENSE").read_bytes(),
           "OPA exact upstream license")
    exe = SCRATCH / "runtime/opa_windows_amd64.exe"
    ensure(exe.stat().st_size == asset["size"] and sha256(exe.read_bytes()) == OPA_HASH,
           "OPA local executable digest")
    build = subprocess.check_output([str(exe), "version"], text=True)
    ensure(f"Version: {vendor['version']}" in build and f"Platform: {vendor['platform']}" in build,
           "OPA executable metadata")
    return {
        "official_source_commit": version["sha"], "official_asset_id": asset["id"], "exe_sha256": OPA_HASH,
        "asset_size": asset["size"], "executable_version": build.splitlines(),
        "official_document_sha256": sha256(doc),
        "vendored_sha256": {file: sha256((package / file).read_bytes()) for file in vendor["vendored"]},
    }


def verify_openssl():
    from cryptography import __version__

    ensure(sha256(OPENSSL_ASSET.read_bytes()) == OPENSSL_HASH, "OpenSSL local executable digest")
    version = subprocess.check_output([str(OPENSSL_ASSET), "version"], text=True).strip()
    ensure(version.startswith("OpenSSL 3.2.4") and __version__ == "43.0.3", "X07 frozen runtime versions")
    return {"exe_sha256": OPENSSL_HASH, "openssl": version, "cryptography": __version__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    options = parser.parse_args()
    pins = read_manifest()
    staged = ("X06", "X07", "X08", "X09", "X10", "X11", "X12", "X13", "X14")
    evidence = {"original_stages": {}}
    with ThreadPoolExecutor(max_workers=5) as pool:
        tasks = {id_: pool.submit(verify_remote, pins[id_]) for id_ in staged}
        amendment = pool.submit(verify_amendment, pins["X05"])
        opa = pool.submit(verify_opa, pins["X06"])
        openssl = pool.submit(verify_openssl)
        for experiment, result in tasks.items():
            evidence["original_stages"][experiment] = result.result()
            print(f"{experiment}: commitments and GitHub stage comparisons agree", flush=True)
        evidence["x05_pre_outcome_amendment"] = amendment.result()
        evidence["official_opa"] = opa.result()
        evidence["offline_openssl"] = openssl.result()
    destination = SCRATCH / options.output
    ensure(destination.resolve().is_relative_to(SCRATCH.resolve()), "Custody output must stay under audit scratch")
    destination.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", "utf-8")


if __name__ == "__main__":
    main()
