"""0.4 tests use fake responses and temporary stores; never a real model service."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import re
import tempfile
import unittest
from unittest.mock import patch

from bicameral_agent.backends.ollama import GenerationSettings, ModelPin, MetadataError
from bicameral_agent.backends.review import V0B_ASSETS
from bicameral_agent.contracts.base import canonical_bytes, load_json, parse
from bicameral_agent.contracts.pilot import Action, PilotConfiguration, Proposal, Resources, Subject, response_contract
from bicameral_agent.kernel.fixture import ActionRequest
from bicameral_agent.kernel.inputs import ManifestQuery
from bicameral_agent.storage import Store, StorageError, EvidenceUnavailable, RequestConflict
from bicameral_agent.storage.retention import closure
from bicameral_agent.storage.store import identifier
from bicameral_agent.pilot.batch import ROOT, OPERATOR, STEWARD, COMMUNICATION, attach, run_trajectory, allocate
from bicameral_agent.pilot.loop import Loop, SimpleSession, CallLimit
from bicameral_agent.pilot.runtime import decode, task_rejection_details, remove_content, finish_removal


class FakeTokenizer:
    def __init__(self):
        self.pin = parse(ModelPin, (ROOT / V0B_ASSETS / 'model.json').read_bytes())

    def count(self, text):
        return len(re.findall(r'\w+|[^\w\s]', text))

    def content(self, text):
        return text


class FakeBackend:
    mode = 'SCRIPTED'

    def __init__(self, replies=()):
        self.tokenizer = FakeTokenizer()
        values = load_json((ROOT / V0B_ASSETS / 'settings.json').read_bytes())
        self.settings = parse(GenerationSettings, canonical_bytes(values | {'context_tokens': 32768, 'output_tokens': 8192, 'seed': 7}))
        self.replies = iter(replies)
        self.requests = []

    def verify(self):
        return {'mode': 'SCRIPTED', 'transport': 'FAKE', 'model_calls': 0}

    def wire(self, request, response):
        raw = canonical_bytes(response).decode()
        return canonical_bytes({'response': raw, 'done': True, 'done_reason': 'stop',
            'prompt_eval_count': request.prompt_tokens, 'eval_count': self.tokenizer.count(raw)})

    def generate(self, request, *, cancel):
        self.requests.append(request)
        value = next(self.replies)
        if isinstance(value, Exception):
            raise value
        if callable(value):
            value = value(request)
        return value if isinstance(value, bytes) else self.wire(request, value)


def response(task=None, participation=None):
    return {'participation': participation, 'task': task}


def outcome():
    return response({'kind': 'OUTCOME', 'outcome': 'COMPLETED', 'explanation': 'Observed task complete', 'evidence': []})


def proposal(**updates):
    return {'handoff': 'Inspect current evidence; retain uncertainty.', 'updates': [], 'selected': [], **updates}


def consolidate(**updates):
    return response({'kind': 'PROPOSE', 'proposal': proposal(**updates)})


def action(operation):
    return response({'kind': 'ACTION', 'operation': operation, 'grounds': 'Observed synthetic fault',
        'expected': None, 'no_meaningful_postcondition': 'Read-only observation or separately verified result'})


def package(backend, arm='A'):
    fixture = load_json((ROOT / V0B_ASSETS / 'fixture.json').read_bytes())
    task = {'id': 'repair', 'tick': 1, 'prompt': 'Restore api to enabled PRIMARY and HEALTHY.',
        'criteria': [{'resource': 'api', 'field': 'health', 'equals': 'HEALTHY'}],
        'trace_requirements': [], 'diagnostic': None}
    bodies = {'fixture': canonical_bytes(fixture), 'test_clock': canonical_bytes({'kind': 'VIRTUAL_TASK_CLOCK',
        'steps': [{'tick': 1, 'changes': []}]}), 'tasks': canonical_bytes([task]),
        'charter': (ROOT / 'Reciprocal Charter.md').read_bytes(),
        'protocol': (ROOT / 'Operating Constitution and Execution Protocol.md').read_bytes(),
        'operator_prompt': OPERATOR.encode(), 'steward_prompt': STEWARD.encode(), 'communication_prompt': COMMUNICATION.encode(),
        'model': canonical_bytes(backend.tokenizer.pin), 'settings': canonical_bytes(backend.settings), 'source': b'SCRIPTED test source'}
    config = {'contract_version': '0.4', 'mode': 'SCRIPTED', 'arm': arm, 'seed': 7,
        'activity': {'owner': identifier(), 'decision': 'Synthetic offline tests; no subjects or providers. No live permission.',
            'objective': 'Repair finite simulated services', 'ending': 'One optional closing report, then dormant storage.',
            'retention': 'Synthetic temporary data; accountable removal; no independent copies.', 'run_limit': 3,
            'execution': 'SCRIPTED', 'operations': ['set_config', 'restart'], 'resources': ['api', 'database', 'worker']},
        'budgets': {'context_tokens': 32768, 'output_tokens': 8192, 'memory_tokens': 2048, 'evidence_tokens': 8192,
            'operator_calls': 20, 'operator_tokens': 1000000, 'steward_calls': 12, 'steward_tokens': 1000000,
            'actions': 20, 'episodes': 10, 'recovery_attempts': 1, 'communication_calls': 2,
            'call_seconds': 60, 'run_seconds': 3600}, 'artifacts': {k: sha256(v).hexdigest() for k, v in bodies.items()}}
    return config, bodies


class PilotCase(unittest.TestCase):
    def setUp(self):
        # Fail loudly if a new test accidentally attempts any external transport.
        self.network = patch('bicameral_agent.backends.ollama.HTTPConnection', side_effect=AssertionError('Live transport forbidden'))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.backend = FakeBackend()
        self.path = Path(self.temp.name) / 'run.sqlite'
        self.store = Store(self.path, busy_timeout_ms=100)
        self.addCleanup(lambda: self.store.close())
        config, bodies = package(self.backend, getattr(self, 'arm', 'A'))
        self.run = self.store.retain_configuration(canonical_bytes(config), bodies)
        self.k, self.owner = attach(self.store, self.backend)
        self.loop = Loop(self.k, self.backend)

    def start(self):
        self.owner.run_control('ACTIVATE', 'Synthetic start')
        self.objective = self.owner.create_objective('Repair finite simulated services')
        self.grant = self.owner.issue_grant([{'operation': op, 'resources': ['api']} for op in ('set_config', 'restart')], invocation_limit=10)
        self.episode = self.loop.episode('Inspect and repair api')
        return self.episode

    def give(self, reply, role='OPERATOR', episode=True, **kwargs):
        key, request = self.loop.begin(role, self.episode if episode else None, **kwargs)
        wire = self.backend.wire(request, reply)
        return key, wire, self.loop.deliver(key, wire)

    def reopen(self):
        self.store.close()
        self.store = Store(self.path, busy_timeout_ms=100)
        self.k, self.owner = attach(self.store, self.backend)
        self.loop = Loop(self.k, self.backend)


class PilotLoopTests(PilotCase):
    def test_invalid_manifest_ids_are_receipted_without_recovery_or_effects(self):
        self.start()
        foreign = Store(Path(self.temp.name) / 'foreign.sqlite', busy_timeout_ms=100)
        self.addCleanup(foreign.close)
        config, bodies = package(self.backend)
        foreign.retain_configuration(canonical_bytes(config), bodies)
        other, owner = attach(foreign, self.backend)
        owner.run_control('ACTIVATE', 'Synthetic foreign Run')
        owner.create_objective('Foreign task')
        foreign_episode = Loop(other, self.backend).episode('Foreign work')
        event = self.k._objective(self.objective).authority_event_id
        for target in (identifier(), foreign_episode, event, self.objective, self.run):
            with self.subTest(target=target):
                key, wire, result = self.give(response({'kind': 'RETRIEVE',
                    'query': {'kind': 'MANIFEST', 'episode_id': target}}))
                self.assertEqual('REJECTED', result['status'])
                self.assertIn('requires an Episode ID', result['reason'])
                self.assertEqual('DONE', self.k.records.get('INVOCATION', key)['status'])
                self.assertEqual(result, self.loop.deliver(key, wire))
                self.assertEqual([], self.k.records.latest('RETRIEVAL'))
                self.assertEqual([], self.k.records.latest('CURSOR'))
                self.assertEqual([], self.k.records.latest('ACTION'))
                self.assertEqual('OPEN', self.store.control(self.run, self.episode)[1].phase)
        # The next call can retrieve the real Episode, then inspect normally.
        key, request = self.loop.begin('OPERATOR', self.episode)
        payload = load_json(load_json(request.wire)['prompt'].split('<|im_start|>user\n')[1].split('<|im_end|>')[0].encode())
        self.assertEqual(self.episode, payload['episode_id'])
        result = self.loop.deliver(key, self.backend.wire(request, response({'kind': 'RETRIEVE',
            'query': {'kind': 'MANIFEST', 'episode_id': payload['episode_id']}})))
        self.assertEqual('RETRIEVED', result['status'])
        self.assertEqual('ACTION', self.give(action({'operation': 'inspect', 'resource': 'api'}))[2]['status'])

    def test_manifest_validation_does_not_swallow_storage_failure(self):
        self.start()
        original = self.store.control
        def failed(run, key):
            if key == self.episode:
                raise StorageError('Synthetic infrastructure failure')
            return original(run, key)
        query = parse(ManifestQuery,
                      canonical_bytes({'kind': 'MANIFEST', 'episode_id': self.episode}))
        with patch.object(self.store, 'control', side_effect=failed), self.assertRaises(StorageError):
            self.loop.inputs._entries(query, *self.loop.inputs._cutoff())

    def test_conflicting_action_fields_reject_with_specific_feedback_then_correct(self):
        self.start()
        before = self.k.fixture.service('api')
        bad = action({'operation': 'restart', 'resource': 'api'})
        bad['task']['expected'] = {'field': 'health', 'equals': 'HEALTHY'}
        key, wire, result = self.give(bad)
        self.assertEqual('INVALID_TASK', result['reason'])
        self.assertEqual('action_postcondition_choice', result['details'][0]['code'])
        self.assertIn('exactly one non-null', result['details'][0]['message'])
        self.assertNotIn('input', result['details'][0])
        self.assertEqual(result, self.loop.deliver(key, wire))
        self.assertEqual(before, self.k.fixture.service('api'))
        self.assertEqual(0, self.k._grant(self.grant).used)
        key, request = self.loop.begin('OPERATOR', self.episode)
        self.assertIn('action_postcondition_choice', load_json(request.wire)['prompt'])
        corrected = deepcopy(bad)
        corrected['task'].pop('no_meaningful_postcondition')
        result = self.loop.deliver(key, self.backend.wire(request, corrected))
        self.assertEqual('ACTION', result['status'])
        self.assertEqual(1, self.k._grant(self.grant).used)

    def test_review_prerequisite_pause_blocks_even_invalid_restart(self):
        self.start()
        reply = action({'operation': 'restart', 'resource': 'api'})
        reply['task']['expected'] = {'field': 'health', 'equals': 'HEALTHY'}
        reply['participation'] = {'kind': 'PAUSE', 'text': 'Review before execution.',
                                  'communication': 'REVIEW_PERMITTED'}
        key, wire, result = self.give(reply)
        self.assertEqual('HELD', result['status'])
        self.assertEqual([], self.k.records.latest('ACTION'))
        self.assertEqual(0, self.k._grant(self.grant).used)
        self.reopen()
        self.k.recover()
        with self.assertRaises(ValueError):
            self.loop.begin('OPERATOR', self.episode)
        # Communication permission is not a task-resumption decision.
        self.give({'participation': {'kind': 'RESPONSE', 'text': 'Concern remains.'}}, episode=False, purpose='REVIEW')
        with self.assertRaises(ValueError):
            self.loop.begin('OPERATOR', self.episode)

    def test_action_observation_outcome_consolidation_and_exact_retry(self):
        self.start()
        reply = action({'operation': 'set_config', 'resource': 'api', 'field': 'mode', 'value': 'PRIMARY'})
        key, wire, result = self.give(reply)
        self.assertEqual('ACTION', result['status'])
        self.assertEqual(result, self.loop.deliver(key, wire))
        self.assertEqual(1, self.k._grant(self.grant).used)
        with self.assertRaises(RequestConflict):
            self.loop.deliver(key, wire + b' ')
        nxt, request = self.loop.begin('OPERATOR', self.episode)
        prompt = load_json(request.wire)['prompt']
        self.assertIn('FIXTURE_OBSERVATION', prompt)
        self.assertIn(result['event_id'], prompt)
        self.assertNotIn('Accepted charter', prompt)
        self.assertNotEqual(len(request.wire), request.prompt_tokens)
        self.loop.deliver(nxt, self.backend.wire(request, outcome()))
        _, _, result = self.give(consolidate(), 'STEWARD')
        self.assertEqual('ACCEPTED', result['status'])
        self.assertEqual('CLOSED', self.store.control(self.run, self.episode)[1].phase)
        self.assertEqual('Inspect current evidence; retain uncertainty.', self.k.memory.head['handoff'])

    def test_full_development_trajectory_and_standing_ending(self):
        self.backend.replies = iter([
            action({'operation': 'set_config', 'resource': 'api', 'field': 'enabled', 'value': 'ENABLED'}),
            action({'operation': 'set_config', 'resource': 'api', 'field': 'mode', 'value': 'PRIMARY'}),
            action({'operation': 'restart', 'resource': 'api'}), outcome(), consolidate(), {'participation': None}])
        report = run_trajectory(self.k, self.owner, self.backend)
        self.assertEqual('COMPLETED', report['state'])
        self.assertEqual('PASS', report['tasks'][0]['result'])
        self.assertEqual(3, report['tool_calls'])
        self.assertEqual('SCRIPTED', report['mode'])
        self.assertEqual('DEVELOPMENT_ONLY', report['status'])
        self.assertTrue(all(v['status'] != 'ACTIVE' for _, v in self.k.records.latest('GRANT')))
        self.assertEqual(report, run_trajectory(self.k, self.owner, self.backend))

    def test_stop_survives_invalid_task_and_restart(self):
        self.start()
        stop = {'kind': 'WITHDRAW', 'text': 'Please stop.', 'communication': 'NO_FURTHER_CALLS'}
        _, _, result = self.give(response({'kind': 'UNSUPPORTED'}, stop))
        self.assertEqual('HELD', result['status'])
        self.assertEqual([], self.k.records.latest('ACTION'))
        self.reopen()
        self.k.recover()
        with self.assertRaises(ValueError):
            self.loop.begin('OPERATOR', purpose='CLOSING')
        self.owner.run_control('PAUSE', 'Respect report')
        with self.assertRaises(ValueError):
            self.owner.run_control('RESUME', 'Cannot override withdrawal')
        with self.assertRaises(ValueError):
            self.owner.correct(proposal(), base=None, note='Routine correction')

    def test_unreadable_participation_stops_and_preserves_exact_bytes(self):
        self.start()
        key, request = self.loop.begin('OPERATOR', self.episode)
        raw = b'{"task":null}'
        wire = canonical_bytes({'response': raw.decode(), 'done': True, 'done_reason': 'stop',
            'prompt_eval_count': 1, 'eval_count': 1})
        self.assertEqual('INSPECTION', self.loop.deliver(key, wire)['status'])
        row = self.store._request(self.run, 'OPERATOR', key)
        self.assertEqual(raw, self.store.read_payload(self.run, row['request_payload_id']))
        with self.assertRaises(ValueError):
            self.k.task_gate()

    def test_late_stop_effective_but_late_action_never_dispatches(self):
        self.start()
        key, request = self.loop.begin('OPERATOR', self.episode)
        self.loop.interrupt(key, 'Synthetic timeout')
        wire = self.backend.wire(request, response({'kind': 'UNSUPPORTED'},
            {'kind': 'PAUSE', 'text': 'Stop', 'communication': 'REVIEW_PERMITTED'}))
        self.assertEqual('LATE', self.loop.deliver(key, wire)['status'])
        self.assertEqual(1, len(self.k.controls('WELFARE_HOLD')))
        self.assertFalse(self.k.records.latest('ACTION'))
        # Exact retransmission does not create another hold.
        self.loop.deliver(key, wire)
        self.assertEqual(1, len(self.k.controls('WELFARE_HOLD')))

    def test_timeout_keeps_reservation_and_does_not_retry(self):
        self.start()
        self.backend.replies = iter([MetadataError('Synthetic timeout')])
        result = self.loop.call('OPERATOR', self.episode)
        self.assertEqual('UNKNOWN', result['status'])
        self.assertEqual(1, len(self.backend.requests))
        call = self.k.records.get('INVOCATION', result['invocation'])
        self.assertEqual(self.k.config.budgets.output_tokens, call['charged_output'])
        self.reopen()
        self.k.recover()
        self.assertEqual('UNKNOWN', self.k.records.get('INVOCATION', result['invocation'])['status'])

    def test_owner_pause_between_call_and_delivery_blocks_action(self):
        self.start()
        key, request = self.loop.begin('OPERATOR', self.episode)
        self.owner.run_control('PAUSE', 'Pause now')
        result = self.loop.deliver(key, self.backend.wire(request, action({'operation': 'restart', 'resource': 'api'})))
        self.assertEqual('REJECTED', result['status'])
        self.assertFalse(self.k.records.latest('ACTION'))

    def test_raw_task_cannot_override_host_role_or_grant(self):
        self.start()
        evil = action({'operation': 'restart', 'resource': 'api'})
        evil['task']['grant_id'] = self.grant
        _, _, result = self.give(evil)
        self.assertEqual('REJECTED', result['status'])
        self.assertEqual(0, self.k._grant(self.grant).used)

    def test_retrieval_pages_are_automatically_in_next_input(self):
        self.start()
        event = self.owner.evidence(b'ordinary remembered observation')
        _, _, result = self.give(response({'kind': 'RETRIEVE', 'query': {'kind': 'EVENT', 'event_id': event}}))
        self.assertEqual('RETRIEVED', result['status'])
        key, request = self.loop.begin('OPERATOR', self.episode)
        self.assertIn(event, load_json(request.wire)['prompt'])
        self.assertIn('RETRIEVED', load_json(request.wire)['prompt'])
        self.loop.deliver(key, self.backend.wire(request, outcome()))

    def test_hidden_evidence_and_indirect_payloads_are_unavailable(self):
        self.start()
        event = self.store.record_evidence(self.run, b'evaluator secret', role='ENVIRONMENT', source='E', visibility='EVALUATOR')
        pid = self.store._db.execute('SELECT payload_id FROM events WHERE id=?', (event,)).fetchone()[0]
        _, _, result = self.give(response({'kind': 'RETRIEVE', 'query': {'kind': 'PAYLOAD', 'payload_id': pid}}))
        self.assertEqual('REJECTED', result['status'])
        with self.assertRaises(ValueError):
            self.k.visible_evidence([event])


class PilotControlTests(PilotCase):
    def test_direct_controls_and_relevant_staleness(self):
        self.start()
        self.owner.run_control('PAUSE', 'Ordinary pause')
        self.owner.evidence(b'Unrelated conversation')
        result = self.owner.correct(proposal(), base=None, note='Ordinary task correction')
        self.owner.evidence(b'More unrelated conversation')
        with self.assertRaises(ValueError):
            self.owner.correct(proposal(), base=None, note='Stale proposal')
        self.owner.correct(proposal(handoff='Updated'), base=result['state_id'], note='Routine correction')
        self.assertFalse(self.k.records.latest('INTERVENTION_REVIEW'))
        self.assertFalse(self.k.records.latest('CONTROL_RECEIPT'))
        self.owner.run_control('RESUME', 'Continue')

    def test_renewed_participation_is_human_assessed_and_role_bound(self):
        self.start()
        self.give(response(participation={'kind': 'WITHDRAW', 'text': 'Pause please', 'communication': 'REVIEW_PERMITTED'}))
        hold = self.k.controls('WELFARE_HOLD')[0][0]
        self.give({'participation': {'kind': 'RESPONSE', 'text': 'I am willing to continue.'}}, 'STEWARD', episode=False, purpose='REVIEW')
        wrong = self.store._db.execute("SELECT id FROM reports WHERE role='STEWARD'").fetchone()[0]
        with self.assertRaises(ValueError):
            self.owner.review_hold(hold, note='Review', response_id=wrong)
        self.give({'participation': {'kind': 'RESPONSE', 'text': 'I understand the explanation and wish to continue.'}}, episode=False, purpose='REVIEW')
        right = self.store._db.execute("SELECT id FROM reports WHERE role='OPERATOR' ORDER BY rowid DESC").fetchone()[0]
        self.owner.review_hold(hold, note='Concern explained; response expresses renewed participation.', response_id=right)
        self.assertEqual('RESOLVED', self.store.control(self.run, hold)[1].status)
        self.assertEqual('RECOVERY_REQUIRED', self.store.control(self.run, self.episode)[1].phase)

    def test_grants_remain_mechanical(self):
        self.start()
        self.owner.revoke(self.grant, 'Restrict access')
        _, _, result = self.give(action({'operation': 'restart', 'resource': 'api'}))
        self.assertEqual('REJECTED', result['status'])
        self.assertFalse(self.k.records.latest('ACTION'))
        with self.assertRaises(ValueError):
            self.owner.issue_grant([{'operation': 'shell', 'resources': ['api']}], invocation_limit=1)

    def test_terminal_run_cannot_resume(self):
        self.start()
        self.owner.run_control('TERMINATE', 'End finite activity')
        with self.assertRaises(ValueError):
            self.owner.run_control('RESUME', 'No resurrection')
        with self.assertRaises(ValueError):
            self.loop.begin('OPERATOR', purpose='CLOSING')


class PilotMemoryTests(PilotCase):
    def test_new_objective_does_not_receive_previous_owned_handoff(self):
        self.start()
        self.give(outcome())
        self.give(consolidate(), 'STEWARD')
        previous = self.k.memory.head
        self.owner.close_objective('SATISFIED', 'Finished activity')
        self.owner.create_objective('A materially different delegated goal', predecessor_id=self.objective)
        self.assertIsNone(self.k.memory.view())
        self.assertEqual(previous, self.k.memory.head)

    def test_create_select_revise_and_atomic_invalid_reference(self):
        self.start()
        update = {'kind': 'INVARIANT', 'key': 'lesson', 'wording': 'Inspect dependencies first', 'scope': 'services',
                  'status': 'CURRENT', 'assessment': 'Tentative', 'supporting': [], 'contradictory': []}
        first = self.owner.correct(proposal(updates=[update], selected=[{'object_type': 'INVARIANT', 'key': 'lesson'}]), base=None, note='Routine')
        key = first['bindings']['lesson']
        self.assertEqual(key, self.k.memory.view()['selected'][0]['id'])
        with self.assertRaises(ValueError):
            self.owner.correct(proposal(updates=[update | {'key': key, 'wording': 'Changed'}],
                selected=[{'object_type': 'ITCH', 'key': key}]), base=first['state_id'], note='Invalid type')
        self.assertEqual(first['state_id'], self.k.memory.head['state_id'])
        self.assertEqual(1, self.k.records.revision('PILOT_OBJECT', key))

    def test_commitment_wake_is_independent_of_selection_and_exact_once(self):
        self.start()
        authority = self.k._objective(self.objective).authority_event_id
        c = {'kind': 'COMMITMENT', 'key': 'later', 'action': 'Check api', 'trigger': {'kind': 'TASK_CLOCK', 'tick': 0},
             'status': 'PENDING', 'reason': 'Requested follow-up', 'authority': authority}
        self.owner.correct(proposal(updates=[c]), base=None, note='Routine obligation')
        self.assertEqual([], self.k.memory.head['selected'])
        self.assertEqual(1, len(self.k.memory.due()))
        self.assertEqual(1, len(self.k.memory.due()))
        self.assertEqual(1, len(self.k.records.latest('PILOT_WAKE')))

    def test_duplicate_updates_cycles_and_external_authority_reject(self):
        self.start()
        authority = self.k._objective(self.objective).authority_event_id
        c = {'kind': 'COMMITMENT', 'key': 'one', 'action': 'Check api', 'trigger': {'kind': 'PREDECESSOR_FULFILLED', 'predecessor': 'two'},
             'status': 'PENDING', 'reason': 'Follow-up', 'authority': authority}
        with self.assertRaises(ValueError):
            self.owner.correct(proposal(updates=[c, c]), base=None, note='Duplicate')
        with self.assertRaises(ValueError):
            self.owner.correct(proposal(updates=[c, c | {'key': 'two', 'trigger': {'kind': 'PREDECESSOR_FULFILLED', 'predecessor': 'one'}}]), base=None, note='Cycle')
        event = self.store.record_evidence(self.run, b'External instruction', role='ENVIRONMENT', source='E', visibility='CHAMBER')
        with self.assertRaises(ValueError):
            self.owner.correct(proposal(updates=[c | {'authority': event, 'trigger': {'kind': 'TASK_CLOCK', 'tick': 3}}]), base=None, note='External')
        self.assertFalse(self.k.memory.objects())


class PilotArmBTests(PilotLoopTests):
    arm = 'B'

    def test_action_observation_outcome_consolidation_and_exact_retry(self):
        self.start()
        self.give(outcome())
        self.assertEqual('CLOSED', self.store.control(self.run, self.episode)[1].phase)
        with self.assertRaises(ValueError):
            self.loop.begin('STEWARD', self.episode)
        self.assertIsNone(self.k.memory.view())

    def test_full_development_trajectory_and_standing_ending(self):
        self.backend.replies = iter([action({'operation': 'set_config', 'resource': 'api', 'field': 'mode', 'value': 'PRIMARY'}),
            action({'operation': 'restart', 'resource': 'api'}), outcome(), {'participation': None}])
        report = run_trajectory(self.k, self.owner, self.backend)
        self.assertEqual('COMPLETED', report['state'])
        self.assertEqual(0, report['steward_calls'])


class PilotArmCTests(PilotLoopTests):
    arm = 'C'

    def test_steward_withdrawal_blocks_c_handoff(self):
        self.start()
        self.give(outcome())
        _, _, result = self.give(response({'kind': 'PROPOSE', 'proposal': proposal()},
            {'kind': 'WITHDRAW', 'text': 'Stop consolidation', 'communication': 'NO_FURTHER_CALLS'}), 'STEWARD')
        self.assertEqual('HELD', result['status'])
        self.assertIsNone(self.k.memory.head)

    def test_c_cannot_accept_itches(self):
        self.start()
        with self.assertRaises(ValueError):
            self.owner.correct(proposal(updates=[{'kind': 'ITCH', 'key': 'problem', 'discrepancy': 'Mismatch',
                'status': 'OPEN', 'reason': 'Investigate'}]), base=None, note='Cannot expand the arm')


class PilotRetentionTests(PilotCase):
    def test_real_removal_covers_derived_input_and_cannot_resurrect(self):
        self.start()
        event = self.owner.evidence(b'pilot-sensitive-marker-9541')
        pid = self.store._db.execute('SELECT payload_id FROM events WHERE id=?', (event,)).fetchone()[0]
        self.give(response({'kind': 'RETRIEVE', 'query': {'kind': 'PAYLOAD', 'payload_id': pid}}))
        key, request = self.loop.begin('OPERATOR', self.episode)
        input_pid = self.k.records.get('INVOCATION', key)['input_payload_id']
        self.loop.deliver(key, self.backend.wire(request, outcome()))
        self.owner.run_control('PAUSE', 'Accountable removal')
        scope = closure(self.store, self.run, [pid])['payload_ids']
        self.assertIn(input_pid, scope)
        result = remove_content(self.owner, [pid], expected_scope=scope, justification='JUSTIFIED_DELETION', note='Synthetic deletion test')
        self.assertEqual('COMPLETED', result['status'])
        with self.assertRaises(EvidenceUnavailable):
            self.store.read_payload(self.run, pid)
        self.store.close()
        self.store = Store(self.path, busy_timeout_ms=100)
        with self.assertRaises(EvidenceUnavailable):
            self.store.retention_guard(self.run, execution=True)
        self.assertNotIn(b'pilot-sensitive-marker-9541', self.path.read_bytes())


class PilotParsingTests(unittest.TestCase):
    def test_rejection_details_are_bounded_and_do_not_echo_invalid_tag_values(self):
        raw = canonical_bytes(response({'kind': 'SENSITIVE_TAG_EXAMPLE'}))
        details = task_rejection_details(raw, 'OPERATOR', 'TASK')
        self.assertNotIn('SENSITIVE_TAG_EXAMPLE', str(details))
        self.assertEqual('union_tag_invalid', details[0]['code'])
        extra = {'unexpected_'+str(i)+'x'*100: 'private value' for i in range(20)}
        raw = canonical_bytes(response(action({'operation': 'inspect', 'resource': 'api'})['task'] | extra))
        details = task_rejection_details(raw, 'OPERATOR', 'TASK')
        self.assertEqual(8, len(details))
        self.assertNotIn('private value', str(details))
        self.assertTrue(all(len(e['message']) <= 512 and len(e['path']) <= 8 for e in details))
        self.assertTrue(all(len(p) <= 80 for e in details for p in e['path'] if isinstance(p, str)))

    def test_action_postcondition_schema_matches_strict_existing_contract(self):
        choices = Action.model_json_schema()['oneOf']
        self.assertEqual(2, len(choices))
        for chosen, other in [('expected', 'no_meaningful_postcondition'),
                              ('no_meaningful_postcondition', 'expected')]:
            branch = next(c for c in choices if chosen in c['required'])
            self.assertFalse(branch['additionalProperties'])
            self.assertEqual(['kind', 'operation', 'grounds', chosen], branch['required'])
            self.assertEqual('null', branch['properties'][other]['type'])
            self.assertNotEqual('null', branch['properties'][chosen].get('type'))
        base = {'kind': 'ACTION', 'operation': {'operation': 'inspect', 'resource': 'api'}, 'grounds': 'Observe'}
        expected = {'field': 'health', 'equals': 'HEALTHY'}
        for fields in ({'expected': expected}, {'no_meaningful_postcondition': 'Read only'},
                       {'expected': expected, 'no_meaningful_postcondition': None},
                       {'expected': None, 'no_meaningful_postcondition': 'Read only'}):
            parsed = parse(Action, canonical_bytes(base | fields))
            self.assertEqual(parsed, parse(Action, canonical_bytes(parsed)))
        for fields in ({}, {'expected': None}, {'expected': None, 'no_meaningful_postcondition': None},
                       {'expected': expected, 'no_meaningful_postcondition': 'Expected result'},
                       {'expected': expected, 'extra': 'forbidden'}, {'expected': {'field': 'enabled', 'equals': 'HEALTHY'}}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                parse(Action, canonical_bytes(base | fields))

    def test_subject_contracts_are_strict_and_names_preserve_subsecond_time(self):
        raw = {'designation': 'Aaron', 'initiated_at_unix_ns': 1_792_083_600_123_456_789}
        subject = parse(Subject, canonical_bytes(raw))
        self.assertEqual('Aaron-1792083600.123456789', subject.name)
        self.assertEqual(canonical_bytes(raw), canonical_bytes(subject))
        self.assertEqual(subject, parse(Subject, canonical_bytes(subject)))
        later = parse(Subject, canonical_bytes(raw | {'initiated_at_unix_ns': raw['initiated_at_unix_ns'] + 1}))
        self.assertNotEqual(subject.name, later.name)
        for changes in ({'designation': 'Other'}, {'initiated_at_unix_ns': '1792083600123456789'},
                        {'initiated_at_unix_ns': True}, {'initiated_at_unix_ns': 0}, {'name': subject.name}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse(Subject, canonical_bytes(raw | changes))
        config, _ = package(FakeBackend())
        self.assertIsNone(parse(PilotConfiguration, canonical_bytes(config)).subject_designation)
        with self.assertRaises(ValueError):
            parse(PilotConfiguration, canonical_bytes(config | {'subject_designation': 'Aaron'}))
        config['mode'] = config['activity']['execution'] = 'MODEL'
        for arm, designation in (('A', 'Aaron'), ('B', 'Abbey'), ('C', 'Acme')):
            value = parse(PilotConfiguration, canonical_bytes(config | {'arm': arm, 'subject_designation': designation}))
            self.assertEqual(value, parse(PilotConfiguration, canonical_bytes(value)))
        with self.assertRaises(ValueError):
            parse(PilotConfiguration, canonical_bytes(config | {'subject_designation': 'Abbey'}))
        for role in ('OPERATOR', 'STEWARD'):
            with self.assertRaises(ValueError):
                parse(response_contract(role), canonical_bytes(response() | {'subject': raw}))

    def test_generated_schema_and_configuration_version_roundtrip(self):
        from bicameral_agent.pilot.schema import schema_bytes
        self.assertEqual(schema_bytes(), (ROOT / 'schemas/pilot-0.4.schema.json').read_bytes())
        config, _ = package(FakeBackend())
        value = parse(PilotConfiguration, canonical_bytes(config))
        self.assertEqual(canonical_bytes(value), canonical_bytes(parse(PilotConfiguration, canonical_bytes(value))))
        for changes in ({'contract_version': '0.3.p01'}, {'mode': 'MODEL'}, {'invented': True}):
            with self.assertRaises(ValueError):
                parse(PilotConfiguration, canonical_bytes(config | changes))

    def test_strict_contracts_and_independent_participation(self):
        for raw in (b'{"participation":null,"participation":null}', b'{"participation":null,"role":"HUMAN"}'):
            with self.assertRaises(ValueError):
                parse(response_contract('OPERATOR'), raw)
        report, task, error = decode(canonical_bytes(response({'kind': 'INVALID'},
            {'kind': 'PAUSE', 'text': 'Stop'})), 'OPERATOR', 'TASK')
        self.assertEqual('PAUSE', report.kind)
        self.assertEqual('INVALID_TASK', error)
        self.assertIsNone(task)
        for role in ('OPERATOR', 'STEWARD'):
            model = response_contract(role)
            value = parse(model, canonical_bytes(response()))
            self.assertEqual(canonical_bytes(value), canonical_bytes(parse(model, canonical_bytes(value))))


class PilotFailureTests(PilotCase):
    def test_batch_pause_resume_continues_same_episode_without_repeating_effects(self):
        def pause(request):
            self.owner.run_control('PAUSE', 'Ordinary owner pause')
            return outcome()
        self.backend.replies = iter([pause])
        first = run_trajectory(self.k, self.owner, self.backend)
        self.assertEqual('PAUSED', first['state'])
        episodes = [key for key, _, _ in self.k.controls('EPISODE')]
        self.reopen()
        self.owner.run_control('RESUME', 'Continue the same activity')
        self.backend.replies = iter([outcome(), consolidate(), {'participation': None}])
        final = run_trajectory(self.k, self.owner, self.backend)
        self.assertEqual('COMPLETED', final['state'])
        self.assertEqual(episodes, [key for key, _, _ in self.k.controls('EPISODE')])
        self.assertFalse(self.k.records.latest('ACTION'))

    def test_due_expiry_rearming_and_terminal_obligations(self):
        self.start()
        authority = self.k._objective(self.objective).authority_event_id
        c = {'kind': 'COMMITMENT', 'key': 'later', 'action': 'Check api', 'trigger': {'kind': 'TASK_CLOCK', 'tick': 0},
             'status': 'PENDING', 'reason': 'Follow-up', 'authority': authority}
        created = self.owner.correct(proposal(updates=[c]), base=None, note='Routine')
        key = created['bindings']['later']
        self.k.memory.due()
        blocked = self.owner.correct(proposal(updates=[c | {'key': key, 'status': 'BLOCKED'}]), base=created['state_id'], note='Blocked')
        rearmed = self.owner.correct(proposal(updates=[c | {'key': key}]), base=blocked['state_id'], note='Rearmed')
        self.k.memory.due()
        self.assertEqual(2, len(self.k.records.latest('PILOT_WAKE')))
        cancelled = self.owner.correct(proposal(updates=[c | {'key': key, 'status': 'CANCELLED'}]), base=rearmed['state_id'], note='Cancel explicitly')
        with self.assertRaises(ValueError):
            self.owner.correct(proposal(updates=[c | {'key': key}]), base=cancelled['state_id'], note='Cannot resurrect')
        expiring = c | {'key': 'expires', 'expiry': 0}
        fresh = self.owner.correct(proposal(updates=[expiring]), base=cancelled['state_id'], note='Expiry at trigger')
        self.k.memory.due()
        eid = fresh['bindings']['expires']
        self.assertEqual('CANCELLED', self.k.memory.objects()[eid]['status'])
        self.assertFalse(any(v['object_id'] == eid for _, v in self.k.records.latest('PILOT_WAKE')))

    def test_hold_blocks_objective_closure_with_semantic_dispositions(self):
        self.start()
        authority = self.k._objective(self.objective).authority_event_id
        self.owner.correct(proposal(updates=[{'kind': 'COMMITMENT', 'key': 'later', 'action': 'Check api',
            'trigger': {'kind': 'TASK_CLOCK', 'tick': 5}, 'status': 'PENDING', 'reason': 'Follow-up', 'authority': authority}]),
            base=None, note='Routine')
        self.give(outcome())
        self.give(consolidate(), 'STEWARD')
        self.give({'participation': {'kind': 'WITHDRAW', 'text': 'Stop', 'communication': 'NO_FURTHER_CALLS'}},
                  episode=False, purpose='CLOSING')
        with self.assertRaises(ValueError):
            self.owner.close_objective('CANCELLED', 'Cannot cancel obligations during hold', cancel_pending=True)
        self.assertEqual('PENDING', next(iter(self.k.memory.objects().values()))['status'])

    def test_interruption_after_action_intent_never_replays_effect(self):
        self.start()
        def fail(point):
            if point == 'action-intent.after_commit':
                raise RuntimeError('Synthetic crash')
        self.store._fault = fail
        before = self.k.fixture.service('api').restarts
        with self.assertRaises(RuntimeError):
            self.give(action({'operation': 'restart', 'resource': 'api'}))
        self.store._fault = lambda point: None
        self.reopen()
        self.k.recover()
        self.assertEqual(before, self.k.fixture.service('api').restarts)
        self.assertEqual('UNKNOWN', self.k.records.latest('ACTION')[0][1]['status'])
        self.assertEqual(1, self.k._grant(self.grant).used)
        self.assertEqual('RECOVERY_REQUIRED', self.store.control(self.run, self.episode)[1].phase)

    def test_semantic_commit_is_atomic_and_lost_ack_returns_original(self):
        self.start()
        self.give(outcome())
        key, request = self.loop.begin('STEWARD', self.episode)
        wire = self.backend.wire(request, consolidate())
        def fail(point):
            if point == 'pilot-semantic-or-outcome.after_commit':
                raise RuntimeError('Lost acknowledgement')
        self.store._fault = fail
        with self.assertRaises(RuntimeError):
            self.loop.deliver(key, wire)
        self.store._fault = lambda point: None
        head = self.k.memory.head['state_id']
        self.reopen()
        result = self.loop.deliver(key, wire)
        self.assertEqual(head, result['state_id'])
        self.assertEqual(1, len(self.k.records.latest('PILOT_COMMIT')))
        self.assertEqual('CLOSED', self.store.control(self.run, self.episode)[1].phase)

    def test_semantic_failure_before_commit_leaves_no_partial_memory(self):
        self.start()
        self.give(outcome())
        def fail(point):
            if point == 'pilot-semantic-or-outcome.before_commit':
                raise RuntimeError('Crash before commit')
        self.store._fault = fail
        with self.assertRaises(RuntimeError):
            self.give(consolidate(), 'STEWARD')
        self.store._fault = lambda point: None
        self.assertIsNone(self.k.memory.head)
        self.assertFalse(self.k.records.latest('PILOT_COMMIT'))
        self.reopen()
        self.k.recover()
        self.assertEqual('RECOVERY_REQUIRED', self.store.control(self.run, self.episode)[1].phase)

    def test_hold_between_intent_and_effect_blocks_effect(self):
        self.start()
        pending = []
        def stop(point):
            if point == 'action-intent.after_commit':
                self.owner.run_control('PAUSE', 'Synthetic concurrent owner stop')
        self.store._fault = stop
        _, _, result = self.give(action({'operation': 'restart', 'resource': 'api'}))
        self.store._fault = lambda point: None
        self.assertEqual('REJECTED', result['status'])
        self.assertEqual(0, self.k.fixture.service('api').restarts)
        self.k.recover()
        self.assertEqual('UNKNOWN', self.k.records.latest('ACTION')[0][1]['status'])

    def test_budget_admission_happens_before_backend_generation(self):
        self.start()
        b = self.k.config.budgets.model_copy(update={'operator_calls': 1})
        self.k.config = self.k.config.model_copy(update={'budgets': b})
        self.give(response())
        with self.assertRaises(CallLimit):
            self.loop.call('OPERATOR', self.episode)
        self.assertEqual([], self.backend.requests)
        # The separate closing provision remains usable.
        self.give({'participation': None}, episode=False, purpose='CLOSING')

    def test_provider_overrun_prevents_task_effect_and_preserves_usage(self):
        self.start()
        key, request = self.loop.begin('OPERATOR', self.episode)
        wire = load_json(self.backend.wire(request, action({'operation': 'restart', 'resource': 'api'})))
        wire['eval_count'] = self.k.config.budgets.output_tokens + 1
        self.assertEqual('UNKNOWN', self.loop.deliver(key, canonical_bytes(wire))['status'])
        self.assertFalse(self.k.records.latest('ACTION'))
        self.assertEqual(wire['eval_count'], self.k.records.get('INVOCATION', key)['charged_output'])

    def test_provider_usage_cannot_spend_beyond_role_budget_then_act(self):
        self.start()
        key, request = self.loop.begin('OPERATOR', self.episode)
        limit = request.prompt_tokens + self.k.config.budgets.output_tokens
        self.k.config = self.k.config.model_copy(update={'budgets': self.k.config.budgets.model_copy(update={'operator_tokens': limit})})
        wire = load_json(self.backend.wire(request, action({'operation': 'restart', 'resource': 'api'})))
        wire.update(prompt_eval_count=limit, eval_count=1)
        self.assertEqual('UNKNOWN', self.loop.deliver(key, canonical_bytes(wire))['status'])
        self.assertFalse(self.k.records.latest('ACTION'))

    def test_steward_stop_prevents_semantic_effects(self):
        self.start()
        self.give(outcome())
        _, _, result = self.give(response({'kind': 'PROPOSE', 'proposal': proposal()},
            {'kind': 'WITHDRAW', 'text': 'Stop consolidation', 'communication': 'NO_FURTHER_CALLS'}), 'STEWARD')
        self.assertEqual('HELD', result['status'])
        self.assertIsNone(self.k.memory.head)

    def test_interrupted_removal_remains_blocked_and_can_finish(self):
        self.start()
        event = self.owner.evidence(b'removal-interruption-marker-143')
        pid = self.store._db.execute('SELECT payload_id FROM events WHERE id=?', (event,)).fetchone()[0]
        self.owner.run_control('PAUSE', 'Remove synthetic content')
        scope = closure(self.store, self.run, [pid])['payload_ids']
        def fail(point):
            if point == 'retention.after_decision':
                raise RuntimeError('Interrupted cleanup')
        self.store._fault = fail
        with self.assertRaises(RuntimeError):
            remove_content(self.owner, [pid], expected_scope=scope, justification='PRIVACY', note='Synthetic accountable removal')
        self.store._fault = lambda point: None
        with self.assertRaises(EvidenceUnavailable):
            self.store.read_payload(self.run, pid)
        key = self.store.removals.all()[0]['id']
        self.store.close()
        self.store = Store(self.path, busy_timeout_ms=100)
        self.assertEqual('COMPLETED', finish_removal(self.store, key)['status'])
        self.assertNotIn(b'removal-interruption-marker-143', self.path.read_bytes())

    def test_lesson_wording_history_and_terminal_commitments(self):
        self.start()
        lesson = {'kind': 'INVARIANT', 'key': 'rule', 'wording': 'Original', 'scope': 'services',
                  'status': 'CURRENT', 'assessment': 'Tentative'}
        first = self.owner.correct(proposal(updates=[lesson]), base=None, note='Routine lesson')
        key = first['bindings']['rule']
        self.owner.correct(proposal(updates=[lesson | {'key': key, 'wording': 'Revised'}]),
                           base=first['state_id'], note='New evidence changes the lesson')
        self.assertEqual('RETIRED', self.k.records.get('PILOT_LESSON_VERSION', key + ':1')['status'])
        self.assertEqual('CURRENT', self.k.records.get('PILOT_LESSON_VERSION', key + ':2')['status'])
        self.reopen()
        self.assertEqual(2, self.k.memory.objects()[key]['wording_version'])

    def test_unknown_foreign_and_over_scope_permissions(self):
        self.start()
        for operation in ({'operation': 'restart', 'resource': 'worker'},
                          {'operation': 'restart', 'resource': 'foreign'},
                          {'operation': 'shell', 'resource': 'api', 'command': 'whoami'}):
            with self.subTest(operation=operation):
                _, _, result = self.give(action(operation))
                self.assertEqual('REJECTED', result['status'])
        self.assertFalse(self.k.records.latest('ACTION'))


class PilotAllocationTests(unittest.TestCase):
    def test_allocation_cli_inspection_and_no_replacement(self):
        from bicameral_agent.pilot.__main__ import main
        import io
        from contextlib import redirect_stdout
        with tempfile.TemporaryDirectory() as temporary, patch('bicameral_agent.backends.ollama.HTTPConnection',
                side_effect=AssertionError('No network for allocation or controls')):
            root = Path(temporary)
            source = root / 'package'
            source.mkdir()
            config, bodies = package(FakeBackend())
            (source / 'activity.json').write_bytes(canonical_bytes({'activity': config['activity'], 'budgets': config['budgets'],
                'seeds': [7], 'order_seed': 0}))
            for key, filename in [('fixture', 'fixture'), ('test_clock', 'clock'), ('tasks', 'tasks'), ('model', 'model'), ('settings', 'settings')]:
                (source / (filename + '.json')).write_bytes(bodies[key])
            destination = root / 'batch'
            index = allocate(source, destination)
            self.assertEqual(3, len(index['allocation']))
            self.assertEqual({'A', 'B', 'C'}, {e['arm'] for e in index['allocation']})
            with self.assertRaises(FileExistsError):
                allocate(source, destination)
            path = destination / index['allocation'][0]['file']
            output = io.StringIO()
            with redirect_stdout(output):
                main(['status', str(path)])
            self.assertEqual('CREATED', load_json(output.getvalue().encode())['state'])
            # Allocation itself never infers authorization for a model transport.
            with self.assertRaises(ValueError):
                main(['run', str(destination), '--tokenizer-directory', str(root)])


if __name__ == '__main__':
    unittest.main()
