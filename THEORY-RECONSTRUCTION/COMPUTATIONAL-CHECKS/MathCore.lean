import Std

namespace PCX

/-- A response coordinate agrees along all selected, lawful observations. -/
def AgreeOn {C Q V : Type} (answer : Q → C → V) (selected : Q → Prop)
    (x y : C) : Prop :=
  ∀ q, selected q → answer q x = answer q y

/-- Sound identification is target constancy on each attainable cell. -/
def Determines {C O T : Type} (admissible : C → Prop) (obs : C → O)
    (target : C → T) : Prop :=
  ∀ x y, admissible x → admissible y → obs x = obs y → target x = target y

theorem attainableCellHasUniqueTarget {C O T : Type}
    {admissible : C → Prop} {obs : C → O} {target : C → T}
    (sound : Determines admissible obs target) (o : O)
    (attainable : ∃ x, admissible x ∧ obs x = o) :
    ∃ t, (∃ x, admissible x ∧ obs x = o ∧ target x = t) ∧
      (∀ y, admissible y → obs y = o → target y = t) := by
  obtain ⟨x, legal, observed⟩ := attainable
  exact ⟨target x, ⟨x, legal, observed, rfl⟩,
    fun y ly oy => sound y x ly legal (oy.trans observed.symm)⟩

theorem disagreementCharacterization {C Q V T : Type}
    (D : C → Prop) (answer : Q → C → V) (selected : Q → Prop) (target : C → T) :
    (∀ x y, D x → D y → AgreeOn answer selected x y → target x = target y) ↔
    (∀ x y, D x → D y → target x ≠ target y →
      ∃ q, selected q ∧ answer q x ≠ answer q y) := by
  classical
  constructor
  · intro h x y dx dy different
    apply Classical.byContradiction
    intro noSeparator
    apply different
    apply h x y dx dy
    intro q sq
    apply Classical.byContradiction
    intro unequal
    exact noSeparator ⟨q, sq, unequal⟩
  · intro h x y dx dy same
    apply Classical.byContradiction
    intro different
    obtain ⟨q, sq, diff⟩ := h x y dx dy different
    exact diff (same q sq)

/-- Two information sets have a two-way total, typed support relation. -/
def Cover {S T : Type} (R : S → T → Prop) (B : S → Prop) (C : T → Prop) : Prop :=
  (∀ s, B s → ∃ t, C t ∧ R s t) ∧
  (∀ t, C t → ∃ s, B s ∧ R s t)

structure Kernel (S A Y : Type) where
  legal : S → A → Prop
  transition : S → A → Y → S → Prop
  closed : S → Prop

/-- Interfaces have already been mapped to shared action and observation labels. -/
structure Matches {S T A Y : Type} (L : Kernel S A Y) (R : Kernel T A Y)
    (rel : S → T → Prop) : Prop where
  legal : ∀ s t, rel s t → ∀ a, L.legal s a ↔ R.legal t a
  closed : ∀ s t, rel s t → (L.closed s ↔ R.closed t)
  forth : ∀ s t, rel s t → ∀ a y u, L.transition s a y u →
    ∃ v, R.transition t a y v ∧ rel u v
  back : ∀ s t, rel s t → ∀ a y v, R.transition t a y v →
    ∃ u, L.transition s a y u ∧ rel u v

def post {S A Y : Type} (K : Kernel S A Y) (B : S → Prop) (a : A) (y : Y)
    (u : S) : Prop :=
  ∃ s, B s ∧ K.transition s a y u

theorem postCover {S T A Y : Type} {L : Kernel S A Y} {R : Kernel T A Y}
    {rel : S → T → Prop} (m : Matches L R rel)
    {B : S → Prop} {C : T → Prop} (cov : Cover rel B C) (a : A) (y : Y) :
    Cover rel (post L B a y) (post R C a y) := by
  constructor
  · intro u hu
    obtain ⟨s, hs, edge⟩ := hu
    obtain ⟨t, ht, hrel⟩ := cov.1 s hs
    obtain ⟨v, step, rv⟩ := m.forth s t hrel a y u edge
    exact ⟨v, ⟨t, ht, step⟩, rv⟩
  · intro v hv
    obtain ⟨t, ht, edge⟩ := hv
    obtain ⟨s, hs, hrel⟩ := cov.2 t ht
    obtain ⟨u, step, ru⟩ := m.back s t hrel a y v edge
    exact ⟨u, ⟨s, hs, step⟩, ru⟩

