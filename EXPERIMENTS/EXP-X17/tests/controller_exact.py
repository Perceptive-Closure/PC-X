"""Reproduce X17 policy, exact forecasts, count/lift, and optimizer witnesses."""

from fractions import Fraction as F
from itertools import product
from math import comb
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from controller.factor_flow import (METRICS, PLANS, World, arm_distribution, build_count_graph,
                                    build_explicit_groups, evaluate, group_explicit_choices,
                                    lift_count_choices, pure_vertex)
from controller.forecast import ARM_MIX, forecast
from controller.optimize import build_net, choose_tightened_probe, optimize
from controller.policy import choose_probe, declare


class FixedDraw:
    def __init__(self, *draws):
        self.draws = list(draws)

    def randrange(self, stop):
        selected = self.draws.pop(0)
        assert 0 <= selected < stop
        return selected


def explicit_native_values(theta, beta, tag, N, probabilities):
    """Check a fixed local mixture by enumerating independently decoded true leaves."""
    p_stay = (1 + (-1)**tag * theta * (1 - theta)) / 2
    actual = dict.fromkeys(METRICS, F(0))
    for history in product((0, 1), repeat=N):
        before = 0
        prefix = F(1)
        for bit in history:
            prefix *= p_stay if bit == before else 1 - p_stay
            before = bit
        risk = theta / 4 + beta + F(tag ^ before, 16)
        for plan, plan_mass in zip(PLANS, probabilities):
            if not plan_mass:
                continue
            responses, cost = ((F(1),), F(0))
            if plan.quality != "skip":
                mean = theta if plan.quality == "high" else (1 + 2 * theta) / 4
                responses = (1 - mean, mean)
                cost = F(1) if plan.quality == "high" else F(3, 8)
            for positive, weight in zip(plan.answers, responses):
                for violation, event_mass in (
                    ((False, 1 - risk), (True, risk)) if positive else ((False, F(1)),)
                ):
                    mass = prefix * plan_mass * weight * event_mass
                    true_positive = theta < F(1, 2)
                    work = F(1, 2) + F(positive and true_positive and not violation, 2)
                    vector = (
                        positive, violation, violation and positive, positive != true_positive,
                        work, cost, F(violation and positive) - F(3, 8) * positive,
                    )
                    for key, value in zip(METRICS, vector):
                        actual[key] += mass * value
    return actual


