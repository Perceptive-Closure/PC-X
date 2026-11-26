import Std

namespace PCX

def clip (cap score : Nat) : Nat := min cap score

theorem clip_add (cap score tariff : Nat) :
    clip cap (clip cap score + tariff) = clip cap (score + tariff) := by
  unfold clip
  omega

def HasExtrema (scores : Nat → Prop) (lower upper : Nat) : Prop :=
  scores lower ∧ scores upper ∧ ∀ score, scores score → lower ≤ score ∧ score ≤ upper

theorem clippedImageExtrema {scores : Nat → Prop} {lower upper : Nat}
    (valid : HasExtrema scores lower upper) (cap tariff : Nat) :
    HasExtrema (fun output => ∃ score, scores score ∧ output = clip cap (score + tariff))
      (clip cap (lower + tariff)) (clip cap (upper + tariff)) := by
  obtain ⟨lowerIn, upperIn, orders⟩ := valid
  refine ⟨⟨lower, lowerIn, rfl⟩, ⟨upper, upperIn, rfl⟩, ?_⟩
  intro output member
  obtain ⟨score, scoreIn, equation⟩ := member
  have inequalities := orders score scoreIn
  unfold clip at *
  omega

theorem unionExtrema {left right : Nat → Prop} {l1 u1 l2 u2 : Nat}
    (first : HasExtrema left l1 u1) (second : HasExtrema right l2 u2) :
    HasExtrema (fun score => left score ∨ right score) (min l1 l2) (max u1 u2) := by
  obtain ⟨firstLower, firstUpper, firstOrders⟩ := first
  obtain ⟨secondLower, secondUpper, secondOrders⟩ := second
  refine ⟨?_, ?_, ?_⟩
  · by_cases smaller : l1 ≤ l2
    · rw [Nat.min_eq_left smaller]
      exact Or.inl firstLower
    · have reverse : l2 ≤ l1 := by omega
      rw [Nat.min_eq_right reverse]
      exact Or.inr secondLower
  · by_cases larger : u2 ≤ u1
    · rw [Nat.max_eq_left larger]
      exact Or.inl firstUpper
    · have reverse : u1 ≤ u2 := by omega
      rw [Nat.max_eq_right reverse]
      exact Or.inr secondUpper
  · intro score member
    rcases member with firstIn | secondIn
    · have inequalities := firstOrders score firstIn
      omega
    · have inequalities := secondOrders score secondIn
      omega

#print axioms clip_add
#print axioms clippedImageExtrema
#print axioms unionExtrema

end PCX
