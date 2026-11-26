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
