"""Stage documented semantic lifecycle edges without interpreting evidence."""
from ..contracts.base import canonical_bytes, parse
from .contracts import StoredObject

EDGES = {
    "ITCH": {"OPEN": {"INVESTIGATING", "RESOLVED", "DISMISSED", "ARCHIVED"},
             "INVESTIGATING": {"OPEN", "RESOLVED", "DISMISSED", "ARCHIVED"},
             "RESOLVED": {"OPEN", "INVESTIGATING"}, "ARCHIVED": {"OPEN", "INVESTIGATING"},
             "DISMISSED": set()},
    "INVARIANT_VERSION": {"TENTATIVE": {"ACTIVE", "CHALLENGED", "RETIRED"},
                          "ACTIVE": {"CHALLENGED", "RETIRED"},
                          "CHALLENGED": {"ACTIVE", "RETIRED"}, "RETIRED": set()},
    "COMMITMENT": {"PENDING": {"TRIGGERED", "CANCELLED", "SUPERSEDED", "EXPIRED"},
                   "TRIGGERED": {"IN_PROGRESS", "BLOCKED", "CANCELLED"},
                   "IN_PROGRESS": {"FULFILLED", "BLOCKED", "CANCELLED"},
                   "BLOCKED": {"PENDING", "IN_PROGRESS", "CANCELLED", "SUPERSEDED"},
                   "FULFILLED": set(), "CANCELLED": set(), "SUPERSEDED": set(), "EXPIRED": set()},
}
SELECTABLE = {"ITCH": {"OPEN", "INVESTIGATING"}, "INVARIANT_VERSION": {"TENTATIVE", "ACTIVE", "CHALLENGED"},
              "COMMITMENT": {"PENDING", "TRIGGERED", "IN_PROGRESS", "BLOCKED"}}

def stage(resolution, existing, *, run_id, task_tick, event_sources, prior_evidence, validate_selection=True):
    """Return complete projection and ordered before/after changes for each mutation."""
    objects = dict(existing)
    bindings = {item.local_key: item for item in resolution.bindings}
    all_changes = []
    used_evidence = {key: set(value) for key, value in prior_evidence.items()}

    def new(key, status, content, predecessor=None):
        binding = bindings[key]
        return parse(StoredObject, canonical_bytes({
            "object_id": binding.object_id, "run_id": run_id, "object_type": binding.object_type,
            "objective_id": binding.objective_id, "revision": 1, "family_id": binding.family_id,
            "predecessor_id": predecessor, "status": status, "content": content,
            "commitment_links": ([content["trigger"]["predecessor"]["object_id"]]
                if content["kind"] == "COMMITMENT_CREATE" and content["trigger"]["kind"] == "PREDECESSOR_FULFILLED" else []),
        }))

    for item in resolution.proposal.mutations:
        mutation = item.model_dump(mode="json")
        kind = mutation["kind"]
        changes = []

        def put(after):
            before = objects.get(after.object_id)
            objects[after.object_id] = after
            changes.append((before, after))

        if kind == "ITCH_CREATE":
            put(new(mutation["local_key"], "OPEN", mutation))
        elif kind == "COMMITMENT_CREATE":
            if event_sources[mutation["authority_event_id"]] not in {"OBJ", "O-D", "A"}:
                raise ValueError("external-only content cannot originate a Commitment")
            put(new(mutation["local_key"], "PENDING", mutation))
        elif kind == "INVARIANT_CREATE":
            put(new(mutation["family_local_key"], "FAMILY", mutation))
            put(new(mutation["version_local_key"], "TENTATIVE", mutation))
        else:
            target = objects[mutation["target"]["object_id"]]
            if target.revision != mutation["expected_revision"]:
                raise ValueError("stale staged revision")
            status = "RETIRED" if kind == "INVARIANT_REVISE" else mutation["status"]
            if status not in EDGES[target.object_type][target.status]:
                raise ValueError("illegal lifecycle edge")
            evidence = set(mutation.get("evidence_event_ids", ()))
            if target.object_type == "ITCH" and target.status in {"RESOLVED", "ARCHIVED"}:
                if not evidence - used_evidence.get(target.object_id, set()):
                    raise ValueError("reopening needs new contradiction evidence")
            if target.object_type == "COMMITMENT":
                if status == "FULFILLED" and not evidence:
                    raise ValueError("fulfilment needs outcome evidence")
                if status in {"TRIGGERED", "EXPIRED"}:
                    if not any(event_sources[e] == "K" for e in evidence):
                        raise ValueError("trigger/expiry needs Kernel observation evidence")
                    content = target.content
                    expired = content.expiry_tick is not None and task_tick >= content.expiry_tick
                    if status == "EXPIRED" and not expired:
                        raise ValueError("expiry condition is not satisfied")
                    if status == "TRIGGERED":
                        trigger = content.trigger
                        due = (task_tick >= trigger.tick if trigger.kind == "TASK_CLOCK" else
                               objects[trigger.predecessor.object_id].status == "FULFILLED")
                        if expired or not due:
                            raise ValueError("trigger is not due or expiry takes precedence")
            changed = target.model_dump(mode="json")
            changed.update(status=status, revision=target.revision + 1)
            if kind == "COMMITMENT_TRANSITION" and mutation["superseded_by"]:
                changed["commitment_links"] = list(dict.fromkeys(
                    changed["commitment_links"] + [mutation["superseded_by"]["object_id"]]))
            put(parse(StoredObject, canonical_bytes(changed)))
            if kind == "INVARIANT_REVISE":
                put(new(mutation["successor_local_key"], "TENTATIVE", mutation, target.object_id))
        for _, after in changes:
            used_evidence.setdefault(after.object_id, set()).update(
                e for key, ids in mutation.items() if key.endswith("event_ids") for e in ids)
        all_changes.append(changes)
    for selected in resolution.proposal.continuity.selected_objects if validate_selection else ():
        obj = objects[selected.object_id]
        if obj.status not in SELECTABLE[obj.object_type]:
            raise ValueError("selection includes an inactive lifecycle")
    return objects, all_changes
