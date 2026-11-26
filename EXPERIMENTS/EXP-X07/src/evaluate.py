"""Pre-opening predictions and post-opening statistics."""

from .fixtures import audit, check_inventory
from .model import conclusion, local_proof
from .native import classify, initial_scope_matches, native_fields_decision
from .records import ROOT, cases, cert_ids, file_digest, read_json, require


INPUT_FILES = ("commitment.json", "audit.json", "diagnostics.json")
PREDICTORS = ("pcx", "coarse", "native_fields", "no_audit", "omit_issuer_binding", "omit_leaf_validity")


def load_pre_outcome(spec, directory):
    commitment, measured, diagnostics = (read_json(directory / path) for path in INPUT_FILES)
    public = directory / "public"
    check_inventory(spec, public, commitment)

    observed = audit(spec, public)
    observed["library"] = measured["library"]
    require(observed == measured, "Independent signature/date audit differs from recorded observation")
    require(set(diagnostics["cases"]) == set(cert_ids(spec)), "Unexpected diagnostic records")
    require(
        diagnostics["openssl"]["version"].startswith(spec["native"]["version"] + " "),
        "Unexpected diagnostic verifier version",
    )
    return commitment, observed, diagnostics


def forecast(spec, directory, observed, diagnostics):
    proof = local_proof(spec)
    proof_path = ROOT / "evidence" / "certificate.json"
    require(
        read_json(proof_path) == {"x03": spec["x03"], "agreement": True, **proof},
        "The frozen X03 cross-check differs from the independent finite proof",
    )
    require(proof["initial_witness"] is not None, "No target-distinct initial ambiguity")
    require(all(
        initial_scope_matches(spec, trace["initial"]) for trace in diagnostics["cases"].values()
    ), "Native initial rejection differs from frozen evidence")
    approved = diagnostics["approved_issuer_fields"]
    rows = {}
    for case in cases(spec):
        measurement = observed["cases"][case]["answers"]
        probes = {query: measurement[query] for query in proof["selected"]}
        trace = diagnostics["cases"][case]
        rows[case] = {
            "answers": probes,
            "pcx": conclusion(spec, probes),
            "coarse": "FAIL",
            "native_fields": native_fields_decision(spec, trace["initial"], trace["leaf_fields"], approved),
            "no_audit": conclusion(spec, {}),
            **{f"omit_{q}": conclusion(spec, {name: value for name, value in probes.items() if name != q})
               for q in spec["controls"]["remove_one"]},
        }
    require(
        {row["pcx"]["decision"] for row in rows.values()} == {"PASS", "FAIL"},
        "Initial witnesses must have signed-byte representatives of both target labels",
    )
    witnesses = {}
    for target in ("PASS", "FAIL"):
        witness_completion = next(
            profile for profile in proof["initial_witness"]
            if any(row["id"] == profile and row["target"] == target for row in spec["completions"])
        )
        witnesses[target] = next(
            case for case, row in rows.items() if row["pcx"]["compatible"] == [witness_completion]
        )
    return {
        "schema": 1,
        "input_sha256": {path: file_digest(directory / path) for path in INPUT_FILES},
        "x03_proof_sha256": file_digest(proof_path),
        "finite_proof": proof, "observed_ambiguity_witnesses": witnesses, "cases": rows,
    }


def sealed_prediction(spec, evidence, observed, diagnostics):
    expected = forecast(spec, evidence, observed, diagnostics)
    sealed = read_json(evidence / "prediction.json")
    require(sealed == expected, "Frozen prediction differs from pre-outcome reconstruction")
    return sealed


def tally(trials, predictor):
    counts = {"correct": 0, "wrong": 0, "abstain": 0, "false_pass": 0,
              "false_fail": 0, "correctly_reversed": 0, "correctly_retained": 0, "unusable_native": 0}
    for trial in trials.values():
        value, actual = trial["predictions"][predictor], trial["native"]
        if actual == "ABSTAIN":
            counts["unusable_native"] += 1
        elif value == "ABSTAIN":
            counts["abstain"] += 1
        elif value == actual:
            counts["correct"] += 1
            change = "correctly_retained" if value == trial["predictions"]["coarse"] else "correctly_reversed"
            counts[change] += 1
        else:
            counts["wrong"] += 1
            counts["false_pass" if value == "PASS" else "false_fail"] += 1
    return counts


def score(spec, forecast_record, outcomes):
    require(
        set(outcomes["cases"]) == {*cert_ids(spec), spec["controls"]["wrong_anchor"]["id"]},
        "Unexpected native outcome inventory",
    )
    trials = {}
    for case, row in forecast_record["cases"].items():
        predictions = {
            name: row[name]["decision"] if isinstance(row[name], dict) else row[name] for name in PREDICTORS
        }
        trials[case] = {
            "native": classify(outcomes["cases"][case]), "predictions": predictions
        }
    controls = {}
    for role in ("positive", "negative", "wrong_anchor"):
        spec_control = spec["controls"][role]
        actual = classify(outcomes["cases"][spec_control["id"]])
        controls[role] = {"expected": spec_control["expected"], "actual": actual}
    stats = {name: tally(trials, name) for name in PREDICTORS}
    n = len(trials)
    all_controls_agree = all(row["expected"] == row["actual"] for row in controls.values())
    success = (
        stats["pcx"]["correct"] == n and all_controls_agree
        and stats["pcx"]["correctly_reversed"] > 0 and stats["pcx"]["correctly_retained"] > 0
    )
    return {
        "schema": 1, "held_out": n, "trials": trials, "controls": controls, "metrics": stats,
        "pcx_minus_coarse_correct": stats["pcx"]["correct"] - stats["coarse"]["correct"],
        "pcx_minus_native_fields_correct": stats["pcx"]["correct"] - stats["native_fields"]["correct"],
        "verdict": "SUPPORTED_IN_FROZEN_FIXTURE" if success else "FAILED_NATIVE_GATE",
    }
