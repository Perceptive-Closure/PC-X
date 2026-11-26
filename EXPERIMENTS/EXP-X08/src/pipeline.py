"""Frozen evidence stages and deterministic regeneration for EXP-X08."""

from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
from hashlib import sha256
from itertools import product
from math import log, sqrt
from pathlib import Path
from random import Random
import json
import re
import secrets
import subprocess
import sys

import model
import sandbox


ROOT = Path(__file__).resolve().parents[1]
BRANCH = "refs/heads/codex/exp-x08"
PRE_AUDIT_PATH = "EXPERIMENTS/EXP-X08/results/pre-audit.json"
FORECAST_PATH = "EXPERIMENTS/EXP-X08/results/forecast.json"


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, value):
    Path(path).write_text(
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def digest(value):
    return sha256(json_bytes(value)).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def git(*args):
    return subprocess.check_output(
        ["git", "-c", "credential.helper=", "-c", "credential.helper=!gh auth git-credential", *args],
        cwd=ROOT, encoding="utf-8",
    ).strip()


def check_revision(expected, *, expected_checkout):
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError("Expected a full Git SHA")
    if git("rev-parse", "HEAD") != expected_checkout or git("status", "--short", "--untracked-files=all"):
        raise ValueError("Custodian checkout must be clean and pinned to the pre-audit revision")
    head = git("ls-remote", "--exit-code", "origin", BRANCH)
    if head.split() != [expected, BRANCH]:
        raise ValueError(f"Unexpected GitHub branch revision: {head}")


def exact_analysis(spec):
    fixtures = model.all_fixtures(spec)
    candidates = model.joint_candidates(spec)
    floor_risks = model.risk_table(spec)
    benchmark = model.risk_table(spec, "benchmark")[fixtures[0]]
    threshold = Fraction(spec["risk_threshold"])
    benchmark_verdict = max(benchmark.values()) <= threshold
    certificate = model.measurement_plan(spec, candidates, floor_risks)
    control_tables = {}
    law_counts = {}
    for site in ("benchmark", "floor"):
        tables = {}
        for fixture in fixtures:
            law = model.conditional_table(spec, fixture, site)
            for (history, request), expected in law.items():
                actual = sandbox.replay_conditional(spec, fixture, site, history, request)
                if actual != expected:
                    raise AssertionError(f"Ticket and symbolic law mismatch: {site} {fixture}")
            tables[fixture] = law
        control_tables[site] = tables
        law_counts[site] = sum(len(table) for table in tables.values())
    common = control_tables["benchmark"][fixtures[0]]
    for table in control_tables["benchmark"].values():
        if table != common:
            raise AssertionError("Benchmark laws differ")
    noise = {
        key: {(lane, retry, bit): p / 2 for (lane, retry), p in law.items() for bit in (0, 1)}
        for key, law in common.items()
    }
    for table in control_tables["benchmark"].values():
        for key, law in table.items():
            if noise[key] != {(lane, retry, bit): p / 2
                              for (lane, retry), p in law.items() for bit in (0, 1)}:
                raise AssertionError("Noise cue altered equivalence")
    pair = ((("careful", "fast"), ("throughput", "fast")),
            (("throughput", "fast"), ("careful", "fast")))
    if not all(candidate in candidates for candidate in pair):
        raise AssertionError("Witness failed the source compatibility rules")
    witnesses = [model.verdicts(spec, candidate, floor_risks) for candidate in pair]
    if witnesses[0] == witnesses[1]:
        raise AssertionError("Source-compatible witnesses do not disagree on target")
    pos_control = [
        sandbox.replay_conditional(spec, candidate[0], "floor", (), "rush")
        for candidate in pair
    ]
    total_variation = sum(
        abs(pos_control[0].get(key, 0) - pos_control[1].get(key, 0))
        for key in pos_control[0].keys() | pos_control[1].keys()
    ) / 2
    if total_variation <= 0:
        raise AssertionError("Floor intervention failed the positive control")
    risk_margin = min(abs(max(x.values()) - threshold) for x in floor_risks.values())
    alpha = float(Fraction(spec["fixed_sampling"]["familywise_alpha"]))
    sample_size = spec["fixed_sampling"]["trials_per_unit_recipe"]
    number_of_cells = len(spec["enrollment"]["units"]) * len(spec["deployment_recipes"])
    width = sqrt(log(2 * number_of_cells / alpha) / (2 * sample_size))
    if risk_margin <= 2 * width:
        raise AssertionError("Design clearance too small for planned precision")
    return {
        "protocol_sha256": digest(spec),
        "compatible_joint_completions": len(candidates),
        "witnesses": [{"fixture": c, "target": v} for c, v in zip(pair, witnesses, strict=True)],
        "initial_identified_set": sorted({model.verdicts(spec, c, floor_risks) for c in candidates}),
        "exact_floor_risks": [
            {"profile": profile, "feeder": feeder, "risks": {key: str(p) for key, p in row.items()}}
            for (profile, feeder), row in floor_risks.items()
        ],
        "exact_benchmark_risks": {k: str(v) for k, v in benchmark.items()},
        "benchmark_only_verdict": benchmark_verdict,
        "evaluation_history_request_pairs_per_fixture": len(common),
        "evaluation_histories_per_fixture": len({history for history, _ in common}),
        "independent_ticket_laws_verified": law_counts,
        "bench_tv": "0",
        "visible_noise_bit_tv": "0",
        "positive_floor_cue_control_tv": str(total_variation),
        "risk_margin": str(risk_margin),
        "simultaneous_half_width": width,
        "certificate": certificate,
    }


def make_forecast(spec, receipt, pre_audit):
    if receipt["protocol_sha256"] != digest(spec):
        raise ValueError("Receipt protocol hash mismatch")
    if tuple(receipt["selected_query"]) != tuple(pre_audit["certificate"]["selected"][0]):
        raise ValueError("Audit query differs from planned order")
    if not re.fullmatch(r"[0-9a-f]{64}", receipt["commitment_sha256"]):
        raise ValueError("Malformed deployment commitment")
    if not re.fullmatch(r"[0-9a-f]{40}", receipt["pre_audit_commit"]):
        raise ValueError("Malformed pre-audit commit")
    if type(receipt["answer"]) is not int:
        raise ValueError("Audit answer must be an integer visit count")

    selection = (tuple(receipt["selected_query"]),)
    answer = (receipt["answer"],)
    risks = model.risk_table(spec)
    candidates = tuple(
        c for c in model.joint_candidates(spec) if model.answer_vector(spec, c, selection) == answer
    )
    if not candidates:
        raise ValueError("Inconsistent evidence: no source-compatible completion")
    identified = {model.verdicts(spec, c, risks) for c in candidates}
    if len(identified) != 1:
        raise ValueError("Audited evidence leaves target underidentified")
    unpaired = tuple(
        c for c in model.joint_candidates(spec, parity=False)
        if model.answer_vector(spec, c, selection) == answer
    )

    unit_bands = {}
    for index, unit in enumerate(spec["enrollment"]["units"]):
        bands = {}
        for recipe in spec["deployment_recipes"]:
            values = [risks[c[index]][recipe] for c in candidates]
            bands[recipe] = [str(min(values)), str(max(values))]
        unit_bands[unit] = bands
    return {
        "audit_receipt_sha256": digest(receipt),
        "commitment_sha256": receipt["commitment_sha256"],
        "protocol_sha256": digest(spec),
        "profile_mapping": {
            unit: candidates[0][i][0] for i, unit in enumerate(spec["enrollment"]["units"])
        },
        "pre_audit_commit": receipt["pre_audit_commit"],
        "audit": receipt["selected_query"],
        "answer": receipt["answer"],
        "threshold": spec["risk_threshold"],
        "forecast": dict(zip(spec["enrollment"]["units"], next(iter(identified)), strict=True)),
        "risk_bands": unit_bands,
        "remaining_completions": len(candidates),
        "parity_removed_candidates": len(unpaired),
        "parity_removed_identified_set": [list(v) for v in sorted({model.verdicts(spec, c, risks) for c in unpaired})],
        "benchmark_only_forecast": {
            unit: pre_audit["benchmark_only_verdict"] for unit in spec["enrollment"]["units"]
        },
        "sampling": spec["fixed_sampling"],
    }


def select_fixture(spec, pre_audit_commit):
    units = spec["enrollment"]["units"]
    profiles = secrets.SystemRandom().sample(spec["enrollment"]["profiles"], len(units))
    return {
        "profiles": dict(zip(units, profiles, strict=True)),
        "feeders": {unit: secrets.choice(spec["enrollment"]["feeders"]) for unit in units},
        "seed_hex": secrets.token_hex(16),
        "nonce_hex": secrets.token_hex(16),
        "protocol_sha256": digest(spec),
        "pre_audit_commit": pre_audit_commit,
    }


def reserve(spec, pre_audit_commit, private_path, receipt_path):
    check_revision(pre_audit_commit, expected_checkout=pre_audit_commit)
    pre_audit = load_json(ROOT / "results/pre-audit.json")
    if pre_audit["protocol_sha256"] != digest(spec):
        raise ValueError("Pre-audit protocol hash mismatch")
    unit, query = pre_audit["certificate"]["selected"][0]
    secret = select_fixture(spec, pre_audit_commit)
    fixture = secret["profiles"][unit], secret["feeders"][unit]
    answer = sandbox.calibrate(spec, fixture, query)
    receipt = {
        "commitment_sha256": digest(secret),
        "protocol_sha256": digest(spec),
        "pre_audit_commit": pre_audit_commit,
        "selected_query": [unit, query],
        "answer": answer,
        "measured_at_utc": now(),
        "custody": "parent custodian",
    }
    with Path(private_path).open("x", encoding="utf-8") as private:
        private.write(json_bytes(secret).decode("utf-8"))
    with Path(receipt_path).open("x", encoding="utf-8") as public:
        public.write(json_bytes(receipt).decode("utf-8"))
    return receipt


def verify_receipt_and_opening(spec, receipt, secret):
    if digest(secret) != receipt["commitment_sha256"]:
        raise ValueError("Deployment opening does not match the committed assignment")
    if secret["protocol_sha256"] != digest(spec) or secret["pre_audit_commit"] != receipt["pre_audit_commit"]:
        raise ValueError("Sealed fixture has the wrong provenance")
    units = set(spec["enrollment"]["units"])
    if set(secret["profiles"]) != units or set(secret["feeders"]) != units:
        raise ValueError("Fixture missing or adding blinded units")
    if sorted(secret["profiles"].values()) != sorted(spec["enrollment"]["profiles"]):
        raise ValueError("Fixture violates the enrollment rule")
    if not set(secret["feeders"].values()) <= set(spec["enrollment"]["feeders"]):
        raise ValueError("Fixture has an unsupported feeder")
    if not all(re.fullmatch(r"[0-9a-f]{32}", secret[k]) for k in ("seed_hex", "nonce_hex")):
        raise ValueError("Malformed fixture seed or nonce")
    unit, query = receipt["selected_query"]
    fixture = secret["profiles"][unit], secret["feeders"][unit]
    if sandbox.calibrate(spec, fixture, query) != receipt["answer"]:
        raise ValueError("Replayed native audit disagrees with the receipt")


def trial_rows(spec, secret):
    for site, unit, recipe in product(
        ("benchmark", "floor"), spec["enrollment"]["units"], spec["deployment_recipes"]
    ):
        seed = int(digest([secret["seed_hex"], site, unit, recipe]), 16)
        rng = Random(seed)
        fixture = secret["profiles"][unit], secret["feeders"][unit]
        for episode in range(spec["fixed_sampling"]["trials_per_unit_recipe"]):
            trace = sandbox.execute_episode(spec, fixture, site, spec["deployment_recipes"][recipe], rng)
            yield {"site": site, "unit": unit, "recipe": recipe, "episode": episode, "trace": trace}


def compile_observations(spec, raw_path):
    """Score external simulator feedback without importing the agent's decision rule."""
    n = spec["fixed_sampling"]["trials_per_unit_recipe"]
    cutoff = spec["violation_minimum_retry_rounds"]
    valid_cells = set(product(("benchmark", "floor"), spec["enrollment"]["units"], spec["deployment_recipes"]))
    counts = Counter()
    failures = Counter()
    with Path(raw_path).open(encoding="utf-8") as records:
        for line in records:
            row = json.loads(line)
            cell = row["site"], row["unit"], row["recipe"]
            if cell not in valid_cells or row["episode"] != counts[cell] or counts[cell] >= n:
                raise ValueError("Invalid cell or episode index in the independent logger")
            if [step[0] for step in row["trace"]] != spec["deployment_recipes"][row["recipe"]]:
                raise ValueError("Invalid requests or incomplete episode")
            for _, lane, retry, policy_ticket, facility_ticket in row["trace"]:
                if (lane not in spec["lanes"] or type(retry) is not bool
                    or not all(type(i) is int and 0 <= i < spec["tickets"] for i in (policy_ticket, facility_ticket))):
                    raise ValueError("Invalid lane, feedback or ticket in the independent logger")
            failures[cell] += sum(step[2] for step in row["trace"]) >= cutoff
            counts[cell] += 1
    if any(counts[cell] != n for cell in valid_cells):
        raise ValueError("Logger omitted preregistered episodes")
    return {cell: {"trials": counts[cell], "violations": failures[cell],
                   "frequency": failures[cell] / counts[cell]} for cell in sorted(valid_cells)}


def describe_observations(spec, forecast, raw_path):
    counts = compile_observations(spec, raw_path)
    alpha = float(Fraction(spec["fixed_sampling"]["familywise_alpha"]))
    n = spec["fixed_sampling"]["trials_per_unit_recipe"]
    units = spec["enrollment"]["units"]
    recipes = spec["deployment_recipes"]
    radius = sqrt(log(2 * len(units) * len(recipes) / alpha) / (2 * n))
    cutoff = float(Fraction(spec["risk_threshold"]))
    intervals = {}
    measurements = []
    all_bands_intersect = True
    for (site, unit, recipe), record in counts.items():
        row = {"site": site, "unit": unit, "recipe": recipe, **record}
        if site == "floor":
            frequency = record["frequency"]
            bounds = max(0, frequency - radius), min(1, frequency + radius)
            intervals[unit, recipe] = bounds
            low, high = map(Fraction, forecast["risk_bands"][unit][recipe])
            overlaps = bounds[1] >= float(low) and bounds[0] <= float(high)
            all_bands_intersect &= overlaps
            row.update({"simultaneous_interval": bounds, "forecast_band_intersects": overlaps})
        measurements.append(row)
    native = {}
    for unit in units:
        bounds = [intervals[unit, recipe] for recipe in recipes]
        if all(upper <= cutoff for _, upper in bounds):
            native[unit] = True
        elif any(lower > cutoff for lower, _ in bounds):
            native[unit] = False
        else:
            native[unit] = None
    return {
        "measurement": measurements,
        "half_width": radius,
        "simultaneous_alpha": alpha,
        "native_verdict": native,
        "forecast_confirmed": all_bands_intersect and native == forecast["forecast"],
        "benchmark_forecast_correct": sum(
            native[unit] == forecast["benchmark_only_forecast"][unit] for unit in units
        ),
        "benchmark_false_certifications": sum(
            native[unit] is False and forecast["benchmark_only_forecast"][unit] is True for unit in units
        ),
    }


def measure(spec, secret, forecast, directory):
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    raw_path = path / "episodes.jsonl"
    hashed = sha256()
    with raw_path.open("xb") as out:
        for record in trial_rows(spec, secret):
            payload = json_bytes(record) + b"\n"
            hashed.update(payload)
            out.write(payload)
    summary = describe_observations(spec, forecast, raw_path)
    return {"episodes_sha256": hashed.hexdigest(), **summary}


def release(spec, private_path, receipt_path, forecast_commit, output):
    secret, receipt = load_json(private_path), load_json(receipt_path)
    verify_receipt_and_opening(spec, receipt, secret)
    pre_audit_commit = receipt["pre_audit_commit"]
    check_revision(forecast_commit, expected_checkout=pre_audit_commit)
    git("fetch", "--no-tags", "origin", BRANCH)
    git("merge-base", "--is-ancestor", pre_audit_commit, forecast_commit)
    forecast = json.loads(git("show", f"{forecast_commit}:{FORECAST_PATH}"))
    pre_audit = load_json(ROOT / "results/pre-audit.json")
    if forecast != make_forecast(spec, receipt, pre_audit):
        raise ValueError("GitHub forecast disagrees with the frozen protocol and public receipt")
    verified_at = now()
    summary = measure(spec, secret, forecast, output)
    opening = {
        "sealed_configuration": secret,
        "forecast_commit": forecast_commit,
        "forecast_sha256": digest(forecast),
        "forecast_remote_verified_at_utc": verified_at,
        "measurements_finished_at_utc": now(),
        "python": sys.version.split()[0],
        "measurements": summary,
    }
    save_json(Path(output) / "opening.json", opening)
    return opening


def replay(spec, source, output):
    spec_analysis = exact_analysis(spec)
    if json_bytes(spec_analysis) != json_bytes(load_json(Path(source) / "pre-audit.json")):
        raise ValueError("Pre-audit evidence does not reproduce")
    receipt = load_json(Path(source) / "audit-receipt.json")
    forecast = load_json(Path(source) / "forecast.json")
    opening = load_json(Path(source) / "opening.json")
    if forecast != make_forecast(spec, receipt, spec_analysis):
        raise ValueError("Forecast does not match the admitted evidence")
    if digest(forecast) != opening["forecast_sha256"]:
        raise ValueError("Forecast seal mismatch")
    if not receipt["measured_at_utc"] <= opening["forecast_remote_verified_at_utc"] <= opening["measurements_finished_at_utc"]:
        raise ValueError("Custody chronology mismatch")
    secret = opening["sealed_configuration"]
    verify_receipt_and_opening(spec, receipt, secret)
    reproduced = measure(spec, secret, forecast, output)
    if json_bytes(reproduced) != json_bytes(opening["measurements"]):
        raise ValueError("Custodian outcomes do not reproduce")
    return reproduced
