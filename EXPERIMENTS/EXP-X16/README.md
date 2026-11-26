# EXP-X16

Prospective finite validation of the T30.CG solver with synthetic document intake, review and routing. The case graph, acquisition prices, useful service and comparison rules are fixed in [Protocol](Protocol.md). The authorized historical refs are in [PINS](PINS.json). The independent solver uses explicit accepting paths and action/receipt histories. The native service engineer and independent verifier work from the common interface. [Roles and gates](WorkPlan.md) · [Execution record](Path.md)

## Replay

Use a fresh local directory and the exact Git blob bytes of the published opening or final snapshot, including original LF endings. Run from this experiment directory with Python 3.13 and Node.js 22. Copy custody/package.json and custody/package-lock.json to a separate dependency directory. Run npm ci --ignore-scripts --no-audit --no-fund from that directory.

1. Run `python -B custody/releasecheck.py opening . <dependency-directory> --remote` to verify the signed catalogue, registered draw, chronological receipts, exact hosted Git objects, fixed BLS round, and traced selection. The same command without --remote verifies the archived bytes and signed beacon offline.
2. To regenerate the forecast, run `python -B experiment.py forecast <source-commit-from-draw> custody/draw-plan.json <scratch-forecast.json>`. Compare its exact SHA-256 to the registered forecast. The command sees the declared graph and prices and needs no installed-mode draw.
3. Run `python -B experiment.py run results/forecast.json custody/heldout.json custody/authority.json <fresh-run-workspace> <fresh-result-directory> --deps <dependency-directory>`. The command checks the opening before issuing native requests. It performs the full row audit and pure-panel comparisons, enumerates all supported online branches, runs the selected native documents, and reads the files back from the filesystem.
4. Run `python -B independent/reference.py cases/catalogue.json <independent-reference.json>` followed by `python -B compare_reference.py cases/catalogue.json results/forecast.json <independent-reference.json> <agreement.json>`. The separate native reproduction command is documented in [the independent record](independent/Path.md).

The experiment needs only communication with the named GitHub repository and drand for live custody. Native jobs and comparisons are local. The workspace path is an isolated destination for generated synthetic records. Training uses the signed dummy demonstration in [the service record](service/Path.md) and never needs held-out data.

## Evidence

The source manifest lists exact byte hashes for the frozen executable sources, roster and protocols. Opening metadata binds the registered Git blobs, round, signatures and installations. The raw run log records complete public step traces, actual tariffs, stopped or denied outcomes, and each stage's durable SHA-256. Example final artifacts preserve their original UTF-8 byte encoding as JSON strings. The anchor ledger records each reachable literal command occurrence and ordered successor test. Benchmark JSON records separate compile, solve, native and read-back times, with per-run traced Python allocation peaks. Clock durations and allocation peaks are rerun measurements. The remaining computed evidence is deterministic.

The proof scope is the signed finite local graph and complete positive receipt support. This experiment measures exact prices under the declared menu and synthetic service. Separate roles share a host account. Cryptographic opening and two distinct authenticated GitHub readbacks preserve the temporal evidence.
