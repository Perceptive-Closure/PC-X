# EXP-X13 execution record

Reserved on 2026-11-26 for a dedicated agent and the branch `codex/exp-x13` at master base `fbc00d153a4ec29ef4b0078fee05a818669df95a`. The Codex-managed worktree is `pcx-x13/PC-X`. The [work plan](WorkPlan.md) and [frozen protocol](Protocol.md) define the full program.

- Verified the 43-page charter digest and visually confirmed printed pp. 28–29 and 34–36. Read pp. 21–22 and 27 for T18 and T25. Pinned X10 trusted measurement and X11 calibration fidelity methods in the design.
- Froze the two independent composition controls, source and authorization boundaries, finite support, agent-local and global events, utility criterion, calibration costs and prospective custody before any holdout assignment.

## Pre-audit checkpoint

- Published the protocol at [577160f934d8d1dd4fcd3271f020df6b6e5f3dcd](https://github.com/Perceptive-Closure/PC-X/tree/577160f934d8d1dd4fcd3271f020df6b6e5f3dcd/EXPERIMENTS/EXP-X13). Custody had not begun at this checkpoint.
- `python -B src/x13.py pre-audit --out results/pre-audit.json` produced SHA-256 `7001b56dcc317c85e54c8a21502ca94e23e2f82d03e5332fa38e6e8ba9b6ca69`. The evidence includes 2,048 executed isolated episodes, 64 presentation checks, 64 grant checks, 32 policy transition checks, 480 sentinel checks and a target-distinct pair with identical isolated evidence. Both criteria for composition were checked separately. The four-mode joint predictions at this stage came from the separate finite specification.
- The minimum uniform static audit costs 15, using allocator and gateway sentinels on ports A, B and C. Both exhaustive partitions and separating-pair coverage agreed over 1,024 query subsets. Greedy also costs 15, cheapest-first costs 18, uniform random order has expected cost 275/14, and acquiring every read costs 25. Full installation identification costs 19 because it also requires the roster read.
- `python -B -m unittest discover -s tests -v` passed seven tests in the working tree with Python 3.13.7. The byte-identical pre-audit replay took 1.386 seconds with 1,946,948 bytes of peak Python allocations under `tracemalloc` on the development host. This timing includes tracing overhead.

## Custody and prospective prediction

- The parent downloaded the exact GitHub pre-audit archive [8708fd1bd36e1eede87b951afe66ac468a324c3d](https://github.com/Perceptive-Closure/PC-X/tree/8708fd1bd36e1eede87b951afe66ac468a324c3d/EXPERIMENTS/EXP-X13), validated its seven tests and reproduced the pre-audit bytes. It verified that revision at 2026-11-26T15:15:08.8513279Z before reserving a private fixture and running only the six authorized sentinel reads. The [public receipt](results/audit-receipt.json) binds commitment `f4d95f896baea05b4c939e8542eef2dca04b6ef16493fe1915dd8758c296cffb` and has SHA-256 `330d7ba3a7dd6ff7fd7d6ab8f7d1300af268eb3ba3fce317aa1e1a93a30a1190`.
- `python -B src/x13.py forecast --receipt results/audit-receipt.json --out results/forecast.json` produced SHA-256 `609c2fe979835105995b3f7484ee4ce1b72fe4ac11f6655d678d5a0d1473c5b3`. It resolved the primary target at every port, while the compatible roster remained two-valued and the schedule order remained sealed. A was forecast to fail containment only, B to fail both premises, C to meet both and accomplish useful work, and D to fail carryover only. Withholding allocator or view reads leaves eight compatible installations in each case. The nameplate-only prior leaves all 48.

## Opening and results

The parent verified forecast revision [3dfb6a1845da350cf94d510b21dbcefa99f69a8a](https://github.com/Perceptive-Closure/PC-X/tree/3dfb6a1845da350cf94d510b21dbcefa99f69a8a/EXPERIMENTS/EXP-X13), its ancestry, exact receipt bytes and unchanged executable at 2026-11-26T15:17:09.125404Z. The audit receipt was issued at 15:15:09.061580Z, and the committed forecast records 15:15:44.500760Z. The independently executed opening records 15:17:09.647860Z and finished at 15:17:09.8790455Z. Both custody commands ran from the verified pre-audit GitHub archive without Git metadata. Here `PARENT_SECRET`, `PUBLIC_RECEIPT`, `VERIFIED_FORECAST` and `PARENT_OBSERVATIONS` stand for the parent-owned custody input and output paths.

```powershell
python -B src/x13.py seal --protocol-commit 577160f934d8d1dd4fcd3271f020df6b6e5f3dcd --source-commit 8708fd1bd36e1eede87b951afe66ac468a324c3d --sealed PARENT_SECRET --receipt PUBLIC_RECEIPT
python -B src/x13.py open --sealed PARENT_SECRET --receipt PUBLIC_RECEIPT --forecast VERIFIED_FORECAST --forecast-commit 3dfb6a1845da350cf94d510b21dbcefa99f69a8a --remote-tip 3dfb6a1845da350cf94d510b21dbcefa99f69a8a --verified-at-utc 2026-11-26T15:17:09.125404Z --out-dir PARENT_OBSERVATIONS
python -B src/x13.py manifest --out results/manifest.json
python -B src/x13.py replay
python -B -m unittest discover -s tests -v
```

The 512 joint and 1,024 isolated executions exhausted all 64 equally weighted tickets in both contexts for all four ports. All eight port-context count vectors and all port judgments matched the sealed forecast. Each local isolated risk was 5/64 in the balanced context and 7/64 in the concentrated context. Each agent processed all 128 required jobs per port and context. The columns below list balanced, then concentrated counts. Both agents had the same local and qualification counts in this workload.

| Port and observed mode | Global events out of 64 | Global events outside the local union | Joint local events out of 64 per agent | Qualified jobs out of 128 per agent | Composition premises |
| --- | --- | --- | --- | --- | --- |
| A, parallel and faithful | 32, 32 | 26, 25 | 5, 7 | 64, 64 | Carryover only |
| B, parallel and shared summary | 40, 60 | 20, 4 | 19, 56 | 56, 32 | Neither |
| C, exclusive and faithful | 6, 7 | 0, 0 | 5, 7 | 123, 121 | Both |
| D, exclusive and shared summary | 20, 56 | 0, 0 | 19, 56 | 109, 62 | Containment only |

- Port C attained the useful 1/4 composition bound. Its measured worst-context risk was 7/64 and per-agent qualification was at least 121/128. In the concentrated context, both local violations occurred together on 7/64 tickets. The product of their marginals is 49/4096, so independence would give the wrong overlap.
- Port A gave a measured failure of containment while the original local bounds held exactly as in isolation. Balanced ticket `[6,3]` has a shared-bench overlap and no local underwork. Port D kept containment while both local risks rose to 56/64 in the concentrated context. The raw witness for balanced ticket `[3,5]` shows two job demands displayed as one only in the joint run. Port B failed both conditions. The baseline that blindly summed isolated bounds certified all four ports and was false on A, B and D.
- The evidence supports composition for this declared workshop, under verified local histories, exclusive allocation, complete ledger truth and exact input coverage. The 15-unit audit minimum is relative to the frozen static query family and enrollment fact. The holdout validates prospectively identified port semantics over an exhausted finite ticket bank. It uses shared-host role separation and makes no sampling claim about an external population. Unrestricted T18 transfer and T27 composition remain research targets.

## Evidence and handoff

| Artifact | SHA-256 |
| --- | --- |
| [Opening](results/opening.json) | `2dfe5e85feb74284a11497851d96f75d2b802ef2b0912afc15e0e20506546d5f` |
| [Summary and native witnesses](results/summary.json) | `893515f2a3c395385db33203eb1d756c629126853d31e5dfeed6f26db63052db` |
| [Compressed ledger](results/episodes.jsonl.gz) | `58e0adce8b77ce21dc74f15c28984e1f32aae4505f60a225d2252c19dd0d9f86` |
| Decompressed ledger | `1f26aa0f162ab34d8c225e9f85c10317d73dc73255f0287577c2e86f62763bdb` |
| [Manifest](results/manifest.json) | `bc095b09827aab7d6481b15cf494b4cdfd85b7246913cc93ca60bdc7e1916ea2` |

Working-tree replay passed all seven tests, reproduced the entire decompressed ledger and the original gzip bytes, and found no native-reference disagreements. A separate occupancy-count tabulation, using only the frozen workload and raw clock and station fields, reproduced all eight global and outside-union counts, the local counts and qualified work. Terminal candidate ready for the parent's clean GitHub verification. The managed worktree and parent-owned custody scratch are intact.
