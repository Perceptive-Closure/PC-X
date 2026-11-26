import Init

/-! Exact preservation of future feasibility by a verified common projection.
The concrete finite-domain path decomposition provides the gluing hypothesis. -/

namespace PCX.M02

def Projected {L K : Type} (key : L → K) (past : L → Prop) (k : K) : Prop :=
  ∃ l, past l ∧ key l = k

theorem projection_preserves_feasibility
    {Whole L R K : Type} (left : Whole → L) (right : Whole → R)
    (leftKey : L → K) (rightKey : R → K)
    (agree : ∀ w, leftKey (left w) = rightKey (right w))
    (glue : ∀ l r, leftKey l = rightKey r →
      ∃ w, left w = l ∧ right w = r)
    (past : L → Prop) (future : R → Prop) :
    (∃ w, past (left w) ∧ future (right w)) ↔
      ∃ r, future r ∧ Projected leftKey past (rightKey r) := by
  constructor
  · rintro ⟨w, validPast, validFuture⟩
    exact ⟨right w, validFuture, left w, validPast, agree w⟩
  · rintro ⟨r, validFuture, l, validPast, matchingKeys⟩
    obtain ⟨w, leftEq, rightEq⟩ := glue l r matchingKeys
    exact ⟨w, leftEq.symm ▸ validPast, rightEq.symm ▸ validFuture⟩

theorem same_projection_same_reply
    {Whole L R K : Type} (left : Whole → L) (right : Whole → R)
    (leftKey : L → K) (rightKey : R → K)
    (agree : ∀ w, leftKey (left w) = rightKey (right w))
    (glue : ∀ l r, leftKey l = rightKey r →
      ∃ w, left w = l ∧ right w = r)
    (past₁ past₂ : L → Prop) (future : R → Prop)
    (same : ∀ k, Projected leftKey past₁ k ↔ Projected leftKey past₂ k) :
    (∃ w, past₁ (left w) ∧ future (right w)) ↔
      (∃ w, past₂ (left w) ∧ future (right w)) := by
  have first := projection_preserves_feasibility left right leftKey rightKey agree glue past₁ future
  have second := projection_preserves_feasibility left right leftKey rightKey agree glue past₂ future
  constructor
  · intro witness
    obtain ⟨r, valid, old⟩ := first.mp witness
    exact second.mpr ⟨r, valid, (same (rightKey r)).mp old⟩
  · intro witness
    obtain ⟨r, valid, old⟩ := second.mp witness
    exact first.mpr ⟨r, valid, (same (rightKey r)).mpr old⟩

#print axioms projection_preserves_feasibility
#print axioms same_projection_same_reply

end PCX.M02
