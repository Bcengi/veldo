#!/bin/bash
set -eu
# The lead runs this under the gate lock, outside any run holding the Claude login lease.
# This script neither acquires nor waits for that lock.
python3 - "$@" <<'PY'
import argparse
import hashlib
import importlib.util
import json
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

root = Path.cwd()
out = root / 'proof/VELDO-0294'
parser = argparse.ArgumentParser()
for name in ('claude', 'codex', 'claude-profile', 'codex-profile', 'claude-model', 'codex-model'):
    parser.add_argument('--' + name, required=True)
args = vars(parser.parse_args())
for name in ('claude', 'codex', 'claude_profile', 'codex_profile'):
    args[name] = str(Path(args[name]).resolve(strict=True))
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

# Refuse an incomplete checkout before spending any engine work.
for suite, rows in suites.items():
    source = (root / 'scripts/suites' / (suite + '.py')).read_text()
    if any(row not in source for row in rows) or 'VELDO-0294' not in source:
        raise SystemExit('Acceptance fixtures are pending. Finish BUILD_STATE.md before queueing this script.')
registry = (root / 'scripts/check_teeth_mutations.py').read_text()
if any(name not in registry for name in mutants):
    raise SystemExit('Mutation registrations are pending. Finish BUILD_STATE.md before queueing this script.')
module_spec = importlib.util.spec_from_file_location('teeth294', root / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(teeth)
registered = [case for case in teeth.cases() if case['finding'] == 294]
if {case['name'] for case in registered} != set(mutants) or len(registered) != 19:
    raise SystemExit('Expected exactly nineteen VELDO-0294 mutations.')
for case in registered:
    source = (root / '.veldo' / case['module']).read_text()
    changed = teeth.mutate(source, case)
    compile(changed, case['module'], 'exec')
    if not all(row.startswith('VELDO-0294 ') for row in case['rows']):
        raise SystemExit('Mutation target has no spec prefix: ' + case['name'])
for name in ('control_reservations', 'control_reservation_runtime', 'control_engine_claude',
             'control_engine_codex', 'control_launch', 'control_launch_work', 'control_telegram_report'):
    if (root / 'engine/.veldo' / (name + '.py')).read_bytes() != (root / '.veldo' / (name + '.py')).read_bytes():
        raise SystemExit('Runtime copy differs: ' + name)

head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
tree = subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], text=True).strip()

def clean(text):
    return text.replace(str(root), '${WORKTREE}').replace(str(Path.home()), '~')

def run(name, command, cwd, revision, rows=(), red=False, extra_red=(), display=None, check=None):
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
        if line.startswith('SELFTEST FAIL: '):
            failed.add(line[len('SELFTEST FAIL: '):].split(':', 1)[0])
        # Keep every failed row and its detail, so an unexpected old red names its own cause.
        if ('VELDO-0294' in line or 'selftest (PARTIAL,' in line or line.startswith('mutations:')
                or ' detail: ' in line or line.startswith('SELFTEST FAIL: ')):
            if len(deciding) < 150:
                deciding.append(clean(line)[:1000])
    code = process.wait()
    if rows:
        expected = {'VELDO-0294 ' + row for row in rows} | set(extra_red)
        passed = (counts is not None and
                  (code == 1 and failed == expected and counts[1] == len(expected)
                   if red else code == 2 and counts[1] == 0))
    else:
        passed = code == 0
    if check is not None and passed:
        passed = check()
    summary = dict(schema='veldo.proof-summary/v1', command=clean(display or ' '.join(command)),
                   environment=dict(commit=revision, build_commit=head, build_tree=tree,
                                    python=platform.python_version(), host=platform.node()),
                   discarded=[dict(name=name + '.stdout', bytes=size, sha256=digest.hexdigest())],
                   deciding=dict(status='passed' if passed else 'failed', exit_code=code,
                                 counts=counts, failed_rows=sorted(failed), expected_old_red=list(extra_red),
                                 rows=deciding, elapsed_seconds=round(time.monotonic() - start, 3)))
    raw = (json.dumps(summary, indent=2) + '\n').encode()
    if len(raw) > 1000000:
        raise SystemExit('Summary exceeds the proof limit: ' + name)
    (out / (name + '.summary.json')).write_bytes(raw)
    if not passed:
        raise SystemExit('Run failed; inspect ' + name + '.summary.json. No later run started.')

