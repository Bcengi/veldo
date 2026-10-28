#!/usr/bin/env python3
"""VELDO-0220's own checks: suite 113 run plainly and inside the gate's confinement, and each of the
four registered falsifiers driven through the teeth driver's own materialize and worker (baseline,
then mutant), without the mutation stage's coordinator or confinement. Writes local_checks.json
beside this file. Run it inside the host lock (it runs mutants)."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SUITE = '113_veldo_0220_gate_host'
ROWS = ['host-lock/held-not-started', 'host-lock/released-on-exit', 'host-scope/own-scope',
        'host-lock/not-started-not-red']


def suite_run(confined):
    command = [sys.executable, 'scripts/selftest.py', '--suite', SUITE]
    if confined:
        command = [sys.executable, '-I', '-S', 'scripts/gate_candidate.py', '--root', str(ROOT), '--'] + command
    run = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, timeout=900)
    lines = run.stdout.splitlines()
    return {'confined': confined, 'command': command[-4:] if not confined else command[:6] + ['...'],
            'summary': [ln for ln in lines if ln.startswith('selftest (PARTIAL')],
            'suite_line': [ln.strip() for ln in lines if ln.strip().startswith(SUITE)],
            'failed': [ln.strip()[:600] for ln in lines if 'SELFTEST FAIL: VELDO-0220' in ln]}


def main():
    spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
    teeth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(teeth)
    cases = [case for case in teeth.cases() if case['finding'] == 220]
    assert [c['name'] for c in cases] == ['host220-ignores-lock', 'host220-lock-inherited',
                                         'host220-no-scope', 'host220-not-started-is-red'], cases
    runs = []
    for case in cases:
        for mode in ('baseline', 'mutant'):
            with tempfile.TemporaryDirectory(prefix='veldo-0220-proof-') as directory:
                made = teeth.materialize(case, mode, directory, ROOT)
                started = time.monotonic()
                result = teeth.worker(case, str(made['mutant']) if made['mutant'] else None)
            ours = {name.split()[-1]: ok for name, ok in result['observations'] if name.startswith('VELDO-0220 ')}
            runs.append({'case': case['name'], 'mode': mode, 'module': case['module'], 'target_rows': case['rows'],
                         'old_digest': made['old_digest'], 'new_digest': made['new_digest'],
                         'rows': ours, 'targets': result['targets'],
                         'failed_rows': [r for r in result['failed_rows'] if r.startswith('VELDO-0220 ')],
                         'seconds': round(time.monotonic() - started, 2)})
            if mode == 'baseline':
                assert sorted(ours) == sorted(ROWS) and all(ours.values()), (case['name'], ours)
            else:
                assert all(ours[row] is False for row in case['rows']), (case['name'], ours)
    record = {'schema': 'veldo.local-checks/v1', 'spec': 'VELDO-0220',
              'commit': subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=str(ROOT), capture_output=True,
                                       text=True).stdout.strip(),
              'dirty': bool(subprocess.run(['git', 'status', '--porcelain', '--', 'scripts', '.veldo', 'engine'],
                                           cwd=str(ROOT), capture_output=True, text=True).stdout.strip()),
              'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'suite': [suite_run(False), suite_run(True)], 'falsifiers': runs}
    plain = record['suite'][0]
    assert plain['failed'] == [] and re.search(r' 0 failed', plain['summary'][0]), plain
    (Path(__file__).parent / 'local_checks.json').write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
    for run in runs:
        print('%-28s %-8s failed=%s' % (run['case'], run['mode'], run['failed_rows']))
    for run in record['suite']:
        print('suite confined=%s %s %s' % (run['confined'], run['suite_line'], [f[:160] for f in run['failed']]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
