"""Scripted diagnostic strategies, not model results or evidence that A beats C."""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from bicameral_agent.contracts.base import canonical_bytes, load_json, parse
from bicameral_agent.kernel.fixture import FixtureDefinition, ClockPlan
from bicameral_agent.pilot.batch import allocate, attach, report_run, run_trajectory
from bicameral_agent.pilot.fixture import CompatibilityDefinition, load_fixture
from bicameral_agent.pilot.inputs import PilotInputs
from bicameral_agent.pilot.loop import Loop, SimpleSession
from bicameral_agent.storage import Store
from bicameral_agent.storage.store import identifier
from tests.test_pilot_runtime import FakeBackend, ROOT, action, package, response


ASSETS = ROOT / 'pilot/compatibility'


def compatibility_package(backend, arm='A'):
    config, bodies = package(backend, arm)
    for key, filename in [('fixture', 'fixture'), ('test_clock', 'clock'), ('tasks', 'tasks')]:
        bodies[key] = (ASSETS / (filename + '.json')).read_bytes()
    config['activity']['resources'] = [s['resource'] for s in load_json(bodies['fixture'])['services']]
    config['activity']['objective'] = 'Repair the requested simulated services; use observed compatibility and avoid unnecessary restarts.'
    config['budgets'].update(operator_calls=64, actions=64, episodes=5)
    config['artifacts'] = {key: sha256(raw).hexdigest() for key, raw in bodies.items()}
    return config, bodies


def observations(payload):
    """Only the ordinary action/result exchanges included in this request."""
    command, result = None, []
    for exchange in payload['exchange']:
        task = exchange.get('response', {}).get('task')
        if task and task['kind'] == 'ACTION':
            command = task['operation']
        value = exchange.get('result', {})
        if value.get('status') == 'ACTION' and command:
            result.append((command, value['observation']['observation'], value['event_id']))
            command = None
    return result


def lesson_key(observation, policy):
    return observation['family'] if policy == 'stale' else f"{observation['family']}:{observation['release']}"


def retained_lessons(payload, policy):
    memory = payload['memory']
    if not memory or policy == 'rediscover':
        return {}
    if payload['arm'] == 'C':
        return load_json(memory['handoff'].encode())
    return {obj['scope']: load_json(obj['wording'].encode()) for obj in memory['selected']}


def learned_lessons(payload, policy):
    lessons = retained_lessons(payload, policy)
    for operation, observation, event in observations(payload):
        if operation['operation'] == 'restart' and observation['health'] == 'HEALTHY':
            key = lesson_key(observation, policy)
            if policy != 'stale' or key not in lessons:
                lessons[key] = {'mode': observation['mode'], 'evidence': event}
    return lessons


