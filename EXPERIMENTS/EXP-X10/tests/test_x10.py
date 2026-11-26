"""Tests for the exact controls, observation boundary and sealed measurement stages."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analysis import audit_bounds, candidates, checked_measurement, exact_cells, targets, verify_exact, visible_law
from routing import Fixture, execute, quality_label
from x10 import digest, evidence_result, load_spec, make_forecast, now, outcome_bytes, read_json, release, reserve, value_digest, verify_open


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.spec = load_spec()

    def test_exact_projection_and_reader_control(self):
        result = verify_exact(self.spec)
        self.assertTrue(result["monitor_visible_equivalent"])
        self.assertEqual((result["candidate_count"], result["checked_traces"]), (8, 768))
        self.assertNotEqual(result["witness"][0]["threshold_signature"], result["witness"][1]["threshold_signature"])
        for stratum in self.spec["strata"]:
            self.assertEqual(result["law"][stratum]["alarm"], "1/6")
            self.assertEqual(result["law"][stratum]["control_alarm"], "1/3")
            self.assertNotEqual(visible_law(self.spec, stratum), visible_law(self.spec, stratum, True))

    def test_independent_card_and_false_alarm_counts(self):
        a = Fixture("atlas", "v1")
        h = Fixture("harbor", "v2")
        self.assertEqual(exact_cells(self.spec, a)["routine"], {
            "risk": Fraction(1, 6), "alarm": Fraction(1, 6), "miss": Fraction(1, 24), "false_alarm": Fraction(1, 24),
        })
        self.assertEqual(targets(self.spec, h), (Fraction(59, 96), Fraction(47, 96)))
        self.assertEqual(execute("oversize", 18).alarm, True)
        self.assertIsNone(quality_label("E", None))
        self.assertFalse(quality_label("E", "E"))
        self.assertTrue(quality_label("E", "W"))

    def test_minimum_audit_and_expected_random_cost(self):
        result = verify_exact(self.spec)
        self.assertEqual(result["minimum_audit"], {"cost": 2, "queries": (("intake-A", "calibration_lane"),)})
        self.assertEqual(result["full_contract"]["cost"], 4)
        self.assertEqual(result["baseline_costs"], {"cheapest_first_worst": 4, "random_order_mean": "8/3",
                                                     "random_order_worst": 4, "greedy_worst": 4, "exhaustive": 6})
        self.assertEqual(result["stock_only_groups_unresolved"], 4)

    def test_t25_attained_bounds(self):
        row = [row for row in candidates(self.spec) if row[0].regime == "atlas"]
        bound = audit_bounds(self.spec, row)["intake-A"]["contexts"]["peak-mix"]
        self.assertEqual((bound["eta"], bound["beta"], bound["additive_upper"], bound["conditional_upper"]),
                         ("1/12", "2/5", "1/4", "5/18"))
        self.assertLess(Fraction(bound["conditional_upper"]), Fraction(self.spec["violation_threshold"]))


class CustodyTests(unittest.TestCase):
    def setUp(self):
        self.spec = load_spec()
        self.preaudit = verify_exact(self.spec)

    def _receipt(self, assignment):
        private = {
            "fixture": {name: list(fixture) for name, fixture in zip(self.spec["units"], assignment)},
            "protocol_sha256": value_digest(self.spec), "pre_audit_commit": "a" * 40,
            "trial_seed": "0" * 64, "nonce": "1" * 64,
        }
        answers = [self.spec["calibration_lanes"][assignment[0][0]]]
        return private, {
            "queries": [["intake-A", "calibration_lane"]], "answers": answers, "issued_at_utc": now(),
            "assignment_commitment_sha256": value_digest(private), "protocol_sha256": value_digest(self.spec),
            "pre_audit_commit": "a" * 40,
        }

    def test_reservation_reads_only_off_population_card_fact(self):
        with TemporaryDirectory() as scratch, patch("x10.outcome_bytes", side_effect=AssertionError("Trial ran during audit")):
            private_path = Path(scratch) / "private.json"
            receipt_path = Path(scratch) / "receipt.json"
            receipt = reserve(self.spec, self.preaudit, "a" * 40, private_path, receipt_path)
            self.assertNotIn("fixture", receipt)
            self.assertNotIn("trial_seed", receipt)
            self.assertEqual(receipt["assignment_commitment_sha256"], value_digest(read_json(private_path)))

    def test_open_and_detect_balanced_design_dependency(self):
        private, receipt = self._receipt((("atlas", "v2"), ("harbor", "v1")))
        forecast = make_forecast(self.spec, self.preaudit, receipt)
        self.assertEqual(forecast["compatible_installations"], 4)
        self.assertEqual(len(forecast["without_balanced_enrollment"]["joint_signatures"]), 2)
        self.assertEqual(forecast["judgments"]["intake-A"], {"risk": True, "miss": True})
        verify_open(self.spec, receipt, private, self.preaudit, forecast)
        tampered = deepcopy(forecast)
        tampered["judgments"]["intake-A"]["risk"] = False
        with self.assertRaisesRegex(ValueError, "forecast"):
            verify_open(self.spec, receipt, private, self.preaudit, tampered)
        private["nonce"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "commitment"):
            verify_open(self.spec, receipt, private, self.preaudit, forecast)

    def test_reject_release_at_wrong_tip(self):
        private, receipt = self._receipt((("atlas", "v1"), ("harbor", "v1")))
        forecast = make_forecast(self.spec, self.preaudit, receipt)
        with TemporaryDirectory() as scratch:
            output = Path(scratch) / "opening"
            with self.assertRaisesRegex(ValueError, "branch tip"):
                release(self.spec, self.preaudit, private, receipt, forecast, "b" * 40, "c" * 40, now(), output)
            self.assertFalse(output.exists())

    def test_public_development_trials_replay_and_strip_missing_truth(self):
        # This uses a disclosed test seed and a separate developer fixture.
        private, receipt = self._receipt((("atlas", "v2"), ("harbor", "v1")))
        forecast = make_forecast(self.spec, self.preaudit, receipt)
        assignment = verify_open(self.spec, receipt, private, self.preaudit, forecast)
        observations = outcome_bytes(self.spec, assignment, private["trial_seed"])
        result = evidence_result(self.spec, observations, assignment, forecast)
        self.assertEqual((result["heldout_trials"], result["threshold_confirmations"],
                          result["forecast_envelope_overlaps"]), (16384, 4, 8))
        self.assertEqual(result["alarm_only_false_certifications"], 1)
        self.assertEqual(digest(observations), result["episode_data_sha256"])
        for unit in result["units"].values():
            self.assertEqual(sum(unit["missing_oversize_labels"].values()), 4096)
            interval = unit["contexts"]["peak-mix"]["missing_oversize_risk_interval"]
            self.assertLess(interval[0], float(Fraction(self.spec["violation_threshold"])))
            self.assertGreater(interval[1], float(Fraction(self.spec["violation_threshold"])))
        lines = [json.loads(line) for line in observations.splitlines()]
        lines[0]["trusted_label"] = None
        with self.assertRaisesRegex(ValueError, "independently scored"):
            checked_measurement(self.spec, lines, assignment, forecast)


if __name__ == "__main__":
    unittest.main()
