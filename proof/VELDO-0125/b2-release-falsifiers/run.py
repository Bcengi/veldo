"""Run one review falsifier against both copies, restoring them even on failure.

Only the named VELDO-0125 suite runs. This is targeted regression evidence,
not the canonical gate, a proof manifest, or independent approval.
"""
import difflib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CASES = {
    'local-slot-retirement': ('project_runner_macos.py',
        "write(path, dict(slot, state='retired', authority_release=outcome))",
        'pass  # falsifier: leak the local slot', 'AC2/actual-worker-launch'),
    'operator-notification': ('control_worker_service.py',
        "self.notify_release(repository, answer['binding'])",
        'pass  # falsifier: no Mac release notification', 'AC3/empty-collector-preserves-files'),
    'authority-restart': ('control_worker_service.py',
        "self.notify_release(data['repository_uuid'], data)",
        'pass  # falsifier: forget durable releases on restart', 'AC3/host-release-replay-and-restart'),
    'stored-outcome': ('control_worker.py',
        "if outcome.get('host_released'):\n                apply_release(host, retained['binding'], outcome)",
        "if outcome.get('host_released'):\n                pass  # falsifier: ignore stored release",
        'AC3/stored-release-restart'),
    'late-usage': ('control_worker_service.py',
        "if (usage is not None and usage != data.get('usage')) or (\n                        not data.get('spend_receipt') and cleanup is not None):",
        "if not data.get('spend_receipt') and (usage is not None or cleanup is not None):",
        'AC3/late-usage-amends-spend'),
    'temporary-deliverables': ('control_worker.py',
        "(('clone', clone), ('scratch', scratch), ('tmp', started.temp))",
        "(('clone', clone), ('scratch', scratch))", 'AC3/default-collector-retains-files'),
    'replay-wake': ('control_worker_service.py',
        'released=host_released, host_released=host_released)',
        'released=False, host_released=host_released)', 'AC3/host-release-replay-and-restart'),
    'retry-backoff': ('control_worker_client.py',
        'delay = min(self.retry_max_seconds, self.retry_seconds * 2 ** attempt)',
        'delay = self.retry_seconds', 'AC3/result-retry-backoff'),
    'retry-limit': ('control_worker_client.py',
        'if attempt + 1 == self.retry_attempts:',
        'if attempt + 1 == self.retry_attempts - 1:', 'AC3/result-retry-backoff'),
}


def main(name):
    filename, before, after, row = CASES[name]
    paths = [ROOT / prefix / filename for prefix in ('engine/.veldo', '.veldo')]
    originals = {path: path.read_text() for path in paths}
    assert len(set(originals.values())) == 1, 'mirrors differ before mutation'
    assert all(text.count(before) == 1 for text in originals.values()), 'mutation target not unique'
    patch = []
    for path, text in originals.items():
        changed = text.replace(before, after, 1)
        relative = str(path.relative_to(ROOT))
        patch.extend(difflib.unified_diff(text.splitlines(True), changed.splitlines(True),
                                         'a/' + relative, 'b/' + relative))
    (HERE / (name + '.diff')).write_text(''.join(patch))
    command = ['python3', 'scripts/selftest.py', '--suite', '106_veldo_0125_routing']
    log_path = HERE / (name + '.log')
    try:
        for path, text in originals.items():
            path.write_text(text.replace(before, after, 1))
        with log_path.open('w') as log:
            result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=300)
    finally:
        for path, text in originals.items():
            path.write_text(text)
    lines = log_path.read_text().splitlines()
    selected = [line for line in lines if 'SELFTEST FAIL:' in line or
                line.startswith('selftest (PARTIAL') or line.startswith(row + ':')]
    (HERE / (name + '.txt')).write_text('command: ' + ' '.join(command) + '\nexit: ' +
                                      str(result.returncode) + '\n' + '\n'.join(selected) + '\n')
    caught = result.returncode == 1 and any('SELFTEST FAIL: VELDO-0125 ' + row in line for line in lines)
    print(json.dumps(dict(mutation=name, caught=caught, exit=result.returncode, row=row)), flush=True)
    return 0 if caught else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1]))
