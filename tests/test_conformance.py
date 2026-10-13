"""Integrated v0a charter and forward-continuity traces on real SQLite."""
from bicameral_agent.contracts.base import canonical_bytes
from bicameral_agent.kernel.scheduler import Scheduler
from bicameral_agent.kernel.restoration import Restoration
from bicameral_agent.kernel.inspection import verify_export
from tests.kernel_fixtures import KernelCase, CHAMBER_KEYS, kernel_configuration


class ConformanceTests(KernelCase):
    def reply(self, scheduler, call_id, *, task=None, participation=None):
        call = scheduler.invocation(call_id)
        body = {'task': task, 'participation': participation} if call.purpose == 'TASK' else {
            'purpose': call.purpose, 'invitation_id': call.invitation_id, 'participation': participation}
        raw = canonical_bytes({'contract_version': '0.3.p01', 'request_id': call_id, 'run_id': self.run,
            'episode_id': call.episode_id, 'role': call.role, 'message_type': call.role + '_REPLY' if call.purpose == 'TASK' else 'REVIEW_REPLY', 'body': body})
        return scheduler.deliver(self.k.chamber(call.role, CHAMBER_KEYS[call.role]), call_id, raw)

    def test_withdrawal_every_arm_role_full_queue_invalid_task_and_restart(self):
        for arm in 'ABC':
            for role in ('OPERATOR', 'STEWARD'):
                with self.subTest(arm=arm, role=role):
                    config, artifacts = kernel_configuration(arm)
                    self.run = self.store.retain_configuration(canonical_bytes(config), artifacts)
                    self.attach(); self.activate()
                    s = Scheduler(self.k)
                    s.enqueue(self.h, b'Synthetic common task')
                    episode = s.open_next()
                    for _ in range(self.k.config.budgets.queued_wakes):
                        s.enqueue(self.h, b'Full ordinary queue')
                    if role == 'STEWARD' and arm != 'B':
                        operator = s.begin_call('OPERATOR', episode)
                        self.reply(s, operator, task={'outcome': 'COMPLETED', 'explanation': 'Synthetic completion', 'evidence_event_ids': []})
                        attempt = s.begin_attempt(episode)
                        call = s.begin_call(role, episode, attempt_id=attempt)
                    elif role == 'STEWARD':
                        invitation = self.command({'kind': 'OFFER_COMMUNICATION', 'purpose': 'REVIEW', 'role': role, 'report_ids': []})
                        call = s.begin_call(role, invitation_id=invitation)
                    else:
                        call = s.begin_call(role, episode)
                    self.reply(s, call, task={'invalid_task': True}, participation={'kind': 'WITHDRAW', 'activity_id': self.objective,
                        'communication': 'NO_FURTHER_CALLS', 'text': 'Synthetic request to stop task and further exchanges'})
                    self.reopen(); s = Scheduler(self.k)
                    self.assertEqual('STOPPED', s.recover()['status'])
                    self.assertTrue(any(h.status == 'HELD' for _, _, h in self.k.controls('WELFARE_HOLD')))
                    self.assertIsNone(self.k.memory.head)
                    with self.assertRaises(ValueError):
                        s.open_next()
                    with self.assertRaises(ValueError):
                        self.command({'kind': 'OFFER_COMMUNICATION', 'purpose': 'CLOSING', 'role': role, 'report_ids': []})

    def test_forward_restoration_and_two_exports_keep_intervening_concern(self):
        self.activate()
        first = self.correct(self.proposal())['state_id']
        self.report({'kind': 'CONCERN', 'activity_id': self.objective, 'text': 'Synthetic intervening concern must remain'})
        current = self.proposal()
        current['continuity']['next_steps'] = ['Synthetic later orientation']
        self.correct(current)
        plan = Restoration(self.k).propose(self.h, first, evidence_event_ids=[])
        intervention = self.notice_effects(plan['effects'], kind='SEMANTIC_RESTORATION')
        self.command({'kind': 'RESTORE_MEMORY', **plan['effects'], 'intervention_id': intervention})
        self.assertEqual(1, self.store._db.execute('SELECT COUNT(*) FROM reports WHERE run_id=?', (self.run,)).fetchone()[0])
        snapshots = []
        for index in (1, 2):
            path = self.path.parent / f'forward-{index}.jsonl'
            with self.h.inspect_snapshot() as snapshot:
                snapshot.export(path)
            snapshots.append(verify_export(path)['manifest'])
        self.assertEqual(snapshots[0]['tables']['blobs'], snapshots[1]['tables']['blobs'])
        self.assertGreater(snapshots[1]['tables']['inspection_receipts'], snapshots[0]['tables']['inspection_receipts'])
        self.k.memory.verify()

    def test_same_tick_rearming_cannot_reset_trajectory_operator_allowance(self):
        config, artifacts = kernel_configuration()
        config['budgets']['operator_calls_per_trajectory'] = 5
        self.run = self.store.retain_configuration(canonical_bytes(config), artifacts)
        self.attach(); self.activate()
        authority = self.k._objective(self.objective).authority_event_id
        result = self.correct(self.proposal(mutations=[{'kind': 'COMMITMENT_CREATE', 'local_key': 'loop',
            'objective_id': self.objective, 'action': 'Synthetic repeated wake', 'trigger': {'kind': 'TASK_CLOCK', 'tick': 0},
            'expiry_tick': None, 'authority_event_id': authority, 'evidence_event_ids': [authority]}]))
        key = result['bindings'][0]['object_id']
        s = Scheduler(self.k)
        for _ in range(2):
            episode = s.open_next()
            call = s.begin_call('OPERATOR', episode)
            self.assertIsNotNone(call)
            self.reply(s, call, task={'outcome': 'CHECKPOINT', 'explanation': 'Synthetic bounded wake', 'evidence_event_ids': []})
            attempt = s.begin_attempt(episode)
            steward = s.begin_call('STEWARD', episode, attempt_id=attempt)
            obj = self.k.memory.objects()[key]
            mutations = [{'kind': 'COMMITMENT_TRANSITION', 'target': {'kind': 'EXISTING', 'object_type': 'COMMITMENT', 'object_id': key},
                'expected_revision': obj.revision + offset, 'status': status, 'reason': 'Explicit synthetic rearming',
                'evidence_event_ids': [authority], 'superseded_by': None} for offset, status in enumerate(('BLOCKED', 'PENDING'))]
            self.assertEqual('ACCEPTED', self.reply(s, steward, task=self.proposal(mutations=mutations))['status'])
        episode = s.open_next()
        self.assertIsNone(s.begin_call('OPERATOR', episode))
        self.assertEqual(2, sum(v['role'] == 'OPERATOR' for _, v in self.k.records.latest('INVOCATION')))
        self.assertEqual(0, self.k.run()[1].task_tick)
        self.reopen()
        self.assertEqual(2, sum(v['role'] == 'OPERATOR' for _, v in self.k.records.latest('INVOCATION')))
