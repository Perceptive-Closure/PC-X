
from dataclasses import replace
from itertools import product
import json
from math import inf
from pathlib import Path
import unittest

from src.fixtures import (
    candidate, factorial_cases, fixture, hand_cases, hidden_case, malformed_cases,
    mixed_case, only_e, source_boundary, state,
)
from src.model import (
    Action, Certificate, ContractError, Evidence, Fact, FREEZE_NAMES,
    checkpoint_target_classes, identify, profiles, semantic_fact, signature,
    source_sha256, touched,
)
from src.reference import reference_signature, verify_certificate

CONFIG = json.loads((Path(__file__).resolve().parents[1] / "configs/protocol.json").read_bytes())


class CompleteContractTests(unittest.TestCase):
    def test_original_coordinate_order(self):
        self.assertEqual(FREEZE_NAMES, ("none", "E", "R", "A", "ER", "EA", "RA", "ERA"))

    def test_source_boundary_equivalence_and_freeze_gap(self):
        for backup in (None, 2, 4, 9):
            with self.subTest(backup=backup):
                e = source_boundary("E", backup, 0)
                r = source_boundary("R", backup, 0)
                self.assertEqual(source_sha256(e), source_sha256(r))
                for checkpoint in range(len(e.states)):
                    self.assertEqual(
                        checkpoint_target_classes(e, checkpoint), checkpoint_target_classes(r, checkpoint)
                    )
                self.assertEqual(touched(e, 0, e.states[0].candidates[0].support), {"E"})
                self.assertEqual(touched(r, 0, r.states[0].candidates[0].support), {"R"})
                self.assertEqual(signature(e)[0], signature(r)[0])
                self.assertEqual(signature(e)[2], 1)
                self.assertEqual(signature(r)[2], inf if backup is None else backup)

    def test_representation_relabeling_is_extensional(self):
        for role, backup in product(("E", "R"), (None, 2, 4, 9)):
            first = source_boundary(role, backup, 0)
            second = source_boundary(role, backup, 1)
            self.assertNotEqual(first.states[0].representation, second.states[0].representation)
            self.assertEqual(signature(first), signature(second))
            self.assertEqual(semantic_fact(first, 0, "R"), semantic_fact(second, 0, "R"))

    def test_hidden_states_and_visible_outcomes(self):
        self.assertEqual(signature(hidden_case("merged", False, 1))[0], inf)
        self.assertEqual(signature(hidden_case("merged", True, 1))[0], 6)
        self.assertEqual(signature(hidden_case("observation", False, 1))[0], 3)
        self.assertEqual(signature(hidden_case("outcome", False, 1))[0], 3)

    def test_protected_query_must_survive_freeze_at_each_hidden_state(self):
        contract, expected = next(
            pair for pair in hand_cases() if pair[0].name.endswith("support-union-reduces-actions")
        )
        self.assertEqual(signature(contract), expected)
        self.assertEqual(signature(contract)[2], 7)

    def test_mixed_atomic_touch_union_and_successor_order(self):
        first = mixed_case(False, 4)
        second = mixed_case(True, 4)
        self.assertEqual(source_sha256(first), source_sha256(second))
        self.assertEqual(touched(first, 0, first.states[0].candidates[0].support), {"E", "R"})
        self.assertEqual(touched(second, 0, second.states[0].candidates[0].support), {"E", "R"})
        self.assertEqual(signature(first), signature(second))
        self.assertEqual(profiles(first, representative_only=True)[2].cost, 1)
        self.assertEqual(profiles(second, representative_only=True)[2].cost, 4)
        self.assertEqual(signature(first)[2], 4)

    def test_all_hand_and_factorial_derivations(self):
        for contract, expected in list(hand_cases()) + list(factorial_cases(CONFIG)):
            with self.subTest(contract=contract.name):
                self.assertEqual(signature(contract), expected)
                self.assertEqual(reference_signature(contract), expected)

    def test_closed_checkpoint_is_target_relative(self):
        contract, _ = next(pair for pair in hand_cases() if pair[0].name.endswith("target-relative-closed"))
        self.assertEqual(sum(contract.states[0].history in history for history in contract.compatibility), 2)
        self.assertEqual(checkpoint_target_classes(contract, 0), {"allow"})
        self.assertEqual(signature(contract), (0,) * 8)

    def test_each_support_leaf_can_close_to_different_classes(self):
        contract = fixture(
            "two certificates",
            (Action("read", "local", 1),),
            (
                state(0, rows=(candidate("read", (1, "done"), (2, "done")),)),
                state(1, observation="closed"),
                state(3, observation="closed"),
            ),
        )
        self.assertEqual(checkpoint_target_classes(contract, 1), {"allow"})
        self.assertEqual(checkpoint_target_classes(contract, 2), {"deny"})
        self.assertEqual(signature(contract), only_e(1))

    def test_cycles_with_and_without_proper_policy(self):
        names = {"zero-loop-exit": 3, "loop-without-exit": inf, "hopeful-loop-fallback": 4,
                 "observable-support-shrink": 4}
        for contract, _ in hand_cases():
            name = contract.name.rsplit("/", 1)[-1]
            if name in names:
                self.assertEqual(signature(contract)[0], names[name])
                self.assertEqual(reference_signature(contract)[0], names[name])

    def test_malformed_contracts_both_refuse_and_cannot_certify(self):
        for condition, malformed in malformed_cases():
            with self.subTest(condition=condition):
                with self.assertRaises(ContractError):
                    signature(malformed)
                with self.assertRaises(ValueError):
                    reference_signature(malformed)
                with self.assertRaises(ContractError):
                    identify((malformed,), Evidence("some source"))


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.e = source_boundary("E", 4, 0)
        self.r = source_boundary("R", 4, 0)
        self.other = source_boundary("E", 9, 0)
        self.anchored = next(c for c, _ in hand_cases() if c.name.endswith("anchored-alternate-history"))
        self.catalog = (self.e, self.r, self.other, self.anchored)
        self.evidence = Evidence(source_sha256(self.e))

    def test_ambiguity_witness_and_public_source_exclusion(self):
        actual = identify(self.catalog, self.evidence)
        self.assertEqual(actual.verdict, "UNDERIDENTIFIED")
        self.assertEqual(len(actual.signatures), 2)
        self.assertEqual(len(actual.compatible), 3)
        self.assertNotIn(self.other.name, actual.compatible)
        self.assertTrue(verify_certificate(self.catalog, self.evidence, actual))

    def test_point_certificate_spans_genuinely_distinct_contracts(self):
        evidence = replace(self.evidence, facts=(Fact(0, "H", 0),))
        certificate = identify(self.catalog, evidence)
        self.assertEqual(certificate.verdict, "IDENTIFIED")
        self.assertEqual(set(certificate.compatible), {self.e.name, self.anchored.name})
        self.assertNotEqual(self.e.states[1].history, self.anchored.states[1].history)
        self.assertTrue(verify_certificate(self.catalog, evidence, certificate))

    def test_empty_catalog_and_contradictory_evidence_are_inconsistent(self):
        evidence = replace(self.evidence, facts=(Fact(0, "H", len(self.e.histories)),))
        self.assertEqual(identify(self.catalog, evidence), Certificate("INCONSISTENT", (), (), ()))
        self.assertEqual(identify((), self.evidence), Certificate("INCONSISTENT", (), (), ()))

    def test_corrupt_certificate_label_refuses(self):
        actual = identify(self.catalog, self.evidence)
        self.assertFalse(verify_certificate(self.catalog, self.evidence, replace(actual, verdict="IDENTIFIED")))

    def test_corrupt_witness_wrong_source_or_value_refuses(self):
        actual = identify(self.catalog, self.evidence)
        _, value = actual.witnesses[0]
        wrong_source = replace(actual, witnesses=((self.other.name, value),) + actual.witnesses[1:])
        self.assertFalse(verify_certificate(self.catalog, self.evidence, wrong_source))
        impossible = replace(actual, witnesses=((self.e.name, (0,) * 8),) + actual.witnesses[1:])
        self.assertFalse(verify_certificate(self.catalog, self.evidence, impossible))

    def test_corrupt_membership_or_incomplete_set_refuses(self):
        actual = identify(self.catalog, self.evidence)
        self.assertFalse(verify_certificate(
            self.catalog, self.evidence, replace(actual, compatible=actual.compatible[:-1])
        ))
        self.assertFalse(verify_certificate(
            self.catalog, self.evidence, replace(actual, signatures=actual.signatures[:-1])
        ))

    def test_duplicate_completion_ids_refused(self):
        duplicated = (self.e, self.e)
        with self.assertRaises(ContractError):
            identify(duplicated, self.evidence)
        one = identify((self.e,), self.evidence)
        self.assertFalse(verify_certificate(duplicated, self.evidence, one))

    def test_invalid_resource_and_checkpoint_refused(self):
        for bad in (Fact(0, "unknown", 1), Fact(-1, "H", 0), Fact(99, "A", frozenset())):
            with self.subTest(fact=bad), self.assertRaises(ContractError):
                identify(self.catalog, replace(self.evidence, facts=(bad,)))
