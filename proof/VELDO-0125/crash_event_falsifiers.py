#!/usr/bin/env python3
"""Round 11 serial falsifiers. Each subprocess runs only the owning suite."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import lifecycle_falsifiers as previous

ROOT = Path(__file__).resolve().parents[2]
CASES = dict(previous.CASES)
CASES.pop('healthy-run-enqueued')
CASES.update({
    'active-receiver-left-pending': ('control_worker.py', 'AC3/active-receiver-no-timer',
        "            acquired = True\n            OUT.move(root, OUT.locate(root, request['dispatch_id']), '.active', CL.durable_json)",
        "            acquired = True\n            OUT.move(root, OUT.locate(root, request['dispatch_id']), '.pending', CL.durable_json)"),
    'lock-error-unrecorded': ('control_worker.py', 'AC3/lock-errors-bounded-recorded',
        '            OUT.failure(config, request, error, CL.durable_json)\n',
        '            if not isinstance(error, PermissionError):\n                OUT.failure(config, request, error, CL.durable_json)\n'),
    'slot-reconciliation-removed': ('project_runner_macos.py', 'AC2/slot-crash-2-after-restart',
        '        indexed = self.live_slots()\n', '        return self.live_slots()\n        indexed = self.live_slots()\n'),
    'retired-slot-stays-live': ('project_runner_macos.py', 'AC2/retirement-crash-False-False-False',
        "            if slot and slot['state'] != 'retired':\n", "            if slot:\n"),
    'migration-deferred-to-admission': ('project_runner_macos.py', 'AC2/upgrade-migrates-before-admission',
        '        self.initialize_slots()\n', '        # Migration omitted from startup.\n'),
    'active-start-recovery-removed': ('control_worker.py', 'AC3/receiver-crash-start-event',
        '        resume_pending(config)  # Worker-start event replays orphaned active owners.\n', ''),
    'recorder-error-swallowed': ('control_worker.py', 'AC3/recorder-failure-stops-drain',
        '            except RecorderFailure:\n                raise\n', ''),
    'supervisor-exit-polling': ('project_runner_macos.py', 'AC3/supervisor-blocking-exit',
        '                    self.exit_seen = self.os.exited(self.watch, seconds)\n',
        '                    self.os.sleep(0.02)\n'),
    'startup-ready-polling': ('project_runner_macos.py', 'AC3/startup-ready-event',
        "                    self.os.wait_file(directory / 'ready.json', until - self.os.monotonic())\n",
        '                    self.os.sleep(0.02)\n'),
    'wrapper-go-polling': ('project_runner_macos_wrapper.py', 'AC3/wrapper-blocking-exit',
        "    if not wait_file(directory / 'go', request['startup_seconds']):\n",
        "    if not (directory / 'go').exists():\n"),
    'wrapper-child-polling': ('project_runner_macos_wrapper.py', 'AC3/wrapper-blocking-exit',
        '            child.wait()  # Blocking waitpid, with no subprocess timeout polling.\n',
        "            child.wait(timeout=request['heartbeat_seconds'])\n"),
    'evidence-release-guard-removed': ('control_worker.py', 'AC3/evidence-release-awaits-authorization',
        "            if not outcome.get('host_released'):\n                raise OUT.WaitingForRelease('release_not_yet_authorized')\n",
        ''),
})


def main():
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for name, (filename, row, before, after) in CASES.items():
        source = (ROOT / '.veldo' / filename).read_text()
        assert source.count(before) == 1, (name, source.count(before))
        mutant = source.replace(before, after)
        (output / (name + '.diff')).write_text(''.join(difflib.unified_diff(
            source.splitlines(True), mutant.splitlines(True), fromfile=filename, tofile=filename, n=3)))
        with tempfile.TemporaryDirectory(prefix='v125-r11-mutant-') as directory:
            modules = Path(directory) / '.veldo'
            shutil.copytree(ROOT / '.veldo', modules, ignore=shutil.ignore_patterns('__pycache__', 'tmp-*'))
            (modules / filename).write_text(mutant)
            log = output / (name + '.log')
            with log.open('w') as stream:
                result = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', '106_veldo_0125_routing'],
                    cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=300,
                    env=dict(os.environ, VELDO_0125_MODULES=str(modules), VELDO_0124_MODULES=str(modules)))
        rejected = result.returncode == 1 and 'SELFTEST FAIL: VELDO-0125 ' + row in log.read_text()
        results.append(dict(case=name, row=row, rejected=rejected, returncode=result.returncode,
            source_sha256=hashlib.sha256(source.encode()).hexdigest(), patch=name + '.diff', log=name + '.log'))
        (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(name + ': ' + ('rejected by ' + row if rejected else 'SURVIVED'), flush=True)
    return 0 if all(result['rejected'] for result in results) else 1


if __name__ == '__main__':
    sys.exit(main())
