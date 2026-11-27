# Reproducing the strategic audit checks

Run the following from the repository root.

~~~powershell
python THEORY-FLAGSHIP-GENERALIZATION/COMPUTATIONAL-CHECKS/A-check.py
lean THEORY-FLAGSHIP-GENERALIZATION/FORMAL-PROOFS/A-StrategicAudit.lean
~~~

Checked with Python 3.13.7 and Lean 4.21.0. The Python program has no external packages.

- It enumerates every deterministic one-read binary test for each G1 example and checks matching rational primal and prior certificates.
- It checks an affine acquisition lower certificate on all 144 deterministic G3 policies of the least favorable pair, as well as restricted-cap and precommitted cases. The attaining private mixture is evaluated separately.
- For the attainable G3 policy, 128 combinations of type and dry, live and direct proposals give exact nonnegative Bernstein coefficients for the stated performance slacks over \(s\in[0,1]\). Each slack in the script has degree at most two, so this is a polynomial sign certificate on an interval.
- It checks the eight possible safeguard selections and the error-and-coverage contradiction associated with retained maintenance completions.
- Lean checks a finite integer-count Bayes identity, the scaled expected and supported price inequalities, and the wrong/report identity on equally distributed records. Minimax, finite convexification, Helly, operative interpretation and real deployment correspondence are supplied by the argument and source premises outside that file.

All checks concern the mathematical family or supporting lemmas. No prospective deployment or experiment was executed.
