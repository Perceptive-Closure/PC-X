# EXP-X11 intervention fidelity

A three-tick print-queue sandbox separates the logger's visible tape from actual service. The [protocol](Protocol.md) fixes the intervention and matched statistical design. The [execution record](Path.md) tracks custody, results and publication. The executable uses the Python 3.13 standard library.

## Reproduce

Run from this experiment directory, using a fresh output path for each replay. These commands also work from a source archive without Git metadata.

```sh
python -B -m unittest discover -s tests -v
mkdir -p scratch
python -B src/x11.py replay --out-dir scratch/replay
```

On PowerShell use `New-Item -ItemType Directory -Force scratch | Out-Null` for the directory. Replay checks every declared package file hash, recalculates the pre-audit, scores the stored observations independently, confirms the sealed assignment and prediction, then regenerates and matches the opening and uncompressed raw hash.

## Evidence and stage commands

- [Pre-audit](results/pre-audit.json) contains compatible completions, exhaustive scoring, the mismatch witness, independent pulse controls and query selection.
- The [audit receipt](results/audit-receipt.json) records the parent custodian's chosen query, raw isolated readback and assignment commitment. The [forecast](results/forecast.json) records risk and fidelity predictions and the no-anchor and no-enrollment ablations.
- The [opening](results/opening.json) contains the assignment, seed and nonce. Each line of the [compressed observation archive](results/observations.jsonl.gz) contains a context, paired block index, three request/ticket tuples, and the four traces. A trace row has public request/display/route/acknowledgement, machine arrivals/completions, tick/last-request/backlog state, and a logger copy or placebo lamp event when applicable. The independent event label uses only arrivals and completions.

The forecaster uses `python -B src/x11.py pre-audit --out results/pre-audit.json` to build pre-audit evidence prior to custody. After the custodian verifies the frozen source from GitHub, use the following commands from their immutable source archive. Substitute full paths for the parent-owned scratch files and full commits for the named parameters. The opening directory must be new and its parent must already exist.

```sh
python -B src/x11.py seal --protocol-commit PROTOCOL_SHA --source-commit PRE_AUDIT_SHA --sealed PARENT_SECRET --receipt AUDIT_RECEIPT
python -B src/x11.py forecast --receipt AUDIT_RECEIPT --out FORECAST
python -B src/x11.py open --sealed PARENT_SECRET --receipt AUDIT_RECEIPT --forecast VERIFIED_FORECAST --forecast-commit VERIFIED_FORECAST_SHA --out-dir PARENT_OPEN
```

Only the custodian runs `seal` and `open`. Share the receipt after sealing. Publish the forecast from the forecaster's checkout. For opening, the parent retrieves the committed forecast and verifies its provenance through GitHub before the held-out run, using the same frozen pre-audit archive. The sealing and opening scripts check the runner and record digests locally. The execution record supplies the independent remote chronology.
