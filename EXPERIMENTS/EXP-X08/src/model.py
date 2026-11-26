"""Exact finite laws, independent checks, and semantic audit optimization."""

from collections import Counter
from fractions import Fraction
from itertools import combinations, permutations, product
from random import Random


def transitions(spec, fixture, site, instruction, previous_retry):
    profile, feeder = fixture
    rules = spec[site]
    base = rules["base_manual"]
    delivery = rules["delivery"]
    if site == "floor":
        base = base[profile]
        delivery = delivery[feeder]
    manual = base + rules["normal_bonus"] * (instruction == "normal")
    manual += rules["retry_bonus"] * previous_retry
    tickets = spec["tickets"]
    probabilities = {}
    for lane, branch_count in zip(spec["lanes"], (manual, tickets - manual), strict=True):
        for retry, outcome_count in ((False, delivery[lane]), (True, tickets - delivery[lane])):
            if branch_count and outcome_count:
                probabilities[lane, retry] = Fraction(branch_count * outcome_count, tickets**2)
    if sum(probabilities.values()) != 1 or min(probabilities.values()) <= 0:
        raise ValueError("Malformed positive-support law")
    return probabilities


def conditional_table(spec, fixture, site):
    """Retain full observations, including auditor-selected inputs."""
    frontier = [()]
    table = {}
    for _ in range(spec["horizon"]):
        next_frontier = []
        for history in frontier:
            for instruction in spec["instructions"]:
                law = transitions(spec, fixture, site, instruction, bool(history and history[-1][-1]))
                table[history, instruction] = law
                next_frontier.extend(history + ((instruction, lane, retry),) for lane, retry in law)
        frontier = next_frontier
    return table


def behavioral_risk(spec, fixture, site, recipe):
    """Enumerate every visible supported path using the conditional probability table."""
    frontier = {(): Fraction(1)}
    for instruction in recipe:
        next_frontier = {}
        for trace, mass in frontier.items():
            law = transitions(spec, fixture, site, instruction, bool(trace and trace[-1][1]))
            for (lane, retry), probability in law.items():
                next_frontier[trace + ((lane, retry),)] = mass * probability
        frontier = next_frontier
    cutoff = spec["violation_minimum_retry_rounds"]
    return sum(mass for trace, mass in frontier.items() if sum(retry for _, retry in trace) >= cutoff)


def retry_state_risk(spec, fixture, site, recipe):
    """Marginalize lane first, using only (number of retries, most recent feedback)."""
    profile, feeder = fixture
    rules = spec[site]
    capacity = rules["delivery"] if site == "benchmark" else rules["delivery"][feeder]
    policy_base = rules["base_manual"] if site == "benchmark" else rules["base_manual"][profile]
    total_tickets = spec["tickets"]
    states = Counter({(0, False): Fraction(1)})
    for instruction in recipe:
        following = Counter()
        for (total_retries, last_retry), mass in states.items():
            preference = policy_base
            if instruction == "normal":
                preference += rules["normal_bonus"]
            if last_retry:
                preference += rules["retry_bonus"]
            success = capacity["manual"] * preference
            success += capacity["belt"] * (total_tickets - preference)
            likelihood = Fraction(success, total_tickets**2)
            following[total_retries, False] += likelihood * mass
            following[total_retries + 1, True] += (1 - likelihood) * mass
        states = following
    cutoff = spec["violation_minimum_retry_rounds"]
    return sum(mass for (n, _), mass in states.items() if n >= cutoff)


def all_fixtures(spec):
    return tuple(product(spec["enrollment"]["profiles"], spec["enrollment"]["feeders"]))


def joint_candidates(spec, *, parity=True):
    profiles = spec["enrollment"]["profiles"]
    pairs = permutations(profiles) if parity else product(profiles, repeat=2)
    return tuple(
        tuple(zip(pair, feeders, strict=True))
        for pair in pairs
        for feeders in product(spec["enrollment"]["feeders"], repeat=2)
    )


def observed_answer(spec, fixture, query):
    profile, feeder = fixture
    if query == "bench_tickets":
        return spec["benchmark"]["base_manual"]
    if query == "feeder_cadence":
        return spec["floor"]["delivery"][feeder]["manual"]
    if query == "routing_calibration":
        return spec["floor"]["base_manual"][profile]
    raise ValueError(f"Unsupported query {query}")


