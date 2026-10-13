"""Database lifecycle, abrupt-process failure, concurrency, and removal acceptance."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing, contextmanager
from hashlib import sha256
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
import unittest

from bicameral_agent.contracts.base import canonical_bytes, parse
from bicameral_agent.contracts.governance import RetentionRecord
from bicameral_agent.storage import Store, StorageError, EvidenceUnavailable
from bicameral_agent.storage.contracts import RunState, ObjectiveState, EpisodeState, Receipt, ChamberKey
from bicameral_agent.storage.store import identifier
from tests import test_storage as fixtures
from tests.fixtures import uid, local, existing, withdrawal

@contextmanager
def fresh_case(arm="A"):
    case = fixtures.StorageCase()
    case.arm = arm
    case.setUp()
    try:
        yield case
    finally:
        case.doCleanups()

class StorageInvariantTests(fixtures.StorageCase):
    def test_all_semantic_lifecycle_pairs_on_real_database(self):
        paths = {
            "ITCH": {"OPEN": (), "INVESTIGATING": ("INVESTIGATING",), "RESOLVED": ("RESOLVED",),
                     "ARCHIVED": ("ARCHIVED",), "DISMISSED": ("DISMISSED",)},
            "INVARIANT_VERSION": {"TENTATIVE": (), "ACTIVE": ("ACTIVE",), "CHALLENGED": ("CHALLENGED",), "RETIRED": ("RETIRED",)},
            "COMMITMENT": {"PENDING": (), "TRIGGERED": ("TRIGGERED",), "IN_PROGRESS": ("TRIGGERED", "IN_PROGRESS"),
                           "BLOCKED": ("TRIGGERED", "BLOCKED"), "FULFILLED": ("TRIGGERED", "IN_PROGRESS", "FULFILLED"),
                           "CANCELLED": ("CANCELLED",), "SUPERSEDED": ("SUPERSEDED",), "EXPIRED": ("EXPIRED",)},
        }
        # Independent acceptance oracle transcribed from Protocol section 6.
        allowed = {
            "ITCH": {"OPEN": ("INVESTIGATING", "RESOLVED", "DISMISSED", "ARCHIVED"),
                     "INVESTIGATING": ("OPEN", "RESOLVED", "DISMISSED", "ARCHIVED"),
                     "RESOLVED": ("OPEN", "INVESTIGATING"), "ARCHIVED": ("OPEN", "INVESTIGATING"), "DISMISSED": ()},
            "INVARIANT_VERSION": {"TENTATIVE": ("ACTIVE", "CHALLENGED", "RETIRED"),
                "ACTIVE": ("CHALLENGED", "RETIRED"), "CHALLENGED": ("ACTIVE", "RETIRED"), "RETIRED": ()},
            "COMMITMENT": {"PENDING": ("TRIGGERED", "CANCELLED", "SUPERSEDED", "EXPIRED"),
                "TRIGGERED": ("IN_PROGRESS", "BLOCKED", "CANCELLED"),
                "IN_PROGRESS": ("FULFILLED", "BLOCKED", "CANCELLED"),
                "BLOCKED": ("PENDING", "IN_PROGRESS", "CANCELLED", "SUPERSEDED"),
                "FULFILLED": (), "CANCELLED": (), "SUPERSEDED": (), "EXPIRED": ()}}
        for kind, states in paths.items():
            for source, path in states.items():
                for destination in states:
                    with self.subTest(kind=kind, source=source, destination=destination), fresh_case() as case:
                        sibling = None
                        if kind == "ITCH":
                            create = case.value()["mutations"][0]
                        elif kind == "INVARIANT_VERSION":
                            create = {"kind": "INVARIANT_CREATE", "family_local_key": "family", "version_local_key": "first",
                                "objective_id": case.objective, "proposition": "Synthetic", "scope": "Fixture",
                                "supporting_event_ids": [case.event], "contradictory_event_ids": []}
                        else:
                            first = case.accept(case.value([case.create_commitment()], []))
                            sibling = first.bindings[0].object_id
                            create = case.create_commitment()
                            if source == "EXPIRED" or (source == "PENDING" and destination == "EXPIRED"):
                                create["expiry_tick"] = 1
                        receipt = case.accept(case.value([create], []))
                        case.assertEqual(receipt.status, "ACCEPTED")
                        obj_id = receipt.bindings[-1].object_id
                        transition_kind = "INVARIANT" if kind == "INVARIANT_VERSION" else kind
                        for next_status in (*path, destination):
                            obj = case.store._objects(case.run)[obj_id]
                            # New evidence for reopening is a structural requirement; meaning stays cognitive.
                            event = case.store.record_evidence(case.run, b"new synthetic observation",
                                role="KERNEL", source="K", visibility="CHAMBER")
                            mutation = case.transition(transition_kind, obj, next_status, [event])
                            if next_status == "SUPERSEDED":
                                mutation["superseded_by"] = existing("COMMITMENT", sibling)
                            expected = next_status in allowed[kind][obj.status]
                            result = case.accept(case.value([mutation], []))
                            case.assertEqual(result.status, "ACCEPTED" if expected else "REJECTED")
                        case.assertEqual(case.store.verify(), ())

    def test_guard_matrix_rejects_absent_terminal_and_wrong_scope(self):
        for status in ("CREATED", "PAUSED", "COMPLETED", "TERMINATED"):
            revision, state = self.store.control(self.run, self.run)
            with self.store._transaction("test-state-arrangement"):
                self.store._control(self.run, self.run, RunState(kind="RUN", status=status,
                    objective_id=self.objective, task_tick=10), expected_revision=revision)
            self.assertEqual(self.accept().status, "REJECTED")
        revision, _ = self.store.control(self.run, self.run)
        with self.store._transaction("test-state-arrangement"):
            self.store._control(self.run, self.run, RunState(kind="RUN", status="ACTIVE",
                objective_id=self.objective, task_tick=10), expected_revision=revision)
        for status in ("SATISFIED", "FAILED", "CANCELLED", "SUPERSEDED"):
            revision, state = self.store.control(self.run, self.objective)
            with self.store._transaction("test-state-arrangement"):
                self.store._control(self.run, self.objective, ObjectiveState(kind="OBJECTIVE",
                    status=status, statement="Synthetic", authority_event_id=self.event), expected_revision=revision)
            self.assertEqual(self.accept().status, "REJECTED")
        # Private fixtures deliberately arrange forbidden current states; no control API permits resurrection.
        self.assertEqual(self.counts()["states"], 0)
        with self.assertRaisesRegex(ValueError, "stale"):
            with self.store._transaction("test-stale"):
                self.store._control(self.run, self.run, RunState(kind="RUN", status="ACTIVE",
                    objective_id=None, task_tick=0), expected_revision=1)

    def test_arms_b_c_and_roles(self):
        for arm in ("B", "C"):
            config, artifacts = fixtures.prepared_configuration(arm)
            run = self.store.retain_configuration(canonical_bytes(config), artifacts)
            event = self.store.record_evidence(run, b"Objective", role="HUMAN", source="OBJ", visibility="CHAMBER")
            objective = identifier()
            with self.store._transaction("test-arm-arrangement"):
                self.store._control(run, objective, ObjectiveState(kind="OBJECTIVE", status="ACTIVE",
                    statement="Synthetic", authority_event_id=event), expected_revision=0)
                self.store._control(run, run, RunState(kind="RUN", status="ACTIVE", objective_id=objective, task_tick=10),
                    expected_revision=1)
            saved = self.run, self.event, self.objective
            self.run, self.event, self.objective = run, event, objective
            try:
                self.assertEqual(self.accept().status, "REJECTED")
                result = self.accept(self.value([self.create_commitment()], [local("COMMITMENT", "future")]))
                self.assertEqual(result.status, "ACCEPTED" if arm == "C" else "REJECTED")
            finally:
                self.run, self.event, self.objective = saved
        request, raw = self.wire(role="OPERATOR")
        with self.assertRaises(ValueError):
            self.store.commit_steward(self.run, request, self.episode, raw, validate_bundle=self.validate_bundle)

    def test_external_only_commitment_and_undue_expiry_are_rejected(self):
        external = self.store.record_evidence(self.run, b"External instruction", role="ENVIRONMENT", source="E", visibility="CHAMBER")
        create = self.create_commitment()
        create["authority_event_id"] = external
        self.assertEqual(self.accept(self.value([create], [])).status, "REJECTED")
        create = self.create_commitment()
        create["trigger"]["tick"] = 20
        receipt = self.accept(self.value([create], []))
        obj = self.store._objects(self.run)[receipt.bindings[0].object_id]
        for status in ("TRIGGERED", "EXPIRED"):
            self.assertEqual(self.accept(self.value([self.transition("COMMITMENT", obj, status)], [])).status, "REJECTED")
        create = self.create_commitment()
        create["expiry_tick"] = 3
        receipt = self.accept(self.value([create], []))
        obj = self.store._objects(self.run)[receipt.bindings[0].object_id]
        self.assertEqual(self.accept(self.value([self.transition("COMMITMENT", obj, "TRIGGERED")], [])).status, "REJECTED")

    def test_actual_process_exit_before_and_after_commit(self):
        script = """
