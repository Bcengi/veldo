#!/usr/bin/env python3
"""Retain detailed observations from the registered suite; verification is the full gate."""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
rows = []
suite = ROOT / 'scripts/suites/58_veldo_0035_snapshots.py'
namespace = {'ROOT': ROOT, '__file__': str(suite),
             'expect': lambda name, condition: rows.append([name, bool(condition)])}
exec(compile(suite.read_text(), str(suite), 'exec'), namespace)
result = dict(namespace['_s35_observations'], rows=rows,
              verification='Diagnostic observations; only bash scripts/verify.sh verifies the change.')
(ROOT / 'proof/VELDO-0035/observations.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'rows': len(rows), 'failed': [name for name, okay in rows if not okay],
                  'elapsed_seconds': result['elapsed_seconds']}))
sys.exit(0 if all(okay for _, okay in rows) else 1)
