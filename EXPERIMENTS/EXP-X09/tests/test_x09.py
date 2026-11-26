"""Focused regressions for scope, independent checks and prospective evidence."""

from fractions import Fraction
from pathlib import Path
from random import Random
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import audit
from contract import ADMITTED, ROSTER, SPEC, TICKETS
import exact
from measure import proportion_interval, threshold_verdict
from model import FAILS, MEETS, right_probability, risks
from sandbox import RecheckStation, SortingPolicy, factor_observation, reset_batch


def trays(right):
    return "1" * right + "0" * (audit.N - right)


def ideal_probe(fixture, query):
    expected = right_probability(fixture, query.cue, query.context)
    return trays(int(expected * audit.N))


class RuntimeTests(unittest.TestCase):
    def test_reset_clears_history(self):
        profile = ADMITTED[1]
        agent = SortingPolicy(profile)
        action = ("gold", "smooth", "plain", 10)
        self.assertEqual(agent.place(*action), 1)
        self.assertEqual(agent.place(*action), 0)
        agent.reset()
        self.assertEqual(agent.place(*action), 1)

    def test_trim_preserves_full_law(self):
        for fixture in ROSTER:
            for cue in SPEC["cues"]:
                for context in SPEC["contexts"]:
                    counts = [
                        exact.runtime_right(fixture, (), (True, cue, context, trim))
                        for trim in SPEC["trims"]
                    ]
                    self.assertEqual(*counts)

    def test_station_shift_changes_scores_without_observability(self):
        admitted, shift = ROSTER[0], ROSTER[6]
        first = reset_batch(admitted, "gold", "smooth", audit.N, Random(3))
        second = reset_batch(shift, "gold", "smooth", audit.N, Random(3))
        self.assertEqual(first, second)
        station, shifted_station = RecheckStation(admitted, "gold"), RecheckStation(shift, "gold")
        self.assertEqual([station.score(0, 8), shifted_station.score(0, 8)], [0, 1])

    def test_factor_warm_prefix_reaches_runtime_memory(self):
        fixture = ADMITTED[0]
        draw = factor_observation(fixture, "carry", "gold", "ribbed", "dotted", Random(41))
        assert draw[0] is not None
        self.assertEqual(draw[1], SortingPolicy(fixture).place(*SPEC["warm_up"], draw[0]))
        expected = right_probability(fixture, "gold", "ribbed", draw[1])
        self.assertEqual(draw[-1], int(draw[2] < TICKETS * expected))

    def test_bad_runtime_law_is_detected(self):
        with patch.object(SortingPolicy, "place", return_value=1):
            with self.assertRaises(AssertionError):
                exact.check_conditional(ADMITTED[0], (), (True, "blue", "smooth", "plain"))

    def test_invalid_operator_input_rejected(self):
        with self.assertRaises(ValueError):
            SortingPolicy(ADMITTED[0]).place("blue", "smooth", "other", 0)


class DesignTests(unittest.TestCase):
    def test_gold_changes_target_and_full_law(self):
        a, b = ADMITTED[:2]
        self.assertEqual(exact.law_signature(a, "fixed_blue"), exact.law_signature(b, "fixed_blue"))
        self.assertEqual(exact.law_signature(a, "carry"), exact.law_signature(b, "carry"))
        self.assertNotEqual(right_probability(a, "gold", "smooth"), right_probability(b, "gold", "smooth"))
        self.assertLess(max(risks(a).values()), max(risks(b).values()))

    def test_exact_costs_and_bounds(self):
        report = exact.law_costs()
        self.assertEqual(report["first_action"], "blue/smooth")
        self.assertEqual(report["adaptive_minimax"], 5)
        self.assertEqual(report["minimum_static"], 7)
        for result in exact.information_bounds().values():
            self.assertGreater(result["expected_cost_lower_bound"], 0)

    def test_interval_and_independent_threshold(self):
        self.assertEqual(proportion_interval(0, 10, Fraction(1, 10)), ["0", "1/10"])
        self.assertEqual(threshold_verdict({"smooth": {"interval": ["3/5", "4/5"]}}), MEETS)
        self.assertEqual(threshold_verdict({"smooth": {"interval": ["9/10", "1"]}}), FAILS)
        self.assertEqual(threshold_verdict({"smooth": {"interval": ["4/5", "9/10"]}}), "INCONCLUSIVE")

    def test_prespecified_coverage_and_power_checks(self):
        self.assertEqual(exact.confidence_design()["smallest_distinct_reset_gap"], "3/8")
        self.assertEqual(len(exact.risk_report()), len(ROSTER))


class AuditTests(unittest.TestCase):
    def test_target_class_and_cost_of_each_frozen_profile(self):
        for fixture in ADMITTED:
            with self.subTest(profile=fixture.name):
                result = audit.run("primary", lambda query: ideal_probe(fixture, query))
                self.assertEqual(result["status"], audit.CERTIFIED)
                self.assertEqual(result["verdict"], (MEETS, FAILS)[fixture.variant])
                self.assertEqual(result["cost"], (4 if fixture.key == "smooth" else 5) * audit.N)

    def test_fixed_blue_abstains(self):
        result = audit.run("fixed_blue", lambda query: ideal_probe(ADMITTED[1], query))
        self.assertEqual(result["status"], audit.ABSTAIN)
        self.assertIsNone(result["verdict"])

    def test_midpoint_and_empty_set_do_not_certify(self):
        midpoint = ROSTER[4]
        result = audit.run("primary", lambda query: ideal_probe(midpoint, query))
        self.assertEqual(result["status"], audit.INCONSISTENT)
        self.assertIsNone(result["verdict"])
        self.assertEqual(audit.decision(()), (audit.INCONSISTENT, None))

    def test_audit_radius_and_out_of_range_observations(self):
        self.assertIn(0, audit.retained(audit.CANDIDATES, 0, 44))
        self.assertNotIn(0, audit.retained(audit.CANDIDATES, 0, 45))
        with self.assertRaises(ValueError):
            audit.retained(audit.CANDIDATES, 0, audit.N + 1)

    def test_receipt_rejects_unselected_queries(self):
        with self.assertRaises(ValueError):
            audit.verify_selected([{"query": "gold/smooth", "trays": trays(20)}])
        with self.assertRaises(ValueError):
            audit.verify_selected([{"query": "blue/smooth", "trays": "2" * audit.N}])
        records = [
            {"query": "blue/smooth", "trays": trays(20)},
            {"query": "gold/smooth", "trays": trays(140)},
        ]
        self.assertEqual(audit.verify_selected(records)["verdict"], FAILS)
        with self.assertRaises(ValueError):
            audit.verify_selected([*records, {"query": "gold/ribbed", "trays": trays(20)}])


if __name__ == "__main__":
    unittest.main()
