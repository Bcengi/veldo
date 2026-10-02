"""Recorded-cause proof: only suite 63, sequentially, with no load modes or gate drivers.

Modes: normal, gate, mutations, pre-fix. Mutation registrations are read as AST data.
The pre-fix case replaces both complete production files with revision 9a48b4ea.
"""
import ast
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from runtime_cap_check import COMMAND, ROOT, SUITE, copy_tree

HERE = ROOT / 'proof/VELDO-0040'
REPORT = HERE / 'recorded-cause-runs.json'
PRE_FIX = '9a48b4ea'
NAMES = ('containment-recorded-runtime-ignored', 'containment-not-found-is-success',
         'containment-normal-exit-unknown', 'containment-recorded-cap-overrides-explicit',
         'containment-start-activation-lost', 'containment-oom-evidence-lost',
         'containment-resolved-exit-hides-cap', 'containment-result-before-settled',
         'containment-unreadable-result-silent')
MODULES = ('control_containment.py', 'control_launch.py')


def run(name, cwd, gate=False, targets=(), diff=None):
    with tempfile.TemporaryDirectory(prefix='v40-observer-') as directory:
        observer = Path(directory)
        snapshot = observer / 'snapshot.json'
        (observer / 'sitecustomize.py').write_text('''import atexit, json, os, sys
from pathlib import Path
def capture():
    s = sys.modules.get('shared')
    if s is not None and hasattr(s, '_V40_OBSERVED'):
        Path(os.environ['V40_SNAPSHOT']).write_text(json.dumps({
            'passed': s.PASS, 'failed': s.FAIL, 'observed': s._V40_OBSERVED,
            'seconds': s._V40_SECONDS}, default=str))
atexit.register(capture)
''')
        env = dict(os.environ, PYTHONPATH=str(observer), V40_SNAPSHOT=str(snapshot),
                   PYTHONDONTWRITEBYTECODE='1')
        log = Path('/tmp') / ('0040-recorded-' + name + '.log')
        command = ['bash', '-c', ' '.join(COMMAND)] if gate else COMMAND
        with log.open('w') as stream:
            process = subprocess.run(command, cwd=cwd, env=env, stdout=stream,
                                     stderr=subprocess.STDOUT, timeout=240)
        output = log.read_text()
        failed = [line.split('SELFTEST FAIL: ', 1)[1] for line in output.splitlines()
                  if 'SELFTEST FAIL: ' in line]
        data = json.loads(snapshot.read_text()) if snapshot.exists() else {}
        counts = re.search(r'selftest \(PARTIAL[^\n]*: (\d+) passed, (\d+) failed', output)
        red = {target: any(line.split(': ', 1)[0] == 'VELDO-0040 containment/' + target
                          for line in failed) for target in targets}
        raised = {target: any('ran/containment/' + target in line for line in failed)
                  for target in targets}
        observations = data.get('observed') or {}
        keys = tuple(target.replace('-', '_') for target in targets) if targets else (
            'start_evidence', 'recorded_runtime_after_collection', 'not_found_unknown',
            'normal_exit_before_cap', 'recorded_cap_explicit_precedence', 'retained_oom_before_cleanup',
            'manager_cap_after_adapter_exit', 'conclude_settles', 'conclude_unknown')
        observations = {key: observations.get(key) for key in (*keys, 'runtime_cap', 'raised', 'conclude_reset_budget')}
        row = dict(name=name, command=command, exit_code=process.returncode, log=str(log),
                   passed=int(counts[1]) if counts else None, failed=int(counts[2]) if counts else None,
                   failed_details=failed, target_red=red, target_raised=raised,
                   sha256={path: hashlib.sha256((cwd / path).read_bytes()).hexdigest()
                           for path in (SUITE, *('.veldo/' + module for module in MODULES))},
                   observed=observations, seconds=data.get('seconds'), diff=diff)
        report = json.loads(REPORT.read_text()) if REPORT.exists() else {}
        report.update(pre_fix_commit=PRE_FIX, source_head=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], text=True).strip())
        report[name] = row
        REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        print(json.dumps({key: row[key] for key in ('name', 'passed', 'failed', 'target_red', 'target_raised')}), flush=True)
        assert counts and process.returncode in (1, 2), row
        if targets:
            assert all(red.values()) and not any(raised.values()), row
        else:
            assert row['failed'] == 0 and not data['observed']['raised'], row


def main():
    mode = sys.argv[1]
    if mode in ('normal', 'gate'):
        run(mode, ROOT, gate=mode == 'gate')
        return
    assert mode in ('mutations', 'pre-fix')
    cases = {}
    if mode == 'mutations':
        tree = ast.parse((ROOT / 'scripts/check_teeth_mutations.py').read_text())
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'contain'
                    and isinstance(node.args[0], ast.Constant) and node.args[0].value in NAMES):
                name, module, old, new, target = map(ast.literal_eval, node.args)
                cases[name] = (module, old, new, target)
        assert set(cases) == set(NAMES)
    else:
        cases['pre-fix'] = None
    for name, case in cases.items():
        with tempfile.TemporaryDirectory(prefix='v40-recorded-') as directory:
            copy = Path(directory)
            copy_tree(copy)
            before = {module: (copy / '.veldo' / module).read_text() for module in MODULES}
            if case:
                module, old, new, target = case
                path = copy / '.veldo' / module
                source = path.read_text()
                assert source.count(old) == 1, name
                path.write_text(source.replace(old, new))
                targets = (target,)
            else:
                for module in MODULES:
                    source = subprocess.check_output(['git', 'show', PRE_FIX + ':engine/.veldo/' + module], text=True)
                    (copy / '.veldo' / module).write_text(source)
                targets = ('recorded-runtime-after-collection', 'not-found-unknown')
            diff = ''.join(''.join(difflib.unified_diff(before[module].splitlines(True),
                           (copy / '.veldo' / module).read_text().splitlines(True),
                           fromfile='a/.veldo/' + module, tofile='b/.veldo/' + module)) for module in MODULES)
            diff_path = HERE / 'mutations' / ('recorded-' + name + '.diff')
            diff_path.write_text(diff)
            run(name, copy, targets=targets, diff=str(diff_path.relative_to(HERE)))


if __name__ == '__main__':
    main()
