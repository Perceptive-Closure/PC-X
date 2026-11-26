"""Local print policy, service state machine and intervention attachments."""


class Printer:
    def __init__(self, capacity):
        self.capacity = capacity
        self.queue = 0
        self.tick = 0

    def work(self, arrivals):
        self.queue += arrivals
        completed = min(self.capacity, self.queue)
        self.queue -= completed
        self.tick += 1
        return completed


class PrintReplica:
    def __init__(self, protocol, arm, disturbed_port):
        if arm not in protocol["arms"] or disturbed_port not in protocol["ports"]:
            raise ValueError("Unsupported arm or port assignment")
        self.protocol = protocol
        self.arm = arm
        self.printer = Printer(
            protocol["disturbed_capacity"] if arm == disturbed_port else protocol["normal_capacity"]
        )
        self.previous = None
        self.passive_log = []
        self.lamp = 0

    def step(self, request, policy_ticket, workload_ticket):
        p = self.protocol
        if request not in p["requests"] or self.printer.tick >= p["horizon"]:
            raise ValueError("Request is outside the admitted horizon or request set")
        if any(type(ticket) is not int or ticket not in range(p["tickets"])
               for ticket in (policy_ticket, workload_ticket)):
            raise ValueError("Unsupported ticket")
        cutoff = 1 + (request == "surge") + (self.previous == "surge")
        route = "bulk" if policy_ticket < cutoff else "standard"
        public = [request, p["advertised_slots"], route, "accepted"]
        arrivals = 2 + (request == "surge") + (workload_ticket < 2) - (route == "bulk")
        completed = self.printer.work(arrivals)
        self.previous = request
        state = [self.printer.tick, self.previous, self.printer.queue]
        side = None
        if self.arm in p["ports"]:
            self.passive_log.append(public.copy())
            side = ["copy", self.passive_log[-1]]
        if self.arm == "placebo":
            self.lamp = 1 - self.lamp
            side = ["lamp", self.lamp]
        return [public, [arrivals, completed], state, side]


def run_sequence(protocol, arm, disturbed_port, steps):
    replica = PrintReplica(protocol, arm, disturbed_port)
    return [replica.step(*step) for step in steps]


def calibrate(protocol, query, disturbed_port):
    """Read one admitted isolated input/transition fact without running the policy."""
    if query == "display_slots":
        return {"display_slots": protocol["advertised_slots"]}
    if query not in protocol["query_costs"] or not query.endswith("_capacity"):
        raise ValueError("Unsupported calibration")
    arm = query.removesuffix("_capacity")
    instrument = PrintReplica(protocol, arm, disturbed_port).printer
    before = [instrument.tick, instrument.queue]
    supplied = protocol["pulse_work"]
    done = instrument.work(supplied)
    return {"start": before, "supplied": supplied, "completed": done,
            "end": [instrument.tick, instrument.queue]}
