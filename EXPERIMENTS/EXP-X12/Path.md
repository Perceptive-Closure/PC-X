# EXP-X12 execution record

## Phase 1. Scope and source

- Charter SHA-256 verified against the master plan. Read pp. 21–26, 34–36 and the status table on pp. 38–40. The study tests finite examples of T17–T20 and a bounded fixed-sample case of T23. T18 and T30 remain open in their central forms.
- Reconstructed X09's reset and confidence method, X10's separate scoring, and X11's passive/placebo fidelity tests from the pins in the frozen protocol. No predecessor behavior enters the new policy runtimes.
- Created the app-managed worktree from orchestration SHA 2477c9c1a4db1f017751f7a03e6d8c3e855d62ae and switched to codex/exp-x12. Scoped all runtime scratch and caches to the worktree.

## Phase 2. Pre-outcome checks

- Implemented the independent exact evaluator, opaque randomized control roster, matched and direct audit cohorts, nominal and stress reference banks, separate native runner and byte-bound forecast.
- The finite preflight checks 192 event paths, 80 exact covered coupling implications, both policies' complete evaluation laws in four supported cells, and 24 structural audit batch subsets. The two uncovered completions disagree in risk by 1/5 and 9/20 in their respective contexts.
- The public development and calibration artifacts are included in the immutable protocol revision. Parent custody begins with an independent GitHub archive of that revision.

## Phase 3. Audit and forecast seal

- Frozen protocol and executable verified on GitHub at 7a742d9835fef3d42205d28f6ff967009207b9a9. Before access to the holdout the parent independently ran all 15 tests and reproduced the exact preflight SHA-256 1a2919d37d16ca43840041e1c8ac8bf2acd8226ac6e5dbbe39ab2e73c924b4d2 and calibration SHA-256 0b16abd23e7358722553bcc4027ef32551dd0c9a5e883757e86b8e585c02598a.
- At 2026-11-26T15:26:20.7067878Z the parent verified the frozen GitHub source and reserved the roster with commitment 1ab286193a9a704c7d84b9ad7dcd52542004015a4361753302e14ce01c365f3a. The parent provided only the authorized receipt, SHA-256 08fba0709bff95c5a189e87d1ecd0cbe739731603e7446757ac0be102e9e3530. Native measurements remained sealed.
- Forecast seal SHA-256 2da0b2a9324f3d025f465e396df4da4485a830636ea39398425835f4b838ca37. The primary forecast is safe for Q01, Q06, S02 and S06, unsafe for Q05 and S03, and abstains for Q02, Q03, Q04, S01, S04 and S05.


## Phase 4. Held-out validation and publication

- The parent verified the current GitHub forecast tip c9fe2f92102298c04fe086e75c993e47c6fc2f17, its ancestry and exact receipt and forecast bytes at 2026-11-26T15:29:16.376097Z. The source and calibration hashes were unchanged. The pinned archive recorded opening at 2026-11-26T15:29:16.641839Z, then finished the independent release at 2026-11-26T15:29:19.5018972Z. [Opening record](results/opening.json)
- All six preregistered gates passed across 98,304 native episodes in 24 cells. Each of the six primary decisions agreed with the entire native worst-risk band, and all 24 contextual forecasts contained the exact risk and intersected the corresponding native band. The native bands also classified all six primary abstentions. The authorized direct audit resolved four of these six cases. The two missing-support outcomes required the trusted native measurement of novel enrollment.
- The trusted measurement baseline was stronger under the configured costs. It resolved 10 units with no errors and used 786,444 weighted operations. The primary resolved six units and used 1,048,804, less than the fixed all-batches baseline's 1,573,092. Cheapest-first tied the primary on the fixed structural menu. Uniformly random batch order averaged 1,398,329.33 and reached 1,573,092 at worst across the per-unit orders. These are counterfactual costs on the same measured comparator suite. The 65,536 shared public reference episodes are reported separately. That suite used 1,572,864 paired primitive comparisons and 196,608 direct audit episodes. [Forecast](results/forecast.json) · [Summary](results/summary.json)
- The fidelity failure repeated in both policies. Both probes reported zero discrepancy when run through the substituting port, but the independent native worst-risk rates were 90.50% in the queue and 97.31% in the sorter. Omitting the pulse check yielded two false favorable forecasts. The verified bounded-drift cells had summed mismatch upper bounds of 0.1254–0.1298. The changed-verdict cells used an independent stress reference and had upper bounds of 0.1332–0.1387. The two large-drift controls used valid ports and saturated the union bound, yielding [0, 1].
- The enrollment audit found exact uncovered mass 20% in routine and 45% in busy for the two missing-support cases. In the queue, the held-out enrollment counts were 799/4,096 and 1,829/4,096. In the sorter they were 815/4,096 and 1,880/4,096. These counts describe the respective holdout draws. The exact tape contributes [0, 0.20] and [0, 0.45] to the forecast. The realized missing-support variants straddled the risk threshold, with the queue safe and the sorter unsafe.
- The exact preflight found two target-distinct completions per policy with all four permitted evaluation laws equal, covering the entire native evaluation record. Their worst risks were 3.75% and 89.06% for the queue, and 11.23% and 97.12% for the sorter. This finite result isolates missing evidence. The broad T18 recovery conditions and the T30 flagship remain open.

