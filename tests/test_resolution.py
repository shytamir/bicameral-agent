import copy
import unittest

from bicameral_agent.contracts.base import canonical_bytes, parse
from bicameral_agent.contracts.resolution import ResolutionContext, resolve_proposal
from bicameral_agent.contracts.semantics import StateProposal
from tests.fixtures import (
    COMMITMENT, EVENT, FAMILY, ITCH, OBJECTIVE, OTHER_RUN, VERSION,
    catalogue_object, context, existing, local, proposal, revision_proposal, uid,
)


def resolve(value, catalogue=None, allocator=None):
    ids = iter(uid(n) for n in range(100, 200))
    return resolve_proposal(parse(StateProposal, canonical_bytes(value)),
                            parse(ResolutionContext, canonical_bytes(context() if catalogue is None else catalogue)),
                            allocator or (lambda: next(ids)))


def commitment(key, predecessor=None):
    return {"kind": "COMMITMENT_CREATE", "local_key": key, "objective_id": OBJECTIVE,
            "action": "Inspect synthetic service", "trigger":
            {"kind": "TASK_CLOCK", "tick": 3} if predecessor is None else
            {"kind": "PREDECESSOR_FULFILLED", "predecessor": predecessor},
            "expiry_tick": None, "authority_event_id": EVENT, "evidence_event_ids": [EVENT]}


