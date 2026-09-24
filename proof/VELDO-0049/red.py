#!/usr/bin/env python3
"""Run the CURRENT suite 63 over the pre-change dispatcher and print every VELDO-0049 row.

    python3 -B proof/VELDO-0049/red.py 0083c85

This is how each row was recorded red by assertion before the change. At 0083c85 the dispatcher
writes the spec file's status line itself (ready -> review on a built outcome, review -> shipped
on a landed pass), judges a review by the verdict it is handed, and has no floor authority at all;
the tracker bridge drafts and promotes into any repository. The suite's two production anchors are
pointed at: prefix/dispatch.py (0083c85's dispatch.py byte for byte, followed by a marked stand-in
section that only lets the suite drive it: the Dispatcher ignores `authority`, and the authority
is absent, finding nothing and refusing nothing) and the commit's own tracker_bridge.py. Every
other module the suite installs is checked byte-identical to the commit's copy and reported, so
the stand-in is the only substitution. A row that fails reports its observation, never a crash:
each region reds its rows on a raise, and a `ran/` row says whether it did.
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
SUITE = ROOT / 'scripts/suites/63_veldo_0049_floor.py'
HERE = Path(__file__).resolve().parent


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True).stdout


def main(commit):
    source = SUITE.read_text()
    new_here = {'dispatch.py', 'tracker_bridge.py'}
    listed = [line.split('\t', 1)[1] for line in git('ls-tree', commit, '.veldo/').decode().splitlines()]
    at_commit = {Path(p).name for p in listed if p.endswith('.py')}
    current = {p.name for p in (ROOT / '.veldo').glob('*.py')}
    differing = sorted(name for name in (current & at_commit) - new_here
                       if (ROOT / '.veldo' / name).read_bytes() != git('show', '%s:.veldo/%s' % (commit, name)))
    prefix = (HERE / 'prefix' / 'dispatch.py').read_bytes()
    original = git('show', '%s:.veldo/dispatch.py' % commit)
    rows = []
    with tempfile.TemporaryDirectory(prefix='v49-red-') as directory:
        bridge = Path(directory) / 'tracker_bridge.py'
        bridge.write_bytes(git('show', '%s:.veldo/tracker_bridge.py' % commit))
        anchors = {
            'ROOT / ".veldo" / "dispatch.py"': HERE / 'prefix' / 'dispatch.py',
            'ROOT / ".veldo" / "tracker_bridge.py"': bridge,
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
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0049')]
    observed = ns.get('_V49_OBSERVED') or {}
    print(json.dumps({
        'production_at': commit,
        'substituted': {'dispatch.py': 'proof/VELDO-0049/prefix/dispatch.py',
                        'tracker_bridge.py': '%s:.veldo/tracker_bridge.py' % commit},
        'prefix_begins_with_the_commit_bytes': prefix.startswith(original),
        'other_installed_modules_identical_to_commit': not differing, 'differing': differing,
        'failed': [n for n, ok in mine if not ok], 'passed': [n for n, ok in mine if ok],
        'raised': observed.get('raised'),
        'observed': {k: observed.get(k) for k in ('status_writes', 'build_acceptance', 'independence', 'binding',
                                                   'policy_count', 'builders', 'findings', 'completion', 'projection',
                                                   'tracker', 'status')},
    }, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '0083c85')
