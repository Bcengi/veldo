#!/usr/bin/env python3
"""Drive every finding-65 mutation and record what each one turned red, and why.

Uses the registry and file materializer of scripts/check_teeth_mutations.py unchanged. Each run
is a fresh interpreter executing the shared preamble and the VELDO-0065 suite, with the suite's
production-copy anchor pointed at the baseline source, an unmutated (no-op) copy or the mutant.
Rows and the suite's own failure detail lines are retained, with source digests and the wall time
of every run. Writes proof/VELDO-0065/mutations.json and one exact applied diff per mutation.

    python3 -B proof/VELDO-0065/drive.py
"""
import ast
import contextlib
import difflib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = '62_veldo_0065_presentations.py'
MODULE = 'control_channel_presentation.py'


def _driver():
    spec = importlib.util.spec_from_file_location('ctm', ROOT / 'scripts/check_teeth_mutations.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def one(path):
    shared = ROOT / 'scripts/suites/shared.py'
    rows = []
    ns = {'__file__': str(shared),
          '__observe__': lambda name, condition: rows.append([name.split(':', 1)[0], bool(condition)])}
    tree = ast.parse(shared.read_text(), str(shared))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        source = (ROOT / 'scripts/suites' / SUITE).read_text()
        if path:
            anchor = 'ROOT / ".veldo" / "' + MODULE + '"'
            if source.count(anchor) != 1:
                raise RuntimeError('suite production-copy anchor moved')
            source = source.replace(anchor, '__import__("pathlib").Path(' + repr(path) + ')')
        exec(compile(source, SUITE, 'exec'), ns)
    mine = [r for r in rows if r[0].startswith('VELDO-0065 ')]
    details = [line.strip() for line in out.getvalue().split('\n') if 'VELDO-0065' in line and 'detail:' in line]
    return {'rows': mine, 'failed_rows': [r[0] for r in mine if not r[1]], 'details': details,
            'preamble_rows': len(rows) - len(mine)}


def run(path=None):
    started = time.monotonic()
    command = [sys.executable, '-B', __file__, '--one', json.dumps(str(path) if path else '')]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if proc.returncode:
        raise RuntimeError('run did not complete its assertions: ' + proc.stderr[-2000:])
    return dict(json.loads(proc.stdout), seconds=round(time.monotonic() - started, 3))


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--one':
        print(json.dumps(one(json.loads(sys.argv[2]) or None)))
        return
    ctm = _driver()
    cases = [c for c in ctm.cases() if c['finding'] == 65]
    report = {'schema': 'veldo.proof-mutations/v1', 'spec_id': 'VELDO-0065', 'suite': 'scripts/suites/' + SUITE,
              'registry': 'scripts/check_teeth_mutations.py --finding 65', 'baseline': run(), 'noop': None, 'mutants': []}
    with tempfile.TemporaryDirectory(prefix='v65-drive-') as directory:
        noop = ctm.materialize(cases[0], 'noop', Path(directory) / 'noop')
        report['noop'] = dict(run(noop['mutant']), source_sha256=noop['old_digest'], copy_sha256=noop['new_digest'])
        for case in cases:
            prepared = ctm.materialize(case, 'mutant', Path(directory) / case['name'])
            source = prepared['source'].read_text()
            (HERE / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                source.splitlines(keepends=True), source.replace(case['old'], case['new']).splitlines(keepends=True),
                n=0, fromfile='a/.veldo/' + MODULE, tofile='b/.veldo/' + MODULE)))
            observed = run(prepared['mutant'])
            report['mutants'].append(dict(name=case['name'], module='.veldo/' + MODULE, named_rows=case['rows'],
                                          diff='proof/VELDO-0065/%s.diff' % case['name'],
                                          source_sha256=prepared['old_digest'], mutant_sha256=prepared['new_digest'],
                                          named_row_red=all('VELDO-0065 ' + r in observed['failed_rows'] for r in case['rows']),
                                          **observed))
    report['all_named_rows_red'] = all(m['named_row_red'] for m in report['mutants'])
    report['controls_green'] = not report['baseline']['failed_rows'] and not report['noop']['failed_rows']
    report['serial_seconds'] = round(report['baseline']['seconds'] + report['noop']['seconds']
                                     + sum(m['seconds'] for m in report['mutants']), 3)
    (HERE / 'mutations.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'mutants': len(report['mutants']), 'all_named_rows_red': report['all_named_rows_red'],
                      'controls_green': report['controls_green'], 'serial_seconds': report['serial_seconds']}))


if __name__ == '__main__':
    main()
