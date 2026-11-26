"""Canonical evidence encoding and the frozen protocol."""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "protocol.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_bytes())


def write_json(path, value):
    with Path(path).open("xb") as output:
        output.write(canonical(value) + b"\n")


def text_sha(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def runner_files():
    return ["configs/protocol.json", *(
        path.relative_to(ROOT).as_posix() for path in sorted((ROOT / "src").glob("*.py"))
    )]


def runner_sha():
    return digest({name: text_sha(ROOT / name) for name in runner_files()})


def require_hex(value, size, label):
    if not isinstance(value, str) or not re.fullmatch(f"[0-9a-f]{{{size}}}", value):
        raise ValueError(f"Invalid {label}")
    return value
