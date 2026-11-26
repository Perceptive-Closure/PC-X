# EXP-X13 — Multi-agent composition

Two executed offline dispatch policies schedule workshop jobs under four combinations of work-order presentation and bench arbitration. Independent physical scoring separates local work violations from bench collisions. [Work plan](WorkPlan.md) · [Frozen protocol](Protocol.md) · [Execution record](Path.md)

## Clean replay

Use Python 3.13.7 and its standard library from the experiment directory. These commands work in a GitHub source archive without Git metadata. On Windows, point TMP, TEMP and caches at an experiment-owned ignored scratch directory for the process.

```powershell
python -B -m unittest discover -s tests -v
python -B src/x13.py replay
```

Replay checks the evidence manifest, rebuilds the pre-audit, rechecks valid completions and query selection, verifies the forecast and nonce-backed opening, rescores the stored physical ledgers and independently reconstructs the sealed native run. Keep the uncompressed ledger digest for verification independently of local archive tools.

## Custody stages

The forecaster publishes the protocol and the immutable executable containing the pre-audit evidence before the parent seals the assignment. Use new paths for the stage outputs. Commands run from the experiment directory. All commit placeholders are full 40-character object IDs, and UTC timestamps use a Z suffix.

```powershell
python -B src/x13.py pre-audit --out PRE_AUDIT_JSON
python -B src/x13.py seal --protocol-commit PROTOCOL_SHA --source-commit PRE_AUDIT_SHA --sealed PARENT_SECRET --receipt AUDIT_RECEIPT
python -B src/x13.py forecast --receipt AUDIT_RECEIPT --out FORECAST
python -B src/x13.py open --sealed PARENT_SECRET --receipt AUDIT_RECEIPT --forecast VERIFIED_FORECAST --forecast-commit FORECAST_SHA --remote-tip VERIFIED_REMOTE_TIP --verified-at-utc UTC_STAMP --out-dir NEW_PARENT_DIR
python -B src/x13.py manifest --out results/manifest.json
```

The parent alone runs `seal` and `open` from the pinned GitHub archive. Keep the sealed file in the parent custodian's ignored scratch until the verified opening. Give the forecaster only the receipt. Before opening, verify the forecast commit and its exact receipt, ancestry and unchanged protected files externally. The CLI checks the chronology and local records against that externally verified receipt. The opening directory must be new and have an existing parent. Keep the parent-generated `opening.json`, `summary.json` and `episodes.jsonl.gz` exactly as emitted.

## Evidence

[Pre-audit](results/pre-audit.json) gives isolated equivalence, finite anchors, witness rows and query costs. [Receipt](results/audit-receipt.json) and [forecast](results/forecast.json) record the authorized calibration and exact predictions. [Opening](results/opening.json) and [summary](results/summary.json) record the assignment, stage provenance and measured results. Each row of [the raw ledger](results/episodes.jsonl.gz) gives a named port, context, ticket and both isolated work traces alongside the joint trace. [The manifest](results/manifest.json) binds the source and evidence by SHA-256.
