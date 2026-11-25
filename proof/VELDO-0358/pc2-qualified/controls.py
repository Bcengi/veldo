"""Bounded pc2-only evidence driver; invoke with /usr/bin/python3 -I -S."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

assert sys.executable == '/usr/bin/python3'
assert platform.node() == 'dmitry-pc2'
sys.dont_write_bytecode = True
root = Path.cwd()
sys.path.insert(0, str(root / 'scripts'))
import gate_fixtures
import check_gate_mutations as driver
import gate_legs

parent = root.parents[2] / 'f'
parent.mkdir(mode=0o700, exist_ok=True)
metadata = dict(host=platform.node(), python=sys.version, executable=sys.executable,
                commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                node=subprocess.check_output(['/usr/bin/node', '--version'], text=True).strip(),
                npm=subprocess.check_output(['/usr/bin/npm', '--version'], text=True).strip())
import pwd
account = Path(pwd.getpwuid(os.getuid()).pw_dir)
metadata['engines'] = {}
for name, rel in {
    'codex': '.local/share/codex-versions/0.166.0/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex',
    'claude': '.local/share/claude/versions/2.1.317',
}.items():
    path = account / rel
    metadata['engines'][name] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())

receipts, raw = [], {}
with gate_fixtures.directory(configured=parent, environment={}) as fixture:
    os.environ['VELDO_FIXTURE_PARENT'] = str(parent)
    os.environ['VELDO_FIXTURE_ROOT'] = str(fixture)
    with tempfile.TemporaryDirectory(prefix='pc2-controls-', dir='/tmp') as scratch:
        for index, name in enumerate(('pool-shared-profile', 'role127-resource-grant-omitted')):
            print('START', name, flush=True)
            logs = Path(scratch) / str(index)
            receipt = driver.run_stage(root, driver.common_directory(root), names=[name],
                parallel=1, leg=gate_legs.mutation_leg(), log_dir=logs, force_fresh=True)
            receipts.append(receipt)
            raw[name] = {str(p.relative_to(logs)): p.read_text(errors='replace')
                         for p in logs.rglob('*') if p.is_file()
                         and ('stdout' in p.name or 'stderr' in p.name)}
            print('END', name, receipt['status'], receipt.get('elapsed'),
                  json.dumps(receipt.get('invalid_results', []))[:3000], flush=True)
metadata['fixture_removed'] = not fixture.exists()
Path('controls-metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
Path('controls-receipts.json.gz').write_bytes(gzip.compress(json.dumps(receipts).encode(), mtime=0))
Path('controls-raw.json.gz').write_bytes(gzip.compress(json.dumps(raw).encode(), mtime=0))
sys.exit(0 if all(r['status'] == 'passed' for r in receipts) else 1)
