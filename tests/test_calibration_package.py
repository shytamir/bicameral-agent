"""The prepared calibration can be rehearsed offline but cannot dispatch MODEL calls."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bicameral_agent.backends.ollama import GenerationSettings, ModelPin
from bicameral_agent.contracts.base import canonical_bytes, load_json, parse
from bicameral_agent.contracts.pilot import SUBJECT_DESIGNATIONS
from bicameral_agent.pilot.__main__ import main
from bicameral_agent.pilot.batch import ROOT, OPERATOR, allocate, artifacts, attach, run_trajectory, report_run
from bicameral_agent.storage import Store, EvidenceUnavailable
from bicameral_agent.storage.retention import closure
from bicameral_agent.pilot.loop import Loop
from bicameral_agent.pilot.runtime import remove_content
from tests.test_compatibility import StrategyBackend
from tests.test_pilot_runtime import package, FakeBackend, response, outcome, consolidate


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
                        self.assertIsNone(result['subject'])
                        self.assertIsNone(kernel.config.subject_designation)
                    finally:
                        store.close()


class ModelBatchCase(unittest.TestCase):
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


class ModelBatchStopTests(ModelBatchCase):
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
        for result, backend in zip(report, self.backends):
            subject = result['subject']
            self.assertEqual(SUBJECT_DESIGNATIONS[result['arm']], subject['designation'])
            self.assertRegex(subject['name'], rf"^{subject['designation']}-[0-9]+\.[0-9]{{9}}$")
            self.assertTrue(backend.requests)
            for request in backend.requests:
                self.assertIn('"name":"' + subject['name'] + '"', load_json(request.wire)['prompt'])


class SubjectLifecycleTests(ModelBatchCase):
    """Prospective naming, tested only on temporary stores with fake transport."""

    def open_run(self, arm='A'):
        entry = next(e for e in self.index['allocation'] if e['arm'] == arm)
        store = Store(self.directory / entry['file'], busy_timeout_ms=100)
        backend = self.backend(load_json((ROOT / 'pilot/calibration/model.json').read_bytes()),
            load_json((ROOT / 'pilot/calibration/settings.json').read_bytes()), '', seconds=360)
        kernel, owner = attach(store, backend)
        return store, kernel, owner, Loop(kernel, backend)

    def start(self, kernel, owner, loop):
        owner.run_control('ACTIVATE', 'Synthetic naming test')
        owner.create_objective('Inspect the fixture')
        return loop.episode('Inspect svc-a')

    def test_initiation_is_shared_across_roles_communication_and_restart(self):
        store, kernel, owner, loop = self.open_run()
        try:
            self.assertIsNone(report_run(kernel)['subject'])
            episode = self.start(kernel, owner, loop)
            self.assertIsNone(kernel.subject)
            with patch('bicameral_agent.pilot.loop.time_ns', return_value=1_792_083_600_123_456_789) as clock:
                key, request = loop.begin('OPERATOR', episode)
                name = 'Aaron-1792083600.123456789'
                self.assertEqual(name, kernel.subject.name)
                self.assertIn(name, load_json(request.wire)['prompt'])
                wire = loop.backend.wire(request, outcome())
                result = loop.deliver(key, wire)
                self.assertEqual(result, loop.deliver(key, wire))
                owner.run_control('PAUSE', 'Synthetic pause')
                key, request = loop.begin('OPERATOR', purpose='REVIEW', notice='Naming preferences welcome.')
                self.assertIn(name, load_json(request.wire)['prompt'])
                loop.deliver(key, loop.backend.wire(request, {'participation': None}))
                owner.run_control('RESUME', 'Synthetic resume')
                clock.assert_called_once_with()
            store.close()
            store, kernel, owner, loop = self.open_run()
            with patch('bicameral_agent.pilot.loop.time_ns', side_effect=AssertionError('Never rename on restart')):
                key, request = loop.begin('STEWARD', episode)
                self.assertIn(name, load_json(request.wire)['prompt'])
                loop.deliver(key, loop.backend.wire(request, consolidate()))
                key, request = loop.begin('OPERATOR', purpose='CLOSING')
                self.assertIn(name, load_json(request.wire)['prompt'])
                loop.deliver(key, loop.backend.wire(request, {'participation': None}))
            self.assertEqual(name, report_run(kernel)['subject']['name'])
            self.assertEqual(1, len(kernel.records.history('PILOT_SUBJECT')))
        finally:
            store.close()

    def test_denied_or_uncommitted_admission_creates_no_subject(self):
        store, kernel, owner, loop = self.open_run()
        try:
            episode = self.start(kernel, owner, loop)
            owner.run_control('PAUSE', 'Synthetic pause')
            with self.assertRaises(ValueError):
                loop.begin('OPERATOR', episode)
            self.assertIsNone(kernel.subject)
            owner.run_control('RESUME', 'Synthetic resume')
            with patch.object(loop, '_admit', side_effect=ValueError('Synthetic budget rejection')):
                with self.assertRaisesRegex(ValueError, 'budget rejection'):
                    loop.begin('OPERATOR', episode)
            self.assertIsNone(kernel.subject)
            self.assertFalse(kernel.records.latest('INVOCATION'))
            def fail(point):
                if point == 'pilot-call-start.before_commit':
                    raise RuntimeError('Synthetic pre-commit crash')
            store._fault = fail
            with self.assertRaisesRegex(RuntimeError, 'pre-commit crash'):
                loop.begin('OPERATOR', episode)
            store._fault = lambda point: None
            self.assertIsNone(kernel.subject)
            self.assertFalse(kernel.records.latest('INVOCATION'))
            self.assertEqual([], loop.backend.requests)
        finally:
            store.close()
        store, kernel, _, _ = self.open_run()
        try:
            self.assertIsNone(kernel.subject)
            self.assertFalse(kernel.records.latest('INVOCATION'))
        finally:
            store.close()

    def test_committed_name_survives_unknown_recovery_and_terminal_reopen(self):
        store, kernel, owner, loop = self.open_run()
        try:
            episode = self.start(kernel, owner, loop)
            def fail(point):
                if point == 'pilot-call-start.after_commit':
                    raise RuntimeError('Synthetic lost acknowledgement')
            store._fault = fail
            with self.assertRaisesRegex(RuntimeError, 'lost acknowledgement'):
                loop.begin('OPERATOR', episode)
            store._fault = lambda point: None
            name = kernel.subject.name
            self.assertEqual(1, len(kernel.records.latest('INVOCATION')))
            self.assertEqual([], loop.backend.requests)
        finally:
            store.close()
        store, kernel, owner, loop = self.open_run()
        try:
            kernel.recover()
            self.assertEqual('UNKNOWN', kernel.records.latest('INVOCATION')[0][1]['status'])
            owner.run_control('TERMINATE', 'Preserve unknown synthetic initiation')
            with self.assertRaises(ValueError):
                loop.begin('OPERATOR', purpose='CLOSING')
            self.assertEqual(name, report_run(kernel)['subject']['name'])
            self.assertEqual(1, len(kernel.records.history('PILOT_SUBJECT')))
        finally:
            store.close()

    def test_legacy_model_configuration_is_not_named_retroactively(self):
        backend = FakeBackend()
        backend.mode = 'MODEL'
        config, bodies = package(backend)
        config['mode'] = config['activity']['execution'] = 'MODEL'
        with Store(self.directory / 'synthetic-legacy.sqlite', busy_timeout_ms=100) as store:
            run = store.retain_configuration(canonical_bytes(config), bodies)
            configuration_id = store._db.execute('SELECT configuration_id FROM runs WHERE id=?', (run,)).fetchone()[0]
            before = store.read_payload(run, configuration_id)
            kernel, owner = attach(store, backend)
            loop = Loop(kernel, backend)
            episode = self.start(kernel, owner, loop)
            key, request = loop.begin('OPERATOR', episode)
            loop.deliver(key, backend.wire(request, response()))
            self.assertNotIn('"subject":', load_json(request.wire)['prompt'])
            self.assertIsNone(report_run(kernel)['subject'])
            self.assertEqual(before, store.read_payload(run, configuration_id))

    def test_subject_retention_covers_inputs_and_cannot_generate_a_replacement(self):
        store, kernel, owner, loop = self.open_run()
        try:
            episode = self.start(kernel, owner, loop)
            key, request = loop.begin('OPERATOR', episode)
            loop.deliver(key, loop.backend.wire(request, response()))
            subject_payload = kernel.records.row('PILOT_SUBJECT', kernel.run_id)['payload_id']
            input_payload = kernel.records.get('INVOCATION', key)['input_payload_id']
            owner.run_control('PAUSE', 'Synthetic justified removal')
            scope = closure(store, kernel.run_id, [subject_payload])['payload_ids']
            self.assertIn(input_payload, scope)
            result = remove_content(owner, [subject_payload], expected_scope=scope,
                justification='JUSTIFIED_DELETION', note='Synthetic subject-retention test; fake transport, no provider copies.',
                provider_verified=True)
            self.assertEqual('COMPLETED', result['status'])
            with self.assertRaises(EvidenceUnavailable):
                kernel.subject
        finally:
            store.close()
        store, kernel, _, loop = self.open_run()
        try:
            with patch('bicameral_agent.pilot.loop.time_ns', side_effect=AssertionError('No replacement name')):
                with self.assertRaises(EvidenceUnavailable):
                    loop.begin('OPERATOR', purpose='CLOSING')
            self.assertEqual(1, kernel.records.revision('PILOT_SUBJECT', kernel.run_id))
        finally:
            store.close()


if __name__ == '__main__':
    unittest.main()
