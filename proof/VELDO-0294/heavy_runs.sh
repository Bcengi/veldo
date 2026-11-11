#!/bin/bash
set -eu
# The lead runs this under the gate lock after phase 2 completes the fixtures.
# This script neither acquires nor waits for that lock.
python3 - <<'PY'
import hashlib
import importlib.util
import json
import platform
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

root = Path.cwd()
out = root / 'proof/VELDO-0294'
suites = {
    '82_veldo_0129_worker_wiring': ['phase/fresh-dispatches', 'phase/brief', 'phase/step-cap',
                                  'phase/budget', 'phase/head-read', 'phase/state-note', 'phase/settled-at-stop'],
    '75_veldo_0062_accounts': ['tokens/run-record', 'tokens/pruned'],
    '72_veldo_0128_reports': ['report/run-over-tokens'],
}
mutants = [
    'phase294-single-dispatch', 'phase294-session-resumed', 'phase294-source-not-advanced',
    'phase294-brief-without-reading-rule', 'phase294-brief-carries-prior-answer',
    'phase294-brief-unbounded', 'phase294-brief-without-note-rule', 'phase294-cap-unenforced',
    'phase294-capped-work-dropped', 'tokens294-record-unwritten', 'tokens294-unknown-as-zero',
    'tokens294-flag-threshold-ignored', 'tokens294-unknown-not-flagged',
    'phase294-dispatches-unbounded', 'tokens294-never-pruned', 'phase294-head-symlink-followed',
    'phase294-ref-symlink-followed', 'phase294-state-note-not-carried', 'phase294-capped-left-unknown',
]

# Do not queue an incomplete phase 1 checkout as acceptance evidence.
for suite, rows in suites.items():
    source = (root / 'scripts/suites' / (suite + '.py')).read_text()
    if any(row not in source for row in rows) or 'VELDO-0294' not in source:
        raise SystemExit('Acceptance fixtures are pending. Finish BUILD_STATE.md before queueing this script.')
registry = (root / 'scripts/check_teeth_mutations.py').read_text()
if any(name not in registry for name in mutants):
    raise SystemExit('Mutation registrations are pending. Finish BUILD_STATE.md before queueing this script.')
for name in ('control_reservations', 'control_reservation_runtime', 'control_engine_claude',
             'control_engine_codex', 'control_launch', 'control_launch_work', 'control_telegram_report'):
    if (root / 'engine/.veldo' / (name + '.py')).read_bytes() != (root / '.veldo' / (name + '.py')).read_bytes():
        raise SystemExit('Runtime copy differs: ' + name)

head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
tree = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], text=True).strip()

def run(name, command, cwd, revision, rows=(), red=False):
    start = time.monotonic()
    digest, size, deciding = hashlib.sha256(), 0, []
    counts = None
    failed = set()
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for raw in process.stdout:
        digest.update(raw)
        size += len(raw)
        line = raw.decode('utf-8', errors='replace').strip()
        if 'selftest (PARTIAL,' in line:
            match = re.search(r': (\d+) passed, (\d+) failed', line)
            if match:
                counts = tuple(map(int, match.groups()))
        if 'FAIL' in line:
            failed.update(row for row in rows if 'VELDO-0294 ' + row in line)
        if ('VELDO-0294' in line or 'selftest (PARTIAL,' in line or line.startswith('mutations:')):
            if len(deciding) < 100:
                deciding.append(line[:1000])
    code = process.wait()
    if rows:
        passed = (code == 2 and counts is not None and
                  (failed == set(rows) and counts[1] == len(rows) if red else counts[1] == 0))
    else:
        passed = code == 0
    summary = dict(schema='veldo.proof-summary/v1', command=' '.join(command),
                   environment=dict(commit=revision, build_commit=head, build_tree=tree,
                                    python=platform.python_version(), host=platform.node()),
                   discarded=[dict(name=name + '.stdout', bytes=size, sha256=digest.hexdigest())],
                   deciding=dict(status='passed' if passed else 'failed', exit_code=code,
                                 counts=counts, rows=deciding, elapsed_seconds=round(time.monotonic() - start, 3)))
    raw = (json.dumps(summary, indent=2) + '\n').encode()
    if len(raw) > 1000000:
        raise SystemExit('Summary exceeds the proof limit: ' + name)
    (out / (name + '.summary.json')).write_bytes(raw)
    if not passed:
        raise SystemExit('Run failed; inspect ' + name + '.summary.json. No later run started.')

with tempfile.TemporaryDirectory(prefix='veldo-0294-red-') as directory:
    scratch = Path(directory) / 'base'
    subprocess.run(['git', 'clone', '-q', '--no-hardlinks', '--no-checkout', str(root), str(scratch)], check=True)
    subprocess.run(['git', '-C', str(scratch), 'checkout', '-q', '--detach', '6ee5bb5f'], check=True)
    for suite in suites:
        rel = Path('scripts/suites') / (suite + '.py')
        shutil.copyfile(root / rel, scratch / rel)
    for suite, rows in suites.items():
        run('red-before-' + suite.split('_')[0], ['python3', 'scripts/selftest.py', '--suite', suite],
            scratch, '6ee5bb5f', rows, red=True)

for suite, rows in suites.items():
    run('green-after-' + suite.split('_')[0], ['python3', 'scripts/selftest.py', '--suite', suite],
        root, head, rows)
for mutant in mutants:
    run('teeth-' + mutant, ['python3', 'scripts/check_teeth_mutations.py', '--case', mutant, '--jobs', '1'],
        root, head)
PY
