# T13 verification record

## Constructor checks

Verifier must separately check feasibility, witness membership and evaluation, exact refutation and correctness of status. No unmeasured verification is claimed.

The deterministic finite challenge script is [check_candidates.py](../../WORKSTREAMS/exact/check_candidates.py). Matching a finite challenge is auxiliary evidence. The hash-pinned sources and retrospective experiment links are in [EVIDENCE.md](../../WORKSTREAMS/exact/EVIDENCE.md).

## Independent proof and hostile review

A distinct reviewer should first record a fresh derivation of the sealed [statement packet](../../WORKSTREAMS/exact/STATEMENTS.md), then check the [proof packet](../../WORKSTREAMS/exact/CONSTRUCTIVE-PROOFS.md) and challenge the premises using [Counterexamples](COUNTEREXAMPLES.md). The parent records independent decisions. This constructor commits a candidate only.
