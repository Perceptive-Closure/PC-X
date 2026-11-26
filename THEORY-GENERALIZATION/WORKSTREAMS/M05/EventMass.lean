import Std

namespace PCXM05

def massWhere {α : Type} (weight : α → Int) (event : α → Bool) : List α → Int
  | [] => 0
  | row :: rest => (if event row then weight row else 0) + massWhere weight event rest

theorem signedFlip {α : Type} (weight : α → Int) (original probed : α → Bool)
    (rows : List α) :
    massWhere weight original rows - massWhere weight probed rows =
      massWhere weight (fun row => original row && !probed row) rows -
      massWhere weight (fun row => !original row && probed row) rows := by
  induction rows with
  | nil => simp [massWhere]
  | cons row rest ih =>
    cases first : original row <;> cases second : probed row <;>
      simp [massWhere, first, second] <;> omega

theorem globalPartition {α : Type} (weight : α → Int) (global localUnion : α → Bool)
    (rows : List α) :
    massWhere weight global rows =
      massWhere weight (fun row => global row && localUnion row) rows +
      massWhere weight (fun row => global row && !localUnion row) rows := by
  induction rows with
  | nil => simp [massWhere]
  | cons row rest ih =>
    cases first : global row <;> cases second : localUnion row <;>
      simp [massWhere, first, second] <;> omega

#print axioms signedFlip
#print axioms globalPartition

end PCXM05
