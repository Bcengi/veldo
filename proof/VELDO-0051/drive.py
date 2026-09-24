#!/usr/bin/env python3
"""Run suite 66 once, unmutated, and record what it observed.

    python3 -B proof/VELDO-0051/drive.py > proof/VELDO-0051/observations.json

The suite runs in this process exactly as scripts/selftest.py runs it (shared.py's namespace, its
expect replaced by a recorder). Recorded: every VELDO-0051 row, the suite's own time, and the
observations each row judged.
"""
import ast
import contextlib
import io
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / 'scripts/suites/66_veldo_0051_events.py'


def main():
    rows = []
    shared = ROOT / 'scripts/suites/shared.py'
    ns = {'__file__': str(shared), '__observe__': lambda name, ok: rows.append([name, bool(ok)])}
    tree = ast.parse(shared.read_text(), str(shared))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        ns['__suite_file__'] = str(SUITE)
        before = len(rows)
        exec(compile(SUITE.read_text(), str(SUITE), 'exec'), ns)
    observed = ns.get('_V51_OBSERVED') or {}
    print(json.dumps({
        'rows': [r for r in rows[before:] if r[0].startswith('VELDO-0051')],
        'suite_seconds': round(ns.get('_V51_SECONDS') or 0, 2),
        'observed': observed,
    }, indent=1, default=str))


if __name__ == '__main__':
    main()
