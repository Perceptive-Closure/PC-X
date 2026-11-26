# EXP-X03 execution record

## 1. Experiment identification

- Experiment EXP-X03, Global and local certificate optimality.
- Assigned experiment agent `exp_x03`.
- Starting revision `91c2158877e5440aedafd76a2b16f6bfa389c330` on `codex/pc-x-orchestration`.
- [Work plan](WorkPlan.md) and [frozen protocol](configs/protocol.json), schema v1. Protocol commit `f5d23f4e8c3ff673c182f7f2ca9366251bba81a9`.
- Theorem packages T04–T07, with finite exact components relevant to T14.
- State RESULTS_DOCUMENTED. Independent local mathematical checks and evidence replay passed. Final remote verification and parent acceptance are tracked in Section 10.

## 2. Scope

The experiment evaluates finite explicit completion tables with categorical semantic answers and positive integer acquisition costs. It covers constructed finite authorization contracts and abstract combinatorial workloads. The implementation assumes a fixed and complete table of admitted completions, a canonical identity for every distinct completion, and deterministic available queries. It runs locally with inert inputs. External-system compatibility, empirical query costs, strategic or noisy audits, and general algorithmic scalability are outside the tested fragment.

## 3. Research reconstruction

Final Theorem Package pp. 7–11 defines evidence-relative target sets, the frozen query interface, disagreement edges, audit inaccessibility, and global and realized weighted optima. A uniform audit separates every target-distinct pair. A realized audit distinguishes a particular admitted completion from target-distinct alternatives in its selected-answer cell. Equal complete-interface answer vectors with different targets witness a limit of every deterministic audit on the interface. Homogeneity gives an empty sufficient query set only for a nonempty compatible domain.

A minimum weight transversal satisfies each edge formed by the differing query answers of a target-distinct pair. The exact algorithm removes redundant supersets and branches over the queries in a smallest outstanding edge. Its verifier independently materializes projected answer cells and enumerates their query subsets. Positive costs ensure that an optimum is inclusion-minimal, while an inclusion-minimal certificate can cost more than the optimum. Charter pp. 15–17 motivates the paired-completion oracle used by later counterexample-guided synthesis. X03 tests explicit components and supplies finite reference evidence for X05.

The structured cases use the original PC coordinates from the Final Theorem Package pp. 2–3. The authorization target maps three latent parcel worlds to approve or deny. The represented history cell initially reaches both labels. A fast or archival operation either admits the verified history under a fixed representation or unaliases the existing admitted history under a refined partition. These effects model distinct source-semantic boundaries on the same candidate action locators. A grant can make a certified E-only closer admissible. The entry license can also already admit that closer. There are eight extensional completions formed by the two operation-boundary choices and the preapproval choice. Touch is computed from coordinate changes and affects all permitted actions. This deterministic fixture has observable states and no hidden-branch optimization.

The constituent audit probes inspect modeled history admission, archival representation semantics, or the independently specified entry license. A joint inspection reads both admission and license facts. These query results do not read closure costs. The combined probe costs 6, separate fast admission and license cost 3 and 4, and archival inspection costs 2. The freeze action costs are 1 for fast, 5 for archive, 2 for grant, and 2 for certified. Acquisition costs are declared units in this fixture. The native acquisition effort of these facts was not measured.

## 4. Implementation ledger

- Phase 1. Read the assigned work plan and charter pp. 7–11 and 15–17. Verified the isolated checkout and base. Froze case counts, query costs, seeded ranges, baseline rules and acceptance gates. The protocol entered GitHub before solver implementation or measurement. Corrected a trailing blank line rejected by Git's whitespace check before the protocol commit.
- Phase 2. Implemented the weighted reduced-edge solver in [certificates.py](src/certificates.py) and an independent direct partition in [reference.py](src/reference.py). Implemented greedy weighted pair coverage, deletion, exhaustive acquisition and random ordering in [baselines.py](src/baselines.py). Added authorization fixtures with extensional touch and an independent direct action-sequence cost calculation in [authorization.py](src/authorization.py).
- Phase 2. Implemented workload generation in [corpus.py](src/corpus.py), verification and evidence serialization in [run.py](run.py), and targeted [tests](tests/test_experiment.py). A pre-execution code review found the drafted correlated fixture's target equal to the XOR query expression. The frozen protocol specified a correlated stratum and the work plan excluded answer-revealing queries. The target implementation was corrected to a sum before any run.
- Phase 3. Ran the full workload, directly checked every supported subset and scope, and replayed artifact serialization byte for byte. Hardened the public verifier to recompute its independent optimum on every call. The hardening changed no scope result and preserved both original artifact hashes.
- Phase 4. Prepared [reproduction commands](README.md) and computed evidence digests for repository persistence. The parent must complete a remote clean-checkout replay before authorizing deletion.

