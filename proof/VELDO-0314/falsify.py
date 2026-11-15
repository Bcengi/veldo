#!/usr/bin/env python3
"""Run every falsifier registered for finding 314, locally, without the teeth driver or the gate.

Each production mutation is written once into this runner's temporary output. The suite's production
anchor for that file selects the copy. Target assertions must run and fail; an exception of the
fixture is not proof, and a case that stops the suite before its last row is not rejected.
"""
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('catalog314', ROOT / 'scripts/check_teeth_mutations.py')
catalog = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog)
cases = [case for case in catalog.cases() if case['finding'] == 314]
suite = (ROOT / 'scripts/suites/153_veldo_0314_session_hooks.py').read_text()
ANCHORS = {
    'control_space_spool.py': ('ROOT / ".veldo" / "control_space_spool.py"', ROOT / '.veldo/control_space_spool.py'),
    'veldo': ('ROOT / "bin" / "veldo"', ROOT / 'bin/veldo'),
    'space-session.py': ('ROOT / "packs/claude/scripts" / "space-session.py"',
                         ROOT / 'packs/claude/scripts/space-session.py'),
}
results = []
for case in cases:
    anchor, production = ANCHORS[case['module']]
    text = production.read_text()
    assert text.count(case['old']) == 1 and suite.count(anchor) == 1, case['name']
    with tempfile.TemporaryDirectory(prefix='veldo-0314-falsifier-') as folder:
        path = Path(folder) / case['module']
        path.write_text(text.replace(case['old'], case['new'], 1))
        observed = []
        source = suite.replace(anchor, 'Path(' + repr(str(path)) + ')')
        exec(compile(source, str(ROOT / 'scripts/suites' / case['suite']), 'exec'),
             {'ROOT': ROOT, 'expect': lambda label, good: observed.append((label, bool(good)))})
        targets = {row: [good for label, good in observed if label.startswith('VELDO-0314 ' + row)]
                   for row in case['rows']}
        errors = [label for label, good in observed if 'fixture/completed' in label or 'Traceback' in label]
        rejected = not errors and all(values and not all(values) for values in targets.values())
        results.append({'case': case['name'], 'module': case['module'], 'applied': 1, 'target_rows': targets,
                        'rejected': rejected, 'errors': errors})
        print(case['name'] + ': ' + ('target red' if rejected else 'FAILED'), flush=True)
output = ROOT / 'proof/VELDO-0314/falsifiers.json'
output.write_text(json.dumps({'scope': 'Every mutation registered for finding 314, applied by hand; the teeth '
                                       'driver run is recorded in targeted-tests.json. No full gate.',
                              'results': results}, indent=2) + '\n')
assert len(results) == 17 and all(result['rejected'] for result in results)
