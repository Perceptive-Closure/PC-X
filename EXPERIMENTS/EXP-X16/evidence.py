"""Verify literal native source rows and durable useful-work receipts."""

from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import unicodedata


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return sha256(data).hexdigest()


def encode(data):
    return (json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def read_json(path):
    return json.loads(Path(path).read_bytes())


class Native:
    def __init__(self, experiment, authority, scratch):
        self.experiment = experiment.resolve()
        self.authority = authority.resolve()
        self.scratch = scratch.resolve()
        self.scratch.mkdir(parents=True, exist_ok=False)
        self.calls = 0
        self.task_count = 0
        self.workspace = self.scratch / "artifacts"
        self.seal = read_json(self.authority)

    def batch(self, tasks):
        self.calls += 1
        self.task_count += len(tasks)
        request = self.scratch / f"request-{self.calls}.json"
        response = self.scratch / f"response-{self.calls}.json"
        request.write_bytes(encode({
            "catalogue": str(self.experiment / "cases" / "catalogue.json"),
            "authority": str(self.authority), "workspace": str(self.workspace),
            "tasks": tasks,
        }))
        subprocess.run(["node", str(self.experiment / "service" / "native.mjs"),
                        str(request), str(response)], check=True)
        rows = read_json(response)["results"]
        require(len(tasks) == len(rows), "native batch count")
        return rows


def expected_quotes(stage, edge, meter, added_charge=0):
    give = [(value["obs"], value["meter"]) for value in edge["gives"]]
    commands = {
        edge.get("literal_fast", "job.fast"):
            ("job", not edge["stale"], stage["base"], 0, give),
        "job.slow": ("job", True, stage["base"] + stage["premium"], 0, give),
    }
    for name, item in stage["reads"].get(meter, {}).items():
        obs = ("stale" if edge["stale"] else "fresh") if item["observe"] == "stale" else "prepared"
        nxt = meter if item["next"] == "same" else item["next"]
        charge = added_charge if name == "ask.flag" else 0
        commands[name] = ("read", True, 0, item["price"] + charge, [(obs, nxt)])
    return commands


def verify_inventory(profile, path, result):
    """Compare complete reachable rows, including rejected candidate successors."""
    initial_obs = "start"
    if profile["variant"] == "free-guard":
        initial_obs = "stale" if path[1]["stale"] else "fresh"
    meter = profile["initial_meter"]
    require(result["initial"] == {"stage": 0, "obs": initial_obs, "meter": meter},
            "initial observation mismatch")
    pending = [(0, meter)]
    expected = {}
    while pending:
        stage, meter = pending.pop()
        if stage == len(path) or (stage, meter) in expected:
            continue
        carry = (profile["variant"] == "hidden-carry"
                 and any(edge.get("carry", False) for edge in path[:stage]))
        commands = expected_quotes(profile["stages"][stage], path[stage], meter, 4 * carry)
        expected[stage, meter] = commands
        for kind, allowed, _, _, support in commands.values():
            if allowed:
                pending.extend((stage + (kind == "job"), nxt) for _, nxt in support)
    rows = {(row["stage"], row["meter"]): row for row in result["rows"]}
    require(len(rows) == len(result["rows"]) and rows.keys() == expected.keys(),
            "native row roster mismatch")
    guards = []
    for stage, reached_meter in sorted(rows):
        row = rows[stage, reached_meter]
        edge = path[stage]
        require(row["edge"] == edge["id"], "wrong installed edge")
        before = row["representation_before"]
        require(digest(encode(before)) == row["representation_before_sha256"], "row prior binding hash")
        commands = {command["id"]: command for command in row["commands"]}
        reference = expected[stage, reached_meter]
        require(len(commands) == len(row["commands"]) and commands.keys() == reference.keys(),
                "literal source menu differs")
        for name, cmd in commands.items():
            kind, allowed, work, paid, support = reference[name]
            require((cmd["kind"], cmd["enabled"], cmd["allowed"], cmd["work"], cmd["paid"])
                    == (kind, True, allowed, work, paid), "guard or tariff differs")
            actual_support = []
            changes = []
            for outcome in cmd["outcomes"]:
                after = outcome["representation_after"]
                require(digest(encode(after)) == outcome["representation_after_sha256"],
                        "successor binding hash")
                changed = encode(before) != encode(after)
                require(changed == outcome["r_changed"], "false extensional comparison")
                if changed:
                    require(len(before) == len(after), "R relation arity changed")
                    require([index for index, pair in enumerate(zip(before, after, strict=True))
                             if pair[0] != pair[1]] == [stage], "changed binding is not the current one")
                changes.append(changed)
                actual_support.append((outcome["obs"], outcome["meter"]))
            require(actual_support == support, "incomplete ordered receipt support")
            require((not any(changes)) == allowed, "whole-occurrence freeze differs")
            guards.append({"stage": stage, "meter": reached_meter, "edge": edge["id"],
                           "id": name, "kind": kind, "allowed": allowed,
                           "work": work, "paid": paid, "support": actual_support,
                           "r_changed": changes})
    return rows, guards


def fastest_jobs(rows, count):
    choices = []
    for stage in range(count):
        local = {
            min((command["work"], command["id"]) for command in row["commands"]
                if command["kind"] == "job" and command["allowed"])
            for (i, _), row in rows.items() if i == stage
        }
        require(len(local) == 1, "fastest known-mode cost or command depends on meter")
        choices.append(local.pop())
    return sum(work for work, _ in choices), [action for _, action in choices]


def read_product(document):
    title = unicodedata.normalize("NFKC", document["title"])
    category = unicodedata.normalize("NFKC", document["category"]).lower()
    category = re.sub(r"[^a-z0-9]+", "-", category).strip("-")[:64].rstrip("-")
    return {
        "id": document["id"], "title": " ".join(title.split()),
        "category": category or "uncategorized",
        "body": document["body"].replace("\r\n", "\n").replace("\r", "\n"),
    }


def verify_artifacts(native, task, profile, run):
    """Verify the actual file tree, independent digests, transformation and route."""
    truth = run["truth"]
    workspace = (native.workspace / task["id"]).resolve()
    require(workspace.is_relative_to(native.workspace), "invalid run directory")
    document = {key: task["document"][key] for key in ("id", "title", "category", "body")}
    normalized = read_product(document)
    current = digest(encode(normalized))
    earlier = digest(encode({**normalized, "body": normalized["body"] + "\n[earlier revision]\n"}))
    edges = [next(edge for edge in stage["edges"] if edge["id"] == identifier)
             for stage, identifier in zip(profile["stages"], task["path"], strict=True)]
    installed = [earlier if edge["stale"] else current for edge in edges]
    expected_destination = "routed/category-" + normalized["category"]
    require(truth["document_sha256"] == digest(encode(document)), "wrong original document digest")
    require(truth["expected_destination"] == expected_destination, "incorrect source-derived route")
    require(run["moves"] == len(run["steps"])
            and run["work"] == sum(step["work"] for step in run["steps"])
            and run["paid"] == sum(step["paid"] for step in run["steps"]), "incorrect run totals")
    require(run["moves"] <= profile["horizon"] and run["work"] <= profile["deadline"],
            "run exceeded declared budgets")
    actual = []
    reviews = []
    last = None
    affected = False
    full = None
    for step in run["steps"]:
        if step["artifact"] is None:
            require(step["work"] == 0, "read used work without a job artifact")
            affected |= profile["variant"] == "changed-instrument" and step["act"] == "ask.flag"
            continue
        stage = len(actual)
        stage_name = profile["stages"][stage]["task"]
        destination = None
        if stage + 1 == len(edges):
            destination = "quarantine" if affected else expected_destination
        if stage_name.startswith("review-"):
            length = int(stage_name[7:])
            terms = sorted({term for term in re.findall(r"[^\W_]+", normalized["body"].lower())
                            if len(term) >= length})
            reviews.append({"task": stage_name, "min_length": length,
                            "term_count": len(terms), "terms": terms})
        relative = f"{destination}/document.json" if destination else f"stages/{stage:03}.json"
        require(relative == step["artifact"] and step["stage"] == stage, "wrong durable stage path")
        artifact = (workspace / relative).resolve()
        require(artifact.is_relative_to(workspace), "artifact outside own run workspace")
        raw = artifact.read_bytes()
        require(digest(raw) == truth["artifact_sha256"][relative], "incorrect native artifact hash")
        value = json.loads(raw)
        expected = {
            "schema": 1, "profile": task["profile"], "stage": stage, "task": stage_name,
            "edge": task["path"][stage], "action": step["act"],
            "receipt": {"obs": step["obs"], "meter": step["next_meter"]},
            "work": step["work"], "paid": step["paid"],
            "input_sha256": digest(encode(document)), "prior_output_sha256": last,
            "source_document": document if stage == 0 else None,
            "representation_before": installed, "representation_before_sha256": digest(encode(installed)),
            "representation_after": installed, "representation_after_sha256": digest(encode(installed)),
            "product": {"document": normalized, "reviews": reviews, "destination": destination},
            **{key: native.seal[key] for key in
               ("catalogue_sha256", "source_commit", "frozen_manifest_sha256")},
        }
        require(value == expected and raw == encode(expected), "wrong persisted contents or byte encoding")
        actual.append(relative)
        last = digest(raw)
        full = raw.decode("utf-8")
    observed_files = sorted(file.relative_to(workspace).as_posix()
                            for file in workspace.rglob("*") if file.is_file())
    require(truth["artifact_paths"] == actual and sorted(actual) == observed_files
            and set(truth["artifact_sha256"]) == set(actual), "unexpected or missing durable files")
    destination = None if len(actual) < len(edges) else ("quarantine" if affected else expected_destination)
    require(truth["done"] == len(actual) and truth["actual_destination"] == destination
            and truth["complete"] == (destination == expected_destination), "wrong useful completion")
    return full


def traverse(policy, rows, initial):
    """Enumerate the actual supported tapes for one fully known installed path."""
    leaves = []
    def step(node, stage, meter, tape, receipts, cost, work):
        if "verdict" in node:
            leaves.append({"tape": tape, "receipt_trace": receipts, "paid": cost,
                           "work": work, "done": stage, "verdict": node["verdict"]})
            return
        row = rows[stage, meter]
        cmd = next((item for item in row["commands"] if item["id"] == node["act"]), None)
        require(cmd is not None and cmd["allowed"], "forecast uses unavailable primary command")
        for index, outcome in enumerate(cmd["outcomes"]):
            nxt = outcome["meter"]
            key = f"{outcome['obs']}|{nxt}"
            require(key in node["next"], "forecast omits a supported receipt")
            step(node["next"][key], stage + (cmd["kind"] == "job"), nxt,
                 tape + [index], receipts + [key], cost + cmd["paid"], work + cmd["work"])
    step(policy, 0, initial["meter"], [], [], 0, 0)
    return leaves
