"""Shared file formats and frozen support, without task or score logic."""

import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


def load(path):
    return json.loads(Path(path).read_bytes())


DESIGN = load(ROOT / "configs/protocol.json")
AGENTS = tuple(DESIGN["agents"])
PORTS = tuple(DESIGN["ports"])
MODES = tuple(itertools.product(DESIGN["allocators"], DESIGN["views"]))
TIES = tuple(DESIGN["tie_orders"])
CONTEXTS = tuple(DESIGN["contexts"])


def tickets(context):
    return tuple(itertools.product(
        range(len(DESIGN["contexts"][context])), range(DESIGN["tempo_tickets"])
    ))


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            + "\n").encode("ascii")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def write(path, raw):
    with Path(path).open("xb") as target:
        target.write(raw)


def assert_canonical(path):
    raw = Path(path).read_bytes()
    value = json.loads(raw)
    if canonical(value) != raw:
        raise ValueError(f"Noncanonical record: {path}")
    return value


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def utc(text):
    if not isinstance(text, str) or not text.endswith("Z"):
        raise ValueError("Expected a UTC timestamp with a Z suffix")
    return datetime.fromisoformat(text[:-1] + "+00:00")


def require_hex(value, size, label):
    if not isinstance(value, str) or not re.fullmatch(rf"[0-9a-f]{{{size}}}", value):
        raise ValueError(f"Invalid {label}")


def protected_files():
    fixed = [".gitattributes", "WorkPlan.md", "Protocol.md", "README.md",
             "configs/protocol.json"]
    sources = [path.relative_to(ROOT).as_posix()
               for folder in ("src", "tests")
               for path in (ROOT / folder).glob("*.py")]
    return sorted(fixed + sources)


def file_hashes(files):
    return {name: digest((ROOT / name).read_bytes()) for name in sorted(files)}


def source_hashes():
    return file_hashes(protected_files())