## 5. Experimental execution ledger

| Item | Measured configuration |
| --- | --- |
| Environment | CPython 3.13.7, AMD64 Windows 11 build 26200, standard library |
| Exhaustive distinct profiles | 80 nonempty subsets and target assignments for four binary profiles at each of three weight pairs, 240 domains |
| Exhaustive repeated profiles | Three distinct completion identities, four binary profiles with replacement, two labels each, 512 domains |
| Seeded workload | 24 domains per stratum for binary sparse, categorical, forced identical-answer disagreement, and correlated answers, 96 domains. Seeds 712003–712098 |
| Named controls | 12 constructive or adversarial domains and 5 authorization conditions |
| Comparators | Greedy weighted marginal pair coverage, input-order deletion, full query acquisition, and 16 fixed-seed random orders per scope |
| Commands | `python -B -m unittest discover -s tests -v`, `python -B run.py --write`, `python -B run.py --check` |
| Runtime | Initial generation 1.439 s and byte replay 1.506 s. Replay after verifier hardening 1.654 s on this host |
| Resource measurement | One separate `tracemalloc` replay measured 9,831,233 peak traced Python allocation bytes over 14.536 s with tracing overhead |
| Evidence | `results/scopes.csv` 453,531 bytes and `results/summary.json` 39,239 bytes. [SHA-256 manifest](results/manifest.sha256) |

The workload balances exact coverage of small binary structures with a finite stress set and semantic controls. Per-scope estimates are exact on each included table. Means use every eligible workload scope and carry no sampling inference.

## 6. Falsification and negative results

- Complete-interface equivalence yielded 725 verified impossibility witnesses, including 24 of 24 forced-alias uniform domains. On the localized inaccessibility control, two incompatible completions are indistinguishable and a third completion remains locally identifiable for cost 2.
- Greedy marginal coverage cost 3 against the exact cost 2 in its trap. Input-order deletion retained an inclusion-minimal query of cost 9 when two other queries together cost 4. Exhaustive acquisition and fixed-order random acquisition also exceeded the optimum in the trap conditions.
- Removing the only informative categorical query or giving two conflicting target rows the same categorical answer rendered the respective uniform audit inaccessible. Lowering the cost of the dominating bundled query changed the weighted trap optimum from 4 to 1.
- The contradictory evidence control yielded INCONSISTENT and no certificate. A mutable copy of the scope artifact with appended junk was rejected by `run.py --check --output-dir` with status 1. This expected failure is distinct from the clean evidence.
- No unexplained solver mismatch or invalid reported certificate occurred. The finite tests leave open the performance of exact search on larger arbitrary inputs.

## 7. Testing and independent verification

`python -B -m unittest discover -s tests -v` passed all 12 tests before the workload and after verifier hardening. Tests cover malformed domains, failed-choice witnesses, ties, minimum versus inclusion-minimal cost, hand-computed scopes, and fixed generator counts. Deliberate proof corruption tested fabricated costs, duplicate or invalid query positions and altered witnesses. All were rejected.

The primary workload checked 59,971 query subsets against direct partitions and independently validated 27,297 target-distinct pairs found inside queried answer cells. It checked all 3,828 solver outputs, including 3,102 certificates, 725 complete-interface impossibility witnesses and one inconsistency. Every selected query in each finite optimum was challenged by removing it and validating a resulting conflict. The independent reference tested every cheaper query subset. The structured targets were independently checked for all 64 completion-freeze combinations. The recorded outputs replayed byte-identically.

## 8. Deviations and scope compliance

No post-outcome change to the protocol, target scope, costs, controls, certificate rules, or evidence interpretation occurred. Code review corrected the draft correlated generator before measurement. The later verifier hardening removed an optional externally supplied optimum and left all emitted data unchanged. This experiment's prescribed inputs are constructed, so a held-out native deployment procedure does not apply. All study activity stayed within the isolated repository package and its scratch directory.

## 9. RESULTS

### Executive summary and question

The experiment tested whether a finite weighted semantic audit engine gives sufficient and minimum-cost uniform and realized certificates relative to a frozen completion table. The hypothesis of agreement with an independent exact partition oracle held throughout the supported workload. All 3,828 scope statuses and costs agreed. The test also recovered weighted failure modes for greedy and inclusion-minimal deletion and found a distinct semantic cost for full contract identification.

### Scope outcomes

