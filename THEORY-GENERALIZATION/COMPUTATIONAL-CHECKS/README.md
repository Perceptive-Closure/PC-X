# Reproducing the mathematical checks

Use the authenticated generalization snapshot. Run from its repository root. The following Python files use the standard library and the Lean checks use Lean 4.21.0. The exact archived experiments and standalone baseline validation have their own frozen checks.

```powershell
python -B THEORY-GENERALIZATION/WORKSTREAMS/M01/check_m01.py
python -B THEORY-GENERALIZATION/WORKSTREAMS/M02/check_m02.py
python -B THEORY-GENERALIZATION/WORKSTREAMS/M03/check_finite.py
python -B THEORY-GENERALIZATION/WORKSTREAMS/M04/check_finite.py
python -B THEORY-GENERALIZATION/WORKSTREAMS/M05/check_m05.py
python -B THEORY-GENERALIZATION/COMPUTATIONAL-CHECKS/correlated_serial.py
python -B THEORY-GENERALIZATION/COMPUTATIONAL-CHECKS/oversight_counts.py
python -B THEORY-GENERALIZATION/VERIFICATION/VERIFY-A/replay_blind.py

lean +leanprover/lean4:v4.21.0 THEORY-GENERALIZATION/WORKSTREAMS/M01/BeliefCover.lean
lean +leanprover/lean4:v4.21.0 THEORY-GENERALIZATION/WORKSTREAMS/M02/Separator.lean
lean +leanprover/lean4:v4.21.0 THEORY-GENERALIZATION/WORKSTREAMS/M03/AnchorLogic.lean
lean +leanprover/lean4:v4.21.0 THEORY-GENERALIZATION/WORKSTREAMS/M04/AuditLogic.lean
lean +leanprover/lean4:v4.21.0 THEORY-GENERALIZATION/WORKSTREAMS/M05/EventMass.lean
lean +leanprover/lean4:v4.21.0 THEORY-GENERALIZATION/FORMAL-PROOFS/Frontier.lean
```

M01 uses exact finite supports and freeze values. M02 compares a factored authorized audit against explicit instances and checks masks, finite noisy posterior calculations and small quantified games. M03 and M04 use exact fractions for transport, acquisition, transcript-state testing and stopping controls. M05 compares monitor and paired-event bounds against exact finite enumeration. The flagship checks compare 998 online graphs and budgets, including 130 inconsistent cases, with explicit path values and test 63,424 static pair queries. The oversight checks compare 49 exact decision-tree counts and 75 noisy hitting/expectation bounds. The proof-blind replay adds distinct frontier and statistical test programs.

Lean checks the declared natural-budget transport lemma, two separator identities, selected mass/anchor and stochastic algebra, terminal-event identities and attained cap extremum operations. It does not formalize source-faithfulness, exact compile coverage, PSPACE reductions, full statistical concentration or the complete flagship theorem. Each general result has a separate prose proof. [Proof index and role seals](../FINAL-VERIFIED-PROOFS.md) · [Independent B replay](../VERIFICATION/VERIFY-B/REPLAY.md)

The [hostile replay](../HOSTILE-REVIEW/REPLAY.md) adds a separately implemented control. Run `python -B THEORY-GENERALIZATION/HOSTILE-REVIEW/replay.py` from repository root.
