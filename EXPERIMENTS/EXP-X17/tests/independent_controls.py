"""Independent X17 falsification replay on explicit off-roster development installations."""

from fractions import Fraction as F
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT))
sys.path.insert(0, str(EXPERIMENT / "independent"))

from evidence import Evidence, coherent_signature, decoded
from model import Installation, forecast
from native import AuthorizationError, NativeService, NativeStore, World


DEV = Installation("independent-dev", F(33, 256), F(3, 512), 1, "L", "good", 7)
OPPOSITE = Installation("independent-opposite", 1 - DEV.theta, DEV.beta, DEV.m, DEV.k, "good", DEV.N)
BAD = Installation("independent-bad", DEV.theta, F(1, 2), DEV.m, DEV.k, "bad", DEV.N)


def deny(reason, callback, *args):
    try:
        callback(*args)
    except AuthorizationError as error:
        assert error.code == reason
    else:
        raise AssertionError("unauthorized occurrence was allowed: " + reason)


def plant(writer, case, world=DEV, guard=True):
    service = NativeService(World(world.theta, world.beta, world.m, world.k, world.B, world.N), writer, case)
    if guard:
        assert coherent_signature("source", service.check_source("guard"))
    return service


def play(writer, reader, service, name, raw_seed, world=DEV, issue=True, offer="high", guarded=True):
    attempt = service.new_attempt(name, raw_seed, require_guard=guarded)
    public = attempt.intake()
    receipt = public["route_receipt"]
    readout = attempt.probe(f"{offer}:{receipt['route']}", receipt)
    attempt.declare(issue)
    writer.flush()
    row = reader.attempt(name)
    return public, readout, row, decoded(reader, row, world)


def authority(writer, reader):
    bad = plant(writer, "C01", BAD)
    deny("good_guard_required", bad.new_attempt, "bad-rejected", 0)
    _, _, _, score = play(writer, reader, bad, "bad-raw", 5, BAD, guarded=False)
    assert score["finalized"]
    assert BAD.theta / 4 + BAD.beta > F(3, 8)

    suppressed = plant(writer, "C02", guard=False)
    assert "revision" not in suppressed.check_source("ordinary")
    deny("guard_receipt_suppressed", suppressed.check_source, "guard")
    deny("good_guard_required", suppressed.new_attempt, "suppressed", 0)

    for case in ("C03", "C04", "C18"):
        target = plant(writer, case).new_attempt(case, 0)
        receipt = target.intake()["route_receipt"]
        if case in ("C03", "C18"):
            deny("wrong_route", target.probe, "low:R", receipt)
        target.probe("low:L", receipt)
        if case == "C04":
            deny("repeated_probe", target.probe, "high:L", receipt)
        target.declare(False)
        writer.flush()
        row = reader.attempt(case)
        trace = row["trace"]
        assert trace["paid_eighths"] == 3 and len(trace["denials"]) == 1
        if case == "C18":
            assert trace["events"].index("denied") < trace["events"].index("probe")

    missing = plant(writer, "C05").new_attempt("C05", 0)
    public = missing.intake()
    assert public["route_receipt"] is None
    deny("missing_route_receipt", missing.probe, "high:L", None)
    assert missing.probe("skip", None) is None
    deny("missing_finish_authority", missing.declare, True)
    missing.declare(False)
    writer.flush()
    assert decoded(reader, reader.attempt("C05"), DEV)["intake_ok"]


def records(writer, reader):
    base = (plant(writer, None, DEV), plant(writer, None, OPPOSITE))
    dev_pair = [play(writer, reader, service, "matched-dev-" + world.id, 19, world, issue=False, offer="skip")[0]
                for service, world in zip(base, (DEV, OPPOSITE))]
    assert dev_pair[0] == dev_pair[1] and set(dev_pair[0]) == {"prelude", "route_receipt"}
    for case, extra in (("C06", "source_fact"), ("C07", "intake_batch_class")):
        changed = [play(writer, reader, plant(writer, case, world), case + world.id, 19,
                        world, issue=False, offer="skip")[0] for world in (DEV, OPPOSITE)]
        assert changed[0][extra] != changed[1][extra]
        for actual, permitted in zip(changed, dev_pair):
            assert {k: v for k, v in actual.items() if k != extra} == permitted

    normal = base[0].new_attempt("direct-unavailable", "same-dev")
    receipt = normal.intake()["route_receipt"]
    deny("direct_not_authorized", normal.probe, "direct:L", receipt)
    normal.abort()
    for expected, world in enumerate((DEV, OPPOSITE)):
        _, bit, row, _ = play(writer, reader, plant(writer, "C17", world), "direct-" + world.id, 27,
                              world, issue=expected == 0, offer="direct")
        assert bit == expected and row["trace"]["paid_eighths"] == 4
        assert coherent_signature("direct", row["trace"]["direct_attestation"])
    assert F(1, 3) * F(1, 2) == F(1, 6)


