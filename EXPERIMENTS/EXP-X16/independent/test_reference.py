import json
from collections import defaultdict
from itertools import product
from pathlib import Path
import unittest

from reference import (
    StaticQuery,
    abstract_profile,
    command_row,
    enumerate_paths,
    initial_receipt,
    receipt_key,
    solve_adaptive,
    solve_catalogue,
    solve_online,
    solve_static,
)


class ReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "cases" / "catalogue.json"
        cls.catalogue = json.loads(path.read_text(encoding="utf-8"))
        cls.profiles = {row["id"]: row for row in cls.catalogue["profiles"]}
        cls.result = solve_catalogue(cls.catalogue)

    def measures(self, name, comparison):
        report = self.result["profiles"][name][comparison]
        return tuple(report[goal]["worst_paid"] for goal in ("target", "identity"))

    def test_real_paths_exclude_crossed_lanes(self):
        paths = enumerate_paths(self.profiles["feedback-live"])
        self.assertEqual([path.ids for path in paths], [
            ("start-left", "middle-left", "route-left"),
            ("start-right", "middle-right", "route-right"),
        ])
        self.assertEqual([(path.remaining[0], path.verdict) for path in paths], [(4, "YES")] * 2)
        counterfactual = self.result["abstract_controls"]["cartesian-relaxation"]
        self.assertEqual(len(counterfactual["paths"]), 8)
        self.assertEqual(sum(row["target"] == "NO" for row in counterfactual["paths"]), 2)
        self.assertEqual(counterfactual["static"]["target"]["worst_paid"], 2)
        self.assertEqual(self.measures("feedback-live", "static"), (0, 1))
        self.assertEqual(self.measures("feedback-live", "online"), (0, 0))
        self.assertEqual(self.measures("feedback-live", "fixed_schedule"), (None, None))
        self.assertEqual(self.measures("feedback-suppressed", "online"), (None, None))

    def test_meter_support_and_horizon(self):
        self.assertEqual(self.measures("meter-h3", "online"), (3, 3))
        self.assertEqual(self.measures("meter-h4", "online"), (2, 2))
        self.assertEqual(self.measures("meter-h4", "fixed_schedule"), (3, 3))
        action = self.result["profiles"]["meter-h4"]["online"]["target"]["policy_by_initial"][
            "start|WORK"
        ]
        self.assertEqual(set(action["next"]), {"filed|SHORT", "filed|LONG"})
        self.assertEqual(action["next"]["filed|SHORT"]["act"], "ask.flag")
        self.assertEqual(action["next"]["filed|LONG"]["act"], "ask.prepare")
        incomplete_support = self.result["abstract_controls"]["missing-long-support"]
        self.assertEqual(incomplete_support["online"]["target"]["worst_paid"], 1)

    def test_deadline_defines_intrinsic_target_separately(self):
        profile = dict(self.profiles["intrinsic-gap"], horizon=2)
        paths = enumerate_paths(profile)
        self.assertEqual([(path.remaining[0], path.verdict) for path in paths], [(3, "YES"), (5, "NO")])
        self.assertIsNone(solve_online(profile, paths)["worst_paid"])
        self.assertEqual(self.measures("intrinsic-gap", "online"), (1, 1))

    def test_gateway_target_and_identity_use_same_panels_and_work(self):
        for size in (2, 4, 6):
            name = f"gateway-{size}"
            with self.subTest(name=name):
                for comparison in ("static", "adaptive", "online"):
                    self.assertEqual(self.measures(name, comparison), (1, size + 1))
                self.assertEqual(self.result["profiles"][name]["all_queries_paid"], 4 * (size + 1))

    def test_weighted_pure_adaptivity_can_improve_on_every_fixed_subset(self):
        worlds = tuple(product((0, 1), repeat=3))
        panel = tuple(
            StaticQuery(name, 1, tuple(str(world[index]) for world in worlds))
            for index, name in enumerate(("selector", "left", "right"))
        )
        values = tuple(world[2] if world[0] else world[1] for world in worlds)
        self.assertEqual(solve_static(panel, values)["worst_paid"], 3)
        adaptive = solve_adaptive(panel, values)
        self.assertEqual(adaptive["worst_paid"], 2)
        self.assertEqual(adaptive["tree"]["query"], "selector")
        self.assertIsNone(solve_static((), values)["worst_paid"])
        self.assertIsNone(solve_adaptive((), values)["worst_paid"])

    def test_scope_controls_change_specific_capabilities(self):
        split = self.profiles["split-calls"]
        for path in enumerate_paths(split):
            self.assertEqual(
                set(command_row(split, path, 0, "WORK")),
                {path.fastest_job_actions[0], "job.slow"},
            )
        self.assertEqual(self.measures("split-calls", "online"), (None, None))
        free = self.result["profiles"]["free-guard"]["online"]["target"]
        self.assertEqual(free["worst_paid"], 0)
        self.assertEqual(free["policy_by_initial"]["stale|WORK"], {"verdict": "NO"})

        carry = self.profiles["hidden-carry"]
        same_edge = [path for path in enumerate_paths(carry) if path.ids[1] == "late-fresh"]
        rows = [command_row(carry, path, 1, "WORK")["ask.flag"] for path in same_edge]
        self.assertEqual(rows[0].outcomes, rows[1].outcomes)
        self.assertEqual([row.paid for row in rows], [1, 5])
        self.assertEqual(self.measures("hidden-carry", "online"), (5, None))
        self.assertEqual(self.measures("changed-instrument", "online"), (None, None))

    def test_freeze_disallows_fast_if_only_last_raw_branch_changes_r(self):
        profile = abstract_profile(self.profiles["meter-h3"], "missing-long-support")
        profile["stages"][0]["edges"][0]["stale"] = 1
        profile["stages"][0]["edges"][0]["gives"].append({"obs": "filed", "meter": "LONG"})
        path = enumerate_paths(profile)[0]
        row = command_row(profile, path, 0, "WORK")
        self.assertEqual(row["job.fast"].outcomes, (
            ("filed", "SHORT", False), ("filed", "LONG", True),
        ))
        self.assertFalse(row["job.fast"].allowed)
        self.assertTrue(row["job.slow"].allowed)

    def test_returned_policies_cover_each_installed_path_and_receipt(self):
        rows = [
            (self.profiles[name], result)
            for name, result in self.result["profiles"].items()
        ]
        rows.extend(
            (abstract_profile(self.profiles[result["profile"]], control), result)
            for control, result in self.result["abstract_controls"].items()
        )
        for profile, report in rows:
            for comparison in ("online", "fixed_schedule"):
                for goal, result in report.get(comparison, {}).items():
                    if result["worst_paid"] is None:
                        continue
                    with self.subTest(profile=profile["id"], comparison=comparison, goal=goal):
                        self.check_policy(profile, goal, result)

    def check_policy(self, profile, goal, result):
        stops = defaultdict(set)
        terminal_prices = []
        acts_by_move = defaultdict(set)

        for path in enumerate_paths(profile):
            initial = initial_receipt(profile, path)
            root = receipt_key(initial["obs"], initial["meter"])
            policy = result["policy_by_initial"][root]

            def walk(node, stage, meter, work, paid, history):
                if "verdict" in node:
                    self.assertEqual(node["verdict"], path.verdict)
                    if node["verdict"] == "YES":
                        self.assertEqual(stage, len(profile["stages"]))
                        if profile["variant"] == "changed-instrument":
                            self.assertFalse(any(act == "ask.flag" for act, _ in history))
                    stops[(root, history)].add(path.ids)
                    terminal_prices.append(paid)
                    return

                self.assertLess(len(history), profile["horizon"])
                act = node["act"]
                acts_by_move[len(history)].add(act)
                command = command_row(profile, path, stage, meter)[act]
                self.assertTrue(command.allowed)
                next_work = work + command.work
                self.assertLessEqual(next_work, profile["deadline"])
                for obs, next_meter, _ in command.outcomes:
                    branch = receipt_key(obs, next_meter)
                    walk(
                        node["next"][branch], stage + (command.kind == "job"), next_meter,
                        next_work, paid + command.paid, (*history, (act, branch)),
                    )

            walk(policy, 0, initial["meter"], 0, 0, ())

        self.assertEqual(max(terminal_prices), result["worst_paid"])
        if goal == "identity":
            self.assertTrue(all(len(identities) == 1 for identities in stops.values()))
        if "schedule" in result:
            self.assertEqual(
                [acts_by_move[index] for index in range(len(acts_by_move))],
                [{act} for act in result["schedule"]],
            )


if __name__ == "__main__":
    unittest.main()
