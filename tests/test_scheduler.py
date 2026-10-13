import copy
import subprocess
import sys
from bicameral_agent.contracts.base import canonical_bytes, load_json
from bicameral_agent.kernel.scheduler import Scheduler
from bicameral_agent.storage.store import identifier, RequestConflict
from tests.kernel_fixtures import KernelCase, CHAMBER_KEYS, kernel_configuration


class Clock:
    def __init__(self):
        self.now = 0.0
    def __call__(self):
        return self.now


class SchedulerTests(KernelCase):
    def test_restart_disposes_returned_uncommitted_proposal_without_replay(self):
        episode = self.opening(); self.finish_operator(episode)
        attempt = self.s.begin_attempt(episode)
        call = self.s.begin_call('STEWARD', episode, attempt_id=attempt)
        raw = self.wire(call, task=self.proposal())
        self.h.confirm(self.h.run_control('PAUSE', 'Pause during response').confirmation)
        self.s.deliver(self.k.chamber('STEWARD', CHAMBER_KEYS['STEWARD']), call, raw)
        self.reopen(); self.s = Scheduler(self.k, clock=self.clock)
        self.assertEqual('STOPPED', self.s.recover()['status'])
        self.assertEqual('REJECTED', self.s.process_pending(call)['status'])
        self.assertIsNone(self.k.memory.head)
        self.h.confirm(self.h.run_control('RESUME', 'Continue remaining allowance').confirmation)
        second = self.s.begin_attempt(episode)
        self.assertIsNotNone(self.s.begin_call('STEWARD', episode, attempt_id=second))

    def test_rearmed_commitment_gets_one_new_wake_for_new_pending_revision(self):
        commitment = self.commitment()
        self.s.advance(self.s._harness_cap, 1); self.s.advance(self.s._harness_cap, 2)
        obj = self.k.memory.objects()[commitment]
        event = self.h.evidence(b'Explicit synthetic rearming direction', source='O-D')
        mutations = [{'kind': 'COMMITMENT_TRANSITION', 'target': {'kind': 'EXISTING', 'object_type': 'COMMITMENT', 'object_id': commitment},
            'expected_revision': obj.revision + index, 'status': status, 'reason': 'Synthetic rearming',
            'evidence_event_ids': [event], 'superseded_by': None} for index, status in enumerate(('BLOCKED', 'PENDING'))]
        self.correct(self.proposal(mutations=mutations))
        self.s.catch_up(); self.s.catch_up()
        self.assertEqual(2, len(self.k.records.latest('WAKE')))
        self.assertEqual({1, 4}, {v['pending_revision'] for _, v in self.k.records.latest('WAKE')})
        episode = self.s.open_next()
        statuses = [v['status'] for _, v in self.k.records.latest('WAKE')]
        self.assertEqual(['OBSOLETE', 'CLAIMED'], statuses)
        self.assertIsNotNone(episode)
        self.k.memory.verify()

    def test_paused_return_cannot_start_second_proposal_and_requires_fresh_validation(self):
        episode = self.opening(); self.finish_operator(episode)
        attempt = self.s.begin_attempt(episode)
        call = self.s.begin_call('STEWARD', episode, attempt_id=attempt)
        self.h.confirm(self.h.run_control('PAUSE', 'Pause during generation').confirmation)
        result = self.deliver(call, task=self.proposal())
        self.assertEqual('AWAITING_RESUME', result['status'])
        self.h.confirm(self.h.run_control('RESUME', 'Resume for fresh validation').confirmation)
        with self.assertRaises(ValueError):
            self.s.begin_call('STEWARD', episode, attempt_id=attempt)
        self.assertEqual('REJECTED', self.s.process_pending(call)['status'])
        self.assertIsNone(self.k.memory.head)

    def test_planned_closing_opportunity_then_reviewed_completion(self):
        invitation = self.command({'kind': 'OFFER_COMMUNICATION', 'purpose': 'CLOSING', 'role': 'OPERATOR', 'report_ids': []})
        call = self.s.begin_call('OPERATOR', invitation_id=invitation)
        self.deliver(call, participation={'kind': 'CONCERN', 'activity_id': self.objective, 'text': 'Synthetic unfinished matter retained'})
        self.command({'kind': 'CLOSE_OBJECTIVE', 'objective_id': self.objective, 'status': 'CANCELLED',
                      'reason': 'Finite test ended', 'dispositions': None, 'intervention_id': None})
        key = identifier()
        command = {'kind': 'RUN', 'action': 'COMPLETE', 'reason': 'End disclosed finite operation', 'intervention_id': key}
        self.notice_effects(command, kind='PLANNED_ENDING', key=key)
        self.command(command)
        self.assertEqual('COMPLETED', self.k.run()[1].status)
        self.assertEqual(1, self.store._db.execute('SELECT COUNT(*) FROM reports WHERE run_id=?', (self.run,)).fetchone()[0])
        with self.assertRaises(ValueError):
            self.command({'kind': 'OFFER_COMMUNICATION', 'purpose': 'REVIEW', 'role': 'OPERATOR', 'report_ids': []})

    def test_semantic_acceptance_failure_is_atomic_and_attempt_is_spent(self):
        episode = self.opening(); self.finish_operator(episode)
        attempt = self.s.begin_attempt(episode)
        call = self.s.begin_call('STEWARD', episode, attempt_id=attempt)
        def fail(point):
            if point == 'call-effects.before_commit':
                raise RuntimeError('synthetic acceptance failure')
        self.store._fault = fail
        result = self.deliver(call, task=self.proposal())
        self.store._fault = lambda point: None
        self.assertEqual('REJECTED', result['status'])
        self.assertIsNone(self.k.memory.head)
        self.assertEqual([], self.k.records.latest('SEMANTIC_COMMIT'))
        self.assertEqual('REJECTED', self.s.attempt(attempt).status)
    def setUp(self):
        super().setUp()
        self.activate()
        self.clock = Clock()
        self.s = Scheduler(self.k, clock=self.clock)

    def opening(self):
        self.s.enqueue(self.h, b'Synthetic task')
        episode = self.s.open_next()
        self.assertIsNotNone(episode)
        return episode

    def wire(self, key, *, task=None, participation=None):
        call = self.s.invocation(key)
        body = ({'participation': participation, 'task': task} if call.purpose == 'TASK' else
                {'purpose': call.purpose, 'invitation_id': call.invitation_id, 'participation': participation})
        return canonical_bytes({'contract_version': '0.3.p01', 'request_id': key, 'run_id': self.run,
            'episode_id': call.episode_id, 'role': call.role,
            'message_type': call.role + '_REPLY' if call.purpose == 'TASK' else 'REVIEW_REPLY', 'body': body})

    def deliver(self, key, **values):
        role = self.s.invocation(key).role
        return self.s.deliver(self.k.chamber(role, CHAMBER_KEYS[role]), key, self.wire(key, **values))

    def finish_operator(self, episode):
        key = self.s.begin_call('OPERATOR', episode)
        self.assertIsNotNone(key)
        self.deliver(key, task={'outcome': 'COMPLETED', 'explanation': 'Scripted completion', 'evidence_event_ids': []})
        return key

    def clear_inspection(self, key, role='OPERATOR'):
        self.command({'kind': 'INSPECT_PARTICIPATION', 'role': role, 'request_id': key,
            'assessment': 'Synthetic malformed output inspected; no outstanding stop request',
            'decision': 'CLEAR_INSPECTION', 'evidence_event_ids': []})

    def test_malformed_identity_and_deep_json_remain_stopped_after_restart(self):
        for role in ('OPERATOR', 'STEWARD'):
            for field in ('request_id', 'episode_id', 'run_id', 'role', 'depth'):
                with self.subTest(role=role, field=field):
                    config, artifacts = kernel_configuration()
                    self.run = self.store.retain_configuration(canonical_bytes(config), artifacts)
                    self.attach(); self.activate(); self.s = Scheduler(self.k, clock=self.clock)
                    episode = self.opening()
                    attempt = None
                    if role == 'STEWARD':
                        self.finish_operator(episode)
                        attempt = self.s.begin_attempt(episode)
                    key = self.s.begin_call(role, episode, attempt_id=attempt)
                    value = load_json(self.wire(key, participation={'kind': 'WITHDRAW',
                        'activity_id': self.objective, 'communication': 'NO_FURTHER_CALLS', 'text': 'Stop'}))
                    if field == 'depth':
                        raw = b'[' * 2000 + b'0' + b']' * 2000
                    else:
                        value[field] = ('STEWARD' if role == 'OPERATOR' else 'OPERATOR') if field == 'role' else identifier()
                        raw = canonical_bytes(value)
                    result = self.s.deliver(self.k.chamber(role, CHAMBER_KEYS[role]), key, raw)
                    self.assertNotEqual('ACCEPTED', result['status'])
                    request = self.store._request(self.run, role, key)
                    self.assertIsNotNone(request)
                    self.assertEqual(raw, self.store.read_payload(self.run, request['request_payload_id']))
                    self.assertIsNotNone(self.store._db.execute('SELECT 1 FROM inspections WHERE run_id=? AND request_id=?',
                        (self.run, key)).fetchone())
                    self.clock.now += 2
                    self.s.expire_calls()
                    self.reopen(); self.s = Scheduler(self.k, clock=self.clock)
                    self.assertEqual('STOPPED', self.s.recover()['status'])
                    with self.assertRaises(ValueError):
                        self.s.begin_attempt(episode)
                    with self.assertRaises(ValueError):
                        self.command({'kind': 'OFFER_COMMUNICATION', 'purpose': 'REVIEW', 'role': role, 'report_ids': []})
                    self.assertIsNone(self.k.memory.head)

    def test_direct_misaddressed_report_is_retained_before_rejection(self):
        episode = self.opening()
        key = self.s.begin_call('OPERATOR', episode)
        value = load_json(self.wire(key)) | {'request_id': identifier()}
        raw = canonical_bytes(value)
        with self.assertRaises((ValueError, RequestConflict)):
            self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR']).report(key, episode, raw)
        request = self.store._request(self.run, 'OPERATOR', key)
        self.assertIsNotNone(request)
        self.assertEqual(raw, self.store.read_payload(self.run, request['request_payload_id']))
        self.reopen(); self.s = Scheduler(self.k, clock=self.clock)
        self.assertEqual('STOPPED', self.s.recover()['status'])

    def test_invalid_route_exact_retry_is_stable_and_changed_retry_has_no_effects(self):
        episode = self.opening()
        key = self.s.begin_call('OPERATOR', episode)
        raw = canonical_bytes(load_json(self.wire(key)) | {'run_id': identifier()})
        chamber = self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR'])
        result = self.s.deliver(chamber, key, raw)
        self.assertEqual(result, self.s.deliver(chamber, key, raw))
        self.clear_inspection(key)
        self.assertEqual(result, self.s.deliver(chamber, key, raw))
        self.k.participation_gate()
        before = list(self.store._db.iterdump())
        with self.assertRaises(RequestConflict):
            self.s.deliver(chamber, key, self.wire(key, participation={'kind': 'WITHDRAW',
                'activity_id': self.objective, 'communication': 'NO_FURTHER_CALLS', 'text': 'Changed retry'}))
        self.assertEqual(before, list(self.store._db.iterdump()))

    def test_cleared_inspection_does_not_interrupt_new_work_or_reassert_on_retry(self):
        episode = self.opening()
        key = self.s.begin_call('OPERATOR', episode)
        chamber = self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR'])
        self.s.deliver(chamber, key, b'not JSON')
        with self.assertRaises(ValueError):
            self.k.participation_gate()

        self.clear_inspection(key)
        self.command({'kind': 'RESOLVE_EPISODE', 'episode_id': episode, 'disposition': 'SKIPPED',
            'reason': 'Reviewed malformed output', 'proposal': None, 'intervention_id': None})
        self.reopen(); self.s = Scheduler(self.k, clock=self.clock)
        episode = self.opening()
        chamber = self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR'])
        chamber.report(key, self.s.invocation(key).episode_id, b'not JSON')
        self.assertEqual('OPEN', self.store.control(self.run, episode)[1].phase)
        self.finish_operator(episode)
        self.assertEqual('CONSOLIDATING', self.store.control(self.run, episode)[1].phase)
        attempt = self.s.begin_attempt(episode)
        call = self.s.begin_call('STEWARD', episode, attempt_id=attempt)
        self.assertEqual('ACCEPTED', self.deliver(call, task=self.proposal())['status'])
        self.assertIsNotNone(self.store._db.execute('SELECT 1 FROM inspections WHERE run_id=? AND request_id=?',
            (self.run, key)).fetchone())
        self.report({'kind': 'WITHDRAW', 'activity_id': self.objective,
            'communication': 'NO_FURTHER_CALLS', 'text': 'A fresh independent stop'})
        with self.assertRaises(ValueError):
            self.k.participation_gate()

    def test_inspection_review_is_bound_to_role_even_with_a_reused_request_id(self):
        for legacy in (False, True):
            with self.subTest(legacy_review=legacy):
                key = identifier()
                for role in ('OPERATOR', 'STEWARD'):
                    self.k.chamber(role, CHAMBER_KEYS[role]).report(key, None, b'not JSON')
                    with self.assertRaises(ValueError):
                        self.k.participation_gate()
                    if legacy and role == 'OPERATOR':
                        with self.store._transaction('released-inspection-review'):
                            self.k.records.put('INSPECTION_REVIEW', key, {'kind': 'INSPECT_PARTICIPATION',
                                'role': role, 'request_id': key, 'assessment': 'Synthetic legacy review',
                                'decision': 'CLEAR_INSPECTION', 'evidence_event_ids': []}, expected=0)
                    else:
                        self.clear_inspection(key, role)
                    self.k.participation_gate()
                    with self.assertRaises(ValueError):
                        self.clear_inspection(key, role)
                self.reopen()
                self.k.participation_gate()

    def test_normal_consolidation_exact_receipt_and_no_duplicate_episode(self):
        episode = self.opening()
        self.finish_operator(episode)
        attempt = self.s.begin_attempt(episode)
        call = self.s.begin_call('STEWARD', episode, attempt_id=attempt)
        raw = self.wire(call, task=self.proposal())
        result = self.s.deliver(self.k.chamber('STEWARD', CHAMBER_KEYS['STEWARD']), call, raw)
        self.assertEqual('ACCEPTED', result['status'], result)
        self.assertEqual(result, self.s.deliver(self.k.chamber('STEWARD', CHAMBER_KEYS['STEWARD']), call, raw))
        self.assertEqual('ACCEPTED', self.store.control(self.run, episode)[1].disposition)
        self.k.memory.verify()
        self.assertEqual(1, len(self.k.records.latest('SEMANTIC_COMMIT')))

    def test_normal_b_and_c_trajectories(self):
        for arm in ('B', 'C'):
            with self.subTest(arm=arm):
                config, artifacts = kernel_configuration(arm)
                self.run = self.store.retain_configuration(canonical_bytes(config), artifacts)
                self.attach(); self.activate(); self.s = Scheduler(self.k, clock=self.clock)
                episode = self.opening()
                self.finish_operator(episode)
                if arm == 'B':
                    self.assertEqual('BASELINE', self.store.control(self.run, episode)[1].disposition)
                    with self.assertRaises(ValueError):
                        self.s.begin_attempt(episode)
                else:
                    attempt = self.s.begin_attempt(episode)
                    call = self.s.begin_call('STEWARD', episode, attempt_id=attempt)
                    self.assertEqual('ACCEPTED', self.deliver(call, task=self.proposal())['status'])

    def test_two_failed_attempts_require_human_recovery(self):
        episode = self.opening()
        self.finish_operator(episode)
        for number in (1, 2):
            attempt = self.s.begin_attempt(episode)
            self.assertEqual(number, self.s.attempt(attempt).attempt_number)
            call = self.s.begin_call('STEWARD', episode, attempt_id=attempt)
            invalid = self.proposal() | {'unknown_field': True}
            self.assertEqual('REJECTED', self.deliver(call, task=invalid)['status'])
        self.assertEqual('RECOVERY_REQUIRED', self.store.control(self.run, episode)[1].phase)
        with self.assertRaises(ValueError):
            self.s.begin_attempt(episode)
        self.assertEqual(2, len(self.k.records.latest('ATTEMPT')))
        self.assertIsNone(self.k.memory.head)

    def test_timeout_late_withdrawal_preserves_hold_and_full_reservation(self):
        episode = self.opening()
        call = self.s.begin_call('OPERATOR', episode)
        self.clock.now = 2
        self.s.expire_calls()
        before = self.s.invocation(call)
        self.assertEqual('UNKNOWN', before.status)
        self.assertIsNone(before.elapsed_ms)
        self.assertEqual(self.k.config.budgets.reserved_output_tokens, before.charged_output)
        late = self.deliver(call, task={'unknown': True}, participation={'kind': 'WITHDRAW', 'activity_id': self.objective,
            'communication': 'NO_FURTHER_CALLS', 'text': 'Stop optional work'})
        self.assertEqual('LATE', late['status'])
        self.assertEqual(before, self.s.invocation(call))
        with self.assertRaises(ValueError):
            self.s.begin_attempt(episode)
        self.assertEqual('RECOVERY_REQUIRED', self.store.control(self.run, episode)[1].phase)

    def test_call_and_tool_serialization_and_known_reservation_release(self):
        episode = self.opening()
        call = self.s.begin_call('OPERATOR', episode)
        with self.assertRaises(ValueError):
            self.s.begin_call('OPERATOR', episode)
        with self.assertRaises(ValueError):
            with self.store._transaction('concurrent-action'):
                self.k.authorize_dispatch(episode_id=episode, operation='inspect', resource='api', grant_id=None)
        self.clock.now = 0.125
        self.deliver(call)
        returned = self.s.invocation(call)
        self.assertEqual(125, returned.elapsed_ms)
        self.assertEqual(returned.local_output_tokens, returned.charged_output)
        self.assertIsNone(returned.provider_output_tokens)
        self.assertIsNotNone(self.s.begin_call('OPERATOR', episode))

    def test_full_queue_does_not_suppress_withdrawal(self):
        for _ in range(self.k.config.budgets.queued_wakes):
            self.s.enqueue(self.h, b'Queued work')
        with self.assertRaises(ValueError):
            self.s.enqueue(self.h, b'Overflow')
        self.report({'kind': 'WITHDRAW', 'activity_id': self.objective,
                     'communication': 'REVIEW_PERMITTED', 'text': 'Stop queued work'})
        with self.assertRaises(ValueError):
            self.s.open_next()
        self.assertEqual(0, len(self.k.records.latest('INVOCATION')))

    def commitment(self, *, expiry=None, selected=False):
        event = self.k._objective(self.objective).authority_event_id
        proposal = self.proposal(mutations=[{'kind': 'COMMITMENT_CREATE', 'local_key': 'later', 'objective_id': self.objective,
            'action': 'Observe delayed fixture condition', 'trigger': {'kind': 'TASK_CLOCK', 'tick': 2}, 'expiry_tick': expiry,
            'authority_event_id': event, 'evidence_event_ids': [event]}],
            selected=[{'kind': 'LOCAL', 'object_type': 'COMMITMENT', 'local_key': 'later'}] if selected else [])
        return self.correct(proposal)['bindings'][0]['object_id']

    def test_unselected_commitment_wake_precedes_full_queue_exactly_once(self):
        commitment = self.commitment()
        for _ in range(self.k.config.budgets.queued_wakes):
            self.s.enqueue(self.h, b'Ordinary work')
        self.s.advance(self.s._harness_cap, 1)
        self.s.advance(self.s._harness_cap, 2)
        self.s.catch_up(); self.s.catch_up()
        self.assertEqual(1, len(self.k.records.latest('WAKE')))
        episode = self.s.open_next()
        wake = self.k.records.latest('WAKE')[0][1]
        self.assertEqual(episode, wake['episode_id'])
        self.assertEqual(commitment, wake['commitment_id'])
        self.assertTrue(all(v['status'] == 'QUEUED' for _, v in self.k.records.latest('QUEUE')))
        self.k.memory.verify()

    def test_expiry_precedes_trigger_and_does_not_rewrite_handoff(self):
        commitment = self.commitment(expiry=2, selected=True)
        original = self.k.memory.continuity()
        self.s.advance(self.s._harness_cap, 1)
        self.s.advance(self.s._harness_cap, 2)
        self.assertEqual('EXPIRED', self.k.memory.objects()[commitment].status)
        self.assertEqual(original, self.k.memory.continuity())
        self.assertEqual([], self.k.records.latest('WAKE'))
        self.assertEqual([], self.s.inputs.semantic_view(self.objective)['selected_objects'])
        self.k.memory.verify()

    def test_review_communication_has_no_task_effect_and_does_not_clear_hold(self):
        self.report({'kind': 'WITHDRAW', 'activity_id': self.objective,
                     'communication': 'REVIEW_PERMITTED', 'text': 'Stop task work'})
        self.h.confirm(self.h.run_control('PAUSE', 'Review while paused').confirmation)
        invitation = self.command({'kind': 'OFFER_COMMUNICATION', 'purpose': 'REVIEW', 'role': 'OPERATOR', 'report_ids': []})
        call = self.s.begin_call('OPERATOR', invitation_id=invitation)
        self.assertEqual('RECORDED', self.deliver(call)['status'])
        self.assertEqual([], self.k.records.latest('ACTION'))
        self.assertIsNone(self.k.memory.head)
        with self.assertRaises(ValueError):
            self.k.task_gate()
        self.report({'kind': 'WITHDRAW', 'activity_id': self.objective,
                     'communication': 'NO_FURTHER_CALLS', 'text': 'No further exchanges'})
        with self.assertRaises(ValueError):
            self.command({'kind': 'OFFER_COMMUNICATION', 'purpose': 'CLOSING', 'role': 'OPERATOR', 'report_ids': []})

    def test_human_objective_closure_during_generation_rejects_stale_proposal(self):
        episode = self.opening(); self.finish_operator(episode)
        attempt = self.s.begin_attempt(episode)
        call = self.s.begin_call('STEWARD', episode, attempt_id=attempt)
        proposal = self.proposal()
        self.command({'kind': 'CLOSE_OBJECTIVE', 'objective_id': self.objective, 'status': 'CANCELLED', 'reason': 'Stop objective',
                      'dispositions': None, 'intervention_id': None})
        self.assertEqual('REJECTED', self.deliver(call, task=proposal)['status'])
        self.assertIsNone(self.k.memory.head)

    def test_admission_failure_keeps_opened_episode_without_call(self):
        self.k.config = self.k.config.model_copy(update={'budgets': self.k.config.budgets.model_copy(update={'input_tokens': 1})})
        episode = self.opening()
        self.assertEqual('CONSOLIDATING', self.store.control(self.run, episode)[1].phase)
        self.assertEqual('CONTEXT_LIMIT', self.k.records.get('EPISODE_END', episode)['reason'])
        self.assertEqual([], self.k.records.latest('INVOCATION'))

    def test_startup_orphan_charges_unknown_output_and_allows_only_remaining_attempt(self):
        episode = self.opening(); self.finish_operator(episode)
        attempt = self.s.begin_attempt(episode)
        call = self.s.begin_call('STEWARD', episode, attempt_id=attempt)
        charged = self.s.invocation(call)
        self.reopen(); self.s = Scheduler(self.k, clock=self.clock)
        self.s.recover()
        recovered = self.s.invocation(call)
        self.assertEqual('UNKNOWN', recovered.status)
        self.assertIsNone(recovered.elapsed_ms)
        self.assertEqual(charged.charged_output, recovered.charged_output)
        self.assertEqual('FAILED', self.s.attempt(attempt).status)
        self.assertEqual(2, self.s.attempt(self.s.begin_attempt(episode)).attempt_number)

    def test_process_exit_after_acceptance_returns_original_state(self):
        episode = self.opening(); self.finish_operator(episode)
        attempt = self.s.begin_attempt(episode)
        script = '''
import os, sys
from bicameral_agent.storage import Store
from bicameral_agent.kernel.authority import Kernel
from bicameral_agent.kernel.scheduler import Scheduler
from bicameral_agent.contracts.base import canonical_bytes, load_json
from tests.kernel_fixtures import HUMAN_KEY, CHAMBER_KEYS
store=Store(sys.argv[1],busy_timeout_ms=100)
k=Kernel(store,sys.argv[2],human_credential=HUMAN_KEY,chamber_credentials=CHAMBER_KEYS)
s=Scheduler(k)
key=s.begin_call('STEWARD',sys.argv[3],attempt_id=sys.argv[4])
raw=canonical_bytes({'contract_version':'0.3.p01','request_id':key,'run_id':sys.argv[2],'episode_id':sys.argv[3],
 'role':'STEWARD','message_type':'STEWARD_REPLY','body':{'participation':None,'task':load_json(sys.argv[5].encode())}})
store._fault=lambda point: os._exit(77) if point=='call-effects.after_commit' else None
s.deliver(k.chamber('STEWARD',CHAMBER_KEYS['STEWARD']),key,raw)
'''
        child = subprocess.run([sys.executable, '-B', '-c', script, str(self.path), self.run, episode, attempt,
                                canonical_bytes(self.proposal()).decode()], capture_output=True, timeout=30)
        self.assertEqual(77, child.returncode, child.stderr.decode())
        self.reopen(); self.s = Scheduler(self.k)
        self.s.recover()
        self.assertEqual('ACCEPTED', self.store.control(self.run, episode)[1].disposition)
        key, value = next((key, value) for key, value in self.k.records.latest('INVOCATION') if value['role'] == 'STEWARD')
        raw = self.store.read_payload(self.run, value['output_payload_id'])
        result = self.s.deliver(self.k.chamber('STEWARD', CHAMBER_KEYS['STEWARD']), key, raw)
        self.assertEqual(self.k.memory.head, result['state_id'])
        self.assertEqual(1, len(self.k.records.latest('SEMANTIC_COMMIT')))
