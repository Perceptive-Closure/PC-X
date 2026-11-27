import Std

namespace AdvancedPCX

theorem directed_difference (matched actualResidual nominalResidual lo hi : Int)
    (actualBounds : lo ≤ actualResidual ∧ actualResidual ≤ hi)
    (nominalBounds : lo ≤ nominalResidual ∧ nominalResidual ≤ hi) :
    matched - (hi - lo) ≤ matched + actualResidual - nominalResidual ∧
      matched + actualResidual - nominalResidual ≤ matched + (hi - lo) := by
  omega

theorem verified_upper_improves (mass massNext upperPair upperPairNext rangeTop : Int)
    (nonnegative : 0 ≤ mass)
    (moreMass : mass ≤ massNext)
    (tighter : upperPairNext ≤ upperPair)
    (rangeEnough : upperPair ≤ rangeTop) :
    rangeTop - massNext * (rangeTop - upperPairNext) ≤
      rangeTop - mass * (rangeTop - upperPair) := by
  have nonnegativeNext : 0 ≤ massNext := by omega
  have factorNonnegative : 0 ≤ rangeTop - upperPair := by omega
  have factorOrder : rangeTop - upperPair ≤ rangeTop - upperPairNext := by omega
  have stepMass := Int.mul_le_mul_of_nonneg_right moreMass factorNonnegative
  have stepInterval := Int.mul_le_mul_of_nonneg_left factorOrder nonnegativeNext
  omega

theorem scoped_fixture_risk_margin :
    ((19 : Int) * 1 - 3 * 17) + 2 * (19 - 3) = 0 := by decide

theorem scoped_fixture_utility_margin :
    (17 : Int) * (19 - 17) - 2 * 17 = 0 := by decide

end AdvancedPCX
