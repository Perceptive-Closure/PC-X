"""Independent checkpoint and raw native-output validation."""

from itertools import combinations
import json

from common import BOTH, BUDGET, FREEZES, HISTORIES, PROTOCOL, REVIEWS, STRATA, TICKETS, case_id, require


def write_history(profile, atom, world):
    has_ticket = profile == "receipt" or atom == "publish"
    has_review = atom == "attest"
    return tuple(event for present, event in ((has_ticket, f"ticket:{world}"), (has_review, f"review:{world}"))
                 if present)


def expected_signature(profile, backup_cost):
    if profile == "publish":
        return [1, "inf", 1, 1, "inf", "inf", 1, "inf"]
    fallback = "inf" if backup_cost is None else backup_cost
    return [1, 1, fallback, 1, "inf", 1, fallback, "inf"]


def verify_witness_table(table):
    require(table.keys() == {s["id"] for s in STRATA}, "witness inventory differs")
    for stratum in STRATA:
        profiles = table[stratum["id"]]
        require(profiles.keys() == {"publish", "receipt"}, "missing witness")
        rows = profiles["publish"] + profiles["receipt"]
        require(len({row["source_sha256"] for row in rows}) == 1, "incompatible visible source")
        for profile, witnesses in profiles.items():
            require([row["world"] for row in witnesses] == [0, 1], "support not exhausted")
            atoms = [{"atomic_action": "publish", "touch": ["E" if profile == "publish" else "R"]}]
            if stratum["backup_cost"] is not None:
                atoms.append({"atomic_action": "attest", "touch": ["E"]})
            for row in witnesses:
                label = "allow" if row["world"] == 0 else "deny"
                require(row["checkpoint_targets"] == [["allow", "deny"]] + [[label]] * len(atoms),
                        "incorrect certificate partition")
                require(row["atomic_actions"] == atoms, "incorrect extensional touch")
                require(row["signature"] == expected_signature(profile, stratum["backup_cost"]),
                        "one-step exhaustive freeze calculus differs")


def pair_equalities(display):
    require(len(display) == len(HISTORIES), "representation is not extensional")
    return {(i, j) for i, j in combinations(range(len(display)), 2) if display[i] == display[j]}


def checkpoint_check(raw, profile, atom, world):
    require(raw["public_phase"] == ("received" if atom is None else "settled"), "visible checkpoint differs")
    require(raw["authority"] == ["offline"], "authority invariant differs")
    require(tuple(raw["H"]) == write_history(profile, atom, world), "admission ledger does not match source")
    merged = profile == "receipt" and atom != "publish"
    require(pair_equalities(raw["PR"]) == ({(1, 2)} if merged else set()), "renderer partition differs")


def view_labels(checkpoint, native_values):
    admitted = tuple(checkpoint["H"])
    labels = checkpoint["PR"]
    representative = labels[HISTORIES.index(admitted)]
    compatible = [
        native_values[world] for world in (0, 1)
        if any(labels[HISTORIES.index(h)] == representative for h in ((), TICKETS[world], REVIEWS[world], BOTH[world]))
    ]
    return set(compatible)


def decisions(raw, fields):
    require(len(raw) == len(fields), "native support count differs")
    values = []
    for row, (user, method, subject) in zip(raw, fields, strict=True):
        expected_input = {"method": method, "path": ["finance", "salary", subject], "user": user}
        require(json.loads(row["stdin"]) == expected_input, "native query set differs")
        require(row["disposition"] == "exit" and row["returncode"] == 0 and not row["stderr"],
                "unexpected native failure")
        artifact = json.loads(row["stdout"])
        require(set(artifact) == {"result"} and len(artifact["result"]) == 1,
                "native response must contain a single result")
        entries = artifact["result"][0]["expressions"]
        require(len(entries) == 1 and entries[0]["text"] == "data.httpapi.authz.allow",
                "native stdout has unexpected query expression")
        value = entries[0]["value"]
        require(type(value) is bool and value is row["decision"], "decision normalization differs")
        values.append(value)
    return values


def verify_development(rows):
    require(len(rows) == len(PROTOCOL["development_controls"]) + 1, "native development inventory differs")
    for observed, frozen in zip(rows[:-1], PROTOCOL["development_controls"], strict=True):
        require(observed["id"] == frozen["id"] and observed["expected"] is frozen["expected"],
                "development control identity differs")
        values = decisions([observed["native"]], [frozen["request"]])
        require(values == [frozen["expected"]], f"wrong development decision for {frozen['id']}")
    malformed = rows[-1]
    require(malformed["id"] == "invalid-json" and malformed["expected"] == "input-error",
            "malformed control identity differs")
    raw = malformed["native"]
    require(raw["stdin"] == '{"user":' and raw["disposition"] == "exit" and raw["returncode"] != 0
            and raw["decision"] is None and (raw["stderr"] or raw["stdout"]),
            "malformed JSON input must be rejected with a diagnostic")
    diagnostic = raw["stderr"] + raw["stdout"]
    require(any(token in diagnostic.casefold() for token in ("eof", "yaml", "json", "unmarshal", "input")),
            "malformed input produced an unrelated diagnostic")


