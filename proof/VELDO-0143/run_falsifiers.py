"""VELDO-0143 falsifiers through check_teeth_mutations' own worker mode, for a host whose mutation coordinator
cannot start (this sandbox): the suite at baseline, then each registered finding-143 case with its mutant copy
(the driver's materialize writes it outside the tree and the worker substitutes it at the suite's PRODUCTION
anchor; the source is never edited), then the baseline again. Adapted from proof/VELDO-0161/run_falsifiers.py.

    python3 proof/VELDO-0143/run_falsifiers.py <checkout> <output.json> [case name ...]
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile

FINDING, LABEL = 143, 'VELDO-0143'
root, out, names = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
spec = importlib.util.spec_from_file_location('teeth', root / 'scripts/check_teeth_mutations.py')
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)
cases = [c for c in T.cases() if c['finding'] == FINDING and (not names or c['name'] in names)]


def run(case, mutant=None):
    argv = [sys.executable, str(root / 'scripts/check_teeth_mutations.py'), '--finding', str(FINDING), '--worker',
            case['name']]
    if mutant:
        argv += ['--mutant', str(mutant)]
    done = subprocess.run(argv, capture_output=True, text=True, cwd=root, timeout=1800)
    try:
        result = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {'exit': done.returncode, 'error': done.stderr[-2000:]}
    return {'exit': done.returncode, 'targets': result['targets'],
            'failed_rows': [r for r in result['failed_rows'] if LABEL in r], 'count': result['count']}


every_row = sorted({row for case in cases for row in case['rows']})
baseline = run(cases[0])
records = []
for case in cases:
    with tempfile.TemporaryDirectory() as directory:
        made = T.materialize(case, 'mutant', directory)
        mutant = run(case, made['mutant'])
    targets = mutant.get('targets') or {}
    # The worker reports each target row as the list of its expect results: killed when every one is red.
    killed = bool(targets) and all(row in targets and not any(targets[row] if isinstance(targets[row], list)
                                                              else [targets[row]]) for row in case['rows'])
    records.append({'case': case['name'], 'module': case['module'], 'rows': case['rows'],
                    'source_digest': made['old_digest'], 'mutant_digest': made['new_digest'],
                    'baseline_failed_rows': baseline.get('failed_rows'), 'mutant': mutant,
                    'new_failures_beyond_baseline': sorted(set(mutant.get('failed_rows') or [])
                                                           - set(baseline.get('failed_rows') or [])),
                    'result': 'killed: the target rows are red on the mutant' if killed
                    else 'not killed: a target row stayed green or the worker did not report'})
    print(case['name'], json.dumps(targets), 'killed' if killed else 'NOT KILLED', flush=True)
after = run(cases[0])
out.write_text(json.dumps({'baseline_before': baseline, 'cases': records, 'baseline_after': after}, indent=1,
                          sort_keys=True) + '\n')
print('baseline before failed:', baseline.get('failed_rows'))
print('baseline after failed:', after.get('failed_rows'))
