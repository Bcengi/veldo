#!/usr/bin/env python3
"""Round 10 isolated negative controls; only the owning routing suite, serially."""
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
    'healthy-run-enqueued': ('control_worker.py', 'AC3/active-receiver-no-timer',
        "                    OUT.move(root, path, '.active', CL.durable_json,",
        "                    OUT.move(root, path, '.pending', CL.durable_json,"),
    'operator-status-polling': ('control_worker.py', 'AC3/operator-wait-no-status-timer',
        "        raise OUT.WaitingForRelease('release_not_yet_authorized')\n    observation",
        "        raise OSError('release_not_yet_authorized')\n    observation"),
    'unattempted-release-parked': ('control_worker_outbox.py', 'AC3/upgraded-release-attempted',
        '        if upgraded:\n', '        if False:\n'),
    'status-dequeues-result': ('control_worker.py', 'AC3/status-is-not-result-ack',
        "        if not outcome.get('host_released'):\n            raise OUT.WaitingForRelease('release_not_yet_authorized')\n",
        ''),
    'original-replay-drops-output': ('control_worker.py', 'AC3/original-replay-retains-usage',
        "    if not evidence.exists() and (directory_existed or request.get('action') in ('release', 'resume')):",
        "    if not evidence.exists() and request.get('action') in ('release', 'resume'):"),
    'lock-error-unrecorded': ('control_worker.py', 'AC3/lock-errors-bounded-recorded',
        '        OUT.failure(config, request, error, CL.durable_json)\n',
        '        if not isinstance(error, PermissionError):\n            OUT.failure(config, request, error, CL.durable_json)\n'),
    'admission-scans-history': ('project_runner_macos.py', 'AC2/live-slot-admission-index',
        '        states = self.live_slots().values()',
        "        states = [read(p)['state'] for p in self.root.glob('*/slot.json') if read(p)['state'] != 'retired']"),
    'park-parent-unsynced': ('control_worker_outbox.py', 'AC3/park-parent-durable',
        '    # Persist the new directory name before removing the old recovery record.\n',
        "    if state == '.parked':\n        target = destination / path.name\n        write(target, entry or json.loads(path.read_text()))\n        sync_remove(path)\n        return target\n"
        '    # Persist the new directory name before removing the old recovery record.\n'),
    'release-skipped-after-result-refusal': ('control_worker.py', 'AC3/upgraded-release-attempted',
        "            CL.durable_json(directory / 'result-refusal.json', dict(reason=reason))\n",
        "            raise error\n            CL.durable_json(directory / 'result-refusal.json', dict(reason=reason))\n"),
}


def main():
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for name, (filename, row, before, after) in CASES.items():
        source = (ROOT / '.veldo' / filename).read_text()
        assert source.count(before) == 1, name
        mutant = source.replace(before, after)
        (output / (name + '.diff')).write_text(''.join(difflib.unified_diff(
            source.splitlines(True), mutant.splitlines(True), fromfile=filename, tofile=filename, n=0)))
        with tempfile.TemporaryDirectory(prefix='v125-lifecycle-mutant-') as directory:
            modules = Path(directory) / '.veldo'
            shutil.copytree(ROOT / '.veldo', modules, ignore=shutil.ignore_patterns('__pycache__', 'tmp-*'))
            (modules / filename).write_text(mutant)
            log = output / (name + '.log')
            with log.open('w') as stream:
                result = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', '106_veldo_0125_routing'],
                    cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=180,
                    env=dict(os.environ, VELDO_0125_MODULES=str(modules), VELDO_0124_MODULES=str(modules)))
        rejected = result.returncode == 1 and 'SELFTEST FAIL: VELDO-0125 ' + row in log.read_text()
        results.append(dict(case=name, row=row, rejected=rejected, returncode=result.returncode,
            source_sha256=hashlib.sha256(source.encode()).hexdigest(), patch=name + '.diff', log=name + '.log'))
        (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(name + ': ' + ('rejected by ' + row if rejected else 'SURVIVED'), flush=True)
    return 0 if all(result['rejected'] for result in results) else 1


if __name__ == '__main__':
    sys.exit(main())
