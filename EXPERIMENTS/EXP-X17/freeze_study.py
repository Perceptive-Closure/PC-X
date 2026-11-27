"""Generate or verify the immutable X17 decision and forecast inputs."""

import argparse
import gzip
import json
from fractions import Fraction as Q
from hashlib import sha256
from itertools import product
from pathlib import Path

from controller.forecast import forecast


ROOT = Path(__file__).resolve().parent
ARMS = ("pcx", "high_skip", "low_only", "always_high", "no_paid")
TABLE = "manifests/forecast-domain.ndjson.gz"
TABLE_INDEX = "manifests/forecast-domain-summary.json"
FREEZE = "manifests/frozen-inputs.json"


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",",":")).encode() + b"\n"


def write(path, data):
    path.write_text(json.dumps(data, sort_keys=True, indent=2)+"\n",
                    encoding="utf-8", newline="\n")


def worlds_in(domain):
    common = (domain["beta_endpoints"], (0,1), ("L","R"))
    for index, theta, depths in [
        (1,Q(1,4),domain["matched_depths"]), (2,Q(3,4),domain["matched_depths"]),
        (3,Q(1,8),domain["extreme_depths"]), (4,Q(7,8),domain["extreme_depths"]),
    ]:
        for beta, mode, route, depth in product(*common, depths):
            yield f"s{index:02d}", theta, Q(beta), mode, route, depth
    for index, numerator_grid in enumerate(domain["interior_theta_numerators"],5):
        for value,beta,mode,route,depth in product(
                numerator_grid,domain["interior_beta"],(0,1),("L","R"),domain["interior_depths"]):
            yield f"s{index:02d}", Q(value,domain["theta_denominator"]), Q(beta), mode, route, depth


def generate_forecast():
    domain_file = ROOT / "custody/roster-domain.json"
    domain_bytes = domain_file.read_bytes()
    content_hash = sha256()
    worlds, rows = 0, 0
    target = ROOT / TABLE
    with target.open("wb") as output, gzip.GzipFile(filename="", mode="wb", fileobj=output,mtime=0) as stream:
        for ident,theta,beta,mode,route,depth in worlds_in(json.loads(domain_bytes)):
            worlds += 1
            for arm in ARMS:
                means = forecast(theta,beta,mode,depth,arm)
                record = [ident,str(theta),str(beta),mode,route,depth,arm,
                          {key:str(value) for key,value in means.items()}]
                line = canonical(record)
                stream.write(line)
                content_hash.update(line)
                rows += 1
    assert worlds==2096 and rows==10480
    write(ROOT/TABLE_INDEX, {
        "possible_stratum_rows":worlds,"forecast_records":rows,"arms":ARMS,
        "domain_sha256":sha256(domain_bytes).hexdigest(),
        "decompressed_forecasts_sha256":content_hash.hexdigest(),
        "stored_forecasts_sha256":sha256(target.read_bytes()).hexdigest(),
        "columns":["id","theta","beta","m","k","N","arm","exact_forecasts"],
    })
    print(f"{rows} exact pre-selection forecast records generated for {worlds} candidate rows.")


def files_to_freeze():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel in (FREEZE,"README.md","RESULTS.md","REPRODUCTION.md") or path.name == "Path.md":
            continue
        if rel.startswith(("results/","tests/hostile/")) or "__pycache__" in path.parts:
            continue
        yield path,rel


def identity():
    return {rel:{"sha256":sha256(path.read_bytes()).hexdigest(),"bytes":path.stat().st_size}
            for path,rel in files_to_freeze()}


def register():
    manifest = {"schema":1,"scope":"EXPERIMENTS/EXP-X17","files":identity()}
    assert len(manifest["files"]) >= 45
    # All actual research outputs plus the registration and holdout receipts
    # are allowed as later additions, with bytes of the registered inputs fixed.
    write(ROOT/FREEZE, manifest)
    print(f"{len(manifest['files'])} scientific input files fixed.")


def verify():
    manifest = json.loads((ROOT/FREEZE).read_bytes())
    terms = manifest["files"]
    for rel, entry in terms.items():
        item = (ROOT/rel).resolve()
        assert item.is_relative_to(ROOT) and item.is_file(), rel
        assert item.stat().st_size==entry["bytes"],rel
        assert sha256(item.read_bytes()).hexdigest()==entry["sha256"],rel
    index = json.loads((ROOT/TABLE_INDEX).read_bytes())
    assert sha256(gzip.decompress((ROOT/TABLE).read_bytes())).hexdigest()==index["decompressed_forecasts_sha256"]
    print(f"{len(terms)} exact frozen inputs and all forecast table bytes verified.")


if __name__ == "__main__":
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode",choices=("forecast","register","verify"))
    {"forecast":generate_forecast,"register":register,"verify":verify}[ap.parse_args().mode]()
