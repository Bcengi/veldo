"""Behavioral regression: controlled ordering, real signatures and crash recovery.

Accept probe receipts, not source text. The old fixture fails this test because it
does not place a receipt and its retirement at the required fractional instants.
Only the investigated row and named clock row qualify here; every other raw
observation remains in the receipt and is never relabeled green.
"""
import gzip
import json
from pathlib import Path
import sys


def check(receipt):
    failures = []
    runs = receipt['runs']
    for mode in ('baseline', 'noop', 'mutant'):
        if sum(r['mode'] == mode for r in runs) < 3:
            failures.append(mode + ': fewer than three runs')
    for run in runs:
        mode, op = run['mode'], run['operands']
        rows = dict(run['result']['observations'])
        base = int(op['signed_at'])
        checks = {
            'fractional signing boundary': op['signed_at'] == base + .25,
            'fractional retirement boundary': op['retired_at'] == base + (0 if mode == 'mutant' else .75),
            'real committed crash': op['committed'] and op['killed'] and op['snapshot_preserved'],
            'projection repair': op['unpublished_refusal'] == 'projection-mismatch' and op['published_accepted'],
            'historical verification': op['historical_valid'] == (mode != 'mutant'),
            'fresh verification refuses': op['fresh_valid'] is False,
            'kill row verdict': rows['VELDO-0027 signing/kill-after-rotation'] == (mode != 'mutant'),
            'clock row verdict': rows['VELDO-0027 signing/transition-clock'] == (mode != 'mutant'),
            'post-lock clock': op.get('lock_release') == base + 4.75 and
                              op.get('clock_effective') == base + (4 if mode == 'mutant' else 4.75),
        }
        failures.extend(f"{run['repeat']}/{mode}: {name}" for name, passed in checks.items() if not passed)
    return dict(host=receipt['host'], commit=receipt['commit'], runs=len(runs),
                passed=not failures, failures=failures)


if __name__ == '__main__':
    results = [check(json.loads(gzip.decompress(Path(path).read_bytes()) if path.endswith('.gz')
                               else Path(path).read_bytes())) for path in sys.argv[1:]]
    print(json.dumps(results, indent=2))
    sys.exit(not results or any(not r['passed'] for r in results))
