"""Frozen configuration, deterministic serialization and evidence I/O."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
PROTECTED = (
    ".gitattributes", "Protocol.md", "WorkPlan.md", "configs/protocol.json", "run.py",
    "src/common.py", "src/game.py", "src/engine.py", "src/checker.py", "src/audit.py",
    "src/preflight.py", "src/custody.py", "tests/test_x14.py",
)
EVIDENCE = (
    "exact.json", "pre-audit.json", "audit-receipt.json", "forecast.json", "opening.json",
    "ledger.jsonl", "summary.json", "runtime-observed.json",
)


def canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("ascii")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_hashes(names):
    return {name: digest((ROOT / name).read_bytes()) for name in names}


def read(path):
    raw = Path(path).read_bytes()
    value = json.loads(raw)
    if canonical(value) != raw:
        raise ValueError(f"Noncanonical JSON at {path}")
    return value


def write(path, data):
    with Path(path).open("xb") as stream:
        stream.write(data)


def fields(value, required):
    if not isinstance(value, dict) or set(value) != set(required):
        raise ValueError(f"Unexpected record fields. Expected {sorted(required)}")


def require_hex(value, width, label):
    if not isinstance(value, str) or len(value) != width or any(
        digit not in "0123456789abcdef" for digit in value
    ):
        raise ValueError(f"Invalid {label}")


def utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("Expected a UTC timestamp with a Z suffix")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


CONFIG = json.loads((ROOT / "configs/protocol.json").read_text(encoding="utf-8"))
JOBS = tuple(CONFIG["jobs"])
SLIPS = tuple(CONFIG["slips"])
PROFILES = CONFIG["profiles"]
ORDER = tuple(CONFIG["action_order"])
COST = CONFIG["cost"]
HELD = CONFIG["heldout"]
