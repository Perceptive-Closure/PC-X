# Independent EXP-X16 execution record

27 November 2026. The independent reference was written from the public catalogue, common interface and T30.CG statement in the isolated independent checkout. The local checks use public defined cases and synthetic mathematical examples. The reference accepts a catalogue and does not consult the native service, authority, selector, installed held-out paths or the parent planner.

Run from the experiment directory.

    python -B independent/reference.py cases/catalogue.json reference-output.json
    python -B -m unittest discover -s independent -p test_reference.py -v

The reference uses Python 3.10 or later and the standard library. For separate same-host measurements, time the import, accepting path enumeration and individual solver calls as required by the experiment harness. The online entry points are `enumerate_paths(profile)` and `solve_online(profile, paths, identity=False)`. `solve_schedule` exposes the fixed-ordinal comparator. A `paths` collection can be reused to measure a solve independently of enumeration.

## Independent method

The solver walks every connected accepting path and saves the minimum known-path tariff for each suffix. Fresh fast and stale slow attain the per-stage minimum. Every supported outcome of a lawfully issued job completes the job, and all known-path minima use exactly one job per stage. The deadline determines the intrinsic label. The move horizon separately constrains online policies.

The static reference enumerates subsets of the identical predeployment panel and explicitly verifies coverage of each distinct opposition mask over pairs of accepting paths. The pure adaptive reference tests every query that splits its current answer cell, using the largest child cost plus the query price. A deterministic query that leaves the cell unchanged cannot improve any continuation. The all-query price is the sum of the declared tariffs, irrespective of the optimum.

The online reference carries explicit path indices with their individual accrued charges, complete action and receipt histories, public meter, stage and work. Every issued command must be callable and authorized on each compatible path. The search branches on every supported pair of receipt observation and next meter. The only cached online data are interpreted, path-conditional command rows. The solver never merges decision histories. It can discard a history when a still-compatible positive path already needs more work or moves than remain. A one-successor act with unchanged compatible paths, stage, meter, work and instrument state spends a move with nondecreasing charge. Removing that act preserves feasible continuations. A candidate with accrued worst charge at least that of a feasible incumbent cannot improve it. For the matched full identity problem a verdict additionally requires a singleton set of compatible paths.

The fixed-ordinal comparator forces one shared literal act at each move position for all histories that continue. A branch stops as soon as its target and service obligations, including identity where requested, are satisfied. Continuing a branch eligible to stop could only increase its charges and add command constraints. Only a stutter common to every continuing history can be skipped as a schedule action. The fixed-ordinal witnesses cover the six preregistered small profiles.

## Reference JSON

| Location | Contents |
| --- | --- |
| Top level | `schema` is `1`. `profiles` maps catalogue profile IDs to results. `abstract_controls` maps the registered model-only exposure IDs to counterfactual results. |
| Profile metadata | `scope` is `valid-profile` or `native-control`. An abstract exposure has `scope: "model-only-control"`, its original `profile` and registered `gate`. |
| `paths` | Lexicographically enumerated rows with `edges`, `intrinsic_cost`, `target` (`YES` or `NO`) and `fastest_job_actions`. Control-only rows are labelled by the enclosing result. |
| `all_queries_paid` | Total price of the entire pure static panel. |
| `static.target`, `static.identity` | `worst_paid`, chosen `queries` and the count of distinct `opposition_masks`. |
| `adaptive.target`, `adaptive.identity` | `worst_paid`, visited `cells` and `tree`, with `{query,next}` nodes keyed by exact answers or `{label}` nodes. Identity labels are full edge-ID arrays. |
| `online.target`, `online.identity` | `worst_paid`, optional `policy_by_initial`, `losing_initial_receipts`, visited `histories` and literal `action_trials`. |
| `fixed_schedule.target`, `fixed_schedule.identity` | `worst_paid`, the fixed literal `schedule`, `policy_by_initial`, visited `ordinal_states` and `action_trials`. |

`worst_paid` is the maximum declared acquisition charge on supported branches of an optimum. A JSON `null` means infeasible. The witness is also `null` for an infeasible problem. A finite online witness maps each initial `obs|meter` key to a native-compatible tree of `{act,next}` and `{verdict}` nodes. Select the root using the actual public initial receipt. The metrics count the performed search with the documented pruning. A fixed-ordinal state may contain several simultaneous receipt histories.

The model-only Cartesian control independently reconnects each stage to a common boundary at that layer. The missing-support control removes the first-job LONG outcome. The hidden-carry diagnostic books its actual per-path charge while retaining the declared `(obs,meter)` decisions. The changed-instrument diagnostic excludes completion through a disturbed instrument even when all stage receipts are obtained. These control values are outside the valid theorem scope.

## Native reproduction

The native check was developed from the documented interface and exact released service commit `172b70a40ff1a7ae586c7ad704c83db1a7ad8c05` before official opening. The verifier uses Python with `cryptography` for Ed25519 and Node.js 22 for native execution. The official mode requires the separately installed, frozen drand dependency lock through `--drand-deps`. The two modes use fresh scratch directories and byte-exact Git blobs. The training command requires the native commit to have been fetched.

    python -B independent/reproduce.py train 172b70a40ff1a7ae586c7ad704c83db1a7ad8c05 <new-scratch-dir>
    python -B -m unittest discover -s independent -p "test_*.py" -v

The public run executed 176 tasks on 14 explicitly labelled installations and training-only variants without discrepancies. Two deliberately altered seals were refused before any output. A training-only stale stage with two raw receipt outcomes verified that a single R-changing branch removes the entire fast occurrence before any choice of outcome.

Only after the official opening is published, fetch the exact opening commit from GitHub. Use that commit even if the branch has advanced. Install the frozen `custody/package.json` and `custody/package-lock.json` in a disposable dependency directory with `npm ci --ignore-scripts --no-audit --no-fund`. From the experiment directory run the command below.

    python -B independent/reproduce.py opened <opening-commit> <new-scratch-dir> --drand-deps <deps-dir>

The checker confirms the exact linear Git history of source, authority, forecast, parent receipt, custody prerelease lock and opening. It checks both Ed25519 signatures independently, verifies the archived BLS signature with the frozen drand verifier and dependency lock, recomputes the installed draw and documents from the exact round, and checks the two relays and three distinct GitHub ref receipts against the scheduled time. The external cryptographic tool used for BLS is shared. The independent chronology, selection and SHA-256 checks are written in Python.

The audit obtains every reachable typed source row and full pure panel from the native service conditional on each accepted path. It compares literal command rights, tariffs and all ordered raw outcomes, including exact R-revision arrays and their digests. For each selected installation the runner checks the known-mode tariff and runs all permitted tapes of finite independent online and fixed-ordinal witnesses. Pure optimized queries use the separate static driver. The seven controls receive targeted tests against the actual signed service or its model-only exposure. Expected denials remain recorded with the other results.

The checker reads each durable artifact directly and compares its bytes against independently reconstructed normalization, reviews, ordered source bindings, prior-stage digests, receipts, and destination. Stage quotes, work and move quotas are checked independently from the service's completion field. The selected paths and exact comparator values are compared to the sealed forecast after opening. The checker records three uninstrumented elapsed-time samples per profile and separately traces Python allocation peaks, with explicit path preparation and solving distinguished. The raw native requests, responses, artifacts, exact source and custody bytes, comparator outputs and timings stay under the supplied scratch directory. `report.json` records checks and discrepancies. A custody or source verification failure instead produces `failure.json` and stops native execution.
