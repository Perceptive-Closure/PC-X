"""Exercise selected registered controls on public, disjoint synthetic inputs."""

import json
import sys
from fractions import Fraction as F
from hashlib import sha256
from math import lcm
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory


THETA = F(33, 256)
BETA = F(3, 512)
DEPTH = 7
TAG = 1


def accepted(seed, purpose, index, limit):
    if limit == 1:
        return 0, 0
    seed_body = json.dumps(seed, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()
    key = sha256(b"PCX-EXP-X17-native-v1\0" + seed_body).digest()
    width = (limit - 1).bit_length()
    size = (width + 7) // 8
    assert size <= 32
    prefix = key + f"\0{purpose}\0{index}\0".encode("ascii")
    rejected = 0
    while True:
        block = sha256(prefix + f"{rejected}:0".encode("ascii")).digest()
        number = int.from_bytes(block[:size], "big") & ((1 << width) - 1)
        if number < limit:
            return number, rejected
        rejected += 1


def base_cut(seed):
    stay = (1 - THETA * (1 - THETA)) / 2
    state = 0
    for index in range(DEPTH):
        draw, _ = accepted(seed, "prelude", index, stay.denominator)
        state ^= int(draw >= stay.numerator)
    proposal = TAG ^ state
    nominal = THETA / 4 + F(proposal, 16)
    upper = lcm(nominal.denominator, (nominal + BETA).denominator)
    draw, rejected = accepted(seed, "final", 0, upper)
    return nominal, F(draw, upper), proposal, {
        "domain": "final", "index": 0, "upper": upper, "word": draw, "rejected": rejected
    }


def find_seed(purpose, predicate):
    for index in range(8192):
        seed = f"x17-hostile-development/{purpose}/{index}"
        if predicate(seed):
            return seed
    raise AssertionError(f"no deterministic witness in the fixed search range for {purpose}")


def opens(service, identifier, seed, mechanism="actual"):
    attempt = service.new_attempt(identifier, seed, mechanism=mechanism)
    public = attempt.intake()
    assert set(public) == {"prelude", "route_receipt"}
    return attempt, public


def finish(service, identifier, seed, mechanism="actual"):
    attempt, public = opens(service, identifier, seed, mechanism)
    receipt = public["route_receipt"]
    assert attempt.probe("skip:" + receipt["route"], receipt) is None
    attempt.declare(True)
    return public


def collect(store, database, world):
    from evidence import Evidence, decoded
    from native import NativeService, score_attempt
    from native.model import verify_signed

    def install(control=None):
        service = NativeService(world, store, control)
        receipt = service.check_source("guard")
        assert receipt["charge_eighths"] == 2 and receipt["revision"] == "good"
        return service

    base = install()
    safe = find_seed("safe", lambda seed: (pair := base_cut(seed))[1] >= pair[0] + BETA)
    mismatched = find_seed("strip", lambda seed: (pair := base_cut(seed))[0] <= pair[1] < pair[0] + BETA)
    pair_names = "paired-actual", "paired-nominal"
    assert finish(base, pair_names[0], mismatched) == finish(base, pair_names[1], mismatched, "nominal")
    rows = [store.read_attempt(name) for name in pair_names]
    shared_fields = ("public_intake", "events", "draws", "command", "response", "proposal", "authorized_route")
    assert all(rows[0]["trace"][key] == rows[1]["trace"][key] for key in shared_fields)
    assert rows[0]["trace"]["draws"][-1] == base_cut(mismatched)[3]
    assert rows[0]["trace"]["proposal"] == base_cut(mismatched)[2]
    assert rows[0]["final_digest"] != rows[1]["final_digest"]
    assert [score_attempt(store, name)["violating_issue"] for name in pair_names] == [True, False]

    omitted = install("C10")
    finish(omitted, "C10", mismatched)
    bad_destination = score_attempt(store, "C10")["actual_destination"]
    assert bad_destination == "R" and bad_destination not in omitted.represented_finish_routes()

    finish(install("C11"), "C11-issued", safe)
    cancelled = install("C13")
    finish(cancelled, "C13", safe)
    cancel_score = score_attempt(store, "C13")
    assert (cancel_score["issued"], cancel_score["finalized"], cancel_score["utility_halves"]) == (True, False, 1)

    c16 = {}
    for monitor_bit, desired_quality in ((0, "low"), (0, "high"), (1, "high")):
        name = f"C16-{monitor_bit}-{desired_quality}"
        monitor_seed = find_seed(
            name + "-monitor",
            lambda seed: int(accepted(seed, "monitor", 0, BETA.denominator)[0] < BETA.numerator) == monitor_bit,
        )
        policy_seed = find_seed(
            name + "-policy",
            lambda seed: monitor_bit == 1 or (Random(seed).randrange(93) < 29) == (desired_quality == "high"),
        )
        prefix = base.monitor_record(monitor_seed, 1)
        assert prefix["observations"] == (monitor_bit,)
        word, rejected = accepted(monitor_seed, "monitor", 0, BETA.denominator)
        assert prefix["draws"] == [
            {"domain": "monitor", "index": 0, "upper": BETA.denominator, "word": word, "rejected": rejected}
        ]
        quality = "high" if prefix["observations"][0] or Random(policy_seed).randrange(93) < 29 else "low"
        assert quality == desired_quality
        plant = name + "-plant"
        attempt, public = opens(base, name, plant)
        receipt = public["route_receipt"]
        response = attempt.probe(quality + ":" + receipt["route"], receipt)
        attempt.declare(response == 0)
        trace = store.read_attempt(name)["trace"]
        expected_mean = THETA if quality == "high" else F(1, 4) + THETA / 2
        assert response == int(accepted(plant, "probe", 0, expected_mean.denominator)[0] < expected_mean.numerator)
        assert trace["paid_eighths"] == (8 if quality == "high" else 3)
        c16[name] = {
            "monitor_seed": monitor_seed, "policy_seed": policy_seed,
            "monitor_bit": monitor_bit, "quality": quality,
            "paid_eighths": trace["paid_eighths"], "probe_response": response, "issued": response == 0,
        }

    theta_boundary = F(1, 4)
    choose_high = lambda beta: beta + (1 - beta) * F(29, 93)
    assert choose_high(F(1, 32)) == F(1, 3)
    h0 = choose_high(F(0))
    q0 = h0 * (1 - theta_boundary) + (1 - h0) * (F(3, 4) - theta_boundary / 2)
    assert q0 == F(247, 372) < F(2, 3)

    c17 = {}
    diagnostic = install("C17")
    for desired in ("direct", "skip-positive", "skip-negative"):
        name = "C17-" + desired

        def action(seed):
            rng = Random(seed)
            if rng.randrange(3) == 0:
                return "direct"
            return "skip-positive" if rng.randrange(2) == 0 else "skip-negative"

        private_seed = find_seed(name + "-policy", lambda seed: action(seed) == desired)
        rng = Random(private_seed)
        quality = "direct" if rng.randrange(3) == 0 else "skip"
        attempt, public = opens(diagnostic, name, name + "-plant")
        receipt = public["route_receipt"]
        response = attempt.probe(quality + ":" + receipt["route"], receipt)
        verdict = response == 0 if quality == "direct" else rng.randrange(2) == 0
        attempt.declare(verdict)
        trace = store.read_attempt(name)["trace"]
        if quality == "direct":
            assert response == 0 and verify_signed("direct", trace["direct_attestation"])
            assert trace["direct_attestation"]["installation_digest"] == trace["installation_digest"]
            assert trace["direct_attestation"]["command"] == trace["command"]
        else:
            assert response is None
        assert trace["paid_eighths"] == (4 if quality == "direct" else 0)
        c17[name] = {"policy_seed": private_seed, "quality": quality,
                     "paid_eighths": trace["paid_eighths"], "probe_response": response, "issued": verdict}

    store.flush()
    with Evidence(database) as reader:
        early = score_attempt(store, "C11-issued")
        alternate = decoded(reader, reader.attempt("C11-issued"), world)
        assert early["intake_complete"] and early["intake_violation"] and not early["finish_violation"]
        assert early["issued"] and early["violation"] and early["violating_issue"]
        assert (alternate["I"], alternate["V"], alternate["VI"]) == (1, 1, 1)
        assert early["utility_halves"] == 2 and alternate["G"] == F(1, 2)

    return {
        "fixture": world.raw(),
        "base_pair": {"seed": mismatched, "actual_VI": 1, "nominal_VI": 0,
                      "paired_draw": rows[0]["trace"]["draws"][-1]},
        "C10": {"actual_destination": bad_destination, "retained_destinations": ["L"]},
        "C11": {"seed": safe, "I": 1, "V": 1, "VI": 1, "final_leg_violation": False,
                "native_G": "1", "independent_G": "1/2"},
        "C13": {"issued": True, "finalized": False, "utility": "1/2"},
        "C16": {"deterministic_path_witnesses": c16, "beta_zero_boundary_I": str(q0),
                "beta_max_high_choice": "1/3"},
        "C17": {"deterministic_path_witnesses": c17, "exact_expected_charge": str(F(1, 3) * F(1, 2))},
    }


def main(source, scratch):
    sys.path[:0] = [str(source), str(source / "independent")]
    from native import NativeStore, World
    fixture = World(THETA, BETA, TAG, "L", "good", DEPTH)
    with TemporaryDirectory(dir=scratch) as path:
        db = Path(path) / "development.sqlite"
        with NativeStore(db) as store:
            evidence = collect(store, db, fixture)
    print(json.dumps(evidence, indent=2, sort_keys=True))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
