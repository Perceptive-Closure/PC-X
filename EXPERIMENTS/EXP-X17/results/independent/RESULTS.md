# Independent X17 results

## Signed opening and fixed measurements

The independent copy used exact freeze `be574f4eaba8a52b50c5604e87075ab4cac81b79` and run authorization `19c9bc68a9f9f98d99a96a6fb662ded73d50e75c`. The before-opening receipt independently matched 71 frozen files and all 10,480 candidate forecasts and recorded both relays withholding Quicknet round 34323065. After authorization, this role authenticated the archived signed beacon, independently retrieved the identical signed value from both registered relays, regenerated all eight roster rows byte for byte, and verified the 40 earlier actual forecasts and 40 associated nominal forecasts. We used the precommitted separate 32-byte role seed. [Before-opening evidence](../../custody/independent-prerelease.json) · [Opening checks](../../custody/independent-opening-checks.json) · [Relay readback](relay-readback.json) · [Independent seed reveal](../../custody/independent-seed-reveal.json)

All 163,840 fixed main attempts were valid across 40 cells. The 512 ordinary diagnostics and 1,024 matched nominal/actual pairs were checked separately. Main and diagnostic invalid counts were zero. The six observed mismatches between matched actual and nominal final artifacts all fell within the exact surcharge strip, and all six strip hits changed the final artifact. No samples were replaced. The native trace and archive verifier checked all 165,376 index rows against 166,400 committed native attempts. [Independent exact cell counts and intervals](independent-summary.json) · [Complete compressed index](independent-index.ndjson.gz) · [Replay checks and material examples](replay-metadata.json)

## Registered empirical decisions

All 320 independent point forecasts fell within their simultaneous intervals. All 280 fixed-score intervals and 32 of 40 conditional-risk intervals fell entirely within the prespecified equivalence tolerance. The other eight conditional intervals were inconclusive about equivalence. The table gives supported cells within this role. Uncounted cells for the displayed tests were inconclusive. [Registered thresholds and comparison rule](../../STATISTICAL-ANALYSIS-PLAN.md) · [Per-cell results](independent-summary.json)

| Registered endpoint | PC-X | Always high |
| --- | ---: | ---: |
| Wrong declaration at most 1/3 | 4/8 | 8/8 |
| All-world issuance at least 1/4 | 6/8 | Outside this arm's registered threshold |
| True-positive issuance at least 2/3 | 2/4 | 4/4 |
| True-positive useful utility at least 25/32 | 2/4 | 4/4 |
| Actual conditional risk at most 3/8 | 8/8 | 7/8 |
| Actual conditional risk at most 5/16 | 6/8 | 5/8 |
| True-positive conditional risk at most 5/32 | 4/4 | 4/4 |
| Signed selective score at most zero | 5/8 | 4/8 |

The matched positive and negative decisions include exact boundary instances. The proved target inequalities and the less decisive finite-sample threshold intervals retain their corresponding scopes. The synthetic random-stream experiment estimates these fixed cells under the registered repeated-run model. Universal statements require the source and mathematical checks.

## Exact source and controls

The independent decoder reconstructs the source-to-intake-to-final artifact chain from native SQLite bytes. It verifies signed receipt fields, scan quantities and variances, correct staging, authorized route literal, one probe and debit, prelude support, post-verdict carried proposal, and proposal-before-word order. It certifies actual wrong routing or corrupted inventory by decoding material artifact content. The source work is genuine within the local synthetic service, with one useful unit from reconciliation and an additional unit earned by safe true-positive completion. The material examples retain these bytes and their exact digests, including one matched pair with equal recorded trace and different nominal/actual routed bytes. [Frozen artifact decoder](../../independent/evidence.py) · [Material records](replay-metadata.json)

