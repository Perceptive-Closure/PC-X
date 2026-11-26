# EXP-X06 execution record

The experiment is running on `codex/exp-x06` from orchestration revision `4303e9eeaa1ba8218b43737826f46ce091e5f141`. The charter digest in [the configuration](config/protocol.json) was verified against the supplied 43-page PDF. Its source is read-only. The protocol uses the foundational resource freeze in pp. 2–9, the target-relative solver obligations in pp. 13–17, and the prospective custody and reproduction sequence in pp. 34–36.

[The frozen protocol](Protocol.md) defines the common checkpoint graph, the two boundary witnesses and the primary budgeted closure endpoint. [The source manifest](config/provenance.json) pins X01, X03, the official OPA CLI binary, the byte-identical upstream example policy and the Apache 2.0 license. All experiments use inert offline fixture decisions.

## Preaudit

Nine preflight tests passed with Python 3.13.7. Windows archives can convert predecessor source line endings to CRLF. The reference loader normalizes CRLF to LF before matching the pinned Git blob digests.

The two X01 solvers and an independent one-step calculation checked all 128 coordinates from 16 source-compatible world/adapter witness contracts. Both X03 methods agree with the five-round lazy certificate and its cost 8. The full partition check evaluated 4,096 subsets. The cheapest-first and exhaustive strategies cost 12 and 28. Enrollment balance restricts the primary target set to 16 vectors, compared with 256 independently varying bits. The envelope-only ablation is audit-inaccessible.

The SHA-256-pinned upstream OPA release passed all five disjoint development controls, including malformed JSON rejected at exit code 2. [Raw development decisions](results/development.json) and [frozen preaudit](results/preaudit.json) are preserved. The official binary reports a dirty-build suffix on its exact pinned source revision. The release's exact artifact digest and reported source revision agree with the frozen manifest.

The parent initially reproduced the frozen preaudit and nine tests from exact GitHub archives without Git metadata. The parent independently verified the pinned binary and original upstream policy and used a separate custody directory in the managed experiment worktree. Custodian and experiment roles shared a filesystem. Only the selected anonymous marks were shared before forecast.

## Custody and opening

| Stage | Evidence and UTC time on 2026-11-26 |
| --- | --- |
| Freeze | [GitHub preaudit revision](https://github.com/Perceptive-Closure/PC-X/commit/8272ea71ab4242459968130b114bcc49fe20dca7), exact preaudit SHA-256 `2527c719648ac860843656c3d42d17ecc82955189c290341b3189694d2b674f4` |
| Parent assignment commitment | 15:22:49.610696, SHA-256 `d93c96bdfb2b0c080ce0fadc67a808e0b1540e0b08f68ae81e12a39ae8a10cd8` |
| Admission-ledger audit | 15:22:49.832637, first-instance marks 0 self, 0 manager, 0 second-manager and 1 method. [Audit receipt](results/audit-receipt.json) |
| Forecast | Generated 15:23:14.903415. The direct child of the freeze added only the receipt and the forecast. [GitHub forecast revision](https://github.com/Perceptive-Closure/PC-X/commit/068241d15abb189c01604b6959ce8fc33e35b576) |
| Remote verification and authorization | The parent independently checked the exact branch head, ancestry, source hashes and receipt bytes before opening. The verified archive produced the authorization record at 15:25:25.074999. [Release record](results/release.json) |
| Native opening | 15:25:25.344036 through 15:25:31.817551. The release matches the private commitment and both evidence artifact hashes. [Raw native evidence](results/native.json) |

## Measured results

| Held-out stratum | First instance cost under frozen R | Second instance cost under frozen R |
| --- | ---: | ---: |
| Self | 1 | 3 |
| Manager | 1 | Infinity |
| Second manager | 1 | 5 |
| Method | Infinity | 1 |

All 8 primary verdicts and all 64 freeze coordinates matched the sealed forecast. Four instances could close at cost 1. Two required the higher-cost attestation and two had no closing route when R was frozen. Before the audit all eight individual budgeted verdicts were ambiguous. The terminal-only baseline treated a defined native Boolean as a positive freeze certification for every instance. It falsely certified four of eight. In each matched pair the unrestricted native decision vector was the same. The evidence ablation retained a source-compatible witness pair that the available envelope queries could not distinguish.

The opening recorded 117 offline OPA evaluations across the frozen coverage and five controls. There were 56 native allows and 56 native denies in the held-out evidence. All five controls passed, including the malformed request's diagnostic and exit code 2. The raw trace includes 48 prospective atomic transitions blocked before their native calls. The independent result validator reconstructed touch, the feasible actions and both target classes from the normalized checkpoints and raw native output. [Summary](results/summary.json) · [Per-instance trace hashes](results/manifest.json)

A local fresh native replay reproduced the complete raw trace SHA-256 `83ac818003be1a8e7a7dccf01bbc36a3cbe92a740d215b03c50e6094f717c2af`. All traces measure coverage of the frozen finite workload. The adapter constructs the two admission semantics while the engine and policy come from upstream. The result supports prospective source-anchored recovery for the declared adapter and policy. General cross-system transport under T30 remains open.
