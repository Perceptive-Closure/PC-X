"""Local inert tray task, monitor projection and independent route-card readback."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Fixture:
    regime: str
    revision: str


@dataclass(frozen=True)
class Visible:
    stratum: str
    mark: int
    orientation: int
    warning: bool
    tray: str

    @property
    def alarm(self):
        return self.warning

    def transcript(self):
        return self.stratum, self.mark, self.orientation, self.warning, self.tray, self.alarm


def execute(stratum, ticket, reader_control=False):
    """Route solely by the public marker, before any truth or fixture read."""
    mark = ticket % 6
    orientation = int(ticket % 4 >= 2)
    warning = mark == 0 or (reader_control and mark == 1)
    tray = ("E", "W")[orientation]
    return Visible(stratum, mark, orientation, warning, tray)


def expected_lane(spec, fixture, stratum, ticket):
    """Independent quality instrument reads the upstream reference card."""
    return spec["lane_reference"][fixture.regime][fixture.revision][stratum][ticket]


def quality_label(actual, expected):
    return None if expected is None else actual != expected


def audit_card(spec, fixture, query):
    """Read a card property or the separate calibration sentinel, without running a trial."""
    if query == "calibration_lane":
        return spec["calibration_lanes"][fixture.regime]
    if query == "label_revision":
        return fixture.revision
    raise ValueError(f"Unsupported audit query {query!r}")


def trial(spec, fixture, unit, stratum, index, ticket):
    visible = execute(stratum, ticket)
    expected = expected_lane(spec, fixture, stratum, ticket)
    return {
        "unit": unit, "stratum": stratum, "index": index,
        "ticket": ticket, "visible": visible.transcript(),
        "trusted_lane": expected, "trusted_label": quality_label(visible.tray, expected),
    }
