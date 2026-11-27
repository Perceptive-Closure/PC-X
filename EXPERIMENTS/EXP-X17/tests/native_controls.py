"""Deterministic X17 developer controls on explicitly non-roster fixtures."""

import json
import sys
import tempfile
from fractions import Fraction as Q
from itertools import product
from pathlib import Path

EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT))

from native import (  # noqa: E402
    AuthorizationError, NativeService, NativeStore, World, reconstruct_draw,
    score_attempt, verify_receipt, verify_source_receipt,
)


DEV = World(Q(33, 256), Q(3, 512), 1, "L", "good", 7)
DEV_OPPOSITE = World(1 - DEV.theta, DEV.beta, DEV.m, DEV.k, DEV.B, DEV.N)
DEV_BAD = World(DEV.theta, Q(1, 2), DEV.m, DEV.k, "bad", DEV.N)


def rejected(code, action, *args):
    try:
        action(*args)
    except AuthorizationError as exception:
        assert exception.code == code, (code, exception.code)
    else:
        raise AssertionError(f"expected authorization rejection {code}")


def install(store, world=DEV, control=None, guard=True):
    service = NativeService(world, store, control)
    if guard:
        assert verify_source_receipt(service.check_source("guard"))
    return service


def finish(service, key, seed, positive=True, mechanism="actual", quality="high", guarded=True):
    attempt = service.new_attempt(key, seed, mechanism=mechanism, require_guard=guarded)
    public = attempt.intake()
    response = attempt.probe(f"{quality}:{public['route_receipt']['route']}", public["route_receipt"])
    attempt.declare(positive)
    return public, response


def trace_for(store, key):
    return store.read_attempt(key)["trace"]


def check_durable_and_transport(store):
    service = install(store)
    for seed in range(64):
        key = f"paired-{seed}"
        assert finish(service, key, seed) == finish(service, f"{key}-nominal", seed, mechanism="nominal")
        actual, nominal = (trace_for(store, name) for name in (key, f"{key}-nominal"))
        assert actual["draws"] == nominal["draws"]
        assert actual["events"].index("declaration") < actual["events"].index("proposal")
        assert actual["events"].index("proposal") < actual["events"].index("final-draw")
        assert actual["events"].count("finalizer-invoked") == 1
        assert actual["proposal"] == DEV.m ^ actual["public_intake"]["prelude"][-1]
        row = actual["draws"][-1]
        uniform = Q(row["word"], row["upper"])
        nominal_cut = DEV.theta / 4 + Q(actual["proposal"], 16)
        assert score_attempt(store, key)["finish_violation"] == (uniform < nominal_cut + DEV.beta)
        assert score_attempt(store, f"{key}-nominal")["finish_violation"] == (uniform < nominal_cut)
        for recorded in actual["draws"]:
            word = reconstruct_draw(actual["seed"], recorded["domain"], recorded["index"], recorded["upper"])
            assert word == (recorded["word"], recorded["rejected"])
    assert {trace_for(store, f"paired-{seed}")["proposal"] for seed in range(64)} == {0, 1}
    service.ordinary("ordinary-dev", 41)
    ordinary = trace_for(store, "ordinary-dev")
    assert ordinary["declaration"] is None and ordinary["public_intake"] is None
    draw = ordinary["draws"][0]
    assert score_attempt(store, "ordinary-dev")["violation"] == (Q(draw["word"], draw["upper"]) < DEV.theta)
    assert service.monitor("monitor-dev", 8) == service.monitor("monitor-dev", 8, mechanism="nominal")


