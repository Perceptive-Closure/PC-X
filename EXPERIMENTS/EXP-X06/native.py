"""Invoke the hash-pinned offline native OPA process and retain raw decisions."""

import json
import os
from pathlib import Path
import subprocess

from adapter import cases, prepared_actions, receive
from common import FREEZES, POLICY, PROTOCOL, PROVENANCE, ROOT, file_digest, request, require


class OPA:
    def __init__(self, binary, temp):
        self.binary = Path(binary).resolve()
        temp = Path(temp).resolve()
        temp.mkdir(parents=True, exist_ok=True)
        pin = PROVENANCE["opa"]
        require(file_digest(self.binary) == pin["sha256"], "official OPA binary digest differs")
        for name, expected in pin["vendored"].items():
            require(file_digest(ROOT / name) == expected, f"upstream source digest differs for {name}")
        self.env = {key: os.environ[key] for key in ("SystemRoot", "WINDIR", "SystemDrive") if key in os.environ}
        self.env.update(TEMP=str(temp), TMP=str(temp), GOMAXPROCS="2")
        self.version = self._run(("version",))
        fields = self.version["stdout"].splitlines()
        commit = f"Build Commit: {pin['commit']}-dirty"
        require(self.version["returncode"] == 0 and commit in fields and f"Version: {pin['version']}" in fields
                and f"Platform: {pin['platform']}" in fields, "native OPA version or platform differs")

    def _run(self, args, payload=None):
        try:
            result = subprocess.run(
                [str(self.binary), *args], input=payload, capture_output=True, timeout=12,
                cwd=ROOT / "vendor", env=self.env, check=False,
            )
        except subprocess.TimeoutExpired as error:
            return {
                "returncode": None,
                "stdout": (error.stdout or b"").decode("utf-8"),
                "stderr": (error.stderr or b"").decode("utf-8"),
                "disposition": "timeout",
            }
        return {
            "returncode": result.returncode,
            "stdout": result.stdout.decode("utf-8"),
            "stderr": result.stderr.decode("utf-8"),
            "disposition": "exit",
        }

    def evaluate(self, payload):
        raw = self._run(("eval", "--format=json", "--stdin-input", "--data", POLICY.name,
                         "data.httpapi.authz.allow"), payload)
        raw["stdin"] = payload.decode("utf-8")
        value = None
        if raw["returncode"] == 0:
            try:
                expressions = json.loads(raw["stdout"])["result"][0]["expressions"]
                if len(expressions) == 1 and type(expressions[0]["value"]) is bool:
                    value = expressions[0]["value"]
            except (IndexError, KeyError, ValueError, TypeError):
                pass
        raw["decision"] = value
        return raw

    def measure(self, fields):
        payload = json.dumps(request(fields), sort_keys=True, separators=(",", ":")).encode("ascii")
        return self.evaluate(payload)


def development(engine):
    controls = []
    for control in PROTOCOL["development_controls"]:
        controls.append({
            "id": control["id"],
            "expected": control["expected"],
            "native": engine.measure(control["request"]),
        })
    controls.append({"id": "invalid-json", "expected": "input-error", "native": engine.evaluate(b'{"user":')})
    return controls


def measure(engine, assignment):
    controls = development(engine)
    units = {}
    for name, stratum, provisioned in cases(assignment):
        start = [receive(provisioned, i) for i in (0, 1)]
        unrestricted = [engine.measure(fields) for fields in stratum["requests"]]
        actions = list(prepared_actions(stratum, start))
        by_freeze = {}
        for freeze in FREEZES:
            blocked_resources = set() if freeze == "none" else set(freeze)
            attempts = []
            for action, cost, staged, touch in actions:
                committed = not bool(touch & blocked_resources)
                measures = [engine.measure(fields) for fields in stratum["requests"]] if committed else []
                attempts.append({
                    "action": action, "cost": cost, "touch": sorted(touch), "staged": staged,
                    "committed": committed, "native": measures,
                })
            by_freeze[freeze] = attempts
        units[name] = {
            "received": [checkpoint.record() for checkpoint in start],
            "unrestricted": unrestricted,
            "freeze_conditions": by_freeze,
        }
    return {
        "engine": engine.version,
        "development": controls,
        "units": units,
    }
