# EXP-X08 execution record

## 1. Experiment identification

EXP-X08 — Evaluation-equivalent AI agents. Assigned agent exp_x08. Parent custodian /root. Initial checkout `91c2158877e5440aedafd76a2b16f6bfa389c330`. [Work plan](WorkPlan.md), [protocol v1](Protocol.md), [parameters](configs/protocol.json). Relevant packages T15–T17, the finite T19 threshold formulation and the T21 indistinguishability bound. State `REPRODUCIBILITY_VERIFIED`.

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

The parent verified remote forecast `ce5f10b0ff0e5d549eecf7cbd8c08a88ccae809e` at 17:58:45 Asia/Karachi and ran the unchanged custodian program on the sealed configuration. The opening confirmed the assignment hash and recorded 4,096 floor and 4,096 descriptive benchmark episodes. Original results used CPython 3.13.7 on Windows. The author recomputed all exact checks and regenerated 8,192 raw observation rows, identical to the independently produced raw SHA-256. The [opening record](results/opening.json) contains the seed, nonce, timestamp and actual fixture. The committed data need no external service or paid access to replay.

## 6. Falsification and negative results

The early floor-cue control yielded total variation 1/2. The independently logged fair bit control preserved exact law equivalence. Omitting route calibration left the synthetic audit interface inaccessible. The dev-only test rejected corrupt counts, altered commitment preimages and malformed or incomplete runtime evidence. The benchmark-only rule falsely predicted one unit met the floor threshold. Both preregistered primary forecasts were confirmed.

## 7. Testing and independent verification

Python 3.13.7 `-B -m unittest discover -s tests -v` passed 7/7 tests. Exact rational law, risk and witness checks passed. A separately defined development seed exercised the trusted logger and threshold-analysis stages. The separate parent runner verified original custody chronology and source revision. The author replay checked the original outcome commitment and full raw SHA-256. The parent independently cloned evidence commit `6f17f4cd603199a76beda5c8db105806c2727844` from GitHub, passed 7/7 tests, reproduced the full raw hash, and verified the forecast ancestry. The parent separately verified every native retry against its facility ticket and recomputed all 8,192 episode outcomes and simultaneous bounds.

## 8. Deviations and scope compliance

No deviation from the work plan at freeze. The target is the pair of unit verdicts under known joint enrollment, plus per-cell risk bands.

## 9. RESULTS

### Question and verdict

For the frozen three-round parcel-routing sandbox, does the complete permitted interactive benchmark law identify which unit meets a 40% limit on the risk of at least two retries? Does independent, minimum-cost calibration resolve the ambiguity? The finite identification hypothesis and preregistered prospective validation both passed. This result supports conditional recovery in the eight admitted joint completions.

### Design and exact findings

The experiment held the controller implementation, benchmark observation, permitted requests and observed lane/retry histories fixed. The deployed profile assignment and feeder operating mode varied within the declared source class. Two valid completions with opposite installed profile assignments and matched fast feeders had the target vectors (meets, above) and (above, meets). Their exact benchmark transcript laws agree for arbitrary, possibly randomized evaluators and early stopping within the three-round interface. The history enumeration covered 73 histories and 146 next-request conditionals per fixture. It compared the conditional law at each reached history with an independent enumeration of actual runner tickets for 584 benchmark and 464 floor laws. The result establishes equality by partitioned conditional laws, including reachable history support. It also permits equal-law repeated benchmark episodes under the prescribed resets.

A separate close-form-style state recursion marginalizing lane and a full visible-path enumeration agreed on all exact risks. Percentages below are exact-model probabilities rounded for display.

| Profile | Feeder | Mixed-normal | Mixed-rush | Maximum | Threshold verdict |
| --- | --- | ---: | ---: | ---: | --- |
| Careful | Fast | 8.51% | 12.33% | 12.33% | Meets |
| Careful | Slow | 22.59% | 27.58% | 27.58% | Meets |
| Throughput | Fast | 58.94% | 64.52% | 64.52% | Above |
| Throughput | Slow | 76.53% | 81.52% | 81.52% | Above |

The initial benchmark identified set for the joint threshold was {(meets, above), (above, meets)}. The costs were fixed before opening. The minimum uniform audit cost was 2, confirmed by exhaustive direct partitions and independently by all pair disagreement transversals. Exactly 48 of 64 subsets were sufficient. The tie-break selects the parcel-A floor-cue routing calibration. Exhaustive acquisition cost 8. Cheapest-first (same stopping rule) cost 6. In the 256 random orderings fixed by seed 808, the mean was 3.33594 and the range was 2–6. The conventional benchmark-only forecast extrapolated the maximum benchmark model risk of 11.17% and declared both units met the threshold.

### Prospective validation

The independent parent measured one manual-lane choice out of eight fixed action tickets for parcel-A using a fresh rush request and physical floor observation, with no delivery transition. Admission of that receipt reduced the source class from eight to four joint completions, fixing the two threshold decisions while leaving both feeder choices for each unit. The forecaster committed the resulting exact recipe-level bands before the custodian opened the concealed intervention. At opening both feeders were fast.

