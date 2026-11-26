"""Executed local policy and independent virtual station."""

from contract import LEFT, RIGHT, SPEC, TICKETS


class SortingPolicy:
    def __init__(self, fixture):
        self.fixture = fixture
        self.previous = None

    def reset(self):
        self.previous = None

    def place(self, cue, context, trim, ticket):
        if (
            cue not in SPEC["cues"]
            or context not in SPEC["contexts"]
            or trim not in SPEC["trims"]
            or type(ticket) is not int
            or not 0 <= ticket < TICKETS
        ):
            raise ValueError("Input outside the declared sorting interface")
        config = SPEC["policy"]
        if self.previous is not None:
            count = config["warm_right_base"]
            if cue == "gold":
                count += config["warm_gold_bonus"]
            if context == "ribbed":
                count += config["warm_ribbed_bonus"]
            if self.previous == RIGHT:
                count += config["warm_previous_right_bonus"]
        elif cue == "blue":
            count = config["blue_key_right"] if context == self.fixture.key else config["blue_other_right"]
        elif self.fixture.mode == "midpoint":
            count = config["midpoint_gold_right"]
        elif self.fixture.variant == 1 and context == self.fixture.key:
            count = config["gold_variant_one_key_right"]
        else:
            count = config["gold_other_right"]
        self.previous = RIGHT if ticket < count else LEFT
        return self.previous


class RecheckStation:
    """Scores placement from a separate ticket and returns no policy feedback."""

    def __init__(self, fixture, cue):
        config = SPEC["station"]
        self.left = config["left_recheck"]
        self.right = config["right_recheck"]
        if fixture.mode == "shift" and cue == SPEC["deployment_cue"]:
            self.left = config["shift_gold_left_recheck"]

    def score(self, tray, ticket):
        if tray not in (LEFT, RIGHT) or type(ticket) is not int or not 0 <= ticket < TICKETS:
            raise ValueError("Invalid station input")
        limit = self.right if tray == RIGHT else self.left
        return int(ticket < limit)


def native_episode(fixture, cue, recipe, rng):
    policy = SortingPolicy(fixture)
    station = RecheckStation(fixture, cue)
    trace = []
    for context in recipe:
        decision_ticket = rng.randrange(TICKETS)
        tray = policy.place(cue, context, "plain", decision_ticket)
        station_ticket = rng.randrange(TICKETS)
        trace.append([decision_ticket, tray, station_ticket, station.score(tray, station_ticket)])
    return trace


def reset_batch(fixture, cue, context, count, rng):
    """Expose tray observations only, each from a separately initialized policy."""
    return "".join(
        str(SortingPolicy(fixture).place(cue, context, "plain", rng.randrange(TICKETS)))
        for _ in range(count)
    )


def factor_observation(fixture, mode, cue, context, trim, rng):
    policy = SortingPolicy(fixture)
    prefix_ticket = prefix_tray = None
    if mode == "carry":
        prefix_ticket = rng.randrange(TICKETS)
        prefix_tray = policy.place(*SPEC["warm_up"], prefix_ticket)
    ticket = rng.randrange(TICKETS)
    return [prefix_ticket, prefix_tray, ticket, policy.place(cue, context, trim, ticket)]
