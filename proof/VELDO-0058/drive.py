#!/usr/bin/env python3
"""Record one run of suite 69 as observations.json: every row, the suite's run time and what each region
observed (the lands, the executor's gates, every sink case, every tampered acceptance and the installed
verifier and policy against the candidate's stubs).

Run from the repository root: python3 -B proof/VELDO-0058/drive.py
The mutation evidence is mutations.py (mutations.json here); the red record is red.py.
"""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import run_suite, SUITE  # noqa: E402

rows, observed, elapsed = run_suite()
record = {'suite': SUITE.name, 'rows': rows, 'passed': sum(ok for _, ok in rows),
          'failed': sum(not ok for _, ok in rows), 'suite_seconds': round(elapsed, 3), 'observed': observed}
out = Path(__file__).with_name('observations.json')
out.write_text(json.dumps(record, indent=1, sort_keys=True, default=str) + '\n')
print('%s: %d passed, %d failed in %.3fs -> %s' % (SUITE.name, record['passed'], record['failed'], elapsed, out.name))
sys.exit(1 if record['failed'] else 0)
