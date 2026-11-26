# EXP-X03 — Global and local certificate optimality

EXP-X03 compares finite weighted semantic audit certificates with independently enumerated answer partitions. It evaluates constructed authorization contracts and controlled finite tables. [Work plan](WorkPlan.md) · [Execution record and findings](Path.md) · [Frozen protocol](configs/protocol.json)

## Reproduce

Use Python 3.13.7. The experiment uses the standard library and runs offline after the repository is checked out. GitHub repository access is required for a remote checkout.

```sh
git clone --single-branch --branch codex/exp-x03 https://github.com/Perceptive-Closure/PC-X.git pc-x03
cd pc-x03/EXPERIMENTS/EXP-X03
python -B -m unittest discover -s tests -v
python -B run.py --check
```

The check reruns the frozen corpus and compares the complete per-scope CSV and summary JSON with the committed files. It also prints their SHA-256 digests. Use `python -B run.py --write --output-dir <owned-directory>` to regenerate evidence in a disposable directory. [Evidence hashes](results/manifest.sha256)

## Evidence

- [Scope-level measurements](results/scopes.csv) include certification status, selected queries, cost, optimum tie counts, impossibility witnesses, full-contract comparisons, partition counts, and all comparator costs. Costs are exact integers or rational means of the 16 fixed random permutations.
- [Aggregate results](results/summary.json) report scope diagnostics by stratum, candidate validity, control outcomes, and comparator performance. Blank CSV costs represent cases with no finite solution.
- [Certificate engine](src/certificates.py) supplies the `Completion`, `Problem`, and `solve` interfaces. Query order indexes the corresponding positive integer costs. The optional `realized` argument is a completion identity. With it, sufficiency is checked only in that completion's observed answer cell.
- [Direct partition oracle](src/reference.py) enumerates all query subsets. With more queries, this full verification cost grows exponentially. [Authorization fixtures](src/authorization.py) derive eight freeze outcomes from explicit histories, representation partitions and authority. X04 can use these tables and uniform and realized costs as deterministic reference fixtures. X05 can use the paired disagreement checks and partition optimum as small-case references.
