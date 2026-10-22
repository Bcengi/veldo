"""VELDO-0161 falsifiers through check_teeth_mutations' own worker mode, for a host whose mutation coordinator
cannot start (this sandbox): the suite at baseline, then each registered finding-161 case with its mutant copy
(the driver's materialize writes it outside the tree and the worker substitutes it at the suite's PRODUCTION
anchor; the source is never edited), then the baseline again.

    python3 proof/VELDO-0161/run_falsifiers.py <checkout> <output.json> [case name ...]
"""
import importlib.util, json, subprocess, sys, tempfile, hashlib
from pathlib import Path
root = Path(sys.argv[1]); out = Path(sys.argv[2]); names = sys.argv[3:]
spec = importlib.util.spec_from_file_location('teeth', root / 'scripts/check_teeth_mutations.py')
T = importlib.util.module_from_spec(spec); spec.loader.exec_module(T)
cases = [c for c in T.cases() if c['finding'] == 161 and (not names or c['name'] in names)]
def run(case, mutant=None):
    argv = [sys.executable, str(root / 'scripts/check_teeth_mutations.py'), '--finding', '161', '--worker', case['name']]
    if mutant: argv += ['--mutant', str(mutant)]
    done = subprocess.run(argv, capture_output=True, text=True, cwd=root, timeout=1200)
    try:
        result = json.loads(done.stdout.strip().splitlines()[-1])
    except Exception:
        return {'exit': done.returncode, 'error': done.stderr[-2000:]}
    return {'exit': done.returncode, 'targets': result['targets'], 'failed_rows': [r for r in result['failed_rows'] if 'VELDO-0161' in r],
            'count': result['count']}
records = []
baseline = run(cases[0])
for case in cases:
    with tempfile.TemporaryDirectory() as d:
        m = T.materialize(case, 'mutant', d)
        mutant = run(case, m['mutant'])
    records.append({'case': case['name'], 'module': case['module'], 'rows': case['rows'],
                    'old_digest': m['old_digest'], 'mutant_digest': m['new_digest'],
                    'baseline_targets': {r: baseline.get('targets', {}).get(r) for r in case['rows']} if case is cases[0] else None,
                    'mutant': mutant})
    print(case['name'], json.dumps(mutant.get('targets')), flush=True)
after = run(cases[0])
out.write_text(json.dumps({'baseline_before': baseline, 'cases': records, 'baseline_after': after}, indent=1, sort_keys=True))
print('baseline before failed:', baseline.get('failed_rows'))
print('baseline after failed:', after.get('failed_rows'))
