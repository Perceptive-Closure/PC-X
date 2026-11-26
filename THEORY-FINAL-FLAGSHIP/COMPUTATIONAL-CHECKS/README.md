# Exact small fixtures and reproducibility

From the repository root run each constructor command.

    python -B THEORY-FINAL-FLAGSHIP/T30-P/check_finite.py
    python -B THEORY-FINAL-FLAGSHIP/T30-A/check_t30a.py
    python -B THEORY-FINAL-FLAGSHIP/T30-U/check_unified.py

Separate proof-blind implementations ran in distinct managed worktrees. After the documented statement-before-proof chronology, run their checks from the same published tree.

    python -B THEORY-FINAL-FLAGSHIP/VERIFICATION/T30-P/check_transport.py
    python -B THEORY-FINAL-FLAGSHIP/VERIFICATION/T30-A/check_receipts.py
    python -B THEORY-FINAL-FLAGSHIP/VERIFICATION/T30-U/check_unified.py

Each compares declared finite cases using exact rational or combinatorial arithmetic. Small symbolic or generated cases are mathematical checks. Their counts are not new prospective empirical observations. The distinct supporting Lean statements and compiler instructions are linked separately. [Formal checks](../FORMAL-PROOFS/README.md) · [Statement and proof chronology](../FINAL-VERIFIED-PROOFS.md)

The independent comparison and hostile replays add operational controls and the shared fixture.

    python -B THEORY-FINAL-FLAGSHIP/VERIFICATION/check_comparisons.py
    python -B THEORY-FINAL-FLAGSHIP/HOSTILE-REVIEW/check_hostile.py
    python -B THEORY-FINAL-FLAGSHIP/HOSTILE-REVIEW/check_unified.py
    lean THEORY-FINAL-FLAGSHIP/HOSTILE-REVIEW/FullCutEnvelope.lean
