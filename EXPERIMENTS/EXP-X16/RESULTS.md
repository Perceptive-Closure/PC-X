# EXP-X16 results

27 November 2026. The native experiment and independent reproduction validate the finite T30.CG correspondence on the signed synthetic service. The forecasts matched all 178 admitted path targets and 70 comparator values. The experiment checked 22 admitted held-out installations and used another 10 for the scope controls. Every tested positive policy branch completed its required durable work. Truly negative cases and jointly infeasible policies had distinct outcomes. [Protocol](Protocol.md) · [Machine-readable results](results/summary.json) · [Exact comparator agreement](results/forecast-agreement.json)

## Matched baseline results

All prices are worst-case paid acquisition units. The pure comparators use the same total query menu before service. The joint comparators use the same legal online commands, public receipts, work deadline and move horizon. Full identity requires one compatible accepting path wherever a verdict is issued. The fixed schedule chooses one literal command per move for all continuing branches and permits an eligible branch to stop. A dash indicates the fixed comparator was outside the preregistered set. The attainable-score-set solver agreed with the frontier-extrema solver on each online target value, including infeasibility.

| Profile | Work deadline / moves | Admitted paths | Held-out YES / NO | Fixed pure target / identity / all | Adaptive pure target / identity | Joint target / identity | Fixed joint target |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| feedback-live | 4 / 3 | 2 | 2 / 0 | 0 / 1 / 12 | 0 / 1 | 0 / 0 | Infeasible |
| feedback-suppressed | 4 / 3 | 2 | 2 / 0 | 0 / 1 / 12 | 0 / 1 | Infeasible / Infeasible | Infeasible |
| meter-h3 | 2 / 3 | 2 | 1 / 1 | 1 / 1 / 8 | 1 / 1 | 3 / 3 | 3 |
| meter-h4 | 2 / 4 | 2 | 1 / 1 | 1 / 1 / 8 | 1 / 1 | 2 / 2 | 3 |
| intrinsic-gap | 4 / 4 | 2 | 1 / 1 | 1 / 1 / 12 | 1 / 1 | 1 / 1 | 1 |
| gateway-2 | 5 / 6 | 8 | 2 / 2 | 1 / 3 / 12 | 1 / 3 | 1 / 3 | 1 |
| gateway-4 | 9 / 10 | 32 | 2 / 2 | 1 / 5 / 20 | 1 / 5 | 1 / 5 | — |
| gateway-6 | 13 / 14 | 128 | 2 / 2 | 1 / 7 / 28 | 1 / 7 | 1 / 7 | — |

- **Useful feedback.** Both connected paths complete at work 4 under their own fastest lawful actions. In the live profile the first completed job issues `LEFT` or `RIGHT`, which permits a common adaptive controller at paid cost 0. A fixed schedule is infeasible. Suppressing that first receipt makes joint completion infeasible while both known-mode executions still complete at work 4.
- **Dynamic meter.** The longer initial receipt exposes a direct read at price 3. The fourth move permits the adaptive controller to prepare at price 1 and inspect at price 1. The fixed schedule remains at 3. The pure predeployment minimum is 1 and certifies the intrinsic label.
- **Target and identity.** In the three gateway profiles the same-menu online target cost is 1 and the online full-identity costs are 3, 5 and 7. The pure same-menu minima have the same gaps. The measured advantage concerns the less demanding target objective on these graphs.

## Native ground truth and scope controls

The signed native diagnostic covers 188 graph-accepted paths across the primary and control profiles. It checks 1,126 stage/installation pairs, 3,388 literal command rows and 3,400 supported raw successors, including rows removed by the whole-occurrence freeze. The strongest trusted comparator reads these native guard rows with installed mode known. It bounds the unavoidable tariff across every stage and replays the cheapest known-mode job sequence on the selected installations. Its job execution incurs zero paid audit charges. Source inspection, job work and file verification are separately accounted for.

The primary runner recorded 890 pure native trials, 118 held-out work runs across trusted direct and finite policy treatments, and 14 additional deliberate control runs. It re-read and verified 359 durable stage records. Every published digest traces the exact source document, receipt, phase, normalized product, previous record and final destination for its run. [Guard ledger](results/anchor-ledger.json) · [Full native traces](results/runs.jsonl) · [Exact artifact examples](results/artifact-examples.json)

| Control | Verified observation |
| --- | --- |
| Cartesian projection | Both connected paths require work 4. The projected double-stale route would require 5, and the signed graph rejects that installation. |
| Suppressed work receipt | Both known-mode executions succeed, their first receipts both report `WORK`, and the common joint policy is infeasible. |
| Literal fast calls | The projected shared command is denied on both paths. The separate `job.fast.left` and `job.fast.right` calls complete their respective installations. |
| Free initial guard | Startup discloses the label. With this changed information the installations use paid cost 0 against 3 for the forecast with a uniform initial receipt. |
| Omitted LONG support | The short-only forecast costs 1. The real LONG receipt falls outside its policy on both installed routes. The complete-support optimum is 3 at three moves and 2 at four. |
| Hidden carry | For the same later edge and visible `WORK` meter, the actual inspection price is 1 after a cleared history and 5 after a set history. |
| Changed instrument | The paired runs agree on paid cost 1, public trace and YES verdict. The trusted run writes to `routed/category-local-correspondence` and the disturbed run writes to `quarantine`. |

