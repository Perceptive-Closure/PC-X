"""Independent assignment, admission-ledger read, and stage receipts."""

from datetime import datetime
from pathlib import Path
from secrets import randbits, token_hex

from common import (
    RESULTS, STRATA, case_id, canonical, digest, file_digest, git_revision, read, require,
    runner_seal, utc, write_once,
)


def preaudit_record():
    record = read(RESULTS / "preaudit.json")
    require(record["runner"] == runner_seal(), "preaudit runner bytes differ")
    return record


def seal(directory, freeze_commit):
    preaudit_record()
    adapters = {}
    for stratum in STRATA:
        bit = randbits(1)
        for member in (0, 1):
            admitted = bool(bit ^ member)
            adapters[case_id(stratum, member)] = {
                "receipt_marks": ["anonymous-ticket-admitted"] if admitted else [],
                "renderer": "merged" if admitted else "exact",
            }
    assignment = {
        "version": 1,
        "nonce": token_hex(32),
        "created_utc": utc(),
        "freeze_commit": git_revision(freeze_commit),
        "preaudit_sha256": file_digest(RESULTS / "preaudit.json"),
        "adapters": adapters,
    }
    write_once(directory / "assignment.json", assignment)
    commitment = {
        "assignment_sha256": digest(canonical(assignment)),
        "freeze_commit": assignment["freeze_commit"],
        "preaudit_sha256": assignment["preaudit_sha256"],
        "committed_utc": utc(),
    }
    write_once(directory / "commitment.json", commitment)
    return commitment


def check_assignment(assignment, commitment):
    require(digest(canonical(assignment)) == commitment["assignment_sha256"], "assignment seal differs")
    for key in ("freeze_commit", "preaudit_sha256"):
        require(assignment[key] == commitment[key], "commitment lineage changed")
    require(datetime.fromisoformat(assignment["created_utc"]) <= datetime.fromisoformat(
        commitment["committed_utc"]), "assignment created after its commitment")
    known = {case_id(s, member) for s in STRATA for member in (0, 1)}
    require(assignment["adapters"].keys() == known, "sealed case inventory differs")
    for stratum in STRATA:
        members = [assignment["adapters"][case_id(stratum, i)] for i in (0, 1)]
        for member in members:
            marks = member["receipt_marks"]
            require(marks in ([], ["anonymous-ticket-admitted"]), "malformed admission journal")
            require(member["renderer"] == ("merged" if marks else "exact"),
                    "enrollment violates paired adapter eligibility")
        require(sum(bool(member["receipt_marks"]) for member in members) == 1, "pair balance violated")


def measured_answers(assignment, selected):
    allowed = {f"{s['id']}.admission-count": case_id(s, 0) for s in STRATA}
    require(set(selected) == allowed.keys() and len(selected) == len(allowed),
            "unfrozen query or nonminimal audit request")
    # The ledger reader sees a count of anonymous marks and never receives an OPA query or input.
    return {query: str(len(assignment["adapters"][allowed[query]]["receipt_marks"])) for query in selected}


def audit(directory):
    preaudit = preaudit_record()
    assignment = read(directory / "assignment.json")
    commitment = read(directory / "commitment.json")
    check_assignment(assignment, commitment)
    require(commitment["preaudit_sha256"] == file_digest(RESULTS / "preaudit.json"),
            "audit came from a different preaudit record")
    receipt = {
        "commitment": commitment,
        "interface": "custodian anonymous receipt-mark count at received checkpoint",
        "selected": preaudit["selected"],
        "answers": measured_answers(assignment, preaudit["selected"]),
        "audited_utc": utc(),
    }
    write_once(directory / "audit-receipt.json", receipt)
    return receipt


def check_receipt(receipt, preaudit):
    commitment = receipt["commitment"]
    git_revision(commitment["freeze_commit"])
    require(commitment["preaudit_sha256"] == file_digest(RESULTS / "preaudit.json"),
            "audit does not refer to this preaudit record")
    require(receipt["selected"] == preaudit["selected"]
            and receipt["answers"].keys() == set(preaudit["selected"]), "wrong audit interface")
    require(all(value in {"0", "1"} for value in receipt["answers"].values()),
            "audit response outside approved values")
    require(datetime.fromisoformat(commitment["committed_utc"]) <= datetime.fromisoformat(
        receipt["audited_utc"]), "audit predates commitment")