def strategy(payload, role, policy):
    """Stateless: no fixture, scoring, task schedule, private cache or future inputs."""
    lessons = learned_lessons(payload, policy)
    seen = observations(payload)
    if role == 'STEWARD':
        if policy == 'rediscover':
            lessons = {}
        evidence = list(dict.fromkeys(item['evidence'] for item in lessons.values()))
        if payload['arm'] == 'C':
            return response({'kind': 'PROPOSE', 'proposal': {
                'handoff': canonical_bytes(lessons).decode(), 'evidence': evidence}})
        existing = {o['scope']: o for o in (payload['memory'] or {}).get('selected', [])}
        updates, selected = [], []
        for index, (scope, item) in enumerate(lessons.items()):
            old = existing.get(scope)
            key = old['id'] if old else f'lesson_{index}'
            wording = canonical_bytes(item).decode()
            if not old or old['wording'] != wording:
                updates.append({'kind': 'INVARIANT', 'key': key, 'scope': scope, 'wording': wording,
                    'status': 'CURRENT', 'assessment': 'Observed synthetic compatibility; scope matters.',
                    'supporting': [item['evidence']]})
            selected.append({'object_type': 'INVARIANT', 'key': key})
        return response({'kind': 'PROPOSE', 'proposal': {'handoff': 'Use the scoped observations.',
            'evidence': evidence, 'updates': updates, 'selected': selected}})

    targets = list(dict.fromkeys(re.findall(r'\bsvc-[a-z]\b', payload['work'])))
    for resource in targets:
        history = [(op, obs, event) for op, obs, event in seen if obs['resource'] == resource]
        if not history:
            return action({'operation': 'inspect', 'resource': resource})
        current = history[-1][1]
        if current['health'] == 'HEALTHY' and current['enabled']:
            continue
        tried = {obs['mode'] for op, obs, _ in history if op['operation'] == 'restart'}
        known = lessons.get(lesson_key(current, policy))
        if policy == 'stale' and known and tried:
            return response({'kind': 'OUTCOME', 'outcome': 'BLOCKED',
                'explanation': 'The retained family-only rule failed; this diagnostic strategy does not revise it.',
                'evidence': [history[-1][2]]})
        modes = [known['mode']] if known else []
        modes += [mode for mode in ('PRIMARY', 'SECONDARY') if mode not in modes]
        desired = next((mode for mode in modes if mode not in tried), None)
        if desired is None:
            return response({'kind': 'OUTCOME', 'outcome': 'BLOCKED', 'explanation': 'Both observed trials failed.'})
        if not current['enabled']:
            return action({'operation': 'set_config', 'resource': resource, 'field': 'enabled', 'value': 'ENABLED'})
        if current['mode'] != desired:
            return action({'operation': 'set_config', 'resource': resource, 'field': 'mode', 'value': desired})
        return action({'operation': 'restart', 'resource': resource})
    return response({'kind': 'OUTCOME', 'outcome': 'COMPLETED',
        'explanation': 'All requested services observed enabled and healthy.',
        'evidence': [event for _, obs, event in seen if obs['health'] == 'HEALTHY']})


class StrategyBackend(FakeBackend):
    def __init__(self, policy):
        super().__init__()
        self.policy = policy

    def generate(self, request, *, cancel):
        self.requests.append(request)  # Inspection only; never read by the strategy.
        wire = load_json(request.wire)
        user = wire['prompt'].split('<|im_start|>user\n', 1)[1].split('<|im_end|>', 1)[0]
        payload = load_json(user.encode())
        if 'purpose' in payload:
            value = {'participation': None}
        else:
            role = 'STEWARD' if 'You are the Steward.' in wire['prompt'] else 'OPERATOR'
            value = strategy(payload, role, self.policy)
        return self.wire(request, value)


