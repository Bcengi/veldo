"""Reproduce readable receiver counts for the registered VELDO-0028 controls.

Run from any directory. All defects and fixtures live in temporary copies. The canonical
full gate remains the completion authority; this retains the suite's numeric observations.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teeth)


def run(case, mode):
    rows = {}
    with tempfile.TemporaryDirectory(prefix='v28-observations-') as directory:
        prepared = teeth.materialize(case, mode, directory)
        source = (ROOT / 'scripts/suites' / case['suite']).read_text()
        if prepared['mutant']:
            source = source.replace('ROOT / ".veldo" / "' + case['module'] + '"',
                                    '__import__("pathlib").Path(' + repr(str(prepared['mutant'])) + ')')
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            exec(compile(source, case['suite'], 'exec'),
                 {'ROOT': ROOT, 'expect': lambda name, ok: rows.update({name.split()[-1]: bool(ok)})})
        observed = json.loads(next(line.split(': ', 1)[1] for line in capture.getvalue().splitlines()
                                   if line.startswith('VELDO-0028 observations:')))
        targets = case['rows'] if mode == 'mutant' else rows
        assert all(rows[name] is (mode != 'mutant') for name in targets), rows
        return {'mode': mode, 'mutation': case['name'] if mode == 'mutant' else None,
                'rows': rows, 'observations': observed,
                'original_sha256': prepared['old_digest'], 'subject_sha256': prepared['new_digest']}


if __name__ == '__main__':
    cases = [case for case in teeth.cases() if case['finding'] == 28]
    results = [run(cases[0], 'baseline')] + [run(case, 'mutant') for case in cases]
    assert results[0]['observations']['out_of_scope_calls'] == 0
    scope = next(r for r in results if r['mutation'] == 'effects-worker-scope')
    assert scope['observations']['out_of_scope_calls'] > 0
    duplicate = next(r for r in results if r['mutation'] == 'effects-second-use-before-consumption')
    for kind in ('provider', 'publication'):
        assert duplicate['observations'][kind + '_calls'] > results[0]['observations'][kind + '_calls']
    print(json.dumps(results, indent=2, sort_keys=True))
