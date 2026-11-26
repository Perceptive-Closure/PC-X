# T05 · Audit-interface impossibility

## Original charter entry

Charter §7, p. 9 rules out uniform static or adaptive identification when an opposite-target pair agrees on every available probe.

## Candidate statement and dependencies

In any nonempty table, absence of such an agreement pair is necessary and sufficient for a successful proper uniform audit, including any deterministic adaptive audit. Coupling internal random choices gives the same obstruction against zero-error randomized auditing.

T04 and a fixed complete observation/price menu. Repeat measurements are identical, no actions mutate the completion, and no additional stochastic transcript observation is silently available.

The quantified typed construction is in the [statement packet](../../WORKSTREAMS/exact/STATEMENTS.md). The complete constructor argument is in [Proof](PROOF.md). Explicit failure cases are preserved in [Counterexamples](COUNTEREXAMPLES.md).

## Evidence and novelty

X03 and X04 retained 725 and 40 verified whole-interface collisions respectively. The X06 no-audit baseline abstains on every protected unit, and two X04 routed probe-ablation classes lose access. [Exact experiment reconstruction](../../WORKSTREAMS/exact/EVIDENCE.md)

Deterministic observational indistinguishability is standard and appears in equivalence-class and decision-region work. [Primary references](../../WORKSTREAMS/exact/PRIMARY-SOURCES.md)

## Status at constructor handoff

| Dimension | Status |
| --- | --- |
| Mathematical | PROOF_CANDIDATE |
| Novelty | KNOWN_PRIOR_RESULT |
| Experimental | EXPERIMENTALLY_SUPPORTED |
| Integration | PENDING |

The proof-blind derivation and hostile review are tracked in [Verification](VERIFICATION.md).
