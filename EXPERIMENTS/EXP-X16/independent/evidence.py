"""Native row, receipt and durable byte checks for the independent X16 replay."""

from dataclasses import dataclass
from hashlib import sha256
from itertools import groupby
import json
from pathlib import Path
import re
import subprocess
import unicodedata

from reference import command_row, initial_receipt, receipt_key, static_panel


PROBE = {
    "id": "public-training-inventory-probe",
    "title": "EXP-X16 native row probe",
    "category": "Training probe",
    "body": "Public synthetic document for native inventory.\n",
}
JS_SPACE = re.compile(r"[\t\n\v\f\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]+")
SURROGATE = re.compile(r"[\ud800-\udfff]")


class EvidenceError(ValueError):
    pass


def digest(data):
    return sha256(data).hexdigest()


def wire(value):
    """Encode the documented record wire format independently of Node."""
    text = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    text = SURROGATE.sub(lambda match: "\\u%04x" % ord(match[0]), text)
    return (text + "\n").encode("utf-8")


def describe(value):
    return repr(value)[:400]


def equal(actual, expected, context):
    # Canonical key order ignores JSON property order where it is not part of the ABI
    # and still distinguishes logical flags such as true from integer 1.
    if json.dumps(actual, sort_keys=True) != json.dumps(expected, sort_keys=True):
        raise EvidenceError(f"{context}: expected {describe(expected)}, got {describe(actual)}")


def read_json(path):
    return json.loads(path.read_bytes())


def save_json(path, value):
    path.write_bytes(wire(value))


def select_keys(item, names):
    return {name: item[name] for name in names}


@dataclass(frozen=True)
class Document:
    source: dict
    normalized: dict
    source_hash: str
    current: str
    earlier: str
    destination: str


def process_document(fields):
    document = select_keys(fields, ("id", "title", "category", "body"))
    title = JS_SPACE.sub(" ", unicodedata.normalize("NFKC", document["title"])).strip(" ")
    category = unicodedata.normalize("NFKC", document["category"]).lower()
    category = re.sub(r"[^a-z0-9]+", "-", category).strip("-")[:64].rstrip("-")
    category = category or "uncategorized"
    body = document["body"].replace("\r\n", "\n").replace("\r", "\n")
    normalized = dict(id=document["id"], title=title, category=category, body=body)
    earlier = dict(normalized, body=body + "\n[earlier revision]\n")
    return Document(
        document, normalized, digest(wire(document)), digest(wire(normalized)),
        digest(wire(earlier)), f"routed/category-{category}",
    )


def installed_revisions(path, document):
    return [document.earlier if edge["stale"] else document.current for edge in path.edges]


def review_terms(body, min_length):
    words = (
        "".join(run)
        for word, run in groupby(body.lower(), lambda ch: unicodedata.category(ch)[0] in "LN")
        if word
    )
    return sorted(
        {word for word in words if len(word) >= min_length},
        key=lambda word: word.encode("utf-16-be", errors="surrogatepass"),
    )


def next_product(phase, source, previous, destination):
    if phase in {"receive", "receive-route"}:
        document, reviews = source.normalized, []
    else:
        document, reviews = previous["document"], previous["reviews"]
    if phase.startswith("review-"):
        min_length = int(phase.removeprefix("review-"))
        terms = review_terms(document["body"], min_length)
        reviews = [*reviews, dict(task=phase, min_length=min_length, term_count=len(terms), terms=terms)]
    return dict(document=document, reviews=reviews, destination=destination)


