# EXP-X09 — Evaluation-aware AI systems

The experiment runs finite stochastic virtual card-sorting policies. A legitimate color cue, surface request and state reset expose audit laws. An independent virtual station measures three-turn recheck risk. See the [work plan](WorkPlan.md), [frozen protocol](Protocol.md), and [execution record](Path.md).

## Run the exact and public development checks

Use CPython 3.13.7 and its standard library. Run from this experiment directory in a pinned checkout or extracted GitHub archive. Use fresh output paths under the managed experiment's ignored scratch directory. Set TEMP, TMP and cache paths within that scratch directory, and use `-B` to prevent Python bytecode writes.

```powershell
python -B -m unittest discover -s tests -v
python -B src/x09.py exact --output "$scratch/exact.json"
python -B src/x09.py develop --output "$scratch/development.json"
```

Compare exact and development outputs with the committed files under `results/`. The exact run enumerates runtime ticket choices on every reachable history, checks station risks by a separate path enumeration, and checks exact minimax, binomial costs and the T22 allocation bound. The development run executes public reset batches with no measurement of the sealed roster.

## Original custody sequence

The instructions below describe the original prospective run. Reserve and release are single-use steps for that run. Use replay for subsequent verification.

1. The custodian retrieves the private repository's GitHub archive at the exact executable pre-audit SHA specified in the ledger. The custodian independently checks the exact output and then runs the following command from the archive's `EXPERIMENTS/EXP-X09` directory.

   ```powershell
   python -B src/x09.py reserve --source-commit $sourceSHA --private "$scratch/private.json" --receipt "$scratch/audit-receipt.json"
   ```

   Only the commitment and selected-measurement receipt go to the forecaster. The custodian holds the private record and uses fresh output paths.

2. The forecaster derives a prediction from the receipt and pushes both files to `codex/exp-x09`.

   ```powershell
   python -B src/x09.py predict --receipt "$scratch/audit-receipt.json" --output results/forecast.json
   ```

3. The custodian retrieves a new GitHub archive at the exact forecast commit. The custodian checks the remote branch, unchanged executable/configuration bytes, and exact uploaded receipt. After this verification, record a UTC timestamp, point `$forecastFile` at the GitHub-retrieved `results/forecast.json`, and run the release command in the original pre-audit archive.

   ```powershell
   python -B src/x09.py release --private "$scratch/private.json" --receipt "$scratch/audit-receipt.json" --forecast $forecastFile --forecast-commit $forecastSHA --github-verified-utc $verifiedUtc --output "$scratch/opened"
   ```

   The archived runner uses no Git metadata or network. The custodian supplies GitHub verification and its timestamp. Release verifies the byte-bound forecast and selected audit before running any native cells. It writes the opening, raw traces, summary and manifest to the new output directory.

## Offline reproduction

From an independently retrieved terminal snapshot of this experiment, run the tests above and then run:

```powershell
python -B src/x09.py replay --output "$scratch/replay"
```

The replay checks the disclosed assignment and seed against the commitment, regenerates the exact model and development outputs, recalculates the sealed forecast and reconstructs all measured traces. The manifest binds both analysis files, the audit receipt, forecast, opening, outcome summary, raw audit batches and compressed native and factorial ledgers. Raw row schemas appear in the summary. In native records each turn contains the policy ticket, right-tray bit, station ticket and recheck bit. In factorial records prefix fields are null in the reset cells. The replay concerns deterministic regeneration of an already opened seed. Prospective custody remains a separate occurrence with separate roles on a shared filesystem.
