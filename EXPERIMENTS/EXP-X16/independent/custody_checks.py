"""Check frozen Git bytes, signed custody, chronology and selected case inputs."""

from base64 import b64decode, b64encode
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from hashlib import sha1
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from evidence import EvidenceError, digest, equal, select_keys
from reference import enumerate_paths


EXPERIMENT = "EXPERIMENTS/EXP-X16"
OFFICIAL_BRANCH = "codex/exp-x16"
CUSTODY_BRANCH = "codex/exp-x16-custody"
SOURCE_PLAN = "b970928bae6dae1fa6c51d7d695de3b34a0bdfae"
SERVICE_FILES = ("Path.md", "document.mjs", "native.mjs", "source.mjs", "training.mjs")
CHAIN = {
    "public_key": "83cf0f2896adee7eb8b5f01fcad3912212c437e0073e911fb90022d3e760183c8c4b"
    "450b6a0a6c3ac6a5776a2d1064510d1fec758c921cc22b0e17e63aaf4bcb5ed66304de9cf809bd274"
    "ca73bab4af5a6e9c76a4bc09e76eae8991ef5ece45a",
    "period": 3,
    "genesis_time": 1692803367,
    "hash": "52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971",
    "groupHash": "f477d5c89f21a17c863a7f937c6a6d15859414d2be09cd448d4279af331c5d3e",
    "schemeID": "bls-unchained-g1-rfc9380",
    "metadata": {"beaconID": "quicknet"},
}
RELAYS = ("https://api.drand.sh", "https://drand.cloudflare.com")


def require(condition, context):
    if not condition:
        raise EvidenceError(context)


def exact_sha(value, digits, context):
    require(isinstance(value, str) and re.fullmatch(f"[0-9a-f]{{{digits}}}", value), context)
    return value


def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], timeout=60)


def blob(repo, commit, relative):
    exact_sha(commit, 40, "expected exact Git commit ID")
    local = PurePosixPath(relative)
    require(not local.is_absolute() and ".." not in local.parts and local.as_posix() == relative,
            f"unsafe experiment file name {relative}")
    return git(repo, "cat-file", "blob", f"{commit}:{EXPERIMENT}/{relative}")


def parents(repo, ref):
    result = git(repo, "rev-list", "--parents", "-n", "1", ref).decode("ascii").split()
    equal(result[0], ref, "exact commit parent query")
    return result[1:]


def export_native(repo, source, target):
    target.mkdir()
    for name in SERVICE_FILES:
        (target / name).write_bytes(blob(repo, source, f"service/{name}"))
    return target / "native.mjs"


def authority_payload(seal):
    names = ("catalogue_sha256", "source_commit", "frozen_manifest_sha256")
    return ("\n".join(("PCX-X16-authority-v1", *(seal[name] for name in names))) + "\n").encode("ascii")


def signature(text):
    raw = b64decode(text, validate=True)
    require(len(raw) == 64 and text == b64encode(raw).decode("ascii"), "noncanonical Ed25519 signature")
    return raw


def check_signatures(seal, signed_draw, draw_bytes):
    key = serialization.load_pem_public_key(seal["public_key_pem"].encode("ascii"))
    require(isinstance(key, Ed25519PublicKey), "authority public key type")
    equal(signed_draw["schema"], 1, "draw signature schema")
    equal(signed_draw["draw_sha256"], digest(draw_bytes), "draw signature bytes")
    key.verify(signature(seal["signature"]), authority_payload(seal))
    key.verify(signature(signed_draw["signature"]), draw_bytes)
    public_bytes = key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    return digest(public_bytes)


def utc(value):
    instant = datetime.fromisoformat(value)
    require(instant.utcoffset() == timezone.utc.utcoffset(None), "timestamp must be UTC")
    return instant


def round_time(number):
    require(type(number) is int and number >= 1, "invalid drand round")
    epoch = CHAIN["genesis_time"] + (number - 1) * CHAIN["period"]
    return datetime.fromtimestamp(epoch, timezone.utc)


def relay_witnesses(receipts, suffix, status, limit, before):
    expected = {f"{relay}/{CHAIN['hash']}{suffix}" for relay in RELAYS}
    equal(len(receipts), 2, f"{suffix} two recorded relay receipts")
    equal(sorted(row["url"] for row in receipts), sorted(expected), f"{suffix} pinned relay URLs")
    observed = []
    for receipt in receipts:
        if status == "pending":
            expected_status = 425 if receipt["url"].startswith(RELAYS[0]) else 404
            if expected_status == 425:
                require(re.match(r"Requested future beacon\b", receipt.get("reason", "")),
                        "api.drand.sh 425 did not announce a future beacon")
        else:
            expected_status = status
        equal(receipt["status"], expected_status, f"{receipt['url']} HTTP status")
        local = utc(receipt["observed_utc"])
        remote = parsedate_to_datetime(receipt["http_date"])
        require(remote.utcoffset() == timezone.utc.utcoffset(None), "relay HTTP date must be UTC")
        if before:
            require(local < limit and remote < limit, f"{receipt['url']} was seen after scheduled lock")
        else:
            require(local >= limit and remote >= limit, f"{receipt['url']} identifies a pre-round beacon")
        observed.append(local)
    return observed


