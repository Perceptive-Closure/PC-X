"""Bounded local OpenSSL commands and native diagnostic baselines."""

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from .records import ROOT, cert_ids, file_digest, parse_utc, require


ERROR = re.compile(r"^error (\d+) at (\d+) depth lookup: (.+)$", re.MULTILINE)
KEY_ID = re.compile(r"^(?:[0-9A-Fa-f]{2}:){19}[0-9A-Fa-f]{2}$")


class OpenSSL:
    def __init__(self, spec, executable, work, temp):
        self.settings = spec["native"]
        self.executable = executable.resolve(strict=True)
        self.work = work.resolve(strict=True)
        scratch = temp.resolve(strict=True)
        self.env = {
            "LC_ALL": "C",
            "OPENSSL_CONF": str(ROOT / "configs" / "openssl.cnf"),
            "TMP": str(scratch),
            "TEMP": str(scratch),
        }
        if os.name == "nt":
            self.env["SystemRoot"] = os.environ["SystemRoot"]
        detail = self.run(["version"])
        version = detail["stdout"].strip()
        require(
            detail["returncode"] == 0 and version.startswith(self.settings["version"] + " "),
            f"Unexpected OpenSSL version: {version}",
        )
        self.identity = {
            "version": version, "sha256": file_digest(self.executable),
            "executable": str(self.executable),
        }

    def run(self, args):
        proc = subprocess.run(
            [self.executable, *args], cwd=self.work, env=self.env, capture_output=True, check=False,
            timeout=self.settings["timeout_seconds"],
        )
        return {
            "args": args, "returncode": proc.returncode,
            "stdout": proc.stdout.decode("ascii"), "stderr": proc.stderr.decode("ascii"),
        }

    def verify(self, case, *, anchor, intermediate=None):
        args = [
            "verify", "-verbose", "-show_chain", "-attime", str(self.settings["evaluation_epoch"]),
            "-purpose", self.settings["purpose"], "-verify_hostname", self.settings["hostname"],
            *self.settings["check_options"], "-trusted", anchor,
        ]
        if intermediate is not None:
            args += ["-untrusted", intermediate]
        record = self.run([*args, f"{case}.pem"])
        errors = ERROR.findall(record["stderr"].replace("\r\n", "\n"))
        record.update({
            "reason_codes": [int(code) for code, _, _ in errors],
            "depths": [int(depth) for _, depth, _ in errors],
            "reasons": [reason.rstrip() for _, _, reason in errors],
        })
        return record


def initial_scope_matches(spec, record):
    return all(record.get(key) == value for key, value in spec["native"]["initial_rejection"].items())


def stage_initial(spec, engine):
    native = spec["native"]
    issuer = engine.run([
        "x509", "-in", native["approved_intermediate"], "-noout",
        "-subject", "-nameopt", "RFC2253", "-ext", "subjectKeyIdentifier",
    ])
    entries = {}
    for case in cert_ids(spec):
        entries[case] = {
            "initial": engine.verify(case, anchor=native["initial_anchor"]),
            "leaf_fields": engine.run([
                "x509", "-in", f"{case}.pem", "-noout", "-issuer", "-nameopt", "RFC2253",
                "-dates", "-dateopt", "iso_8601", "-ext", "authorityKeyIdentifier",
            ]),
        }
    return {"openssl": engine.identity, "approved_issuer_fields": issuer, "cases": entries}


def printed_key_id(text):
    values = [line.strip() for line in text.splitlines() if KEY_ID.fullmatch(line.strip())]
    return values[0].replace(":", "").lower() if len(values) == 1 else None


def printed_fields(record):
    return dict(
        tuple(part.strip() for part in line.split("=", 1))
        for line in record["stdout"].splitlines()
        if line.startswith(("notBefore=", "notAfter=", "subject=", "issuer="))
    )


def native_fields_decision(spec, initial, leaf_record, approved_record):
    if not initial_scope_matches(spec, initial) or leaf_record["returncode"] or approved_record["returncode"]:
        return "ABSTAIN"
    leaf, approved = printed_fields(leaf_record), printed_fields(approved_record)
    aki = printed_key_id(leaf_record["stdout"])
    ski = printed_key_id(approved_record["stdout"])
    if not aki or not ski or not leaf.get("issuer") or not approved.get("subject"):
        return "ABSTAIN"
    try:
        start = datetime.fromisoformat(leaf["notBefore"])
        end = datetime.fromisoformat(leaf["notAfter"])
        at = parse_utc(spec["native"]["evaluation_utc"])
        time_valid = start <= at < end
    except (ValueError, KeyError, TypeError):
        return "ABSTAIN"
    return "PASS" if time_valid and leaf["issuer"] == approved["subject"] and aki == ski else "FAIL"


def classify(record):
    if record["returncode"] == 0 and not record["reason_codes"] and ": OK" in record["stdout"]:
        return "PASS"
    if record["returncode"] == 2 and record["reason_codes"]:
        return "FAIL"
    return "ABSTAIN"


def native_outcomes(spec, engine):
    native = spec["native"]
    records = {
        case: engine.verify(case, anchor=native["approved_anchor"], intermediate=native["approved_intermediate"])
        for case in cert_ids(spec)
    }
    wrong = spec["controls"]["wrong_anchor"]
    records[wrong["id"]] = engine.verify(
        wrong["leaf"], anchor=native["initial_anchor"], intermediate=native["approved_intermediate"]
    )
    return {"openssl": engine.identity, "cases": records}
