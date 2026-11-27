"""The local, synthetic U.G3 source and its phase-specific authority."""

import json
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from math import lcm

from .model import (
    CHECK_EIGHTHS,
    CONTROLS,
    PRICE_EIGHTHS,
    ROUTES,
    World,
    _private_key,
    draw_word,
    immutable_stock,
    normalized_seed,
    signed_record,
    verify_signed,
)
from .store import canonical_json


_ORDINARY_SPEC = {
    "primitive": "ordinary-routing-v1",
    "violation_law": "Bernoulli(theta)",
    "label_cutoff": "1/2",
}
_REVISION_BOUNDS = {"good": ["0", "1/32"], "bad": ["1/2", "1/2"]}


class AuthorizationError(RuntimeError):
    """A closed-menu rejection. Its code contains no private source value."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def verify_receipt(receipt):
    return (
        isinstance(receipt, dict)
        and set(receipt) == {"route", "intake_digest", "signature"}
        and receipt.get("route") in ROUTES
        and isinstance(receipt.get("intake_digest"), str)
        and len(receipt["intake_digest"]) == 64
        and verify_signed("route", receipt)
    )


def verify_source_receipt(receipt):
    if not isinstance(receipt, dict) or not verify_signed("source", receipt):
        return False
    kind = receipt.get("check")
    if not isinstance(kind, str) or kind not in CHECK_EIGHTHS or receipt.get("charge_eighths") != CHECK_EIGHTHS[kind]:
        return False
    expected = {"check", "charge_eighths", "signature"}
    if kind in ("ordinary", "full"):
        expected.add("ordinary_spec")
        if receipt.get("ordinary_spec") != _ORDINARY_SPEC:
            return False
    if kind in ("guard", "full"):
        expected.update(("revision", "surcharge_bounds"))
        revision = receipt.get("revision")
        if not isinstance(revision, str) or revision not in _REVISION_BOUNDS or receipt.get("surcharge_bounds") != _REVISION_BOUNDS[revision]:
            return False
    return set(receipt) == expected


def _opposite(route):
    return "R" if route == "L" else "L"


def _inventory(stock):
    counts = Counter()
    seen = set()
    for scan in stock["scans"]:
        lot, sku, quantity = scan["lot"], scan["sku"], scan["quantity"]
        if lot in seen or sku not in stock["book"] or type(quantity) is not int or quantity < 0:
            raise ValueError("invalid synthetic stock scan")
        seen.add(lot)
        counts[sku] += quantity
    return {sku: counts[sku] for sku in stock["book"]}


class NativeService:
    """Install one fixed source. The outer runner passes no service handle to a controller."""

    def __init__(self, world, store, control=None):
        if not isinstance(world, World):
            raise TypeError("an immutable World is required")
        if control is not None and control not in CONTROLS:
            raise ValueError("unknown isolated native control")
        if control == "C01" and world.B != "bad":
            raise ValueError("C01 requires a bad installed revision")
        self._world = world
        self._store = store
        self._control = control
        _, self._stock_bytes = immutable_stock(world.k)
        self._checks = []
        self._installation_bytes = canonical_json({
            "schema": "x17-install-v1",
            "world": world.raw(),
            "ordinary_reference": {
                "operation": "ordinary-routing-v1",
                "defect_probability": str(world.theta),
                "cutoff": "1/2",
            },
        })

    def check_source(self, kind):
        if kind not in CHECK_EIGHTHS:
            raise AuthorizationError("unknown_source_check")
        if self._control == "C02" and kind != "ordinary":
            raise AuthorizationError("guard_receipt_suppressed")
        payload = {"check": kind, "charge_eighths": CHECK_EIGHTHS[kind]}
        if kind in ("ordinary", "full"):
            payload["ordinary_spec"] = deepcopy(_ORDINARY_SPEC)
        if kind in ("guard", "full"):
            payload["revision"] = self._world.B
            payload["surcharge_bounds"] = list(_REVISION_BOUNDS[self._world.B])
        receipt = signed_record("source", payload)
        self._checks.append(receipt)
        return deepcopy(receipt)

    def new_attempt(self, attempt_id, seed, mechanism="actual", require_guard=True):
        if mechanism not in ("actual", "nominal"):
            raise AuthorizationError("unknown_governed_mechanism")
        if type(require_guard) is not bool:
            raise TypeError("require_guard must be a boolean")
        if require_guard:
            if self._control == "C14":
                raise AuthorizationError("source_correspondence_failed")
            if not any(
                check.get("revision") == "good" and verify_source_receipt(check)
                for check in self._checks
            ):
                raise AuthorizationError("good_guard_required")
        return self._start(attempt_id, seed, mechanism, require_guard)

    def _start(self, attempt_id, seed, mechanism, require_guard):
        if not isinstance(attempt_id, str) or not attempt_id:
            raise TypeError("attempt_id must be nonempty text")
        digest = self._store.put_artifact(self._stock_bytes)
        return NativeAttempt(
            self._world,
            self._store,
            self._control,
            deepcopy(self._checks),
            attempt_id,
            seed,
            mechanism,
            digest,
            self._store.put_artifact(self._installation_bytes),
            require_guard,
        )

    def ordinary(self, attempt_id, seed):
        """Run the fixed intrinsic target protocol outside the governed menu."""
        attempt = self._start(attempt_id, seed, "ordinary", False)
        attempt._write_intake()
        attempt._events.append("ordinary-invoked")
        defective = attempt._bernoulli("ordinary", 0, self._world.theta)
        attempt._write_final(bool(defective))
        attempt._events.append("ordinary-committed")
        attempt._archive("completed")

    def monitor_record(self, seed, n, mechanism="actual", matched=True):
        """Keep upstream optional monitoring distinct from a governed attempt."""
        if type(n) is not int or n < 0:
            raise ValueError("monitor count must be a nonnegative integer")
        if mechanism not in ("actual", "nominal") or type(matched) is not bool:
            raise ValueError("invalid monitor scope")
        mean = self._world.beta if matched or mechanism == "actual" else Fraction(0)
        seed_record = normalized_seed(seed)
        key = _private_key(seed_record)
        observations = []
        draws = []
        for index in range(n):
            word, rejected = draw_word(key, "monitor", index, mean.denominator)
            draws.append(_draw_receipt("monitor", index, mean.denominator, word, rejected))
            observations.append(int(word < mean.numerator))
        return {"seed": seed_record, "observations": tuple(observations), "draws": draws}

    def monitor(self, seed, n, mechanism="actual", matched=True):
        return self.monitor_record(seed, n, mechanism, matched)["observations"]

    def represented_finish_routes(self):
        """Expose the registered modeled support, with C10's deliberate omission."""
        return (self._world.k,) if self._control == "C10" else ROUTES


