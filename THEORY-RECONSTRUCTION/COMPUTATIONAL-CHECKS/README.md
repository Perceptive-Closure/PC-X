# Supplemental proof and counterexample checks

From repository root run:

```powershell
lean +leanprover/lean4:v4.21.0 THEORY-RECONSTRUCTION/COMPUTATIONAL-CHECKS/MathCore.lean
python -B THEORY-RECONSTRUCTION/COMPUTATIONAL-CHECKS/finite_foundation.py
```

The Lean file imports only Std. It establishes the deterministic disagreement equivalence and reachable-cell fact. It also checks whole-belief transition cover, enabling and stopping invariance, and policy-budget invariance for kernel relations over a previously shared visible alphabet and natural costs. The accompanying prose proves the observation-consistent label correspondence and real nonnegative-cost statement.

The Python check compares 4,096 base support graphs and their hidden lifts under four masks at bounded depth, and confirms three explicit boundary examples. It imports only the standard library and does not need downloads or writable experiment directories. The finite runs are supplemental.


Additional finite and arithmetic checks run from the repository root.

    python -B THEORY-RECONSTRUCTION/COMPUTATIONAL-CHECKS/scope_boundaries.py
    python -B THEORY-RECONSTRUCTION/WORKSTREAMS/flagship/check_flagship.py
    lean +leanprover/lean4:v4.21.0 THEORY-RECONSTRUCTION/WORKSTREAMS/flagship/CappedSum.lean
    lean +leanprover/lean4:v4.21.0 THEORY-RECONSTRUCTION/WORKSTREAMS/governance/readback_cover.lean

The original corpus and other check commands are referenced in the individual workstream paths. The scope verifier uses exact fractions and finite supported choices.
