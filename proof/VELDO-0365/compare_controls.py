"""Falsify the bounded comparator without executing any host workload."""
import copy
import importlib.util
import json
from pathlib import Path
import sys

here = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('compare', here / 'compare.py')
compare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compare)
expected = json.loads((here / 'expected.json').read_text())
results = []
for value in expected:
    record = {k: v for k, v in value.items() if k != 'observations'}
    record.update({mode: dict(observations=rows) for mode, rows in value['observations'].items()})
    results.append(record)
receipt = dict(status='passed', scope='selected', registered=100, executed=100, rejected=100,
               reused=0, force_fresh=True, invalid_results=[], surviving_workers=0,
               qualification_ledger={'held': {}}, worker_outcomes=[dict(scratch_removed=True, cleanup={'directories': 1, 'units': []})],
               results=results, case_receipts=[dict(validated=True) for _ in results],
               elapsed=1, worker_invocations=1, peak_workers=1, input_digest='fixture', implementation_digest='fixture')
checks = {'positive': compare.compare(expected, receipt)['passed']}
for field, bad in [('status', 'failed'), ('executed', 99), ('registered', 101), ('reused', 1),
                   ('invalid_results', ['invalid']), ('surviving_workers', 1),
                   ('case_receipts', [dict(validated=False) for _ in results]),
                   ('qualification_ledger', dict(held={'worker': {}})),
                   ('worker_outcomes', [dict(error='hang', scratch_removed=True)])]:
    altered = copy.deepcopy(receipt)
    altered[field] = bad
    checks[field] = not compare.compare(expected, altered)['passed']
for change in ('missing', 'duplicate', 'observation', 'digest'):
    altered = copy.deepcopy(receipt)
    if change == 'missing':
        altered['results'].pop()
    elif change == 'duplicate':
        altered['results'][0] = altered['results'][1]
    elif change == 'observation':
        altered['results'][0]['mutant']['observations'][0][1] = 'different'
    else:
        altered['results'][0]['new_digest'] = 'different'
    checks[change] = not compare.compare(expected, altered)['passed']
print(json.dumps(dict(passed=all(checks.values()), checks=checks), indent=2))
sys.exit(not all(checks.values()))
