"""X01 closure and X03 minimum-audit checks for the finite adapter class."""

from dataclasses import asdict
from importlib import import_module
from itertools import combinations, product
from math import inf
from pathlib import Path
import sys
from types import ModuleType

from common import (
    BOTH, FREEZES, HISTORIES, PROTOCOL, PROVENANCE, REVIEWS, STRATA, TICKETS,
    case_id, digest, primary, require, runner_seal,
)


def reference(deps, name, module):
    root = Path(deps).resolve() / name
    pin = PROVENANCE["references"][name]
    for relative, expected in pin["source_files"].items():
        source = (root / relative).read_bytes().replace(b"\r\n", b"\n")
        require(digest(source) == expected, f"mismatched pinned source {relative}")
    package = "_pcx_" + name
    path = list(pin["source_files"])[0]
    package_path = str((root / path).parent)
    if package not in sys.modules:
        sys.modules[package] = ModuleType(package)
        sys.modules[package].__path__ = [package_path]
    require(sys.modules[package].__path__ == [package_path], "reference path changed within process")
    return import_module(package + "." + module)


def one_world(model, stratum, profile, world):
    fine = tuple(map(str, range(len(HISTORIES))))
    coarse = ("0", "ticket", "ticket", "3", "4", "5", "6")
    authority = frozenset(["offline"])
    def state(history, display, phase, candidates=()):
        return model.State(HISTORIES.index(history), display, authority, phase, candidates)

    # All support is deterministic once the inert fixture world is held fixed.
    actions = [model.Action("publish", "offline", 1)]
    candidates = [model.Candidate("publish", (model.Branch(1, "settled"),))]
    if stratum["backup_cost"] is not None:
        actions.append(model.Action("attest", "offline", stratum["backup_cost"]))
        candidates.append(model.Candidate("attest", (model.Branch(2, "settled"),)))
    initially_admitted = profile == "receipt"
    h0 = TICKETS[world] if initially_admitted else ()
    r0 = coarse if initially_admitted else fine
    states = [
        state(h0, r0, "received", tuple(candidates)),
        state(TICKETS[world], fine, "settled"),
    ]
    if len(actions) == 2:
        states.append(state(BOTH[world] if initially_admitted else REVIEWS[world], r0, "settled"))
    compatibility = tuple(
        frozenset(HISTORIES.index(h) for h in ((), ticket, review, both))
        for ticket, review, both in zip(TICKETS, REVIEWS, BOTH, strict=True)
    )
    return model.Contract(
        f"{stratum['id']}/{profile}/{world}", f"shared-source/{stratum['id']}",
        tuple(map(str, HISTORIES)), ("allow", "deny"), compatibility, 0, tuple(actions), tuple(states),
    )


def witnesses(deps):
    model = reference(deps, "X01", "model")
    oracle = reference(deps, "X01", "reference")
    require(tuple(FREEZES) == model.FREEZE_NAMES, "freeze order differs from pinned X01")
    table = {}
    for stratum in STRATA:
        name = stratum["id"]
        table[name] = {}
        for profile in ("publish", "receipt"):
            rows = []
            for world in (0, 1):
                contract = one_world(model, stratum, profile, world)
                model.validate(contract)
                cost = model.signature(contract)
                require(cost == oracle.reference_signature(contract), "independent X01 disagreement")
                observations = []
                initial = contract.states[0]
                for candidate in initial.candidates:
                    observations.append({
                        "atomic_action": candidate.name,
                        "touch": sorted(model.touched(contract, 0, candidate.support)),
                    })
                rows.append({
                    "world": world,
                    "source_sha256": model.source_sha256(contract),
                    "checkpoint_targets": [sorted(model.checkpoint_target_classes(contract, i))
                                           for i in range(len(contract.states))],
                    "signature": [value if value != inf else "inf" for value in cost],
                    "atomic_actions": observations,
                })
            require(rows[0]["signature"] == rows[1]["signature"], "world-specific freeze cost")
            table[name][profile] = rows
        require(len({row["source_sha256"] for rows in table[name].values() for row in rows}) == 1,
                "source projections differ")
        require(primary(table[name]["publish"][0]["signature"])
                != primary(table[name]["receipt"][0]["signature"]), "witness target does not differ")
    return table


def query_interface():
    return [(f"{stratum['id']}.{family['id']}", family["cost"])
            for stratum in STRATA for family in PROTOCOL["query_families"]]


