# EXP-X04 — Adaptive semantic audits

This package compares exact minimax adaptive acquisition with static certificates and four acquisition baselines. It uses constructed finite inputs and the exact accepted X03 authorization fixtures. Start with [WorkPlan.md](WorkPlan.md), [Protocol.md](Protocol.md) and [Path.md](Path.md).

## Reproduce

The original run used CPython 3.13.7 and its standard library. From a clone of Perceptive-Closure/PC-X pinned to the recorded X04 head, fetch the exact X03 dependency, then run the commands below. The results runner itself works offline. It checks the X03 protocol and scopes byte hashes before importing the actual X03 fixtures into the checkout's ignored scratch directory.

```powershell
git fetch --no-tags origin d85fe1cdb76cbc6d03e58e34f320c4c58a3f243c
cd EXPERIMENTS/EXP-X04
python -B -m unittest discover -s tests -v
python -B run.py --check
```

The check regenerates the complete measured case tables, policy replays and summary byte-for-byte. The runtime and memory observations have a separate recorded hash, since host measurements vary. Use `python -B run.py --write` in a disposable checkout to record fresh observations and regenerate the manifest.

## Evidence

- `results/summary.json` gives exact per-case static, adaptive and realized costs and statuses, comparator measurements, coverage, inaccessibility witnesses and derived large-address bounds.
- `results/tables.jsonl` includes the full measured answer and target tables, permitted query names, costs and prior weights. One row represents one test case.
- `results/policy_replays.jsonl` records the observed query answer paths, cost and target verdict for every completion and every tested comparator policy, plus the optimized tree.
- `results/runtime_observed.json` records wall time and peak traced Python allocations for each measured exact optimizer call. These are observations on the original run host.
- `results/manifest.sha256` binds the freeze configuration and recorded evidence.

The routed workflows explicitly model admission, certificate equivalence and authority. The route query reports a factual source endpoint. Other queries report local admission, remap or license facts. The closure target is computed through permitted paths after the R freeze. Each site's configuration affects its own R-frozen cost under a legitimate intake route. Test cases establish finite exactness and bounded cost differences for declared synthetic instances.
