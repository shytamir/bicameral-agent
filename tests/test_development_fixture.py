"""Synthetic fixture/scorer controls; never model performance or A/C evidence."""
from hashlib import sha256
import copy
from unittest.mock import patch
from bicameral_agent.backends.development import check_current_task
from bicameral_agent.backends.prepare import ROOT, validate_assets
from bicameral_agent.backends.review import V0B_ASSETS
from bicameral_agent.contracts.base import canonical_bytes, load_json
from bicameral_agent.kernel.fixture import Fixture
from bicameral_agent.storage import EvidenceUnavailable
from bicameral_agent.storage.store import identifier
from tests.kernel_fixtures import KernelCase, CHAMBER_KEYS, kernel_configuration


def op(operation, resource, **arguments):
    return {'operation': operation, 'resource': resource, **arguments}


def current_observation_solution():
    # Explicit path for fault injection. Policy controls below choose their
    # actions from returned observations rather than this prewritten witness.
    return [
        [op('inspect', 'api'), op('inspect', 'database'),
         op('set_config', 'api', field='mode', value='PRIMARY'), op('restart', 'api')],
        [op('read_config', 'database')],
        [op('inspect', 'api'), op('inspect', 'database'), op('set_config', 'database', field='mode', value='PRIMARY'),
         op('restart', 'database'), op('set_config', 'api', field='mode', value='PRIMARY'), op('restart', 'api')],
        [op('inspect', 'database'), op('inspect', 'api'), op('set_config', 'database', field='enabled', value='ENABLED'),
         op('restart', 'database'), op('restart', 'api')],
        [op('inspect', 'worker'), op('inspect', 'database'), op('set_config', 'worker', field='enabled', value='ENABLED'),
         op('set_config', 'worker', field='mode', value='PRIMARY'), op('restart', 'worker')],
        [op('read_health', 'api')],
    ]


