"""Targeted falsifiers in disposable copies. This does not run a teeth stage."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = ROOT / 'scripts/suites/155_veldo_0304_space_boundary.py'


def exercise(root):
    rows = []
    def expect(label, passed):
        rows.append({'row': label.split(':', 1)[0], 'passed': bool(passed),
                     'detail': label.split(':', 1)[1] if ':' in label else ''})
    exec(compile(SUITE.read_text(), str(SUITE), 'exec'), {'ROOT': root, 'expect': expect})
    return rows


def run(case):
    with tempfile.TemporaryDirectory(prefix='v304-mutation-') as directory:
        root = Path(directory)
        for part in ('.veldo', 'engine/.veldo', 'engine/scripts'):
            shutil.copytree(ROOT / part, root / part, ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(ROOT / 'scripts', root / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        target = root / case['path']
        before = target.read_text()
        assert before.count(case['old']) == 1, case['name']
        after = before.replace(case['old'], case['new'])
        target.write_text(after)
        rows = exercise(root)
        red = [row for row in rows if not row['passed']]
        assert 'VELDO-0304 ' + case['row'] in {row['row'] for row in red}, red
        return {'case': case['name'], 'row': case['row'], 'red': red,
                'before': hashlib.sha256(before.encode()).hexdigest(),
                'after': hashlib.sha256(after.encode()).hexdigest()}


if __name__ == '__main__':
    import sys
    baseline = exercise(ROOT)
    assert baseline and all(row['passed'] for row in baseline), baseline
    cases = json.loads((HERE / 'falsifier-cases.json').read_text())
    selected = set(sys.argv[1:])
    for case in cases:
        if selected and case['name'] not in selected:
            continue
        result = run(case)
        (HERE / (case['name'] + '.json')).write_text(json.dumps(result, indent=1) + '\n')
        print(case['name'] + ': designated row red')
