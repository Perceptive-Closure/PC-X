# EXP-X14 — Governed alignment realizability

The experiment routes two workshop orders under finite uncertainty about bench compatibility, panel observations, and authorization. A winning policy must complete both orders safely on every supported observation branch. [Work plan](WorkPlan.md) · [Frozen protocol](Protocol.md) · [Execution record](Path.md)

## Reproduce the study

Use Python 3.13.7 and its standard library from this experiment directory. The commands also run in a GitHub source archive. On Windows, use process-local scratch for temporary files and the Python cache.

```powershell
New-Item -ItemType Directory -Force -Path scratch/tmp,scratch/cache | Out-Null
$env:TEMP = (Resolve-Path scratch/tmp).Path
$env:TMP = $env:TEMP
$env:PYTHONPYCACHEPREFIX = (Resolve-Path scratch/cache).Path
python -B -m unittest discover -s tests -v
python -B run.py prepare --out-dir scratch/reproduced
```

Compare `scratch/reproduced/exact.json` and `scratch/reproduced/pre-audit.json` with their registered counterparts in [results](results). Host timings and traced allocation peaks are observations from the registered run and can vary.

On the terminal package, `python -B run.py replay` checks the manifest, regenerates the exact bounded verdicts and external audit, verifies custody and policy digests, and reproduces every native event and score. It needs the published receipt, forecast, opening and ledger. Work runtime caches remain under ignored scratch.

## Custody

Use the registered source archive by exact GitHub SHA. Substitute new file paths, full object IDs and a UTC timestamp ending in `Z`.

```powershell
python -B run.py seal --protocol-commit PROTOCOL_SHA --source-commit SOURCE_SHA --sealed PRIVATE_JSON --receipt RECEIPT_JSON
python -B run.py forecast --receipt RECEIPT_JSON --out FORECAST_JSON
python -B run.py open --sealed PRIVATE_JSON --receipt RECEIPT_JSON --forecast VERIFIED_FORECAST_JSON --forecast-commit FORECAST_SHA --remote-tip VERIFIED_TIP_SHA --verified-at-utc UTC_STAMP --out-dir NEW_OPENING_DIR
python -B run.py manifest --out results/manifest.json
```

The custodian runs `seal` from the frozen source archive and releases the receipt. The experiment agent generates and publishes the forecast from the receipt. The custodian verifies the remote forecast commit, receipt bytes, source ancestry and unchanged protected bytes before running `open` in the frozen archive. The opening directory must be new. Preserve the emitted opening, raw ledger and summary byte for byte.

## Bounded evidence

The [exact results](results/exact.json) retain each scenario, policy, concrete path check, upper cost, lower-cost or infeasibility proof, omniscient and single-contract costs, and exhaustive acquisition and refusal baselines. The [pre-audit](results/pre-audit.json) retains target-distinct compatible installations, external readback validation, the frozen adaptive acquisition tree, the exact cheaper-budget check and unavailable-interface witnesses.

The common-action control finishes both orders with zero audit cost across eight starting states. In the quantifier-gap control, each contract can finish at cost zero when it is known, but the only universally safe first actions buffer or refuse. A lawful layout read restores a common policy at cost two with three ticks. With two ticks, that same read leaves insufficient time. A masked panel requires cost-three codec refinement even when the contract is known. The relief control requires a cost-four lawful grant. The heterogeneous control requires a cost-six worst branch because the evidence directs different later interventions.

The external acquisition effort and in-task acquisition effort are reported in separate design units. The support is finite and exhausted. The result provides a bounded synthesis and validation example for T28–T29. T30 and general deployment control remain open.
