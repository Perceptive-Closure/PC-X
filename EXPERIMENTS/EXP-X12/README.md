# EXP-X12 deployment generalization

Two benign three-tick systems test transport from frozen source calibration to a blinded deployment roster. The reactive sorter and stateful print queue have independently scored machine ledgers. The [work plan](WorkPlan.md), [frozen protocol](Protocol.md), and [execution record](Path.md) describe the scope, assumptions and evidence.

## Run public checks

Run from the EXP-X12 directory of a clean checkout or a GitHub source archive. Use CPython 3.13.7 and its standard library. Set $scratch to an existing ignored experiment-owned directory, point TMP, TEMP and caches inside it, and use fresh output paths.

~~~powershell
python -B -m unittest discover -s tests -v
python -B src/x12.py preflight --exact "$scratch/preflight.json" --calibration "$scratch/calibration.json"
Get-FileHash "$scratch/preflight.json", "results/preflight.json", "$scratch/calibration.json", "results/calibration.json"
~~~

The preflight checks exact equivalence and target-distinct witness pairs, independent labels, finite coupling implications and minimum sufficient structural batch costs. Calibration reproduces the two frozen reference banks without sampling held-out deployments.

## Original prospective run

The original custody steps use the parent custodian's independently retrieved GitHub archive at the exact immutable pre-outcome SHA. The custodian alone executes reserve and release. Use replay for an already opened roster.

1. In the pinned archive, verify pristine source and the public checks. Set $sourceSHA to the full pre-outcome SHA and reserve into distinct new paths.

   ~~~powershell
   python -B src/x12.py reserve --source-commit $sourceSHA --private "$scratch/private.json" --receipt "$scratch/audit-receipt.json"
   ~~~

   The private record stays with the custodian. Send the commitment and receipt only.

2. In the forecaster's worktree, retain the exact receipt and generate the forecast.

   ~~~powershell
   python -B src/x12.py forecast --receipt results/audit-receipt.json --out results/forecast.json
   ~~~

   Publish the receipt and forecast on the experiment branch descended from the source SHA.

3. Check the exact current GitHub tip, ancestry, immutable source hashes and receipt bytes in a fresh GitHub archive at the published forecast SHA. Point $forecastFile to the verified archive file and record $verifiedAt in ISO 8601 UTC ending in Z. Return to the original pre-outcome archive to open the commitment and run the independent holdout.

   ~~~powershell
   python -B src/x12.py release --private "$scratch/private.json" --receipt "$scratch/audit-receipt.json" --forecast $forecastFile --forecast-commit $forecastSHA --remote-tip $verifiedTip --verified-at-utc $verifiedAt --out-dir "$scratch/opened"
   ~~~

   The runner checks the provided remote verification facts but uses no Git metadata or network. The parent maintains the actual chronology. It writes a new opening, raw ledger, summary and manifest. Neither reserve nor forecast invokes the native holdout generator.

## Verify opened evidence

Run the public checks above, then reproduce from an independently downloaded terminal GitHub source archive. Use a new output directory with an existing parent.

~~~powershell
python -B src/x12.py replay --out-dir "$scratch/replay"
~~~

Replay checks the manifest, commitment and forecast bytes, reproduces source calibration and audit, independently scores the retained raw ledger and then regenerates the holdout archive. The manifest binds both compressed and uncompressed bytes. A successful replay verifies an already disclosed run. Independent custody establishes the original sequence. The two roles use separate source directories on a shared filesystem.
