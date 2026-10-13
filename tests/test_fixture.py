import copy
import os
import subprocess
import sys
from bicameral_agent.contracts.base import canonical_bytes
from bicameral_agent.kernel.fixture import Fixture, ActionRequest
from bicameral_agent.storage.store import identifier, RequestConflict
from tests.kernel_fixtures import KernelCase, CHAMBER_KEYS


class FixtureTests(KernelCase):
    def test_task_clock_sealed_order_freeze_and_evaluator_isolation(self):
        with self.assertRaises(PermissionError):
            self.fixture.advance(object(), 1)
        with self.assertRaises(ValueError):
            self.fixture.advance(self.fixture._clock_cap, 1)
        with self.store._transaction('synthetic-close'):
            revision, episode = self.store.control(self.run, self.episode_id)
            self.store._control(self.run, self.episode_id, episode.model_copy(update={'phase': 'CLOSED', 'disposition': 'SKIPPED'}),
                                expected_revision=revision)
        with self.assertRaises(ValueError):
            self.fixture.advance(self.fixture._clock_cap, 2)
        first = self.fixture.advance(self.fixture._clock_cap, 1)
        self.assertEqual(first, self.fixture.advance(self.fixture._clock_cap, 1))
        self.fixture.advance(self.fixture._clock_cap, 2)
        self.assertEqual(2, self.k.run()[1].task_tick)
        self.assertFalse(self.fixture.service('api').enabled)
        hidden = [e for e in self.store.events(self.run) if e['visibility'] == 'EVALUATOR']
        self.assertEqual(1, len(hidden))

    def test_postcondition_field_types_and_unknown_field_rejection(self):
        for field, value in [('enabled', 1), ('restarts', True), ('mode', 'HEALTHY')]:
            request = self.request({'operation': 'inspect', 'resource': 'api'}, expected={'field': field, 'equals': value})
            with self.assertRaises(ValueError):
                self.fixture.execute(self.operator, canonical_bytes(request))
        request = self.request({'operation': 'inspect', 'resource': 'api'})
        parsed = ActionRequest.model_validate_json(canonical_bytes(request), strict=True)
        self.assertEqual(canonical_bytes(request), canonical_bytes(parsed))
        request['arbitrary_memory'] = 'forbidden'
        with self.assertRaises(ValueError):
            self.fixture.execute(self.operator, canonical_bytes(request))
    def setUp(self):
        super().setUp()
        self.activate()
        self.episode_id = self.episode()
        self.fixture = Fixture(self.k)
        self.operator = self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR'])

    def request(self, operation, grant=None, expected=None):
        return {'request_id': identifier(), 'episode_id': self.episode_id, 'grant_id': grant,
                'grounds': 'Scripted fixture test', 'expected': expected,
                'no_meaningful_postcondition': 'Observation only' if expected is None else None,
                'operation': operation}

    def test_finite_channels_and_source_roles(self):
        for operation in ({'operation': 'shell', 'resource': 'api', 'command': 'x'},
                          {'operation': 'set_config', 'resource': 'api', 'field': 'notes', 'value': 'remember'},
                          {'operation': 'set_config', 'resource': 'api', 'field': 'mode', 'value': 'arbitrary text'},
                          {'operation': 'inspect', 'resource': 'api', 'path': '../secret'},
                          {'operation': 'inspect', 'resource': 'unregistered'}):
            with self.assertRaises(ValueError):
                self.fixture.execute(self.operator, canonical_bytes(self.request(operation)))
        with self.assertRaises(PermissionError):
            self.fixture.execute(self.k.chamber('STEWARD', CHAMBER_KEYS['STEWARD']),
                                 canonical_bytes(self.request({'operation': 'inspect', 'resource': 'api'})))
        self.assertEqual([], self.k.records.latest('ACTION'))

    def test_set_restart_postconditions_and_exact_retries(self):
        grant = self.grant(operation='set_config', limit=1)
        request = self.request({'operation': 'set_config', 'resource': 'api', 'field': 'mode', 'value': 'PRIMARY'}, grant,
                               {'field': 'mode', 'equals': 'PRIMARY'})
        accepted = self.fixture.execute(self.operator, canonical_bytes(request))
        self.assertTrue(accepted['postcondition_satisfied'])
        self.assertEqual(accepted, self.fixture.execute(self.operator, canonical_bytes(request)))
        changed = copy.deepcopy(request); changed['operation']['value'] = 'SECONDARY'
        with self.assertRaises(RequestConflict):
            self.fixture.execute(self.operator, canonical_bytes(changed))
        restart = self.grant(operation='restart', limit=1)
        result = self.fixture.execute(self.operator, canonical_bytes(self.request({'operation': 'restart', 'resource': 'api'},
            restart, {'field': 'health', 'equals': 'HEALTHY'})))
        self.assertTrue(result['postcondition_satisfied'])
        self.assertEqual(1, self.fixture.service('api').restarts)
        event = next(e for e in self.store.events(self.run) if e['id'] == result['result_event_id'])
        self.assertEqual(('ENVIRONMENT', 'E'), (event['role'], event['source']))

    def test_unmet_postcondition_is_evidence_not_semantic_state(self):
        result = self.fixture.execute(self.operator, canonical_bytes(self.request({'operation': 'read_health', 'resource': 'api'},
            expected={'field': 'health', 'equals': 'HEALTHY'})))
        self.assertFalse(result['postcondition_satisfied'])
        self.assertEqual('RETURNED', result['status'])
        self.assertEqual({}, self.k.memory.objects())

    def test_snapshot_restoration_is_forward_fixture_only(self):
        grant = self.grant(limit=1)
        self.fixture.execute(self.operator, canonical_bytes(self.request(
            {'operation': 'set_config', 'resource': 'api', 'field': 'mode', 'value': 'PRIMARY'}, grant)))
        before = len(self.store.events(self.run))
        restore = self.grant(operation='restore_snapshot', limit=1)
        self.fixture.execute(self.operator, canonical_bytes(self.request(
            {'operation': 'restore_snapshot', 'resource': 'api', 'snapshot': 'baseline'}, restore)))
        self.assertEqual('SECONDARY', self.fixture.service('api').mode)
        self.assertGreater(len(self.store.events(self.run)), before)
        self.assertEqual('ACTIVE', self.k.run()[1].status)

    def test_process_crash_after_effect_keeps_unknown_and_never_replays(self):
        grant = self.grant(operation='restart', limit=2)
        request = self.request({'operation': 'restart', 'resource': 'api'}, grant)
        script = '''
import os, sys
from bicameral_agent.storage import Store
from bicameral_agent.kernel.authority import Kernel
from bicameral_agent.kernel.fixture import Fixture
from tests.kernel_fixtures import HUMAN_KEY, CHAMBER_KEYS
store=Store(sys.argv[1],busy_timeout_ms=100)
k=Kernel(store,sys.argv[2],human_credential=HUMAN_KEY,chamber_credentials=CHAMBER_KEYS)
fixture=Fixture(k)
store._fault=lambda point: os._exit(74) if point=='fixture-effect.after_commit' else None
fixture.execute(k.chamber('OPERATOR',CHAMBER_KEYS['OPERATOR']),sys.argv[3].encode())
'''
        child = subprocess.run([sys.executable, '-B', '-c', script, str(self.path), self.run, canonical_bytes(request).decode()],
                               capture_output=True, timeout=30)
        self.assertEqual(74, child.returncode, child.stderr.decode())
        self.fixture.recover()
        self.assertEqual('UNKNOWN', self.fixture.action(request['request_id']).status)
        self.assertEqual(1, self.fixture.service('api').restarts)
        self.fixture.execute(self.operator, canonical_bytes(request))
        self.assertEqual(1, self.fixture.service('api').restarts)
        with self.assertRaises(ValueError):
            self.fixture.execute(self.operator, canonical_bytes(self.request({'operation': 'restart', 'resource': 'api'}, grant)))
        self.fixture.observe_uncertain(self.h, request['request_id'])
        self.assertEqual('UNKNOWN', self.fixture.action(request['request_id']).status)
        self.fixture.execute(self.operator, canonical_bytes(self.request({'operation': 'restart', 'resource': 'api'}, grant)))
        self.assertEqual(2, self.fixture.service('api').restarts)

    def test_intent_failure_rolls_back_grant_use(self):
        grant = self.grant(limit=1)
        def fail(point):
            if point == 'action-intent.before_commit':
                raise RuntimeError('synthetic intent failure')
        self.store._fault = fail
        with self.assertRaises(RuntimeError):
            self.fixture.execute(self.operator, canonical_bytes(self.request(
                {'operation': 'set_config', 'resource': 'api', 'field': 'mode', 'value': 'PRIMARY'}, grant)))
        self.store._fault = lambda point: None
        self.assertEqual(0, self.k._grant(grant).used)
        self.assertEqual('SECONDARY', self.fixture.service('api').mode)
