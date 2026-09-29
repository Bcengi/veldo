#!/usr/bin/env python3
"""Replay only VELDO-0127 against an unchanged archived pre-change tree."""
import ast
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = '86_veldo_0127_agent_configuration.py'
P = '-' * 2


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def one(root):
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
        exec(compile((ROOT / 'scripts/suites' / SUITE).read_text(), SUITE, 'exec'), ns)
    rows = [r for r in rows if r[0].startswith('VELDO-0127 ')]
    details = [line.strip() for line in output.getvalue().splitlines() if 'VELDO-0127' in line and 'detail:' in line]
    return {'rows':rows, 'failed_rows':[r[0] for r in rows if not r[1]], 'details':details,
            'by_assertion':not any('raised ' in d for d in details)}


def main():
    if len(sys.argv) == 3 and sys.argv[1] == P + 'one':
        print(json.dumps(one(sys.argv[2])))
        return
    if len(sys.argv) != 3 or sys.argv[1] != P + 'red':
        raise SystemExit('Use ' + P + 'red PRE_CHANGE_COMMIT. Mutations are run only by the reviewer.')
    git = load('role_drive_git', ROOT / '.veldo/git_process.py')
    commit = git.run(['git','-C',str(ROOT),'rev-parse',P+'verify',sys.argv[2]+'^{commit}'],
                     capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='v127-red-') as temp:
        archive = git.run(['git','-C',str(ROOT),'archive',commit], capture_output=True,check=True).stdout
        subprocess.run(['tar','-x','-C',temp],input=archive,check=True)
        result = subprocess.run([sys.executable,'-B',__file__,P+'one',temp],capture_output=True,text=True,timeout=120)
        if result.returncode:
            raise SystemExit('Red replay did not finish: ' + result.stderr[-1000:])
        observed = json.loads(result.stdout)
    behavior = [r for r in observed['rows'] if r[0] in {
        'VELDO-0127 review/skill-git-boundary'}]
    observed['behavior_rows'] = behavior
    observed['every_changed_behavior_row_red'] = len(behavior) == 1 and all(not ok for _, ok in behavior)
    report = dict(schema='veldo.proof-red/v1',spec_id='VELDO-0127',commit=commit,
                  suite='scripts/suites/'+SUITE,tree='unchanged git archive; current suite and proof helper',**observed)
    path = HERE / ('red-at-' + sys.argv[2] + '.json')
    path.write_text(json.dumps(report,indent=1,sort_keys=True)+'\n')
    print(json.dumps({'failed_rows':len(report['failed_rows']),'rows':len(report['rows']),
                      'by_assertion':report['by_assertion'],'record':str(path.relative_to(ROOT))}))


if __name__ == '__main__':
    main()
