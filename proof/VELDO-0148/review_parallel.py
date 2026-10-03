#!/usr/bin/env python3
"""Scoped 16-way review-suite reproduction; never runs the repository gate.

Each suite runs alone in each detached disposable clone. Logs stay in --out;
results.json records every completed round. Exit 2 from a selected selftest is
expected and never constitutes gate evidence. No tracing or fault injection.
"""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SUITES = {'63_veldo_0049_floor': 46, '64_veldo_0050_proof': 40}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=5)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    clones = []
    with (out / 'setup.log').open('w') as log:
        for slot in range(16):
            clone = out / ('clone-%02d' % slot)
            subprocess.run(['git', 'clone', '-q', '--shared', '--no-checkout', str(ROOT), str(clone)],
                           stdout=log, stderr=log, check=True)
            subprocess.run(['git', 'checkout', '-q', '--detach', args.ref], cwd=clone,
                           stdout=log, stderr=log, check=True)
            home = out / ('home-%02d' % slot)
            bindir = home / 'bin'
            bindir.mkdir(parents=True)
            (bindir / 'python3').symlink_to(sys.executable)
            env = {'PATH': str(bindir) + ':/usr/bin:/bin', 'HOME': str(home), 'TMPDIR': str(home),
                   'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC',
                   'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'PYTHONHASHSEED': '0',
                   'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0'}
            clones.append((clone, env))
    results = {'revision': args.ref, 'workers': 16, 'rounds': []}
    for round_number in range(1, args.rounds + 1):
        for suite, expected in SUITES.items():
            def run(slot):
                clone, env = clones[slot]
                path = out / ('round-%d-%s-%02d.log' % (round_number, suite, slot))
                started = time.monotonic()
                with path.open('w') as log:
                    proc = subprocess.run([sys.executable, '-B', '-s', 'scripts/selftest.py', '--suite', suite],
                                          cwd=clone, env=env, stdout=log, stderr=log,
                                          start_new_session=True, timeout=300)
                lines = path.read_text().splitlines()
                summary = next((line for line in reversed(lines) if line.startswith('selftest (PARTIAL,')), '')
                match = re.search(r': (\d+) passed, (\d+) failed', summary)
                passed = (proc.returncode == 2 and match is not None
                          and tuple(map(int, match.groups())) == (expected, 0))
                return {'slot': slot, 'passed': bool(passed), 'exit': proc.returncode,
                        'seconds': round(time.monotonic() - started, 3), 'summary': summary,
                        'failures': [line for line in lines if 'SELFTEST FAIL:' in line]}
            with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
                runs = list(pool.map(run, range(16)))
            results['rounds'].append({'round': round_number, 'suite': suite, 'runs': runs})
            (out / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
            print('%s round %d: %d/16 green' % (suite, round_number, sum(r['passed'] for r in runs)), flush=True)
    return 0 if all(r['passed'] for batch in results['rounds'] for r in batch['runs']) else 1


if __name__ == '__main__':
    sys.exit(main())
