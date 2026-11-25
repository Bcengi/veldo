"""Diagnostic only: expose a failing fixture child's stderr without changing its result."""
from pathlib import Path
import runpy
import subprocess
import sys

original = subprocess.Popen.wait

def wait(self, *args, **kwargs):
    code = original(self, *args, **kwargs)
    if code and self.stderr is not None and not self.stderr.closed:
        data = self.stderr.read()
        print('DIAGNOSTIC child:', self.args, 'exit:', code, file=sys.stderr)
        print(data.decode(errors='replace') if isinstance(data, bytes) else data, file=sys.stderr)
    return code

subprocess.Popen.wait = wait
root = Path(__file__).resolve().parents[2]
sys.argv = [str(root / 'scripts/selftest.py'), '--suite', '49_veldo_0109_unavailable']
runpy.run_path(sys.argv[0], run_name='__main__')
