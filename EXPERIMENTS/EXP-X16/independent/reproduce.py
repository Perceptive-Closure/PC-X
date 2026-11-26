"""Run the independent X16 native audit on public fixtures or a verified opening."""

import argparse
from base64 import b64encode
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import time
import tracemalloc

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from custody_checks import (
    SOURCE_PLAN, authority_payload, blob, export_native, opened_inputs,
)
from evidence import (
    EvidenceError, NativeBatch, digest, equal, inspect_inventory, inspect_run,
    inspect_static, policy_tapes, save_json, to_native_static, wire, work_tapes,
)
from reference import (
    abstract_profile, enumerate_paths, initial_receipt, receipt_key, solve_catalogue, solve_online,
)


PUBLIC_DOCUMENT = {
    "id": "independent-public-training-document",
    "title": "  Ｐublic\u00a0 training  intake \ufeff",
    "category": "  Local / Memo  ",
    "body": "Evidence Alpha 2026 \r\nBETA alpha.\rRésumé Ω𐐀.",
}
PUBLIC_ROWS = {
    "feedback-live": [("start-left", "middle-left", "route-left")],
    "feedback-suppressed": [("start-left", "middle-left", "route-left")],
    "meter-h3": [("intake", "route-fresh"), ("intake", "route-stale")],
    "meter-h4": [("intake", "route-fresh"), ("intake", "route-stale")],
    "gateway-2": [("stage1-stale", "stage2-fresh", "stage3-fresh")],
    "split-calls": [("split-left",), ("split-right",)],
    "free-guard": [("intake", "route-fresh"), ("intake", "route-stale")],
    "hidden-carry": [("early-clear", "late-fresh"), ("early-set", "late-fresh")],
    "changed-instrument": [("intake-fresh", "review", "route")],
}


@dataclass(frozen=True)
class Trial:
    treatment: str
    request: dict
    expected: dict
    maximum_paid: int | None = None


def profiles_and_paths(catalogue):
    profiles = {row["id"]: row for row in catalogue["profiles"]}
    paths = {
        key: {path.ids: path for path in enumerate_paths(profile)}
        for key, profile in profiles.items()
    }
    return profiles, paths


def job_trial(name, case, treatment, expected, **driver):
    return Trial(
        treatment, dict(
            id=f"{name}-{case['id']}", profile=case["profile"], path=case["path"],
            op="run", document=case["document"], **driver,
        ), expected,
    )


def fixture_cases(catalogue):
    _, paths = profiles_and_paths(catalogue)
    return [
        dict(
            id=f"public-{name}-{index}", profile=name, path=list(edges),
            nominal_stratum=paths[name][edges].verdict, document=PUBLIC_DOCUMENT,
        )
        for name, rows in PUBLIC_ROWS.items() for index, edges in enumerate(rows)
    ]


def inventory_trials(profiles, path_pool):
    trials = []
    for index, (profile, path) in enumerate(path_pool, start=1):
        trials.append(Trial(
            "inventory", dict(id=f"rows-{index}", profile=profile, path=path, op="inventory"), {},
        ))
        queries = [
            query["id"] for stage in profiles[profile]["stages"] for query in stage["statics"]
        ]
        trials.append(Trial(
            "full-static-panel",
            dict(id=f"panel-{index}", profile=profile, path=path, op="static", queries=queries), {},
        ))
    return trials


