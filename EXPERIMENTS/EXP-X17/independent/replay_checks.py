"""Verify all independently archived X17 attempt indices and preserve routed examples."""

import argparse
from collections import Counter
from fractions import Fraction as F
import gzip
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import sqlite3
import sys

from evidence import Evidence, decoded
from model import ARMS, Installation
from run import file_digest


def verify(directory, roster):
    s = json.loads((directory / "independent-summary.json").read_bytes())
    db = directory / "independent.sqlite"
    raw = directory / "independent-index.ndjson.gz"
    assert file_digest(db) == s["raw_db_sha256"] and file_digest(raw) == s["raw_index_sha256"]
    worlds = {world.id: world for world in map(Installation.from_row, roster["worlds"])}
    summaries = {(c["id"], c["arm"]): c for c in s["cells"]}
    diagnostics = {d["id"]: d for d in s["diagnostics"]}
    retained = {}
    with gzip.open(raw, "rt", encoding="ascii") as stream, Evidence(db) as evidence:
        entries = map(json.loads, stream)

        def compare(row, source):
            for name in ("source_digest", "intake_digest", "final_digest", "trace_sha256"):
                assert row.get(name) == source[name]

        def preserve(key, world, name, row):
            decoded_score = decoded(evidence, row, world)
            installation = row["trace"]["installation_digest"]
            artifact_hashes = {"installation": installation, "source": row["source_digest"],
                               "intake": row["intake_digest"], "final": row["final_digest"]}
            retained[key] = {"id": name, "mechanism": row["mechanism"], "artifact_hashes": artifact_hashes,
                             "artifacts": {label: evidence.artifact(value) if value else None
                                           for label, value in artifact_hashes.items()},
                             "trace": row["trace"], "trace_sha256": row["trace_sha256"],
                             "decoded": {k: str(v) if isinstance(v, F) else v for k, v in decoded_score.items()}}

        for label, world in worlds.items():
            for arm in ARMS:
                sums = Counter()
                for attempt in range(s["planned_per_cell"]):
                    record = next(entries)
                    expected = f"{label}-{arm}-{attempt:05}"
                    assert record["id"] == expected and "invalid" not in record
                    row = evidence.attempt(expected)
                    compare(record, row)
                    outcomes = {k: F(v) for k, v in record["outcome"].items()}
                    sums.update({k: outcomes[k] for k in ("I", "V", "VI", "wrong")})
                    sums.update(G_halves=2 * outcomes["G"], cost_eighths=8 * outcomes["cost"],
                                Z_eighths=8 * outcomes["Z"])
                    assert record["logical_moves"] == world.N + 3 + outcomes["I"]
                    if label == "s01" and arm == "pcx":
                        class_name = ("useful_positive" if outcomes["G"] == 1 else
                                      "violating_positive" if outcomes["V"] else "negative_with_useful_intake")
                        if class_name not in retained:
                            preserve(class_name, world, expected, row)
                assert sums == summaries[label, arm]["counts"]
                assert summaries[label, arm]["valid"] == s["planned_per_cell"]
            ordinary_bad = 0
            for n in range(diagnostics[label]["ordinary_count"]):
                entry = next(entries)
                attempt = f"{label}-ordinary-{n:03}"
                assert entry["id"] == attempt and entry["kind"] == "ordinary"
                row = evidence.attempt(attempt)
                assert entry["trace_sha256"] == row["trace_sha256"] and entry["final_digest"] == row["final_digest"]
                assert entry["V"] == decoded(evidence, row, world)["V"]
                ordinary_bad += entry["V"]
                if "ordinary_reference" not in retained:
                    preserve("ordinary_reference", world, attempt, row)
            assert ordinary_bad == diagnostics[label]["ordinary_violation"]
            paired_issue = paired_difference = strip = 0
            for n in range(diagnostics[label]["paired_count"]):
                entry = next(entries)
                attempt = f"{label}-paired-{n:03}"
                assert entry["id"] == attempt and entry["kind"] == "paired"
                paired_issue += entry["I"]
                actual, nominal = (evidence.attempt(attempt + "-" + side) for side in ("actual", "nominal"))
                for side, row in (("actual", actual), ("nominal", nominal)):
                    assert row["trace_sha256"] == entry[side + "_trace"] and row["final_digest"] == entry[side + "_final"]
                    assert decoded(evidence, row, world)["V"] == entry[side + "_V"]
                strip += entry["in_strip"]
                paired_difference += entry["actual_V"] - entry["nominal_V"]
                if entry["in_strip"] and "strip_actual" not in retained:
                    preserve("strip_actual", world, attempt + "-actual", actual)
                    preserve("strip_nominal", world, attempt + "-nominal", nominal)
            d = diagnostics[label]
            assert (paired_issue, paired_difference, strip) == (d["paired_issued"], d["paired_disagreement"], d["strip_count"])
        assert next(entries, None) is None
        native_count = evidence.connection.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        artifact_count = evidence.connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0]
    assert set(summaries) == set(product(worlds, ARMS)) and len(s["cells"]) == len(summaries)
    main = sum(c["planned"] for c in s["cells"])
    ordinary = sum(d["ordinary_count"] for d in s["diagnostics"])
    pairs = sum(d["paired_count"] for d in s["diagnostics"])
    invalid = sum(c["invalid"] for c in s["cells"])
    assert (main, ordinary, pairs, invalid, native_count) == (163840, 512, 1024, 0, 166400)
    assert len(retained) == 6
    return {"schema": 1, "role": "independent", "main_attempts": main, "main_invalid": invalid,
            "ordinary": ordinary, "pairs": pairs, "index_rows_checked": main + ordinary + pairs,
            "sqlite_native_attempts_checked": native_count, "sqlite_artifacts": artifact_count,
            "matched_strip": sum(d["strip_count"] for d in s["diagnostics"]),
            "raw_index_sha256": s["raw_index_sha256"], "raw_index_bytes": raw.stat().st_size,
            "raw_db_sha256": s["raw_db_sha256"], "raw_db_bytes": db.stat().st_size,
            "source_commit": s["auth_inputs"]["source_commit"], "authorization_sha256": s["auth_inputs"]["authorization_sha256"],
            "python": sys.version, "sqlite": sqlite3.sqlite_version, "illustrative_material_records": retained}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("opening", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = verify(args.run, json.loads(args.opening.read_bytes()))
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(f"Validated {report['index_rows_checked']} index rows against {report['sqlite_native_attempts_checked']} native originals.")


if __name__ == "__main__":
    main()
