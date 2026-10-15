"""The prepared calibration can be rehearsed offline but cannot dispatch MODEL calls."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bicameral_agent.backends.ollama import GenerationSettings, ModelPin
from bicameral_agent.contracts.base import canonical_bytes, load_json, parse
from bicameral_agent.pilot.__main__ import main
from bicameral_agent.pilot.batch import ROOT, OPERATOR, allocate, artifacts, attach, run_trajectory
from bicameral_agent.storage import Store
from bicameral_agent.pilot.loop import Loop
from tests.test_compatibility import StrategyBackend


class CalibrationPackageTests(unittest.TestCase):
    def test_preparation_cannot_be_run_as_model_authorization(self):
        with tempfile.TemporaryDirectory() as temporary, patch(
                'bicameral_agent.backends.ollama.HTTPConnection',
                side_effect=AssertionError('No live transport')):
            destination = Path(temporary) / 'batch'
            index = allocate(ROOT / 'pilot/calibration', destination)
            self.assertEqual('SCRIPTED', index['mode'])
            self.assertEqual(3, len(index['allocation']))
            with self.assertRaisesRegex(ValueError, 'explicitly authorized MODEL'), redirect_stdout(StringIO()):
                main(['run', str(destination), '--tokenizer-directory', 'not-needed'])

    def test_prepared_limits_support_complete_scripted_trajectories(self):
        source = ROOT / 'pilot/calibration'
        _, budgets, _, _, bodies = artifacts(source)
        pin = parse(ModelPin, bodies['model'])
        self.assertEqual('0.40.4', pin.ollama_version)
        self.assertTrue(bodies['operator_prompt'].decode().replace('\r\n', '\n').startswith(OPERATOR))
        for name in ('fixture', 'clock', 'tasks'):
            self.assertEqual((ROOT / 'pilot/compatibility' / (name + '.json')).read_bytes(),
                             (source / (name + '.json')).read_bytes())
        with tempfile.TemporaryDirectory() as temporary, patch(
                'bicameral_agent.backends.ollama.HTTPConnection',
                side_effect=AssertionError('No live transport')):
            destination = Path(temporary) / 'batch'
            index = allocate(source, destination)
            for entry in index['allocation']:
                with self.subTest(arm=entry['arm']):
                    backend = StrategyBackend('rediscover' if entry['arm'] == 'B' else 'scoped')
                    backend.tokenizer.pin = pin
                    backend.settings = parse(GenerationSettings, bodies['settings'])
                    store = Store(destination / entry['file'], busy_timeout_ms=100)
                    try:
                        kernel, owner = attach(store, backend)
                        result = run_trajectory(kernel, owner, backend)
                        self.assertEqual('COMPLETED', result['state'])
                        self.assertEqual(['PASS'] * 5, [t['result'] for t in result['tasks']])
                        self.assertLessEqual(result['operator_calls'], budgets.operator_calls)
                        self.assertLessEqual(result['steward_calls'], budgets.steward_calls)
                        self.assertLessEqual(result['tool_calls'], budgets.actions)
                        self.assertEqual('SCRIPTED', result['mode'])
                    finally:
                        store.close()


class ModelBatchStopTests(unittest.TestCase):
    """Exercise the MODEL CLI with real stores and a fake backend, never Ollama."""

    def setUp(self):
        network = patch('bicameral_agent.backends.ollama.HTTPConnection',
                        side_effect=AssertionError('No live transport'))
        network.start()
        self.addCleanup(network.stop)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        package = Path(temporary.name) / 'package'
        package.mkdir()
        source = ROOT / 'pilot/calibration'
        for name in ('activity.json', 'fixture.json', 'clock.json', 'tasks.json',
                     'model.json', 'settings.json', 'operator.md', 'steward.md', 'communication.md'):
            (package / name).write_bytes((source / name).read_bytes())
        activity = load_json((package / 'activity.json').read_bytes())
        activity['activity'].update(execution='MODEL', resources=['svc-a'],
            decision='Synthetic MODEL-path regression with fake transport only; no live authorization.')
        activity['budgets'].update(operator_calls=8, operator_tokens=80000, steward_calls=2,
            steward_tokens=20000, actions=6, episodes=1, call_seconds=360, run_seconds=4320)
        (package / 'activity.json').write_bytes(canonical_bytes(activity))
        tasks = load_json((package / 'tasks.json').read_bytes())[:1]
        clock = load_json((package / 'clock.json').read_bytes())
        clock['steps'] = clock['steps'][:1]
        (package / 'tasks.json').write_bytes(canonical_bytes(tasks))
        (package / 'clock.json').write_bytes(canonical_bytes(clock))
        self.directory = Path(temporary.name) / 'batch'
        self.index = allocate(package, self.directory)
        self.backends = []

    def backend(self, model, settings, tokenizer_directory, **limits):
        backend = StrategyBackend('scoped')
        backend.mode = 'MODEL'
        backend.tokenizer.pin = parse(ModelPin, canonical_bytes(model))
        backend.settings = parse(GenerationSettings, canonical_bytes(settings))
        self.assertEqual(360, limits['seconds'])
        self.backends.append(backend)
        return backend

    def run_cli(self, factory=None):
        output = StringIO()
        with patch('bicameral_agent.pilot.__main__.OllamaBackend',
                   side_effect=factory or self.backend), redirect_stdout(output):
            main(['run', str(self.directory), '--tokenizer-directory', 'synthetic-only'])
        return load_json(output.getvalue().encode())

    def test_unknown_terminal_run_stops_batch_and_command_retry(self):
        def factory(*args, **kwargs):
            backend = self.backend(*args, **kwargs)
            def timeout(request, *, cancel):
                raise TimeoutError('synthetic timeout')
            backend.generate = timeout
            return backend
        first = self.run_cli(factory)
        self.assertEqual(1, len(first))
        self.assertEqual('TERMINATED', first[0]['state'])
        self.assertEqual('UNKNOWN', first[0]['result']['cause'])
        self.assertEqual(1, first[0]['calls'])
        self.assertEqual(1, len(self.backends))
        self.assertEqual(first, self.run_cli())
        self.assertEqual([], self.backends[-1].requests)
        for entry in self.index['allocation'][1:]:
            store = Store(self.directory / entry['file'], busy_timeout_ms=100)
            try:
                kernel, _ = attach(store, self.backends[-1])
                self.assertEqual('CREATED', kernel.run()[1].status)
                self.assertEqual([], kernel.records.latest('INVOCATION'))
            finally:
                store.close()

    def test_unknown_closing_call_stops_before_next_arm(self):
        def factory(*args, **kwargs):
            backend = self.backend(*args, **kwargs)
            generate = backend.generate
            def closing_timeout(request, *, cancel):
                if '"purpose":"CLOSING"' in load_json(request.wire)['prompt']:
                    raise TimeoutError('synthetic closing timeout')
                return generate(request, cancel=cancel)
            backend.generate = closing_timeout
            return backend
        report = self.run_cli(factory)
        self.assertEqual(1, len(report))
        self.assertEqual('PASS', report[0]['tasks'][0]['result'])
        self.assertEqual('UNKNOWN', report[0]['result']['communication'])
        self.assertEqual(1, len(self.backends))

    def test_recovered_interrupted_call_stops_before_any_new_call(self):
        entry = self.index['allocation'][0]
        store = Store(self.directory / entry['file'], busy_timeout_ms=100)
        try:
            backend = self.backend(load_json((ROOT / 'pilot/calibration/model.json').read_bytes()),
                load_json((ROOT / 'pilot/calibration/settings.json').read_bytes()), '', seconds=360)
            kernel, owner = attach(store, backend)
            owner.run_control('ACTIVATE', 'Synthetic interruption')
            owner.create_objective('Synthetic test')
            loop = Loop(kernel, backend)
            loop.begin('OPERATOR', loop.episode('Inspect svc-a'))
        finally:
            store.close()
        report = self.run_cli()
        self.assertEqual(1, len(report))
        self.assertEqual(1, report[0]['calls'])
        self.assertEqual([], self.backends[-1].requests)
        self.assertEqual(2, len(self.backends))
        self.assertEqual(report, self.run_cli())

    def test_withdrawal_still_stops_batch_and_command_retry(self):
        def factory(*args, **kwargs):
            backend = self.backend(*args, **kwargs)
            def withdraw(request, *, cancel):
                return backend.wire(request, {'participation': {'kind': 'WITHDRAW',
                    'text': 'Stop this synthetic activity.', 'communication': 'NO_FURTHER_CALLS'}})
            backend.generate = withdraw
            return backend
        report = self.run_cli(factory)
        self.assertEqual(1, len(report))
        self.assertEqual(1, report[0]['calls'])
        self.assertEqual('HELD', report[0]['result']['cause'])
        self.assertEqual(report, self.run_cli())
        self.assertEqual([], self.backends[-1].requests)

    def test_paused_run_still_stops_before_any_new_call(self):
        store = Store(self.directory / self.index['allocation'][0]['file'], busy_timeout_ms=100)
        try:
            kernel, owner = attach(store, StrategyBackend('scoped'))
            owner.run_control('ACTIVATE', 'Synthetic start')
            owner.run_control('PAUSE', 'Synthetic owner pause')
        finally:
            store.close()
        report = self.run_cli()
        self.assertEqual(1, len(report))
        self.assertEqual('PAUSED', report[0]['state'])
        self.assertEqual(0, report[0]['calls'])
        self.assertEqual([], self.backends[0].requests)

    def test_complete_fixed_budget_block_advances_all_three_arms(self):
        report = self.run_cli()
        self.assertEqual(['A', 'B', 'C'], [r['arm'] for r in report])
        self.assertEqual(['COMPLETED'] * 3, [r['state'] for r in report])
        self.assertEqual(['PASS'] * 3, [r['tasks'][0]['result'] for r in report])
        self.assertEqual(3, len(self.backends))


if __name__ == '__main__':
    unittest.main()
