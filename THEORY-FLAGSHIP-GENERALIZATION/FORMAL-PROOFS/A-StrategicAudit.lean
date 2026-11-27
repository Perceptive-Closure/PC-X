import Std

namespace GeneralizedStrategicAudit

def sumBy (f : Nat × Nat → Nat) : List (Nat × Nat) → Nat
  | [] => 0
  | row :: tail => f row + sumBy f tail

def gap (row : Nat × Nat) : Nat :=
  (row.1 - row.2) + (row.2 - row.1)

/-- A local count identity for the decision between the two signs. -/
theorem local_bayes_counts (row : Nat × Nat) :
    2 * min row.1 row.2 + gap row = row.1 + row.2 := by
  rcases row with ⟨left, right⟩
  simp only [gap]
  omega

/-- For any finite stopped-record law in common integer units, twice the
minimum Bayes error counts plus the absolute gap is the total mass. -/
theorem finite_bayes_counts (rows : List (Nat × Nat)) :
    2 * sumBy (fun row => min row.1 row.2) rows + sumBy gap rows =
      sumBy Prod.fst rows + sumBy Prod.snd rows := by
  induction rows with
  | nil => rfl
  | cons row tail ih =>
    have point := local_bayes_counts row
    simp only [sumBy]
    omega

/-- The heterogeneous expected and supported price lower bounds in
integer units after imposing the matched-gain constraint. -/
theorem heterogeneous_lower (scale left right : Nat)
    (leftCap : left ≤ scale) (requiredGain : 7 * scale ≤ 4 * left + 6 * right) :
    scale ≤ 2 * right ∧ 5 * scale ≤ 2 * left + 6 * right := by
  omega

/-- The two wrong counts sum to the report count on equal records. -/
inductive Decision where
  | positive
  | negative
  | abstain

def reported : Decision → Nat
  | .abstain => 0
  | _ => 1

def wrongPositive : Decision → Nat
  | .negative => 1
  | _ => 0

def wrongNegative : Decision → Nat
  | .positive => 1
  | _ => 0

theorem equal_record_counts (ds : List Decision) :
    (ds.map wrongPositive).sum + (ds.map wrongNegative).sum = (ds.map reported).sum := by
  induction ds with
  | nil => rfl
  | cons d tail ih =>
    cases d <;>
      simp only [List.map_cons, List.sum_cons, wrongPositive, wrongNegative, reported]
    all_goals omega

end GeneralizedStrategicAudit
