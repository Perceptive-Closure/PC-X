import Std

namespace PCXGovernance

def Included {U : Type} (left right : U → Prop) : Prop :=
  ∀ ⦃u⦄, left u → right u

def AnswerCell {U Q : Type} {D : Q → Type}
    (domain : U → Prop) (answer : (q : Q) → U → D q)
    (chosen : Q → Prop) (representative : U) : U → Prop :=
  fun u => domain u ∧ ∀ q, chosen q → answer q u = answer q representative

def Split {U Q : Type} {D : Q → Type} (answer : (q : Q) → U → D q)
    (chosen : Q → Prop) (family : U → Prop) : Prop :=
  ∃ q, chosen q ∧ ∃ x y, family x ∧ family y ∧ answer q x ≠ answer q y

/-- The equivalence holds for any exhaustive family of nonempty obstructions.
    For T29.b the finite deletion proof constructs that family. -/
theorem exactReadbackCover {U Q : Type} {D : Q → Type}
    (domain : U → Prop) (answer : (q : Q) → U → D q) (chosen : Q → Prop)
    (ready obstruction : (U → Prop) → Prop)
    (hereditary : ∀ {s t}, Included s t → ready t → ready s)
    (inside : ∀ {s}, obstruction s → Included s domain)
    (nonempty : ∀ {s}, obstruction s → ∃ u, s u)
    (losing : ∀ {s}, obstruction s → ¬ ready s)
    (complete : ∀ {s}, Included s domain → (∃ u, s u) → ¬ ready s →
      ∃ t, obstruction t ∧ Included t s) :
    (∀ u, domain u → ready (AnswerCell domain answer chosen u)) ↔
      (∀ s, obstruction s → Split answer chosen s) := by
  constructor
  · intro wins failure isObstruction
    apply Classical.byContradiction
    intro notSplit
    obtain ⟨u, hu⟩ := nonempty isObstruction
    have covered : Included failure (AnswerCell domain answer chosen u) := by
      intro v hv
      refine ⟨inside isObstruction hv, ?_⟩
      intro q isChosen
      apply Classical.byContradiction
      intro distinct
      exact notSplit ⟨q, isChosen, v, u, hv, hu, distinct⟩
    exact losing isObstruction (hereditary covered (wins u (inside isObstruction hu)))
  · intro splits u hu
    apply Classical.byContradiction
    intro noWin
    have rooted : AnswerCell domain answer chosen u u :=
      ⟨hu, fun _ _ => rfl⟩
    have contained : Included (AnswerCell domain answer chosen u) domain := by
      intro v hv
      exact hv.1
    obtain ⟨s, isObstruction, within⟩ := complete contained ⟨u, rooted⟩ noWin
    obtain ⟨q, isChosen, x, y, hx, hy, differs⟩ := splits s isObstruction
    exact differs (((within hx).2 q isChosen).trans ((within hy).2 q isChosen).symm)

#print axioms exactReadbackCover

end PCXGovernance
