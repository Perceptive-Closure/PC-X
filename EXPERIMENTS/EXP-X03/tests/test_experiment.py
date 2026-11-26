import json
from dataclasses import replace
from itertools import product
from pathlib import Path
import unittest

from src.authorization import SemanticCompletion, cases, evaluate, independent_path_costs
from src.baselines import evaluate as baselines
from src.certificates import (
    CERTIFIED, INACCESSIBLE, INCONSISTENT, Certificate, Completion, Problem, solve,
)
from src.corpus import exhaustive, hand_controls, seeded
from src.reference import conflict, exact_by_partition, verify_proof, verify_witness


BASE = Path(__file__).resolve().parents[1]
CONFIG = json.loads((BASE / "configs" / "protocol.json").read_text(encoding="utf-8"))
CONTROLS = hand_controls()


class CertificateTests(unittest.TestCase):
    def test_positive_weight_and_shape_validation(self):
        for invalid_cost in (False, True, 0, -1, 1.0):
            with self.subTest(invalid_cost=invalid_cost), self.assertRaises(ValueError):
                Problem("bad", ("a",), (invalid_cost,), ())
        for keywords in (
            {"query_names": ("x", "x"), "costs": (1, 2)},
            {"query_names": ("x",), "costs": (1, 2)},
            {"completions": (Completion("a", (), "A"),)},
            {"completions": (Completion("a", ("b",), "A"), Completion("a", ("c",), "B"))},
            {"completions": (Completion("a", (10,), "A"),)},
        ):
            defaults = {"name": "bad", "query_names": ("x",), "costs": (1,), "completions": ()}
            with self.subTest(keywords=keywords), self.assertRaises(ValueError):
                Problem(**(defaults | keywords))

    def test_empty_and_homogeneous(self):
        empty = CONTROLS["empty_evidence"]
        self.assertEqual(solve(empty).status, INCONSISTENT)
        self.assertTrue(verify_proof(empty, solve(empty)))
        homogeneous = CONTROLS["homogeneous_distinct_contracts"]
        self.assertEqual(solve(homogeneous).cost, 0)
        self.assertEqual(solve(homogeneous).queries, ())
        self.assertFalse(verify_proof(empty, Certificate(CERTIFIED, 0)))

    def test_inaccessible_and_partly_accessible_realized_scopes(self):
        no_queries = CONTROLS["no_queries_heterogeneous"]
        self.assertEqual(solve(no_queries).status, INACCESSIBLE)
        self.assertTrue(verify_proof(no_queries, solve(no_queries)))
        table = CONTROLS["localized_inaccessibility"]
        self.assertEqual(solve(table).status, INACCESSIBLE)
        self.assertEqual(solve(table, "c0").status, INACCESSIBLE)
        self.assertEqual(solve(table, "c2").cost, 2)
        self.assertTrue(verify_proof(table, solve(table, "c2"), "c2"))
        with self.assertRaises(ValueError):
            solve(table, "not-admitted")

    def test_weighted_cost_is_distinct_from_inclusion_minimality(self):
        problem = CONTROLS["weighted_deletion_trap"]
        checked = solve(problem)
        optimized = exact_by_partition(problem)
        comparators = baselines(problem, None, random_seed=90, permutations=16)
        self.assertEqual((checked.cost, checked.queries), (4, (0, 1)))
        self.assertEqual(optimized.optima, ((0, 1),))
        self.assertEqual(comparators["deletion"].attempted_cost, 9)
        self.assertIsNone(conflict(problem, (2,)))
        self.assertFalse(verify_proof(problem, Certificate(CERTIFIED, 9, (2,))))

    def test_greedy_cover_trap(self):
        problem = CONTROLS["greedy_cover_trap"]
        self.assertEqual(solve(problem).queries, (1, 2))
        self.assertEqual(baselines(problem, None, random_seed=0, permutations=16)["greedy"].attempted_cost, 3)

    def test_strict_global_realized_gap(self):
        problem = CONTROLS["strict_local_global"]
        self.assertEqual(solve(problem).cost, 2)
        self.assertEqual({solve(problem, row.identity).cost for row in problem.completions}, {1})

    def test_multivalued_answers_and_multiple_minima(self):
        categorical = CONTROLS["categorical_query"]
        self.assertEqual(solve(categorical).cost, 3)
        ties = CONTROLS["equal_cost_ties"]
        reference = exact_by_partition(ties)
        self.assertEqual(reference.optima, ((0,), (1,)))
        self.assertTrue(verify_proof(ties, Certificate(CERTIFIED, 2, (1,))))

    def test_protocol_perturbations(self):
        solution = solve(CONTROLS["cost_perturbation"])
        self.assertEqual((solution.cost, solution.queries), (1, (2,)))
        for name in ("missing_query_perturbation", "answer_perturbation"):
            with self.subTest(name=name):
                problem = CONTROLS[name]
                self.assertEqual(solve(problem).status, INACCESSIBLE)
                self.assertTrue(verify_proof(problem, solve(problem)))

    def test_corrupted_proofs_and_witnesses_are_rejected(self):
        weighted = CONTROLS["weighted_deletion_trap"]
        optimum = solve(weighted)
        for corrupted in (
            replace(optimum, cost=3),
            replace(optimum, cost=True),
            replace(optimum, queries=(0,)),
            replace(optimum, queries=(0, 0)),
            replace(optimum, queries=(0, -1)),
            replace(optimum, queries=(0, 99)),
            replace(optimum, queries=(False, 1)),
            Certificate(INACCESSIBLE, witness=("c0", "c2")),
        ):
            with self.subTest(corrupted=corrupted):
                self.assertFalse(verify_proof(weighted, corrupted))
        inaccessible = CONTROLS["localized_inaccessibility"]
        self.assertFalse(verify_witness(inaccessible, ("c0", "forged"), (0,)))
        self.assertFalse(verify_witness(inaccessible, ("c0", "c0"), (0,)))
        self.assertFalse(verify_witness(inaccessible, ("c0", "c2"), (0,)))
        self.assertFalse(verify_witness(inaccessible, ("c0", "c1"), (0,), "c2"))
        self.assertTrue(verify_witness(inaccessible, ("c0", "c1"), (0,), "c0"))

    def test_frozen_domain_counts_and_seeds(self):
        exercise = list(exhaustive(CONFIG["exhaustive"]))
        self.assertEqual(sum(p.name.startswith("distinct") for p in exercise), 240)
        self.assertEqual(sum(p.name.startswith("alias") for p in exercise), 512)
        sample = list(seeded(CONFIG["seeded"]))
        self.assertEqual(len(sample), 96)
        self.assertEqual([seed for _, seed, _ in sample], list(range(712003, 712099)))
        self.assertEqual(tuple(CONTROLS), tuple(CONFIG["controls"]))


