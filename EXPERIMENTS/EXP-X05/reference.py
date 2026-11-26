"""Independent source-policy, witness, and exact outside-context verifier."""

from dataclasses import dataclass
from itertools import combinations, product
from math import prod

from domain import CLASSES, FRAGMENT, FREEZES, HISTORIES, INTERFACES


class RejectedSource(ValueError):
    pass


class InvalidReport(AssertionError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidReport(message)


@dataclass(frozen=True)
class Row:
    mode: int
    answers: tuple[int, ...]
    costs: tuple[int | None, ...]


def source_ok(case):
    """Check the fragment directly from source records, before accepting a proof."""
    if (
        case.fragment != FRAGMENT or case.freeze not in FREEZES
        or not 1 <= len(case.stages) <= 64
        or type(case.budget) is not int or not 0 <= case.budget <= 10000
    ):
        raise RejectedSource("case outside the finite fragment")
    graphs = [(stage.graph, stage.width, False) for stage in case.stages]
    graphs.append((case.terminal, 0, True))
    for graph, width, terminal in graphs:
        expected_join = None if terminal else len(graph.nodes) - 1
        if not graph.nodes or graph.join != expected_join:
            raise RejectedSource("invalid serial join")
        if not terminal and (not 1 <= width <= 3 or graph.nodes[graph.join].actions):
            raise RejectedSource("invalid stage width or pending join action")
        for attribute in ("name", "observation"):
            labels = [getattr(node, attribute) for node in graph.nodes]
            if "" in labels or len(labels) != len(set(labels)):
                raise RejectedSource("source states must have identifiable observations")
        for index, node in enumerate(graph.nodes):
            if (
                type(node.history) is not int or node.history not in range(len(HISTORIES))
                or len(node.labels) != len(HISTORIES)
                or any(type(label) is not int for label in node.labels)
                or len(node.effects) != 3
                or any(fact is not None and (
                    type(fact) is not int or fact not in range(width)
                ) for fact in node.effects)
                or len(set(node.authority)) != len(node.authority)
                or set(node.authority).difference(INTERFACES)
            ):
                raise RejectedSource("invalid source coordinates")
            if len({op.name for op in node.actions}) != len(node.actions):
                raise RejectedSource("duplicate actions")
            for op in node.actions:
                if (
                    not op.name or op.interface != "route" or "route" not in node.authority
                    or type(op.price) is not int or not 0 <= op.price <= 10000
                ):
                    raise RejectedSource("invalid action")
                labels = tuple(branch.outcome for branch in op.support)
                if not labels or "" in labels or len(set(labels)) != len(labels):
                    raise RejectedSource("invalid support labels")
                if any(
                    type(branch.successor) is not int
                    or not index < branch.successor < len(graph.nodes)
                    for branch in op.support
                ):
                    raise RejectedSource("nonforward support")
    initial = interpret(case.terminal.nodes[0], ())
    for stage in case.stages:
        variables = set(range(1, stage.width + 1))
        for clause in stage.clauses:
            if not clause or any(type(literal) is not int or abs(literal) not in variables
                                 for literal in clause):
                raise RejectedSource("nonlocal evidence")
        names = [query.name for query in stage.queries]
        if not all(names) or len(names) != len(set(names)):
            raise RejectedSource("invalid query names")
        for query in stage.queries:
            if not (
                type(query.facts) is int and 0 < query.facts < 2 ** stage.width
                and type(query.price) is int and 0 < query.price <= 10000
            ):
                raise RejectedSource("query outside the allowed interface")
        for boundary in (stage.graph.nodes[0], stage.graph.nodes[stage.graph.join]):
            if any(fact is not None for fact in boundary.effects) or interpret(boundary, ()) != initial:
                raise RejectedSource("incompatible serial boundary")


def facts_of(mode, width):
    return tuple(bool((mode // 2 ** i) % 2) for i in range(width))


def compatible_modes(stage):
    for assignment in product((False, True), repeat=stage.width):
        if all(any(
            assignment[abs(lit) - 1] if lit > 0 else not assignment[abs(lit) - 1]
            for lit in clause
        ) for clause in stage.clauses):
            mode = sum(2 ** i for i, value in enumerate(assignment) if value)
            yield mode, assignment


def interpret(node, assignment):
    changes = tuple(fact is not None and assignment[fact] for fact in node.effects)
    history = 1 if changes[0] else node.history
    labels = (0, 0, 1, 2, 3) if changes[1] else node.labels
    equalities = frozenset(
        (first, second) for first, second in combinations(range(len(HISTORIES)), 2)
        if labels[first] == labels[second]
    )
    authority = frozenset(node.authority).union({"reserve"} if changes[2] else ())
    return history, equalities, authority


def policy_signature(graph, assignment, *, first_touch=False, first_cost=False):
    """List proper supported local policies before filtering their resource footprint."""
    coordinates = tuple(interpret(node, assignment) for node in graph.nodes)
    closed = []
    for history, equalities, _ in coordinates:
        histories = {history}
        for first, second in equalities:
            if history == first:
                histories.add(second)
            elif history == second:
                histories.add(first)
        classes = sum(not histories.isdisjoint(compatible) for _, compatible in CLASSES)
        if classes == 0 or (graph.join is not None and classes == 1):
            raise RejectedSource("empty or prematurely closed semantic fiber")
        closed.append(classes == 1)

    # A policy is its worst cost and the union of extensional changes in its support.
    def policies(origin):
        if origin == graph.join or closed[origin]:
            return ((0, frozenset()),)
        catalog = set()
        for operation in graph.nodes[origin].actions:
            if operation.interface not in coordinates[origin][2]:
                continue
            transitions = tuple(branch.successor for branch in operation.support)
            inspected = transitions[:1] if first_touch else transitions
            followed = transitions[:1] if first_cost else transitions
            effects = frozenset(
                key for dest in inspected
                for key, lvalue, rvalue in zip("ERA", coordinates[origin], coordinates[dest], strict=True)
                if lvalue != rvalue
            )
            for continuation in product(*(policies(dest) for dest in followed)):
                highest_cost = max(value for value, _ in continuation)
                footprint = effects.union(*(resources for _, resources in continuation))
                catalog.add((operation.price + highest_cost, footprint))
        return catalog

    catalog = policies(0)
    signatures = []
    for freeze in FREEZES:
        removed = set() if freeze == "none" else set(freeze)
        candidates = [value for value, effects in catalog if removed.isdisjoint(effects)]
        signatures.append(min(candidates, default=None))
    return tuple(signatures)


def query_answers(stage, assignment):
    return tuple(
        sum(value for value, included in zip(assignment, facts_of(query.facts, stage.width), strict=True)
            if included) % 2
        for query in stage.queries
    )


def independent_rows(stage, modes):
    return tuple(
        Row(mode, query_answers(stage, assignment), policy_signature(stage.graph, assignment))
        for mode, assignment in sorted(modes)
    )


@dataclass
class Reference:
    case: object
    stages: tuple[tuple[Row, ...], ...]
    terminal: tuple[int | None, ...]
    index: int
    queries: tuple[int, ...]
    offsets: tuple[int, ...]
    count: int
    costs: frozenset[int]
    infinity: bool
    edges: tuple[frozenset[tuple[int, ...]], ...]
    pivotal_facts: int


def finite_totals(groups, start, ceiling=None):
    """Enumerate distinct sums, without enumerating combinations achieving them."""
    totals = {start}
    for prices in groups:
        totals = {
            running + price for running in totals for price in prices
            if price is not None and (ceiling is None or running + price <= ceiling)
        }
    return totals


def reference(case):
    source_ok(case)
    rows = tuple(independent_rows(stage, compatible_modes(stage)) for stage in case.stages)
    terminal = policy_signature(case.terminal, ())
    index = FREEZES.index(case.freeze)
    prices = tuple(query.price for stage in case.stages for query in stage.queries)
    offsets = []
    offset = 0
    for stage in case.stages:
        offsets.append(offset)
        offset += len(stage.queries)
    count = prod(len(group) for group in rows)
    values = tuple({row.costs[index] for row in group} for group in rows)
    infinity = bool(count and (terminal[index] is None or any(None in group for group in values)))
    costs = frozenset(
        finite_totals(values, terminal[index]) if count and terminal[index] is not None else ()
    )

    evidence = []
    affected = 0
    for i, group in enumerate(rows):
        local_edges = set()
        pivotal = set()
        if costs and min(costs) <= case.budget and (infinity or max(costs) > case.budget):
            others = finite_totals(values[:i] + values[i + 1:], terminal[index], case.budget)
            for first, second in combinations(group, 2):
                a, b = first.costs[index], second.costs[index]
                if a == b:
                    continue
                lo, hi = sorted((a, b), key=lambda amount: float("inf") if amount is None else amount)
                if not any(
                    context + lo <= case.budget and (hi is None or context + hi > case.budget)
                    for context in others
                ):
                    continue
                local_edges.add(tuple(offsets[i] + j for j, (x, y) in enumerate(
                    zip(first.answers, second.answers, strict=True)
                ) if x != y))
                changed = first.mode ^ second.mode
                if changed.bit_count() == 1:
                    pivotal.add(changed)
        affected += len(pivotal)
        evidence.append(frozenset(local_edges))
    return Reference(
        case, rows, terminal, index, prices, tuple(offsets), count, costs, infinity,
        tuple(evidence), affected,
    )


def completion(ref, modes):
    require(isinstance(modes, (list, tuple)) and len(modes) == len(ref.stages),
            "a completion needs one local assignment per stage")
    rows = []
    for mode, group in zip(modes, ref.stages, strict=True):
        row = next((entry for entry in group if type(mode) is int and mode == entry.mode), None)
        require(row is not None, "incompatible witness mode")
        rows.append(row)
    return tuple(rows)


def completion_cost(rows, terminal, freeze):
    amounts = (terminal[freeze], *(row.costs[freeze] for row in rows))
    return None if None in amounts else sum(amounts)


def proof_pair(ref, witness, selected):
    first = completion(ref, witness["left"])
    second = completion(ref, witness["right"])
    changes = tuple(i for i, (left, right) in enumerate(zip(first, second, strict=True))
                    if left.mode != right.mode)
    require(
        type(witness["stage"]) is int and changes == (witness["stage"],),
        "witness must differ at its declared single stage",
    )
    low = completion_cost(first, ref.terminal, ref.index)
    high = completion_cost(second, ref.terminal, ref.index)
    require(low is not None and low <= ref.case.budget and (high is None or high > ref.case.budget),
            "a witness must straddle the exact source target")
    require(tuple(witness["costs"]) == (low, high), "witness costs disagree with source")
    left_answers = tuple(answer for row in first for answer in row.answers)
    right_answers = tuple(answer for row in second for answer in row.answers)
    edge = tuple(
        i for i, (left, right) in enumerate(zip(left_answers, right_answers, strict=True))
        if left != right
    )
    require(tuple(witness["edge"]) == edge and not set(edge).intersection(selected),
            "invalid disagreement edge or selected-answer agreement")
    require(edge in ref.edges[witness["stage"]], "witness not in independent edge set")
    return edge


def sufficient(selected, all_edges):
    return all(any(q in selected for q in edge) for stage in all_edges for edge in stage)


def optimum(prices, stage_edges):
    """Enumerate local subset prices directly from independently reconstructed edges."""
    if any(() in edges for edges in stage_edges):
        return None
    result = 0
    for edges in stage_edges:
        if not edges:
            continue
        involved = sorted({q for edge in edges for q in edge})
        result += min(
            sum(prices[q] for q in subset)
            for size in range(1, len(involved) + 1)
            for subset in combinations(involved, size)
            if all(not set(subset).isdisjoint(edge) for edge in edges)
        )
    return result


def target_set(ref):
    if not ref.count:
        return frozenset()
    outcomes = {cost <= ref.case.budget for cost in ref.costs}
    if ref.infinity:
        outcomes.add(False)
    return frozenset(outcomes)


def verify_symbolic(ref, result):
    """Check each retained search round, terminal proof and minimum weight."""
    if result["compatible_count"] is not None:
        require(result["compatible_count"] == ref.count, "compatibility count mismatch")
    outcomes = target_set(ref)
    if result["feasibility"] is not None:
        completion(ref, result["feasibility"])
        require(
            tuple(sorted(ref.costs)) == tuple(result["finite_costs"])
            and ref.infinity == result["infinity"],
            "cost projection mismatch",
        )
    learned = [set() for _ in ref.stages]
    prior_bound = None
    pair_count = 0
    checked_unsat = False
    empty_edge = False
    for round_ in result["rounds"]:
        require(not checked_unsat and not empty_edge, "search continued after terminal result")
        indices = tuple(round_["selected"])
        require(indices == tuple(sorted(set(indices))) and all(
            type(q) is int and 0 <= q < len(ref.queries) for q in indices
        ), "invalid query selection")
        selected = set(indices)
        lower = optimum(ref.queries, learned)
        require(
            lower == round_["bound"] == sum(ref.queries[q] for q in indices)
            and sufficient(selected, learned), "claimed optimizer bound is not exact",
        )
        prior_bound = lower
        witness = round_["witness"]
        if witness is None:
            require(ref.count and sufficient(selected, ref.edges), "invalid UNSAT claim")
            checked_unsat = True
        else:
            require(outcomes == {False, True}, "underidentification requires both polarities")
            edge = proof_pair(ref, witness, selected)
            pair_count += 1
            if edge:
                learned[witness["stage"]].add(edge)
            else:
                empty_edge = True
    status = result["status"]
    if status == "INCONSISTENT":
        require(
            not ref.count and result["compatible_count"] == 0
            and len(ref.stages[result["empty_stage"]]) == 0 and not result["rounds"]
            and result["initial"] == "INCONSISTENT",
            "inconsistency requires empty evidence",
        )
    elif status == "AUDIT_INACCESSIBLE":
        require(empty_edge and result["initial"] == "UNDERIDENTIFIED"
                and optimum(ref.queries, ref.edges) is None, "invalid audit-inaccessibility claim")
    elif status in {"IDENTIFIED", "CERTIFIED"}:
        require(checked_unsat and result["feasibility"] is not None, "missing terminal proof")
        expected = "IDENTIFIED" if len(outcomes) == 1 else "UNDERIDENTIFIED"
        require(result["initial"] == expected, "initial identification mismatch")
        require(
            prior_bound == result["lower_bound"] == result["upper_bound"] == result["cost"]
            == optimum(ref.queries, ref.edges),
            "global optimality gap",
        )
        require(tuple(result["selected"]) == tuple(result["rounds"][-1]["selected"]),
                "submitted queries differ from terminal proof")
        if status == "IDENTIFIED":
            require(outcomes == {result["value"]} and result["cost"] == 0,
                    "incorrect point identification")
        else:
            require(outcomes == {False, True} and result["value"] is None,
                    "a uniform audit does not acquire its answers")
    else:
        require(status == "UNRESOLVED" and result["reason"] in {"step-cap", "deadline"},
                "unexpected reported status")
        require(not checked_unsat and not empty_edge, "confirmed proof labeled unresolved")
        if result["lower_bound"] is not None:
            require(result["lower_bound"] in {prior_bound, optimum(ref.queries, learned)},
                    "unverified partial lower bound")
    if status not in {"IDENTIFIED", "CERTIFIED"}:
        require(all(result[key] is None for key in ("cost", "value", "upper_bound"))
                and not result["selected"], "unsupported affirmative claim")
    return {"witness_pairs": pair_count, "unsat_rounds": int(checked_unsat)}
