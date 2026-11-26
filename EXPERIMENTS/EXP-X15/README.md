# EXP-X15 independent hostile reproduction

All fourteen terminal PC-X experiments reproduced from their exact GitHub revisions. The published suites passed 152 tests. Independent calculations agreed on the tested finite and sandbox outcomes. Six new falsification control groups and eight harness tests passed. The strongest new negative result concerns X05. At the largest matched condition the minimum target audit and the minimum full-identity audit both cost 677. The published 1,070 comparator buys every query.

[Audit and discrepancies](Path.md) · [T01–T30 evidence matrix](theorems.md) · [Frozen protocol](protocol.md) · [Full evidence inventory](results/manifest.sha256)

## Verify the terminal evidence

Run from the repository root using CPython 3.13.7.

```powershell
python -B EXPERIMENTS/EXP-X15/check.py --evidence
Push-Location EXPERIMENTS/EXP-X15
python -B -m unittest discover -s tests -v
Pop-Location
```

The evidence check verifies the complete enumerated package, fourteen pins, successful predecessor replay receipts, original custody records and new control outputs. It works offline with the Python standard library. The SHA-256 inventory covers every package file except itself. Published evidence, harness logs and independent calculations have separate content and checksums.

## Reproduce the audit

Use a clean Git checkout, authenticated GitHub CLI, Git for Windows, PowerShell 7, CPython 3.13.7 and its standard library. X07 also used cryptography 43.0.3 and Git for Windows OpenSSL 3.2.4 in its standard program location. X06 used the official Windows AMD64 OPA release. Verify both binary digests before running native replay. Use a checkout-owned PowerShell process.

```powershell
New-Item -ItemType Directory -Force -Path scratch/audit/tmp,scratch/audit/runtime | Out-Null
$env:TEMP = (Resolve-Path scratch/audit/tmp).Path
$env:TMP = $env:TEMP
gh release download v1.22.4 --repo open-policy-agent/opa --pattern opa_windows_amd64.exe --dir scratch/audit/runtime
python -B EXPERIMENTS/EXP-X15/fetch_inputs.py
python -B EXPERIMENTS/EXP-X15/replay.py --label clean-replay --jobs 4
python -B EXPERIMENTS/EXP-X15/check.py --reconstruct --label clean-replay
python -B EXPERIMENTS/EXP-X15/verify_custody.py --output clean-custody.json
```

The exact-SHA archive fetch authenticates all tracked blobs against the GitHub Git tree. X02 and X04 use the checkout's Git metadata with the authenticated archive roots as the working trees for their documented predecessor preparation. The published study measurements execute locally after acquisition. Each replay label names a new output directory. The X07 command operates on previously published inert local certificate fixtures. The inputs, preparation, commands, exit status, elapsed time and concise output are bound in the replay receipts. [Intake receipts](results/sources.json) · [Replay receipts](results/replays.json) · [Custody and binary verification](results/custody.json)

To collect fresh resource observations separately, run the X05 timing command with a new label. The reconstruction comparison covers stable independent results. Fresh timings and traced allocations are host observations. [Fresh raw observations](results/x05-fresh-measurements.csv) · [Fresh aggregates](results/x05-fresh-performance.json)

```powershell
python -B EXPERIMENTS/EXP-X15/replay.py --label fresh-resources --jobs 1 --measure-x05 X05
```

[Initial twelve pins](inputs.initial.json) · [Two staged pins](inputs.late.jsonl) · [Independent reconstructions](results/independent.json) · [Falsification controls](results/controls.json)
