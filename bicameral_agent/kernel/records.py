"""Versioned, removal-aware Kernel records using the P02 transaction boundary."""
from ..contracts.base import canonical_bytes, load_json
from ..storage import StorageError


class Records:
    def __init__(self, store, run_id):
        self.store, self.run_id = store, run_id

    def row(self, kind, key):
        return self.store._db.execute(
            "SELECT * FROM kernel_records WHERE run_id=? AND kind=? AND id=? ORDER BY revision DESC LIMIT 1",
            (self.run_id, kind, key)).fetchone()

    def get(self, kind, key, default=None):
        row = self.row(kind, key)
        return default if row is None else load_json(self.store.read_payload(self.run_id, row['payload_id']))

    def revision(self, kind, key):
        row = self.row(kind, key)
        return row['revision'] if row else 0

    def put(self, kind, key, value, *, expected):
        if not self.store._db.in_transaction:
            raise StorageError('Kernel records require a transaction')
        if self.revision(kind, key) != expected:
            raise ValueError('stale Kernel record')
        payload = self.store._payload(self.run_id, canonical_bytes(value))
        self.store._write('INSERT INTO kernel_records(run_id,kind,id,revision,payload_id) VALUES(?,?,?,?,?)',
                          (self.run_id, kind, key, expected + 1, payload))

    def latest(self, kind):
        rows = self.store._db.execute('''SELECT a.* FROM kernel_records a WHERE run_id=? AND kind=?
            AND NOT EXISTS(SELECT 1 FROM kernel_records b WHERE b.run_id=a.run_id AND b.kind=a.kind
                AND b.id=a.id AND b.revision>a.revision) ORDER BY a.sequence''', (self.run_id, kind))
        return [(r['id'], load_json(self.store.read_payload(self.run_id, r['payload_id']))) for r in rows]

    def history(self, kind):
        return [(r['id'], r['revision'], load_json(self.store.read_payload(self.run_id, r['payload_id'])))
                for r in self.store._db.execute('SELECT * FROM kernel_records WHERE run_id=? AND kind=? ORDER BY sequence',
                                               (self.run_id, kind))]
