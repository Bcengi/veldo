"""Inspect registry anchors only; never execute a mutation driver or a suite."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = '9763249e09c689d850973eaa5e39ea030eb59df4'
START = '62cea275'


def definitions(driver):
    path = ROOT / 'scripts' / driver
    tree = ast.parse(path.read_text(), str(path))
    # Retain only declarative registry inputs and the pure replacement helpers.
    constants = {'ROOT', 'SIGNED', 'FIELDS', 'RENDERER_LOADERS',
                 'RENDERER_COMPANIONS', 'CASES'}
    functions = {'cases', 'edits', 'mutate'}
    selected = [node for node in tree.body
                if (isinstance(node, ast.Assign)
                    and all(isinstance(t, ast.Name) and t.id in constants
                            for t in node.targets))
                or (isinstance(node, ast.FunctionDef) and node.name in functions)]
    namespace = {'__file__': str(path), 'Path': Path, 'json': json}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


def audit():
    changed = set(subprocess.check_output(
        ['git', 'diff', '--name-only', BASE + '...' + START], cwd=ROOT,
        text=True).splitlines())
    reports = []
    replacement = definitions('check_teeth_mutations.py')
    for driver in ('check_teeth_mutations.py', 'check_review_mutations.py'):
        registry = definitions(driver)['cases']()
        for case in registry:
            folder = 'scripts/fixtures' if case.get('fixture') else case.get('dir', '.veldo')
            path = Path(folder) / case['module']
            # Engine changes also count when the registry uses the installed copy.
            affected = str(path) in changed or str(Path('engine') / path) in changed
            if not affected:
                continue
            text = (ROOT / path).read_bytes()
            report = dict(driver=driver, name=case['name'], path=str(path),
                          suite=case['suite'], rows=case['rows'], anchors=[])
            for old, new in replacement['edits'](case):
                old, new = old.encode(), new.encode()
                count = text.count(old)
                report['anchors'].append(dict(count=count,
                    old_sha256=hashlib.sha256(old).hexdigest(),
                    new_sha256=hashlib.sha256(new).hexdigest()))
                if count != 1:
                    break
                text = text.replace(old, new)
            report['applies'] = (len(report['anchors']) == len(replacement['edits'](case))
                                 and all(a['count'] == 1 for a in report['anchors']))
            reports.append(report)
    result = dict(base=BASE, start=START, changed_files=sorted(changed), cases=reports)
    destination = HERE / sys.argv[1]
    assert not destination.exists(), destination
    destination.write_text(json.dumps(result, indent=2) + '\n')
    failed = [r for r in reports if not r['applies']]
    print(json.dumps(dict(checked=len(reports), failed=failed), indent=2))


if __name__ == '__main__':
    audit()
