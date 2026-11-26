"""Independent offline verification of the admitted public X.509 fixtures."""

from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
import re

from verify_exact import ensure, partition_costs, read


def interpretable_fields(artifact, prefix):
    value = artifact["stdout"]
    ensure(artifact["returncode"] == 0 and not artifact["stderr"], f"X07 {prefix} field command")
    first = next(line.split("=", 1)[1].strip() for line in value.splitlines() if line.startswith(f"{prefix}="))
    identifier = re.search(r"^\s*([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){19})\s*$", value, re.MULTILINE)
    ensure(identifier is not None, f"X07 {prefix} identifier")
    return first, identifier[1].replace(":", "").lower()


def validity_fields(artifact, when):
    dates = [datetime.fromisoformat(line.split("=", 1)[1]) for line in artifact["stdout"].splitlines()
             if line.startswith(("notBefore=", "notAfter="))]
    ensure(len(dates) == 2, "X07 validity diagnostics")
    return dates[0] <= when <= dates[1]


def verify_x07(package):
    # Only the already-published inert certificate bytes enter this verifier.
    from cryptography import x509
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.hashes import SHA256

    spec = read(package / "configs" / "protocol.json")
    protocol = spec["native"]
    when = datetime.fromisoformat(protocol["evaluation_utc"])
    top = package / "evidence"
    before, after = top / "pre-outcome", top / "post-outcome"
    proof = read(top / "certificate.json")
    audit, commitment, diagnostics, forecast = (read(before / file) for file in
        ("audit.json", "commitment.json", "diagnostics.json", "prediction.json"))
    reveals, raw, results = (read(after / file) for file in ("reveal.json", "native.json", "results.json"))
    for line in (top / "manifest.sha256").read_text("ascii").splitlines():
        digest, relative = line.split("  ", 1)
        ensure(sha256((package / relative).read_bytes()).hexdigest() == digest, ("X07 evidence digest", relative))
    reveal_bytes = json.dumps(reveals, sort_keys=True, separators=(",", ":")).encode("ascii")
    ensure(sha256(reveal_bytes).hexdigest() == commitment["reveal_sha256"],
           "X07 commitment opening")
    certs = {}
    for name, digest in commitment["public_sha256"].items():
        data = (before / "public" / name).read_bytes()
        ensure(data.count(b"-----BEGIN ") == 1 and data.startswith(b"-----BEGIN CERTIFICATE-----")
               and sha256(data).hexdigest() == digest, ("X07 public certificate inventory", name))
        certs[name] = x509.load_pem_x509_certificate(data)
    ensure(len(certs) == 14, "X07 public certificate count")
    for chain in ("approved", "other"):
        issuer, root = certs[f"{chain}-issuer.pem"], certs[f"{chain}-root.pem"]
        root.verify_directly_issued_by(root)
        issuer.verify_directly_issued_by(root)
        for certificate in (root, issuer):
            ensure(certificate.not_valid_before_utc <= when <= certificate.not_valid_after_utc
                   and certificate.extensions.get_extension_for_class(x509.BasicConstraints).value.ca,
                   (chain, "CA profile"))

    domains = spec["completions"]
    queries = sorted(spec["queries"])
    costs = [spec["queries"][query]["cost"] for query in queries]
    rows = [{"identity": row["id"], "answers": [row[query] for query in queries],
             "target": row["target"]} for row in domains]
    status, optimum, choices = partition_costs(rows, costs)
    ensure(status == "CERTIFIED" and optimum == proof["uniform"]["cost"] and (0, 1) in choices,
           "X07 uniform exact audit")
    local = {row["identity"]: partition_costs(rows, costs, realized=row["identity"])[1] for row in rows}
    ensure(all(local[identity] == detail["cost"] for identity, detail in proof["realized"].items()),
           "X07 local exact audits")
    projected_models = {
        "pcx": queries, "no_audit": [],
        "omit_issuer_binding": ["leaf_validity"], "omit_leaf_validity": ["issuer_binding"],
    }
    metrics = {name: Counter() for name in ("coarse", "native_fields", *projected_models)}
    controls = {}
    confirmed = {}
    reasons = Counter()
    issuer_name, issuer_key = interpretable_fields(diagnostics["approved_issuer_fields"], "subject")
    for case, observed in raw["cases"].items():
        rc = observed["returncode"]
        args = observed["args"]
        ensure(args[0] == "verify" and args[args.index("-purpose") + 1] == protocol["purpose"]
               and args[args.index("-attime") + 1] == str(protocol["evaluation_epoch"])
               and args[args.index("-verify_hostname") + 1] == protocol["hostname"],
               (case, "X07 frozen native scope"))
        if case == "control-wrong-anchor":
            ensure(rc == 2 and args[args.index("-trusted") + 1] == protocol["initial_anchor"],
                   "X07 wrong-anchor control")
            controls[case] = "FAIL"
            continue
        leaf = certs[f"{case}.pem"]
        ensure(leaf.fingerprint(SHA256()).hex() == audit["cases"][case]["der_sha256"],
               (case, "X07 leaf bytes"))
        ensure(protocol["hostname"] in leaf.extensions.get_extension_for_class(
            x509.SubjectAlternativeName,
        ).value.get_values_for_type(x509.DNSName), (case, "X07 public fixture hostname"))
        linked = []
        for chain in ("approved", "other"):
            try:
                leaf.verify_directly_issued_by(certs[f"{chain}-issuer.pem"])
            except (InvalidSignature, ValueError):
                continue
            linked.append(chain)
        ensure(len(linked) == 1, (case, "X07 fixture binding witness"))
        current = leaf.not_valid_before_utc <= when <= leaf.not_valid_after_utc
        approved = linked == ["approved"]
        answers = {"issuer_binding": approved, "leaf_validity": current}
        ensure(audit["cases"][case]["answers"] == answers
               and reveals["assignments"][case] == f"{linked[0]}-{'current' if current else 'expired'}",
               (case, "X07 independently signed semantics"))
        result = "PASS" if rc == 0 else "FAIL" if rc == 2 else "UNKNOWN"
        predicted = "PASS" if approved and current else "FAIL"
        ensure(result == predicted and args[args.index("-trusted") + 1] == protocol["approved_anchor"]
               and args[args.index("-untrusted") + 1] == protocol["approved_intermediate"],
               (case, "X07 provisioned verdict"))
        errors = re.findall(r"error (\d+) at (\d+) depth lookup", observed["stderr"])
        expected_error = None if approved and current else (10, 0) if approved else (20, 0)
        ensure([(int(code), int(depth)) for code, depth in errors] ==
               ([] if expected_error is None else [expected_error]), (case, "X07 native reason"))
        if case.startswith("control-"):
            controls[case] = result
            continue

        confirmed[case] = result
        reasons["PASS" if expected_error is None else str(expected_error[0])] += 1
        initial = diagnostics["cases"][case]["initial"]
        ensure(initial["returncode"] == protocol["initial_rejection"]["returncode"]
               and initial["reason_codes"] == protocol["initial_rejection"]["reason_codes"]
               and initial["depths"] == protocol["initial_rejection"]["depths"]
               and "-untrusted" not in initial["args"], (case, "X07 initial ambiguity"))
        leaf_fields = diagnostics["cases"][case]["leaf_fields"]
        parsed_issuer, parsed_aki = interpretable_fields(leaf_fields, "issuer")
        baseline = "PASS" if validity_fields(leaf_fields, when) and (
            parsed_issuer, parsed_aki,
        ) == (issuer_name, issuer_key) else "FAIL"
        observed_prediction = forecast["cases"][case]
        decisions = {"coarse": "FAIL", "native_fields": baseline}
        for method, allowed in projected_models.items():
            compatibles = [row for row in domains if all(row[q] == answers[q] for q in allowed)]
            options = {row["target"] for row in compatibles}
            decisions[method] = next(iter(options)) if len(options) == 1 else "ABSTAIN"
            ensure(decisions[method] == observed_prediction[method]["decision"], (case, method, "X07 audit projection"))
        for method in ("coarse", "native_fields"):
            ensure(decisions[method] == observed_prediction[method], (case, method, "X07 baseline"))
        for method, decision in decisions.items():
            metrics[method]["correct"] += decision == result
            metrics[method]["abstain"] += decision == "ABSTAIN"
            metrics[method]["wrong"] += decision != "ABSTAIN" and decision != result

    ensure(len(confirmed) == results["held_out"] and controls == {
        "control-valid": "PASS", "control-expired": "FAIL", "control-wrong-anchor": "FAIL",
    }, "X07 holdout and controls")
    for method, tally in metrics.items():
        ensure(all(count == results["metrics"][method][metric] for metric, count in tally.items()),
               (method, "X07 counts"))
    return {
        "public_certificates": len(certs), "held_out": len(confirmed), "native_reasons": dict(reasons),
        "native_outcomes": confirmed, "controls": controls, "uniform_audit_cost": optimum,
        "realized_costs": local, "metrics": {method: dict(row) for method, row in metrics.items()},
    }
