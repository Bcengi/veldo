#!/usr/bin/env python3
"""Isolated negative controls, running only the owning suite, strictly serially."""
import difflib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
CASES = {
    'recorder-requeues': ('control_worker_outbox.py', 'AC3/recorder-failure-no-relaunch',
        "            target = root / '.parked'", "            target = root / '.pending'"),
    'backlog-before-request': ('control_worker.py', 'AC3/new-request-independent-of-backlog',
        '        install_resumer(config_path, config)\n',
        '        install_resumer(config_path, config)\n        resume_pending(config)\n'),
    'recorder-aborts-peers': ('control_worker.py', 'AC3/new-request-independent-of-backlog',
        '                recorder_errors.append(error)', '                raise'),
    'future-orphan-skipped': ('control_worker_outbox.py', 'AC3/future-active-scheduled',
        "            request = json.loads(path.read_text())['request']",
        "            if json.loads(path.read_text())['due'] > time.time():\n                continue\n            request = json.loads(path.read_text())['request']"),
    'receiver-migrates': ('control_worker.py', 'AC2/receiver-never-migrates-history',
        "    host = M.Supervisor(config['profile'], config['qualification'], migrate=False)",
        "    host = M.Supervisor(config['profile'], config['qualification'])"),
    'stop-ignores-runtime': ('project_runner_macos.py', 'AC3/cooperative-stop-runtime-bound',
        "                until = (min(self.due, self.deadline) if self.stage == 'cooperative'\n                         else self.due if self.stage else self.deadline)",
        '                until = self.due if self.stage else self.deadline'),
    'runtime-detection-late': ('project_runner_macos.py', 'AC3/stalled-wrapper-event-or-runtime-cap',
        '                         else self.due if self.stage else self.deadline)',
        '                         else self.due if self.stage else self.deadline + .1)'),
    'dead-heartbeat-required': ('project_runner_macos_profile.py', 'AC2/profile-v2-no-heartbeat-fields',
        "        'startup_seconds')", "        'startup_seconds', 'heartbeat_window_seconds')"),
    'profile-version-unchanged': ('project_runner_macos_profile.py', 'AC2/profile-v2-no-heartbeat-fields',
        "SCHEMA = 'veldo.macos_worker_profile/v2'", "SCHEMA = 'veldo.macos_worker_profile/v1'"),
    'watch-allocation-unprotected': ('project_runner_macos_os.py', 'AC3/exit-watch-init-closes-resources',
        '        try:\n            self.reader, self.writer = os.pipe()\n            os.set_blocking(self.reader, False)\n            os.set_blocking(self.writer, False)\n',
        '        self.reader, self.writer = os.pipe()\n        os.set_blocking(self.reader, False)\n        os.set_blocking(self.writer, False)\n        try:\n'),
    'wake-close-race': ('project_runner_macos_os.py', 'AC3/exit-watch-close-serializes-wake',
        '        # The lifetime lock covers the write, so close cannot recycle its fd.\n        with self.lock:',
        "        # Mutant: wake no longer owns the descriptor lifetime.\n        with __import__('contextlib').nullcontext():"),
    'stop-rereads-cleared-watch': ('project_runner_macos.py', 'AC3/stop-captures-watch-lifetime',
        '            watch = self.watch\n            if watch is not None:\n                with contextlib.suppress(OSError):\n                    self.os.wake(watch)',
        '            if self.watch is not None:\n                with contextlib.suppress(OSError):\n                    self.os.wake(self.watch)'),
    'correction-claims-partial': ('routing-correction.json', 'AC1/round11-log-correction-and-original-row',
        '"complete": true', '"complete": false'),
}


def main():
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for name, (filename, row, before, after) in CASES.items():
        correction = filename.endswith('.json')
        source_path = ROOT / ('proof/VELDO-0125/b2-round12' if correction else '.veldo') / filename
        source = source_path.read_text()
        assert source.count(before) == 1, (name, source.count(before))
        mutant = source.replace(before, after)
        (output / (name + '.diff')).write_text(''.join(difflib.unified_diff(
            source.splitlines(True), mutant.splitlines(True), fromfile=filename, tofile=filename)))
        with tempfile.TemporaryDirectory(prefix='v125-r12-mutant-') as directory:
            modules = Path(directory) / '.veldo'
            shutil.copytree(ROOT / '.veldo', modules, ignore=shutil.ignore_patterns('__pycache__', 'tmp-*'))
            (modules / filename).write_text(mutant)
            override = {'VELDO_0125_CORRECTION_OVERRIDE': str(modules / filename)} if correction else {}
            log = output / (name + '.log')
            with log.open('w') as stream:
                result = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', '106_veldo_0125_routing'],
                    cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=300,
                    env=dict(os.environ, VELDO_0125_MODULES=str(modules), VELDO_0124_MODULES=str(modules), **override))
        rejected = result.returncode == 1 and 'SELFTEST FAIL: VELDO-0125 ' + row in log.read_text()
        results.append(dict(case=name, row=row, rejected=rejected, returncode=result.returncode,
            source_sha256=hashlib.sha256(source.encode()).hexdigest(), patch=name + '.diff', log=name + '.log'))
        (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(name + ': ' + ('rejected by ' + row if rejected else 'SURVIVED'), flush=True)
    return 0 if all(result['rejected'] for result in results) else 1


if __name__ == '__main__':
    sys.exit(main())
