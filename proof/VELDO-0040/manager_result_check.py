"""Drive manager-result guards and historical rebuilds, one suite at a time on copies.

Read registrations as data without importing or executing the teeth mutation driver.
Usage: python3 proof/VELDO-0040/manager_result_check.py
"""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

from runtime_cap_check import COMMAND, ROOT, SUITE, copy_tree

NAMES = ('containment-resolved-exit-hides-cap', 'containment-result-before-settled',
         'containment-unreadable-result-silent')
HERE = ROOT / 'proof/VELDO-0040'
PRE_FIX = 'ffb12c22'


def method(source, owner, name):
    cls = next(node for node in ast.parse(source).body if isinstance(node, ast.ClassDef) and node.name == owner)
    node = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == name)
    return ''.join(source.splitlines(True)[node.lineno - 1:node.end_lineno])


def main():
    tree = ast.parse((ROOT / 'scripts/check_teeth_mutations.py').read_text())
    cases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'contain':
            if isinstance(node.args[0], ast.Constant) and node.args[0].value in NAMES:
                name, module, old, new, row = map(ast.literal_eval, node.args)
                cases[name] = (module, old, new, row)
    assert set(cases) == set(NAMES)
    for name, module, owner, function, row in (
            ('containment-pre-fix-conclude', 'control_containment.py', 'Group', 'conclude', 'conclude-settles'),
            ('containment-pre-fix-receiver-control', 'control_launch.py', 'Receiver', '_reap',
             'manager-cap-after-adapter-exit')):
        current = (ROOT / '.veldo' / module).read_text()
        previous = subprocess.check_output(['git', 'show', PRE_FIX + ':engine/.veldo/' + module], text=True)
        cases[name] = (module, method(current, owner, function), method(previous, owner, function), row)
    # Remove only the reset budget guard to demonstrate the new bound assertion.
    module = 'control_containment.py'
    current = (ROOT / '.veldo' / module).read_text()
    old = method(current, 'Group', 'conclude')
    new = old.replace("                    remaining = end - time.monotonic()\n", "")
    new = new.replace("if shown.get('ActiveState') == 'failed' and remaining > 0:",
                      "if shown.get('ActiveState') == 'failed':")
    new = new.replace('timeout=min(TOOL_SECONDS, remaining), env=self.environment,',
                      'timeout=TOOL_SECONDS, env=self.environment,')
    cases['containment-reset-past-budget'] = (module, old, new, 'conclude-settles')
    report = {'command': COMMAND, 'pre_fix_commit': PRE_FIX, 'source_head': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], text=True).strip(), 'mutations': []}
    for name in cases:
        module, old, new, row = cases[name]
        with tempfile.TemporaryDirectory(prefix='flake0040-manual-') as directory:
            copy = Path(directory)
            copy_tree(copy)
            target = copy / '.veldo' / module
            source = target.read_text()
            assert source.count(old) == 1, name
            mutated = source.replace(old, new)
            target.write_text(mutated)
            diff = ''.join(difflib.unified_diff(source.splitlines(True), mutated.splitlines(True),
                                               fromfile='a/.veldo/' + module, tofile='b/.veldo/' + module))
            (HERE / 'mutations' / (name + '.diff')).write_text(diff)
            log = Path('/tmp') / ('flake0040-manual-' + name + '.log')
            with log.open('w') as stream:
                process = subprocess.run(COMMAND, cwd=copy, stdout=stream, stderr=subprocess.STDOUT, timeout=240)
            output = log.read_text()
            failed = [line.split('SELFTEST FAIL: ', 1)[1] for line in output.splitlines()
                      if 'SELFTEST FAIL: ' in line]
            target_row = 'VELDO-0040 containment/' + row
            raised = [line for line in failed if 'ran/containment/' in line]
            target_red = any(line.split(': ', 1)[0] == target_row for line in failed)
            target_raised = any('ran/containment/' + row in line for line in raised)
            counts = re.search(r'selftest \(PARTIAL[^\n]*: (\d+) passed, (\d+) failed', output)
            record = dict(name=name, target=target_row, exit_code=process.returncode,
                          failed_details=failed, target_red=target_red, target_raised=target_raised, raised_regions=raised,
                          purpose='historical rebuild' if 'pre-fix' in name else 'regression guard',
                          passed=int(counts[1]) if counts else None, failed=int(counts[2]) if counts else None,
                          source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                          mutated_sha256=hashlib.sha256(mutated.encode()).hexdigest(),
                          suite_sha256=hashlib.sha256((copy / SUITE).read_bytes()).hexdigest(),
                          diff='mutations/' + name + '.diff', log=str(log))
            report['mutations'].append(record)
            (HERE / 'manager-result-mutations.json').write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(record), flush=True)
            if name == 'containment-pre-fix-receiver-control':
                assert not target_red and not target_raised and counts, record
            else:
                assert target_red and not target_raised and counts, record
                if name != 'containment-pre-fix-conclude':
                    assert not raised, record


if __name__ == '__main__':
    main()
