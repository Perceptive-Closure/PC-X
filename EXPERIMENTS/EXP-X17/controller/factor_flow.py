"""Exact count-factor and complete-history realizations of the X17 base menu."""

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from itertools import product

from .forecast import ARM_MIX, THRESHOLD, positive_label, stay_probability

F = Fraction
ROUTES = ("L", "R")
METRICS = ("I", "V", "VI", "wrong", "G", "cost", "Z")
COST = {"low": F(3, 8), "high": F(1), "skip": F(0)}
POSITIVE_ON_ZERO = (True, False)


@dataclass(frozen=True, slots=True)
class Plan:
    quality: str
    answers: tuple[bool, ...]

    def literal(self, route: str) -> str:
        return f"{self.quality}:{route}"


PLANS = tuple(
    Plan(quality, answers)
    for quality in ("low", "high", "skip")
    for answers in product((False, True), repeat=1 if quality == "skip" else 2)
)
LOW_ZERO = PLANS.index(Plan("low", POSITIVE_ON_ZERO))
HIGH_ZERO = PLANS.index(Plan("high", POSITIVE_ON_ZERO))
SKIP_NO = PLANS.index(Plan("skip", (False,)))
SKIP_YES = PLANS.index(Plan("skip", (True,)))


@dataclass(frozen=True, slots=True)
class World:
    theta: F
    beta: F
    tag: int
    route: str

    def __post_init__(self) -> None:
        positive_label(self.theta)
        if self.tag not in (0, 1) or self.route not in ROUTES:
            raise ValueError("invalid responder tag or physical route")
        if self.beta < 0 or self.theta / 4 + F(1, 16) + self.beta > 1:
            raise ValueError("invalid governed finalizer law")


@dataclass(frozen=True, slots=True)
class CountNode:
    depth: int
    stays: int
    public_bit: int
    seed_flow: int
    children: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class Group:
    route: str
    stays: int
    public_bit: int
    multiplicity: int
    record: tuple[int, ...] | None = None

    @property
    def key(self) -> tuple[str, int]:
        return self.route, self.stays


@dataclass(frozen=True, slots=True)
class CountGraph:
    N: int
    nodes: tuple[CountNode, ...]
    groups: tuple[Group, ...]


def build_count_graph(N: int) -> CountGraph:
    """Build the actual chance-symbol DAG and propagate its unweighted seed flows."""
    if N < 0:
        raise ValueError("the prelude length is nonnegative")
    nodes = []
    flow = [1]
    for depth in range(N + 1):
        next_flow = [0] * (depth + 2)
        next_offset = (depth + 1) * (depth + 2) // 2
        for stays, amount in enumerate(flow):
            children = ()
            if depth < N:
                children = (("flip", next_offset + stays), ("stay", next_offset + stays + 1))
                next_flow[stays] += amount
                next_flow[stays + 1] += amount
            nodes.append(CountNode(depth, stays, (depth - stays) % 2, amount, children))
        if depth < N:
            flow = next_flow
    groups = tuple(
        Group(route, stays, (N - stays) % 2, amount)
        for route in ROUTES
        for stays, amount in enumerate(flow)
    )
    return CountGraph(N, tuple(nodes), groups)


def build_explicit_groups(N: int) -> tuple[Group, ...]:
    """Enumerate actual delivered v histories without using graph edges or binomial counts."""
    if not 0 <= N <= 12:
        raise ValueError("explicit enumeration is reserved for small verification cases")
    groups = []
    for route in ROUTES:
        for record in product((0, 1), repeat=N):
            previous = 0
            stays = 0
            for bit in record:
                stays += previous == bit
                previous = bit
            groups.append(Group(route, stays, previous, 1, record))
    return tuple(groups)


def local_vertex(world: World, public_bit: int, plan: Plan) -> tuple[F, ...]:
    """Conditional metric column for one genuine local plan in one complete world."""
    theta = world.theta
    if plan.quality == "skip":
        issue = F(plan.answers[0])
    else:
        high = theta if plan.quality == "high" else F(1, 4) + theta / 2
        issue = (1 - high) * plan.answers[0] + high * plan.answers[1]
    positive = positive_label(theta)
    risk_if_issued = theta / 4 + F(world.tag ^ public_bit, 16) + world.beta
    violation = issue * risk_if_issued
    useful = F(1, 2) + (issue * (1 - risk_if_issued) / 2 if positive else 0)
    return (issue, violation, violation, 1 - issue if positive else issue,
            useful, COST[plan.quality], violation - THRESHOLD * issue)


