#!/usr/bin/env python3
"""Run the CURRENT suite 62 over an earlier commit's production code and print every row.

    python3 -B proof/VELDO-0045/red.py b21cab1

This is how every row was recorded red before VELDO-0045 was built. The suite's production-copy
anchors (the ones the mutation driver substitutes: control_runtime.py, authorization.py and
init_scaffold.py) are pointed at that commit's copies, a module the commit does not have is pointed at
a path that does not exist, and the canonical engine templates the suite installs from (ROOT /
'engine') are that commit's engine tree, exported with git archive. Every other line runs as committed.
A row that fails reports its observation, never a crash: each region reds its rows on a raise and a
`ran/` row says whether it did, so a red row with its `ran/` row green is red by its assertion.
"""
import ast
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / 'scripts/suites/62_veldo_0045_runtime.py'
ENGINE = "ROOT / 'engine'"


def show(commit, relative):
    proc = subprocess.run(['git', '-C', str(ROOT), 'show', '%s:%s' % (commit, relative)], capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def main(commit):
    source = SUITE.read_text()
    anchors = {}
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and isinstance(node.right, ast.Constant):
            text = ast.get_source_segment(source, node)
            if text and text.startswith('ROOT / ".veldo" / "'):
                anchors[text] = '.veldo/' + node.right.value
    rows, substituted = [], {}
    with tempfile.TemporaryDirectory(prefix='v45-red-') as directory:
        top = Path(directory)
        for text, relative in sorted(anchors.items()):
            target = top / 'production' / relative
            data = show(commit, relative)
            if data is not None:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            substituted[relative] = 'present' if data is not None else 'absent at ' + commit
            source = source.replace(text, '__import__("pathlib").Path(%r)' % str(target))
        archive = subprocess.run(['git', '-C', str(ROOT), 'archive', commit, 'engine'], capture_output=True, check=True).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(top / 'tree', filter='data')
        assert source.count(ENGINE) >= 2, 'the engine template anchor moved'
        source = source.replace(ENGINE, '__import__("pathlib").Path(%r)' % str(top / 'tree' / 'engine'))
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
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0045')]
    observed = ns.get('_V45_OBSERVED') or {}
    print(json.dumps({'production_at': commit, 'engine_templates_at': commit, 'substituted_modules': substituted,
                      'failed': [n for n, ok in mine if not ok], 'passed': [n for n, ok in mine if ok],
                      'raised': observed.get('raised'),
                      'observed': {k: observed.get(k) for k in ('records', 'workload', 'altered_hash', 'altered_wheel',
                                                               'omitted_dependency', 'observations', 'omitted_asset')},
                      'journey': {k: (observed.get('journey') or {}).get(k) for k in ('exit', 'trace_exit', 'outcome',
                                                                                     'reached_installed', 'declared')},
                      'enforcement': {k: (observed.get('enforcement') or {}).get(k) for k in ('exit', 'passed', 'derived')}},
                     indent=1, default=str).replace(str(Path.home()), '<account home>'))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'HEAD')
