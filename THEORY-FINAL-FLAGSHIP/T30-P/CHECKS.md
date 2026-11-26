# T30.P · Reproduction

Run these from the repository root in the T30.P constructor revision.

~~~powershell
python THEORY-FINAL-FLAGSHIP/T30-P/check_finite.py
lean THEORY-FINAL-FLAGSHIP/T30-P/CoreChecks.lean
~~~

Validated with Python 3.13.7 and Lean 4.21.0. The Python replay uses only the standard library. The Lean replay imports the bundled Std library.

~~~text
PASS: 160 per-component policies, exact raw/compiled and alternate ticket equality
PASS: useful robust randomized risk 1/5, deterministic risk 7/30, bad risk 2/5
PASS: 57 exact audit trees, prospective 4, fixed universal 5, realized 2 or 4
PASS: pairwise feasible and jointly infeasible cores, linked-law and confidence controls
~~~

The Python reference enumerates concrete ticket draws, literal route authority, hidden event bits and work completions for every component and deterministic protected plan, including stop choices. It independently multiplies canonical conditional rows. Both raw ticket encodings agree exactly with these laws. It checks a fair mixture of pure controllers, optimizes its small rational risk epigraph by exact vertex enumeration, suppresses the actual first receipt, and removes a hazard with unchanged visible receipt marginals. Exhaustive prospective audit trees, an independent minimax recurrence and universal/realized subset enumeration corroborate all audit costs. A separate exact vertex calculation checks the three-world obstruction and an interior rational grouped certificate. The remaining checks enumerate finite Bernoulli outcomes for optional stopping, selection, a close-mean total variation example and activation-risk accounting.

The Lean check proves product domination for nonnegative integer row numerators, equivalence between a zero sum of marked products and absence of a marked leaf with all factors positive, and equivalence between removal of a group blocker and hitting its disagreement field set. Finite rational leaf weights can be cleared to nonnegative integer numerators with one positive common factor when using the zero-mass lemma. Product domination similarly uses common positive denominators for each comparison. The check leaves source semantics, probabilities in the general model, compact LP duality, finite-confidence inference and theorem-level correspondence to the written proof.

The Python instance is a controlled synthetic fixture. The check uses an explicit tiny rational solver and does not implement the general LP or exact source-verification procedure.
