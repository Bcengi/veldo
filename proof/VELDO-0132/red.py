#!/usr/bin/env python3
"""Run the CURRENT suite 65 over the pre-change code and print every VELDO-0132 row.

    python3 -B proof/VELDO-0132/red.py 5a5dfcd > proof/VELDO-0132/red-5a5dfcd.json

This is how each row was recorded red by assertion before the change. At 5a5dfcd there is no
control_workflow, control_workflow_cycle or control_workflow_langgraph module: a workflow could only
be kept with the store's generic upsert_entity (no validation, written in place, no layout kept
apart), and a cycle could only run the production runner, which registers no workflow. The suite's
three production anchors are pointed at prefix/, marked stand-ins that give the names the suite
calls exactly that behaviour. Every other module the suite installs (.veldo/*.py and .veldo/runtime/)
is taken from the commit itself: its bytes are written from `git show` into a temporary tree and the
suite's copy loop is pointed there, so the stand-ins are the only substitution. A row that fails
reports its observation, never a crash: each region reds its rows on a raise, and a `ran/` row says
whether it did.
"""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile

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
    at_commit = sorted(p for p in listed if p.endswith('.py') and p.count('/') == 1 or p.startswith('.veldo/runtime/'))
    present = [name for name in NEW if '.veldo/' + name in at_commit]
    tree_dir = tempfile.TemporaryDirectory(prefix='v132-red-')
    veldo = Path(tree_dir.name) / '.veldo'
    for path in at_commit:
        target = Path(tree_dir.name) / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git('show', '%s:%s' % (commit, path)))
    source = SUITE.read_text()
    for name in NEW:
        text = 'ROOT / ".veldo" / "%s"' % name
        assert source.count(text) == 1, 'anchor moved: ' + text
        source = source.replace(text, '__import__("pathlib").Path(%r)' % str(HERE / 'prefix' / name))
    # The suite's copy loop reads the installed tree from ROOT / '.veldo': point it at the commit's own.
    assert source.count("ROOT / '.veldo'") == 2, 'copy loop moved'
    source = source.replace("ROOT / '.veldo'", '__import__("pathlib").Path(%r)' % str(veldo))
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
    tree_dir.cleanup()
    print(json.dumps({
        'production_at': commit,
        'substituted': {name: 'proof/VELDO-0132/prefix/%s (absent at %s)' % (name, commit) for name in NEW},
        'new_modules_present_at_commit': present,
        'installed_from_commit': len(at_commit),
        'installed_tree': 'git show %s:<path> for each of .veldo/*.py and .veldo/runtime/*' % commit,
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
