# G01/G02 · Reproduction

From the repository root, use Python 3.13.7 with z3-solver 4.15 or later and Lean 4.21.0. The recorded run used the installed Z3 5.1.0. All finite arithmetic uses Python fractions, and the only algebraic solver dependency is Z3's nonlinear real arithmetic tactic for the quadratic example.

~~~powershell
python THEORY-FLAGSHIP-GENERALIZATION/T30-P-GENERALIZED/check_finite.py
lean THEORY-FLAGSHIP-GENERALIZATION/T30-P-GENERALIZED/TransportChecks.lean
~~~

~~~text
PASS: nonpolyhedral example, false endpoint mesh, and linked box cut examples
PASS: exact nonlinear algebraic policy and polynomial certificate (root-obj (+ (* 2 (^ x 2)) (- 1)) 2)
PASS: 336 raw source/fragment checks, sharp selective rates, optimal audit cost three
PASS: source-evidence refinement and dependent-calibration counterexamples
PASS: fixed guard survives a narrower report, with exact linear refutation
~~~

G01 replay computes full two-draw laws and supporting function values on a finite rational grid, checks three exact Simple Max Cut reductions, uses nonlinear real satisfiability to refute each possible breach of the algebraic candidate on the compact example, and verifies a small equality-certificate identity coefficient by coefficient. Finite grid agreement does not establish the continuum results. The separate written proof does.

G02 replay independently enumerates raw source tag and residual tickets for both nominal and actual protocols. It checks pointwise subrow dominance, score envelopes, their tight values and every certified audit subset over four report tuples. It tests prospective minimax read cost and an additional source evidence refinement with the represented world set fixed. Confidence examples show that equal unconditional marginals can conceal retained state and that rare activation can select the entire exception mass. The hostile fixed-guard replay checks a one-world report that leaves the original two-world authority guard in force, and validates the combined linear refutation and selective score endpoints.

Lean checks the scaled additive directed interval argument, monotonicity of one upper-envelope term as matched mass grows and a checked interval tightens, and the two exact signed margins in the fixture. Common scaling is by positive denominators. These results verify finite algebraic subarguments and fixture arithmetic. They do not formalize source fidelity, nonlinear real decision, semi-infinite convex feasibility or martingale inference.
