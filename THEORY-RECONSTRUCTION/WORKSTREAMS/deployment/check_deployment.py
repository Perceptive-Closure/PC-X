"""Finite candidate falsification and read-only recounted experiment ledgers."""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from fractions import Fraction as F
from hashlib import sha256
from itertools import product
from math import isclose, log
import gzip
import json
from pathlib import Path


def chance(p, bit):
    return p if bit else 1 - p


def actual_primitives(row):
    p_first, given_zero, given_one = row
    pairs = product((0, 1), repeat=2)
    return {(u, v): chance(p_first, u) * chance((given_zero, given_one)[u], v)
            for u, v in pairs}


def common_factors(left, right):
    for u, v in product((0, 1), repeat=2):
        first = min(chance(left[0], u), chance(right[0], u))
        second = min(chance(left[1 + u], v), chance(right[1 + u], v))
        yield (u, v), first * second


def canonical_law(primitives):
    frontier = {((0, 0, 0),): F(1)}
    for _ in range(2):
        following = defaultdict(F)
        for history, mass in frontier.items():
            state, last_public_bit, _ = history[-1]
            action = last_public_bit
            for (u, v), weight in primitives.items():
                if weight:
                    next_letter = (state ^ u, u, state ^ action ^ v)
                    following[history + (next_letter,)] += mass * weight
        frontier = dict(following)
    return frontier


def risk_parts(law):
    values = [F(0), F(0)]
    for path, mass in law.items():
        violates = any(letter[2] for letter in path[1:])
        values[violates] += mass
    return values


def check_transport():
    grid = (F(1, 4), F(1, 2), F(3, 4))
    rows = list(product(grid, repeat=3))
    physical = {row: canonical_law(actual_primitives(row)) for row in rows}
    count = 0
    for left, right in product(rows, repeat=2):
        sublaw = canonical_law(dict(common_factors(left, right)))
        for row in (left, right):
            assert all(mass <= physical[row][path] for path, mass in sublaw.items())
        safe, harmful = risk_parts(sublaw)
        risks = [risk_parts(physical[row])[1] for row in (left, right)]
        assert all(harmful <= risk <= 1 - safe for risk in risks)
        assert abs(risks[0] - risks[1]) <= 1 - safe - harmful
        if left == right:
            assert sublaw == physical[left]
        count += 1
    # The routine row is certain and anchored. The busy row has zero shared mass.
    common = {((0, 0, 0), (0, 0, 0)): F(9, 10)}
    safe, harmful = risk_parts(common)
    assert (harmful, 1-safe) == (0, F(1, 10))
    return count


def audit_law(means, horizon=3):
    """A controlled tree, with adaptive queries and early stopping."""
    def visit(history, mass):
        if len(history) == horizon or (len(history) == 2 and history[-1][1] == 0):
            yield history, mass
            return
        query = history[-1][1] if history else 0
        for bit in (0, 1):
            yield from visit(history + ((query, bit),), mass * chance(means[query], bit))
    return dict(visit((), F(1)))


def interval_gap(left, right):
    return max(F(0), left[0] - right[1], right[0] - left[1])


def distance(value, interval):
    return max(F(0), interval[0] - value, value - interval[1])


def check_intervals():
    grid = (F(0), F(1, 2), F(1))
    intervals = [(low, high) for low, high in product(grid, repeat=2) if low <= high]
    pairs = product(product(intervals, repeat=2), repeat=2)
    overlaps = 0
    separations = 0
    for left, right in pairs:
        gaps = [interval_gap(a, b) for a, b in zip(left, right, strict=True)]
        if not any(gaps):
            means = [max(a[0], b[0]) for a, b in zip(left, right, strict=True)]
            assert all(a[0] <= m <= a[1] and b[0] <= m <= b[1]
                       for a, b, m in zip(left, right, means, strict=True))
            p = audit_law(means)
            q = audit_law(means)
            assert p == q and sum(p.values()) == 1
            overlaps += 1
        else:
            for q, gap in enumerate(gaps):
                if gap:
                    radius = gap / 3
                    for k in range(17):
                        sample_mean = F(k, 16)
                        assert not (distance(sample_mean, left[q]) <= radius
                                    and distance(sample_mean, right[q]) <= radius)
            separations += 1
    return overlaps, separations


def check_stopping_kl():
    p = (F(1, 2), F(3, 8), F(1, 8))
    q = (F(1, 2), F(1, 8), F(3, 8))
    stopped_kl = sum(float(a) * log(a / b) for a, b in zip(p, q, strict=True))
    row_kl = float(F(3, 4)) * log(3) + float(F(1, 4)) * log(F(1, 3))
    assert stopped_kl > 0 and isclose(stopped_kl, 0.5 * row_kl)
    # p,q can also be laws of a distinguishing initialization then immediate stop.
    # In that interpretation all acquisition counts are zero but the initial term is not.
    return stopped_kl


def artifact(root, ident, filename):
    return root / ident / "EXPERIMENTS" / f"EXP-{ident}" / filename


def data(root, ident, filename):
    return json.loads(artifact(root, ident, filename).read_text(encoding="utf-8"))


def raw_rows(root, ident, filename, summary):
    digest = sha256()
    with gzip.open(artifact(root, ident, filename), "rb") as source:
        for line in source:
            digest.update(line)
            yield json.loads(line)
    summary[ident, filename] = digest.hexdigest()


