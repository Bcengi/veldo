#!/usr/bin/env python3
"""Read the last full mutation receipt; never launch validation workers.

Use the admission log's actual worker legs and historical case registrations,
then classify unconfined suites with the unchanged authority tracer exclusions.
Elapsed worker seconds include waits; they are neither CPU seconds nor gate wall time.
"""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def measure(log):
    spec = importlib.util.spec_from_file_location('measurement_trace', ROOT / 'scripts/case_trace.py')
    tracer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tracer)
    manifest = json.loads((ROOT / 'scripts/suites/manifest.json').read_text())
    suites = {entry['file']: entry['name'] for entry in manifest['suites']}
    declaration = (ROOT / 'scripts/gate_unconfined.json').read_bytes()
    records = []
    for number, line in enumerate(Path(log).open(), 1):
        if '"admissions"' not in line or '"worker_outcomes"' not in line:
            continue
        record = json.loads(line[line.index('{'):])
        if record.get('scope') == 'full' or record.get('registered') == 4023:
            records.append((number, record))
    if len(records) != 1:
        raise ValueError('expected exactly one full mutation receipt')
    number, record = records[0]
    if record['unconfined']['declaration'] != 'sha256:' + hashlib.sha256(declaration).hexdigest():
        raise ValueError('historical confinement declaration differs')
    cases = {item['case']['identity']: item['case'] for item in record['results']}
    groups = collections.defaultdict(lambda: dict(cases=0, controls=0, mutant_seconds=0., control_seconds=0.))
    seen = set()
    for worker in record['worker_outcomes']:
        if worker['name'] in seen:
            raise ValueError('duplicate worker')
        seen.add(worker['name'])
        mutant = worker['mode'] == 'mutant'
        if not mutant and worker['mode'] not in ('baseline', 'noop'):
            raise ValueError('unknown worker mode')
        suite = cases[worker['name']]['suite'] if mutant else worker['name'].split(':')[0]
        if suite not in suites or worker['leg'] not in ('confined', 'unconfined'):
            raise ValueError('unmapped suite or leg')
        group = ('confined' if worker['leg'] == 'confined' else
                 'unconfined_compatible' if tracer.compatible(ROOT, [suites[suite]]) else 'nested_or_excluded')
        row = groups[group]
        row['cases' if mutant else 'controls'] += 1
        row['mutant_seconds' if mutant else 'control_seconds'] += worker['elapsed']
    if sum(row['cases'] for row in groups.values()) != record['registered']:
        raise ValueError('case inventory differs')
    total = sum(row['mutant_seconds'] + row['control_seconds'] for row in groups.values())
    for row in groups.values():
        row['total_seconds'] = row['mutant_seconds'] + row['control_seconds']
        row['share_percent'] = 100 * row['total_seconds'] / total
    return dict(source_line=number, registered=record['registered'], total_worker_seconds=total,
                stage_elapsed=record['elapsed'], groups=dict(groups))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    args = parser.parse_args()
    print(json.dumps(measure(args.log), indent=2, sort_keys=True))
