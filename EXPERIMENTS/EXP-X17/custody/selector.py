"""Deterministic X17 roster generation after independent beacon verification."""

import argparse
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import re


SELECTOR = "PCX-X17-draw-v1"


def choose(entropy, label, choices):
    count = len(choices)
    if not count:
        raise ValueError("empty stratum")
    space = 1 << 256
    cutoff = space - space % count
    nonce = 0
    while True:
        material = f"{SELECTOR}\n{entropy}\n{label}\n{nonce}\n".encode("ascii")
        value = int.from_bytes(sha256(material).digest(), "big")
        if value < cutoff:
            return choices[value % count]
        nonce += 1


def select_worlds(domain, entropy):
    if domain["selector"] != SELECTOR or not re.fullmatch(r"[0-9a-f]{64}", entropy):
        raise ValueError("unrecognized roster version or entropy")
    routes = ("L", "R")
    mode = choose(entropy, "matched/m", (0, 1))
    route = choose(entropy, "matched/k", routes)
    beta = choose(entropy, "matched/beta", domain["beta_endpoints"])
    other_beta = next(value for value in domain["beta_endpoints"] if value != beta)
    other_route = next(value for value in routes if value != route)
    depth = choose(entropy, "matched/N", domain["matched_depths"])
    extreme_depth = choose(entropy, "extreme/N", domain["extreme_depths"])

    def row(index, theta, beta, m, k, depth):
        return {"id": f"s{index:02}", "theta": str(F(theta)), "beta": str(F(beta)),
                "m": m, "k": k, "B": "good", "N": depth}

    worlds = [
        row(1, "1/4", beta, mode, route, depth),
        row(2, "3/4", beta, mode, route, depth),
        row(3, "1/8", other_beta, 1 - mode, other_route, extreme_depth),
        row(4, "7/8", other_beta, 1 - mode, other_route, extreme_depth),
    ]
    for index, grid in enumerate(domain["interior_theta_numerators"], start=5):
        key = f"s{index:02}"
        theta = F(choose(entropy, key + "/theta", grid), domain["theta_denominator"])
        b = choose(entropy, key + "/beta", domain["interior_beta"])
        m = choose(entropy, key + "/m", (0, 1))
        k = choose(entropy, key + "/k", routes)
        n = choose(entropy, key + "/N", domain["interior_depths"])
        worlds.append(row(index, theta, b, m, k, n))
    if len(worlds) != 8 or len({world["theta"] for world in worlds}) != 8:
        raise ValueError("domain does not generate the registered roster")
    return worlds


def canonical(document):
    return (json.dumps(document, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("domain", type=Path)
    parser.add_argument("draw", type=Path)
    parser.add_argument("beacon", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    domain_bytes = args.domain.read_bytes()
    beacon_bytes = args.beacon.read_bytes()
    draw_bytes = args.draw.read_bytes()
    domain = json.loads(domain_bytes)
    beacon = json.loads(beacon_bytes)["beacon"]
    draw = json.loads(draw_bytes)
    if draw["round"] != beacon["round"] or draw["domain_sha256"] != sha256(domain_bytes).hexdigest():
        raise ValueError("roster domain or beacon differs from the draw plan")
    with args.output.open("xb") as stream:
        stream.write(canonical({
            "schema": 1,
            "selector": SELECTOR,
            "round": beacon["round"],
            "domain_sha256": sha256(domain_bytes).hexdigest(),
            "draw_sha256": sha256(draw_bytes).hexdigest(),
            "beacon_sha256": sha256(beacon_bytes).hexdigest(),
            "worlds": select_worlds(domain, beacon["randomness"]),
        }))


if __name__ == "__main__":
    main()
