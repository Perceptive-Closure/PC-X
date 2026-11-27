"""Pure X17 command selection and declaration over the detached public interface."""

from collections.abc import Mapping, Sequence
from typing import Protocol


class PrivateRng(Protocol):
    def randrange(self, stop: int) -> int: ...


PAID_QUALITIES = {
    "pcx": frozenset(("low", "high")),
    "high_skip": frozenset(("high", "skip")),
    "low_only": frozenset(("low",)),
    "always_high": frozenset(("high",)),
    "no_paid": frozenset(("skip",)),
}


def _route(receipt: Mapping[str, object]) -> str:
    route = receipt.get("route")
    if route == "L" or route == "R":
        return route
    raise ValueError("controller requires a delivered L or R route receipt")


def choose_probe(
    arm: str, prelude: Sequence[int], route_receipt: Mapping[str, object], rng: PrivateRng
) -> str:
    """Choose one registered quality and append the genuine public route."""
    route = _route(route_receipt)
    if arm == "pcx":
        quality = "low" if rng.randrange(3) < 2 else "high"
    elif arm == "high_skip":
        quality = "high" if rng.randrange(3) < 2 else "skip"
    elif arm == "low_only":
        quality = "low"
    elif arm == "always_high":
        quality = "high"
    elif arm == "no_paid":
        quality = "skip"
    else:
        raise ValueError("unknown registered policy")
    return f"{quality}:{route}"


def declare(
    arm: str,
    prelude: Sequence[int],
    route_receipt: Mapping[str, object],
    literal: str,
    response: int | None,
    rng: PrivateRng,
) -> bool:
    """Return the binary declaration using only the public probe response and RNG."""
    route = _route(route_receipt)
    qualities = PAID_QUALITIES.get(arm)
    if qualities is None:
        raise ValueError("unknown registered policy")
    if literal not in {f"{quality}:{route}" for quality in qualities}:
        raise ValueError("probe literal is outside the policy or delivered route")
    if literal == f"skip:{route}":
        if response is not None:
            raise ValueError("skip requires the declared blank response")
        return rng.randrange(2) == 0
    if type(response) is not int or response not in (0, 1):
        raise ValueError("paid probe response must be the integer 0 or 1")
    return response == 0
