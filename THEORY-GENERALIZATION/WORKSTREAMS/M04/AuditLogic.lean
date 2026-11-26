namespace M04

theorem overlap_lower_bound (u v miss pass : Nat) :
    min u v * (miss + pass) ≤ u * miss + v * pass := by
  rw [Nat.mul_add]
  exact Nat.add_le_add
    (Nat.mul_le_mul_right miss (Nat.min_le_left u v))
    (Nat.mul_le_mul_right pass (Nat.min_le_right u v))

theorem overlap_attained (u v denom : Nat) :
    ∃ miss pass : Nat, miss + pass = denom ∧
      u * miss + v * pass = min u v * denom := by
  by_cases h : u ≤ v
  · exact ⟨denom, 0, by simp, by simp [Nat.min_eq_left h]⟩
  · have h' : v ≤ u := Nat.le_of_lt (Nat.lt_of_not_ge h)
    exact ⟨0, denom, by simp, by simp [Nat.min_eq_right h']⟩

theorem shared_law_failure_bound (pass fail abstain : Nat) :
    pass + fail + abstain ≤ (fail + abstain) + (pass + abstain) := by
  omega

theorem truncated_path_cost_bound (floor horizon probes cost : Nat)
    (continued : horizon < probes) (priced : floor * probes ≤ cost) :
    floor * (horizon + 1) ≤ cost := by
  exact Nat.le_trans (Nat.mul_le_mul_left floor (Nat.succ_le_of_lt continued)) priced

end M04
