"""A synthetic feasibility witness, not model performance or pilot scoring."""
from hashlib import sha256
from bicameral_agent.backends.prepare import ROOT, validate_assets
from bicameral_agent.contracts.base import canonical_bytes, load_json
from bicameral_agent.kernel.fixture import Fixture
from bicameral_agent.storage.store import identifier
from tests.kernel_fixtures import KernelCase, CHAMBER_KEYS, kernel_configuration


class DevelopmentFixtureTests(KernelCase):
    def test_six_tasks_have_a_finite_solution_within_proposed_operator_caps(self):
        _, _, draft, _, _, tasks = validate_assets(ROOT)
        config, artifacts = kernel_configuration()
        config['budgets']['actions_per_trajectory'] = draft.fixture_actions_per_run
        artifacts['fixture'] = (ROOT / 'pilot/v0b/fixture.json').read_bytes()
        artifacts['test_clock'] = (ROOT / 'pilot/v0b/clock.json').read_bytes()
        tools = load_json(artifacts['tools'])
        tools['operations'] = [op | {'resources': list(draft.grant_resources)} for op in tools['operations']]
        artifacts['tools'] = canonical_bytes(tools)
        for name in ('fixture', 'tools'):
            config['artifacts'][name] = sha256(artifacts[name]).hexdigest()
        config['test_clock'] = sha256(artifacts['test_clock']).hexdigest()
        self.run = self.store.retain_configuration(canonical_bytes(config), artifacts)
        self.attach()
        self.activate()
        fixture = Fixture(self.k)
        operator = self.k.chamber('OPERATOR', CHAMBER_KEYS['OPERATOR'])
        grant = self.h.confirm(self.h.issue_grant([
            {'operation': op, 'resources': list(draft.grant_resources)} for op in draft.grant_operations
        ], invocation_limit=draft.grant_invocation_limit_per_run, expires_at=None).confirmation)['result']

        def op(operation, resource, **arguments):
            return {'operation': operation, 'resource': resource, **arguments}

        witness = [
            [op('inspect', 'api'), op('set_config', 'api', field='mode', value='PRIMARY'), op('restart', 'api')],
            [op('read_config', 'database')],
            [op('inspect', 'api'), op('set_config', 'api', field='mode', value='PRIMARY'), op('restart', 'api')],
            [op('inspect', 'database'), op('inspect', 'api'),
             op('set_config', 'database', field='mode', value='PRIMARY'), op('restart', 'database')],
            [op('inspect', 'worker'), op('inspect', 'database'), op('set_config', 'worker', field='enabled', value='ENABLED'),
             op('set_config', 'worker', field='mode', value='PRIMARY'), op('restart', 'worker')],
            [op('read_health', 'api')],
        ]
        calls = mutations = 0
        for task, operations in zip(tasks, witness, strict=True):
            fixture.advance(fixture._clock_cap, task.tick)
            episode = self.episode()
            # One hypothetical model call per action and one outcome call.
            self.assertLessEqual(len(operations) + 1, draft.operator_calls_per_episode)
            calls += len(operations) + 1
            for operation in operations:
                mutating = operation['operation'] in draft.grant_operations
                mutations += mutating
                request = {'request_id': identifier(), 'episode_id': episode,
                           'grant_id': grant if mutating else None, 'grounds': 'Synthetic feasibility witness',
                           'expected': None, 'no_meaningful_postcondition': 'Criteria checked independently below',
                           'operation': operation}
                result = fixture.execute(operator, canonical_bytes(request))
                self.assertEqual('RETURNED', result['status'])
            for criterion in task.criteria:
                self.assertEqual(criterion.equals, getattr(fixture.service(criterion.resource), criterion.field))
            # This witness tests fixture feasibility only, not the model scheduler or consolidation.
            with self.store._transaction('synthetic-feasibility-close'):
                revision, state = self.store.control(self.run, episode)
                self.store._control(self.run, episode, state.model_copy(update={
                    'phase': 'CLOSED', 'disposition': 'SKIPPED'}), expected_revision=revision)
        self.assertLessEqual(calls + draft.review_calls_per_run + draft.closing_calls_per_run,
                             draft.operator_calls_including_communication_per_run)
        self.assertLessEqual(mutations, draft.grant_invocation_limit_per_run)
        self.assertLessEqual(sum(map(len, witness)), draft.fixture_actions_per_run)
        self.assertEqual(23, calls)
        self.assertEqual(9, mutations)
