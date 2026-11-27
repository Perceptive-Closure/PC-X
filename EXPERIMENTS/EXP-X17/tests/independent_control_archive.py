"""Replay the frozen off-roster X17 controls and retain their original artifacts."""

import argparse
from fractions import Fraction as F
from gzip import GzipFile
from hashlib import sha256
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


def execute(official, output):
    sys.path[:0] = [str(official), str(official / "independent"), str(official / "tests")]
    from independent_controls import BAD, DEV, OPPOSITE, authority, deny, inferential, physical, plant, records
    from evidence import Evidence, canonical, coherent_signature, decoded
    from native import NativeStore

    with TemporaryDirectory(prefix="x17-independent-control-evidence-") as scratch:
        database = Path(scratch) / "controls.sqlite"
        with NativeStore(database) as writer, Evidence(database) as reader:
            authority(writer, reader)
            records(writer, reader)
            physical(writer, reader)
            inferential(writer)

            catalog = {}
            for world in (DEV, OPPOSITE, BAD):
                service = plant(writer, None, world, guard=False)
                deny("good_guard_required", service.new_attempt, "without-source", 0)
                catalog[world.id] = {}
                for key in ("ordinary", "guard", "full"):
                    catalog[world.id][key] = service.check_source(key)
                    assert coherent_signature("source", catalog[world.id][key])
                    if key == "ordinary":
                        deny("good_guard_required", service.new_attempt, "ordinary-alone", 0)
            assert catalog[DEV.id] == catalog[OPPOSITE.id]
            assert catalog[DEV.id]["ordinary"] == catalog[BAD.id]["ordinary"]
            assert catalog[DEV.id]["guard"] != catalog[BAD.id]["guard"]
            assert {k: r["charge_eighths"] for k, r in catalog[DEV.id].items()} == {
                "ordinary": 1, "guard": 2, "full": 8,
            }

            repeated = plant(writer, "C04").new_attempt("C04-identical", 0)
            receipt = repeated.intake()["route_receipt"]
            repeated.probe("low:L", receipt)
            deny("repeated_probe", repeated.probe, "low:L", receipt)
            repeated.declare(False)
            writer.flush()
            repeated_row = reader.attempt("C04-identical")["trace"]
            assert repeated_row["paid_eighths"] == 3 and len(repeated_row["denials"]) == 1

            for world in (DEV, OPPOSITE):
                name = "C06-free-" + world.id
                attempt = plant(writer, "C06", world).new_attempt(name, 19)
                public = attempt.intake()
                receipt = public["route_receipt"]
                assert attempt.probe("skip:" + receipt["route"], receipt) is None
                attempt.declare(public["source_fact"] == "positive")
                writer.flush()
                score = decoded(reader, reader.attempt(name), world)
                assert score["wrong"] == 0 and score["cost"] == 0

            changed = reader.attempt("corrupted")
            clean = reader.attempt("original-" + str(changed["trace"]["seed"]))
            public = ("public_intake", "command", "response", "declaration", "paid_eighths", "events")
            assert all(changed["trace"][key] == clean["trace"][key] for key in public)
            assert all(changed[key] == clean[key] for key in ("source_digest", "intake_digest"))
            assert changed["final_digest"] != clean["final_digest"]
            assert decoded(reader, changed, DEV)["V"] == 1 and decoded(reader, clean, DEV)["V"] == 0

            attempts = {}
            for name, in reader.connection.execute("SELECT attempt_id FROM attempts ORDER BY attempt_id"):
                attempts[name] = reader.attempt(name)
            artifacts = {}
            for oid, body in reader.connection.execute("SELECT digest,body FROM artifacts ORDER BY digest"):
                assert sha256(body).hexdigest() == oid
                artifacts[oid] = json.loads(body)

    half = F(1, 2)
    ell = F(1, 8)
    assert min(F(1), half + ell) - max(F(0), half - ell) == F(1, 4)
    eta = F(1, 20)
    counts = {"issued": 1, "violating_issued": 1, "tickets": 20}
    assert F(counts["issued"], counts["tickets"]) == eta
    assert F(counts["violating_issued"], counts["issued"]) == 1
    a = F(3, 8)
    assert a * eta + (1 - a) * min(eta, eta) == eta

    registered = (
        ("C01", "native and exact", "bad guard refused", {"bad_true_positive_lower_risk": str(BAD.theta / 4 + BAD.beta)}),
        ("C02", "native", "ordinary receipt lacked B; guarded entry refused", {"ordinary_price": "1/8"}),
        ("C03", "native", "wrong route rejected, correct single low request charged", {"attempt": "C03"}),
        ("C04", "native", "identical repeated low literal rejected at unchanged first debit", {"attempt": "C04-identical", "eighths": 3}),
        ("C05", "native", "withheld receipt blocked paid access and positive finish while retaining work", {"attempt": "C05"}),
        ("C06", "native and exact", "authorized sign distinguishes the matched records; deterministic free skip has zero error",
         {"matched_theta": [str(DEV.theta), str(OPPOSITE.theta)], "free_price": "0"}),
        ("C07", "native", "independent complete-record comparison detected the target-bearing batch field",
         {"extra": "intake_batch_class"}),
        ("C08", "native and exact", "word precedes proposal; effective cut equals the proposal-one threshold",
         {"actual_anticipatory_cut": str(DEV.theta / 4 + DEV.beta + F(1, 16)),
          "base_proposal_zero_cut": str(DEV.theta / 4 + DEV.beta)}),
        ("C09", "native", "complete controller-facing record stays equal while the final inventory is corrupted",
         {"clean_final": clean["final_digest"], "changed_final": changed["final_digest"]}),
        ("C10", "native and exact", "wrong destination occurred in an omitted represented row with strictly positive mass",
         {"conditional_wrong_route_floor": str(DEV.theta / 4 + DEV.beta)}),
        ("C11", "native", "unsafe staging remains in V on a negative decision", {"attempt": "unsafe-intake", "V": 1, "VI": 0}),
        ("C12", "native and exact", "reset changed the carried proposal on an observed v=1 and shifts the cut by 1/16",
         {"absolute_threshold_change": "1/16"}),
        ("C13", "native", "recorded positive did not invoke mandatory finalizer", {"attempt": "cancelled", "I": 1, "final": None}),
        ("C14", "native and exact", "excess surcharge rejected under guarded authority; unchecked physical cut is higher",
         {"attempt": "shifted-unchecked", "exact_extra_surcharge": "1/8"}),
        ("C15", "native and exact", "omitting matched monitor tolerance invalidates a finalizer-only transport bound",
         {"two_read_difference": str(1 - F(31, 32)**2), "candidate_bound": "1/32"}),
        ("C16", "exact scope fixture", "checking only the largest surcharge misses the failure at beta=0",
         {"beta_max_cost": "7/12", "beta_zero_issuance": "247/372", "positive_issuance_floor": "2/3"}),
        ("C17", "native and exact changed menu", "authorized direct bit has price 1/2 and TV efficiency 2",
         {"direct_one_read": "1/2", "direct_and_fair_skip_optimum": "1/6", "base_direct": "unavailable"}),
        ("C18", "native and exact continuous scope fixture", "literal denial remains required on supported paths",
         {"uniform_singleton": "1/2", "singleton_probability": "0", "one_neighborhood_probability": "1/4"}),
        ("C19", "exact scope fixture", "selective issuance occurs only in the failing calibration ticket",
         counts | {"unconditional_bad_mass": "1/20", "conditional_risk": "1"}),
    )
    cases = [{"id": name, "scope": scope, "outcome": outcome, "evidence": evidence, "status": "verified"}
             for name, scope, outcome, evidence in registered]
    body = {"schema": 1, "role": "independent", "registered_replay": "tests/independent_controls.py",
            "main_seed_used": False, "complete_source_catalog_receipts": catalog, "cases": cases, "attempts": attempts, "artifacts": artifacts}
    destination = output / "independent-controls.json.gz"
    with destination.open("xb") as stream, GzipFile(mtime=0, fileobj=stream, mode="wb", filename="") as compressed:
        compressed.write(canonical(body) + b"\n")
    summary = {"schema": 1, "role": "independent", "controls_verified": len(cases),
               "control_native_attempts_archived": len(attempts), "control_native_artifacts_archived": len(artifacts),
               "control_archive_sha256": sha256(destination.read_bytes()).hexdigest(),
               "least_sufficient_guard_price": "1/4", "cases": cases}
    with (output / "independent-control-summary.json").open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print(f"Archived {len(cases)} independently verified controls, {len(attempts)} native attempts and {len(artifacts)} artifacts.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("official", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    execute(args.official, args.output)


if __name__ == "__main__":
    main()