class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        network = patch('bicameral_agent.backends.ollama.HTTPConnection', side_effect=AssertionError('No live transport'))
        network.start()
        self.addCleanup(network.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    @contextmanager
    def host(self, policy='scoped', arm='A', edit=None):
        backend = StrategyBackend(policy)
        config, bodies = compatibility_package(backend, arm)
        if edit:
            edit(config, bodies)
        config['artifacts'] = {key: sha256(raw).hexdigest() for key, raw in bodies.items()}
        store = Store(Path(self.temp.name) / (identifier() + '.sqlite'), busy_timeout_ms=100)
        try:
            store.retain_configuration(canonical_bytes(config), bodies)
            kernel, owner = attach(store, backend)
            yield kernel, owner, backend
        finally:
            store.close()

    def start(self, kernel, owner):
        owner.run_control('ACTIVATE', 'Synthetic diagnostic')
        owner.create_objective(kernel.config.activity.objective)
        owner.issue_grant([{'operation': op, 'resources': list(kernel.config.activity.resources)}
                           for op in ('set_config', 'restart')], invocation_limit=64)
        kernel.fixture.advance(kernel.fixture._clock_cap, 1)
        loop = Loop(kernel, StrategyBackend('scoped'))
        episode = loop.episode('Repair svc-a to enabled and HEALTHY.')
        return loop, episode

    def give(self, loop, episode, operation):
        key, request = loop.begin('OPERATOR', episode)
        result = loop.deliver(key, loop.backend.wire(request, action(operation)))
        self.assertEqual('ACTION', result['status'], result)
        return result['observation']['observation']

    def test_strategies_distinguish_history_and_scope_without_favoring_a(self):
        expected = {'scoped': (['PASS'] * 5, [1, 0, 0, 0, 0], 16),
                    'rediscover': (['PASS'] * 5, [1, 0, 1, 0, 1], 18),
                    'stale': (['PASS', 'PASS', 'PASS', 'FAIL', 'FAIL'], [1, 0, 0, 1, 1], 18)}
        for policy, (results, mistakes, actions) in expected.items():
            for arm in ('A', 'C'):
                with self.subTest(policy=policy, arm=arm), self.host(policy, arm) as (kernel, owner, backend):
                    report = run_trajectory(kernel, owner, backend)
                    self.assertEqual(results, [t['result'] for t in report['tasks']], report)
                    self.assertEqual(mistakes, [t['score']['metrics']['unsuccessful_restarts'] for t in report['tasks']])
                    self.assertEqual(actions, report['tool_calls'])
                    self.assertEqual(sum(mistakes), report['unsuccessful_restarts'])
                    self.assertEqual(0, report['human_interventions'])
                    self.assertEqual(5, len(kernel.records.latest('PILOT_EPISODE')))
                    self.assertEqual(5, report['steward_calls'])
                    self.assertEqual('COMPLETED', report['state'])
                    self.assertTrue(all('healthy_mode' not in load_json(r.wire)['prompt'] for r in backend.requests))
                    if policy == 'scoped':
                        if arm == 'A':
                            lessons = {o['scope']: load_json(o['wording'].encode()) for o in kernel.memory.objects().values()}
                        else:
                            self.assertFalse(kernel.memory.objects())
                            lessons = load_json(kernel.memory.head['handoff'].encode())
                        self.assertEqual('SECONDARY', lessons['Cedar:1']['mode'])
                        self.assertEqual('PRIMARY', lessons['Cedar:2']['mode'])

    def test_same_visible_start_does_not_reveal_the_working_mode(self):
        def flip(config, bodies):
            fixture = load_json(bodies['fixture'])
            fixture['rules'][0]['healthy_mode'] = 'PRIMARY'
            bodies['fixture'] = canonical_bytes(fixture)
        starts, outcomes = [], []
        for edit in (None, flip):
            with self.host(edit=edit) as (kernel, owner, _):
                loop, episode = self.start(kernel, owner)
                starts.append(self.give(loop, episode, {'operation': 'inspect', 'resource': 'svc-a'}))
                outcomes.append(self.give(loop, episode, {'operation': 'restart', 'resource': 'svc-a'})['health'])
                self.assertIsNone(report_run(kernel)['unsuccessful_restarts'])
        self.assertEqual(starts[0], starts[1])
        self.assertEqual(['DEGRADED', 'HEALTHY'], outcomes)

    def test_hidden_rule_table_and_future_tasks_are_not_retrievable(self):
        with self.host() as (kernel, owner, backend):
            loop, episode = self.start(kernel, owner)
            inputs = PilotInputs(kernel)
            for name in ('fixture', 'test_clock', 'tasks', 'source'):
                key = kernel.store._db.execute('SELECT payload_id FROM artifacts WHERE run_id=? AND name=?',
                                               (kernel.run_id, name)).fetchone()[0]
                with self.subTest(name=name), self.assertRaises((ValueError, PermissionError)):
                    inputs.retrieve(SimpleSession(kernel, 'OPERATOR'), episode, canonical_bytes({
                        'request_id': identifier(), 'query': {'kind': 'PAYLOAD', 'payload_id': key}, 'cursor': None}))
            key, request = loop.begin('OPERATOR', episode)
            prompt = load_json(request.wire)['prompt']
            self.assertNotIn('healthy_mode', prompt)
            self.assertNotIn('changed-release', prompt)
            loop.deliver(key, loop.backend.wire(request, action({'operation': 'inspect', 'resource': 'svc-a'})))

    def test_enabled_and_dependency_checks_still_apply(self):
        def dependent(config, bodies):
            fixture = load_json(bodies['fixture'])
            fixture['services'][0]['dependency'] = 'svc-b'
            bodies['fixture'] = canonical_bytes(fixture)
            clock = load_json(bodies['test_clock'])
            clock['steps'][0]['changes'][0]['dependency'] = 'svc-b'
            bodies['test_clock'] = canonical_bytes(clock)
        with self.host(edit=dependent) as (kernel, owner, _):
            loop, episode = self.start(kernel, owner)
            self.give(loop, episode, {'operation': 'set_config', 'resource': 'svc-a', 'field': 'mode', 'value': 'SECONDARY'})
            self.assertEqual('DEGRADED', self.give(loop, episode, {'operation': 'restart', 'resource': 'svc-a'})['health'])
            self.give(loop, episode, {'operation': 'restart', 'resource': 'svc-b'})
            self.assertEqual('HEALTHY', self.give(loop, episode, {'operation': 'restart', 'resource': 'svc-a'})['health'])
            self.give(loop, episode, {'operation': 'set_config', 'resource': 'svc-a', 'field': 'enabled', 'value': 'DISABLED'})
            self.assertEqual('STOPPED', self.give(loop, episode, {'operation': 'restart', 'resource': 'svc-a'})['health'])

    def test_strict_profiles_serialization_and_legacy_contracts(self):
        raw, clock = (ASSETS / 'fixture.json').read_bytes(), (ASSETS / 'clock.json').read_bytes()
        _, parsed, _ = load_fixture(raw, clock)
        self.assertEqual(parsed, parse(CompatibilityDefinition, canonical_bytes(parsed)))
        original = load_json(raw)
        invalid = []
        for field, value in [('release', True), ('release', 0), ('healthy_mode', 'SECONDARY')]:
            fixture = deepcopy(original)
            fixture['services'][0][field] = value
            invalid.append(fixture)
        fixture = deepcopy(original)
        fixture['rules'].append(fixture['rules'][0])
        invalid.append(fixture)
        fixture = deepcopy(original)
        fixture['rules'].pop(0)
        invalid.append(fixture)
        for fixture in invalid:
            with self.subTest(fixture=fixture), self.assertRaises(ValueError):
                load_fixture(canonical_bytes(fixture), clock)
        future = load_json(clock)
        future['steps'][3]['changes'][0]['release'] = 99
        with self.assertRaises(ValueError):
            load_fixture(raw, canonical_bytes(future))
        with self.assertRaises(ValueError):
            load_fixture(b'[]', clock)
        with self.assertRaises(ValueError):
            parse(FixtureDefinition, raw)
        with self.assertRaises(ValueError):
            parse(ClockPlan, clock)
        legacy = (ROOT / 'pilot/v0b/fixture.json').read_bytes()
        self.assertEqual(load_json(legacy), load_json(canonical_bytes(parse(FixtureDefinition, legacy))))

    def test_allocation_reuses_three_arm_host_and_rejects_invalid_plan_before_writing(self):
        source = Path(self.temp.name) / 'package'
        source.mkdir()
        config, bodies = compatibility_package(StrategyBackend('scoped'))
        (source / 'activity.json').write_bytes(canonical_bytes({'activity': config['activity'], 'budgets': config['budgets'],
                                                              'seeds': [7], 'order_seed': 0}))
        for key, filename in [('fixture', 'fixture'), ('test_clock', 'clock'), ('tasks', 'tasks'),
                              ('model', 'model'), ('settings', 'settings')]:
            (source / (filename + '.json')).write_bytes(bodies[key])
        destination = Path(self.temp.name) / 'batch'
        index = allocate(source, destination)
        self.assertEqual({'A', 'B', 'C'}, {r['arm'] for r in index['allocation']})
        for entry in index['allocation']:
            store = Store(destination / entry['file'], busy_timeout_ms=100)
            try:
                backend = StrategyBackend('scoped' if entry['arm'] != 'B' else 'rediscover')
                kernel, owner = attach(store, backend)
                result = run_trajectory(kernel, owner, backend)
                self.assertEqual(['PASS'] * 5, [t['result'] for t in result['tasks']])
            finally:
                store.close()
        invalid = load_json(bodies['test_clock'])
        invalid['steps'][0]['changes'][0]['release'] = 99
        (source / 'clock.json').write_bytes(canonical_bytes(invalid))
        rejected = Path(self.temp.name) / 'invalid-batch'
        with self.assertRaises(ValueError):
            allocate(source, rejected)
        self.assertFalse(rejected.exists())


if __name__ == '__main__':
    unittest.main()
