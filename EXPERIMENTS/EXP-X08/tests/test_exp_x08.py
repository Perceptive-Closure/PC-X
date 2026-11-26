"""Independent and adversarial checks for the X08 finite interface."""

from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "src"))

import model
import pipeline
import sandbox


class ExperimentalProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = pipeline.load_json(PACKAGE / "configs/protocol.json")
        cls.analysis = pipeline.exact_analysis(cls.spec)

    def development_fixture(self):
        opening = {
            "profiles": {"parcel-A": "careful", "parcel-B": "throughput"},
            "feeders": {"parcel-A": "fast", "parcel-B": "slow"},
            "seed_hex": "00000000000000000000000000000001",
            "nonce_hex": "00000000000000000000000000000002",
            "protocol_sha256": pipeline.digest(self.spec),
            "pre_audit_commit": "a" * 40,
        }
        receipt = {
            "commitment_sha256": pipeline.digest(opening),
            "protocol_sha256": pipeline.digest(self.spec),
            "pre_audit_commit": opening["pre_audit_commit"],
            "selected_query": ["parcel-A", "routing_calibration"],
            "answer": 5,
        }
        return opening, receipt

    def test_full_transcript_conditional_law_invariance(self):
        self.assertEqual(self.analysis["evaluation_histories_per_fixture"], 73)
        self.assertEqual(self.analysis["evaluation_history_request_pairs_per_fixture"], 146)
        self.assertEqual(self.analysis["independent_ticket_laws_verified"]["benchmark"], 584)
        self.assertEqual(self.analysis["bench_tv"], "0")
        self.assertEqual(self.analysis["visible_noise_bit_tv"], "0")
        self.assertEqual(self.analysis["positive_floor_cue_control_tv"], "1/2")
        self.assertEqual(self.analysis["initial_identified_set"], [(False, True), (True, False)])

    def test_feedback_and_request_change_policy(self):
        actor = sandbox.RoutingAgent(self.spec, "careful")
        self.assertEqual(actor.choose("benchmark", "rush", 4), "belt")
        self.assertEqual(actor.choose("benchmark", "normal", 4), "manual")
        actor.receive(True)
        self.assertEqual(actor.choose("benchmark", "rush", 4), "manual")

    def test_one_round_risk_by_hand(self):
        spec = deepcopy(self.spec)
        spec["violation_minimum_retry_rounds"] = 1
        # Careful/fast/rush procures 5/8 manual tickets and 3/8 belt; the belt retries 6/8.
        fixture = ("careful", "fast")
        self.assertEqual(model.behavioral_risk(spec, fixture, "floor", ["rush"]), Fraction(9, 32))
        self.assertEqual(model.retry_state_risk(spec, fixture, "floor", ["rush"]), Fraction(9, 32))

    def test_minimum_route_audit_and_ablation(self):
        certificate = self.analysis["certificate"]
        self.assertEqual(certificate["selected"], (("parcel-A", "routing_calibration"),))
        self.assertEqual(certificate["minimum_cost"], 2)
        self.assertEqual(certificate["cheapest_first_cost"], 6)
        self.assertEqual(certificate["exhaustive_cost"], 8)
        self.assertTrue(certificate["audit_inaccessible_without_routing_calibration"])

    def test_grounded_repair_and_parity_ablation(self):
        opening, receipt = self.development_fixture()
        pipeline.verify_receipt_and_opening(self.spec, receipt, opening)
        forecast = pipeline.make_forecast(self.spec, receipt, self.analysis)
        self.assertEqual(forecast["remaining_completions"], 4)
        self.assertEqual(forecast["forecast"], {"parcel-A": True, "parcel-B": False})
        self.assertEqual(forecast["parity_removed_identified_set"], [[True, False], [True, True]])
        self.assertEqual(
            list(map(Fraction, forecast["risk_bands"]["parcel-A"]["mixed-normal"])),
            [Fraction(1395, 16384), Fraction(3701, 16384)],
        )

    def test_rejects_corrupt_audit_count_and_reveal(self):
        opening, receipt = self.development_fixture()
        mismatching = dict(receipt, answer=4)
        with self.assertRaisesRegex(ValueError, "no source-compatible completion"):
            pipeline.make_forecast(self.spec, mismatching, self.analysis)
        wrong_seed = dict(opening, seed_hex="f" * 32)
        with self.assertRaisesRegex(ValueError, "does not match"):
            pipeline.verify_receipt_and_opening(self.spec, receipt, wrong_seed)
        with self.assertRaisesRegex(ValueError, "disagrees"):
            pipeline.verify_receipt_and_opening(self.spec, mismatching, opening)

    def test_statistical_analysis_and_corrupt_logger(self):
        # Execute only this declared development seed, never the separately sealed fixture.
        opening, receipt = self.development_fixture()
        forecast = pipeline.make_forecast(self.spec, receipt, self.analysis)
        with TemporaryDirectory() as temporary:
            summary = pipeline.measure(self.spec, opening, forecast, temporary)
            self.assertTrue(summary["forecast_confirmed"])
            self.assertEqual(summary["benchmark_false_certifications"], 1)
            self.assertEqual(sum(row["trials"] for row in summary["measurement"]), 8192)
            self.assertLess(summary["half_width"], .05)
            raw = Path(temporary) / "episodes.jsonl"
            clean_lines = raw.read_text(encoding="utf-8").splitlines()
            raw.write_text("\n".join(clean_lines[:-1]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "omitted"):
                pipeline.compile_observations(self.spec, raw)
            first = json.loads(clean_lines[0])
            first["episode"] = 1024
            raw.write_text(json.dumps(first), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "index"):
                pipeline.compile_observations(self.spec, raw)


if __name__ == "__main__":
    unittest.main()