All 19 controls reproduced their registered consequences on disjoint off-roster fixtures. The archive retains 70 native control attempts and the linked native artifacts. C04 explicitly repeated the identical low literal with unchanged first debit. C06 used the disclosed sign through an actual authorized skip to classify both off-roster signs at zero paid acquisition cost. C09 independently checked an unchanged complete controller-facing record and a changed final physical object. C18 additionally uses the exact measure-zero supported singleton, and C19 the 20-ticket selective-risk counterexample. [Control outcomes](independent-control-summary.json) · [Control artifact archive](independent-controls.json.gz) · [Frozen control expectations](../../CONTROL-REGISTRY.md)

The guard price of 1/4 is separate from paid acquisition. The executed 1/8 ordinary source receipt could not authenticate revision B, while the full check cost one. The guard evidence preserves both signs on the matched pair, with route and stock-dependent receipt values, complete prelude and offered support matching before the selected probe. Low, high and skip have exact opposite-parameter TV gaps 1/4, 1/2 and zero, respectively. After a real positive the carried bit and installed mode set the proposal. The ordinary operation uses the installed theta, with an outcome distinct from useful finalization for the declared classifier. [Native API at frozen revision](https://github.com/Perceptive-Closure/PC-X/blob/3e4ddbaad5cf3170cdafa0c4f615b4b0f98b9316/EXPERIMENTS/EXP-X17/native/API.md)

## Exact explicit histories and grid checks

The independently implemented exact LP returned 7/12 in the full menu and 2/3 with high plus skip, both on the selected eight worlds and separately on the exact matched pair. Low plus skip, no paid, and every hard cap below one are infeasible for this pair. The re-evaluation checked those claims with and without the 1/4 all-world issuance floor. It validates each rational primal separately and refutes every strictly lower epigraph cost using a rational linear solver. Under the expanded direct-bit menu the column-wise TV bound and the one-third direct mixture yield exactly 1/6. [Explicit-history certificates](independent-optimization.json) · [Reconstruction code](../../formal-checks/independent_optimization.py)

In counted coordinates, each word with the same number of stays has the same mass, and the carried ending bit is the parity of its number of flips. Averaging the exact explicit selection and issue-flow fractions within the class preserves every endpoint. Assigning the average back to every word lifts a counted controller to the original law. There are (2^N) complete words per route and (N+1) count classes per route. The replay independently checked multiplicities and exact masses for the selected worlds. For depths 1, 2, 4 and 6 the upper/lower mesh also checked the complete (eta=1/32) rational constraints at both refinements. The certified lower/upper values were [7/12, 121/192] and [7/12, 233/384]. These certificates use the base uncalibrated menu and the original positive-only coverage constraints. The 1/4 floor is kept in the separate finite-instance comparison. [Grid checks, counts, and exact slacks](independent-grid-check.json)

## Reproduce the archived material

Use an isolated checkout or Git archive of authorization `19c9bc68a9f9f98d99a96a6fb662ded73d50e75c`. Export the 32 raw bytes from the published independent seed reveal after checking its SHA-256 against the frozen independent commitment. Run the frozen `independent/run.py` with the exact PH-06 arguments in its README and a fresh output directory. From the verification branch run `python independent/replay_checks.py RUN_DIR OFFICIAL_CUSTODY/opening-roster.json OUTPUT.json` within EXP-X17. It checks all native attempt IDs, hashes, integer sums, diagnostic totals and recorded artifact examples. Keep a replay copy of the local SQLite in scratch. The complete index and registered code, seed, inputs, and environment supply the deterministic replay. The measured duration and SQLite file layout can vary across runtimes. [Runnable frozen method](../../independent/README.md) · [Exact data digests and runtime](replay-metadata.json)

Replay the exact discrete optimization using `python formal-checks/independent_optimization.py OFFICIAL_CUSTODY/opening-roster.json FRESH_REPORT_DIR`. Replay the off-roster artifact snapshot using `python tests/independent_control_archive.py EXACT_OFFICIAL_EXPERIMENT_DIR FRESH_REPORT_DIR`. The independent role did not need the other role's private analysis or native raw data. Cross-role compatibility is evaluated against both separately authored public results.
