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

## Complete reconstruction checks

The whole package can be checked from the repository root using Python 3 and the stated Lean toolchain. The previous section covers the parent and Lean cases. Run the independently released and constructor checks with:

```powershell
python -B THEORY-RECONSTRUCTION/WORKSTREAMS/foundation/check_foundation.py
python -B THEORY-RECONSTRUCTION/WORKSTREAMS/exact/check_candidates.py
python -B THEORY-RECONSTRUCTION/VERIFICATION/initial/boundary_replay.py
python -B THEORY-RECONSTRUCTION/WORKSTREAMS/deployment/check_deployment.py --intake 'path/to/verified-intake'
python -B THEORY-RECONSTRUCTION/WORKSTREAMS/governance/check_candidates.py
python -B THEORY-RECONSTRUCTION/VERIFICATION/hostile/replay_boundaries.py
```

For the deployment check, put the respective full GitHub source archives under `X08`, `X09`, `X11` and `X12` in the intake directory. The archive layout is `<intake>/X08/EXPERIMENTS/EXP-X08/` and analogously for the other pins, with the ZIP wrapper directory removed. Verify the archive blob hashes and lengths against the immutable Git tree. The check validates the retained raw ledger digests again before reading archived outcomes. Other scripts run on their finite constructed inputs. [Exact source pins](../SOURCE-PINS.json) · [Source retrieval receipts](../SOURCE-RETRIEVAL.json)
