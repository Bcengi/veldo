"""Mutation workers must own orphan reaping while an outer stage stays alive."""
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('mutation_tree_observer', ROOT / 'scripts/mutation_observer.py')
OBSERVER = importlib.util.module_from_spec(spec)
spec.loader.exec_module(OBSERVER)
spec = importlib.util.spec_from_file_location('gate_fixtures', ROOT / 'scripts/gate_fixtures.py')
ALLOCATOR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ALLOCATOR)

BOOTSTRAP = r'''
import importlib.util, json, sys
from pathlib import Path
source, root = map(Path, sys.argv[1:])
spec = importlib.util.spec_from_file_location('observer', source)
observer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(observer)
observer.ROOT = root
print(json.dumps(observer.worker(dict(suite='fixture.py', rows=['child']))))
'''

SUITE = r'''
import os, select, signal
from pathlib import Path
ready_r, ready_w = os.pipe()
release_r, release_w = os.pipe()
parent = os.fork()
if parent == 0:
    child = os.fork()
    if child == 0:
        null = os.open(os.devnull, os.O_RDWR)
        for descriptor in (0, 1, 2):
            os.dup2(null, descriptor)
        os.close(null)
        os.close(ready_r)
        os.close(release_w)
        os.write(ready_w, str(os.getpid()).encode())
        os.read(release_r, 1)
        os._exit(0)
    os._exit(0)
os.close(ready_w)
os.close(release_r)
os.waitpid(parent, 0)
child = int(os.read(ready_r, 64))
(ROOT / 'orphan').write_text(str(child))
# This process is now orphaned, and its original parent has already been collected.
fd = os.pidfd_open(child)
if (ROOT / 'abort').exists():
    # Hold a live orphan independently of pipe EOF while the exception unwinds.
    os.kill(child, signal.SIGSTOP)
    raise RuntimeError('fixture failed before completion')
os.write(release_w, b'.')
assert select.select([fd], [], [], WAITS.WAIT_HANG_SECONDS)[0]
os.close(fd)
os.close(release_w)
os.close(ready_r)
expect('child', True)
'''


@unittest.skipUnless(sys.platform == 'linux', 'Linux subreaper and pidfd fixture')
class MutationTree(unittest.TestCase):
    def run_worker(self, abort):
        libc = ctypes.CDLL(None, use_errno=True)
        previous = ctypes.c_int()
        self.assertEqual(libc.prctl(37, ctypes.byref(previous), 0, 0, 0), 0)
        self.assertEqual(libc.prctl(36, 1, 0, 0, 0), 0)
        orphan = None
        try:
            with ALLOCATOR.directory() as directory:
                root = Path(directory)
                suites = root / 'scripts/suites'
                suites.mkdir(parents=True)
                shared = (
                    'from pathlib import Path\nimport sys\n'
                    'ROOT = Path(__file__).resolve().parents[2]\n'
                    'sys.path.insert(0, %r)\nimport waits as WAITS\n'
                    'def expect(name, condition):\n    pass\n'
                    % str(ROOT / 'scripts/suites/support'))
                (suites / 'shared.py').write_text(shared)
                (suites / 'fixture.py').write_text(SUITE)
                if abort:
                    (root / 'abort').touch()
                done = OBSERVER.run_heavy(
                    [sys.executable, '-B', '-c', BOOTSTRAP,
                     str(ROOT / 'scripts/mutation_observer.py'), str(root)],
                    cwd=ROOT, env=dict(os.environ))
                orphan = int((root / 'orphan').read_text())
                if abort:
                    self.assertNotEqual(done.returncode, 0)
                    self.assertIn('fixture failed before completion', done.stderr)
                else:
                    self.assertEqual(done.returncode, 0, done.stderr)
                    self.assertEqual(json.loads(done.stdout)['observations'], [['child', True]])
                self.assertFalse(Path('/proc/%d' % orphan).exists(),
                                 'mutation orphan escaped to the still-running outer stage')
        finally:
            if orphan is not None:
                try:
                    os.kill(orphan, signal.SIGKILL)
                    os.waitpid(orphan, 0)
                except (ProcessLookupError, ChildProcessError):
                    pass
            libc.prctl(36, previous.value, 0, 0, 0)

    def test_completed_worker_reaps_orphans_before_returning(self):
        self.run_worker(False)

    def test_failed_worker_kills_and_reaps_live_orphans(self):
        self.run_worker(True)


if __name__ == '__main__':
    unittest.main()