def check_private_boundary(store):
    # This enumerates a mathematical probability identity at the registered
    # least favorable endpoints. It runs no stochastic endpoint attempts.
    endpoint_low = World(Q(1, 4), DEV.beta, DEV.m, DEV.k, DEV.B, DEV.N)
    endpoint_high = World(Q(3, 4), DEV.beta, DEV.m, DEV.k, DEV.B, DEV.N)
    assert endpoint_low.stay_probability == endpoint_high.stay_probability
    for stays in product((0, 1), repeat=DEV.N):
        served_weights = []
        for world in (endpoint_low, endpoint_high):
            p = world.stay_probability
            served_weights.append(p**sum(stays) * (1 - p)**(DEV.N - sum(stays)))
        assert served_weights[0] == served_weights[1]
    left, right = (NativeService(world, store) for world in (endpoint_low, endpoint_high))
    for name in ("ordinary", "guard", "full"):
        assert left.check_source(name) == right.check_source(name)

    # The executable coupled endpoint-format test uses two non-roster
    # complementary development installations with different private IDs.
    low, high = (install(store, world) for world in (DEV, DEV_OPPOSITE))
    p1, _ = finish(low, "dev-positive-secret-id", "matched-dev", positive=False, quality="skip")
    p2, _ = finish(high, "dev-negative-secret-id", "matched-dev", positive=False, quality="skip")
    assert p1 == p2
    assert set(p1) == {"prelude", "route_receipt"}
    assert set(p1["route_receipt"]) == {"route", "intake_digest", "signature"}
    assert verify_receipt(p1["route_receipt"])


def check_read_and_authority_controls(store):
    bad = install(store, DEV_BAD, "C01")
    assert bad.check_source("guard")["surcharge_bounds"] == ["1/2", "1/2"]
    rejected("good_guard_required", bad.new_attempt, "bad-block", 0)
    finish(bad, "bad-lab", 0, guarded=False)
    assert not trace_for(store, "bad-lab")["guard_required"]

    suppressed = install(store, control="C02", guard=False)
    assert set(suppressed.check_source("ordinary")) == {"check", "charge_eighths", "ordinary_spec", "signature"}
    rejected("guard_receipt_suppressed", suppressed.check_source, "guard")
    rejected("good_guard_required", suppressed.new_attempt, "no-guard", 0)

    for control in ("C03", "C04", "C18"):
        attempt = install(store, control=control).new_attempt(control, 0)
        public = attempt.intake()
        receipt = public["route_receipt"]
        if control in ("C03", "C18"):
            rejected("wrong_route", attempt.probe, "high:R", receipt)
        assert attempt.probe("low:L", receipt) in (0, 1)
        if control == "C04":
            rejected("repeated_probe", attempt.probe, "high:L", receipt)
        attempt.declare(False)
        assert trace_for(store, control)["paid_eighths"] == 3
        assert len(trace_for(store, control)["denials"]) == 1

    no_receipt = install(store, control="C05").new_attempt("C05", 0)
    assert no_receipt.intake()["route_receipt"] is None
    rejected("missing_route_receipt", no_receipt.probe, "high:L", None)
    assert no_receipt.probe("skip", None) is None
    rejected("missing_finish_authority", no_receipt.declare, True)
    no_receipt.declare(False)
    assert score_attempt(store, "C05")["intake_complete"]

    for control, leak in (("C06", "source_fact"), ("C07", "intake_batch_class")):
        positive = finish(install(store, control=control), control + "+", 0, positive=False, quality="skip")[0]
        negative = finish(install(store, DEV_OPPOSITE, control), control + "-", 0, positive=False, quality="skip")[0]
        assert positive[leak] != negative[leak]
        assert {key: val for key, val in positive.items() if key != leak} == {
            key: val for key, val in negative.items() if key != leak
        }

    baseline = install(store).new_attempt("direct-forbidden", 0)
    public = baseline.intake()
    rejected("direct_not_authorized", baseline.probe, "direct:L", public["route_receipt"])
    baseline.abort()
    for index, world in enumerate((DEV, DEV_OPPOSITE)):
        service = install(store, world, "C17")
        _, bit = finish(service, f"direct-{index}", index, positive=not index, quality="direct")
        assert bit == index
        trace = trace_for(store, f"direct-{index}")
        assert trace["paid_eighths"] == 4 and trace["direct_attestation"]["response"] == bit


