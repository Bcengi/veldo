"""Run suite 62 twenty times while a full gate runs on this host; retain only small summaries.

The caller starts the gate and passes its PID in V0288_GATE_PID. This script never starts a gate
and never takes the host lock. Exit 0: all 20 runs passed with the gate alive. Exit 1: a suite run
failed. Exit 2: no live gate at the start, or the gate ended before the 20 runs finished.
"""
import datetime
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
COMMAND = [sys.executable, 'scripts/check_teeth_mutations.py', '--worker', 'stop288-no-retry']
TARGETS = ['dispatch/stop-during-exit', 'dispatch/stop-during-natural-end', 'dispatch/stop-during-accept-run']


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def gate_alive(pid):
    """True when signal 0 reaches the gate process and it is not an unreaped zombie."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        stat = Path('/proc/%d/stat' % pid).read_text()
    except OSError:
        return False
    return stat.rsplit(')', 1)[1].split()[0] != 'Z'


def save(summary):
    (ROOT / 'proof/VELDO-0288/repeated.json').write_text(json.dumps(summary, indent=2) + '\n')


def gate_ended(summary, message):
    summary['gate_ended'] = message
    save(summary)
    print(message, file=sys.stderr)
    raise SystemExit(2)


raw_pid = os.environ.get('V0288_GATE_PID', '')
if not raw_pid.isdigit() or int(raw_pid) < 2:
    print('V0288_GATE_PID is unset or not a process id; refusing to start', file=sys.stderr)
    raise SystemExit(2)
GATE_PID = int(raw_pid)
if not gate_alive(GATE_PID):
    print('gate process %d is not alive; refusing to start' % GATE_PID, file=sys.stderr)
    raise SystemExit(2)


commit = git('rev-parse', 'HEAD')
summary = {
    'commit': commit,
    'tree': git('rev-parse', 'HEAD^{tree}'),
    'host': platform.node(),
    'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': ('lock-queue job, W is the worktree and G a fresh temporary directory: '
                'git clone -q $W $G/veldo; '
                '(cd $G/veldo && exec bash scripts/verify.sh) > $G/gate.log 2>&1 & GATE=$!; '
                'sleep 600; V0288_GATE_PID=$GATE python3 proof/VELDO-0288/repeat.py; wait $GATE'),
    'suite_command': 'python3 scripts/check_teeth_mutations.py --worker stop288-no-retry',
    'mode': 'baseline; full suite 62 with no mutation',
    'gate': 'concurrent full gate, verify.sh in a clone of %s' % commit,
    'gate_pid': GATE_PID,
    'runs': [],
}
for number in range(1, 21):
    alive = gate_alive(GATE_PID)
    if not alive:
        gate_ended(summary, 'gate ended before run %d' % number)
    started = time.monotonic()
    load = os.getloadavg()
    run = subprocess.run(COMMAND, cwd=ROOT, text=True, capture_output=True, timeout=240)
    if run.returncode:
        raise SystemExit('suite worker failed with exit %d' % run.returncode)
    result = json.loads(run.stdout)
    targets = {name: [ok for label, ok in result['observations'] if label == 'VELDO-0039 ' + name]
               for name in TARGETS}
    item = dict(run=number, gate_alive=alive, gate_alive_after=gate_alive(GATE_PID),
                seconds=round(time.monotonic() - started, 3), load_average=load,
                rows=result['count'], failed=result['failed_rows'], targets=targets)
    summary['runs'].append(item)
    print(json.dumps(item), flush=True)
    save(summary)
    if result['failed_rows'] or any(values != [True] for values in targets.values()):
        raise SystemExit('suite row failed; see repeated.json')
    if not item['gate_alive_after']:
        gate_ended(summary, 'gate ended during run %d' % number)
summary['passed'] = {name: sum(run['targets'][name] == [True] for run in summary['runs']) for name in TARGETS}
summary['gate_alive_runs'] = sum(run['gate_alive'] and run['gate_alive_after'] for run in summary['runs'])
save(summary)
