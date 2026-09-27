#!/usr/bin/env python3
"""Drive every finding-155 mutation and record what each one turned red, and why.

Uses the registry and file materializer of scripts/check_teeth_mutations.py unchanged. Each run is a
fresh interpreter executing the shared preamble and the VELDO-0155 suite, with the suite's
production-copy anchor pointed at the baseline source, an unmutated (no-op) copy or the mutant. Rows
and the suite's own failure detail lines are retained, with source digests and the wall time of
every run. Writes proof/VELDO-0155/mutations.json and one exact applied diff per mutation beside it.

    python3 -B proof/VELDO-0155/drive.py

With `--red COMMIT` it instead runs the current suite once against the whole tree of COMMIT,
extracted read-only with `git archive` into a temporary directory, and writes
proof/VELDO-0155/red-at-COMMIT.json. Nothing in that tree is changed: its Claude Code module
qualifies no baseline, adds nothing after the flags and has no login guard, and its receiver strips
nothing at the wrapper and names no runtime directory, so the rows fail by their own assertions.

    python3 -B proof/VELDO-0155/drive.py --red <pre-change commit>

With `--survivors` it drives again the registered mutants of the two AC1 switches whose planted row
no mutant can turn red on 2.1.281 (unset CLAUDE_CODE_DISABLE_CLAUDE_MDS, drop disableAllHooks, each
with every other switch in place) and writes proof/VELDO-0155/survivors.json: the row that holds each
(baseline/qualified) red, the planted row it leaves green, and why the binary's own gates keep the
planted item out without it.

    python3 -B proof/VELDO-0155/drive.py --survivors
"""
import ast
import contextlib
import difflib
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
HERE = Path(__file__).resolve().parent
SUITE = '80_veldo_0155_claude_baseline.py'
PREFIX = 'VELDO-0155 '
FINDING = 155
MODULES = ('control_launch.py', 'control_engine_claude.py')


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Every Git call goes through the repository's one neutralized boundary.
_git_process = _load('v155_drive_git_process', ROOT / '.veldo' / 'git_process.py')


def _driver():
    spec = importlib.util.spec_from_file_location('ctm', ROOT / 'scripts/check_teeth_mutations.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def one(paths, root):
    """Run the shared preamble of `root` and the current suite once, in this interpreter."""
    shared = Path(root) / 'scripts/suites/shared.py'
    rows = []
    ns = {'__file__': str(shared), '__suite_file__': str(ROOT / 'scripts/suites' / SUITE),
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
    mine = [r for r in rows if r[0].startswith(PREFIX)]
    details = [line.strip() for line in out.getvalue().split('\n') if PREFIX.strip() in line and 'detail:' in line]
    return {'rows': mine, 'failed_rows': [r[0] for r in mine if not r[1]], 'details': details,
            'preamble_rows': len(rows) - len(mine)}


def run(paths=None, root=None):
    started = time.monotonic()
    command = [sys.executable, '-B', __file__, '--one', json.dumps(paths or {}), str(root or ROOT)]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=600)
    if proc.returncode:
        raise RuntimeError('run did not complete its assertions: ' + proc.stderr[-2000:])
    return dict(json.loads(proc.stdout), seconds=round(time.monotonic() - started, 3))


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None


def _raised(observed):
    return any('ran to its end' in d for d in observed['details'])


def red(commit):
    """Run the current suite once against the whole tree of COMMIT, extracted with git archive."""
    resolved = _git_process.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', commit + '^{commit}'],
                                capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='v155-red-') as directory:
        tree = Path(directory) / 'tree'
        tree.mkdir()
        archive = _git_process.run(['git', '-C', str(ROOT), 'archive', resolved], capture_output=True, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(tree)], input=archive, check=True)
        modules = {'.veldo/' + m: dict(at_commit=_sha(tree / '.veldo' / m), now=_sha(ROOT / '.veldo' / m)) for m in MODULES}
        observed = run({}, tree)
    report = dict(schema='veldo.proof-red/v1', spec_id='VELDO-0155', suite='scripts/suites/' + SUITE, commit=resolved,
                  tree='git archive %s, unchanged; the current suite file run against it' % resolved, modules=modules,
                  by_assertion=not _raised(observed), **observed)
    name = 'red-at-%s.json' % commit
    (HERE / name).write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'commit': resolved, 'failed_rows': observed['failed_rows'], 'by_assertion': report['by_assertion'],
                      'written': name}))


