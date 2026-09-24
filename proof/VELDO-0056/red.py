#!/usr/bin/env python3
"""Run the CURRENT suite 67 over the pre-change lander and print every VELDO-0056 row.

    python3 -B proof/VELDO-0056/red.py 8995740 > proof/VELDO-0056/red-8995740.json

This is how each row was recorded red by assertion before the change. At 8995740 the lander's
sync_main checks out the trunk in the caller's own checkout, reconcile merges the build ref into
whatever is checked out there, and the gate and the policy run in the caller's tree. The suite's one
production anchor is pointed at 8995740's lander.py byte for byte; every other installed module is
checked byte-identical to that commit's copy and reported, so the lander is the only substitution.
The suite hands the pre-change class exactly the arguments its constructor takes. A row that fails
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
SUITE = ROOT / 'scripts/suites/67_veldo_0056_candidates.py'
_spec = importlib.util.spec_from_file_location('red_git', ROOT / '.veldo' / 'git_process.py')
_git_process = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_git_process)


def git(*args):
    return _git_process.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True).stdout


def main(commit):
    source = SUITE.read_text()
    listed = [line.split('\t', 1)[1] for line in git('ls-tree', commit, '.veldo/').decode().splitlines()]
    at_commit = {Path(p).name for p in listed if p.endswith('.py')}
    current = {p.name for p in (ROOT / '.veldo').glob('*.py')}
    differing = sorted(name for name in (current & at_commit) - {'lander.py'}
                       if (ROOT / '.veldo' / name).read_bytes() != git('show', '%s:.veldo/%s' % (commit, name)))
    rows = []
    with tempfile.TemporaryDirectory(prefix='v56-red-') as directory:
        lander = Path(directory) / 'lander.py'
        lander.write_bytes(git('show', '%s:.veldo/lander.py' % commit))
        anchor = 'ROOT / ".veldo" / "lander.py"'
        assert source.count(anchor) == 1, 'anchor moved: ' + anchor
        source = source.replace(anchor, '__import__("pathlib").Path(%r)' % str(lander))
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
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0056')]
    observed = ns.get('_V56_OBSERVED') or {}
    every = observed.get('every_operation') or {}
    print(json.dumps({
        'production_at': commit,
        'substituted': {'lander.py': '%s:.veldo/lander.py' % commit},
        'other_installed_modules_identical_to_commit': not differing, 'differing': differing,
        'failed': [n for n, ok in mine if not ok], 'passed': [n for n, ok in mine if ok],
        'raised': observed.get('raised'),
        'observed': {
            'rejections': observed.get('rejections'),
            'valid_land': observed.get('valid_land'),
            'detached': observed.get('detached'),
            'failures': observed.get('failures'),
            'every_operation': {'baseline': every.get('baseline'), 'faults': len(every.get('faults') or [])},
            'observations': {k: (observed.get('observations') or {}).get(k) for k in ('events', 'refused')},
        },
    }, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '8995740')
