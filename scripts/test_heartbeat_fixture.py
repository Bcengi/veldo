"""The real heartbeat fixture cannot finish its stop subject while other rows run."""
import ast
import io
import importlib.util
import json
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def engine_source():
    tree = ast.parse((ROOT / 'scripts/suites/67_veldo_0041_heartbeat.py').read_text())
    common = next(n.value.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == 'common' for t in n.targets))
    engine = next(n.args[0].right.value for n in ast.walk(tree) if isinstance(n, ast.Call)
                  and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                  and n.func.value.id == 'engine' and n.func.attr == 'write_text')
    return common + engine


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HeartbeatDecision(unittest.TestCase):
    def decision(self, now, mutant=False):
        boundary = load(ROOT / 'scripts/fixtures/heartbeat_decision_boundary.py')
        hb = load(ROOT / '.veldo/control_heartbeat.py')
        source = (ROOT / '.veldo/control_launch.py').read_text()
        if mutant:
            teeth = load(ROOT / 'scripts/check_teeth_mutations.py')
            case = next(c for c in teeth.cases() if c['name'] == 'heartbeat-missing-not-stopped')
            source = teeth.mutate(source.encode(), case).decode()
        tree = ast.parse(boundary.instrument(source))
        decision = next(n for n in ast.walk(tree) if isinstance(n, ast.If)
                        and len(n.body) == 1 and isinstance(n.body[0], ast.Expr)
                        and isinstance(n.body[0].value, ast.Call)
                        and isinstance(n.body[0].value.func, ast.Name)
                        and n.body[0].value.func.id == 'begin'
                        and isinstance(n.body[0].value.args[0], ast.Constant)
                        and n.body[0].value.args[0].value == 'deadline')
        guard = next(n for n in ast.walk(tree) if isinstance(n, ast.If)
                     and any(isinstance(x, ast.Constant) and
                             x.value == 'heartbeat timer evaluated without stopping expired worker'
                             for x in ast.walk(n)))
        watch = hb.Watch(-1, .25, 1.0, 0)
        watch.first, watch.last = 3, 10
        ns = dict(cause=None, code=None, watch=watch, now=now, self=None, stop=None,
                  contract={'deadline': 3600}, _wall=lambda _: 0, runtime_deadline=float('inf'))
        def begin(cause):
            ns['cause'] = cause
        ns['begin'] = begin
        exec(compile(ast.Module(body=[decision, guard], type_ignores=[]), 'receiver-decision', 'exec'), ns)
        return ns['cause'], watch

    def test_exact_expiry_uses_latest_heartbeat(self):
        before, watch = self.decision(10.999)
        self.assertIsNone(before)
        self.assertEqual(watch.liveness, 'live')
        for now in (11, 100000):
            cause, watch = self.decision(now)
            self.assertEqual(cause, 'heartbeat_missing')
            self.assertEqual(watch.uncertain_at, now)
            self.assertEqual(watch.liveness, 'uncertain')

    def test_registered_missing_stop_mutant_fails_at_decision(self):
        with self.assertRaisesRegex(AssertionError, 'without stopping'):
            self.decision(11, mutant=True)


class Stopped(BaseException):
    pass


class HeartbeatFixture(unittest.TestCase):
    def test_arbitrary_elapsed_time_does_not_release_stop_subject(self):
        handlers, clock = {}, [0]

        def advance():
            clock[0] += 100000
            return clock[0]

        with tempfile.TemporaryDirectory() as directory:
            markers = Path(directory)

            def stop_event():
                self.assertTrue((markers / '.worker').exists())
                self.assertFalse((markers / '.exit').exists())
                # The fixture has outlived the old 8/30 second delays. Only its
                # actual stop handler may terminate it, with its original result.
                advance()
                handlers[signal.SIGTERM](signal.SIGTERM, None)

            packet = io.TextIOWrapper(io.BytesIO(json.dumps({'payload': {'hold_until_stop': True}}).encode()))
            with patch.object(sys, 'argv', ['engine', directory, 'unused-child']), \
                    patch.object(sys, 'stdin', packet), \
                    patch.dict('os.environ', {'VELDO_DISPATCH_ID': ''}), \
                    patch('signal.signal', side_effect=lambda number, handler: handlers.update({number: handler})), \
                    patch('signal.pause', side_effect=stop_event), patch('time.monotonic', side_effect=advance), \
                    patch('os._exit', side_effect=Stopped(143)):
                with self.assertRaises(Stopped) as ended:
                    exec(compile(engine_source(), 'heartbeat-fixture', 'exec'), {})
            self.assertEqual(ended.exception.args, (143,))
            self.assertTrue((markers / '.worker.term').exists())
            self.assertFalse((markers / '.exit').exists())


if __name__ == '__main__':
    unittest.main()
