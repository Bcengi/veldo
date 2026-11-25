"""Diagnostic only: expose a failing fixture child's stderr without changing its result."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
def load(name):
    spec = importlib.util.spec_from_file_location(name, root / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

if len(sys.argv) == 1:
    with tempfile.TemporaryDirectory(prefix='qd-', dir='/tmp') as scratch:
        code = load('agent_sandbox').worker_tree([sys.executable, '-I', '-S', __file__, scratch],
                dict(os.environ, HOME=scratch, TMPDIR=scratch), root, scratch)
    sys.exit(code)

load('mutation_sandbox').confine_in_tree(root, root, Path(sys.argv[1]))
original = subprocess.Popen.wait
def wait(self, *args, **kwargs):
    code = original(self, *args, **kwargs)
    if code and self.stderr is not None and not self.stderr.closed:
        data = self.stderr.read()
        print('DIAGNOSTIC child:', self.args, 'exit:', code, file=sys.stderr)
        print(data.decode(errors='replace') if isinstance(data, bytes) else data, file=sys.stderr)
    return code
subprocess.Popen.wait = wait
observer = load('mutation_observer')
case = dict(suite='49_veldo_0109_unavailable.py', module='control_client.py', rows=[])
print(json.dumps(observer.worker(case)))
