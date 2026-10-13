"""P02 acceptance on real temporary SQLite files; all authority setup is synthetic."""
import copy
from hashlib import sha256
from pathlib import Path
import sqlite3
import tempfile
import unittest

from bicameral_agent.contracts.base import canonical_bytes, parse
from bicameral_agent.contracts.governance import WelfareHold
from bicameral_agent.storage import Store, StorageError, EvidenceUnavailable, RequestConflict
from bicameral_agent.storage.contracts import RunState, ObjectiveState, EpisodeState, StorageContracts
from bicameral_agent.storage.schema import schema_bytes
from tests.fixtures import configuration, proposal, message, withdrawal, local, existing, uid

def prepared_configuration(arm="A"):
    value = configuration()
    value["arm"] = arm
    value["budgets"]["proposal_bytes"] = 32768
    artifacts = {}
    for name, digest in value["artifacts"].items():
        if digest is not None:
            artifacts[name] = ("synthetic artifact: " + name).encode()
            value["artifacts"][name] = sha256(artifacts[name]).hexdigest()
    for name in ("scripted_messages", "scripted_outcomes", "test_tokenizer", "test_clock"):
        artifacts[name] = ("synthetic artifact: " + name).encode()
        value[name] = sha256(artifacts[name]).hexdigest()
    return value, artifacts

class Crash(BaseException):
    pass

class StorageCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "store.db"
        self.store = Store(self.path, busy_timeout_ms=100)
        self.addCleanup(lambda: self.store.close())
        config, artifacts = prepared_configuration(getattr(self, "arm", "A"))
        self.run = self.store.retain_configuration(canonical_bytes(config), artifacts)
        self.objective = uid(100)
        self.event = self.store.record_evidence(self.run, b"synthetic accepted Objective", role="HUMAN", source="OBJ", visibility="CHAMBER")
        self.kernel_event = self.store.record_evidence(self.run, b"synthetic task clock observation", role="KERNEL", source="K", visibility="CHAMBER")
        with self.store._transaction("test-fixture"):
            self.store._control(self.run, self.objective, ObjectiveState(kind="OBJECTIVE", statement="Synthetic task",
                status="ACTIVE", authority_event_id=self.event), expected_revision=0)
            self.store._control(self.run, self.run, RunState(kind="RUN", status="ACTIVE", objective_id=self.objective,
                task_tick=10), expected_revision=1)
        self.episode = None

    def reopen(self):
        self.store.close()
        self.store = Store(self.path, busy_timeout_ms=100)

    def new_episode(self):
        from bicameral_agent.storage.store import identifier
        self.episode = identifier()
        with self.store._transaction("test-fixture"):
            self.store._control(self.run, self.episode, EpisodeState(kind="EPISODE", objective_id=self.objective,
                phase="CONSOLIDATING", disposition=None), expected_revision=0)
        return self.episode

    def value(self, mutations=None, selected=None):
        value = proposal()
        value["expected_parent_state_id"] = self.store._head(self.run)
        value["mutations"][0]["objective_id"] = self.objective
        value["mutations"][0]["evidence_event_ids"] = [self.event]
        value["continuity"]["focus_objective_id"] = self.objective
        value["continuity"]["event_ids"] = [self.event]
        value["supporting_event_ids"] = [self.event]
        if mutations is not None:
            value["mutations"] = mutations
        if selected is not None:
            value["continuity"]["selected_objects"] = selected
        return value

    def wire(self, value=None, participation=None, role="STEWARD"):
        from bicameral_agent.storage.store import identifier
        self.new_episode()
        request = identifier()
        document = message(kind=role + "_REPLY", role=role, body={"participation": participation, "task": value or self.value()})
        document.update(run_id=self.run, request_id=request, episode_id=self.episode)
        return request, canonical_bytes(document)

    def accept(self, value=None, *, validator=None):
        request, raw = self.wire(value)
        return self.store.commit_steward(self.run, request, self.episode, raw,
            validate_bundle=validator or self.validate_bundle)

    @staticmethod
    def validate_bundle(raw):
        # Explicit test framing only, never a production tokenizer or default.
        if len(raw) > 32768:
            raise ValueError("synthetic bundle limit")
        return None

    def counts(self):
        return {table: self.store._db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
            for table in ("states", "mutations", "object_history", "object_heads", "evidence_links", "semantic_heads")}

    def create_commitment(self):
        return {"kind": "COMMITMENT_CREATE", "local_key": "future", "objective_id": self.objective,
                "action": "Inspect fixture", "trigger": {"kind": "TASK_CLOCK", "tick": 3}, "expiry_tick": None,
                "authority_event_id": self.event, "evidence_event_ids": [self.event]}

    def transition(self, kind, obj, status, evidence=None):
        value = {"kind": kind + "_TRANSITION", "target": existing("INVARIANT_VERSION" if kind == "INVARIANT" else kind, obj.object_id),
            "expected_revision": obj.revision, "status": status, "reason": "Synthetic evidence",
            "evidence_event_ids": [self.kernel_event] if evidence is None else evidence}
        if kind == "COMMITMENT":
            value["superseded_by"] = None
        return value

