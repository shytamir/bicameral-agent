"""Pure proposal resolution against a caller-supplied, read-only catalogue.

This is not transaction acceptance. No database, authority decision, budget check,
full lifecycle engine, or durable allocation is implemented in P01.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from .base import Contract, EventIDs, Identifier, Positive, canonical_bytes, parse
from .semantics import ObjectType, StateProposal


class CatalogObject(Contract):
    object_id: Identifier
    run_id: Identifier
    object_type: ObjectType
    objective_id: Identifier | None
    revision: Positive
    family_id: Identifier | None
    commitment_links: EventIDs


class CatalogEvent(Contract):
    event_id: Identifier
    run_id: Identifier
    chamber_visible: bool


class ResolutionContext(Contract):
    run_id: Identifier
    objective_id: Identifier | None
    parent_state_id: Identifier | None
    arm: Literal["A", "B", "C"]
    objects: tuple[CatalogObject, ...]
    events: tuple[CatalogEvent, ...]


class Binding(Contract):
    local_key: str
    object_type: ObjectType
    object_id: Identifier
    objective_id: Identifier | None
    family_id: Identifier | None


@dataclass(frozen=True)
class Resolution:
    proposal: StateProposal
    bindings: tuple[Binding, ...]


def resolve_proposal(proposal: StateProposal, context: ResolutionContext,
                     allocate_id: Callable[[], str]) -> Resolution:
    """Resolve all references or raise without mutating the inputs.

    The future Kernel supplies the ID allocator and authoritative catalogue.
    Returned IDs are provisional; P02 must commit them atomically with effects.
    """
    if context.arm == "B":
        raise ValueError("arm B has no semantic proposal channel")
    if proposal.expected_parent_state_id != context.parent_state_id:
        raise ValueError("stale semantic parent")
    if proposal.continuity.focus_objective_id != context.objective_id:
        raise ValueError("handoff focus differs from current Objective")

    objects = {obj.object_id: obj for obj in context.objects}
    events = {event.event_id: event for event in context.events}
    if len(objects) != len(context.objects) or len(events) != len(context.events):
        raise ValueError("duplicate catalogue identity")
    document = proposal.model_dump(mode="json")
    declarations: dict[str, tuple[str, dict]] = {}

    def declare(key: str, kind: str, mutation: dict) -> None:
        if key in declarations:
            raise ValueError("duplicate local binding")
        if context.arm == "C" and kind != "COMMITMENT":
            raise ValueError("arm C excludes Itches and Invariants")
        if "objective_id" in mutation:
            owner = mutation["objective_id"]
            global_invariant = kind.startswith("INVARIANT") and owner is None
            if not global_invariant and (owner is None or owner != context.objective_id):
                raise ValueError("creation belongs to another or absent Objective")
        declarations[key] = (kind, mutation)

    for mutation in document["mutations"]:
        match mutation["kind"]:
            case "ITCH_CREATE":
                declare(mutation["local_key"], "ITCH", mutation)
            case "COMMITMENT_CREATE":
                declare(mutation["local_key"], "COMMITMENT", mutation)
            case "INVARIANT_CREATE":
                declare(mutation["family_local_key"], "INVARIANT_FAMILY", mutation)
                declare(mutation["version_local_key"], "INVARIANT_VERSION", mutation)
            case "INVARIANT_REVISE":
                declare(mutation["successor_local_key"], "INVARIANT_VERSION", mutation)

    used = set(objects) | set(events) | {context.run_id, context.objective_id, context.parent_state_id}
    allocated: dict[str, str] = {}
    for key, (kind, _) in declarations.items():
        identifier = allocate_id()
        # Use a contract field for the allocator's output as well as wire IDs.
        parse(Binding, canonical_bytes({"local_key": key, "object_type": kind,
              "object_id": identifier, "objective_id": None, "family_id": None}))
        if identifier in used:
            raise ValueError("allocator returned a colliding identity")
        used.add(identifier)
        allocated[key] = identifier

    bindings: dict[str, Binding] = {}
    visiting: set[str] = set()

    def check_object(obj: CatalogObject | Binding) -> None:
        if isinstance(obj, CatalogObject) and obj.run_id != context.run_id:
            raise ValueError("foreign Run reference")
        if context.arm == "C" and obj.object_type != "COMMITMENT":
            raise ValueError("object type is excluded from arm C")
        global_invariant = obj.object_type.startswith("INVARIANT") and obj.objective_id is None
        if not global_invariant and (obj.objective_id is None or obj.objective_id != context.objective_id):
            raise ValueError("foreign or absent Objective reference")
        if isinstance(obj, CatalogObject) and obj.object_type == "INVARIANT_VERSION":
            family = objects.get(obj.family_id)
            if (family is None or family.object_type != "INVARIANT_FAMILY"
                    or family.run_id != context.run_id or family.objective_id != obj.objective_id):
                raise ValueError("Invariant family is absent, foreign or inconsistently owned")

    def lookup(reference: dict) -> CatalogObject | Binding:
        if reference["kind"] == "LOCAL":
            key = reference["local_key"]
            if key not in declarations:
                raise ValueError("unbound local reference")
            obj = binding(key)
        else:
            obj = objects.get(reference["object_id"])
            if obj is None:
                raise ValueError("unknown existing reference")
        if obj.object_type != reference["object_type"]:
            raise ValueError("reference type differs from target")
        check_object(obj)
        return obj

    def binding(key: str) -> Binding:
        if key in bindings:
            return bindings[key]
        if key in visiting:
            raise ValueError("cyclic Invariant successor bindings")
        visiting.add(key)
        kind, mutation = declarations[key]
        family_id = None
        if mutation["kind"] == "INVARIANT_REVISE":
            predecessor = lookup(mutation["target"])
            owner = predecessor.objective_id
            family_id = predecessor.family_id
            if family_id is None:
                raise ValueError("Invariant predecessor has no family")
        else:
            owner = mutation["objective_id"]
            if kind == "INVARIANT_VERSION":
                family_id = allocated[mutation["family_local_key"]]
        result = Binding(local_key=key, object_type=kind, object_id=allocated[key],
                         objective_id=owner, family_id=family_id)
        bindings[key] = result
        visiting.remove(key)
        return result

    def event(identifier: str) -> None:
        record = events.get(identifier)
        if record is None or record.run_id != context.run_id or not record.chamber_visible:
            raise ValueError("unknown, foreign or invisible evidence")

    def walk(value: object) -> object:
        if isinstance(value, list):
            return [walk(item) for item in value]
        if not isinstance(value, dict):
            return value
        if value.get("kind") in ("LOCAL", "EXISTING"):
            obj = lookup(value)
            return {"kind": "EXISTING", "object_type": obj.object_type, "object_id": obj.object_id}
        result = {}
        for key, item in value.items():
            if key.endswith("event_ids"):
                for identifier in item:
                    event(identifier)
            elif key == "authority_event_id":
                event(item)
            result[key] = walk(item)
        return result

    resolved = walk(document)
    for key in declarations:
        binding(key)
    # Duplicate selection can arise only after LOCAL and EXISTING names resolve.
    resolved_proposal = parse(StateProposal, canonical_bytes(resolved))

    revisions = {key: obj.revision for key, obj in objects.items()}
    retired: set[str] = set()
    for mutation in resolved["mutations"]:
        kind = mutation["kind"]
        if kind in ("ITCH_CREATE", "COMMITMENT_CREATE"):
            revisions[allocated[mutation["local_key"]]] = 1
        elif kind == "INVARIANT_CREATE":
            revisions[allocated[mutation["family_local_key"]]] = 1
            revisions[allocated[mutation["version_local_key"]]] = 1
        else:
            target = mutation["target"]["object_id"]
            if target not in revisions or mutation["expected_revision"] != revisions[target]:
                raise ValueError("stale or not-yet-created mutation target")
            if target in retired:
                raise ValueError("retired predecessor cannot be mutated again")
            revisions[target] += 1
            if kind == "INVARIANT_REVISE":
                retired.add(target)
                revisions[allocated[mutation["successor_local_key"]]] = 1
    if any(ref["object_id"] in retired for ref in resolved["continuity"]["selected_objects"]):
        raise ValueError("handoff selects a retired predecessor")

    graph = {obj.object_id: set(obj.commitment_links) for obj in context.objects
             if obj.object_type == "COMMITMENT" and obj.run_id == context.run_id
             and obj.objective_id == context.objective_id}
    for mutation in resolved["mutations"]:
        if mutation["kind"] == "COMMITMENT_CREATE":
            identifier = allocated[mutation["local_key"]]
            trigger = mutation["trigger"]
            graph[identifier] = ({trigger["predecessor"]["object_id"]}
                                 if trigger["kind"] == "PREDECESSOR_FULFILLED" else set())
        elif mutation["kind"] == "COMMITMENT_TRANSITION" and mutation["superseded_by"] is not None:
            graph.setdefault(mutation["target"]["object_id"], set()).add(mutation["superseded_by"]["object_id"])
    completed: set[str] = set()
    for root in graph:
        path: set[str] = set()
        stack = [(root, False)]
        while stack:
            identifier, leaving = stack.pop()
            if leaving:
                path.remove(identifier)
                completed.add(identifier)
                continue
            if identifier in path:
                raise ValueError("cyclic Commitment references")
            if identifier in completed:
                continue
            if identifier not in graph:
                raise ValueError("Commitment graph contains a missing or foreign reference")
            path.add(identifier)
            stack.append((identifier, True))
            stack.extend((child, False) for child in graph[identifier])
    return Resolution(resolved_proposal, tuple(bindings[key] for key in declarations))
