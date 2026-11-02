"""Check the requested proof documents and the owner's untouched boundaries."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
PROOF = ROOT / 'proof/VELDO-0220'
entry = {
    'suite': '113_veldo_0220_gate_host',
    'rows': 'userbus',
    'reason': "systemd user manager: the gate's own scope is created through the user manager and inspected under /sys/fs/cgroup",
}
checks = {'README.md exists': (PROOF / 'README.md').is_file(),
          'OPEN.md exists': (PROOF / 'OPEN.md').is_file()}
if checks['OPEN.md exists']:
    source = (PROOF / 'OPEN.md').read_text()
    checks['exact proposed entry'] = json.loads(source.split('```json\n')[1].split('```')[0]) == entry
    checks['owner work remains explicit'] = 'REMAINING' in source
for relative in ('scripts/gate_unconfined.json',
                 'specs/VELDO-0220-the-gate-holds-the-host-and-runs-in-its-own-scope.md'):
    original = subprocess.check_output(['git', 'show', 'a0760882:' + relative], cwd=ROOT)
    checks[relative + ' unchanged'] = (ROOT / relative).read_bytes() == original
print(json.dumps(checks, indent=2))
raise SystemExit(0 if all(checks.values()) else 1)
