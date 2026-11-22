"""Only B2's registered mutants, with a baseline and module no-ops; host runner required.

Every mutant is judged by each of its registered rows. Worker exceptions and absent rows
are errors, never mutation kills. Output is a small, path-scrubbed .txt receipt.

Usage: b2-mutation-controls.py <receipt.txt> [mutant name ...]. With names, only those registered
mutants run (beside the baseline and the no-op of each module they touch). A mutant counts only when
every bound row goes red by an assertion: a row whose only failure is a raised exception is not a kill.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
DRIVER = ROOT / 'scripts/check_teeth_mutations.py'
spec = importlib.util.spec_from_file_location('b2_mutations', DRIVER)
registry = importlib.util.module_from_spec(spec)
spec.loader.exec_module(registry)
cases = [case for case in registry.cases() if case['suite'] == '158_veldo_0359_store_guard.py']
chosen = sys.argv[2:]
if chosen:
    unknown = sorted(set(chosen) - {case['name'] for case in cases})
    if unknown:
        sys.exit('not a registered suite 158 mutant: ' + ', '.join(unknown))
    cases = [case for case in cases if case['name'] in chosen]
# Owner decision 2026-11-22 (Telegram 43030): recorded here because the worker captures the suite's output.
DEFERRED = ['layout/mounts: real directory, ancestor, database and lock bind mounts in the enforcement namespace',
            'layout/entries: a device entry in the store directory',
            'store359-file-binds-allowed against a real bind mount (it is judged on recorded mountinfo only)']


def run(case, mode, directory):
    prepared = registry.materialize(case, mode, directory, root=ROOT)
    argv = [sys.executable, '-B', str(DRIVER), '--worker', case['name']]
    if prepared['mutant'] is not None:
        argv += ['--mutant', str(prepared['mutant'])]
    environment = dict(os.environ)
    if mode == 'mutant':
        environment['VELDO_0359_ROWS'] = ','.join(case['rows'])
    result = subprocess.run(argv, cwd=ROOT, env=environment, capture_output=True, text=True, timeout=600)
    if result.returncode:
        return dict(case=case['name'], mode=mode, passed=False, error=result.stderr[-2000:])
    observed = json.loads(result.stdout)
    targets = observed['targets']
    present = all(targets.get(row) for row in case['rows'])
    # A row is red by assertion when at least one of its failed details is not a raised exception.
    asserted = {row: any(name.split()[-1] == row and not detail.startswith('raised ')
                         for name, detail in observed['failed_details']) for row in case['rows']}
    passed = present and (all(not all(targets[row]) and asserted[row] for row in case['rows']) if mode == 'mutant' else all(all(targets[row]) for row in case['rows']))
    return dict(case=case['name'], mode=mode, passed=passed, targets=targets,
                **({'red_by_assertion': asserted} if mode == 'mutant' else {}),
                failed_rows=observed['failed_rows'], failed_details=observed['failed_details'],
                rows={name.split()[-1]: ok for name, ok in observed['observations']},
                source_sha256=prepared['old_digest'], tested_sha256=prepared['new_digest'])


with tempfile.TemporaryDirectory(prefix='v359-b2-mutants-') as scratch:
    results = [run(cases[0], 'baseline', Path(scratch) / 'baseline')]
    modules = {}
    for case in cases:
        modules.setdefault(case['module'], case)
    for case, mode in [*( (case, 'noop') for case in modules.values()), *((case, 'mutant') for case in cases)]:
        if mode == 'mutant' and not all(results[0].get('rows', {}).get(row) for row in case['rows']):
            results.append(dict(case=case['name'], mode=mode, passed=False, status='NOT RUN', reason='unmutated target row incomplete on this host'))
        else:
            results.append(run(case, mode, Path(scratch) / (mode + '-' + case['name'])))
        print(case['name'], mode, results[-1]['passed'], flush=True)
    report = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  suite_sha256=hashlib.sha256((ROOT / 'scripts/suites/158_veldo_0359_store_guard.py').read_bytes()).hexdigest(),
                  passed=all(result['passed'] for result in results), selected=chosen or 'all',
                  deferred_by_owner_approval_2026_11_22=dict(
                      cases=DEFERRED, counted_as_passed=False,
                      follow_up='research/specs-pending/VELDO-0359-follow-up-real-mount-fixture.md'),
                  results=results)
    text = json.dumps(report, indent=2, sort_keys=True).replace(str(Path.home()), '~')
    text = re.sub(r'user-\d+\.slice|user@\d+\.service', '<user-unit>', text)
    text = re.sub(r'/run/user/\d+', '/run/user/<uid>', text)
    Path(sys.argv[1]).write_text(text + '\n')
    sys.exit(0 if report['passed'] else 1)