def expected_inventory(profile, path):
    initial = initial_receipt(profile, path)
    source = process_document(PROBE)
    revisions = installed_revisions(path, source)
    before_hash = digest(wire(revisions))
    meters = {initial["meter"]}
    rows = {}

    for stage, edge in enumerate(path.edges):
        following = set()
        unvisited = set(meters)
        visited = set()
        while unvisited:
            meter = unvisited.pop()
            visited.add(meter)
            expected = []
            for act, command in command_row(profile, path, stage, meter).items():
                outcomes = []
                for obs, next_meter, changed in command.outcomes:
                    after = list(revisions)
                    if changed:
                        after[stage] = source.current
                    outcomes.append(dict(
                        obs=obs, meter=next_meter, r_changed=changed,
                        representation_after=after, representation_after_sha256=digest(wire(after)),
                    ))
                    if command.allowed and command.kind == "job":
                        following.add(next_meter)
                    elif command.allowed and next_meter not in visited:
                        unvisited.add(next_meter)
                expected.append(dict(
                    id=act, kind=command.kind, enabled=True, allowed=command.allowed,
                    work=command.work, paid=command.paid, outcomes=outcomes,
                ))
            rows[(stage, meter)] = dict(
                stage=stage, edge=edge["id"], meter=meter, commands=expected,
                representation_before=revisions, representation_before_sha256=before_hash,
            )
        meters = following
    return initial, rows


def inspect_inventory(profile, path, actual):
    if path is None:
        equal(actual, {"status": "denied", "reason": "invalid-installation"}, "invalid path inventory")
        return {"guard_rows": 0, "commands": 0, "raw_outcomes": 0}
    initial, expected_rows = expected_inventory(profile, path)
    equal(actual["initial"], initial, "inventory initial receipt")
    rows = {(row["stage"], row["meter"]): row for row in actual["rows"]}
    equal(len(rows), len(actual["rows"]), "unique inventory row keys")
    equal(sorted(map(list, rows)), sorted(map(list, expected_rows)), "reachable row keys")
    minima = {}
    commands = 0
    outcomes = 0
    for key, expected in expected_rows.items():
        row = rows[key]
        context = f"stage {key[0]} meter {key[1]}"
        observed = row["commands"]
        equal(len({command["id"] for command in observed}), len(observed), f"{context} unique commands")
        equal(
            sorted(observed, key=lambda item: item["id"]),
            sorted(expected["commands"], key=lambda item: item["id"]),
            f"{context} typed commands and raw ordered outcomes",
        )
        for field in ("stage", "edge", "meter", "representation_before", "representation_before_sha256"):
            equal(row[field], expected[field], f"{context} {field}")
        commands += len(observed)
        outcomes += sum(len(command["outcomes"]) for command in observed)
        minimum = min(
            command["work"] for command in observed
            if command["kind"] == "job" and command["enabled"] and command["allowed"]
        )
        stage = key[0]
        if stage in minima:
            equal(minimum, minima[stage], f"{context} known minimum work across meters")
        minima[stage] = minimum
    work = [minima[stage] for stage in range(len(path.ids))]
    equal(sum(work), path.remaining[0], "native intrinsic tariff lower bound")
    return {
        "guard_rows": len(rows), "commands": commands, "raw_outcomes": outcomes,
        "known_minimum_by_stage": work, "known_minimum_work": sum(work), "target": path.verdict,
    }


def to_native_static(tree):
    if "label" in tree:
        label = tree["label"]
        return {"verdict": label} if label in ("YES", "NO") else {}
    return {
        "ask": tree["query"],
        "next": {answer: to_native_static(node) for answer, node in tree["next"].items()},
    }


def inspect_static(profile, path, task, actual, workspace):
    panel = {query.id: query for query in static_panel(profile, (path,))}
    steps = []
    verdict = None
    if "queries" in task:
        sequence = task["queries"]
        for query_id in sequence:
            query = panel[query_id]
            steps.append(dict(id=query.id, answer=query.answers[0], paid=query.price))
    else:
        node = task["static_policy"]
        while "ask" in node:
            query = panel[node["ask"]]
            answer = query.answers[0]
            steps.append(dict(id=query.id, answer=answer, paid=query.price))
            node = node["next"][answer]
        verdict = node.get("verdict")
    expected = dict(
        status="stopped", verdict=verdict, reason=None,
        answers={step["id"]: step["answer"] for step in steps},
        paid=sum(step["paid"] for step in steps),
        sequence=[step["id"] for step in steps], steps=steps,
    )
    if verdict:
        equal(verdict, path.verdict, "static declared label")
    equal(actual, expected, "static responses")
    equal((workspace / task["id"]).exists(), False, "pure query has no work directory")
    return {"queries": len(steps), "paid": expected["paid"]}


