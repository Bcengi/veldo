"""Summarize the two original/split pc2 controls without running workloads."""
import gzip
import hashlib
import json
from pathlib import Path

here = Path(__file__).resolve().parent
data = {label: json.loads(gzip.decompress((here / label / 'controls-receipts.json.gz').read_bytes()))
        for label in ('original', 'split')}
names = ('pool-shared-profile', 'role127-resource-grant-omitted')
summary = {'cases': {}, 'environment': {}, 'files': {}}
for label in data:
    summary['environment'][label] = json.loads((here / label / 'controls-metadata.json').read_text())
for index, name in enumerate(names):
    entry = {}
    records = {}
    for label, receipts in data.items():
        receipt = receipts[index]
        row = dict(status=receipt['status'], elapsed=receipt['elapsed'],
            executed=receipt['executed'], rejected=receipt['rejected'], reused=receipt['reused'],
            invalid_results=receipt['invalid_results'], surviving_workers=receipt['surviving_workers'],
            workers=[{k: w.get(k) for k in ('mode', 'elapsed', 'scratch_removed', 'cleanup', 'error')}
                     for w in receipt['worker_outcomes']])
        if receipt['results']:
            record = next(r for r in receipt['results'] if r['case']['name'] == name)
            records[label] = record
            row.update(kills=record['kills'], kill_by=record['kill_by'],
                observations={mode: record[mode]['observations'] for mode in ('baseline', 'noop', 'mutant')},
                failed_details={mode: record[mode].get('failed_details', []) for mode in ('baseline', 'noop', 'mutant')})
        entry[label] = row
    entry['green'] = all(entry[label]['status'] == 'passed' and entry[label]['executed'] == 1
                        and entry[label]['rejected'] == 1 and entry[label]['reused'] == 0
                        and not entry[label]['invalid_results'] and entry[label]['surviving_workers'] == 0
                        for label in data)
    if len(records) == 2:
        entry['same_named_kills'] = records['original']['kills'] == records['split']['kills']
        entry['common_observations_match'] = {}
        for mode in ('baseline', 'noop', 'mutant'):
            original = dict(records['original'][mode]['observations'])
            split = dict(records['split'][mode]['observations'])
            entry['common_observations_match'][mode] = all(original[k] == split[k] for k in original.keys() & split.keys())
            entry.setdefault('extracted_rows', {})[mode] = sorted(original.keys() - split.keys())
    summary['cases'][name] = entry
for path in sorted(here.rglob('*')):
    if path.is_file() and path.name != 'summary.json' and '__pycache__' not in path.parts:
        summary['files'][str(path.relative_to(here))] = hashlib.sha256(path.read_bytes()).hexdigest()
(here / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps({name: {k: v for k, v in row.items() if k not in data}
                  for name, row in summary['cases'].items()}, indent=2))