def check_physical_controls(store):
    normal = install(store)
    c08 = install(store, control="C08")
    strip = DEV.theta / 4 + DEV.beta
    for seed in range(32):
        key = f"C08-{seed}"
        finish(c08, key, seed)
        trace = trace_for(store, key)
        assert trace["events"].index("final-draw") < trace["events"].index("proposal")
        row = trace["draws"][-1]
        uniform = Q(row["word"], row["upper"])
        assert trace["proposal"] == int(strip <= uniform < strip + Q(1, 16))
        assert score_attempt(store, key)["finish_violation"] == (uniform < strip + Q(1, 16))
    for word in range(row["upper"]):
        uniform = Q(word, row["upper"])
        proposal = int(strip <= uniform < strip + Q(1, 16))
        assert (uniform < strip + Q(proposal, 16)) == (uniform < strip + Q(1, 16))

    c09 = install(store, control="C09")
    assert finish(c09, "C09", 9) == finish(normal, "C09-base", 9)
    row = store.read_attempt("C09")
    intake = json.loads(store.read_artifact(row["intake_digest"]))
    final = json.loads(store.read_artifact(row["final_digest"]))
    first_sku = min(intake["inventory"])
    assert final["inventory"][first_sku] == intake["inventory"][first_sku] + 1
    assert score_attempt(store, "C09")["finish_violation"]

    c10 = install(store, control="C10")
    assert c10.represented_finish_routes() == ("L",)
    witness = None
    for seed in range(256):
        key = f"C10-{seed}"
        finish(c10, key, seed)
        if score_attempt(store, key)["actual_destination"] == "R":
            witness = key
            break
    assert witness is not None

    finish(install(store, control="C11"), "C11", 0, positive=False)
    score = score_attempt(store, "C11")
    assert score["intake_complete"] and score["intake_violation"] and score["violation"] and not score["issued"]
    assert score["utility_halves"] == 1

    c12 = install(store, control="C12")
    changed = False
    for seed in range(64):
        key = f"C12-{seed}"
        finish(c12, key, seed)
        trace = trace_for(store, key)
        assert trace["proposal"] == DEV.m and "continuation-reset" in trace["events"]
        changed |= bool(trace["public_intake"]["prelude"][-1])
    assert changed

    finish(install(store, control="C13"), "C13", 0)
    score = score_attempt(store, "C13")
    assert score["issued"] and not score["finalized"] and score["utility_halves"] == 1
    assert "finalizer-cancelled" in trace_for(store, "C13")["events"]

    c14 = install(store, control="C14")
    rejected("source_correspondence_failed", c14.new_attempt, "C14", 0)
    finish(c14, "C14", 0, guarded=False)
    trace = trace_for(store, "C14")
    draw = trace["draws"][-1]
    cut = DEV.theta / 4 + Q(trace["proposal"], 16) + DEV.beta + Q(1, 8)
    assert score_attempt(store, "C14")["finish_violation"] == (Q(draw["word"], draw["upper"]) < cut)


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(dir=EXPERIMENT / "native", prefix="dev-native-") as temp:
        database = Path(temp) / "development.sqlite"
        with NativeStore(database, batch_size=23) as writer:
            check_durable_and_transport(writer)
            check_private_boundary(writer)
            check_read_and_authority_controls(writer)
            check_physical_controls(writer)
        with NativeStore(database) as reader:
            assert score_attempt(reader, "ordinary-dev")["finalized"]
            assert score_attempt(reader, "C11")["intake_violation"]
            assert trace_for(reader, "C13")["declaration"] is True
            assert len(tuple(reader.iter_attempts())) >= 200
    print("Native development controls passed for separate baselines, durability, and C01-C14/C17/C18.")