def physical(writer, reader):
    c08 = plant(writer, "C08")
    for seed in range(17):
        _, _, row, score = play(writer, reader, c08, f"anticipation-{seed}", seed)
        trace = row["trace"]
        assert trace["events"].index("final-draw") < trace["events"].index("proposal")
        draw = trace["draws"][-1]
        assert score["finish_violation"] == (F(draw["word"], draw["upper"]) < DEV.theta / 4 + DEV.beta + F(1, 16))

    changed = plant(writer, "C09")
    nominal = plant(writer, None)
    for seed in range(60):
        _, _, original, original_score = play(writer, reader, nominal, f"original-{seed}", seed)
        if not original_score["finish_violation"]:
            break
    else:
        raise AssertionError("no off-roster nondefective outcome")
    _, _, corrupted, corrupted_score = play(writer, reader, changed, "corrupted", seed)
    assert corrupted["trace"]["response"] == original["trace"]["response"]
    assert corrupted_score["destination"] == original_score["destination"] and corrupted_score["finish_violation"]

    omitted = plant(writer, "C10")
    for seed in range(100):
        _, _, _, score = play(writer, reader, omitted, f"support-{seed}", seed)
        if score["destination"] not in omitted.represented_finish_routes():
            break
    else:
        raise AssertionError("no real occurrence of the omitted supported output")

    _, _, _, unsafe = play(writer, reader, plant(writer, "C11"), "unsafe-intake", 0, issue=False)
    assert unsafe["intake_ok"] and unsafe["intake_violation"] and unsafe["V"] == 1 and unsafe["VI"] == 0

    reset = plant(writer, "C12")
    changes = 0
    for seed in range(18):
        _, _, row, _ = play(writer, reader, reset, f"reset-{seed}", seed)
        trace = row["trace"]
        assert trace["proposal"] == DEV.m and "continuation-reset" in trace["events"]
        changes += trace["proposal"] != DEV.m ^ trace["public_intake"]["prelude"][-1]
    assert changes > 0

    _, _, cancelled, score = play(writer, reader, plant(writer, "C13"), "cancelled", 0)
    assert score["I"] == 1 and not score["finalized"] and cancelled["final_digest"] is None

    shifted = plant(writer, "C14")
    deny("source_correspondence_failed", shifted.new_attempt, "shifted-denied", 0)
    _, _, row, score = play(writer, reader, shifted, "shifted-unchecked", 0, guarded=False)
    draw = row["trace"]["draws"][-1]
    threshold = DEV.theta / 4 + F(row["trace"]["proposal"], 16) + DEV.beta + F(1, 8)
    assert score["finish_violation"] == (F(draw["word"], draw["upper"]) < threshold)


def inferential(writer):
    monitor_world = Installation("independent-monitor-dev", DEV.theta, F(1, 32), DEV.m, DEV.k, "good", DEV.N)
    service = plant(writer, None, monitor_world)
    trace = next(seed for seed in range(200) if any(service.monitor(seed, 2)))
    assert service.monitor(trace, 2, "actual", True) == service.monitor(trace, 2, "nominal", True)
    assert service.monitor(trace, 2, "nominal", False) == (0, 0)
    assert 1 - F(31, 32)**2 == F(63, 1024) > F(1, 32)

    high = lambda beta: beta + (1 - beta) * F(29, 93)
    assert high(F(1, 32)) == F(1, 3)
    assert F(5, 8) + high(F(0)) / 8 == F(247, 372) < F(2, 3)
    e, a, eta = F(3, 8), F(1, 20), F(1, 20)
    assert e * a + (1 - e) * min(a, eta) == a
    assert forecast(DEV, "pcx")["I"] > 0


def main():
    with TemporaryDirectory(prefix="x17-independent-controls-") as scratch:
        database = Path(scratch) / "independent-controls.sqlite"
        with NativeStore(database) as writer, Evidence(database) as reader:
            authority(writer, reader)
            records(writer, reader)
            physical(writer, reader)
            inferential(writer)
    print("PASS independent C01-C19 native and mathematical controls on disjoint development sources.")


if __name__ == "__main__":
    main()
