"""The real registered parent-only mutant must fail at the stop operation boundary."""
import importlib.util
from pathlib import Path
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


boundary = load('stop_boundary', ROOT / 'scripts/fixtures/containment_stop_boundary.py')


class StopBoundary(unittest.TestCase):
    def stop(self, mutant=False):
        path = ROOT / '.veldo/control_containment.py'
        module = types.ModuleType('boundary_containment')
        module.__file__ = str(path)
        source = path.read_bytes()
        if mutant:
            driver = load('boundary_teeth', ROOT / 'scripts/check_teeth_mutations.py')
            case = next(c for c in driver.cases() if c['name'] == 'containment-stop-only-parent')
            source = driver.mutate(source, case)
        exec(compile(source, str(path), 'exec'), module.__dict__)
        calls = []

        class Group:
            def terminate(self):
                calls.append('terminate')

            def kill(self):
                calls.append('kill')

        boundary.observe_stop_boundary(module.Stop)
        return module, module.Stop(Group(), 42, 1, 1), calls

    def test_real_operations_are_forwarded_and_restored(self):
        _, stop, calls = self.stop()
        for stage in ('terminate', 'kill'):
            stop._step(stage, 0)
        self.assertEqual(calls, ['terminate', 'kill'])
        self.assertEqual(vars(stop.group), {})
        self.assertEqual([s['step'] for s in stop.steps], calls)

    def test_parent_only_terminate_is_conclusive_at_return(self):
        self.parent_only('terminate')

    def test_parent_only_kill_is_conclusive_at_return(self):
        self.parent_only('kill')

    def parent_only(self, stage):
        module, stop, calls = self.stop(mutant=True)
        signals = []
        fake_os = types.SimpleNamespace(kill=lambda *args: signals.append(args))
        with patch.object(module, 'os', fake_os):
            with self.assertRaisesRegex(AssertionError, 'completed ' + stage + ' without the group operation'):
                stop._step(stage, 0)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0][0], 42)
        self.assertEqual(calls, [])
        self.assertEqual(vars(stop.group), {})

    def test_operation_failure_is_preserved(self):
        _, stop, _ = self.stop()
        def broken():
            raise OSError('group write failed')
        stop.group.kill = broken
        with self.assertRaisesRegex(OSError, 'group write failed'):
            stop._step('kill', 0)
        self.assertIs(stop.group.kill, broken)


if __name__ == '__main__':
    unittest.main()
