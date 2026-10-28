#!/usr/bin/env python3
"""Execute VELDO-0161's three setup161 falsifiers on suite 73, the worker run as an ordinary process of this host.

    python3 proof/VELDO-0161/round4/drive_setup.py [<output.json>]

As proof/VELDO-0185/drive.py does for suite 106: scripts/check_teeth_mutations.py's own worker runs each case
in a separate process of this host, once on the unchanged production modules (the baseline, where
`VELDO-0139 setup/lays-down` and every other suite 73 row must pass) and once per case on a copy of
control_factory_setup.py with the case's exact replacement (materialize; the source is never edited). A case
is killed when its named row is false under the mutant and every row the baseline passed is still there.

Why outside the confined domain: suite 73 runs factory setup, which qualifies the worker profile through this
host's systemd user manager, and the mutation stage's confined domain does not reach it (the baseline ends
unavailable_service:profile:user_manager, invalid_baseline). The gate's own mutation stage runs suite 73's
cases in its unconfined leg (scripts/gate_unconfined.json names 73_veldo_0139_factory_setup), as it does
finding 139's; `scripts/check_teeth_mutations.py --finding 161` passes no leg, so there every case is
confined. Exit 0 only when the baseline is green and every case is killed.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
TARGET = 'VELDO-0139 setup/lays-down'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def worker(name, mutant=None):
    """The teeth driver's own worker for case `name`, as a separate ordinary process: its JSON answer."""
    command = [sys.executable, '-B', str(ROOT / 'scripts/check_teeth_mutations.py'), '--finding', '161',
               '--worker', name] + (['--mutant', str(mutant)] if mutant else [])
    started = time.monotonic()
    done = subprocess.run(command, capture_output=True, text=True, timeout=1800, cwd=str(ROOT))
    lines = [line for line in done.stdout.splitlines() if line.startswith('{"count"')]
    answer = json.loads(lines[-1]) if lines else {'error': done.stderr[-600:]}
    answer.update(exit=done.returncode, seconds=round(time.monotonic() - started, 3))
    return answer


def main(argv):
    out = Path(argv[0]) if argv else None
    teeth = load('v161_teeth', ROOT / 'scripts/check_teeth_mutations.py')
    cases = [c for c in teeth.cases() if c['finding'] == 161 and c['suite'] == '73_veldo_0139_factory_setup.py']
    baseline = worker(cases[0]['name'])
    passed = {name for name, ok in baseline.get('observations', []) if ok}
    report = {'schema': 'veldo.mutation-registration/v1', 'spec_id': 'VELDO-0161', 'suite': cases[0]['suite'],
              'status': 'executed by proof/VELDO-0161/round4/drive_setup.py outside the confined stage',
              'baseline': {'exit': baseline.get('exit'), 'rows': baseline.get('count'),
                           'failed_rows': baseline.get('failed_rows'), 'target': TARGET in passed,
                           'error': baseline.get('error'), 'seconds': baseline.get('seconds')},
              'cases': []}
    for case in cases:
        with tempfile.TemporaryDirectory(prefix='v161-setup-mutant-') as directory:
            made = teeth.materialize(case, 'mutant', directory)
            answer = worker(case['name'], made['mutant'])
        observed = dict((name, ok) for name, ok in answer.get('observations', []))
        lost = sorted(name for name in passed if name not in observed)
        killed = TARGET in passed and observed.get(TARGET) is False and not lost and answer.get('exit') == 0
        report['cases'].append({'case': case['name'], 'module': '.veldo/' + case['module'], 'rows': case['rows'],
                                'old_digest': made['old_digest'], 'mutant_digest': made['new_digest'],
                                'exit': answer.get('exit'), 'count': answer.get('count'),
                                'failed_rows': answer.get('failed_rows'), 'target': observed.get(TARGET),
                                'rows_lost': lost, 'killed': killed, 'error': answer.get('error'),
                                'seconds': answer.get('seconds')})
        print(json.dumps({k: report['cases'][-1][k] for k in ('case', 'killed', 'target', 'failed_rows')}), flush=True)
    report['all_killed'] = (not report['baseline']['failed_rows'] and report['baseline']['target']
                            and all(c['killed'] for c in report['cases']))
    text = json.dumps(report, indent=1, sort_keys=True) + '\n'
    if out:
        out.write_text(text)
    print('baseline failed rows: %s' % report['baseline']['failed_rows'])
    print('setup161: %s' % ('all killed' if report['all_killed'] else 'NOT all killed'))
    return 0 if report['all_killed'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