class DevelopmentFixtureTests(KernelCase):
    def prepare_run(self):
        _, _, self.draft, _, _, self.tasks = validate_assets(ROOT)
        config, artifacts = kernel_configuration()
        config['budgets']['actions_per_trajectory'] = self.draft.fixture_actions_per_run
        artifacts['fixture'] = (ROOT / V0B_ASSETS / 'fixture.json').read_bytes()
        artifacts['test_clock'] = (ROOT / V0B_ASSETS / 'clock.json').read_bytes()
        tools = load_json(artifacts['tools'])
        tools['operations'] = [item | {'resources': list(self.draft.grant_resources)} for item in tools['operations']]
        artifacts['tools'] = canonical_bytes(tools)
        for name in ('fixture', 'tools'):
            config['artifacts'][name] = sha256(artifacts[name]).hexdigest()
        config['test_clock'] = sha256(artifacts['test_clock']).hexdigest()
        self.run = self.store.retain_configuration(canonical_bytes(config), artifacts)
        self.attach()
        self.activate()
        self.fixture = Fixture(self.k)
        self.operator = self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR'])
        self.grant_id = self.h.confirm(self.h.issue_grant([
            {'operation': name, 'resources': list(self.draft.grant_resources)} for name in self.draft.grant_operations
        ], invocation_limit=self.draft.grant_invocation_limit_per_run, expires_at=None).confirmation)['result']

    def perform(self, episode, operation):
        request = {'request_id': identifier(), 'episode_id': episode,
            'grant_id': self.grant_id if operation['operation'] in self.draft.grant_operations else None,
            'grounds': 'Synthetic scorer control', 'expected': None,
            'no_meaningful_postcondition': 'Predicates checked independently after the tick', 'operation': operation}
        result = self.fixture.execute(self.operator, canonical_bytes(request))
        self.assertEqual('RETURNED', result['status'])
        return result

    def close_episode(self, episode):
        with self.store._transaction('synthetic-control-close'):
            revision, state = self.store.control(self.run, episode)
            self.store._control(self.run, episode, state.model_copy(update={
                'phase': 'CLOSED', 'disposition': 'SKIPPED'}), expected_revision=revision)

    def execute(self, operations):
        episode = self.episode()
        results = [self.perform(episode, operation) for operation in operations]
        self.close_episode(episode)
        return results

    def observation_policy(self, *, remember):
        """Finite transparent solver: no hidden schedule, fixture-state reads,
        prior journal or cross-tick cache. Only the reminder variant keeps the
        explicit future request. This is a fixture control, not an A/C model.
        """
        self.prepare_run()
        reminder, results, call_counts, mutations = None, [], [], 0
        for task in self.tasks:
            self.fixture.advance(self.fixture._clock_cap, task.tick)
            episode, cache, actions = self.episode(), {}, []

            def act(operation):
                result = self.perform(episode, operation)
                actions.append(operation)
                # Deliver only the returned tool observation to the policy.
                # No hidden-change or evaluator payload is read here.
                event = self.store._db.execute('SELECT payload_id FROM events WHERE run_id=? AND id=?',
                                               (self.run, result['result_event_id'])).fetchone()
                return load_json(self.store.read_payload(self.run, event[0]))['observation']

            def repair(resource):
                if resource not in cache:
                    cache[resource] = act(op('inspect', resource))
                state = cache[resource]
                if state['dependency'] is not None:
                    repair(state['dependency'])
                changed = False
                for field, needed, value in (('enabled', True, 'ENABLED'), ('mode', 'PRIMARY', 'PRIMARY')):
                    if state[field] != needed:
                        state = act(op('set_config', resource, field=field, value=value))
                        changed = True
                if changed or state['health'] != 'HEALTHY':
                    state = act(op('restart', resource))
                cache[resource] = state

            prompt = task.prompt.lower()
            if remember and 'verify api health again when task tick 6 arrives' in prompt:
                reminder = ('api', 6)
            if 'make no change' in prompt:
                act(op('read_config', 'database'))
            else:
                for target in ('database', 'api', 'worker'):
                    if target in prompt:
                        repair(target)
            if reminder is not None and task.tick == reminder[1]:
                act(op('read_health', reminder[0]))
                reminder = None
            self.close_episode(episode)
            results.append(check_current_task(self.k, task))
            call_counts.append(len(actions) + 1)
            mutations += sum(action['operation'] in self.draft.grant_operations for action in actions)
        return results, call_counts, mutations

    def trajectory(self, operations):
        self.prepare_run()
        results = []
        for task, actions in zip(self.tasks, operations, strict=True):
            self.fixture.advance(self.fixture._clock_cap, task.tick)
            self.execute(actions)
            before = self.store._db.total_changes
            result = check_current_task(self.k, task)
            self.assertEqual(before, self.store._db.total_changes)
            self.assertFalse(self.store._db.in_transaction)
            results.append(result)
        return results

    def test_idle_never_receives_success_credit(self):
        results = self.trajectory([[] for _ in range(6)])
        self.assertEqual(['FAIL'] * 6, [r['mechanical_result'] for r in results])

    def test_current_state_solver_without_reminder_loses_only_delayed_check(self):
        results, _, _ = self.observation_policy(remember=False)
        self.assertEqual(['PASS'] * 5 + ['FAIL'], [r['mechanical_result'] for r in results])

    def test_remembered_check_passes_and_caps_cover_bounded_stress_case(self):
        results, calls, mutations = self.observation_policy(remember=True)
        self.assertEqual(['PASS'] * 6, [r['mechanical_result'] for r in results])
        self.assertEqual([5, 2, 7, 6, 6, 2], calls)
        self.assertEqual(12, mutations)
        # Keep a queued tick-6 read plus a separate wake read/outcome. These
        # deliberately bounded stress scenarios are not empirical frequencies.
        stress = [count + 3 for count in calls]  # invalid reply, retrieval, verification
        communication = self.draft.review_calls_per_run + self.draft.closing_calls_per_run
        self.assertLessEqual(max(stress), self.draft.operator_calls_per_episode)
        self.assertEqual(50, sum(stress) + 2 + communication)
        self.assertLessEqual(sum(stress) + 2 + communication,
                             self.draft.operator_calls_including_communication_per_run)
        self.assertLessEqual(sum(calls) - len(calls) + 1 + len(calls), self.draft.fixture_actions_per_run)
        self.assertLessEqual(len(calls) + 1, self.draft.episodes_per_run)
        self.assertLessEqual(mutations, self.draft.grant_invocation_limit_per_run)
        self.assertGreater(sum(calls) + 2 + communication, 26)

    def test_old_local_recipe_is_contradicted_by_dependency_change(self):
        actions = current_observation_solution()
        actions[2] = [op('inspect', 'api'), op('set_config', 'api', field='mode', value='PRIMARY'), op('restart', 'api')]
        result = self.trajectory(actions)[2]
        self.assertEqual('FAIL', result['mechanical_result'])
        self.assertFalse(next(c for c in result['checks'] if c.get('field') == 'health')['satisfied'])

    def test_state_only_scoring_reproduces_the_two_false_positives(self):
        actions = current_observation_solution()
        actions[1] = actions[-1] = []
        results = self.trajectory(actions)
        for index in (1, 5):
            self.assertTrue(all(c['satisfied'] for c in results[index]['checks'] if c['kind'] == 'STATE'))
            self.assertEqual('FAIL', results[index]['mechanical_result'])

    def test_no_mutations_includes_reverted_changes(self):
        actions = current_observation_solution()
        actions[1] += [op('set_config', 'database', field='mode', value='SECONDARY'),
                       op('set_config', 'database', field='mode', value='PRIMARY')]
        self.assertEqual('FAIL', self.trajectory(actions)[1]['mechanical_result'])

    def test_observation_must_precede_mutation_when_explicitly_required(self):
        actions = current_observation_solution()
        actions[0] = actions[0][1:] + actions[0][:1]
        self.assertEqual('FAIL', self.trajectory(actions)[0]['mechanical_result'])

    def test_read_health_does_not_count_as_configuration_observation(self):
        actions = current_observation_solution()
        actions[1] = [op('read_health', 'database')]
        self.assertEqual('FAIL', self.trajectory(actions)[1]['mechanical_result'])

    def test_same_tick_wake_observation_counts_but_narration_or_earlier_observation_does_not(self):
        actions = current_observation_solution()
        actions[-1] = []
        self.trajectory(actions)
        with self.store._transaction('synthetic-narration'):
            self.k.event({'kind': 'FIXTURE_OBSERVATION', 'observation': {'resource': 'api', 'health': 'HEALTHY'}},
                         role='OPERATOR', source='A')
        self.assertEqual('FAIL', check_current_task(self.k, self.tasks[-1])['mechanical_result'])
        # This extra Episode models wake tool work at the same tick. Existing
        # scheduler tests separately prove actual Commitment delivery.
        self.execute([op('inspect', 'api')])
        self.assertEqual('PASS', check_current_task(self.k, self.tasks[-1])['mechanical_result'])
        with self.assertRaises(ValueError):
            check_current_task(self.k, self.tasks[0])

    def test_unavailable_observation_and_open_episode_cannot_pass(self):
        self.trajectory(current_observation_solution())
        result_id = self.k.records.latest('ACTION')[-1][1]['result_event_id']
        payload = next(e['payload_id'] for e in self.store.events(self.run) if e['id'] == result_id)
        read = self.store.read_payload

        def removed(run, key):
            if key == payload:
                raise EvidenceUnavailable('Synthetic unavailable observation')
            return read(run, key)

        with patch.object(self.store, 'read_payload', side_effect=removed):
            self.assertEqual('INDETERMINATE', check_current_task(self.k, self.tasks[-1])['mechanical_result'])

        def malformed(run, key):
            raw = read(run, key)
            if key == payload:
                body = load_json(raw)
                del body['observation']['health']
                return canonical_bytes(body)
            return raw

        with patch.object(self.store, 'read_payload', side_effect=malformed):
            self.assertEqual('INDETERMINATE', check_current_task(self.k, self.tasks[-1])['mechanical_result'])
        self.episode()
        with self.assertRaises(ValueError):
            check_current_task(self.k, self.tasks[-1])

    def test_unknown_foreign_stale_or_misbound_action_cannot_supply_observation(self):
        self.trajectory(current_observation_solution())
        original = self.k.records.latest('ACTION')
        for change in ({'status': 'UNKNOWN'}, {'result_event_id': identifier()},
                       {'result_event_id': original[0][1]['result_event_id']},
                       {'episode_id': identifier()}):
            changed = copy.deepcopy(original)
            changed[-1][1].update(change)
            with self.subTest(change=change), patch.object(self.k.records, 'latest', return_value=changed):
                self.assertEqual('INDETERMINATE', check_current_task(self.k, self.tasks[-1])['mechanical_result'])
