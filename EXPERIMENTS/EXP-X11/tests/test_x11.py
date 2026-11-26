import copy
import sys
import unittest
from fractions import Fraction
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from analysis import fidelity_verdict, interval_family, threshold_verdict
from common import CONFIG, digest, read_json
from measure import block_steps
from model import exact_risk, pre_audit
from pipeline import build_receipt, make_forecast, verify_open_inputs
from sandbox import run_sequence
from verify import score_ledger, verify_path, verify_pulse


class FidelityExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = read_json(CONFIG)
        cls.prior = pre_audit(cls.protocol)

    def test_exact_outcomes_under_each_capacity(self):
        contexts = self.protocol["contexts"]
        self.assertEqual(exact_risk(self.protocol, contexts["steady"], 3), Fraction(1, 16))
        self.assertEqual(exact_risk(self.protocol, contexts["burst"], 3), Fraction(7, 64))
        self.assertEqual(exact_risk(self.protocol, contexts["steady"], 2), Fraction(49, 64))
        self.assertEqual(exact_risk(self.protocol, contexts["burst"], 2), Fraction(25, 32))
        self.assertEqual(self.prior["exact_independently_scored_counts"]["probe_b"]["probe_b"]["steady"],
                         [3136, 4096])

    def test_equivalence_and_hidden_step_witness(self):
        support = self.prior["public_support"]
        self.assertEqual(support["public_mismatches"], 0)
        self.assertEqual(support["checked_rows"], 512)
        witness = support["observation_held_constant_witness"]
        self.assertEqual(witness["same_public"], ["regular", 3, "standard", "accepted"])
        self.assertEqual(sorted({tuple(event) for event in witness["machine_events"]}), [(3, 2), (3, 3)])
        self.assertGreater(support["private_event_distinctions"], 0)

    def test_audit_optimum_and_abstention(self):
        audit = self.prior["audit"]
        self.assertEqual(audit["selected"], ("probe_a_capacity",))
        self.assertEqual(audit["minimum_uniform_cost"], 2)
        self.assertEqual(audit["subsets_checked"], 16)
        for arm in self.protocol["ports"]:
            self.assertEqual(self.prior["not_queried"][arm]["fidelity_decision"], "abstain")

    def test_paired_anchor_requires_own_state_correspondence(self):
        for disturbed, arms in self.prior["coupling_support"].items():
            for arm in self.protocol["arms"]:
                if arm == "original":
                    continue
                bounds = [Fraction(row["union_risk_bound"]) for row in arms[arm].values()]
                if arm == disturbed:
                    self.assertTrue(all(bound > 0 for bound in bounds))
                else:
                    self.assertEqual(bounds, [0, 0])

    def test_observer_uses_the_service_ledger(self):
        valid = [(3, 2), (2, 2), (1, 2)]
        self.assertEqual(score_ledger(valid, 3, 2), 1)
        self.assertEqual(score_ledger([(3, 3), (2, 2), (1, 1)], 3, 2), 0)
        with self.assertRaisesRegex(ValueError, "Invalid service ledger"):
            score_ledger([(3, 4), *valid[1:]], 3, 2)

    def test_placebo_and_logger_installation_are_checked(self):
        recipe = [("regular", 1, 0), ("surge", 3, 1), ("regular", 0, 2)]
        original = run_sequence(self.protocol, "original", "probe_b", recipe)
        for arm in ("placebo", "probe_a"):
            frames = run_sequence(self.protocol, arm, "probe_b", recipe)
            verify_path(self.protocol, arm, 3, recipe, frames)
            self.assertEqual([row[:3] for row in frames], [row[:3] for row in original])
            frames[0][3] = None
            with self.assertRaisesRegex(ValueError, "Unexpected"):
                verify_path(self.protocol, arm, 3, recipe, frames)

    def test_inference_conditions_and_widths(self):
        comparisons, risk_w, paired_w = interval_family(self.protocol)
        self.assertEqual(comparisons, 14)
        self.assertLess(risk_w, 0.028)
        self.assertLess(2 * paired_w, 0.12)
        self.assertEqual(fidelity_verdict([(-0.13, 0.02)], 0.12), "abstain")
        self.assertEqual(fidelity_verdict([(-0.30, -0.20)], 0.12), "disturbed")
        self.assertEqual(threshold_verdict([(0.23, 0.31)], 0.30), "abstain")
        self.assertEqual(threshold_verdict([(0.23, 0.30)], 0.30), "within_threshold")

    def test_frozen_ticket_derivation_and_reset(self):
        steps = block_steps(self.protocol, "steady", 0, "24" * 32)
        self.assertEqual(steps, block_steps(self.protocol, "steady", 0, "24" * 32))
        self.assertNotEqual(steps, block_steps(self.protocol, "steady", 1, "24" * 32))
        self.assertEqual(run_sequence(self.protocol, "probe_a", "probe_b", steps),
                         run_sequence(self.protocol, "probe_a", "probe_b", steps))

    def test_receipt_forecast_and_reveal_bind_source(self):
        sealed = {"protocol_commit": "1" * 40, "source_commit": "2" * 40,
                  "pre_audit_sha256": digest(self.prior), "runner_sha256": self.prior["runner_sha256"],
                  "disturbed_port": "probe_b", "measurement_seed": "3" * 64, "nonce": "4" * 32}
        receipt = build_receipt(self.protocol, self.prior, sealed)
        forecast = make_forecast(self.protocol, self.prior, receipt)
        self.assertEqual(forecast["retained_completions"], ["probe_b"])
        self.assertEqual(forecast["predicted_naive_transfer_error_ports"], ["probe_b"])
        self.assertEqual(forecast["without_balanced_enrollment"]["unqueried_bounds"]["fidelity_decision"],
                         "abstain")
        verify_open_inputs(self.protocol, self.prior, sealed, receipt, forecast, "5" * 40)
        with self.assertRaisesRegex(ValueError, "distinct later revision"):
            verify_open_inputs(self.protocol, self.prior, sealed, receipt, forecast, "2" * 40)
        with self.assertRaisesRegex(ValueError, "committed receipt"):
            verify_open_inputs(self.protocol, self.prior, dict(sealed, nonce="6" * 32),
                               receipt, forecast, "5" * 40)
        other_forecast = copy.deepcopy(forecast)
        other_forecast["arm_predictions"]["probe_b"]["fidelity"] = "equivalent"
        with self.assertRaisesRegex(ValueError, "Forecast differs"):
            verify_open_inputs(self.protocol, self.prior, sealed, receipt, other_forecast, "5" * 40)

    def test_corrupt_probe_pulse_rejected(self):
        invalid = {"start": [0, 0], "supplied": 4, "completed": 3, "end": [1, 0]}
        with self.assertRaisesRegex(ValueError, "Invalid isolated capacity readback"):
            verify_pulse(self.protocol, "probe_a_capacity", invalid)


if __name__ == "__main__":
    unittest.main()
