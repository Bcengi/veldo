#!/usr/bin/env python3
"""Single change falsifiers, each driven through only its owning 0124 suite."""
import difflib
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MUTANTS = (
    ('AC1-qualification', 'project_runner_macos_profile.py',
     "or evidence.get('kind') != 'native'", 'or False', '103_veldo_0124_macos', 'AC1/qualification'),
    ('AC1-session-type', 'project_runner_macos_os.py',
     "                    LimitLoadToSessionType='Background',\n", '', '103_veldo_0124_macos',
     'AC1/apple-interfaces'),
    ('AC1-claude-sandbox', 'project_runner_macos_profile.py',
     "if value.get('sandbox', {}).get('enabled', False) is not False:",
     'if False:', '103_veldo_0124_macos', 'AC1/claude-sandbox-refused'),
    ('AC2-deadline', 'project_runner_macos.py',
     "if now >= self.deadline and self.stage in (None, 'cooperative'):",
     "if False and self.stage in (None, 'cooperative'):", '103_veldo_0124_macos', 'AC2/deadline'),
    ('AC2-capacity', 'project_runner_macos.py',
     "if self.status()['pending'] >= p['max_workers']:",
     'if False:', '103_veldo_0124_macos', 'AC2/capacity'),
    ('AC3-parent-only', 'project_runner_macos.py',
     'if self.exit_seen and not members:', 'if self.exit_seen:', '103_veldo_0124_macos', 'AC3/descendant'),
    ('AC3-group-only', 'project_runner_macos.py',
     "            if pid != self.process['pid']:\n                self.os.send(pid, number)",
     "            if False:\n                self.os.send(pid, number)", '103_veldo_0124_macos', 'AC3/descendant'),
    ('AC2-postcall', 'project_runner_macos_control.py',
     "receipt = guard.invoke('macos-call/' + dispatch, dispatch, invocation, RR.boundary(contract),",
     "started.append(self.host.start(request)); receipt = guard.invoke('macos-call/' + dispatch, dispatch, invocation, RR.boundary(contract),",
     '104_veldo_0124_control', 'AC2/precall-caps'),
    ('AC3-unknown-retire', 'project_runner_macos_control.py',
     "if not seen['outcome_known']:", 'if False:', '104_veldo_0124_control', 'AC3/unknown-charge'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE,
                        help='Observation directory; keep earlier rounds intact.')
    output = parser.parse_args().output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    observations = []
    for name, filename, before, after, suite, row in MUTANTS:
        source = (ROOT / '.veldo' / filename).read_text()
        assert source.count(before) == 1, name
        changed = source.replace(before, after)
        patch = ''.join(difflib.unified_diff(source.splitlines(True), changed.splitlines(True),
                                            fromfile='a/' + filename, tofile='b/' + filename))
        (output / (name + '.patch')).write_text(patch)
        with tempfile.TemporaryDirectory(prefix='v124-mutant-') as temporary:
            target = Path(temporary)
            for path in (ROOT / '.veldo').glob('*.py'):
                shutil.copyfile(path, target / path.name)
            (target / filename).write_text(changed)
            log = output / (name + '.log')
            with log.open('w') as stream:
                child = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', suite], cwd=ROOT,
                                       env=dict(os.environ, VELDO_0124_MODULES=str(target), PYTHONDONTWRITEBYTECODE='1'),
                                       stdout=stream, stderr=subprocess.STDOUT, timeout=60)
            marker = 'SELFTEST FAIL: VELDO-0124 ' + row
            killed = child.returncode == 1 and marker in log.read_text()
            observations.append(dict(name=name, suite=suite, row=row, rejected=killed, exit_code=child.returncode,
                                     source_sha256=hashlib.sha256(source.encode()).hexdigest(),
                                     patch=name + '.patch', log=name + '.log'))
            print(name, 'REJECTED' if killed else 'SURVIVED', row)
    (output / 'negative-controls.json').write_text(json.dumps(observations, indent=2) + '\n')
    return 0 if all(o['rejected'] for o in observations) else 1


if __name__ == '__main__':
    sys.exit(main())