class StorageTests(StorageCase):
    def test_strict_database_identity_and_integer_constraints(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.store._db.execute("INSERT INTO blobs VALUES(NULL,?,?)", ("0" * 64, b"synthetic"))
        payload = self.store._db.execute("SELECT configuration_id FROM runs WHERE id=?", (self.run,)).fetchone()[0]
        for revision in (1.5, "not-an-integer", 0):
            with self.subTest(revision=revision), self.assertRaises(sqlite3.IntegrityError):
                self.store._db.execute("INSERT INTO control_history VALUES(?,?,?,?,?)",
                    (self.run, uid(999), revision, "RUN", payload))
        self.assertEqual(self.store.verify(), ())

    def test_file_configuration_foreign_keys_and_reopen(self):
        self.assertEqual(self.store._db.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(self.store._db.execute("PRAGMA synchronous").fetchone()[0], 2)
        self.assertEqual(self.store._db.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.assertEqual(self.store._db.execute("PRAGMA busy_timeout").fetchone()[0], 100)
        with self.assertRaises(sqlite3.IntegrityError):
            with self.store._transaction("negative"):
                self.store._write("INSERT INTO artifacts VALUES(?,?,?)", (self.run, "foreign", uid(999)))
        self.reopen()
        self.assertEqual(self.store.problems, [])
        self.assertEqual(self.store.configuration(self.run).mode, "SCRIPTED")

    def test_configuration_retains_verified_bytes_atomically(self):
        config, artifacts = prepared_configuration()
        before = self.store._db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        artifacts["fixture"] += b"changed"
        with self.assertRaisesRegex(ValueError, "hash"):
            self.store.retain_configuration(canonical_bytes(config), artifacts)
        self.assertEqual(self.store._db.execute("SELECT COUNT(*) FROM runs").fetchone()[0], before)
        config, artifacts = prepared_configuration()
        self.store._fault = lambda point: (_ for _ in ()).throw(Crash()) if point == "configuration.before_commit" else None
        with self.assertRaises(Crash):
            self.store.retain_configuration(canonical_bytes(config), artifacts)
        self.store._fault = lambda point: None
        self.assertEqual(self.store._db.execute("SELECT COUNT(*) FROM runs").fetchone()[0], before)
        self.assertEqual(self.store.verify(), ())

    def test_payloads_deduplicate_bytes_with_run_scoped_references(self):
        for _ in range(2):
            self.store.record_evidence(self.run, b"shared-source", role="ENVIRONMENT", source="E", visibility="CHAMBER")
        self.assertEqual(self.store._db.execute("SELECT COUNT(*) FROM blobs WHERE body=?", (b"shared-source",)).fetchone()[0], 1)
        payload = self.store.events(self.run)[-1]["payload_id"]
        with self.assertRaisesRegex(StorageError, "foreign"):
            self.store.read_payload(uid(999), payload)

    def test_source_role_cannot_be_promoted(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.record_evidence(self.run, b"pretend human", role="STEWARD", source="OBJ", visibility="CHAMBER")

    def test_create_select_replay_and_exact_retry_after_reopen(self):
        request, raw = self.wire()
        receipt = self.store.commit_steward(self.run, request, self.episode, raw, validate_bundle=self.validate_bundle)
        self.assertEqual(receipt.status, "ACCEPTED")
        self.assertEqual(self.store.control(self.run, self.episode)[1].phase, "CLOSED")
        objects = self.store.replay(self.run)
        self.assertEqual(list(objects), [receipt.bindings[0].object_id])
        counts = self.counts()
        self.reopen()
        repeated = self.store.commit_steward(self.run, request, self.episode, raw, validate_bundle=self.validate_bundle)
        self.assertEqual(canonical_bytes(receipt), canonical_bytes(repeated))
        self.assertEqual(self.counts(), counts)
        with self.assertRaises(RequestConflict):
            self.store.commit_steward(self.run, request, self.episode, raw + b" ", validate_bundle=self.validate_bundle)

    def test_invariant_successor_and_staged_ordered_edges(self):
        create = {"kind": "INVARIANT_CREATE", "family_local_key": "family", "version_local_key": "v1",
            "objective_id": self.objective, "proposition": "Synthetic lesson", "scope": "Synthetic service",
            "supporting_event_ids": [self.event], "contradictory_event_ids": []}
        first = self.accept(self.value([create], [local("INVARIANT_VERSION", "v1")]))
        self.assertEqual(first.status, "ACCEPTED")
        predecessor = self.store._objects(self.run)[first.bindings[1].object_id]
        revise = {"kind": "INVARIANT_REVISE", "target": existing("INVARIANT_VERSION", predecessor.object_id),
            "expected_revision": 1, "successor_local_key": "v2", "proposition": "Revised synthetic lesson", "scope": "Service",
            "supporting_event_ids": [self.event], "contradictory_event_ids": [self.kernel_event]}
        second = self.accept(self.value([revise], [local("INVARIANT_VERSION", "v2")]))
        self.assertEqual(second.status, "ACCEPTED")
        objects = self.store.replay(self.run)
        self.assertEqual(objects[predecessor.object_id].status, "RETIRED")
        successor = objects[second.bindings[0].object_id]
        self.assertEqual(successor.family_id, predecessor.family_id)
        self.assertEqual(successor.predecessor_id, predecessor.object_id)
        failed = self.accept(self.value([self.transition("INVARIANT", objects[predecessor.object_id], "ACTIVE")], []))
        self.assertEqual(failed.status, "REJECTED")

    def test_commitment_multiple_edges_commit_together_and_terminal_rejects(self):
        first = self.accept(self.value([self.create_commitment()], []))
        self.assertEqual(first.status, "ACCEPTED")
        obj = self.store._objects(self.run)[first.bindings[0].object_id]
        changes = []
        for index, status in enumerate(("TRIGGERED", "IN_PROGRESS", "FULFILLED")):
            change = self.transition("COMMITMENT", obj, status)
            change["expected_revision"] = index + 1
            changes.append(change)
        second = self.accept(self.value(changes, []))
        self.assertEqual(second.status, "ACCEPTED")
        obj = self.store.replay(self.run)[obj.object_id]
        self.assertEqual((obj.status, obj.revision), ("FULFILLED", 4))
        self.assertEqual(self.accept(self.value([self.transition("COMMITMENT", obj, "PENDING")], [])).status, "REJECTED")

    def test_forbidden_references_and_stale_state(self):
        for variant in ("foreign", "invisible", "stale", "late"):
            with self.subTest(variant=variant):
                value = self.value()
                if variant == "foreign":
                    value["supporting_event_ids"] = [uid(999)]
                elif variant == "invisible":
                    event = self.store.record_evidence(self.run, b"hidden scoring", role="KERNEL", source="K", visibility="EVALUATOR")
                    value["supporting_event_ids"] = [event]
                elif variant == "stale":
                    value["expected_parent_state_id"] = uid(999)
                elif variant == "late":
                    value["mutations"].append({"kind": "ITCH_TRANSITION", "target": local("ITCH", "new-itch"),
                        "expected_revision": 2, "status": "RESOLVED", "reason": "stale", "evidence_event_ids": [self.event]})
                before = self.counts()
                self.assertEqual(self.accept(value).status, "REJECTED")
                self.assertEqual(self.counts(), before)

    def test_bundle_validation_is_required_and_failure_is_atomic(self):
        def reject(bundle):
            self.assertIn(b"selected_objects", bundle)
            self.assertIn(b"Synthetic health", bundle)
            raise ValueError("synthetic full bundle exceeds limit")
        before = self.counts()
        self.assertEqual(self.accept(validator=reject).status, "REJECTED")
        self.assertEqual(self.counts(), before)

    def test_withdrawal_survives_invalid_task_and_blocks_later_proposal(self):
        value = self.value()
        value["unexpected"] = True
        report = withdrawal()
        report["activity_id"] = self.objective
        request, raw = self.wire(value, participation=report)
        receipt = self.store.commit_steward(self.run, request, self.episode, raw, validate_bundle=self.validate_bundle)
        self.assertEqual(receipt.error_code, "WITHDRAWAL")
        self.assertEqual(self.store._db.execute("SELECT COUNT(*) FROM reports").fetchone()[0], 1)
        self.assertEqual(self.counts()["states"], 0)
        self.reopen()
        self.assertEqual(self.accept().status, "REJECTED")
        duplicate = self.store.receive_chamber(self.run, "STEWARD", request, parse_header(raw)["episode_id"], raw)
        self.assertEqual(duplicate, receipt)
        self.assertEqual(self.store._db.execute("SELECT COUNT(*) FROM reports").fetchone()[0], 1)

    def test_duplicate_report_does_not_reassert_resolved_hold(self):
        report = withdrawal()
        report["activity_id"] = self.objective
        request, raw = self.wire(participation=report)
        self.store.receive_chamber(self.run, "STEWARD", request, self.episode, raw)
        row = self.store._db.execute("SELECT id FROM control_history WHERE kind='WELFARE_HOLD'").fetchone()
        revision, hold = self.store.control(self.run, row[0])
        # Test arrangement only. P03 must validate actual review and renewed participation.
        resolved = hold.model_dump(mode="json")
        resolved.update(revision=2, status="RESOLVED", resolution_review_id=uid(500))
        with self.store._transaction("test-reviewed-fixture"):
            self.store._control(self.run, row[0], parse(WelfareHold, canonical_bytes(resolved)), expected_revision=revision)
        self.reopen()
        self.store.receive_chamber(self.run, "STEWARD", request, self.episode, raw)
        self.assertEqual(self.store.control(self.run, row[0])[1].status, "RESOLVED")

    def test_malformed_participation_stops_for_inspection_after_restart(self):
        self.new_episode()
        self.store.receive_chamber(self.run, "OPERATOR", uid(300), self.episode, b"{not-json")
        self.reopen()
        self.assertEqual(self.store._db.execute("SELECT COUNT(*) FROM inspections").fetchone()[0], 1)
        self.assertEqual(self.accept().status, "REJECTED")

    def test_report_and_hold_are_atomic_at_each_write(self):
        from contextlib import closing
        points = []
        self.store._fault = points.append
        report = withdrawal()
        report["activity_id"] = self.objective
        request, raw = self.wire(participation=report)
        baseline = Path(self.temp.name) / 'report-baseline.db'
        with closing(sqlite3.connect(baseline)) as destination:
            self.store._db.backup(destination)
        points.clear()
        self.store.receive_chamber(self.run, "STEWARD", request, self.episode, raw)
        count = len([point for point in points if point.startswith("write:")])
        self.store._fault = lambda point: None
        for index in range(count):
            target_path = Path(self.temp.name) / f'report-{index}.db'
            with closing(sqlite3.connect(baseline)) as source, closing(sqlite3.connect(target_path)) as destination:
                source.backup(destination)
            with self.subTest(write=index), Store(target_path, busy_timeout_ms=100,
                                                 removal_journal=self.store.removals.path) as target:
                counter = [0]
                def crash(point):
                    if point.startswith("write:"):
                        counter[0] += 1
                        if counter[0] == index + 1:
                            raise Crash()
                target._fault = crash
                with self.assertRaises(Crash):
                    target.receive_chamber(self.run, "STEWARD", request, self.episode, raw)
                self.assertEqual(target._db.execute("SELECT COUNT(*) FROM reports").fetchone()[0], 0)
                self.assertEqual(target._db.execute("SELECT COUNT(*) FROM requests").fetchone()[0], 0)
                self.assertEqual(target._db.execute("SELECT COUNT(*) FROM control_history WHERE kind='WELFARE_HOLD'").fetchone()[0], 0)

    def test_semantic_failure_at_each_write_has_no_partial_effect(self):
        from contextlib import closing
        value = self.value()
        value["mutations"].extend([
            {"kind": "ITCH_TRANSITION", "target": local("ITCH", "new-itch"), "expected_revision": 1,
             "status": "INVESTIGATING", "reason": "Synthetic staged edge", "evidence_event_ids": [self.event]},
            self.create_commitment()])
        value["continuity"]["selected_objects"].append(local("COMMITMENT", "future"))
        request, raw = self.wire(value)
        self.store.receive_chamber(self.run, "STEWARD", request, self.episode, raw)
        baseline = Path(self.temp.name) / "fault-baseline.db"
        with closing(sqlite3.connect(baseline)) as destination:
            self.store._db.backup(destination)
        points = []
        self.store._fault = points.append
        self.store.commit_steward(self.run, request, self.episode, raw, validate_bundle=self.validate_bundle)
        writes = [p for p in points if p.startswith("write:")]
        self.store._fault = lambda point: None
        # Same synthetic identity restored for independent crash trials, never a populated-Run fork.
        for index in range(len(writes)):
            target_path = Path(self.temp.name) / f"semantic-fault-{index}.db"
            with closing(sqlite3.connect(baseline)) as source, closing(sqlite3.connect(target_path)) as destination:
                source.backup(destination)
            with self.subTest(write=index), Store(target_path, busy_timeout_ms=100,
                                                 removal_journal=self.store.removals.path) as target:
                before = {table: target._db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
                    for table in self.counts()}
                counter = [0]
                def fail(point):
                    if point.startswith("write:"):
                        counter[0] += 1
                        if counter[0] == index + 1:
                            raise sqlite3.OperationalError("synthetic injected write failure")
                target._fault = fail
                receipt = target.commit_steward(self.run, request, self.episode, raw, validate_bundle=self.validate_bundle)
                target._fault = lambda point: None
                self.assertEqual(receipt.status, "REJECTED")
                after = {table: target._db.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] for table in before}
                self.assertEqual(after, before)
                self.assertEqual(target.control(self.run, self.episode)[1].phase, "CONSOLIDATING")
                self.assertEqual(target.verify(), ())

    def test_crash_before_and_after_semantic_commit_preserves_identities(self):
        for point in ("semantic.before_commit", "semantic.after_commit"):
            request, raw = self.wire()
            before = self.counts()
            self.store._fault = lambda actual: (_ for _ in ()).throw(Crash()) if actual == point else None
            with self.assertRaises(Crash):
                self.store.commit_steward(self.run, request, self.episode, raw, validate_bundle=self.validate_bundle)
            self.reopen()
            if point.endswith("before_commit"):
                self.assertEqual(self.counts(), before)
            else:
                self.assertEqual(self.counts()["states"], before["states"] + 1)
            receipt = self.store.commit_steward(self.run, request, self.episode, raw, validate_bundle=self.validate_bundle)
            self.assertEqual(receipt.status, "ACCEPTED")
            self.assertEqual(self.counts()["states"], before["states"] + 1)

    def test_removed_payload_blocks_retry_and_replay_without_reconstructing(self):
        request, raw = self.wire()
        receipt = self.store.commit_steward(self.run, request, self.episode, raw, validate_bundle=self.validate_bundle)
        row = self.store._request(self.run, "STEWARD", request)
        # Simulate P10's explicit removal transaction; no production deletion endpoint is exposed by P02.
        with self.store._transaction("test-removal-fixture"):
            self.store._write("UPDATE payloads SET blob_id=NULL,disposition='REMOVED' WHERE id=?", (row["request_payload_id"],))
        with self.assertRaises(EvidenceUnavailable):
            self.store.commit_steward(self.run, request, self.episode, raw, validate_bundle=self.validate_bundle)
        self.reopen()
        self.assertTrue(self.store.problems[0].startswith("UNAVAILABLE:"))
        self.assertEqual(self.store._request(self.run, "STEWARD", request)["status"], receipt.status)
        with self.assertRaises(EvidenceUnavailable):
            self.store.replay(self.run)

    def test_corruption_blocks_writes_but_metadata_remains_inspectable(self):
        self.accept()
        self.store._db.execute("UPDATE blobs SET body=? WHERE id=(SELECT id FROM blobs LIMIT 1)", (b"damaged",))
        self.reopen()
        self.assertTrue(self.store.problems)
        self.assertTrue(self.store.events(self.run))
        with self.assertRaises(StorageError):
            self.store.record_evidence(self.run, b"not allowed", role="KERNEL", source="K", visibility="CHAMBER")

    def test_projection_drift_is_detected(self):
        self.accept()
        self.store._db.execute("DELETE FROM object_heads")
        self.reopen()
        self.assertIn("projection", self.store.problems[0])

    def test_append_only_metadata_constraint(self):
        with self.assertRaisesRegex(sqlite3.IntegrityError, "append-only"):
            self.store._db.execute("DELETE FROM events")

    def test_migration_failure_rolls_back_and_unknown_version_rejects(self):
        path = Path(self.temp.name) / "migration.db"
        count = [0]
        def fail(point):
            if point.startswith("write:"):
                count[0] += 1
                if count[0] == 6:
                    raise Crash()
        with self.assertRaises(Crash):
            Store(path, busy_timeout_ms=100, fault=fail)
        with Store(path, busy_timeout_ms=100) as migrated:
            self.assertEqual(migrated.problems, [])
            migrated._db.execute("UPDATE migrations SET digest='wrong'")
        with self.assertRaisesRegex(StorageError, "checksum"):
            Store(path, busy_timeout_ms=100)

        from bicameral_agent.storage.migrations import MIGRATIONS
        for version in (len(MIGRATIONS) + 1, 999):
            other_path = Path(self.temp.name) / f"version-{version}.db"
            with Store(other_path, busy_timeout_ms=100) as migrated:
                migrated._db.execute("UPDATE migrations SET version=? WHERE version=(SELECT MAX(version) FROM migrations)", (version,))
            with self.assertRaisesRegex(StorageError, "unknown or nonconsecutive"):
                Store(other_path, busy_timeout_ms=100)

    def test_storage_schema_is_closed_and_stable(self):
        path = Path(__file__).resolve().parents[1] / "schemas" / "p02.schema.json"
        self.assertEqual(path.read_bytes(), schema_bytes())
        schema = StorageContracts.model_json_schema()
        for item in schema["$defs"].values():
            if item.get("type") == "object":
                self.assertFalse(item["additionalProperties"])

def parse_header(raw):
    import json
    return json.loads(raw)
