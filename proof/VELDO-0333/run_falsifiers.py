"""Run only this ticket's six falsifiers and the adjusted prior keep falsifier.

Uses the existing driver's materialize and worker seams, without its coordinator or gate.
Each mutation is applied once to a temporary production copy, after a no-op control.
"""
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('v333_mutations', ROOT / 'scripts/check_teeth_mutations.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
cases = [case for case in driver.cases()
         if case['finding'] == 333 or case['name'] == 'budget214-keep-not-spared']
assert len(cases) == 7
results = []
with tempfile.TemporaryDirectory(prefix='veldo-0333-falsifiers-') as directory:
    for case in cases:
        results_by_mode = {}
        for mode in ('noop', 'mutant'):
            made = driver.materialize(case, mode, Path(directory) / case['name'] / mode)
            observed = driver.worker(case, str(made['mutant']))
            results_by_mode[mode] = observed
        control, mutant = results_by_mode['noop'], results_by_mode['mutant']
        rejected = (not control['failed_rows'] and
                    all(mutant['targets'][row] and not all(mutant['targets'][row]) for row in case['rows']))
        results.append({'falsifier': case['name'], 'expected_red': case['rows'],
                        'noop_red_rows': control['failed_rows'], 'red_rows': mutant['failed_rows'],
                        'red_details': mutant['failed_details'], 'red_as_expected': rejected})
        print('%s: control %s; expected rows %s' %
              (case['name'], 'green' if not control['failed_rows'] else 'RED', 'red' if rejected else 'NOT RED'))
(Path(__file__).parent / 'falsifiers.json').write_text(json.dumps(results, indent=1) + '\n')
assert all(result['red_as_expected'] for result in results)
