# M04 computational and formal checks

The constructor ran these commands on 27 November 2026 from the project root using Python 3.13 and Lean 4.21.0.

    py -B THEORY-GENERALIZATION/WORKSTREAMS/M04/check_finite.py
    lean THEORY-GENERALIZATION/WORKSTREAMS/M04/AuditLogic.lean

| Test | Independent finite computation | Observed result |
| --- | --- | --- |
| Composite feasibility | Rational three-variable test LP solved by active-constraint enumeration and independently compared with exact shared-mixture or prior-breakpoint overlaps | Intersecting hulls require worst failure 1/2 despite positive simple distances. Disjoint example has worst failure 1/4 at optimal unequal weight versus equal-prior error 1/6. |
| Complete records | Enumerate both joint supports and each marginal | Both pairs of marginal supports agree and the two full records have disjoint support. |
| Sequence risks | Enumerate 256 pure cue-contingent test plans and compare an explicit private mixture's leaf probabilities with independent sequence-flow sums | Four pure plans win, all selecting the cue-matched probe. Open-loop one-probe error is 1/4. |
| Private-bit challenge | Enumerate both nonanticipating guesses and the anticipatory choice | Erasure probabilities 1/2 and 1 respectively; exact symmetric failure 1/4 and 1/2. |
| Strategic interval | Compare full enumeration of the 128 endpoint plans per label with a dynamic conditional recurrence for three draws | The majority test has a worst failure of 5/32 for each class. |
| Stopped audit | Analyze the shared geometric erasure paths at caps 1 through 12, the capped mixture-confidence counterexample and a one-probe acquisition objective | Exact zero-error rule has expected cost 3 and each finite cap leaves positive risk. Anytime ratio stays below 3/2 through the separate histogram cap. Exact worst expected cost at 2/5 failure is 3/5, above the count relaxation. |

The checks use exact fractions for record laws, endpoint choices, decisions, witness costs and geometric tail comparisons. Floating point appears in the comparisons of an analytic histogram radius and KL function; their inequalities have ample strict margin. The test LP reimplementation is intentionally limited to the finite two-symbol fixture.

[AuditLogic.lean](AuditLogic.lean) verifies four elementary lemmas on natural-valued scaled record masses and accumulated costs: pointwise weighted overlap lower bound and attainment, the shared-law failure-sum bound including abstention, and the per-path price implication after a cap. For rational weights the first three apply after clearing denominators. The machine check covers those local inequalities. The minimax exchange, sequence form, martingale argument, and expected-cost compactness use the complete [prose proof](PROOF.md). Independent mathematical review and hostile corroboration are separate records.
