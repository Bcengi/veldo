#!/usr/bin/env python3
"""Drive every finding-64 mutation and record what each one turned red, and why.

Uses the registry and file materializer of scripts/check_teeth_mutations.py unchanged. Each run
is a fresh interpreter executing the shared preamble and the VELDO-0064 suite, with the
suite's production-copy anchor pointed at the baseline source, an unmutated (no-op) copy or the
mutant. Rows and the suite's own failure detail lines are retained, with source digests and
the wall time of every run. Writes proof/VELDO-0064/mutations.json.

    python3 -B proof/VELDO-0064/drive.py

With `--red COMMIT` it instead runs the current suite once against the production modules of
COMMIT (the inbox, the projection and the claim organ, read with `git show`), to record which
rows that code fails. Writes proof/VELDO-0064/red-at-COMMIT.json. The suite constructs the
Telegram edge without a configured chat because the edge now routes per owner; the edge at a
commit that still takes one configured chat receives the suite owner's enrolled chat as that
default, which is the only deployment such an edge supported. That one-line default is the only
change to the old code, and the record names it.

    python3 -B proof/VELDO-0064/drive.py --red 8125bcc
"""
import ast
import contextlib
import hashlib
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
SUITE = '60_veldo_0064_inbox.py'


def _driver():
    spec = importlib.util.spec_from_file_location('ctm', ROOT / 'scripts/check_teeth_mutations.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RED_MODULES = ('control_assignment.py', 'control_channel_projection.py', 'control_claim.py')
OLD_EDGE = '    def __init__(self, base_url, token, chat, timeout=10):\n'
OLD_EDGE_DEFAULT = '    def __init__(self, base_url, token, chat=5550001, timeout=10):\n'


def one(paths):
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
        for module, path in paths.items():
            anchor = 'ROOT / ".veldo" / "' + module + '"'
            if source.count(anchor) != 1:
                raise RuntimeError('suite production-copy anchor moved: ' + module)
            source = source.replace(anchor, '__import__("pathlib").Path(' + repr(path) + ')')
        exec(compile(source, SUITE, 'exec'), ns)
    mine = [r for r in rows if r[0].startswith('VELDO-0064 ')]
    details = [line.strip() for line in out.getvalue().split('\n') if 'VELDO-0064' in line and 'detail:' in line]
    return {'rows': mine, 'failed_rows': [r[0] for r in mine if not r[1]], 'details': details,
            'preamble_rows': len(rows) - len(mine)}


def run(module, path=None, paths=None):
    started = time.monotonic()
    paths = paths if paths is not None else ({module: str(path)} if path else {})
    command = [sys.executable, '-B', __file__, '--one', json.dumps(paths)]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if proc.returncode:
        raise RuntimeError('run did not complete its assertions: ' + proc.stderr[-2000:])
    return dict(json.loads(proc.stdout), seconds=round(time.monotonic() - started, 3))


def red(commit):
    """Run the current suite once against COMMIT's inbox, projection and claim organ."""
    resolved = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', commit + '^{commit}'],
                              capture_output=True, text=True, check=True).stdout.strip()
    paths, sources = {}, {}
    with tempfile.TemporaryDirectory(prefix='v64-red-') as directory:
        for module in RED_MODULES:
            text = subprocess.run(['git', '-C', str(ROOT), 'show', resolved + ':.veldo/' + module],
                                  capture_output=True, text=True, check=True).stdout
            changed = []
            if module == 'control_channel_projection.py' and text.count(OLD_EDGE) == 1:
                text = text.replace(OLD_EDGE, OLD_EDGE_DEFAULT)
                changed.append(OLD_EDGE_DEFAULT.strip())
            target = Path(directory) / module
            target.write_text(text)
            paths[module] = str(target)
            sources[module] = dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(), changed=changed)
        observed = run(None, paths=paths)
    report = dict(schema='veldo.proof-red/v1', spec_id='VELDO-0064', suite='scripts/suites/' + SUITE,
                  commit=resolved, modules=sources, **observed)
    name = 'red-at-%s.json' % commit
    (Path(__file__).parent / name).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'commit': resolved, 'failed_rows': observed['failed_rows'], 'written': name}))


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == '--one':
        print(json.dumps(one(json.loads(sys.argv[2]))))
        return
    if len(sys.argv) >= 3 and sys.argv[1] == '--red':
        red(sys.argv[2])
        return
    ctm = _driver()
    cases = [c for c in ctm.cases() if c['finding'] == 64]
    report = {'schema': 'veldo.proof-mutations/v1', 'spec_id': 'VELDO-0064', 'suite': 'scripts/suites/' + SUITE,
              'registry': 'scripts/check_teeth_mutations.py --finding 64', 'baseline': None, 'noop': {}, 'mutants': []}
    report['baseline'] = run('control_assignment.py')
    with tempfile.TemporaryDirectory(prefix='v64-drive-') as directory:
        for module in sorted({c['module'] for c in cases}):
            case = next(c for c in cases if c['module'] == module)
            noop = ctm.materialize(case, 'noop', Path(directory) / ('noop-' + module))
            report['noop'][module] = dict(run(module, noop['mutant']), source_sha256=noop['old_digest'],
                                          copy_sha256=noop['new_digest'])
        for case in cases:
            prepared = ctm.materialize(case, 'mutant', Path(directory) / case['name'])
            observed = run(case['module'], prepared['mutant'])
            report['mutants'].append(dict(name=case['name'], module='.veldo/' + case['module'], named_rows=case['rows'],
                                          diff='proof/VELDO-0064/%s.diff' % case['name'],
                                          source_sha256=prepared['old_digest'], mutant_sha256=prepared['new_digest'],
                                          named_row_red=all('VELDO-0064 ' + r in observed['failed_rows'] for r in case['rows']),
                                          **observed))
    report['all_named_rows_red'] = all(m['named_row_red'] for m in report['mutants'])
    report['controls_green'] = not report['baseline']['failed_rows'] and all(
        not n['failed_rows'] for n in report['noop'].values())
    report['serial_seconds'] = round(report['baseline']['seconds'] + sum(n['seconds'] for n in report['noop'].values())
                                     + sum(m['seconds'] for m in report['mutants']), 3)
    (Path(__file__).parent / 'mutations.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'mutants': len(report['mutants']), 'all_named_rows_red': report['all_named_rows_red'],
                      'controls_green': report['controls_green'], 'serial_seconds': report['serial_seconds']}))


if __name__ == '__main__':
    main()