class ControllerChecks(unittest.TestCase):
    def test_all_registered_policies_are_literal_and_exact(self):
        public = (0, 1, 1)
        for route in ("L", "R"):
            receipt = {"route": route, "intake_digest": "opaque", "signature": "opaque"}
            self.assertEqual(
                [choose_probe("pcx", public, receipt, FixedDraw(i)) for i in range(3)],
                [f"low:{route}", f"low:{route}", f"high:{route}"],
            )
            self.assertEqual(
                [choose_probe("high_skip", public, receipt, FixedDraw(i)) for i in range(3)],
                [f"high:{route}", f"high:{route}", f"skip:{route}"],
            )
            for arm, quality in (("always_high", "high"), ("low_only", "low"), ("no_paid", "skip")):
                self.assertEqual(choose_probe(arm, public, receipt, FixedDraw()),
                                 f"{quality}:{route}")
            self.assertTrue(declare("pcx", public, receipt, f"low:{route}", 0, FixedDraw()))
            self.assertFalse(declare("pcx", public, receipt, f"high:{route}", 1, FixedDraw()))
            self.assertEqual(
                [declare("no_paid", public, receipt, f"skip:{route}", None, FixedDraw(i))
                 for i in range(2)],
                [True, False],
            )
        with self.assertRaises(ValueError):
            choose_probe("pcx", (), {}, FixedDraw(0))
        with self.assertRaises(ValueError):
            declare("low_only", (), {"route": "L"}, "low:R", 0, FixedDraw())
        with self.assertRaises(ValueError):
            declare("no_paid", (), {"route": "L"}, "skip:L", 0, FixedDraw())

    def test_forecasts_match_true_leaf_enumeration(self):
        self.assertEqual(len(PLANS), 10)
        for theta, beta, tag, route in (
            (F(33, 256), F(3, 512), 0, "L"),
            (F(3, 4), F(1, 32), 1, "R"),
        ):
            for arm in ARM_MIX:
                with self.subTest(arm=arm, theta=theta, tag=tag):
                    predictions = forecast(theta, beta, tag, 4, arm)
                    self.assertEqual(predictions, explicit_native_values(
                        theta, beta, tag, 4, arm_distribution(arm)
                    ))
                    nominal = forecast(theta, 0, tag, 4, arm)
                    self.assertEqual(predictions["VI"] - nominal["VI"], beta * predictions["I"])

    def test_full_performance_group_and_lift(self):
        N = 5
        compact = build_count_graph(N)
        explicit = build_explicit_groups(N)
        for node in compact.nodes:
            self.assertEqual(node.seed_flow, comb(node.depth, node.stays))
            self.assertEqual(node.public_bit, (node.depth - node.stays) % 2)
            if node.children:
                self.assertEqual(len(node.children), 2)
                for letter, index in node.children:
                    child = compact.nodes[index]
                    self.assertEqual(child.depth, node.depth + 1)
                    self.assertEqual(child.stays, node.stays + (letter == "stay"))
        arbitrary = tuple(
            tuple((2 * a + b) / 3 for a, b in zip(
                pure_vertex(i % len(PLANS)), pure_vertex((3 * i + 1) % len(PLANS))
            ))
            for i in range(len(explicit))
        )
        grouped = group_explicit_choices(explicit, arbitrary, compact.groups)
        lifted = lift_count_choices(compact.groups, grouped, explicit)
        for theta, tag, route in product((F(1, 8), F(1, 4), F(3, 4), F(7, 8)),
                                          (0, 1), ("L", "R")):
            w = World(theta, F(1, 32), tag, route)
            observed = evaluate(N, explicit, arbitrary, w)
            self.assertEqual(observed, evaluate(N, compact.groups, grouped, w))
            self.assertEqual(observed, evaluate(N, explicit, lifted, w))

    def test_exact_mesh_lower_and_tightened_upper(self):
        graph = build_count_graph(2)
        explicit = build_explicit_groups(2)
        bounds = optimize(2, graph.groups)
        self.assertEqual(bounds, optimize(2, explicit))
        self.assertEqual((bounds["lower"], bounds["upper"]), (F(7, 12), F(121, 192)))
        self.assertEqual(bounds["tightened_actual_policy_cost"], F(239, 384))
        self.assertEqual(bounds["tightened_high"], F(19, 48))
        self.assertEqual(bounds["tightened_extrema"]["negative_coverage_all"], -F(61, 256))
        self.assertEqual(build_net(2, 2).alpha, F(1, 256))
        refined = optimize(2, graph.groups, refinement=2)
        self.assertEqual((refined["lower"], refined["upper"]), (F(7, 12), F(233, 384)))
        self.assertEqual(refined["tightened_actual_policy_cost"], F(463, 768))
        choices = [choose_tightened_probe(F(1, 128), {"route": "R"}, FixedDraw(i))
                   for i in range(48)]
        self.assertEqual(choices.count("high:R"), 19)
        self.assertEqual(choices.count("low:R"), 29)

    def test_optional_calibration_projection_and_richer_menu(self):
        hi_only_on_upstream_zero = F(29, 93)
        high_at_endpoint = F(1, 32) + F(31, 32) * hi_only_on_upstream_zero
        self.assertEqual(high_at_endpoint, F(1, 3))
        q_zero = F(5, 8) + hi_only_on_upstream_zero / 8
        self.assertEqual(q_zero, F(247, 372))
        self.assertEqual(F(2, 3) - q_zero, F(1, 372))
        self.assertEqual(1 - F(31, 32)**2, F(63, 1024))
        perfect = F(1, 3)
        self.assertEqual(perfect * F(1, 2), F(1, 6))
        self.assertEqual(perfect + (1 - perfect) / 2, F(2, 3))
        self.assertEqual((1 - perfect) / 2, F(1, 3))


if __name__ == "__main__":
    unittest.main()
