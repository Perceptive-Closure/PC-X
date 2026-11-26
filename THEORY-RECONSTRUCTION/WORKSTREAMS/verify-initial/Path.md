# Independent verifier path

## Record of intake

- Role: independent proof-blind verifier of D-35 Theorems 1–3, P1–P7 and PC-X T01–T14, including each sealed subclaim.
- Branch: `codex/pcx-math-verify-initial`, based at `532762acb07f0a2a2b2d8fb59dfff9c709b97420`.
- Foundation intake blob: `45f78196b7de89462075d54ae98b5867577005d6`. It equals the foundation statement blob at origin commit `b66a1373533232ecab6200d95182ce4e97573b36`.
- Exact intake blob: `149240f93f8155e39c3fbe8721e2ea979b845d35`. It equals the exact statement blob at origin commit `63bafa4f6778675c975920dfcd4f3e1c39749cef`.
- The two object IDs described as blobs in [INTAKE.md](INTAKE.md) are origin commits. A statement-only tree query resolved the origin blob IDs above. The verifier read the statement copies at the assigned base.
- [Source pins](../../SOURCE-PINS.json) bind D-35 SHA-256 `f27b6f6e593129592577a0863f46853540b4377ec9393a4f28d48026dd2ebcd4`, the PC-X Final Theorem Package SHA-256 `3110e8020cc1b86cdf7ba389602fb0ce0b941be84dfdef05d3eeb5580dec06bc`, the experimental master, and X01–X15. The read-only intake retrieval manifest lists the same accepted experiment commits. D-35 pp. 2–7 and 11 supplied the definitions and claim references. The Charter supplied claim identifiers and scope.
- The prior proof appendices, constructor proofs, other verifications, and parent construction records were outside the blind read set.

## Gates

1. The precomparison record is [BLIND-DERIVATION.md](../../VERIFICATION/initial/BLIND-DERIVATION.md). The commit introducing it seals the independent proof, boundary examples, and open wording issues.
2. Comparison starts after the precomparison commit has exact remote readback and the parent supplies the constructor commits. The comparison will record those full SHAs, original appendix checks, accepted evidence and claim-by-claim recommendations.

## Comparison and checks

26 November 2026. Published seal `ba490ac8ead7e4c40e7eb502c197d0e6dc5ee321`. Exact GitHub ref readback through both Git transport and the GitHub ref API matched that hash before the proof comparison started.

The parent then supplied foundation proof commit `8f1bd921831abebaa1af19b32f173caf571f27c9` and exact proof commit `6fbc9f7b1cd36fe69f5d6ff0e4fa6adbfe6bf61e`. I read their exact proof files and D-35 Appendices A–G, pp. 12–15. The terminal foundation statement is the sealed blob. The terminal exact statement at blob `3f1661b56c41b5e0af445c76091fc23fe36134ab` differs from the sealed statement only in T08's math delimiters. The independent precomparison record is preserved byte for byte.

The [comparison report](../../VERIFICATION/initial/COMPARISON.md) records a separate recommendation for each claim and sealed subclaim. T03.2 uses globally injective observation-indexed action maps as in the revised proof, with a counterexample to per-menu bijectivity alone. T12's generator uses residual-budget-indexed antichains. T10.b's NP-completeness uses compact serial binary encoding. The other claims pass in their declared scopes. Appendix A's certificate-fidelity and Appendix D's observation-transport proof gaps are repaired in the pinned foundation revision.

I read primary results on discernibility, equivalence-class determination, imperfect-information games, direct sums, blockers, implicit hitting sets, counterexample-guided synthesis and bounded-width constraint elimination. The comparison records the checked overlap and PC-specific proof obligations. Numeric conclusions use the original pinned packages and X15 independent readback. In particular, the X05 matched largest target and identity optima both cost 677, compared with the separately defined all-query price 1,070.

Both constructor finite check scripts passed from commit-pinned archives. The foundation run included 960 tiny-game coordinates and eight common-renaming coordinates. The exact run included 544 binary paired cases, 256 support clutters, 1,280 product-score calls and 5,120 correlated-width comparisons. The [independent focused replay](../../VERIFICATION/initial/boundary_replay.py) checked the weakened T03 interface, T12 residual-budget counterexample, 628 binary threshold cases, 864 capped-sum triples and a correlated shared-bag join. It runs with `python -B THEORY-RECONSTRUCTION/VERIFICATION/initial/boundary_replay.py`. These checks use finite proof examples and the retained records. Historical experiments were used as read-only evidence.

The terminal comparison commit includes only the comparison report, focused replay, and this Path update. The publication ref is `refs/heads/codex/pcx-math-verify-initial` on GitHub; the readback is recorded with the terminal commit in the parent handoff.
