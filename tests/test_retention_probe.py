"""Early feasibility only: no production store, media-erasure or recovery claim."""

from contextlib import closing
import sqlite3
import unittest

from bicameral_agent.contracts.base import canonical_bytes, parse
from bicameral_agent.contracts.governance import ParticipationRecord
from tests.fixtures import governance_examples


class RetentionFeasibilityTests(unittest.TestCase):
    def test_shared_source_can_be_removed_without_erasing_accountability(self):
        # Deliberately temporary and synthetic. WAL/backups/exports remain P02/P10 work.
        source = b"synthetic-sensitive-report-123"
        _, record_value = governance_examples()["PARTICIPATION_RECORD"]
        record = parse(ParticipationRecord, canonical_bytes(record_value))
        payload_id = record.original_payload.payload_id
        with closing(sqlite3.connect(":memory:")) as db:
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript("""
                CREATE TABLE content(id TEXT PRIMARY KEY, body BLOB, removed INTEGER NOT NULL,
                    CHECK ((removed=0 AND body IS NOT NULL) OR (removed=1 AND body IS NULL)));
                CREATE TABLE evidence(kind TEXT PRIMARY KEY, content_id TEXT NOT NULL REFERENCES content(id));
                CREATE TABLE decisions(id INTEGER PRIMARY KEY, reason TEXT NOT NULL);
            """)
            db.execute("INSERT INTO content VALUES (?, ?, 0)", (payload_id, source))
            db.executemany("INSERT INTO evidence VALUES (?, ?)",
                           [(kind, payload_id) for kind in ("journal", "invocation", "retrieval-cache")])
            db.commit()
            with self.assertRaises(sqlite3.IntegrityError):
                with db:
                    db.execute("UPDATE content SET body=NULL, removed=1 WHERE id=?", (payload_id,))
                    db.execute("INSERT INTO decisions VALUES (1, NULL)")
            self.assertEqual(db.execute("SELECT body FROM content").fetchone()[0], source)
            with db:
                db.execute("UPDATE content SET body=NULL, removed=1 WHERE id=?", (payload_id,))
                db.execute("INSERT INTO decisions VALUES (1, 'Synthetic justified removal')")
            rows = db.execute("SELECT body, removed FROM evidence JOIN content ON content.id=evidence.content_id").fetchall()
            self.assertEqual(rows, [(None, 1)] * 3)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0], 3)
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertNotIn(source, canonical_bytes(record))
            self.assertNotIn(source.decode(), "\n".join(db.iterdump()))


if __name__ == "__main__":
    unittest.main()
