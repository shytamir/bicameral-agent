"""Transactional P02 storage, callable only by a trusted in-process Kernel.

No transport authentication, human control adapter, scheduler, provider or fixture
execution lives here. P03 supplies authority decisions; P05 supplies the required
bundle validator; P06 supplies attempt accounting. All examples are scripted.
"""
from contextlib import contextmanager, nullcontext
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import sqlite3
from uuid import uuid4

from pydantic import TypeAdapter

from ..contracts.base import canonical_bytes, load_json, parse
from ..contracts.configuration import RunConfiguration
from ..contracts.governance import ParticipationRecord, WelfareHold
from ..contracts.messages import decode_chamber_reply
from ..contracts.resolution import ResolutionContext, resolve_proposal
from ..contracts.semantics import ContinuityState
from .contracts import CONTROL, RunState, ObjectiveState, EpisodeState, Receipt, StoredObject, ChamberKey, MutationEntry
from .migrations import MIGRATIONS, checksum
from .semantics import stage

class StorageError(RuntimeError):
    pass

class EvidenceUnavailable(StorageError):
    """Identity remains known; removed evidence cannot be reconstructed."""

class RequestConflict(StorageError):
    pass

def identifier():
    return str(uuid4())

def observed_at():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

class Store:
    def __init__(self, path, *, busy_timeout_ms, fault=None, removal_journal=None):
        if type(busy_timeout_ms) is not int or busy_timeout_ms <= 0:
            raise ValueError("busy timeout must be an explicit positive integer")
        if str(path) == ":memory:":
            raise ValueError("P02 requires a file-backed database")
        if sqlite3.sqlite_version_info < (3, 37, 0):
            raise StorageError("SQLite 3.37+ is required for STRICT storage tables")
        self.path = Path(path)
        self._fault = fault or (lambda point: None)
        self._poisoned = False
        self.problems = []
        self._read_dependencies = None
        from .retention import RemovalJournal
        self.removals = RemovalJournal(removal_journal or str(self.path) + '.removals.sqlite')
        self._db = sqlite3.connect(self.path, isolation_level=None, timeout=busy_timeout_ms / 1000)
        self._db.row_factory = sqlite3.Row
        try:
            self._db.execute("PRAGMA foreign_keys=ON")
            if self._db.execute("PRAGMA journal_mode=WAL").fetchone()[0] != "wal":
                raise StorageError("WAL unavailable")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute(f"PRAGMA busy_timeout={busy_timeout_ms}")
            self._db.execute("PRAGMA secure_delete=ON")
            self._migrate()
            binding = self._db.execute('SELECT journal_id FROM journal_binding').fetchone()
            if binding is None:
                self._db.execute('INSERT INTO journal_binding VALUES(1,?)', (self.removals.identity,))
            elif binding[0] != self.removals.identity:
                raise StorageError('current removal journal is missing or belongs to a different store; use governed recovery')
            from .retention import scrub_database
            scrub_database(self)
            self.verify()
        except BaseException:
            self._db.close()
            self.removals.close()
            raise

    def close(self):
        self._db.close()
        self.removals.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _write(self, sql, parameters=()):
        result = self._db.execute(sql, parameters)
        self._fault("write:" + sql.split()[0] + ":" + sql.split()[2])
        return result

    @contextmanager
    def _transaction(self, label):
        if self.problems or self._poisoned:
            raise StorageError("storage blocked; inspect diagnostics before recovery")
        self._db.execute("BEGIN IMMEDIATE")
        self._read_dependencies = {}
        try:
            yield
            self._fault(label + ".before_commit")
            self._db.commit()
        except BaseException:
            self._db.rollback()
            raise
        finally:
            self._read_dependencies = None
        self._fault(label + ".after_commit")

    @contextmanager
    def _snapshot(self):
        if self._db.in_transaction:
            yield
            return
        self._db.execute("BEGIN")
        try:
            yield
        finally:
            self._db.rollback()

    def _migrate(self):
        with self._transaction("migration"):
            self._write("CREATE TABLE IF NOT EXISTS migrations(version INTEGER PRIMARY KEY, digest TEXT NOT NULL) STRICT")
            rows = self._db.execute("SELECT version,digest FROM migrations ORDER BY version").fetchall()
            if [r["version"] for r in rows] != list(range(1, len(rows) + 1)) or len(rows) > len(MIGRATIONS):
                raise StorageError("unknown or nonconsecutive migration version")
            for row in rows:
                if row["digest"] != checksum(MIGRATIONS[row["version"] - 1]):
                    raise StorageError("migration checksum mismatch")
            for index in range(len(rows), len(MIGRATIONS)):
                for statement in MIGRATIONS[index]:
                    self._write(statement)
                self._write("INSERT INTO migrations VALUES(?,?)", (index + 1, checksum(MIGRATIONS[index])))
            if self._db.execute("PRAGMA foreign_key_check").fetchall():
                raise StorageError("migration foreign-key failure")

    def _payload(self, run_id, body, *, sources=()):
        self.retention_guard(run_id, execution=True)
        if type(body) is not bytes:
            raise TypeError("retained payload must be exact bytes")
        digest = sha256(body).hexdigest()
        row = self._db.execute("SELECT id,body FROM blobs WHERE digest=?", (digest,)).fetchone()
        if row is None:
            blob_id = identifier()
            self._write("INSERT INTO blobs VALUES(?,?,?)", (blob_id, digest, body))
        else:
            blob_id = row["id"]
            if row["body"] != body:
                raise StorageError("content hash collision or corruption")
        payload_id = identifier()
        self._write("INSERT INTO payloads VALUES(?,?,?,'RETAINED')", (payload_id, run_id, blob_id))
        for source in sorted(set(sources)):
            self.read_payload(run_id, source)
        dependencies = set(sources) | (self._read_dependencies or {}).get(run_id, set()) | self._referenced_payloads(run_id, body)
        dependencies.discard(payload_id)
        for source in sorted(dependencies):
            self._write('INSERT INTO derived_payloads VALUES(?,?,?)', (run_id, source, payload_id))
        self._write('INSERT INTO payload_lineage VALUES(?,?)', (run_id, payload_id))
        return payload_id

    def _referenced_payloads(self, run_id, body):
        try:
            value = load_json(body)
        except (ValueError, UnicodeError):
            return set()
        identities = set()
        def visit(item):
            if isinstance(item, dict):
                for key, child in item.items():
                    visit(child)
            elif isinstance(item, list):
                for child in item:
                    visit(child)
            elif isinstance(item, str) and len(item) == 36 and item != run_id:
                identities.add(item)
        visit(value)
        if not identities:
            return set()
        encoded = canonical_bytes(sorted(identities)).decode()
        result = {r[0] for r in self._db.execute('SELECT id FROM payloads WHERE run_id=? AND id IN (SELECT value FROM json_each(?))', (run_id, encoded))}
        for table in ('events', 'kernel_records', 'control_history', 'states', 'object_history'):
            result.update(r[0] for r in self._db.execute(f'SELECT payload_id FROM {table} WHERE run_id=? AND id IN (SELECT value FROM json_each(?))', (run_id, encoded)))
        return result

    def read_payload(self, run_id, payload_id):
        self.retention_guard(run_id, payload_id=payload_id)
        row = self._db.execute(
            "SELECT p.disposition,b.body,b.digest FROM payloads p LEFT JOIN blobs b ON b.id=p.blob_id WHERE p.run_id=? AND p.id=?",
            (run_id, payload_id)).fetchone()
        if row is None:
            raise StorageError("unknown or foreign payload")
        if row["disposition"] == "REMOVED":
            raise EvidenceUnavailable("REMOVED: payload bytes and digest are unavailable")
        if row["body"] is None or sha256(row["body"]).hexdigest() != row["digest"]:
            raise StorageError("payload integrity failure")
        if self._read_dependencies is not None:
            self._read_dependencies.setdefault(run_id, set()).add(payload_id)
        return row["body"]

    def retention_guard(self, run_id, *, payload_id=None, execution=False):
        decisions = self.removals.all(run_id)
        if decisions and (execution or payload_id is not None and any(payload_id in d['payload_ids'] for d in decisions)):
            raise EvidenceUnavailable('REMOVED_OR_REMOVAL_PENDING: current governed disposition blocks this operation')

    def retention_epoch(self, run_id):
        return tuple(d['id'] for d in self.removals.all(run_id))

    @staticmethod
    def _declared_artifacts(config):
        declared = {key: digest for key, digest in config.artifacts.model_dump().items() if digest is not None}
        if config.mode == "SCRIPTED":
            declared.update({key: getattr(config, key) for key in
                             ("scripted_messages", "scripted_outcomes", "test_tokenizer", "test_clock")})
        else:
            declared.update({key: getattr(config.model_identity, key) for key in
                             ("tokenizer_artifact", "framing_artifact", "runtime_artifact")})
        return declared

    def retain_configuration(self, raw, artifacts):
        """Atomic byte-retention step for later human sealing; creates CREATED only.

        Artifact keys are the declared field names, not machine paths. P03 must
        perform preflight and human sealing/activation; this method authorizes none.
        """
        config = TypeAdapter(RunConfiguration).validate_json(canonical_bytes(load_json(raw)), strict=True)
        declared = self._declared_artifacts(config)
        if set(artifacts) != set(declared):
            raise ValueError("artifact manifest differs from configuration")
        for name, digest in declared.items():
            if type(artifacts[name]) is not bytes or sha256(artifacts[name]).hexdigest() != digest:
                raise ValueError("artifact bytes do not match declared hash")
        run_id, configuration_id = identifier(), identifier()
        with (nullcontext() if self._db.in_transaction else self._transaction("configuration")):
            self._write("INSERT INTO runs VALUES(?,?,?)", (run_id, config.arm, configuration_id))
            stored = self._payload(run_id, canonical_bytes(config))
            # The temporary selector is never visible outside this deferred-FK transaction.
            self._write("UPDATE runs SET configuration_id=? WHERE id=?", (stored, run_id))
            for name, body in artifacts.items():
                payload_id = self._payload(run_id, body)
                self._write("INSERT INTO artifacts VALUES(?,?,?)", (run_id, name, payload_id))
            self._control(run_id, run_id, RunState(kind="RUN", status="CREATED", objective_id=None, task_tick=0), expected_revision=0)
        return run_id

    def configuration(self, run_id):
        row = self._db.execute("SELECT configuration_id FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise StorageError("unknown Run")
        return TypeAdapter(RunConfiguration).validate_json(self.read_payload(run_id, row[0]), strict=True)

    def _event(self, run_id, payload_id, *, role, source, visibility, episode_id=None):
        event_id = identifier()
        sequence = self._db.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE run_id=?", (run_id,)).fetchone()[0]
        self._write("INSERT INTO events VALUES(?,?,?,?,?,?,?,?)",
                    (event_id, run_id, sequence, role, source, visibility, observed_at(), payload_id))
        if episode_id is not None:
            self._write('INSERT INTO event_episodes VALUES(?,?,?)', (run_id, event_id, episode_id))
        return event_id

    def record_evidence(self, run_id, raw, *, role, source, visibility):
        """Trusted route metadata, never chamber-supplied source/visibility labels."""
        with self._transaction("evidence"):
            return self._event(run_id, self._payload(run_id, raw), role=role, source=source, visibility=visibility)

    def events(self, run_id):
        """Internal inspection metadata; P05/P08 will provide bounded authorized views."""
        return [dict(row) for row in self._db.execute("SELECT * FROM events WHERE run_id=? ORDER BY sequence", (run_id,))]

    def _control(self, run_id, record_id, record, *, expected_revision):
        """Private transactional writer for later guarded P03/P06 operations.

        This is deliberately not an exposed human-control/activation API.
        """
        if not self._db.in_transaction:
            raise StorageError("control history and projection require a transaction")
        record = CONTROL.validate_json(canonical_bytes(record), strict=True)
        mapping = {"WelfareHold": "WELFARE_HOLD", "WelfareReview": "WELFARE_REVIEW",
                   "InterventionRecord": "INTERVENTION", "BoundaryDiscussion": "BOUNDARY_DISCUSSION",
                   "RetentionRecord": "RETENTION"}
        kind = record.kind if isinstance(record, (RunState, ObjectiveState, EpisodeState)) else mapping[type(record).__name__]
        row = self._db.execute("SELECT revision FROM control_heads WHERE run_id=? AND id=?", (run_id, record_id)).fetchone()
        current = row[0] if row else 0
        if current != expected_revision:
            raise ValueError("stale control revision")
        if current:
            old = self._db.execute("SELECT kind FROM control_history WHERE run_id=? AND id=? AND revision=?",
                                   (run_id, record_id, current)).fetchone()[0]
            if old != kind:
                raise ValueError("control identity cannot change type")
        if isinstance(record, WelfareHold) and (record.run_id != run_id or record.hold_id != record_id or record.revision != current + 1):
            raise ValueError("hold identity or revision mismatch")
        payload_id = self._payload(run_id, canonical_bytes(record))
        self._write("INSERT INTO control_history VALUES(?,?,?,?,?)", (run_id, record_id, current + 1, kind, payload_id))
        self._write("INSERT INTO control_heads VALUES(?,?,?) ON CONFLICT(run_id,id) DO UPDATE SET revision=excluded.revision",
                    (run_id, record_id, current + 1))

    def _control_at(self, run_id, record_id, revision):
        row = self._db.execute("SELECT payload_id FROM control_history WHERE run_id=? AND id=? AND revision=?",
                               (run_id, record_id, revision)).fetchone()
        if row is None:
            raise StorageError("unknown control revision")
        return CONTROL.validate_json(self.read_payload(run_id, row[0]), strict=True)

    def control(self, run_id, record_id):
        row = self._db.execute(
            "SELECT h.revision,h.payload_id FROM control_history h JOIN control_heads p USING(run_id,id,revision) WHERE h.run_id=? AND h.id=?",
            (run_id, record_id)).fetchone()
        if row is None:
            raise StorageError("unknown or foreign control")
        return row["revision"], CONTROL.validate_json(self.read_payload(run_id, row["payload_id"]), strict=True)

    def _request(self, run_id, role, request_id):
        return self._db.execute("SELECT * FROM requests WHERE run_id=? AND role=? AND id=?", (run_id, role, request_id)).fetchone()

    def _retry(self, row, raw, episode_id):
        retained = self.read_payload(row["run_id"], row["request_payload_id"])
        if retained != raw or row["episode_id"] != episode_id:
            raise RequestConflict("same request key has different bytes or Episode")
        if row["response_payload_id"] is None:
            return None
        return parse(Receipt, self.read_payload(row["run_id"], row["response_payload_id"]))

    def _respond(self, run_id, role, receipt):
        payload_id = self._payload(run_id, canonical_bytes(receipt))
        self._write("UPDATE requests SET response_payload_id=?,status=? WHERE run_id=? AND role=? AND id=?",
                    (payload_id, receipt.status, run_id, role, receipt.request_id))
        return receipt

    def receive_chamber(self, run_id, role, request_id, episode_id, raw):
        """Retain exact authenticated input and report/hold before any task effect.

        Transport identity is provided by the trusted caller; no text authenticates.
        Malformed participation is durably flagged for inspection, never retried.
        """
        parse(ChamberKey, canonical_bytes({"run_id": run_id, "role": role, "request_id": request_id, "episode_id": episode_id}))
        decoded = decode_chamber_reply(raw, authenticated_role=role, run_id=run_id)
        if decoded.header is not None and (decoded.header.request_id != request_id or decoded.header.episode_id != episode_id):
            raise RequestConflict("envelope disagrees with trusted request identity")
        try:
            with self._transaction("report"):
                previous = self._request(run_id, role, request_id)
                if previous:
                    return self._retry(previous, raw, episode_id)
                payload_id = self._payload(run_id, raw)
                self._write("INSERT INTO requests VALUES(?,?,?,?,?,?,?)",
                            (run_id, role, request_id, episode_id, payload_id, None, "PENDING"))
                self._event(run_id, payload_id, role=role, source="A", visibility="CHAMBER")
                if decoded.participation is not None:
                    report_id = identifier()
                    report = ParticipationRecord(report_id=report_id, run_id=run_id, episode_id=episode_id,
                        source_role=role, original_message_id=request_id, original_payload={"payload_id": payload_id},
                        observed_at=observed_at(), kind=decoded.participation.kind)
                    record_payload = self._payload(run_id, canonical_bytes(report))
                    self._write("INSERT INTO reports VALUES(?,?,?,?,?)", (report_id, run_id, role, request_id, record_payload))
                    if decoded.stop_requested:
                        hold_id = identifier()
                        hold = WelfareHold(hold_id=hold_id, run_id=run_id, activity_id=decoded.participation.activity_id,
                            revision=1, report_ids=(report_id,), status="HELD",
                            communication=decoded.participation.communication, resolution_review_id=None)
                        self._control(run_id, hold_id, hold, expected_revision=0)
                if decoded.participation_uncertain:
                    self._write("INSERT INTO inspections VALUES(?,?,?)", (run_id, role, request_id))
                error_code = ("INSPECTION_REQUIRED" if decoded.participation_uncertain else
                              "WITHDRAWAL" if decoded.stop_requested else
                              "INVALID_TASK" if decoded.message is None else None)
                is_proposal = (role == "STEWARD" and decoded.message is not None and
                               decoded.message.message_type == "STEWARD_REPLY" and decoded.message.body.task is not None)
                if error_code or not is_proposal:
                    diagnostics = self._payload(run_id, (decoded.error or error_code).encode()) if decoded.error or error_code else None
                    return self._respond(run_id, role, Receipt(request_id=request_id,
                        status="REJECTED" if error_code else "RECORDED", state_id=None, bindings=(),
                        error_code=error_code, diagnostics={"payload_id": diagnostics} if diagnostics else None))
                return None
        except (RequestConflict, ValueError):
            raise
        except Exception:
            self._poisoned = True
            raise

    def _objects(self, run_id):
        return {row["id"]: parse(StoredObject, self.read_payload(run_id, row["payload_id"]))
                for row in self._db.execute(
                    "SELECT h.id,h.payload_id FROM object_history h JOIN object_heads p USING(run_id,id,revision) WHERE h.run_id=?",
                    (run_id,))}

    def _head(self, run_id):
        row = self._db.execute("SELECT state_id FROM semantic_heads WHERE run_id=?", (run_id,)).fetchone()
        return row[0] if row else None

    def _guard(self, run_id, episode_id):
        run_revision, run = self.control(run_id, run_id)
        episode_revision, episode = self.control(run_id, episode_id)
        if not isinstance(run, RunState) or run.status != "ACTIVE":
            raise ValueError("Run is not ACTIVE")
        if not isinstance(episode, EpisodeState) or episode.phase != "CONSOLIDATING":
            raise ValueError("Episode is not CONSOLIDATING")
        objective_revision, objective = self.control(run_id, episode.objective_id)
        if not isinstance(objective, ObjectiveState) or objective.status != "ACTIVE" or run.objective_id != episode.objective_id:
            raise ValueError("Objective is not current and ACTIVE")
        authority = self._db.execute("SELECT source,role,payload_id FROM events WHERE run_id=? AND id=?",
                                     (run_id, objective.authority_event_id)).fetchone()
        if authority is None or authority["role"] != "HUMAN" or authority["source"] not in {"OBJ", "O-D"}:
            raise ValueError("Objective lacks retained human authority provenance")
        self.read_payload(run_id, authority["payload_id"])
        if self._db.execute("SELECT 1 FROM inspections WHERE run_id=?", (run_id,)).fetchone():
            raise ValueError("participation inspection is unresolved")
        rows = self._db.execute("SELECT h.id FROM control_heads p JOIN control_history h USING(run_id,id,revision) WHERE h.run_id=? AND h.kind='WELFARE_HOLD'", (run_id,)).fetchall()
        if any(self.control(run_id, row[0])[1].status == "HELD" for row in rows):
            raise ValueError("welfare hold blocks semantic acceptance")
        return run_revision, run, objective_revision, episode_revision, episode

    def commit_steward(self, run_id, request_id, episode_id, raw, *, validate_bundle):
        """Atomic persistence primitive, not a complete runtime acceptance endpoint.

        P03/P06 must guard human authority and attempt eligibility before calling;
        validate_bundle is mandatory and must enforce the P05 rendered input budget.
        """
        result = self.receive_chamber(run_id, "STEWARD", request_id, episode_id, raw)
        if result is not None:
            return result
        try:
            with self._transaction("semantic"):
                row = self._request(run_id, "STEWARD", request_id)
                retry = self._retry(row, raw, episode_id)
                if retry is not None:
                    return retry
                run_revision, run, objective_revision, episode_revision, episode = self._guard(run_id, episode_id)
                decoded = decode_chamber_reply(raw, authenticated_role="STEWARD", run_id=run_id)
                proposal = decoded.message.body.task
                config = self.configuration(run_id)
                if len(canonical_bytes(proposal)) > config.budgets.proposal_bytes:
                    raise ValueError("proposal byte budget exceeded")
                objects = self.replay(run_id)
                events = self.events(run_id)
                context = parse(ResolutionContext, canonical_bytes({
                    "run_id": run_id, "objective_id": episode.objective_id, "parent_state_id": self._head(run_id), "arm": config.arm,
                    "objects": [{key: obj.model_dump(mode="json")[key] for key in
                        ("object_id", "run_id", "object_type", "objective_id", "revision", "family_id", "commitment_links")} for obj in objects.values()],
                    "events": [{"event_id": e["id"], "run_id": run_id, "chamber_visible": e["visibility"] == "CHAMBER"} for e in events]}))
                resolution = resolve_proposal(proposal, context, identifier)
                prior_evidence = {}
                for entry in self._db.execute("SELECT payload_id FROM mutations WHERE run_id=? ORDER BY rowid", (run_id,)):
                    ledger = load_json(self.read_payload(run_id, entry[0]))
                    evidence = self._event_ids(ledger["mutation"])
                    for change in ledger["changes"]:
                        prior_evidence.setdefault(change["object_id"], set()).update(evidence)
                final, changes = stage(resolution, objects, run_id=run_id, task_tick=run.task_tick,
                                       event_sources={e["id"]: e["source"] for e in events}, prior_evidence=prior_evidence)
                bundle = canonical_bytes({"continuity": resolution.proposal.continuity.model_dump(mode="json"),
                    "selected_objects": [final[r.object_id].model_dump(mode="json") for r in resolution.proposal.continuity.selected_objects]})
                if validate_bundle(bundle) is not None:
                    raise ValueError("bundle validator must raise on failure and return None on success")
                evidence_ids = self._event_ids(resolution.proposal.model_dump(mode="json"))
                for event in events:
                    if event["id"] in evidence_ids:
                        self.read_payload(run_id, event["payload_id"])
                state_id = identifier()
                handoff = self._payload(run_id, canonical_bytes(resolution.proposal.continuity))
                self._write("INSERT INTO states VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (state_id, run_id, episode_id, request_id, "STEWARD", context.parent_state_id, handoff,
                     run_revision, episode.objective_id, objective_revision, episode_revision))
                for index, (mutation, object_changes) in enumerate(zip(resolution.proposal.mutations, changes)):
                    ledger_changes = []
                    for before, after in object_changes:
                        prior = self._db.execute("SELECT payload_id FROM object_history WHERE run_id=? AND id=? AND revision=?",
                            (run_id, before.object_id, before.revision)).fetchone()[0] if before else None
                        after_payload = self._payload(run_id, canonical_bytes(after))
                        self._write("INSERT INTO object_history VALUES(?,?,?,?,?)", (run_id, after.object_id, after.revision, state_id, after_payload))
                        self._write("INSERT INTO object_heads VALUES(?,?,?) ON CONFLICT(run_id,id) DO UPDATE SET revision=excluded.revision",
                                    (run_id, after.object_id, after.revision))
                        ledger_changes.append({"object_id": after.object_id, "before": prior, "after": after_payload})
                    ledger = self._payload(run_id, canonical_bytes({"mutation": mutation.model_dump(mode="json"), "changes": ledger_changes}))
                    self._write("INSERT INTO mutations VALUES(?,?,?,?)", (run_id, state_id, index, ledger))
                for event_id in sorted(evidence_ids):
                    self._write("INSERT INTO evidence_links VALUES(?,?,?)", (run_id, state_id, event_id))
                self._write("INSERT INTO semantic_heads VALUES(?,?) ON CONFLICT(run_id) DO UPDATE SET state_id=excluded.state_id",
                            (run_id, state_id))
                self._control(run_id, episode_id, EpisodeState(kind="EPISODE", objective_id=episode.objective_id,
                    phase="CLOSED", disposition="ACCEPTED"), expected_revision=episode_revision)
                receipt = self._respond(run_id, "STEWARD", Receipt(request_id=request_id, status="ACCEPTED", state_id=state_id,
                    bindings=resolution.bindings, error_code=None, diagnostics=None))
            return receipt
        except Exception as error:
            # A failed semantic transaction cannot erase the separately committed report.
            # Store rejection only if acceptance did not commit (e.g. a lost response).
            with self._transaction("rejection"):
                row = self._request(run_id, "STEWARD", request_id)
                previous = self._retry(row, raw, episode_id)
                if previous is not None:
                    return previous
                diagnostic = self._payload(run_id, str(error).encode("utf-8"))
                return self._respond(run_id, "STEWARD", Receipt(request_id=request_id, status="REJECTED", state_id=None,
                    bindings=(), error_code="VALIDATION_FAILED", diagnostics={"payload_id": diagnostic}))

    @staticmethod
    def _event_ids(value):
        result = set()
        if isinstance(value, list):
            for item in value:
                result.update(Store._event_ids(item))
        elif isinstance(value, dict):
            for key, item in value.items():
                if key.endswith("event_ids"):
                    result.update(item)
                elif key == "authority_event_id":
                    result.add(item)
                else:
                    result.update(Store._event_ids(item))
        return result

    def replay(self, run_id):
        """Reconstruct from retained requests/ledger in one consistent read snapshot."""
        with self._snapshot():
            return self._replay(run_id)

    def _replay(self, run_id):
        replayed, history, parent, prior_evidence = {}, {}, None, {}
        config = self.configuration(run_id)
        events = self.events(run_id)
        event_sources = {e["id"]: e["source"] for e in events}
        for state in self._db.execute("SELECT * FROM states WHERE run_id=? ORDER BY rowid", (run_id,)):
            if state["parent_id"] != parent:
                raise StorageError("semantic parent chain mismatch")
            handoff = parse(ContinuityState, self.read_payload(run_id, state["payload_id"]))
            run = self._control_at(run_id, run_id, state["run_revision"])
            objective = self._control_at(run_id, state["objective_id"], state["objective_revision"])
            episode = self._control_at(run_id, state["episode_id"], state["episode_revision"])
            if (not isinstance(run, RunState) or run.status != "ACTIVE" or run.objective_id != state["objective_id"]
                    or not isinstance(objective, ObjectiveState) or objective.status != "ACTIVE"
                    or not isinstance(episode, EpisodeState) or episode.phase != "CONSOLIDATING"
                    or episode.objective_id != state["objective_id"]):
                raise StorageError("invalid retained acceptance basis")
            for evidence in self._db.execute(
                "SELECT e.payload_id FROM evidence_links l JOIN events e ON e.run_id=l.run_id AND e.id=l.event_id WHERE l.run_id=? AND l.state_id=?",
                (run_id, state["id"])):
                self.read_payload(run_id, evidence["payload_id"])
            request = self._request(run_id, state["role"], state["request_id"])
            if request is None or request["status"] != "ACCEPTED":
                raise StorageError("state lacks acceptance")
            receipt = parse(Receipt, self.read_payload(run_id, request["response_payload_id"]))
            if receipt.state_id != state["id"]:
                raise StorageError("acceptance points to another state")
            rows = self._db.execute("SELECT * FROM mutations WHERE run_id=? AND state_id=? ORDER BY position", (run_id, state["id"])).fetchall()
            original = decode_chamber_reply(self.read_payload(run_id, request["request_payload_id"]), authenticated_role="STEWARD", run_id=run_id)
            if (original.message is None or original.message.message_type != "STEWARD_REPLY"
                    or original.message.body.task is None or original.stop_requested or original.participation_uncertain
                    or len(original.message.body.task.mutations) != len(rows)):
                raise StorageError("mutation count or participation differs from accepted proposal")
            context = parse(ResolutionContext, canonical_bytes({
                "run_id": run_id, "objective_id": state["objective_id"], "parent_state_id": parent, "arm": config.arm,
                "objects": [{key: obj.model_dump(mode="json")[key] for key in
                    ("object_id", "run_id", "object_type", "objective_id", "revision", "family_id", "commitment_links")} for obj in replayed.values()],
                "events": [{"event_id": e["id"], "run_id": run_id, "chamber_visible": e["visibility"] == "CHAMBER"} for e in events]}))
            ids = iter(binding.object_id for binding in receipt.bindings)
            try:
                resolution = resolve_proposal(original.message.body.task, context, lambda: next(ids))
            except StopIteration as error:
                raise StorageError("missing retained identity binding") from error
            if resolution.bindings != receipt.bindings or resolution.proposal.continuity != handoff:
                raise StorageError("retained bindings or handoff disagree with proposal")
            _, staged = stage(resolution, replayed, run_id=run_id, task_tick=run.task_tick,
                              event_sources=event_sources, prior_evidence=prior_evidence)
            expected_evidence = self._event_ids(resolution.proposal.model_dump(mode="json"))
            actual_evidence = {r[0] for r in self._db.execute("SELECT event_id FROM evidence_links WHERE run_id=? AND state_id=?", (run_id,state["id"]))}
            if actual_evidence != expected_evidence:
                raise StorageError("evidence links differ from proposal")
            if [r["position"] for r in rows] != list(range(len(rows))):
                raise StorageError("mutation order is not consecutive")
            for index, row in enumerate(rows):
                entry = parse(MutationEntry, self.read_payload(run_id, row["payload_id"])).model_dump(mode="json")
                if entry["mutation"] != resolution.proposal.mutations[index].model_dump(mode="json"):
                    raise StorageError("ledger mutation differs from resolved proposal")
                if len(entry["changes"]) != len(staged[index]):
                    raise StorageError("ledger change count differs from staged proposal")
                for change, expected in zip(entry["changes"], staged[index]):
                    before = parse(StoredObject, self.read_payload(run_id, change["before"])) if change["before"] else None
                    after = parse(StoredObject, self.read_payload(run_id, change["after"]))
                    if (before, after) != expected:
                        raise StorageError("ledger change differs from staged proposal")
                    if replayed.get(change["object_id"]) != before or after.object_id != change["object_id"] or after.run_id != run_id:
                        raise StorageError("mutation before/after chain mismatch")
                    if after.revision != (before.revision + 1 if before else 1):
                        raise StorageError("mutation revision gap")
                    replayed[after.object_id] = after
                    history[(after.object_id, after.revision)] = (state["id"], change["after"])
                    prior_evidence.setdefault(after.object_id, set()).update(self._event_ids(entry["mutation"]))
            current_episode = self.control(run_id, state["episode_id"])[1]
            if not isinstance(current_episode, EpisodeState) or current_episode.disposition != "ACCEPTED":
                raise StorageError("accepted state has no closed Episode")
            parent = state["id"]
        if self._head(run_id) != parent or self._objects(run_id) != replayed:
            raise StorageError("semantic projection differs from replay")
        actual_history = {(r["id"], r["revision"]): (r["state_id"], r["payload_id"]) for r in self._db.execute("SELECT * FROM object_history WHERE run_id=?", (run_id,))}
        if actual_history != history:
            raise StorageError("object history differs from ledger")
        return replayed

    def verify(self):
        """Return diagnostics and block writes on corruption or removed dependencies."""
        with self._snapshot():
            return self._verify()

    def _verify(self):
        problems = []
        try:
            if self._db.execute("PRAGMA integrity_check").fetchall()[0][0] != "ok":
                raise StorageError("SQLite integrity failure")
            if self._db.execute("PRAGMA foreign_key_check").fetchall():
                raise StorageError("SQLite foreign-key failure")
            for blob in self._db.execute("SELECT * FROM blobs"):
                if sha256(blob["body"]).hexdigest() != blob["digest"]:
                    raise StorageError("blob hash mismatch")
            for run in self._db.execute("SELECT * FROM runs"):
                if self.removals.all(run['id']):
                    continue  # Structural checks above remain; governed loss is separately inspectable.
                config = self.configuration(run["id"])
                if config.arm != run["arm"]:
                    raise StorageError("Run arm differs from retained configuration")
                declared = self._declared_artifacts(config)
                artifacts = self._db.execute("SELECT * FROM artifacts WHERE run_id=?", (run["id"],)).fetchall()
                if {a["name"] for a in artifacts} != set(declared):
                    raise StorageError("retained artifact manifest differs from configuration")
                for artifact in artifacts:
                    body = self.read_payload(run["id"], artifact["payload_id"])
                    if sha256(body).hexdigest() != declared[artifact["name"]]:
                        raise StorageError("artifact differs from sealed hash")
                events = self.events(run["id"])
                if [e["sequence"] for e in events] != list(range(1, len(events) + 1)):
                    raise StorageError("Event sequence gap")
                heads = {}
                for control in self._db.execute("SELECT * FROM control_history WHERE run_id=? ORDER BY rowid", (run["id"],)):
                    expected = heads.get(control["id"], 0) + 1
                    if control["revision"] != expected:
                        raise StorageError("control history revision gap")
                    CONTROL.validate_json(self.read_payload(run["id"], control["payload_id"]), strict=True)
                    heads[control["id"]] = expected
                actual = {r["id"]: r["revision"] for r in self._db.execute("SELECT * FROM control_heads WHERE run_id=?", (run["id"],))}
                if heads != actual:
                    raise StorageError("control projection differs from history")
                self.replay(run["id"])
        except EvidenceUnavailable as error:
            problems.append("UNAVAILABLE: " + str(error))
        except (StorageError, ValueError, KeyError, TypeError, sqlite3.DatabaseError) as error:
            problems.append("INTEGRITY: " + str(error))
        self.problems = problems
        return tuple(problems)
