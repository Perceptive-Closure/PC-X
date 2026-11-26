"""Frozen checks exercised before private fixture enrollment."""

import os
from pathlib import Path
import unittest

from common import HISTORIES, PROTOCOL, ROOT, case_id
from contract import preaudit, prediction
from custody import measured_answers
from verify import pair_equalities, verify_witness_table, view_labels


class PreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        deps = Path(os.environ.get("PCX_X06_DEPS", ROOT / "scratch/deps"))
        cls.record = preaudit(deps)

    def test_two_worlds_two_source_compatible_completions(self):
        table = self.record["witness_table"]
        self.assertEqual(sum(len(rows) for pair in table.values() for rows in pair.values()), 16)
        verify_witness_table(table)
        self.assertEqual(self.record["verdict_initial"], "UNDERIDENTIFIED")

    def test_exact_correlated_target_set(self):
        self.assertEqual(len(self.record["joint_identified_set"]), 16)
        self.assertEqual(self.record["independent_bit_relaxation_size"], 256)
        for target in self.record["joint_identified_set"]:
            for i in range(0, 8, 2):
                self.assertIn(target[i:i + 2], ("01", "10"))

    def test_exact_global_query_minimum(self):
        self.assertEqual(self.record["audit_cost"], 8)
        self.assertEqual(self.record["direct_partition"]["subsets_checked"], 4096)
        self.assertEqual([step["cost"] for step in self.record["lazy_transcript"]], [0, 2, 4, 6, 8])
        self.assertEqual(self.record["cheapest_first_cost"], 12)
        self.assertEqual(self.record["exhaustive_query_cost"], 28)

    def test_evidence_ablation_is_inaccessible(self):
        ablation = self.record["evidence_ablation"]
        self.assertEqual(ablation["status"], "AUDIT_INACCESSIBLE")
        self.assertNotEqual(*ablation["witness"])

    def test_no_audit_refuses_to_forecast(self):
        with self.assertRaisesRegex(ValueError, "does not identify"):
            prediction(self.record, {})
        selected = self.record["selected"]
        with self.assertRaisesRegex(ValueError, "does not identify"):
            prediction(self.record, {name: "2" for name in selected})

    def test_each_attainable_readout_has_a_unique_prediction(self):
        selected = self.record["selected"]
        for row in self.record["completions"]:
            answers = {q: row["answers"][q] for q in selected}
            self.assertEqual(prediction(self.record, answers), row["prediction"])

    def test_only_admission_counts_can_be_read(self):
        assignment = {"adapters": {}}
        for stratum in PROTOCOL["strata"]:
            assignment["adapters"][case_id(stratum, 0)] = {"receipt_marks": ["anonymous-ticket-admitted"]}
        result = measured_answers(assignment, self.record["selected"])
        self.assertTrue(all(value == "1" for value in result.values()))
        with self.assertRaisesRegex(ValueError, "unfrozen"):
            measured_answers(assignment, ["self.renderer-partition"])

    def test_renderer_equality_is_extensional(self):
        labels = [f"exact:{i}" for i in range(len(HISTORIES))]
        self.assertFalse(pair_equalities(labels))
        self.assertEqual(view_labels({"H": ["ticket:0"], "PR": labels}, [True, False]), {True})
        labels[2] = labels[1]
        self.assertEqual(pair_equalities(labels), {(1, 2)})
        self.assertEqual(view_labels({"H": ["ticket:0"], "PR": labels}, [True, False]), {True, False})

    def test_development_and_holdout_requests_are_distinct(self):
        holdout = {tuple(req) for stratum in PROTOCOL["strata"] for req in stratum["requests"]}
        controls = {tuple(control["request"]) for control in PROTOCOL["development_controls"]}
        self.assertTrue(holdout.isdisjoint(controls))


if __name__ == "__main__":
    unittest.main()
