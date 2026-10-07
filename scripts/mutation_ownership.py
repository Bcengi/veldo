"""Repository test-worker ownership, persisted before external resources are used.

The worker observes temporary allocations, serialized containment profiles and unit
file creation. The coordinator reaps those resources even after SIGKILL. No global
prefix sweep: only paths and units recorded by this worker may be removed.

The ledger is the coordinator's file, outside every worker write grant. The worker
holds only an append descriptor to it, and candidate code shares that process, so
every line is a claim, not a fact: cleanup() acts only on entries of the exact shapes
the Tracker can produce for that worker and turns anything else into an error.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

SLICE = re.compile(r'(?:v|veldo)[A-Za-z0-9]+\.slice')
SERVICE = re.compile(r'veldo-authority-[0-9a-f]+\.service')


def unit_directory():
    return Path('/run/user/%d/systemd/user' % os.getuid())


class Tracker:
    def __init__(self, home, fd):
        # fd appends to the coordinator's ledger; the worker cannot open or name that file.
        self.home = Path(home).resolve()
        self.directories = {str(self.home)}
        self.seen = set()
        self.enabled = True
        self.encode = json.JSONEncoder.iterencode
        self.fd = fd

    def record(self, kind, value):
        pair = (kind, str(value))
        if pair not in self.seen:
            self.seen.add(pair)
            # Do not call the instrumented encoder recursively.
            body = json.JSONEncoder()
            data = ''.join(self.encode(body, list(pair))) + '\n'
            os.write(self.fd, data.encode())

    def owned(self, path):
        try:
            path = Path(path).absolute()
            return any(path.is_relative_to(parent) for parent in self.directories)
        except (TypeError, ValueError):
            return False

    def observe(self, value):
        # Walked with an explicit stack, never recursion: the observer runs inside every
        # json encoding of the code under test, so it must accept any value the encoder
        # accepts. A recursive walk raised RecursionError at Python's 1000-frame limit on a
        # value the C encoder serializes fine (VELDO-0054's 5000-deep blocks row), which
        # changed the suite's behaviour only inside mutation workers: an invalid baseline.
        visited, stack = set(), [value]
        while stack:
            value = stack.pop()
            if id(value) in visited:
                continue
            visited.add(id(value))
            if isinstance(value, dict):
                if (value.get('kind') == 'linux-systemd' and self.owned(value.get('lock'))
                        and isinstance(value.get('slice'), str)
                        and SLICE.fullmatch(value['slice'])):
                    self.record('slice', value['slice'])
                stack.extend(value.values())
            elif isinstance(value, (list, tuple)):
                stack.extend(value)

    def audit(self, event, args):
        if not self.enabled:
            return
        if event == 'tempfile.mkdtemp':
            path = str(Path(args[0]).absolute())
            self.directories.add(path)
            self.record('directory', path)
        elif event == 'open':
            path, mode, flags = args
            if isinstance(path, (str, bytes)) and flags & (os.O_CREAT | os.O_TRUNC):
                path = Path(os.fsdecode(path)).absolute()
                if path.parent == unit_directory() and SERVICE.fullmatch(path.name):
                    self.record('service', str(path))

    def install(self):
        sys.addaudithook(self.audit)
        def encode(encoder, value, *args, **kwargs):
            if self.enabled:
                self.observe(value)
            return self.encode(encoder, value, *args, **kwargs)
        json.JSONEncoder.iterencode = encode
        return self

    def close(self):
        self.enabled = False
        json.JSONEncoder.iterencode = self.encode
        os.close(self.fd)


def remove_tree(path):
    def writable(function, name, error):
        # Fixtures deliberately install read-only directories. Change only our tree.
        parent = Path(name).parent
        parent.chmod(parent.stat().st_mode | 0o700)
        if Path(name).is_dir():
            Path(name).chmod(Path(name).stat().st_mode | 0o700)
        function(name)
    if Path(path).exists():
        shutil.rmtree(path, onexc=writable)


def admitted(home, ledger, runtime=None):
    """Split the ledger into entries the Tracker can produce for the worker at `home` and the rest:
    a directory strictly beneath that home (after resolving links), a veldo-authority-<hex>.service
    file directly in the user unit directory, or a slice of the Tracker's own pattern.

    Python audits tempfile.mkdtemp before its mkdir, so the Tracker also records attempts the
    domain refused (a suite probing /dev/shm) and directories the case removed itself. A directory
    entry outside the home that does not exist names nothing to reap and is dropped; one that
    exists, or whose absence cannot be shown, stays rejected and is never touched."""
    home = Path(home).resolve()
    runtime = unit_directory() if runtime is None else Path(runtime)
    accepted, rejected = [], []
    for line in Path(ledger).read_text(errors='replace').splitlines():
        try:
            kind, value = json.loads(line)
            if not isinstance(kind, str) or not isinstance(value, str):
                raise ValueError(line)
            path = Path(value)
            plain = path.is_absolute() and os.path.normpath(value) == value
            if kind == 'directory' and plain:
                resolved = path.resolve()
                if resolved != home and resolved.is_relative_to(home):
                    accepted.append((kind, str(resolved)))
                    continue
                try:
                    os.lstat(value)
                except (FileNotFoundError, NotADirectoryError):
                    continue
            elif kind == 'service' and plain and path.parent == runtime and SERVICE.fullmatch(path.name):
                accepted.append((kind, value))
                continue
            elif kind == 'slice' and SLICE.fullmatch(value):
                accepted.append((kind, value))
                continue
        except (TypeError, ValueError, OSError):
            pass
        rejected.append(line[:200])
    return accepted, rejected


def cleanup(home, ledger, run=subprocess.run, runtime=None):
    ledger = Path(ledger)
    if not ledger.exists():
        return {'units': [], 'directories': 0}
    entries, rejected = admitted(home, ledger, runtime)
    directories = [v for k, v in entries if k == 'directory']
    services = [Path(v) for k, v in entries if k == 'service']
    units = sorted({v for k, v in entries if k == 'slice'} | {p.name for p in services})
    env = dict(os.environ, XDG_RUNTIME_DIR='/run/user/%d' % os.getuid())
    def ctl(*args):
        return run(['systemctl', '--user', *args], env=env, capture_output=True, text=True, timeout=60)
    if units:
        # Missing/unloaded units are already clean; a transport error is not.
        ctl('stop', *units)
        answer = ctl('show', '--property=ActiveState', *units)
        states = [line.partition('=')[2] for line in answer.stdout.splitlines() if line.startswith('ActiveState=')]
        if len(states) != len(units) or any(s not in ('inactive', 'failed') for s in states):
            raise RuntimeError('worker units did not stop: ' + answer.stdout + answer.stderr)
        ctl('reset-failed', *units)
    changed = False
    for path in services:
        if path.exists():
            path.unlink()
            changed = True
    if changed:
        answer = ctl('daemon-reload')
        if answer.returncode:
            raise RuntimeError('worker unit reload failed: ' + answer.stderr)
    for path in reversed(directories):
        remove_tree(path)
    if rejected:
        # Reap what this worker can own, then stay red: a forged entry is never acted on.
        raise RuntimeError('ownership ledger names resources outside this worker: ' + '; '.join(rejected[:5]))
    return {'units': units, 'directories': len(directories)}
