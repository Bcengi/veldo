#!/usr/bin/env python3
"""Run the CURRENT suite 63 over the pre-change launch path and print every VELDO-0040 row.

    python3 -B proof/VELDO-0040/red.py f5aebae

This is how each row was recorded red by assertion before the change. At f5aebae the receiver
(VELDO-0039's control_launch.py) spawns every local worker directly in its own session, stops it at
the deadline by killing that session's process group, reaps it by reading its output to its end,
retires its slot on a canned observation and has no worker profile, containment group or stop
request. The suite's three production anchors are pointed at: f5aebae's own control_launch.py and
init_scaffold.py, and prefix/control_containment.py (the module that does not exist there: it refuses
nothing and states nothing). Every other module the suite installs is checked byte-identical to the
commit's copy and reported, so the stand-in is the only substitution. A row that fails reports its
observation, never a crash: each region reds its rows on a raise, and a `ran/` row says whether it did.
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
SUITE = ROOT / 'scripts/suites/63_veldo_0040_containment.py'
HERE = Path(__file__).resolve().parent


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True).stdout


def main(commit):
    source = SUITE.read_text()
    substituted = {'control_launch.py', 'init_scaffold.py', 'control_containment.py'}
    listed = [line.split('\t', 1)[1] for line in git('ls-tree', commit, '.veldo/').decode().splitlines()]
    at_commit = {Path(p).name for p in listed if p.endswith('.py')}
    current = {p.name for p in (ROOT / '.veldo').glob('*.py')}
    differing = sorted(name for name in (current & at_commit) - substituted
                       if (ROOT / '.veldo' / name).read_bytes() != git('show', '%s:.veldo/%s' % (commit, name)))
    rows = []
    with tempfile.TemporaryDirectory(prefix='v40-red-') as directory:
        anchors = {'ROOT / ".veldo" / "control_containment.py"': HERE / 'prefix' / 'control_containment.py'}
        for name in ('control_launch.py', 'init_scaffold.py'):
            path = Path(directory) / name
            path.write_bytes(git('show', '%s:.veldo/%s' % (commit, name)))
            anchors['ROOT / ".veldo" / "%s"' % name] = path
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
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0040')]
    observed = ns.get('_V40_OBSERVED') or {}
    print(json.dumps({
        'production_at': commit,
        'substituted': {'control_launch.py': '%s:.veldo/control_launch.py' % commit,
                        'init_scaffold.py': '%s:.veldo/init_scaffold.py' % commit,
                        'control_containment.py': 'proof/VELDO-0040/prefix/control_containment.py'},
        'other_installed_modules_identical_to_commit': not differing, 'differing': differing,
        'failed': [n for n, ok in mine if not ok], 'passed': [n for n, ok in mine if ok],
        'raised': observed.get('raised'),
        'observed': {k: observed.get(k) for k in ('group', 'ordinary_exit', 'unqualified', 'required_settings',
                                                   'exit_notified', 'caps', 'runtime_cap', 'cooperative', 'escalation',
                                                   'retire_after_empty', 'observations')},
    }, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'f5aebae')
