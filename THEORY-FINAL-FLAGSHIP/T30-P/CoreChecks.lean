import Std

namespace T30P

structure CoveredRow where
  lower : Nat
  actual : Nat
  sound : lower ≤ actual

def rowProduct : List Nat → Nat
  | [] => 1
  | value :: rest => value * rowProduct rest

theorem lower_product_le (rows : List CoveredRow) :
    rowProduct (rows.map CoveredRow.lower) ≤ rowProduct (rows.map CoveredRow.actual) := by
  induction rows with
  | nil => simp [rowProduct]
  | cons row rows smaller =>
    simp only [List.map_cons, rowProduct]
    exact Nat.mul_le_mul row.sound smaller

structure Leaf where
  component : Nat
  chance : Nat
  realization : Nat
  marked : Bool

def markedWeight (leaf : Leaf) : Nat :=
  if leaf.marked then leaf.component * (leaf.chance * leaf.realization) else 0

def markedMass : List Leaf → Nat
  | [] => 0
  | leaf :: rest => markedWeight leaf + markedMass rest

theorem all_weights_zero (leaves : List Leaf) :
    markedMass leaves = 0 ↔ ∀ leaf ∈ leaves, markedWeight leaf = 0 := by
  induction leaves with
  | nil => simp [markedMass]
  | cons head rest ih =>
    constructor
    · intro zero leaf mem
      have zeroSum : markedWeight head + markedMass rest = 0 := zero
      have headZero : markedWeight head = 0 := by omega
      have tailZero : markedMass rest = 0 := by omega
      rcases List.mem_cons.mp mem with same | later
      · rw [same]
        exact headZero
      · exact ih.mp tailZero leaf later
    · intro vanish
      have headZero := vanish head (List.mem_cons_self)
      have tailZero := ih.mpr (fun leaf mem => vanish leaf (List.mem_cons_of_mem head mem))
      simp [markedMass, headZero, tailZero]

theorem empty_marked_support (leaves : List Leaf) :
    markedMass leaves = 0 ↔
      ∀ leaf ∈ leaves, leaf.marked = true →
        leaf.component = 0 ∨ leaf.chance = 0 ∨ leaf.realization = 0 := by
  rw [all_weights_zero]
  constructor
  · intro zero leaf present marked
    have leafZero := zero leaf present
    simpa [markedWeight, marked, Nat.mul_eq_zero] using leafZero
  · intro zero leaf present
    cases marked : leaf.marked
    · simp [markedWeight, marked]
    · have oneZero := zero leaf present marked
      simpa [markedWeight, marked, Nat.mul_eq_zero] using oneZero

def Survives {World Read : Type}
    (blocker : World → Prop) (selected : Read → Prop)
    (agrees : World → Read → Prop) : Prop :=
  ∀ world, blocker world → ∀ field, selected field → agrees world field

def Hits {World Read : Type}
    (blocker : World → Prop) (selected : Read → Prop)
    (agrees : World → Read → Prop) : Prop :=
  ∃ field, selected field ∧ ∃ world, blocker world ∧ ¬agrees world field

theorem blocked_group_removed_iff_hit {World Read : Type}
    (blocker : World → Prop) (selected : Read → Prop)
    (agrees : World → Read → Prop) :
    ¬Survives blocker selected agrees ↔ Hits blocker selected agrees := by
  constructor
  · intro fail
    apply Classical.byContradiction
    intro misses
    apply fail
    intro world member field taken
    apply Classical.byContradiction
    intro rejects
    apply misses
    exact ⟨field, taken, world, member, rejects⟩
  · intro hits survives
    obtain ⟨field, taken, world, member, rejects⟩ := hits
    exact rejects (survives world member field taken)

end T30P
