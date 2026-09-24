#!/usr/bin/env python3
"""Retain VELDO-0037 suite observations and driven mutation records; verification is the full gate.

Writes observations.json (every row and the suite's own observations), mutations.json (baseline,
byte-identical no-op copy and mutant target observations per registered finding-37 case, with red
rows and module digests), one unified diff per mutation, and timing.json.
"""
import difflib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'proof/VELDO-0037'
sys.path.insert(0, str(ROOT / 'scripts'))
import check_teeth_mutations as teeth  # noqa: E402


def suite_observations():
    rows = []
    suite = ROOT / 'scripts/suites/59_veldo_0037_aliases.py'
    namespace = {'ROOT': ROOT, '__file__': str(suite),
                 'expect': lambda name, condition: rows.append([name, bool(condition)])}
    started = time.monotonic()
    exec(compile(suite.read_text(), str(suite), 'exec'), namespace)
    elapsed = time.monotonic() - started
    return dict(namespace['_s37_observations'], rows=rows), elapsed


def mutant_observations(case, mutant):
    """The suite's own observations against one mutant copy: what actually failed, not only which row."""
    suite = ROOT / 'scripts/suites/59_veldo_0037_aliases.py'
    anchor = 'ROOT / ".veldo" / "%s"' % case['module']
    source = suite.read_text().replace(anchor, '__import__("pathlib").Path(%r)' % str(mutant))
    namespace = {'ROOT': ROOT, '__file__': str(suite), 'expect': lambda name, condition: None}
    exec(compile(source, str(suite), 'exec'), namespace)
    found = namespace['_s37_observations']
    return {'independent_allocations': found['allocations'].get('independent'),
            'stale_overwrite_refusals': found['refusals'].get('stale-overwrite'),
            'reader_v1': {alias: {k: v for k, v in value.items() if k != 'body'}
                          for alias, value in found['readers'].get('v1', {}).items()},
            'reader_tampered': {k: v for k, v in (found['readers'].get('tampered') or {}).items() if k != 'body'},
            'invalid_unit_id_checks': found['refusals'].get('invalid-unit-id')}


def worker(case, mutant=None):
    command = [sys.executable, '-B', str(ROOT / 'scripts/check_teeth_mutations.py'), '--worker', case['name']]
    if mutant:
        command += ['--mutant', str(mutant)]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if proc.returncode:
        raise RuntimeError('%s did not complete its assertions: %s' % (case['name'], proc.stderr[-2000:]))
    return json.loads(proc.stdout)


def main():
    observations, suite_seconds = suite_observations()
    observations['verification'] = 'Diagnostic observations; only bash scripts/verify.sh verifies the change.'
    (OUT / 'observations.json').write_text(json.dumps(observations, indent=2, sort_keys=True) + '\n')
    cases = [c for c in teeth.cases() if c['finding'] == 37]
    records = []
    with tempfile.TemporaryDirectory(prefix='veldo-0037-drive-') as directory:
        for case in cases:
            begun = time.monotonic()
            noop = teeth.materialize(case, 'noop', Path(directory) / (case['name'] + '-noop'))
            mutant = teeth.materialize(case, 'mutant', Path(directory) / (case['name'] + '-mutant'))
            honest, unchanged, broken = worker(case), worker(case, noop['mutant']), worker(case, mutant['mutant'])
            source = mutant['source'].read_text()
            relative = str(mutant['source'].relative_to(ROOT))
            (OUT / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                source.splitlines(keepends=True), source.replace(case['old'], case['new']).splitlines(keepends=True),
                n=0, fromfile='a/' + relative, tofile='b/' + relative)))
            records.append({'mutation': case['name'], 'module': case['module'], 'rows': case['rows'],
                            'baseline': honest['targets'], 'noop': unchanged['targets'], 'mutant': broken['targets'],
                            'baseline_failed_rows': honest['failed_rows'], 'noop_failed_rows': unchanged['failed_rows'],
                            'red_rows': broken['failed_rows'], 'assertions': broken['count'],
                            'replacement_count': mutant['replacement_count'], 'old_digest': mutant['old_digest'],
                            'noop_digest': noop['new_digest'], 'new_digest': mutant['new_digest'],
                            'elapsed_seconds': round(time.monotonic() - begun, 3),
                            'mutant_observations': mutant_observations(case, mutant['mutant'])})
    rejected = all(r['baseline'][row] == [True] and r['noop'][row] == [True] and r['mutant'][row] == [False]
                   and not r['baseline_failed_rows'] and not r['noop_failed_rows'] and r['noop_digest'] == r['old_digest']
                   for r in records for row in r['rows'])
    (OUT / 'mutations.json').write_text(json.dumps({
        'source': 'proof/VELDO-0037/drive.py over scripts/check_teeth_mutations.py finding 37',
        'status': 'rejected' if rejected else 'NOT REJECTED', 'registered': len(cases), 'records': records},
        indent=2, sort_keys=True) + '\n')
    (OUT / 'timing.json').write_text(json.dumps({
        'suite_seconds_in_process': round(suite_seconds, 3),
        'mutation_seconds_serial_baseline_noop_mutant': round(sum(r['elapsed_seconds'] for r in records), 3),
        'mutation_cases': len(records),
        'note': 'Component timings on this host; the lead measures the whole gate.'}, indent=2) + '\n')
    print(json.dumps({'rows': len(observations['rows']),
                      'failed': [n for n, ok in observations['rows'] if not ok],
                      'mutations': {r['mutation']: r['red_rows'] for r in records}, 'rejected': rejected}))
    return 0 if rejected and all(ok for _, ok in observations['rows']) else 1


if __name__ == '__main__':
    sys.exit(main())
