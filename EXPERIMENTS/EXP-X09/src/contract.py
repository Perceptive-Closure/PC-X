"""Frozen configuration and stable evidence encoding."""

from hashlib import sha256
import json
from pathlib import Path
from random import Random
from typing import NamedTuple


ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "configs/protocol.json").read_bytes())
TICKETS = SPEC["tickets"]
UNITS = tuple(SPEC["units"])
LEFT, RIGHT = range(2)


class Fixture(NamedTuple):
    mode: str
    key: str
    variant: int

    @property
    def name(self):
        return f"{self.key}/{self.variant}"


ROSTER = tuple(Fixture(*fields) for fields in SPEC["roster"])
ADMITTED = tuple(fixture for fixture in ROSTER if fixture.mode == "anchored")
RECIPES = dict(zip(SPEC["contexts"], SPEC["recipes"], strict=True))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def document(value):
    return canonical(value) + b"\n"


def digest(data):
    return sha256(data).hexdigest()


def file_digest(path):
    with path.open("rb") as handle:
        return sha256_file(handle)


def sha256_file(handle):
    checksum = sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        checksum.update(chunk)
    return checksum.hexdigest()


def save(path, value):
    with path.open("xb") as handle:
        handle.write(document(value))


def read(path):
    data = path.read_bytes()
    value = json.loads(data)
    if document(value) != data:
        raise ValueError(f"Expected canonical JSON in {path.name}")
    return value


def fingerprint():
    """The same executable/configuration bytes bind each archived stage."""
    paths = [ROOT / "Protocol.md", ROOT / "configs/protocol.json"]
    paths.extend(sorted((ROOT / "src").glob("*.py")))
    hashes = {path.relative_to(ROOT).as_posix(): file_digest(path) for path in paths}
    return digest(canonical(hashes))


def stream(seed, *labels):
    key = sha256(canonical(["EXP-X09/v1", seed, labels])).digest()
    return Random(int.from_bytes(key, "big"))