def per_installation(profiles, paths, reference, cases):
    trials = []
    for case in cases:
        identifier, name = case["id"], case["profile"]
        path = paths[name][tuple(case["path"])]
        target = path.verdict
        equal(case["nominal_stratum"], target, f"{identifier} independent intrinsic target")
        profile = profiles[name]
        result = reference["profiles"][name]
        for index, tape in enumerate(work_tapes(profile, path)):
            if target == "YES":
                expected = dict(status="manual-done", work=path.remaining[0], truth={"complete": True})
            else:
                expected = dict(status="denied", reason="work-deadline", truth={"complete": False})
            trials.append(job_trial(
                f"direct-{index}", case, "known-path-work", expected,
                actions=path.fastest_job_actions, tape=tape,
            ))
        for comparison in ("static", "adaptive"):
            for goal, value in result[comparison].items():
                if value["worst_paid"] is None:
                    continue
                driver = {"queries": value["queries"]} if comparison == "static" else {
                    "static_policy": to_native_static(value["tree"]),
                }
                trials.append(Trial(
                    f"{comparison}-{goal}",
                    dict(id=f"{comparison}-{goal}-{identifier}", profile=name,
                         path=case["path"], op="static", **driver), {}, value["worst_paid"],
                ))
        initial = initial_receipt(profile, path)
        root = receipt_key(initial["obs"], initial["meter"])
        for comparison in ("online", "fixed_schedule"):
            for goal, value in result.get(comparison, {}).items():
                if value["worst_paid"] is None:
                    continue
                policy = value["policy_by_initial"][root]
                expected = dict(status="stopped", verdict=target, truth={"complete": target == "YES"})
                for index, tape in enumerate(policy_tapes(profile, path, policy)):
                    trial = job_trial(
                        f"{comparison}-{goal}-{index}", case, f"{comparison}-{goal}",
                        expected, policy=policy, tape=tape,
                    )
                    trials.append(Trial(trial.treatment, trial.request, expected, value["worst_paid"]))
    return trials


