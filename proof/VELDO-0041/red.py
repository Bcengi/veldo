#!/usr/bin/env python3
"""Run the CURRENT suite 67 over the pre-change launch path and print every VELDO-0041 row.

    python3 -B proof/VELDO-0041/red.py e231721

This is how each row was recorded red by assertion before the change. At e231721 the trusted wrapper
starts no heartbeat and the receiver watches none (a profile that declares one is refused as naming an
unknown setting), the stop's graces are timed and recorded on the wall clock only, and the runner's
`_retire` observes the group only on its first attempt, holds no outcome or clone obligation and keeps
no pending list. The suite's production anchors are pointed at e231721's own control_launch.py,
control_containment.py, control_reservations.py and init_scaffold.py, and at prefix/control_heartbeat.py
and prefix/control_retirement.py (the modules that do not exist there, and are empty). Every other
module the suite installs is compared with the commit's copy and each one that differs is named: those
are the modules other specifications landed on main since (VELDO-0042's clones among them, which the
clone row provisions with). A row that fails reports its observation, never a crash: each region reds
its rows on a raise, and a `ran/` row says whether it did.
"""
import ast
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / 'scripts/suites/67_veldo_0041_heartbeat.py'
HERE = Path(__file__).resolve().parent
AT_COMMIT = ('control_launch.py', 'control_containment.py', 'control_reservations.py', 'init_scaffold.py')
STAND_INS = ('control_heartbeat.py', 'control_retirement.py')


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_git_process = _load('red_git_process', ROOT / '.veldo' / 'git_process.py')


def git(repository, *args):
    return _git_process.run(['git', '-C', str(repository), *args], check=True, capture_output=True).stdout


def main(commit, repository):
    source = SUITE.read_text()
    listed = [line.split('\t', 1)[1] for line in git(repository, 'ls-tree', commit, '.veldo/').decode().splitlines()]
    at_commit = {Path(p).name for p in listed if p.endswith('.py')}
    current = {p.name for p in (ROOT / '.veldo').glob('*.py')}
    substituted = set(AT_COMMIT) | set(STAND_INS)
    differing = sorted(name for name in (current & at_commit) - substituted
                       if (ROOT / '.veldo' / name).read_bytes() != git(repository, 'show', '%s:.veldo/%s' % (commit, name)))
    absent_at_commit = sorted(current - at_commit - substituted)
    rows = []
    with tempfile.TemporaryDirectory(prefix='v41-red-') as directory:
        anchors = {'ROOT / ".veldo" / "%s"' % name: HERE / 'prefix' / name for name in STAND_INS}
        for name in AT_COMMIT:
            path = Path(directory) / name
            path.write_bytes(git(repository, 'show', '%s:.veldo/%s' % (commit, name)))
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
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0041')]
    observed = ns.get('_V41_OBSERVED') or {}
    print(json.dumps({
        'production_at': commit,
        'substituted': dict({name: '%s:.veldo/%s' % (commit, name) for name in AT_COMMIT},
                            **{name: 'proof/VELDO-0041/prefix/' + name for name in STAND_INS}),
        'installed_from_current_tree': {'differing_from_commit': differing, 'absent_at_commit': absent_at_commit},
        'failed': [n for n, ok in mine if not ok], 'passed': [n for n, ok in mine if ok],
        'raised': observed.get('raised'),
        'observed': {k: v for k, v in observed.items() if k != 'raised'},
    }, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'e231721', Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT)
