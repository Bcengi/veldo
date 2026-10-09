#!/usr/bin/env python3
"""Run only suite 103 against three temporary source mutations, serially, restoring every byte."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = '103_veldo_0211_borrowed_login'
SOURCES = [ROOT / path for path in ('engine/scripts/agent_sandbox.py', 'scripts/agent_sandbox.py')]
MUTATIONS = [
    ('AC1', '                write_back(scratch, credentials, locked=True)',
     '                pass  # falsifier: omit credential persistence', 'rotation/live/claude/success'),
    ('AC2', '            replace_atomically(real, original, expected=original, locked=True)',
     '            pass  # falsifier: admit without write-back preflight', 'refused-before-launch/live/claude/preflight'),
    ('AC3', '    if failures:\n', '    if False and failures:\n', 'recovery/live-retains-private-rotated-token'),
]


def main():
    original = {path: path.read_bytes() for path in SOURCES}
    rows = []
    for criterion, old, new, target in MUTATIONS:
        changes = []
        try:
            for path, data in original.items():
                text = data.decode()
                if text.count(old) != 1:
                    raise RuntimeError('falsifier anchor moved: ' + criterion)
                mutant = text.replace(old, new)
                changes.extend(difflib.unified_diff(text.splitlines(True), mutant.splitlines(True),
                                                   fromfile=str(path.relative_to(ROOT)),
                                                   tofile=str(path.relative_to(ROOT))))
                path.write_text(mutant)
            (HERE / (criterion + '.diff')).write_text(''.join(changes))
            with (HERE / (criterion + '.log')).open('w') as log:
                done = subprocess.run([sys.executable, 'scripts/selftest.py', '-' * 2 + 'suite', SUITE],
                                      cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=60)
            text = (HERE / (criterion + '.log')).read_text()
            detected = 'SELFTEST FAIL: VELDO-0211 ' + target in text
            rows.append(dict(criterion=criterion, target=target, detected=detected,
                             exit_code=done.returncode, diff=criterion + '.diff', log=criterion + '.log'))
        finally:
            for path, data in original.items():
                path.write_bytes(data)
    report = dict(scope='diagnostic suite selections only; no gate or passed unit evidence',
                  sources={str(p.relative_to(ROOT)): hashlib.sha256(b).hexdigest() for p, b in original.items()},
                  mutations=rows, restored=all(p.read_bytes() == b for p, b in original.items()))
    (HERE / 'falsifiers.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'detected': sum(row['detected'] for row in rows), 'total': len(rows),
                      'restored': report['restored']}))
    return 0 if report['restored'] and all(row['detected'] for row in rows) else 1


if __name__ == '__main__':
    sys.exit(main())