def randomness(beacon, round_number):
    equal(beacon["round"], round_number, "BLS beacon round")
    raw = exact_sha(beacon["signature"], 96, "quicknet G1 signature encoding")
    expected = digest(bytes.fromhex(raw))
    equal(beacon["randomness"], expected, "quicknet randomness from signature digest")
    return expected


def check_round(draw, beacon):
    equal(draw["chain"], CHAIN, "pinned drand quicknet network")
    equal(draw["selector"], "PCX-X16-draw-v1", "registered selector domain")
    number = draw["round"]
    scheduled = round_time(number)
    equal(utc(draw["scheduled_utc"]).isoformat(), scheduled.isoformat(), "scheduled UTC for exact round")
    registered = utc(draw["registered_utc"])
    require(registered < scheduled, "draw plan was not registered before its scheduled round")
    samples = draw["reference_beacons"]
    sample_rounds = [row["beacon"]["round"] for row in samples]
    equal(number, max(sample_rounds) + 120, "registered round offset")
    relay_witnesses([row["http"] for row in samples], "/public/latest", 200, scheduled, before=True)
    for item in samples:
        prior = item["beacon"]["round"]
        randomness(item["beacon"], prior)
        require(round_time(prior) <= utc(item["http"]["observed_utc"]) <= registered,
                "latest network round was outside pre-commitment read time")
    suffix = f"/public/{number}"
    pending = relay_witnesses(draw["still_unavailable_at_commitment"], suffix, "pending", scheduled, before=True)
    require(min(pending) >= registered, "commitment pending receipts predate the draw")
    equal(beacon["schema"], 1, "verified beacon envelope schema")
    value = randomness(beacon["beacon"], number)
    published = relay_witnesses(beacon["fetched"], suffix, 200, scheduled, before=False)
    require(utc(beacon["verified_utc"]) >= max(published), "BLS verification predates the relay fetch")
    return value


def check_receipt(repo, receipt, opening, draw):
    equal(receipt["schema"], 1, "GitHub readback schema")
    bindings = (
        "source_commit", "commitment_commit", "forecast_commit", "forecast_git_blob",
        "forecast_sha256", "draw_sha256", "authority_sha256", "round",
    )
    equal(select_keys(receipt, bindings), select_keys(opening, bindings), "GitHub readback byte pins")
    equal(receipt["scheduled_utc"], draw["scheduled_utc"], "readback round time")
    forecast = opening["forecast_commit"]
    tip = exact_sha(receipt["github_tip"], 40, "GitHub readback tip")
    if tip != forecast:
        equal(parents(repo, tip), [forecast], "readback tip directly follows forecast")
        blob(repo, tip, "results/forecast-receipt.json")
    scheduled = round_time(opening["round"])
    last_read = utc(draw["registered_utc"])
    for key, resource in {
        "github_ref": f"git/ref/heads/{OFFICIAL_BRANCH}",
        "github_forecast": f"git/commits/{forecast}",
    }.items():
        item = receipt[key]
        equal([item["status"], item["resource"]], [200, resource], f"{key} GitHub endpoint and status")
        require(bool(item["request_id"]), f"{key} GitHub response ID absent")
        stamp = utc(item["observed_utc"])
        server = parsedate_to_datetime(item["http_date"])
        require(stamp < scheduled and server < scheduled, f"{key} GitHub forecast readback was late")
        last_read = max(last_read, stamp)
    before = receipt["before_opening"]
    equal([before["schema"], before["round"]], [1, opening["round"]], "readback pending round")
    pending = relay_witnesses(
        before["receipts"], f"/public/{opening['round']}", "pending", scheduled, before=True,
    )
    require(min(pending) >= last_read, "pending read predated GitHub forecast readback")
    return max(pending)


