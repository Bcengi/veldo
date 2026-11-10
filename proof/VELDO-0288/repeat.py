"""Run suite 62 twenty times inside host_heavy.sh and retain only small summaries."""
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


summary = {
    'commit': git('rev-parse', 'HEAD'),
    'tree': git('rev-parse', 'HEAD^{tree}'),
    'host': platform.node(),
    'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'command': 'bash $HOST_HEAVY python3 proof/VELDO-0288/repeat.py',
    'suite_command': 'python3 scripts/check_teeth_mutations.py --worker stop288-no-retry',
    'mode': 'baseline; full suite 62 with no mutation',
    'gate': 'not run, as instructed; host load sampled for every run',
    'runs': [],
}
for number in range(1, 21):
    started = time.monotonic()
    load = os.getloadavg()
    run = subprocess.run(COMMAND, cwd=ROOT, text=True, capture_output=True, timeout=240)
    if run.returncode:
        raise SystemExit('suite worker failed with exit %d' % run.returncode)
    result = json.loads(run.stdout)
    targets = {name: [ok for label, ok in result['observations'] if label == 'VELDO-0039 ' + name]
               for name in TARGETS}
    item = dict(run=number, seconds=round(time.monotonic() - started, 3), load_average=load,
                rows=result['count'], failed=result['failed_rows'], targets=targets)
    summary['runs'].append(item)
    print(json.dumps(item), flush=True)
    (ROOT / 'proof/VELDO-0288/repeated.json').write_text(json.dumps(summary, indent=2) + '\n')
    if result['failed_rows'] or any(values != [True] for values in targets.values()):
        raise SystemExit('suite row failed; see repeated.json')
summary['passed'] = {name: sum(run['targets'][name] == [True] for run in summary['runs']) for name in TARGETS}
(ROOT / 'proof/VELDO-0288/repeated.json').write_text(json.dumps(summary, indent=2) + '\n')
