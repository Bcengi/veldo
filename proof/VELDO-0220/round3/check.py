#!/usr/bin/env python3
"""Ticket-only red and green runs through the real mutation coordinator.

Invoke under the owner's blocking host flock, passing an unchanged checkout of
6d879aae as the only argument. All fixture gates use scratch locks. Logs are
collected outside the input tree, then copied here after the coordinator exits.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
DEST = Path(__file__).resolve().parent
OLD = Path(sys.argv[1]).resolve()
EXPECTED = {
    'host220-ignores-lock': ('113_veldo_0220_gate_host', 'host-lock/held-not-started'),
    'host220-lock-inherited': ('113_veldo_0220_gate_host', 'host-lock/released-on-exit'),
    'host220-forged-holder': ('113_veldo_0220_gate_host', 'host-lock/held-not-started'),
    'host220-not-started-is-red': ('113_veldo_0220_gate_host', 'host-lock/not-started-not-red'),
    'host220-no-scope': ('114_veldo_0220_gate_scope', 'host-scope/own-scope'),
    'host220-no-scope-kill': ('114_veldo_0220_gate_scope', 'host-scope/own-scope'),
    'host220-lock-not-retained': ('114_veldo_0220_gate_scope', 'host-scope/own-scope'),
}
ENV = {k: v for k, v in os.environ.items() if not k.startswith('VELDO_GATE_')}
ENV['VELDO_GATE_FORCE_FRESH'] = '1'
ENV['PYTHONDONTWRITEBYTECODE'] = '1'
summary = {'commands': [], 'scope': 'VELDO-0220 suites and mutation cases only'}


def head(root):
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()


def run(root, name, args, work):
    started = time.monotonic()
    command = [sys.executable, *map(str, args)]
    with (work / (name + '.log')).open('w') as log:
        result = subprocess.run(command, cwd=root, env=ENV, stdout=log, stderr=subprocess.STDOUT)
    summary['commands'].append({'name': name, 'cwd': str(root), 'argv': command,
                                'exit': result.returncode, 'seconds': time.monotonic() - started})
    print(name, 'exit', result.returncode, flush=True)
    return result.returncode


with tempfile.TemporaryDirectory(prefix='v220-round3-results-') as temporary:
    work = Path(temporary)
    summary['red_head'], summary['green_head'] = head(OLD), head(ROOT)
    assert summary['red_head'].startswith('6d879aae')
    try:
        status = run(OLD, 'red-coordinator', [OLD / 'scripts/check_gate_mutations.py',
                     '--root', OLD, '--finding', '220', '--receipt', work / 'red-coordinator.json'], work)
        red = json.loads((work / 'red-coordinator.json').read_text())
        assert status == 1 and red['error'] == 'rows_scoped_unconfined_case', red
        assert red['registered'] == 7 and red['executed'] == 0, red

        status = run(ROOT, 'green-suites', ['scripts/selftest.py', '--suite',
                     '113_veldo_0220_gate_host', '--suite', '114_veldo_0220_gate_scope'], work)
        assert status == 2, 'Passing partial suite runs deliberately exit 2'
        suite_log = (work / 'green-suites.log').read_text()
        assert '0 failed' in suite_log, suite_log

        status = run(ROOT, 'green-coordinator', ['scripts/check_gate_mutations.py',
                     '--root', ROOT, '--finding', '220', '--receipt', work / 'green-coordinator.json',
                     '--worker-log-dir', work / 'workers'], work)
        green = json.loads((work / 'green-coordinator.json').read_text())
        assert status == 0 and green['status'] == 'passed', green
        assert (green['registered'], green['executed'], green['rejected'], green['reused']) == (7, 7, 7, 0)
        assert green['force_fresh'] and green['surviving_workers'] == 0 and not green['invalid_results']
        assert {r['case']['name'] for r in green['results']} == set(EXPECTED)
        summary['falsifiers'] = []
        outside = set(green['unconfined']['cases'])
        for result in sorted(green['results'], key=lambda r: r['case']['name']):
            case = result['case']
            suite, row = EXPECTED[case['name']]
            assert case['suite'] == suite + '.py' and case['rows'] == [row], case
            unconfined = case['identity'] in outside
            assert unconfined == suite.startswith('114_'), case
            observed = {}
            for mode in ('baseline', 'noop', 'mutant'):
                observed[mode] = [ok for name, ok in result[mode]['observations'] if name.split()[-1] == row]
                assert observed[mode] == [mode != 'mutant'], (case, mode, observed)
                if mode != 'mutant':
                    assert not result[mode]['failed_rows'], result[mode]
            summary['falsifiers'].append({'case': case['name'], 'suite': suite, 'row': row,
                                           'leg': 'unconfined' if unconfined else 'confined', **observed})
        sources = ['scripts/gate_host.py', 'scripts/check_gate_mutations.py', 'scripts/check_teeth_mutations.py',
                   'scripts/gate_unconfined.json', 'scripts/suites/manifest.json', 'scripts/suites/requires.json',
                   'scripts/suites/113_veldo_0220_gate_host.py', 'scripts/suites/114_veldo_0220_gate_scope.py',
                   '.veldo/lander.py', '.veldo/executor.py', '.veldo/control_proof.py']
        summary['sources'] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sources}
        summary['status'] = 'passed'
    finally:
        (work / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
        shutil.copytree(work, DEST, dirs_exist_ok=True)
print('All seven cases admitted; every mutant red, every baseline and no-op green.', flush=True)
