"""Report actual pathwise charges separately from the frozen additive export."""

import argparse
import gzip
import json
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path


ROOT=Path(__file__).resolve().parent/"results"


def load_rows(path):
    with gzip.open(path,mode="rt",encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def observe(cost, count):
    count["valid"]+=1
    count["positive_tariff"]+=cost>0
    count["total_paid_eighths"]+=cost
    count["actual_max_paid_eighths"]=max(count["actual_max_paid_eighths"],cost)


def collect():
    primary=defaultdict(Counter)
    for row in load_rows(ROOT/"primary/rows.jsonl.gz"):
        group=primary[row[1]]
        if len(row)==4:
            group["invalid"]+=1
            continue
        observe(row[8],group)
        group["actual_intake"]+=row[9]
        group["actual_finalizations"]+=row[10]
        group["instrumented_events"]+=row[12]

    independent=defaultdict(Counter)
    for row in load_rows(ROOT/"independent/independent-index.ndjson.gz"):
        if "kind" in row:
            continue
        arm=row["id"].split("-")[1]
        group=independent[arm]
        if "invalid" in row:
            group["invalid"]+=1
            continue
        paid=8*Fraction(row["outcome"]["cost"])
        assert paid.denominator==1
        observe(int(paid),group)
        # Independent admission checks exact intake and one finalizer iff issued.
        group["actual_intake"]+=1
        group["actual_finalizations"]+=int(row["outcome"]["I"])
        group["declared_logical_moves"]+=int(row["logical_moves"])
    assert primary["pcx"]["actual_max_paid_eighths"] == independent["pcx"]["actual_max_paid_eighths"] == 8
    return {
        "schema":1,"primary":primary,"independent":independent,"actual_trial_path_cap_eighths":8,
        "guard_setup_eighths_per_role":16,"guard_setup_eighths_per_world":2,
        "calibration_in_main_trials":False,
        "notes":{
            "hard_cap":"Maximum across actual paths, not the sum of per-cell maxima.",
            "instrumented_events":"Actual primary trace event count, including bookkeeping.",
            "declared_logical_moves":"Different instrument, one independent declared move per prelude step and emitted intake, paid choice including skip, report and finalization if authorized.",
            "guard":"Eight once-per-world audited guard acquisitions per role; this charge is separate from per-attempt paid cost.",
        }
    }


if __name__=="__main__":
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output",type=Path)
    path=cli.parse_args().output
    with path.open("x",encoding="utf-8",newline="\n") as handle:
        json.dump(collect(),handle,sort_keys=True,indent=2)
        handle.write("\n")
