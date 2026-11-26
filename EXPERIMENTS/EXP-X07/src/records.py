"""Canonical evidence records and scope validation."""

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_FILE = ROOT / "configs" / "protocol.json"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_digest(path):
    return digest(path.read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def read_json(path):
    return json.loads(path.read_bytes())


def write_json(path, value):
    with path.open("x", encoding="ascii", newline="\n") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=True)
        stream.write("\n")


def protocol():
    return read_json(PROTOCOL_FILE)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def parse_utc(value):
    parsed = datetime.fromisoformat(value)
    require(parsed.tzinfo == timezone.utc, f"UTC timestamp required: {value}")
    return parsed


def check_git_sha(value):
    require(re.fullmatch(r"[0-9a-f]{40}", value) is not None, "A full Git commit SHA is required")


def cases(spec):
    count = spec["sample"]["held_out_per_completion"] * len(spec["completions"])
    prefix = spec["sample"]["opaque_id_prefix"]
    return [f"{prefix}{i:02d}" for i in range(1, count + 1)]


def cert_ids(spec):
    controls = spec["controls"]
    return cases(spec) + [controls["positive"]["id"], controls["negative"]["id"]]
