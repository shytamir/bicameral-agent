"""Human-only paged SQLite snapshots and nonrecursive streamed evidence exports."""
import base64
from hashlib import sha256
from pathlib import Path
import sqlite3
from ..contracts.base import canonical_bytes, load_json
from ..storage.store import identifier, EvidenceUnavailable


class Inspector:
    def __init__(self, kernel):
        self.k = kernel

    def open(self, human):
        self.k._human(human._cap)
        return Inspection(self.k)

    def copy_status(self, human, copy_id, destination):
        self.k._human(human._cap)
        row = self.k.store._db.execute('SELECT * FROM known_copies WHERE run_id=? AND id=?',
                                       (self.k.run_id, copy_id)).fetchone()
        if row is None:
            raise ValueError('unknown copy')
        if row['disposition'] == 'REMOVED':
            return 'REMOVED'
        path = Path(destination)
        if not path.is_file():
            return 'UNAVAILABLE'
        digest, length = file_digest(path)
        return 'AVAILABLE' if (digest, length) == (row['digest'], row['byte_length']) else 'INTEGRITY_FAILURE'


def file_digest(path):
    digest, length = sha256(), 0
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            digest.update(block); length += len(block)
    return digest.hexdigest(), length


class Inspection:
    def __init__(self, kernel):
        self.k, self.id, self.closed = kernel, identifier(), False
        self.retention_epoch = kernel.store.retention_epoch(kernel.run_id)
        self.db = sqlite3.connect(kernel.store.path.resolve().as_uri() + '?mode=ro', uri=True, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('BEGIN')
        self.event_cutoff = self.db.execute('SELECT COALESCE(MAX(sequence),0) FROM events WHERE run_id=?', (kernel.run_id,)).fetchone()[0]
        self.record_cutoff = self.db.execute('SELECT COALESCE(MAX(sequence),0) FROM kernel_records WHERE run_id=?', (kernel.run_id,)).fetchone()[0]
        self.tables = {}
        for row in self.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"):
            name = row[0]
            columns = [col[1] for col in self.db.execute(f'PRAGMA table_info("{name}")')]
            if name == 'blobs':
                sql, params = 'SELECT b.* FROM blobs b WHERE EXISTS(SELECT 1 FROM payloads p WHERE p.run_id=? AND p.blob_id=b.id)', (kernel.run_id,)
            elif name == 'runs':
                sql, params = 'SELECT * FROM runs WHERE id=?', (kernel.run_id,)
            elif 'run_id' in columns:
                sql, params = f'SELECT * FROM "{name}" WHERE run_id=?', (kernel.run_id,)
            elif name == 'study_suspensions':
                sql, params = 'SELECT * FROM study_suspensions WHERE plan_id IN (SELECT plan_id FROM allocations WHERE run_id=?)', (kernel.run_id,)
            elif name == 'migrations':
                sql, params = 'SELECT * FROM migrations', ()
            else:
                continue
            self.tables[name] = (sql, params)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _check(self):
        if self.closed:
            raise ValueError('inspection snapshot closed')
        # P10 may invalidate a previously opened snapshot; old SQLite pages are
        # never an exemption from a current removal decision.
        if self.retention_epoch != self.k.store.retention_epoch(self.k.run_id):
            raise EvidenceUnavailable('REMOVAL_CHANGED: reopen inspection for current dispositions')

    def manifest(self):
        self._check()
        return {'format': 'BICAMERAL_EXPORT_1', 'scope': 'RUN', 'run_id': self.k.run_id, 'snapshot_id': self.id,
            'event_cutoff': self.event_cutoff, 'record_cutoff': self.record_cutoff,
            'tables': {name: self.db.execute('SELECT COUNT(*) FROM (' + sql + ')', params).fetchone()[0]
                       for name, (sql, params) in self.tables.items()}}

    def page(self, table, *, offset, limit):
        self._check()
        if table not in self.tables or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 128:
            raise ValueError('invalid inspection page')
        sql, params = self.tables[table]
        if table == 'blobs':
            sql = 'SELECT id,digest,length(body) AS byte_length FROM (' + sql + ')'
        rows = [dict(row) for row in self.db.execute(sql + ' ORDER BY 1 LIMIT ? OFFSET ?', (*params, limit, offset))]
        if table == 'blobs':
            for row in rows:
                self._live_blob(row['id'])
        return {'snapshot_id': self.id, 'table': table, 'offset': offset, 'rows': rows,
                'next_offset': offset + len(rows) if len(rows) == limit else None}

    def _live_blob(self, blob_id):
        row = self.k.store._db.execute('SELECT id FROM payloads WHERE run_id=? AND blob_id=?', (self.k.run_id, blob_id)).fetchone()
        if row is None:
            raise EvidenceUnavailable('REMOVED: snapshot blob no longer retained')
        self.k.store.read_payload(self.k.run_id, row[0])

    def blob(self, blob_id, *, offset, limit):
        self._check()
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 65536:
            raise ValueError('invalid byte page')
        self._live_blob(blob_id)
        sql, params = self.tables['blobs']
        row = self.db.execute('SELECT digest,length(body),substr(body,?,?) FROM (' + sql + ') WHERE id=?',
                              (offset + 1, limit, *params, blob_id)).fetchone()
        if row is None or offset > row[1]:
            raise ValueError('unknown snapshot blob or offset')
        return {'id': blob_id, 'digest': row[0], 'byte_length': row[1], 'offset': offset,
                'body': row[2], 'next_offset': offset + len(row[2]) if offset + len(row[2]) < row[1] else None}

    def export(self, destination):
        self._check()
        path = Path(destination).resolve()
        if path == self.k.store.path.resolve() or path.name in {self.k.store.path.name + '-wal', self.k.store.path.name + '-shm'}:
            raise ValueError('export must be outside the live database')
        if path.exists():
            self._receipt('FAILED', diagnostic='DESTINATION_EXISTS')
            raise FileExistsError('export never overwrites an existing file')
        copy_id = identifier()
        with self.k.store._transaction('export-intent'):
            self.k.store._write("INSERT INTO known_copies VALUES(?,?,'EXPORT','PENDING',NULL,NULL,NULL)", (copy_id, self.k.run_id))
        digest, length = sha256(), 0
        try:
            with path.open('xb') as stream:
                def write(value):
                    nonlocal length
                    data = canonical_bytes(value) + b'\n'
                    stream.write(data); digest.update(data); length += len(data)
                write({'kind': 'MANIFEST', 'copy_id': copy_id, **self.manifest()})
                for table in self.tables:
                    offset = 0
                    while True:
                        page = self.page(table, offset=offset, limit=128)
                        for row in page['rows']:
                            write({'kind': 'ROW', 'table': table, 'value': row})
                            if table == 'blobs':
                                start = 0
                                while True:
                                    part = self.blob(row['id'], offset=start, limit=32768)
                                    write({'kind': 'BLOB', 'id': row['id'], 'offset': start, 'data': base64.b64encode(part['body']).decode()})
                                    if part['next_offset'] is None:
                                        break
                                    start = part['next_offset']
                        if page['next_offset'] is None:
                            break
                        offset = page['next_offset']
                write({'kind': 'COMPLETE', 'prior_digest': digest.hexdigest(), 'prior_byte_length': length})
                stream.flush()
                import os
                os.fsync(stream.fileno())
            verify_export(path)
        except Exception:
            self._receipt('FAILED', copy_id=copy_id, diagnostic='EXPORT_FAILED_OR_INCOMPLETE')
            raise
        with self.k.store._transaction('export-complete'):
            stat = path.stat()
            self.k.store._write("UPDATE known_copies SET disposition='AVAILABLE',digest=?,byte_length=?,file_identity=? WHERE run_id=? AND id=?",
                (digest.hexdigest(), length, canonical_bytes([stat.st_dev, stat.st_ino]).decode(), self.k.run_id, copy_id))
            self._write_receipt('EXPORTED', digest=digest.hexdigest(), length=length, copy_id=copy_id)
        return {'copy_id': copy_id, 'digest': digest.hexdigest(), 'byte_length': length}

    def _write_receipt(self, disposition, *, digest=None, length=None, copy_id=None, diagnostic=None):
        self.k.store._write('INSERT INTO inspection_receipts VALUES(?,?,?,?,?,?,?,?,?,?)',
            (identifier(), self.k.run_id, self.id, self.event_cutoff, self.record_cutoff, disposition, digest, length, copy_id, diagnostic))

    def _receipt(self, disposition, **values):
        with self.k.store._transaction('inspection-receipt'):
            self._write_receipt(disposition, **values)

    def close(self):
        if not self.closed:
            self.db.rollback(); self.db.close(); self.closed = True
            self._receipt('INSPECTED')


def verify_export(path):
    """Stream verification without retaining full export or blob bodies."""
    digest, length, counts, blobs, refs, manifest, complete = sha256(), 0, {}, {}, set(), None, False
    with Path(path).open('rb') as stream:
        for line in stream:
            value = load_json(line)
            if complete:
                raise ValueError('trailing export bytes')
            if value['kind'] == 'MANIFEST':
                if manifest is not None or length or value['format'] != 'BICAMERAL_EXPORT_1':
                    raise ValueError('invalid export manifest')
                manifest = value
            elif value['kind'] == 'ROW':
                table, row = value['table'], value['value']
                if manifest is None or table not in manifest['tables']:
                    raise ValueError('unexpected export table')
                counts[table] = counts.get(table, 0) + 1
                if table == 'blobs':
                    if row['id'] in blobs:
                        raise ValueError('duplicate blob')
                    blobs[row['id']] = [row['digest'], row['byte_length'], sha256(), 0]
                elif table == 'payloads' and row['blob_id'] is not None:
                    refs.add(row['blob_id'])
            elif value['kind'] == 'BLOB':
                blob = blobs[value['id']]
                raw = base64.b64decode(value['data'], validate=True)
                if value['offset'] != blob[3]:
                    raise ValueError('noncontiguous blob')
                blob[2].update(raw); blob[3] += len(raw)
            elif value['kind'] == 'COMPLETE':
                if value['prior_digest'] != digest.hexdigest() or value['prior_byte_length'] != length:
                    raise ValueError('export digest mismatch')
                complete = True
            else:
                raise ValueError('unknown export record')
            digest.update(line); length += len(line)
    if (not complete or manifest is None or {k: counts.get(k, 0) for k in manifest['tables']} != manifest['tables'] or
            refs != set(blobs) or any(d != h.hexdigest() or size != actual for d, size, h, actual in blobs.values())):
        raise ValueError('incomplete export')
    return {'digest': digest.hexdigest(), 'byte_length': length, 'manifest': manifest}
