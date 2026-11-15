"""Apply this ticket's registered defects once each, without running a teeth stage."""
import importlib.util
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('registered_mutations', ROOT / 'scripts/check_teeth_mutations.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
results = []
for case in module.cases():
    if case['finding'] != 336:
        continue
    with tempfile.TemporaryDirectory(prefix='falsifier-', dir=Path(__file__).parent) as folder:
        made = module.materialize(case, 'mutant', folder)
        observed = module.worker(case, str(made['mutant']))
        targets = observed['targets']
        rejected = all(values and False in values for values in targets.values())
        record = {'name': case['name'], 'module': case['module'], 'targets': targets,
                  'rejected': rejected, 'failed_rows': observed['failed_rows'],
                  'failed_details': observed['failed_details'],
                  'old_digest': made['old_digest'], 'new_digest': made['new_digest']}
        results.append(record)
        print(case['name'] + ': ' + ('rejected' if rejected else 'NOT REJECTED'), flush=True)
Path(__file__).with_name('falsifiers.json').write_text(json.dumps({
    'scope': 'VELDO-0336 isolated applications only; no teeth stage or full gate run',
    'results': results}, indent=1) + '\n')
raise SystemExit(0 if all(row['rejected'] for row in results) else 1)
