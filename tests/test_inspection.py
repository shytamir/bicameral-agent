from bicameral_agent.kernel.inspection import Inspector, verify_export
from bicameral_agent.storage import EvidenceUnavailable
from tests.kernel_fixtures import KernelCase, CHAMBER_KEYS


class InspectionTests(KernelCase):
    def setUp(self):
        super().setUp()
        self.activate()
        self.i = Inspector(self.k)

    def test_human_snapshot_pages_include_original_reports_and_hidden_evidence(self):
        raw = b'Synthetic confidential evaluator bytes'
        event = self.store.record_evidence(self.run, raw, role='ENVIRONMENT', source='E', visibility='EVALUATOR')
        self.report({'kind': 'CONCERN', 'activity_id': self.objective, 'text': 'Synthetic retained concern'})
        with self.i.open(self.h) as snapshot:
            events = snapshot.page('events', offset=0, limit=128)['rows']
            pid = next(row['payload_id'] for row in events if row['id'] == event)
            payloads = snapshot.page('payloads', offset=0, limit=128)['rows']
            bid = next(row['blob_id'] for row in payloads if row['id'] == pid)
            parts, offset = [], 0
            while True:
                page = snapshot.blob(bid, offset=offset, limit=3)
                parts.append(page['body'])
                if page['next_offset'] is None:
                    break
                offset = page['next_offset']
            self.assertEqual(raw, b''.join(parts))
            self.assertEqual(1, snapshot.manifest()['tables']['reports'])
        with self.assertRaises(PermissionError):
            self.i.open(self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR']))

    def test_snapshot_cutoff_does_not_move_during_concurrent_evidence_writes(self):
        with self.i.open(self.h) as snapshot:
            before = snapshot.manifest()
            event = self.h.evidence(b'Later independent evidence', source='O-D')
            self.assertEqual(before, snapshot.manifest())
            self.assertNotIn(event, [r['id'] for r in snapshot.page('events', offset=0, limit=128)['rows']])
        with self.i.open(self.h) as later:
            self.assertGreater(later.event_cutoff, before['event_cutoff'])

    def test_two_exports_are_complete_nonrecursive_and_live_growth_is_receipts_only(self):
        self.h.evidence(b'Large synthetic original-' * 20000, source='O-D')
        before = self.store._db.execute('SELECT COUNT(*) FROM payloads').fetchone()[0]
        paths = [self.path.parent / name for name in ('first.jsonl', 'second.jsonl')]
        for path in paths:
            with self.i.open(self.h) as snapshot:
                result = snapshot.export(path)
            self.assertEqual(result['digest'], verify_export(path)['digest'])
            self.assertEqual('AVAILABLE', self.i.copy_status(self.h, result['copy_id'], path))
        self.assertEqual(before, self.store._db.execute('SELECT COUNT(*) FROM payloads').fetchone()[0])
        a, b = (verify_export(path)['manifest'] for path in paths)
        self.assertEqual(a['tables']['blobs'], b['tables']['blobs'])
        self.assertGreater(b['tables']['inspection_receipts'], a['tables']['inspection_receipts'])
        self.assertLess(paths[1].stat().st_size - paths[0].stat().st_size, 5000)

    def test_missing_export_is_unavailable_without_losing_original_evidence(self):
        path = self.path.parent / 'export.jsonl'
        with self.i.open(self.h) as snapshot:
            result = snapshot.export(path)
        path.unlink()
        self.assertEqual('UNAVAILABLE', self.i.copy_status(self.h, result['copy_id'], path))
        self.assertEqual((), self.store.verify())

    def test_truncated_modified_exports_fail_verification(self):
        path = self.path.parent / 'export.jsonl'
        with self.i.open(self.h) as snapshot:
            snapshot.export(path)
        raw = path.read_bytes()
        path.write_bytes(raw[:len(raw)//2])
        with self.assertRaises(ValueError):
            verify_export(path)
        path.write_bytes(raw.replace(b'BICAMERAL_EXPORT_1', b'BICAMERAL_EXPORT_2', 1))
        with self.assertRaises(ValueError):
            verify_export(path)

    def test_failed_export_records_failure_without_success_or_overwrite(self):
        path = self.path.parent / 'existing.txt'
        path.write_bytes(b'User-owned data')
        with self.i.open(self.h) as snapshot:
            with self.assertRaises(FileExistsError):
                snapshot.export(path)
        self.assertEqual(b'User-owned data', path.read_bytes())
        self.assertEqual(['FAILED', 'INSPECTED'], [r[0] for r in self.store._db.execute('SELECT disposition FROM inspection_receipts')])
        self.assertEqual(0, self.store._db.execute('SELECT COUNT(*) FROM known_copies').fetchone()[0])

    def test_terminal_inspection_cannot_restart_and_old_blob_checks_removal(self):
        event = self.h.evidence(b'Synthetic removable inspection source', source='O-D')
        bid = self.store._db.execute('SELECT p.blob_id FROM events e JOIN payloads p ON p.id=e.payload_id WHERE e.id=?', (event,)).fetchone()[0]
        self.h.emergency_stop(reason='Synthetic terminal inspection', terminate=True, alternatives=['Stop'], unresolved_consequences=[])
        with self.i.open(self.h) as snapshot:
            self.assertTrue(snapshot.page('control_history', offset=0, limit=128)['rows'])
            with self.store._transaction('synthetic-p10-removal-probe'):
                self.store._write("UPDATE payloads SET disposition='REMOVED',blob_id=NULL WHERE blob_id=?", (bid,))
                self.store._write('DELETE FROM blobs WHERE id=?', (bid,))
            with self.assertRaises(EvidenceUnavailable):
                snapshot.blob(bid, offset=0, limit=10)
        self.assertEqual('TERMINATED', self.k.run()[1].status)
        with self.assertRaises(ValueError):
            self.h.confirm(self.h.run_control('RESUME', 'No restart').confirmation)
