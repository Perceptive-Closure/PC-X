# T14 · Counterexample-guided minimum audit synthesis

## Original charter entry

Charter §16, pp. 16–17 proposes iterative minimum hitting set with paired counterexamples and asks for compact PC-specific pair generation.

## Candidate statement and dependencies

T14.a is exact proof-producing implicit transversal synthesis. T14.b proves the serial stage-crossing decomposition, local cost addition, and a capped Pareto oracle with lower bounds, upper bounds and reconstructed witnesses. T14.c proves paired feasibility via a supplied bounded-width correlated evidence decomposition, with duplicated local modes and saturated left/right resource sums.

T04–T06, T11, T13 and a checked exact optimizer. T14.b additionally needs product compatibility, per-stage local readouts, additive source values and a matching fresh entry after every required stage. T14.c needs explicit relation tables, additive verified scores, local readouts and supplied finite decomposition. All cost cap claims assume nonnegative integer scores.

The quantified typed construction is in the [statement packet](../../WORKSTREAMS/exact/STATEMENTS.md). The complete constructor argument is in [Proof](PROOF.md). Explicit failure cases are preserved in [Counterexamples](COUNTEREXAMPLES.md).

## Evidence and novelty

X05's 70-case accepted scope verifies local threshold crossings, 6,446 paired witnesses and 125 symbolic no-conflict checks. Its matched largest target/full-identity tie is 677 each. The bounded-width extension has only theorem-adjacent finite controls and no matching experiment. [Exact experiment reconstruction](../../WORKSTREAMS/exact/EVIDENCE.md)

Implicit hitting set and width-based elimination are known. The exact statements link the counterexamples and numeric complexity to a declared resource-closure source, beyond toy query predicates. Substantial novelty awaits broader primary-source review. [Primary references](../../WORKSTREAMS/exact/PRIMARY-SOURCES.md)

## Status at constructor handoff

| Dimension | Status |
| --- | --- |
| Mathematical | PROOF_CANDIDATE |
| Novelty | POTENTIAL_STRENGTHENING |
| Experimental | PARTIALLY_SUPPORTED |
| Integration | PENDING |

The proof-blind derivation and hostile review are tracked in [Verification](VERIFICATION.md).
