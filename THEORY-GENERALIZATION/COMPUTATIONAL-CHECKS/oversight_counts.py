from fractions import Fraction
from functools import cache
from itertools import product


def best_correct_assignments(size, limit):
    @cache
    def solve(remaining, calls):
        if not remaining:
            return 0
        best = 1
        if calls:
            for query in range(-1, size):
                yes = tuple((gate, key) for gate, key in remaining
                            if (gate == 1 if query == -1 else key == query))
                no = tuple(pair for pair in remaining if pair not in yes)
                if yes and no:
                    best = max(best, solve(yes, calls - 1) + solve(no, calls - 1))
        return best

    return solve(tuple(product(range(2), range(size))), limit)


def hit_upper_probability(up, lower, upper):
    ratio = (1 - up) / up
    return (1 - ratio ** lower) / (1 - ratio ** (lower + upper))


def main():
    exact = 0
    for size in range(2, 9):
        for cap in range(size + 2):
            expected = 1 if cap == 0 else min(2 * size, 2 * cap)
            assert best_correct_assignments(size, cap) == expected
            exact += 1
    noisy = 0
    for error in (Fraction(1, 8), Fraction(1, 4), Fraction(2, 5)):
        ratio = (1 - error) / error
        drift = 1 - 2 * error
        for lower, upper in product(range(1, 6), repeat=2):
            false_positive = hit_upper_probability(error, lower, upper)
            false_negative = 1 - hit_upper_probability(1 - error, lower, upper)
            expect_zero = (lower - (upper + lower) * false_positive) / drift
            expect_one = (upper - (upper + lower) * false_negative) / drift
            assert false_positive <= ratio ** (-upper)
            assert false_negative <= ratio ** (-lower)
            assert 0 < expect_zero <= lower / drift
            assert 0 < expect_one <= upper / drift
            noisy += 1
    print(f"{exact} exact optimal success-count checks; {noisy} biased walk error and expectation checks")


if __name__ == "__main__":
    main()
