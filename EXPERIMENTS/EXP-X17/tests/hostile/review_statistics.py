"""Check the independent evidence and adjudicate both roles under the frozen X17 rules."""

import argparse
import gzip
import json
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from fractions import Fraction as F
from pathlib import Path

from review_release import (
    AUTH, FREEZE, N, OPENING, ROLE_CHARGES, blob, check_primary_release,
    document, hash_bytes, pack, signed_record,
)
from verify_freeze import ARMS, independent_expected


INDEPENDENT = "952708cc2713387612edc008f122564733d3b7a3"
DIRECTORY = "results/independent/"
RANGES = {
    **{name: (F(0), F(1)) for name in ("wrong", "I", "V", "VI", "cost", "selected")},
    "G": (F(1, 2), F(1)), "Z": (F(-3, 8), F(5, 8)),
}


def linked_artifacts():
    artifacts = {}
    for route in ("L", "R"):
        source = blob(f"native/fixtures/stock-{route}.json", FREEZE).replace(b"\r\n", b"\n")
        content = json.loads(source)
        inventory = dict.fromkeys(content["book"], 0)
        for scan in content["scans"]:
            inventory[scan["sku"]] += scan["quantity"]
        digest = hash_bytes(source)
        intake = {
            "source_digest": digest, "inventory": inventory,
            "variance": {sku: units - content["book"][sku] for sku, units in inventory.items()},
            "staging_destination": route,
        }
        intake_digest = hash_bytes(pack(intake))
        finishes = {
            destination: hash_bytes(pack({"destination": destination, "intake_digest": intake_digest,
                                          "inventory": inventory}))
            for destination in ("L", "R")
        }
        artifacts[route] = {"source": digest, "intake": intake_digest, "finishes": finishes}
    return artifacts


def check_hex(text):
    assert len(bytes.fromhex(text)) == 32


