"""Current removal decisions live outside restorable evidence snapshots.

The trusted bootstrap must preserve this journal independently and supply it
when recovering older backups. It contains opaque identities and human-reviewed
non-sensitive accounting, never source bytes or their hashes.
"""
import sqlite3
from uuid import uuid4
from pathlib import Path
from ..contracts.base import canonical_bytes, load_json


class RemovalJournal:
    def __init__(self, path):
        self.path = Path(path)
        self.db = sqlite3.connect(self.path, isolation_level=None)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('PRAGMA secure_delete=ON')
        self.db.execute('CREATE TABLE IF NOT EXISTS decisions(id TEXT PRIMARY KEY,run_id TEXT NOT NULL,body BLOB NOT NULL) STRICT')
        self.db.execute('CREATE TABLE IF NOT EXISTS identity(singleton INTEGER PRIMARY KEY CHECK(singleton=1),id TEXT NOT NULL) STRICT')
        self.db.execute('INSERT OR IGNORE INTO identity VALUES(1,?)', (str(uuid4()),))
        self.identity = self.db.execute('SELECT id FROM identity').fetchone()[0]
        self.db.execute('CREATE TABLE IF NOT EXISTS progress(sequence INTEGER PRIMARY KEY,decision_id TEXT NOT NULL,body BLOB NOT NULL) STRICT')

    def close(self):
        self.db.close()

    def all(self, run_id=None):
        rows = self.db.execute('SELECT body FROM decisions' + (' WHERE run_id=?' if run_id else ''), (run_id,) if run_id else ())
        return [load_json(row[0]) for row in rows]

    def put(self, value):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old = self.db.execute('SELECT body FROM decisions WHERE id=?', (value['id'],)).fetchone()
            if old:
                prior = load_json(old[0])
                for key in ('run_id', 'payload_ids', 'intervention_id', 'decision_maker_id', 'justification', 'public_reason'):
                    if value[key] != prior[key]:
                        raise ValueError('approved removal scope is immutable')
            self.db.execute('INSERT INTO progress(decision_id,body) VALUES(?,?)', (value['id'], canonical_bytes(value)))
            self.db.execute('INSERT INTO decisions VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET body=excluded.body',
                            (value['id'], value['run_id'], canonical_bytes(value)))
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise


def closure(store, run_id, roots):
    """Conservative, review-visible dependency closure including shared bytes."""
    rows = list(store._db.execute('SELECT id,blob_id FROM payloads WHERE run_id=?', (run_id,)))
    payloads = {row['id']: row['blob_id'] for row in rows}
    if not roots or len(roots) != len(set(roots)) or not set(roots) <= payloads.keys():
        raise ValueError('removal roots must be unique retained payloads in this Run')
    for key in roots:
        store.read_payload(run_id, key)
    lineage = {r[0] for r in store._db.execute('SELECT payload_id FROM payload_lineage WHERE run_id=?', (run_id,))}
    # Older released stores had only partial provenance. They require explicit
    # review of conservative whole-Run content disposition, never a false claim
    # that selective erasure can identify every historical derivative.
    legacy = bool(set(payloads) - lineage)
    affected = set(payloads) if legacy else set(roots)
    edges = list(store._db.execute('SELECT source_id,target_id FROM derived_payloads WHERE run_id=?', (run_id,)))
    while True:
        before = set(affected)
        blobs = {payloads[key] for key in affected if payloads[key] is not None}
        affected.update(key for key, blob in payloads.items() if blob in blobs)
        affected.update(target for source, target in edges if source in affected)
        if before == affected:
            break
    shared = [dict(r) for r in store._db.execute('''SELECT p.run_id,p.id FROM payloads p WHERE p.run_id!=?
        AND p.blob_id IN (SELECT blob_id FROM payloads WHERE run_id=? AND id IN (SELECT value FROM json_each(?)))''',
        (run_id, run_id, canonical_bytes(sorted(affected)).decode()))]
    copies = [dict(r) for r in store._db.execute("SELECT * FROM known_copies WHERE run_id=? AND disposition!='REMOVED'", (run_id,))]
    return {'payload_ids': sorted(affected), 'copies': copies, 'shared_payloads': shared, 'legacy_whole_run': legacy}


def scrub_database(store):
    """Idempotently apply all current decisions before any evidence is read."""
    decisions = store.removals.all()
    if not decisions:
        return
    for decision in decisions:
        if decision.get('scope_review_required') or decision['legacy_whole_run']:
            continue
        incomplete = store._db.execute('''SELECT 1 FROM payloads p WHERE p.run_id=? AND p.disposition='RETAINED'
            AND NOT EXISTS(SELECT 1 FROM payload_lineage l WHERE l.run_id=p.run_id AND l.payload_id=p.id)
            AND p.id NOT IN (SELECT value FROM json_each(?)) LIMIT 1''',
            (decision['run_id'], canonical_bytes(decision['payload_ids']).decode())).fetchone()
        if incomplete:
            # A released selective decision may have omitted derivatives. Do not
            # expand immutable deletion authority or continue claiming completion.
            decision.update(status='INCOMPLETE', scope_review_required=True,
                scope_review_reason='Historical lineage is incomplete; accountable review of the remaining content is required.')
            store.removals.put(decision)
    store._db.execute('BEGIN IMMEDIATE')
    try:
        for decision in decisions:
            run_id = decision['run_id']
            for key in decision['payload_ids']:
                store._db.execute("UPDATE payloads SET blob_id=NULL,disposition='REMOVED' WHERE run_id=? AND id=?", (run_id, key))
            store._db.execute('UPDATE inspection_receipts SET digest=NULL,byte_length=NULL WHERE run_id=?', (run_id,))
            store._db.execute('UPDATE known_copies SET digest=NULL,byte_length=NULL WHERE run_id=?', (run_id,))
        store._db.execute('DELETE FROM blobs WHERE NOT EXISTS(SELECT 1 FROM payloads p WHERE p.blob_id=blobs.id)')
        store._db.commit()
    except BaseException:
        store._db.rollback()
        raise
    store._fault('retention.after_scrub')


def compact(store):
    if store._db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0] != 0:
        return False
    store._db.execute('VACUUM')
    return store._db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0] == 0
