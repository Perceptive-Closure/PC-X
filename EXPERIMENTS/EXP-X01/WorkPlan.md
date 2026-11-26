# EXP-X01 — Exact finite completion recovery

## A. Scientific objective

Does a finite engine recover the exact set of compatible Perceptive Closure signatures, including distinct values and evidence-inconsistent cases? Test T01–T04 and the finite branch of T13, including the limits of observation versus certificate identification. The hypothesis is agreement with exhaustive reference results for every supported case. Agreement supports implementation correctness on the declared fragment. It supplies no general proof, complexity bound or native-system claim.

## B. Scope

Use `EXPERIMENTS/EXP-X01/` for code, tests, configs, docs and results. Use finite explicit source-atomic contracts with integral nonnegative costs and reachable certificate fibers. Respect source IDs, authority admissibility and controller-visible observations and outcomes. Constructed instances are legitimate for this experiment. Declare any unsupported semantics explicitly. Use Python 3.13 and the standard library or justify a pinned dependency. No external systems or paid services.

## C. Mathematical specification

For contract C, evaluate target homogeneity on worlds compatible with the extensional equivalence class of H(s) under PR(s). Derive E/R/A touch through the union of coordinate differences over positive-support successors. Use the freeze order empty, E, R, A, ER, EA, RA, ERA. Each observation-measurable proper finite tree closes all its supported leaves. Under hidden states, a policy chooses a common admissible action on each belief and observes the next (outcome class, observation), never the underlying state. Terminal stopping requires all belief states closed. Positive support, rather than probability-weighted cost, governs the adversarial branch maximum. Preserve explicit infinity and distinguish it from computation failure.

Use at least one shared finite source graph whose alternatives preserve source-visible facts but alter extensional evidence versus representation boundaries. Include atomically mixed actions, renaming invariance, hidden successors with merged or split observations, authority gates, dead ends and cycles or a clearly narrower acyclic fragment with unsupported-cycle refusal. Map explicit evidence predicates to compatible completions. Empty, one-signature/multiple-contract and multiple-signature cases must be distinct, and witnesses must independently satisfy the evidence.

## D. Methodology

Freeze enumeration ranges and random seeds before the suite runs. Use exhaustive cross-products for small meaningful factors, seeded generated contracts across several strata, and hand-specified control cases. Compare the main evaluation to independently structured exhaustive observation-measurable policy trees on the tractable range. Check all eight freeze coordinates, nested evidence refinement and resource-freeze monotonicity. Include an oracle that reads hidden state as a negative control, and a representative-only touch ablation. Run intentional invalid data tests. Report counts, mismatches, runtime, extent of coverage, limitations and exact hand-derived signatures.

## E. Implementation

Provide a well-formed finite model and contract/completion engine, independently written reference, deterministic corpus generator, test suite, environment/version details, run and analysis commands, raw or regenerable evidence and hashes for retained outputs. Document how X02 and X05 can import or independently check compatible finite fixtures without assuming the engine's verdict.

## F. Acceptance

Require zero unexplained supported-case discrepancies across all coordinates and evidence-refined target sets. Validate every emitted witness by a separate check. Require identification only after nonemptiness and agreement, and reject every intentionally malformed case. Show controls that would fail under hidden-state or partial-touch assumptions. Report any failing hypothesis as such even if the package reproduces.

## G. Execution phases

| Phase | Work and output | Acceptance and verification |
| --- | --- | --- |
| 1 | Freeze fragment, source constraints, controls, generator and canonical target encoding | Document charter pp. 2–9 and 15–16 and original PC pp. 2–5. Check belief information and finite horizon or cycle treatment. |
| 2 | Implement evaluator, independent exhaustive reference and fixture validators | Hand-check available actions and all touch/closure properties on the controls. Test negative inputs and hidden-state ablation. |
| 3 | Run complete planned corpus and aggregate results | Retain configuration, counts, full signatures or regeneration hashes, time and all discrepancies. Test evidence refinement monotonicity. |
| 4 | Publish results and evidence manifest | Reproduce commands from a clean GitHub checkout, document claim boundaries and release the workspace only after parent verification. |
