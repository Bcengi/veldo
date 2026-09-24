#!/usr/bin/env python3
"""Run the CURRENT suite 67 over a pre-change frontier, work loop and dispatcher and print every
VELDO-0135 row.

    python3 -B proof/VELDO-0135/red.py e5b4dad

The suite's three production anchors are pointed at the commit's own frontier.py, work.py and
dispatch.py, byte for byte, with no stand-in. Every other module the suite installs is checked
byte-identical to the commit's copy and reported, so those three files are the only substitution. A failing row reports its
observation, never a crash: each region reds its rows on a raise, and a `ran/` row says whether it
did. Writes red-<commit>.json beside this file.
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
SUITE = ROOT / 'scripts/suites/67_veldo_0135_offers.py'
HERE = Path(__file__).resolve().parent
SUBSTITUTED = ('frontier.py', 'work.py', 'dispatch.py')


def git(*args):
    return subprocess.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True).stdout


def main(commit):
    source = SUITE.read_text()
    listed = [line.split('\t', 1)[1] for line in git('ls-tree', commit, '.veldo/').decode().splitlines()]
    at_commit = {Path(p).name for p in listed if p.endswith('.py')}
    current = {p.name for p in (ROOT / '.veldo').glob('*.py')}
    differing = sorted(name for name in (current & at_commit) - set(SUBSTITUTED)
                       if (ROOT / '.veldo' / name).read_bytes() != git('show', '%s:.veldo/%s' % (commit, name)))
    rows = []
    with tempfile.TemporaryDirectory(prefix='v135-red-') as directory:
        for name in SUBSTITUTED:
            path = Path(directory) / name
            path.write_bytes(git('show', '%s:.veldo/%s' % (commit, name)))
            anchor = 'ROOT / ".veldo" / "%s"' % name
            assert source.count(anchor) == 1, 'anchor moved: ' + anchor
            source = source.replace(anchor, '__import__("pathlib").Path(%r)' % str(path))
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
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0135')]
    observed = ns.get('_V135_OBSERVED') or {}
    record = {
        'production_at': commit,
        'substituted': {name: '%s:.veldo/%s' % (commit, name) for name in SUBSTITUTED},
        'other_installed_modules_identical_to_commit': not differing, 'differing': differing,
        'failed': [n for n, ok in mine if not ok], 'passed': [n for n, ok in mine if ok],
        'raised': observed.get('raised'),
        'observed': {k: observed.get(k) for k in ('states', 'offers', 'no_reclaim', 'recheck', 'finding_path', 'journey', 'plain')},
    }
    (HERE / ('red-%s.json' % commit)).write_text(json.dumps(record, indent=1, default=str) + '\n')
    print(json.dumps({k: record[k] for k in ('failed', 'passed', 'raised', 'differing')}, indent=1))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'e5b4dad')
