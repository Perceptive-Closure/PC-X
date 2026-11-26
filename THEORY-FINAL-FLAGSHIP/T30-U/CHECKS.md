# T30.U selected checks

Run from the repository root.

    python -B THEORY-FINAL-FLAGSHIP/T30-U/check_unified.py
    lean THEORY-FINAL-FLAGSHIP/T30-U/SelectedLemmas.lean

The Python checker uses exact rational arithmetic. It explicitly expands small histories and compares five distinct fixed-world expectations with the reference-posterior policy, including a genuine responder-dependent note. Its additional likelihood recursion counts the compressed prelude states without explicit exponential enumeration. It checks the six pure single-opportunity tests against the lower supporting line and verifies exact matched prices and risk and utility values at five error levels. The Lean code checks common policy-factor cancellation and mass scaling on exact integer encodings, and the covered-versus-exposed numerator inequality used in U.3. These are supporting checks. The two programs do not formalize the complete theorem, source membership or a deployment experiment.
