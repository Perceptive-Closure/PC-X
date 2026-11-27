"""Authenticate the public before-opening X17 freeze and rebuild its exact forecasts."""

import argparse
import gzip
import json
import subprocess
from decimal import Decimal, localcontext
from fractions import Fraction as F
from hashlib import sha256
from itertools import product
from pathlib import Path


FREEZE = "be574f4eaba8a52b50c5604e87075ab4cac81b79"
ROOT = "EXPERIMENTS/EXP-X17/"
ARMS = ("pcx", "high_skip", "low_only", "always_high", "no_paid")


class Blobs:
    def __enter__(self):
        self.process = subprocess.Popen(
            ["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
        )
        return self

    def __exit__(self, *_exc):
        self.process.stdin.close()
        with self.process.stdout:
            assert self.process.wait() == 0

    def read(self, path):
        request = (FREEZE + ":" + ROOT + path).encode("ascii")
        self.process.stdin.write(request + b"\n")
        self.process.stdin.flush()
        header = self.process.stdout.readline().split()
        assert len(header) == 3 and header[1] == b"blob", path
        size = int(header[2])
        body = self.process.stdout.read(size)
        assert len(body) == size and self.process.stdout.read(1) == b"\n", path
        return body


def digest(body):
    return sha256(body).hexdigest()


def registered_worlds(domain):
    endpoints = (F(1, 4), F(3, 4), F(1, 8), F(7, 8))
    for index, theta in enumerate(endpoints, 1):
        depths = domain["matched_depths" if index < 3 else "extreme_depths"]
        for beta, tag, route, depth in product(domain["beta_endpoints"], (0, 1), "LR", depths):
            yield f"s{index:02}", theta, F(beta), tag, route, depth
    for index, integers in enumerate(domain["interior_theta_numerators"], 5):
        for integer, beta, tag, route, depth in product(
            integers, domain["interior_beta"], (0, 1), "LR", domain["interior_depths"]
        ):
            yield f"s{index:02}", F(integer, domain["theta_denominator"]), F(beta), tag, route, depth


def independent_expected(theta, beta, tag, depth, arm):
    stay = (1 + (-1) ** tag * theta * (1 - theta)) / 2
    endings = F(1), F(0)
    for _ in range(depth):
        old_zero, old_one = endings
        endings = (
            old_zero * stay + old_one * (1 - stay),
            old_one * stay + old_zero * (1 - stay),
        )
    cases = {
        "pcx": ((F(2, 3), F(3, 4) - theta / 2, F(3, 8)), (F(1, 3), 1 - theta, 1)),
        "high_skip": ((F(2, 3), 1 - theta, 1), (F(1, 3), F(1, 2), 0)),
        "low_only": ((F(1), F(3, 4) - theta / 2, F(3, 8)),),
        "always_high": ((F(1), 1 - theta, 1),),
        "no_paid": ((F(1), F(1, 2), 0),),
    }[arm]
    issue = sum(mass * accept for mass, accept, _ in cases)
    paid = sum(mass * price for mass, _, price in cases)
    defect = sum(
        mass * accept * carried_mass * (theta / 4 + F(tag ^ v, 16) + beta)
        for mass, accept, _ in cases
        for v, carried_mass in enumerate(endings)
    )
    positive = theta < F(1, 2)
    return {
        "I": issue, "V": defect, "VI": defect,
        "wrong": 1 - issue if positive else issue,
        "G": F(1, 2) + ((issue - defect) / 2 if positive else 0),
        "cost": paid, "Z": defect - F(3, 8) * issue,
    }


def verify():
    with Blobs() as blobs:
        manifest = json.loads(blobs.read("manifests/frozen-inputs.json"))
        assert manifest["schema"] == 1 and manifest["scope"] == ROOT.rstrip("/")
        for path, row in manifest["files"].items():
            assert not (set(path.split("/")) & {"", ".", ".."}), path
            body = blobs.read(path)
            assert row == {"bytes": len(body), "sha256": digest(body)}, path
        packed = blobs.read("manifests/forecast-domain.ndjson.gz")
        unpacked = gzip.decompress(packed)
        index = json.loads(blobs.read("manifests/forecast-domain-summary.json"))
        domain = blobs.read("custody/roster-domain.json")
        assert index["stored_forecasts_sha256"] == digest(packed)
        assert index["decompressed_forecasts_sha256"] == digest(unpacked)
        assert index["domain_sha256"] == digest(domain)
    expected_worlds = set(registered_worlds(json.loads(domain)))
    seen = set()
    for line in unpacked.splitlines():
        ident, theta, beta, tag, route, depth, arm, reported = json.loads(line)
        world = ident, F(theta), F(beta), tag, route, depth
        assert world in expected_worlds and arm in ARMS and (world, arm) not in seen
        assert {key: F(number) for key, number in reported.items()} == independent_expected(
            world[1], world[2], tag, depth, arm
        ), (world, arm)
        seen.add((world, arm))
    assert len(expected_worlds) == index["possible_stratum_rows"] == 2096
    assert len(seen) == index["forecast_records"] == 10480 == len(expected_worlds) * len(ARMS)
    with localcontext() as context:
        context.prec = 50
        family_error = Decimal(1280) * (-Decimal(8192) / Decimal(625)).exp()
        assert family_error < Decimal("0.05")
    return {
        "freeze_commit": FREEZE,
        "frozen_artifact_hashes_checked": len(manifest["files"]),
        "prospective_forecast_rows_independently_rebuilt": len(seen),
        "public_candidate_rows": len(expected_worlds),
        "simultaneous_hoeffding_upper_at_main_radius": str(family_error),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    path = parser.parse_args().output
    report = json.dumps(verify(), indent=2, sort_keys=True) + "\n"
    if path is None:
        print(report, end="")
    else:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(report)


if __name__ == "__main__":
    main()
