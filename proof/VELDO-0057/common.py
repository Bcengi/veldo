"""Shared by drive.py and red.py: run suite 70 in this process with every assertion captured, optionally
with production anchors pointed at other files."""
import ast
import contextlib
import io
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / 'scripts/suites/70_veldo_0057_landing.py'
ANCHORS = {'lander.py': 'ROOT / ".veldo" / "lander.py"',
           'control_landing.py': 'ROOT / ".veldo" / "control_landing.py"'}


def run_suite(substitute=None):
    """(rows of VELDO-0057, the suite's observations, seconds)."""
    source = SUITE.read_text()
    for name, path in (substitute or {}).items():
        anchor = ANCHORS[name]
        assert source.count(anchor) == 1, 'anchor moved: ' + anchor
        source = source.replace(anchor, '__import__("pathlib").Path(%r)' % str(path))
    shared = ROOT / 'scripts/suites/shared.py'
    rows = []
    ns = {'__file__': str(shared), '__observe__': lambda name, ok: rows.append([name, bool(ok)])}
    tree = ast.parse(shared.read_text(), str(shared))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        ns['__suite_file__'] = str(SUITE)
        before = len(rows)
        started = time.monotonic()
        exec(compile(source, str(SUITE), 'exec'), ns)
        elapsed = time.monotonic() - started
    return [r for r in rows[before:] if r[0].startswith('VELDO-0057')], ns.get('_V57_OBSERVED') or {}, elapsed
