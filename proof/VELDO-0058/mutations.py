#!/usr/bin/env python3
"""Drive finding 58 and record mutations.json: for each registered mutation, the row it names, the rows
it turned red, whether the named row went red, and whether that row's own region ran to its end (its
`ran/` row stayed green), so a red row is a failed assertion, never a raise. Then the unmutated
controls: a byte-identical copy of each mutated module (verify.sh, control_verification.py, lander.py)
handed to the suite through the very same substitution the mutants use, each of which must leave every
row green.

Run from the repository root: python3 -B proof/VELDO-0058/mutations.py
"""
import ast
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = ROOT / 'scripts/suites/69_veldo_0058_gate_output.py'
DECLARED = {'gate-output-reconcile-writes-candidate': 'AC1', 'gate-output-acceptance-skips-tree-equality': 'AC2',
            'gate-output-candidate-policy-launched': 'AC3'}
COMMAND = [sys.executable, '-B', 'scripts/check_teeth_mutations.py', '--finding', '58', '--jobs', '4',
           '--diff-dir', 'proof/VELDO-0058/mutations']


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
    cases = {c['name']: c for c in teeth.cases() if c['finding'] == 58}
    started = time.monotonic()
    proc = subprocess.run(COMMAND, cwd=ROOT, capture_output=True, text=True, timeout=3600)
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
        records.append({'mutation': line['mutation'], 'module': case.get('dir', '.veldo') + '/' + case['module'],
                        'target_rows': case['rows'],
                        **({'declared_falsifier_of': DECLARED[line['mutation']]} if line['mutation'] in DECLARED else {}),
                        'edits': 1 + len(case.get('also', ())), 'baseline': line['baseline'], 'red_rows': red,
                        'target_red': target in red,
                        'target_region_completed': 'ran/' + owner[target] not in red,
                        'diff': 'mutations/%s.diff' % line['mutation']})
    per_row = {}
    for record in records:
        per_row.setdefault(record['target_rows'][0], []).append(record['mutation'])
    controls = []
    seen = set()
    with tempfile.TemporaryDirectory(prefix='v58-noop-') as directory:
        for case in cases.values():
            module = case.get('dir', '.veldo') + '/' + case['module']
            if module in seen:
                continue
            seen.add(module)
            made = teeth.materialize(case, 'noop', Path(directory) / case['name'])
            control_started = time.monotonic()
            control = subprocess.run([sys.executable, '-B', 'scripts/check_teeth_mutations.py', '--finding', '58',
                                      '--worker', case['name'], '--mutant', str(made['mutant'])],
                                     cwd=ROOT, capture_output=True, text=True, timeout=600)
            ran = json.loads(control.stdout) if control.returncode == 0 else {'failed_rows': ['worker failed'], 'row_names': []}
            controls.append({'module': module, 'identical_bytes': made['old_digest'] == made['new_digest'],
                             'rows': len([n for n in ran.get('row_names', []) if n.startswith('VELDO-0058')]),
                             'failed_rows': ran.get('failed_rows'),
                             'seconds': round(time.monotonic() - control_started, 1)})
    out = {'command': ' '.join(['python3'] + COMMAND[1:]), 'summary': dict(summary, driver_seconds=round(elapsed, 1)),
           'all_targets_red_by_assertion': all(r['target_red'] and r['target_region_completed'] for r in records),
           'mutations_per_row': per_row,
           'every_row_has_two_or_more': all(len(v) >= 2 for v in per_row.values()),
           'unmutated_controls': controls, 'mutations': records}
    (HERE / 'mutations.json').write_text(json.dumps(out, indent=1) + '\n')
    print('%d mutations, all targets red by assertion: %s, controls green: %s, %.1fs' % (
        len(records), out['all_targets_red_by_assertion'],
        all(c['identical_bytes'] and not c['failed_rows'] for c in controls), elapsed))


if __name__ == '__main__':
    main()
