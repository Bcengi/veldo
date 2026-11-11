#!/bin/bash
# The lead queues this script while holding the host gate lock. It never takes the lock.
# Run once from any directory. A red stops the script. AC2 cannot be retried by this script.
exec python3 - "$0" "$@" <<'PY'
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time

script = Path(sys.argv[1]).resolve()
root = script.parents[2]
out = script.parent
suite_file = 'scripts/suites/112_veldo_0215_case_deadlines.py'
row = 'VELDO-0293: case-deadlines/unmeasured-mutant-floor'
scope = ['systemd-run', '--user', '--scope', '-p', 'MemoryMax=10G']

if len(sys.argv) > 2:
    if sys.argv[2] != 'mutation-worker':
        raise SystemExit('Unknown mode')
    # Exercise the teeth CLI with its normal coordinator and worker isolation. Only the
    # timing reader uses an empty scratch store. No owner samples are removed or written.
    spec = importlib.util.spec_from_file_location('teeth293', root / 'scripts/check_teeth_mutations.py')
    teeth = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(teeth)
    coordinator = teeth._coordinator()
    empty = Path(sys.argv[3])
    if list(empty.iterdir()):
        raise SystemExit('Timing store must be empty')
    coordinator.case_deadlines.__defaults__ = (empty,)
    teeth._coordinator = lambda: coordinator
    names = sys.argv[4:]
    os.environ['VELDO_GATE_FORCE_FRESH'] = '1'
    sys.argv = ['scripts/check_teeth_mutations.py', '--jobs', '1']
    for name in names:
        sys.argv.extend(['--case', name])
    raise SystemExit(teeth.main())


def git(where, *args):
    return subprocess.check_output(['git', '-C', str(where), *args], text=True).strip()


def summary(name, command, deciding, where=root, raw=b'', copied=None, exclusive=False):
    document = dict(schema='veldo.proof-summary/v1', command=command,
                    environment=dict(commit=git(where, 'rev-parse', 'HEAD'),
                                     tree=git(where, 'rev-parse', 'HEAD^{tree}'),
                                     python=platform.python_version(), host=platform.node(),
                                     load=list(os.getloadavg())),
                    deciding=deciding, discarded=[])
    if copied:
        document['environment']['copied_files_sha256'] = copied
    if raw:
        document['discarded'] = [dict(name=name + '.stdout', bytes=len(raw),
                                      sha256=hashlib.sha256(raw).hexdigest())]
    body = json.dumps(document, indent=2, sort_keys=True) + '\n'
    if len(body.encode()) >= 1000000:
        raise SystemExit('Summary exceeds 1 MB')
    with (out / name).open('x' if exclusive else 'w') as target:
        target.write(body)


def run(command, where, work, label):
    log = work / (label + '.log')
    started = time.monotonic()
    with log.open('wb') as stream:
        result = subprocess.run(command, cwd=where, stdout=stream, stderr=subprocess.STDOUT)
    raw = log.read_bytes()
    log.unlink()
    return result.returncode, raw, round(time.monotonic() - started, 3)


def suite(where, name, output, work, red=False):
    command = scope + ['python3', 'scripts/selftest.py', '--suite', name]
    rc, raw, elapsed = run(command, where, work, output)
    text = raw.decode(errors='replace')
    counts = re.findall(r'selftest \(PARTIAL[^\n]*\): (\d+) passed, (\d+) failed', text)
    failures = re.findall(r'SELFTEST FAIL: ([^\n]+)', text)
    observations = [json.loads(line.split(': ', 1)[1]) for line in text.splitlines()
                    if line.startswith('VELDO-0293: {')]
    expected = [row] if red else []
    ok = bool(counts) and rc == (1 if red else 2) and failures == expected and int(counts[-1][1]) == len(expected)
    if name == '112_veldo_0215_case_deadlines':
        ok = ok and len(observations) == 1
        if observations:
            seen = observations[0]
            ok = ok and (seen.get('error') == 'mutation_budget_exceeded'
                         and seen.get('mutant_budget') == 120 if red else
                         seen.get('status') == 'passed' and seen.get('mutant_budget') == 360
                         and seen.get('mutant_elapsed') == 150 and seen.get('noop_budget', 0) >= 360)
    summary(output, ' '.join(command), dict(verdict='pass' if ok else 'fail',
            exit_status=rc, elapsed_seconds=elapsed, expected_red=expected, failed_rows=failures,
            rows_passed=int(counts[-1][0]) if counts else None,
            rows_failed=int(counts[-1][1]) if counts else None, floor_row=observations,
            scope='Partial suite only; no gate or landing claim'), where, raw,
            {suite_file: hashlib.sha256((root / suite_file).read_bytes()).hexdigest()} if red else None)
    print(output + ': ' + ('pass' if ok else 'FAIL'), flush=True)
    if not ok:
        raise SystemExit('Suite result was unexpected; report it to the lead')