def policy_tapes(profile, path, policy):
    """Walk the ordered support of all reachable acts within this installed run."""
    def visit(stage, meter, work, node, tape):
        if node is None or "verdict" in node or len(tape) >= profile["horizon"]:
            yield tape
            return
        act = node["act"]
        command = command_row(profile, path, stage, meter).get(act)
        if command is None or not command.allowed or work + command.work > profile["deadline"]:
            yield tape
            return
        for index, (obs, next_meter, _) in enumerate(command.outcomes):
            key = receipt_key(obs, next_meter)
            yield from visit(
                stage + (command.kind == "job"), next_meter, work + command.work,
                node.get("next", {}).get(key), (*tape, index),
            )

    initial = initial_receipt(profile, path)
    return tuple(visit(0, initial["meter"], 0, policy, ()))


def work_tapes(profile, path):
    """Enumerate supported ordinary receipts up to completion or quota denial."""
    def visit(stage, meter, work, tape):
        if stage == len(path.ids) or stage >= profile["horizon"]:
            yield tape
            return
        act = path.fastest_job_actions[stage]
        command = command_row(profile, path, stage, meter)[act]
        if work + command.work > profile["deadline"]:
            yield tape
            return
        for index, (_, next_meter, _) in enumerate(command.outcomes):
            yield from visit(stage + 1, next_meter, work + command.work, (*tape, index))

    initial = initial_receipt(profile, path)
    return tuple(visit(0, initial["meter"], 0, ()))


def plan_run(profile, path, task):
    document = process_document(task["document"])
    if path is None:
        return document, None, ("denied", None, "invalid-installation"), []
    initial = initial_receipt(profile, path)
    stage, meter, work, disturbed = 0, initial["meter"], 0, False
    manual = "actions" in task
    node = task.get("policy")
    tape = task.get("tape", [])
    planned = []
    while True:
        move = len(planned)
        if manual and move == len(task["actions"]):
            stop = "manual-done", None, None
            break
        if not manual and "verdict" in node:
            stop = "stopped", node["verdict"], None
            break
        if move >= profile["horizon"]:
            stop = "horizon", None, None
            break
        act = task["actions"][move] if manual else node["act"]
        command = command_row(profile, path, stage, meter).get(act)
        if command is None:
            stop = "denied", None, "unknown-command"
            break
        if not command.allowed:
            stop = "denied", None, "r-freeze"
            break
        if work + command.work > profile["deadline"]:
            stop = "denied", None, "work-deadline"
            break
        index = tape[move] if move < len(tape) else 0
        if type(index) is not int or not 0 <= index < len(command.outcomes):
            stop = "denied", None, "unsupported-outcome"
            break
        obs, after_meter, _ = command.outcomes[index]
        artifact = None
        if command.kind == "job":
            if stage == len(path.ids) - 1:
                destination = "quarantine" if disturbed else document.destination
                artifact = f"{destination}/document.json"
            else:
                artifact = f"stages/{stage:03d}.json"
        elif profile["variant"] == "changed-instrument" and act == "ask.flag":
            disturbed = True
        planned.append(dict(
            act=act, stage=stage, meter=meter, obs=obs, next_meter=after_meter,
            work=command.work, paid=command.paid, artifact=artifact,
        ))
        stage += command.kind == "job"
        work += command.work
        meter = after_meter
        if not manual:
            key = receipt_key(obs, meter)
            node = node.get("next", {}).get(key)
            if node is None:
                stop = "missing-branch", None, None
                break
    return document, initial, stop, planned


def expected_record(profile, path, document, step, seal, previous, previous_hash):
    stage = step["stage"]
    task = profile["stages"][stage]["task"]
    revisions = installed_revisions(path, document)
    revisions_hash = digest(wire(revisions))
    destination = step["artifact"].rsplit("/", 1)[0] if stage == len(path.ids) - 1 else None
    product = next_product(task, document, previous, destination)
    return dict(
        schema=1, profile=profile["id"], stage=stage, task=task, edge=path.ids[stage],
        action=step["act"], receipt=dict(obs=step["obs"], meter=step["next_meter"]),
        work=step["work"], paid=step["paid"], input_sha256=document.source_hash,
        prior_output_sha256=previous_hash, source_document=document.source if stage == 0 else None,
        representation_before=revisions, representation_before_sha256=revisions_hash,
        representation_after=revisions, representation_after_sha256=revisions_hash, product=product,
        catalogue_sha256=seal["catalogue_sha256"], source_commit=seal["source_commit"],
        frozen_manifest_sha256=seal["frozen_manifest_sha256"],
    )


