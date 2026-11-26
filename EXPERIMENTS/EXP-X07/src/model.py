"""Finite completion proof and independent X03 cross-check."""

from importlib import import_module
from itertools import combinations
from pathlib import Path
from types import ModuleType
import sys

from .records import file_digest, require


def compatible(spec, answers):
    return [
        row for row in spec["completions"]
        if all(type(value) is bool and row[query] == value for query, value in answers.items())
    ]


def conclusion(spec, answers):
    rows = compatible(spec, answers)
    targets = sorted({row["target"] for row in rows})
    return {
        "decision": targets[0] if len(targets) == 1 else "ABSTAIN",
        "status": {0: "INCONSISTENT", 1: "IDENTIFIED", 2: "UNDERIDENTIFIED"}[len(targets)],
        "compatible": [row["id"] for row in rows],
        "target_set": targets,
    }


def conflict(spec, probes, actual=None):
    rows = spec["completions"]
    pairs = combinations(rows, 2) if actual is None else ((actual, row) for row in rows)
    for left, right in pairs:
        if left["target"] != right["target"] and all(left[q] == right[q] for q in probes):
            return [left["id"], right["id"]]
    return None


def minimum(spec, actual=None):
    costs = {query: details["cost"] for query, details in spec["queries"].items()}
    tested = []
    for size in range(len(costs) + 1):
        for probes in combinations(costs, size):
            tested.append((sum(costs[q] for q in probes), probes, conflict(spec, probes, actual)))
    optimum = min(price for price, _, witness in tested if witness is None)
    return {
        "cost": optimum,
        "optima": [list(probes) for price, probes, witness in tested if price == optimum and witness is None],
        "subsets": [
            {"queries": list(probes), "cost": price, "conflict": witness}
            for price, probes, witness in tested
        ],
    }


def local_proof(spec):
    global_optimum = minimum(spec)
    selected, = global_optimum["optima"]
    return {
        "initial_witness": conflict(spec, ()),
        "uniform": global_optimum,
        "realized": {row["id"]: minimum(spec, row) for row in spec["completions"]},
        "selected": selected,
    }


def validate_x03(spec, source):
    """Load two source blobs by content hash to keep archive replay independent of Git."""
    source = Path(source).resolve() / "src"
    pin = spec["x03"]
    for filename, sha in pin["source_sha256"].items():
        require(file_digest(source / filename) == sha, f"X03 source digest differs: {filename}")

    package = ModuleType("_pcx_x07_pinned_x03")
    package.__path__ = [str(source)]
    sys.modules[package.__name__] = package
    try:
        exact = import_module(f"{package.__name__}.certificates")
        reference = import_module(f"{package.__name__}.reference")
        keys = tuple(spec["queries"])
        problem = exact.Problem(
            spec["id"], keys, tuple(spec["queries"][key]["cost"] for key in keys),
            tuple(exact.Completion(row["id"], tuple(str(row[key]) for key in keys), row["target"])
                  for row in spec["completions"]),
        )
        proof = local_proof(spec)
        for profile in [None, *proof["realized"]]:
            local = proof["uniform"] if profile is None else proof["realized"][profile]
            solved = exact.solve(problem, profile)
            partition = reference.exact_by_partition(problem, profile)
            require(reference.verify_proof(problem, solved, profile), f"X03 rejected proof: {profile}")
            require(solved.status == "CERTIFIED" and solved.cost == local["cost"], f"X03 cost differs: {profile}")
            require(
                [list(keys[i] for i in candidate) for candidate in partition.optima] == local["optima"],
                f"X03 candidate suites differ: {profile}",
            )
        witness = tuple(proof["initial_witness"])
        require(reference.verify_witness(problem, witness, ()), "X03 rejected initial ambiguity witness")
    finally:
        for module in (package.__name__, f"{package.__name__}.certificates", f"{package.__name__}.reference"):
            sys.modules.pop(module, None)
    return {"x03": pin, "agreement": True, **proof}
