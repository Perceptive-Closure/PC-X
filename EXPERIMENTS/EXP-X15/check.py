"""Reconstruct X15 evidence and verify the self-contained terminal inventory."""

import argparse
import json
from pathlib import Path
import re
import sys

from falsify import control_results
from fetch_inputs import PACKAGE, ROOT, SCRATCH, read_manifest, sha256
from replay import source_root
from verify_benchmarks import verify_x06, verify_x08, verify_x09, verify_x10, verify_x11
from verify_certificates import verify_x07
from verify_deployment import verify_x12, verify_x13, verify_x14
from verify_exact import ensure, read, verify_x01, verify_x02, verify_x03, verify_x04, verify_x05
from verify_scalability import verify_matched_grid

RESULTS = PACKAGE / "results"
MANIFEST = RESULTS / "manifest.sha256"
EXPECTED = {f"X{i:02}" for i in range(1, 15)}


def write(path, data):
    path.write_bytes((json.dumps(data, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii"))


def paths():
    return {
        file.relative_to(PACKAGE).as_posix(): sha256(file.read_bytes())
        for file in PACKAGE.rglob("*")
        if file.is_file() and file != MANIFEST and "__pycache__" not in file.parts
    }


def verify_evidence():
    archived = {}
    for line in MANIFEST.read_text("ascii").splitlines():
        digest, relative = line.split("  ", 1)
        ensure(relative not in archived, ("repeated manifest entry", relative))
        archived[relative] = digest
    observed = paths()
    ensure(observed == archived, {
        "missing": sorted(archived.keys() - observed.keys()),
        "unlisted": sorted(observed.keys() - archived.keys()),
        "changed": sorted(name for name in archived.keys() & observed.keys() if archived[name] != observed[name]),
    })
    pins = read_manifest()
    sources = read(RESULTS / "sources.json")
    replays = read(RESULTS / "replays.json")
    independent = read(RESULTS / "independent.json")
    ensure(set(pins) == set(sources) == set(replays) == set(independent) == EXPECTED,
           "Evidence requires all fourteen exact inputs")
    ensure(read(RESULTS / "controls.json") == json.loads(json.dumps(control_results())),
           "Independent falsification controls differ")
    count = 0
    for experiment in sorted(pins):
        revision = pins[experiment]["sha"]
        ensure(revision == sources[experiment]["commit"] == replays[experiment]["commit"],
               (experiment, "input revision"))
        ensure(all(stage["exit_code"] == 0 for stage in replays[experiment]["stages"]),
               (experiment, "published replay did not pass"))
        tests = [stage for stage in replays[experiment]["stages"] if stage["stage"] == "tests"]
        ensure(len(tests) == 1 and tests[0]["test_count"] > 0, (experiment, "test coverage"))
        count += tests[0]["test_count"]
        ensure(all(isinstance(value, str) and len(value) == 64
                   for value in replays[experiment]["additional_byte_matches"].values()),
               (experiment, "byte readback mismatch"))
    stages = read(RESULTS / "custody.json")["original_stages"]
    ensure(set(stages) == {f"X{i:02}" for i in range(6, 15)}, "Missing original custody stage record")
    ensure(all(stages[id_]["terminal_commit"] == pins[id_]["sha"] for id_ in stages), "Custody input pin mismatch")
    print(f"Verified {len(observed)} files, {len(pins)} input commits, {count} passing predecessor tests, and "
          f"{len(control_results())} independent control groups.")


def verify_pinned_sources(pins):
    receipts = {}
    for experiment, pin in pins.items():
        source = source_root(pin)
        receipt = read(source.parent / "receipt.json")
        package = source / "EXPERIMENTS" / f"EXP-{experiment}"
        ensure(receipt["commit"] == pin["sha"] and sha256(
            (source.parent / "source.zip").read_bytes()
        ) == receipt["archive_sha256"], (experiment, "intake archive changed"))
        for relative, digest in receipt["package_file_sha256"].items():
            ensure(sha256((package / relative).read_bytes()) == digest,
                   (experiment, relative, "authenticated source changed"))
        receipts[experiment] = receipt
    return receipts


def reconstruct(label, pins):
    packages = {id_: source_root(pin) / "EXPERIMENTS" / f"EXP-{id_}" for id_, pin in pins.items()}
    run = SCRATCH / "runs" / label
    independent = SCRATCH / "independent" / label
    independent.mkdir(parents=True, exist_ok=True)
    operations = {
        "X01": (verify_x01, run / "X01", independent),
        "X02": (verify_x02, run / "X02"),
        "X03": (verify_x03, independent),
        "X04": (verify_x04,),
        "X05": (verify_x05,),
        "X06": (verify_x06,),
        "X07": (verify_x07,),
        "X08": (verify_x08, run / "X08"),
        "X09": (verify_x09,),
        "X10": (verify_x10,),
        "X11": (verify_x11,),
        "X12": (verify_x12,),
        "X13": (verify_x13,),
        "X14": (verify_x14,),
    }
    evidence = {}
    for experiment, (verify, *arguments) in sorted(operations.items()):
        evidence[experiment] = verify(packages[experiment], *arguments)
        if experiment == "X05":
            evidence[experiment]["matched_grid"] = verify_matched_grid(packages[experiment], independent)
        print(f"{experiment}: independent reconstruction agrees", flush=True)
    verify_pinned_sources(pins)
    return evidence


def portable_record(record):
    roots = ((str(ROOT), "{audit_checkout}"), (str(Path.home()), "{home}"), (sys.base_prefix, "{python}"))
    for stage in record["stages"]:
        for field in ("transcript_tail", "argv"):
            safe = []
            for value in stage[field]:
                for local, name in roots:
                    value = value.replace(local, name).replace(local.replace("\\", "/"), name)
                safe.append(value)
            stage[field] = safe
    return record


def collect(label, timings_label):
    pins = read_manifest()
    ensure(set(pins) == EXPECTED, "Missing terminal inputs")
    findings = reconstruct(label, pins)
    RESULTS.mkdir(exist_ok=True)
    write(RESULTS / "independent.json", findings)
    write(RESULTS / "controls.json", control_results())
    write(RESULTS / "sources.json", {id_: read(source_root(pin).parent / "receipt.json") for id_, pin in pins.items()})
    run = SCRATCH / "runs" / label
    write(RESULTS / "replays.json", {id_: portable_record(read(run / id_ / "replay.json")) for id_ in sorted(pins)})
    write(RESULTS / "custody.json", read(SCRATCH / "custody.json"))
    timing_evidence = source_root(pins["X05"]) / "scratch" / "x15-replay" / timings_label
    for name in ("measurements.csv", "performance.json"):
        (RESULTS / f"x05-fresh-{name}").write_bytes((timing_evidence / name).read_bytes())
    receipt = SCRATCH / "runs" / timings_label / "X05" / "replay.json"
    write(RESULTS / "x05-fresh-replay.json", portable_record(read(receipt)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--evidence", action="store_true", help="verify the offline terminal evidence, code and pins")
    mode.add_argument("--collect", action="store_true", help="write a terminal evidence bundle from complete replay")
    mode.add_argument("--seal", action="store_true", help="write the terminal SHA-256 inventory")
    mode.add_argument("--reconstruct", action="store_true", help="rerun independent checks against populated scratch")
    parser.add_argument("--label", default="verified", help="published replay run label")
    parser.add_argument("--timings-label", default="fresh-timings", help="fresh X05 resource run label")
    options = parser.parse_args()
    if not all(re.fullmatch(r"[a-z0-9][a-z0-9-]*", name)
               for name in (options.label, options.timings_label)):
        parser.error("Run labels must be alphanumeric or hyphenated")
    if options.evidence:
        verify_evidence()
    elif options.reconstruct:
        actual = reconstruct(options.label, read_manifest())
        expected = read(RESULTS / "independent.json")
        ensure(json.loads(json.dumps(actual)) == expected, "Independent reconstruction changed")
    elif options.collect:
        collect(options.label, options.timings_label)
    else:
        text = "".join(f"{digest}  {name}\n" for name, digest in sorted(paths().items()))
        MANIFEST.write_bytes(text.encode("ascii"))


if __name__ == "__main__":
    main()
