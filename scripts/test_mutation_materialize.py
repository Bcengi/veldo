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


class WorkerScratch(unittest.TestCase):
    def test_finished_workers_release_scratch_and_preserve_evidence(self):
        import io
        import json
        from types import SimpleNamespace
        from unittest.mock import Mock, patch

        for name in ('scripts/check_gate_mutations.py', 'engine/scripts/check_gate_mutations.py'):
            gate = load(ROOT / name)
            ownership = load(ROOT / 'scripts/mutation_ownership.py')
            for outcome in ('rejected', 'driver_error', 'worker_cancelled', 'worker_cleanup_error'):
                with self.subTest(coordinator=name, outcome=outcome):
                    with load(ROOT / 'scripts/gate_fixtures.py').directory() as directory:
                        top = Path(directory)
                        home = top / '0'
                        copied = home / 'veldo'
                        copied.mkdir(parents=True)
                        (copied / 'module.py').write_text('answer = False\n')
                        (copied / 'module.py').chmod(0o444)
                        copied.chmod(0o500)
                        original = top / 'input'
                        original.mkdir()
                        (original / 'module.py').write_text('answer = True\n')
                        (home / 'input-link').symlink_to(original, target_is_directory=True)
                        ledger = top / 'ownership-0.jsonl'
                        ledger.write_text('')  # Materialized trees have no ownership-ledger entry.
                        observation = {'observation': {'failed_rows': ['target']}}
                        stdout = json.dumps(observation).encode()
                        stderr = b'[Errno 28] No space left on device' if outcome == 'driver_error' else b''
                        (top / '0-stdout').write_bytes(stdout)
                        (top / '0-stderr').write_bytes(stderr)
                        resources = SimpleNamespace(release=Mock())
                        worker = gate.Workers(resources=resources, parallel=1)
                        proc = SimpleNamespace(pid=12345, returncode=1 if stderr else 0, wait=Mock())
                        worker.active['case'] = (proc, io.BytesIO(stdout), io.BytesIO(stderr), 0)
                        worker.jobs['case'] = {'case': {'driver': 'check_teeth_mutations.py'}, 'mode': 'mutant'}
                        worker.homes['case'], worker.ledgers['case'] = home, ledger
                        worker.budgets['case'] = 120
                        worker.driver_spans['check_teeth_mutations.py'] = [0, 0]

                        def released(_name):
                            self.assertFalse(home.exists(), 'scratch must be gone before admission is released')
                            self.assertEqual((top / '0-stdout').read_bytes(), stdout)
                            self.assertEqual((top / '0-stderr').read_bytes(), stderr)
                            self.assertEqual((original / 'module.py').read_text(), 'answer = True\n')
                        resources.release.side_effect = released
                        remove = (Mock(side_effect=PermissionError('controlled cleanup failure'))
                                  if outcome == 'worker_cleanup_error' else ownership.remove_tree)
                        error = (gate.Refused('worker_cancelled', 'controlled cancellation')
                                 if outcome == 'worker_cancelled' else None)
                        try:
                            with patch.object(gate.os, 'killpg'), patch.object(gate, 'load', return_value=ownership), \
                                    patch.object(ownership, 'remove_tree', remove):
                                if outcome == 'rejected':
                                    self.assertEqual(worker.finish('case')['result'], observation)
                                else:
                                    with self.assertRaises(gate.Refused) as raised:
                                        worker.finish('case', error)
                                    self.assertEqual(raised.exception.code, outcome)
                            if outcome == 'worker_cleanup_error':
                                self.assertTrue(home.exists())
                                resources.release.assert_not_called()
                            else:
                                resources.release.assert_called_once_with('case')
                                self.assertTrue(worker.outcomes[0]['cleanup']['scratch_removed'])
                            if outcome == 'driver_error':
                                self.assertIn('No space left on device', worker.outcomes[0]['stderr_tail'])
                            self.assertNotIn('case', worker.active)
                        finally:
                            ownership.remove_tree(home)


if __name__ == '__main__':
    unittest.main()