def forecast(receipt_file, output):
    from contract import prediction

    preaudit = preaudit_record()
    receipt = read(receipt_file)
    check_receipt(receipt, preaudit)
    record = {
        "freeze_commit": receipt["commitment"]["freeze_commit"],
        "runner": preaudit["runner"],
        "audit_receipt_sha256": file_digest(receipt_file),
        "assignment_commitment": receipt["commitment"]["assignment_sha256"],
        "created_utc": utc(),
        "predictions": prediction(preaudit, receipt["answers"]),
    }
    write_once(output, record)
    return record


def check_forecast(receipt_file, forecast_file):
    from contract import prediction

    preaudit = preaudit_record()
    receipt = read(receipt_file)
    check_receipt(receipt, preaudit)
    record = read(forecast_file)
    require(record["freeze_commit"] == receipt["commitment"]["freeze_commit"]
            and record["assignment_commitment"] == receipt["commitment"]["assignment_sha256"],
            "forecast lineage differs")
    require(record["runner"] == preaudit["runner"], "forecast and runner were frozen separately")
    require(record["audit_receipt_sha256"] == file_digest(receipt_file), "forecast receipt hash differs")
    require(record["predictions"] == prediction(preaudit, receipt["answers"]), "forecast is incorrect")
    require(datetime.fromisoformat(receipt["audited_utc"]) <= datetime.fromisoformat(
        record["created_utc"]), "forecast predates audit")
    return receipt, record


def authorize(directory, frozen_root, forecast_revision):
    """Run only after the custodian has independently fetched both immutable GitHub archives."""
    from common import ROOT

    require(not (ROOT.parent.parent / ".git").exists(), "use a GitHub archive for the forecast")
    require(not (frozen_root.parent.parent / ".git").exists(), "use a GitHub archive for the preaudit")
    local_receipt = directory / "audit-receipt.json"
    committed_receipt = RESULTS / "audit-receipt.json"
    forecast_file = RESULTS / "forecast.json"
    require(local_receipt.read_bytes() == committed_receipt.read_bytes(), "remote receipt changed")
    receipt, record = check_forecast(committed_receipt, forecast_file)
    require((frozen_root / "results/preaudit.json").read_bytes() == (RESULTS / "preaudit.json").read_bytes(),
            "remote preaudit record changed")
    require(all(file_digest(frozen_root / path) == sha for path, sha in record["runner"].items()),
            "remote frozen runner changed")
    require(git_revision(forecast_revision) != record["freeze_commit"], "forecast needs its own revision")
    authorization = {
        "forecast_commit": forecast_revision,
        "freeze_commit": record["freeze_commit"],
        "assignment_commitment": receipt["commitment"]["assignment_sha256"],
        "forecast_sha256": file_digest(forecast_file),
        "audit_receipt_sha256": file_digest(committed_receipt),
        "runner_sha256": digest(canonical(record["runner"])),
        "verified_utc": utc(),
    }
    require(datetime.fromisoformat(record["created_utc"]) <= datetime.fromisoformat(
        authorization["verified_utc"]), "forecast verification predates forecast creation")
    write_once(directory / "authorization.json", authorization)
    return authorization


def validate_release(assignment, authorization):
    receipt_file = RESULTS / "audit-receipt.json"
    forecast_file = RESULTS / "forecast.json"
    receipt, record = check_forecast(receipt_file, forecast_file)
    commitment = receipt["commitment"]
    check_assignment(assignment, commitment)
    require(measured_answers(assignment, receipt["selected"]) == receipt["answers"],
            "revealed fixture disagrees with independently measured audit")
    require(authorization["assignment_commitment"] == commitment["assignment_sha256"]
            and authorization["freeze_commit"] == commitment["freeze_commit"]
            and authorization["forecast_sha256"] == file_digest(forecast_file)
            and authorization["audit_receipt_sha256"] == file_digest(receipt_file)
            and authorization["runner_sha256"] == digest(canonical(record["runner"])),
            "opening authorization does not bind forecast and receipt")
    require(git_revision(authorization["forecast_commit"]) != commitment["freeze_commit"],
            "authorization needs a forecast revision distinct from the preaudit")
    require(datetime.fromisoformat(record["created_utc"]) <= datetime.fromisoformat(
        authorization["verified_utc"]), "opening authorization predates forecast")
    return record["predictions"]
