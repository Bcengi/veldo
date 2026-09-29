"""Run-local acceleration for the setup suites, including their child interpreters.

Only pure derivations are memoized: Python compilation and the installer's engine
census. Every source byte, filename and declared seed participates in the key.
Installed records, host state, setup calls and service processes are never cached.
"""
import base64
import contextlib
import hashlib
import importlib.machinery
import json
import marshal
import os
from pathlib import Path
import select
import socket
import sys
import time


def install(base):
    base = Path(base)
    cache = base / 'derivations'
    cache.mkdir(exist_ok=True)
    loader = importlib.machinery.SourceFileLoader
    original_compile, original_exec = loader.source_to_code, loader.exec_module

    def publish(path, data):
        temporary = path.with_suffix('.%d.tmp' % os.getpid())
        temporary.write_bytes(data)
        os.replace(temporary, path)

    def compile_source(self, data, path, *, _optimize=-1):
        if not Path(path).is_relative_to(base):
            return original_compile(self, data, path, _optimize=_optimize)
        key = hashlib.sha256(repr((path, _optimize, sys.implementation.cache_tag)).encode() + data).hexdigest()
        target = cache / (key + '.code')
        if target.exists():
            return marshal.loads(target.read_bytes())
        code = original_compile(self, data, path, _optimize=_optimize)
        publish(target, marshal.dumps(code))
        return code

    def census(module, function, args):
        directory = module.HERE
        digest = hashlib.sha256(function.__name__.encode())
        digest.update(repr((module.ENTRY_POINTS, module.EL.VALIDATOR_ROLES, args)).encode())
        paths = sorted(directory.glob('*.py'))
        if function.__name__ == 'runtime_assets':
            runtime = directory / 'runtime' if (directory / 'runtime').is_dir() else directory.parent / 'runtime'
            paths += sorted(p for p in runtime.rglob('*') if p.is_file())
        for path in paths:
            digest.update(str(path.relative_to(directory.parent)).encode() + b'\0')
            digest.update(hashlib.sha256(path.read_bytes()).digest())
        target = cache / (digest.hexdigest() + '.json')
        if target.exists():
            answer = json.loads(target.read_text())
            return ({k: base64.b64decode(v) for k, v in answer.items()}
                    if function.__name__ == 'runtime_assets' else answer)
        answer = function(*args)
        encoded = ({k: base64.b64encode(v).decode() for k, v in answer.items()}
                   if function.__name__ == 'runtime_assets' else answer)
        publish(target, json.dumps(encoded).encode())
        return answer

    def execute(self, module):
        original_exec(self, module)
        if Path(self.path).name == 'control_service.py' and Path(self.path).is_relative_to(base):
            for name in ('closure', 'runtime_assets'):
                if hasattr(module, name):
                    function = getattr(module, name)
                    def cached(*args, function=function):
                        return census(module, function, args)
                    setattr(module, name, cached)

    loader.source_to_code, loader.exec_module = compile_source, execute

    def close():
        loader.source_to_code, loader.exec_module = original_compile, original_exec
    return close


def notify_listen(address):
    """A child reports the real inet listen event, even on the wrong interface."""
    original = socket.socket.listen

    def listen(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        if self.family in (socket.AF_INET, socket.AF_INET6):
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as event:
                event.sendto(b'LISTEN', address)
        return result
    socket.socket.listen = listen


def ready(proc, listener, expected, seconds=5):
    """Wait for a specific readiness event or this child's exit, with a deadline."""
    deadline = time.monotonic() + seconds
    with contextlib.ExitStack() as stack:
        exited = os.pidfd_open(proc.pid)
        stack.callback(os.close, exited)
        while proc.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return False
            events = select.select([listener, exited], [], [], remaining)[0]
            if listener in events and expected in listener.recv(4096):
                return proc.poll() is None
            if exited in events:
                return False
    return False


def wake_authority(config):
    """Wake the stopped authority's accept wait after SIGTERM, without a command."""
    with contextlib.suppress(OSError, ValueError, KeyError):
        address = json.loads(Path(config).read_text())['socket']
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as wake:
            wake.settimeout(0.2)
            wake.connect(address)
