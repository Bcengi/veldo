#!/usr/bin/env python3
"""Replay only VELDO-0127 against an unchanged archived pre-change tree."""
import ast
import contextlib
import importlib.util
import io
import json
import hashlib
import time
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = '87_veldo_0127_codex_delivery.py'
P = '-' * 2


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def one(root, paths=None, baseline=False):
    rows = []
    shared = Path(root) / 'scripts/suites/shared.py'
    ns = {'__file__':str(shared), '__suite_file__':str(ROOT / 'scripts/suites' / SUITE),
          '__observe__':lambda name, condition: rows.append([name.split(':',1)[0], bool(condition)])}
    tree = ast.parse(shared.read_text(), str(shared))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        source = ((Path(root) if baseline else ROOT) / 'scripts/suites' / SUITE).read_text()
        for module, path in (paths or {}).items():
            anchor = 'ROOT / ".veldo" / "' + module + '"'
            assert source.count(anchor) == 1, module
            source = source.replace(anchor, '__import__("pathlib").Path(' + repr(str(path)) + ')')
        started = time.monotonic()
        exec(compile(source, SUITE, 'exec'), ns)
        if baseline:
            seconds = time.monotonic() - started
            ns['expect']('VELDO-0127 delivery/runtime', seconds < 60)
            print('  VELDO-0127 delivery/runtime seconds: %.3f' % seconds)
    rows = [r for r in rows if r[0].startswith('VELDO-0127 ')]
    details = [line.strip() for line in output.getvalue().splitlines() if 'VELDO-0127' in line and 'detail:' in line]
    timings = [line.strip() for line in output.getvalue().splitlines() if 'delivery/runtime seconds:' in line]
    return {'timings': timings, 'rows':rows, 'failed_rows':[r[0] for r in rows if not r[1]], 'details':details,
            'by_assertion':not any('raised ' in d for d in details)}


def manual_mutations():
    """Read two literal registrations without importing or running the checker."""
    selected = {'role127-search-unsupported-accepted', 'role127-delivery-web-dropped'}
    tree = ast.parse((ROOT / 'scripts/check_teeth_mutations.py').read_text())
    cases = {}
    for call in ast.walk(tree):
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name) or call.func.id != 'add':
            continue
        if len(call.args) < 7 or not isinstance(call.args[1], ast.Constant) or call.args[1].value not in selected:
            continue
        finding, name = [ast.literal_eval(n) for n in call.args[:2]]
        assert finding == 127 and name not in cases
        module, old, new, rows = [ast.literal_eval(n) for n in call.args[3:7]]
        cases[name] = (module, old, new, rows)
    assert set(cases) == selected
    reports = []
    for name in sorted(cases):
        module, old, new, targets = cases[name]
        source = (ROOT / '.veldo' / module).read_text()
        assert source.count(old) == 1, name
        mutant = source.replace(old, new)
        with tempfile.TemporaryDirectory(prefix='v127-manual-mutant-') as temp:
            path = Path(temp) / '.veldo' / module
            path.parent.mkdir()
            path.write_text(mutant)
            started = time.monotonic()
            done = subprocess.run([sys.executable, '-B', __file__, P + 'one', str(ROOT),
                                   json.dumps({module: str(path)})], capture_output=True, text=True, timeout=120)
            assert done.returncode == 0, done.stderr[-1000:]
            observed = json.loads(done.stdout)
        named = {row: [ok for label, ok in observed['rows'] if label == 'VELDO-0127 ' + row] for row in targets}
        rejected = observed['by_assertion'] and all(values == [False] for values in named.values())
        reports.append(dict(name=name, module='.veldo/' + module, suite=SUITE, named_rows=targets,
                            named_observations=named, rejected=rejected, by_assertion=observed['by_assertion'],
                            failed_rows=observed['failed_rows'], details=observed['details'],
                            seconds=round(time.monotonic()-started,3),
                            source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                            mutant_sha256=hashlib.sha256(mutant.encode()).hexdigest()))
        assert rejected, name
    path = HERE / 'mutations.json'
    report = json.loads(path.read_text())
    report['speed_repair_manual_checks'] = dict(base='2fb32ed8', executed=True, completed=True,
                                               checker_executed=False, mutants=reports)
    path.write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps([dict(name=r['name'], rejected=r['rejected'], seconds=r['seconds'],
                           rows=r['named_observations']) for r in reports]))


def main():
    if len(sys.argv) == 3 and sys.argv[1] == P + 'baseline':
        print(json.dumps(one(sys.argv[2], baseline=True)))
        return
    if len(sys.argv) in (3, 4) and sys.argv[1] == P + 'one':
        print(json.dumps(one(sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) == 4 else None)))
        return
    if sys.argv[1:] == [P + 'mutations']:
        manual_mutations()
        return
    if len(sys.argv) != 3 or sys.argv[1] != P + 'red':
        raise SystemExit('Use ' + P + 'red PRE_CHANGE_COMMIT or ' + P + 'mutations for the two manual checks.')
    git = load('role_drive_git', ROOT / '.veldo/git_process.py')
    commit = git.run(['git','-C',str(ROOT),'rev-parse',P+'verify',sys.argv[2]+'^{commit}'],
                     capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='v127-red-') as temp:
        archive = git.run(['git','-C',str(ROOT),'archive',commit], capture_output=True,check=True).stdout
        subprocess.run(['tar','-x','-C',temp],input=archive,check=True)
        result = subprocess.run([sys.executable,'-B',__file__,P+'baseline',temp],capture_output=True,text=True,timeout=600)
        if result.returncode:
            raise SystemExit('Red replay did not finish: ' + result.stderr[-1000:])
        observed = json.loads(result.stdout)
    behavior = [r for r in observed['rows'] if r[0] == 'VELDO-0127 delivery/runtime']
    observed['behavior_rows'] = behavior
    observed['every_changed_behavior_row_red'] = len(behavior) == 1 and all(not ok for _, ok in behavior)
    preserved = [r for r in observed['rows'] if r[0] != 'VELDO-0127 delivery/runtime']
    observed['all_original_rows_preserved_green'] = len(preserved) == 176 and all(ok for _, ok in preserved)
    report = dict(schema='veldo.proof-red/v1',spec_id='VELDO-0127',commit=commit,
                  suite='scripts/suites/'+SUITE,tree='unchanged git archive and delivery suite; current runtime assertion and unchanged wire helpers',**observed)
    path = HERE / ('red-at-' + sys.argv[2] + '.json')
    path.write_text(json.dumps(report,indent=1,sort_keys=True)+'\n')
    print(json.dumps({'failed_rows':len(report['failed_rows']),'rows':len(report['rows']),
                      'by_assertion':report['by_assertion'],
                      'every_changed_behavior_row_red': report['every_changed_behavior_row_red'],
                      'record':str(path.relative_to(ROOT))}))
    if (not report['by_assertion'] or not report['every_changed_behavior_row_red']
            or not report['all_original_rows_preserved_green']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