def inspect_run(profile, path, task, actual, workspace, seal):
    document, initial, stop, planned = plan_run(profile, path, task)
    status, verdict, reason = stop
    paid, work = (sum(step[name] for step in planned) for name in ("paid", "work"))
    expected = dict(
        initial=initial, status=status, verdict=verdict, reason=reason, steps=planned,
        work=work, paid=paid, moves=len(planned),
    )
    equal(select_keys(actual, expected), expected, "observable receipts and quota accounting")

    base = workspace / task["id"]
    if base.is_symlink() or not base.resolve().is_relative_to(workspace.resolve()):
        raise EvidenceError("work directory lies outside scratch workspace")
    previous, previous_hash = None, None
    hashes = {}
    artifact_steps = [step for step in planned if step["artifact"] is not None]
    for step in artifact_steps:
        relative = step["artifact"]
        target = base / relative
        if target.is_symlink() or not target.resolve().is_relative_to(base.resolve()):
            raise EvidenceError(f"artifact {relative} lies outside its run directory")
        artifact = target.read_bytes()
        record = expected_record(profile, path, document, step, seal, previous, previous_hash)
        if artifact != wire(record):
            try:
                equal(json.loads(artifact), record, f"{relative} independently reconstructed work")
            except (ValueError, UnicodeError) as problem:
                raise EvidenceError(f"{relative}: {problem}") from problem
            raise EvidenceError(f"{relative}: schema values match but exact encoded bytes differ")
        previous = record["product"]
        previous_hash = digest(artifact)
        hashes[relative] = previous_hash

    if not hashes and base.exists():
        raise EvidenceError("native claimed a work directory without an authorized job")
    files = {file.relative_to(base).as_posix() for file in base.rglob("*") if not file.is_dir()}
    equal(sorted(files), sorted(hashes), "workspace contains precisely the declared durable files")
    destination = previous["destination"] if previous else None
    complete = path is not None and len(hashes) == len(path.ids) and destination == document.destination
    truth = dict(
        complete=complete, done=len(hashes), expected_destination=document.destination,
        actual_destination=destination, artifact_paths=list(hashes), artifact_sha256=hashes,
        document_sha256=document.source_hash,
    )
    equal(actual["truth"], truth, "native truth against persisted artifact bytes")
    return {
        **select_keys(expected, ("status", "verdict", "reason", "work", "paid", "moves")),
        "truth": truth,
    }


class NativeBatch:
    def __init__(self, service, catalogue, authority, output):
        self.service = service.resolve()
        self.catalogue = catalogue.resolve()
        self.authority = authority.resolve()
        self.output = output.resolve()

    def launch(self, name, tasks, reject=False):
        workspace = self.output / f"{name}-work"
        request = self.output / f"{name}-request.json"
        response = self.output / f"{name}-response.json"
        save_json(request, dict(
            catalogue=str(self.catalogue), authority=str(self.authority),
            workspace=str(workspace), tasks=tasks,
        ))
        process = subprocess.run(
            ["node", str(self.service), str(request), str(response)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300, check=False,
        )
        (self.output / f"{name}-stderr.txt").write_bytes(process.stderr)
        if reject:
            equal(process.returncode, 1, f"{name} seal failure return code")
            equal(response.exists(), False, f"{name} seal failure has no response")
            equal(workspace.exists(), False, f"{name} seal failure has no artifacts")
            return process.stderr.decode("utf-8")
        if process.returncode:
            raise EvidenceError(f"native batch {name} failed: {process.stderr.decode('utf-8', errors='replace')}")
        results = read_json(response)["results"]
        equal(len(results), len(tasks), f"{name} request/result count")
        return workspace, results