def profile_for(bit, member):
    return "receipt" if bit ^ member else "publish"


def domain(table):
    for orientation in product((0, 1), repeat=len(STRATA)):
        prediction = {}
        answers = {}
        for stratum, bit in zip(STRATA, orientation, strict=True):
            name = stratum["id"]
            answers[name + ".envelope-schema"] = "ticket-v1"
            answers[name + ".admission-count"] = str(bit)
            answers[name + ".renderer-partition"] = "merged" if bit else "exact"
            for member in (0, 1):
                profile = profile_for(bit, member)
                signature = table[name][profile][0]["signature"]
                prediction[case_id(stratum, member)] = {"signature": signature, "holds": primary(signature)}
        yield {
            "id": "".join(map(str, orientation)),
            "answers": answers,
            "prediction": prediction,
        }


def subset_catalog(queries):
    for size in range(len(queries) + 1):
        for subset in combinations(range(len(queries)), size):
            yield sum(queries[i][1] for i in subset), subset


def lazy_audit(queries, domain_rows):
    names = tuple(name for name, _ in queries)
    catalog = sorted(subset_catalog(queries))
    edges = []
    steps = []
    while True:
        cost, chosen = next((cost, subset) for cost, subset in catalog
                            if all(set(subset).intersection(edge) for edge in edges))
        conflict = next(
            ((left, right) for left, right in combinations(domain_rows, 2)
             if left["prediction"] != right["prediction"]
             and all(left["answers"][names[i]] == right["answers"][names[i]] for i in chosen)),
            None,
        )
        step = {"cost": cost, "chosen": [names[i] for i in chosen]}
        steps.append(step)
        if conflict is None:
            return cost, chosen, steps
        left, right = conflict
        edge = [i for i, name in enumerate(names) if left["answers"][name] != right["answers"][name]]
        require(bool(edge), "declared query interface cannot identify the target")
        edges.append(edge)
        step.update({"witness": [left["id"], right["id"]], "edge": [names[i] for i in edge]})


def preaudit(deps):
    from verify import verify_witness_table

    table = witnesses(deps)
    verify_witness_table(table)
    rows = list(domain(table))
    queries = query_interface()
    names = tuple(name for name, _ in queries)

    def problem(indices):
        return x03.Problem(
            "EXP-X06",
            tuple(names[i] for i in indices),
            tuple(queries[i][1] for i in indices),
            tuple(x03.Completion(
                row["id"], tuple(row["answers"][names[i]] for i in indices),
                "".join("1" if outcome["holds"] else "0" for outcome in row["prediction"].values()),
            ) for row in rows),
        )

    x03 = reference(deps, "X03", "certificates")
    oracle = reference(deps, "X03", "reference")
    full = problem(tuple(range(len(queries))))
    cost, chosen, steps = lazy_audit(queries, rows)
    optimum = x03.solve(full)
    exact = oracle.exact_by_partition(full)
    require((cost, chosen) == (optimum.cost, optimum.queries)
            and oracle.verify_proof(full, optimum), "X03 optimum differs")
    ablated = problem(tuple(i for i, name in enumerate(names) if name.endswith(".envelope-schema")))
    inaccessible = x03.solve(ablated)
    require(oracle.verify_proof(ablated, inaccessible), "ablation certificate could not be verified")
    cheapest = sorted(range(len(queries)), key=lambda i: (queries[i][1], i))
    length = next(i for i in range(len(cheapest) + 1) if oracle.conflict(full, tuple(cheapest[:i])) is None)
    return {
        "runner": runner_seal(),
        "witness_table": table,
        "completions": rows,
        "verdict_initial": "UNDERIDENTIFIED",
        "joint_identified_set": sorted(set(row.target for row in full.completions)),
        "independent_bit_relaxation_size": 2 ** (2 * len(STRATA)),
        "queries": [list(query) for query in queries],
        "selected": [names[i] for i in chosen],
        "audit_cost": cost,
        "exhaustive_query_cost": sum(full.costs),
        "cheapest_first_cost": sum(full.costs[i] for i in cheapest[:length]),
        "lazy_transcript": steps,
        "direct_partition": asdict(exact),
        "evidence_ablation": asdict(inaccessible),
    }


def prediction(preaudit_record, answers):
    compatible = [row for row in preaudit_record["completions"]
                  if all(row["answers"].get(query) == value for query, value in answers.items())]
    require(len(compatible) == 1, "audit receipt does not identify one frozen completion")
    return compatible[0]["prediction"]
