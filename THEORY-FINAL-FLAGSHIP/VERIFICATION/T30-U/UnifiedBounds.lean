namespace FlagshipU

theorem routing_paid_mass_lower_bound (total wrongBudget paid : Nat)
    (bayesBudget : 2 * total ≤ 4 * wrongBudget + paid) :
    2 * total - 4 * wrongBudget ≤ paid := by
  omega

theorem calibration_contamination_at_two_fifths
    (good bad goodViolations badViolations : Nat)
    (goodCap : 5 * goodViolations ≤ 2 * good)
    (badBound : badViolations ≤ bad) :
    5 * (goodViolations + badViolations) ≤ 2 * (good + bad) + 3 * bad := by
  omega

end FlagshipU
