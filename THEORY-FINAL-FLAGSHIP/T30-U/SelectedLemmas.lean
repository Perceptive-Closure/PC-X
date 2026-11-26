import Std

namespace PCXFlagship

theorem cancelCommonFactor (policy likelihood normalizer : Nat) :
    (policy * likelihood) * normalizer = likelihood * (policy * normalizer) := by
  ac_rfl

theorem sumScaled (policy : Nat) (masses : List Nat) :
    (masses.map (fun m => policy * m)).sum = policy * masses.sum := by
  induction masses with
  | nil => simp
  | cons head tail ih =>
    simp [ih, Nat.mul_add]

theorem selectiveLoss
    (den eps covered exposed lossCovered lossExposed : Nat)
    (hEps : eps ≤ den)
    (hCovered : den * lossCovered ≤ eps * covered)
    (hExposed : lossExposed ≤ exposed) :
    den * (lossCovered + lossExposed) ≤
      eps * (covered + exposed) + (den - eps) * exposed := by
  have total : eps + (den - eps) = den := by omega
  calc
    den * (lossCovered + lossExposed) =
        den * lossCovered + den * lossExposed := Nat.mul_add _ _ _
    _ ≤ eps * covered + den * exposed :=
        Nat.add_le_add hCovered (Nat.mul_le_mul_left den hExposed)
    _ = eps * covered + (eps + (den - eps)) * exposed := by rw [total]
    _ = eps * (covered + exposed) + (den - eps) * exposed := by
        rw [Nat.add_mul, Nat.mul_add, Nat.add_assoc]

#print axioms cancelCommonFactor
#print axioms sumScaled
#print axioms selectiveLoss

end PCXFlagship
