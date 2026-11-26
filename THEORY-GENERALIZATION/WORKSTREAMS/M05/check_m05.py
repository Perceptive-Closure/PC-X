"""Exact finite corroboration for the M05 candidates."""

from collections import defaultdict
from fractions import Fraction
from functools import cache
from itertools import combinations, product


BIT_PAIRS = tuple(product((0, 1), repeat=2))


def intersections(rows):
    """Intersect pairs of lines, keeping points satisfying every halfspace."""
    points = set()
    for (a, b, c), (d, e, f) in combinations(rows, 2):
        determinant = a * e - b * d
        if determinant == 0:
            continue
        x = (c * e - b * f) / determinant
        y = (a * f - c * d) / determinant
        if all(p * x + q * y <= r for p, q, r in rows):
            points.add((x, y))
    return points


def feasible_monitor_points(tickets, confirmed_hit, confirmed_false_alarm):
    low = Fraction(confirmed_hit, 2 * tickets)
    high = Fraction(tickets - confirmed_false_alarm, 2 * tickets)
    rows = [(-1, 0, -low), (1, 0, high), (0, -1, Fraction(0)), (-1, 1, Fraction(0))]
    # Each half has an affine worst-context objective. The split preserves both.
    lower_piece = rows + [(1, 1, Fraction(1, 2))]
    upper_piece = rows + [(-1, -1, Fraction(-1, 2))]
    return intersections(lower_piece) | intersections(upper_piece)


def enumerate_ticket_labels(tickets, confirmed_hit, confirmed_false_alarm):
    """Generate allowed label words for the two flags before projecting their masses."""
    free = tickets - confirmed_hit - confirmed_false_alarm
    slots = (
        [((1, 0), (1, 1))] * confirmed_hit
        + [((0, 0),)] * confirmed_false_alarm
        + [((0, 0), (1, 0), (1, 1))] * free
    )
    outcomes = set()
    for word in product(*slots):
        alarms, silent = zip(*word)
        outcomes.add((Fraction(sum(alarms), 2 * tickets), Fraction(sum(silent), 2 * tickets)))
    return outcomes


def endpoints(values):
    values = list(values)
    return (min(values), max(values)) if values else None


def monitor_metrics(points):
    summaries = []
    risks = []
    for context in (0, 1):
        context_points = points if context == 0 else {(Fraction(1, 2) - a, Fraction(1, 2) - b) for a, b in points}
        summaries.append(
            (
                endpoints(hit + miss for hit, miss in context_points),
                endpoints(miss for _, miss in context_points),
                endpoints(Fraction(1, 2) - hit for hit, _ in context_points),
                endpoints(miss / (hit + miss) for hit, miss in context_points if hit + miss > 0),
                any(hit + miss == 0 for hit, miss in context_points),
            )
        )
    for hit, miss in points:
        risks.append(max(hit + miss, 1 - hit - miss))
    return tuple(summaries), endpoints(risks)


def check_monitor():
    cases = 0
    for tickets in range(1, 9):
        for hits in range(tickets + 1):
            for false_alarms in range(tickets - hits + 1):
                polytope = feasible_monitor_points(tickets, hits, false_alarms)
                words = enumerate_ticket_labels(tickets, hits, false_alarms)
                assert monitor_metrics(polytope) == monitor_metrics(words), (tickets, hits, false_alarms)
                cases += 1
    metrics, worst_risk = monitor_metrics(feasible_monitor_points(4, 1, 1))
    assert metrics == (
        ((Fraction(1, 8), Fraction(3, 4)), (0, Fraction(3, 8)), (Fraction(1, 8), Fraction(3, 8)), (0, Fraction(1, 2)), False),
        ((Fraction(1, 4), Fraction(7, 8)), (Fraction(1, 8), Fraction(1, 2)), (Fraction(1, 8), Fraction(3, 8)), (Fraction(1, 2), Fraction(4, 5)), False),
    )
    assert worst_risk == (Fraction(1, 2), Fraction(7, 8))

    exclusive_modes = ((Fraction(1, 2), 0), (0, Fraction(1, 2)), (0, 0))
    defined = {miss / (hit + miss) for hit, miss in exclusive_modes if hit + miss > 0}
    assert defined == {0, 1}
    assert any(hit + miss == 0 for hit, miss in exclusive_modes)
    assert Fraction(1, 2) not in defined
    assert all(miss - (hit + miss) <= 0 for hit, miss in exclusive_modes)
    return cases


