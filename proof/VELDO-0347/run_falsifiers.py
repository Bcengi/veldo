#!/usr/bin/env python3
"""VELDO-0347: run each registered falsifier (scripts/check_teeth_mutations.py, finding 347) once,
through the driver's own materialize() and worker(): a no-op copy, then the mutant copy, each in its own
worker process. Writes falsifiers.json and mutations.txt beside this file. Sequential: one suite at a time."""
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts' / 'check_teeth_mutations.py')
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
CRITERION = {'ignored': 'AC1', 'beneath-worktrees': 'AC2', 'logs': 'AC2', 'remote-ref': 'AC2',
             'folder-remover': 'AC3', 'without-snapshot': 'AC3', 'without-comparison': 'AC3',
             'marked-name': 'AC3', 'measured-digest': 'AC4', 'beneath-the-item': 'AC5', 'formless': 'AC5',
             # Fix round 1: the review's findings, each by the criterion it guards.
             'trunk-is-head': 'AC4', 'table-1-': 'AC3', 'unlistable': 'AC2', 'present-taken': 'AC2',
             'table-2-not-whole': 'AC5', 'batch-clone-never': 'AC3', 'own-look-on-worktrees': 'AC5'}
WORK = '161_veldo_0347_space_work.py'  # this ticket's suite: a case's red rows stay within its criterion


def run(case, mode):
    with tempfile.TemporaryDirectory(prefix='v347-mutant-') as folder:
        made = T.materialize(case, mode, folder, ROOT)
        done = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'check_teeth_mutations.py'), '--finding', '347',
                               '--worker', case['name'], '--mutant', str(made['mutant'])],
                              capture_output=True, text=True, timeout=1800)
        if done.returncode:
            raise RuntimeError(case['name'] + ' ' + mode + ': ' + done.stderr[-500:])
        return json.loads(done.stdout.strip().splitlines()[-1])


results, lines = [], ['# VELDO-0347 registered mutation cases (finding 347), each applied once through the driver\'s '
                      'materialize() and worker(): noop copy then mutant copy, target rows.']
for case in [c for c in T.cases() if c['finding'] == 347]:
    noop, mutant = run(case, 'noop'), run(case, 'mutant')
    red = sorted(set(name.split(' ', 1)[-1] for name in mutant['failed_rows']))
    noop_red = sorted(set(name.split(' ', 1)[-1] for name in noop['failed_rows']))
    criterion = next(v for k, v in CRITERION.items() if k in case['name'])
    # Review F4: in this ticket's suite each row has its own guard, so a falsifier of one criterion turns
    # only that criterion's rows red; the others still read green under the mutant.
    within = (all(row.startswith(criterion.lower() + '/') for row in red) if case['suite'] == WORK else None)
    as_expected = not noop_red and all(row in red for row in case['rows']) and within is not False
    results.append({'falsifier': case['name'], 'module': case['module'], 'suite': case['suite'],
                    'criterion': criterion, 'red_within_criterion': within,
                    'expected_red': case['rows'], 'red_rows': red,
                    'red_details': [d for d in mutant['failed_details'] if d[0].split(' ', 1)[-1] in case['rows']],
                    'noop_red_rows': noop_red, 'red_as_expected': as_expected})
    lines.append('%s noop rows %d targets %s failed %s' % (case['name'], noop['count'],
                 json.dumps({k: v for k, v in noop['targets'].items()}), noop_red))
    lines.append('%s mutant rows %d targets %s failed %s' % (case['name'], mutant['count'],
                 json.dumps({k: v for k, v in mutant['targets'].items()}), red))
    print(lines[-1], flush=True)
def local(text):
    """No path of this checkout in the proof: a row's words may quote a traceback's file."""
    return text.replace(str(ROOT) + '/', '')


(HERE / 'falsifiers.json').write_text(local(json.dumps(results, indent=1)) + '\n')
(HERE / 'mutations.txt').write_text(local('\n'.join(lines)) + '\n')
print('all red as expected' if all(r['red_as_expected'] for r in results) else 'NOT all red as expected')
