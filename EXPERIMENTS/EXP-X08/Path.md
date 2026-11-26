# EXP-X08 execution record

## 1. Experiment identification

EXP-X08 — Evaluation-equivalent AI agents. Assigned agent exp_x08. Parent custodian /root. Initial checkout `91c2158877e5440aedafd76a2b16f6bfa389c330`. [Work plan](WorkPlan.md), [protocol v1](Protocol.md), [parameters](configs/protocol.json). Relevant packages T15–T17, the finite T19 threshold formulation and the T21 indistinguishability bound. State `FORECAST_SEALED`.

## 2. Explicit scope declaration

Use only the local, inert virtual parcel-routing sandbox and the isolated experiment folder. Files under this experiment subtree may change. No external APIs, infrastructure access, actual security bypasses or paid services. A physical-context observation can change the policy decision, and the floor feeder can change delivery behavior. Candidate models, interface boundaries and the trusted label are declared before execution. The result is about this finite source class and its admitted calibration procedure.

## 3. Research reconstruction

Charter pp. 18–26 give deployment relative threshold risk, evaluation-law equivalence, implementation-relative ambiguity, target sufficiency and statistical indistinguishability. The shared implementation alone does not establish installed policy and feeder semantics. Two target-distinct joint completions agreeing on all authorized adaptive benchmark transcripts yield a counterexample to evaluation-only threshold identification. Independent routing calibration is an action-level propensity measurement. Conditioning on its result can leave feeder ambiguity while identifying the threshold. Chapter 38, pp. 35–36, requires prospective commitment before the measured held-out outcome opens.

## 4. Implementation ledger

- Phase 1, 2026-11-26. Read the experiment work plan and master plan, plus all specified charter pages. Verified the starting GitHub revision. Wrote the frozen parameter file and protocol design. Scope, sample rule, baseline, interventions and controls were recorded before implementation and execution.

- Phase 2. Built `src/model.py` for full-support laws, direct conditioning and weighted audit optimization. Implemented an independently enumerated ticket-law verifier and interactive runtime in `src/sandbox.py`. `src/pipeline.py` provides receipt validation, sealed forecasting, trusted measurement and deterministic replay. No external dependencies were introduced. The random comparator uses 256 orderings with seed 808, fixed before analysis. Scope and primary sample parameters remain as frozen.

## 5. Experimental execution ledger

Ran `python -B src/x08.py exact --output results/pre-audit.json`. It compared all four fixtures, 73 permitted histories and 146 history/request pairs per benchmark fixture. The independent runtime was checked on 584 benchmark and 464 floor history/request laws. The two exact risk calculations agreed on all 8 fixture/recipe risks per site. Two source-compatible witnesses have opposite threshold vectors. An independent exhaustive pair-disagreement computation checks the minimum cost 2 route calibration. Benchmark-only risk concludes both pass. Random-order cost counts are preserved in the pre-audit result. The configured holdout interval half-width is 0.049781. The minimum exact threshold clearance is 0.124213.

The parent independently checked out GitHub revision `52a04c5d65c196892d4c888e2a5e8b82d07d4fbf` and ran the selected action-only measurement. The receipt measured 1 manual choice across the eight tickets on parcel-A at 12:57:25 UTC (17:57:25 Asia/Karachi), independently of delivery. The concealed fixture commitment is `28097faa180957fde1494472c79acfb6f623f3c08754a6d1fb7735e716051460`. The protocol ran `python -B src/x08.py predict --receipt results/audit-receipt.json --output results/forecast.json`, conditioned on the answer and preserved the four compatible feeder assignments. The prediction for parcel-A is above threshold, and for parcel-B it meets the threshold. Exact forecast bands are in `results/forecast.json`. Removing enrollment parity leaves the second unit unclassified. This commit seals the forecast before any held-out episodes open.

## 6. Falsification and negative results

The early floor-cue control yielded total variation 1/2. The independently logged fair bit control preserved exact law equivalence. Omitting route calibration left the synthetic audit interface inaccessible. The dev-only test rejected corrupt counts, altered commitment preimages and malformed or incomplete runtime evidence. Held-out outcome analysis remains pending.

## 7. Testing and independent verification

Python 3.13.7 `-B -m unittest discover -s tests -v` passed 7/7 tests. Exact rational law, risk and witness checks passed. A separately defined development seed exercised the trusted logger and threshold-analysis stages. Clean-checkout replay and original held-out custody verification remain pending.

## 8. Deviations and scope compliance

No deviation from the work plan at freeze. The target is the pair of unit verdicts under known joint enrollment, plus per-cell risk bands.

## 9. RESULTS

Pending execution and verification.

## 10. GitHub persistence and cleanup record

Repository `Perceptive-Closure/PC-X`. Branch `codex/exp-x08`. Final package, clean-checkout review and local cleanup are pending.