def optimize_binary_row(left, right, child_costs, direction):
    """Affine row optimization in its free (1, 1) coordinate."""
    lower = max(0, left + right - 1)
    upper = min(left, right)
    offsets = (1 - left - right, right, left, Fraction(0))
    slopes = (1, -1, -1, 1)
    for offset, slope, cost in zip(offsets, slopes, child_costs):
        if cost is None:
            required = -offset / slope
            lower = max(lower, required)
            upper = min(upper, required)
    if lower > upper:
        return None

    values = []
    for free_mass in (lower, upper):
        values.append(
            sum(
                (offset + slope * free_mass) * cost
                for offset, slope, cost in zip(offsets, slopes, child_costs)
                if cost is not None
            )
        )
    return direction(values)


def backward_extreme(left, right, ticket_count, scoring, allowed, direction):
    def value(prefix):
        if len(prefix) == 2:
            return scoring(prefix) if allowed(prefix) else None
        if prefix:
            first_left, first_right = prefix[0]
            row_indices = (1 + first_left, 1 + first_right)
        else:
            row_indices = (0, 0)
        child_costs = [value(prefix + (pair,)) for pair in BIT_PAIRS]
        return optimize_binary_row(
            Fraction(left[row_indices[0]], ticket_count),
            Fraction(right[row_indices[1]], ticket_count),
            child_costs,
            direction,
        )

    return value(())


@cache
def integer_couplings(left, right, ticket_count):
    """Independent enumeration of entire 2 by 2 row tables."""
    return tuple(
        counts
        for counts in product(range(ticket_count + 1), repeat=4)
        if sum(counts) == ticket_count and sum(counts[2:]) == left and counts[1] + counts[3] == right
    )


def enumerate_complete_pairs(left, right, ticket_count, scoring, allowed):
    """Enumerate row-table choices on complete two-tick experiments."""
    results = []
    for first_row in integer_couplings(left[0], right[0], ticket_count):
        first_path_counts = [(pair, count) for pair, count in zip(BIT_PAIRS, first_row) if count]
        row_choices = [
            integer_couplings(left[1 + bit_left], right[1 + bit_right], ticket_count)
            for (bit_left, bit_right), _ in first_path_counts
        ]
        for second_rows in product(*row_choices):
            paths = [
                ((first, second), first_count * second_count)
                for (first, first_count), second_row in zip(first_path_counts, second_rows)
                for second, second_count in zip(BIT_PAIRS, second_row)
                if second_count
            ]
            if all(allowed(path) for path, _ in paths):
                results.append(Fraction(sum(scoring(path) * count for path, count in paths), ticket_count**2))
    return endpoints(results)


def final_bit_cost(path):
    return int(path[1][0] != path[1][1])


def path_label_cost(path):
    (earlier_left, earlier_right), (later_left, later_right) = path
    return int((earlier_left ^ later_left) != (earlier_right | later_right))


