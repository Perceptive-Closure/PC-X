# Selected machine-checked results

Lean 4.21.0 checks finite algebraic and logical components of this campaign. These results are narrower than the written proofs. No Lean file independently verifies the full source correspondences, statistical sampling assumptions, LP optimality model, external validity or the complete three theorem packages.

- T30.P constructor finite realization and event lemmas. [CoreChecks.lean](../T30-P/CoreChecks.lean)
- T30.A constructor guarded counting and monotonicity. [GuardedCounts.lean](../T30-A/GuardedCounts.lean)
- T30.U constructor scaled masses, common-factor cancellation and calibrated selective numerator inequality. [SelectedLemmas.lean](../T30-U/SelectedLemmas.lean)
- Independent scaled versions and direct checks remain under each theorem's verification directory. [A](../VERIFICATION/T30-A/ReceiptOdds.lean) · [P](../VERIFICATION/T30-P/RobustGuard.lean) · [U](../VERIFICATION/T30-U/UnifiedBounds.lean)

The separate hostile replay also checks the finite full-cut envelope in [FullCutEnvelope.lean](../HOSTILE-REVIEW/FullCutEnvelope.lean).

From repository root run `lean` followed by each explicit file path. Nonproof fixture replays and source hashes have their own records. [Computational instructions](../COMPUTATIONAL-CHECKS/README.md)
