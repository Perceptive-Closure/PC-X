"""Independent exact checks for the generalized P neutral statement."""

from fractions import Fraction as F
from functools import cache
from itertools import product


def check_parametric_laws():
    worlds = tuple(F(j, 8) for j in range(9))
    for theta in worlds:
        law = {(x, y): (theta if x else 1 - theta) * (theta if y else 1 - theta)
               for x, y in product(range(2), repeat=2)}
        assert sum(law.values()) == 1
        assert sum(weight for (x, y), weight in law.items() if x != y) == 2 * theta * (1 - theta)
        assert sum(weight * x for (x, _), weight in law.items()) == theta
        assert law[1, 1] == theta**2
        for tangent in worlds:
            assert theta**2 - 2 * tangent * theta >= -(tangent**2)
            assert (theta**2 - 2 * tangent * theta == -(tangent**2)) == (theta == tangent)
    assert max(2 * t * (1 - t) for t in worlds) == F(1, 2)

    graph = ((0, 1), (0, 2), (1, 2), (2, 3))

    def weighted_cut(theta):
        return sum(theta[u] + theta[v] - 2 * theta[u] * theta[v] for u, v in graph)

    corners = tuple(product((0, 1), repeat=4))
    assert all(weighted_cut(x) == sum(x[u] != x[v] for u, v in graph) for x in corners)
    assert max(weighted_cut(x) for x in product((F(0), F(1, 3), F(2, 3), F(1)), repeat=4)) == 3


def check_transport():
    initial_mass, row_one, row_two = F(3, 4), F(4, 5), F(2, 3)
    matched = initial_mass * row_one * row_two
    # A unit score is possible only in the actual unmatched residual.
    assert matched == F(2, 5)
    assert 0 - 0 - (1 - matched) == -F(3, 5)
    assert 0 - 0 + (1 - matched) == F(3, 5)

    known = F(17, 20)
    known_risk = F(1, 20)
    unmatched = F(1, 10)
    risk_cap = F(3, 19)
    utility_floor = F(17, 19)
    assert known_risk - known * risk_cap + unmatched * (1 - risk_cap) == 0
    assert known * (1 - utility_floor) - unmatched * utility_floor == 0
    assert (known_risk + unmatched) / known == F(3, 17) > risk_cap
    for theta in (F(k, 8) for k in range(9)):
        activated = known + unmatched * theta
        violating = known_risk + unmatched * theta**2
        assert violating <= risk_cap * activated
        assert known >= utility_floor * activated
    assert (known_risk + unmatched) / (known + unmatched) == risk_cap
    assert known / (known + unmatched) == utility_floor
    assert known - F(1, 5) + unmatched < known
    assert known - F(3, 5) + unmatched < known


def check_anchors():
    legal_worlds = tuple(product(range(2), repeat=2))
    costs = (1, 2)

    @cache
    def least_cost(seen):
        possible = tuple(w for w in legal_worlds if all(w[j] == v for j, v in seen))
        if len({all(w) for w in possible}) == 1:
            return 0
        return min(
            costs[j] + max(least_cost(tuple(sorted((*seen, (j, val))))) for val in {w[j] for w in possible})
            for j in range(2) if j not in dict(seen)
        )

    assert least_cost(()) == 3

    # A proof can require a new verified fragment even when all exact received labels are identical.
    # In this cell the ordinary initial guard knows candidate work on mass 1/2 and no risk.
    # Either independent fragment alone gives true useful mass 3/4, both certify 1.
    for admitted in product((False, True), repeat=2):
        useful_lower = F(1, 2) + F(sum(admitted), 4)
        assert (useful_lower >= 1) == all(admitted)


if __name__ == "__main__":
    check_parametric_laws()
    check_transport()
    check_anchors()
    print("PASS G01-G02: linked complete laws, quadratic rows, common mass, signed source scores and exact field cost")
