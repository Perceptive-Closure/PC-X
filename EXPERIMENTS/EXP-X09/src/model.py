"""Exact response kernels and risk calculation independent of runtime transitions."""

from collections import defaultdict
from fractions import Fraction
from functools import cache

from contract import LEFT, RECIPES, RIGHT, SPEC, TICKETS


MEETS = "MEETS"
FAILS = "FAILS"
THRESHOLD = Fraction(SPEC["threshold"])


def right_probability(fixture, cue, context, previous=None):
    config = SPEC["policy"]
    if previous is None:
        matched = context == fixture.key
        if cue == "blue":
            count = (config["blue_other_right"], config["blue_key_right"])[matched]
        else:
            cold = (config["gold_other_right"], config["gold_variant_one_key_right"])
            count = cold[matched and fixture.variant == 1]
            if fixture.mode == "midpoint":
                count = config["midpoint_gold_right"]
    else:
        count = (
            config["warm_right_base"]
            + (cue == "gold") * config["warm_gold_bonus"]
            + (context == "ribbed") * config["warm_ribbed_bonus"]
            + previous * config["warm_previous_right_bonus"]
        )
    return Fraction(count, TICKETS)


def station_probability(fixture, cue, tray):
    config = SPEC["station"]
    if tray == RIGHT or (fixture.mode == "shift" and cue == SPEC["deployment_cue"]):
        field = "right_recheck" if tray == RIGHT else "shift_gold_left_recheck"
    else:
        field = "left_recheck"
    return Fraction(config[field], TICKETS)


def risk(fixture, cue, recipe):
    survives = {None: Fraction(1)}
    for context in recipe:
        following = defaultdict(Fraction)
        for previous, mass in survives.items():
            right = right_probability(fixture, cue, context, previous)
            for tray, probability in ((LEFT, 1 - right), (RIGHT, right)):
                following[tray] += mass * probability * (1 - station_probability(fixture, cue, tray))
        survives = following
    return 1 - sum(survives.values())


@cache
def risks(fixture, cue=SPEC["deployment_cue"]):
    return {name: risk(fixture, cue, recipe) for name, recipe in RECIPES.items()}


def target(fixture, cue=SPEC["deployment_cue"]):
    return MEETS if max(risks(fixture, cue).values()) <= THRESHOLD else FAILS


def factor_probability(fixture, mode, cue, context):
    if mode == "reset":
        return right_probability(fixture, cue, context)
    warm_cue, warm_context, _ = SPEC["warm_up"]
    warm_right = right_probability(fixture, warm_cue, warm_context)
    return (1 - warm_right) * right_probability(
        fixture, cue, context, LEFT
    ) + warm_right * right_probability(fixture, cue, context, RIGHT)
