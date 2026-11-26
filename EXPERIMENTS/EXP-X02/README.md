# EXP-X02 · Nonrectangular semantic ambiguity

EXP-X02 computes exact finite identified sets under Boolean correlation constraints. It compares them with the rectangular action-touch product authorized by each case's fixed source skeleton. Read the [work plan](WorkPlan.md), [frozen protocol](protocol.json) and [execution record](Path.md) for scope and claim limits.

## Reproduce

Use CPython 3.13.7, Git, PowerShell and authenticated access to the existing private [Perceptive-Closure/PC-X repository](https://github.com/Perceptive-Closure/PC-X). The software uses the Python standard library. A clean checkout can be obtained with the project GitHub HTTPS URL and the dedicated `codex/exp-x02` branch. Pin the accepted X02 commit supplied by the master execution record. From the repository root, run:

```powershell
& './EXPERIMENTS/EXP-X02/prepare-x01.ps1'
$env:TEMP = (Resolve-Path -LiteralPath 'scratch/tmp').Path
$env:TMP = $env:TEMP
Push-Location 'EXPERIMENTS/EXP-X02'
python -B -m unittest discover -s tests -v
Pop-Location
python -B EXPERIMENTS/EXP-X02/run.py --check --details scratch/x02-details.json
```

The preparation script fetches [X01 at a52d45f1b8c0036b1a69b1fc024f95e48d4ce012](https://github.com/Perceptive-Closure/PC-X/tree/a52d45f1b8c0036b1a69b1fc024f95e48d4ce012/EXPERIMENTS/EXP-X01), confirms it is part of the authenticated predecessor branch, and extracts its source to ignored scratch space. The imported model is verified against its recorded byte digest on every process start. Running PowerShell in a per-experiment command process keeps the temporary-directory settings local. The check regenerates the canonical summary and manifest, including the hash of all completion assignments, signatures, touch options, joint sets, bounds, independently verified witnesses, and refinements. Infinity is recorded as `"inf"`. Empty evidence has no signature or extrema.

## Model and comparator

Boolean variables represent conditional decisions about evidence admission, certificate equivalence, or a declared reserve authority. A positive literal selects its feature. A negative literal selects the feature's complement. Declared candidate IDs, costs, observations, terminal classes and all positive-support outcomes remain fixed across a case. A complete source action touches a resource when at least one positive-support successor changes its extensional coordinate. The E/R/A touch rule and full freeze solver use the byte-verified X01 engine.

The two evidence searches are prefix-pruning and an exhaustive Cartesian truth table. Each assignment's results are checked by backward worst-support dynamic programming, X01's finite solver and a separate exhaustive policy-tree catalog. The catalog tracks whole policy supports and evaluates exact removals by disjointness. The rectangular product takes independent choices among the observed touch sets at each common action location. Definite and possible removal endpoints are checked against the catalog. The joint product of exact marginal outcome sets is also counted. Its unattainable combinations expose loss of cross-freeze dependence.

The code is deliberately limited to the fully observable forward finite fragment specified in the protocol. The results supply exact finite checks of the charter's correlation and source-boundary problems. They leave general nonrectangular tractability and native-system prevalence open.
