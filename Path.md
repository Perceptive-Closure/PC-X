# PC-X master execution record

## Program status

2026-11-26, Asia/Karachi. The 43-page final charter and experimental directive were read. The starting local Git repository had no commits and no remote. GitHub CLI confirmed administrator access and created the private `Perceptive-Closure/PC-X` repository. The charter's definitions, experimental gates, dependencies and the original manuscript's finite PC semantics informed the first protocols. The experiment database is the registry below. The dependency graph and acceptance gates are in [WorkPlan.md](WorkPlan.md).

## Execution slots

| Slot | Experiment | Agent | Lifecycle |
| --- | --- | --- | --- |
| 1 | X02 | exp_x02 | RESERVED |
| 2 | X04 | exp_x04 | RESERVED |
| 3 | X10 | exp_x10 | RESERVED |

Each slot remains occupied through parent clean-checkout verification, safe cleanup, and independent verification of remote evidence and cleanup. Reserved slots count toward the concurrency ceiling.

## Experiment registry

| Experiment | State | Scientific verdict | Branch | Commit and verification |
| --- | --- | --- | --- | --- |
| X01 | COMPLETE | Finite agreement supported | codex/exp-x01 | [a52d45f1b8c0036b1a69b1fc024f95e48d4ce012](https://github.com/Perceptive-Closure/PC-X/tree/a52d45f1b8c0036b1a69b1fc024f95e48d4ce012/EXPERIMENTS/EXP-X01) |
| X02 | WORKPLAN_CREATED | Pending | codex/exp-x02 | X01 accepted and cleaned |
| X03 | COMPLETE | Finite minimum-cost correctness supported | codex/exp-x03 | [d85fe1cdb76cbc6d03e58e34f320c4c58a3f243c](https://github.com/Perceptive-Closure/PC-X/tree/d85fe1cdb76cbc6d03e58e34f320c4c58a3f243c/EXPERIMENTS/EXP-X03) |
| X04 | WORKPLAN_CREATED | Pending | codex/exp-x04 | X03 accepted and cleaned |
| X05 | WORKPLAN_CREATED | Pending | codex/exp-x05 | Awaiting X01–X03 |
| X06 | WORKPLAN_CREATED | Pending | codex/exp-x06 | Awaiting X01 and X03 |
| X07 | WORKPLAN_CREATED | Pending | codex/exp-x07 | Awaiting X03 |
| X08 | COMPLETE | Bounded transcript equivalence and forecast supported | codex/exp-x08 | [a8c6650a7ff9901ca9ac5ed4036a37f6cb7c9200](https://github.com/Perceptive-Closure/PC-X/tree/a8c6650a7ff9901ca9ac5ed4036a37f6cb7c9200/EXPERIMENTS/EXP-X08) |
| X09 | WORKPLAN_CREATED | Pending | codex/exp-x09 | Awaiting X04 and X08 |
| X10 | WORKPLAN_CREATED | Pending | codex/exp-x10 | X08 accepted and cleaned |
| X11 | WORKPLAN_CREATED | Pending | codex/exp-x11 | Awaiting X08 |
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

## First-wave cleanup and restart

Automatic command approval rejected recursive removal and individually verified literal-path file removal for X03. Individually verified literal-path removal was also rejected for X08. The sole error detail was `blocked by policy` at process creation. Rejections occurred before execution and no files were deleted. X01 cleanup was held after the same methods were rejected for the other experiment roots. These directories were created for this program, contain the disposable clones, reproduction checkouts and scoped outputs, and have verified durable GitHub packages.

| Exact directory | Inventory before cleanup |
| --- | --- |
| `C:\Users\Saif malik\AppData\Local\Temp\PC-X-20261126\EXP-X01` | 6,885,856 logical bytes in parent-repro, repro-agent, scratch, source and verify-temp |
| `C:\Users\Saif malik\AppData\Local\Temp\PC-X-20261126\EXP-X03` | 2,633,143 logical bytes in repro, scratch, self-repro, source and verify-temp |
| `C:\Users\Saif malik\AppData\Local\Temp\PC-X-20261126\EXP-X08` | 4,636,778 logical bytes in cache, custodian, parent-replay, repro, source, tmp and verify-temp |

On 2026-11-26 at 19:17 Asia/Karachi, Infernus explicitly directed the parent to perform the cleanup. The parent used File Explorer's permanent-delete workflow after verifying the exact targets, absence of reparse points, and all three remote commits. Independent filesystem readback confirmed the three roots and every nested experiment-owned file and cache were absent. All three remote heads were unchanged on readback. The removed files accounted for 14,155,777 logical bytes. Slots 1–3 were released. X02, X04 and X10 were selected for the next wave.

## Findings and outstanding obligations

Operationally complete 3/15. Three next-wave slots reserved and nine experiments awaiting prerequisites. Accepted claims remain bounded to the tested finite and sandbox systems. The general transport and flagship results remain open.