## Computation and measurement

The three columns in each cell are frontier extrema, full attainable score sets and the independent explicit-history solver, respectively. Each solve entry is the median of three same-host timings with Python allocation tracing enabled. The memory entry is the peak traced Python allocation across these invocations. Preparation, native diagnostics, file inspection and independently measured uninstrumented solve times are preserved separately.

| Profile | Online solve median, ms | Online solve peak, KiB |
| --- | ---: | ---: |
| feedback-live | 0.84 / 0.85 / 0.59 | 10.9 / 11.7 / 11.1 |
| feedback-suppressed | 0.60 / 0.64 / 0.27 | 10.3 / 9.4 / 4.4 |
| meter-h3 | 1.05 / 1.24 / 0.93 | 13.3 / 14.3 / 11.4 |
| meter-h4 | 1.90 / 1.63 / 0.97 | 16.3 / 18.1 / 12.1 |
| intrinsic-gap | 1.11 / 1.14 / 0.51 | 11.8 / 12.0 / 6.2 |
| gateway-2 | 8.51 / 8.62 / 5.85 | 57.3 / 53.9 / 30.4 |
| gateway-4 | 76.54 / 76.81 / 113.83 | 321.8 / 381.7 / 288.4 |
| gateway-6 | 397.17 / 406.30 / 2,433.65 | 1,238.3 / 1,402.1 / 1,335.7 |

The frontier representations visited the same number of memoized states on all eight profiles. The explicit solver was quicker by median on six profiles. Both frontier representations were quicker on gateway-4 and gateway-6. The full-score-set frontier had the lower median of the two frontier implementations on meter-h4. These timings are specific to the declared small graphs, code and host. [Primary raw timings and diagnostic overhead](results/raw-benchmarks.json) · [Independent explicit timings](results/independent/explicit-history-timing.json)

## Prospective registration and independent replay

| Gate | GitHub revision | UTC witness on 26 November 2026 |
| --- | --- | --- |
| Freeze 36 source files | [861bc00](https://github.com/Perceptive-Closure/PC-X/commit/861bc00b5836aabb8aea9dc129f0674afbe30fc2) | Before draw commitment |
| Signed draw commitment | [06f728b](https://github.com/Perceptive-Closure/PC-X/commit/06f728b0ae8c09bc7b18c8014ec66df39a710a9c) | 21:59:35 |
| Published full forecast | [cd3fcd3](https://github.com/Perceptive-Closure/PC-X/commit/cd3fcd3a385d85236275024f7dc704b1b1e71775) | 22:00:06 |
| Primary prerelease receipt | [42196a0](https://github.com/Perceptive-Closure/PC-X/commit/42196a0c83649b50fad124c67c302ea845a5fc6e) | Both relays confirmed future round |
| Independent prerelease receipt | [77b4d9f](https://github.com/Perceptive-Closure/PC-X/commit/77b4d9fa3f0a5ee3bb9bd6b23378ac3a68b570bf) | 22:01:28 |
| Fixed round 34309120 | [bf91bb5](https://github.com/Perceptive-Closure/PC-X/commit/bf91bb5f48549853ee614361d4bc0f9f917e08b6) | 22:05:24 scheduled, 22:05:49 signatures verified |

The forecast was regenerated byte for byte from the frozen source. The opening binds the exact Git objects, forecast SHA-256, signed round and selected installations. Both pre-round receipts verified that the fixed round was unavailable. The custodian confirmed the exact opening commit by independent GitHub readback. [Source manifest](custody/frozen-manifest.json) · [Signed draw plan](custody/draw-plan.json) · [Forecast receipt](results/forecast-receipt.json) · [Independent custody receipt](custody/prerelease-receipt.json) · [Opening](custody/opening.json)

The independent runner re-created all 32 installations from the verified round and executed 649 native trials with zero discrepancies. It used separately written search and native evidence checks. Its own online target and full-identity witnesses each traversed 24 selected tapes, with 13 useful YES outcomes and 11 lawful NO outcomes per treatment. The runner independently checked 188 installed paths, 3,388 literal commands and 3,400 raw outcomes. It re-read actual files, verified all seven scope controls and matched every admitted forecast bundle. [Independent replay report](results/independent/report.json) · [Independent evidence commit](https://github.com/Perceptive-Closure/PC-X/commit/2912de224021dba41f20362b44b4cdb1c53164df)

The engineering, custody and reproduction roles used distinct worktrees on one host account. The unavailability of the external future round and the GitHub readbacks are the basis for temporal withholding. Validation covers the stipulated finite graph, signed tariffs and positive receipt supports for this synthetic service. Runtime, probability, strategic behavior and production transfer remain outside that scope. All 15 original experiment branch tips, both mathematical baselines and the default branch matched their original pins. [Original pins](PINS.json) · [Replay commands](README.md)
