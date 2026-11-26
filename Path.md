# PC-X master execution record

## Program status

2026-11-26, Asia/Karachi. The 43-page final charter and experimental directive were read. The starting local Git repository had no commits and no remote. GitHub CLI confirmed administrator access and created the private `Perceptive-Closure/PC-X` repository. The charter's definitions, experimental gates, dependencies and the original manuscript's finite PC semantics informed the first protocols. The experiment database is the registry below. The dependency graph and acceptance gates are in [WorkPlan.md](WorkPlan.md).

## Execution slots

| Slot | Experiment | Agent | Lifecycle |
| --- | --- | --- | --- |
| 1 | X01 | exp_x01 | IMPLEMENTING |
| 2 | X03 | exp_x03 | RESULTS_DOCUMENTED |
| 3 | X08 | exp_x08 | EXECUTING |

Each slot remains occupied through parent clean-checkout verification, safe cleanup, and independent verification of remote evidence and cleanup. Reserved slots count toward the concurrency ceiling.

## Experiment registry

| Experiment | State | Scientific verdict | Branch | Commit and verification |
| --- | --- | --- | --- | --- |
| X01 | IMPLEMENTING | Pending | codex/exp-x01 | Protocol df82c2ffb97387fb0ac2e00dd53b741bf7e4408c |
| X02 | WORKPLAN_CREATED | Pending | codex/exp-x02 | Awaiting X01 |
| X03 | RESULTS_DOCUMENTED | Under review | codex/exp-x03 | Protocol f5d23f4e8c3ff673c182f7f2ca9366251bba81a9 |
| X04 | WORKPLAN_CREATED | Pending | codex/exp-x04 | Awaiting X03 |
| X05 | WORKPLAN_CREATED | Pending | codex/exp-x05 | Awaiting X01–X03 |
| X06 | WORKPLAN_CREATED | Pending | codex/exp-x06 | Awaiting X01 and X03 |
| X07 | WORKPLAN_CREATED | Pending | codex/exp-x07 | Awaiting X03 |
| X08 | EXECUTING | Pending | codex/exp-x08 | Pre-audit 52a04c5d65c196892d4c888e2a5e8b82d07d4fbf |
| X09 | WORKPLAN_CREATED | Pending | codex/exp-x09 | Awaiting X04 and X08 |
| X10 | WORKPLAN_CREATED | Pending | codex/exp-x10 | Awaiting X08 |
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
- X08 pre-audit found a minimum-cost parcel-A routing calibration (cost 2). The parent cloned and verified `52a04c5d65c196892d4c888e2a5e8b82d07d4fbf` and independently measured the permitted calibration answer at 2026-11-26 17:57:25 Asia/Karachi. The assignment commitment is `28097faa180957fde1494472c79acfb6f623f3c08754a6d1fb7735e716051460`. The prediction is pending and native outcomes remain sealed.

## Findings and outstanding obligations

No experimental results have been observed. Operationally complete 0/15. The execution phases, remaining dependency order and claim gates are recorded in the work plan.
