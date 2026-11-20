#!/usr/bin/env python3
"""Repeat the entire suite 78 worker under the host_heavy.sh lock; retain compact row receipts."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PROOF = Path(__file__).resolve().parent
RUNS, JOBS = 1000, 40
CASE = 'claude-launch-wait-skips-exited'


def run(index):
    started = time.monotonic()
    result = subprocess.run([sys.executable, 'scripts/check_teeth_mutations.py', '--worker', CASE],
                            cwd=ROOT, capture_output=True, text=True, timeout=600)
    receipt = json.loads(result.stdout.splitlines()[-1])
    red = receipt['failed_rows']
    required = ['VELDO-0060 ' + name for name in ('pin/rehash-before-exec', 'pin/rehash-dot-dot',
                'contained/rehash-before-exec', 'launch/exited-before-settle', 'launch/record-before-report')]
    if any(receipt['row_names'].count(name) != 1 for name in required):
        raise AssertionError('required rehash/regression row missing or duplicated')
    return {'run': index, 'seconds': round(time.monotonic() - started, 3), 'returncode': result.returncode,
            'count': receipt['count'], 'red': red,
            'rehash_rows': 3, 'regression_rows': 2,
            'rehash_red': [name for name in red if 'rehash' in name],
            'details': receipt['failed_details']}


def main():
    started = time.monotonic()
    paths = ['.veldo/control_launch.py', 'engine/.veldo/control_launch.py',
             'scripts/suites/78_veldo_0060_claude_adapter.py',
             'scripts/check_teeth_mutations.py']
    summary = {'runs': RUNS, 'jobs': JOBS, 'completed': 0, 'red_runs': 0, 'red_rows': 0,
               'rehash_rows': 0, 'rehash_red_rows': 0, 'regression_rows': 0, 'errors': [],
               'implementation_commit': subprocess.check_output(
                   ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
               'sha256': {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths}}
    with (PROOF / 'loaded.jsonl').open('w') as log, concurrent.futures.ThreadPoolExecutor(JOBS) as pool:
        tasks = {pool.submit(run, index): index for index in range(RUNS)}
        for future in concurrent.futures.as_completed(tasks):
            try:
                receipt = future.result()
            except Exception as error:
                receipt = {'run': tasks[future], 'error': str(error)[:1000]}
                summary['errors'].append(receipt)
            else:
                summary['completed'] += 1
                summary['red_runs'] += bool(receipt['red'])
                summary['red_rows'] += len(receipt['red'])
                summary['rehash_red_rows'] += len(receipt['rehash_red'])
                summary['rehash_rows'] += receipt['rehash_rows']
                summary['regression_rows'] += receipt['regression_rows']
                if receipt['returncode']:
                    summary['errors'].append({'run': receipt['run'], 'returncode': receipt['returncode']})
            log.write(json.dumps(receipt, sort_keys=True) + '\n')
            log.flush()
            done = summary['completed'] + len([e for e in summary['errors'] if 'error' in e])
            if done % 40 == 0:
                print('completed=%d red_runs=%d rehash_red_rows=%d errors=%d' % (
                    done, summary['red_runs'], summary['rehash_red_rows'], len(summary['errors'])), flush=True)
    summary['seconds'] = round(time.monotonic() - started, 3)
    (PROOF / 'loaded-summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, sort_keys=True), flush=True)
    return int(bool(summary['red_runs'] or summary['errors']))


if __name__ == '__main__':
    sys.exit(main())
