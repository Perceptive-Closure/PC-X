namespace FlagshipA

theorem odds_excess_ones (a b common excess : Nat) :
    a ^ (common + excess) * b ^ common * b ^ excess =
      b ^ (common + excess) * a ^ common * a ^ excess := by
  simp only [Nat.pow_add]
  ac_rfl

theorem opposite_declarations_cover_at_most_total
    (total positive negative abstain : Nat)
    (partition : positive + negative + abstain = total) :
    total ≤ (negative + abstain) + (positive + abstain) := by
  omega

end FlagshipA
