"""Canonical stage records and the frozen protocol inputs."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
CONFIG = ROOT / "config"
POLICY = ROOT / "vendor" / "example.rego"
RESULTS = ROOT / "results"
PROTOCOL = json.loads((CONFIG / "protocol.json").read_bytes())
PROVENANCE = json.loads((CONFIG / "provenance.json").read_bytes())
FREEZES = PROTOCOL["freeze_order"]
STRATA = PROTOCOL["strata"]
BUDGET = PROTOCOL["primary_budget"]

EMPTY = ()
TICKETS = (("ticket:0",), ("ticket:1",))
REVIEWS = (("review:0",), ("review:1",))
BOTH = tuple(ticket + review for ticket, review in zip(TICKETS, REVIEWS, strict=True))
HISTORIES = (EMPTY, *TICKETS, *REVIEWS, *BOTH)

RUNNER = (
    ".gitattributes",
    "Protocol.md",
    "adapter.py",
    "common.py",
    "config/protocol.json",
    "config/provenance.json",
    "contract.py",
    "custody.py",
    "native.py",
    "tests/test_preflight.py",
    "verify.py",
    "vendor/LICENSE",
    "vendor/example.rego",
    "x06.py",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return sha256(data).hexdigest()


def file_digest(path):
    with Path(path).open("rb") as source:
        from hashlib import file_digest as hash_file

        return hash_file(source, "sha256").hexdigest()


def canonical(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")


def read(path):
    return json.loads(Path(path).read_bytes())


def write_once(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as target:
        target.write(canonical(value))


def runner_seal():
    return {name: file_digest(ROOT / name) for name in RUNNER}


def utc():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def git_revision(revision):
    require(isinstance(revision, str) and re.fullmatch(r"[0-9a-f]{40}", revision), "expected full Git revision")
    return revision


def case_id(stratum, member):
    return f"{stratum['id']}-{member + 1}"


def request(fields):
    user, method, subject = fields
    return {"user": user, "method": method, "path": ["finance", "salary", subject]}


def primary(signature):
    value = signature[FREEZES.index("R")]
    return type(value) is int and value <= BUDGET
