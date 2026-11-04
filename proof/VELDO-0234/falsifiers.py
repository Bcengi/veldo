#!/usr/bin/env python3
"""VELDO-0234: each registered mutant of finding 234, and the two VELDO-0171 cases whose anchors this change moved
(api171-funnel-in-place-of-serve, api171-origin-loopback), run by the teeth driver's own worker outside the gate's
confinement, because suites 127 and 85 run factory setup against this host's systemd user manager and suite 127 is
not (yet) on the owner's protected unconfined list (scripts/gate_unconfined.json); see OPEN.md.

For every case: the baseline (unmutated production copy) with every target row green, the mutant (the driver's
own materialize, its exact replacement) with at least one target row red, then the baseline again (green
restored). Writes falsifiers.json beside this file. Usage: python3 proof/VELDO-0234/falsifiers.py
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts' / 'check_teeth_mutations.py')
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)


def run(case, mutant=None):
    """The driver's worker in its own process (as the coordinator starts it): the targets of each row."""
    argv = [sys.executable, str(ROOT / 'scripts' / 'check_teeth_mutations.py'), '--finding', str(case['finding']),
            '--worker', case['name']] + (['--mutant', str(mutant)] if mutant else [])
    started = time.monotonic()
    done = subprocess.run(argv, capture_output=True, text=True, timeout=900, cwd=str(ROOT))
    seconds = round(time.monotonic() - started, 3)
    try:
        result = json.loads(done.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {'returncode': done.returncode, 'seconds': seconds, 'error': (done.stderr or done.stdout)[-600:]}
    return {'returncode': done.returncode, 'seconds': seconds, 'targets': result['targets'],
            'failed_rows': result['failed_rows'], 'failed_details': result['failed_details']}


def green(outcome):
    return 'targets' in outcome and not outcome['failed_rows'] and all(all(v) and v for v in outcome['targets'].values())


def red(outcome):
    return 'targets' in outcome and any(not all(v) for v in outcome['targets'].values())


def main():
    commit = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    moved = ('api171-funnel-in-place-of-serve', 'api171-origin-loopback')
    cases = [c for c in T.cases() if c['finding'] == 234 or c['name'] in moved]
    records = []
    for case in cases:
        with tempfile.TemporaryDirectory(prefix='v234-mutant-') as directory:
            made = T.materialize(case, 'mutant', directory)
            record = {'case': case['name'], 'suite': case['suite'], 'module': '.veldo/' + case['module'], 'rows': case['rows'],
                      'old': case['old'], 'new': case['new'], 'source_sha256': made['old_digest'],
                      'mutant_sha256': made['new_digest'], 'replacement_count': made['replacement_count']}
            record['baseline'] = run(case)
            record['mutant'] = run(case, made['mutant'])
            record['restored'] = run(case)
        record['verdict'] = ('red_under_mutant_green_restored'
                             if green(record['baseline']) and red(record['mutant']) and green(record['restored'])
                             else 'not_proven')
        records.append(record)
        print('%s: baseline %s, mutant %s %s, restored %s -> %s' % (
            case['name'], 'green' if green(record['baseline']) else 'NOT GREEN',
            'red' if red(record['mutant']) else 'NOT RED', record['mutant'].get('failed_rows'),
            'green' if green(record['restored']) else 'NOT GREEN', record['verdict']), flush=True)
    receipt = {'schema': 'veldo.falsifier_receipt/v1', 'spec': 'VELDO-0234', 'commit': commit,
               'driver': 'scripts/check_teeth_mutations.py --worker (unconfined; see OPEN.md)',
               'driver_sha256': hashlib.sha256((ROOT / 'scripts' / 'check_teeth_mutations.py').read_bytes()).hexdigest(),
               'suites': {c['suite']: hashlib.sha256((ROOT / 'scripts/suites' / c['suite']).read_bytes()).hexdigest()
                          for c in cases},
               'cases': records, 'proven': sum(r['verdict'] == 'red_under_mutant_green_restored' for r in records),
               'registered': len(records)}
    (Path(__file__).parent / 'falsifiers.json').write_text(json.dumps(receipt, indent=1, sort_keys=True) + '\n')
    print('falsifiers: %d of %d red under the mutant, green restored' % (receipt['proven'], receipt['registered']))
    return 0 if receipt['proven'] == receipt['registered'] else 1


if __name__ == '__main__':
    sys.exit(main())