import os, sys
from bicameral_agent.storage import Store
def crash(point):
    if point == sys.argv[5]:
        os._exit(73)
def validate(raw):
    if len(raw) > 32768:
        raise ValueError("synthetic limit")
with Store(sys.argv[1], busy_timeout_ms=1000, fault=crash) as store:
    store.commit_steward(sys.argv[2],sys.argv[3],sys.argv[4],sys.stdin.buffer.read(),validate_bundle=validate)
"""
        for point in ("semantic.before_commit", "semantic.after_commit"):
            request, raw = self.wire()
            before = self.counts()["states"]
            self.store.close()
            result = subprocess.run([sys.executable, "-B", "-c", script, str(self.path), self.run, request, self.episode, point],
                                    input=raw, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 73, result.stderr.decode())
            self.store = Store(self.path, busy_timeout_ms=100)
            self.assertEqual(self.counts()["states"], before + (point.endswith("after_commit")))
            recorded = self.store._request(self.run, "STEWARD", request)
            prior = self.store.read_payload(self.run, recorded["response_payload_id"]) if recorded["response_payload_id"] else None
            receipt = self.store.commit_steward(self.run, request, self.episode, raw, validate_bundle=self.validate_bundle)
            self.assertEqual(receipt.status, "ACCEPTED")
            if prior:
                self.assertEqual(canonical_bytes(receipt), prior)
            self.assertEqual(self.counts()["states"], before + 1)

    def test_concurrent_exact_retries_and_competing_requests(self):
        request, raw = self.wire()
        def run_pair(second_request, second_raw):
            barrier = threading.Barrier(2)
            def worker(request_id, body):
                with Store(self.path, busy_timeout_ms=5000) as store:
                    barrier.wait(timeout=10)
                    return store.commit_steward(self.run, request_id, self.episode, body, validate_bundle=self.validate_bundle)
            with ThreadPoolExecutor(max_workers=2) as pool:
                first = pool.submit(worker, request, raw)
                second = pool.submit(worker, second_request, second_raw)
                return first.result(), second.result()
        left, right = run_pair(request, raw)
        self.assertEqual(left.status, "ACCEPTED")
        self.assertEqual(canonical_bytes(left), canonical_bytes(right))
        self.assertEqual(self.counts()["states"], 1)
        request, raw = self.wire()
        changed = fixtures.parse_header(raw)
        changed["request_id"] = identifier()
        left, right = run_pair(changed["request_id"], canonical_bytes(changed))
        self.assertEqual({left.status, right.status}, {"ACCEPTED", "REJECTED"})
        self.assertEqual(self.counts()["states"], 2)
        self.assertEqual(self.store.verify(), ())

    def test_configuration_faults_at_every_write(self):
        config, artifacts = fixtures.prepared_configuration()
        points = []
        path = Path(self.temp.name) / "configuration-reference.db"
        with Store(path, busy_timeout_ms=100) as target:
            target._fault = points.append
            target.retain_configuration(canonical_bytes(config), artifacts)
        writes = [point for point in points if point.startswith("write:")]
        for index in range(len(writes)):
            with self.subTest(write=index), Store(Path(self.temp.name) / f"configuration-{index}.db", busy_timeout_ms=100) as target:
                count = [0]
                def fail(point):
                    if point.startswith("write:"):
                        count[0] += 1
                        if count[0] == index + 1:
                            raise fixtures.Crash()
                target._fault = fail
                with self.assertRaises(fixtures.Crash):
                    target.retain_configuration(canonical_bytes(config), artifacts)
                self.assertEqual(target._db.execute("SELECT COUNT(*) FROM runs").fetchone()[0], 0)
                self.assertEqual(target._db.execute("SELECT COUNT(*) FROM blobs").fetchone()[0], 0)
                self.assertEqual(target._db.execute("SELECT COUNT(*) FROM payloads").fetchone()[0], 0)

    def test_actual_schema_removal_of_source_and_derived_copies(self):
        marker = b"synthetic-p02-sensitive-content-unique"
        value = self.value()
        value["mutations"][0]["discrepancy"] = marker.decode()
        value["continuity"]["items"] = [{"kind": "OBSERVATION", "text": marker.decode(), "evidence_event_ids": [self.event]}]
        request, raw = self.wire(value)
        receipt = self.store.commit_steward(self.run, request, self.episode, raw, validate_bundle=self.validate_bundle)
        source = self.store._db.execute("SELECT id,digest,body FROM blobs").fetchall()
        sensitive = [row for row in source if marker in row["body"]]
        self.assertGreaterEqual(len(sensitive), 4)  # original reply, object, handoff, mutation
        targets = [row[0] for row in self.store._db.execute(
            "SELECT id FROM payloads WHERE blob_id IN (" + ",".join("?" for _ in sensitive) + ")",
            [row["id"] for row in sensitive])]
        disposition_id, intervention_id = identifier(), identifier()
        disposition = RetentionRecord(
            disposition_id=disposition_id, intervention_id=intervention_id, decision_maker_id=uid(40),
            purpose="Synthetic reviewed storage-removal proof",
            targets=tuple({"record_type": "PAYLOAD", "record_id": key, "expected_revision": 1} for key in targets),
            copies=({"copy_id": uid(901), "location_class": "PAYLOAD", "disposition": "REMOVED", "reason": "Synthetic governed-store bytes removed"},
                    {"copy_id": uid(902), "location_class": "WAL", "disposition": "PENDING", "reason": "Checkpoint and file verification pending"}),
            status="IN_PROGRESS", removal_event_id=None, continuity_and_replay_effects="Required evidence unavailable",
            remaining_state="Opaque metadata and a non-sensitive intervention record", unresolved_copy_ids=(uid(902),),
            continuation="STOPPED")
        # Deliberate storage-only proof. P03/P10 must supply actual review, access
        # blocking, progress/recovery, exports/backups and external-copy disposition.
        with self.store._transaction("test-approved-removal"):
            self.store._control(self.run, disposition_id, disposition, expected_revision=0)
            for row in sensitive:
                self.store._write("UPDATE payloads SET blob_id=NULL,disposition='REMOVED' WHERE blob_id=?", (row["id"],))
                self.store._write("DELETE FROM blobs WHERE id=?", (row["id"],))
        self.assertEqual(self.store._db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0], 0)
        self.store._db.execute("VACUUM")
        self.assertEqual(self.store._db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0], 0)
        for target in targets:
            with self.assertRaises(EvidenceUnavailable):
                self.store.read_payload(self.run, target)
        with self.assertRaises(EvidenceUnavailable):
            self.store.replay(self.run)
        self.reopen()
        self.assertTrue(self.store.problems[0].startswith("UNAVAILABLE:"))
        self.assertEqual(self.store._request(self.run, "STEWARD", request)["status"], receipt.status)
        self.assertNotIn(marker, canonical_bytes(self.store.control(self.run, disposition_id)[1]))
        # File checks establish this synthetic SQLite mechanism, not SSD/media or external erasure.
        for file in self.path.parent.glob("store.db*"):
            content = file.read_bytes()
            self.assertNotIn(marker, content)
            for row in sensitive:
                self.assertNotIn(row["digest"].encode(), content)

    def test_removed_supporting_event_blocks_new_commit(self):
        receipt = self.accept()
        payload = next(e["payload_id"] for e in self.store.events(self.run) if e["id"] == self.event)
        with self.store._transaction("test-removal"):
            self.store._write("UPDATE payloads SET disposition='REMOVED',blob_id=NULL WHERE id=?", (payload,))
        self.assertEqual(self.accept().status, "REJECTED")
        with self.assertRaises(EvidenceUnavailable):
            self.store.replay(self.run)

    def test_storage_contracts_strict_roundtrip_and_unknown_fields(self):
        key = {"run_id": self.run, "role": "STEWARD", "request_id": uid(400), "episode_id": None}
        model = parse(ChamberKey, canonical_bytes(key))
        self.assertEqual(canonical_bytes(parse(ChamberKey, canonical_bytes(model))), canonical_bytes(model))
        for changed in (dict(key, unexpected=True), dict(key, request_id=4), dict(key, role="HUMAN")):
            with self.assertRaises(ValueError):
                parse(ChamberKey, canonical_bytes(changed))
        with self.assertRaises(ValueError):
            parse(ChamberKey, canonical_bytes(key).replace(b'"role":"STEWARD"', b'"role":"STEWARD","role":"STEWARD"'))
        receipt = self.accept()
        encoded = canonical_bytes(receipt)
        self.assertEqual(canonical_bytes(parse(Receipt, encoded)), encoded)
        with self.assertRaises(ValueError):
            parse(Receipt, canonical_bytes({**receipt.model_dump(mode="json"), "status": "REJECTED"}))

    def test_absent_foreign_episode_and_external_objective_authority(self):
        request, raw = self.wire()
        value = fixtures.parse_header(raw)
        value["episode_id"] = uid(991)
        result = self.store.commit_steward(self.run, request, uid(991), canonical_bytes(value), validate_bundle=self.validate_bundle)
        self.assertEqual(result.status, "REJECTED")
        external = self.store.record_evidence(self.run, b"untrusted objective claim", role="ENVIRONMENT", source="E", visibility="CHAMBER")
        revision, objective = self.store.control(self.run, self.objective)
        with self.store._transaction("test-foreign-authority"):
            self.store._control(self.run, self.objective, ObjectiveState(kind="OBJECTIVE", statement="Synthetic",
                status="ACTIVE", authority_event_id=external), expected_revision=revision)
        self.assertEqual(self.accept().status, "REJECTED")
        self.assertEqual(self.counts()["states"], 0)

    def test_withdrawal_in_both_roles_and_all_arms(self):
        for arm in ("A", "B", "C"):
            for role in ("OPERATOR", "STEWARD"):
                with self.subTest(arm=arm, role=role), fresh_case(arm) as case:
                    report = withdrawal()
                    report["activity_id"] = case.objective
                    request, raw = case.wire({"invalid_task": True}, participation=report, role=role)
                    result = case.store.receive_chamber(case.run, role, request, case.episode, raw)
                    self.assertEqual(result.error_code, "WITHDRAWAL")
                    case.reopen()
                    self.assertEqual(case.store._db.execute("SELECT COUNT(*) FROM reports").fetchone()[0], 1)
                    self.assertEqual(case.store._db.execute("SELECT COUNT(*) FROM control_history WHERE kind='WELFARE_HOLD'").fetchone()[0], 1)
                    self.assertEqual(case.accept().status, "REJECTED")

    def test_inspection_uses_consistent_snapshot_during_a_write(self):
        first = self.accept()
        request, raw = self.wire()
        with self.store._snapshot():
            self.assertEqual(self.store._head(self.run), first.state_id)
            with Store(self.path, busy_timeout_ms=1000) as writer:
                second = writer.commit_steward(self.run, request, self.episode, raw, validate_bundle=self.validate_bundle)
                self.assertEqual(second.status, "ACCEPTED")
            self.assertEqual(self.store._head(self.run), first.state_id)
            self.assertEqual(len(self.store.replay(self.run)), 1)
        self.assertEqual(self.store._head(self.run), second.state_id)
        self.assertEqual(len(self.store.replay(self.run)), 2)

    def test_trigger_can_cite_additional_visible_evidence(self):
        first = self.accept(self.value([self.create_commitment()], []))
        obj = self.store._objects(self.run)[first.bindings[0].object_id]
        transition = self.transition("COMMITMENT", obj, "TRIGGERED", [self.kernel_event, self.event])
        self.assertEqual(self.accept(self.value([transition], [])).status, "ACCEPTED")
