"""Run only VELDO-0302 falsifiers on disposable copies, never the gate mutation stages."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CASES = json.loads((HERE / 'falsifier-cases.json').read_text())
SUITE = ROOT / 'scripts/suites/153_veldo_0302_space_creators.py'


def exercise(root):
    rows = []
    def expect(name, condition):
        rows.append({'row': name.split(':', 1)[0], 'passed': bool(condition),
                     'detail': name.split(':', 1)[1].strip() if ':' in name else ''})
    exec(compile(SUITE.read_text(), str(SUITE), 'exec'), {'ROOT': root, 'expect': expect})
    return rows


baseline = exercise(ROOT)
assert baseline and all(row['passed'] for row in baseline), baseline
results = []
for case in CASES:
    with tempfile.TemporaryDirectory(prefix='v302-mutant-') as directory:
        root = Path(directory)
        shutil.copytree(ROOT / '.veldo', root / '.veldo', ignore=shutil.ignore_patterns('__pycache__'))
        (root / 'scripts').mkdir()
        shutil.copyfile(ROOT / 'scripts/agent_sandbox.py', root / 'scripts/agent_sandbox.py')
        target = root / case['dir'] / case['module']
        before = target.read_text()
        source = before
        for old, new in [(case['old'], case['new']), *case.get('also', [])]:
            assert source.count(old) == 1, case['name']
            source = source.replace(old, new)
        target.write_text(source)
        rows = exercise(root)
        expected = {'VELDO-0302 ' + name for name in case['rows']}
        red = [row for row in rows if not row['passed']]
        detected = expected <= {row['row'] for row in red}
        results.append({'name': case['name'], 'detected': detected, 'target_rows': case['rows'],
                        'red': red, 'before': hashlib.sha256(before.encode()).hexdigest(),
                        'after': hashlib.sha256(source.encode()).hexdigest()})
        print(case['name'] + ': ' + ('red on every target row' if detected else 'NOT DETECTED'), flush=True)
        assert detected, results[-1]
(HERE / 'falsifiers.json').write_text(json.dumps({'baseline_rows': len(baseline), 'baseline_passed': True,
                                                'mutations': results}, indent=1) + '\n')
