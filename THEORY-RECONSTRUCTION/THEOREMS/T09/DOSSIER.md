# T09 · Static–adaptive acquisition separation

## Original charter entry

Charter §11, pp. 12–13 gives the realized/optimal adaptive/static inequalities and the unbounded generic bit-address example.

## Candidate statement and dependencies

The largest realized cost is at most worst-case adaptive cost, which is at most static uniform cost. Both gaps can be strict together. In a canonical routed PC family with r address bits and 2^r independent site gate facts, the independently grounded unit-price readouts have adaptive optimum r+1 and static optimum r+2^r.

T06–T08, read-only pretarget probes, independent route and gate facts, ordinary route selection and a measured R-frozen short-path budget. The lower bound requires a feasible parity data vector with every address alternative.

The quantified typed construction is in the [statement packet](../../WORKSTREAMS/exact/STATEMENTS.md). The complete constructor argument is in [Proof](PROOF.md). Explicit failure cases are preserved in [Counterexamples](COUNTEREXAMPLES.md).

## Evidence and novelty

X04 explicitly measured bit-address widths 1 and 2 and routed cases of up to five directly dispatched sites. Larger original address values are analytical. The new equivalent bit-address canonical family is separately constructed. [Exact experiment reconstruction](../../WORKSTREAMS/exact/EVIDENCE.md)

The Boolean address problem and hierarchy are known. The substantive PC addition is an atomic, source-licensed route with a fixed physical E/R threshold and a proven tight acquisition cost under its menu. [Primary references](../../WORKSTREAMS/exact/PRIMARY-SOURCES.md)

## Status at constructor handoff

| Dimension | Status |
| --- | --- |
| Mathematical | PROOF_CANDIDATE |
| Novelty | ADAPTATION |
| Experimental | PARTIALLY_SUPPORTED |
| Integration | PENDING |

The proof-blind derivation and hostile review are tracked in [Verification](VERIFICATION.md).