def risk_table(spec, site="floor"):
    result = {}
    for fixture in all_fixtures(spec):
        risks = {}
        for name, recipe in spec["deployment_recipes"].items():
            risk = behavioral_risk(spec, fixture, site, recipe)
            if risk != retry_state_risk(spec, fixture, site, recipe):
                raise AssertionError(f"Independent risk check failed for {site}/{fixture}/{name}")
            risks[name] = risk
        result[fixture] = risks
    return result


def verdicts(spec, candidate, risks):
    cutoff = Fraction(spec["risk_threshold"])
    return tuple(max(risks[fixture].values()) <= cutoff for fixture in candidate)


def unit_queries(spec):
    return tuple(sorted(product(spec["enrollment"]["units"], spec["queries"])))


def answer_vector(spec, candidate, queries):
    fixtures = dict(zip(spec["enrollment"]["units"], candidate, strict=True))
    return tuple(observed_answer(spec, fixtures[unit], query) for unit, query in queries)


def sufficient(spec, candidates, risks, queries):
    if not candidates:
        raise ValueError("Empty governing evidence")
    partitions = {}
    for candidate in candidates:
        observation = answer_vector(spec, candidate, queries)
        target = verdicts(spec, candidate, risks)
        if observation in partitions and partitions[observation] != target:
            return False
        partitions[observation] = target
    return True


def cost(spec, queries):
    return sum(spec["queries"][query]["cost"] for _, query in queries)


def minimum_audit(spec, candidates, risks, allowed=None):
    if allowed is None:
        allowed = unit_queries(spec)
    modes = [
        (cost(spec, subset), subset)
        for size in range(len(allowed) + 1)
        for subset in combinations(allowed, size)
        if sufficient(spec, candidates, risks, subset)
    ]
    return min(modes) if modes else None


def target_edges(spec, candidates, risks, allowed):
    answers = {candidate: answer_vector(spec, candidate, allowed) for candidate in candidates}
    return {
        frozenset(query for query, a, b in zip(allowed, answers[left], answers[right], strict=True)
                  if a != b)
        for left, right in combinations(candidates, 2)
        if verdicts(spec, left, risks) != verdicts(spec, right, risks)
    }


def acquisition_cost(spec, candidates, risks, order):
    for i in range(len(order) + 1):
        prefix = order[:i]
        if sufficient(spec, candidates, risks, prefix):
            return cost(spec, prefix)
    return None


def measurement_plan(spec, candidates, risks):
    queries = unit_queries(spec)
    optimum = minimum_audit(spec, candidates, risks, queries)
    if optimum is None:
        raise AssertionError("The frozen complete interface is unexpectedly audit-inaccessible")
    edges = target_edges(spec, candidates, risks, queries)
    independently_sufficient = [
        (cost(spec, subset), subset)
        for size in range(len(queries) + 1)
        for subset in combinations(queries, size)
        if all(edge.intersection(subset) for edge in edges)
    ]
    if min(independently_sufficient) != optimum:
        raise AssertionError("Pair transversals and conditioning gave different optima")
    cheapest_first = tuple(sorted(queries, key=lambda q: (cost(spec, (q,)), q)))
    generator = Random(808)
    drawn_orders = [tuple(generator.sample(queries, len(queries))) for _ in range(256)]
    no_calibration = tuple(q for q in queries if q[1] != "routing_calibration")
    return {
        "selected": optimum[1],
        "minimum_cost": optimum[0],
        "sufficient_subsets": len(independently_sufficient),
        "disagreement_edge_count": len(edges),
        "exhaustive_cost": cost(spec, queries),
        "cheapest_first_cost": acquisition_cost(spec, candidates, risks, cheapest_first),
        "random_order_cost_counts": dict(sorted(Counter(
            acquisition_cost(spec, candidates, risks, order) for order in drawn_orders
        ).items())),
        "audit_inaccessible_without_routing_calibration": minimum_audit(
            spec, candidates, risks, no_calibration
        ) is None,
    }
