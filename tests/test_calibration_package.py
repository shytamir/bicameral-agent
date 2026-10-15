"""The prepared calibration can be rehearsed offline but cannot dispatch MODEL calls."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bicameral_agent.backends.ollama import GenerationSettings, ModelPin
from bicameral_agent.contracts.base import parse
from bicameral_agent.pilot.__main__ import main
from bicameral_agent.pilot.batch import ROOT, allocate, artifacts, attach, run_trajectory
from bicameral_agent.storage import Store
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


if __name__ == '__main__':
    unittest.main()
