"""Regression for lazy imports through a mutation worker's production tree."""
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load(path):
    spec = importlib.util.spec_from_file_location('materialize_test', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProductionTree(unittest.TestCase):
    def test_lazy_round_trip_and_owner_path(self):
        # The sibling imports the selected module again, just as conversation
        # decisions construct settlement. Both paths must see the same bytes and
        # ownership identity, including when the registry's companions are stale.
        source = '''from pathlib import Path
import importlib.util
answer = True
def observe():
    spec = importlib.util.spec_from_file_location('sibling', Path(__file__).with_name('sibling.py'))
    sibling = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sibling)
    return sibling.observe()
'''
        sibling = '''from pathlib import Path
import importlib.util
def observe():
    path = Path(__file__).with_name('subject.py')
    spec = importlib.util.spec_from_file_location('subject_again', path)
    subject = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(subject)
    return subject.answer, Path(subject.__file__).resolve()
'''
        for name in ('scripts/check_teeth_mutations.py', 'scripts/mutation_observer.py',
                     'engine/scripts/mutation_observer.py'):
            materializer = load(ROOT / name)
            with load(ROOT / 'scripts/gate_fixtures.py').directory() as directory:
                root = Path(directory) / 'input'
                base = root / '.veldo'
                base.mkdir(parents=True)
                (base / 'subject.py').write_text(source)
                (base / 'sibling.py').write_text(sibling)
                (base / 'unrelated.py').write_text('value = 42\n')
                for source_name in ('subject.py', 'sibling.py', 'unrelated.py'):
                    (base / source_name).chmod(0o444)
                (base / '__pycache__').mkdir()
                (base / '__pycache__/stale.pyc').write_bytes(b'not executable')
                for layout in ({}, {'companions': ['unrelated.py']}, {'siblings': True}):
                    case = dict(name='lazy', module='subject.py', old='answer = True',
                                new='answer = False', **layout)
                    for mode in ('baseline', 'noop', 'mutant'):
                        with self.subTest(materializer=name, layout=layout, mode=mode):
                            destination = Path(directory) / str(len(list(Path(directory).iterdir())))
                            made = materializer.materialize(case, mode, destination, root=root)
                            path = made['mutant'] or made['source']
                            module = load(path)
                            self.assertEqual(module.observe(), (mode != 'mutant', path.resolve()))
                            self.assertEqual(made['replacement_count'], 1)
                            self.assertEqual(made['old_digest'] == made['new_digest'], mode != 'mutant')
                            self.assertEqual((base / 'subject.py').read_text(), source)
                            self.assertEqual((base / 'subject.py').stat().st_mode & 0o777, 0o444)
                            if mode != 'baseline':
                                self.assertNotEqual(path.parent, base)
                                self.assertTrue(path.stat().st_mode & 0o200)
                                self.assertEqual((path.parent / 'sibling.py').stat().st_mode & 0o777, 0o444)
                                self.assertEqual((path.parent / 'unrelated.py').stat().st_mode & 0o777,
                                                 0o644 if layout.get('companions') else 0o444)
                                self.assertFalse((path.parent / '__pycache__/stale.pyc').exists())

    def test_fixture_and_script_layouts(self):
        for name in ('scripts/check_teeth_mutations.py', 'scripts/mutation_observer.py',
                     'engine/scripts/mutation_observer.py'):
            materializer = load(ROOT / name)
            with load(ROOT / 'scripts/gate_fixtures.py').directory() as directory:
                root = Path(directory) / 'input'
                for index, options in enumerate(({'fixture': True}, {'dir': 'scripts'},
                                                 {'dir': 'scripts', 'siblings': True})):
                    base = root / ('scripts/fixtures' if options.get('fixture') else 'scripts')
                    base.mkdir(parents=True, exist_ok=True)
                    (base / 'subject.py').write_bytes(b'answer = True\r\n')
                    (base / 'companion.py').write_text('value = 42\n')
                    case = dict(name='layout', module='subject.py', old='answer = True',
                                new='answer = False', companions=['companion.py'], **options)
                    made = materializer.materialize(case, 'mutant', Path(directory) / str(index), root=root)
                    target = made['mutant'] / 'subject.py' if options.get('fixture') else made['mutant']
                    self.assertEqual(target.read_bytes(), b'answer = False\r\n')
                    self.assertEqual((target.parent / 'companion.py').read_text(), 'value = 42\n')
                    self.assertEqual((base / 'subject.py').read_bytes(), b'answer = True\r\n')


if __name__ == '__main__':
    unittest.main()
