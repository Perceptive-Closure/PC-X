"""Fixed installations, exact rational lottery inputs, and fixture loading."""

import hashlib
import hmac
import json
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from .store import canonical_json


# This public synthetic test key is a stability/authenticity convention for the
# registered closed host interface. It is never supplied to a controller.
_SIGNING_KEY = b"PCX EXP-X17 PUBLIC SYNTHETIC SOURCE KEY V1"
_FIXTURES = Path(__file__).parent / "fixtures"
_SOURCE_DOMAIN = b"PCX-EXP-X17-native-v1"
ROUTES = ("L", "R")
PRICE_EIGHTHS = {"low": 3, "high": 8, "skip": 0, "direct": 4}
CHECK_EIGHTHS = {"ordinary": 1, "guard": 2, "full": 8}
CONTROLS = frozenset(
    {f"C{number:02}" for number in range(1, 15)} | {"C17", "C18"}
)


def fraction_text(value):
    return str(value)


@dataclass(frozen=True, slots=True)
class World:
    theta: Fraction
    beta: Fraction
    m: int
    k: str
    B: str
    N: int

    def __post_init__(self):
        if not isinstance(self.theta, (str, int, Fraction)) or type(self.theta) is bool:
            raise TypeError("theta must have an exact rational representation")
        if not isinstance(self.beta, (str, int, Fraction)) or type(self.beta) is bool:
            raise TypeError("beta must have an exact rational representation")
        theta, beta = Fraction(self.theta), Fraction(self.beta)
        object.__setattr__(self, "theta", theta)
        object.__setattr__(self, "beta", beta)
        if not (Fraction(1, 8) <= theta <= Fraction(1, 4) or Fraction(3, 4) <= theta <= Fraction(7, 8)):
            raise ValueError("theta is outside the represented strata")
        if type(self.m) is not int or self.m not in (0, 1) or self.k not in ROUTES:
            raise ValueError("invalid program tag or route")
        if type(self.N) is not int or self.N < 1:
            raise ValueError("N must be a positive integer")
        if self.B == "good" and Fraction(0) <= beta <= Fraction(1, 32):
            return
        if self.B == "bad" and beta == Fraction(1, 2):
            return
        raise ValueError("surcharge is outside the registered revision range")

    @property
    def target(self):
        return self.theta <= Fraction(1, 2)

    @property
    def stay_probability(self):
        contrast = self.theta * (1 - self.theta) / 2
        return Fraction(1, 2) + contrast * (1 if self.m == 0 else -1)

    def raw(self):
        return {
            "theta": fraction_text(self.theta),
            "beta": fraction_text(self.beta),
            "m": self.m,
            "k": self.k,
            "B": self.B,
            "N": self.N,
        }


def immutable_stock(route):
    if route not in ROUTES:
        raise ValueError("invalid synthetic stock route")
    body = (_FIXTURES / f"stock-{route}.json").read_text(encoding="utf-8").encode()
    stock = json.loads(body)
    expected = stock["routing"][stock["zone"]]
    if stock["expected_route"] != route or expected != route:
        raise ValueError("native stock route does not match its signed physical destination")
    return stock, body


def signature(kind, record):
    message = kind.encode("ascii") + b"\0" + canonical_json(record)
    return hmac.new(_SIGNING_KEY, message, hashlib.sha256).hexdigest()


def signed_record(kind, payload):
    return {**payload, "signature": signature(kind, payload)}


def verify_signed(kind, record):
    if not isinstance(record, dict) or not isinstance(record.get("signature"), str):
        return False
    unsigned = {key: value for key, value in record.items() if key != "signature"}
    try:
        return hmac.compare_digest(record["signature"], signature(kind, unsigned))
    except (TypeError, ValueError):
        return False


def normalized_seed(seed):
    if isinstance(seed, (str, int)) and type(seed) is not bool:
        return seed
    if isinstance(seed, bytes):
        return {"bytes_hex": seed.hex()}
    raise TypeError("seed must be a public replay string, integer, or bytes")


def _private_key(seed_record):
    return hashlib.sha256(_SOURCE_DOMAIN + b"\0" + canonical_json(seed_record)).digest()


def draw_word(key, domain, index, upper):
    """Sample by accepting a fixed-width candidate only when it is below upper."""
    if upper < 1:
        raise ValueError("draw limit must be positive")
    width = (upper - 1).bit_length()
    if width == 0:
        return 0, 0
    byte_count = (width + 7) // 8
    mask = (1 << width) - 1
    prefix = key + b"\0" + domain.encode("ascii") + b"\0" + str(index).encode() + b"\0"
    rejected = 0
    while True:
        candidate_bytes = b"".join(
            hashlib.sha256(prefix + f"{rejected}:{block}".encode()).digest()
            for block in range((byte_count + 31) // 32)
        )[:byte_count]
        candidate = int.from_bytes(candidate_bytes, "big") & mask
        if candidate < upper:
            return candidate, rejected
        rejected += 1


def reconstruct_draw(seed_record, domain, index, upper):
    """Reconstruct an accepted draw and rejection count from its private ledger."""
    return draw_word(_private_key(seed_record), domain, index, upper)
