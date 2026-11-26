import copy
import json
from pathlib import Path
import unittest

from src.audit import Case, Completion, fixed_policy, greedy_policy, solve
from src.cases import address, address_bounds, controls, routed
from src.reference import adaptive_budget_optimum, certificate_optima, measure, replay, verify_witness


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((ROOT / "configs" / "protocol.json").read_bytes())


class OptimizerChecks(unittest.TestCase):
    def setUp(self):
        self.controls = {case.name: case for case in controls(PROTOCOL["controls"])}

    def test_inconsistent_domain_never_certifies(self):
        case = self.controls["empty_domain"]
        self.assertEqual(solve(case).status, "INCONSISTENT")
        self.assertEqual(replay(case, None), [])
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            replay(case, {"target": "approve"})

    def test_constant_target_and_explicit_full_acquisition(self):
        case = self.controls["constant_target"]
        self.assertEqual(solve(case).cost, 0)
        self.assertEqual(measure(replay(case, solve(case).tree))["expected_cost"], "0")
        self.assertEqual(measure(replay(case, fixed_policy(case, (0,))))["worst_cost"], 3)

    def test_no_query_and_full_answer_alias_witnesses(self):
        for name in ("no_queries", "full_answer_alias"):
            case = self.controls[name]
            result = solve(case)
            self.assertEqual(result.status, "AUDIT_INACCESSIBLE")
            self.assertIsNone(adaptive_budget_optimum(case)[0])
            verify_witness(case, result.witness)
            with self.assertRaisesRegex(ValueError, "disagree in target"):
                verify_witness(case, (result.witness[0], result.witness[0]))

    def test_majority_has_strict_local_minimax_gap(self):
        case = self.controls["majority_of_three"]
        uniform, local = certificate_optima(case)
        self.assertEqual(set(local.values()), {2})
        self.assertEqual(solve(case).cost, 3)
        self.assertEqual(adaptive_budget_optimum(case)[0], 3)
        self.assertEqual(uniform[0], 3)

    def test_weighted_categorical_has_three_attainable_answers(self):
        case = self.controls["categorical_weighted"]
        result = solve(case)
        self.assertEqual(result.cost, 5)
        self.assertEqual(result.tree["query"], "route")
        self.assertEqual(set(result.tree["answers"]), {"red", "blue", "gray"})
        self.assertEqual(measure(replay(case, result.tree))["expected_cost"], "11/3")
        self.assertEqual(certificate_optima(case)[0][0], 6)

    def test_address_lower_bounds_and_explicit_domains(self):
        for width in (1, 2):
            case = address(width, 1)
            bound = address_bounds(width, 1)
            self.assertEqual(len(case.rows), bound["domain_size"])
            self.assertEqual(solve(case).cost, bound["minimax_cost"])
            self.assertEqual(adaptive_budget_optimum(case)[0], bound["minimax_cost"])
            self.assertEqual(certificate_optima(case)[0][0], bound["static_cost"])

    def test_routed_touch_and_ablated_interface(self):
        spec = PROTOCOL["routed"]
        active = routed(spec, next(row for row in spec["conditions"] if row["name"] == "route_3"))
        withheld = routed(
            spec, next(row for row in spec["conditions"] if row["name"] == "route_3_without_dispatch"),
        )
        self.assertEqual({row.target for row in active.rows}, {"2", "5"})
        self.assertEqual(active.rows[0].target, "5")
        self.assertEqual(solve(active).cost, 2)
        self.assertEqual(certificate_optima(active)[0][0], 4)
        self.assertEqual(solve(withheld).status, "AUDIT_INACCESSIBLE")
        verify_witness(withheld, solve(withheld).witness)

    def test_positive_integer_cost_and_prior_required(self):
        for cost, weight in ((0, 1), (True, 1), (1, 0)):
            with self.assertRaises(ValueError):
                Case("invalid", "control", ("known",), (cost,), (Completion("c", ("v",), "t", weight),))


class PolicyAdversarialChecks(unittest.TestCase):
    def setUp(self):
        self.case = controls(("categorical_weighted",))[0]
        self.tree = solve(self.case).tree

    def test_rejects_corrupted_leaf_label(self):
        invalid = copy.deepcopy(self.tree)
        invalid["answers"]["red"]["answers"]["0"] = {"target": "1"}
        with self.assertRaisesRegex(ValueError, "unjustified leaf"):
            replay(self.case, invalid)

    def test_rejects_missing_and_unreachable_answer_branches(self):
        invalid = copy.deepcopy(self.tree)
        del invalid["answers"]["gray"]
        with self.assertRaisesRegex(ValueError, "branches"):
            replay(self.case, invalid)
        unexpected = copy.deepcopy(self.tree)
        unexpected["answers"]["green"] = {"target": "0"}
        with self.assertRaisesRegex(ValueError, "branches"):
            replay(self.case, unexpected)

    def test_rejects_unavailable_query(self):
        invalid = {**self.tree, "query": "secret_query"}
        with self.assertRaisesRegex(ValueError, "unavailable"):
            replay(self.case, invalid)

    def test_rejects_repeated_query(self):
        invalid = copy.deepcopy(self.tree)
        invalid["answers"]["red"] = {"query": "route", "answers": {"red": {"target": "0"}}}
        with self.assertRaisesRegex(ValueError, "repeated"):
            replay(self.case, invalid)

    def test_rejects_hidden_completion_selection(self):
        with self.assertRaisesRegex(ValueError, "completion-dependent"):
            replay(self.case, {"by_completion": {row.identity: {"target": row.target} for row in self.case.rows}})

    def test_rejects_mixed_certification_and_premature_abstention(self):
        with self.assertRaisesRegex(ValueError, "unjustified"):
            replay(self.case, {"target": self.case.rows[0].target})
        with self.assertRaisesRegex(ValueError, "abstention"):
            replay(self.case, {"abstain": True})

    def test_all_baselines_use_only_allowed_answers(self):
        for name, seed in (("partition", None), ("edge_cut", None), ("random", 405011)):
            tree = greedy_policy(self.case, name, seed)
            self.assertEqual(measure(replay(self.case, tree))["certified"], len(self.case.rows))
            if name == "random":
                self.assertEqual(tree, greedy_policy(self.case, name, seed))


if __name__ == "__main__":
    unittest.main()
