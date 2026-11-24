"""Event-synchronized controls for the exact VELDO-0183 one-opener row."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

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
            holder = None
            try:
                rows = []
                before = len(FIX.opens(root))

                def run():
                    nonlocal holder
                    holder = subprocess.Popen([interpreter, '-B', '-c', HOLDER, str(data)],
                                              stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                              stderr=subprocess.PIPE, text=True)
                    self.assertEqual(holder.stdout.readline().strip(), 'ready')
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
                if holder is not None:
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

    def test_unrelated_bad_fd_does_not_escape_audit_hook(self):
        with mock.patch.object(FIX.EVENTS.os, 'readlink', side_effect=OSError('unavailable')):
            FIX.EVENTS._audit('open', (-1, 'r', 0))
            FIX.EVENTS._audit('fcntl.flock', (-1, 2))
            FIX.EVENTS._audit('os.scandir', (-1,))
        self.assertFalse(FIX.EVENTS._LOCAL.busy)

    def test_only_sqlite_and_its_sidecars_are_store_files(self):
        for name in ('chroma.sqlite3', 'chroma.sqlite3-wal', 'chroma.sqlite3-shm'):
            self.assertTrue(FIX.EVENTS.store_file(name))
        for name in ('index-files.json', 'history.db', 'veldo-store.lock', 'server.log', 'chromadb'):
            self.assertFalse(FIX.EVENTS.store_file(name))
        with ALLOCATOR.directory() as scratch:
            directory = Path(scratch) / 'chroma.sqlite3'
            directory.mkdir()
            self.assertFalse(FIX.EVENTS.store_file(directory))

    def test_event_crosscheck_scopes_nested_store_and_rejects_later_credit(self):
        directory = '/fixture/memory_kb/data/chromadb'
        event = dict(store='/fixture/memory_kb/data', path=directory + '/server.log',
                     kind='diagnostic', pid=1, holders=[dict(pid=2, kind='store')])
        later = dict(store=event['store'], path=directory + '/chroma.sqlite3',
                     kind='store', pid=2, holders=[])
        self.assertEqual(FIX.EVENTS.unobserved([event, later], directory), {2})
        self.assertEqual(FIX.EVENTS.unobserved([later, event], directory, since=1), set())

    def escape(self, mode, boundary):
        with ALLOCATOR.directory() as scratch:
            root = Path(scratch) / 'stores'
            manifest = FIX.build(root)
            data = root / 'mem0_memory/data'
            interpreter = manifest['parts']['ava_memory']['interpreter']
            code = manifest['parts']['ava_memory']['code']
            holder = subprocess.Popen([interpreter, '-B', '-c', HOLDER, str(data)],
                                      stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            child = None
            try:
                self.assertEqual(holder.stdout.readline().strip(), 'ready')
                if mode == 'collection':
                    command = [sys.executable, '-B', '-c',
                               "import sys;sys.path.insert(0,sys.argv[1]);import chroma;"
                               "c=chroma.Collection(sys.argv[2], 'x');print('ready',flush=True);sys.stdin.read()",
                               code, str(data / 'chromadb')]
                elif mode == 'isolated':
                    command = [interpreter, '-I', '-c',
                               "import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);"
                               "print('ready',flush=True);sys.stdin.read()", str(data / 'chromadb/chroma.sqlite3')]
                else:
                    command = ['sh', '-c', 'exec 3<"$1"; echo ready; read finish',
                               'sh', str(data / 'chromadb/chroma.sqlite3')]

                def launch():
                    nonlocal child
                    child = subprocess.Popen(command, env={k: os.environ[k] for k in ('PATH', 'HOME')},
                                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
                    self.assertEqual(child.stdout.readline().strip(), 'ready')

                def finish():
                    child.communicate('\n')
                    self.assertEqual(child.returncode, 0)

                if boundary == 'start':
                    launch()
                before = len(FIX.opens(root))

                def run():
                    if boundary != 'start':
                        launch()
                    if boundary == 'event':
                        # A diagnostic open must still cross-check store holders.
                        with (data / 'server.log').open('a'):
                            pass
                    if boundary != 'end':
                        finish()

                rows = []
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    FIX.watched(lambda row, label, ok: rows.append((label, ok)),
                                'escape', {'ava_memory': str(data)}, root, run,
                                existing=None if boundary == 'transient' else {'ava_memory': holder.pid})
                self.assertFalse(all(ok for _, ok in rows), rows)
                if mode == 'collection' and boundary != 'start':
                    events, conflicts, _ = FIX.EVENTS.evidence(FIX.opens(root)[before:], data)
                    self.assertTrue(any(e['pid'] == child.pid for e in events), events)
                    self.assertTrue(conflicts)
                if mode != 'collection' and boundary != 'transient':
                    evidence = json.loads(output.getvalue().split('ava_memory ', 1)[1])
                    self.assertIn(child.pid, evidence['unobserved'])
                    self.assertFalse(rows[-1][1], rows)
                if boundary == 'transient' and mode != 'collection':
                    self.assertEqual(FIX.opens(root)[before:], [])
                    self.assertFalse(rows[0][1], rows)  # Past sqlite/flock evidence cannot pass this window.
                print('escape:', mode, boundary, 'row=FAIL (expected)')
            finally:
                if child is not None and child.returncode is None:
                    child.communicate('\n')
                holder.communicate('')
                self.assertEqual(holder.returncode, 0)

    def test_review_three_transient_openers_fail_separately(self):
        for mode in ('collection', 'isolated', 'sh'):
            with self.subTest(mode=mode):
                self.escape(mode, 'transient')

    def test_unhooked_holders_fail_at_each_endpoint_and_event(self):
        for mode in ('isolated', 'sh'):
            for boundary in ('start', 'end', 'event'):
                with self.subTest(mode=mode, boundary=boundary):
                    self.escape(mode, boundary)

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
