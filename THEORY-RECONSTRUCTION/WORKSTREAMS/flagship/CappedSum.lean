import Std

namespace PCX

/-- Positive increment preserves the information retained by an overflow cap. -/
theorem capped_addition (cap a b : Nat) :
    min cap (min cap a + b) = min cap (a + b) := by
  omega

/-- Overflow leaves a nonnegative integer deadline comparison invariant. -/
theorem capped_at_deadline (budget time : Nat) :
    min (budget + 1) time ≤ budget ↔ time ≤ budget := by
  omega

end PCX
