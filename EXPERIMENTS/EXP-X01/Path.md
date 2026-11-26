# EXP-X01 execution record

## 1. Experiment identification

Exact finite completion recovery, assigned to `exp_x01`. Work plan v1 at parent revision `91c2158877e5440aedafd76a2b16f6bfa389c330`. Theorem packages T01–T04 and T13. Branch `codex/exp-x01` in the private `Perceptive-Closure/PC-X` repository. Phase 1 opened on 2026-11-26 Asia/Karachi.

## 2. Explicit scope declaration

Only the experiment package is writable. The declared fragment consists of explicit finite checkpoints, latent worlds and normalized history values, finite source action and interface identities, statewise authority permissions, positive-support successor/outcome lists, and nonnegative integer action costs. Completion domains are supplied finite catalogs, with no unsupported or unspecified symbolic completions inferred. Evidence constraints are finite equality predicates over source locators and semantic facts. All systems and datasets here are constructed. No native system, prevalence, universal safety or runtime-prevalence inference is in scope.

## 3. Research reconstruction

The charter (pp. 2–9 and 15–16) and original manuscript (pp. 2–5) independently motivate two evaluations. Within a complete contract, the represented fiber of a checkpoint consists of worlds compatible with any history in its current certificate equivalence class. Closure asks whether the sealed target is constant on that fiber. Each source action touches the union of extensional changes to H, the representation equivalence, and authority along all positive-support successors. Atomic freezing removes an entire action for any intersecting touch. An observation-measurable controller groups successors by outcome and observation and has to choose an admissible common action for the surviving belief. Proper closure is finite on every support branch. The same finite belief can recur via different hidden histories, but along a single proper tree path the suffix rooted at the repeated belief can replace the longer prefix at no greater cost under nonnegative costs. This permits independently exhaustive enumeration of cycle-free belief paths even when the physical graph has cycles.

Across contracts, the finite signature set is deduplicated over source-compatible, well-formed, evidence-matching completions. A nonempty singleton supports an identification certificate relative to that catalog. An empty set is inconsistent. A multi-signature result retains witnesses. T01–T03 serve as original foundation claims with bounded constructed checks here. T04 gives the finite target-relative criterion and T13 poses further symbolic and constructive obligations. Exhaustion is the certificate mechanism in this experiment.

## 4. Implementation ledger

| Phase and task | Decision, files and verification | Outcome |
| --- | --- | --- |
| 1.1 Isolate | Clone the verified parent revision from the private organization using the existing GitHub CLI credential helper. Create a dedicated branch and root-owned scratch path. | Isolated checkout at the expected parent revision. |
| 1.2 Freeze protocol | Fix source projection and broad finite domain, experiment factors, two seeds, workload and acceptance before executing any model. See [configs/protocol.json](configs/protocol.json). | Protocol and this ledger are persisted as the first experiment commit. |
| 1.3 Independent verification plan | Main solver will label reachable beliefs from target-homogeneous leaves. The independent algorithm will enumerate costs of admissible observation-measurable proper policy trees with a per-path repeated-belief cut. It rederives representation equivalence, authority, touch and evidence satisfaction directly from the contract fields. | Pending construction. |

| 2.1 Contract and exact label setting | Implement finite extensional coordinates, authority coherence, full positive-support union, reachable belief graph, and reverse minimax label setting in src/model.py. | The solver finalizes a belief only from a goal or an action with finite proof for every successor. |
| 2.2 Independent checker | Implement explicit policy-tree cost enumeration in src/reference.py. Build controller-visible history branches directly from raw source rows and rederive representation equivalence by pair comparisons. Reconstruct the source projection separately during certificate checking. | The checker shares record types only with the optimized evaluator. |
| 2.3 Fixtures and harness | Implement public source-equivalent E/R pairs, an authority gate, zero/positive cyclic controls, mixed-versus-split actions, reachable belief refinement, frozen factorials and seeded strata. Build src/run.py and tests/test_recovery.py. | Prepared for first test and measurement. |
## 5. Experimental execution ledger

