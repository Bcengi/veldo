#!/usr/bin/env python3
"""Run the CURRENT suite 65 over the pre-change code and print every VELDO-0132 row.

    python3 -B proof/VELDO-0132/red.py 5a5dfcd > proof/VELDO-0132/red-5a5dfcd.json

This is how each row was recorded red by assertion before the change. At 5a5dfcd there is no
control_workflow, control_workflow_cycle or control_workflow_langgraph module: a workflow could only
be kept with the store's generic upsert_entity (no validation, written in place, no layout kept
apart), and a cycle could only run the production runner, which registers no workflow. The suite's
three production anchors are pointed at prefix/, marked stand-ins that give the names the suite
calls exactly that behaviour. Every other installed module the suite copies (.veldo/*.py and
.veldo/runtime/) is checked byte-identical to the commit's copy and the result reported, so the
stand-ins are the only substitution. A row that fails reports its observation, never a crash: each
region reds its rows on a raise, and a `ran/` row says whether it did.
"""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / 'scripts/suites/65_veldo_0132_workflow.py'
HERE = Path(__file__).resolve().parent
NEW = ('control_workflow.py', 'control_workflow_cycle.py', 'control_workflow_langgraph.py')
_spec = importlib.util.spec_from_file_location('red_git', ROOT / '.veldo' / 'git_process.py')
_git_process = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_git_process)


def git(*args):
    return _git_process.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True).stdout


def main(commit):
    listed = [line.split('\t', 1)[1] for line in git('ls-tree', '-r', commit, '.veldo/').decode().splitlines()]
    at_commit = {p for p in listed if p.endswith('.py') and p.count('/') == 1 or p.startswith('.veldo/runtime/')}
    installed = {'.veldo/' + p.name for p in (ROOT / '.veldo').glob('*.py')}
    installed |= {str(p.relative_to(ROOT)) for p in (ROOT / '.veldo' / 'runtime').rglob('*') if p.is_file()}
    absent = sorted(p for p in installed - at_commit)
    differing = sorted(p for p in installed & at_commit if (ROOT / p).read_bytes() != git('show', '%s:%s' % (commit, p)))
    source = SUITE.read_text()
    for name in NEW:
        text = 'ROOT / ".veldo" / "%s"' % name
        assert source.count(text) == 1, 'anchor moved: ' + text
        source = source.replace(text, '__import__("pathlib").Path(%r)' % str(HERE / 'prefix' / name))
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
        exec(compile(source, str(SUITE), 'exec'), ns)
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0132')]
    observed = ns.get('_V132_OBSERVED') or {}
    cycles = (observed.get('cycles') or {}).get('records') or {}
    print(json.dumps({
        'production_at': commit,
        'substituted': {name: 'proof/VELDO-0132/prefix/%s (absent at %s)' % (name, commit) for name in NEW},
        'absent_at_commit': absent,
        'other_installed_modules_identical_to_commit': absent == ['.veldo/' + n for n in NEW] and not differing,
        'differing': differing,
        'failed': [n for n, ok in mine if not ok], 'passed': [n for n, ok in mine if ok],
        'raised': observed.get('raised'), 'condition_errors': observed.get('condition_errors'),
        'observed': {
            'validation_accepted_by_the_old_write': sorted(
                k for k, v in ((observed.get('validation') or {}).get('results') or {}).items() if 'ok' in v),
            'editors_accepted': sorted(k for k, v in ((observed.get('editors') or {}).get('refused') or {}).items()
                                       if 'ok' in v),
            'canvas': {k: v for k, v in (observed.get('canvas') or {}).items() if k in ('stale', 'overwrite')},
            'edit': (observed.get('edit') or {}).get('records'),
            'cycles': {name: {k: record.get(k) for k in ('state', 'refusal')} for name, record in cycles.items()},
            'authority': observed.get('authority'),
            'observations': observed.get('observations'),
        },
    }, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '5a5dfcd')
