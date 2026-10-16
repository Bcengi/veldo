#!/usr/bin/env python3
"""Single-defect negative controls, confined to VELDO-0125's routing suite."""
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
    'retirement-order': ('control_worker.py', 'AC3/stored-release-restart',
        "        host.release_authority(binding['dispatch_id'], binding['contract_digest'], outcome)",
        "        client.retired(binding)\n        host.release_authority(binding['dispatch_id'], binding['contract_digest'], outcome)"),
    'release-skips-outbox': ('control_worker.py', 'AC3/release-flushes-saved-usage',
        '    if evidence.exists():', "    if evidence.exists() and request.get('action') != 'release':"),
    'usage-unwired': ('control_worker.py', 'AC3/default-collector-retains-files',
        "return engine_usage(started, engine), {'output':", "return None, {'output':"),
    'retry-eight': ('control_worker_client.py', 'AC3/result-retry-backoff',
        '        while True:', '        for attempt in range(8):'),
    'startup-history': ('control_worker_service.py', 'AC3/host-release-replay-and-restart',
        '''        for row in conn.execute("SELECT data FROM entities INDEXED BY worker_release_pending "
                "WHERE kind='worker_observation' AND json_extract(data, '$.release_state')='pending'"):''',
        '''        for row in conn.execute("SELECT data FROM entities WHERE kind='worker_observation'"):'''),
    'early-release-refused': ('project_runner_macos.py', 'AC3/release-before-start',
        '            if slot is None:\n                # A release may beat bootstrap.',
        "            if slot is None:\n                raise P.Refused('missing_evidence:slot')\n                # A release may beat bootstrap."),
    'startup-no-drain': ('control_worker.py', 'AC3/delivery-launch-agent',
        '            resume_pending(config)\n            time.sleep(30)',
        '            time.sleep(30)'),
    'repeat-release-wake': ('control_worker_service.py', 'AC3/release-wakes-bounded-once',
        '            if dispatch in self.release_sent:', '            if False:'),
}


def main():
    output = Path(sys.argv[1])
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for name, (filename, row, before, after) in CASES.items():
        source = (ROOT / '.veldo' / filename).read_text()
        assert source.count(before) == 1, name
        mutant = source.replace(before, after)
        patch = ''.join(difflib.unified_diff(source.splitlines(True), mutant.splitlines(True),
                                           fromfile=filename, tofile=filename, n=0))
        (output / (name + '.diff')).write_text(patch)
        with tempfile.TemporaryDirectory(prefix='v125-delivery-mutant-') as directory:
            modules = Path(directory) / '.veldo'
            shutil.copytree(ROOT / '.veldo', modules, ignore=shutil.ignore_patterns('__pycache__', 'tmp-*'))
            (modules / filename).write_text(mutant)
            log = output / (name + '.log')
            with log.open('w') as stream:
                result = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', '106_veldo_0125_routing'],
                    cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=180,
                    env=dict(os.environ, VELDO_0125_MODULES=str(modules), VELDO_0124_MODULES=str(modules)))
        log.write_text('\n'.join(line.rstrip() for line in log.read_text().splitlines()) + '\n')
        rejected = result.returncode == 1 and 'SELFTEST FAIL: VELDO-0125 ' + row in log.read_text()
        results.append(dict(case=name, row=row, rejected=rejected, returncode=result.returncode,
            source_sha256=hashlib.sha256(source.encode()).hexdigest(), patch=name + '.diff', log=name + '.log'))
        (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(name + ': ' + ('rejected by ' + row if rejected else 'SURVIVED'), flush=True)
    return 0 if all(r['rejected'] for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())
