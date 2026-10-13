from hashlib import sha256
import sqlite3
import subprocess
import sys
from bicameral_agent.contracts.base import canonical_bytes, load_json
from bicameral_agent.kernel.authority import Kernel
from bicameral_agent.kernel.inputs import Inputs
from bicameral_agent.kernel.models import COMMAND
from bicameral_agent.kernel.retention import Retention, backup, recover_backup
from bicameral_agent.kernel.scheduler import Scheduler
from bicameral_agent.storage import Store, EvidenceUnavailable
from bicameral_agent.storage import StorageError
from bicameral_agent.storage.store import identifier
from bicameral_agent.storage.retention import closure
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
        paths = list(self.path.parent.glob(self.path.name + '*'))
        self.assertIn(self.path, paths)
        for path in paths:
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

    def response_removal(self, *, invalid_route=False, crash=False):
        attempt = self.s.begin_attempt(self.episode_id)
        key = self.s.begin_call('STEWARD', self.episode_id, attempt_id=attempt)
        call = self.s.invocation(key)
        self.assertIn(self.marker, self.store.read_payload(self.run, call.input_payload_id))
        if crash:
            raw = canonical_bytes({'contract_version': '0.3.p01', 'request_id': key, 'run_id': self.run,
                'episode_id': self.episode_id, 'role': 'STEWARD', 'message_type': 'STEWARD_REPLY',
                'body': {'participation': None, 'task': self.proposal() | {'mutations': self.marker.decode()}}})
            def fail(point):
                if point == 'report.after_commit':
                    raise RuntimeError('Synthetic failure before scheduler retains output')
            self.store._fault = fail
        elif invalid_route:
            raw = canonical_bytes({'contract_version': '0.3.p01', 'request_id': key, 'run_id': identifier(),
                'episode_id': self.episode_id, 'role': 'STEWARD', 'message_type': 'STEWARD_REPLY',
                'body': {'participation': None, 'task': {'private_copy': self.marker.decode()}}})
        else:
            raw = b'wrapped malformed response: ' + self.marker
            self.s.interrupt_call(key, reason='SYNTHETIC_DEADLINE')
        chamber = self.k.chamber('STEWARD', CHAMBER_KEYS['STEWARD'])
        if crash:
            with self.assertRaisesRegex(RuntimeError, 'Synthetic failure'):
                self.s.deliver(chamber, key, raw)
            self.reopen(); self.s = Scheduler(self.k)
            self.assertIsNone(self.s.invocation(key).output_payload_id)
        else:
            result = self.s.deliver(chamber, key, raw)
            self.assertEqual('REJECTED' if invalid_route else 'LATE', result['status'])
        request = self.store._request(self.run, 'STEWARD', key)
        self.assertIsNotNone(request)
        raw_id = request['request_payload_id']
        receipt = load_json(self.store.read_payload(self.run, request['response_payload_id']))
        diagnostic = receipt['diagnostics']['payload_id']
        if crash:
            self.assertIn(self.marker, self.store.read_payload(self.run, diagnostic))
        plan = closure(self.store, self.run, [self.root])
        self.assertFalse(plan['legacy_whole_run'])
        self.assertIn(raw_id, plan['payload_ids'])
        self.assertIn(diagnostic, plan['payload_ids'])
        decision = self.authorize()
        result = Retention.resume(self.store, decision, locations={})
        self.assertEqual('COMPLETED', result['status'])
        for pid in (raw_id, diagnostic):
            with self.assertRaises(EvidenceUnavailable):
                self.store.read_payload(self.run, pid)
        paths = list(self.path.parent.glob(self.path.name + '*'))
        self.assertIn(self.path, paths)
        for path in paths:
            content = path.read_bytes()
            for material in (self.marker, sha256(self.marker).hexdigest().encode(), sha256(raw).hexdigest().encode()):
                self.assertNotIn(material, content)

    def test_late_malformed_response_is_removed_with_its_input(self):
        self.response_removal()

    def test_invalid_route_response_is_removed_with_its_input(self):
        self.response_removal(invalid_route=True)

    def test_first_report_commit_retains_raw_and_diagnostic_lineage_before_crash(self):
        self.response_removal(crash=True)

    def test_artifact_removal_includes_configuration_digest(self):
        self.root = self.store._db.execute("SELECT payload_id FROM artifacts WHERE run_id=? AND name='scripted_messages'",
            (self.run,)).fetchone()[0]
        material = self.store.read_payload(self.run, self.root)
        configuration = self.store._db.execute('SELECT configuration_id FROM runs WHERE id=?', (self.run,)).fetchone()[0]
        self.assertIn(configuration, closure(self.store, self.run, [self.root])['payload_ids'])
        decision = self.authorize()
        result = Retention.resume(self.store, decision, locations={})
        self.assertEqual('COMPLETED', result['status'])
        self.assertFalse(result['legacy_whole_run'])
        paths = list(self.path.parent.glob(self.path.name + '*'))
        self.assertIn(self.path, paths)
        for path in paths:
            self.assertNotIn(sha256(material).hexdigest().encode(), path.read_bytes())

    def test_upgrade_invalidates_historical_incomplete_lineage(self):
        from unittest.mock import patch
        from bicameral_agent.storage.migrations import MIGRATIONS
        old_path = self.path.parent / 'released.db'
        # Versions 1-7 are released history; they falsely marked missing edges complete.
        with patch('bicameral_agent.storage.store.MIGRATIONS', MIGRATIONS[:7]):
            with Store(old_path, busy_timeout_ms=100) as old:
                config, artifacts = kernel_configuration()
                run = old.retain_configuration(canonical_bytes(config), artifacts)
                root = old._db.execute('SELECT payload_id FROM artifacts WHERE run_id=? LIMIT 1', (run,)).fetchone()[0]
                with old._transaction('released-missing-edges'):
                    old._write('DELETE FROM derived_payloads WHERE run_id=?', (run,))
                self.assertFalse(closure(old, run, [root])['legacy_whole_run'])
        with Store(old_path, busy_timeout_ms=100) as upgraded:
            plan = closure(upgraded, run, [root])
            self.assertTrue(plan['legacy_whole_run'])
            all_payloads = {r[0] for r in upgraded._db.execute('SELECT id FROM payloads WHERE run_id=?', (run,))}
            self.assertEqual(all_payloads, set(plan['payload_ids']))

    def test_upgrade_blocks_omitted_derivatives_from_previously_completed_removal(self):
        # Reproduce a v7 decision: every payload claims complete lineage, but a
        # wrapped response is missing its source edge and is left out of scope.
        with self.store._transaction('released-removal-fixture'):
            omitted = self.store._payload(self.run, b'legacy wrapped response: ' + self.marker)
            self.store._write('DELETE FROM migrations WHERE version>7')
        decision = self.authorize()
        original = Retention.resume(self.store, decision, locations={})
        self.assertEqual('COMPLETED', original['status'])
        self.assertNotIn(omitted, original['payload_ids'])
        self.assertIn(self.marker, self.store.read_payload(self.run, omitted))
        self.maintenance()
        updated = self.store.removals.all(self.run)[0]
        self.assertEqual('INCOMPLETE', updated['status'])
        self.assertTrue(updated['scope_review_required'])
        self.assertEqual(original['payload_ids'], updated['payload_ids'])
        with self.assertRaises(EvidenceUnavailable):
            self.store.read_payload(self.run, omitted)
        result = Retention.resume(self.store, decision, locations={})
        self.assertEqual('INCOMPLETE', result['status'])
        self.assertEqual(original['payload_ids'], result['payload_ids'])
        # Blocking access must not silently expand the human-approved deletion.
        self.assertEqual('RETAINED', self.store._db.execute('SELECT disposition FROM payloads WHERE id=?',
            (omitted,)).fetchone()[0])
        with self.h.inspect_snapshot() as snapshot:
            with self.assertRaises(EvidenceUnavailable):
                snapshot.page('blobs', offset=0, limit=128)
        self.maintenance()
        with self.assertRaises(EvidenceUnavailable):
            self.store.read_payload(self.run, omitted)

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

    def test_welfare_hold_preserves_separately_reviewed_removal_path(self):
        self.report({'kind': 'WITHDRAW', 'activity_id': self.objective,
            'communication': 'NO_FURTHER_CALLS', 'text': 'Keep optional work stopped'})
        decision = self.authorize()
        result = Retention.resume(self.store, decision, locations={})
        self.assertEqual('COMPLETED', result['status'])
        self.assertEqual('STOPPED', result['continuation'])

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
