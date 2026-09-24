#!/usr/bin/env python3
"""Run the CURRENT suite 62 over the pre-fix launch path and print every VELDO-0039 row.

    python3 -B proof/VELDO-0039/red.py d95a809

This is how each row was recorded red by assertion before the fix. At the pre-fix commit the only
launch path is VELDO-0052's StationCalls.launch with CallHandle.invoke and VELDO-0036's
InvocationGuard, and there is no dispatch authority at all. The suite drives the runner interface,
so the suite's three production anchors are pointed at: prefix/control_dispatch.py (the absent
authority: every read finds nothing, every observation changes nothing), prefix/control_launch.py
(that d95a809 launch path behind the runner's names) and the commit's own init_scaffold.py. Every
other module the suite installs is checked byte-identical to the commit's copy and reported, so the
stand-ins are the only substitution. A row that fails reports its observation, never a crash: each
region reds its rows on a raise, and a `ran/` row says whether it did.
"""
import ast
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / 'scripts/suites/62_veldo_0039_dispatch.py'
HERE = Path(__file__).resolve().parent


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True).stdout


def main(commit):
    source = SUITE.read_text()
    new_here = {'control_dispatch.py', 'control_launch.py', 'init_scaffold.py'}
    listed = git('ls-tree', '--name-only', commit, '.veldo/').decode().split()
    at_commit = {Path(p).name for p in listed if p.endswith('.py')}
    current = {p.name for p in (ROOT / '.veldo').glob('*.py')}
    differing = sorted(name for name in (current & at_commit) - new_here
                       if (ROOT / '.veldo' / name).read_bytes() != git('show', '%s:.veldo/%s' % (commit, name)))
    rows = []
    with tempfile.TemporaryDirectory(prefix='v39-red-') as directory:
        scaffold = Path(directory) / 'init_scaffold.py'
        scaffold.write_bytes(git('show', '%s:.veldo/init_scaffold.py' % commit))
        anchors = {
            'ROOT / ".veldo" / "control_dispatch.py"': HERE / 'prefix' / 'control_dispatch.py',
            'ROOT / ".veldo" / "control_launch.py"': HERE / 'prefix' / 'control_launch.py',
            'ROOT / ".veldo" / "init_scaffold.py"': scaffold,
        }
        for text, path in anchors.items():
            assert source.count(text) == 1, 'anchor moved: ' + text
            source = source.replace(text, '__import__("pathlib").Path(%r)' % str(path))
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
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0039')]
    observed = ns.get('_V39_OBSERVED') or {}
    print(json.dumps({
        'production_at': commit,
        'substituted': {'control_dispatch.py': 'proof/VELDO-0039/prefix/control_dispatch.py',
                        'control_launch.py': 'proof/VELDO-0039/prefix/control_launch.py',
                        'init_scaffold.py': '%s:.veldo/init_scaffold.py' % commit},
        'other_installed_modules_identical_to_commit': not differing, 'differing': differing,
        'failed': [n for n, ok in mine if not ok], 'passed': [n for n, ok in mine if ok],
        'raised': observed.get('raised'),
        'observed': {k: observed.get(k) for k in ('contract', 'uniqueness', 'launch_results', 'unknown_relaunch',
                                                   'binding', 'terminal', 'authority', 'status')},
    }, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'd95a809')
