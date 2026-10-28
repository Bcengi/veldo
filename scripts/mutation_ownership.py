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
import socket
import subprocess
import sys

SLICE = re.compile(r'(?:v|veldo)[A-Za-z0-9]+\.slice')
SERVICE = re.compile(r'veldo-authority-[0-9a-f]+\.service')


def unit_directory():
    return Path('/run/user/%d/systemd/user' % os.getuid())


class Tracker:
    def __init__(self, home, fd, lifecycle_fd=None):
        # fd appends to the coordinator's ledger; the worker cannot open or name that file.
        self.home = Path(home).resolve()
        self.directories = {str(self.home)}
        self.seen = set()
        self.enabled = True
        self.encode = json.JSONEncoder.iterencode
        self.fd = fd
        self.lifecycle = socket.socket(fileno=lifecycle_fd) if lifecycle_fd is not None else None
        self.Popen = subprocess.Popen

    def record(self, kind, value):
        pair = (kind, str(value))
        if pair not in self.seen:
            self.seen.add(pair)
            # Do not call the instrumented encoder recursively.
            body = json.JSONEncoder()
            data = ''.join(self.encode(body, list(pair))) + '\n'
            os.write(self.fd, data.encode())
            if kind in ('slice', 'service'):
                self.notify('register', kind, str(value))

    def notify(self, operation, kind='', value=''):
        if self.lifecycle is None:
            return
        # This channel supplies names only. The authority reads every counter.
        self.lifecycle.sendall(json.dumps([operation, kind, value]).encode())
        answer = json.loads(self.lifecycle.recv(65536))
        if answer != {'ok': True}:
            raise RuntimeError('worker_measurement_error: ' + str(answer))

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
        tracker = self
        class Popen(self.Popen):
            def __init__(self, args, *positional, **kwargs):
                self.accounting = tracker.lifecycle is not None and isinstance(args, (list, tuple)) and bool(args) and Path(args[0]).name in ('systemctl', 'systemd-run')
                self.accounted = False
                if self.accounting:
                    tracker.notify('before')
                super().__init__(args, *positional, **kwargs)
            def wait(self, *args, **kwargs):
                result = super().wait(*args, **kwargs)
                if self.accounting and not self.accounted:
                    tracker.notify('after')
                    self.accounted = True
                return result
        subprocess.Popen = Popen
        return self

    def close(self):
        self.enabled = False
        json.JSONEncoder.iterencode = self.encode
        subprocess.Popen = self.Popen
        if self.lifecycle is not None:
            self.lifecycle.close()
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


class RetainedSlice:
    """Keep an accounting parent loaded until the authority reads final counters.

    Descendant CPU is retained by the kernel even when a short unit's cgroup
    disappears. A manager reference also preserves CPUUsageNSec after an explicit
    stop. Each restart is a new counter generation, never maxed against a prior run.
    """
    def __init__(self, unit, root):
        import ctypes as ct
        self.unit, self.root = unit, root
        self.total, self.current, self.peak, self.invocation = 0., 0., 0, None
        self.memory_peak = 0
        self.lib = ct.CDLL('libsystemd.so.0')
        pointer = ct.c_void_p
        self.bus = pointer()
        for name, args, result in (
            ('sd_bus_open_user', [ct.POINTER(pointer)], ct.c_int),
            ('sd_bus_call_method', [pointer, ct.c_char_p, ct.c_char_p, ct.c_char_p,
                                   ct.c_char_p, pointer, pointer, ct.c_char_p], ct.c_int),
            ('sd_bus_flush_close_unref', [pointer], pointer)):
            function = getattr(self.lib, name)
            function.argtypes, function.restype = args, result
        try:
            if self.lib.sd_bus_open_user(ct.byref(self.bus)) < 0:
                raise OSError('cannot open accounting manager connection')
            # Starting an empty slice creates a durable kernel accounting parent.
            self.ctl('start', unit)
            rc = self.lib.sd_bus_call_method(self.bus, b'org.freedesktop.systemd1',
                b'/org/freedesktop/systemd1', b'org.freedesktop.systemd1.Manager',
                b'RefUnit', None, None, b's', ct.c_char_p(unit.encode()))
            if rc < 0:
                raise OSError(-rc, 'cannot retain accounting slice')
            self.path = None
            self.inode = None
            self.sample()
        except BaseException:
            try:
                self.ctl('stop', unit)
            finally:
                self.close()
            raise

    @staticmethod
    def ctl(*args):
        result = subprocess.run(['systemctl', '--user', *args], capture_output=True, text=True,
                                timeout=10, env=dict(os.environ, XDG_RUNTIME_DIR='/run/user/%d' % os.getuid()))
        if result.returncode:
            raise OSError('accounting manager command failed: ' + result.stderr)
        return result.stdout

    def sample(self, final=False):
        if not final and self.path is not None:
            return self.kernel_sample()
        shown = dict(line.split('=', 1) for line in self.ctl('show', self.unit,
                     '-p', 'ControlGroup', '-p', 'CPUUsageNSec', '-p', 'InvocationID', '-p', 'MemoryPeak').splitlines() if '=' in line)
        invocation = shown.get('InvocationID')
        if invocation and invocation != self.invocation:
            self.total += self.current
            self.current = 0.
            self.invocation = invocation
        cpu = shown.get('CPUUsageNSec', '')
        if cpu.isdigit() and int(cpu) < 2**64-1:
            self.current = max(self.current, int(cpu)/1e9)
        peak = shown.get('MemoryPeak', '')
        if peak.isdigit() and int(peak) < 2**64-1:
            self.memory_peak = max(self.memory_peak, int(peak))
        value = shown.get('ControlGroup')
        if value:
            if not value.startswith('/') or '..' in Path(value).parts or Path(value).name != self.unit:
                raise ValueError('invalid accounting cgroup')
            self.path = self.root / value.lstrip('/')
            self.inode = self.path.stat().st_ino if self.path.exists() else None
        return self.kernel_sample()

    def kernel_sample(self):
        if self.path is not None:
            try:
                if self.path.stat().st_ino != self.inode:
                    return self.sample(final=True)
                cpu = dict(line.split() for line in (self.path/'cpu.stat').read_text().splitlines())
                memory = dict(line.split() for line in (self.path/'memory.stat').read_text().splitlines())
                self.current = max(self.current, int(cpu['usage_usec'])/1e6)
                self.peak = max(self.peak, int(memory['anon']))
                self.memory_peak = max(self.memory_peak, int((self.path/'memory.peak').read_text()))
            except FileNotFoundError:
                pass
        return self.total + self.current, self.peak

    def close(self):
        if self.bus:
            self.lib.sd_bus_flush_close_unref(self.bus)
            self.bus = None



