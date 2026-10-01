"""Run one VELDO-0127 capture control through the suite-only dispatcher.

Usage: python3 proof/VELDO-0127/reproduce-capture-controls.py MODE /absolute/path/to/log
MODE is noop, comment, or one of the three registered live.py mutation names.
Run from the repository root. No mutation driver or gate is executed; the registry
is read as AST data. Temporary copies reproduce materialize()'s relocated module
and worker()'s suite-anchor substitution. The sole child command runs suite 86.
"""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path.cwd()
mode, log_name = sys.argv[1:]
suite = '86_veldo_0127_agent_configuration'
module = 'proof/VELDO-0127/live.py'
cases = {}
for node in ast.walk(ast.parse((root / 'scripts/check_teeth_mutations.py').read_text())):
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'add' and len(node.args) >= 7:
        try:
            finding, name = [ast.literal_eval(n) for n in node.args[:2]]
            target = ast.literal_eval(node.args[3])
        except (ValueError, TypeError):
            continue
        if finding == 127 and target == module:
            cases[name] = [ast.literal_eval(n) for n in node.args[4:7]]
assert len(cases) == 3, cases
before = (root / module).read_bytes()
after = before
expected = []
if mode in cases:
    old, new, expected = cases[mode]
    assert before.count(old.encode()) == 1
    after = before.replace(old.encode(), new.encode())
elif mode == 'comment':
    after += b'\n# Semantically neutral capture relocation control.\n'
else:
    assert mode == 'noop', mode
with tempfile.TemporaryDirectory(prefix='v127-capture-control-') as scratch:
    scratch = Path(scratch)
    tree = scratch / 'tree'
    tree.mkdir()
    for path in root.iterdir():
        if path.name not in ('.git', 'scripts'):
            (tree / path.name).symlink_to(path, target_is_directory=path.is_dir())
    (tree / 'scripts/suites').mkdir(parents=True)
    for path in (root / 'scripts').iterdir():
        if path.name == 'selftest.py':
            (tree / 'scripts' / path.name).write_bytes(path.read_bytes())
        elif path.name != 'suites':
            (tree / 'scripts' / path.name).symlink_to(path, target_is_directory=path.is_dir())
    for path in (root / 'scripts/suites').iterdir():
        if path.name != suite + '.py':
            (tree / 'scripts/suites' / path.name).symlink_to(path, target_is_directory=path.is_dir())
    copied = scratch / 'relocated' / module
    copied.parent.mkdir(parents=True)
    copied.write_bytes(after)
    source = (root / ('scripts/suites/' + suite + '.py')).read_text()
    anchor = 'ROOT / "." / "' + module + '"'
    assert source.count(anchor) == 1
    source = source.replace(anchor, '__import__("pathlib").Path(' + repr(str(copied)) + ')')
    (tree / ('scripts/suites/' + suite + '.py')).write_text(source)
    with open(log_name, 'w') as log:
        proc = subprocess.run(['python3', 'scripts/selftest.py', '--suite', suite], cwd=tree, stdout=log, stderr=subprocess.STDOUT)
    lines = Path(log_name).read_text().splitlines()
    failures = [line.split('SELFTEST FAIL: ', 1)[1] for line in lines if 'SELFTEST FAIL: ' in line]
    summary = [line for line in lines if line.startswith('selftest (PARTIAL,') or 'detail:' in line]
    expected_rows = ['VELDO-0127 ' + row for row in expected]
    result = dict(mode=mode, command=['python3', 'scripts/selftest.py', '--suite', suite], returncode=proc.returncode,
                  old_digest=hashlib.sha256(before).hexdigest(), new_digest=hashlib.sha256(after).hexdigest(),
                  copied_loopback_exists=(copied.parent / 'loopback.py').exists(), failed_rows=failures,
                  expected_rows=expected_rows, summary=summary)
    Path(log_name + '.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    assert len([line for line in summary if line.startswith('selftest (PARTIAL,')]) == 1, result
    assert failures == expected_rows, result
    assert proc.returncode == (1 if expected_rows else 2), result
