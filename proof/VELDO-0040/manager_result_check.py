"""Manually drive only the three manager-result mutations, one suite at a time on copies.

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

NAMES = ('containment-inferred-exit-hides-cap', 'containment-result-before-settled',
         'containment-unreadable-result-silent')
HERE = ROOT / 'proof/VELDO-0040'


def main():
    tree = ast.parse((ROOT / 'scripts/check_teeth_mutations.py').read_text())
    cases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, 'id', None) == 'contain':
            if isinstance(node.args[0], ast.Constant) and node.args[0].value in NAMES:
                name, module, old, new, row = map(ast.literal_eval, node.args)
                cases[name] = (module, old, new, row)
    assert set(cases) == set(NAMES)
    report = {'command': COMMAND, 'source_head': subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], text=True).strip(), 'mutations': []}
    for name in NAMES:
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
            counts = re.search(r'selftest \(PARTIAL[^\n]*: (\d+) passed, (\d+) failed', output)
            record = dict(name=name, target=target_row, exit_code=process.returncode,
                          failed_details=failed, target_red=target_row in failed, raised_regions=raised,
                          passed=int(counts[1]) if counts else None, failed=int(counts[2]) if counts else None,
                          source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                          mutated_sha256=hashlib.sha256(mutated.encode()).hexdigest(),
                          suite_sha256=hashlib.sha256((copy / SUITE).read_bytes()).hexdigest(),
                          diff='mutations/' + name + '.diff', log=str(log))
            report['mutations'].append(record)
            (HERE / 'manager-result-mutations.json').write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(record), flush=True)
            assert record['target_red'] and not raised and counts, record


if __name__ == '__main__':
    main()