def read_independent(worlds):
    report = document(DIRECTORY + "independent-summary.json", INDEPENDENT)
    replay = document(DIRECTORY + "replay-metadata.json", INDEPENDENT)
    reveal = document("custody/independent-seed-reveal.json", INDEPENDENT)
    commitment = document("custody/independent-seed-commitment.json", FREEZE)["sha256"]
    authorization = hash_bytes(blob("custody/run-authorization.json", AUTH))
    assert reveal["authorization_commit"] == AUTH and reveal["opening_commit"] == OPENING
    assert hash_bytes(bytes.fromhex(reveal["seed_hex"])) == commitment == report["seed_commitment"]
    assert commitment != document("custody/primary-seed-commitment.json", FREEZE)["sha256"]
    assert report["auth_inputs"]["authorization_sha256"] == replay["authorization_sha256"] == authorization
    assert report["auth_inputs"]["source_commit"] == replay["source_commit"] == FREEZE
    assert report["raw_db_sha256"] == replay["raw_db_sha256"]
    assert report["family_size"] == 640 and report["planned_per_cell"] == N
    assert document(DIRECTORY + "relay-readback.json", INDEPENDENT)["beacon"] == document(
        "custody/verified-beacon.json", AUTH)["beacon"]

    custody = document("custody/independent-opening-checks.json", INDEPENDENT)
    assert custody["authorization_commit"] == AUTH and custody["authorization_sha256"] == authorization
    assert custody["opening_commit"] == OPENING and custody["actual_and_nominal_predictions_verified"] == 80
    assert all(custody[key] is True for key in ("bls_quicknet_verified", "registered_roster_matches",
                                                "roles_have_distinct_seed_bytes", "seed_commitment_matches"))
    packed_index = blob(DIRECTORY + "independent-index.ndjson.gz", INDEPENDENT)
    assert hash_bytes(packed_index) == report["raw_index_sha256"] == replay["raw_index_sha256"]
    assert len(packed_index) == replay["raw_index_bytes"]
    totals = defaultdict(Counter)
    diagnostic = defaultdict(Counter)
    material_lookup = linked_artifacts()
    material_ids = {row["id"] for row in replay["illustrative_material_records"].values()}
    retained = {}
    for line in gzip.decompress(packed_index).splitlines():
        row = json.loads(line)
        identifier, slot = row["id"], row["id"].split("-")[0]
        world = worlds[slot]
        if row.get("kind") == "ordinary":
            counts = diagnostic[slot]
            assert int(identifier.split("-")[-1]) == counts["ordinary_count"]
            counts.update({"ordinary_count": 1, "ordinary_violation": row["V"]})
            check_hex(row["trace_sha256"])
        elif row.get("kind") == "paired":
            counts = diagnostic[slot]
            assert int(identifier.split("-")[-1]) == counts["paired_count"]
            assert row["actual_V"] - row["nominal_V"] == row["in_strip"] <= row["I"]
            assert (row["actual_final"] != row["nominal_final"]) == bool(row["in_strip"])
            assert bool(row["actual_final"]) == bool(row["nominal_final"]) == bool(row["I"])
            assert row["actual_trace"] == row["nominal_trace"]
            counts.update({"paired_count": 1, "paired_issued": row["I"], "strip_count": row["in_strip"],
                           "paired_disagreement": row["actual_V"] - row["nominal_V"]})
        else:
            _, arm, index = identifier.split("-")
            counts = totals[slot, arm]
            assert "invalid" not in row and "execution_error" not in row
            assert int(index) == counts["valid"] and arm in ARMS
            values = {key: F(number) for key, number in row["outcome"].items()}
            issue, violation = values["I"], values["V"]
            positive = F(world["theta"]) < F(1, 2)
            assert issue in (0, 1) and values["wrong"] == int(bool(issue) != positive)
            assert values["VI"] == violation <= issue and violation in (0, 1)
            assert values["G"] == F(1, 2) + F(int(positive and issue and not violation), 2)
            assert values["Z"] == violation - F(3, 8) * issue
            cost = 8 * values["cost"]
            assert cost in ROLE_CHARGES[arm] and row["logical_moves"] == world["N"] + 3 + issue
            route = world["k"]
            genuine = material_lookup[route]
            assert row["source_digest"] == genuine["source"] and row["intake_digest"] == genuine["intake"]
            destination = ("R" if route == "L" else "L") if violation else route
            assert row["final_digest"] == (genuine["finishes"][destination] if issue else None)
            check_hex(row["trace_sha256"])
            counts.update({key: int(values[key]) for key in ("wrong", "I", "V", "VI")})
            counts.update({"valid": 1, "G2": int(2 * values["G"]), "cost8": int(cost)})
            counts["max_cost8"] = max(counts["max_cost8"], int(cost))
        if identifier in material_ids or identifier + "-actual" in material_ids:
            retained[identifier] = row

    assert set(totals) == {(slot, arm) for slot in worlds for arm in ARMS}
    assert len(report["cells"]) == len(totals)
    for row in report["cells"]:
        counts = totals[row["id"], row["arm"]]
        assert row["planned"] == row["valid"] == counts["valid"] == N and row["invalid"] == 0
        assert row["issued"] == counts["I"]
        expected = {key: counts[key] for key in ("wrong", "I", "V", "VI")}
        expected.update({"G_halves": counts["G2"], "cost_eighths": counts["cost8"],
                         "Z_eighths": 8 * counts["VI"] - 3 * counts["I"]})
        assert row["counts"] == expected
    assert len(report["setup_receipts"]) == len(worlds)
    for row in report["setup_receipts"]:
        receipt = row["receipt"]
        assert row["id"] in worlds and signed_record("source", receipt)
        assert receipt["check"] == "guard" and receipt["charge_eighths"] == 2 and receipt["revision"] == "good"

    source_checks = Counter()
    for row in report["diagnostics"]:
        counts = diagnostic[row["id"]]
        assert counts == {key: row[key] for key in counts}
        assert counts["paired_count"] == 128 and counts["ordinary_count"] == 64
        source_checks.update(counts)
    assert replay["index_rows_checked"] == 163840 + source_checks["ordinary_count"] + source_checks["paired_count"]
    assert replay["main_attempts"] == 163840 and replay["main_invalid"] == 0
    assert replay["matched_strip"] == source_checks["strip_count"]
    verify_independent_artifacts(replay["illustrative_material_records"], material_lookup, retained)
    return totals, {
        "independent_commit": INDEPENDENT,
        "fixed_rows_checked": replay["main_attempts"],
        "diagnostic_rows_checked": sum(source_checks[k] for k in ("ordinary_count", "paired_count")),
        "ordinary_diagnostics": source_checks["ordinary_count"], "actual_nominal_pairs": source_checks["paired_count"],
        "paired_issues": source_checks["paired_issued"], "matched_surcharge_strip": source_checks["strip_count"],
        "material_records_checked": len(material_ids),
        "pcx_actual_paid_cap": str(F(max(row["max_cost8"] for (_, arm), row in totals.items() if arm == "pcx"), 8)),
    }


