#!/usr/bin/env python3
"""Regenerate readable signing evidence. Large raw gate logs stay in /tmp.

python3 proof/VELDO-0027/drive.py --mutations
python3 proof/VELDO-0027/drive.py --gate-log /tmp/veldo-0027-gate.log --gate-seconds SECONDS
The canonical gate, not this targeted driver, is the acceptance authority.
"""
import argparse
import ast
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
PROOF = ROOT / 'proof/VELDO-0027'
sys.dont_write_bytecode = True


def sha(body):
    return hashlib.sha256(body).hexdigest()


def write(name, value):
    (PROOF / name).write_text(json.dumps(value, indent=2) + '\n')


def suite():
    rows = []
    shared = ROOT / 'scripts/suites/shared.py'
    ns = {'__file__': str(shared), '__observe__': lambda n, c: rows.append({'row': n, 'passed': bool(c)})}
    tree = ast.parse(shared.read_text())
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        path = ROOT / 'scripts/suites/56_veldo_0027_signing.py'
        exec(compile(path.read_text(), str(path), 'exec'), ns)
    own = [{**r, 'row': r['row'].removeprefix('VELDO-0027 ')} for r in rows if r['row'].startswith('VELDO-0027 ')]
    assert all(r['passed'] for r in rows), [r for r in rows if not r['passed']]
    write('observations.json', {'rows': own, 'suite_seconds': ns['_v27_elapsed'],
                              'public_keys': {name: {'sha256': sha(key.encode())} for name, key in ns['_v27_public'].items()},
                              'private_material_retained': False,
                              'receipt_digests': [sha(ns['_v27_signer'].canonical(r)) for r in ns['_v27_results']],
                              'regenerate': 'python3 proof/VELDO-0027/drive.py --mutations'})


def mutations():
    started = time.monotonic()
    result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/check_teeth_mutations.py'),
                             '--finding', '27', '--diff-dir', str(PROOF)], capture_output=True, text=True, timeout=110)
    if result.returncode:
        raise RuntimeError(result.stderr)
    records = [json.loads(line) for line in result.stdout.splitlines()]
    write('mutations.json', {'command': 'python3 -B scripts/check_teeth_mutations.py --finding 27 --diff-dir proof/VELDO-0027',
                           'elapsed_seconds': time.monotonic() - started,
                           'results': records, 'raw_sha256': sha(result.stdout.encode()),
                           'note': 'Full gate additionally executes no-op controls and validates exact target observations.'})


def gate(log, seconds):
    body = log.read_bytes()
    lines = body.decode().splitlines()
    summary = [line for line in lines if line.startswith(('GATE:', 'catalog:', 'selftest: ', 'mutations:'))]
    report = next(json.loads(line) for line in lines if line.startswith('{"drivers":'))
    compact = {k: report[k] for k in ('schema', 'registered', 'executed', 'rejected', 'elapsed', 'input_digest', 'implementation_digest', 'invalid_results', 'drivers') if k in report}
    compact['signing_cases'] = [
        {'case': row['case']['name'], 'old_digest': row['old_digest'], 'new_digest': row['new_digest'],
         'baseline_failed': row['baseline']['failed_rows'], 'noop_failed': row['noop']['failed_rows'],
         'mutant_failed': row['mutant']['failed_rows']}
        for row in report['results'] if row['case']['finding'] == 27]
    write('gate-summary.json', {'command': 'bash scripts/verify.sh', 'seconds': seconds,
                               'raw_log_sha256': sha(body), 'summary': summary, 'mutation_stage': compact,
                               'raw_log_committed': False,
                               'reason': 'Raw gate output includes pre-existing credential-shaped negative fixtures; retain digest and regenerate command only.'})
    (PROOF / 'gate.log').write_text('\n'.join(summary) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mutations', action='store_true')
    parser.add_argument('--gate-log', type=Path)
    parser.add_argument('--gate-seconds', type=float)
    args = parser.parse_args()
    if args.gate_log:
        gate(args.gate_log, args.gate_seconds)
    else:
        suite()
        if args.mutations:
            mutations()


if __name__ == '__main__':
    main()
