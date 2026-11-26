"""Check the registered optima and intrinsic path roster against the independent solver."""

import argparse
from pathlib import Path

from evidence import read_json, require
from planner import dump


METRICS = {
    "static_target": ("static", "target", "worst_paid"),
    "static_identity": ("static", "identity", "worst_paid"),
    "static_all": ("all_queries_paid",),
    "adaptive_pure_target": ("adaptive", "target", "worst_paid"),
    "adaptive_pure_identity": ("adaptive", "identity", "worst_paid"),
    "online": ("online", "target", "worst_paid"),
    "online_identity": ("online", "identity", "worst_paid"),
    "online_fixed": ("fixed_schedule", "target", "worst_paid"),
    "structured_scores": ("online", "target", "worst_paid"),
}


def compare(catalogue, expected, explicit):
    profiles = {}
    for name in catalogue["valid_profiles"]:
        preregistered = expected["profiles"][name]
        reference = explicit["profiles"][name]
        a = {tuple(row["path"]): (row["known_work"], row["label"])
             for row in preregistered["targets"]}
        b = {tuple(row["edges"]): (row["intrinsic_cost"], row["target"])
             for row in reference["paths"]}
        require(a == b, f"independent intrinsic verdict or cost differs on {name}")
        values = {}
        for treatment, keys in METRICS.items():
            expected_value = preregistered[treatment]
            if expected_value is None:
                continue
            actual = reference
            for label in keys:
                actual = actual[label]
            require(actual == expected_value["value"], f"{name}/{treatment}: independent optimum differs")
            values[treatment] = actual
        profiles[name] = {"paths": len(a), "matching_optima": values}
    return {"schema": 1, "source_commit": expected["source_commit"], "profiles": profiles,
            "path_total": sum(row["paths"] for row in profiles.values()),
            "optimum_total": sum(len(row["matching_optima"]) for row in profiles.values())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("catalogue", "forecast", "independent_reference", "out"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    result = compare(read_json(args.catalogue), read_json(args.forecast), read_json(args.independent_reference))
    dump(args.out, result)
    print(f"Matched {result['path_total']} independent path targets and {result['optimum_total']} comparator values.")


if __name__ == "__main__":
    main()
