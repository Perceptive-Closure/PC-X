import Std

namespace X17

-- Paid fractions share a positive integer denominator D.
-- TV >= 1/3 becomes 3*(l + 2*h) >= 4*D.
-- The cost lower bound 3*l/(8*D) + h/D >= 7/12 is scaled by 24*D.
theorem base_price (l h d : Int)
    (oneProbe : l + h ≤ d) (separation : 4 * d ≤ 3 * (l + 2 * h)) :
    14 * d ≤ 9 * l + 24 * h := by
  omega

theorem low_skip_impossible (l d : Int)
    (positive : 0 < d) (oneProbe : l ≤ d) (separation : 4 * d ≤ 3 * l) :
    False := by
  omega

theorem tightened_price (l h d margin : Int)
    (oneProbe : l + h ≤ d) (separation : 4 * d + 24 * margin ≤ 3 * (l + 2 * h)) :
    14 * d + 120 * margin ≤ 9 * l + 24 * h := by
  omega

-- The most efficient extended-menu paid quality contributes at most 2 times price.
theorem direct_menu_lower (separation price d : Int)
    (enough : d ≤ 3 * separation) (efficiency : separation ≤ 2 * price) :
    d ≤ 6 * price := by
  omega

end X17
