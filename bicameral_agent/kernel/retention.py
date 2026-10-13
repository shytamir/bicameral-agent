"""Authenticated reviewed removal and forward-only recovery from old copies."""
import os
from pathlib import Path
import sqlite3
from ..contracts.base import canonical_bytes, load_json
from ..storage.retention import closure, scrub_database, compact
from ..storage.store import identifier, Store


class Retention:
    def __init__(self, kernel):
        self.k = kernel

    @staticmethod
    def effects(command):
        return command.model_dump(mode='json', exclude={'intervention_id'})

    def describe(self, command):
        plan = closure(self.k.store, self.k.run_id, command.payload_ids)
        if set(command.copy_ids) != {c['id'] for c in plan['copies']} or len(command.copy_ids) != len(set(command.copy_ids)):
            raise ValueError('review must account for every known export/backup exactly once')
        return plan

    def confirm(self, cap, command, stamp, token):
        self.k._human(cap)
        previous = next((d for d in self.k.store.removals.all(self.k.run_id) if d['id'] == token), None)
        if previous:
            return {'control': 'REMOVE_CONTENT', 'result': {'decision_id': token}}
        with self.k.store._transaction('removal-authorization'):
            if stamp != self.k._stamp():
                raise ValueError('stale removal display')
            revision, run = self.k.run()
            if run.status not in {'PAUSED', 'TERMINATED', 'COMPLETED'}:
                raise ValueError('stop computation before reviewed removal')
            plan = self.describe(command)
            _, review = self.k.store.control(self.k.run_id, command.intervention_id)
            targets = {(t.record_type, t.record_id, t.expected_revision) for t in review.targets}
            required = {('RUN', self.k.run_id, revision)} | {('PAYLOAD', key, 1) for key in command.payload_ids}
            if targets != required:
                raise ValueError('retention review must name current Run and exact source payloads')
            self.k.check_intervention(command.intervention_id, self.effects(command), required_kind='RETENTION')
            # Include review records derived from the sources in this transaction.
            plan = self.describe(command)
            decision = {'id': token, 'run_id': self.k.run_id, 'intervention_id': command.intervention_id,
                'decision_maker_id': self.k.config.responsible_human_id, 'justification': command.justification,
                'public_reason': command.public_reason, 'previous_run_status': run.status,
                'payload_ids': plan['payload_ids'], 'legacy_whole_run': plan['legacy_whole_run'],
                'copies': [{'id': c['id'], 'kind': c['kind'], 'disposition': 'PENDING',
                            'origin_identity': load_json(c['file_identity'].encode()) if c['file_identity'] else None} for c in plan['copies']],
                'shared_payloads': plan['shared_payloads'], 'status': 'IN_PROGRESS', 'storage_scrubbed': False,
                'file_compaction_verified': False, 'continuation': 'STOPPED',
                'report_count': self.k.store._db.execute('SELECT COUNT(*) FROM reports WHERE run_id=?', (self.k.run_id,)).fetchone()[0],
                'limits': ['Logical SQLite/file removal only; physical media and unregistered copies are not verifiable.',
                           'No provider copies exist in the SCRIPTED envelope.'],
                'remaining_state': 'Opaque provenance, allocation and non-sensitive disposition; removed evidence cannot support replay.'}
            # This external decision is authoritative even if the evidence
            # transaction fails or an older evidence snapshot is recovered.
            self.k.store.removals.put(decision)
            self.k.store._fault('retention.after_decision')
        return {'control': 'REMOVE_CONTENT', 'result': {'decision_id': token}}

    @staticmethod
    def resume(store, decision_id, *, locations):
        decision = next((d for d in store.removals.all() if d['id'] == decision_id), None)
        if decision is None:
            raise ValueError('no approved removal decision')
        if set(locations) - {c['id'] for c in decision['copies']}:
            raise ValueError('unapproved copy location')
        scrub_database(store)
        decision = next(d for d in store.removals.all() if d['id'] == decision_id)
        decision['storage_scrubbed'] = True
        for copy in decision['copies']:
            if copy['disposition'] == 'REMOVED':
                continue
            destination = locations.get(copy['id'])
            if destination is None:
                copy['disposition'] = 'INACCESSIBLE'
                continue
            path = Path(destination).resolve()
            if path in {store.path.resolve(), store.removals.path.resolve()}:
                raise ValueError('copy disposition cannot delete the live store or current journal')
            if not path.exists():
                copy['disposition'] = 'REMOVED' if copy['disposition'] == 'ERASING' else 'UNVERIFIED'
                copy.pop('file_identity', None)
                continue
            stat = path.stat()
            identity = [stat.st_dev, stat.st_ino]
            if copy['origin_identity'] is not None and identity != copy['origin_identity']:
                raise ValueError('reviewed file identity changed')
            if copy['disposition'] == 'ERASING':
                valid = identity == copy['file_identity']
            elif copy['kind'] == 'EXPORT':
                with path.open('rb') as stream:
                    header = load_json(stream.readline())
                valid = header.get('copy_id') == copy['id'] and header.get('run_id') == decision['run_id']
            else:
                db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
                try:
                    valid = db.execute('SELECT 1 FROM known_copies WHERE run_id=? AND id=?', (decision['run_id'], copy['id'])).fetchone() is not None
                finally:
                    db.close()
            if not valid:
                raise ValueError('destination is not the reviewed copy')
            copy['disposition'], copy['file_identity'] = 'ERASING', identity
            store.removals.put(decision)
            store._fault('retention.after_copy_intent')
            # Do not claim media erasure. Overwrite the governed file's logical
            # bytes, synchronize it, and remove its directory entry.
            with path.open('r+b') as stream:
                opened = os.fstat(stream.fileno())
                if [opened.st_dev, opened.st_ino] != identity:
                    raise ValueError('copy identity changed during opening')
                remaining = path.stat().st_size
                while remaining:
                    amount = min(65536, remaining)
                    stream.write(b'\0' * amount); remaining -= amount
                stream.flush(); os.fsync(stream.fileno())
            store._fault('retention.after_copy_overwrite')
            path.unlink()
            copy['disposition'] = 'REMOVED'
            copy.pop('file_identity', None)
            store.removals.put(decision)
            store._fault('retention.after_copy')
        decision['shared_payloads'] = [p for p in decision['shared_payloads'] if store._db.execute(
            "SELECT 1 FROM payloads WHERE run_id=? AND id=? AND disposition='RETAINED'", (p['run_id'], p['id'])).fetchone()]
        decision['file_compaction_verified'] = compact(store)
        decision['status'] = ('COMPLETED' if not decision.get('scope_review_required') and
            decision['file_compaction_verified'] and not decision['shared_payloads'] and
            all(c['disposition'] == 'REMOVED' for c in decision['copies']) else 'INCOMPLETE')
        store.removals.put(decision)
        with store._transaction('retention-copy-dispositions'):
            for copy in decision['copies']:
                store._write('UPDATE known_copies SET disposition=?,digest=NULL,byte_length=NULL WHERE run_id=? AND id=?',
                    ('REMOVED' if copy['disposition'] == 'REMOVED' else 'UNAVAILABLE', decision['run_id'], copy['id']))
        store.verify()
        return decision


