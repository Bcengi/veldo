"""Explicit service/keystore fixture for pre-0258 service integration suites.

Each invocation gets its own libsecret executable and custody directory, inherited
by real service children. Production uses the same SecretService protocol.
"""
import contextlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch


@contextlib.contextmanager
def service(root):
    with tempfile.TemporaryDirectory(prefix='outside-fixture-') as directory:
        folder = Path(directory)
        script = folder / 'secret-tool'
        script.write_text('#!' + sys.executable + '\n' + '''import os,sys
from pathlib import Path
root = Path(__file__).parent / 'custody'
root.mkdir(exist_ok=True, mode=0o700)
name = sys.argv[-1]
if '/' in name or name in ('.', '..'): raise SystemExit(2)
path = root / name
action = sys.argv[1]
if action == 'store':
    path.write_bytes(sys.stdin.buffer.read())
    path.chmod(0o600)
elif action == 'lookup':
    if not path.exists(): raise SystemExit(1)
    sys.stdout.buffer.write(path.read_bytes())
elif action == 'clear':
    path.unlink(missing_ok=True)
else: raise SystemExit(2)
''')
        script.chmod(0o700)
        spec = importlib.util.spec_from_file_location('outside_fixture_calls', root / '.veldo/control_plane_calls.py')
        calls = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(calls)
        with patch.dict(os.environ, PATH=str(folder) + os.pathsep + os.environ.get('PATH', '')), calls.service(None):
            yield


def run(root, function):
    with service(root):
        return function()
