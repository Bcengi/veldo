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
    def test_exec_wrapper_never_loads_compiler(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            entry, cache = root / 'main.py', root / 'code'
            missing = root / 'compiled_sources.py'
            entry.write_text("print('wrapper ran')\n")
            with patch.object(SUPPORT, '__file__', str(missing)):
                SUPPORT.install_main_cache(entry, root, cache)
            # An absent support file makes any attempt to read the compiler fail.
            wrapper = subprocess.run([sys.executable, '-B', str(entry), 'exec', '--contained'],
                                     capture_output=True, text=True)
            self.assertEqual(wrapper.returncode, 0, wrapper.stderr)
            self.assertEqual(wrapper.stdout.strip(), 'wrapper ran')
            self.assertFalse(cache.exists())
            receiver = subprocess.run([sys.executable, '-B', str(entry), 'receive'],
                                      capture_output=True, text=True)
            self.assertNotEqual(receiver.returncode, 0)
            self.assertIn(str(missing), receiver.stderr)

    def check_entry_header(self, header, body=b'print(42)\n', expected='42'):
        with tempfile.TemporaryDirectory(prefix='compiled-\u00e9-') as temporary:
            root = Path(temporary)
            entry, cache = root / 'main.py', root / 'code'
            entry.write_bytes(header + body)
            entry.chmod(0o700)
            SUPPORT.install_main_cache(entry, root, cache)
            self.assertTrue(entry.read_bytes().startswith(header))
            self.assertTrue(entry.read_bytes().endswith(body))
            self.assertEqual(subprocess.check_output(
                [str(entry)] if header.startswith(b'#!') else [sys.executable, '-B', str(entry)],
                text=True).strip(), expected)

    def test_shebang_only(self):
        self.check_entry_header(b'#!/usr/bin/env python3\n')

    def test_shebang_and_encoding(self):
        self.check_entry_header(b'#!/usr/bin/env python3\n# coding: utf-8\n')

    def test_latin1_encoding_declaration(self):
        self.check_entry_header(b'# coding: latin-1\n', b"print('caf\xe9')\n", 'caf\u00e9')

    def test_shebang_and_latin1_encoding_declaration(self):
        self.check_entry_header(b'#!/usr/bin/env python3\n# -*- coding: latin-1 -*-\n',
                                b"print('caf\xe9')\n", 'caf\u00e9')

    def test_read_only_cache_still_imports(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            organ, entry, cache = root / 'organ.py', root / 'main.py', root / 'code'
            organ.write_text('def value(): return 42\n')
            entry.write_text('import organ\nprint(organ.value())\n')
            cache.mkdir(mode=0o500)
            try:
                with self.assertRaises(PermissionError):
                    (cache / 'probe').write_bytes(b'')
                SUPPORT.install_main_cache(entry, root, cache)
                self.assertEqual(subprocess.check_output(
                    [sys.executable, '-B', str(entry)], text=True).strip(), '42')
                self.assertEqual(list(cache.iterdir()), [])
            finally:
                cache.chmod(0o700)

    def test_failed_cache_publish_cleans_temporary_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, cache = root / 'organ.py', root / 'code'
            path.write_text('def value(): return 42\n')
            with patch.object(SUPPORT.os, 'replace', side_effect=OSError('cache full')):
                with SUPPORT.compiled_sources(root, cache):
                    self.assertEqual(load(path).value(), 42)
            self.assertEqual(list(cache.iterdir()), [])

    def test_unavailable_cache_directory_still_imports(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path, blocked = root / 'organ.py', root / 'blocked'
            path.write_text('def value(): return 42\n')
            blocked.write_bytes(b'not a directory')
            with SUPPORT.compiled_sources(root, blocked / 'code'):
                self.assertEqual(load(path).value(), 42)

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
            # The parent's own import must not write bytecode, so the final
            # __pycache__ check sees only what the cache and children produce.
            with patch.object(sys, 'dont_write_bytecode', True):
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


def suite_rows(expect):
    """Run each cache control as an ordinary, independently reported suite row."""
    for name in unittest.defaultTestLoader.getTestCaseNames(CompilationControls):
        result = unittest.TestResult()
        CompilationControls(name).run(result)
        for _, detail in result.errors + result.failures:
            print(detail)
        expect('VELDO-0143 compiled-sources/' + name.removeprefix('test_'), result.wasSuccessful())


if __name__ == '__main__':
    unittest.main()
