"""Run published tests and exact replay in independent, scoped GitHub snapshots."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from time import perf_counter

from fetch_inputs import ROOT, SCRATCH, read_manifest, sha256

PYTHON = [sys.executable, "-B"]
GIT = ["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential"]
OPA_HASH = "4cd179b95041aa50c44241324da3becf35d0b28dca92bf10a07f32d002724d5e"
OPENSSL_ASSET = Path("C:/Program Files/Git/usr/bin/openssl.exe")
OPENSSL_HASH = "e7c10875d990b320a6000653b3a8c12f5aa06442c1937a246d2daeb342b7c9c5"


def source_root(pin):
    return SCRATCH / "inputs" / pin["experiment"] / pin["sha"] / "source"


def verify_equal(generated, committed):
    observed = sha256(generated.read_bytes())
    expected = sha256(committed.read_bytes())
    if expected != observed:
        raise ValueError(f"{generated.name}: generated {observed}, committed {expected}")
    return observed


def steps_for(experiment, package, source, output, pins, measure=False):
    deps = output / "deps"
    local_scratch = source / "scratch" / "x15-replay" / output.parent.name
    opa = SCRATCH / "runtime" / "opa_windows_amd64.exe"
    tests = ("tests", package, PYTHON + ["-m", "unittest", "discover", "-s", "tests", "-v"])
    steps = {
        "X01": [
            ("check", package, PYTHON + ["-m", "src.run", "--check", "--details", output / "details.json"]),
        ],
        "X02": [
            ("check", source, PYTHON + [
                "EXPERIMENTS/EXP-X02/run.py", "--check", "--details", local_scratch / "details.json",
            ]),
        ],
        "X03": [
            ("check", package, PYTHON + ["run.py", "--check"]),
        ],
        "X04": [
            ("check", package, PYTHON + ["run.py", "--check"]),
        ],
        "X05": [
            ("check", source, PYTHON + [
                "EXPERIMENTS/EXP-X05/run.py", "--check", "--out", local_scratch,
            ] + (["--measure"] if measure else [])),
        ],
        "X06": [
            ("preaudit", package, PYTHON + ["x06.py", "preaudit", "--check", "--deps", deps]),
            ("check-evidence", package, PYTHON + ["x06.py", "check-evidence"]),
            ("replay", package, PYTHON + [
                "x06.py", "replay", "--opa", opa, "--temp", output / "tmp",
            ]),
            ("development", package, PYTHON + [
                "x06.py", "development", "--opa", opa, "--temp", output / "tmp",
            ]),
        ],
        "X07": [
            ("solve", package, PYTHON + [
                "run.py", "solve", "--x03-source",
                source_root(pins["X03"]) / "EXPERIMENTS" / "EXP-X03",
                "--out", output / "x03-proof.json",
            ]),
            ("replay", package, PYTHON + [
                "run.py", "check", "--evidence", "evidence/pre-outcome", "--post",
                "evidence/post-outcome", "--replay", "--openssl", OPENSSL_ASSET, "--temp", output / "tmp",
            ]),
        ],
        "X08": [
            ("exact", package, PYTHON + ["src/x08.py", "exact", "--output", output / "pre-audit.json"]),
            ("replay", package, PYTHON + ["src/x08.py", "replay", "--output", output / "replay"]),
        ],
        "X09": [
            ("exact", package, PYTHON + ["src/x09.py", "exact", "--output", output / "pre-audit.json"]),
            ("develop", package, PYTHON + ["src/x09.py", "develop", "--output", output / "development.json"]),
            ("replay", package, PYTHON + ["src/x09.py", "replay", "--output", output / "replay"]),
        ],
        "X10": [
            ("exact", package, PYTHON + ["src/x10.py", "exact", "--output", output / "pre-audit.json"]),
            ("replay", package, PYTHON + ["src/x10.py", "replay", "--output", output / "replay-summary.json"]),
        ],
        "X11": [
            ("replay", package, PYTHON + ["src/x11.py", "replay", "--out-dir", output / "replay"]),
        ],
        "X12": [
            ("preflight", package, PYTHON + [
                "src/x12.py", "preflight", "--exact", output / "preflight.json",
                "--calibration", output / "calibration.json",
            ]),
            ("replay", package, PYTHON + ["src/x12.py", "replay", "--out-dir", output / "replay"]),
        ],
        "X13": [
            ("replay", package, PYTHON + ["src/x13.py", "replay"]),
        ],
        "X14": [
            ("prepare", package, PYTHON + ["run.py", "prepare", "--out-dir", output / "prepared"]),
            ("replay", package, PYTHON + ["run.py", "replay"]),
        ],
    }
    prepare = {
        "X02": [("prepare-x01", source, [
            "pwsh", "-NoProfile", "-File", "EXPERIMENTS/EXP-X02/prepare-x01.ps1",
        ])],
        "X04": [("fetch-x03", source, GIT + [
            "fetch", "--no-write-fetch-head", "--no-tags", "origin", pins["X03"]["sha"],
        ])],
    }
    return prepare.get(experiment, []) + [tests] + steps[experiment]


def show_command(args, source, output):
    return [
        argument.replace(str(output), "{output}").replace(str(source), "{source}")
        .replace(str(SCRATCH), "{scratch}").replace(sys.executable, "python")
        for argument in map(str, args)
    ]


def stage_record(name, cwd, cmd, environment, source, output):
    started = perf_counter()
    print(f"{output.name} start {name}", flush=True)
    timed_out = False
    try:
        result = subprocess.run(
            list(map(str, cmd)), cwd=cwd, env=environment, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, check=False, timeout=2700,
        )
        transcript = result.stdout
        exit_code = result.returncode
    except subprocess.TimeoutExpired as exc:
        transcript = exc.stdout or b""
        exit_code = None
        timed_out = True
    except OSError as exc:
        transcript = str(exc).encode("utf-8")
        exit_code = None

    (output / f"{name}.log").write_bytes(transcript)
    lines = transcript.decode("utf-8", errors="replace").splitlines()
    counts = re.search(r"^Ran (\d+) tests? in ", "\n".join(lines), re.MULTILINE)
    elapsed = round(perf_counter() - started, 3)
    print(f"{output.name} {name}: exit {exit_code}, {elapsed} s", flush=True)
    return {
        "stage": name, "argv": show_command(cmd, source, output),
        "cwd": "." if source == cwd else cwd.relative_to(source).as_posix(),
        "seconds": elapsed, "exit_code": exit_code, "timed_out": timed_out,
        "test_count": int(counts.group(1)) if counts else None,
        "transcript_sha256": sha256(transcript),
        "transcript_tail": [line if len(line) <= 700 else line[:700] + " [truncated]"
                            for line in lines[-8:]],
    }


def run(pin, output, pins, git_dir, measure):
    experiment = pin["experiment"]
    source = source_root(pin)
    package = source / "EXPERIMENTS" / f"EXP-{experiment}"
    output.mkdir()
    temp = output / "tmp"
    temp.mkdir()
    environment = {
        **os.environ,
        "TEMP": str(temp), "TMP": str(temp), "TMPDIR": str(temp),
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0",
        "PYTHONIOENCODING": "utf-8", "GH_NO_UPDATE_NOTIFIER": "1",
    }
    if experiment in {"X02", "X04"}:
        environment.update(GIT_DIR=str(git_dir), GIT_WORK_TREE=str(source))
    if experiment == "X02":
        # The predecessor pins the Windows Git archive's CRLF model bytes.
        config_slot = int(environment.get("GIT_CONFIG_COUNT", "0"))
        environment["GIT_CONFIG_COUNT"] = str(config_slot + 1)
        environment[f"GIT_CONFIG_KEY_{config_slot}"] = "core.autocrlf"
        environment[f"GIT_CONFIG_VALUE_{config_slot}"] = "true"
    if experiment == "X06":
        import shutil

        dependencies = output / "deps"
        dependencies.mkdir()
        environment["PCX_X06_DEPS"] = str(dependencies)
        for dependency in ("X01", "X03"):
            shutil.copytree(source_root(pins[dependency]), dependencies / dependency)

    if experiment == "X02":
        (source / "scratch" / "x15-replay" / output.parent.name).mkdir(parents=True)
    stages = steps_for(experiment, package, source, output, pins, measure)
    records = []
    for name, cwd, cmd in stages:
        if experiment == "X06" and name in {"replay", "development"}:
            opa = SCRATCH / "runtime" / "opa_windows_amd64.exe"
            if not opa.exists() or sha256(opa.read_bytes()) != OPA_HASH:
                records.append({"stage": name, "exit_code": None, "blocker": "OPA asset digest unavailable"})
                continue
        if experiment == "X07" and name == "replay":
            if not OPENSSL_ASSET.exists() or sha256(OPENSSL_ASSET.read_bytes()) != OPENSSL_HASH:
                records.append({"stage": name, "exit_code": None, "blocker": "OpenSSL executable digest unavailable"})
                continue
        records.append(stage_record(name, cwd, cmd, environment, source, output))

    byte_matches = {}
    names = {
        "X08": ["pre-audit.json"],
        "X09": ["pre-audit.json", "development.json"],
        "X10": ["pre-audit.json"],
        "X12": ["preflight.json", "calibration.json"],
        "X14": ["exact.json", "pre-audit.json"],
    }
    for name in names.get(experiment, []):
        try:
            generated = output / "prepared" / name if experiment == "X14" else output / name
            byte_matches[name] = verify_equal(generated, package / "results" / name)
        except (ValueError, OSError) as exc:
            byte_matches[name] = {"error": str(exc)}
    if experiment == "X02":
        name = "scratch/x01/EXPERIMENTS/EXP-X01/src/model.py"
        converted = source.joinpath(name).read_bytes()
        raw = source_root(pins["X01"]).joinpath("EXPERIMENTS/EXP-X01/src/model.py").read_bytes()
        expected = raw.replace(b"\n", b"\r\n")
        byte_matches[name] = sha256(converted) if converted == expected else {"error": "GitHub blob differs"}
    if experiment == "X07":
        try:
            byte_matches["certificate.json"] = verify_equal(
                output / "x03-proof.json", package / "evidence" / "certificate.json",
            )
        except (ValueError, OSError) as exc:
            byte_matches["certificate.json"] = {"error": str(exc)}
    if experiment == "X04":
        for name in ("authorization.py", "certificates.py"):
            generated = source / "scratch" / "exp-x04-x03" / "pcx_x03_pinned" / name
            committed = source_root(pins["X03"]) / "EXPERIMENTS" / "EXP-X03" / "src" / name
            try:
                byte_matches[name] = verify_equal(generated, committed)
            except (ValueError, OSError) as exc:
                byte_matches[name] = {"error": str(exc)}

    receipt = {
        "experiment": experiment, "commit": pin["sha"], "source": "verified GitHub archive",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": platform.python_version(), "system": platform.system(),
        "stages": records, "additional_byte_matches": byte_matches,
    }
    (output / "replay.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return any(record["exit_code"] != 0 for record in records) or any(
        isinstance(result, dict) for result in byte_matches.values()
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiments", nargs="*")
    parser.add_argument("--label", required=True)
    parser.add_argument("--jobs", default=3, type=int)
    parser.add_argument("--measure-x05", action="store_true")
    options = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", options.label):
        raise SystemExit("Use an alphanumeric or hyphenated run label")
    output = SCRATCH / "runs" / options.label
    output.mkdir(parents=True)
    scoped_temp = output / "tmp"
    scoped_temp.mkdir()
    os.environ.update(TEMP=str(scoped_temp), TMP=str(scoped_temp))
    git_dir = Path(subprocess.check_output(
        ["git", "rev-parse", "--absolute-git-dir"], cwd=ROOT, text=True,
    ).strip())
    pins = read_manifest()
    experiments = options.experiments or sorted(pins)
    failures = []
    with ThreadPoolExecutor(max_workers=options.jobs) as pool:
        futures = [
            pool.submit(run, pins[experiment], output / experiment, pins, git_dir, options.measure_x05)
            for experiment in experiments
        ]
        for experiment, computation in zip(experiments, futures, strict=True):
            try:
                if computation.result():
                    failures.append(experiment)
            except (ValueError, OSError, subprocess.CalledProcessError) as exc:
                failures.append(experiment)
                print(f"{experiment}: {exc}", flush=True)
    if failures:
        raise SystemExit(f"Replays with discrepancies: {', '.join(failures)}")


if __name__ == "__main__":
    main()
