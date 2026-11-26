# T08 · Exact adaptive semantic audit complexity

## Original charter entry

Charter §10, pp. 11–12 asks for an exact worst-case adaptive recurrence with posterior answer cells.

## Candidate statement and dependencies

At each nonempty homogeneous cell the minimax continuation costs zero. At a mixed cell minimize price plus the largest attainable child value over splitting probes. Values are infinite when no proper distinguishing policy exists. A product of independent tuple-target tasks with disjoint menus has additive static, worst-case adaptive and actual realized optima.

Read-only deterministic menu, fixed positive prices, finite compatible domain and output on all admitted completions. T05 supplies interface-obstruction handling. The product extension additionally requires independent domains, disjoint menus, additive prices and a tuple target.

The quantified typed construction is in the [statement packet](../../WORKSTREAMS/exact/STATEMENTS.md). The complete constructor argument is in [Proof](PROOF.md). Explicit failure cases are preserved in [Counterexamples](COUNTEREXAMPLES.md).

## Evidence and novelty

X04 exact replay on 88 cases independently checks 21,062 policy paths. The tuple extension is demonstrated by a standalone finite product control rather than an original matched factorial experiment. [Exact experiment reconstruction](../../WORKSTREAMS/exact/EVIDENCE.md)

The cell recurrence is deterministic decision-tree dynamic programming. Exact direct sums of independent query tasks are prior. The weighted adaptation makes the assumptions explicit. [Primary references](../../WORKSTREAMS/exact/PRIMARY-SOURCES.md)

## Status at constructor handoff

| Dimension | Status |
| --- | --- |
| Mathematical | PROOF_CANDIDATE |
| Novelty | ADAPTATION |
| Experimental | PARTIALLY_SUPPORTED |
| Integration | PENDING |

The proof-blind derivation and hostile review are tracked in [Verification](VERIFICATION.md).
