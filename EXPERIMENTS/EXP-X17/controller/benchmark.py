"""Measure genuine X17 compilation and exact certificate checks, without native trials."""

import argparse
import gc
import json
import platform
import tracemalloc
from fractions import Fraction as F
from math import comb
from time import perf_counter_ns

from .factor_flow import (World, arm_distribution, build_count_graph,
                          build_explicit_groups, evaluate, world_weights)
from .optimize import optimize


def timed_and_measured(operation):
    """One timed invocation plus a separate invocation for Python peak allocations."""
    gc.collect()
    start = perf_counter_ns()
    result = operation()
    elapsed = perf_counter_ns() - start
    gc.collect()
    tracemalloc.start()
    try:
        operation()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result, {"elapsed_ns": elapsed, "peak_traced_bytes": peak}


def encode_world(world):
    return {"theta": str(world.theta), "beta": str(world.beta),
            "tag": world.tag, "route": world.route}


def summarize(optimum):
    grid = optimum["net"]
    return {
        "subdivisions_per_stratum": grid.subdivisions,
        "grid_worlds": len(grid.points) * 4,
        "radius": str(grid.radius),
        "modulus": str(grid.modulus),
        "alpha": str(grid.alpha),
        **{key: str(optimum[key]) for key in
           ("lower", "upper", "tightened_actual_policy_cost", "tightened_high")},
        "column_slacks": [str(z) for z in optimum["column_slacks"]],
        "lower_maxima": {k: str(v) for k, v in optimum["lower_extrema"].items()},
        "lower_argmax": {k: encode_world(w) for k, w in optimum["lower_worlds"].items()},
        "tightened_maxima": {k: str(v) for k, v in optimum["tightened_extrema"].items()},
        "tightened_argmax": {k: encode_world(w) for k, w in optimum["tightened_worlds"].items()},
    }


def run(depths: tuple[int, ...], large: tuple[int, ...]) -> dict[str, object]:
    rows = []
    for depth in depths:
        count, count_compile = timed_and_measured(lambda: build_count_graph(depth))
        full, explicit_compile = timed_and_measured(lambda: build_explicit_groups(depth))
        count_opt, count_time = timed_and_measured(lambda: optimize(depth, count.groups))
        explicit_opt, explicit_time = timed_and_measured(lambda: optimize(depth, full))
        assert count_opt == explicit_opt
        rows.append({
            "N": depth,
            "count_prefix_nodes": len(count.nodes),
            "count_prefix_arcs": sum(len(node.children) for node in count.nodes),
            "explicit_prefix_nodes_per_route": 2 ** (depth + 1) - 1,
            "count_terminal_route_groups": len(count.groups),
            "explicit_terminal_route_records": len(full),
            "count_compile": count_compile,
            "explicit_compile": explicit_compile,
            "count_finite_grid_solve_and_check": count_time,
            "explicit_finite_grid_solve_and_check": explicit_time,
            "optimality_certificate": summarize(count_opt),
        })

    large_rows = []
    for depth in large:
        graph, compile_time = timed_and_measured(lambda: build_count_graph(depth))
        world = World(F(33, 256), F(3, 512), 1, "L")
        strategies = (arm_distribution("pcx"),) * len(graph.groups)
        values, evaluation = timed_and_measured(
            lambda: evaluate(depth, graph.groups, strategies, world)
        )
        weights = world_weights(depth, world)
        max_weight_bits = max(max(v.numerator.bit_length(), v.denominator.bit_length())
                              for v in weights)
        assert graph.nodes[-1].seed_flow == 1
        assert max(group.multiplicity for group in graph.groups) == comb(depth, depth // 2)
        record = {
            "N": depth,
            "count_prefix_nodes": len(graph.nodes),
            "count_prefix_arcs": sum(len(node.children) for node in graph.nodes),
            "count_terminal_route_groups": len(graph.groups),
            "supported_full_words_per_route_exact": str(2**depth),
            "count_compile": compile_time,
            "single_world_exact_count_evaluation": evaluation,
            "max_exact_per_history_weight_bits": max_weight_bits,
            "single_world_cost": str(values["cost"]),
            "explicit_run": None,
        }
        large_rows.append(record)
    return {
        "runtime": {"python": platform.python_version(), "machine": platform.machine(),
                    "system": platform.system(), "logical_counters": "Python tracemalloc",
                    "method": "one wall time and a second invocation for traced peak"},
        "small_measured_optimization": rows,
        "large_measured_counted_only": large_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--small", type=int, nargs="+", default=[1, 3, 5, 6])
    parser.add_argument("--large", type=int, nargs="+", default=[16, 32, 64, 128, 256])
    args = parser.parse_args()
    print(json.dumps(run(tuple(args.small), tuple(args.large)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
