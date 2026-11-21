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
             'marked-name': 'AC3', 'measured-digest': 'AC4', 'beneath-the-item': 'AC5', 'formless': 'AC5'}


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
    red = sorted(set(name.split('VELDO-0347 ', 1)[-1] for name in mutant['failed_rows']))
    noop_red = sorted(set(name.split('VELDO-0347 ', 1)[-1] for name in noop['failed_rows']))
    as_expected = not noop_red and all(row in red for row in case['rows'])
    results.append({'falsifier': case['name'], 'module': case['module'],
                    'criterion': next(v for k, v in CRITERION.items() if k in case['name']),
                    'expected_red': case['rows'], 'red_rows': red,
                    'red_details': [d for d in mutant['failed_details'] if d[0].split('VELDO-0347 ', 1)[-1] in case['rows']],
                    'noop_red_rows': noop_red, 'red_as_expected': as_expected})
    lines.append('%s noop rows %d targets %s failed %s' % (case['name'], noop['count'],
                 json.dumps({k: v for k, v in noop['targets'].items()}), noop_red))
    lines.append('%s mutant rows %d targets %s failed %s' % (case['name'], mutant['count'],
                 json.dumps({k: v for k, v in mutant['targets'].items()}), red))
    print(lines[-1], flush=True)
(HERE / 'falsifiers.json').write_text(json.dumps(results, indent=1) + '\n')
(HERE / 'mutations.txt').write_text('\n'.join(lines) + '\n')
print('all red as expected' if all(r['red_as_expected'] for r in results) else 'NOT all red as expected')