class ResolutionTests(unittest.TestCase):
    def test_create_and_select_same_proposal(self):
        value = proposal()
        before = copy.deepcopy(value)
        result = resolve(value)
        self.assertEqual(value, before)
        self.assertEqual(result.bindings[0].object_id, uid(100))
        self.assertEqual(result.proposal.continuity.selected_objects[0].object_id, uid(100))
        self.assertNotIn(b'"kind":"LOCAL"', canonical_bytes(result.proposal))

    def test_revise_and_select_preserves_family(self):
        result = resolve(revision_proposal())
        self.assertEqual(result.bindings[0].family_id, FAMILY)
        self.assertEqual(result.bindings[0].objective_id, OBJECTIVE)
        self.assertEqual(result.proposal.continuity.selected_objects[0].object_id, uid(100))

    def test_create_invariant_family_and_version(self):
        value = proposal()
        value["mutations"] = [{"kind": "INVARIANT_CREATE", "family_local_key": "family",
                               "version_local_key": "first", "objective_id": OBJECTIVE,
                               "proposition": "Synthetic lesson", "scope": "Synthetic fixture",
                               "supporting_event_ids": [EVENT], "contradictory_event_ids": []}]
        value["continuity"]["selected_objects"] = [local("INVARIANT_VERSION", "first")]
        result = resolve(value)
        self.assertEqual(result.bindings[1].family_id, result.bindings[0].object_id)
        self.assertNotEqual(result.bindings[1].object_id, result.bindings[0].object_id)

    def test_forward_predecessor_reference_resolves(self):
        value = proposal()
        value["mutations"] = [commitment("later", local("COMMITMENT", "first")), commitment("first")]
        value["continuity"]["selected_objects"] = [local("COMMITMENT", "later")]
        result = resolve(value)
        self.assertEqual(result.proposal.mutations[0].trigger.predecessor.object_id, uid(101))

    def test_ordered_revision_checks_include_prior_staged_change(self):
        value = proposal()
        value["mutations"] = [
            {"kind": "COMMITMENT_TRANSITION", "target": existing("COMMITMENT", COMMITMENT),
             "expected_revision": 1, "status": "IN_PROGRESS", "reason": "Synthetic start",
             "evidence_event_ids": [EVENT], "superseded_by": None},
            {"kind": "COMMITMENT_TRANSITION", "target": existing("COMMITMENT", COMMITMENT),
             "expected_revision": 2, "status": "FULFILLED", "reason": "Synthetic observation",
             "evidence_event_ids": [EVENT], "superseded_by": None}]
        value["continuity"]["selected_objects"] = []
        self.assertEqual(len(resolve(value).proposal.mutations), 2)
        value["mutations"][1]["expected_revision"] = 1
        with self.assertRaisesRegex(ValueError, "stale"):
            resolve(value)

    def test_retired_predecessor_cannot_remain_selected(self):
        value = revision_proposal()
        value["continuity"]["selected_objects"] = [existing("INVARIANT_VERSION", VERSION)]
        with self.assertRaisesRegex(ValueError, "retired predecessor"):
            resolve(value)

    def test_unknown_duplicate_and_wrong_type_local_bindings_reject(self):
        for ref in (local("ITCH", "missing"), local("COMMITMENT", "new-itch")):
            value = proposal()
            value["continuity"]["selected_objects"] = [ref]
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                resolve(value)
        value = proposal()
        value["mutations"] *= 2
        with self.assertRaisesRegex(ValueError, "duplicate local binding"):
            resolve(value)

    def test_existing_target_run_type_and_scope_are_checked(self):
        for change in ({"run_id": OTHER_RUN}, {"object_type": "COMMITMENT"},
                       {"objective_id": uid(99)}, {"objective_id": None}):
            catalogue = context()
            catalogue["objects"][2].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                resolve(revision_proposal(), catalogue)

    def test_unknown_existing_and_evidence_references_reject(self):
        value = proposal()
        value["continuity"]["selected_objects"] = [existing("ITCH", uid(99))]
        with self.assertRaises(ValueError):
            resolve(value)
        for change in ({"run_id": OTHER_RUN}, {"chamber_visible": False}, {"event_id": uid(99)}):
            catalogue = context()
            catalogue["events"][0].update(change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "evidence"):
                resolve(proposal(), catalogue)

    def test_global_invariant_requires_matching_global_family(self):
        catalogue = context()
        catalogue["objects"][1]["objective_id"] = None
        catalogue["objects"][2]["objective_id"] = None
        result = resolve(revision_proposal(), catalogue)
        self.assertIsNone(result.bindings[0].objective_id)
        for change in ({"run_id": OTHER_RUN}, {"object_type": "ITCH"}, {"object_id": uid(99)}):
            invalid = copy.deepcopy(catalogue)
            invalid["objects"][1].update(change)
            with self.subTest(change=change), self.assertRaisesRegex(ValueError, "family"):
                resolve(revision_proposal(), invalid)

    def test_stale_parent_and_focus_reject(self):
        for field in ("parent_state_id", "objective_id"):
            catalogue = context()
            catalogue[field] = uid(99)
            with self.subTest(field=field), self.assertRaises(ValueError):
                resolve(proposal(), catalogue)

    def test_allocator_cannot_supply_foreign_shapes_or_reuse_identities(self):
        for identifier in (ITCH, EVENT, "not-a-uuid", "A" * 36, True):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                resolve(proposal(), allocator=lambda: identifier)
        value = proposal()
        value["mutations"] = [commitment("first"), commitment("second")]
        value["continuity"]["selected_objects"] = []
        with self.assertRaisesRegex(ValueError, "colliding"):
            resolve(value, allocator=lambda: uid(100))

    def test_invalid_late_reference_does_not_modify_inputs(self):
        value = proposal()
        value["continuity"]["event_ids"].append(uid(999))
        catalogue = context()
        before = canonical_bytes([value, catalogue])
        with self.assertRaises(ValueError):
            resolve(value, catalogue)
        self.assertEqual(before, canonical_bytes([value, catalogue]))

    def test_local_cannot_name_control_or_evidence_identifiers(self):
        value = proposal()
        for kind in ("OBJECTIVE", "GRANT", "RUN", "CONSTITUTION", "EVENT", "INVARIANT_FAMILY"):
            value["continuity"]["selected_objects"] = [local(kind, "new-itch")]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                resolve(value)

    def test_wrong_mutation_target_type_rejects_before_resolution(self):
        value = revision_proposal()
        value["mutations"][0]["target"] = existing("ITCH", ITCH)
        with self.assertRaisesRegex(ValueError, "object_type"):
            resolve(value)

    def test_arm_exclusions(self):
        for arm in ("B", "C"):
            catalogue = context()
            catalogue["arm"] = arm
            with self.subTest(arm=arm), self.assertRaises(ValueError):
                resolve(proposal(), catalogue)
        catalogue["arm"] = "C"
        value = proposal()
        value["mutations"] = [commitment("future")]
        value["continuity"]["selected_objects"] = [local("COMMITMENT", "future")]
        self.assertEqual(resolve(value, catalogue).bindings[0].object_type, "COMMITMENT")

    def test_cycles_include_predecessors_and_existing_supersession_links(self):
        value = proposal()
        value["mutations"] = [commitment("a", local("COMMITMENT", "b")), commitment("b", local("COMMITMENT", "a"))]
        value["continuity"]["selected_objects"] = []
        with self.assertRaisesRegex(ValueError, "cyclic Commitment"):
            resolve(value)
        catalogue = context()
        catalogue["objects"][-1]["commitment_links"] = [uid(90)]
        catalogue["objects"].append(catalogue_object("COMMITMENT", uid(90)))
        value["mutations"] = [{"kind": "COMMITMENT_TRANSITION", "target": existing("COMMITMENT", uid(90)),
                               "expected_revision": 1, "status": "SUPERSEDED", "reason": "Synthetic",
                               "evidence_event_ids": [EVENT], "superseded_by": existing("COMMITMENT", COMMITMENT)}]
        with self.assertRaisesRegex(ValueError, "cyclic Commitment"):
            resolve(value, catalogue)

    def test_creates_cannot_supply_durable_id_or_starting_status(self):
        for change in ({"object_id": uid(100)}, {"status": "RESOLVED"}, {"revision": 2}):
            value = proposal()
            value["mutations"][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                resolve(value)

    def test_long_existing_commitment_history_does_not_use_python_call_depth(self):
        catalogue = context()
        catalogue["objects"].extend(catalogue_object("COMMITMENT", uid(n), links=(uid(n + 1),))
                                    for n in range(1000, 2500))
        catalogue["objects"].append(catalogue_object("COMMITMENT", uid(2500)))
        self.assertEqual(resolve(proposal(), catalogue).bindings[0].object_id, uid(100))


if __name__ == "__main__":
    unittest.main()
