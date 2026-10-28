"""Run this ticket's falsifiers on disposable copies, restoring before each green.

Invoke under the owner's host flock. This driver never acquires a host lock and
never changes the production source. A crash, absent row or unrelated exception
cannot count as a detected falsifier.
"""
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'proof/VELDO-0112'
SUITE = 'scripts/suites/113_veldo_0112_registered_clients.py'
FIXTURE = 'scripts/fixtures/registered_clients.py'
ROWS = ('clients/registry-is-the-boundary', 'clients/every-registration-is-drivable',
        'clients/registry-growth-expands-cases')
MUTATIONS = (
    ('AC1', '.veldo/claim.py',
     "@_CLIENTS.entrypoint('claim', ('local_ipc',))\ndef claim(", 'def claim('),
    ('AC2', FIXTURE,
     "        'control_dispatch:Dispatches.prepare': 'in_process',\n", ''),
    ('AC3', FIXTURE,
     '    return tuple(result)\n', "    return tuple(case for case in result if case.client != 'extension')\n"),
)


def run(root):
    process = subprocess.run([sys.executable, '-B', str(root / SUITE)], cwd=root,
                             text=True, capture_output=True)
    try:
        result = json.loads(process.stdout)
    except ValueError as error:
        raise RuntimeError(dict(exit=process.returncode, stdout=process.stdout, stderr=process.stderr)) from error
    if set(result.get('rows', {})) != set(ROWS) or process.returncode not in (0, 1):
        raise RuntimeError('invalid drive: missing rows or abnormal exit')
    result['exit_code'] = process.returncode
    result['stderr'] = process.stderr
    return result


def main():
    summary = []
    for index, (ac, path, old, new) in enumerate(MUTATIONS):
        with tempfile.TemporaryDirectory(prefix='v112-mutation-') as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / '.veldo', root / '.veldo', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(ROOT / 'engine/.veldo', root / 'engine/.veldo', ignore=shutil.ignore_patterns('__pycache__'))
            for name in (SUITE, FIXTURE):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, root / name)
            source = (root / path).read_text()
            if source.count(old) != 1:
                raise RuntimeError('mutation anchor is not unique: ' + ac)
            changed = source.replace(old, new)
            (root / path).write_text(changed)
            if path.startswith('.veldo/'):
                (root / 'engine' / path).write_text(changed)
            diff = ''.join(difflib.unified_diff(source.splitlines(True), changed.splitlines(True),
                                               fromfile=path, tofile=path))
            (OUT / (ac + '.diff')).write_text(diff)
            red = run(root)
            (OUT / (ac + '-red.json')).write_text(json.dumps(red, indent=2) + '\n')
            if red['rows'][ROWS[index]] is not False or red['exit_code'] != 1:
                raise RuntimeError('falsifier did not redden its completed row: ' + ac)
            (root / path).write_text(source)
            if path.startswith('.veldo/'):
                (root / 'engine' / path).write_text(source)
            green = run(root)
            (OUT / (ac + '-green.json')).write_text(json.dumps(green, indent=2) + '\n')
            if not all(green['rows'].values()) or green['exit_code'] != 0:
                raise RuntimeError('restored control failed: ' + ac)
            summary.append(dict(ac=ac, row=ROWS[index], red=False, restored_green=True,
                                mutation_digest=hashlib.sha256(diff.encode()).hexdigest()))
            print(ac + ': named row red, restored run green', flush=True)
    (OUT / 'mutations.json').write_text(json.dumps(summary, indent=2) + '\n')


if __name__ == '__main__':
    main()
