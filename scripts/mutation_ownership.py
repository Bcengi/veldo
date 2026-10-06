"""Repository test-worker ownership, persisted before external resources are used.

The worker observes temporary allocations, serialized containment profiles and unit
file creation. The coordinator reaps those resources even after SIGKILL. No global
prefix sweep: only paths and units recorded by this worker may be removed.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


class Tracker:
    def __init__(self, home):
        self.home = Path(home).resolve()
        self.path = self.home / 'ownership.jsonl'
        self.directories = {str(self.home)}
        self.seen = set()
        self.enabled = True
        self.encode = json.JSONEncoder.iterencode
        self.fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)

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

    def observe(self, value, visited=None):
        visited = set() if visited is None else visited
        if id(value) in visited:
            return
        visited.add(id(value))
        if isinstance(value, dict):
            if (value.get('kind') == 'linux-systemd' and self.owned(value.get('lock'))
                    and isinstance(value.get('slice'), str)
                    and re.fullmatch(r'(?:v|veldo)[A-Za-z0-9]+\.slice', value['slice'])):
                self.record('slice', value['slice'])
            for child in value.values():
                self.observe(child, visited)
        elif isinstance(value, (list, tuple)):
            for child in value:
                self.observe(child, visited)

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
                runtime = Path('/run/user/%d/systemd/user' % os.getuid())
                if path.parent == runtime and re.fullmatch(r'veldo-authority-[0-9a-f]+\.service', path.name):
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


def cleanup(home, run=subprocess.run):
    ledger = Path(home) / 'ownership.jsonl'
    if not ledger.exists():
        return {'units': [], 'directories': 0}
    entries = [json.loads(line) for line in ledger.read_text().splitlines()]
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
    return {'units': units, 'directories': len(directories)}
