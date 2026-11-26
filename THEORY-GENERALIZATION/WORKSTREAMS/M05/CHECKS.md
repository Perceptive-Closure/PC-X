# Exact finite and Lean checks

Run from the PC-X checkout root. The Python checks need only the standard library and use Fraction arithmetic on finite constructed fixtures. They read no experimental records.

~~~powershell
python -B THEORY-GENERALIZATION/WORKSTREAMS/M05/check_m05.py
lean THEORY-GENERALIZATION/WORKSTREAMS/M05/EventMass.lean
~~~

The constructor ran CPython 3.13.7 and Lean 4.21.0 (commit 6741444a63ee) on Windows. The executable checks report:

~~~text
T25.J exact monitor geometry versus ticket enumeration: 164 cases
T26.C backward checks versus complete pair enumeration: 2916 cases (1152 empty)
T27.J exact shared-ticket composition and conditional profiles: 13 cases
Exclusive modes, zero denominators, early/late pairing and triple compatibility checked.
~~~

The T25 check computes endpoints by intersecting rational halfspaces and independently enumerates per-ticket physical label words. It cuts the two-dimensional feasible polygon at the worst-context balancing line before computing either affine piece. It tests every choice of confirmed alarm positives and negatives for up to eight ticket pairs, including degenerate cells. The fixed four-pair reproduction checks risk, miss, false alarm and false-negative extrema and denominator states. The separate three-mode case checks the gap between defined rates and the undefined mode.

The T26 check solves the conditional binary-row problem in its scalar free cell and enumerates all complete two-step couplings by independent integer row tables. The two are compared on all 729 pairs of native row menus for each of four scoring/support profiles. With denominators two, the endpoint row weights of the restricted \(2\times2\) polytopes are all representable by those count tables, including downstream restriction to zero particular paired cells. The reference enumerator generates complete path weights before scoring, so it also finds infeasible cases without the recurrence. An additional early/late counterexample contrasts the native-prefix restriction with unrestricted coupling of the terminal Bernoulli events.

The T27 check enumerates stateful shared-ticket terminal masses and the paired diagnostic monitor for 13 exact conditional collision probabilities. It accounts for a local event that is scored after the first timeout bit, tests conditional risk at the ticket-3 prefix, and checks the dependence of uncovered risk and probe-only loss on the same physical law. A separate exhaustive three-bit enumeration checks global infeasibility despite feasible opposite-bit pair marginals.

Lean checks two finite integer-weight identities. The first proves the signed original-versus-probed difference from the two directional flip masses. The second partitions the global mass into the portion within and outside the local-event union. Clearing denominators extends these identities to rational weights. They both report the standard axioms propext and Quot.sound. The polytope realization, conditional disintegration, optimization, algorithmic complexity and operational source assumptions are established in prose or by the supplied model contracts. The finite comparisons corroborate that proof within their enumerated domains.
