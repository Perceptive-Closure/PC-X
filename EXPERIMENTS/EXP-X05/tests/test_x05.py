"""Focused correctness and proof-rejection controls for EXP-X05."""

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import unittest

from baselines import solve_explicit, subsets_by_price
from domain import FREEZES, workload
from engine import graph_signature, kernel, solve_symbolic
from reference import InvalidReport, RejectedSource, optimum, reference, verify_symbolic
from run import control_checks, verify_explicit


PROTOCOL = json.loads(
    (Path(__file__).resolve().parents[1] / "protocol.json").read_text(encoding="utf-8")
)
BUDGETS = PROTOCOL["budgets"]
CASES = {case.name: case for case in workload(PROTOCOL)}


class TestSymbolic(unittest.TestCase):
    def test_frozen_workload_retains_original_and_matched_strata(self):
        self.assertEqual(len(CASES), 70)
        original = [case for case in CASES.values() if case.stratum == "large"]
        matched = [case for case in CASES.values() if case.stratum == "large-matched"]
        self.assertEqual(len(original), len(matched))
        self.assertEqual({(case.freeze, case.threshold) for case in matched}, {("R", "middle")})
        for first, second in zip(original, matched, strict=True):
            self.assertEqual(first.stages, second.stages)
            self.assertEqual(first.seed, second.seed)

    def test_hand_controls_and_guard_refusals(self):
        for control in PROTOCOL["controls"]:
            name = control["name"]
            with self.subTest(control=name):
                case = CASES[name]
                result = solve_symbolic(case, BUDGETS)
                try:
                    checker = reference(case)
                except RejectedSource:
                    self.assertEqual(name, "unsupported-observation")
                    checker = None
                if checker is not None:
                    verify_symbolic(checker, result)
                control_checks(case, checker, result)

    def test_representation_labels_can_change_without_touching_r(self):
        stage = CASES["full-positive-support"].stages[0]
        graph = stage.graph
        nodes = list(graph.nodes)
        nodes[1] = replace(nodes[1], labels=(5, 5, 8, 13, 13))
        relabeled = replace(graph, nodes=tuple(nodes))
        self.assertEqual(kernel(graph, 0), kernel(relabeled, 0))
        self.assertEqual(graph_signature(graph, 0), graph_signature(relabeled, 0))

    def test_second_branch_changes_r_and_sets_the_closing_cost(self):
        case = CASES["full-positive-support"]
        graph = case.stages[0].graph
        signature_unblocked = graph_signature(graph, 0)
        signature_blocked = graph_signature(graph, 1)
        costs_without_freeze = FREEZES.index("none")
        self.assertEqual(signature_unblocked[costs_without_freeze],
                         signature_blocked[costs_without_freeze])
        self.assertEqual(
            signature_unblocked[costs_without_freeze],
            graph.nodes[0].actions[0].price + graph.nodes[2].actions[0].price,
        )
        self.assertGreater(signature_blocked[FREEZES.index("R")],
                           signature_unblocked[FREEZES.index("R")])
        self.assertIn("R", kernel(graph, 1)[1][0][0][2])

    def test_witness_cost_and_query_mutations_are_rejected(self):
        case = CASES["full-positive-support"]
        checker = reference(case)
        actual = solve_symbolic(case, BUDGETS)
        forged = deepcopy(actual)
        forged["rounds"][0]["witness"]["costs"] = (0, 0)
        with self.assertRaises(InvalidReport):
            verify_symbolic(checker, forged)
        altered = deepcopy(actual)
        altered["rounds"][-1]["selected"] = ()
        with self.assertRaises(InvalidReport):
            verify_symbolic(checker, altered)

    def test_unverifiable_lower_bound_is_rejected(self):
        case = CASES["full-positive-support"]
        result = solve_symbolic(case, BUDGETS)
        result["rounds"][-1]["bound"] += 1
        with self.assertRaises(InvalidReport):
            verify_symbolic(reference(case), result)

    def test_exact_unequal_costs_and_eager_edges(self):
        case = CASES["small-w3-n2-free"]
        checker = reference(case)
        actual = optimum(checker.queries, checker.edges)
        self.assertGreater(actual, 0)
        for eager in (False, True):
            result = solve_explicit(case, BUDGETS, eager=eager)
            verify_explicit(checker, result)
            self.assertEqual(result["cost"], actual)
            self.assertEqual(result["counters"]["materialized_completions"], 64)

    def test_explicit_caps_preserve_partial_counts(self):
        case = CASES["small-w3-n2-free"]
        budgets = {**BUDGETS, "eager_opposite_pairs": 1}
        result = solve_explicit(case, budgets, eager=True)
        self.assertEqual((result["status"], result["reason"]), ("UNRESOLVED", "opposite-pair-cap"))
        self.assertEqual(result["counters"]["opposite_pairs"], 1)
        self.assertIsNone(result["cost"])

    def test_positive_weight_subset_stream_is_complete(self):
        prices = (5, 1, 1, 4, 2)
        found = list(subsets_by_price(prices))
        self.assertEqual([cost for cost, _ in found], sorted(cost for cost, _ in found))
        self.assertEqual({mask for _, mask in found}, set(range(1 << len(prices))))
        self.assertEqual(len(found), 1 << len(prices))
        for cost, mask in found:
            self.assertEqual(cost, sum(price for i, price in enumerate(prices) if mask & (1 << i)))

    def test_unsupported_numeric_range_and_observation_alias(self):
        case = CASES["full-positive-support"]
        for invalid in (replace(case, budget=10001), CASES["unsupported-observation"]):
            result = solve_symbolic(invalid, BUDGETS)
            self.assertEqual((result["status"], result["reason"]), ("UNRESOLVED", "unsupported"))
            self.assertIsNone(result["cost"])
            with self.assertRaises(RejectedSource):
                reference(invalid)


if __name__ == "__main__":
    unittest.main()
