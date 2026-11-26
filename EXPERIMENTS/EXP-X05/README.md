# EXP-X05 · Symbolic scalability

This experiment checks whether the structure of a finite authorization contract permits exact target identification and minimum-cost semantic audits without a full completion table. It compares a paired symbolic method with direct weighted answer partitions, eager disagreement generation, and a dominance-pruning ablation. [Work plan](WorkPlan.md) · [Frozen protocol](Protocol.md) · [Execution record](Path.md)

## Reproduce

Use CPython 3.13.7 and its standard library. Check out the exact experiment revision from the private [PC-X repository](https://github.com/Perceptive-Closure/PC-X). Run from the repository root in PowerShell.

```powershell
New-Item -ItemType Directory -Force -Path 'scratch/x05/tmp' | Out-Null
$env:TMP = (Resolve-Path -LiteralPath 'scratch/x05/tmp').Path
$env:TEMP = $env:TMP
$env:PYTHONHASHSEED = '0'
Push-Location 'EXPERIMENTS/EXP-X05'
python -B -m unittest discover -s tests -v
Pop-Location
python -B EXPERIMENTS/EXP-X05/run.py --check --out scratch/x05/replay
```

Run `python -B EXPERIMENTS/EXP-X05/run.py --check --measure --out scratch/x05/timed-replay` to collect fresh wall times and peak Python allocations. The runner verifies the deterministic byte-for-byte checks and the checksums of the archived resource observations. Fresh raw measurements depend on the replay host and load.

## Check the proof

The main engine derives complete atomic effects from every source edge and solves the coupled budget test with a Pareto frontier of attainable cost pairs. Positive or negative classification of that test always presupposes nonempty evidence. Each refinement adds a verified query-disagreement edge from a single-stage threshold-crossing pair. A conclusive absence of disagreement plus an independently checked lower bound gives minimum uniform acquisition cost. A uniform certificate specifies which valid queries to obtain. The target may still depend on their answers.

The reference reconstructs all local source policies, complete support footprints, semantic query answers and attainable outside costs. It checks every reported witness and proves global sufficiency and cost by examining all locally reachable threshold crossings. [Independent verifier](reference.py) · [Symbolic engine](engine.py) · [Explicit baselines](baselines.py)

The design uses synthetic, fully observable serial contracts with within-stage correlations and fixed source boundaries. It does not estimate native performance or settle unrestricted tractability.

## Evidence

- [Summary](results/summary.json) records the acceptance counts and refusal reasons.
- [Invariants](results/invariants.json) retain the per-case input digest, exact cost projection, every proof round with assignment witnesses and acquisition comparator costs. A null witness cost denotes structural infinity.
- [Raw resource runs](results/measurements.csv) and [per-case aggregates](results/performance.json) retain the original performance observations.
- [Manifest](results/manifest.json) pins the two pre-outcome GitHub revisions and every evidence digest.
