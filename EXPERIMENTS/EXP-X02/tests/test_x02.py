"""Unit and negative controls for the nonrectangular evidence fragment."""

from dataclasses import replace
from math import inf
from pathlib import Path
import json
import unittest

from cases import all_cases, control_cases
from model import (
    FREEZE_NAMES, UnsupportedKernel, compatible_assignments, kernel_key, materialize,
    signature, touch_profile, validate_case,
)
from reference import truth_table
from run import assert_named_controls, evaluate, has_witness, negative_kernel_checks

BASE = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((BASE / "protocol.json").read_text(encoding="utf-8"))
LIMITS = PROTOCOL["finite_limits"]
CONTROLS = {case.name: case for case in control_cases()}


class NonrectangularEvidenceTests(unittest.TestCase):
    def test_frozen_case_counts_and_unique_names(self):
        cases = all_cases(PROTOCOL)
        self.assertEqual(len(cases), 94)
        self.assertEqual(len({case.name for case in cases}), 94)
        self.assertEqual(sum(case.stratum == "exhaustive" for case in cases), 48)

    def test_controls_match_preregistered_values_and_refinements(self):
        results = [evaluate(case, LIMITS) for case in CONTROLS.values()]
        assert_named_controls(results)
        self.assertTrue(all(len(result["refinements"]) == 6 for result in results))

    def test_exclusive_and_contradictory_domains(self):
        for name, assignments in (
            ("complementary", ((False, True), (True, False))),
            ("infeasible", ()),
        ):
            case = CONTROLS[name]
            self.assertEqual(compatible_assignments(case), assignments)
            self.assertEqual(truth_table(case), assignments)

    def test_rejects_inadmissible_assignment_and_corrupt_signature(self):
        case = CONTROLS["finite-fallback"]
        row = (True, False)
        correct = signature(case, touch_profile(case, materialize(case, row)))
        incorrect = (*correct[:2], 999, *correct[3:])
        self.assertTrue(has_witness(case, row, correct))
        self.assertFalse(has_witness(case, row, incorrect))
        self.assertFalse(has_witness(case, (True, True), correct))
        self.assertFalse(has_witness(case, (1, False), correct))

    def test_all_branches_contribute_extensional_touch(self):
        case = CONTROLS["mixed-support"]
        root = (0, "atomic")
        untouched_representation = touch_profile(case, materialize(case, (False, True)))[root]
        mixed_resources = touch_profile(case, materialize(case, (True, False)))[root]
        self.assertEqual(untouched_representation, frozenset({"E"}))
        self.assertEqual(mixed_resources, frozenset({"E", "R"}))

    def test_partition_relabeling_is_extensional(self):
        case = CONTROLS["mixed-support"]
        contract = materialize(case, (True, False))
        renamed = replace(contract, states=tuple(
            replace(state, representation=tuple(f"{index}-{item}" for item in state.representation))
            for index, state in enumerate(contract.states)
        ))
        self.assertEqual(kernel_key(contract, case), kernel_key(renamed, case))
        self.assertEqual(touch_profile(case, contract), touch_profile(case, renamed))

    def test_kernel_drift_is_refused(self):
        self.assertEqual(len(negative_kernel_checks()), 4)

    def test_no_proper_closer_does_not_mean_inconsistent_evidence(self):
        case = replace(CONTROLS["independent"], routes=((), (), ()))
        outcome = evaluate(case, LIMITS)
        self.assertEqual(outcome["compatible_rows"], 4)
        self.assertEqual(outcome["status"], "point")
        self.assertEqual(outcome["joint_signatures"], [["inf"] * len(FREEZE_NAMES)])
        self.assertTrue(has_witness(case, (True, True), (inf,) * len(FREEZE_NAMES)))

    def test_refuses_unsupported_literal_and_cycle(self):
        case = CONTROLS["independent"]
        with self.assertRaisesRegex(UnsupportedKernel, "outside"):
            validate_case(replace(case, clauses=((3,),)), LIMITS)
        cycle = replace(case.routes[0][0], successors=(0,))
        with self.assertRaisesRegex(UnsupportedKernel, "forward"):
            validate_case(replace(case, routes=((cycle,), (), ())), LIMITS)

    def test_rectangular_budget_overflow_is_refused(self):
        case = CONTROLS["independent"]
        with self.assertRaisesRegex(UnsupportedKernel, "limit"):
            evaluate(case, {**LIMITS, "rectangular_profiles": 3})


if __name__ == "__main__":
    unittest.main()
