"""Regression tests for event-held heartbeat subjects and supplied expiry times."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


WAITS = load(ROOT / 'scripts/suites/support/waits.py')
CLOCK = load(ROOT / 'scripts/fixtures/heartbeat_clock.py')
HB = load(ROOT / '.veldo/control_heartbeat.py')
ALLOCATOR = load(ROOT / 'scripts/gate_fixtures.py')


class HeartbeatFixture(unittest.TestCase):
    def test_subject_survives_arbitrary_clock_advance_until_observed_and_released(self):
        tree = ast.parse((ROOT / 'scripts/suites/67_veldo_0041_heartbeat.py').read_text())
        common = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'common' for t in n.targets))
        engine = next(n.args[0].right.value for n in ast.walk(tree) if isinstance(n, ast.Call)
                      and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                      and n.func.value.id == 'engine' and n.func.attr == 'write_text')
        with ALLOCATOR.directory() as folder:
            directory = Path(folder)
            source = eval(compile(ast.Expression(common), 'common', 'eval'),
                          {'mods': ROOT / 'scripts/fixtures'}) + engine
            clock = directory / 'clock'
            clock.mkdir()
            CLOCK.write(clock / 'now', 100)
            release = directory / 'release'
            os.mkfifo(release)
            fd = os.open(release, os.O_RDWR | os.O_NONBLOCK)
            child = subprocess.Popen([sys.executable, '-c', source, str(directory), 'unused'],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     env=dict(os.environ, V41_CLOCK=str(clock), VELDO_DISPATCH_ID='fixture'))
            try:
                child.stdin.write(json.dumps({'payload': {'hold': 0, 'release': str(release)}}).encode())
                child.stdin.close()
                marker = directory / 'fixture.worker'
                WAITS.wait('fixture subject started', marker.exists, lambda: child.poll() is not None,
                           [WAITS.PathAppears(marker), WAITS.Pidfd(child)])
                self.assertTrue(marker.exists())
                CLOCK.write(clock / 'now', 10 ** 9)
                self.assertIsNone(child.poll())
                self.assertFalse((directory / 'fixture.exit').exists())
                os.write(fd, b'g')
                self.assertEqual(child.wait(timeout=WAITS.WAIT_HANG_SECONDS), 0)
                self.assertEqual(json.loads((directory / 'fixture.exit').read_text())['at'], 10 ** 9)
            finally:
                if child.poll() is None:
                    child.kill()
                child.wait(timeout=WAITS.WAIT_HANG_SECONDS)
                child.stdout.close()
                child.stderr.close()
                os.close(fd)

    def decision(self, now, mutation=None):
        source = (ROOT / '.veldo/control_launch.py').read_text()
        if mutation:
            teeth = load(ROOT / 'scripts/check_teeth_mutations.py')
            case = next(c for c in teeth.cases() if c['name'] == mutation)
            source = teeth.mutate(source.encode(), case).decode()
        tree = ast.parse(source)
        decision = next(n for n in ast.walk(tree) if isinstance(n, ast.If)
                        and len(n.body) == 1 and isinstance(n.body[0], ast.Expr)
                        and isinstance(n.body[0].value, ast.Call)
                        and isinstance(n.body[0].value.func, ast.Name)
                        and n.body[0].value.func.id == 'begin'
                        and isinstance(n.body[0].value.args[0], ast.Constant)
                        and n.body[0].value.args[0].value == 'deadline')
        watch = HB.Watch(-1, .25, 1, 0)
        watch.first, watch.last = 3, 10
        ns = dict(cause=None, code=None, watch=watch, now=now, self=None, stop=None,
                  contract={'deadline': 3600}, _wall=lambda _: 0, runtime_deadline=float('inf'))
        ns['begin'] = lambda reason: ns.update(cause=reason)
        exec(compile(ast.Module(body=[decision], type_ignores=[]), 'receiver-decision', 'exec'), ns)
        return ns['cause'], watch

    def test_real_receiver_decision_at_latest_heartbeat_boundary(self):
        self.assertEqual(self.decision(10.999)[0], None)
        for value in (11, 10 ** 6):
            cause, watch = self.decision(value)
            self.assertEqual(cause, 'heartbeat_missing')
            self.assertEqual(watch.uncertain_at, value)

    def test_missing_stop_mutant_has_a_conclusive_negative_observation(self):
        cause, watch = self.decision(11, 'heartbeat-missing-not-stopped')
        self.assertIsNone(cause)
        self.assertEqual(watch.liveness, 'live')

    def test_pidfd_reap_notification_follows_exit_notification(self):
        import select
        tree = ast.parse((ROOT / 'scripts/suites/67_veldo_0041_heartbeat.py').read_text())
        function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'exit_sources')
        namespace = {'WAITS': WAITS}
        exec(compile(ast.Module(body=[function], type_ignores=[]), 'fixture-reap-source', 'exec'), namespace)
        pid = os.fork()
        if pid == 0:
            os._exit(0)
        source = namespace['exit_sources'](pid, reaped=True)[0]
        poller = select.poll()
        poller.register(source.fileno(), select.POLLIN)
        try:
            WAITS.wait('child exit before reap', lambda: bool(poller.poll(0)), None,
                       [WAITS.Readable(source.fileno(), drain=False)])
            poller.modify(source.fileno(), source.events)
            self.assertEqual(poller.poll(0), [])
            os.waitpid(pid, 0)
            WAITS.wait('keeper reap notification', lambda: bool(poller.poll(0)), None, [source])
            self.assertFalse(Path('/proc/%d' % pid).exists())
        finally:
            source.close()
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass

    def test_snapshot_reports_decision_sample_even_if_clock_advanced_before_publication(self):
        with ALLOCATOR.directory() as folder:
            directory = Path(folder)
            CLOCK.write(directory / 'now', 100)
            clock = CLOCK.Clock(directory)
            sampled = clock.monotonic()
            CLOCK.write(directory / 'now', 101)
            clock.snapshot(now=sampled, cause=None)
            self.assertEqual(CLOCK.read(directory / 'receiver')['now'], 100)

    def test_clock_wakes_poll_without_advancing_from_scheduling(self):
        with ALLOCATOR.directory() as folder:
            directory = Path(folder)
            CLOCK.write(directory / 'now', 100)
            os.mkfifo(directory / 'sender')
            clock = CLOCK.Clock(directory)
            poller = clock.select('sender').poll()
            try:
                CLOCK.write(directory / 'now', 10 ** 9)
                os.write(poller.tick, b'g')
                self.assertEqual(poller.poll(0), [])
                self.assertEqual(clock.monotonic(), 10 ** 9)
                self.assertEqual(CLOCK.read(directory / 'sender-waiting')['timeout'], 0)
            finally:
                poller.poller.close()
                os.close(poller.tick)


if __name__ == '__main__':
    unittest.main()
