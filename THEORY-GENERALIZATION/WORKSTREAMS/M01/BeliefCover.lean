import Init

/-! The finite-tree induction for a directed observable belief cover.
This formalization uses natural-number costs and abstract belief nodes. -/

namespace PCX.M01

structure Arena (Belief Action Reply Resource Report : Type) where
  stop : Belief → Report → Prop
  legal : Belief → Action → Prop
  cost : Belief → Action → Nat
  touches : Belief → Action → Resource → Prop
  supported : Belief → Action → Reply → Prop
  next : Belief → Action → Reply → Belief
  supportNonempty : ∀ {b a}, legal b a → ∃ r, supported b a r

def survives (g : Arena B A L F D) (freeze : F → Prop) (b : B) (a : A) : Prop :=
  ∀ r, g.touches b a r → ¬ freeze r

inductive Feasible (g : Arena B A L F D) (freeze : F → Prop) :
    Nat → Nat → B → Prop where
  | stop {height budget b} (report : D) (valid : g.stop b report) :
      Feasible g freeze height budget b
  | act {height budget b} (a : A) (remaining : Nat)
      (legal : g.legal b a) (kept : survives g freeze b a)
      (affordable : g.cost b a + remaining ≤ budget)
      (continuations : ∀ reply, g.supported b a reply →
        Feasible g freeze height remaining (g.next b a reply)) :
      Feasible g freeze (height + 1) budget b

structure Cover (g : Arena B A L F D) (h : Arena B' A' L' F D)
    (related : B → B' → Prop) : Prop where
  stops : ∀ {b b'}, related b b' → ∀ {report}, g.stop b report → h.stop b' report
  moves : ∀ {b b'}, related b b' → ∀ {a}, g.legal b a →
    ∃ a', h.legal b' a' ∧ h.cost b' a' ≤ g.cost b a ∧
      (∀ {r}, h.touches b' a' r → g.touches b a r) ∧
      (∀ reply', h.supported b' a' reply' →
        ∃ reply, g.supported b a reply ∧ related (g.next b a reply) (h.next b' a' reply'))

theorem transport (g : Arena B A L F D) (h : Arena B' A' L' F D)
    {related : B → B' → Prop} (cover : Cover g h related)
    (freeze : F → Prop) {height budget b b'} (matched : related b b')
    (policy : Feasible g freeze height budget b) :
    Feasible h freeze height budget b' := by
  induction policy generalizing b' with
  | stop report valid =>
      exact Feasible.stop report (cover.stops matched valid)
  | act a remaining legal kept affordable _ ih =>
      obtain ⟨a', legal', cheaper, fewerTouches, replyMatch⟩ := cover.moves matched legal
      refine Feasible.act a' remaining legal' ?_ ?_ ?_
      · exact fun r touch => kept r (fewerTouches touch)
      · exact Nat.le_trans (Nat.add_le_add_right cheaper remaining) affordable
      · intro reply' supported'
        obtain ⟨reply, supported, nextPair⟩ := replyMatch reply' supported'
        exact ih reply supported nextPair

#print axioms transport

end PCX.M01
