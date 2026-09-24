#!/usr/bin/env python3
"""Run suite 65 once, unmutated, and record what it observed.

    python3 -B proof/VELDO-0132/drive.py > proof/VELDO-0132/observations.json

The suite runs in this process exactly as scripts/selftest.py runs it (shared.py's namespace, its
expect replaced by a recorder). Recorded: every VELDO-0132 row, the suite's own time, and the
observations each row judged, trimmed to identities, codes and states.
"""
import ast
import contextlib
import io
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / 'scripts/suites/65_veldo_0132_workflow.py'


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
    observed = ns.get('_V132_OBSERVED') or {}
    records = (observed.get('cycles') or {}).get('records') or {}
    edit = observed.get('edit') or {}
    print(json.dumps({
        'rows': [r for r in rows[before:] if r[0].startswith('VELDO-0132')],
        'suite_seconds': round(ns.get('_V132_SECONDS') or 0, 2),
        'cycle_seconds': (observed.get('cycles') or {}).get('seconds'),
        'raised': observed.get('raised'), 'condition_errors': observed.get('condition_errors'),
        'validation': {k: v.get('refused') for k, v in ((observed.get('validation') or {}).get('results') or {}).items()},
        'editors': {k: v.get('refused') for k, v in ((observed.get('editors') or {}).get('refused') or {}).items()},
        'canvas': {k: v for k, v in (observed.get('canvas') or {}).items() if k in ('stale', 'overwrite')},
        'edit_without_execution': {'launches': (edit.get('result') or {}).get('launches'),
                                   'network': (edit.get('result') or {}).get('network'),
                                   'signed': (edit.get('result') or {}).get('signed'),
                                   'journal_records': edit.get('records'), 'kinds_written': edit.get('kinds')},
        'cycles': {name: {'binding': (r.get('binding') or {}).get('id', '') + ' v%s' % (r.get('binding') or {}).get('version'),
                          'state': r.get('state'), 'refusal': r.get('refusal'), 'steps': r.get('steps'),
                          'trace': r.get('trace'), 'waiting': r.get('waiting')} for name, r in records.items()},
        'authorization': {k: v for k, v in (observed.get('authorization') or {}).items() if k in ('ran', 'named', 'revisit')},
        'authority': observed.get('authority'),
        'observations': observed.get('observations'),
    }, indent=1, default=str))


if __name__ == '__main__':
    main()
