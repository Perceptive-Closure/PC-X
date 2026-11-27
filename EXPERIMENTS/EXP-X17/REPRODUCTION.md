# Reproduce the published EXP-X17 evidence

Use the campaign's exact accepted GitHub commit and run from its repository root. Python 3.13.7, Node 22.15.0, Lean 4.21.0 and the declared drand-client lock were used. The controller and native sampling use the Python standard library. The separate explicit solver uses the documented Z3 binding.

## Governing bytes, registered proof and statistics

~~~powershell
$p='EXPERIMENTS/EXP-X17'
python -B "$p/freeze_study.py" verify
python -B "$p/verify_predictions.py"
python -B "$p/tests/native_controls.py"
python -B "$p/tests/controller_exact.py"
python -B "$p/tests/independent_controls.py"
lean "$p/formal-checks/controller_price.lean"
python -B "$p/verify_evidence.py"
~~~

The last verifier streams both published compact raw indexes, reconstitutes the exact registered endpoint counts and confidence analysis, checks commitment hashes and verifies actual representative durable artifact bytes. The index records point to complete deterministic precommitment and seed-driven evidence. Captured SQLite files need not be bitwise portable across library versions. Canonical rows and artifact digests are the replay contract. Rehearsal data never enter the main results.

## Verify the external selector

~~~powershell
$p='EXPERIMENTS/EXP-X17'
$deps='scratch/x17-drand-replay'
New-Item -ItemType Directory -Force -Path $deps | Out-Null
Copy-Item -LiteralPath "$p/custody/package.json","$p/custody/package-lock.json" -Destination $deps
npm --prefix $deps ci --ignore-scripts --no-fund --no-audit
node "$p/custody/beacon.mjs" verify $deps "$p/custody/draw-plan.json" "$p/custody/pre-opening-pending.json" "$p/custody/verified-beacon.json"
python -B "$p/custody/selector.py" "$p/custody/roster-domain.json" "$p/custody/draw-plan.json" "$p/custody/verified-beacon.json" 'scratch/x17-roster-replay.json'
~~~

Compare the replayed roster bytes to the published roster. Exact before-round GitHub Date and activity witnesses are stored alongside the draw. The full source input manifest and candidate forecast announce laws before the chosen randomness is available. The server timestamps are platform receipts rather than proof of an isolated secret host. [Custody instructions](custody/README.md) · [Quicknet developer documentation](https://docs.drand.love/developer/) · [GitHub repository activity API](https://docs.github.com/en/rest/repos/repos#list-repository-activities)

## Rerun actual evidence

From the same exact checkout, use distinct new output directories. They are created by the callers so they must not already exist. The primary reads its published synthetic seed opening from the gate-bound custody directory. The independent command reads the separate binary seed file recreated from its published opening. Match each gzip index hash and deterministic records to the corresponding registered role. Fresh primary and independent results differ because their randomness is intentionally separate.

~~~powershell
$p='EXPERIMENTS/EXP-X17'
python -B "$p/run_primary.py" 'scratch/x17-replay-primary' --release "$p/custody"
python -B "$p/run_controls.py" 'scratch/x17-replay-controls'
python -B "$p/independent/reference.py" "$p/custody/opening-roster.json" full --exposure-floor 0
$seed='scratch/x17-independent-seed-replay.bin'
python -B -c "import json,sys; from pathlib import Path; p=Path(sys.argv[1]); s=bytes.fromhex(json.loads(p.read_bytes())['seed_hex']); Path(sys.argv[2]).write_bytes(s)" "$p/custody/independent-seed-reveal.json" $seed
python -B "$p/independent/run.py" --authorization "$p/custody/run-authorization.json" --draw "$p/custody/draw-plan.json" --beacon "$p/custody/verified-beacon.json" --opening "$p/custody/opening-roster.json" --independent-seed $seed --seed-commitment "$p/custody/independent-seed-commitment.json" --output 'scratch/x17-replay-independent'
python -B "$p/summarize_operations.py" 'scratch/x17-operations-replay.json'
~~~

Compare the primary `rows.jsonl.gz` and the independent `independent-index.ndjson.gz` with the hashes in their [primary report](results/primary/report.json) and [independent report](results/independent/independent-summary.json). Confirm `x17-operations-replay.json` against the published [pathwise-cost summary](results/statistics/operations.json). [Independent method](independent/README.md) · [Seed opening](custody/independent-seed-reveal.json) · [Final results](RESULTS.md) The archived SQLite operations can be decoded from the same input schedule, seed and pinned source. Source and controller reconstruction use only published synthetic data. Timing and memory results are measurements specific to code, instrumentation and host.
