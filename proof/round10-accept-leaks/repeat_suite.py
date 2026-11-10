"""Run a selected suite twice through the dispatcher's supported ordering override."""

import os
from pathlib import Path
import runpy
import sys
import threading


root = Path(__file__).resolve().parents[2]
name = sys.argv[1]
before = set(threading.enumerate())
os.environ['VELDO_SUITE_ORDER'] = ','.join((name, name))
sys.argv = [str(root / 'scripts/selftest.py'), '--suite', name]
try:
    runpy.run_path(sys.argv[0], run_name='__main__')
except SystemExit as error:
    status = error.code
else:
    raise RuntimeError('The dispatcher did not return its selector status')

remaining = [thread for thread in threading.enumerate() if thread not in before]
print('Round 10 repeat: %s; new live threads: %d; selector rc=%s'
      % (name, len(remaining), status), flush=True)
for thread in remaining:
    print('Remaining thread: %s' % thread.name, flush=True)
sys.exit(1 if remaining else status)