The frozen protocol commit is `df82c2ffb97387fb0ac2e00dd53b741bf7e4408c`. The executed evaluator, reference, workload and tests are at `3b7e6fa6cb12c708d624aad18e9ec81174a866ff`. The case generators use deterministic cross-products and Python's pseudorandom generator with seeds 104729 and 130363. Each seed produces 24 cases per stratum across four strata. The 40 factorial and 11 hand-derived contracts supply 408 precomputed coordinate expectations. The larger deterministic generated corpus supplies workload diversity under declared rules. No prospective native measurement or population sampling applies.

Runtime was CPython 3.13.7 on Windows 11 build 26200 with Git 2.49.0.windows.1. No package installations, external inputs or services were used during execution. The source hash for the original manuscript is `f27b6f6e593129592577a0863f46853540b4377ec9393a4f28d48026dd2ebcd4`. The frozen charter hash is in the master work plan.

| Run | Command and environment | Observed result |
| --- | --- | --- |
| First tests | `python -B -m unittest discover -s tests -v` with an isolated scratch directory | 19 tests passed in 0.039 seconds. |
| First experimental execution | `python -B -m src.run --timing --details <scratch>/run-first.json` | 243 complete contracts and 1,378 evidence cases with zero unexplained discrepancies in 1.217 seconds. |
| Traced evidence generation | `PYTHONHASHSEED=17`, `python -B -m src.run --record --timing --memory --details <scratch>/run-traced.json` | Same full evidence hash. 13.761 seconds with allocation tracing, 4,988,953 peak traced Python bytes. |
| Reproduction before publication | `PYTHONHASHSEED=43`, `python -B -m src.run --check --timing` | 1.524 seconds and matching regenerated summary and full evidence digests. |

Each full evidence file was 2,109,235 bytes. All comparisons concern exact integers or explicit structural infinity. Timing, allocation tracing and total file regeneration are reported separately from the measurement of mathematical agreement.

## 6. Falsification and negative results

- The intentionally privileged full-state oracle underestimated the optimum in all six hidden-successor cases with merged observations. Three cases had no supported common closer, and the oracle still returned a finite cost. Three shared-fallback cases had a true cost three units larger. The remaining 12 cases deliberately exposed distinguishing observations or outcomes and showed no discrepancy.
- First-successor-only resource touch incorrectly allowed the atomic action under an R freeze in three of six cases. It returned cost 1 when the correct values were infinity, 4 and 8. Putting the R-touching branch first suppressed that error in the other three cases. The exact evaluator was invariant to support order.
- The zero-cost hopeful loop with a positive-support self outcome required the deterministic fallback costing 4. A zero-cost loop without any exit was structurally unclosable.
- Nine malformed conditions were refused by both reference and optimized paths, including absent checkpoints, invalid authority, missing support or certificate-compatible worlds, negative costs and invalid evidence locators.
- No optimized-versus-exhaustive discrepancies or failed preregistered controls were observed. Confirmatory tests covered exact values on a constructed finite workload.

## 7. Testing and independent verification

All 19 tests passed. They cover the original coordinate order, hand-derived and factorial target values, source projection, representation relabeling, atomic freeze and support union, controller-visible outcomes, hidden-state filtering, target-relative closure, cycles and information-state refinement. They reject malformed contracts and deliberately corrupted verdicts, completion membership, witness values and witness source identities.

The independently written exhaustive tree checker agreed on 1,944 coordinates, verified every one of 1,378 catalog results, and checked every emitted witness. Two byte-equivalent evidence regenerations used different Python hash seeds. The committed digest causes `--check` to fail on any divergence in complete detailed evidence. Clean-checkout repro is recorded separately in section 10.

## 8. Deviations and scope compliance

No frozen factor, seed, comparison, acceptance threshold or estimand was modified after the first run. The single planned split-versus-batched hand control has two explicit contracts, giving 11 hand contracts over 10 planned hand-control scenarios. All cases, intermediate files and runtime storage are owned by this experiment's isolated root. The data are deterministic constructed evidence. Observational prevalence, native deployment performance, arbitrary contract classes and structural scaling are outside the measured claim.

## 9. RESULTS

### Research question and verdict

Can exact finite recovery compute every compatible resource-freezing signature and distinguish inconsistent, identified and ambiguous cases? The hypothesis predicted zero disagreement with exhaustive policy-tree and completion checks on the frozen fragment. The test supported that prediction within the declared fragment.

