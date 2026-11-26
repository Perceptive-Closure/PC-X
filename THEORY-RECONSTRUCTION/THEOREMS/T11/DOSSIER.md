# T11 · Exact nonrectangular partial identification

## Original charter entry

Charter §13, pp. 13–14 extends D-35 Proposition 3 from independent R-touch bounds to correlated exact target sets and extrema.

## Candidate statement and dependencies

For every nonempty compatible mask-profile family sharing a finite positive-support kernel, the exact projection is the image of compatible masks under budget-freeze evaluation. Intersections/unions give outer bounds and may be strict. Profile image finite implies attainment. An exact finite belief-horizon procedure and optional label-setting evaluation recover each value.

Finite typed resource kernel, outcome aliasing, known state-independent action costs, nonnegative cost, frozen source support and termination, and correct semantic masks. For computation over an implicit family, exact decidability of mask membership is additionally required.

The quantified typed construction is in the [statement packet](../../WORKSTREAMS/exact/STATEMENTS.md). The complete constructor argument is in [Proof](PROOF.md). Explicit failure cases are preserved in [Counterexamples](COUNTEREXAMPLES.md).

## Evidence and novelty

X02 tests 94 inputs and 249 compatible completions, with narrower exact intervals and 58 marginal-product overcoverage cases. X01 verifies support blocking on all eight freeze coordinates and X05 verifies exact cost projections in a separate serial fragment. [Exact experiment reconstruction](../../WORKSTREAMS/exact/EVIDENCE.md)

The monotone bounds extend D-35's elementary rectangular comparison. The sharp image and finite horizon protect correlations and proper observation-based reachability. Knowledge-state methods have prior art. [Primary references](../../WORKSTREAMS/exact/PRIMARY-SOURCES.md)

## Status at constructor handoff

| Dimension | Status |
| --- | --- |
| Mathematical | PROOF_CANDIDATE |
| Novelty | ADAPTATION |
| Experimental | EXPERIMENTALLY_SUPPORTED |
| Integration | PENDING |

The proof-blind derivation and hostile review are tracked in [Verification](VERIFICATION.md).