theorem allClosedEqual {S T A Y : Type} {L : Kernel S A Y} {R : Kernel T A Y}
    {rel : S → T → Prop} (m : Matches L R rel)
    {B : S → Prop} {C : T → Prop} (cov : Cover rel B C) :
    (∀ s, B s → L.closed s) ↔ (∀ t, C t → R.closed t) := by
  constructor
  · intro h t ht
    obtain ⟨s, hs, related⟩ := cov.2 t ht
    exact (m.closed s t related).mp (h s hs)
  · intro h s hs
    obtain ⟨t, ht, related⟩ := cov.1 s hs
    exact (m.closed s t related).mpr (h t ht)

theorem commonLegalEqual {S T A Y : Type} {L : Kernel S A Y} {R : Kernel T A Y}
    {rel : S → T → Prop} (m : Matches L R rel)
    {B : S → Prop} {C : T → Prop} (cov : Cover rel B C) (a : A) :
    (∀ s, B s → L.legal s a) ↔ (∀ t, C t → R.legal t a) := by
  constructor
  · intro h t ht
    obtain ⟨s, hs, related⟩ := cov.2 t ht
    exact (m.legal s t related a).mp (h s hs)
  · intro h s hs
    obtain ⟨t, ht, related⟩ := cov.1 s hs
    exact (m.legal s t related a).mpr (h t ht)

theorem emptyEqual {S T : Type} {rel : S → T → Prop}
    {B : S → Prop} {C : T → Prop} (cov : Cover rel B C) :
    (∀ s, ¬ B s) ↔ (∀ t, ¬ C t) := by
  constructor
  · intro h t ht
    obtain ⟨s, hs, _⟩ := cov.2 t ht
    exact h s hs
  · intro h s hs
    obtain ⟨t, ht, _⟩ := cov.1 s hs
    exact h t ht

/-- One continuation per visible label, irrespective of hidden state. -/
inductive Policy (A Y : Type) where
  | stop : Policy A Y
  | act : A → (Y → Policy A Y) → Policy A Y

/-- An unreachable child imposes no budget or legality requirement. -/
def within {S A Y : Type} (K : Kernel S A Y) (cost : A → Nat) :
    Policy A Y → (S → Prop) → Nat → Prop
  | .stop, B, _ => ∀ s, B s → K.closed s
  | .act a next, B, n =>
    (∀ s, ¬ B s) ∨ (cost a ≤ n ∧
      (∀ s, B s → K.legal s a) ∧
      ∀ y, within K cost (next y) (post K B a y) (n - cost a))

theorem budgetPolicyInvariant {S T A Y : Type}
    {L : Kernel S A Y} {R : Kernel T A Y} {rel : S → T → Prop}
    (m : Matches L R rel) (cost : A → Nat) (p : Policy A Y)
    (B : S → Prop) (C : T → Prop) (cov : Cover rel B C) (n : Nat) :
    within L cost p B n ↔ within R cost p C n := by
  induction p generalizing B C n with
  | stop =>
    exact allClosedEqual m cov
  | act a next ih =>
    change (_ ∨ (_ ∧ _ ∧ _)) ↔ (_ ∨ (_ ∧ _ ∧ _))
    constructor
    · intro h
      apply h.elim
      · intro e
        exact Or.inl ((emptyEqual cov).mp e)
      · intro ⟨budget, enabled, more⟩
        apply Or.inr
        exact ⟨budget, (commonLegalEqual m cov a).mp enabled,
          fun y => (ih y _ _ (postCover m cov a y) _).mp (more y)⟩
    · intro h
      apply h.elim
      · intro e
        exact Or.inl ((emptyEqual cov).mpr e)
      · intro ⟨budget, enabled, more⟩
        apply Or.inr
        exact ⟨budget, (commonLegalEqual m cov a).mpr enabled,
          fun y => (ih y _ _ (postCover m cov a y) _).mpr (more y)⟩

end PCX
