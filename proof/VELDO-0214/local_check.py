#!/usr/bin/env python3
"""Run suite 111 and drive VELDO-0214's five registered falsifiers through the teeth driver's own
materialize and worker, without the mutation stage's coordinator or confinement."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SUITE = '111_veldo_0214_first_use_budget'


def main():
    run = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', SUITE], cwd=str(ROOT),
                         capture_output=True, text=True, timeout=600)
    summary = [ln for ln in run.stdout.splitlines() if ln.startswith('selftest (PARTIAL')]
    line = [ln for ln in run.stdout.splitlines() if ln.strip().startswith(SUITE)]
    assert len(summary) == 1 and re.search(r' 0 failed', summary[0]), (summary, run.stdout[-2000:])
    assert 'SELFTEST FAIL' not in run.stdout, run.stdout[-2000:]

    spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
    teeth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(teeth)
    cases = [case for case in teeth.cases() if case['finding'] == 214]
    assert [c['name'] for c in cases] == ['budget214-fixed-1800-restored', 'budget214-caller-value-kept',
                                         'budget214-failed-leg-recorded', 'budget214-stale-docstring',
                                         'budget214-main-drops-the-budget']
    runs = []
    for case in cases:
        for mode in ('baseline', 'mutant'):
            with tempfile.TemporaryDirectory(prefix='veldo-0214-proof-') as directory:
                made = teeth.materialize(case, mode, directory, ROOT)
                result = teeth.worker(case, str(made['mutant']) if made['mutant'] else None)
            ours = [r for r in result['failed_rows'] if r.startswith('VELDO-0214 ')]
            if mode == 'baseline':
                assert not result['failed_rows'], result['failed_rows']
            else:
                assert ours == ['VELDO-0214 ' + row for row in case['rows']], result['failed_rows']
                assert result['failed_rows'] == ours, result['failed_rows']
            runs.append({'case': case['name'], 'mode': mode, 'module': case['dir'] + '/' + case['module'],
                         'replacement_count': made['replacement_count'], 'old_digest': made['old_digest'],
                         'new_digest': made['new_digest'], 'rows_observed': result['count'],
                         'target_rows': case['rows'], 'targets': result['targets'],
                         'failed_rows': result['failed_rows']})
    print(json.dumps({'scope': 'suite 111 through selftest.py --suite; the five registered VELDO-0214 '
                               'falsifiers through check_teeth_mutations.materialize and worker. No '
                               'mutation coordinator, confinement or repository gate executed.',
                      'suite_line': line, 'suite_summary': summary[0], 'falsifier_runs': runs}, indent=1))


if __name__ == '__main__':
    main()