with tempfile.TemporaryDirectory(prefix='red-', dir=out) as directory:
    scratch = Path(directory) / 'base'
    subprocess.run(['git', 'clone', '-q', '--no-hardlinks', '--no-checkout', str(root), str(scratch)], check=True)
    subprocess.run(['git', '-C', str(scratch), 'checkout', '-q', '--detach', '6ee5bb5f'], check=True)
    for suite in suites:
        rel = Path('scripts/suites') / (suite + '.py')
        shutil.copyfile(root / rel, scratch / rel)
    for suite, rows in suites.items():
        # These old assertions now require the new event too. No other old row may fail.
        extra = ['VELDO-0128 ' + row for row in ('registry/declared-set', 'registry/delivery',
                 'sources/real-writers')] if suite.startswith('72_') else []
        run('red-before-' + suite.split('_')[0], ['python3', 'scripts/selftest.py', '--suite', suite],
            scratch, '6ee5bb5f', rows, red=True, extra_red=extra)

for suite, rows in suites.items():
    run('green-after-' + suite.split('_')[0], ['python3', 'scripts/selftest.py', '--suite', suite],
        root, head, rows)
for mutant in mutants:
    run('teeth-' + mutant, ['python3', 'scripts/check_teeth_mutations.py', '--case', mutant, '--jobs', '1',
        '--summary', 'proof/VELDO-0294/teeth-' + mutant + '.receipt.summary.json'],
        root, head)

# Qualification writes many derived files. Run it in a checkout under this proof directory,
# then import only the four permitted resource captures. Changed runtime qualifications
# would require a wider footprint, so stop instead of using them only in the scratch checkout.
resources = sorted((root / 'proof/VELDO-0127').glob('resources-*.json'))
if len(resources) != 4:
    raise SystemExit('Expected four resource captures.')
with tempfile.TemporaryDirectory(prefix='qualification-', dir=out) as directory:
    scratch = Path(directory) / 'tree'
    subprocess.run(['git', 'clone', '-q', '--no-hardlinks', '--no-checkout', str(root), str(scratch)], check=True)
    subprocess.run(['git', '-C', str(scratch), 'checkout', '-q', '--detach', head], check=True)
    def qualified():
        for path in (root / '.veldo/runtime').glob('*.json'):
            other = scratch / path.relative_to(root)
            if not other.is_file() or other.read_bytes() != path.read_bytes():
                return False
        record = json.loads((scratch / 'proof/VELDO-0127/resource-qualification.json').read_text())
        return len(record['cases']) == 4 and all(case['exact_equality'] for case in record['cases'])
    run('resource-qualification', ['python3', '.veldo/qualify.py', '--root', '.',
        '--claude', args['claude'], '--codex', args['codex']], scratch, head,
        display='python3 .veldo/qualify.py --root . --claude <binary> --codex <binary>', check=qualified)
    for path in resources:
        source = scratch / path.relative_to(root)
        raw = source.read_bytes()
        if len(raw) > 1000000 or b'/' + b'home/' in raw:
            raise SystemExit('Resource capture violates the size or path rule: ' + path.name)
        path.write_bytes(raw)
        summary = dict(schema='veldo.proof-summary/v1', command='python3 .veldo/qualify.py in scratch checkout',
                       environment=dict(commit=head), discarded=[],
                       deciding=dict(status='passed', path=path.relative_to(root).as_posix(),
                                     bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        (out / (path.stem + '.summary.json')).write_text(json.dumps(summary, indent=2) + '\n')

live_args = [part for key, value in args.items() for part in ('--' + key.replace('_', '-'), value)]
for engine in ('claude', 'codex'):
    def captured():
        path = root / 'proof/VELDO-0127' / (engine + '-live.json')
        raw = path.read_bytes()
        return len(raw) <= 1000000 and b'/' + b'home/' not in raw and not json.loads(raw)['problems']
    run('live-' + engine, ['python3', 'proof/VELDO-0127/live.py', *live_args, '--only', engine],
        root, head, display='python3 proof/VELDO-0127/live.py <six qualified engine arguments> --only ' + engine,
        check=captured)

run('green-after-86', ['python3', 'scripts/selftest.py', '--suite', '86_veldo_0127_agent_configuration'],
    root, head, rows=['suite86'])
print('VELDO-0294 heavy runs completed. The lead reviews the summaries before updating pending proof.')
PY
