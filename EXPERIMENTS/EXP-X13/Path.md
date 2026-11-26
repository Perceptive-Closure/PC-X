# EXP-X13 execution record

Reserved on 2026-11-26 for a dedicated agent and the branch `codex/exp-x13` at master base `fbc00d153a4ec29ef4b0078fee05a818669df95a`. The Codex-managed worktree is `pcx-x13/PC-X`. The [work plan](WorkPlan.md) and [frozen protocol](Protocol.md) define the full program.

- Verified the 43-page charter digest and visually confirmed printed pp. 28–29 and 34–36. Read pp. 21–22 and 27 for T18 and T25. Pinned X10 trusted measurement and X11 calibration fidelity methods in the design.
- Froze the two independent composition controls, source and authorization boundaries, finite support, agent-local and global events, utility criterion, calibration costs and prospective custody before any holdout assignment.

## Pre-audit checkpoint

- Published the protocol at [577160f934d8d1dd4fcd3271f020df6b6e5f3dcd](https://github.com/Perceptive-Closure/PC-X/tree/577160f934d8d1dd4fcd3271f020df6b6e5f3dcd/EXPERIMENTS/EXP-X13). Custody had not begun at this checkpoint.
- `python -B src/x13.py pre-audit --out results/pre-audit.json` produced SHA-256 `7001b56dcc317c85e54c8a21502ca94e23e2f82d03e5332fa38e6e8ba9b6ca69`. The evidence includes 2,048 executed isolated episodes, 64 presentation checks, 64 grant checks, 32 policy transition checks, 480 sentinel checks and a target-distinct pair with identical isolated evidence. Both criteria for composition were checked separately. The four-mode joint predictions at this stage came from the separate finite specification.
- The minimum uniform static audit costs 15, using allocator and gateway sentinels on ports A, B and C. Both exhaustive partitions and separating-pair coverage agreed over 1,024 query subsets. Greedy also costs 15, cheapest-first costs 18, uniform random order has expected cost 275/14, and acquiring every read costs 25. Full installation identification costs 19 because it also requires the roster read.
- `python -B -m unittest discover -s tests -v` passed seven tests in the working tree with Python 3.13.7. The byte-identical pre-audit replay took 1.386 seconds with 1,946,948 bytes of peak Python allocations under `tracemalloc` on the development host. This timing includes tracing overhead.
