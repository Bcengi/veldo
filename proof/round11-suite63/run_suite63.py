"""Round 11 proof: repeat suite 63 alone and under a scope load, and keep a small summary.

  python3 proof/round11-suite63/run_suite63.py observe         one suite run, in this process
  python3 proof/round11-suite63/run_suite63.py alone 20        20 runs with no load of its own
  python3 proof/round11-suite63/run_suite63.py loaded 20       20 runs beside 15 load workers
  python3 proof/round11-suite63/run_suite63.py both 20         alone, then loaded

Each run is its own systemd user scope with MemoryMax=10G. A load worker loops a new user scope
that burns 0.5 s of CPU. The raw log of every run is hashed, measured and then deleted; only
<mode>.summary.json beside this file is kept.
"""

import hashlib
import json
import os
from pathlib import Path
import platform
import runpy
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
PROOF = Path(__file__).resolve().parent
SUITE = '63_veldo_0040_containment'
WORKERS = 15
SCOPE = ['systemd-run', '--user', '--scope', '-q', '-p', 'MemoryMax=10G']
BURN = 'import time\nend = time.process_time() + 0.5\nwhile time.process_time() < end:\n    pass\n'
MARK = 'ROUND11_OBSERVED '
# The suite's own bounds, repeated here only to print each measured value beside its bound.
BOUNDS = {'first_beat_after_activation': 1.2, 'last_beat_after_activation': 1.2 + 0.5 + 1.0,
          'cap_stop_after_activation': 1.2 + 0.5, 'exit_latency': 0.75}


def observe():
    """Run the suite through the dispatcher's selector and print what it measured."""
    sys.argv = [str(ROOT / 'scripts' / 'selftest.py'), '--suite', SUITE]
    try:
        runpy.run_path(sys.argv[0], run_name='__main__')
    except SystemExit as error:
        status = error.code
    else:
        raise RuntimeError('The dispatcher did not return its selector status')
    seen = getattr(sys.modules.get('shared'), '_V40_OBSERVED', None) or {}
    cap, idle = seen.get('runtime_cap') or {}, seen.get('exit_notified') or {}
    active, beats = cap.get('active') or 0, cap.get('beats_monotonic') or []
    terms = cap.get('term_monotonic') or []
    values = {
        'first_beat_after_activation': beats[0] - active if beats and active else None,
        'last_beat_after_activation': cap.get('last_beat_after_active'),
        'cap_stop_after_activation': terms[0] - active if terms and active else None,
        'submit_to_running': (cap['running_at'] - cap['began']
                              if cap.get('running_at') and cap.get('began') else None),
        'exit_latency': idle.get('latency'),
        'runtime_false_conjuncts': cap.get('false_conjuncts'),
        'cooperative_deadline_stop': ((seen.get('cooperative') or {}).get('termination') or {}).get('deadline_stop'),
        'escalation_deadline_stop': ((seen.get('escalation') or {}).get('termination') or {}).get('deadline_stop'),
        'raised': [label for label, _ in seen.get('raised') or []],
    }
    print(MARK + json.dumps(values, sort_keys=True), flush=True)
    sys.exit(status)


def load_average():
    return float(Path('/proc/loadavg').read_text().split()[0])


def text(*command):
    return subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


