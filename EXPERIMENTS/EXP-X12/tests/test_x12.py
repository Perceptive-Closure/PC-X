import json
from fractions import Fraction
from itertools import product
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import analysis
import measure
import oracle
import outcomes
import runtime as rt
import x12


class X12Tests(unittest.TestCase):
    def test_exact_preflight_verifies_full_eval_and_target_distinct_witnesses(self):
        report = oracle.exact_preflight()
        self.assertEqual(report["paths_checked"], 192)
        self.assertEqual(report["covered_transport_checks"], 80)
        self.assertEqual(report["query_subset_checks"], 24)
        for row in report["witnesses"].values():
            self.assertEqual(row["exact_equal_full_eval_laws"], 4)
            self.assertLessEqual(Fraction(row["safe_worst"]), Fraction(7, 20))
            self.assertGreater(Fraction(row["unsafe_worst"]), Fraction(7, 20))
            self.assertEqual(row["uncovered_risk_gap_by_context"], {"routine": "1/5", "busy": "9/20"})

    def test_reactive_and_memory_dependent_policy_paths(self):
        _, sorting = rt.episode("sorter", "routine", "standard", (0, 1, 0, 0))
        self.assertEqual([row[2] for row in sorting], [1, 1, 0])
        _, queue = rt.episode("queue", "routine", "standard", (0, 1, 0, 0))
        self.assertEqual([row[2] for row in queue], [0, 1, 0])
        self.assertEqual([row[4] for row in queue], [1, 0, 0])

    def test_union_bound_matches_exact_covered_coupling(self):
        for family in rt.FAMILIES:
            installed = rt.install(family, "bounded_drift", 1)
            seams = oracle.exact_step_disagreement(rt.REFERENCES["nominal"]["busy"]["priority"],
                                                  installed.limits["busy"]["priority"])
            self.assertEqual(seams, [Fraction(10, 1000), Fraction(8, 1000),
                                    Fraction(12, 1000), Fraction(9, 1000)])
            oracle.assert_transport(installed)

    def test_exact_identity_requires_same_storage(self):
        shared = measure.registry(rt.install("sorter", "identical", 0))
        equal_but_independently_installed = measure.registry(rt.install("sorter", "missing_support", 0))
        self.assertTrue(shared["shared_storage"])
        self.assertFalse(equal_but_independently_installed["shared_storage"])

    def test_pulse_uses_actual_passive_placebo_and_audit_branches(self):
        matched = measure.pulse(rt.install("sorter", "bounded_drift", 0))
        disturbed = measure.pulse(rt.install("sorter", "fidelity_violation", 0))
        self.assertTrue(analysis.faithful_pulse(matched))
        self.assertFalse(analysis.faithful_pulse(disturbed))
        self.assertEqual([row[:2] for row in matched], [row[:2] for row in disturbed])
        self.assertEqual([row[0] != row[2] for row in disturbed], [True, False, True, True, False, True])

    def test_support_keeps_the_full_uncovered_contribution(self):
        weights = {"standard": 0.25, "priority": 0.3, "novel": 0.45}
        low, high = analysis.mixture(weights, {"standard": [0.1, 0.2], "priority": [0.2, 0.3]})
        self.assertAlmostEqual(low, 0.085)
        self.assertAlmostEqual(high, 0.59)
        self.assertEqual(analysis.verdict(low, high), "abstain")

    def test_threshold_strictness_and_worst_context(self):
        self.assertEqual(analysis.verdict(0.1, 0.35), "safe")
        self.assertEqual(analysis.verdict(0.35, 0.9), "abstain")
        self.assertEqual(analysis.verdict(0.35001, 0.9), "unsafe")
        self.assertEqual(analysis.envelope({"routine": [0.05, 0.4], "busy": [0.2, 0.25]})["worst"], [0.2, 0.4])

    def test_family_error_and_fixed_batch_counts(self):
        design = analysis.confidence_design()
        self.assertAlmostEqual(design["simultaneous_alpha_budget"], 0.05)
        self.assertEqual(design["multiplicity"], {"reference": 16, "paired": 192, "full": 48, "holdout": 24})
        with self.assertRaises(ValueError):
            analysis.proportion_band(0, 16, "holdout")
        with self.assertRaises(ValueError):
            analysis.paired_bounds([[0, 0, 2, 3]] * 4)

    def test_custody_uses_disjoint_seed_domains(self):
        common = "public-development-test"
        values = [rt.random_stream(common, label, "S01").randrange(2**64) for label in x12.SEED_NAMES]
        self.assertEqual(len(set(values)), len(values))
        assignment = x12.recreate_assignment(common)
        self.assertEqual(assignment, x12.recreate_assignment(common))
        for family in rt.FAMILIES:
            self.assertCountEqual(
                [item["control"] for item in assignment.values() if item["family"] == family],
                rt.CONTROLS,
            )

    def fake_measurement(self, family, control, variant):
        installed = rt.install(family, control, variant)
        bank = rt.REFERENCES[installed.bank]
        paired = {}
        direct = {}
        for context in rt.CONTEXTS:
            paired[context] = {}
            direct[context] = {}
            for stratum in rt.COVERED:
                target = installed.limits[context][stratum]
                steps = oracle.exact_step_disagreement(bank[context][stratum], target)
                n = analysis.SAMPLE_SIZES["paired"]
                mismatches = [round(n * float(value)) for value in steps]
                if installed.probe_overwrites:
                    mismatches = [0] * len(rt.STAGES)
                paired[context][stratum] = [[n - k, 0, k, 0] for k in mismatches]
                d_n = analysis.SAMPLE_SIZES["full"]
                exact = oracle.conditional_risk(family, context, stratum, target)
                direct[context][stratum] = {"n": d_n, "events": round(d_n * float(exact))}
        return {"registry": measure.registry(installed), "pulse": measure.pulse(installed),
                "paired": paired, "direct": direct}

    def test_primary_controls_for_every_public_candidate_using_exact_expected_counts(self):
        refs = measure.calibration()
        for family, (control, expected), variant in product(rt.FAMILIES, outcomes.EXPECTED_PRIMARY.items(), (0, 1)):
            with self.subTest(family=family, control=control, variant=variant):
                record = self.fake_measurement(family, control, variant)
                unit = analysis.forecast_units({"A01": record}, refs, {"A01": family})["A01"]
                self.assertEqual(unit["anchored"]["verdict"], expected)
                if control == "vacuous":
                    self.assertEqual(unit["anchored"]["worst"], [0.0, 1.0])
                if control == "fidelity_violation":
                    self.assertEqual(unit["ignore_fidelity"]["verdict"], "safe")
                    self.assertEqual(unit["full"]["verdict"], "unsafe")

    def test_forecast_fails_closed_on_mismatched_labels(self):
        family = "sorter"
        record = self.fake_measurement(family, "identical", 0)
        record["registry"]["deployed_semantics"]["event"] = "different-label"
        unit = analysis.forecast_units({"A01": record}, measure.calibration(), {"A01": family})["A01"]
        self.assertEqual(unit["admission"], "semantic_mismatch")
        self.assertEqual(unit["anchored"]["verdict"], "abstain")

    def test_random_and_greedy_batch_baselines(self):
        assumed = analysis.acquisition_costs({"registry", "pulse"})
        self.assertEqual(assumed["anchored"], 19)
        self.assertEqual(assumed["cheapest_first"], assumed["restricted_minimum"])
        self.assertGreater(assumed["uniform_order_mean"], assumed["restricted_minimum"])
        self.assertEqual(assumed["nonadaptive"], assumed["uniform_order_worst"])

    def test_independent_scoring_rejects_impossible_queue_machine_record(self):
        with self.assertRaises(ValueError):
            outcomes.count_ledger("queue", [[2, 0, 0, 3, 0]], 0)
        self.assertEqual(outcomes.count_ledger("sorter", [[0, 1, 1, 1]], 0), (1, 0, 1))

    def test_opening_requires_later_verified_sha_and_bound_receipt(self):
        seed = "a" * 64
        private = {"protocol": rt.CONFIG["id"], "source_commit": "1" * 40,
                   "reserved_at_utc": "2026-11-26T10:00:00Z", "nonce": "b" * 64,
                   "assignment": x12.recreate_assignment(seed), "seeds": dict.fromkeys(x12.SEED_NAMES, seed)}
        receipt = {"private_commitment": x12.digest(x12.canonical(private)), "source_commit": "1" * 40}
        receipt_sha = x12.digest(x12.canonical(receipt))
        forecast_sha = x12.digest(x12.canonical({}))
        opening = {
            "private": private, "forecast_commit": "2" * 40, "verified_remote_tip": "2" * 40,
            "verified_at_utc": "2026-11-26T10:01:00Z", "opened_at_utc": "2026-11-26T10:02:00Z",
            "receipt_sha256": receipt_sha, "forecast_sha256": forecast_sha,
        }
        with patch.object(x12, "forecast_record", return_value={}), patch.object(x12, "make_receipt", return_value=receipt):
            x12.validate_opening(opening, receipt, receipt_sha, {}, forecast_sha)
            for field, altered in (("verified_remote_tip", "3" * 40),
                                   ("verified_at_utc", "2026-11-26T09:59:59Z"),
                                   ("receipt_sha256", "c" * 64)):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    x12.validate_opening({**opening, field: altered}, receipt, receipt_sha, {}, forecast_sha)

    def test_forecast_json_is_canonical(self):
        content = {"b": [3], "a": {"summary": True}}
        blob = x12.canonical(content)
        self.assertEqual(json.loads(blob), content)
        self.assertTrue(blob.startswith(b'{\n  "a"'))
        self.assertTrue(blob.endswith(b"\n"))


if __name__ == "__main__":
    unittest.main()
