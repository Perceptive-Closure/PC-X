# T10 · Computational hardness and tractability

## Final disposition

`RESTRICTED_RESULT` · `POTENTIAL_STRENGTHENING` · `OUTSIDE_EXPERIMENTAL_SCOPE` · `ACCEPTED_AS_NEW_RESULT`.

[Verification and accepted scope](VERIFICATION.md) · [Full status ledger](../../THEOREM-STATUS-LEDGER.md)

## Original charter entry

Charter §12, p. 13 requests generic static hardness, meaningful PC-specific encodings, and exact structural tractability.

## Candidate statement and dependencies

T10.a is NP-complete static union-of-differences certificate decision for a tabulated finite Boolean class, including a one-step canonical PC family. T10.b is NP-complete selected-probe pair feasibility for binary-encoded serial additive budgets with two local modes and fully observed deterministic protected routes. T14.b–c give precise local-width/budget upper bounds.

T04, explicitly listed compatible assignments for T10.a; separately T14.b-style independent serial scores with read-only local probes for T10.b. The latter's input numbers use binary encoding. No arbitrary succinct full-identity equivalence algorithm is assumed.

The quantified typed construction is in the [statement packet](../../WORKSTREAMS/exact/STATEMENTS.md). The complete constructor argument is in [Proof](PROOF.md). Explicit failure cases are preserved in [Counterexamples](COUNTEREXAMPLES.md).

## Evidence and novelty

X03 verifies finite static solutions, and X05 tests restricted serial computation. Neither establishes hardness or absence of hardness from timing. The code verifies finite instances of both mathematical reductions. [Exact experiment reconstruction](../../WORKSTREAMS/exact/EVIDENCE.md)

Weighted set cover, SUBSET SUM, and multiple decision-tree hardness results are prior. The embeddings derive their promised resource costs from shared checkpoint semantics. The paired-oracle limit is a useful consequence for this encoding. [Primary references](../../WORKSTREAMS/exact/PRIMARY-SOURCES.md)

## Status at constructor handoff

| Dimension | Status |
| --- | --- |
| Mathematical | PROOF_CANDIDATE |
| Novelty | ADAPTATION |
| Experimental | OUTSIDE_EXPERIMENTAL_SCOPE |
| Integration | PENDING |

The proof-blind derivation and hostile review are tracked in [Verification](VERIFICATION.md).
