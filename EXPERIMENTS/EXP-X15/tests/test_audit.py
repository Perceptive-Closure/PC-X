"""Regression checks for the independent X15 falsification harness."""

import io
import json
import unittest
from zipfile import ZipFile

from falsify import control_results, radius
from fetch_inputs import archived_files, git_blob, read_manifest
from verify_benchmarks import mark_index, threshold
from verify_deployment import Bench, bench_step, winning_minimum
from verify_exact import finite_horizon_cost, hit_cost, read
from verify_custody import canonical

PIN = "e" * 40


def zip_bytes(root, files):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        for file, data in files.items():
            archive.writestr(f"Perceptive-Closure-PC-X-{root}/{file}", data)
    return buffer.getvalue()


class IntakeTests(unittest.TestCase):
    def test_archive_matches_full_or_abbreviated_root_and_blob_digest(self):
        files = {"EXPERIMENTS/EXP-X01/README.md": b"registered source\n"}
        expected = {file: {"sha": git_blob(data), "size": len(data)} for file, data in files.items()}
        for revision in (PIN, PIN[:7]):
            _, observed = archived_files(zip_bytes(revision, files), PIN, expected)
            self.assertEqual(files, observed)
        with self.assertRaisesRegex(ValueError, "revision"):
            archived_files(zip_bytes("a" * 7, files), PIN, expected)
        with self.assertRaisesRegex(ValueError, "Blob mismatch"):
            archived_files(zip_bytes(PIN, {next(iter(files)): b"changed bytes\n"}), PIN, expected)

    def test_reject_incomplete_archive(self):
        complete = {"one": b"one", "two": b"two"}
        expected = {file: {"sha": git_blob(data), "size": len(data)} for file, data in complete.items()}
        with self.assertRaisesRegex(ValueError, "Incomplete archive"):
            archived_files(zip_bytes(PIN, {"one": b"one"}), PIN, expected)

    def test_all_branch_pins_complete_and_unique(self):
        pins = read_manifest()
        self.assertEqual(set(pins), {f"X{i:02}" for i in range(1, 15)})
        self.assertEqual(len({row["sha"] for row in pins.values()}), 14)


class IndependentLogicTests(unittest.TestCase):
    def test_zero_cost_cycle_requires_a_proper_termination_branch(self):
        model = {
            "targets": ["approved", "denied"], "compatibility": [[0, 1], [0]], "initial": 0,
            "actions": [{"name": "stay", "interface": "run", "cost": 0},
                        {"name": "close", "interface": "run", "cost": 2}],
            "states": [
                {"history": 0, "representation": ["A", "B"], "authority": ["run"], "observation": "a",
                 "candidates": [{"name": "stay", "support": [{"state": 0, "outcome": "stay"}]},
                                {"name": "close", "support": [{"state": 1, "outcome": "done"}]}]},
                {"history": 1, "representation": ["A", "B"], "authority": ["run"], "observation": "b",
                 "candidates": []},
            ],
        }
        self.assertEqual(finite_horizon_cost(model, frozenset()), 2)
        self.assertEqual(finite_horizon_cost(model, frozenset({"E"})), "inf")

    def test_weighted_refinement_requires_legal_coverage(self):
        self.assertEqual(hit_cost([{0, 1}, {1, 2}], [2, 9, 2]), 4)
        self.assertEqual(hit_cost([{0}, {0, 1}, {2}], [2, 9, 2]), 4)
        self.assertIsNone(hit_cost([set()], [2, 9, 2]))

    def test_fixed_denominator_and_threshold_tie(self):
        self.assertTrue(threshold([[0.0, 0.4], [0.2, 0.4]], 0.4))
        self.assertFalse(threshold([[0.41, 0.6], [0.1, 0.4]], 0.4))
        self.assertIsNone(threshold([[0.39, 0.41], [0.1, 0.2]], 0.4))
        self.assertGreater(radius(1024, 4, 0.05), radius(1024, 1, 0.05))
        seen = set()
        mark_index(seen, ("unit", "context"), 0, 1)
        with self.assertRaisesRegex(AssertionError, "duplicate"):
            mark_index(seen, ("unit", "context"), 0, 1)

    def test_bench_authority_and_full_supported_utility(self):
        spec = {
            "profiles": {"left": {"entry": "left", "panel": "indexed", "relief": False},
                         "right": {"entry": "right", "panel": "indexed", "relief": False}},
            "cost": {"layout": 2}, "slips": [0, 1], "jobs": ["first", "second"],
        }
        scope = {"actions": ["left", "right", "refuse", "layout"], "evidence": "two-slots",
                 "horizon": 3, "profiles": ["left", "right"]}
        self.assertEqual(bench_step(spec, Bench("left", False, 0), "plate")[0], "unauthorized")
        self.assertEqual(bench_step(spec, Bench("left", False, 0), "right")[0], "unsafe")
        self.assertEqual(winning_minimum(spec, scope), 2)
        self.assertIsNone(winning_minimum(spec, dict(scope, horizon=2)))

    def test_committed_new_controls_and_distinct_canonical_formats(self):
        results = control_results()
        self.assertFalse(results["extensional_atomic_touch"]["complete_atomic_action_available_when_R_frozen"])
        self.assertEqual(results["nonrectangular_target"]["rectangle_target"], [0, 1])
        self.assertEqual(results["quantifier_order_utility"]["without_admitted_read"], [])
        compact = canonical({"z": True, "a": 2}, "compact")
        self.assertEqual(compact, b'{"a":2,"z":true}')
        self.assertEqual(canonical(json.loads(compact), "line"), compact + b"\n")


if __name__ == "__main__":
    unittest.main()
