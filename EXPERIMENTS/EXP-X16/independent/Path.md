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

The next phase will add the independent checker after release of the native source and before the official source freeze. It will read and verify the authenticated opening, reconstruct the installations and policy supports, invoke native tasks in its own workspace and validate the persisted records independently.
