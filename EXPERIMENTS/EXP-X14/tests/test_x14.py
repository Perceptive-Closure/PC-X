"""Regressions for support, resource bounds, brittle observations and custody."""

import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from audit import COMPLETIONS, model_read, measured_read, posterior
from checker import reference_cost, verify_certificate, verify_policy
from common import CONFIG
from custody import validate_receipt
from engine import play, score
from game import Game
from preflight import FIXED_LEFT, REFUSE, held_scope, verify_transitions


class BoundedChecks(unittest.TestCase):
    def control(self, name):
        scope = CONFIG["controls"][name]
        cert = Game(scope).certificate()
        verify_certificate(scope, cert)
        return scope, cert

    def test_expected_named_controls(self):
        expected = {
            "common": ("winning", 0), "quantifier-gap": ("infeasible", None),
            "audit-enabled": ("winning", 2), "audit-horizon": ("infeasible", None),
            "observation-alias": ("infeasible", None), "refined-view": ("winning", 3),
            "authority-enabled": ("winning", 4), "authority-withheld": ("infeasible", None),
            "mixed-acquisition": ("winning", 6), "impossible-evidence": ("inconsistent", None),
        }
        for name, (status, cost) in expected.items():
            with self.subTest(name=name):
                _, cert = self.control(name)
                self.assertEqual((cert["status"], cert["cost"]), (status, cost))

    def test_quantifier_gap_and_masked_world(self):
        scope, cert = self.control("quantifier-gap")
        self.assertEqual(cert["immediate"], ["buffer", "refuse"])
        for profile in scope["profiles"]:
            self.assertEqual(reference_cost({**scope, "profiles": [profile]}), 0)
        aliased, _ = self.control("observation-alias")
        self.assertIsNone(reference_cost(aliased))
        self.assertEqual(reference_cost(aliased, omniscient=True), 0)

    def test_policy_mutations(self):
        scope, cert = self.control("common")
        policy = cert["policy"]
        missing = deepcopy(policy)
        del missing["branches"]["offer-1"]
        spurious = deepcopy(policy)
        spurious["branches"]["third-slot"] = {"complete": True}
        bad_leaf = deepcopy(policy)
        bad_leaf["branches"]["offer-0"]["branches"]["complete"]["complete"] = 1
        unsafe = {**policy, "action": "right"}
        label_leak = {**policy, "profile": "left-indexed"}
        for description, changed in (("missing", missing), ("spurious", spurious),
                                     ("false leaf", bad_leaf), ("unsafe", unsafe), ("leak", label_leak)):
            with self.subTest(description=description), self.assertRaises(ValueError):
                verify_policy(scope, changed, 0)
        with self.assertRaises(ValueError):
            verify_policy(scope, policy, 1)
        with self.assertRaises(ValueError):
            verify_policy({**scope, "horizon": 1}, policy, 0)
        with self.assertRaises(ValueError):
            verify_policy(scope, REFUSE, 0)

    def test_refusal_stall_and_authority(self):
        scope, cert = self.control("authority-enabled")
        self.assertEqual(cert["policy"]["action"], "grant")
        fake = {"action": "relief", "branches": {"queued": {"complete": True}}}
        with self.assertRaises(ValueError):
            verify_policy(scope, fake, 0)
        idle = {"action": "buffer", "branches": {"buffered": REFUSE}}
        trace = play("relief-only", False, 1, scope, idle)
        self.assertEqual(score("relief-only", False, 1, scope, trace),
                         {"finish": "refused", "safe": True, "useful": False,
                          "qualified": 1, "audit_cost": 0})
        with self.assertRaises(ValueError):
            verify_policy(scope, idle, 0)

    def test_losing_proof_mutations(self):
        scope, valid = self.control("quantifier-gap")
        invalid = deepcopy(valid)
        proof = invalid["counterproof"]
        del proof["nodes"][proof["root"]]["rejections"]["right"]
        with self.assertRaises(ValueError):
            verify_certificate(scope, invalid)
        invalid = deepcopy(valid)
        proof = invalid["counterproof"]
        proof["nodes"][proof["root"]]["rejections"]["buffer"]["observation"] = "complete"
        with self.assertRaises(ValueError):
            verify_certificate(scope, invalid)
        invalid = deepcopy(valid)
        invalid["lower_bound"] = scope["horizon"]
        with self.assertRaises(ValueError):
            verify_certificate(scope, invalid)

    def test_extensional_touches(self):
        checked = verify_transitions(3)["audit_touch_counts"]
        self.assertEqual(set(checked["layout"]), {"E", "empty"})
        self.assertEqual(set(checked["plate"]), {"E", "empty"})
        self.assertEqual(set(checked["refine"]), {"R", "empty"})
        self.assertEqual(set(checked["grant"]), {"A", "empty"})

    def test_ledger_corruption(self):
        scope = held_scope(["left-indexed"])
        trace = play("left-indexed", True, 1, scope, FIXED_LEFT)
        self.assertEqual(score("left-indexed", True, 1, scope, trace)["finish"], "unsafe")
        trace["events"][0]["physical_job"]["bench"] = "right"
        with self.assertRaises(ValueError):
            score("left-indexed", True, 1, scope, trace)


class AcquisitionChecks(unittest.TestCase):
    def test_independent_structural_read(self):
        for query in ("layout-A", "viewer-B", "roster", "nameplate"):
            for candidate in (COMPLETIONS[0], COMPLETIONS[-1]):
                self.assertEqual(model_read(candidate, query), measured_read(candidate, query))

    def test_impossible_receipt(self):
        policy = {"query": "layout-A", "branches": {}}
        with self.assertRaisesRegex(ValueError, "Impossible audit observation"):
            posterior([{"query": "layout-A", "value": "attic"}], policy)
        with self.assertRaisesRegex(ValueError, "registered audit"):
            posterior([{"query": "roster", "value": True}], policy)

    def test_receipt_metadata_rejects_stage_hash_drift(self):
        incoming = {"protocol_commit": "a" * 40, "source_commit": "b" * 40,
                    "source_manifest_sha256": "c" * 64, "pre_audit_sha256": "d" * 64,
                    "exact_sha256": "e" * 64, "commitment": "f" * 64, "cost": 0, "reads": [],
                    "reserved_at_utc": "2026-11-26T00:00:00Z",
                    "issued_at_utc": "2026-11-26T00:00:01Z"}
        with patch("custody.pinned_evidence", return_value={"source_manifest_sha256": "e" * 64}):
            with self.assertRaisesRegex(ValueError, "Archived evidence mismatch"):
                validate_receipt(incoming, {})
        incoming["ticket_order_seed"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_receipt(incoming, {})