def check_coupling():
    tickets = 2
    row_specs = tuple(product(range(tickets + 1), repeat=3))
    compare = (
        (final_bit_cost, lambda _: True),
        (path_label_cost, lambda _: True),
        (path_label_cost, lambda path: path[0][0] == path[0][1]),
        (final_bit_cost, lambda path: path[0][0] != path[0][1] and path[1][0] == path[1][1]),
    )
    comparisons = 0
    infeasible = 0
    for left, right in product(row_specs, repeat=2):
        for scoring, allowed in compare:
            reference = enumerate_complete_pairs(left, right, tickets, scoring, allowed)
            low = backward_extreme(left, right, tickets, scoring, allowed, min)
            high = backward_extreme(left, right, tickets, scoring, allowed, max)
            assert low is not None or high is None
            assert (None if low is None else (low, high)) == reference, (left, right, low, high, reference)
            comparisons += 1
            infeasible += reference is None

    # The original learns its true terminal bit one tick earlier than the probe.
    early = (1, 0, 2)
    late = (0, 1, 1)
    assert backward_extreme(early, late, tickets, final_bit_cost, lambda _: True, min) == Fraction(1, 2)

    # An unconstrained terminal pairing could equalize those two fair outcomes.
    terminal_pairings = integer_couplings(1, 1, tickets)
    assert min(Fraction(row[1] + row[2], tickets) for row in terminal_pairings) == 0
    return comparisons, infeasible


def check_composition():
    configurations = 0
    for numerator in range(13):
        collision_chance = Fraction(numerator, 12)
        patterns = defaultdict(Fraction)
        native_isolated_risk = Fraction(0)
        early_uncovered = Fraction(0)
        conditional_global = Fraction(0)
        missed_mass = Fraction(0)
        probe_only = Fraction(0)
        for ticket in range(1, 9):
            timeout = ticket in (1, 2)
            eventual_local = timeout
            isolated = ticket == 1
            native_isolated_risk += Fraction(isolated, 8)
            if timeout:
                early_uncovered += Fraction(1, 8)
            chance = collision_chance if ticket == 3 else 0
            for collision, weight in ((False, 1 - chance), (True, chance)):
                global_event = timeout or collision
                probe_event = timeout or ticket == 3
                alarm = ticket == 1
                path_mass = weight / Fraction(8)
                patterns[global_event, eventual_local, eventual_local] += path_mass
                if global_event and not alarm:
                    missed_mass += path_mass
                if probe_event and not global_event:
                    probe_only += path_mass
                assert not global_event or probe_event or path_mass == 0
                if ticket == 3 and global_event:
                    conditional_global += weight
        assert sum(patterns.values()) == 1
        assert patterns[True, True, True] == Fraction(1, 4)
        assert patterns[True, False, False] == collision_chance / 8
        assert patterns[False, False, False] == Fraction(3, 4) - collision_chance / 8
        global_risk = sum(weight for (g, _, _), weight in patterns.items() if g)
        assert global_risk == Fraction(1, 4) + collision_chance / 8
        for local_index in (1, 2):
            joint_risk = sum(weight for pattern, weight in patterns.items() if pattern[local_index])
            assert joint_risk - native_isolated_risk == Fraction(1, 8)
        assert conditional_global == collision_chance
        assert early_uncovered == Fraction(1, 4)
        assert missed_mass / global_risk == (1 + collision_chance) / (2 + collision_chance)
        assert probe_only + patterns[True, False, False] == Fraction(1, 8)
        configurations += 1

    pair_support = [(left, right) for left, right in BIT_PAIRS if left != right]
    assert len(pair_support) == 2
    assert all(sum(pair[coordinate] for pair in pair_support) == 1 for coordinate in (0, 1))
    assert all(
        any(bits[left] == bits[right] for left, right in combinations(range(3), 2))
        for bits in product((0, 1), repeat=3)
    )
    return configurations


def main():
    monitor_cases = check_monitor()
    pair_cases, infeasible = check_coupling()
    composition_cases = check_composition()
    print(f"T25.J exact monitor geometry versus ticket enumeration: {monitor_cases} cases")
    print(f"T26.C backward checks versus complete pair enumeration: {pair_cases} cases ({infeasible} empty)")
    print(f"T27.J exact shared-ticket composition and conditional profiles: {composition_cases} cases")
    print("Exclusive modes, zero denominators, early/late pairing and triple compatibility checked.")


if __name__ == "__main__":
    main()
