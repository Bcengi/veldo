#!/usr/bin/env python3
"""Drive finding 50 and record mutations.json: for each registered mutation, the row it names, the
rows it turned red, whether the named row went red, and whether that row's own region ran to its
end (its `ran/` row stayed green), so a red row is a failed assertion, never a raise.

Run from the repository root: python3 -B proof/VELDO-0050/mutations.py
"""
import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = ROOT / 'scripts/suites/64_veldo_0050_proof.py'
DECLARED = {'proof-kept-in-temporary-storage': 'AC1', 'proof-check-json-alone': 'AC2',
            'proof-default-passed-check': 'AC3', 'proof-executor-emits-verdict': 'AC4'}
COMMAND = ['python3', '-B', 'scripts/check_teeth_mutations.py', '--finding', '50', '--jobs', '4',
           '--diff-dir', 'proof/VELDO-0050/mutations']


def regions():
    """Each row label mapped to the first label of the region that asserts it."""
    owner = {}
    for node in ast.walk(ast.parse(SUITE.read_text())):
        if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'region':
            labels = [a.value for a in node.args if isinstance(a, ast.Constant)]
            for label in labels:
                owner[label] = labels[0]
    return owner


def main():
    spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
    teeth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(teeth)
    cases = {c['name']: c for c in teeth.cases() if c['finding'] == 50}
    started = time.monotonic()
    proc = subprocess.run(COMMAND, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    elapsed = time.monotonic() - started
    if proc.returncode:
        sys.exit(proc.stderr)
    owner = regions()
    lines = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    summary = lines[-1]
    records = []
    for line in lines[:-1]:
        case = cases[line['mutation']]
        red = [r.split()[-1] for r in line['red_rows']]
        target = case['rows'][0]
        records.append({'mutation': line['mutation'], 'module': '.veldo/' + case['module'], 'target_rows': case['rows'],
                        **({'declared_falsifier_of': DECLARED[line['mutation']]} if line['mutation'] in DECLARED else {}),
                        'edits': 1 + len(case.get('also', ())), 'baseline': line['baseline'], 'red_rows': red,
                        'target_red': target in red,
                        'target_region_completed': 'ran/' + owner[target] not in red,
                        'diff': 'mutations/%s.diff' % line['mutation']})
    out = {'command': ' '.join(COMMAND), 'summary': dict(summary, driver_seconds=round(elapsed, 1)),
           'all_targets_red_by_assertion': all(r['target_red'] and r['target_region_completed'] for r in records),
           'mutations': records}
    (HERE / 'mutations.json').write_text(json.dumps(out, indent=1) + '\n')
    print('%d mutations, all targets red by assertion: %s, %.1fs' % (len(records), out['all_targets_red_by_assertion'], elapsed))


if __name__ == '__main__':
    main()
