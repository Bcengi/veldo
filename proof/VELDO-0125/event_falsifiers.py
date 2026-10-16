#!/usr/bin/env python3
"""Isolated single-defect controls; run only the 0125 routing suite, serially."""
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
    'idle-polling': ('control_worker.py', 'AC3/event-index-idle-and-history',
        '        resume_pending(config, drain=True)',
        '        while True:\n            resume_pending(config, drain=True)\n            time.sleep(30)'),
    'mac-history-scan': ('control_worker_outbox.py', 'AC3/event-index-idle-and-history',
        "        return [json.loads(path.read_text()) for path in sorted(pending.glob('*.json'))]",
        "        list(root.iterdir())\n        return [json.loads(path.read_text()) for path in sorted(pending.glob('*.json'))]"),
    'dispatch-aborts-pass': ('control_worker.py', 'AC3/event-dispatch-error-isolation',
        '                pass  # receive durably records/parks this dispatch; drain its peers.',
        '                raise  # defect: one refusal aborts the remaining deliveries'),
    'permanent-refusal-retried': ('control_worker_outbox.py', 'AC3/event-dispatch-error-isolation',
        "    transient = isinstance(error, (OSError, TimeoutError)) or reason.startswith('AUTHORITY_UNAVAILABLE:')",
        '    transient = True'),
    'ssh-failure-marked-sent': ('control_worker_service.py', 'AC3/failed-release-wake-retry',
        '                if result.returncode == 0:', '                if True:'),
    'ssh-timeout-marked-sent': ('control_worker_service.py', 'AC3/failed-release-wake-retry',
        '                reason = type(error).__name__', '                continue'),
    'unknown-usage-discarded': ('control_worker_service.py', 'AC3/unknown-measured-usage-once',
        "                    data['invocation'], sequence, usage or data.get('usage') or {}, final=True, now=now)",
        "                    data['invocation'], sequence, {}, final=True, now=now)"),
    'crash-output-unread': ('control_worker.py', 'AC3/crash-before-evidence-usage',
        '        retain_crashed_output(host, client, request, directory)',
        '        pass  # defect: release without reading retained wrapper output'),
    'busy-release-forgotten': ('control_worker.py', 'AC3/busy-release-durable-event',
        "        except BlockingIOError:\n            if not queued:\n                OUT.enqueue(config, request, CL.durable_json)",
        '        except BlockingIOError:\n            pass'),
    'acknowledgement-not-dequeued': ('control_worker_outbox.py', 'AC3/event-index-idle-and-history',
        'def acknowledge(config, dispatch, *, release=False):\n',
        'def acknowledge(config, dispatch, *, release=False):\n    return\n'),
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
        with tempfile.TemporaryDirectory(prefix='v125-event-mutant-') as directory:
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
