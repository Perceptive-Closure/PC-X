"""Exact controls for the clarified statement scopes."""

from fractions import Fraction
from math import log


def main():
    w0 = Fraction(1, 2**33)
    for t in range(33):
        p1 = Fraction(1, 2**t)
        mixture = w0 + (1 - w0) * p1
        assert mixture < 10
        assert mixture / p1 < Fraction(3, 2)
    assert 32 > 2 * log(2 * 2 / 0.1) / 0.5**2

    joint0 = {(0, 0), (1, 1)}
    joint1 = {(0, 1), (1, 0)}
    assert {u for u, _ in joint0} == {u for u, _ in joint1}
    assert {v for _, v in joint0} == {v for _, v in joint1}
    assert not (joint0 & joint1)

    action_class = {"L": "fast", "R": "fast", "S": "slow"}
    menus = ({"L", "S"}, {"R", "S"})
    assert {action_class[a] for a in menus[0]} == {"fast", "slow"}
    assert {action_class[a] for a in menus[1]} == {"fast", "slow"}
    assert set.intersection(*menus) == {"S"}
    assert int(1 + 1 * 0 <= 1) != int(1 + 1 * 1 <= 1)

    print("T23 mixture nondecisiveness, T24 joint-vs-marginal alias, and T30 common lift boundaries passed")


if __name__ == "__main__":
    main()