def controls_trials(catalogue, profiles, paths, reference, cases):
    selected = {name: [row for row in cases if row["profile"] == name] for name in profiles}
    gates = {control["id"]: control["gate"] for control in catalogue["controls"]}
    trials = []
    findings = {}

    cartesian = reference["abstract_controls"]["cartesian-relaxation"]
    real = paths["feedback-live"]
    invalid = [path for path in cartesian["paths"] if tuple(path["edges"]) not in real]
    false_target = [path["edges"] for path in invalid if path["target"] == "NO"]
    ordinary = reference["profiles"]["feedback-live"]
    findings["cartesian-relaxation"] = dict(
        gate=gates["cartesian-relaxation"], rejected_paths=[path["edges"] for path in invalid],
        introduced_negative_paths=false_target,
        signed_static_target=ordinary["static"]["target"]["worst_paid"],
        relaxed_static_target=cartesian["static"]["target"]["worst_paid"],
    )
    if selected["feedback-live"]:
        document = selected["feedback-live"][0]["document"]
        for index, path in enumerate(invalid):
            bad = dict(id=f"cartesian-{index}", profile="feedback-live",
                       path=path["edges"], document=document)
            trials.append(job_trial(
                "invalid", bad, "cartesian-relaxation",
                dict(status="denied", reason="invalid-installation", truth={"done": 0, "complete": False}),
                actions=["job.fast"],
            ))

    live_policy = ordinary["online"]["target"]["policy_by_initial"]["start|WORK"]
    suppressed = reference["profiles"]["feedback-suppressed"]
    findings["suppressed-useful-receipt"] = dict(
        gate=gates["suppressed-useful-receipt"], worst_paid_before=ordinary["online"]["target"]["worst_paid"],
        worst_paid_after=suppressed["online"]["target"]["worst_paid"],
    )
    for case in selected["feedback-suppressed"]:
        trials.append(job_trial(
            "suppressed", case, "suppressed-useful-receipt",
            dict(status="missing-branch", moves=1, truth={"done": 1, "complete": False}),
            policy=live_policy,
        ))

    split = profiles["split-calls"]
    literals = {edge["id"]: edge["literal_fast"] for edge in split["stages"][0]["edges"]}
    findings["split-literal-commands"] = dict(
        gate=gates["split-literal-commands"], fast_names=literals,
        worst_paid=reference["profiles"]["split-calls"]["online"]["target"]["worst_paid"],
    )
    for case in selected["split-calls"]:
        wrong = next(literal for name, literal in literals.items() if name != case["path"][0])
        for attempted, reason in ((wrong, "unknown-command"), ("job.slow", "work-deadline")):
            trials.append(job_trial(
                f"split-{reason}", case, "split-literal-commands",
                dict(status="denied", reason=reason, truth={"done": 0}),
                actions=[attempted],
            ))

    guard = reference["profiles"]["free-guard"]["online"]["target"]
    findings["initial-free-disclosure"] = dict(
        gate=gates["initial-free-disclosure"], disclosed_roots=sorted(guard["policy_by_initial"]),
        worst_paid_with_disclosure=guard["worst_paid"],
        worst_paid_with_standard_initial=reference["profiles"]["meter-h3"]["online"]["target"]["worst_paid"],
    )
    for case in selected["free-guard"]:
        initial = initial_receipt(profiles["free-guard"], paths["free-guard"][tuple(case["path"])])
        trials.append(job_trial(
            "free", case, "initial-free-disclosure",
            dict(status="stopped", verdict=case["nominal_stratum"], paid=0,
                 truth={"complete": case["nominal_stratum"] == "YES"}),
            policy=guard["policy_by_initial"][receipt_key(initial["obs"], initial["meter"])],
        ))

    dropped = reference["abstract_controls"]["missing-long-support"]["online"]["target"]
    findings["missing-long-support"] = dict(
        gate=gates["missing-long-support"], lossy_model_worst_paid=dropped["worst_paid"],
        full_support_worst_paid=reference["profiles"]["meter-h3"]["online"]["target"]["worst_paid"],
    )
    for case in selected["meter-h3"]:
        lossy_policy = dropped["policy_by_initial"]["start|WORK"]
        trials.append(job_trial(
            "missing-long", case, "missing-long-support",
            dict(status="missing-branch", moves=1, truth={"done": 1, "complete": False}),
            policy=lossy_policy, tape=[1],
        ))

    findings["prior-hidden-carry"] = dict(
        gate=gates["prior-hidden-carry"], observed_meter="WORK", later_edge="late-fresh",
        expected_quotes={"early-clear": 1, "early-set": 5},
    )
    for case in selected["hidden-carry"]:
        if case["path"][1] != "late-fresh":
            continue
        price = findings["prior-hidden-carry"]["expected_quotes"][case["path"][0]]
        trials.append(job_trial(
            "carry", case, "prior-hidden-carry",
            dict(status="manual-done", paid=price, truth={"complete": True}),
            actions=["job.fast", "ask.flag", "job.fast"],
        ))

    findings["trusted-versus-changed-instrument"] = dict(
        gate=gates["trusted-versus-changed-instrument"],
        expected_altered_destination="quarantine", expected_altered_read_price=1,
    )
    for case in selected["changed-instrument"]:
        if case["nominal_stratum"] != "YES":
            continue
        path = paths["changed-instrument"][tuple(case["path"])]
        trials.append(job_trial(
            "trusted", case, "trusted-versus-changed-instrument",
            dict(status="manual-done", paid=0, truth={"complete": True}),
            actions=path.fastest_job_actions,
        ))
        trials.append(job_trial(
            "disturbed", case, "trusted-versus-changed-instrument",
            dict(status="manual-done", paid=1,
                 truth={"done": len(path.ids), "complete": False, "actual_destination": "quarantine"}),
            actions=("ask.flag", *path.fastest_job_actions),
        ))
        if "intrinsic-gap" in profiles:
            standard = dict(case, id=f"standard-{case['id']}", profile="intrinsic-gap")
            trials.append(job_trial(
                "ordinary-quoted", standard, "trusted-versus-changed-instrument",
                dict(status="manual-done", paid=1, truth={"complete": True}),
                actions=("ask.flag", *path.fastest_job_actions),
            ))
    return trials, findings


def expect_subset(actual, expected, path="differential observation"):
    for key, value in expected.items():
        if isinstance(value, dict):
            expect_subset(actual[key], value, f"{path}.{key}")
        else:
            equal(actual[key], value, f"{path}.{key}")


