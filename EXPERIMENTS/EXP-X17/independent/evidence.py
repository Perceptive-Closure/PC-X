"""Read committed native SQLite bytes and score actual staged and routed artifacts."""

from collections import defaultdict
from fractions import Fraction as F
from functools import lru_cache
from hashlib import sha256
from hmac import new as mac, compare_digest
import json
from math import lcm
import sqlite3
import zlib

from model import PRICES, bit_one, final_probability, stay_probability


TEST_KEY = b"PCX EXP-X17 PUBLIC SYNTHETIC SOURCE KEY V1"
DECLARED_STAGES = ("opened", "prelude", "reconciled", "receipt-delivered", "probe", "declaration")
ISSUED_STAGES = ("finalizer-authorized", "finalizer-invoked", "proposal", "final-draw", "finalizer-committed")


class EvidenceError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def canonical(record):
    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


class Evidence:
    def __init__(self, database):
        self.connection = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        self.close()

    def close(self):
        self.connection.close()
        self.artifact.cache_clear()

    @lru_cache(maxsize=128)
    def artifact(self, digest):
        data = self.connection.execute("SELECT body FROM artifacts WHERE digest=?", (digest,)).fetchone()
        require(data is not None, "missing linked content")
        body = data[0]
        require(sha256(body).hexdigest() == digest, "artifact commitment differs")
        return json.loads(body)

    def attempt(self, name):
        row = self.connection.execute(
            "SELECT mechanism,source_digest,intake_digest,final_digest,trace FROM attempts WHERE attempt_id=?",
            (name,),
        ).fetchone()
        require(row is not None, "missing durable attempt")
        mechanism, source, intake, final, trace = row
        encoded = zlib.decompress(trace)
        return {"mechanism": mechanism, "source_digest": source, "intake_digest": intake,
                "final_digest": final, "trace": json.loads(encoded), "trace_sha256": sha256(encoded).hexdigest()}


def coherent_signature(kind, receipt):
    payload = {key: value for key, value in receipt.items() if key != "signature"}
    signature = mac(TEST_KEY, kind.encode("ascii") + b"\x00" + canonical(payload), sha256).hexdigest()
    return compare_digest(signature, receipt.get("signature", ""))


def decoded(evidence, row, world):
    source = evidence.artifact(row["source_digest"])
    intake = evidence.artifact(row["intake_digest"])
    trace = row["trace"]
    installation = evidence.artifact(trace["installation_digest"])
    fields = {"theta": str(world.theta), "beta": str(world.beta), "m": world.m,
              "k": world.k, "B": world.B, "N": world.N}
    require(installation == {
        "schema": "x17-install-v1",
        "world": fields,
        "ordinary_reference": {
            "operation": "ordinary-routing-v1", "defect_probability": str(world.theta), "cutoff": "1/2",
        },
    } and trace["world"] == fields, "installed-world links differ")
    route = source["routing"][source["zone"]]
    require(route == source["expected_route"] == world.k, "authoritative source route differs")
    counts = defaultdict(int, {sku: 0 for sku in source["book"]})
    seen = set()
    for scan in source["scans"]:
        lot, sku, amount = scan["lot"], scan["sku"], scan["quantity"]
        require(lot not in seen and sku in counts and type(amount) is int and amount >= 0, "stock scan invalid")
        seen.add(lot)
        counts[sku] += amount
    counts = dict(counts)
    variance = {sku: counts[sku] - source["book"][sku] for sku in counts}
    useful_intake = (intake.get("inventory") == counts and intake.get("variance") == variance
                     and intake.get("source_digest") == row["source_digest"])
    intake_violation = intake.get("staging_destination") != route
    issued = trace["declaration"] is True
    finalized = row["final_digest"] is not None
    finish_violation = False
    destination = None
    if finalized:
        final = evidence.artifact(row["final_digest"])
        destination = final.get("destination")
        finish_violation = (destination != route or final.get("inventory") != counts
                            or final.get("intake_digest") != row["intake_digest"])
    positive = F(installation["ordinary_reference"]["defect_probability"]) <= F(1, 2)
    violation = intake_violation or finish_violation
    useful_finish = issued and finalized and not violation and useful_intake
    return {
        "I": int(issued), "V": int(violation), "VI": int(issued and violation),
        "wrong": int(issued != positive), "G": F(int(useful_intake) + int(positive and useful_finish), 2),
        "cost": F(trace["paid_eighths"], 8), "Z": F(int(issued and violation)) - F(3, 8) * int(issued),
        "intake_ok": useful_intake, "intake_violation": intake_violation, "finalized": finalized,
        "finish_violation": finish_violation, "destination": destination,
    }


