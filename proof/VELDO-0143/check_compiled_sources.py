"""Regression controls for the new-project fixture's immutable compilation cache.

Run: python3 proof/VELDO-0143/check_compiled_sources.py
"""
import concurrent.futures
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('compiled_sources',
    ROOT / 'scripts/suites/support/compiled_sources.py')
SUPPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SUPPORT)


def load(path):
    spec = importlib.util.spec_from_file_location('fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CompilationControls(unittest.TestCase):
    def test_fresh_globals_and_content_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / 'organ.py'
            before = 'state = []\ndef value(): return 1\n'
            path.write_text(before)
            timestamp = path.stat().st_mtime_ns
            with SUPPORT.compiled_sources(root):
                first, second = load(path), load(path)
                self.assertIs(first.value.__code__, second.value.__code__)
                self.assertEqual(first.value.__code__.co_filename, str(path))
                first.state.append('private')
                self.assertEqual(second.state, [])
                self.assertIsNot(first.__dict__, second.__dict__)
                # Timestamp/size bytecode validation would miss this mutation.
                path.write_text(before.replace('return 1', 'return 2'))
                os.utime(path, ns=(timestamp, timestamp))
                mutated = load(path)
                self.assertEqual(mutated.value(), 2)
                self.assertIsNot(first.value.__code__, mutated.value.__code__)
                path.write_text(before)
                restored = load(path)
                self.assertEqual(restored.value(), 1)
                self.assertIs(first.value.__code__, restored.value.__code__)
                other = root / 'other.py'
                other.write_text(before)
                self.assertEqual(load(other).value.__code__.co_filename, str(other))
                path.write_text('invalid syntax!')
                with self.assertRaises(SyntaxError):
                    load(path)
            self.assertFalse((root / '__pycache__').exists())

    def test_loader_restored_after_failure(self):
        loader = importlib.machinery.SourceFileLoader
        original = loader.get_code
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(RuntimeError, 'fixture failed'):
                with SUPPORT.compiled_sources(temporary):
                    raise RuntimeError('fixture failed')
        self.assertIs(loader.get_code, original)

    def test_private_disk_cache_revalidates_bytes_and_executes_fresh_globals(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, cache = root / 'organ.py', root / 'code'
            source = 'state = []\ndef value(): return 1\n'
            path.write_text(source)
            timestamp = path.stat().st_mtime_ns
            loader = importlib.machinery.SourceFileLoader
            original, calls = loader.source_to_code, []

            def compile_source(self, *args, **kwargs):
                calls.append(self.path)
                return original(self, *args, **kwargs)

            with patch.object(loader, 'source_to_code', compile_source):
                with SUPPORT.compiled_sources(root, cache):
                    first = load(path)
                    first.state.append('private')
                with SUPPORT.compiled_sources(root, cache):
                    second = load(path)
                    self.assertEqual(second.state, [])
                    self.assertEqual(second.value(), 1)
                    self.assertEqual(second.value.__code__.co_filename, str(path))
                    self.assertEqual(calls, [str(path)])
                    path.write_text(source.replace('return 1', 'return 2'))
                    os.utime(path, ns=(timestamp, timestamp))
                    self.assertEqual(load(path).value(), 2)
                    self.assertEqual(calls, [str(path), str(path)])
            self.assertFalse((root / '__pycache__').exists())

    def test_child_entry_keeps_docstring_future_imports_and_private_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            organ, entry, cache = root / 'organ.py', root / 'main.py', root / 'code'
            source = 'state = []\ndef value(): return 1\n'
            organ.write_text(source)
            entry.write_text('''"""fixture entry"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
def annotated(value: int): return value
def fresh():
    spec = importlib.util.spec_from_file_location('organ', Path(__file__).with_name('organ.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
if __name__ == '__main__':
    first, second = fresh(), fresh()
    first.state.append('private')
    print(json.dumps([__doc__, annotated.__annotations__['value'], first.value(), second.state]))
''')
            SUPPORT.install_main_cache(entry, root, cache)
            original = importlib.machinery.SourceFileLoader.get_code
            self.assertEqual(load(entry).__doc__, 'fixture entry')
            self.assertIs(importlib.machinery.SourceFileLoader.get_code, original)

            def run():
                return json.loads(subprocess.check_output([sys.executable, '-B', str(entry)], text=True))

            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as children:
                results = [future.result() for future in (children.submit(run), children.submit(run))]
            self.assertEqual(results, [['fixture entry', 'int', 1, []]] * 2)
            timestamp = organ.stat().st_mtime_ns
            organ.write_text(source.replace('return 1', 'return 2'))
            os.utime(organ, ns=(timestamp, timestamp))
            self.assertEqual(run(), ['fixture entry', 'int', 2, []])
            self.assertFalse((root / '__pycache__').exists())


if __name__ == '__main__':
    unittest.main()
