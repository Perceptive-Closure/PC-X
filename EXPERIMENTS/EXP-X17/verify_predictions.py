"""Cross-check all frozen exact forecast candidates and resolve the selected subset."""

import argparse
import gzip
import json
from hashlib import sha256
from pathlib import Path

from independent.model import Installation, forecast as independent_forecast, forecast_roster

ROOT=Path(__file__).resolve().parent
TABLE=ROOT/"manifests/forecast-domain.ndjson.gz"
ARMS={"pcx","high_skip","low_only","always_high","no_paid"}


def source_records():
    with gzip.open(TABLE,"rt",encoding="utf-8") as stream:
        for line in stream:
            ident,theta,beta,mode,route,depth,arm,predicted=json.loads(line)
            job=Installation.from_row({"id":ident,"theta":theta,"beta":beta,"m":mode,
                                       "k":route,"N":depth,"B":"good"})
            separate={metric:str(value) for metric,value in independent_forecast(job,arm).items()
                      if metric in predicted}
            if predicted != separate:
                raise ValueError(f"independent forecast disagreement at {ident}/{arm}")
            yield (ident,theta,beta,mode,route,depth),arm,predicted


def check_all():
    keys=set()
    for key,arm,_ in source_records():
        encoded=key+(arm,)
        assert arm in ARMS and encoded not in keys, encoded
        keys.add(encoded)
    assert len(keys)==10480
    print(f"Independently reconstructed {len(keys)} sealed forecast vectors before selection or outcomes.")


def bind(opening, output):
    payload=json.loads(opening.read_bytes())
    integrated=forecast_roster(payload)
    chosen={
        (r["id"],r["theta"],r["beta"],r["m"],r["k"],r["N"])
        for r in payload["worlds"]
    }
    chosen_found={}
    for key,arm,predicted in source_records():
        if key in chosen:
            ident=key[0]
            selected=integrated["predictions"][ident][arm]["actual"]
            assert all(selected[k]==v for k,v in predicted.items())
            chosen_found[(ident,arm)]=predicted
    assert len(chosen_found)==len(chosen)*len(ARMS)==40
    integrated["opening_sha256"]=sha256(opening.read_bytes()).hexdigest()
    integrated["verified_selected_rows"]=len(chosen_found)
    with output.open("x", encoding="utf-8",newline="\n") as sink:
        json.dump(integrated,sink,sort_keys=True,indent=2)
        sink.write("\n")
    print("Selected 40 vectors matched the published full table and independent code.")


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opening",type=Path)
    parser.add_argument("--output",type=Path)
    a=parser.parse_args()
    if a.opening and a.output:
        bind(a.opening,a.output)
    elif a.opening or a.output:
        parser.error("supply both opening and output")
    else:
        check_all()