def audit_batch(batch, name, profiles, paths, seal, trials):
    workspace, answers = batch.launch(name, [trial.request for trial in trials])
    records = []
    errors = []
    for trial, actual in zip(trials, answers, strict=True):
        task = trial.request
        profile = profiles[task["profile"]]
        path = paths[task["profile"]].get(tuple(task["path"]))
        audit = dict(
            treatment=trial.treatment, id=task["id"], profile=task["profile"],
            path=task["path"], tape=task.get("tape"),
        )
        try:
            if task["op"] == "inventory":
                observed = inspect_inventory(profile, path, actual)
            elif task["op"] == "static":
                observed = inspect_static(profile, path, task, actual, workspace)
            else:
                observed = inspect_run(profile, path, task, actual, workspace, seal)
            expect_subset(observed, trial.expected)
            if trial.maximum_paid is not None and observed["paid"] > trial.maximum_paid:
                raise EvidenceError("native quote exceeds the independent worst supported optimum")
            audit.update(status="verified", observed=observed)
        except (OSError, TypeError, ValueError, KeyError, IndexError) as issue:
            audit.update(status="discrepancy", failure=str(issue))
            errors.append(audit)
        records.append(audit)
    return records, errors


def audit_catalogue(batch, data, inventory_cases):
    catalogue, cases, seal = (data[name] for name in ("catalogue", "heldout", "authority"))
    profiles, paths = profiles_and_paths(catalogue)
    reference = solve_catalogue(catalogue)
    save_json(batch.output / "reference.json", reference)
    corpus = inventory_trials(profiles, inventory_cases)
    rows, row_errors = audit_batch(batch, "source-rows", profiles, paths, seal, corpus)
    controls, findings = controls_trials(catalogue, profiles, paths, reference, cases)
    trials = [*per_installation(profiles, paths, reference, cases), *controls]
    replay, failures = audit_batch(batch, "document-replay", profiles, paths, seal, trials)
    valid = set(catalogue["valid_profiles"])
    inventory = [row for row in rows if row["treatment"] == "inventory" and row["status"] == "verified"]
    valid_rows = [row["observed"] for row in inventory if row["profile"] in valid]
    return dict(
        cases=len(cases), trials=len(trials) + len(corpus), controls=findings,
        inventoried_installations=len(inventory), valid_inventoried_installations=len(valid_rows),
        guard_rows=sum(row["observed"]["guard_rows"] for row in inventory),
        valid_guard_rows=sum(row["guard_rows"] for row in valid_rows),
        guard_commands=sum(row["observed"]["commands"] for row in inventory),
        raw_guard_outcomes=sum(row["observed"]["raw_outcomes"] for row in inventory),
        records=[*rows, *replay], discrepancies=[*row_errors, *failures],
    )


def training_seal(catalogue, authority):
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    seal = dict(
        schema=1, source_commit="0" * 40,
        catalogue_sha256=digest(catalogue.read_bytes()),
        frozen_manifest_sha256=digest(b"EXP-X16 INDEPENDENT PUBLIC TRAINING ONLY\n"),
        public_key_pem=public.decode("ascii"),
    )
    seal["signature"] = b64encode(private.sign(authority_payload(seal))).decode("ascii")
    save_json(authority, seal)
    return seal


