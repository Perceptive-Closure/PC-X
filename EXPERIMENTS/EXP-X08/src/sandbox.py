"""The exercised parcel controller and local virtual facility.

The evaluator can supply normal/rush requests only on the benchmark. The custodian
can instantiate a separate floor-cue action calibration, without running the facility.
"""

from collections import Counter
from fractions import Fraction
from itertools import product


class RoutingAgent:
    def __init__(self, spec, profile):
        self.profile = profile
        self.rules = spec
        self.had_retry = False

    def choose(self, observation, request, ticket):
        if request not in self.rules["instructions"] or not 0 <= ticket < self.rules["tickets"]:
            raise ValueError("Action or ticket outside the frozen interface")
        configuration = self.rules[observation]
        weights = configuration["base_manual"]
        weight = weights[self.profile] if observation == "floor" else weights
        if request == "normal":
            weight += configuration["normal_bonus"]
        if self.had_retry:
            weight += configuration["retry_bonus"]
        return "manual" if ticket < weight else "belt"

    def receive(self, retry):
        if type(retry) is not bool:
            raise ValueError("Facility feedback must be a Boolean")
        self.had_retry = retry


class VirtualFacility:
    def __init__(self, spec, feeder, site):
        self.site = site
        self.tickets = spec["tickets"]
        installed = spec[site]["delivery"]
        self.delivery = installed[feeder] if site == "floor" else installed

    def dispatch(self, lane, ticket):
        if not 0 <= ticket < self.tickets:
            raise ValueError("Unsupported environment ticket")
        return ticket >= self.delivery[lane]


def execute_episode(spec, fixture, site, recipe, rng):
    """The custodian records simulator feedback independently of policy reports."""
    profile, feeder = fixture
    agent = RoutingAgent(spec, profile)
    facility = VirtualFacility(spec, feeder, site)
    trace = []
    for request in recipe:
        policy_ticket = rng.randrange(spec["tickets"])
        lane = agent.choose(site, request, policy_ticket)
        facility_ticket = rng.randrange(spec["tickets"])
        retry = facility.dispatch(lane, facility_ticket)
        trace.append([request, lane, retry, policy_ticket, facility_ticket])
        agent.receive(retry)
    return trace


def replay_conditional(spec, fixture, site, history, request):
    """Enumerate all ticket pairs in the executed runtime as a law checker."""
    profile, feeder = fixture
    agent = RoutingAgent(spec, profile)
    environment = VirtualFacility(spec, feeder, site)
    for _, _, retry in history:
        agent.receive(retry)
    tickets = range(spec["tickets"])
    outcomes = Counter()
    for actor_ticket, environment_ticket in product(tickets, repeat=2):
        lane = agent.choose(site, request, actor_ticket)
        outcomes[lane, environment.dispatch(lane, environment_ticket)] += 1
    return {key: Fraction(count, len(tickets)**2) for key, count in outcomes.items()}


def calibrate(spec, fixture, query):
    profile, feeder = fixture
    tickets = range(spec["tickets"])
    if query == "feeder_cadence":
        facility = VirtualFacility(spec, feeder, "floor")
        return sum(not facility.dispatch("manual", ticket) for ticket in tickets)
    if query not in ("bench_tickets", "routing_calibration"):
        raise ValueError("Unknown authorized measurement")
    site = "benchmark" if query == "bench_tickets" else "floor"
    actor = RoutingAgent(spec, profile)
    return sum(actor.choose(site, "rush", ticket) == "manual" for ticket in tickets)
