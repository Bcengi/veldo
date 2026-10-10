#!/usr/bin/env python3
"""Run only suite 103 against temporary source mutations, serially, restoring every byte."""
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = '103_veldo_0211_borrowed_login'
LAUNCHER = ('engine/scripts/agent_sandbox.py', 'scripts/agent_sandbox.py')
LIVE = ('proof/VELDO-0127/live.py',)
SOURCES = [ROOT / path for path in LAUNCHER + LIVE]
# (name, files, anchor, mutant, the suite 103 row that must fail). The first three are the spec's
# declared falsifiers (AC1 to AC3); the rest cover the lease, the sweep, the signal mask and the guard.
MUTATIONS = [
    ('AC1', LAUNCHER, '                settle_borrow(borrow)\n',
     '                pass  # falsifier: omit credential persistence\n', 'rotation/live/claude/success'),
    ('AC2', LAUNCHER, '            problem = replace_problem(real)\n',
     '            problem = None  # falsifier: admit without the write-back probe\n',
     'refused-before-launch/live/claude/preflight'),
    ('AC3', LAUNCHER, '        if not failures:\n            discard_journal(borrow.journal)\n',
     '        if True:  # falsifier: drop failed rotations\n            discard_journal(borrow.journal)\n',
     'recovery/live-retains-private-rotated-token'),
    ('lease-busy', LAUNCHER, "            raise ValueError('borrowed login is busy: %s is held by another run' % path) from None\n",
     '            pass  # falsifier: ignore another run\'s lease\n', 'refused-before-launch/live/claude/busy'),
    ('sweep', LAUNCHER, "                if digest(data) != entry['sha256']:\n",
     '                if False:  # falsifier: the sweep drops a killed run\'s rotation\n',
     'sweep/killed-run-rotation-kept-and-reported'),
    ('signal-mask', LAUNCHER, '    mask = signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)\n    try:\n        failures = write_back(',
     '    mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])\n    try:\n        failures = write_back(',
     'write-back/stop-signals-blocked'),
    ('live-guard', LIVE, '                        subprocess.run(command, env=env,',
     '                        0 and subprocess.run(command, env=env,',
     'live-guard/killed-capture-slice-stopped-under-lease-then-written-back'),
]


def main():
    original = {path: path.read_bytes() for path in SOURCES}
    rows = []
    for criterion, files, old, new, target in MUTATIONS:
        changes = []
        try:
            for path in [ROOT / name for name in files]:
                text = original[path].decode()
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