def slot_payoffs(
    world: World, public_bit: int, probabilities: Sequence[F]
) -> tuple[F, ...]:
    """Weighted metrics of a local simplex, skipping its zero-weight vertices."""
    terms = [(mass, local_vertex(world, public_bit, plan))
             for mass, plan in zip(probabilities, PLANS) if mass]
    return tuple(sum((mass * values[i] for mass, values in terms), F(0))
                 for i in range(len(METRICS)))


def world_weights(N: int, world: World) -> tuple[F, ...]:
    """Per-history factors, before the count multiplicity or any decision weight."""
    p = stay_probability(world.theta, world.tag)
    return tuple(p**stays * (1 - p)**(N - stays) for stays in range(N + 1))


def evaluate(
    N: int, groups: Sequence[Group], choices: Sequence[Sequence[F]], world: World
) -> dict[str, F]:
    """Evaluate one common count or explicit controller on a fixed whole world."""
    if len(groups) != len(choices):
        raise ValueError("each group needs one local plan distribution")
    weights = world_weights(N, world)
    values = [F(0)] * len(METRICS)
    mass_sum = F(0)
    # Conditional score is constant for equal local mixtures and parity at this world.
    payoff_cache: dict[tuple[int, tuple[F, ...]], tuple[F, ...]] = {}
    for group, probabilities in zip(groups, choices):
        if group.route != world.route:
            continue
        mass = group.multiplicity * weights[group.stays]
        mass_sum += mass
        key = group.public_bit, tuple(probabilities)
        if key not in payoff_cache:
            payoff_cache[key] = slot_payoffs(world, group.public_bit, probabilities)
        for i, value in enumerate(payoff_cache[key]):
            values[i] += mass * value
    if mass_sum != 1:
        raise ValueError("history groups do not partition this world's full prelude")
    return dict(zip(METRICS, values))


def pure_vertex(index: int) -> tuple[F, ...]:
    return tuple(F(i == index) for i in range(len(PLANS)))


def paid_mix(high: F) -> tuple[F, ...]:
    if not 0 <= high <= 1:
        raise ValueError("high selection is a probability")
    return tuple((1 - high if i == LOW_ZERO else high if i == HIGH_ZERO else F(0))
                 for i in range(len(PLANS)))


def arm_distribution(arm: str) -> tuple[F, ...]:
    low, high, skip = ARM_MIX[arm]
    weights = [F(0)] * len(PLANS)
    weights[LOW_ZERO], weights[HIGH_ZERO] = low, high
    weights[SKIP_NO] = weights[SKIP_YES] = skip / 2
    return tuple(weights)


def group_explicit_choices(
    explicit: Sequence[Group], choices: Sequence[Sequence[F]], compact: Sequence[Group]
) -> tuple[tuple[F, ...], ...]:
    """Average explicit realization weights in each full (route, count) cell."""
    if len(explicit) != len(choices):
        raise ValueError("all explicit histories need local distributions")
    total: dict[tuple[str, int], list[F]] = defaultdict(lambda: [F(0)] * len(PLANS))
    counts: dict[tuple[str, int], int] = defaultdict(int)
    for group, probabilities in zip(explicit, choices):
        if group.record is None or group.multiplicity != 1:
            raise ValueError("source must enumerate individual lawful histories")
        if len(probabilities) != len(PLANS) or min(probabilities) < 0 or sum(probabilities) != 1:
            raise ValueError("invalid local realization simplex")
        counts[group.key] += 1
        for i, value in enumerate(probabilities):
            total[group.key][i] += value
    result = []
    for group in compact:
        if counts[group.key] != group.multiplicity:
            raise ValueError("explicit and compact cell sizes differ")
        result.append(tuple(value / group.multiplicity for value in total[group.key]))
    return tuple(result)


def lift_count_choices(
    compact: Sequence[Group], choices: Sequence[Sequence[F]], explicit: Sequence[Group]
) -> tuple[tuple[F, ...], ...]:
    if len(compact) != len(choices):
        raise ValueError("every compact group needs a choice")
    by_count = {group.key: tuple(choice) for group, choice in zip(compact, choices)}
    return tuple(by_count[group.key] for group in explicit)