def verify_independent_artifacts(examples, linked, index):
    for label, item in examples.items():
        hashes, artifacts, trace = item["artifact_hashes"], item["artifacts"], item["trace"]
        assert hash_bytes(pack(trace)) == item["trace_sha256"]
        route = trace["world"]["k"]
        assert hashes["source"] == linked[route]["source"] and hashes["intake"] == linked[route]["intake"]
        assert artifacts["source"] == document(f"native/fixtures/stock-{route}.json", FREEZE)
        for part in ("installation", "intake", "final"):
            assert hashes[part] == (hash_bytes(pack(artifacts[part])) if artifacts[part] is not None else None)
        assert artifacts["installation"]["world"] == trace["world"]
        result = item["decoded"]
        assert result["intake_ok"] and not result["intake_violation"]
        expected_v = bool(artifacts["final"] and artifacts["final"]["destination"] != route)
        assert F(result["V"]) == int(expected_v)
        if label.startswith("strip"):
            shared = index[item["id"].rsplit("-", 1)[0]]
            side = label.split("_")[1]
            assert shared[side + "_trace"] == item["trace_sha256"]
            assert shared[side + "_final"] == hashes["final"] and shared["in_strip"] == 1
        else:
            recorded = index[item["id"]]
            assert recorded["trace_sha256"] == item["trace_sha256"] and recorded["final_digest"] == hashes["final"]
    assert examples["strip_actual"]["trace"] == examples["strip_nominal"]["trace"]
    assert examples["strip_actual"]["artifact_hashes"]["final"] != examples["strip_nominal"]["artifact_hashes"]["final"]


def check_independent_exact():
    control = document(DIRECTORY + "independent-control-summary.json", INDEPENDENT)
    compressed = blob(DIRECTORY + "independent-controls.json.gz", INDEPENDENT)
    assert hash_bytes(compressed) == control["control_archive_sha256"]
    archive = json.loads(gzip.decompress(compressed))
    cases = [row for row in archive["cases"] if row["status"] == "verified"]
    assert {row["id"] for row in cases} == {f"C{i:02d}" for i in range(1, 20)}
    assert control["controls_verified"] == len(cases) == 19 and archive["main_seed_used"] is False
    assert len(archive["attempts"]) == control["control_native_attempts_archived"] == 70
    repeated = archive["attempts"]["C04-identical"]["trace"]
    assert repeated["command"] == "low:L" and repeated["paid_eighths"] == 3
    assert repeated["denials"] == ["repeated_probe"]
    optimizer = document(DIRECTORY + "independent-optimization.json", INDEPENDENT)["lookup"]
    assert len(optimizer) == 20
    for entry in optimizer:
        cheaper = entry["hard_cap"] != "1" or entry["menu"] in ("low_skip", "no_paid")
        result = entry["result"]
        if cheaper:
            assert result["status"] == "infeasible"
        else:
            assert result["status"] == "optimal" and F(result["cost"]) == (
                F(7, 12) if entry["menu"] == "full" else F(2, 3)
            )
    checked = document(DIRECTORY + "independent-grid-check.json", INDEPENDENT)
    assert F(checked["direct_changed_menu_optimum"]) == F(1, 6)
    for grid in checked["grid_certificates"]:
        alpha = F(1, 128 * grid["refinement"])
        assert F(grid["alpha"]) == alpha and F(grid["lower"]) == F(7, 12)
        assert F(grid["upper_epigraph"]) == F(7, 12) + 6 * alpha
        assert F(grid["explicit_upper_price"]) == F(7, 12) + 5 * alpha
    return {"independent_control_cases_checked": len(cases), "independent_control_archive_rows": len(archive["attempts"]),
            "explicit_optimizer_cases_checked": len(optimizer), "exact_grid_certificates": len(checked["grid_certificates"])}


def interval(name, observed, count):
    floor, ceiling = RANGES[name]
    if name != "selected":
        return max(floor, observed - F(1, 25)), min(ceiling, observed + F(1, 25))
    with localcontext() as context:
        context.prec = 60
        point = Decimal(observed.numerator) / Decimal(observed.denominator)
        radius = (Decimal(25600).ln() / (2 * count)).sqrt()
        tick = Decimal("0.000000001")
        lower = max(Decimal(0), point - radius).quantize(tick, rounding=ROUND_FLOOR)
        upper = min(Decimal(1), point + radius).quantize(tick, rounding=ROUND_CEILING)
    return F(lower), F(upper)


def resolve_limit(limits, cap, lower):
    low, high = limits
    if lower:
        return "supported" if low >= cap else "contradicted" if high < cap else "inconclusive"
    return "supported" if high <= cap else "contradicted" if low > cap else "inconclusive"


def threshold_specs(arm, positive):
    if arm not in ("pcx", "always_high"):
        return {}
    limits = {"wrong_at_most_1/3": ("wrong", F(1, 3), False),
              "signed_risk_at_most_3/8": ("Z", F(0), False),
              "selected_risk_at_most_3/8": ("selected", F(3, 8), False),
              "selected_risk_at_most_5/16": ("selected", F(5, 16), False)}
    if arm == "pcx":
        limits["issuance_at_least_1/4"] = "I", F(1, 4), True
    if positive:
        limits.update({"positive_issuance_at_least_2/3": ("I", F(2, 3), True),
                       "positive_utility_at_least_25/32": ("G", F(25, 32), True),
                       "positive_selected_risk_at_most_5/32": ("selected", F(5, 32), False)})
    return limits


