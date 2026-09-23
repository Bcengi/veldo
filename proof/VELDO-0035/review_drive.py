#!/usr/bin/env python3
"""Record completed regression assertions; the full gate remains canonical verification."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
suite = ROOT / 'scripts/suites/58_veldo_0035_snapshots.py'
rows = []
started = time.monotonic()
with tempfile.TemporaryDirectory(prefix='snapshot-review-baseline-') as temporary:
    root = ROOT
    if '--original' in sys.argv:
        root = Path(temporary)
        (root / '.veldo').mkdir()
        for name in ('control_store', 'control_snapshot', 'control_readset', 'git_process', 'init_scaffold'):
            (root / '.veldo' / (name + '.py')).write_bytes(subprocess.check_output(
                ['git', 'show', '296be42:.veldo/' + name + '.py'], cwd=ROOT))
    ns = {'ROOT': root, 'expect': lambda name, condition: rows.append([name, bool(condition)])}
    exec(compile(suite.read_text(), str(suite), 'exec'), ns)
result = {'production': '296be42' if '--original' in sys.argv else subprocess.check_output(
    ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() + ' plus working changes',
    'rows': rows, 'failed': [name for name, passed in rows if not passed],
    'elapsed_seconds': time.monotonic() - started}
print(json.dumps(result, indent=2))
sys.exit(bool(result['failed']))
