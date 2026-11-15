"""Targeted production-copy checks, without invoking a teeth coordinator or stage."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = ROOT / 'scripts/suites/155_veldo_0304_space_boundary.py'


def run(source):
    rows = []
    def expect(label, passed):
        rows.append({'row': label.split(':', 1)[0], 'passed': bool(passed)})
    exec(compile(source, str(SUITE), 'exec'), {'ROOT': ROOT, 'expect': expect})
    return rows


if __name__ == '__main__':
    cases = json.loads((HERE / 'registry-definitions.json').read_text())
    # Inspect literal registrations without executing the driver.
    tree = ast.parse((ROOT / 'scripts/check_teeth_mutations.py').read_text())
    definitions = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'add'
                and isinstance(node.args[0], ast.Constant) and node.args[0].value == 304):
            values = [ast.literal_eval(arg) for arg in node.args]
            definitions[values[1]] = values
    source = SUITE.read_text()
    baseline = run(source)
    assert len(baseline) == 40 and all(row['passed'] for row in baseline), baseline
    results = []
    for case in cases:
        path = Path(case['path'])
        registered = definitions['space304-' + case['name']]
        assert registered[2:] == [SUITE.name, path.name, case['old'], case['new'], [case['row']]]
        before = (ROOT / path).read_text()
        assert before.count(case['old']) == 1, case['name']
        after = before.replace(case['old'], case['new'])
        with tempfile.TemporaryDirectory(prefix='v304-production-copy-') as temporary:
            target = Path(temporary) / path
            target.parent.mkdir(parents=True)
            target.write_text(after)
            anchor = 'ROOT / "' + str(path.parent) + '" / "' + path.name + '"'
            assert source.count(anchor) == 1, (case['name'], anchor)
            injected = source.replace(anchor, '__import__("pathlib").Path(' + repr(str(target)) + ')')
            rows = run(injected)
            red = [row['row'] for row in rows if not row['passed']]
            assert 'VELDO-0304 ' + case['row'] in red, (case['name'], red)
        results.append({'case': case['name'], 'target': case['row'], 'red': red,
                        'before': hashlib.sha256(before.encode()).hexdigest(),
                        'after': hashlib.sha256(after.encode()).hexdigest()})
        print(case['name'] + ': designated row red', flush=True)
    result = {'baseline': baseline, 'cases': results, 'teeth_stage': 'not run',
              'suite_sha256': hashlib.sha256(source.encode()).hexdigest()}
    (HERE / 'registered-falsifiers.json').write_text(json.dumps(result, indent=1) + '\n')
