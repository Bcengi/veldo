#!/usr/bin/env python3
"""Drive finding 51 and record what each mutation turned red.

    python3 -B proof/VELDO-0051/mutations.py > proof/VELDO-0051/mutations.json

Runs scripts/check_teeth_mutations.py --finding 51 --jobs 4, which runs suite 66 once unmutated
(the control) and once per mutation on a temporary production copy, and requires each mutation's
named row to go red and every named row to be green in the control. The exact applied edits are
written to proof/VELDO-0051/mutations/<name>.diff. Recorded per mutation: its module, the row it
names, the criterion whose declared falsifier it is (if any), every row it turned red, and whether
any `ran/` row went red (a mutation that reds its row by a raise instead of an assertion would).
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DECLARED = {'events-validator-forgets-run-done': 'AC1', 'projection-skips-committed-event': 'AC2',
            'events-direct-spec-shipped': 'AC3'}


def main():
    spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts' / 'check_teeth_mutations.py')
    teeth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(teeth)
    cases = {c['name']: c for c in teeth.cases() if c['finding'] == 51}
    started = time.monotonic()
    proc = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts' / 'check_teeth_mutations.py'), '--finding', '51',
                           '--jobs', '4', '--diff-dir', str(HERE / 'mutations')], capture_output=True, text=True,
                          timeout=1800, cwd=ROOT)
    seconds = round(time.monotonic() - started, 1)
    lines = [json.loads(line) for line in proc.stdout.splitlines() if line.startswith('{')]
    results = [line for line in lines if 'mutation' in line]
    summary = next((line for line in lines if 'mutations_rejected' in line), None)
    rows = []
    for line in results:
        case = cases[line['mutation']]
        red = [name.replace('VELDO-0051 ', '') for name in line['red_rows']]
        rows.append({'mutation': line['mutation'], 'module': case['module'], 'row': case['rows'][0],
                     'declared_falsifier_of': DECLARED.get(line['mutation']), 'red_rows': red,
                     'target_red': case['rows'][0] in red, 'ran_rows_red': [r for r in red if r.startswith('ran/')],
                     'diff': 'mutations/%s.diff' % line['mutation']})
    per_row = {}
    for row in rows:
        per_row.setdefault(row['row'], []).append(row['mutation'])
    print(json.dumps({'command': 'python3 -B scripts/check_teeth_mutations.py --finding 51 --jobs 4', 'exit': proc.returncode,
                      'seconds': seconds, 'summary': summary, 'control': {'suite': '66_veldo_0051_events.py',
                      'assertions': (summary or {}).get('green_suites', {}).get('66_veldo_0051_events.py')},
                      'every_target_red': all(r['target_red'] for r in rows) and len(rows) == len(cases),
                      'no_ran_row_red': not any(r['ran_rows_red'] for r in rows),
                      'mutations_per_row': per_row, 'mutations': rows}, indent=1))
    return proc.returncode


if __name__ == '__main__':
    sys.exit(main())