def spread(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return {'min': round(min(values), 4), 'median': round(statistics.median(values), 4),
            'max': round(max(values), 4), 'count': len(values)}


def one_run(raw, index):
    """One suite run in its own scope; its parsed result and the facts of its raw log."""
    log = raw / ('run-%02d.log' % index)
    before, started = load_average(), time.monotonic()
    with log.open('wb') as handle:
        status = subprocess.run(SCOPE + [sys.executable, str(Path(__file__).resolve()), 'observe'], cwd=ROOT,
                                stdin=subprocess.DEVNULL, stdout=handle, stderr=subprocess.STDOUT).returncode
    elapsed = time.monotonic() - started
    data = log.read_bytes()
    lines = data.decode('utf-8', 'replace').splitlines()
    failures = [line.split('SELFTEST FAIL: ', 1)[1].split(': ', 1)[0] for line in lines if 'SELFTEST FAIL: ' in line]
    partial = next((line for line in lines if line.startswith('selftest (PARTIAL,')), '')
    checks = next((int(line.split()[1]) for line in lines if line.split()[:1] == [SUITE] and 'passed' in line), None)
    observed = next((json.loads(line[len(MARK):]) for line in lines if line.startswith(MARK)), {})
    passed = status == 2 and ', 0 failed in ' in partial and not failures and checks is not None
    row = {'run': index, 'passed': passed, 'status': status, 'suite_checks_passed': checks, 'failed_labels': failures,
           'seconds': round(elapsed, 2), 'load_before': before, 'load_after': load_average(), 'observed': observed}
    if not passed:
        row['partial_line'] = partial[:200]
    return row, {'name': log.name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def load_worker(stop, counts, lock):
    while not stop.is_set():
        status = subprocess.run(SCOPE + [sys.executable, '-c', BURN], stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        with lock:
            counts['scopes'] += 1
            counts['errors'] += status != 0


def measure(mode, runs):
    stop, counts, lock, threads = threading.Event(), {'scopes': 0, 'errors': 0}, threading.Lock(), []
    raw = Path(tempfile.mkdtemp(prefix='round11-%s-' % mode))
    load_start = load_average()
    try:
        if mode == 'loaded':
            threads = [threading.Thread(target=load_worker, args=(stop, counts, lock)) for _ in range(WORKERS)]
            for thread in threads:
                thread.start()
            end = time.monotonic() + 15  # the load is up before the first run starts
            while time.monotonic() < end and counts['scopes'] < 2 * WORKERS:
                time.sleep(0.5)
        rows, files = [], []
        for index in range(1, runs + 1):
            row, fact = one_run(raw, index)
            rows.append(row)
            files.append(fact)
            print('%s run %2d: %s, %s checks, %.1f s, load %.1f, failed %s'
                  % (mode, index, 'pass' if row['passed'] else 'FAIL', row['suite_checks_passed'], row['seconds'],
                     row['load_after'], row['failed_labels']), flush=True)
    finally:
        stop.set()
        for thread in threads:
            thread.join()
        shutil.rmtree(raw)
    seen = [row['observed'] for row in rows]
    measured = {name: dict(spread([o.get(name) for o in seen]) or {}, bound=bound,
                           rule=('not a suite conjunct: the descendant has to be running before the cap fires'
                                 if name == 'first_beat_after_activation' else 'the suite requires a value below the bound'))
                for name, bound in BOUNDS.items()}
    measured['submit_to_running'] = spread([o.get('submit_to_running') for o in seen])
    good = sum(row['passed'] for row in rows)
    summary = {
        'command': 'python3 proof/round11-suite63/run_suite63.py %s %d, started through the shared gate lock '
                   'in a user scope with MemoryMax=10G; each run is %s python3 '
                   'proof/round11-suite63/run_suite63.py observe' % (mode, runs, ' '.join(SCOPE)),
        'environment': {
            'commit': text('git', 'rev-parse', 'HEAD'), 'tree': text('git', 'rev-parse', 'HEAD^{tree}'),
            'uncommitted_changes_under_scripts': bool(text('git', 'status', '--porcelain', '--', 'scripts')),
            'host': platform.node(), 'kernel': platform.release(), 'cores': os.cpu_count(),
            'python': platform.python_version(), 'systemd': text('systemctl', '--version').splitlines()[0],
            'load_1min': {'at_start': load_start, 'at_end': load_average(),
                          'per_run_after': spread([row['load_after'] for row in rows])},
        },
        'load': ({'workers': WORKERS, 'work': 'each worker loops a new systemd user scope (MemoryMax=10G) that '
                  'burns 0.5 s of CPU', 'scopes_finished': counts['scopes'], 'scope_errors': counts['errors']}
                 if mode == 'loaded' else 'none started by this run'),
        'deciding': {
            'runs': len(rows), 'passed': good, 'failed': len(rows) - good,
            'verdict': 'pass' if good == runs == len(rows) else 'fail',
            'rule': 'every run ends with selector status 2, a partial line with 0 failed and no failed row',
            'suite_checks_passed_per_run': sorted({row['suite_checks_passed'] for row in rows}, key=str),
            'failures': [{k: row[k] for k in ('run', 'status', 'failed_labels', 'seconds', 'load_after', 'observed')}
                         for row in rows if not row['passed']],
            'run_seconds': spread([row['seconds'] for row in rows]),
            'measured_seconds': measured,
            'cooperative_deadline_stop': sorted({str(o.get('cooperative_deadline_stop')) for o in seen}),
            'escalation_deadline_stop': sorted({str(o.get('escalation_deadline_stop')) for o in seen}),
        },
        'raw_files': {'kept': False, 'files': files},
    }
    (PROOF / ('%s.summary.json' % mode)).write_text(json.dumps(summary, indent=1, sort_keys=True) + '\n')
    return good == runs


if __name__ == '__main__':
    if sys.argv[1:] == ['observe']:
        observe()
    modes = {'alone': ['alone'], 'loaded': ['loaded'], 'both': ['alone', 'loaded']}[sys.argv[1]]
    results = [measure(mode, int(sys.argv[2])) for mode in modes]
    sys.exit(0 if all(results) else 1)