def reproduce_selection(catalogue, entropy):
    def hash_fields(label, profile_id, path):
        fields = json.dumps([profile_id, path.verdict, path.ids], separators=(",", ":"), ensure_ascii=True)
        return digest(f"PCX-X16-draw-v1\n{entropy}\n{label}\n{fields}\n".encode("ascii"))

    selected = []
    for profile in sorted(catalogue["profiles"], key=lambda row: row["id"]):
        profile_id = profile["id"]
        paths = enumerate_paths(profile)
        for target in ("YES", "NO"):
            ranked = sorted(
                (hash_fields("rank", profile_id, path), path.ids, path)
                for path in paths if path.verdict == target
            )
            for ordinal, (_, _, path) in enumerate(ranked[:2], start=1):
                key = hash_fields("document", profile_id, path)
                categories = ("Registry Forms", "Dispatch Notice", "Local Correspondence")
                selected.append({
                    "id": f"{profile_id}-{target.lower()}-{ordinal}",
                    "profile": profile_id,
                    "path": list(path.ids),
                    "nominal_stratum": target,
                    "document": {
                        "id": "intake-" + key[:18],
                        "title": "  Synthetic   intake  " + key[18:26] + "  ",
                        "category": categories[int(key[26:28], 16) % len(categories)],
                        "body": "Review case " + key[28:38]
                        + ".\r\nArchive the approved packet.\r\nRoute the synthetic registry.",
                    },
                })
    return selected