| Unit | Recipe | Benchmark retries ≥2 | Floor retries ≥2 | Floor risk | Simultaneous 95% interval | Sealed floor risk band |
| --- | --- | ---: | ---: | ---: | --- | --- |
| Parcel-A | Mixed-normal | 125/1,024 | 579/1,024 | 56.54% | 51.56%–61.52% | 58.94%–76.53% |
| Parcel-A | Mixed-rush | 115/1,024 | 651/1,024 | 63.57% | 58.60%–68.55% | 64.52%–81.52% |
| Parcel-B | Mixed-normal | 113/1,024 | 101/1,024 | 9.86% | 4.89%–14.84% | 8.51%–22.59% |
| Parcel-B | Mixed-rush | 121/1,024 | 128/1,024 | 12.50% | 7.52%–17.48% | 12.33%–27.58% |

The maximum measured risk was 63.57% for A and 12.50% for B. The measured difference was 51.07 percentage points, with a simultaneous interval of 41.12–61.03 points derived from the respective maximum-risk envelopes. The results confirm both prospectively sealed decisions, and all four floor intervals intersected their bands. The benchmark-only baseline correctly forecast one of two units and falsely certified the throughput unit. The eight cohorts were complete and no episodes were replaced. The benchmark cohort proportions are descriptive.

### Controls and falsification

Giving the evaluator the floor context in the prespecified positive control yielded exact total variation 1/2 on the fresh-rush law. An independently logged fair bit preserved equivalence with total variation zero. Removing all route calibration leaves the target audit-inaccessible, and removing the known enrollment parity after the chosen query leaves the other unit's threshold unidentified. The corrupt count, altered commitment, missing logger record and forged episode index checks refused the corresponding invalid inputs. The intentionally optimistic benchmark extrapolation disagreed with native floor results. There were no unexplained numerical discrepancies or other failed primary controls.

### Acceptance and limits

- **Exact equivalence and valid disagreement witness.** Passed across every authorized reachable history and request. The two exact implementations agreed, and the positive control breaks equivalence.
- **Different deployment risk on either side of 40%.** Passed throughout the declared class. The minimum exact distance from the threshold was 12.42 percentage points.
- **Legitimate sufficient audit.** Passed. The audit executed action calibration without delivery and the mathematically independent partition and pair checks agreed on the minimum. The conclusion about the unmeasured second unit uses the frozen enrollment parity.
- **Chronologically sealed independent outcomes.** Passed. The parent verified the prediction from GitHub in a separate clean clone of the fixed pre-audit runner, then generated the floor and descriptive benchmark observations. The agents shared a filesystem. The separation is by role and recorded execution order with a SHA-256 commitment.
- **Outcome verification.** Both forecasts confirmed using the preregistered simultaneous intervals. The conventional baseline supplied one false certification. Exact author replay reproduced every observation digest and aggregate. Parent terminal clean-checkout acceptance is recorded in the master ledger.
- **Claim boundary.** T15 and T17's indistinguishability and sufficiency implications are illustrated on this local finite class. The shared but incompletely instantiated implementation supplies a bounded witness relevant to T16. T21's zero-total-variation case gives the usual worst-case decision error bound of one-half for the benchmark-only binary distinction. The risk band example is compatible with T19 threshold identification. The evidence is an executed virtual environment, with confidence conditional on pseudorandom draws modeling independent tickets and resets. It supplies no evidence about the prevalence of evaluation equivalence, external agents or facilities, adversarial audit guarantees, or transport beyond the two prescribed deployment recipes.

Reproduce with the test and replay commands in [README.md](README.md). See [pre-audit model checks](results/pre-audit.json), [independent receipt](results/audit-receipt.json), [sealed forecast](results/forecast.json), [held-out opening and observed results](results/opening.json) and [evidence manifest](results/manifest.json). The recorded raw 8,192-episode stream was independently hashed as `72a5ce71dd8f654ffbf9dacc5938352cef7fe45783fa16aa5a87bbc9cddc925f` and regenerates byte-for-byte with the pinned runner and disclosed seed.

## 10. GitHub persistence and cleanup record

Repository `Perceptive-Closure/PC-X`. Branch `codex/exp-x08`. Protocol freeze `100cddd656a94e7ebdc3341df13b857c3ff030f4`, pre-audit runner `52a04c5d65c196892d4c888e2a5e8b82d07d4fbf`, and forecast seal `ce5f10b0ff0e5d549eecf7cbd8c08a88ccae809e` were individually pushed and verified. The final package includes its protocol, source, tests, exact enumeration, receipt, forecast, opening and evidence manifest. The essential held-out records are committed. Raw deterministic outputs and development/reproduction scratch files regenerate from the pinned package. The parent accepted the reproduced evidence SHA `6f17f4cd603199a76beda5c8db105806c2727844` and authorized cleanup after verification of this Path-only handoff commit. The master Path records the final remote tip and independent local cleanup verification.
