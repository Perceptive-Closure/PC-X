"""Verify final X17 published evidence by replaying its fixed deterministic reductions."""

import gzip
import json
import re
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
from pathlib import Path

from analyze import analyze
from freeze_study import verify as verify_freeze


ROOT = Path(__file__).resolve().parent
PRIMARY = ROOT/"results/primary"
INDEPENDENT = ROOT/"results/independent"
CUSTODY = ROOT/"custody"


def read(path):
    return json.loads(path.read_bytes())


def primary_check(report):
    index = PRIMARY/"rows.jsonl.gz"
    assert sha256(index.read_bytes()).hexdigest() == report["compressed_rows_sha256"]
    collected = defaultdict(Counter)
    next_trial = Counter()
    state = sha256()
    chains = defaultdict(sha256)
    with gzip.open(index,"rb") as file:
        for line in file:
            state.update(line)
            src = json.loads(line)
            ident = tuple(src[:2])
            assert src[2] == next_trial[ident], (ident,src[2])
            next_trial[ident] += 1
            c = collected[ident]
            if len(src) == 4:
                assert "invalid" in src[3]
                c["invalid"] += 1
                continue
            assert len(src) == len(report["fields"])
            for field,value in zip(report["fields"][3:11],src[3:11]):
                c[field] += value
            c["operations"] += src[-2]
            c["max_cost8"] = max(c["max_cost8"],src[8])
            c["proposal_zero"] += src[11] == 0
            c["proposal_one"] += src[11] == 1
            c["valid"] += 1
            assert re.fullmatch("[0-9a-f]{64}",src[-1])
            chains[ident].update(bytes.fromhex(src[-1]))
    for row in report["cells"]:
        ident = row["world"],row["arm"]
        c = collected[ident]
        c["attempts"] = next_trial[ident]
        for key,val in row["counts"].items():
            assert c[key]==val, (ident,key,c[key],val)
        assert chains[ident].hexdigest()==row["record_chain_sha256"]
    assert state.hexdigest()==report["uncompressed_rows_sha256"]
    return sum(next_trial.values())


def independent_check(report):
    index = INDEPENDENT/"independent-index.ndjson.gz"
    assert sha256(index.read_bytes()).hexdigest()==report["raw_index_sha256"]
    counts = defaultdict(Counter)
    diagnostics = defaultdict(Counter)
    for main in ("s01","s02","s03","s04","s05","s06","s07","s08"):
        diagnostics[main]  # establish each declared world
    with gzip.open(index,"rt",encoding="utf8") as stream:
        for line in stream:
            row = json.loads(line)
            if kind := row.get("kind"):
                cell = diagnostics[row["id"].split("-")[0]]
                if kind == "ordinary":
                    cell["ordinary_count"] += 1
                    cell["ordinary_violation"] += row["V"]
                elif kind == "paired":
                    cell["paired_count"] += 1
                    cell["paired_issued"] += row["I"]
                    cell["paired_disagreement"] += row["actual_V"] - row["nominal_V"]
                    cell["strip_count"] += row["in_strip"]
                else:
                    raise AssertionError(f"unknown independent recorded diagnostic {kind}")
                continue
            world,arm,trial = row["id"].split("-")
            stat = counts[world,arm]
            assert int(trial)==stat["planned"]
            stat["planned"] += 1
            if "invalid" in row:
                stat["invalid"] += 1
                continue
            stat["valid"] += 1
            values = {key:Fraction(v) for key,v in row["outcome"].items()}
            for key in ("wrong","I","V","VI"):
                stat[key] += values[key]
            stat["G_halves"] += 2*values["G"]
            stat["cost_eighths"] += 8*values["cost"]
            stat["Z_eighths"] += 8*values["Z"]
            assert re.fullmatch("[0-9a-f]{64}",row["trace_sha256"])
    for cell in report["cells"]:
        stat = counts[cell["id"],cell["arm"]]
        for name in ("planned","valid","invalid"):
            assert stat[name]==cell[name]
        for k,v in cell["counts"].items():
            assert stat[k]==v,(cell["id"],cell["arm"],k,stat[k],v)
    for item in report["diagnostics"]:
        d=diagnostics[item["id"]]
        for k in ("ordinary_count","ordinary_violation","paired_count","paired_issued",
                  "paired_disagreement","strip_count"):
            assert d[k]==item[k]
    return sum(c["planned"] for c in counts.values())


def check_examples(path):
    entries = read(path)
    for row in entries.values():
        for address,body in row["artifacts"].items():
            assert sha256(body.encode("utf-8")).hexdigest()==address
    return len(entries)


def main():
    verify_freeze()
    plan = read(CUSTODY/"draw-plan.json")
    release = read(CUSTODY/"run-authorization.json")
    assert release["phase"]=="PH-06-VERIFIED" and release["round"]==plan["round"]
    for name,digest in release["files"].items():
        assert Path(name).name==name and sha256((CUSTODY/name).read_bytes()).hexdigest()==digest
    primary=read(PRIMARY/"report.json")
    independent=read(INDEPENDENT/"independent-summary.json")
    n_primary=primary_check(primary)
    n_independent=independent_check(independent)
    assert n_primary==n_independent==163840
    result=analyze(read(CUSTODY/"opening-roster.json"),primary,independent)
    assert json.loads(json.dumps(result))==read(ROOT/"results/statistics/summary.json")
    n_examples=check_examples(PRIMARY/"artifact-examples.json")
    controls=read(ROOT/"results/controls/observations.json")
    assert set(controls)=={f"C{i:02d}" for i in range(1,20)}
    print(f"Verified {n_primary} primary and {n_independent} independent indexed attempts, "
          f"{n_examples} actual primary artifact examples, and the final fixed analysis."
          " See the custody verifier for the external BLS validation.")


if __name__=="__main__":
    main()