def opened_inputs(repo, opening_commit, output, drand_deps):
    raw_opening = blob(repo, opening_commit, "custody/opening.json")
    opening = json.loads(raw_opening)
    equal(opening["schema"], 1, "opening schema")
    ordered = ["source_commit", "commitment_commit", "forecast_commit", "prerelease_commit"]
    source, commitment, forecast, prerelease = [
        exact_sha(opening[key], 40, key) for key in ordered
    ]
    require(source != "0" * 40, "opening cannot use a public training seal")
    equal(parents(repo, commitment), [source], "authority commit directly follows source freeze")
    equal(parents(repo, forecast), [commitment], "forecast commit directly follows draw")
    prerelease_parents = parents(repo, prerelease)
    require(len(prerelease_parents) == 1, "prerelease must be a non-merge commit")
    registration = prerelease_parents[0]
    equal(parents(repo, registration), [forecast], "parent receipt directly follows forecast")
    equal(parents(repo, opening_commit), [prerelease], "opening directly follows prerelease")

    archive = output / "archive"
    archive.mkdir()
    (archive / "opening.json").write_bytes(raw_opening)
    artifacts = {
        "manifest": "custody/frozen-manifest.json", "catalogue": "cases/catalogue.json",
        "draw": "custody/draw-plan.json", "authority": "custody/authority.json",
        "draw_signature": "custody/draw-signature.json", "beacon": "custody/beacon.json",
        "heldout": "custody/heldout.json", "forecast": "results/forecast.json",
        "forecast_receipt": "results/forecast-receipt.json",
        "prerelease_receipt": "custody/prerelease-receipt.json",
    }
    paths = {}
    raw = {}
    for name, relative in artifacts.items():
        raw[name] = blob(repo, opening_commit, relative)
        paths[name] = archive / PurePosixPath(relative).name
        paths[name].write_bytes(raw[name])
        pin = f"{name}_sha256"
        if name in {"draw", "authority", "forecast", "heldout", "beacon"}:
            equal(digest(raw[name]), opening[pin], f"opening {name} SHA-256")
    for name in ("draw", "authority", "draw_signature"):
        for ref in (commitment, forecast):
            equal(digest(blob(repo, ref, artifacts[name])), digest(raw[name]), f"{name} persisted at {ref}")
    equal(digest(blob(repo, forecast, artifacts["forecast"])), digest(raw["forecast"]), "forecast is unchanged")
    for ref in (registration, prerelease):
        equal(digest(blob(repo, ref, artifacts["forecast_receipt"])), digest(raw["forecast_receipt"]),
              f"parent forecast readback persisted at {ref}")
    equal(
        digest(blob(repo, prerelease, artifacts["prerelease_receipt"])),
        digest(raw["prerelease_receipt"]), "prerelease receipt is unchanged",
    )
    for name in ("heldout", "beacon"):
        process = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", f"{prerelease}:{EXPERIMENT}/{artifacts[name]}"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False,
        )
        require(process.returncode != 0, f"{name} was already in the prerelease commit")
    forecast_blob = sha1(f"blob {len(raw['forecast'])}\0".encode("ascii") + raw["forecast"]).hexdigest()
    equal(opening["forecast_git_blob"], forecast_blob, "forecast exact Git blob ID")

    data = {name: json.loads(contents) for name, contents in raw.items()}
    manifest = data["manifest"]
    equal(manifest["schema"], 1, "frozen source manifest schema")
    files = manifest["files"]
    needed = {
        "cases/catalogue.json", "custody/selector.py", "custody/beacon.mjs",
        "custody/package.json", "custody/package-lock.json",
    }
    needed |= {f"service/{name}" for name in SERVICE_FILES}
    needed |= {f"independent/{name}" for name in ("reference.py", "evidence.py", "custody_checks.py", "reproduce.py")}
    require(needed <= files.keys(), f"frozen manifest omits {sorted(needed - files.keys())}")
    equal(digest(blob(repo, source, artifacts["manifest"])), digest(raw["manifest"]), "frozen manifest is unchanged")
    for relative, sha in files.items():
        for ref in (source, opening_commit):
            equal(digest(blob(repo, ref, relative)), sha, f"frozen bytes {relative} at {ref}")
    independent_dir = Path(__file__).resolve().parent
    for relative in needed:
        if relative.startswith("independent/"):
            active = independent_dir / PurePosixPath(relative).name
            # Git's CRLF checkout conversion does not change Python source semantics.
            equal(digest(active.read_bytes().replace(b"\r\n", b"\n")), files[relative],
                  f"running independent checker {active.name} matches frozen source")

    draw, seal, beacon, forecast_data = (data[name] for name in ("draw", "authority", "beacon", "forecast"))
    binding = dict(
        schema=1, source_commit=source, catalogue_sha256=digest(raw["catalogue"]),
        frozen_manifest_sha256=digest(raw["manifest"]),
    )
    for name, item in (("authority", seal), ("draw", draw)):
        equal(select_keys(item, binding), binding, f"{name} exact source and manifest")
    equal(forecast_data["source_commit"], source, "forecast source commit")
    equal(forecast_data["draw_sha256"], digest(raw["draw"]), "forecast exact registered round")
    equal(draw["round"], opening["round"], "opening round binding")
    key_fingerprint = check_signatures(seal, data["draw_signature"], raw["draw"])
    entropy = check_round(draw, beacon)
    equal(data["forecast_receipt"]["github_tip"], forecast, "forecast at parent registration")
    equal(data["prerelease_receipt"]["github_tip"], registration, "parent registration at custody review")
    check_receipt(repo, data["forecast_receipt"], opening, draw)
    latest_prerelease = check_receipt(repo, data["prerelease_receipt"], opening, draw)
    witness = opening["prerelease_github_ref"]
    equal([witness["status"], witness["resource"]], [200, f"git/ref/heads/{CUSTODY_BRANCH}"],
          "prerelease custody branch GitHub receipt")
    request_ids = {
        data["forecast_receipt"]["github_ref"]["request_id"],
        data["prerelease_receipt"]["github_ref"]["request_id"],
        witness["request_id"],
    }
    require(all(request_ids) and len(request_ids) == 3, "expected three distinct GitHub ref receipts")
    lock = round_time(opening["round"])
    require(latest_prerelease <= utc(witness["observed_utc"]) < lock
            and parsedate_to_datetime(witness["http_date"]) < lock,
            "custody branch receipt was not captured after its checks and before the lock")
    verifier = archive / "beacon.mjs"
    verifier.write_bytes(blob(repo, source, "custody/beacon.mjs"))
    for name in ("package.json", "package-lock.json"):
        frozen = blob(repo, source, f"custody/{name}")
        (archive / name).write_bytes(frozen)
        equal(json.loads((drand_deps / name).read_bytes()), json.loads(frozen),
              f"BLS verifier dependency input {name}")
    lock = json.loads((archive / "package-lock.json").read_bytes())["packages"]
    for directory, dependency in lock.items():
        if directory:
            actual_version = json.loads((drand_deps / directory / "package.json").read_bytes())["version"]
            equal(actual_version, dependency["version"], f"installed BLS dependency {directory}")
    verified = subprocess.run(
        ["node", str(verifier), "verify", str(drand_deps.resolve()), str(paths["draw"]), str(paths["beacon"])],
        capture_output=True, timeout=100, check=True,
    )
    (archive / "bls-replay.txt").write_bytes(verified.stdout + verified.stderr)
    reproduced = reproduce_selection(data["catalogue"], entropy)
    equal(data["heldout"], reproduced, "independently reproduced strata, paths and document content")
    canonical = json.dumps(reproduced, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
    equal(digest(canonical.encode("utf-8")), digest(raw["heldout"]), "held-out registry byte encoding")
    return paths, data, {
        "opening_commit": opening_commit, "source_commit": source, "forecast_commit": forecast,
        "commitment_commit": commitment, "forecast_receipt_commit": registration,
        "prerelease_commit": prerelease, "round": opening["round"],
        "scheduled_utc": draw["scheduled_utc"], "frozen_files": len(files),
        "authority_public_key_spki_sha256": key_fingerprint,
        "manifest_sha256": digest(raw["manifest"]), "heldout_sha256": digest(raw["heldout"]),
        "forecast_sha256": digest(raw["forecast"]), "bls_replay": verified.stdout.decode("utf-8").strip(),
        "independently_reconstructed_installations": len(reproduced),
    }