| Scope | Examined | Finite optimum | Audit inaccessible | Inconsistent | Multiple finite optima |
| --- | ---: | ---: | ---: | ---: | ---: |
| Uniform | 865 | 645 | 219 | 1 | 14 |
| Realized | 2,963 | 2,457 | 506 | 0 | 98 |
| Total | 3,828 | 3,102 | 725 | 1 | 112 |

A one-hot-answer control had uniform optimum 2 and every realized optimum 1. There were 12 domains with a finite uniform optimum strictly greater than the worst realized optimum. In 180 tested uniform scopes a target certificate existed even though full contract identification was inaccessible. Among the 465 finite uniform scopes with finite full contract cost, the target was strictly cheaper in 287.

### Comparator costs

Means and excess counts below use the same feasible scopes for every comparator. Available queries and declared costs are held fixed. Random reports a per-scope mean over 16 permutations.

| Method | Uniform mean cost, 645 scopes | Uniform above exact | Realized mean cost, 2,457 scopes | Realized above exact |
| --- | ---: | ---: | ---: | ---: |
| Exact | 2.131783 | 0 | 2.439967 | 0 |
| Greedy coverage | 2.207752 | 33 | 2.560033 | 178 |
| Inclusion-minimal deletion | 2.412403 | 61 | 3.208791 | 587 |
| Full acquisition | 6.262016 | 543 | 10.004070 | 2,336 |
| Random order | 3.095446 | 315 | 4.607397 | 1,707 |

All comparators used independent partition checking for sufficiency and abstained on all inaccessible and inconsistent scopes. Attempt costs for inaccessible scopes averaged 9.383562 uniform and 10.247036 realized. Those attempts are excluded from finite optimum gaps. The largest observed uniform greedy excess was 6 and deletion excess was 16.

### Structured authorization controls

| Evidence and target | Admitted completions | Uniform cost | Realized cost range | Full contract cost |
| --- | ---: | --- | --- | --- |
| Full grid, R-freeze cost | 8 | 6 | 3–6 | 8 |
| Full grid, full freeze signature | 8 | 8 | 5–8 | 8 |
| Correlated boundaries, R-freeze cost | 4 | 6 | 2–6 | 6 |
| Fast admission probes removed, R-freeze cost | 8 | Inaccessible | Inaccessible for all 8 | Inaccessible |
| Fast action known E-only, R-freeze cost | 4 | 0 | 0 for all 4 | 6 |

The full-grid R-freeze cost set is `{1,2,4}`. The combined inspection of fast admission and entry license sufficed at cost 6. Greedy acquisition reached cost 9. The archive boundary changes the full freeze signature for some admissible pairs. Archival inspection alone leaves all three R-freeze costs possible in the full grid. The full signature and full contract needed the archival inspection for uniform sufficiency at total cost 8. The correlated constraint made archival inspection informative about fast admission and produced two tied uniform minima. Removing both probes that can observe fast admission produced the witness `E/R/1` and `R/R/1`, with equal available answers and frozen-R costs 1 and 2 respectively. In the E-only condition, the cost-1 fast closer survives the R freeze throughout the remaining evidence set without a new query.

### Acceptance and theorem implications

- **Correctness and validity passed.** Direct projected partitions agreed exactly with all candidate statuses, selected minima and subset characterizations.
- **Falsification and baseline comparison passed.** The named structural counterexamples, perturbations, forged proofs, illegal inputs and changed artifact all behaved as preregistered. All comparators used the same available answers and cost model.
- **Results completeness passed.** Every preregistered domain and its realized scopes are in the CSV, with deterministic aggregate metrics and evidence hashes. Parent clean-checkout review is the remaining lifecycle gate.
- **Scientific verdict.** This is finite empirical support for the T04 characterization, T05 interface impossibility, T06 weighted minima, and a bounded structured T07 separation. It independently checks components relevant to T14's conditional algorithm. It leaves symbolic scalability, asymptotic separation, source completeness for external engines, and deployment claims open.

Use the two reproduction commands in [README.md](README.md). The complete measurements are [scopes.csv](results/scopes.csv) and [summary.json](results/summary.json).

## 10. GitHub persistence and cleanup record

Repository [Perceptive-Closure/PC-X](https://github.com/Perceptive-Closure/PC-X), branch `codex/exp-x03`. The protocol commit was pushed before execution. The candidate includes the versioned protocol, solver, independent oracle, baselines, fixtures, runner, tests, README, execution record and deterministic evidence manifest. Scratch corruption copies, Python cache, PDF sources and isolated checkout metadata are excluded. All experiment inputs and evidence replay from the frozen manifest. Independent remote replay, exact remote commit verification and authorized cleanup are pending.
