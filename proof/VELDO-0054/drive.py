#!/usr/bin/env python3
"""Record one run of suite 62 as observations.json: every row, the consumer set derived from call
sites, each unit's answer at the build station and the file readers after every change, the
production Gate's answers, the error taxonomy of every refusal seen and the decision metrics.

Run from the repository root: python3 -B proof/VELDO-0054/drive.py
The mutation evidence is scripts/check_teeth_mutations.py --finding 54 (mutations.json here).
"""
import ast
import contextlib
import io
import json
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
shared = ROOT / 'scripts/suites/shared.py'
suite = ROOT / 'scripts/suites/62_veldo_0054_decisions.py'
rows = []
ns = {'__file__': str(shared), '__observe__': lambda name, ok: rows.append([name, bool(ok)])}
tree = ast.parse(shared.read_text(), str(shared))
for node in tree.body:
    if isinstance(node, ast.FunctionDef) and node.name == 'expect':
        node.body = ast.parse('__observe__(name, condition)').body
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
    ns['__suite_file__'] = str(suite)
    before = len(rows)
    started = time.monotonic()
    exec(compile(suite.read_text(), str(suite), 'exec'), ns)
    elapsed = time.monotonic() - started
mine = [r for r in rows[before:] if r[0].startswith('VELDO-0054')]
record = {'suite': suite.name, 'rows': mine, 'passed': sum(ok for _, ok in mine), 'failed': sum(not ok for _, ok in mine),
          'suite_seconds': round(elapsed, 3), 'observed': ns.get('_V54_OBSERVED')}
out = Path(__file__).with_name('observations.json')
out.write_text(json.dumps(record, indent=1, sort_keys=True) + '\n')
print('%s: %d passed, %d failed in %.3fs -> %s' % (suite.name, record['passed'], record['failed'], elapsed, out.name))
sys.exit(1 if record['failed'] else 0)
