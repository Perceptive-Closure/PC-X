"""Exercise the preregistered scope controls in the literal native service."""

from itertools import product

from evidence import require, verify_artifacts


def check_controls(native, profiles, forecasts, heldouts, inventories, direct):
    cases = {name: [item for item in heldouts if item["profile"] == name] for name in profiles}
    tasks = []
    committed = forecasts["profiles"]

    def add(item, identifier, **configuration):
        record = {"id": identifier, "op": "run", "profile": item["profile"],
                  "path": item["path"], "document": item["document"], **configuration}
        tasks.append(record)

    for item in cases["split-calls"]:
        add(item, "control-split-" + item["id"],
            policy=committed["split-calls"]["online"]["policy"])
    for item in cases["free-guard"]:
        if item["nominal_stratum"] == "NO":
            add(item, "control-free-" + item["id"], policy={"verdict": "NO"})
            continue
        policy = {"act": "job.fast", "next": {
            "filed|SHORT": {"act": "job.fast", "next": {"filed|WORK": {"verdict": "YES"}}},
            "filed|LONG": {"act": "job.fast", "next": {"filed|WORK": {"verdict": "YES"}}},
        }}
        for tape in (0, 1):
            add(item, f"control-free-{item['id']}-{tape}", policy=policy, tape=[tape, 0])
    for item in cases["meter-h3"]:
        add(item, "control-missing-" + item["id"],
            policy=forecasts["controls"]["missing-long"]["policy"], tape=[1])
    for item in cases["hidden-carry"]:
        add(item, "control-carry-" + item["id"], actions=["job.fast", "ask.flag"])
    actual_changed = next(item for item in cases["changed-instrument"] if item["nominal_stratum"] == "YES")
    for name in ("changed-instrument", "intrinsic-gap"):
        add({**actual_changed, "profile": name}, "control-instrument-" + name,
            policy=committed["intrinsic-gap"]["online"]["policy"])

    hybrid = ["start-left", "middle-right", "route-left"]
    graph = {"id": "control-cartesian-phantom", "op": "inventory",
             "profile": "feedback-live", "path": hybrid}
    raw = native.batch([*tasks, graph])
    require(raw[-1] == {"status": "denied", "reason": "invalid-installation"},
            "native admitted the Cartesian phantom")
    reports = {}
    files = {}
    for task, result in zip(tasks, raw[:-1], strict=True):
        reports[task["id"]] = result
        full = verify_artifacts(native, task, profiles[task["profile"]], result)
        if full is not None and task["id"].startswith("control-instrument"):
            files[task["id"]] = full

    def group(prefix):
        return {key: row for key, row in reports.items() if key.startswith("control-" + prefix + "-")}

    live = profiles["feedback-live"]
    status = {edge["id"]: bool(edge["stale"]) for stage in live["stages"] for edge in stage["edges"]}
    actual_bits = {tuple(status[edge_id] for edge_id in result["path"])
                   for result in committed["feedback-live"]["targets"]}
    phantom = (False, True, True)
    layer_sets = [sorted({bool(edge["stale"]) for edge in stage["edges"]}) for stage in live["stages"]]
    phantom_work = sum(stage["base"] + stage["premium"] * stale
                       for stage, stale in zip(live["stages"], phantom, strict=True))
    require(phantom in product(*layer_sets) and phantom not in actual_bits
            and phantom_work == 5 and live["deadline"] == 4
            and {row["known_work"] for row in committed["feedback-live"]["targets"]} == {4},
            "missing opposite phantom from Cartesian projection")
    live_first = {direct[item["id"]]["steps"][0]["next_meter"] for item in cases["feedback-live"]}
    suppressed = [direct[item["id"]] for item in cases["feedback-suppressed"]]
    require(live_first == {"LEFT", "RIGHT"} and len(suppressed) == 2 and all(
            row["truth"]["complete"] and row["steps"][0]["next_meter"] == "WORK" for row in suppressed)
            and committed["feedback-suppressed"]["online"]["value"] is None,
            "suppressed native receipts or infeasibility discrepancy")

    split = group("split")
    literal_calls = [direct[item["id"]]["steps"][0]["act"] for item in cases["split-calls"]]
    require(len(split) == 2 and all(row["status"] == "denied" and row["moves"] == 0 for row in split.values())
            and set(literal_calls) == {"job.fast.left", "job.fast.right"}
            and committed["split-calls"]["online"]["value"] == 0, "split literal gate failed")

    free = group("free")
    for key, result in free.items():
        yes = key.startswith("control-free-free-guard-yes-")
        require(result["initial"]["obs"] == ("fresh" if yes else "stale")
                and result["paid"] == 0 and result["status"] == "stopped"
                and result["verdict"] == ("YES" if yes else "NO")
                and result["truth"]["complete"] == yes, "free guard baseline differs")
    require(len(free) == 3 and committed["free-guard"]["online"]["value"] == 3,
            "free guard forecast under uniform initial observation missing")

    missing = group("missing")
    require(len(missing) == 2 and all(
            row["status"] == "missing-branch" and row["steps"][0]["next_meter"] == "LONG"
            for row in missing.values()) and forecasts["controls"]["missing-long"]["value"] == 1
            and committed["meter-h3"]["online"]["value"] == 3
            and committed["meter-h4"]["online"]["value"] == 2, "missing LONG not falsified")

    carry = group("carry")
    by_edge = {}
    for target in committed["hidden-carry"]["targets"]:
        path = target["path"]
        _, rows, _ = inventories["hidden-carry", tuple(path)]
        quote = next(cmd["paid"] for cmd in rows[1, "WORK"]["commands"] if cmd["id"] == "ask.flag")
        by_edge.setdefault(path[1], {})[path[0]] = quote
    require(len(carry) == 4 and all(
            row["steps"][0]["next_meter"] == "WORK" and row["steps"][1]["obs"] in {"fresh", "stale"}
            for row in carry.values()) and {row["steps"][1]["paid"] for row in carry.values()} == {1, 5}
            and len(by_edge) == 2 and all(quotes == {"early-clear": 1, "early-set": 5}
                                          for quotes in by_edge.values()), "hidden carry gate failed")

    ordinary = reports["control-instrument-intrinsic-gap"]
    changed = reports["control-instrument-changed-instrument"]
    shape = lambda row: [{key: step[key] for key in ("act", "obs", "next_meter", "work", "paid")}
                         for step in row["steps"]]
    require(ordinary["verdict"] == changed["verdict"] == "YES" and shape(ordinary) == shape(changed)
            and ordinary["truth"]["complete"] and not changed["truth"]["complete"]
            and changed["truth"]["actual_destination"] == "quarantine"
            and changed["truth"]["done"] == ordinary["truth"]["done"] == 3,
            "disturbed instrument did not falsify useful completion")
    checks = {
        "cartesian": {"phantom": hybrid, "nominal_work": phantom_work, "actual_work": 4,
                      "native": raw[-1]},
        "suppressed-receipt": {"ordinary_first_meters": sorted(live_first), "suppressed_meter": "WORK",
                               "individually_complete": len(suppressed), "joint_worst_paid": None},
        "split-calls": {"projection_paid": 0, "native_denials": len(split), "known_fast_calls": literal_calls},
        "free-guard": {"uniform_initial_projection_paid": 3, "initial_disclosed_paid": 0},
        "missing-long": {"short_only_paid": 1, "observed_missing_branches": len(missing),
                         "three_move_paid": 3, "four_move_paid": 2},
        "hidden-carry": {"same_meter": "WORK", "actual_quotes_by_suffix_and_history": by_edge},
        "changed-instrument": {"public_trace_equal": True, "paid": changed["paid"],
                               "ordinary_destination": ordinary["truth"]["actual_destination"],
                               "disturbed_destination": "quarantine"},
    }
    return checks, [{"treatment": "control", "task": task, "native": result}
                    for task, result in zip(tasks, raw[:-1], strict=True)], files