def check_x08(root):
    opening = data(root, "X08", "results/opening.json")
    measurement = opening["measurements"]
    floor = [r for r in measurement["measurement"] if r["site"] == "floor"]
    assert len(floor) == 4 and all(r["trials"] == 1024 for r in floor)
    assert all(r["forecast_band_intersects"] for r in floor)
    assert [r["violations"] for r in floor] == [579, 651, 101, 128]
    assert measurement["benchmark_false_certifications"] == 1
    assert opening["forecast_remote_verified_at_utc"] == opening["measurements_finished_at_utc"]


def check_x09(root, hashes):
    native = defaultdict(Counter)
    factorial = Counter()
    seen = set()
    for unit, cue, context, index, trace in raw_rows(root, "X09", "results/raw-native.jsonl.gz", hashes):
        cell = (unit, cue, context)
        assert (*cell, index) not in seen and len(trace) == 3
        seen.add((*cell, index))
        native[cell].update(trials=1, events=any(turn[3] for turn in trace))
    assert len(native) == 32 and all(row["trials"] == 4096 for row in native.values())
    for unit, _, mode, cue, surface, trim, *_ in raw_rows(
            root, "X09", "results/raw-factorial.jsonl.gz", hashes):
        factorial[unit, mode, cue, surface, trim] += 1
    assert len(factorial) == 128 and set(factorial.values()) == {512}
    for unit, expected in {"U04": (4085, 4086), "U07": (4092, 4091)}.items():
        assert tuple(native[unit, "gold", surface]["events"]
                     for surface in ("smooth", "ribbed")) == expected
    return len(seen), sum(factorial.values())


def check_x11(root, hashes):
    protocol = data(root, "X11", "configs/protocol.json")
    counts = Counter()
    seen = set()
    for row in raw_rows(root, "X11", "results/observations.jsonl.gz", hashes):
        context, index = row["context"], row["index"]
        assert (context, index) not in seen
        seen.add((context, index))
        original_tape = [frame[0] for frame in row["arms"]["original"]]
        for port, frames in row["arms"].items():
            assert [frame[0] for frame in frames] == original_tape
            queue = 0
            late = 0
            for _, (arrivals, completions), *_ in frames:
                assert 0 <= completions <= queue + arrivals
                queue += arrivals - completions
                late += queue > 0
            counts[context, port] += late >= protocol["label_backlogged_rounds"]
    assert len(seen) == 8192
    assert [counts[context, "probe_b"] for context in ("steady", "burst")] == [3119, 3221]
    opening = data(root, "X11", "results/opening.json")
    assert not any(key.endswith("_utc") for key in opening.keys())
    return len(seen), 4 * len(seen)


def check_x12(root, hashes):
    opened = data(root, "X12", "results/opening.json")
    summary = data(root, "X12", "results/summary.json")
    roster = opened["private"]["assignment"]
    counts = defaultdict(Counter)
    seen = set()
    for unit, context, index, _, _, initial, ledger in raw_rows(
            root, "X12", "results/observations.jsonl.gz", hashes):
        assert (unit, context, index) not in seen and len(ledger) == 3
        seen.add((unit, context, index))
        if roster[unit]["family"] == "sorter":
            violation = any(printed != received for printed, _, _, received in ledger)
        else:
            submitted = initial + sum(row[0] for row in ledger)
            finished = sum(row[3] for row in ledger)
            assert finished <= submitted
            violation = finished < submitted
        counts[unit, context].update(trials=1, events=violation)
    assert len(counts) == 24 and len(seen) == 98304
    for (unit, context), counts_row in counts.items():
        reported = summary["units"][unit]["observed"][context]
        assert counts_row == {"events": reported["events"], "trials": reported["n"]}
    return len(seen)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path, help="Read-only intake root with exact XNN packages")
    args = parser.parse_args()
    print(f"T18 exact factor-envelope pairs: {check_transport()}")
    overlapping, separated = check_intervals()
    print(f"T24 finite interval controls: {overlapping} overlaps, {separated} separated")
    print(f"T22 stopped KL check: {check_stopping_kl():.9f}")
    if args.intake:
        hashes = {}
        check_x08(args.intake)
        print("X08: four archived floor cells, one false certification, whole-second timing tie")
        native, factorial = check_x09(args.intake, hashes)
        print(f"X09: {native} native episodes and {factorial} factorial observations")
        blocks, episodes = check_x11(args.intake, hashes)
        print(f"X11: {blocks} blocks and {episodes} recorded arm episodes")
        print(f"X12: {check_x12(args.intake, hashes)} machine-ledger episodes")
        expected = {
            ("X09", "results/raw-factorial.jsonl.gz"):
                "bb4d7fb88f69468bdae1d7e8e87c697a595a0a5cc234cb9f802755b743d079c8",
            ("X09", "results/raw-native.jsonl.gz"):
                "344a8fd1d0040a860929a68426c50be1e90e605d0177f681d877574d96605030",
            ("X11", "results/observations.jsonl.gz"):
                "d8185fcdbbb84bbbe25d58038b738b7663e70859deb88017fca47cba963e1f88",
            ("X12", "results/observations.jsonl.gz"):
                "843abfef78aada53e86cd3df726668e05aba031e6d97429c2ca8ca585731366a",
        }
        assert hashes == expected
        print("Verified four decompressed archived ledger hashes.")


if __name__ == "__main__":
    main()
