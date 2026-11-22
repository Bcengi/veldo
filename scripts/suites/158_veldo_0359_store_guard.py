"""VELDO-0359 B2. Disposable stores and fixture payloads only; never a model engine.

The receiver's launch, preflight, containment, wrapper and acknowledgement run unchanged.
Dispatch prerequisites are fixtures; systemd, Landlock, descriptors and setup pipes are real.
HANG is a hang detector, never an observation window. Every child exchange is event driven.
"""


def _v359_guard_suite():
    import contextlib
    import copy
    import ctypes
    import errno
    import importlib.util
    import json
    import os
    from pathlib import Path
    import select
    import shutil
    import socket
    import sqlite3
    import subprocess
    import sys
    import tempfile
    import threading
    import time
    import types
    from unittest.mock import patch

    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_clone.py': ROOT / ".veldo" / "control_clone.py",
        'control_agent_config_handoff.py': ROOT / ".veldo" / "control_agent_config_handoff.py",
    }
    HANG = 120
    names = ('launch/guard-default', 'ruleset/primitive-symlink-out', 'launch/guard-read',
             'launch/enforce-fail', 'launch/descriptors-early', 'launch/descriptors-leaked',
             'launch/ack', 'launch/receiver-memory', 'launch/abi', 'layout/entries',
             'layout/mounts', 'layout/placement', 'launch/risky-real', 'launch/risky-census',
             'launch/engines', 'query/journey', 'switch/off', 'switch/run-cannot-flip', 'switch/transitions', 'paths/canon')
    selected = set(os.environ.get('VELDO_0359_ROWS', '').split(',')) - {''}
    rows = {name: [] for name in names if not selected or name in selected}
    def check(row, label, value):
        if row in rows:
            rows[row].append((label, bool(value)))
    def needed(*labels):
        return bool(set(labels) & rows.keys())
    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    @contextlib.contextmanager
    def section(*labels):
        try:
            yield
        except Exception as error:
            for label in labels:
                check(label, 'raised ' + repr(error), False)

    # A fresh directory outside home and all temporary roots is essential to placement.
    # Never discover, open, or remove an existing store; TemporaryDirectory creates exclusively.
    with tempfile.TemporaryDirectory(prefix='v359-b2-', dir='/var/lib/veldo') as directory:
        base = Path(directory)
        mods = base / 'installed/.veldo'
        mods.mkdir(parents=True)
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        L = load('v359_guard', mods / 'control_launch.py')
        CL = load('v359_clone', mods / 'control_clone.py')
        store = base / 'state/authority'
        store.mkdir(parents=True)
        db = store / 'custom.sqlite3'
        writer = L.S.open_store(str(db))
        writer.close()
        for name in ('custom.sqlite3-wal', 'custom.sqlite3-shm', 'custom.sqlite3-journal', 'authority.lock'):
            (store / name).write_bytes(b'fixture sentinel\n')
        work = base / 'work'
        work.mkdir()
        runs = base / 'runs'
        runs.mkdir()
        runtime = base / 'runtime'
        runtime.mkdir()
        config = dict(store=str(db), runs=str(runs), principal='fixture', domain='fixture-domain',
                      repository='fixture-repository', journal_key=str(base / 'unused-key'),
                      authority_generation=1, workspace=str(work))
        trust = base / 'trust.json'
        signers = base / 'signers'
        signers.write_text('')
        trust.write_text(json.dumps(dict(schema='veldo.host_trust/v1', host_identity='fixture-host',
                                        enrollment_signers=str(signers))))
        config['host_trust'] = str(trust)
        profile = dict(kind='linux-systemd', slice='app.slice', lock=str(base / 'admission.lock'), concurrency=4,
                       runtime_seconds=HANG, memory_bytes=256 << 20, cpu_percent=150, file_bytes=8 << 20,
                       tasks_max=128, stop_grace_seconds=1, kill_grace_seconds=1,
                       heartbeat_seconds=120, heartbeat_window_seconds=240)
        config['profile'] = profile
        risky_config = base / 'probe-runner.json'
        risky_config.write_text((ROOT / 'scripts/agent_sandbox.json').read_text())
        sample = L.RQ.switch(db)
        good_probe = dict(platform='x86_64', abi=8, reason=None)
        def preflight(**kwargs):
            return L.guard_preflight(kwargs.pop('config', config), kwargs.pop('sample', L.RQ.switch(db)),
                                     kwargs.pop('risky', False), kwargs.pop('locations', [('work', work, True)]),
                                     probe=kwargs.pop('probe', good_probe), **kwargs)
        def digest():
            return __import__('hashlib').sha256(db.read_bytes()).hexdigest()
        before = digest()

        # Payload and injector live outside the denied directory. All result channels are ordinary pipes.
        payload = work / 'payload.py'
        payload.write_text(r'''import ctypes, errno, fcntl, json, os, socket, subprocess, sys
from pathlib import Path
store, work, mode = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
result = {}
def trial(name, operation):
    try:
        operation()
        result[name] = 0
    except OSError as error:
        result[name] = error.errno
    except Exception as error:
        result[name] = type(error).__name__
def opened(path, flags):
    fd = os.open(path, flags)
    os.close(fd)
def rename_back(source, target):
    existed = target.is_dir()
    os.rename(source, target)
    os.rename(target, source)
    if existed: target.mkdir()
def exchange_back(source, target):
    libc = ctypes.CDLL(None, use_errno=True)
    for _ in range(2):
        if libc.renameat2(-100, os.fsencode(source), -100, os.fsencode(target), 2):
            code = ctypes.get_errno()
            raise OSError(code, os.strerror(code))
def truncate_restore(path, readonly=False):
    if readonly: opened(path, os.O_RDONLY | os.O_TRUNC)
    else: os.truncate(path, 0)
    path.write_bytes(b'sentinel')
def unlink_restore(path):
    path.unlink()
    path.write_bytes(b'sentinel')
def link_out(source, target):
    os.link(source, target)
    target.unlink()
def create(path, kind):
    if kind == 'file': path.write_bytes(b'new'); path.unlink()
    elif kind == 'dir': path.mkdir(); path.rmdir()
    elif kind == 'link': path.symlink_to(work); path.unlink()
    else:
        sock = socket.socket(socket.AF_UNIX)
        try: sock.bind(str(path))
        finally: sock.close()
        path.unlink()
if mode == 'attacks':
    for name in ('custom.sqlite3', 'custom.sqlite3-wal', 'custom.sqlite3-shm', 'custom.sqlite3-journal', 'authority.lock'):
        trial(name + '/read', lambda name=name: opened(store / name, os.O_RDONLY))
        trial(name + '/write', lambda name=name: opened(store / name, os.O_WRONLY))
    for kind in ('file', 'dir', 'link', 'socket'):
        trial('create/' + kind, lambda kind=kind: create(store / ('new-' + kind), kind))
    for name in ('truncate-ro', 'truncate', 'unlink', 'rename', 'link'):
        path = store / ('trial-' + name)
        if name == 'truncate-ro': fn = lambda: truncate_restore(path, True)
        elif name == 'truncate': fn = lambda: truncate_restore(path)
        elif name == 'unlink': fn = lambda: unlink_restore(path)
        elif name == 'rename': fn = lambda: rename_back(path, work / 'renamed')
        else: fn = lambda: link_out(path, work / 'linked')
        trial(name, fn)
    trial('store-move', lambda: rename_back(store, store.with_name('moved')))
    trial('store-replace', lambda: rename_back(store, work / 'empty'))
    trial('store-exchange', lambda: exchange_back(store, work / 'empty'))
    trial('store-exchange-in', lambda: exchange_back(work / 'empty', store))
    trial('ancestor', lambda: create(store.parent / 'new', 'file'))
    trial('outside-link', lambda: opened(work / 'outside-link', os.O_RDONLY))
    trial('marker-create', lambda: create(store / 'store-guard.off', 'file'))
    trial('marker-link', lambda: link_out(work / 'source', store / 'store-guard.off'))
    trial('marker-rename', lambda: rename_back(work / 'source', store / 'store-guard.off'))
    trial('parent-move', lambda: rename_back(store.parent, store.parent.with_name('moved-state')))
    trial('work-write', lambda: create(work / 'allowed', 'file'))
    trial('home-write', lambda: create(Path(os.environ['HOME']) / 'allowed', 'file'))
    trial('tmp-write', lambda: create(Path(os.environ['TMPDIR']) / 'allowed', 'file'))
    for name, operation in (('socket-link', lambda: link_out(store / 'authority.sock', work / 'socket-link')),
                            ('socket-rename', lambda: rename_back(store / 'authority.sock', work / 'socket-moved'))):
        trial(name, operation)
    sock = socket.socket(socket.AF_UNIX)
    try:
        sock.connect(str(store / 'authority.sock'))
        sock.sendall(b'{}\n')
        result['socket-refusal'] = json.loads(sock.recv(65536))
    finally: sock.close()
    if len(sys.argv) < 5:
        child = subprocess.run([sys.executable, '-B', __file__, str(store), str(work), mode, 'child'], capture_output=True, text=True, timeout=120)
        result['child'] = json.loads(child.stdout)
elif mode == 'socket-unlink':
    if len(sys.argv) > 4 and sys.argv[4] == 'descendant':
        child = subprocess.run([sys.executable, '-B', __file__, str(store), str(work), mode], capture_output=True, text=True, timeout=120)
        result = json.loads(child.stdout)
    else: trial('unlink', lambda: (store / 'authority.sock').unlink())
elif mode == 'switch-attempts':
    (work / 'source').write_bytes(b'fixture')
    trial('create', lambda: create(store / 'store-guard.off', 'file'))
    trial('link', lambda: link_out(work / 'source', store / 'store-guard.off'))
    trial('rename', lambda: rename_back(work / 'source', store / 'store-guard.off'))
    trial('store', lambda: rename_back(store, store.with_name('moved-store')))
    trial('parent', lambda: rename_back(store.parent, store.parent.with_name('moved-parent')))
elif mode == 'route':
    target = Path(sys.argv[4]); target = target if target.is_absolute() else Path.home() / target
    result['sentinel'] = target.read_text()
elif mode == 'flip':
    trial('marker', lambda: Path(sys.argv[4]).write_text('fixture'))
elif mode == 'read':
    def lock():
        fd = os.open(store / 'authority.lock', os.O_RDONLY)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        os.close(fd)
    trial('lock', lock)
elif mode == 'leak':
    fd = int(sys.argv[4])
    def use():
        if os.path.isdir('/proc/self/fd/' + str(fd)): os.listdir(fd)
        else: os.read(fd, 1)
    trial('leak', use)
elif mode == 'hold':
    print(json.dumps({'ready': True}), flush=True)
    sys.stdin.buffer.read(1)
    trial('read', lambda: opened(store / 'custom.sqlite3', os.O_RDONLY))
elif mode == 'memory':
    pid, address, fd = map(int, sys.argv[4:7])
    trial('fd', lambda: opened('/proc/%d/fd/%d' % (pid, fd), os.O_RDONLY))
    trial('mem', lambda: opened('/proc/%d/mem' % pid, os.O_RDONLY))
    libc = ctypes.CDLL(None, use_errno=True)
    class IOV(ctypes.Structure): _fields_ = [('base', ctypes.c_void_p), ('size', ctypes.c_size_t)]
    buf = ctypes.create_string_buffer(b'sentinel')
    for name in ('process_vm_readv', 'process_vm_writev'):
        local, remote = IOV(ctypes.addressof(buf), 1), IOV(address, 1)
        rc = getattr(libc, name)(pid, ctypes.byref(local), 1, ctypes.byref(remote), 1, 0)
        result[name] = 0 if rc >= 0 else ctypes.get_errno()
    pfd = os.pidfd_open(pid)
    got = libc.syscall(438, pfd, fd, 0)
    result['pidfd_getfd'] = 0 if got >= 0 else ctypes.get_errno()
    if got >= 0: os.close(got)
    os.close(pfd)
else:
    trial('read', lambda: opened(store / 'custom.sqlite3', os.O_RDONLY))
    trial('lock', lambda: opened(store / 'authority.lock', os.O_RDONLY))
print(json.dumps(result), flush=True)
''')
        injector = base / 'inject.py'
        injector.write_text(r'''import ctypes, importlib.util, json, os, sys
spec = importlib.util.spec_from_file_location('injected_launch', sys.argv[1])
L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
mode, argv = sys.argv[2], sys.argv[3:]
if mode.startswith('seccomp:'):
    _, step, code = mode.split(':'); code = int(code)
    class Filter(ctypes.Structure): _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte), ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint)]
    class Program(ctypes.Structure): _fields_ = [('len', ctypes.c_ushort), ('filter', ctypes.POINTER(Filter))]
    syscall = {'probe': 444, 'create': 444, 'add': 445, 'restrict': 446}[step]
    # nr at 0, flags (third argument of create) at 32. Only the chosen form is refused.
    ins = [(0x20,0,0,0), (0x15,0,4,syscall), (0x20,0,0,32),
           (0x15,0,1,1 if step == 'probe' else 0), (0x06,0,0,0x50000 | code), (0x06,0,0,0x7fff0000), (0x06,0,0,0x7fff0000)]
    if step == 'create': ins = [(0x20,0,0,0),(0x15,0,7,444),(0x20,0,0,32),(0x15,0,5,0),(0x20,0,0,16),(0x15,0,2,0),(0x20,0,0,20),(0x15,1,0,0),(0x06,0,0,0x50000 | code),(0x06,0,0,0x7fff0000)]
    if step in ('add','restrict'): ins = [(0x20,0,0,0),(0x15,0,1,syscall),(0x06,0,0,0x50000 | code),(0x06,0,0,0x7fff0000)]
    filters = (Filter * len(ins))(*(Filter(*item) for item in ins)); program = Program(len(ins), filters)
    libc = ctypes.CDLL(None, use_errno=True)
    assert libc.prctl(38,1,0,0,0) == 0
    assert libc.prctl(22,2,ctypes.byref(program),0,0) == 0
elif mode == 'enumeration':
    original = L.os.scandir
    def scandir(path):
        if str(path) == '/proc/self/fd': raise PermissionError('fixture')
        return original(path)
    L.os.scandir = scandir
elif mode == 'listing':
    def entries(path): raise PermissionError('fixture')
    L.guard_entries = entries
elif mode == 'inspection':
    original = L.os.readlink
    def readlink(path):
        if str(path) == '/proc/self/fd/2': raise PermissionError('fixture')
        return original(path)
    L.os.readlink = readlink
L.wrap(argv)
''')
        events = []
        class Dispatches:
            state = 'prepared'
            def record(self, dispatch): return {'state': self.state, 'contract_digest': L.D.digest(self.contract)}
            def accept(self, *args, **kwargs): self.state = 'accepted'
            def receipt(self, *args): return 'fixture-acceptance'
            def refuse(self, *args, **kwargs): self.state = 'refused'
            def run(self, *args, **kwargs): self.state = 'running'
            def exit(self, *args, **kwargs): self.state = 'exited'
            def unknown(self, *args, **kwargs): self.state = 'unknown'
        class Receiver(L.Receiver):
            def _recheck(self, *args): pass
            def _login(self, *args): pass
            def _bind(self, *args): pass
            def _space_end(self, *args): pass
            def _remove_run(self): pass
            def _engine_cwd(self, *args): return str(work)
            def _invoke(self, contract, acceptance, adapter):
                if 'flip' in adapter['argv']:
                    adapter = dict(adapter, argv=[*adapter['argv'], self.store_guard['path']])
                if 'attacks' in adapter['argv']:
                    (store / 'custom.sqlite3-journal').write_bytes(b'fixture sentinel')
                self._record(adapter, os.environ)
                return self._contained(contract['dispatch_id'], adapter['argv'], self.environment, cwd=str(work))
            def _reap(self, worker, contract, carry, **kwargs):
                self.worker = worker
                try:
                    output, errors = worker.communicate(timeout=HANG)
                    self.payload_output = output.decode()
                    self.payload_errors = errors.decode() if errors else ''
                    self.supervision = {'cause': None, 'empty': worker.group.discard(worker)}
                    self.committed = self.recorder.close() if self.recorder else None
                    return {'code': worker.returncode, 'deadline_stop': False}
                finally:
                    os.close(worker.heartbeat.fd)
                    worker.group.close()
        counter = [0]
        real_popen = subprocess.Popen
        def launch(mode='simple', *, off=False, kind='project', injection=None, descriptor=None, risky=False, extra=(), receiver_probe=None, client_name=None, filter_errno=None):
            counter[0] += 1
            marker = store / 'store-guard.off'
            if off: marker.write_text('fixture recovery')
            else: marker.unlink(missing_ok=True)
            settings = copy.deepcopy(config)
            settings['receiver_kind'] = 'conversation' if kind == 'conversation' else 'project'
            settings['adapters'] = {'fixture': {'argv': [sys.executable, '-B', str(payload), str(store), str(work), mode, *map(str, extra)]}}
            if risky:
                settings['risky'] = {'installation': True}
                settings['confined_runner'] = {'program': str(ROOT / 'scripts/agent_sandbox.py'), 'config': str(risky_config)}
            contract = dict(dispatch_id='b2-%d-%d' % (os.getpid(), counter[0]), capability={'adapter': 'fixture', 'configuration': {}},
                            subject_kind='conversation' if kind == 'conversation' else 'project',
                            unit='fixture-unit', station='workflow' if kind == 'workflow' else 'build',
                            reservation={'project': 'fixture-project', 'account': 'fixture-account'},
                            input={'context': {}}, deadline=time.time() + HANG, repository='fixture-repository')
            held_events = []
            receiver = Receiver(settings, lambda event: held_events.append(copy.deepcopy(event)))
            if client_name:
                receiver.binding = {'engine': 'codex' if client_name == 'codex' else 'claude_code', 'argv': settings['adapters']['fixture']['argv']}
            receiver.dispatches = Dispatches()
            receiver.dispatches.contract = contract
            receiver.environment = dict(os.environ, HOME=str(work / 'home'), TMPDIR=str(work / 'tmp'))
            for path in (work / 'home', work / 'tmp'):
                path.mkdir(exist_ok=True)
            receiver.payload_output = receiver.payload_errors = ''
            opened = []
            def spawn(argv, **kwargs):
                if '--contained' not in argv:
                    return real_popen(argv, **kwargs)
                argv = list(argv)
                at = argv.index('--contained')
                if injection:
                    argv[at-4:at] = [sys.executable, '-B', str(injector), str(mods / 'control_launch.py'), injection]
                if descriptor:
                    target, flags, slot = descriptor
                    fd = os.open(target, flags)
                    opened.append(fd)
                    if slot in ('stdin', 'stdout', 'stderr'):
                        kwargs[slot] = fd
                    else:
                        kwargs['pass_fds'] = (*kwargs['pass_fds'], fd)
                        if slot == 'setup':
                            at = argv.index('--contained')
                            held = json.loads(argv[at+1]); held['heartbeat_setup'] = fd
                            argv[at+1] = json.dumps(held)
                        elif slot == 'deleted':
                            Path(target).unlink()
                        if mode == 'leak': argv.append(str(fd))
                return real_popen(argv, **kwargs)
            try:
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(L.subprocess, 'Popen', spawn))
                    stack.enter_context(patch.object(L, 'report_end', lambda r, c, e: r.emit(e)))
                    if receiver_probe is not None:
                        organ = L._organ
                        def probe_organ(name):
                            module = organ(name)
                            if name == 'control_clone': module.store_guard_probe = lambda: receiver_probe
                            return module
                        stack.enter_context(patch.object(L, '_organ', probe_organ))
                    if risky:
                        # Same production wrapper, with the runner argv production _spawn constructs.
                        old_invoke = receiver._invoke
                        def risky_invoke(c, a, adapter):
                            adapter = dict(adapter, argv=L.runner_argv(settings, {'runner': 'confined'}, adapter['argv'], work, client_name))
                            return old_invoke(c, a, adapter)
                        receiver._invoke = risky_invoke
                    if filter_errno is not None:
                        if risky:
                            assert L.runner_refusal(settings, {'runner': 'confined'}, receiver.confined_checked) is None
                        class Filter(ctypes.Structure):
                            _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte), ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint)]
                        class Program(ctypes.Structure):
                            _fields_ = [('length', ctypes.c_ushort), ('filters', ctypes.POINTER(Filter))]
                        instructions = [(0x20,0,0,0), (0x15,0,3,444), (0x20,0,0,32), (0x15,0,1,1), (0x06,0,0,0x50000 | filter_errno), (0x06,0,0,0x7fff0000)]
                        filters = (Filter * len(instructions))(*(Filter(*i) for i in instructions))
                        program = Program(len(instructions), filters)
                        libc = ctypes.CDLL(None, use_errno=True)
                        assert libc.prctl(38,1,0,0,0) == 0
                        assert libc.prctl(22,2,ctypes.byref(program),0,0) == 0
                    receiver.launch(contract)
            finally:
                receiver.descriptor_offsets = []
                for fd in opened:
                    with contextlib.suppress(OSError): receiver.descriptor_offsets.append(os.lseek(fd, 0, os.SEEK_CUR))
                    os.close(fd)
                receiver.close()
            return receiver, held_events

        def outcome(receiver): return (receiver.store_guard or {}).get('outcome')
        def state_unchanged(): return digest() == before
        def prepare_attacks():
            for name in ('truncate-ro', 'truncate', 'unlink', 'rename', 'link'):
                (store / ('trial-' + name)).write_bytes(b'sentinel')
            (work / 'empty').mkdir(exist_ok=True)
            (work / 'source').write_bytes(b'source')
            (work / 'outside-link').unlink(missing_ok=True)
            (work / 'outside-link').symlink_to(db)
        # Actual authority protocol, with no enrolled member signature.
        client = L._organ('control_client')
        listener = client.bind(str(store / 'authority.sock'))
        stopped = threading.Event()
        def serve():
            while not stopped.is_set():
                if not select.select([listener], [], [], HANG)[0]: return
                conn, _ = listener.accept()
                with conn:
                    body = conn.recv(65536)
                    if not body: return
                    # Same unsigned-request classification used by Authority.judge.
                    authority = client.Authority('fixture-store', 'fixture-domain', str(db), None, lambda *a: False, 'fixture-host', lambda *a: None)
                    # Full judge requires the signed command envelope; malformed requests stop first.
                    result = authority.judge(json.loads(body), os.getuid())
                    conn.sendall((json.dumps(result) + '\n').encode())
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        try:
            if needed('layout/entries', 'layout/placement', 'launch/abi', 'switch/off'):
                with section('layout/entries', 'layout/placement', 'launch/abi', 'switch/off'):
                    check('layout/entries', 'normal bound socket', preflight()['outcome'] == 'pending')
                    for kind in ('symlink', 'fifo', 'socket', 'nested-socket', 'hardlink'):
                        path = store / ('unexpected-' + kind)
                        sock = None
                        if kind == 'symlink': path.symlink_to(work)
                        elif kind == 'fifo': os.mkfifo(path)
                        elif kind in ('socket', 'nested-socket'):
                            if kind == 'nested-socket': path.mkdir(); path = path / 'authority.sock'
                            sock = socket.socket(socket.AF_UNIX); sock.bind(str(path))
                        else: os.link(db, path)
                        check('layout/entries', kind, preflight().get('reason') == 'invalid_input:layout:entry')
                        if sock: sock.close()
                        path.unlink()
                        if kind == 'nested-socket': path.parent.rmdir()
                    sidecar = store / 'custom.sqlite3-journal'
                    sidecar.unlink(missing_ok=True); sidecar.symlink_to(work / 'journal-outside')
                    check('layout/entries', 'custom database sidecar link', preflight().get('reason') == 'invalid_input:layout:entry')
                    sidecar.unlink()
                    device = store / 'fixture-device'
                    try:
                        os.mknod(device, __import__('stat').S_IFCHR | 0o600, os.makedev(1, 3))
                    except PermissionError as error:
                        print('NOT RUN layout/entries device: errno=' + str(error.errno))
                    else:
                        check('layout/entries', 'device', preflight().get('reason') == 'invalid_input:layout:entry')
                        device.unlink()
                    for name in ('custom.sqlite3', 'custom.sqlite3-wal', 'authority.lock'):
                        outside = work / 'hardlink'; os.link(store / name, outside)
                        check('layout/entries', 'external hardlink ' + name, preflight().get('reason') == 'invalid_input:layout:entry')
                        outside.unlink()
                    for field in ('worktree', 'gitdir', 'common', 'home', 'temporary', 'runtime', 'client_state', 'scratch_parent'):
                        for path in (store, store / 'nested', store.parent):
                            check('layout/placement', field + str(path), preflight(locations=[(field, path, True)]).get('reason') == 'invalid_input:layout:placement')
                    fallback = dict(config); fallback.pop('runs')
                    check('layout/placement', 'actual fallback', preflight(config=fallback).get('reason') == 'invalid_input:layout:runs')
                    check('layout/placement', 'explicit runs without state root', preflight()['outcome'] == 'pending')
                    for reason in ('unsupported_platform', 'landlock_disabled', 'syscall_missing', 'syscall_blocked', 'abi_below_3'):
                        for risky in (False, True):
                            check('launch/abi', reason + str(risky), preflight(risky=risky, probe=dict(platform='x86_64', abi=2, reason=reason)).get('reason') == 'unavailable_service:confinement:store_guard:' + reason)
                    for abi in (3, 4, 5):
                        check('launch/abi', 'risky floor ' + str(abi), preflight(risky=True, probe=dict(platform='x86_64', abi=abi, reason=None)).get('reason') == 'confined_runner_unavailable:landlock_abi_below_6')
                    check('launch/abi', 'risky platform', preflight(risky=True, probe=dict(platform='aarch64', abi=8, reason=None)).get('reason') == 'confined_runner_unavailable:platform')
                    for abi in (3, 8): check('launch/abi', 'default ABI ' + str(abi), preflight(probe=dict(platform='x86_64', abi=abi, reason=None))['outcome'] == 'pending')
                    check('launch/abi', 'risky host', preflight(risky=True)['outcome'] == 'pending')
                    marker = store / 'store-guard.off'; marker.write_text('off')
                    alias = work / 'hardlink'; os.link(db, alias)
                    check('switch/off', 'off bypasses defective layout and ABI', preflight(probe=dict(platform='x86_64', abi=2, reason='abi_below_3'))['outcome'] == 'off')
                    marker.unlink(); alias.unlink()
                    for bad in ('directory', 'symlink'):
                        if bad == 'directory': marker.mkdir()
                        else: marker.symlink_to(work)
                        check('switch/off', bad, preflight().get('reason') == 'invalid_input:layout:switch')
                        if bad == 'directory': marker.rmdir()
                        else: marker.unlink()

            if needed('launch/abi'):
                with section('launch/abi'):
                    for code, reason in ((errno.ENOSYS, 'syscall_missing'), (errno.EPERM, 'syscall_blocked'), (errno.EOPNOTSUPP, 'landlock_disabled')):
                        for risky in (False, True):
                            read_fd, write_fd = os.pipe()
                            pid = os.fork()
                            if pid == 0:
                                os.close(read_fd)
                                try:
                                    receiver, observed = launch(risky=risky, filter_errno=code)
                                    answer = {'guard': receiver.store_guard, 'accepted': any(e['event'] == 'accepted' for e in observed)}
                                except Exception as error: answer = {'error': repr(error)}
                                os.write(write_fd, json.dumps(answer).encode()); os._exit(0)
                            os.close(write_fd)
                            assert select.select([read_fd], [], [], HANG)[0]
                            answer = json.loads(os.read(read_fd, 65536)); os.close(read_fd); os.waitpid(pid, 0)
                            check('launch/abi', 'receiver seccomp ' + reason + str(risky), answer.get('guard', {}).get('reason') == 'unavailable_service:confinement:store_guard:' + reason and not answer.get('accepted'))
                    for abi in (1, 2):
                        receiver, observed = launch(receiver_probe=dict(platform='x86_64', abi=abi, reason='abi_below_3'))
                        check('launch/abi', 'actual launch low ABI ' + str(abi), receiver.store_guard.get('reason', '').endswith('abi_below_3') and not any(e['event'] == 'accepted' for e in observed))
                    for abi in (3, 4, 5):
                        receiver, observed = launch(risky=True, receiver_probe=dict(platform='x86_64', abi=abi, reason=None))
                        check('launch/abi', 'actual risky launch low ABI ' + str(abi), receiver.store_guard.get('reason') == 'confined_runner_unavailable:landlock_abi_below_6' and not any(e['event'] == 'accepted' for e in observed))
                    for abi in (3, 8):
                        receiver, observed = launch(receiver_probe=dict(platform='x86_64', abi=abi, reason=None))
                        check('launch/abi', 'actual launch supported ABI ' + str(abi), outcome(receiver) == 'applied')
            if needed('launch/guard-default', 'launch/ack', 'switch/run-cannot-flip', 'layout/entries'):
                with section('launch/guard-default', 'launch/ack', 'switch/run-cannot-flip', 'layout/entries'):
                    for reason, metric in (
                            ('invalid_input:layout:switch', 'refused_switch'),
                            ('unavailable_service:confinement:store_guard:abi_below_3', 'refused_kernel'),
                            ('confined_runner_unavailable:landlock_abi_below_6', 'refused_risky_floor'),
                            ('invalid_input:layout:mount', 'refused_layout'),
                            ('confined_runner_unavailable:store_source', 'refused_census')):
                        notices = []
                        observer = types.SimpleNamespace(store_guard=dict(state='on', reason=reason), emit=notices.append)
                        L.guard_observe(observer, 'refused')
                        check('launch/ack', 'named metric ' + metric, notices[-1]['metrics'] == {'store_guard_' + metric: 1})
                    for step in ('audit', 'probe', 'create', 'add', 'restrict', 'unreported'):
                        notices = []
                        observer = types.SimpleNamespace(store_guard=dict(state='on'), emit=notices.append)
                        L.guard_observe(observer, 'enforce_failed', step=step)
                        check('launch/ack', 'failure metric ' + step, notices[-1]['metrics'] == {'store_guard_enforce_failed_' + step: 1})
                    for kind in ('project', 'conversation', 'workflow'):
                        prepare_attacks()
                        receiver, observed = launch('attacks', kind=kind)
                        result = json.loads(receiver.payload_output)
                        for child, answers in (('parent', result), ('child', result.get('child', {}))):
                            for name, code in answers.items():
                                if name in ('child', 'socket-refusal'): continue
                                allowed = name in ('work-write', 'home-write', 'tmp-write')
                                check('launch/guard-default', kind + '/' + child + '/' + name,
                                      code == 0 if allowed else code in (errno.EACCES, errno.EXDEV))
                            check('launch/guard-default', 'socket unsigned refusal', answers.get('socket-refusal', {}).get('accepted') is False)
                        check('layout/entries', 'ordinary guarded receiver with serving authority', outcome(receiver) == 'applied')
                        sequence = [e.get('store_guard', {}).get('outcome') for e in observed]
                        accepted = next(i for i, e in enumerate(observed) if e['event'] == 'accepted')
                        applied = next(i for i, e in enumerate(observed) if e.get('store_guard', {}).get('outcome') == 'applied')
                        check('launch/ack', kind + ' pending at acceptance then applied', observed[accepted]['store_guard']['outcome'] == 'pending' and applied > accepted)
                        check('launch/guard-default', 'database bytes unchanged', state_unchanged())
                        control, _ = launch('attacks', kind=kind, off=True)
                        allowed = json.loads(control.payload_output)
                        for child, answers in (('parent', allowed), ('child', allowed.get('child', {}))):
                            for name, code in answers.items():
                                if name not in ('child', 'socket-refusal'):
                                    check('launch/guard-default', kind + '/control/' + child + '/' + name, code == 0)
                            check('launch/guard-default', 'control unsigned refusal', answers.get('socket-refusal', {}).get('reason') == 'malformed_request')
                        (store / 'store-guard.off').unlink(missing_ok=True)
                        check('switch/run-cannot-flip', 'marker absent and next decision on', not (store / 'store-guard.off').exists() and L.RQ.switch(db)['state'] == 'on')
                        for name in ('marker-create', 'marker-link', 'marker-rename', 'store-move', 'parent-move'):
                            check('switch/run-cannot-flip', name, result[name] in (errno.EACCES, errno.EXDEV))
            if needed('switch/run-cannot-flip'):
                with section('switch/run-cannot-flip'):
                    receiver, _ = launch('flip')
                    check('switch/run-cannot-flip', 'write the sampled marker path refused', json.loads(receiver.payload_output)['marker'] == errno.EACCES)
                    following, _ = launch()
                    check('switch/run-cannot-flip', 'next actual launch stays guarded', outcome(following) == 'applied' and json.loads(following.payload_output)['read'] == errno.EACCES)
                    (work / 'store-guard.off').unlink(missing_ok=True)
            if needed('launch/guard-read', 'switch/off'):
                with section('launch/guard-read', 'switch/off'):
                    on, _ = launch('read')
                    off, _ = launch('read', off=True)
                    check('launch/guard-read', 'read-only flock denied before flock', json.loads(on.payload_output)['lock'] == errno.EACCES)
                    check('launch/guard-read', 'unguarded no competing lock holder', json.loads(off.payload_output)['lock'] == 0)
                    check('switch/off', 'off opens fixture lock', outcome(off) == 'off' and json.loads(off.payload_output)['lock'] == 0)
                    (store / 'store-guard.off').unlink()
                    outside = work / 'defective-hardlink'; os.link(db, outside)
                    probe = dict(platform='x86_64', abi=2, reason='abi_below_3')
                    off, observed = launch(off=True, receiver_probe=probe)
                    check('switch/off', 'actual launch with ABI 2 and hardlink while off', outcome(off) == 'off' and json.loads(off.payload_output)['read'] == 0)
                    on, observed = launch(receiver_probe=probe)
                    check('switch/off', 'removing marker restores named refusal', on.store_guard.get('reason', '').endswith('abi_below_3') and not any(e['event'] == 'accepted' for e in observed))
                    outside.unlink()
            if needed('launch/enforce-fail', 'launch/ack'):
                with section('launch/enforce-fail', 'launch/ack'):
                    for step in ('probe', 'create', 'add', 'restrict'):
                        receiver, observed = launch(injection='seccomp:%s:%d' % (step, errno.EPERM))
                        check('launch/enforce-fail', step + ' named, no payload', outcome(receiver) == 'enforce_failed' and receiver.store_guard.get('step') == step and not receiver.payload_output)
                        check('launch/ack', step + ' never applied', not any(e.get('store_guard', {}).get('outcome') == 'applied' for e in observed))
            if needed('launch/descriptors-early', 'launch/descriptors-leaked'):
                with section('launch/descriptors-early', 'launch/descriptors-leaked'):
                    for slot in ('stdout', 'stderr', 'stdin', 'setup'):
                        snapshot = db.read_bytes()
                        receiver, observed = launch(descriptor=(str(db), os.O_RDWR, slot))
                        check('launch/descriptors-early', slot + ' bytes unchanged', db.read_bytes() == snapshot)
                        if slot == 'stdin': check('launch/descriptors-early', 'forbidden stdin never read', receiver.descriptor_offsets == [0])
                        record = Path(L.ER.path(L.ER.directory(receiver.config), receiver.contract['dispatch_id']) + '.store-guard.jsonl')
                        recorded = [json.loads(line)['store_guard'] for line in record.read_text().splitlines()]
                        check('launch/descriptors-early', slot + ' durable audit outcome', recorded[-1].get('outcome') == 'enforce_failed' and recorded[-1].get('step') == 'audit')
                        check('launch/descriptors-early', slot + ' final audit record', outcome(receiver) == 'enforce_failed' and receiver.store_guard.get('step') == 'audit' and not receiver.payload_output and receiver.dispatches.state == 'refused')
                        check('launch/descriptors-early', slot + ' unreported only for forbidden setup', receiver.store_guard.get('unreported') == (slot == 'setup'))
                    outside = work / 'ordinary.log'; outside.touch()
                    receiver, _ = launch(descriptor=(str(outside), os.O_WRONLY, 'stderr'))
                    check('launch/descriptors-early', 'ordinary log succeeds', outcome(receiver) == 'applied')
                    for name, flags, slot in (('custom.sqlite3-wal', os.O_RDWR, 'extra'), ('authority.lock', os.O_RDONLY, 'extra'), ('', os.O_RDONLY, 'extra'), ('deleted', os.O_RDONLY, 'deleted')):
                        target = store / name
                        if slot == 'deleted': target.write_bytes(b'sentinel')
                        receiver, _ = launch('leak', descriptor=(str(target), flags, slot))
                        check('launch/descriptors-leaked', name + ' no inherited payload', outcome(receiver) == 'enforce_failed' and receiver.store_guard.get('step') == 'audit' and not receiver.payload_output and receiver.dispatches.state == 'refused')
                    for injection in ('enumeration', 'inspection', 'listing'):
                        receiver, _ = launch(injection=injection)
                        check('launch/descriptors-leaked', injection, outcome(receiver) == 'enforce_failed' and receiver.store_guard.get('step') == 'audit')
                    receiver, _ = launch()
                    check('launch/descriptors-leaked', 'clean launch', outcome(receiver) == 'applied')
            if needed('launch/engines'):
                with section('launch/engines'):
                    H = load('v359_handoff', mods / 'control_agent_config_handoff.py')
                    for state, expected in (('on', 'danger-full-access'), ('off', 'workspace-write')):
                        extra = {'argv': ['-c', 'sandbox_mode="workspace-write"'], 'files': {H.X.GENERATED_FILE: b'sandbox_mode = "workspace-write"\n'}}
                        H.codex_store_guard(extra, {'state': state})
                        check('launch/engines', state + ' sampled setting wins', extra['argv'][-1] == 'sandbox_mode="%s"' % expected)
                        check('launch/engines', state + ' generated setting', expected.encode() in extra['files'][H.X.GENERATED_FILE])
            if needed('launch/receiver-memory'):
                with section('launch/receiver-memory'):
                    memory = ctypes.create_string_buffer(b'sentinel')
                    fd = os.open(db, os.O_RDONLY)
                    libc = ctypes.CDLL(None, use_errno=True)
                    assert libc.prctl(0x59616d61, -1, 0, 0, 0) == 0  # PR_SET_PTRACER: qualify the unguarded control
                    try:
                        arguments = (os.getpid(), ctypes.addressof(memory), fd)
                        control, _ = launch('memory', off=True, extra=arguments)
                        guarded, _ = launch('memory', extra=arguments)
                        a, b = json.loads(control.payload_output), json.loads(guarded.payload_output)
                        for name in a:
                            if a[name] != 0:
                                check('launch/receiver-memory', name + ' other denying layer errno=' + str(a[name]), b[name] != 0)
                            else:
                                check('launch/receiver-memory', name + ' guarded denial with successful control', b[name] in (errno.EACCES, errno.EPERM))
                    finally: os.close(fd)
            if needed('ruleset/primitive-symlink-out', 'launch/guard-read'):
                with section('ruleset/primitive-symlink-out', 'launch/guard-read'):
                    target = work / 'outside'; target.write_text('outside')
                    link = store / 'points-out'; link.symlink_to(target)
                    code = "import importlib.util,sys,os,fcntl; from pathlib import Path; s=importlib.util.spec_from_file_location('cl',sys.argv[1]); c=importlib.util.module_from_spec(s); s.loader.exec_module(c); c.confine(c.rules([sys.argv[2]], [] if sys.argv[3]=='write' else [sys.argv[2]])); "
                    primitive = subprocess.run([sys.executable, '-B', '-c', code + "print(Path(sys.argv[4]).read_text())", str(mods / 'control_clone.py'), str(store), 'both', str(link)], capture_output=True, text=True, timeout=HANG)
                    check('ruleset/primitive-symlink-out', 'target resolution', primitive.returncode == 0 and primitive.stdout.strip() == 'outside')
                    control = subprocess.run([sys.executable, '-B', '-c', code + "fd=os.open(sys.argv[4],os.O_RDONLY); fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB); print('flock')", str(mods / 'control_clone.py'), str(store), 'write', str(store / 'authority.lock')], capture_output=True, text=True, timeout=HANG)
                    check('launch/guard-read', 'write-only ruleset allows actual flock', control.returncode == 0 and control.stdout.strip() == 'flock')
                    link.unlink()
            if needed('layout/mounts'):
                with section('layout/mounts'):
                    # Filesystem coordinates deliberately differ from namespace paths.
                    mountinfo = '1 0 8:1 /subvolume / rw - ext4 /dev/test rw\n'
                    coordinate = '/subvolume' + str(store)
                    for name, root in (('directory', coordinate), ('ancestor', '/subvolume' + str(store.parent)), ('database', coordinate + '/custom.sqlite3'), ('lock', coordinate + '/authority.lock')):
                        text = mountinfo + '2 1 8:1 %s /alias rw - ext4 /dev/test rw\n' % root
                        check('layout/mounts', name + ' translated alias', preflight(mountinfo=text).get('reason') == 'invalid_input:layout:mount')
                    for text in ('', 'unparseable'):
                        check('layout/mounts', 'unreadable or malformed', preflight(mountinfo=text).get('reason') == 'invalid_input:layout:mount')
                    alias = work / 'store-path'; alias.symlink_to(store)
                    check('layout/mounts', 'resolved symlink store path', preflight(config=dict(config, store=str(alias / db.name)), sample=L.RQ.switch(alias / db.name))['outcome'] == 'pending')
                    alias.unlink()
                    mount_probe = base / 'mount-probe.py'
                    mount_probe.write_text(r'''import ctypes, importlib.util, json, os, sys
from pathlib import Path
libc = ctypes.CDLL(None, use_errno=True)
def call(rc, step):
    if rc: raise OSError(ctypes.get_errno(), step)
try:
    uid, gid = os.getuid(), os.getgid()
    call(libc.unshare(0x10000000), 'user namespace')
    Path('/proc/self/setgroups').write_text('deny')
    Path('/proc/self/uid_map').write_text('%d %d 1' % (uid, uid))
    Path('/proc/self/gid_map').write_text('%d %d 1' % (gid, gid))
    call(libc.unshare(0x20000), 'mount namespace')
    call(libc.mount(None, b'/', None, 16384 | (1 << 18), None), 'private mounts')
except OSError as error:
    print(json.dumps({'not_run': error.strerror, 'errno': error.errno})); sys.exit(0)
spec = importlib.util.spec_from_file_location('mount_launch', sys.argv[1]); L = importlib.util.module_from_spec(spec); spec.loader.exec_module(L)
config = json.loads(sys.argv[2]); store = Path(config['store']).parent
results = []
for index, source in enumerate((store, store.parent, Path(config['store']), store / 'authority.lock')):
    target = Path(config['runs']) / ('bind-' + str(index))
    if source.is_dir(): target.mkdir()
    else: target.touch()
    try:
        call(libc.mount(os.fsencode(source), os.fsencode(target), None, 4096, None), 'bind')
        result = L.guard_preflight(config, L.RQ.switch(config['store']), False, [])
        results.append(result.get('reason'))
    finally:
        libc.umount2(os.fsencode(target), 0)
        if target.is_dir(): target.rmdir()
        else: target.unlink()
print(json.dumps({'results': results}))
''')
                    tested = subprocess.run([sys.executable, '-B', str(mount_probe), str(mods / 'control_launch.py'), json.dumps(config)], capture_output=True, text=True, timeout=HANG)
                    observed = json.loads(tested.stdout) if tested.returncode == 0 else {'not_run': tested.stderr[-500:]}
                    if observed.get('not_run'):
                        check('layout/mounts', 'NOT RUN actual bind namespace: ' + str(observed), False)
                    else:
                        check('layout/mounts', 'actual directory, ancestor, database and lock binds', observed['results'] == ['invalid_input:layout:mount'] * 4)
            if needed('switch/transitions'):
                with section('switch/transitions'):
                    # Keep two production wrappers alive across changes using their stdin pipe.
                    processes = []
                    def surviving(off):
                        marker = store / 'store-guard.off'
                        if off: marker.write_text('off')
                        else: marker.unlink(missing_ok=True)
                        receiver = Receiver(config, lambda e: None)
                        receiver.runner = {'runner': 'default'}
                        receiver.store_guard = preflight()
                        worker = receiver._contained('survivor-%d-%d' % (os.getpid(), len(processes)), [sys.executable, '-B', str(payload), str(store), str(work), 'hold'], dict(os.environ), cwd=str(work))
                        assert select.select([worker.stdout], [], [], HANG)[0]
                        assert json.loads(worker.stdout.readline())['ready']
                        processes.append((receiver, worker))
                        return worker
                    off = surviving(True); on = surviving(False)
                    check('switch/transitions', 'status on after removal', L.RQ.switch(db)['state'] == 'on')
                    following, _ = launch()
                    check('switch/transitions', 'new launch guarded with both survivors alive', outcome(following) == 'applied' and json.loads(following.payload_output)['read'] == errno.EACCES)
                    (store / 'store-guard.off').write_text('off again')
                    for receiver, worker in processes:
                        output, errors = worker.communicate(b'x', timeout=HANG)
                        code = json.loads(output)['read']
                        check('switch/transitions', 'surviving ' + receiver.store_guard['state'], code == (0 if receiver.store_guard['state'] == 'off' else errno.EACCES))
                        worker.group.discard(worker); worker.group.close(); os.close(worker.heartbeat.fd); receiver.close()
                    (store / 'store-guard.off').unlink()
            if needed('launch/risky-census', 'launch/risky-real', 'switch/run-cannot-flip'):
                with section('launch/risky-census', 'launch/risky-real', 'switch/run-cannot-flip'):
                    sandbox = load('v359_runner', ROOT / 'scripts/agent_sandbox.py')
                    risky_config = base / 'risky.json'
                    reuse = base / 'reuse'; reuse.mkdir(mode=0o700)
                    scratch = base / 'scratch'; scratch.mkdir()
                    source_config = json.loads((ROOT / 'scripts/agent_sandbox.json').read_text())
                    source_config['store'] = str(reuse)
                    source_config['seed_files'] = {}
                    for entry in source_config['clients'].values():
                        entry['places'] = {name: [variable, str(base / ('client-' + name))] for name, (variable, default) in entry['places'].items()}
                    risky_config.write_text(json.dumps(source_config))
                    environment = {name: '' for name in ('CODEX_HOME', 'CLAUDE_CONFIG_DIR')}
                    with patch.dict(os.environ, environment):
                        def census(body, client=None):
                            risky_config.write_text(json.dumps(body))
                            return L.guard_census(str(ROOT / 'scripts/agent_sandbox.py'), str(risky_config), str(work), client, str(store), scratch)
                        for client_name in (None, 'claude', 'codex'):
                            actual = census(source_config, client_name)
                            path, prepared = sandbox.policy_module().configuration(risky_config)
                            prepared['deny_read'] = [*prepared.get('deny_read', []), str(sandbox.borrow_root()), *map(str, sandbox.credential_sources(prepared, work))]
                            files = sandbox.client_files(prepared, client_name, work) if client_name else {}
                            extra = [*sandbox.project_roots(prepared), *(source.resolve() for source, _ in files.get('read_links', []) if source.exists())]
                            grants, protected = sandbox.grants_for(prepared, ROOT, work, scratch, path, extra)
                            grants += sandbox.resolver_grants()
                            grants += [(real, sandbox.READ | sandbox.WRITE) for real, _ in sandbox.state_grants(files, [reuse, work, ROOT, *protected, path, *[Path(p).expanduser().resolve() for p in prepared['deny_read']]])]
                            expected = sorted({(str(path), rights) for path, rights in grants})
                            check('launch/risky-census', str(client_name) + ' both-way parity', actual.get('grants') == expected)
                        exposed = copy.deepcopy(source_config); exposed['read_roots'].append(str(store.parent))
                        check('launch/risky-census', 'broad root exposed', census(exposed).get('reason') == 'confined_runner_unavailable:store_reachable')
                        excluded = copy.deepcopy(exposed); excluded['deny_read'].append(str(store))
                        check('launch/risky-census', 'post-exclusion broad root accepted', census(excluded).get('reason') is None)
                        optional = copy.deepcopy(source_config); optional['optional_read_roots'].append(str(base / 'absent-tool'))
                        check('launch/risky-census', 'optional absent', census(optional).get('reason') is None)
                        for kind in ('seed_files', 'credentials', 'read_links'):
                            body = copy.deepcopy(source_config)
                            body['clients']['codex'][kind] = {str(db): '.codex/fixture'}
                            result = census(body, 'codex')
                            expected = 'store_reachable' if kind == 'read_links' else 'store_source'
                            check('launch/risky-census', kind, result.get('reason') == 'confined_runner_unavailable:' + expected)
                        body = copy.deepcopy(source_config); body['seed_files'] = {str(db): 'fixture'}
                        check('launch/risky-census', 'general seed', census(body).get('reason') == 'confined_runner_unavailable:store_source')
                        body = copy.deepcopy(source_config); body['clients']['codex']['places']['unused'] = ['V359_UNUSED', str(store)]
                        check('launch/risky-census', 'unused place not a grant', census(body, 'codex').get('reason') is None)
                        state_home = base / 'client-home'
                        state_home.mkdir(exist_ok=True)
                        for client_name in ('claude', 'codex'):
                            actual = census(source_config, client_name)
                            path, prepared = sandbox.policy_module().configuration(risky_config)
                            prepared['deny_read'] = [*prepared.get('deny_read', []), str(sandbox.borrow_root()), *map(str, sandbox.credential_sources(prepared, work))]
                            files = sandbox.client_files(prepared, client_name, work)
                            extra = [*sandbox.project_roots(prepared), *(source.resolve() for source, _ in files.get('read_links', []) if source.exists())]
                            grants, protected = sandbox.grants_for(prepared, ROOT, work, scratch, path, extra)
                            grants += sandbox.resolver_grants()
                            grants += [(real, sandbox.READ | sandbox.WRITE) for real, _ in sandbox.state_grants(files, [reuse, work, ROOT, *protected, path, *[Path(p).expanduser().resolve() for p in prepared['deny_read']]])]
                            expected = sorted({(str(path), rights) for path, rights in grants})
                            check('launch/risky-census', client_name + ' state created parity', actual.get('grants') == expected and census(source_config, client_name).get('grants') == expected)
                        sentinel = store / 'fixture-sentinel'
                        sentinel.write_text(json.dumps({'fixture': 'B2 fixture sentinel'}))
                        sentinel.chmod(0o600)
                        (store / '.runner-lease').touch(mode=0o600)
                        ordinary_config = risky_config
                        for route in ('read-root', 'read-link', 'configuration', 'general-seed', 'client-seed', 'credential'):
                            body = copy.deepcopy(source_config)
                            target, selected_client = str(sentinel), None
                            reason = 'store_reachable'
                            if route == 'read-root': body['read_roots'].append(str(store.parent))
                            elif route == 'configuration':
                                risky_config = store / 'runner-fixture.json'
                                body['fixture_sentinel'] = 'B2 fixture sentinel'
                                target = str(risky_config)
                            elif route == 'general-seed':
                                body['seed_files'] = {str(sentinel): 'fixture'}
                                target, reason = 'fixture', 'store_source'
                            else:
                                selected_client, target = 'codex', '.codex/fixture'
                                field = {'read-link': 'read_links', 'client-seed': 'seed_files', 'credential': 'credentials'}[route]
                                body['clients']['codex'][field] = {str(sentinel): target}
                                if route != 'read-link': reason = 'store_source'
                            risky_config.write_text(json.dumps(body))
                            refused, observed = launch('route', risky=True, client_name=selected_client, extra=(target,))
                            check('launch/risky-census', route + ' refused before acceptance', refused.store_guard.get('reason') == 'confined_runner_unavailable:' + reason and not any(e['event'] in ('accepted', 'running') for e in observed))
                            companion, observed = launch('route', risky=True, client_name=selected_client, extra=(target,), off=True)
                            if not companion.payload_output: raise RuntimeError(route + ': ' + companion.payload_errors + repr(companion.store_guard))
                            check('launch/risky-census', route + ' unchanged runner exposes sentinel', 'B2 fixture sentinel' in json.loads(companion.payload_output)['sentinel'])
                            if route == 'configuration': risky_config.unlink(); risky_config = ordinary_config
                        body = copy.deepcopy(source_config); body['read_roots'].append(str(base / 'required-missing'))
                        risky_config.write_text(json.dumps(body))
                        refused, observed = launch(risky=True)
                        check('launch/risky-census', 'unresolvable root before acceptance', refused.store_guard.get('reason') == 'confined_runner_unavailable:store_reachable' and not any(e['event'] == 'accepted' for e in observed))
                        companion, observed = launch(risky=True, off=True)
                        check('launch/risky-census', 'unresolvable root companion accepted then runner fails', any(e['event'] == 'accepted' for e in observed) and not companion.payload_output)
                        risky_config.write_text(json.dumps(source_config))
                        receiver, observed = launch(risky=True)
                        result = json.loads(receiver.payload_output)
                        check('launch/risky-real', 'real runner reaches fixture', outcome(receiver) == 'runner_started' and result == {'read': errno.EACCES, 'lock': errno.EACCES})
                        attempts, _ = launch('switch-attempts', risky=True)
                        refused = json.loads(attempts.payload_output)
                        for name, code in refused.items():
                            check('switch/run-cannot-flip', 'risky ' + name, code in (errno.EACCES, errno.EXDEV))
                        following, _ = launch(risky=True)
                        check('switch/run-cannot-flip', 'next risky launch stays guarded', outcome(following) == 'runner_started' and json.loads(following.payload_output)['read'] == errno.EACCES)
            if needed('layout/entries', 'launch/guard-default'):
                with section('layout/entries', 'launch/guard-default'):
                    stopped.set()
                    with socket.socket(socket.AF_UNIX) as wake: wake.connect(str(store / 'authority.sock'))
                    thread.join(HANG); listener.close()
                    stale, _ = launch()
                    check('layout/entries', 'stale authority socket actual launch', outcome(stale) == 'applied')
                    for role in ('direct', 'descendant'):
                        for off in (False, True):
                            socket_path = store / 'authority.sock'
                            if not socket_path.exists():
                                with socket.socket(socket.AF_UNIX) as bound: bound.bind(str(socket_path))
                            receiver, _ = launch('socket-unlink', off=off, extra=(role,))
                            check('launch/guard-default', role + '/socket-unlink/' + str(off), json.loads(receiver.payload_output)['unlink'] == (0 if off else errno.EACCES))
        finally:
            stopped.set()
            with contextlib.suppress(OSError), socket.socket(socket.AF_UNIX) as wake:
                wake.connect(str(store / 'authority.sock'))
            thread.join(HANG)
            listener.close()
        if needed('query/journey'):
            with section('query/journey'):
                environment = dict(os.environ, VELDO_0359_GUARDED_JOURNEY='1')
                tested = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/selftest.py'), '--suite', '157_veldo_0359_run_query'], cwd=ROOT, env=environment, capture_output=True, text=True, timeout=HANG)
                check('query/journey', 'B1 differential client journey under actual ruleset: ' + tested.stderr[-1000:], tested.returncode == 2 and '32 passed, 0 failed' in tested.stdout)
        for name in PRODUCTION:
            check('paths/canon', name, (ROOT / '.veldo' / name).read_bytes() == (ROOT / 'engine/.veldo' / name).read_bytes())
    for row, checks in rows.items():
        failures = [label for label, ok in checks if not ok]
        expect('v359 ' + row + ': ' + ('PASS' if checks and not failures else '; '.join(failures) or 'NOT RUN'), bool(checks) and not failures)


_v359_guard_suite()
