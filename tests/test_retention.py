from hashlib import sha256
import sqlite3
import subprocess
import sys
from bicameral_agent.contracts.base import canonical_bytes
from bicameral_agent.kernel.authority import Kernel
from bicameral_agent.kernel.inputs import Inputs
from bicameral_agent.kernel.models import COMMAND
from bicameral_agent.kernel.retention import Retention, backup, recover_backup
from bicameral_agent.kernel.scheduler import Scheduler
from bicameral_agent.storage import Store, EvidenceUnavailable
from bicameral_agent.storage import StorageError
from bicameral_agent.storage.store import identifier
from tests.kernel_fixtures import KernelCase, HUMAN_KEY, CHAMBER_KEYS, kernel_configuration


class RetentionTests(KernelCase):
    def setUp(self):
        super().setUp()
        self.activate()
        self.marker = b'SYNTHETIC_PRIVATE_CONTENT_9f4321'
        event = self.h.evidence(self.marker, source='O-D')
        self.root = self.store._db.execute('SELECT payload_id FROM events WHERE id=?', (event,)).fetchone()[0]
        self.h.evidence(self.marker, source='O-D')
        proposal = self.proposal()
        proposal['continuity']['items'] = [{'kind': 'OBSERVATION', 'text': self.marker.decode(), 'evidence_event_ids': [event]}]
        self.correct(proposal)
        self.s = Scheduler(self.k)
        self.s.enqueue(self.h, b'Synthetic work')
        self.episode_id = self.s.open_next()
        self.inputs = Inputs(self.k)
        self.chamber = self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR'])
        self.query = canonical_bytes({'request_id': identifier(), 'query': {'kind': 'PAYLOAD', 'payload_id': self.root}, 'cursor': None})
        self.cached = self.inputs.retrieve(self.chamber, self.episode_id, self.query)
        call = self.s.begin_call('OPERATOR', self.episode_id)
        raw = canonical_bytes({'contract_version': '0.3.p01', 'request_id': call, 'run_id': self.run,
            'episode_id': self.episode_id, 'role': 'OPERATOR', 'message_type': 'OPERATOR_REPLY',
            'body': {'participation': None, 'task': {'outcome': 'COMPLETED', 'explanation': 'Synthetic result', 'evidence_event_ids': [event]}}})
        self.s.deliver(self.chamber, call, raw)
        self.copies = {}

    def export_and_backup(self):
        export_path = self.path.parent / 'evidence.jsonl'
        with self.h.inspect_snapshot() as snapshot:
            exported = snapshot.export(export_path)
        self.copies[exported['copy_id']] = export_path
        backup_path = self.path.parent / 'old.db'
        self.copies[backup(self.h, backup_path)] = backup_path
        return backup_path

    def request(self, *, terminal=False, objection=False):
        if terminal:
            self.h.emergency_stop(reason='Synthetic terminal removal', terminate=True, alternatives=['Stop'], unresolved_consequences=[])
        elif self.k.run()[1].status == 'ACTIVE':
            self.h.confirm(self.h.run_control('PAUSE', 'Review justified synthetic removal').confirmation)
        effects = {'kind': 'REMOVE_CONTENT', 'scope': 'SOURCE_AND_ALL_DERIVED_COPIES', 'payload_ids': [self.root],
            'copy_ids': list(self.copies), 'justification': 'PRIVACY', 'public_reason': 'Remove synthetic private material; preserve accountability'}
        targets = [{'record_type': 'RUN', 'record_id': self.run, 'expected_revision': self.k.run()[0]},
                   {'record_type': 'PAYLOAD', 'record_id': self.root, 'expected_revision': 1}]
        key = self.notice_effects(effects, kind='RETENTION', targets=targets, objection=objection)
        return effects | {'intervention_id': key}

    def authorize(self, **kwargs):
        command = self.request(**kwargs)
        display = self.h.preview(canonical_bytes(command))
        self.assertIn('Affected source/derived closure', display.text)
        return self.h.confirm(display.confirmation)['result']['decision_id']

    def maintenance(self):
        self.store.close()
        self.store = Store(self.path, busy_timeout_ms=100)
        self.k = Kernel(self.store, self.run, human_credential=HUMAN_KEY, chamber_credentials=CHAMBER_KEYS, maintenance=True)
        owner = self.store.removals.all(self.run)[0]['decision_maker_id']
        self.h = self.k.human(owner, HUMAN_KEY)

    def test_source_derived_cache_exports_backup_and_file_hashes_removed(self):
        self.export_and_backup()
        decision = self.authorize(terminal=True)
        with self.assertRaises(EvidenceUnavailable):
            self.store.read_payload(self.run, self.root)
        with self.assertRaises(EvidenceUnavailable):
            self.inputs.retrieve(self.chamber, self.episode_id, self.query)
        result = Retention.resume(self.store, decision, locations=self.copies)
        self.assertEqual('COMPLETED', result['status'])
        self.assertFalse(result['legacy_whole_run'])
        self.assertTrue(all(not path.exists() for path in self.copies.values()))
        self.assertEqual('STOPPED', result['continuation'])
        self.assertGreater(len(result['payload_ids']), 10)
        for path in self.path.parent.glob('store.db*'):
            content = path.read_bytes()
            self.assertNotIn(self.marker, content)
            self.assertNotIn(sha256(self.marker).hexdigest().encode(), content)
        self.maintenance()
        self.assertEqual('STOPPED', self.h.inspect()['execution'])
        with self.h.inspect_snapshot() as snapshot:
            rows = snapshot.page('payloads', offset=0, limit=128)['rows']
            self.assertEqual('REMOVED', next(r['disposition'] for r in rows if r['id'] == self.root))
        with self.assertRaises(ValueError):
            self.h.run_control('RESUME', 'Cannot revive removed evidence')

    def test_decision_survives_authorization_transaction_failure_and_restart(self):
        command = self.request()
        display = self.h.preview(canonical_bytes(command))
        def fail(point):
            if point == 'retention.after_decision':
                raise RuntimeError('Synthetic crash after independent decision')
        self.store._fault = fail
        with self.assertRaises(RuntimeError):
            self.h.confirm(display.confirmation)
        self.store._fault = lambda point: None
        self.assertEqual('IN_PROGRESS', self.store.removals.all(self.run)[0]['status'])
        with self.assertRaises(EvidenceUnavailable):
            self.store.read_payload(self.run, self.root)
        self.maintenance()
        result = Retention.resume(self.store, display.confirmation, locations={})
        self.assertEqual('COMPLETED', result['status'])

    def test_inaccessible_backup_and_old_snapshot_recovery_never_revive_content(self):
        old = self.export_and_backup()
        decision = self.authorize()
        export_only = {key: path for key, path in self.copies.items() if path.suffix == '.jsonl'}
        result = Retention.resume(self.store, decision, locations=export_only)
        self.assertEqual('INCOMPLETE', result['status'])
        with self.assertRaises(StorageError):
            Store(old, busy_timeout_ms=100)
        restored_path = self.path.parent / 'recovered.db'
        with recover_backup(old, restored_path, current_removal_journal=self.store.removals.path, busy_timeout_ms=100) as recovered:
            with self.assertRaises(EvidenceUnavailable):
                recovered.read_payload(self.run, self.root)
            self.assertEqual(self.run, recovered._db.execute('SELECT id FROM runs').fetchone()[0])
            self.assertNotIn(self.marker, restored_path.read_bytes())
        self.assertEqual('COMPLETED', Retention.resume(self.store, decision, locations=self.copies)['status'])

    def test_open_snapshot_and_interrupted_copy_cleanup_remain_blocked(self):
        self.export_and_backup()
        snapshot = self.h.inspect_snapshot()
        decision = self.authorize()
        with self.assertRaises(EvidenceUnavailable):
            snapshot.manifest()
        snapshot.close()
        def fail(point):
            if point == 'retention.after_copy_overwrite':
                raise RuntimeError('Synthetic crash after copy overwrite')
        self.store._fault = fail
        with self.assertRaises(RuntimeError):
            Retention.resume(self.store, decision, locations=self.copies)
        self.store._fault = lambda point: None
        self.maintenance()
        self.assertEqual('COMPLETED', Retention.resume(self.store, decision, locations=self.copies)['status'])

    def test_changed_review_unknown_scope_and_wrong_copy_reject(self):
        self.export_and_backup()
        command = self.request()
        with self.assertRaises(ValueError):
            COMMAND.validate_json(canonical_bytes(command | {'erase_everything': True}), strict=True)
        changed = command | {'public_reason': 'Different reviewed effects'}
        with self.assertRaises(ValueError):
            self.command(changed)
        self.assertEqual([], self.store.removals.all())
        decision = self.command(command)['decision_id']
        unrelated = self.path.parent / 'unrelated.jsonl'
        unrelated.write_bytes(b'{"copy_id":"unrelated"}\n')
        with self.assertRaises(ValueError):
            Retention.resume(self.store, decision, locations={next(iter(self.copies)): unrelated})
        self.assertEqual(b'{"copy_id":"unrelated"}\n', unrelated.read_bytes())

    def test_dormant_state_is_retained_until_explicit_disposition(self):
        self.h.confirm(self.h.run_control('PAUSE', 'Dormant with retained state').confirmation)
        self.assertEqual(self.marker, self.store.read_payload(self.run, self.root))
        self.assertEqual([], self.store.removals.all())
        decision = self.authorize()
        self.assertEqual('PAUSED', self.store.removals.all()[0]['previous_run_status'])
        self.assertEqual('COMPLETED', Retention.resume(self.store, decision, locations={})['status'])

    def test_compaction_waits_for_old_reader(self):
        # A retained reader holds old SQLite pages; logical blocking precedes
        # physical cleanup and the status must remain incomplete meanwhile.
        reader = self.h.inspect_snapshot()
        decision = self.authorize()
        result = Retention.resume(self.store, decision, locations={})
        self.assertEqual('INCOMPLETE', result['status'])
        self.assertFalse(result['file_compaction_verified'])
        reader.close()
        self.assertEqual('COMPLETED', Retention.resume(self.store, decision, locations={})['status'])

    def test_shared_content_in_another_run_prevents_false_completion(self):
        config, artifacts = kernel_configuration('B')
        other = self.store.retain_configuration(canonical_bytes(config), artifacts)
        event = self.store.record_evidence(other, self.marker, role='HUMAN', source='O-D', visibility='CHAMBER')
        pid = self.store._db.execute('SELECT payload_id FROM events WHERE id=?', (event,)).fetchone()[0]
        decision = self.authorize()
        result = Retention.resume(self.store, decision, locations={})
        self.assertEqual('INCOMPLETE', result['status'])
        self.assertIn({'run_id': other, 'id': pid}, result['shared_payloads'])
        self.assertEqual(self.marker, self.store.read_payload(other, pid))

    def test_legacy_missing_lineage_requires_visible_conservative_scope(self):
        with self.store._transaction('synthetic-legacy-provenance'):
            self.store._write('DELETE FROM payload_lineage WHERE run_id=? AND payload_id=?', (self.run, self.root))
        command = self.request()
        display = self.h.preview(canonical_bytes(command))
        self.assertIn('"legacy_whole_run":true', display.text)
        decision = self.h.confirm(display.confirmation)['result']['decision_id']
        self.assertTrue(Retention.resume(self.store, decision, locations={})['legacy_whole_run'])
        self.maintenance()
        self.assertEqual('STOPPED', self.h.inspect()['execution'])

    def test_actual_process_exit_after_decision_blocks_bytes_before_recovery(self):
        command = self.request()
        script = '''
import os, sys
from bicameral_agent.storage import Store
from bicameral_agent.kernel.authority import Kernel
from tests.kernel_fixtures import HUMAN_KEY, CHAMBER_KEYS
store=Store(sys.argv[1],busy_timeout_ms=100)
k=Kernel(store,sys.argv[2],human_credential=HUMAN_KEY,chamber_credentials=CHAMBER_KEYS)
h=k.human(k.config.responsible_human_id,HUMAN_KEY)
display=h.preview(sys.argv[3].encode())
store._fault=lambda point: os._exit(77) if point=='retention.after_decision' else None
h.confirm(display.confirmation)
'''
        child = subprocess.run([sys.executable, '-B', '-c', script, str(self.path), self.run, canonical_bytes(command).decode()],
                               capture_output=True, timeout=30)
        self.assertEqual(77, child.returncode, child.stderr.decode())
        with self.assertRaises(EvidenceUnavailable):
            self.store.read_payload(self.run, self.root)
        self.maintenance()
        decision = self.store.removals.all(self.run)[0]['id']
        self.assertEqual('COMPLETED', Retention.resume(self.store, decision, locations={})['status'])