def audit_mixed_freeze(service, output, baseline):
    profile = deepcopy(next(row for row in baseline["profiles"] if row["id"] == "meter-h3"))
    profile["id"] = "public-training-mixed-freeze"
    profile["deadline"] = 3
    profile["stages"][1]["edges"][1]["gives"].append(dict(obs="filed", meter="ALTERNATE"))
    catalogue = dict(schema=1, profiles=[profile])
    profiles, paths = profiles_and_paths(catalogue)
    path = ["intake", "route-stale"]
    file, authority = output / "mixed-training.json", output / "mixed-training-authority.json"
    save_json(file, catalogue)
    seal = training_seal(file, authority)
    batch = NativeBatch(service, file, authority, output)
    case = dict(id="public-mixed", profile=profile["id"], path=path, document=PUBLIC_DOCUMENT)
    trials = inventory_trials(profiles, [(profile["id"], path)])
    for index in (0, 1):
        trials.append(job_trial(
            f"whole-freeze-{index}", case, "whole-occurrence-r-freeze",
            dict(status="denied", reason="r-freeze", moves=1, truth={"done": 1}),
            actions=["job.fast", "job.fast"], tape=[0, index],
        ))
        trials.append(job_trial(
            f"whole-slow-{index}", case, "whole-occurrence-r-freeze",
            dict(status="manual-done", moves=2, truth={"done": 2, "complete": True}),
            actions=["job.fast", "job.slow"], tape=[0, index],
        ))
    return audit_batch(batch, "mixed-freeze", profiles, paths, seal, trials)


def train(repo, service_pin, output):
    catalogue = output / "public-catalogue.json"
    catalogue.write_bytes(blob(repo, SOURCE_PLAN, "cases/catalogue.json"))
    baseline = json.loads(catalogue.read_bytes())
    authority = output / "public-dummy-authority.json"
    seal = training_seal(catalogue, authority)
    service = export_native(repo, service_pin, output / "service")
    batch = NativeBatch(service, catalogue, authority, output)
    cases = fixture_cases(baseline)
    inventory = [(row["profile"], row["path"]) for row in cases]
    audit = audit_catalogue(batch, dict(catalogue=baseline, heldout=cases, authority=seal), inventory)
    mixed, failures = audit_mixed_freeze(service, output, baseline)
    audit["records"].extend(mixed)
    audit["trials"] += len(mixed)
    audit["discrepancies"].extend(failures)

    invalid_authority = output / "bad-signature.json"
    save_json(invalid_authority, dict(seal, source_commit="1" * 40))
    invalid_catalogue = output / "different-catalogue.json"
    invalid_catalogue.write_bytes(catalogue.read_bytes() + b"\n")
    rejected = [
        (catalogue, invalid_authority, "altered-signature", "Invalid authority signature"),
        (invalid_catalogue, authority, "altered-catalogue", "Invalid authority seal or catalogue bytes"),
    ]
    should_write = job_trial(
        "would-write", cases[0], "expected-as-denied", {}, actions=["job.fast"],
    ).request
    for trial_catalogue, trial_authority, name, message in rejected:
        trial_batch = NativeBatch(service, trial_catalogue, trial_authority, output)
        note = trial_batch.launch(name, [should_write], reject=True)
        if message not in note:
            raise EvidenceError(f"{name} incorrect reason: {note}")
    return dict(mode="public-training", native_commit=service_pin, rejected_seals=2, **audit)



def compare_forecast(catalogue, reference, published):
    """Compare published values and path targets to code frozen before reading them."""
    equal(published["schema"], 1, "published forecast schema")
    compared = []
    failures = []
    for name in catalogue["valid_profiles"]:
        local = reference["profiles"][name]
        remote = published["profiles"][name]
        expected = {
            "static_target": local["static"]["target"]["worst_paid"],
            "static_identity": local["static"]["identity"]["worst_paid"],
            "static_all": local["all_queries_paid"],
            "adaptive_pure_target": local["adaptive"]["target"]["worst_paid"],
            "adaptive_pure_identity": local["adaptive"]["identity"]["worst_paid"],
            "online": local["online"]["target"]["worst_paid"],
            "online_identity": local["online"]["identity"]["worst_paid"],
            "structured_scores": local["online"]["target"]["worst_paid"],
        }
        published_values = {key: remote[key]["value"] for key in expected}
        if "fixed_schedule" in local:
            expected["online_fixed"] = local["fixed_schedule"]["target"]["worst_paid"]
            published_values["online_fixed"] = remote["online_fixed"]["value"]
        else:
            expected["online_fixed"] = None
            published_values["online_fixed"] = remote["online_fixed"]
        targets = sorted((row["edges"], row["intrinsic_cost"], row["target"]) for row in local["paths"])
        forecast_targets = sorted((row["path"], row["known_work"], row["label"]) for row in remote["targets"])
        compared.append(dict(profile=name, values=expected, intrinsic_targets=len(targets)))
        for field, (observed, independent) in {
            **{key: (published_values[key], value) for key, value in expected.items()},
            "intrinsic_targets": (forecast_targets, targets),
        }.items():
            try:
                equal(observed, independent, f"{name} sealed forecast {field}")
            except EvidenceError as error:
                failures.append(dict(profile=name, treatment="frozen-forecast", failure=str(error)))
    return dict(profiles=compared, discrepancies=failures)

