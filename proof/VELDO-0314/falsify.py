#!/usr/bin/env python3
"""Run only VELDO-0314's four declared falsifiers, locally, without the teeth driver or gate.

Each production mutation is written once into this runner's temporary output. The normal suite's
production anchor selects that copy. Target assertions must run and fail; exceptions are not proof.
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
production = (ROOT / '.veldo/control_space_spool.py').read_text()
results = []
for case in cases:
    assert production.count(case['old']) == 1, case['name']
    with tempfile.TemporaryDirectory(prefix='veldo-0314-falsifier-') as folder:
        path = Path(folder) / 'control_space_spool.py'
        path.write_text(production.replace(case['old'], case['new'], 1))
        observed = []
        source = suite.replace('ROOT / ".veldo" / "control_space_spool.py"', 'Path(' + repr(str(path)) + ')')
        exec(compile(source, str(ROOT / 'scripts/suites' / case['suite']), 'exec'),
             {'ROOT': ROOT, 'expect': lambda label, good: observed.append((label, bool(good)))})
        targets = {row: [good for label, good in observed if label.startswith('VELDO-0314 ' + row)]
                   for row in case['rows']}
        errors = [label for label, good in observed if 'fixture/completed' in label or 'Traceback' in label]
        rejected = not errors and all(values and not all(values) for values in targets.values())
        results.append({'case': case['name'], 'applied': 1, 'target_rows': targets, 'rejected': rejected,
                        'errors': errors})
        print(case['name'] + ': ' + ('target red' if rejected else 'FAILED'), flush=True)
output = ROOT / 'proof/VELDO-0314/falsifiers.json'
output.write_text(json.dumps({'scope': 'Four targeted manual mutations; no teeth run and no full gate.',
                              'results': results}, indent=2) + '\n')
assert len(results) == 4 and all(result['rejected'] for result in results)
