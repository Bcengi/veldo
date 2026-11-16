#!/usr/bin/env python3
"""Apply every falsifier registered for finding 329 once, by hand, without the teeth driver or the gate.

Each mutation is written into a copy of the production module in this runner's temporary folder; the
suite's production anchor selects the copy. A falsifier counts only when the suite ran to its last row
with no fixture exception, its target row turned red, and the unchanged module gave every row green.
"""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('catalog329', ROOT / 'scripts/check_teeth_mutations.py')
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)
cases = [case for case in catalog.cases() if case['finding'] == 329]
SUITE = ROOT / 'scripts/suites/150_veldo_0329_hook_install.py'
ANCHOR = 'ROOT / ".veldo" / "control_space_install.py"'
PRODUCTION = ROOT / '.veldo/control_space_install.py'
suite, text = SUITE.read_text(), PRODUCTION.read_text()
assert suite.count(ANCHOR) == 1


def run(module):
    observed = []
    source = suite.replace(ANCHOR, 'Path(' + repr(str(module)) + ')')
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        exec(compile(source, str(SUITE), 'exec'),
             {'ROOT': ROOT, 'expect': lambda label, good: observed.append((label.split(':', 1)[0], bool(good)))})
    return observed


baseline = run(PRODUCTION)
assert baseline and all(good for _label, good in baseline), baseline
results = []
for case in cases:
    assert text.count(case['old']) == 1, case['name']
    with tempfile.TemporaryDirectory(prefix='veldo-0329-falsifier-') as folder:
        path = Path(folder) / case['module']
        path.write_text(text.replace(case['old'], case['new'], 1))
        observed = run(path)
    red = sorted(label for label, good in observed if not good)
    errors = [label for label in red if 'fixture/completed' in label]
    rejected = not errors and len(observed) == len(baseline) and all(row in red for row in case['rows'])
    results.append({'case': case['name'], 'module': case['module'], 'applied': 1, 'target_rows': case['rows'],
                    'red_rows': red, 'rows_run': len(observed), 'rejected': rejected})
    print(case['name'] + ': ' + ('target red' if rejected else 'FAILED') + ' ' + str(red), flush=True)
(ROOT / 'proof/VELDO-0329/falsifiers.json').write_text(json.dumps({
    'scope': 'Every mutation registered for finding 329, applied once by hand to a copy of '
             '.veldo/control_space_install.py. The teeth driver run is recorded in teeth.json. No full gate.',
    'baseline': {'rows': [label for label, _good in baseline], 'all_green': True},
    'results': results}, indent=2) + '\n')
assert len(results) == 18 and all(result['rejected'] for result in results)