def random_word(seed, domain, index, limit, recorded_rejections):
    key = sha256(b"PCX-EXP-X17-native-v1\x00" + canonical(seed)).digest()
    prefix = b"\x00".join((key, domain.encode("ascii"), str(index).encode("ascii"), b""))
    bits = (limit - 1).bit_length()
    if bits == 0:
        require(recorded_rejections == 0, "deterministic draw has a rejection")
        return 0
    size = (bits + 7) // 8
    for rejection in range(recorded_rejections + 1):
        data = b"".join(
            sha256(prefix + (str(rejection) + ":" + str(block)).encode("ascii")).digest()
            for block in range((size + 31) // 32)
        )
        number = int.from_bytes(data[:size], "big") & ((1 << bits) - 1)
        if number < limit:
            require(rejection == recorded_rejections, "unreported earlier acceptance")
            return number
    raise EvidenceError("draw never reaches recorded acceptance")


def checked_draw(draw, seed, domain, index, upper):
    require(draw["domain"] == domain and draw["index"] == index and draw["upper"] == upper,
            "chance support or draw provenance differs")
    word, rejected = draw["word"], draw["rejected"]
    require(type(word) is int and 0 <= word < upper and type(rejected) is int and rejected >= 0,
            "accepted word or rejection count invalid")
    require(random_word(seed, domain, index, upper, rejected) == word, "accepted draw replay differs")
    return word


def certify_admitted(evidence, row, world, seed, command, decision):
    world.check_good()
    trace = row["trace"]
    score = decoded(evidence, row, world)
    require(trace["seed"] == seed and trace["control"] is None and trace["guard_required"] is True
            and trace["status"] == "completed" and not trace["denials"], "not an admitted completed attempt")
    require(len(trace["source_checks"]) == 1, "unexpected source check history")
    guard = trace["source_checks"][0]
    require(set(guard) == {"check", "charge_eighths", "revision", "surcharge_bounds", "signature"}
            and coherent_signature("source", guard)
            and guard["check"] == "guard" and guard["charge_eighths"] == 2
            and guard["revision"] == "good" and guard["surcharge_bounds"] == ["0", "1/32"],
            "invalid guard source receipt")
    public = trace["public_intake"]
    require(set(public) == {"prelude", "route_receipt"}, "unexpected delivered information")
    receipt = public["route_receipt"]
    require(set(receipt) == {"route", "intake_digest", "signature"}
            and receipt["route"] == world.k and receipt["intake_digest"] == row["intake_digest"]
            and coherent_signature("route", receipt), "route receipt is not anchored to actual work")
    require(score["intake_ok"] and not score["intake_violation"], "initial work did not reconcile and stage correctly")
    offer, _, route = command.partition(":")
    require(route == world.k and offer in PRICES and trace["command"] == command
            and score["cost"] == PRICES[offer] and trace["declaration"] is decision,
            "literal, charge or verdict differs from the executed policy")

    draws = iter(trace["draws"])
    last = 0
    stay = stay_probability(world)
    delivered_word = []
    for j in range(world.N):
        take = checked_draw(next(draws), seed, "prelude", j, stay.denominator)
        last ^= int(take >= stay.numerator)
        delivered_word.append(last)
    require(public["prelude"] == delivered_word, "carried prelude record differs")
    response = None
    if offer != "skip":
        mean = bit_one(world.theta, offer)
        response = int(checked_draw(next(draws), seed, "probe", 0, mean.denominator) < mean.numerator)
    require(trace["response"] == response, "probe record differs from the trusted draw")

    require(trace["events"] == list(DECLARED_STAGES + (ISSUED_STAGES if decision else ())),
            "execution ordering or actual finalization differs")
    require(score["finalized"] is decision, "authority changed without exactly one completed finish")
    if decision:
        require(trace["authorized_route"] == world.k and trace["proposal"] == world.m ^ last,
                "post-verdict route or carried proposal differs")
        actual = final_probability(world, last)
        nominal = final_probability(world, last, "nominal")
        upper = lcm(actual.denominator, nominal.denominator)
        u = F(checked_draw(next(draws), seed, "final", 0, upper), upper)
        cut = actual if row["mechanism"] == "actual" else nominal
        require(score["finish_violation"] == (u < cut), "physical event differs from actual protected source")
    else:
        require(trace["proposal"] is None and trace["authorized_route"] is None, "hidden activation")
    require(next(draws, None) is None, "unexpected positive-support transition")
    return score