def mutations(names, output, work, measurement=False):
    empty = work / (output + '.times')
    empty.mkdir()
    command = scope + ['bash', str(script), 'mutation-worker', str(empty), *names]
    display = ' '.join(scope + ['bash', 'proof/VELDO-0293/heavy_runs.sh',
                               'mutation-worker', '<empty-scratch-store>', *names])
    if measurement:
        # Persist the attempt before starting. A crash or red cannot silently become a retry.
        summary(output, display, dict(status='started', verdict='pending', cases=names), exclusive=True)
    rc, raw, elapsed = run(command, root, work, output)
    receipts = []
    for line in raw.decode(errors='replace').splitlines():
        if line.startswith('{'):
            try:
                value = json.loads(line)
                if value.get('schema') == 'veldo.mutation-stage/v1':
                    receipts.append(value)
            except ValueError:
                pass
    receipt = receipts[-1] if receipts else {}
    killed = {r['case']['name'] for r in receipt.get('results', [])}
    rows = []
    identities = {'check_teeth_mutations.py:' + name for name in names}
    for name in names:
        identity = 'check_teeth_mutations.py:' + name
        worker = next((w for w in receipt.get('worker_outcomes', [])
                       if w.get('name') == identity and w.get('mode') == 'mutant'), {})
        rows.append(dict(case=name, expected='killed', observed='killed' if name in killed else
                         worker.get('error', receipt.get('error', 'not_judged')),
                         elapsed_seconds=worker.get('elapsed'), budget_seconds=worker.get('budget_seconds')))
    ok = (rc == 0 and receipt.get('status') == 'passed' and killed == set(names)
          and receipt.get('reused') == 0 and receipt.get('executed') == len(names)
          and set(receipt.get('unmeasured_cases', [])) == identities)
    if measurement:
        ok = ok and all(isinstance(r['elapsed_seconds'], (int, float))
                        and 0 < r['elapsed_seconds'] < 360 for r in rows)
    summary(output, display, dict(verdict='pass' if ok else 'fail', exit_status=rc,
            elapsed_seconds=elapsed, rows=rows, unmeasured_cases=receipt.get('unmeasured_cases'),
            stage_status=receipt.get('status'), error=receipt.get('error'),
            reused=receipt.get('reused'), executed=receipt.get('executed'),
            case_time_store='empty scratch directory; owner store untouched'), raw=raw)
    print(output + ': ' + ('pass' if ok else 'FAIL'), flush=True)
    if not ok:
        raise SystemExit('Mutation result was red; it stands and must go to the lead')


if (out / 'ac2-measurement.summary.json').exists():
    raise SystemExit('AC2 was already attempted; do not repeat it')
with tempfile.TemporaryDirectory(prefix='veldo293-heavy-') as temporary:
    work = Path(temporary)
    before = work / 'before'
    subprocess.run(['git', 'clone', '--quiet', '--no-hardlinks', str(root), str(before)], check=True)
    subprocess.run(['git', '-C', str(before), 'checkout', '--quiet', '--detach', '6ee5bb5f'], check=True)
    shutil.copyfile(root / suite_file, before / suite_file)
    suite(before, '112_veldo_0215_case_deadlines', 'red-before.summary.json', work, red=True)
    suite(root, '112_veldo_0215_case_deadlines', 'green-112.summary.json', work)
    suite(root, '62_veldo_0039_dispatch', 'green-62.summary.json', work)
    mutations(['floor293-removed'], 'teeth.summary.json', work)
    mutations(['dispatch-receiver-store-only-gate', 'dispatch-spawn-before-contract'],
              'ac2-measurement.summary.json', work, measurement=True)
PY
