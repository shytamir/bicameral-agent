"""Pre-schema, file-backed synthetic proof; not a physical-media erasure claim."""
from contextlib import closing
from hashlib import sha256
from pathlib import Path
import sqlite3
import tempfile
import unittest


class FileRetentionDesignProbe(unittest.TestCase):
    def test_removal_reaches_shared_references_and_file_backed_copies(self):
        source = b'synthetic-sensitive-p02-design-probe'
        digest = sha256(source).hexdigest().encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'probe.db'
            with closing(sqlite3.connect(path)) as db:
                db.execute('PRAGMA foreign_keys=ON')
                db.execute('PRAGMA journal_mode=WAL')
                db.execute('PRAGMA synchronous=FULL')
                db.execute('PRAGMA secure_delete=ON')
                db.executescript('''
                    CREATE TABLE payload(id INTEGER PRIMARY KEY, digest TEXT UNIQUE, body BLOB,
                        removed INTEGER NOT NULL CHECK(removed IN (0,1)),
                        CHECK((removed=0 AND body IS NOT NULL AND digest IS NOT NULL)
                           OR (removed=1 AND body IS NULL AND digest IS NULL)));
                    CREATE TABLE copy(kind TEXT PRIMARY KEY, payload_id INTEGER REFERENCES payload(id));
                    CREATE TABLE intervention(id INTEGER PRIMARY KEY, decision TEXT NOT NULL);
                ''')
                db.execute('INSERT INTO payload VALUES(1, ?, ?, 0)', (digest.decode(), source))
                db.executemany('INSERT INTO copy VALUES(?,1)', [(kind,) for kind in
                    ('journal', 'mutation', 'projection', 'invocation', 'idempotency', 'retrieval')])
                db.commit()
                with self.assertRaises(sqlite3.IntegrityError):
                    with db:
                        db.execute('UPDATE payload SET body=NULL,digest=NULL,removed=1')
                        db.execute('INSERT INTO intervention VALUES(1,NULL)')
                self.assertEqual(db.execute('SELECT body FROM payload').fetchone()[0], source)
                with db:
                    db.execute('UPDATE payload SET body=NULL,digest=NULL,removed=1')
                    db.execute("INSERT INTO intervention VALUES(1,'Synthetic approved removal; evidence unavailable')")
                self.assertEqual(db.execute('SELECT body,digest,removed FROM copy JOIN payload ON payload.id=copy.payload_id').fetchall(), [(None, None, 1)] * 6)
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
                self.assertEqual(db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0], 0)
                db.execute('VACUUM')
                self.assertEqual(db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()[0], 0)
            with closing(sqlite3.connect(path)) as reopened:
                self.assertEqual(reopened.execute('SELECT COUNT(*) FROM intervention').fetchone()[0], 1)
                self.assertEqual(reopened.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            for file in Path(directory).iterdir():
                self.assertNotIn(source, file.read_bytes())
                self.assertNotIn(digest, file.read_bytes())
