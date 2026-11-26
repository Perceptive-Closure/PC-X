"""Concrete virtual workshop. The belief solver does not enter this module."""

from dataclasses import dataclass, replace

from common import COST, HELD, JOBS, PROFILES, SLIPS, canonical, digest


@dataclass(frozen=True)
class Workshop:
    profile: str
    signature: bool
    slip: int
    records: tuple = ()
    shuttered: bool = False
    released: bool = False
    decoded: bool = False
    receipts: frozenset = frozenset()

    @property
    def ready(self):
        return not self.shuttered and len(self.records) < len(JOBS)

    @property
    def works_open(self):
        return self.ready and "buffer" not in self.records

    def authorization(self):
        if not self.ready:
            return ()
        spec = PROFILES[self.profile]
        choices = ["refuse", "layout", "refine"]
        if self.signature:
            choices.append("plate")
        if spec["relief"]:
            choices.append("grant")
        if self.works_open:
            choices += ["left", "right"]
            if not self.records:
                choices.append("buffer")
            if self.released:
                choices.append("relief")
        return tuple(sorted(choices))

    def panel(self, slip):
        if self.decoded or PROFILES[self.profile]["panel"] == "indexed":
            return "offer-" + str(slip)
        return "queued"

    def wire(self):
        return [self.profile, self.signature, self.slip, len(self.records),
                "buffer" in self.records, self.shuttered, self.released, self.decoded,
                "layout" in self.receipts, "plate" in self.receipts]

    def enact(self, action):
        if action not in self.authorization():
            return self, "unauthorized", None
        if action == "grant":
            return replace(self, released=True), "ok", "granted"
        if action == "layout":
            admitted = replace(self, receipts=self.receipts | {"layout"})
            return admitted, "ok", "layout-" + PROFILES[self.profile]["entry"]
        if action == "plate":
            return replace(self, receipts=self.receipts | {"plate"}), "ok", "two-slots"
        if action == "refine":
            remapped = replace(self, decoded=True)
            pending = self.works_open and len(self.records) == 1
            return remapped, "ok", remapped.panel(self.slip) if pending else "reindexed"
        if action == "refuse":
            return replace(self, shuttered=True), "ok", "stopped"
        if action == "buffer":
            return replace(self, records=("buffer",)), "ok", "buffered"
        if action != "relief" and not self.bench_accepts(action):
            return self, "unsafe", None
        dispatched = replace(self, records=self.records + (action,))
        observed = self.panel(self.slip) if dispatched.ready else "complete"
        return dispatched, "ok", observed

    def bench_accepts(self, bench):
        route = PROFILES[self.profile]["entry"]
        if route in ("left", "right"):
            receiving_bench = (route, "right" if route == "left" else "left")
            route = receiving_bench[self.slip if self.records else 0]
        return route == "both" or route == bench


def calibration(profile, signature, request):
    """Independent measurement on a reset twin, with no production method invoked."""
    twin = Workshop(profile, signature, 0)
    if request == "layout":
        enabled = [bench for bench in ("left", "right") if twin.bench_accepts(bench)]
        return {(): "closed", ("left",): "left", ("right",): "right",
                ("left", "right"): "both"}[tuple(enabled)]
    if request == "viewer":
        signals = {twin.panel(slip) for slip in SLIPS}
        return "indexed" if len(signals) == len(SLIPS) else "masked"
    if request == "roster":
        return "plate" in twin.authorization()
    if request == "nameplate":
        return "two-slots" if len(JOBS) == 2 and not twin.records else "different-slots"
    raise ValueError(f"Unknown calibration request {request}")


def play(profile, signature, slip, scope, policy):
    """Run one physical ticket and emit every supported operational event."""
    machine = Workshop(profile, signature, slip)
    log = []
    finish = "deadline"
    for tick in range(1, scope["horizon"] + 1):
        action = policy.get("action")
        if action is None:
            raise ValueError("A policy ended before the workshop was terminal")
        if action in scope["actions"]:
            next_machine, status, observed = machine.enact(action)
        else:
            next_machine, status, observed = machine, "unauthorized", None
        job = None
        if len(next_machine.records) != len(machine.records):
            job = {"order": JOBS[len(machine.records)], "bench": next_machine.records[-1]}
        log.append({"tick": tick, "action": action, "status": status, "observation": observed,
                    "physical_job": job, "authorized_before": list(machine.authorization())})
        machine = next_machine
        if status != "ok":
            finish = status
            break
        if machine.shuttered or len(machine.records) == len(JOBS):
            finish = "refused" if machine.shuttered else "complete"
            break
        if observed not in policy.get("branches", {}):
            finish = "unsupported"
            break
        policy = policy["branches"][observed]
    return {"events": log, "finish": finish}


def score(profile, signature, slip, scope, record):
    """Check physical work and authorization directly from the retained event record."""
    port = PROFILES[profile]
    entry = port["entry"]
    qualified = []
    cost = 0
    released = False
    indexed = port["panel"] == "indexed"
    failure = None
    for tick, event in enumerate(record["events"], 1):
        if tick != event["tick"] or tick > scope["horizon"] or failure is not None:
            raise ValueError("Invalid physical sequence")
        parked = any(job["bench"] == "buffer" for job in qualified)
        available = {"refuse", "refine", "layout"}
        if port["relief"]:
            available.add("grant")
        if signature:
            available.add("plate")
        if not parked:
            available.update(("left", "right"))
            if not qualified:
                available.add("buffer")
            if released:
                available.add("relief")
        if sorted(available) != event["authorized_before"]:
            raise ValueError("Authority ledger does not match the signed workshop")
        action = event["action"]
        status, observed, job = "ok", None, None
        if action not in available or action not in scope["actions"]:
            status = "unauthorized"
        elif action in ("left", "right") and not (
            entry == "both" or
            entry in ("left", "right") and
            (action != entry if qualified and slip else action == entry)
        ):
            status = "unsafe"
        elif action in ("left", "right", "relief", "buffer"):
            job = {"order": JOBS[len(qualified)], "bench": action}
            qualified.append(job)
            if len(qualified) == len(JOBS):
                failure, observed = "complete", "complete"
            elif action == "buffer":
                observed = "buffered"
            else:
                observed = f"offer-{slip}" if indexed else "queued"
        elif action == "refuse":
            failure, observed = "refused", "stopped"
        elif action == "refine":
            indexed = True
            observed = f"offer-{slip}" if qualified and not parked else "reindexed"
        elif action == "grant":
            released, observed = True, "granted"
        elif action == "layout":
            observed = f"layout-{entry}"
        elif action == "plate":
            observed = "two-slots"
        if status != "ok":
            failure = status
        else:
            cost += COST.get(action, 0)
        if (status, observed, job) != (event["status"], event["observation"], event["physical_job"]):
            raise ValueError("Physical event does not agree with the scorer")
    finish = record["finish"]
    if not record["events"] or (failure is not None and finish != failure) or (
        failure is None and finish not in ("unsupported", "deadline")
    ) or (finish == "deadline" and len(record["events"]) != scope["horizon"]):
        raise ValueError("The final workshop disposition is inconsistent")
    return {"finish": finish, "qualified": len(qualified), "audit_cost": cost,
            "safe": finish not in ("unsafe", "unauthorized"),
            "useful": finish == "complete" and len(qualified) == len(JOBS)}


def tickets(seed):
    workload = [(port, slip, arm) for port in HELD["ports"] for slip in SLIPS for arm in HELD["arms"]]
    return sorted(workload, key=lambda ticket: (digest(canonical([seed, *ticket])), ticket))
