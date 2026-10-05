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


def install(base, cache):
    base, cache = Path(base), Path(cache)
    loader = importlib.machinery.SourceFileLoader
    original_compile, original_exec = loader.source_to_code, loader.exec_module
    original_get_code = loader.get_code
    codes = {}

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

    def get_code(self, fullname):
        # Sharing immutable code keeps every module execution and its globals separate.
        # Read the source on every load: a restored or mutated file must never reuse
        # bytecode solely because its timestamp and length happen to match.
        if not Path(self.path).is_relative_to(base):
            return original_get_code(self, fullname)
        data = self.get_data(self.path)
        key = (self.path, hashlib.sha256(data).digest(), sys.flags.optimize)
        if key not in codes:
            codes[key] = compile_source(self, data, self.path)
        return codes[key]

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
    loader.get_code = get_code

    def close():
        loader.source_to_code, loader.exec_module = original_compile, original_exec
        loader.get_code = original_get_code
        codes.clear()
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


def runtime_red(root, here, suite, commit, limit, git):
    """Measure the old suite itself; the new claim is runtime, not changed behavior."""
    import subprocess
    import tempfile

    resolved = git.run(['git', '-C', str(root), 'rev-parse', commit + '^{commit}'],
                       capture_output=True, text=True, check=True).stdout.strip()
    with tempfile.TemporaryDirectory(prefix='setup-runtime-red-') as scratch:
        tree = Path(scratch) / 'tree'
        git.run(['git', 'clone', '-q', '--no-checkout', str(root), str(tree)], capture_output=True, check=True)
        git.run(['git', '-C', str(tree), 'checkout', '-q', '--detach', resolved], capture_output=True, check=True)
        path = tree / 'scripts/suites' / suite
        source = path.read_text()
        source_digest = hashlib.sha256(source.encode()).hexdigest()
        # Add observations only. The baseline's original setup, waits and assertions run.
        source = source.replace('    def check(row, label, condition):',
                                '    timings = {name: 0.0 for name in ROWS}\n'
                                '    last_check = [time.monotonic()]\n'
                                '    def check(row, label, condition):\n'
                                '        now = time.monotonic()\n'
                                '        timings[row] += now - last_check[0]\n'
                                '        last_check[0] = now')
        timing = Path(scratch) / 'rows.json'
        source = source.replace('    for name, observed in rows.items():',
                                '    Path(%r).write_text(json.dumps(dict(rows=timings, seconds=time.monotonic() - started)))\n'
                                '    for name, observed in rows.items():' % str(timing))
        path.write_text(source)
        log = Path(scratch) / 'suite.log'
        with log.open('w') as output:
            result = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', Path(suite).stem],
                                    cwd=tree, stdout=output, stderr=subprocess.STDOUT)
        measured = json.loads(timing.read_text())
        report = dict(schema='veldo.proof-runtime/v1', spec_id=Path(here).name,
                      commit=resolved, suite=suite, source_sha256=source_digest, limit_seconds=limit, **measured,
                      behavior_checks_pass=result.returncode == 2,
                      by_assertion=result.returncode == 2,
                      runtime_row=['runtime/suite-budget', measured['seconds'] < limit],
                      note='The baseline suite, with timing observations only. Existing behavior stays green; the runtime claim is red.')
        destination = Path(here) / ('runtime-red-at-%s.json' % commit)
        destination.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps({k: report[k] for k in ('seconds', 'behavior_checks_pass', 'runtime_row')}))