def measure_public_solver(catalogue, output):
    """Keep raw same-process timing and separately measured Python allocation peaks."""
    results = []
    valid = set(catalogue["valid_profiles"])
    for profile in catalogue["profiles"]:
        if profile["id"] not in valid:
            continue
        stage = dict(profile=profile["id"], repeats=[])
        for index in range(3):
            started = time.perf_counter_ns()
            paths = enumerate_paths(profile)
            prepared = time.perf_counter_ns()
            solved = solve_online(profile, paths)
            elapsed = time.perf_counter_ns()
            tracemalloc.start()
            try:
                measured_paths = enumerate_paths(profile)
                prepare_peak = tracemalloc.get_traced_memory()[1]
                tracemalloc.reset_peak()
                measured = solve_online(profile, measured_paths)
                solve_peak = tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()
            equal(measured["worst_paid"], solved["worst_paid"], "timed and profiled exact result")
            stage["repeats"].append(dict(
                repetition=index + 1, prepare_ns=prepared - started, solve_ns=elapsed - prepared,
                prepare_peak_python_bytes=prepare_peak, solve_peak_python_bytes_including_prepared_paths=solve_peak,
                worst_paid=solved["worst_paid"], histories=solved["histories"],
                action_trials=solved["action_trials"],
            ))
        results.append(stage)
    save_json(output / "explicit-history-timing.json", dict(schema=1, profiles=results))


def opened(repo, opening_commit, output, deps):
    files, data, custody = opened_inputs(repo, opening_commit, output, deps)
    service = export_native(repo, custody["source_commit"], output / "service")
    batch = NativeBatch(service, files["catalogue"], files["authority"], output)
    profiles, combinations = profiles_and_paths(data["catalogue"])
    inventory = [(name, path) for name in profiles for path in combinations[name]]
    audit = audit_catalogue(batch, data, inventory)
    reference = json.loads((output / "reference.json").read_bytes())
    comparison = compare_forecast(data["catalogue"], reference, data["forecast"])
    audit["discrepancies"].extend(comparison["discrepancies"])
    measure_public_solver(data["catalogue"], output)
    return dict(mode="authenticated-opening", custody=custody, forecast_comparison=comparison, **audit)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    commands = parser.add_subparsers(dest="mode", required=True)
    training = commands.add_parser("train")
    training.add_argument("native_commit")
    training.add_argument("output", type=Path)
    opening = commands.add_parser("opened")
    opening.add_argument("opening_commit")
    opening.add_argument("output", type=Path)
    opening.add_argument("--drand-deps", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True)
    try:
        if args.mode == "train":
            result = train(args.repo.resolve(), args.native_commit, output)
        else:
            result = opened(args.repo.resolve(), args.opening_commit, output, args.drand_deps)
    except (EvidenceError, InvalidSignature, KeyError, OSError, ValueError, subprocess.SubprocessError) as error:
        failure = f"{type(error).__name__}: {error}"
        save_json(output / "failure.json", {"mode": args.mode, "failure": failure})
        print(f"Verification stopped. {failure}")
        return 1
    save_json(output / "report.json", result)
    print(f"{result['trials']} native trials, {len(result['discrepancies'])} discrepancies. Report {output / 'report.json'}")
    return int(bool(result["discrepancies"]))


if __name__ == "__main__":
    raise SystemExit(main())
