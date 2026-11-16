"""Apply registered VELDO-0315 falsifiers to disposable copies, without a teeth stage."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = ROOT / 'scripts/suites/156_veldo_0315_reconcile.py'


def registered():
    found = []
    tree = ast.parse((ROOT / 'scripts/check_teeth_mutations.py').read_text())
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'add'
                and node.args and isinstance(node.args[0], ast.Constant) and node.args[0].value == 315):
            values = [ast.literal_eval(arg) for arg in node.args]
            record = dict(zip(('finding', 'name', 'suite', 'module', 'old', 'new', 'rows'), values))
            record.update({key.arg: ast.literal_eval(key.value) for key in node.keywords})
            found.append(record)
    return found


def exercise(source):
    rows = []

    def expect(label, passed):
        name, _, detail = label.partition(':')
        rows.append({'row': name, 'passed': bool(passed), 'detail': detail.strip()})

    exec(compile(source, str(SUITE), 'exec'), {'ROOT': ROOT, 'expect': expect})
    return rows


def main():
    cases = json.loads((HERE / 'falsifier-cases.json').read_text())
    assert cases == json.loads(json.dumps(registered())), 'literal registrations differ'
    source = SUITE.read_text()
    baseline = exercise(source)
    assert baseline and all(row['passed'] for row in baseline), baseline
    results = []
    for case in cases:
        before = (ROOT / '.veldo' / case['module']).read_text()
        after = before
        for old, new in [(case['old'], case['new'])] + case.get('also', []):
            assert after.count(old) == 1, case['name']
            after = after.replace(old, new)
        with tempfile.TemporaryDirectory(prefix='veldo-0315-mutant-') as directory:
            mutant = Path(directory) / case['module']
            mutant.write_text(after)
            anchor = 'ROOT / ".veldo" / "' + case['module'] + '"'
            assert source.count(anchor) == 1
            changed = source.replace(anchor, '__import__("pathlib").Path(' + repr(str(mutant)) + ')')
            rows = exercise(changed)
        red = [row for row in rows if not row['passed']]
        targeted = all(name in {row['row'] for row in red} for name in case['rows'])
        result = {'case': case['name'], 'applications': 1, 'targeted_rows_red': targeted,
                  'red': red, 'before_sha256': hashlib.sha256(before.encode()).hexdigest(),
                  'after_sha256': hashlib.sha256(after.encode()).hexdigest()}
        results.append(result)
        (HERE / 'falsifiers.json').write_text(json.dumps({'baseline': baseline, 'results': results,
            'scope': 'targeted copies only; not a teeth stage or gate receipt'}, indent=1) + '\n')
        print(case['name'] + ': ' + ('designated row red' if targeted else 'FAILED'), flush=True)
        assert targeted, result
    print(str(len(results)) + ' falsifiers detected; ' + str(len(baseline)) + ' baseline rows green', flush=True)


if __name__ == '__main__':
    main()