class AuthorizationTests(unittest.TestCase):
    def test_independent_path_values_for_all_complete_contracts(self):
        config = CONFIG["authorization"]
        costs, freezes = config["action_costs"], config["freeze_order"]
        for settings in product("ER", "ER", (False, True)):
            completion = SemanticCompletion(*settings)
            with self.subTest(completion=completion):
                self.assertEqual(evaluate(completion, costs, freezes), independent_path_costs(completion, costs, freezes))
        self.assertEqual(evaluate(SemanticCompletion("E", "R", False), costs, freezes), (1, 5, 1, 1, None, 5, 1, None))
        self.assertEqual(evaluate(SemanticCompletion("R", "R", False), costs, freezes), (1, 1, 4, 1, None, 1, None, None))
        self.assertEqual(evaluate(SemanticCompletion("R", "R", True), costs, freezes), (1, 1, 2, 1, None, 1, 2, None))

    def test_semantically_meaningful_target_full_cost_and_audit_removal(self):
        fixtures = {problem.name: problem for problem in cases(CONFIG["authorization"])}
        narrow = fixtures["pc_grid_rfreeze"]
        broad = fixtures["pc_grid_signature"]
        self.assertEqual(solve(narrow).cost, 6)
        self.assertEqual(solve(broad).cost, 8)
        self.assertEqual(solve(fixtures["pc_correlated_rfreeze"]).cost, 6)
        self.assertEqual(solve(fixtures["pc_missing_fast_rfreeze"]).status, INACCESSIBLE)
        self.assertEqual(solve(fixtures["pc_homogeneous_rfreeze"]).cost, 0)
        # Holding fast admission and license fixed, the archive changes the E freeze.
        self.assertEqual(narrow.completions[0].target, narrow.completions[2].target)
        self.assertNotEqual(broad.completions[0].target, broad.completions[2].target)


if __name__ == "__main__":
    unittest.main()