class WorkerMeter:
    """Coordinator-owned cgroup counters, read before ownership cleanup.

    Anonymous memory is sampled at each coordinator poll. CPU counters are
    cumulative. Owned user units may live outside the worker's subtree; count
    only disjoint roots so a slice and its services are never charged twice.
    """
    def __init__(self, scope, name, cgroup_root=Path('/sys/fs/cgroup')):
        import time
        self.clock = time.monotonic
        self.root = Path(cgroup_root)
        scope = Path(scope)
        if not scope.is_absolute() or '..' in scope.parts or not scope.name:
            raise ValueError('worker_launch_error: invalid delegated scope')
        if self.root == Path('/sys/fs/cgroup'):
            own = Path('/proc/self/cgroup').read_text().split('::', 1)[1].strip()
            if not (own == str(scope) or own.startswith(str(scope) + '/')):
                raise ValueError('worker_launch_error: gate scope is not an ancestor')
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name):
            raise ValueError('worker_launch_error: invalid worker cgroup name')
        self.path = self.root / str(scope).lstrip('/') / ('worker-%d-%s' % (os.getpid(), name))
        self.path.mkdir()
        self.paths, self.counters = {}, {}
        self.peak, self.last_discovery = 0, float('-inf')
        self.lifecycle = self.peer = None
        self.retained, self.dropins = {}, []
        self.covered_units = set()
        self.accounting_slice = 'veldometer%s.slice' % self.path.name.replace('-', '')


    def open_lifecycle(self):
        self.lifecycle, self.peer = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self.lifecycle.setblocking(False)
        return self.peer.fileno()

    def launched(self):
        if self.peer is not None:
            self.peer.close()
            self.peer = None

    def retain(self, unit):
        if unit not in self.retained:
            self.retained[unit] = RetainedSlice(unit, self.root)
        return self.retained[unit]

    def prepare_unit(self, kind, value):
        if kind == 'slice' and SLICE.fullmatch(value):
            self.retain(value)
        elif kind == 'service' and Path(value).parent == unit_directory() and SERVICE.fullmatch(Path(value).name):
            self.retain(self.accounting_slice)
            directory = unit_directory() / (Path(value).name + '.d')
            directory.mkdir(exist_ok=True)
            target = directory / '90-veldo-meter.conf'
            # Never overwrite a preexisting owner's drop-in.
            with target.open('x') as handle:
                handle.write('[Service]\nSlice=' + self.accounting_slice + '\n')
            self.dropins.append(target)
            self.covered_units.add(Path(value).name)
        else:
            raise ValueError('invalid lifecycle unit ownership')

    def lifecycle_events(self, home, ledger):
        if self.lifecycle is None:
            return
        while True:
            try:
                data = self.lifecycle.recv(65536)
            except BlockingIOError:
                return
            if not data:
                return
            try:
                operation, kind, value = json.loads(data)
                if operation == 'register':
                    entries, rejected = admitted(home, ledger)
                    if rejected or (kind, value) not in entries:
                        raise ValueError('lifecycle unit is not in the ownership ledger')
                    self.prepare_unit(kind, value)
                elif operation not in ('before', 'after'):
                    raise ValueError('invalid lifecycle operation')
                for retained in self.retained.values():
                    retained.sample(final=True)
                self.lifecycle.send(json.dumps({'ok': True}).encode())
            except Exception as error:
                self.lifecycle.send(json.dumps({'error': str(error)}).encode())
                raise

    def open_join(self):
        return os.open(self.path / 'cgroup.procs', os.O_WRONLY | os.O_CLOEXEC)

    def unit_paths(self, home, ledger):
        entries, rejected = admitted(home, ledger)
        if rejected:
            raise ValueError('ownership ledger contains invalid resource entries')
        units = {v if k == 'slice' else Path(v).name for k, v in entries if k in ('slice', 'service')}
        for unit in sorted(units - self.paths.keys() - self.retained.keys() - self.covered_units):
            answer = subprocess.run(['systemctl', '--user', 'show', '-p', 'ControlGroup', '--value', unit],
                                    capture_output=True, text=True, timeout=5,
                                    env=dict(os.environ, XDG_RUNTIME_DIR='/run/user/%d' % os.getuid()))
            value = answer.stdout.strip()
            if answer.returncode or not value:
                continue
            path = self.root / value.lstrip('/')
            if not value.startswith('/') or '..' in Path(value).parts or path == self.root:
                raise ValueError('invalid owned unit cgroup')
            if path.name != unit:
                raise ValueError('owned unit cgroup does not match unit')
            self.paths[unit] = path

    def sample(self, home=None, ledger=None):
        if ledger is not None:
            self.lifecycle_events(home, ledger)
        if ledger is not None and self.clock() - self.last_discovery >= .1:
            self.unit_paths(home, ledger)
            self.last_discovery = self.clock()
        retained_values = {r.path: r.sample() for r in self.retained.values() if r.path is not None}
        paths = {self.path, *self.paths.values(), *retained_values}

        roots = [p for p in paths if not any(other != p and other in p.parents for other in paths)]
        for path in roots:
            try:
                cpu = dict(line.split() for line in (path / 'cpu.stat').read_text().splitlines())
                memory = dict(line.split() for line in (path / 'memory.stat').read_text().splitlines())
                prior = self.counters.get(path, (0, 0))
                self.counters[path] = (max(prior[0], int(cpu['usage_usec']) / 1e6),
                                       max(prior[1], int(memory['anon'])))
            except FileNotFoundError:
                if path == self.path:
                    raise
        self.counters.update(retained_values)
        # Sum per-root peaks conservatively. Removed units retain their counters.
        # Remove nested entries if a parent became visible in a later poll.
        self.counters = {p: v for p, v in self.counters.items()
                         if not any(other != p and other in p.parents for other in self.counters)}
        self.peak = max(self.peak, sum(v[1] for v in self.counters.values()))
        # Anonymous memory remains sampled. The kernel's durable total-memory
        # peak is a separate conservative bound for units missed between polls;
        # never relabel file cache as measured anonymous memory.
        memory_bound = sum(v[1] for p, v in self.counters.items() if p not in retained_values)
        memory_bound += sum(r.memory_peak for r in self.retained.values())

        return dict(cpu_seconds=sum(v[0] for v in self.counters.values()), peak_anon_bytes=self.peak,
                    peak_memory_bytes=max(self.peak, memory_bound),
                    metrics_source='cgroup-v2-anon-sampled-20ms-with-final-unit-accounting',
                    cgroups=sorted(str(p) for p in self.counters))

    def close(self):
        import time
        for target in self.dropins:
            target.unlink(missing_ok=True)
            try:
                target.parent.rmdir()
            except OSError:
                pass
        self.dropins.clear()
        if self.accounting_slice in self.retained:
            RetainedSlice.ctl('stop', self.accounting_slice)
        for retained in self.retained.values():
            retained.close()
        self.retained.clear()
        for sock in (self.peer, self.lifecycle):
            if sock is not None:
                sock.close()
        self.peer = self.lifecycle = None
        if not self.path.exists():
            return
        events = self.path / 'cgroup.events'
        if 'populated 1' in events.read_text():
            (self.path / 'cgroup.kill').write_text('1')
            end = time.monotonic() + 5
            while 'populated 1' in events.read_text():
                if time.monotonic() >= end:
                    raise RuntimeError('worker cgroup remains populated')
                time.sleep(.02)
        for path in sorted(self.path.rglob('*'), reverse=True):
            if path.is_dir():
                path.rmdir()
        self.path.rmdir()
