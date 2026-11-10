"""Retake the four resource records and the authorized Codex capture after the code is final."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
engines = json.loads((ROOT / '.veldo/runtime/engines.json').read_text())
binaries = {name: str(Path(engines[name]['binary']).expanduser()) for name in ('codex', 'claude_code')}
env = dict(os.environ, CODEX_HOME=str(Path.home() / '.codex2'))
commands = [
    [sys.executable, '.veldo/qualify.py', '--codex', binaries['codex'], '--claude', binaries['claude_code']],
    [sys.executable, 'proof/VELDO-0127/live.py', '--only', 'codex',
     '--codex', binaries['codex'], '--claude', binaries['claude_code'],
     '--codex-profile', env['CODEX_HOME'], '--claude-profile', str(Path.home() / '.claude'),
     '--codex-model', 'gpt-6-astra', '--claude-model', 'claude-haiku-4-5-20251001'],
]
summary = {'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
           'commands': ['python3 .veldo/qualify.py with the pinned binaries in runtime/engines.json',
                        'CODEX_HOME=$CODEX2_PROFILE python3 proof/VELDO-0127/live.py --only codex '
                        'with the pinned binaries and the existing capture models'],
           'results': []}
for index, command in enumerate(commands):
    print('Capturing ' + ('resources' if index == 0 else 'codex live'), flush=True)
    run = subprocess.run(command, cwd=ROOT, env=env, text=True, capture_output=True, timeout=1800)
    # Store summaries, never the driver's raw output or login paths.
    summary['results'].append({'capture': 'resources' if index == 0 else 'codex-live', 'exit': run.returncode,
                               'output_sha256': hashlib.sha256((run.stdout + run.stderr).encode()).hexdigest()})
    (ROOT / 'proof/VELDO-0288/captures.json').write_text(json.dumps(summary, indent=2) + '\n')
    if run.returncode:
        print((run.stdout + run.stderr).replace(str(Path.home()), '$HOME')[-6000:], flush=True)
        raise SystemExit(run.returncode)
paths = sorted((ROOT / 'proof/VELDO-0127').glob('resources-*.json'))
paths.append(ROOT / 'proof/VELDO-0127/codex-live.json')
summary['records'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
summary['codex_problems'] = json.loads(paths[-1].read_text()).get('problems')
summary['claude'] = 'not retaken; reserved for the lead'
(ROOT / 'proof/VELDO-0288/captures.json').write_text(json.dumps(summary, indent=2) + '\n')
if summary['codex_problems']:
    raise SystemExit('Codex capture reports problems')
print('Four resource records and codex-live.json retaken.', flush=True)