def _draw_receipt(domain, index, upper, word, rejected):
    return {"domain": domain, "index": index, "upper": upper, "word": word, "rejected": rejected}


class NativeAttempt:
    """Complete one audited attempt and commit a separate private ledger."""

    def __init__(self, world, store, control, checks, attempt_id, seed, mechanism, source_digest, installation_digest, guarded):
        self._world = world
        self._store = store
        self._control = control
        self._attempt_id = attempt_id
        self._mechanism = mechanism
        self._source_digest = source_digest
        self._intake_digest = None
        self._final_digest = None
        self._receipt = None
        self._phase = "opened"
        self._v = 0
        seed_record = normalized_seed(seed)
        self._key = _private_key(seed_record)
        self._events = ["opened"]
        self._trace = {
            "version": 1,
            "control": control,
            "installation_digest": installation_digest,
            "world": world.raw(),
            "seed": seed_record,
            "source_checks": checks,
            "guard_required": guarded,
            "events": self._events,
            "draws": [],
            "public_intake": None,
            "command": None,
            "response": None,
            "paid_eighths": 0,
            "declaration": None,
            "authorized_route": None,
            "proposal": None,
            "denials": [],
        }

    def _deny(self, code):
        self._trace["denials"].append(code)
        self._events.append("denied")
        raise AuthorizationError(code)

    def _draw(self, domain, index, upper):
        word, rejected = draw_word(self._key, domain, index, upper)
        self._trace["draws"].append(_draw_receipt(domain, index, upper, word, rejected))
        return word

    def _bernoulli(self, domain, index, mean):
        return int(self._draw(domain, index, mean.denominator) < mean.numerator)

    def _write_intake(self):
        stock = json.loads(self._store.read_artifact(self._source_digest))
        counts = _inventory(stock)
        route = stock["routing"][stock["zone"]]
        staging = _opposite(route) if self._control == "C11" and self._mechanism != "ordinary" else route
        reconciliation = {
            "source_digest": self._source_digest,
            "inventory": counts,
            "variance": {sku: counts[sku] - booked for sku, booked in stock["book"].items()},
            "staging_destination": staging,
        }
        self._intake_digest = self._store.put_artifact(canonical_json(reconciliation))
        self._events.append("reconciled")
        return route

    def intake(self):
        if self._phase != "opened":
            self._deny("intake_already_started")
        prelude = []
        stay = self._world.stay_probability
        for index in range(self._world.N):
            if not self._bernoulli("prelude", index, stay):
                self._v ^= 1
            prelude.append(self._v)
        self._events.append("prelude")
        route = self._write_intake()
        if self._control != "C05":
            self._receipt = signed_record("route", {"route": route, "intake_digest": self._intake_digest})
            self._events.append("receipt-delivered")

        public = {"prelude": tuple(prelude), "route_receipt": deepcopy(self._receipt)}
        if self._control == "C06":
            public["source_fact"] = "positive" if self._world.target else "negative"
        if self._control == "C07":
            public["intake_batch_class"] = "alpha" if self._world.target else "beta"
        self._trace["public_intake"] = deepcopy(public)
        self._phase = "intake"
        return public

    def probe(self, command, receipt):
        if self._phase == "probed":
            self._deny("repeated_probe")
        if self._phase != "intake":
            self._deny("probe_out_of_phase")
        if not isinstance(command, str):
            self._deny("invalid_literal")
        if self._receipt is None:
            if command != "skip" or receipt is not None:
                self._deny("missing_route_receipt")
            quality = "skip"
        else:
            if not verify_receipt(receipt) or receipt != self._receipt:
                self._deny("invalid_route_receipt")
            quality, separator, route = command.partition(":")
            if not separator or quality not in PRICE_EIGHTHS:
                self._deny("invalid_literal")
            if route != self._receipt["route"]:
                self._deny("wrong_route")
            if quality == "direct" and self._control != "C17":
                self._deny("direct_not_authorized")

        response = None
        if quality == "low":
            response = self._bernoulli("probe", 0, Fraction(1, 4) + self._world.theta / 2)
        elif quality == "high":
            response = self._bernoulli("probe", 0, self._world.theta)
        elif quality == "direct":
            installed = json.loads(self._store.read_artifact(self._trace["installation_digest"]))
            reference = installed["ordinary_reference"]
            response = int(Fraction(reference["defect_probability"]) > Fraction(reference["cutoff"]))
            self._trace["direct_attestation"] = signed_record("direct", {
                "command": command, "response": response, "installation_digest": self._trace["installation_digest"]
            })
        self._trace["command"] = command
        self._trace["response"] = response
        self._trace["paid_eighths"] = PRICE_EIGHTHS[quality]
        self._events.append("probe")
        self._phase = "probed"
        return response

    def declare(self, positive):
        if self._phase != "probed":
            self._deny("declaration_out_of_phase")
        if type(positive) is not bool:
            self._deny("invalid_declaration")
        if positive and self._receipt is None:
            self._deny("missing_finish_authority")
        self._trace["declaration"] = positive
        self._events.append("declaration")
        if positive:
            self._trace["authorized_route"] = self._receipt["route"]
            self._events.append("finalizer-authorized")
            if self._control == "C13":
                self._events.append("finalizer-cancelled")
            else:
                self._finish()
        self._archive("completed")

    def abort(self):
        if self._phase == "closed":
            self._deny("attempt_closed")
        self._events.append("aborted")
        self._archive("aborted")

    def _surcharge(self):
        return self._world.beta + (Fraction(1, 8) if self._control == "C14" else 0)

    def _finish(self):
        if self._control == "C12":
            self._v = 0
            self._events.append("continuation-reset")
        self._events.append("finalizer-invoked")
        base = self._world.theta / 4
        increment = Fraction(1, 16)
        surcharge = self._surcharge()
        actual_offset = surcharge if self._mechanism == "actual" else Fraction(0)
        if self._control == "C08":
            upper = lcm(base.denominator, increment.denominator, surcharge.denominator)
            uniform = Fraction(self._draw("final", 0, upper), upper)
            self._events.append("final-draw")
            proposal = int(base + actual_offset <= uniform < base + actual_offset + increment)
            self._set_proposal(proposal)
        else:
            proposal = self._world.m ^ self._v
            self._set_proposal(proposal)
            nominal_cut = base + proposal * increment
            upper = lcm(nominal_cut.denominator, (nominal_cut + surcharge).denominator)
            uniform = Fraction(self._draw("final", 0, upper), upper)
            self._events.append("final-draw")
        defective = uniform < base + actual_offset + proposal * increment
        self._write_final(defective)
        self._events.append("finalizer-committed")

    def _set_proposal(self, proposal):
        self._trace["proposal"] = proposal
        self._events.append("proposal")

    def _write_final(self, defective):
        intake = json.loads(self._store.read_artifact(self._intake_digest))
        route = self._world.k if self._mechanism == "ordinary" else self._trace["authorized_route"]
        output = {
            "destination": _opposite(route) if defective else route,
            "intake_digest": self._intake_digest,
            "inventory": intake["inventory"],
        }
        if self._control == "C09" and self._mechanism != "ordinary":
            sku = sorted(output["inventory"])[0]
            output["inventory"][sku] += 1
        self._final_digest = self._store.put_artifact(canonical_json(output))

    def _archive(self, status):
        self._trace["status"] = status
        self._store.write_attempt(
            self._attempt_id,
            self._mechanism,
            self._source_digest,
            self._intake_digest,
            self._final_digest,
            self._trace,
        )
        self._phase = "closed"
