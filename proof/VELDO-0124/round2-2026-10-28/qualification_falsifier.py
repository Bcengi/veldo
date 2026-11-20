"""Drive the forged record against the reviewed profile and the fixed profile."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BASE = 'e20b4c15'
PROFILE = '.veldo/project_runner_macos_profile.py'
probe = """import sys, tempfile
from pathlib import Path
sys.path.insert(0, 'proof/VELDO-0124')
import checks
with tempfile.TemporaryDirectory(prefix='v124-forged-') as directory:
    checks.forged_qualification(Path(directory))
print('PASS: forged, missing, digest, malformed, edited and substituted evidence refused before bootstrap; intact evidence admitted')
"""
results = []
for phase in ('red', 'green'):
    with tempfile.TemporaryDirectory(prefix='v124-evidence-') as directory:
        target = Path(directory)
        for path in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(path, target / path.name)
        source = (subprocess.check_output(['git', 'show', BASE + ':' + PROFILE], cwd=ROOT)
                  if phase == 'red' else (ROOT / PROFILE).read_bytes())
        (target / Path(PROFILE).name).write_bytes(source)
        run = subprocess.run([sys.executable, '-c', probe], cwd=ROOT,
                             env=dict(os.environ, VELDO_0124_MODULES=str(target),
                                      PYTHONDONTWRITEBYTECODE='1'),
                             capture_output=True, text=True, timeout=60)
        (HERE / ('qualification-' + phase + '.log')).write_text(run.stdout + run.stderr)
        (HERE / ('qualification-' + phase + '.exit')).write_text(str(run.returncode) + '\n')
        results.append(dict(phase=phase, exit=run.returncode,
                            profile_sha256=hashlib.sha256(source).hexdigest()))
assert results[0]['exit'] == 1 and results[1]['exit'] == 0, results
(HERE / 'qualification-red-green.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
