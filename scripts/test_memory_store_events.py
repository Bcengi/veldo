"""Event-synchronized controls for the exact VELDO-0183 one-opener row."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIX = load(ROOT / 'proof/VELDO-0183/fixtures.py')
ALLOCATOR = load(ROOT / 'scripts/gate_fixtures.py')
HOLDER = '''import fcntl, os, sqlite3, sys
lock = open(sys.argv[1] + '/veldo-store.lock', 'a')
fcntl.flock(lock, fcntl.LOCK_EX)
store = sqlite3.connect(sys.argv[1] + '/chromadb/chroma.sqlite3')
print('ready', flush=True)
sys.stdin.read()
'''


class StoreOpenEvidence(unittest.TestCase):
    def control(self, operation, verdict, event):
        with ALLOCATOR.directory() as scratch:
            root = Path(scratch) / 'stores'
            manifest = FIX.build(root)
            data = root / 'mem0_memory/data'
            interpreter = manifest['parts']['ava_memory']['interpreter']
            holder = subprocess.Popen([interpreter, '-B', '-c', HOLDER, str(data)],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                self.assertEqual(holder.stdout.readline().strip(), 'ready')
                rows = []
                before = len(FIX.opens(root))

                def run():
                    # No Collection import: the hook must cover ordinary Python/sqlite/file opens.
                    result = subprocess.run([interpreter, '-B', '-c',
                                             'import os, sqlite3, sys\n' + operation, str(data)],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)

                with contextlib.redirect_stdout(io.StringIO()):
                    FIX.watched(lambda row, label, ok: rows.append((row, label, ok)),
                                'control', {'ava_memory': str(data)}, root, run)
                self.assertEqual(all(ok for _, _, ok in rows), verdict, rows)
                events = FIX.opens(root)[before:]
                observed = [e for e in events if e['event'] == event]
                self.assertTrue(observed, events)
                self.assertTrue(any(holder.pid in e['others'] for e in observed), observed)
                for e in observed:
                    self.assertTrue(e['path'])
                    self.assertTrue(e['command'])
                    self.assertTrue(all(h['path'] and h['command'] for h in e['holders']))
                if not verdict:
                    self.assertTrue(any(e['kind'] == 'store' and holder.pid in e['others'] for e in observed))
                print('control:', event, operation, 'row=' + ('PASS' if all(r[2] for r in rows) else 'FAIL (expected)'),
                      json.dumps(observed))
            finally:
                holder.communicate('')
                self.assertEqual(holder.returncode, 0)

    def test_second_sqlite_open_fails_row(self):
        self.control("c = sqlite3.connect(sys.argv[1] + '/chromadb/chroma.sqlite3')", False, 'sqlite3.connect')

    def test_second_file_open_fails_row(self):
        self.control("f = open(sys.argv[1] + '/chromadb/chroma.sqlite3', 'rb')", False, 'open')

    def test_second_os_open_fails_row(self):
        self.control("fd = os.open(sys.argv[1] + '/chromadb/chroma.sqlite3', os.O_RDONLY); os.close(fd)", False, 'open')

    def test_lock_fd_passes_row(self):
        self.control("f = open(sys.argv[1] + '/veldo-store.lock', 'a')", True, 'open')

    def test_log_fd_passes_row(self):
        self.control("f = open(sys.argv[1] + '/server.log', 'a')", True, 'open')

    def test_directory_fd_passes_row(self):
        self.control("fd = os.open(sys.argv[1] + '/chromadb', os.O_RDONLY | os.O_DIRECTORY); os.close(fd)", True, 'open')

    def test_scandir_passes_row(self):
        self.control("with os.scandir(sys.argv[1] + '/chromadb') as entries: list(entries)", True, 'os.scandir')

    def test_runner_is_observed_and_auxiliary_holders_do_not_convict(self):
        with ALLOCATOR.directory() as scratch:
            root = Path(scratch) / 'stores'
            manifest = FIX.build(root)
            data = root / 'mem0_memory/data'
            interpreter = manifest['parts']['ava_memory']['interpreter']
            code = "import sys; f = open(sys.argv[1] + '/server.log', 'a'); print('ready', flush=True); sys.stdin.read()"
            holder = subprocess.Popen([interpreter, '-B', '-c', code, str(data)],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            try:
                self.assertEqual(holder.stdout.readline().strip(), 'ready')
                before = len(FIX.opens(root))
                with (data / 'chromadb/chroma.sqlite3').open('rb'):
                    pass
                opened, beside, _ = FIX.EVENTS.evidence(FIX.opens(root)[before:], data)
                self.assertEqual(len(opened), 1)
                self.assertEqual(opened[0]['pid'], os.getpid())
                self.assertEqual(beside, [])
                self.assertTrue(any(h['pid'] == holder.pid and h['kind'] == 'auxiliary'
                                    and h['path'].endswith('/server.log') and h['command']
                                    for h in opened[0]['holders']))
            finally:
                holder.communicate('')
                self.assertEqual(holder.returncode, 0)


if __name__ == '__main__':
    unittest.main()
