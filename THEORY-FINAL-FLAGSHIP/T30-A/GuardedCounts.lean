namespace T30A

def badCount : List Bool → Nat
  | [] => 0
  | false :: samples => badCount samples
  | true :: samples => badCount samples + 1

def goodCount : List Bool → Nat
  | [] => 0
  | false :: samples => goodCount samples + 1
  | true :: samples => goodCount samples

def finalizeOutcomes : List Bool → List Bool → List Bool
  | [], _ => []
  | bit :: words, extra =>
    extra.map (fun value => bit || value) ++ finalizeOutcomes words extra

theorem badCount_append (xs ys : List Bool) :
    badCount (xs ++ ys) = badCount xs + badCount ys := by
  induction xs with
  | nil => simp [badCount]
  | cons bit tail ih =>
    cases bit <;> simp [badCount, ih, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm]

theorem badCount_all (xs : List Bool) :
    badCount (xs.map (fun _ => true)) = xs.length := by
  induction xs with
  | nil => simp [badCount]
  | cons bit tail ih => simp [badCount, ih]

theorem full_support_partition (xs : List Bool) :
    badCount xs + goodCount xs = xs.length := by
  induction xs with
  | nil => simp [badCount, goodCount]
  | cons bit tail ih =>
    cases bit <;> simp [badCount, goodCount, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm] at *
    all_goals omega

theorem violation_count (words extra : List Bool) :
    badCount (finalizeOutcomes words extra) =
      badCount words * extra.length + goodCount words * badCount extra := by
  induction words with
  | nil => simp [finalizeOutcomes, badCount, goodCount]
  | cons bit tail ih =>
    cases bit <;>
      simp [finalizeOutcomes, badCount, goodCount, badCount_append, badCount_all,
        ih, Nat.add_mul, Nat.add_assoc, Nat.add_left_comm, Nat.add_comm]

theorem cut_count_bounds (bad good total lower actual upper : Nat)
    (below : lower ≤ actual) (above : actual ≤ upper) :
    bad * total + good * lower ≤ bad * total + good * actual ∧
      bad * total + good * actual ≤ bad * total + good * upper :=
  ⟨Nat.add_le_add_left (Nat.mul_le_mul_left good below) (bad * total),
   Nat.add_le_add_left (Nat.mul_le_mul_left good above) (bad * total)⟩

theorem fixture_positive_count :
    badCount (finalizeOutcomes [true, false, false, false] [true, false, false, false]) = 7 := rfl

theorem fixture_negative_count :
    badCount (finalizeOutcomes [true, true, true, false] [true, false, false, false]) = 13 := rfl

end T30A