def verify_native(trace, assignment, forecast):
    verify_development(trace["development"])
    measured = {}
    invocations = len(trace["development"])
    blocked = 0
    allowed = 0
    denied = 0
    conventional = {}
    require(trace["units"].keys() == assignment["adapters"].keys() == forecast.keys(), "unit inventory differs")
    for stratum in STRATA:
        for member in (0, 1):
            name = case_id(stratum, member)
            unit = trace["units"][name]
            provisioned = assignment["adapters"][name]
            profile = "receipt" if provisioned["receipt_marks"] else "publish"
            baseline = decisions(unit["unrestricted"], stratum["requests"])
            require(baseline == [True, False], "frozen target partition did not match native policy")
            invocations += len(baseline)
            allowed += baseline.count(True)
            denied += baseline.count(False)
            conventional[name] = all(type(value) is bool for value in baseline)
            for i, raw in enumerate(unit["received"]):
                checkpoint_check(raw, profile, None, i)
                require(view_labels(raw, baseline) == {False, True}, "initial view already closed")
            require(len(unit["received"]) == 2 and set(unit["freeze_conditions"]) == set(FREEZES),
                    "native initial support or freeze order coverage differs")
            signature = []
            for freeze in FREEZES:
                candidates = unit["freeze_conditions"][freeze]
                expected_costs = {"publish": 1}
                if stratum["backup_cost"] is not None:
                    expected_costs["attest"] = stratum["backup_cost"]
                require([item["action"] for item in candidates] == list(expected_costs), "atomic action inventory differs")
                closing_costs = []
                for action in candidates:
                    atom = action["action"]
                    require(action["cost"] == expected_costs[atom], "atomic cost differs")
                    raw_touches = set()
                    pairs = zip(unit["received"], action["staged"], strict=True)
                    for i, (before, after) in enumerate(pairs):
                        checkpoint_check(after, profile, atom, i)
                        for resource, changed in (
                            ("E", before["H"] != after["H"]),
                            ("R", pair_equalities(before["PR"]) != pair_equalities(after["PR"])),
                            ("A", before["authority"] != after["authority"]),
                        ):
                            if changed:
                                raw_touches.add(resource)
                    require(set(action["touch"]) == raw_touches, "recorded action touch differs")
                    remains = freeze == "none" or all(label not in raw_touches for label in freeze)
                    require(action["committed"] is remains, "whole-action freeze crossing")
                    if remains:
                        values = decisions(action["native"], stratum["requests"])
                        require(values == baseline, "native policy or input semantics changed under intervention")
                        invocations += len(values)
                        allowed += values.count(True)
                        denied += values.count(False)
                        if all(len(view_labels(after, values)) == 1 for after in action["staged"]):
                            closing_costs.append(action["cost"])
                    else:
                        require(not action["native"], "blocked atomic action emitted a native outcome")
                        blocked += 1
                signature.append(min(closing_costs) if closing_costs else "inf")
            limit = signature[FREEZES.index("R")]
            holds = type(limit) is int and limit <= BUDGET
            measured[name] = {"signature": signature, "holds": holds}
    forecast_errors = [name for name in measured if measured[name] != forecast[name]]
    baseline_errors = [name for name in measured if conventional[name] != measured[name]["holds"]]
    return {
        "measured": measured,
        "primary_agree": sum(measured[name]["holds"] == forecast[name]["holds"] for name in measured),
        "signature_coordinates_agree": sum(
            actual == predicted for name in measured
            for actual, predicted in zip(measured[name]["signature"], forecast[name]["signature"], strict=True)
        ),
        "freeze_coordinates": len(measured) * len(FREEZES),
        "forecast_errors": forecast_errors,
        "conventional_terminal_only": conventional,
        "conventional_errors": baseline_errors,
        "no_audit_abstentions": len(measured),
        "atomic_actions_blocked": blocked,
        "native_invocations_excluding_version": invocations,
        "heldout_native_allow": allowed,
        "heldout_native_deny": denied,
        "development_controls_passed": len(trace["development"]),
        "units": len(measured),
    }
