# M03 computational record

On 27 November 2026, Python 3.13 ran the constructor's standard-library fixture check from the repository root.

    py -B THEORY-GENERALIZATION/WORKSTREAMS/M03/check_finite.py

The following computations use exact fractions except for evaluation of three calibration radii. The calibrated comparison margins are strictly positive after outward rounding.

| Fixture | Independent computation | Output |
| --- | --- | --- |
| Uncertain row and uncertain event | Enumerate reference/deployment eighths, then endpoint event rates and unseen-context mixtures | Covered risk [1/8,1/2]. Adding freely labeled mass up to 1/5 yields [1/10,3/5]. |
| Correlated roster | Enumerate the coupled pairs (u,1−u) on the fixture grid and compare individually minimized risks | Each coordinate minimum is 0 and the minimum of the maximum is 1/2. |
| Shared unknown conditional | Compute the exact midpoint of the two occupancy/event arrays | Normalized conditional probabilities become 3/4 and 1/4, violating equality. |
| Retrospective weighted anchors | Enumerate exact 2-D vertices and independently enumerate the aligned eighths grid. Check all 8 subsets and derive new patterns from actual violating vertices | Base maximum 3/4. At threshold 1/4 the optimum is A+B at cost 2. The search finds 3 patterns under its stated tie rule. |
| Prospective deterministic anchors | Solve recursive cost over partially observed installed registers and independently enumerate the feasible fixed sets | Adaptive worst cost 3. Fixed acquisition cost 4. Direct prices 7/2 and 5/2 respectively make the semantic or direct method cheaper. |

The fractional minimum test compares two methods on a specific grid-aligned instance. It is independent of a numerical LP solver and does not establish correctness between arbitrary grid points or for arbitrary inputs. The structural arguments are in the [proof](PROOF.md). Lean 4.21.0 checked the sufficiency/hitting equivalence, freshness of a disjoint opposing witness, and the master-optimum comparison in [AnchorLogic.lean](AnchorLogic.lean). Run the command below from the repository root. This covers the logical kernel, with the LP modeling, stopping argument, and calibration proof still on paper. Independent review is separate.

    lean THEORY-GENERALIZATION/WORKSTREAMS/M03/AnchorLogic.lean
