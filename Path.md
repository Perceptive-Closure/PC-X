# PC-X master execution record

## Program status

2026-11-26, Asia/Karachi. The 43-page final charter and experimental directive were read. The starting local Git repository had no commits and no remote. GitHub CLI confirmed administrator access and created the private `Perceptive-Closure/PC-X` repository. The charter's definitions, experimental gates, dependencies and the original manuscript's finite PC semantics informed the first protocols. The experiment database is the registry below. The dependency graph and acceptance gates are in [WorkPlan.md](WorkPlan.md).

## Execution slots

| Slot | Experiment | Agent | Lifecycle |
| --- | --- | --- | --- |
| 1 | X05 | exp_x05 | DISPATCHED |
| 2 | X09 | exp_x09 | DISPATCHED |
| 3 | X11 | exp_x11 | DISPATCHED |

Each slot remains occupied through parent clean-checkout verification, safe cleanup, and independent verification of remote evidence and cleanup. Reserved slots count toward the concurrency ceiling.

## Experiment registry

| Experiment | State | Scientific verdict | Branch | Commit and verification |
| --- | --- | --- | --- | --- |
| X01 | COMPLETE | Finite agreement supported | codex/exp-x01 | [a52d45f1b8c0036b1a69b1fc024f95e48d4ce012](https://github.com/Perceptive-Closure/PC-X/tree/a52d45f1b8c0036b1a69b1fc024f95e48d4ce012/EXPERIMENTS/EXP-X01) |
| X02 | COMPLETE | Correlation and strict outer-set gaps confirmed in the finite fragment | codex/exp-x02 | [18bc904d7073df3536d9794f18b868b9a3de53bc](https://github.com/Perceptive-Closure/PC-X/tree/18bc904d7073df3536d9794f18b868b9a3de53bc/EXPERIMENTS/EXP-X02) |
| X03 | COMPLETE | Finite minimum-cost correctness supported | codex/exp-x03 | [d85fe1cdb76cbc6d03e58e34f320c4c58a3f243c](https://github.com/Perceptive-Closure/PC-X/tree/d85fe1cdb76cbc6d03e58e34f320c4c58a3f243c/EXPERIMENTS/EXP-X03) |
| X04 | COMPLETE | Exact minimax supported with conditional cost savings | codex/exp-x04 | [b6ce562aa91323f2913615b92e91ffb2b9cc4731](https://github.com/Perceptive-Closure/PC-X/tree/b6ce562aa91323f2913615b92e91ffb2b9cc4731/EXPERIMENTS/EXP-X04) |
| X05 | DISPATCHED | Pending | codex/exp-x05 | X01–X03 accepted and cleaned |
| X06 | WORKPLAN_CREATED | Pending | codex/exp-x06 | Awaiting X01 and X03 |
| X07 | WORKPLAN_CREATED | Pending | codex/exp-x07 | Awaiting X03 |
| X08 | COMPLETE | Bounded transcript equivalence and forecast supported | codex/exp-x08 | [a8c6650a7ff9901ca9ac5ed4036a37f6cb7c9200](https://github.com/Perceptive-Closure/PC-X/tree/a8c6650a7ff9901ca9ac5ed4036a37f6cb7c9200/EXPERIMENTS/EXP-X08) |
| X09 | DISPATCHED | Pending | codex/exp-x09 | X04 and X08 accepted and cleaned |
| X10 | COMPLETE | Monitor ambiguity and bounded recovery supported | codex/exp-x10 | [4a16ef37d0e90e856560ce153c0fd690c28016b6](https://github.com/Perceptive-Closure/PC-X/tree/4a16ef37d0e90e856560ce153c0fd690c28016b6/EXPERIMENTS/EXP-X10) |
| X11 | DISPATCHED | Pending | codex/exp-x11 | X08 accepted and cleaned |
| X12 | WORKPLAN_CREATED | Pending | codex/exp-x12 | Awaiting X09–X11 |
| X13 | WORKPLAN_CREATED | Pending | codex/exp-x13 | Awaiting X10 and X11 |
| X14 | WORKPLAN_CREATED | Pending | codex/exp-x14 | Awaiting X04 and X13 |
| X15 | WORKPLAN_CREATED | Pending | codex/exp-x15 | Awaiting all predecessor terminal outcomes |

## Parent verification ledger

- Repository metadata confirmed correct owner, private visibility and administrator access. Starting checkout and source PDFs are outside cleanup scope.
- Verified the first remote protocol commit at `91c2158877e5440aedafd76a2b16f6bfa389c330`. Dispatched one isolated agent each for X01, X03 and X08, with disposable clones, isolated caches and independent parent review before cleanup.
- All fifteen experiment work plans are versioned. X01 froze a cyclic finite positive-support fragment, X03 froze an exact weighted certificate corpus, and X08 froze independently assigned three-round parcel routing profiles. X08 assigned the parent prospective custodian. Held-out outcomes are sealed.
- X03 reported 12 passing preflight tests, 865 domains, 3,828 scopes, 59,971 subset checks and zero status or cost discrepancies in its initial replay. Parent acceptance is pending independent remote reproduction.
- X08 pre-audit found a minimum-cost parcel-A routing calibration (cost 2). The parent cloned and verified `52a04c5d65c196892d4c888e2a5e8b82d07d4fbf` and independently measured the permitted calibration answer at 2026-11-26 17:57:25 Asia/Karachi. The assignment commitment is `28097faa180957fde1494472c79acfb6f623f3c08754a6d1fb7735e716051460`. At that stage the prediction was pending and the outcomes remained sealed.
- X08 parent verified forecast `ce5f10b0ff0e5d549eecf7cbd8c08a88ccae809e` at 2026-11-26 17:58:45 Asia/Karachi before the unchanged runner executed and opened 8,192 sandbox episodes. Both unit-level threshold forecasts were confirmed and four out of four deployment intervals intersected the forecast bands. The benchmark-only comparison falsely certified one unit. Parent and agent roles used separate checkouts on a shared filesystem.
- X01 reported 19 passing tests, agreement across 1,944 freeze coordinate values and 1,378 evidence cases, and 1,155 individually checked witnesses. Hidden-state and incomplete-touch controls each exposed optimistic ablation errors. Parent verification is pending a terminal candidate.
- X01 parent reproduced candidate `ad6124afbb662e385ecdc695e6fcfa3d58fe3570` in a clean GitHub checkout. All 19 tests and the full evidence digest check passed. The corpus had 243 contracts, 1,944 freeze-coordinate evaluations, 1,378 evidence cases, 1,155 independently checked witnesses and zero unexpected discrepancies. The hidden-state oracle and representative-only touch ablations failed on 6/18 and 3/6 intended examples. The terminal revision adds only the verification ledger.
- X03 parent reproduced candidate `540c680b095ad59ed42fcb2edc70fcba94241d57` from a clean GitHub checkout. All 12 tests and two evidence hashes matched. An independent CSV aggregation checked 59,971 subset checks over 3,828 scopes, 3,102 accepted certificates, 725 inaccessibility scopes, one inconsistent case, and exact cost no greater than every comparator for all 645 finite uniform scopes. Mean optimum was 2.131783 cost units versus greedy's 2.207752. The terminal revision adds only the verification ledger.
- X08 parent reproduced candidate `6f17f4cd603199a76beda5c8db105806c2727844` from a clean GitHub checkout. All seven tests passed and all 8,192 episodes reproduced with SHA-256 `72a5ce71dd8f654ffbf9dacc5938352cef7fe45783fa16aa5a87bbc9cddc925f`. A separate computation checked native retry flags from facility tickets, trial counts, both threshold conclusions and simultaneous intervals. The parent first misread the Boolean as delivery. Rechecking the schema and reconstructing from tickets corrected the verification. Worst observed deployment risk was 651/1,024 for parcel-A and 128/1,024 for parcel-B. The two forecasts resolved correctly relative to the 40% threshold. The exact minimum audit cost was 2 versus cheapest-first 6 and exhaustive cost 8. The terminal revision adds only the verification ledger.

## Second-wave implementation

- X02, X04 and X10 created isolated, app-managed worktrees. Their attachment paths are `pcx-x02/PC-X`, `pcx-x04/PC-X` and `pcx-x10/PC-X` under the app's worktree directory. Scratch and caches are scoped to each checkout.
- X02 fetched the verified X01 package and froze its finite fixed-skeleton protocol. X04 fetched the verified X03 exact certificate fixtures. X10 froze its passive independent route-card audit before any holdout assignment or measurement.

- X02: The parent fetched the terminal tree by immutable SHA and reproduced all 10 tests and full evidence hashes. The first preparation attempt inherited a Git path prefix from its enclosing worktree. Explicit temporary Git metadata and the snapshot as working root fixed the parent replay. Three separate evaluators agreed on 1,992 freeze values across 249 completions and 94 cases. An independent tabulation confirmed 29 strict joint relaxations among 83 nonempty cases, 19 false coordinate ambiguities and 51 wider coordinate bounds. The app archived the clean, pushed worktree. Verified the root absent and unchanged remote SHA. Removed 4,282,884 logical bytes in checkout and scratch. X05 is eligible and reserved.
- X04: Protocol `989b6865f03375dc500abed5f6be3d75a7377261` was sealed before execution. Independently retrieved X04 and pinned X03 from GitHub. All 15 tests and summary, table and policy-replay digests matched. Across 88 finite workload cases there were 47 finite minimax policies, 40 verified unavailable-audit witnesses, one inconsistent domain, 21,062 checked policy paths, and zero independent budget-search disagreements. Six of seven feasible routed cases reduced worst-case cost, with a tie in the other. Two routed ablations were inaccessible. All four feasible X03 fixtures tied static cost.
- X10: The parent retrieved pre-audit `558787d095716e21a6692f56a5eb3e886174f16f` and obtained only the selected route-card calibration. The assignment was committed with digest `cefc4b52e6abf870446c587b637d06801c4bd0f92d141f44623384efd359e846`. The parent checked forecast `ae3665bf83ed4650d4acf19c00f5cca2eff4ae3a`, unchanged runner/config and exact receipt bytes at 19:32:54 Asia/Karachi before opening. Clean remote replay of the terminal commit passed 8 tests and matched 16,384 trials, 4/4 threshold confirmations and 8/8 risk envelope overlaps. Alarm-only reporting missed one of two cases. Raw trace integrity SHA-256 `1269290b40011c127201036e7789c8bfd4d9963b5ab2687a6b1df4711d8c0d71`.

- X04 independent recomputation from the frozen routed tables confirmed all six strict cost reductions, one tie and two interface failures. Five-site costs were 2 adaptive versus 6 static. Skewed weighted costs were 7 versus 12. The app removed the managed worktree and scratch, accounting for 9,688,895 logical bytes, and the parent verified absence and the unchanged remote SHA.
- X10 raw independent scoring reproduced all route quality, alarm, miss and false-alarm counts in four 4,096-trial cells, both raw and gzip hashes, and the simultaneous confidence width. At peak mix the alarm rates were 17.14% and 16.64% while missed-event frequencies were 48.24% and 8.58%. The audit used a legitimate route-card read, with validity conditional on the frozen balanced enrollment and trusted scoring. The app removed the managed worktree and scratch, accounting for 762,768 logical bytes. Parent verified absence and the unchanged remote SHA.
- X05 is active after X02's slot release. X09 and X11 are eligible after the verified X04 and X10 releases.

## First-wave cleanup and restart

Automatic command approval rejected recursive removal and individually verified literal-path file removal for X03. Individually verified literal-path removal was also rejected for X08. The sole error detail was `blocked by policy` at process creation. Rejections occurred before execution and no files were deleted. X01 cleanup was held after the same methods were rejected for the other experiment roots. These directories were created for this program, contain the disposable clones, reproduction checkouts and scoped outputs, and have verified durable GitHub packages.

| Exact directory | Inventory before cleanup |
| --- | --- |
| `C:\Users\Saif malik\AppData\Local\Temp\PC-X-20261126\EXP-X01` | 6,885,856 logical bytes in parent-repro, repro-agent, scratch, source and verify-temp |
| `C:\Users\Saif malik\AppData\Local\Temp\PC-X-20261126\EXP-X03` | 2,633,143 logical bytes in repro, scratch, self-repro, source and verify-temp |
| `C:\Users\Saif malik\AppData\Local\Temp\PC-X-20261126\EXP-X08` | 4,636,778 logical bytes in cache, custodian, parent-replay, repro, source, tmp and verify-temp |

On 2026-11-26 at 19:17 Asia/Karachi, Infernus explicitly directed the parent to perform the cleanup. The parent used File Explorer's permanent-delete workflow after verifying the exact targets, absence of reparse points, and all three remote commits. Independent filesystem readback confirmed the three roots and every nested experiment-owned file and cache were absent. All three remote heads were unchanged on readback. The removed files accounted for 14,155,777 logical bytes. Slots 1–3 were released. X02, X04 and X10 were selected for the next wave.

The next wave uses one managed Git worktree per experiment with all ignored scratch and caches scoped inside the managed checkout. Parent reproducibility checks retrieve the exact committed source independently from GitHub. This permits scoped checkout cleanup through the app's worktree lifecycle.

## Findings and outstanding obligations

Operationally complete 6/15. X05, X09 and X11 are dispatched and six experiments are queued. Accepted claims remain bounded to the tested finite and sandbox systems. The general transport and flagship results remain open.