def backup(human, destination):
    k = human._k
    k._human(human._cap)
    k.store.retention_guard(k.run_id, execution=True)
    path = Path(destination).resolve()
    if path.exists():
        raise FileExistsError('backup destination must be new')
    copy_id = identifier()
    runs = [row[0] for row in k.store._db.execute('SELECT id FROM runs')]
    if runs != [k.run_id]:
        raise ValueError('backup adapter requires a single-Run database so copy authority is unambiguous')
    with k.store._transaction('backup-intent'):
        k.store._write("INSERT INTO known_copies VALUES(?,?,'BACKUP','PENDING',NULL,NULL,NULL)", (copy_id, k.run_id))
    target = sqlite3.connect(path)
    try:
        k.store._db.backup(target)
    finally:
        target.close()
    from .inspection import file_digest
    digest, length = file_digest(path)
    with k.store._transaction('backup-receipt'):
        stat = path.stat()
        k.store._write("UPDATE known_copies SET disposition='AVAILABLE',digest=?,byte_length=?,file_identity=? WHERE run_id=? AND id=?",
                       (digest, length, canonical_bytes([stat.st_dev, stat.st_ino]).decode(), k.run_id, copy_id))
    return copy_id


def recover_backup(source, destination, *, current_removal_journal, busy_timeout_ms):
    """Trusted recovery: preserve Run identity and apply current decisions first."""
    source, destination, journal = Path(source).resolve(), Path(destination).resolve(), Path(current_removal_journal).resolve()
    if destination.exists() or not journal.is_file() or journal in {source, destination}:
        raise ValueError('recovery requires a new destination and the independently preserved current journal')
    src = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
    target = sqlite3.connect(destination)
    try:
        src.backup(target)
    finally:
        src.close()
        target.close()
    store = Store(destination, busy_timeout_ms=busy_timeout_ms, removal_journal=journal)
    compact(store)
    return store
