namespace M03

def Hits {Fact : Type} (selected : Fact → Prop)
    (family : (Fact → Prop) → Prop) : Prop :=
  ∀ edge, family edge → ∃ i, selected i ∧ edge i

theorem sufficiency_iff_hitting {World Fact : Type}
    (selected : Fact → Prop) (admits : Fact → World → Prop)
    (opposes : World → Prop) :
    (∀ w, (∀ i, selected i → admits i w) → ¬ opposes w) ↔
      (∀ w, opposes w → ∃ i, selected i ∧ ¬ admits i w) := by
  constructor
  · intro sufficient w opposing
    apply Classical.byContradiction
    intro misses
    apply sufficient w _ opposing
    intro i taken
    apply Classical.byContradiction
    intro failure
    exact misses ⟨i, taken, failure⟩
  · intro hits w consistent opposing
    obtain ⟨i, taken, failure⟩ := hits w opposing
    exact failure (consistent i taken)

theorem disjoint_witness_is_new {Fact : Type}
    (selected edge : Fact → Prop) (discovered : (Fact → Prop) → Prop)
    (hits : Hits selected discovered)
    (misses : ∀ i, selected i → ¬ edge i) :
    ¬ discovered edge := by
  intro known
  obtain ⟨i, taken, violation⟩ := hits edge known
  exact misses i taken violation

theorem master_optimality {Fact Cost : Type} [LE Cost]
    (candidate : Fact → Prop) (cost : (Fact → Prop) → Cost)
    (discovered full : (Fact → Prop) → Prop)
    (subset : ∀ edge, discovered edge → full edge)
    (masterMin : ∀ other, Hits other discovered → cost candidate ≤ cost other) :
    ∀ other, Hits other full → cost candidate ≤ cost other := by
  intro other allEdges
  apply masterMin
  intro edge known
  exact allEdges edge (subset edge known)

end M03
