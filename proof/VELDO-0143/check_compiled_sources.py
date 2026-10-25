"""Regression controls for the new-project fixture's immutable compilation cache.

Run: python3 proof/VELDO-0143/check_compiled_sources.py
"""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

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


if __name__ == '__main__':
    unittest.main()
