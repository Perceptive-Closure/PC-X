# Exact reproduction

Run from an exact checkout of this campaign. Python 3.13.7, Z3 5.1.0.0 (the P checker uses nonlinear real satisfiability) and Lean 4.21.0 were used for campaign replay. The P checker documents its compatible z3-solver requirement. Other constructor Python checks use the standard library and exact fractions. Python invocations use `-B` to avoid caches.

~~~powershell
python -B THEORY-FLAGSHIP-GENERALIZATION/T30-P-GENERALIZED/check_finite.py
python -B THEORY-FLAGSHIP-GENERALIZATION/COMPUTATIONAL-CHECKS/A-check.py
python -B THEORY-FLAGSHIP-GENERALIZATION/COMPUTATIONAL-CHECKS/U-check.py
python -B THEORY-FLAGSHIP-GENERALIZATION/VERIFICATION/check_p_blind.py
python -B THEORY-FLAGSHIP-GENERALIZATION/VERIFICATION/check_a_blind.py
python -B THEORY-FLAGSHIP-GENERALIZATION/VERIFICATION/check_u_blind.py
~~~

P checks linked box extrema and algebraic feasibility witnesses, the guarded-relative blocker and 336 raw source and fragment cases. A checks 144 deterministic price comparisons and 128 exact Bernstein coefficient tests for continuous interval bounds. U compares 1,296 expanded and count-compiled performance cases, exact probe-price polytope vertices, an actual-optimum enclosure, lost-record, repeated-edge and tail controls. The \(2^{64}\) to 65 structural contrast comes from an exact symbolic count. No such Cartesian history set was enumerated at depth 64.

Additional challenged cases and their matched replays are in the [hostile role record](../HOSTILE-REVIEW/Path.md). The [formal modules](../FORMAL-PROOFS/README.md) verify selected algebraic instances. None of these finite checks replaces the continuous or strategic proofs.
