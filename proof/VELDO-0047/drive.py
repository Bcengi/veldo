#!/usr/bin/env python3
"""Record one run of suite 66 as observations.json: every row, the suite's run time and what each
region observed (placement refusals, the installed layout and modes, the lock holders, the independent
store reads, the refusals by name, the absent and crashed service, the observation log).

Run from the repository root: python3 -B proof/VELDO-0047/drive.py [output]
The mutation evidence is mutations.py (mutations.json here); the red record is red.py.
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
suite = ROOT / 'scripts/suites/66_veldo_0047_authority.py'
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
mine = [r for r in rows[before:] if r[0].startswith('VELDO-0047')]
record = {'suite': suite.name, 'rows': mine, 'passed': sum(ok for _, ok in mine), 'failed': sum(not ok for _, ok in mine),
          'suite_seconds': round(elapsed, 3), 'observed': ns.get('_V47_OBSERVED')}
out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name('observations.json')
out.write_text(json.dumps(record, indent=1, sort_keys=True, default=str) + '\n')
print('%s: %d passed, %d failed in %.3fs -> %s' % (suite.name, record['passed'], record['failed'], elapsed, out))
sys.exit(1 if record['failed'] else 0)
