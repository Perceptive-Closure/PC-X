import Std

namespace PCXAdvancedUnified

theorem scalePrice (low high d : Nat)
    (budget : low + high ≤ 3 * d)
    (separation : 4 * d ≤ low + 2 * high) :
    14 * d ≤ 3 * low + 8 * high := by
  omega

theorem zeroUnsharedRisk (common actual nominal unmatched : Int)
    (referenceBound : common ≤ nominal)
    (actualBound : actual ≤ common + unmatched) :
    actual - nominal ≤ unmatched := by
  omega

theorem meshDeploymentCap (deploy grid cap delivery mesh : Int)
    (comparison : deploy ≤ grid + delivery + mesh)
    (tightened : grid ≤ cap - delivery - mesh) :
    deploy ≤ cap := by
  omega

theorem twoSidedGap (l u mixture surcharge cover : Int)
    (bound : u ≤ l + mixture + 2 * surcharge + cover) :
    u-l ≤ mixture + 2 * surcharge + cover := by
  omega

end PCXAdvancedUnified

#print axioms PCXAdvancedUnified.scalePrice
#print axioms PCXAdvancedUnified.meshDeploymentCap
