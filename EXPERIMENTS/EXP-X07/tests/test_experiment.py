"""Focused verdict, baseline and custody regression checks."""

import unittest

from run import check_receipt
from src.evaluate import tally
from src.model import conclusion, local_proof
from src.native import classify, native_fields_decision
from src.records import PROTOCOL_FILE, file_digest, protocol


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.spec = protocol()

    def test_uniform_and_realized_minima(self):
        proof = local_proof(self.spec)
        self.assertEqual(proof["uniform"]["cost"], 4)
        self.assertEqual(proof["selected"], ["issuer_binding", "leaf_validity"])
        self.assertEqual(
            {key: value["cost"] for key, value in proof["realized"].items()},
            {"approved-current": 4, "approved-expired": 1, "other-current": 3, "other-expired": 1},
        )
        cheaper = [row["conflict"] for row in proof["uniform"]["subsets"] if row["cost"] < 4]
        self.assertEqual(len(cheaper), 3)
        self.assertTrue(all(len(pair) == 2 for pair in cheaper))

    def test_refuse_ambiguity_and_inconsistent_evidence(self):
        cases = (
            ({}, "UNDERIDENTIFIED", "ABSTAIN"),
            ({"issuer_binding": True}, "UNDERIDENTIFIED", "ABSTAIN"),
            ({"leaf_validity": True}, "UNDERIDENTIFIED", "ABSTAIN"),
            ({"leaf_validity": False}, "IDENTIFIED", "FAIL"),
            ({"issuer_binding": False}, "IDENTIFIED", "FAIL"),
            ({"issuer_binding": True, "leaf_validity": True}, "IDENTIFIED", "PASS"),
            ({"issuer_binding": "true"}, "INCONSISTENT", "ABSTAIN"),
        )
        for answers, status, decision in cases:
            self.assertEqual(conclusion(self.spec, answers)["status"], status)
            self.assertEqual(conclusion(self.spec, answers)["decision"], decision)

    def test_native_fields_requires_printed_identifiers_and_time(self):
        identifier = ":".join(["a1"] * 20)
        approved = {"returncode": 0, "stdout": f"subject=CN=Issuer\n  {identifier}\n"}
        good = {"returncode": 0, "stdout": (
            "issuer=CN=Issuer\nnotBefore=2029-01-01 00:00:00Z\nnotAfter=2031-01-01 00:00:00Z\n"
            f"  {identifier}\n"
        )}
        initial = self.spec["native"]["initial_rejection"]
        self.assertEqual(native_fields_decision(self.spec, initial, good, approved), "PASS")
        for before, after, want in (
            ("2031", "2029", "FAIL"), ("a1", "b2", "FAIL"), ("00:00:00Z", "bad-date", "ABSTAIN"),
        ):
            changed = {**good, "stdout": good["stdout"].replace(before, after)}
            self.assertEqual(native_fields_decision(self.spec, initial, changed, approved), want)
        self.assertEqual(native_fields_decision(self.spec, {**initial, "depths": [1]}, good, approved), "ABSTAIN")

    def test_native_status_and_score_accounting(self):
        self.assertEqual(classify({"returncode": 0, "reason_codes": [], "stdout": "case.pem: OK\n"}), "PASS")
        self.assertEqual(classify({"returncode": 2, "reason_codes": [20]}), "FAIL")
        self.assertEqual(classify({"returncode": 1, "reason_codes": []}), "ABSTAIN")
        outcomes = {
            str(index): {"predictions": {"coarse": "FAIL", "pcx": prediction}, "native": actual}
            for index, (prediction, actual) in enumerate(
                [("PASS", "PASS"), ("FAIL", "FAIL"), ("PASS", "FAIL"), ("ABSTAIN", "FAIL"), ("FAIL", "ABSTAIN")]
            )
        }
        self.assertEqual(
            tally(outcomes, "pcx"),
            {"correct": 2, "wrong": 1, "abstain": 1, "false_pass": 1, "false_fail": 0,
             "correctly_reversed": 1, "correctly_retained": 1, "unusable_native": 1},
        )

    def test_wrong_forecast_digest_and_time_rejected(self):
        receipt = {
            "repository": "Perceptive-Closure/PC-X",
            "forecast_commit": "a" * 40,
            "forecast_verified_at": "2030-01-02T00:00:00+00:00",
            "native_started_at": "2030-01-03T00:00:00+00:00",
            "prediction_sha256": file_digest(PROTOCOL_FILE),
        }
        commitment = {"created_at": "2030-01-01T00:00:00+00:00"}
        check_receipt(receipt, commitment, PROTOCOL_FILE)
        for key, value in (
            ("prediction_sha256", "0" * 64),
            ("forecast_verified_at", "2030-01-04T00:00:00+00:00"),
            ("forecast_verified_at", "2029-12-31T00:00:00+00:00"),
        ):
            with self.assertRaises(ValueError):
                check_receipt({**receipt, key: value}, commitment, PROTOCOL_FILE)
