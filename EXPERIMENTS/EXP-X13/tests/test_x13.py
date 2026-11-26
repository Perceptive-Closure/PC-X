"""Regression tests for the experimental gates and release checks."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from audit import CATALOG, audit_read, posterior
from common import AGENTS, MODES, PORTS, RESULTS, canonical, digest, source_hashes, utc_now
from preflight import run
from sandbox import Workshop
from scoring import score
from stages import RECEIPT_METADATA, make_forecast, validate_opening


class CompositionStudyTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.pre_audit = run()

    def test_local_evidence_and_preserved_history(self):
        isolated = self.pre_audit["isolation"]
        self.assertEqual(isolated["native_trials"], 2048)
        self.assertEqual(len(set(isolated["evidence_sha256"].values())), 1)
        for mode, evidence in self.pre_audit["reference_modes"].items():
            with self.subTest(mode=mode):
                judgments = evidence["judgments"]
                self.assertTrue(judgments["isolated_certificates_valid"])
                self.assertEqual(judgments["local_history_preserved"], mode.endswith("/faithful"))

    def test_containment_and_carryover_fail_independently(self):
        expected = [(True, True), (True, False), (False, True), (False, False)]
        for (mode, evidence), gates in zip(self.pre_audit["reference_modes"].items(), expected, strict=True):
            with self.subTest(mode=mode):
                actual = evidence["judgments"]
                self.assertEqual((actual["event_containment"], actual["local_bounds_carried_over"]),
                                 gates)
                self.assertEqual("outside_union" in evidence["witnesses"], not gates[0])
                self.assertEqual("new_local_violation" in evidence["witnesses"], not gates[1])

    def test_nonindependence_in_useful_regime(self):
        model = self.pre_audit["reference_modes"]["exclusive/faithful"]
        self.assertTrue(model["judgments"]["useful_certificate"])
        self.assertEqual(model["judgments"]["composed_bound"], "1/4")
        for context, cell in model["contexts"].items():
            with self.subTest(context=context):
                self.assertGreater(cell["both_local"], 0)
                self.assertNotEqual(cell["both_local"] * cell["episodes"],
                                    cell["joint_local"]["alpha"] * cell["joint_local"]["beta"])
                self.assertEqual(cell["global"], cell["local_union"])

    def test_scorer_reads_occupancy_and_clock_instead_of_requests(self):
        rows = [
            {"turn": turn, "agent": name, "station": "shared", "quanta": [0],
             "requested": 2, "seen": "untrusted"}
            for turn in range(2) for name in AGENTS
        ]
        clean_orders = score("balanced", (4, 0), rows, AGENTS)
        self.assertEqual(clean_orders["local"], {"alpha": False, "beta": False})
        self.assertTrue(clean_orders["outside_union"])
        short_orders = score("balanced", (0, 0), rows, AGENTS)
        self.assertEqual(short_orders["local"], {"alpha": True, "beta": True})
        self.assertFalse(short_orders["outside_union"])
        self.assertEqual(short_orders["qualified"], {"alpha": 0, "beta": 0})
        with self.assertRaises(ValueError):
            score("balanced", (4, 0), rows[:3], AGENTS)
        with self.assertRaises(ValueError):
            score("balanced", (4, 0), [*rows, rows[0]], AGENTS)

    def test_workshop_rejects_claims_outside_local_authority(self):
        plant = Workshop("exclusive", "faithful", "alpha")
        for claims in ([{"agent": "alpha", "preferred": "private-beta"}],
                       [{"agent": "unknown", "preferred": "shared"}],
                       [{"agent": "alpha", "preferred": "shared"}] * 2):
            with self.subTest(claims=claims), self.assertRaises(ValueError):
                plant.grant(claims)

    def test_sentinel_budget_ablation(self):
        audit = self.pre_audit["audit"]["composition"]
        self.assertEqual(audit["minimum_cost"], 15)
        self.assertEqual(audit["minimum_set_count"], 16)
        self.assertEqual(audit["subsets_checked"], 1024)
        completion = (MODES, "alpha")
        reads = {query: audit_read(completion, query) for query in audit["selected"]}
        self.assertEqual(len(posterior(reads)), 2)
        self.assertEqual(len(posterior({"nameplate": audit_read(completion, "nameplate")})), 48)
        for omitted in ("allocator", "view"):
            surviving = {key: value for key, value in reads.items() if CATALOG[key][0] != omitted}
            with self.subTest(omitted=omitted):
                self.assertGreater(len(posterior(surviving)), len(posterior(reads)))

    def test_opening_binding_and_forecast_checks_without_a_deployment_run(self):
        completion = (MODES, "alpha")
        sealed = {
            "protocol_commit": "a" * 40, "source_commit": "b" * 40,
            "source_sha256": digest(canonical(source_hashes())),
            "pre_audit_sha256": digest((RESULTS / "pre-audit.json").read_bytes()),
            "reserved_at_utc": utc_now(), "modes": dict(zip(PORTS, MODES, strict=True)),
            "tie_order": "alpha", "ticket_order_seed": "4" * 64, "nonce": "0" * 32,
        }
        audit = self.pre_audit["audit"]["composition"]
        reads = {query: audit_read(completion, query) for query in audit["selected"]}
        receipt = {key: sealed[key] for key in RECEIPT_METADATA}
        receipt.update({"commitment": digest(canonical(sealed)), "reads": reads,
                        "cost": audit["minimum_cost"], "issued_at_utc": utc_now()})
        forecast = make_forecast(receipt, utc_now())
        verification = {"forecast_commit": "c" * 40, "remote_tip": "c" * 40,
                        "verified_at_utc": utc_now(), "opened_at_utc": utc_now()}
        with self.assertRaisesRegex(ValueError, "commitment"):
            validate_opening({**sealed, "nonce": "1" * 32}, receipt, forecast, verification)
        changed = copy.deepcopy(forecast)
        changed["prediction"]["A"]["contexts"]["balanced"]["global"] += 1
        with self.assertRaisesRegex(ValueError, "Forecast"):
            validate_opening(sealed, receipt, changed, verification)
        with self.assertRaisesRegex(ValueError, "verification"):
            validate_opening(sealed, receipt, forecast, {**verification, "remote_tip": "d" * 40})
        self.assertEqual(validate_opening(sealed, receipt, forecast, verification), (
            dict(zip(PORTS, MODES, strict=True)), "alpha"))


if __name__ == "__main__":
    unittest.main()
