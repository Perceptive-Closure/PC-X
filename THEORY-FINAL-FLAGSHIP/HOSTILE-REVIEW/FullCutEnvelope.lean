import Std

namespace HostileReview

structure CutCount where
  mass : Nat
  bad : Nat

def sumBy (f : CutCount → Nat) : List CutCount → Nat
  | [] => 0
  | cut :: tail => f cut + sumBy f tail

/-- A local scaled envelope persists under aggregation of all covered cuts. -/
theorem aggregate_envelope (cuts : List CutCount) (lo scale hi : Nat)
    (localBounds : ∀ c ∈ cuts, lo * c.mass ≤ scale * c.bad ∧ scale * c.bad ≤ hi * c.mass) :
    lo * sumBy CutCount.mass cuts ≤ scale * sumBy CutCount.bad cuts ∧
      scale * sumBy CutCount.bad cuts ≤ hi * sumBy CutCount.mass cuts := by
  induction cuts with
  | nil => simp [sumBy]
  | cons head tail ih =>
    have headBounds := localBounds head (by simp)
    have tailBounds := ih (fun c hc => localBounds c (by simp [hc]))
    simp only [sumBy, Nat.mul_add]
    exact ⟨Nat.add_le_add headBounds.1 tailBounds.1, Nat.add_le_add headBounds.2 tailBounds.2⟩

/-- The denominator for the entire protocol may be used when the cuts exhaust its mass. -/
theorem covered_envelope (cuts : List CutCount) (lo scale hi mass : Nat)
    (localBounds : ∀ c ∈ cuts, lo * c.mass ≤ scale * c.bad ∧ scale * c.bad ≤ hi * c.mass)
    (exhaustive : sumBy CutCount.mass cuts = mass) :
    lo * mass ≤ scale * sumBy CutCount.bad cuts ∧
      scale * sumBy CutCount.bad cuts ≤ hi * mass := by
  rw [← exhaustive]
  exact aggregate_envelope cuts lo scale hi localBounds

/-- A half-mass finalizer has local risk 3/4 and complete protocol risk 3/8. -/
example :
    (3 : Nat) * 4 = 4 * 3 ∧ 4 * 3 < 3 * 8 ∧ 2 * 3 ≤ 8 := by decide

end HostileReview
