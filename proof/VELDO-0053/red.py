#!/usr/bin/env python3
"""Run the CURRENT suite 60_veldo_0053 over every .veldo module of an earlier commit and print every row.

    python3 -B proof/VELDO-0053/red.py 60d5018     (the first review's rows)
    python3 -B proof/VELDO-0053/red.py 8798a78     (the second review's rows)
    python3 -B proof/VELDO-0053/red.py e299772     (the third review's rows)
    python3 -B proof/VELDO-0053/red.py 4c29526     (the fourth review's rows)
    python3 -B proof/VELDO-0053/red.py e12aab1     (the fifth review's rows)
    python3 -B proof/VELDO-0053/red.py 8a3c709     (the sixth review's rows)

This is how the rows added for the 2026-09-23 review were recorded red before their fixes. The suite's
ROOT is pointed at an export of that commit's .veldo directory, so every module the suite installs
(its production-copy anchors and the rest of the engine it copies beside them) is that commit's. One
fixture line reaches an interface 60d5018 did not have: the validator snapshot's one structural
validator instance (`.arch`), where 60d5018 re-executed arch.py at every call. For such a commit that
line is replaced by one that pins a single instance on 60d5018's validate_checks, so the injected writer
runs at all, and it is printed as the one substitution made (null when none was needed). Every other
line runs as committed. A row that fails reports its observation, never a crash: each region reds its
rows on a raise and a `ran/` row says whether it did.
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
SUITE = ROOT / 'scripts/suites/60_veldo_0053_architecture.py'
FIXTURE_LINE = '                validator = racing._architecture_validator().arch\n'
FIXTURE_THEN = ('                _vc = racing._architecture_validator()\n'
                '                validator = _vc._arch_module()\n'
                '                _vc._arch_module = lambda: validator\n')


def main(commit):
    source = SUITE.read_text()
    rows = []
    with tempfile.TemporaryDirectory(prefix='v53-red-') as directory:
        archive = subprocess.run(['git', '-C', str(ROOT), 'archive', commit, '.veldo'], check=True,
                                 capture_output=True).stdout
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(directory, filter='data')
        then = (Path(directory) / '.veldo' / 'control_eligibility.py').read_text()
        substituted = 'class ValidatorSnapshot' not in then
        if substituted:
            assert source.count(FIXTURE_LINE) == 1, 'fixture line moved'
            source = source.replace(FIXTURE_LINE, FIXTURE_THEN)
        shared = ROOT / 'scripts/suites/shared.py'
        ns = {'__file__': str(shared), '__observe__': lambda name, ok: rows.append([name, bool(ok)])}
        stree = ast.parse(shared.read_text(), str(shared))
        for node in stree.body:
            if isinstance(node, ast.FunctionDef) and node.name == 'expect':
                node.body = ast.parse('__observe__(name, condition)').body
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(ast.fix_missing_locations(stree), str(shared), 'exec'), ns)
            ns['ROOT'] = Path(directory)
            ns['__suite_file__'] = str(SUITE)
            before = len(rows)
            exec(compile(source, str(SUITE), 'exec'), ns)
    mine = [r for r in rows[before:] if r[0].startswith('VELDO-0053')]
    observed = ns.get('_V53_OBSERVED') or {}
    print(json.dumps({'production_at': commit, 'modules': '.veldo/*.py of ' + commit,
                      'fixture_substitution': [FIXTURE_LINE, FIXTURE_THEN] if substituted else None,
                      'failed': [n for n, ok in mine if not ok], 'passed': sum(ok for _, ok in mine),
                      'observed': {k: observed.get(k) for k in ('store_only', 'public_seam', 'identity_is_what_ran',
                                                                'validated_is_digested', 'snapshot_in_memory', 'not_text', 'snapshot_source', 'snapshot_by_name',
                                                                'identity_covers_what_ran', 'snapshot_held_names',
                                                                'snapshot_module_files', 'identity_keyed_by_module',
                                                                'snapshot_file_bounded',
                                                                'raised')}},
                     indent=1, default=str))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'HEAD')
