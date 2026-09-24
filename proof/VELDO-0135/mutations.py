#!/usr/bin/env python3
"""Drive finding 135 and record mutations.json: for each registered mutation, the row it names, the
rows it turned red, whether the named row went red, and whether that row's own region ran to its end
(its `ran/` row stayed green), so a red row is a failed assertion, never a raise. Then the unmutated
control: each substituted module copied byte for byte through the same anchor substitution, and the
suite required green with every row present.

Run from the repository root: python3 -B proof/VELDO-0135/mutations.py
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
SUITE = ROOT / 'scripts/suites/67_veldo_0135_offers.py'
DECLARED = {'offers-status-line-read': 'AC1', 'offers-handoff-claimable': 'AC2',
            'offers-build-again-after-acceptance': 'AC3'}
COMMAND = [sys.executable, '-B', 'scripts/check_teeth_mutations.py', '--finding', '135', '--jobs', '4',
           '--diff-dir', 'proof/VELDO-0135/mutations']


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
    cases = {c['name']: c for c in teeth.cases() if c['finding'] == 135}
    started = time.monotonic()
    proc = subprocess.run(COMMAND, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    elapsed = time.monotonic() - started
    if proc.returncode:
        sys.exit(proc.stderr)
    owner = regions()
    lines = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
    records = []
    for line in lines[:-1]:
        case = cases[line['mutation']]
        red = [r.split()[-1] for r in line['red_rows']]
        target = case['rows'][0]
        records.append({'mutation': line['mutation'], 'module': '.veldo/' + case['module'], 'target_rows': case['rows'],
                        **({'declared_falsifier_of': DECLARED[line['mutation']]} if line['mutation'] in DECLARED else {}),
                        'baseline': line['baseline'], 'red_rows': red, 'target_red': target in red,
                        'target_region_completed': 'ran/' + owner[target] not in red,
                        'diff': 'mutations/%s.diff' % line['mutation']})
    controls = []
    with tempfile.TemporaryDirectory(prefix='v135-noop-') as directory:
        for module in ('frontier.py', 'work.py'):
            case = next(c for c in cases.values() if c['module'] == module)
            made = teeth.materialize(case, 'noop', Path(directory) / module.replace('.', '-'))
            run = subprocess.run([sys.executable, '-B', 'scripts/check_teeth_mutations.py', '--finding', '135',
                                  '--worker', case['name'], '--mutant', str(made['mutant'])],
                                 cwd=ROOT, capture_output=True, text=True, timeout=600)
            observed = json.loads(run.stdout) if run.returncode == 0 else {}
            controls.append({'module': '.veldo/' + module, 'byte_identical': made['old_digest'] == made['new_digest'],
                             'assertions': observed.get('count'), 'failed_rows': observed.get('failed_rows')})
    per_row = {}
    for r in records:
        per_row.setdefault(r['target_rows'][0], []).append(r['mutation'])
    out = {'command': ' '.join(COMMAND[1:]), 'summary': dict(lines[-1], driver_seconds=round(elapsed, 1)),
           'all_targets_red_by_assertion': all(r['target_red'] and r['target_region_completed'] for r in records),
           'mutations_per_row': per_row, 'unmutated_controls': controls,
           'controls_green': all(c['byte_identical'] and c['failed_rows'] == [] for c in controls),
           'mutations': records}
    (HERE / 'mutations.json').write_text(json.dumps(out, indent=1) + '\n')
    print('%d mutations, all targets red by assertion: %s, controls green: %s, %.1fs' % (
        len(records), out['all_targets_red_by_assertion'], out['controls_green'], elapsed))


if __name__ == '__main__':
    main()
