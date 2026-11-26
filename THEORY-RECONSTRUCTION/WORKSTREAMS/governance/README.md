# Governance proof candidates

The statement-only seal is `3e87a71df84617399f92c73380cdb8ea0605f93a`. This workstream constructs T25–T29. Exact historical experiments remain in their pinned packages.

- [T25 monitorability](../../THEOREMS/T25/DOSSIER.md)
- [T26 intervention fidelity](../../THEOREMS/T26/DOSSIER.md)
- [T27 composition](../../THEOREMS/T27/DOSSIER.md)
- [T28 immediate action](../../THEOREMS/T28/DOSSIER.md)
- [T29 governed synthesis and acquisition](../../THEOREMS/T29/DOSSIER.md)
- [Source reconstruction](EVIDENCE.md) and [primary literature](LITERATURE.md)

Run the new finite checks from the repository root without fetching any historical data.

```powershell
python -B THEORY-RECONSTRUCTION/WORKSTREAMS/governance/check_candidates.py
lean +leanprover/lean4:v4.21.0 THEORY-RECONSTRUCTION/WORKSTREAMS/governance/readback_cover.lean
```

Python uses only the standard library. Lean imports only Std and checks the equivalence between ready attainable cells and coverage of an exhaustive family of known nonempty obstructions, including heterogeneous query-answer types. The human proof derives the required obstruction family by finite deletion. Neither this mechanization nor the synthetic grids is a blind independent verification of the entire package.
