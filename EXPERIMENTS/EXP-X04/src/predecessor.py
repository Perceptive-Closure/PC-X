"""Load exactly the X03 source and published scopes pinned by the X04 protocol."""

import csv
from hashlib import sha256
from importlib import import_module
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys

from .audit import Case, Completion


def _git(root, *arguments):
    return subprocess.run(
        ["git", *arguments], cwd=root, check=True, stdout=subprocess.PIPE,
    ).stdout


def load_predecessor(root, protocol):
    commit = protocol["commit"]
    if _git(root, "rev-parse", f"{commit}^{{commit}}").decode().strip() != commit:
        raise ValueError("X03 pinned commit is unavailable")
    prefix = f"{commit}:EXPERIMENTS/EXP-X03"
    config_bytes = _git(root, "show", f"{prefix}/configs/protocol.json")
    scope_bytes = _git(root, "show", f"{prefix}/results/scopes.csv")
    if sha256(config_bytes).hexdigest() != protocol["protocol_sha256"]:
        raise ValueError("X03 protocol hash mismatch")
    if sha256(scope_bytes).hexdigest() != protocol["scopes_sha256"]:
        raise ValueError("X03 scope evidence hash mismatch")

    worktree = Path(_git(root, "rev-parse", "--show-toplevel").decode().strip())
    isolated = worktree / "scratch" / "exp-x04-x03"
    package = isolated / "pcx_x03_pinned"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    for filename in ("authorization.py", "certificates.py"):
        (package / filename).write_bytes(_git(root, "show", f"{prefix}/src/{filename}"))
    sys.path.insert(0, str(isolated))
    try:
        authorization = import_module("pcx_x03_pinned.authorization")
    finally:
        sys.path.remove(str(isolated))

    source_config = json.loads(config_bytes)
    source_cases = list(authorization.cases(source_config["authorization"]))
    if len(source_cases) != protocol["structured_cases"]:
        raise ValueError("X03 structured case count mismatch")
    cases = [
        Case(
            original.name, "predecessor_x03", original.query_names, original.costs,
            tuple(Completion(row.identity, row.answers, row.target) for row in original.completions),
        )
        for original in source_cases
    ]
    scopes = {
        (row["case"], row["completion"]): (
            row["status"], int(row["optimum"]) if row["optimum"] else None,
        )
        for row in csv.DictReader(StringIO(scope_bytes.decode("utf-8")))
        if row["stratum"] == "pc_authorization"
    }
    return cases, scopes
