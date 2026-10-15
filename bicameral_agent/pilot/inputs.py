"""Reuse journal paging, with 0.4 semantic views and common policy lookup."""
from hashlib import sha256
from ..contracts.base import canonical_bytes, load_json
from ..kernel.inputs import Inputs, ObjectQuery, StateQuery


class PilotInputs(Inputs):
    def _object_rows(self, cutoff):
        if self.k.config.arm == 'B':
            return []
        return self.k.store._db.execute('''SELECT a.* FROM kernel_records a WHERE run_id=? AND kind='PILOT_OBJECT'
            AND sequence<=? AND NOT EXISTS(SELECT 1 FROM kernel_records b WHERE b.run_id=a.run_id
                AND b.kind=a.kind AND b.id=a.id AND b.sequence<=? AND b.revision>a.revision)
            ORDER BY a.sequence,a.id''', (self.k.run_id, cutoff, cutoff))

    def _payload_allowed(self, key, event_cutoff, record_cutoff):
        db = self.k.store._db
        if db.execute("SELECT 1 FROM events WHERE run_id=? AND visibility='CHAMBER' AND sequence<=? AND payload_id=?",
                      (self.k.run_id, event_cutoff, key)).fetchone():
            return True
        for row in self._object_rows(record_cutoff):
            if row['payload_id'] == key:
                obj = load_json(self.k.store.read_payload(self.k.run_id, key))
                return self.k.config.arm == 'A' or obj['kind'] == 'COMMITMENT'
        if self.k.config.arm != 'B' and db.execute("SELECT 1 FROM kernel_records WHERE run_id=? AND kind='PILOT_MEMORY' AND sequence<=? AND payload_id=?",
                (self.k.run_id, record_cutoff, key)).fetchone():
            return True
        for row in db.execute("SELECT kind,payload_id FROM kernel_records WHERE run_id=? AND sequence<=? AND kind IN ('ACTION','INVOCATION')",
                              (self.k.run_id, record_cutoff)):
            value = load_json(self.k.store.read_payload(self.k.run_id, row['payload_id']))
            fields = ('request_payload_id',) if row['kind'] == 'ACTION' else ('input_payload_id', 'output_payload_id')
            if key in [value.get(field) for field in fields]:
                return True
        return False

    def _entries(self, query, event_cutoff, record_cutoff):
        if not isinstance(query, (ObjectQuery, StateQuery)):
            return super()._entries(query, event_cutoff, record_cutoff)
        if self.k.config.arm == 'B':
            raise PermissionError('B has no semantic retrieval channel')
        if isinstance(query, StateQuery):
            rows = self.k.store._db.execute("SELECT * FROM kernel_records WHERE run_id=? AND kind='PILOT_MEMORY' AND sequence<=? ORDER BY sequence",
                                           (self.k.run_id, record_cutoff))
        else:
            rows = self._object_rows(record_cutoff)
        entries, dependencies = [], []
        for row in rows:
            raw = self.k.store.read_payload(self.k.run_id, row['payload_id'])
            value = load_json(raw)
            if isinstance(query, StateQuery):
                if value['state_id'] != query.state_id:
                    continue
                key = value['state_id']
            else:
                mapped = {'INVARIANT': 'INVARIANT_VERSION'}.get(value['kind'], value['kind'])
                if (self.k.config.arm == 'C' and value['kind'] != 'COMMITMENT' or
                        query.object_id is not None and query.object_id != value['id'] or
                        query.object_type is not None and query.object_type != mapped or
                        query.status is not None and query.status != value['status']):
                    continue
                key = value['id']
            dependencies.append(row['payload_id'])
            entries.append({'id': key, 'payload_id': row['payload_id'], 'bytes': len(raw),
                            'sha256': sha256(raw).hexdigest(), 'sources': ['M']})
        return entries, dependencies
