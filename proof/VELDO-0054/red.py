#!/usr/bin/env python3
"""Run a CURRENT suite (60 or 62) over the production modules of an earlier commit and print its rows.

    python3 -B proof/VELDO-0054/red.py 62 1e1bc00
    python3 -B proof/VELDO-0054/red.py 60 1e1bc00

This is how the rows added for the 2026-09-23 review (A and B) were recorded red before their
fixes: the suite's own production-copy anchors (the ones the mutation driver substitutes) are pointed
at that commit's copies of every module the suite installs by name. No fixture line is substituted.
A row that fails reports its observation, never a crash: each region reds its rows on a raise and a
`ran/` row says whether it did.
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
SUITES = {'60': ('scripts/suites/60_veldo_0052_eligibility.py', 'VELDO-0052', '_V52_OBSERVED'),
          '62': ('scripts/suites/62_veldo_0054_decisions.py', 'VELDO-0054', '_V54_OBSERVED')}


def main(which, commit):
    path, prefix, observed_name = SUITES[which]
    suite = ROOT / path
    source = suite.read_text()
    anchors = {}
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and isinstance(node.right, ast.Constant):
            text = ast.get_source_segment(source, node) or ''
            if text.startswith('ROOT / ".veldo" / "') or text.startswith('ROOT / "bin" / "'):
                anchors[text] = text.split(' / ')[1:]
    rows = []
    with tempfile.TemporaryDirectory(prefix='v54-red-') as directory:
        for text, parts in sorted(anchors.items()):
            relative = '/'.join(p.strip('"') for p in parts)
            target = Path(directory) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.run(['git', '-C', str(ROOT), 'show', '%s:%s' % (commit, relative)],
                                              check=True, capture_output=True).stdout)
            source = source.replace(text, '__import__("pathlib").Path(%r)' % str(target))
        shared = ROOT / 'scripts/suites/shared.py'
        ns = {'__file__': str(shared), '__observe__': lambda name, ok: rows.append([name, bool(ok)])}
        stree = ast.parse(shared.read_text(), str(shared))
        for node in stree.body:
            if isinstance(node, ast.FunctionDef) and node.name == 'expect':
                node.body = ast.parse('__observe__(name, condition)').body
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(ast.fix_missing_locations(stree), str(shared), 'exec'), ns)
            ns['__suite_file__'] = str(suite)
            before = len(rows)
            exec(compile(source, str(suite), 'exec'), ns)
    mine = [r for r in rows[before:] if r[0].startswith(prefix)]
    observed = ns.get(observed_name) or {}
    keep = ('status_reader', 'malformed', 'malformed_subject', 'malformed_blocks', 'invalid_order', 'status_stop', 'deep_blocks', 'store_refusal', 'settlement_order', 'minor_shapes', 'settlement_text', 'stops', 'unexpected_messages', 'verifier_input', 'rsa_signature_chars', 'raised')
    print(json.dumps({'suite': suite.name, 'production_at': commit,
                      'substituted_modules': sorted('/'.join(p.strip('"') for p in v) for v in anchors.values()),
                      'failed': [n for n, ok in mine if not ok], 'passed': sum(ok for _, ok in mine),
                      'observed': {k: v for k, v in observed.items() if k in keep}}, indent=1, sort_keys=True, default=str))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else 'HEAD')
