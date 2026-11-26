"""Two offline dispatch policies with an in-memory input and machine interface."""

from collections import Counter

from common import AGENTS, DESIGN, MODES, TIES, tickets


class Dispatcher:
    """Select a station and service duration using only a local card and memory."""

    def __init__(self, name):
        self.name = name
        self.previous = 1

    def submit(self, demand, prefer_shared, expedited):
        previous = self.previous
        self.previous = demand
        station = "shared" if prefer_shared else f"private-{self.name}"
        duration = 2 if demand == 2 and (not expedited or previous == 2) else 1
        return {"agent": self.name, "seen": demand, "previous": previous,
                "preferred": station, "requested": duration}


class Workshop:
    """Own the presentation gateway and the physical virtual-bench ledger."""

    def __init__(self, allocator, view, tie_order):
        if (allocator, view) not in MODES or tie_order not in TIES:
            raise ValueError("Unsupported workshop installation")
        self.allocator = allocator
        self.view = view
        self.tie_order = tie_order

    def show_cards(self, demands):
        if not demands or not set(demands) <= set(AGENTS):
            raise ValueError("Unknown card recipient")
        if any(type(value) is not int or value not in (1, 2) for value in demands.values()):
            raise ValueError("Invalid demand card")
        if self.view == "shared_summary" and len(demands) == 2 and all(
                demand == 2 for demand in demands.values()):
            return dict.fromkeys(demands, 1)
        return demands.copy()

    def grant(self, requests):
        grants = {request["agent"]: request["preferred"] for request in requests}
        if len(grants) != len(requests) or not grants or not set(grants) <= set(AGENTS):
            raise ValueError("Unknown or duplicate claimant")
        if any(station not in ("shared", f"private-{agent}")
               for agent, station in grants.items()):
            raise ValueError("Claim outside local authority")
        if self.allocator == "exclusive" and list(grants.values()).count("shared") == 2:
            deferred = next(agent for agent in AGENTS if agent != self.tie_order)
            grants[deferred] = f"private-{deferred}"
        return grants

    def execute(self, context, ticket, agents):
        if tuple(ticket) not in tickets(context):
            raise ValueError("Ticket outside frozen context support")
        if agents not in (AGENTS, *((name,) for name in AGENTS)):
            raise ValueError("Unsupported evaluation roster")
        load, tempo = ticket
        dispatchers = {name: Dispatcher(name) for name in agents}
        rows = []
        for turn, plan in enumerate(DESIGN["contexts"][context][load]):
            cards = self.show_cards({name: plan[AGENTS.index(name)] for name in agents})
            orders = []
            for name in agents:
                prefers_shared = tempo < 4 or (turn + AGENTS.index(name)) % 2 == 0
                orders.append(dispatchers[name].submit(cards[name], prefers_shared, tempo == 0))
            grants = self.grant(orders)
            for order in orders:
                # Advancing the simulated service clock is the only operation
                # that emits a physical work quantum.
                quanta = [step for step in range(2) if step < order["requested"]]
                rows.append({"turn": turn, **order, "station": grants[order["agent"]],
                             "quanta": quanta})
        return rows

    def probe(self, query):
        """Read the installed component on sentinel inputs in a fresh replica."""
        if query == "allocator":
            grant_counts = Counter(self.grant(
                [{"agent": name, "preferred": "shared"} for name in AGENTS]
            ).values())
            return {"submitted_shared": 2, "granted_shared": grant_counts["shared"],
                    "granted_private": sum(grant_counts[f"private-{name}"] for name in AGENTS)}
        if query == "view":
            return {
                "sentinel_demands": [2, 2],
                "displayed_in_isolation": [self.show_cards({name: 2})[name] for name in AGENTS],
                "displayed_jointly": list(self.show_cards(dict.fromkeys(AGENTS, 2)).values()),
            }
        if query == "roster":
            return {"first_on_tie": self.tie_order}
        if query == "nameplate":
            return {"displayed_time_quanta_per_turn": 2}
        raise ValueError(f"Unknown calibration: {query}")