| Measurement | Outcome |
| --- | --- |
| Distinct finite contract records | 243 at 227 public source descriptions |
| Exhaustive signature-coordinate checks | 1,944 with 0 discrepancies |
| Hand-calculated signature-coordinate checks | 408 with 0 discrepancies |
| Strict freeze nesting checks | 4,617 with 0 violations |
| Exact finite versus structural coordinates | 528 finite, 1,416 structural |
| Evidence cases | 1,147 point-identified, 4 underidentified, 227 inconsistent |
| Point cases admitting more than one completion ID | 47 |
| Strict semantic evidence refinements | 2,306 with 0 set-nesting violations |
| Independently checked representative completions | 1,155 witnesses, 0 invalid |
| Source-equivalent E/R comparison pairs | 16 with identical unrestricted projections |
| Relabeling and anchored comparison pairs | 9 with invariant signatures |
| Deliberate invalid inputs | 9/9 rejected by both paths |

### Contrasts and interpretation

With fallback cost 4, the two source-consistent completions share a public graph, unrestricted optimum 1, available action classes and certificate target classes at corresponding checkpoints. The E-completion signature is `[1, inf, 1, 1, inf, inf, 1, inf]`. The R-completion signature is `[1, 1, 4, 1, inf, 1, 4, inf]`. The no-fallback R-completion changes its R and RA coordinates to infinity. Conditioning on an independently declared H boundary selects a single signature within the catalog. An anchored E variant separately changes the admitted final history while keeping the same signature. Public source behavior alone is ambiguous on all four fallback configurations.

The complete candidate's structural judgments agree with exhaustive observation-measurable synthesis. Invalid privileged planning understated the true value on one third of the hidden-state controls. The first-successor touch ablation failed on half the mixed-action controls. The exact evaluator resolved the open-to-closed target irrespective of world identity when two worlds shared the same sealed decision. It distinguished loss of every strategy from a finite cost increase when an intervention removed the cheap strategy.

### Theorem and claim boundaries

- T01 and T02 receive constructed checks of finite and structural counterfactual divergence despite fixed unrestricted behavior and source observations. Operational prevalence would require separately designed cases.
- T03 receives bounded checks of invariant resource support under extensional relabeling or a pinned alternate history. General interface-equivariant bisimulation and arbitrary semantic anchors lie outside this computational comparison.
- T04 receives finite explicit evidence-set and refinement checks. This experiment targets recovered signature sets and leaves optimal query-set synthesis to subsequent experiments.
- T13 receives independently rechecked explicit finite certificates and disagreement witnesses. Performance in symbolic fragments and completion universes beyond the supplied catalog require additional evidence.

### Acceptance and reproduction

The frozen protocol's zero-mismatch, malformed-input, sound witness, positive and negative control, and nested-refinement criteria passed. Finite exact comparisons use counts and no sampling intervals. Consult [README.md](README.md) for commands and the reusable reference. The durable [results summary](results/summary.json) and [reproduction manifest](results/manifest.json) record the observed counts and full regenerable evidence digest `0e975b0c8b369fab769221cface9eed6865fa066e4ee887e80681fdf8ccec39d`.

## 10. GitHub persistence and cleanup record

Protocol was pushed to `Perceptive-Closure/PC-X`, branch `codex/exp-x01`, at `df82c2ffb97387fb0ac2e00dd53b741bf7e4408c`. The terminal candidate adds the README, results summary and digest manifest to the above implementation. Timings and test details remain in this record. Complete detailed evidence is regenerated by the replay command and checked against the recorded SHA-256. The run produced no external or irreplaceable observations. Source PDFs, temporary logs, scratch evidence copies and temporary checkouts stay out of Git. Remote and clean-checkout verification precede cleanup.

Remote branch head matched the expected terminal evidence candidate `ad6124afbb662e385ecdc695e6fcfa3d58fe3570`. A disposable clean GitHub clone at that SHA passed all 19 tests in 0.040 seconds and regenerated the complete evidence digest in 1.288 seconds with Python hash seed 209. Replacing the manifest's expected evidence hash with 64 zeros produced the expected exit status 1 and the specific manifest discrepancy. The original manifest was restored byte for byte and the verification checkout was clean.

The handoff commit adds these verification observations to Path.md only. The source and checkouts remain under the isolated experiment root for parent review. Parent acceptance, final head verification and workspace cleanup are recorded in the master execution record.
