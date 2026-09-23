#!/usr/bin/env python3
"""Run the CURRENT suite 60 over the production modules of an earlier commit and print every row.

    python3 -B proof/VELDO-0052/red.py 0ea33e3

This is how the rows added for the 2026-09-23 review were recorded red before their fixes: the
suite's own production-copy anchors (the ones the mutation driver substitutes) are pointed at that
commit's copies of every module the suite installs by name. One fixture line constructs an interface
0ea33e3 did not have (StationCalls with the runner's account and clock); for a commit that predates
it, the line is replaced by that commit's constructor so the suite can run at all, and is printed as
the one substitution made (null when none was needed). Every other line runs as committed. A row that
fails reports its observation, never a crash: each region reds its rows on a raise and a `ran/` row
says whether it did.
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
SUITE = ROOT / 'scripts/suites/60_veldo_0052_eligibility.py'
FIXTURE_LINE = "calls = EL.StationCalls(gate, guards, account='acct-floor', clock=tick)"
FIXTURE_THEN = 'calls = EL.StationCalls(gate, guards)'


def main(commit):
    source = SUITE.read_text()
    anchors = {}
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and isinstance(node.right, ast.Constant):
            text = ast.get_source_segment(source, node)
            if text and text.startswith('ROOT / ".veldo" / "') or (text or '').startswith('ROOT / "bin" / "'):
                anchors[text] = text.split(' / ')[1:]
    rows = []
    with tempfile.TemporaryDirectory(prefix='v52-red-') as directory:
        for text, parts in sorted(anchors.items()):
            relative = '/'.join(p.strip('"') for p in parts)
            target = Path(directory) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.run(['git', '-C', str(ROOT), 'show', '%s:%s' % (commit, relative)],
                                              check=True, capture_output=True).stdout)
            source = source.replace(text, '__import__("pathlib").Path(%r)' % str(target))
        assert source.count(FIXTURE_LINE) == 1, 'fixture line moved'
        # Only a commit whose StationCalls predates the runner's account and clock needs the one
        # substitution; a later commit runs the fixture exactly as committed.
        then = subprocess.run(['git', '-C', str(ROOT), 'show', '%s:.veldo/control_eligibility.py' % commit],
                              check=True, capture_output=True, text=True).stdout
        substituted = 'account=None' not in then
        if substituted:
            source = source.replace(FIXTURE_LINE, FIXTURE_THEN)
        shared = ROOT / 'scripts/suites/shared.py'
        ns = {'__file__': str(shared), '__observe__': lambda name, ok: rows.append([name, bool(ok)])}
        stree = ast.parse(shared.read_text(), str(shared))
        for node in stree.body:
            if isinstance(node, ast.FunctionDef) and node.name == 'expect':
                node.body = ast.parse('__observe__(name, condition)').body
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(ast.fix_missing_locations(stree), str(shared), 'exec'), ns)
            ns['__suite_file__'] = str(SUITE)
            before = len(rows)
            exec(compile(source, str(SUITE), 'exec'), ns)
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0052')]
    print(json.dumps({'production_at': commit, 'substituted_modules': sorted('/'.join(p.strip('"') for p in v) for v in anchors.values()),
                      'fixture_substitution': [FIXTURE_LINE, FIXTURE_THEN] if substituted else None,
                      'failed': [n for n, ok in mine if not ok], 'passed': sum(ok for _, ok in mine),
                      'observed': {k: v for k, v in (ns.get('_V52_OBSERVED') or {}).items()
                                   if k in ('executor', 'enrollment_git_error', 'status_reader', 'work_loop',
                                            'landed_offers', 'production_entries', 'raised', 'slot_retirement',
                                            'host_trust', 'provider_refusal')}}, indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'HEAD')
