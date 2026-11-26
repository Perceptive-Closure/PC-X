"""Experimental local fixture adapter, separate from policy and counterfactual solver."""

from dataclasses import dataclass, replace

from common import HISTORIES, STRATA, case_id, require


@dataclass(frozen=True)
class Checkpoint:
    admitted: tuple
    renderer: str
    authority: tuple = ("offline",)
    phase: str = "received"

    def display(self, history):
        if self.renderer == "merged" and history in (("ticket:0",), ("ticket:1",)):
            return "ticket awaiting display"
        return "|".join(history) or "no admission"

    def record(self):
        return {
            "H": list(self.admitted),
            "PR": [self.display(h) for h in HISTORIES],
            "authority": list(self.authority),
            "public_phase": self.phase,
        }


def receive(provisioned, index):
    # Anonymous receipt marks are read by custody. This adapter supplies only the inert ticket
    # label corresponding to the fixture world during native evaluation.
    ledger = []
    for mark in provisioned["receipt_marks"]:
        require(mark == "anonymous-ticket-admitted", "unrecognized receipt mark")
        ledger.append(f"ticket:{index}")
    return Checkpoint(tuple(ledger), provisioned["renderer"])


def transition(checkpoint, operation, index):
    require(checkpoint.phase == "received" and "offline" in checkpoint.authority,
            "source checkpoint has no usable operation")
    if operation == "publish":
        ticket = f"ticket:{index}"
        admission = checkpoint.admitted if ticket in checkpoint.admitted else checkpoint.admitted + (ticket,)
        return replace(checkpoint, admitted=admission, renderer="exact", phase="settled")
    if operation == "attest":
        return replace(checkpoint, admitted=checkpoint.admitted + (f"review:{index}",), phase="settled")
    raise ValueError(f"unknown source atomic operation {operation}")


def partition(record):
    buckets = {}
    for index, display in enumerate(record["PR"]):
        buckets.setdefault(display, set()).add(index)
    return {frozenset(bucket) for bucket in buckets.values()}


def touched(before, after):
    resources = set()
    if before["H"] != after["H"]:
        resources.add("E")
    if partition(before) != partition(after):
        resources.add("R")
    if set(before["authority"]) != set(after["authority"]):
        resources.add("A")
    return resources


def cases(assignment):
    for stratum in STRATA:
        for member in (0, 1):
            name = case_id(stratum, member)
            provisioned = assignment["adapters"][name]
            yield name, stratum, provisioned


def prepared_actions(stratum, start):
    source_actions = [("publish", 1)]
    if stratum["backup_cost"] is not None:
        source_actions.append(("attest", stratum["backup_cost"]))
    for name, cost in source_actions:
        # Calculate the complete candidate transaction on scratch checkpoint values before it
        # can commit. Freeze the whole action if any supported fixture world touches the resource.
        successors = [transition(checkpoint, name, i).record() for i, checkpoint in enumerate(start)]
        full_touch = set().union(*(touched(before.record(), after)
                                   for before, after in zip(start, successors, strict=True)))
        yield name, cost, successors, full_touch