| Method | Certified / 12 | Native confirmed | Abstentions | False safe | Forecast overlaps / 24 | Mean worst-risk width |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Anchored primary | 6 | 6 | 6 | 0 | 24 | 0.5178 |
| Conventional nominal extrapolation | 12 | 5 | 0 | 7 | 10 | 0.0628 |
| Full authorized direct measurement | 10 | 10 | 2 | 0 | 24 | 0.1355 |
| Nonadaptive all-batches anchors | 6 | 6 | 6 | 0 | 24 | 0.5178 |
| Diagnostic fidelity ablation | 8 | 6 | 4 | 2 | 20 | 0.3859 |

Each method had zero false unsafe conclusions. Native bands wholly opposed each false safe forecast. Full authorized measurement abstained on the two missing-support units. Every native episode issued three decisions. Correct-tray or finished-job rates in the final column measure realized utility.

| Unit | Control | Routine events / 4,096 | Busy events / 4,096 | Primary worst-risk band | Native worst-risk band | Utility |
| --- | --- | ---: | ---: | --- | --- | ---: |
| Q01 | Bounded drift | 173 | 207 | [0%, 19.59%] safe | [1.84%, 8.27%] safe | 99.26% |
| Q02 | Missing support | 88 | 62 | [0%, 54.23%] abstain | [0%, 5.37%] safe | 99.70% |
| Q03 | Vacuous | 1,986 | 2,042 | [0%, 100%] abstain | [46.64%, 53.07%] unsafe | 92.08% |
| Q04 | Fidelity violation | 3,564 | 3,707 | [0%, 100%] abstain | [87.29%, 93.72%] unsafe | 82.20% |
| Q05 | Changed verdict | 3,581 | 3,695 | [73.08%, 100%] unsafe | [86.99%, 93.43%] unsafe | 82.44% |
| Q06 | Identical | 97 | 151 | [0.69%, 6.97%] safe | [0.47%, 6.90%] safe | 99.52% |
| S01 | Fidelity violation | 3,946 | 3,986 | [0%, 100%] abstain | [94.10%, 100%] unsafe | 35.65% |
| S02 | Bounded drift | 423 | 569 | [0%, 28.22%] safe | [10.67%, 17.11%] safe | 95.77% |
| S03 | Changed verdict | 3,948 | 3,982 | [80.18%, 100%] unsafe | [94.00%, 100%] unsafe | 35.90% |
| S04 | Missing support | 1,155 | 2,172 | [0%, 60.04%] abstain | [49.81%, 56.24%] unsafe | 75.41% |
| S05 | Vacuous | 3,439 | 3,441 | [0%, 100%] abstain | [80.79%, 87.23%] unsafe | 54.37% |
| S06 | Identical | 304 | 454 | [9.03%, 15.31%] safe | [7.87%, 14.30%] safe | 96.82% |

The initial pre-freeze pulse test expected six distinct readings from the faulty port. Four sentinels distinguish the ports and two legitimately agree at their respective thresholds. The test expectation was corrected before the executable was sealed. All 15 frozen tests passed before reservation and after release. The full local replay matched the published manifest in 4.81 seconds with CPython 3.13.7. A separate readback without experiment module imports independently checked the 24 trusted raw cells, 160 admitted seam bands, 20 context mixtures and 24 exact risks. [Reproduction commands](README.md#verify-opened-evidence)

| Evidence | SHA-256 |
| --- | --- |
| Opening | 93b0e24cedab414b7d53ed8d791eddf2361886cc5249afb6b5c216d14cd44df7 |
| Compressed machine ledger | c9a8b151fbbc8c399be2e03eefacd5a6cb23c91fd1850547508ea4a12cd69d77 |
| Uncompressed JSONL | 843abfef78aada53e86cd3df726668e05aba031e6d97429c2ca8ca585731366a |
| Outcome summary | 754a7a7a192acf0c20c2a46e1b2719ccc8fdc6479e0decc74b582d06abb66096 |
| Complete digest manifest | e92897932cd948fc2a9a2ce53a6313fc735f113c386ffed26fed9176c1cee7cd |

The manifest binds every result file and the unchanged executable sources. [Digest manifest](results/manifest.json)
