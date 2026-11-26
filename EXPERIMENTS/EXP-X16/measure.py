"""Same-host raw timing and Python allocation comparisons for fixed X16 inputs."""

from pathlib import Path
import platform
import subprocess
from time import perf_counter_ns
import tracemalloc

from planner import Frontier


def timed(phase, callback, repetition):
    tracemalloc.start()
    start = perf_counter_ns()
    result = callback()
    elapsed = perf_counter_ns() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"phase": phase, "repeat": repetition, "elapsed_ns": elapsed,
            "python_traced_peak_bytes": peak}, result


def compare(profiles):
    import sys
    referee = sys.modules.get("x16_referee")
    if referee is None:
        import importlib.util
        path = Path(__file__).with_name("independent") / "reference.py"
        spec = importlib.util.spec_from_file_location("x16_referee", path)
        referee = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = referee
        start = perf_counter_ns()
        spec.loader.exec_module(referee)
        import_ns = perf_counter_ns() - start
    else:
        import_ns = None
    samples = []
    for profile in profiles:
        for repetition in range(1, 4):
            formats = [("frontier_extrema", False), ("frontier_full_scores", True)]
            if repetition % 2 == 0:
                formats.reverse()
            for name, full in formats:
                compiled, graph = timed(name + ":source_compile", lambda: Frontier(profile, full), repetition)
                solved, optimum = timed(name + ":online_solve", graph.solve, repetition)
                solved.update({"value": optimum["value"], "states": optimum["states"]})
                samples.extend({"profile": profile["id"], **row} for row in (compiled, solved))
            prepared, paths = timed("explicit:enumerate_paths", lambda: referee.enumerate_paths(profile), repetition)
            solved, optimum = timed("explicit:online_solve", lambda: referee.solve_online(profile, paths), repetition)
            solved.update({"value": optimum["worst_paid"], "states": optimum["histories"],
                           "action_trials": optimum["action_trials"]})
            samples.extend({"profile": profile["id"], **row} for row in (prepared, solved))
    return {
        "python": platform.python_version(),
        "node": subprocess.check_output(["node", "--version"], text=True).strip(),
        "os": platform.system(),
        "clock": "perf_counter_ns",
        "memory": "tracemalloc, peak Python allocations within each separate invocation",
        "instrumentation": "Measured with tracing enabled. The native child has separate batch elapsed time.",
        "explicit_import_elapsed_ns": import_ns,
        "samples": samples,
    }
