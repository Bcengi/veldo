"""Apply only VELDO-0328's registered falsifiers, each once in an isolated copy."""
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('images328_mutations', ROOT / 'scripts/check_teeth_mutations.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
results = []
for case in [case for case in driver.cases() if case['name'].startswith('space328-')]:
    with tempfile.TemporaryDirectory(prefix='veldo-0328-falsifier-') as folder:
        root = Path(folder)
        control = driver.materialize(case, 'noop', root / 'control')
        baseline = driver.worker(case, str(control['mutant']))
        changed = driver.materialize(case, 'mutant', root / 'changed')
        mutant = driver.worker(case, str(changed['mutant']))
        caught = not baseline['failed_rows'] and all(
            mutant['targets'].get(row) and not all(mutant['targets'][row]) for row in case['rows'])
        results.append({'name': case['name'], 'rows': case['rows'], 'caught': bool(caught),
                        'control_checks': baseline['count'], 'control_failed': baseline['failed_rows'],
                        'mutant_failed': mutant['failed_rows'],
                        'details': mutant['failed_details'],
                        'source_sha256': changed['old_digest'], 'mutant_sha256': changed['new_digest']})
        print(case['name'], 'caught' if caught else 'FAILED', flush=True)
output = Path(__file__).with_name('falsifiers.json')
output.write_text(json.dumps({'cases': results, 'passed': all(row['caught'] for row in results)}, indent=2) + '\n')
raise SystemExit(0 if results and all(row['caught'] for row in results) else 1)