# The two AC1 switches the binary's gates make unfalsifiable on a planted profile or clone item: their
# registered mutants (held by baseline/qualified) driven again, judged on the planted row they cannot red.
SURVIVORS = {
    'claude-baseline-claude-mds-unset': dict(
        rows=['baseline/planted-instructions'],
        why='the binary loads the user CLAUDE.md only when pr("userSettings") and the project ones only when '
            'pw("projectSettings"): with no setting source neither loads, whatever the switch; what only the switch '
            'keeps out is the managed CLAUDE.md under /etc/claude-code (not relocatable) and --add-dir directories'),
    'claude-baseline-hooks-kept': dict(
        rows=['baseline/planted-hook'],
        why='the binary takes hooks from the merged settings of the enabled sources: with no setting source the '
            'profile\'s and the clone\'s hooks never merge; what only the switch keeps out is hooks in the --settings '
            'file itself, --plugin-dir plugins and skill or agent frontmatter, none of which a baseline run has'),
}


def survivors():
    ctm = _driver()
    report = {'schema': 'veldo.proof-survivors/v1', 'spec_id': 'VELDO-0155', 'suite': 'scripts/suites/' + SUITE,
              'baseline': run(), 'survivors': []}
    with tempfile.TemporaryDirectory(prefix='v155-survivors-') as directory:
        for case in [c for c in ctm.cases() if c['finding'] == FINDING and c['name'] in SURVIVORS]:
            planted = SURVIVORS[case['name']]
            prepared = ctm.materialize(case, 'mutant', Path(directory) / case['name'])
            observed = run({case['module']: str(prepared['mutant'])})
            report['survivors'].append(dict(name=case['name'], module='.veldo/' + case['module'],
                                            registered_rows=case['rows'], planted_rows=planted['rows'],
                                            why=planted['why'], diff='proof/VELDO-0155/%s.diff' % case['name'],
                                            registered_row_red=all(PREFIX + r in observed['failed_rows']
                                                                   for r in case['rows']),
                                            planted_row_green=not any(PREFIX + r in observed['failed_rows']
                                                                      for r in planted['rows']), **observed))
    (HERE / 'survivors.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({s['name']: s['failed_rows'] for s in report['survivors']}))


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == '--survivors':
        survivors()
        return
    if len(sys.argv) >= 3 and sys.argv[1] == '--red':
        red(sys.argv[2])
        return
    if len(sys.argv) >= 4 and sys.argv[1] == '--one':
        print(json.dumps(one(json.loads(sys.argv[2]), sys.argv[3])))
        return
    ctm = _driver()
    cases = [c for c in ctm.cases() if c['finding'] == FINDING]
    report = {'schema': 'veldo.proof-mutations/v1', 'spec_id': 'VELDO-0155', 'suite': 'scripts/suites/' + SUITE,
              'registry': 'scripts/check_teeth_mutations.py --finding %d' % FINDING, 'baseline': run(), 'noop': None,
              'mutants': []}
    with tempfile.TemporaryDirectory(prefix='v155-drive-') as directory:
        report['noop'] = {}
        for module in sorted({c['module'] for c in cases}):
            case = next(c for c in cases if c['module'] == module)
            noop = ctm.materialize(case, 'noop', Path(directory) / ('noop-' + module))
            report['noop'][module] = dict(run({module: str(noop['mutant'])}), source_sha256=noop['old_digest'],
                                          copy_sha256=noop['new_digest'])
        for case in cases:
            prepared = ctm.materialize(case, 'mutant', Path(directory) / case['name'])
            source = prepared['source'].read_text()
            (HERE / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                source.splitlines(keepends=True), ctm.mutate(source, case).splitlines(keepends=True),
                n=0, fromfile='a/.veldo/' + case['module'], tofile='b/.veldo/' + case['module'])))
            observed = run({case['module']: str(prepared['mutant'])})
            report['mutants'].append(dict(name=case['name'], module='.veldo/' + case['module'], named_rows=case['rows'],
                                          diff='proof/VELDO-0155/%s.diff' % case['name'],
                                          source_sha256=prepared['old_digest'], mutant_sha256=prepared['new_digest'],
                                          named_row_red=all(PREFIX + r in observed['failed_rows'] for r in case['rows']),
                                          by_assertion=not _raised(observed), **observed))
    report['all_named_rows_red'] = all(m['named_row_red'] for m in report['mutants'])
    report['all_by_assertion'] = all(m['by_assertion'] for m in report['mutants'])
    report['controls_green'] = not report['baseline']['failed_rows'] and all(
        not n['failed_rows'] for n in report['noop'].values())
    per_row = {}
    for m in report['mutants']:
        for r in m['named_rows']:
            per_row.setdefault(r, []).append(m['name'])
    report['mutations_per_row'] = per_row
    report['serial_seconds'] = round(report['baseline']['seconds'] + sum(n['seconds'] for n in report['noop'].values())
                                     + sum(m['seconds'] for m in report['mutants']), 3)
    (HERE / 'mutations.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps({'mutants': len(report['mutants']), 'all_named_rows_red': report['all_named_rows_red'],
                      'all_by_assertion': report['all_by_assertion'],
                      'controls_green': report['controls_green'], 'serial_seconds': report['serial_seconds']}))


if __name__ == '__main__':
    main()