def analyze_role(worlds, totals):
    rows, summary = {}, {}
    for slot, arm in sorted(totals):
        tally = totals[slot, arm]
        world = worlds[slot]
        theta, beta = F(world["theta"]), F(world["beta"])
        issued = tally["I"]
        assert issued > 0
        predicted = independent_expected(theta, beta, world["m"], world["N"], arm)
        predicted["selected"] = predicted["VI"] / predicted["I"]
        value = {key: F(tally[key], N) for key in ("wrong", "I", "V", "VI")}
        value.update({"G": F(tally["G2"], 2 * N), "cost": F(tally["cost8"], 8 * N),
                      "Z": F(tally["VI"], N) - F(3, 8) * F(issued, N),
                      "selected": F(tally["VI"], issued)})
        bands = {key: interval(key, mean, issued) for key, mean in value.items()}
        outcomes = {}
        for key, (lo, hi) in bands.items():
            expected = predicted[key]
            outcomes[key] = {
                "estimate": str(value[key]), "forecast": str(expected),
                "CI": [str(lo), str(hi)], "point_compatible": lo <= expected <= hi,
                "equivalent": expected - F(2, 25) <= lo and hi <= expected + F(2, 25),
            }
        limits = threshold_specs(arm, theta < F(1, 2))
        criteria = {key: resolve_limit(bands[metric], cap, direction)
                    for key, (metric, cap, direction) in limits.items()}
        rows[slot, arm] = (bands, outcomes, criteria)
        entry = summary.setdefault(arm, {"compatible": 0, "equivalent": 0, "thresholds": defaultdict(Counter),
                                         "worst": {}, "positive_lower_risk_cells": 0,
                                         "total_issued": 0, "total_violating_issues": 0, "total_eighths": 0,
                                         "negative_world_issued": 0, "negative_world_violating_issues": 0})
        entry["compatible"] += sum(x["point_compatible"] for x in outcomes.values())
        entry["equivalent"] += sum(x["equivalent"] for x in outcomes.values())
        entry["positive_lower_risk_cells"] += bands["selected"][0] > 0
        entry["total_issued"] += tally["I"]
        entry["total_violating_issues"] += tally["VI"]
        entry["total_eighths"] += tally["cost8"]
        if theta > F(1, 2):
            entry["negative_world_issued"] += tally["I"]
            entry["negative_world_violating_issues"] += tally["VI"]
        for key, (metric, _, lower) in limits.items():
            entry["thresholds"][key][criteria[key]] += 1
            adverse = bands[metric][0] if lower else bands[metric][1]
            if key not in entry["worst"] or (adverse < F(entry["worst"][key]["bound"]) if lower
                                              else adverse > F(entry["worst"][key]["bound"])):
                entry["worst"][key] = {"world": slot, "bound": str(adverse)}
    for entry in summary.values():
        entry["observed_paid_cost"] = str(F(entry["total_eighths"], 8 * N * len(worlds)))
    return rows, summary


def review():
    worlds, primary, primary_report = check_primary_release()
    independent, independent_report = read_independent(worlds)
    checks = check_independent_exact()
    primary_rows, primary_summary = analyze_role(worlds, primary)
    independent_rows, independent_summary = analyze_role(worlds, independent)
    comparisons = []
    count = 0
    for slot, arm in sorted(primary_rows):
        primary_bands, primary_endpoints, primary_decisions = primary_rows[slot, arm]
        independent_bands, independent_endpoints, independent_decisions = independent_rows[slot, arm]
        shared = {
            name: max(limits[0], independent_bands[name][0]) <= min(limits[1], independent_bands[name][1])
            for name, limits in primary_bands.items()
        }
        count += sum(shared.values())
        comparisons.append({"world": slot, "arm": arm, "overlap": shared,
                            "primary": {"endpoints": primary_endpoints, "thresholds": primary_decisions},
                            "independent": {"endpoints": independent_endpoints, "thresholds": independent_decisions}})
    return {"primary_release": primary_report, "independent_release": independent_report, "exact_cross_checks": checks,
            "role_summaries": {"primary": primary_summary, "independent": independent_summary},
            "overlapping_intervals": count, "compared_intervals": len(comparisons) * 8, "cells": comparisons}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    output = parser.parse_args().output
    matrix = review()
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(matrix, stream, sort_keys=True, indent=2)
        stream.write("\n")
    values = {role: {key: sum(item[key] for item in arms.values()) for key in ("compatible", "equivalent")}
              for role, arms in matrix["role_summaries"].items()}
    print(json.dumps({"role_forecasts": values, "overlaps": matrix["overlapping_intervals"],
                      "compared": matrix["compared_intervals"]}, sort_keys=True))


if __name__ == "__main__":
    main()
