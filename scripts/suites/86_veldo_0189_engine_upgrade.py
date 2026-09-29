"""VELDO-0189: re-running factory setup upgrades an earlier installation's engine in place.

Run: python3 scripts/selftest.py --suite 86_veldo_0189_engine_upgrade

Only shared ROOT and expect are consumed. One temporary tree holds the .veldo copy the suite loads and the
current installer copies its fixed executable from, so a registered mutation of a production file (the setup
module, its upgrade and API steps, the service installer, the scaffolder) reaches every run. The older
engines are the whole .veldo of commit 8bc34e94 (the merge that landed VELDO-0139) and of commit 971186ac
(the landing of VELDO-0155 and VELDO-0156), each taken from the repository's history with `git archive` and
set up by its own setup module; each is its own scratch host with its own state root, install root, unit
directory, host trust and clone. Every path setup writes is scratch. Real: the owner's OpenSSH key made here,
Git clones, 0600 token files, the setup modules' own command surface (main), the installed authority unit's
ExecStart run as the service process by a user manager stand-in of this run's own (Type=notify on its own
socket, a unit's .wants started with it, SIGTERM on stop, a restart that can be made to fail once), whose
invocation log the suite owns, and setup killed with SIGKILL at each write point its upgrade's step log names,
in a process of its own whose systemctl calls reach that same stand-in over a socket. The Tailscale CLI setup
runs is scripts/suites/support/v171_tailscale.py (the host's real Tailscale is never run), the Bot API a
loopback stand-in, and a socket guard refuses every connection beyond 127.0.0.1 in this process and in every
process the suite starts. No real key, token or credential is read; no private key byte, signature or token
is printed.
"""


def _v189_suite():
    import contextlib
    import hashlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import select
    import shlex
    import shutil
    import signal
    import socket
    import sqlite3
    import stat
    import subprocess
    import sys
    import tarfile
    import tempfile
    import threading
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
        'control_factory_setup_upgrade.py': ROOT / ".veldo" / "control_factory_setup_upgrade.py",
        'control_factory_setup_engines.py': ROOT / ".veldo" / "control_factory_setup_engines.py",
        'control_factory_setup_api.py': ROOT / ".veldo" / "control_factory_setup_api.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_store.py': ROOT / ".veldo" / "control_store.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    ROWS = ('install/assets', 'upgrade/from-8bc34e94', 'upgrade/from-971186ac', 'upgrade/removed-module',
            'upgrade/census', 'upgrade/refused-by-name', 'switch/kill-points', 'switch/failed-restart',
            'kept/owner-data', 'announce/before-first-write', 'restart/rules', 'second-run/changes-nothing',
            'switch/failed-after-start', 'ownership/restore-differs', 'ownership/committed',
            'switch/resumed-failure', 'switch/rollback-kills', 'switch/stop-refused',
            'ownership/restore-reported', 'ownership/start-drops', 'ownership/commit-refused',
            'switch/stop-before-restore')
    IA, U8, U9, UR, CN, RF, KP, FR, KD, AN, RS, SR, FA, OD, OC, RE, BK, ST, RP, SD, CR, BS = ROWS
    EQ, RN, PF = 'upgrade/older-0186-equivalence', 'kept/runs', 'upgrade/fresh-0186'
    ROWS += (EQ, RN, PF)
    rows = {name: [] for name in ROWS}
    # The older engines, each the whole .veldo of its commit.
    OLDER = ('8bc34e94', '971186ac')

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    class section:
        """An exception is recorded as a failure of each named row and the run goes on."""

        def __init__(self, *names):
            self.names = names

        def __enter__(self):
            return self

        def __exit__(self, kind, value, trace):
            if kind is not None:
                for name in self.names:
                    check(name, 'the section ran to its end (it raised %s: %s)' % (kind.__name__, str(value)[:300]), False)
            return True

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    started = time.monotonic()
    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    base = Path(tempfile.mkdtemp(prefix='b189-', dir=fast))
    mods = base / 'src' / '.veldo'
    (mods / 'services').mkdir(parents=True)
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        shutil.copyfile(source, mods / source.name)
    for source in sorted((ROOT / '.veldo' / 'services').glob('*.service')):
        shutil.copyfile(source, mods / 'services' / source.name)
    for name, source in PRODUCTION.items():
        target = mods / name
        if target.exists():
            target.unlink()
        if Path(source).is_file():
            shutil.copyfile(source, target)
    fixtures186 = load('v189_install_fixtures', ROOT / 'proof/VELDO-0186/fixtures.py')
    engines186 = fixtures186.install(ROOT, base, mods)
    with (mods / 'control_engine_claude.py').open('a') as handle:
        handle.write("\n_UPGRADE_ASSET = 'runtime/nested/upgrade.json'\n")
    (mods / 'runtime/nested').mkdir()
    (mods / 'runtime/nested/upgrade.json').write_text('{"upgrade": true}\n')
    prior_path186 = os.environ.get('PATH', '')
    os.environ['PATH'] = str(engines186['path']) + os.pathsep + prior_path186
    H = load('v189_support', ROOT / 'scripts' / 'suites' / 'support' / 'v73_authority.py')
    TS = load('v189_tailscale', ROOT / 'scripts' / 'suites' / 'support' / 'v171_tailscale.py')
    _git_process = load('v189_git', mods / 'git_process.py')
    CS = load('v189_service', mods / 'control_service.py')
    CC = load('v189_client', mods / 'control_client.py')
    CEN = load('v189_enrollment', mods / 'control_enrollment.py')
    EL = load('v189_eligibility', mods / 'control_eligibility.py')
    claims = load('v189_claims', mods / 'control_claim.py')
    S = claims.S
    ACC = load('v189_accounts', mods / 'control_accounts.py')
    F = load('v189_setup', mods / 'control_factory_setup.py')
    UP = (load('v189_upgrade', mods / 'control_factory_setup_upgrade.py')
          if (mods / 'control_factory_setup_upgrade.py').is_file() else None)
    CAPTURE = ROOT / 'proof' / 'VELDO-0171' / 'tailscale-capture.json'
    EQUIVALENCE = ROOT / 'proof' / 'VELDO-0189' / 'fresh-equivalence.json'

    # The socket guard of this process: nothing but the loopback interface.
    attempts = []
    real_connect, real_resolve = socket.create_connection, socket.getaddrinfo

    def guarded(address, *args, **kwargs):
        if address[0] != '127.0.0.1':
            attempts.append(str(address[0]))
            raise OSError('suite guard: no network beyond the loopback interface')
        return real_connect(address, *args, **kwargs)

    def resolve(host, *args, **kwargs):
        if host not in ('127.0.0.1', 'localhost', None):
            attempts.append(str(host))
            raise socket.gaierror('suite guard: no name resolution beyond the loopback interface')
        return real_resolve(host, *args, **kwargs)
    socket.create_connection, socket.getaddrinfo = guarded, resolve

    # The same guard, armed in every process the suite starts (the service processes and the killed setups).
    guard_dir, guard_log = base / 'guard', base / 'guard-attempts'
    guard_dir.mkdir()
    (guard_dir / 'sitecustomize.py').write_text(
        'import os, socket\n'
        '_log = os.environ.get("VELDO_V189_GUARD_LOG")\n'
        'def _note(what):\n'
        '    with open(_log, "a") as handle:\n'
        '        handle.write(str(what) + "\\n")\n'
        'def _loopback(sock, address):\n'
        '    return sock.family not in (socket.AF_INET, socket.AF_INET6) or (isinstance(address, tuple) and address[0] == "127.0.0.1")\n'
        '_connect, _connect_ex, _sendto, _resolve = socket.socket.connect, socket.socket.connect_ex, socket.socket.sendto, socket.getaddrinfo\n'
        'def connect(self, address):\n'
        '    if not _loopback(self, address):\n'
        '        _note(address)\n'
        '        raise OSError("guard: no network beyond the loopback interface")\n'
        '    return _connect(self, address)\n'
        'def connect_ex(self, address):\n'
        '    if not _loopback(self, address):\n'
        '        _note(address)\n'
        '        return 111\n'
        '    return _connect_ex(self, address)\n'
        'def sendto(self, data, *rest):\n'
        '    if not _loopback(self, rest[-1]):\n'
        '        _note(rest[-1])\n'
        '        raise OSError("guard: no network beyond the loopback interface")\n'
        '    return _sendto(self, data, *rest)\n'
        'def getaddrinfo(host, *args, **kwargs):\n'
        '    if host not in ("127.0.0.1", "localhost", None):\n'
        '        _note(host)\n'
        '        raise socket.gaierror("guard: no name resolution beyond the loopback interface")\n'
        '    return _resolve(host, *args, **kwargs)\n'
        'if _log:\n'
        '    socket.socket.connect, socket.socket.connect_ex, socket.socket.sendto = connect, connect_ex, sendto\n'
        '    socket.getaddrinfo = getaddrinfo\n')

    def child_env():
        env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': os.environ.get('HOME', str(base)),
               'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'PYTHONDONTWRITEBYTECODE': '1',
               'PYTHONPATH': str(guard_dir), 'VELDO_V189_GUARD_LOG': str(guard_log)}
        if os.environ.get('XDG_RUNTIME_DIR'):
            env['XDG_RUNTIME_DIR'] = os.environ['XDG_RUNTIME_DIR']
        return env

    def child_setup():
        os.umask(0o077)
        with contextlib.suppress(Exception):
            import ctypes
            ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM)

    class Manager:
        """A stand-in for the owner's systemd user manager: start runs a unit's ExecStart (Type=notify waits
        for READY=1) and then every unit its .wants links; stop stops every unit bound to or part of it
        first, with SIGTERM; restart is stop then start, and fails once (the unit left stopped) while
        `fail_restart` is set: before the start, or with `fail_after_start` after the unit came up and was
        stopped again (`came_up` holds that process's pid); show reports the state. `calls` is the invocation log of what setup asked
        for, the suite's own lifecycle actions calling start and stop directly and never appearing in it."""

        def __init__(self, unit_dir):
            self.unit_dir, self.procs, self.calls, self.fail_restart = Path(unit_dir), {}, [], 0
            self.fail_after_start, self.came_up = False, []
            self.fail_stop, self.keep_failed_running, self.after_failed_start = False, False, None
            self.lock = threading.Lock()

        def _field(self, unit, key):
            path = self.unit_dir / unit
            text = path.read_text() if path.is_file() else ''
            return [line.split('=', 1)[1].strip() for line in text.splitlines() if line.startswith(key + '=')]

        def alive(self, unit):
            proc = self.procs.get(unit)
            return proc is not None and proc.poll() is None

        def pid(self, unit):
            return self.procs[unit].pid if self.alive(unit) else None

        def run(self, args):
            with self.lock:
                args = list(args)
                self.calls.append(args)
                unit = args[-1]
                if args[0] == 'show':
                    if not (self.unit_dir / unit).is_file():
                        return 0, 'LoadState=not-found\nActiveState=inactive\nMainPID=0\n', ''
                    alive = self.alive(unit)
                    return 0, ('LoadState=loaded\nActiveState=%s\nSubState=%s\nMainPID=%d\nNRestarts=0\nResult=success\n'
                               % ('active' if alive else 'inactive', 'running' if alive else 'dead',
                                  self.procs[unit].pid if alive else 0)), ''
                if args[0] == 'start':
                    return self.start(unit)
                if args[0] == 'stop':
                    if self.fail_stop:
                        return 1, '', 'stand-in stop refused'
                    self.stop(unit)
                    return 0, '', ''
                if args[0] == 'restart':
                    self.stop(unit)
                    if self.fail_restart:
                        self.fail_restart -= 1
                        if self.fail_after_start:
                            # The reviewer's case: the unit comes up on what is installed, then stops.
                            code, _out, _err = self.start(unit)
                            self.came_up.append(self.pid(unit) if code == 0 else None)
                            if self.after_failed_start:
                                self.after_failed_start()
                            if not self.keep_failed_running:
                                self.stop(unit)
                        return 1, '', 'Job for %s failed (the suite stand-in fails this restart)' % unit
                    return self.start(unit)
                return 0, '', ''

        def start(self, unit):
            if not (self.unit_dir / unit).is_file():
                return 5, '', 'unit not found'
            if any(not self.alive(bound) for bound in self._field(unit, 'BindsTo')):
                return 1, '', 'a unit it binds to is inactive'
            if not self.alive(unit):
                kind = (self._field(unit, 'Type') or ['simple'])[0]
                env = child_env()
                listener, notify = None, None
                if kind == 'notify':
                    notify = base / ('n%d.sock' % os.getpid())
                    with contextlib.suppress(FileNotFoundError):
                        notify.unlink()
                    listener = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                    listener.bind(str(notify))
                    env['NOTIFY_SOCKET'] = str(notify)
                log = base / ('unit-%s.log' % unit[:24])
                with open(log, 'ab') as out:
                    proc = subprocess.Popen(shlex.split(self._field(unit, 'ExecStart')[0]), env=env,
                                            stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                            preexec_fn=child_setup)
                self.procs[unit] = proc
                ready = False
                try:
                    if listener is not None:
                        deadline = time.monotonic() + 30
                        while not ready and proc.poll() is None and time.monotonic() < deadline:
                            if select.select([listener], [], [], 0.2)[0]:
                                ready = b'READY=1' in listener.recv(4096)
                    else:
                        time.sleep(0.3)
                        ready = proc.poll() is None
                finally:
                    if listener is not None:
                        listener.close()
                        notify.unlink()
                if not ready:
                    return 1, '', 'the unit did not start'
            wants = self.unit_dir / (unit + '.wants')
            if wants.is_dir():
                for link in sorted(wants.iterdir()):
                    self.start(link.name)
            return 0, '', ''

        def stop(self, unit):
            for other in sorted(self.unit_dir.glob('*.service')):
                if other.name != unit and unit in self._field(other.name, 'BindsTo') + self._field(other.name, 'PartOf'):
                    self.stop(other.name)
            proc = self.procs.get(unit)
            if proc is not None and proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
                try:
                    proc.wait(15)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(5)

        def stop_all(self):
            for unit in sorted(self.procs):
                self.stop(unit)

        def close(self):
            for proc in self.procs.values():
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(5)

    class Bridge:
        """The stand-in manager reached from a setup running in a process of its own: one JSON line of
        systemctl arguments in, [code, out, err] back, answered by the manager's own run()."""

        def __init__(self, manager, path):
            self.manager, self.path = manager, str(path)
            self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.server.bind(self.path)
            self.server.listen(4)
            self.thread = threading.Thread(target=self.serve, daemon=True)
            self.thread.start()

        def serve(self):
            while True:
                try:
                    conn, _ = self.server.accept()
                except OSError:
                    return
                with conn:
                    data = b''
                    while not data.endswith(b'\n'):
                        chunk = conn.recv(65536)
                        if not chunk:
                            break
                        data += chunk
                    try:
                        answer = list(self.manager.run(json.loads(data)))
                    except Exception as exc:  # noqa: BLE001 - the stand-in answers every call
                        answer = [1, '', 'stand-in error %s' % type(exc).__name__]
                    with contextlib.suppress(OSError):
                        conn.sendall(json.dumps(answer).encode())

        def close(self):
            with contextlib.suppress(OSError):
                self.server.close()

    # The setup run in a process of its own, SIGKILLed right after its upgrade's Nth step-log line (0: never).
    driver = base / 'kill_driver.py'
    driver.write_text(
        'import importlib.util, json, os, signal, socket, sys\n'
        'mods, kill_at, bridge, overrides, argv = sys.argv[1], int(sys.argv[2]), sys.argv[3], json.loads(sys.argv[4]), json.loads(sys.argv[5])\n'
        'spec = importlib.util.spec_from_file_location("v189_killed_setup", os.path.join(mods, "control_factory_setup.py"))\n'
        'F = importlib.util.module_from_spec(spec)\n'
        'spec.loader.exec_module(F)\n'
        'count = [0]\n'
        'organ = F.organ\n'
        'def patched(name):\n'
        '    module = organ(name)\n'
        '    if name == "control_factory_setup_upgrade":\n'
        '        original = module.point\n'
        '        def point(log, entry):\n'
        '            original(log, entry)\n'
        '            count[0] += 1\n'
        '            if count[0] == kill_at:\n'
        '                os.kill(os.getpid(), signal.SIGKILL)\n'
        '        module.point = point\n'
        '    return module\n'
        'F.organ = patched\n'
        'class Runner:\n'
        '    def run(self, args):\n'
        '        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:\n'
        '            conn.connect(bridge)\n'
        '            conn.sendall(json.dumps(list(args)).encode() + b"\\n")\n'
        '            data = b""\n'
        '            while True:\n'
        '                chunk = conn.recv(65536)\n'
        '                if not chunk:\n'
        '                    break\n'
        '                data += chunk\n'
        '        code, out, err = json.loads(data)\n'
        '        return code, out, err\n'
        'overrides["runner"] = Runner()\n'
        'sys.exit(F.main(argv, **overrides))\n')

    def keygen(path, comment):
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', comment, '-f', str(path)], check=True,
                       capture_output=True, timeout=10, stdin=subprocess.DEVNULL)

    def sign_with(path, message, namespace='veldo-command'):
        return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(path), '-n', namespace], input=message,
                              capture_output=True, check=True, timeout=10).stdout.decode()

    def private(path, text, mode=0o600):
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(fd, 'w') as handle:
            handle.write(text)
        os.chmod(str(path), mode)
        return Path(path)

    def clone(name):
        path = base / name
        _git_process.run(['git', 'init', '-q', str(path)], check=True, capture_output=True)
        (path / 'README').write_text('v189 %s\n' % name)
        _git_process.run(['git', '-C', str(path), 'add', 'README'], check=True, capture_output=True)
        _git_process.run(['git', '-C', str(path), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'v189'], check=True,
                         capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        return path

    def digests(directory):
        """{name: (mode, sha256)} of every entry of an engine directory."""
        found = {}
        for path in sorted(Path(directory).rglob('*')):
            info = os.lstat(str(path))
            found[str(path.relative_to(directory))] = (oct(stat.S_IMODE(info.st_mode)), hashlib.sha256(path.read_bytes()).hexdigest()
                                if stat.S_ISREG(info.st_mode) else 'not-a-file')
        return found

    def named(directory):
        """{name: 'sha256:...'} of an engine directory, as an installation record names its files."""
        return {name: 'sha256:' + digest for name, (_mode, digest) in digests(directory).items() if digest != 'not-a-file'}

    def snapshot(*roots):
        """Every file, link and directory under `roots`: its mode and, for a file, its content digest."""
        seen = {}
        for top in roots:
            top = Path(top)
            if not os.path.lexists(str(top)):
                continue
            paths = [str(top)]
            if top.is_dir() and not top.is_symlink():
                for directory, dirs, files in os.walk(str(top)):
                    paths += [os.path.join(directory, name) for name in dirs + files]
            for path in paths:
                info = os.lstat(path)
                digest = None
                if stat.S_ISREG(info.st_mode):
                    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest() if info.st_mode & 0o400 else 'unreadable'
                elif stat.S_ISLNK(info.st_mode):
                    digest = 'link:' + os.readlink(path)
                seen[path] = (stat.S_IMODE(info.st_mode), digest)
        return seen

    def changes(before, after):
        return (sorted(k for k in before if k in after and before[k] != after[k]),
                sorted(k for k in after if k not in before), sorted(k for k in before if k not in after))

    def save(*roots):
        """Every entry under `roots` with its bytes, to lay the trees down again exactly (restore)."""
        entries = {}
        for top in roots:
            for directory, dirs, files in os.walk(str(top)):
                info = os.lstat(directory)
                entries[directory] = ('dir', stat.S_IMODE(info.st_mode), None)
                for name in dirs + files:
                    path = os.path.join(directory, name)
                    info = os.lstat(path)
                    if stat.S_ISLNK(info.st_mode):
                        entries[path] = ('link', 0, os.readlink(path))
                    elif stat.S_ISREG(info.st_mode):
                        entries[path] = ('file', stat.S_IMODE(info.st_mode), Path(path).read_bytes())
        return {'roots': [str(r) for r in roots], 'entries': entries}

    def remove(top):
        if os.path.lexists(str(top)):
            for directory, _dirs, _files in os.walk(str(top)):
                with contextlib.suppress(OSError):
                    os.chmod(directory, 0o700)
            shutil.rmtree(str(top))

    def restore(saved):
        for top in saved['roots']:
            remove(top)
        for path, (kind, mode, data) in sorted(saved['entries'].items()):
            if kind == 'dir':
                os.mkdir(path, 0o700)
            elif kind == 'link':
                os.symlink(data, path)
            else:
                with open(path, 'wb') as handle:
                    handle.write(data)
                os.chmod(path, mode)
        for path, (kind, mode, _data) in sorted(saved['entries'].items(), reverse=True):
            if kind == 'dir':
                os.chmod(path, mode)

    def read_store(store, fn):
        conn = S.open_store(str(store), mode='r')
        try:
            conn.execute('BEGIN')
            try:
                return fn(conn)
            finally:
                conn.execute('ROLLBACK')
        finally:
            conn.close()

    def journal(store):
        return read_store(store, lambda c: S.export_journal(c))

    def recorded_previous(host):
        """The store's record of previous ownership bindings (VELDO-0189), or 'no record kept' when the store
        keeps none."""
        lister = getattr(S, 'previous_owners', None)
        return read_store(host.store, lister) if lister is not None else 'no record kept'

    def ownership_observations(host):
        """The ownership lines of the installation's observation log."""
        path = Path(host.record()['observations'])
        lines = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.is_file() else []
        return [line for line in lines if line.get('kind') == 'ownership']

    def channel_of(host):
        """The running service's channel status from an inspect over its socket."""
        answer = host.send({'operation': 'inspect', 'entity_ids': []})
        channel = (answer.get('result') or {}).get('channel') or {}
        return {k: channel.get(k) for k in ('available', 'refusal') if k in channel} or {'answer': answer.get('reason')}

    def entity_rows(store):
        return read_store(store, lambda c: [list(r) for r in c.execute(
            'SELECT id, kind, version, data FROM entities ORDER BY id')])

    owner = 'dmitry'
    chat = 5590189
    token = 'v189tok' + os.urandom(8).hex()
    bot_user = {'id': 8000000189, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_upgrade_bot'}
    url, bot_api, stop_bot_api = H.stand_in({token: bot_user})
    bot_api['chats'][chat] = {'id': chat, 'type': 'private', 'first_name': 'Owner'}
    person = base / 'person'
    person.mkdir(mode=0o700)
    owner_key = person / 'owner'
    keygen(owner_key, 'v189-owner')
    token_file = private(person / 'bot-token', token + '\n')
    profile = {'kind': 'linux-systemd', 'slice': 'v189%s.slice' % os.urandom(3).hex(), 'lock': str(base / 'workers.lock'),
               'concurrency': 1, 'runtime_seconds': 600, 'memory_bytes': 256 << 20, 'cpu_percent': 100,
               'file_bytes': 64 << 20, 'tasks_max': 256, 'stop_grace_seconds': 1, 'kill_grace_seconds': 1}
    ts = TS.stand_in(CAPTURE, sys.executable) if CAPTURE.is_file() else None
    port = TS.free_port()
    managers, bridges = [], []

    class Host:
        """One scratch host: its own state root, install root, unit directory, host trust and clone."""

        def __init__(self, name):
            self.name = name
            self.clone = clone('clone-' + name)
            self.root = base / ('state-' + name)
            self.root.mkdir(mode=0o700)
            os.chmod(str(self.root), 0o700)
            self.trust = base / ('xdg-' + name) / 'veldo' / 'host_trust.json'
            self.install, self.units = base / ('install-' + name), base / ('units-' + name)
            self.manager = Manager(self.units)
            managers.append(self.manager)
            self.laid = {}

        def argv(self):
            return ['setup', '--state-root', str(self.root), '--owner', owner, '--owner-key', str(owner_key),
                    '--workspace', str(self.clone), '--chat', str(chat), '--token-file', str(token_file)]

        def overrides(self, current=True):
            found = dict(host_trust=str(self.trust), install_root=str(self.install), unit_dir=str(self.units),
                         profile=profile, writable=[], origin=url)
            if current:
                found.update(tailscale=[ts.path], api_port=port)
            return found

        def setup(self, module=None, stderr=None):
            """veldo factory setup through a setup module's own command surface: (exit code, JSON answer)."""
            current = module is None
            out = io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(stderr or io.StringIO()):
                code = (module or F).main(self.argv(), runner=self.manager, **self.overrides(current))
            try:
                shown = json.loads(out.getvalue().strip().splitlines()[-1])
            except (ValueError, IndexError):
                shown = {'unparsed': out.getvalue()[-300:]}
            if code == 0 and 'home' in shown and not self.laid:
                self.laid = shown
            return code, shown

        @property
        def home(self):
            return Path(self.laid['home'])

        @property
        def unit(self):
            return self.laid['unit']

        @property
        def record_path(self):
            return self.home / 'config' / 'service.json'

        def record(self):
            return json.loads(self.record_path.read_text())

        @property
        def store(self):
            return self.root / 'authority' / 'control.sqlite3'

        def binding(self):
            return Path(CEN.binding_path(str(self.clone)))

        def trees(self):
            return (self.root, self.install, self.units, self.trust.parent, self.binding())

        def send(self, packet):
            laid = json.loads((self.root / 'host' / 'ingress.json').read_text())
            trust, workspace = EL.load_host_trust(laid['host_trust']), laid['workspace']
            verify = trust.verifier(owner, workspace)
            try:
                return CC.send(workspace, packet, CEN, verify, lambda data: sign_with(owner_key, data),
                               trust.host_identity, timeout=30)
            except CC.RoutingRefused as exc:
                return {'accepted': False, 'reason': 'routing:' + exc.reason}

        def answers(self):
            return bool(self.send({'operation': 'inspect', 'entity_ids': []}).get('accepted'))

    def older_engine(commit):
        """The whole .veldo of `commit`, from the repository's history with `git archive`, and its setup module."""
        directory = base / ('engine-' + commit)
        directory.mkdir()
        shipped = _git_process.run(['git', '-C', str(ROOT), 'archive', '--format=tar', commit, '.veldo'],
                                   capture_output=True)
        if shipped.returncode or not shipped.stdout:
            return None
        with tarfile.open(fileobj=io.BytesIO(shipped.stdout)) as archive:
            archive.extractall(str(directory), filter='data')
        return load('v189_setup_' + commit, directory / '.veldo' / 'control_factory_setup.py')

    def owner_sets(host):
        """One value in each receiver configuration set as the owner could have (its engine adapters)."""
        chosen = {}
        for path in sorted((host.record().get('receiver') or {}).get('configs', {}).values()):
            held = json.loads(Path(path).read_text())
            held['adapters'] = {'owner-engine': {'argv': ['/bin/true', 'owner-set']}}
            Path(path).write_text(json.dumps(held, indent=1, sort_keys=True) + '\n')
            chosen[path] = held['adapters']
        return chosen

    # AC1: the upgraded host equals a fresh one, after each host's scratch root and identities are
    # substituted and apart from the listed fields.
    equivalence = json.loads(EQUIVALENCE.read_text()) if EQUIVALENCE.is_file() else {}

    def substitutions(host):
        record = host.record()
        repository = sorted(record.get('repositories') or {})
        found = {str(host.root): '@STATE_ROOT@', str(host.install): '@INSTALL_ROOT@', str(host.units): '@UNIT_DIR@',
                 str(host.trust.parent): '@HOST_TRUST_DIR@', str(host.clone): '@CLONE@',
                 record.get('service'): '@SERVICE@', record.get('domain_uuid'): '@DOMAIN@',
                 record.get('store_uuid'): '@STORE@'}
        for uuid in repository:
            found[uuid] = '@REPOSITORY@'
            found[hashlib.sha256(uuid.encode()).hexdigest()[:16]] = '@RECEIVER@'
        return sorted(((k, v) for k, v in found.items() if k), key=lambda kv: -len(kv[0]))

    def substituted(value, table):
        if isinstance(value, dict):
            return {substituted(k, table): substituted(v, table) for k, v in value.items()}
        if isinstance(value, list):
            return [substituted(v, table) for v in value]
        if isinstance(value, str):
            for old, new in table:
                value = value.replace(old, new)
        return value

    def without(value, path):
        """`value` with the field at dotted `path` removed (a listed field)."""
        value = json.loads(json.dumps(value))
        parts = path.split('.')
        parent = value
        for part in parts[:-1]:
            parent = parent.get(part) if isinstance(parent, dict) else None
        if isinstance(parent, dict):
            parent.pop(parts[-1], None)
        return value

    def rendering(host):
        """{name: content} of what AC1 compares: the unit files and link, the record and every configuration
        file, each substituted, the listed fields removed."""
        table = substitutions(host)
        listed = {}
        for field in equivalence.get('fields') or []:
            listed.setdefault(field.get('file'), []).append(field.get('field'))
        found = {}
        for path in sorted(host.units.rglob('*')):
            name = 'units/' + substituted(str(path.relative_to(host.units)), table)
            if path.is_symlink():
                found[name] = 'link:' + substituted(os.readlink(str(path)), table)
            elif path.is_file():
                found[name] = substituted(path.read_text(), table)
        for path in sorted((host.home / 'config').iterdir()):
            name = 'config/' + substituted(path.name, table)
            text = path.read_text()
            try:
                value = substituted(json.loads(text), table)
            except ValueError:
                found[name] = substituted(text, table)
                continue
            for field in listed.get(name, []):
                value = without(value, field)
            found[name] = value
        record = host.root / 'host' / 'engines.json'
        found['host/engines.json'] = substituted(json.loads(record.read_text()), table) if record.is_file() else None
        return found

    def equals_fresh(row, host, fresh, label):
        """AC1's comparison of an upgraded host with a fresh one, every difference named."""
        mine, theirs = digests(host.home / 'bin'), digests(fresh.home / 'bin')
        check(row, '%s: the installed engine directory equals the fresh one in names, bytes and modes [missing %s, '
              'extra %s, differing %s]' % (label, sorted(set(theirs) - set(mine))[:4], sorted(set(mine) - set(theirs))[:4],
                                           sorted(n for n in mine if n in theirs and mine[n] != theirs[n])[:4]),
              mine == theirs and oct(stat.S_IMODE(os.lstat(str(host.home / 'bin')).st_mode))
              == oct(stat.S_IMODE(os.lstat(str(fresh.home / 'bin')).st_mode)))
        pin = Path('engines/claude_code') / engines186['version']
        target, reference = host.root / pin, fresh.root / pin
        check(row, label + ': qualified Claude pin equals fresh bytes and mode',
              target.is_file() and reference.is_file() and target.read_bytes() == reference.read_bytes()
              and stat.S_IMODE(target.stat().st_mode) == stat.S_IMODE(reference.stat().st_mode) == 0o555)
        a, b = rendering(host), rendering(fresh)
        differing = sorted(n for n in set(a) | set(b) if a.get(n) != b.get(n))
        detail = []
        for name in differing[:3]:
            x, y = a.get(name), b.get(name)
            if isinstance(x, dict) and isinstance(y, dict):
                detail.append('%s: %s' % (name, sorted(k for k in set(x) | set(y) if x.get(k) != y.get(k))[:6]))
            else:
                detail.append(name)
        check(row, '%s: the unit files, the record and every configuration file equal the fresh host\'s after each '
              'host\'s scratch root and identities are substituted, apart from the listed fields [%s]' % (label, detail),
              bool(a) and not differing and equivalence.get('fields') is not None
              and sorted(s.get('placeholder') for s in equivalence.get('substituted') or [])
              == sorted({new for _old, new in substitutions(host)})
              and all(f.get('reason') for f in equivalence.get('fields') or []))

    # The kept data of AC3: the key directory, the host trust, the binding, the token file, every registered
    # account's profile directory, the store's rows and every configuration value.
    def kept(host):
        files = {}
        trust = json.loads(host.trust.read_text())
        paths = [host.trust, Path(trust['enrollment_signers']), Path(trust['settlement_signers']), host.binding(),
                 token_file]
        paths += sorted(p for p in (host.root / 'keys').rglob('*') if p.is_file())
        accounts = read_store(host.store, lambda c: [json.loads(r[0]) for r in c.execute(
            'SELECT data FROM entities WHERE kind=?', (ACC.KIND,))])
        for record in accounts:
            for directory in sorted((record.get('profiles') or {}).values()):
                paths += sorted(p for p in Path(directory).rglob('*') if p.is_file())
        for path in paths:
            files[str(path)] = Path(path).read_bytes()
        configs = {}
        for path in sorted((host.home / 'config').iterdir()):
            text = path.read_text()
            try:
                configs[path.name] = json.loads(text)
            except ValueError:
                configs[path.name] = text
        return {'runs': snapshot(host.root / 'authority' / 'runs'), 'files': files, 'journal': journal(host.store), 'entities': entity_rows(host.store), 'configs': configs,
                'accounts': len(accounts)}

    def kept_after(row, host, before, owner_set, label):
        after = kept(host)
        check(row, label + ': existing runs tree unchanged', after['runs'] == before['runs'])
        changed = sorted(p for p, data in before['files'].items() if after['files'].get(p) != data)
        check(row, '%s: every file under the key directory, the host trust and the files it names, the workspace '
              'binding, the token file and every registered account\'s profile directory (%d) is unchanged byte for '
              'byte [%s]' % (label, before['accounts'], changed[:3]), before['files'] and not changed)
        check(row, '%s: every journal row the store held is unchanged, in order and digest [%d of %d]'
              % (label, len(before['journal']), len(after['journal'])),
              after['journal'][:len(before['journal'])] == before['journal'] and before['journal'])
        rows_after = {r[0]: r for r in after['entities']}
        moved = sorted(r[0] for r in before['entities'] if rows_after.get(r[0]) != r)
        new = after['journal'][len(before['journal']):]
        written = {entity for record in new for entity in (record.get('after_versions') or {})}
        check(row, '%s: every entity row the store held is unchanged but those the API steps\' own journal records '
              'wrote after it (VELDO-0171) [%s, written by %s]' % (label, moved[:3], [r.get('command_id') for r in new]),
              before['entities'] and set(moved) <= written
              and all('api-edge' in str(r.get('command_id')) for r in new))
        lost = []
        for name, value in before['configs'].items():
            now = after['configs'].get(name)
            if isinstance(value, dict) and isinstance(now, dict):
                for key, held in value.items():
                    if key in ('closure', 'runtime_assets', 'template') and name == 'service.json':
                        continue
                    if now.get(key) != held and not (held is None and key in now):
                        lost.append('%s:%s' % (name, key))
            elif now != value:
                lost.append(name)
        check(row, '%s: every value in every configuration file under the installation\'s config directory keeps what '
              'was there, the only changes a key the file lacked or held as null and the record\'s engine keys [%s]'
              % (label, lost[:4]), not lost and before['configs'])
        for path, adapters in owner_set.items():
            check(row, '%s: the receiver configuration keeps the owner-set adapters [%s]'
                  % (label, json.loads(Path(path).read_text()).get('adapters')),
                  json.loads(Path(path).read_text()).get('adapters') == adapters)

    def engine_digest(closure, template):
        return 'sha256:' + hashlib.sha256(json.dumps({'closure': closure, 'template': template},
                                                     sort_keys=True).encode()).hexdigest()

    class Witness(io.StringIO):
        """setup's standard error, noting at its first line what had been written by then."""

        def __init__(self, observe):
            super().__init__()
            self.observe, self.first = observe, None

        def write(self, text):
            if self.first is None and text.strip():
                self.first = self.observe()
            return super().write(text)

    try:
        if UP is None or ts is None or 'layout' not in dir(CS):
            for name in ROWS:
                check(name, 'the setup upgrade module, the installer\'s layout and the Tailscale stand-in exist', False)
            raise StopIteration

        # The module travels with the engine.
        with section(IA):
            scaffold = load('v189_scaffold', mods / 'init_scaffold.py')
            rel = '.veldo/control_factory_setup_upgrade.py'
            check(IA, rel + ' installed by the scaffold, not claimed as validator substrate',
                  rel in scaffold._FILES and rel not in scaffold.REQUIRED_SUBSTRATE)
            check(IA, 'the service names the previous engine directory the upgrade keeps beside bin [%s %s]'
                  % (getattr(CS, 'PREVIOUS_ENGINE', None), UP.STAGE), getattr(CS, 'PREVIOUS_ENGINE', None) == UP.STAGE)
            for rel in ('.veldo/control_factory_setup.py', '.veldo/control_factory_setup_upgrade.py',
                        '.veldo/control_service.py', '.veldo/control_store.py', '.veldo/init_scaffold.py'):
                engine = ROOT / 'engine' / rel
                check(IA, rel + ' engine copy identical', engine.is_file() and engine.read_bytes() == (ROOT / rel).read_bytes())

        # The fresh host, set up by the current setup with the same arguments, with the owner's same setting.
        fresh = Host('fresh')
        code, laid = fresh.setup()
        if code != 0:
            for name in ROWS:
                check(name, 'the current setup laid a fresh host down [%s]' % laid.get('reason'), False)
            raise StopIteration
        owner_sets(fresh)
        with section(PF):
            before = snapshot(*fresh.trees())
            code, report = fresh.setup()
            check(PF, 'post-0186 re-run accepts recorded runtime directory: ' + str(report.get('reason')), code == 0)
            check(PF, 'post-0186 re-run writes nothing', snapshot(*fresh.trees()) == before)
        current = named(fresh.home / 'bin')
        current_template = fresh.record()['template']

        # AC1 and AC3 and AC4, over each older engine's host.
        hosts, laid_down = {}, {}
        for commit, row in zip(OLDER, (U8, U9)):
            old = older_engine(commit)
            host = Host('h' + commit)
            code, laid = host.setup(module=old) if old else (None, {})
            if code != 0 or laid.get('outcome') != 'set_up':
                for name in (row, KD, AN, RS, SR) + ((KP, FR, RF) if commit == OLDER[0] else ()):
                    check(name, 'the setup of %s laid a host down [%s]' % (commit, laid.get('reason')), False)
                continue
            hosts[commit] = host
            laid_down[commit] = save(host.root, host.install, host.units, host.trust.parent)
            active = commit == OLDER[1]
            if active:
                # The 971186ac host upgrades with its service running through its unit, on its own engine; the
                # 8bc34e94 host with nothing running.
                host.manager.start(host.unit)
            chosen = owner_sets(host)
            launch = load('v189_runs_' + commit, mods / 'control_launch.py')
            receivers = list(host.record()['receiver']['configs'].values())
            runs_before = {p: launch.runs_root(json.loads(Path(p).read_text())) for p in receivers}
            for place in runs_before.values():
                (Path(place) / 'existing-run').mkdir(parents=True, mode=0o700)
                private(Path(place) / 'existing-run' / 'evidence.json', '{"kept": true}\n')
            before_kept = kept(host)
            record = host.record()
            recorded = record['closure']
            installed_before = named(host.home / 'bin')
            before_trees = snapshot(*host.trees())
            pid_before = host.manager.pid(host.unit)

            def observe(host=host, record_bytes=host.record_path.read_bytes(), trees=before_trees):
                changed, added, removed = changes(trees, snapshot(*host.trees()))
                written = [p for p in changed + added + removed
                           if not p.startswith((str(host.root / 'authority'), str(host.home / 'state')))]
                return {'written': written, 'record_same': host.record_path.read_bytes() == record_bytes}
            witness = Witness(observe)
            calls = len(host.manager.calls)
            ts.set('ready')
            code, report = host.setup(stderr=witness)
            steps = {s.get('step'): s for s in report.get('steps') or []}
            upgrade = steps.get('engine_upgrade') or {}
            with section(row):
                check(row, 'the re-run with the same arguments over the %s host is accepted and upgrades its engine [%s %s]'
                      % (commit, report.get('outcome'), report.get('reason')),
                      code == 0 and report.get('outcome') == 'set_up' and upgrade.get('outcome') == 'done')
                check(row, 'before the upgrade the host held the older engine: the record named %d files and the '
                      'engine directory was exactly those' % len(recorded), installed_before == recorded != current)
                check(row, 'the upgraded engine directory holds control_client_api.py, the API process the older engine '
                      'lacked',
                      'control_client_api.py' not in recorded and (host.home / 'bin' / 'control_client_api.py').is_file()
                      and named(host.home / 'bin').get('control_client_api.py') == current.get('control_client_api.py'))
                equals_fresh(row, host, fresh, commit)
                check(row, 'the record names the current engine: its closure and template are the fresh host\'s',
                      host.record()['closure'] == fresh.record()['closure']
                      and host.record()['template'] == current_template)
                check(row, 'nothing of the switch is left beside the engine directory [%s]'
                      % sorted(p.name for p in host.home.iterdir()),
                      sorted(p.name for p in host.home.iterdir()) == ['bin', 'config', 'state'])
            with section(EQ):
                equals_fresh(EQ, host, fresh, commit)
            with section(RN):
                for path, place in runs_before.items():
                    held = json.loads(Path(path).read_text())
                    check(RN, commit + ': state_root names the factory and runs keeps its previous resolution',
                          held.get('state_root') == str(host.root) and held.get('runs') == place
                          and launch.runs_root(held) == place)
                check(RN, commit + ': existing runs contents and modes unchanged',
                      kept(host)['runs'] == before_kept['runs'] and bool(before_kept['runs']))
            with section(KD):
                kept_after(KD, host, before_kept, chosen, commit)
            with section(AN):
                ran = host.manager.calls[calls:]
                check(AN, '%s: setup printed one plain line to its standard error before its first write [%r %s]'
                      % (commit, witness.getvalue()[:160], witness.first),
                      len(witness.getvalue().strip().splitlines()) == 1 and witness.first is not None
                      and not witness.first['written'] and witness.first['record_same'])
                changed_names = sorted(n for n in recorded if n in current and recorded[n] != current[n])
                added_names = sorted(n for n in current if n not in recorded)
                removed_names = sorted(n for n in recorded if n not in current)
                words = ('Upgrading the installed factory engine: %d files change, %d are new, %d are removed; '
                         % (len(changed_names), len(added_names), len(removed_names)))
                check(AN, '%s: the line names what will change and what the service will do [%s]'
                      % (commit, witness.getvalue().strip()),
                      witness.getvalue().startswith(words) and (
                          'the authority service will restart once.' if active
                          else 'the authority service is not running, so its next start runs the current engine.')
                      in witness.getvalue())
                check(AN, '%s: the engine_upgrade step names the previous and current engine digests and the files '
                      'changed, added and removed [%s %s %s]' % (commit, len(upgrade.get('changed') or []),
                                                                 len(upgrade.get('added') or []),
                                                                 len(upgrade.get('removed') or [])),
                      upgrade.get('previous') == engine_digest(recorded, record['template'])
                      and upgrade.get('current') == engine_digest(current, current_template)
                      and upgrade.get('changed') == changed_names and upgrade.get('added') == added_names
                      and upgrade.get('removed') == removed_names)
            with section(RS):
                restarts = [c for c in ran if c[0] in ('start', 'stop', 'restart')]
                if active:
                    check(RS, 'with the authority unit active, setup restarted it once through systemctl and nothing else '
                          '[%s]' % restarts, restarts == [['restart', host.unit]] and upgrade.get('restart') == 'restarted')
                    check(RS, 'the service answers an inspect over its socket, a new process on the current engine [%s %s]'
                          % (pid_before, host.manager.pid(host.unit)),
                          host.answers() and host.manager.pid(host.unit) not in (None, pid_before))
                else:
                    check(RS, 'with nothing running, setup started and restarted nothing [%s]' % restarts,
                          restarts == [] and upgrade.get('restart') == 'not_running')
                    check(RS, 'the answer says the next start runs the current engine [%s]' % upgrade.get('next'),
                          'next start runs the current engine' in str(upgrade.get('next')))

        # AC4 (declared falsifier): a second run over the upgraded host writes nothing and restarts nothing.
        host = hosts.get(OLDER[1])
        if host is not None:
            with section(SR):
                # The host at rest: the authority and its API unit running, as after the owner's restart.
                host.manager.stop(host.unit)
                host.manager.start(host.unit)
                own = (str(host.root / 'authority'), str(host.home / 'state'), str(host.root / 'api'))

                def trees():
                    return {k: v for k, v in snapshot(*host.trees()).items() if not k.startswith(own)}
                before, head, calls = trees(), journal(host.store), len(host.manager.calls)
                ts.clear()
                code, again = host.setup()
                ran = host.manager.calls[calls:]
                changed, added, removed = changes(before, trees())
                steps = {s.get('step'): s for s in again.get('steps') or []}
                check(SR, 'the second run is accepted, its engine_upgrade already done [%s %s]'
                      % (again.get('outcome'), steps.get('engine_upgrade', {}).get('outcome')),
                      code == 0 and again.get('outcome') == 'already_set_up'
                      and steps.get('engine_upgrade', {}).get('outcome') == 'already_done')
                check(SR, 'every file under the state root, install root, unit directory, host trust and workspace '
                      'binding is byte for byte the same [%s]' % (changed + added + removed)[:4],
                      not (changed or added or removed))
                check(SR, 'the journal head is unchanged', journal(host.store) == head)
                check(SR, 'the invocation log shows no restart, start or stop [%s]'
                      % [c for c in ran if c[0] in ('start', 'stop', 'restart')],
                      not any(c[0] in ('start', 'stop', 'restart') for c in ran))
                host.manager.stop_all()

        # AC1: every installer from 8bc34e94 on writes the closure and template keys the upgrade reads.
        with section(CN):
            import ast
            chain = _git_process.run(['git', '-C', str(ROOT), 'rev-list', '--first-parent', 'HEAD'], capture_output=True,
                                     text=True).stdout.split()
            anchor = _git_process.run(['git', '-C', str(ROOT), 'rev-parse', '--verify', '8bc34e94^{commit}'],
                                      capture_output=True, text=True).stdout.strip()
            check(CN, '8bc34e94 is on the first-parent history of this engine [%d commits]' % len(chain), anchor in chain)
            commits = chain[:chain.index(anchor) + 1] if anchor in chain else []
            main = _git_process.run(['git', '-C', str(ROOT), 'rev-list', '--first-parent', 'main'], capture_output=True,
                                    text=True).stdout.split()
            if anchor in main:
                commits += [c for c in main[:main.index(anchor) + 1] if c not in commits]
            batch = _git_process.run(['git', '-C', str(ROOT), 'cat-file', '--batch-check'], capture_output=True, text=True,
                                     input=''.join('%s:.veldo/control_service.py\n' % c for c in commits)).stdout.splitlines()
            blobs = {}
            for commit, line in zip(commits, batch):
                blobs.setdefault(line.split()[0], []).append(commit)

            def writes_engine_keys(source):
                tree = ast.parse(source)
                functions = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
                if 'install' not in functions:
                    return False
                for name in ('install', 'layout'):
                    for node in ast.walk(functions.get(name) or ast.Module(body=[], type_ignores=[])):
                        if not isinstance(node, ast.Dict):
                            continue
                        keys = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant)}
                        closure, template = keys.get('closure'), keys.get('template')
                        if (isinstance(closure, ast.DictComp) and isinstance(closure.value, ast.Call)
                                and getattr(closure.value.func, 'id', None) == '_digest'
                                and isinstance(template, ast.Call) and getattr(template.func, 'id', None) == '_digest'):
                            return True
                return False
            lacking = []
            for blob, found in sorted(blobs.items()):
                source = _git_process.run(['git', '-C', str(ROOT), 'cat-file', 'blob', blob], capture_output=True,
                                          text=True).stdout if blob != 'missing' else ''
                if not source or not writes_engine_keys(source):
                    lacking += found
            check(CN, 'each of the %d first-parent commits from 8bc34e94 on (%d distinct installers) writes the record\'s '
                  'closure (each file\'s digest) and template digest [%s]' % (len(commits), len(blobs), lacking[:3]),
                  len(commits) > 1 and not lacking)

        # AC2: kill setup at each write point its upgrade's step log names, over the 8bc34e94 host.
        old8 = load('v189_setup_kill', base / ('engine-' + OLDER[0]) / '.veldo' / 'control_factory_setup.py') \
            if (base / ('engine-' + OLDER[0])).is_dir() else None
        if old8 is not None:
            # The older installer's real writer lays down a unit whose template differs today.
            template = base / ('engine-' + OLDER[0]) / '.veldo' / 'services' / 'veldo-authority.service'
            template.write_text(template.read_text() + '\n# earlier installation template\n')
        kill = Host('kill')
        code, laid = kill.setup(module=old8) if old8 else (None, {})
        if code != 0:
            for name in (KP, FR, RF, FA, OC):
                check(name, 'the setup of %s laid the kill host down [%s]' % (OLDER[0], laid.get('reason')), False)
            raise StopIteration
        owner_sets(kill)
        saved = save(kill.root, kill.install, kill.units, kill.trust.parent)
        old_engine = named(kill.home / 'bin')
        old_record = kill.record_path.read_bytes()
        bridge = Bridge(kill.manager, base / 'bridge.sock')
        bridges.append(bridge)
        log = kill.home / 'state' / UP.LOG

        def killed(at):
            """One setup in a process of its own, SIGKILLed right after its upgrade's `at`th write point."""
            done = subprocess.run([sys.executable, '-B', str(driver), str(mods), str(at), bridge.path,
                                   json.dumps(kill.overrides()), json.dumps(kill.argv())], env=child_env(),
                                  capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)
            return done.returncode

        def fresh_start():
            """The kill host as its setup laid it down, its authority running through its unit on its own engine."""
            kill.manager.stop_all()
            restore(saved)
            ts.set('ready')
            kill.manager.start(kill.unit)

        with section(KP, OC):
            fresh_start()
            whole = killed(0)
            points = [json.loads(line).get('point') for line in log.read_text().splitlines()] if log.is_file() else []
            # AC2: the upgrade committed (its restart answered, the previous engine removed), and its service had
            # recorded the previous bindings its rebinding replaced while the previous engine was beside bin.
            seen = ownership_observations(kill)
            rebinds = [o.get('bindings') for o in seen if o.get('operation') == 'ownership_rebind']
            commits = [o.get('bindings') for o in seen if o.get('operation') == 'ownership_commit']
            check(OC, 'the upgraded service rebound the declarations of the owning modules the upgrade changed [%s]'
                  % [len(b or []) for b in rebinds], len(rebinds) == 1 and rebinds[0])
            check(OC, 'the commit dropped exactly the previous bindings that rebinding recorded [%s]'
                  % [len(b or []) for b in commits], commits == rebinds[:1] and commits)
            check(OC, 'the step log records the commit after the previous engine was removed [%s]' % points[-4:],
                  points[-3:] == ['removed_previous', 'committed', 'done'])
            check(OC, 'a committed upgrade has no recorded previous bindings [%s]' % recorded_previous(kill),
                  recorded_previous(kill) == [])
            check(KP, 'an upgrade run to its end names its write points in its step log [%s %s]' % (whole, points),
                  whole == 0 and 'exchanged' in points and points[-1:] == ['done'])
            exchanged = points.index('exchanged') + 1 if 'exchanged' in points else None
            restarted = points.index('restart') + 1 if 'restart' in points else None
            before_points = sum(not one for _label, one in rows[KP])
            for at in range(1, len(points) + 1):
                # The row is red from the first point that fails; the points after it are not run (a defect that
                # writes one point per file would otherwise cost a kill per file).
                if sum(not one for _label, one in rows[KP]) > before_points:
                    check(KP, 'the kill rows stopped at the first point that failed, before point %d' % at, False)
                    break
                fresh_start()
                calls = len(kill.manager.calls)
                code = killed(at)
                name = points[at - 1]
                engine = named(kill.home / 'bin')
                check(KP, 'killed at write point %d (%s): the setup process died by SIGKILL [%s]' % (at, name, code),
                      code == -signal.SIGKILL)
                check(KP, 'killed at %d (%s): the installed engine directory equals exactly one engine\'s digests '
                      '[%s]' % (at, name, 'previous' if engine == old_engine else 'current' if engine == current
                                else 'neither (%d files)' % len(engine)),
                      (engine == old_engine) != (engine == current))
                kill.manager.stop(kill.unit)
                kill.manager.start(kill.unit)
                check(KP, 'killed at %d (%s): the installed control_service.py serve starts on the scratch store and '
                      'answers an inspect over its socket' % (at, name), kill.answers())
                code, report = kill.setup()
                channel = ((kill.send({'operation': 'inspect', 'entity_ids': []}).get('result') or {}).get('channel')
                           or {}) if code else {}
                check(KP, 'killed at %d (%s): a second run is accepted [%s %s; the service\'s channel %s]'
                      % (at, name, report.get('outcome'), report.get('reason'),
                         {k: channel.get(k) for k in ('available', 'refusal') if k in channel}), code == 0)
                equals_fresh(KP, kill, fresh, 'killed at %d (%s), then run again' % (at, name))
                restarts = [c for c in kill.manager.calls[calls:] if c == ['restart', kill.unit]]
                check(KP, 'killed at %d (%s): the service was restarted once across the killed run and the second '
                      '[%d]' % (at, name, len(restarts)), len(restarts) == 1)
                if exchanged is not None and exchanged <= at < (restarted or 0):
                    check(KP, 'killed at %d (%s), after the exchange and before its restart: the second run restarted '
                          'the service [%s]' % (at, name, [s for s in report.get('steps') or []
                                                           if s.get('step') == 'engine_upgrade'][:1]),
                          any(s.get('step') == 'engine_upgrade' and s.get('restart') == 'restarted'
                              for s in report.get('steps') or []))
            check(KP, 'a kill row ran at every point, at least begin, staged, exchanged, record and restart [%s]' % points,
                  {'begin', 'staged', 'exchanged', 'record', 'restart'} <= set(points))
            # The service the upgrade restarted carried the store's ownership declarations to the installed engine's
            # bytes (control_store.rebind_owners from its record), and a digest the file's bytes do not have rebinds
            # nothing (on a copy of the store, so the running service's own is never written).
            installed = {os.path.realpath(str(kill.home / 'bin' / n)): d for n, d in kill.record()['closure'].items()}
            owners = read_store(kill.record()['store_path'], S.entity_owners)
            bound = [r for r in owners if r[4] in installed]
            stale = [(r[1], os.path.basename(r[4])) for r in bound if r[5] != installed[r[4]]]
            check(KP, 'after the upgrades every ownership declaration naming an installed engine file names the digest the '
                  'record holds [%d of %d declarations name one; stale %s]' % (len(bound), len(owners), stale[:3]),
                  bound and not stale)
            copy = base / 'owners-copy.sqlite'
            source = sqlite3.connect('file:%s?mode=ro' % kill.record()['store_path'], uri=True)
            target = sqlite3.connect(str(copy))
            source.backup(target)
            source.close()
            target.close()
            conn = S.open_store(str(copy))
            try:
                module = bound[0][4] if bound else str(kill.home / 'bin' / 'control_channel_activation.py')
                other = 'sha256:' + hashlib.sha256(b'bytes the installed file does not have').hexdigest()
                again = S.rebind_owners(conn, {module: other})
                after = S.entity_owners(conn)
            finally:
                conn.close()
            check(KP, 'a declaration is not rebound to a digest its file\'s bytes do not have [%s]' % again,
                  again == [] and after == owners)

        # AC2 (the review of 2026-09-28): the restart brings the unit up on the current engine, which rebinds the
        # store's ownership declarations to its bytes, and then fails; the switch back runs the current engine's
        # own restore before the previous engine starts, so its channel and every owned command are available.
        def failed_after_start(host, saved, label):
            host.manager.stop_all()
            restore(saved)
            ts.set('ready')
            host.manager.start(host.unit)
            old = named(host.home / 'bin')
            old_record = host.record_path.read_bytes()
            before = channel_of(host)
            check(FA, '%s: before the upgrade the previous engine\'s channel is available [%s]' % (label, before),
                  before.get('available') is True)
            declared = read_store(host.store, S.entity_owners)
            differs = [r for r in declared if os.path.dirname(r[4]) == str(host.home / 'bin')
                       and host.record()['closure'].get(os.path.basename(r[4])) != current.get(os.path.basename(r[4]))]
            host.manager.fail_restart, host.manager.fail_after_start, host.manager.came_up = 1, True, []
            calls = len(host.manager.calls)
            try:
                code, report = host.setup()
            finally:
                host.manager.fail_restart, host.manager.fail_after_start = 0, False
            ran = host.manager.calls[calls:]
            check(FA, '%s: setup refused by name after the restart came up and failed [%s %s; came up %s]'
                  % (label, code, report.get('reason'), host.manager.came_up),
                  code == 1 and report.get('reason') == 'unavailable_service:authority:upgrade_start'
                  and len(host.manager.came_up) == 1 and host.manager.came_up[0])
            check(FA, '%s: the previous engine is back in bin and its record restored byte for byte' % label,
                  named(host.home / 'bin') == old and host.record_path.read_bytes() == old_record)
            seen = ownership_observations(host)
            rebinds = [o.get('bindings') for o in seen if o.get('operation') == 'ownership_rebind']
            restores = [o.get('bindings') for o in seen if o.get('operation') == 'ownership_restore']
            if differs:
                check(FA, '%s: the current engine came up and rebound the %d declarations of the owning modules it '
                      'changed, and the switch back restored exactly those [%s %s]'
                      % (label, len(differs), [len(b or []) for b in rebinds], [len(b or []) for b in restores]),
                      len(rebinds) == 1 and len(rebinds[0] or []) == len(differs) and restores == rebinds)
            steps = [json.loads(line) for line in (host.home / 'state' / UP.LOG).read_text().splitlines()]
            check(FA, '%s: the step log records the switch back and the restore before the previous engine\'s restart '
                  '[%s]' % (label, [(s.get('point'), s.get('outcome')) for s in steps][-4:]),
                  [(s.get('point'), s.get('outcome')) for s in steps if s.get('point') != 'stopped'][-3:]
                  == [('switched_back', None), ('ownership_restore', 'restored'), ('restart', 'previous_engine_restarted')])
            check(FA, '%s: the service was restarted once more, on the previous engine [%s]'
                  % (label, [c for c in ran if c[0] in ('start', 'stop', 'restart')]),
                  [c for c in ran if c[0] == 'restart'] == [['restart', host.unit]] * 2)
            after = channel_of(host)
            check(FA, '%s: the previous engine\'s channel is available [%s]' % (label, after),
                  after.get('available') is True and not after.get('refusal'))
            owners = read_store(host.store, S.entity_owners)
            wrong = [(r[1], os.path.basename(r[4])) for r in owners if S.module_digest(r[4]) != r[5]]
            check(FA, '%s: every owned command is available: each of the %d declarations binds the bytes its file has '
                  'now, the previous engine\'s [%s]' % (label, len(owners), wrong[:3]), owners and not wrong)
            check(FA, '%s: no previous binding is left recorded [%s]' % (label, recorded_previous(host)),
                  recorded_previous(host) == [])
            host.manager.stop_all()

        with section(FA):
            failed_after_start(kill, saved, OLDER[0])
            if OLDER[1] in laid_down:
                failed_after_start(hosts[OLDER[1]], laid_down[OLDER[1]], OLDER[1])
            else:
                check(FA, 'the %s host was laid down' % OLDER[1], False)

        # Each recovery row starts with the real older installer and the real setup writer.
        def fail_next(keep=False):
            kill.manager.fail_restart = 1
            kill.manager.fail_after_start = True
            kill.manager.keep_failed_running = keep

        def clear_failure():
            kill.manager.fail_restart = 0
            kill.manager.fail_after_start = False
            kill.manager.keep_failed_running = False
            kill.manager.fail_stop = False
            kill.manager.after_failed_start = None

        def previous_answers(row, label):
            check(row, label + ': previous engine and original record restored',
                  named(kill.home / 'bin') == old_engine and kill.record_path.read_bytes() == old_record)
            check(row, label + ': previous engine channel available', channel_of(kill).get('available') is True)

        with section(RE):
            for target in ('unit', 'record'):
                fresh_start()
                units_before = snapshot(kill.units)
                at = points.index(target) + 1 if target in points else None
                check(RE, 'the upgrade has a ' + target + ' write point', at is not None)
                if at is None:
                    continue
                check(RE, 'setup killed after ' + target, killed(at) == -signal.SIGKILL)
                # A second begin must not hide the first exchange.
                check(RE, 'the resumed setup killed after its begin', killed(1) == -signal.SIGKILL)
                fail_next()
                code, report = kill.setup()
                clear_failure()
                check(RE, target + ': failed resumed restart refused', code == 1)
                previous_answers(RE, target)
                check(RE, target + ': every original unit restored across runs', snapshot(kill.units) == units_before)
                code, report = kill.setup()
                check(RE, target + ': forward re-run answers before removing previous engine',
                      code == 0 and channel_of(kill).get('available') is True
                      and not (kill.home / UP.STAGE).exists())

        with section(BK):
            fresh_start()
            fail_next()
            killed(0)
            clear_failure()
            back_points = [json.loads(line)['point'] for line in log.read_text().splitlines()]
            begin_back = back_points.index('switched_back') if 'switched_back' in back_points else len(back_points)
            check(BK, 'switch back exposes the stop as a kill point', 'stopped' in back_points)
            for at in range(begin_back + 1, len(back_points) + 1):
                fresh_start()
                fail_next()
                check(BK, 'killed inside switch back at ' + back_points[at-1], killed(at) == -signal.SIGKILL)
                clear_failure()
                calls = len(kill.manager.calls)
                code, report = kill.setup()
                ran = kill.manager.calls[calls:]
                check(BK, 'resume after ' + back_points[at-1] + ' restarts and answers',
                      code == 0 and ['restart', kill.unit] in ran and channel_of(kill).get('available') is True)
                check(BK, 'resume removes stage only after the service answers', not (kill.home / UP.STAGE).exists())

        with section(ST):
            fresh_start()
            fail_next(keep=True)
            kill.manager.fail_stop = True
            code, report = kill.setup()
            check(ST, 'stop failure is refused by name in the owner answer',
                  code == 1 and report.get('reason') == 'unavailable_service:authority:upgrade_stop')
            check(ST, 'stop failure does not attempt ownership restore',
                  not any(json.loads(line)['point'] == 'ownership_restore' for line in log.read_text().splitlines()))
            clear_failure()
            code, report = kill.setup()
            check(ST, 'a re-run after stop failure recovers', code == 0 and channel_of(kill).get('available') is True)

        with section(BS):
            fresh_start()
            fail_next(keep=True)
            code, report = kill.setup()
            clear_failure()
            previous_answers(BS, 'failed restart leaves current service alive')
            check(BS, 'restore ran after a successful stop',
                  any(json.loads(line).get('outcome') == 'restored' for line in log.read_text().splitlines()))

        with section(RP):
            fresh_start()
            fail_next()
            def damage_previous():
                path = kill.home / UP.STAGE / 'control_channel_activation.py'
                os.chmod(path, 0o600)
                path.write_bytes(path.read_bytes() + b'\n# changed previous engine\n')
            kill.manager.after_failed_start = damage_previous
            code, report = kill.setup()
            clear_failure()
            blocked = recorded_previous(kill)
            detail = report.get('detail', '')
            check(RP, 'restore refusal and forward recovery are in the owner answer',
                  code == 1 and 'ownership_restore_differs' in detail and 're-run setup forward' in detail)
            check(RP, 'every blocked ownership row is named in the answer',
                  len(blocked) >= 2 and all(value in detail and module in detail for _, value, module, _, _ in blocked))
            check(RP, 'a refused restore leaves all bindings and records intact',
                  blocked and all(r[5] == next((b[4] for b in blocked if b[0:2] == r[0:2]), r[5])
                                  for r in read_store(kill.store, S.entity_owners)))
            # Restore the edited fixture bytes; the refused transaction itself changes no row.
            path = kill.home / 'bin' / 'control_channel_activation.py'
            path.write_bytes(saved['entries'][str(path)][2])
            os.chmod(path, saved['entries'][str(path)][1])
            code, report = kill.setup()
            check(RP, 're-running setup forward recovers owned commands',
                  code == 0 and channel_of(kill).get('available') is True)

        with section(SD, CR):
            fresh_start()
            at = points.index('restart') + 1 if 'restart' in points else None
            check(CR, 'setup killed after current service answered', at is not None and killed(at) == -signal.SIGKILL)
            before = recorded_previous(kill)
            reply = kill.send({'operation': CS.OWNERSHIP_COMMIT})
            check(CR, 'commit refuses while previous engine is installed and keeps all records [%s]' % reply,
                  (reply.get('accepted') is False or (reply.get('result') or {}).get('ok') is False) and 'previous_engine_installed' in json.dumps(reply)
                  and before and recorded_previous(kill) == before)
            kill.manager.stop_all()
            # Exercise serve's crash recovery after the real setup writer removed the previous engine.
            fresh_start()
            at = points.index('removed_previous') + 1 if 'removed_previous' in points else None
            check(SD, 'setup killed after removing previous engine', at is not None and killed(at) == -signal.SIGKILL)
            before = recorded_previous(kill)
            kill.manager.stop_all()
            kill.manager.start(kill.unit)
            check(SD, 'serve drops previous bindings with no previous engine beside it',
                  before and recorded_previous(kill) == [] and channel_of(kill).get('available') is True)

        # A restore whose previous file bytes do not match is refused by name and leaves the new bindings; each
        # step's observation is written before its commit.
        with section(OD):
            parts = ('rebind_owners', 'restore_owners', 'previous_owners')
            check(OD, 'the store rebinds keeping the previous bindings, restores them and lists them [%s]'
                  % [n for n in parts if not hasattr(S, n)], all(hasattr(S, n) for n in parts))
            if all(hasattr(S, n) for n in parts):
                scratch = base / 'restore-differs'
                scratch.mkdir()
                module = Path(os.path.realpath(str(scratch))) / 'owning_module.py'
                module.write_bytes(b'# the previous engine\n')
                store = str(scratch / 'owners.sqlite3')
                conn = S.open_store(store)
                committed = []

                def seen_by_another(rows):
                    committed.append(read_store(store, S.entity_owners)[0][5])
                try:
                    S.declare_owners(conn, 'v189-owner', kinds={'v189_owned': ['v189_write']}, module=str(module))
                    previous = S.module_digest(str(module))
                    module.write_bytes(b'# the current engine\n')
                    new = S.module_digest(str(module))
                    rebound = S.rebind_owners(conn, {str(module): new}, keep_previous=True, observe=seen_by_another)
                    record = S.previous_owners(conn)
                    check(OD, 'the rebinding recorded the previous binding in its transaction and was observed before its '
                          'commit [%s %s]' % (record, committed),
                          rebound and record == [('kind', 'v189_owned', str(module), previous, new)]
                          and committed == [previous] and S.entity_owners(conn)[0][5] == new)
                    module.write_bytes(b'# neither engine\n')
                    try:
                        S.restore_owners(conn, observe=seen_by_another)
                        refused = None
                    except S.StoreRefused as exc:
                        refused = (exc.code, exc.detail)
                    check(OD, 'a restore whose file does not have the previous bytes is refused by name [%s]' % (refused,),
                          refused is not None and refused[0] == 'ownership_restore_differs' and str(module) in refused[1])
                    check(OD, 'the refused restore leaves the new bindings and the record [%s]' % S.previous_owners(conn),
                          S.entity_owners(conn)[0][5] == new and S.previous_owners(conn) == record
                          and len(committed) == 1)
                    module.write_bytes(b'# the previous engine\n')
                    restored = S.restore_owners(conn, observe=seen_by_another)
                    check(OD, 'with the previous bytes back the restore binds the previous digest, clears the record and is '
                          'observed before its commit [%s %s]' % (restored, committed),
                          restored == record and S.entity_owners(conn)[0][5] == previous and S.previous_owners(conn) == []
                          and committed == [previous, new])
                finally:
                    conn.close()

        # AC2: a restart that fails puts the previous engine back and the service answering on it.
        with section(FR):
            fresh_start()
            kill.manager.fail_restart = 1
            calls = len(kill.manager.calls)
            code, report = kill.setup()
            ran = kill.manager.calls[calls:]
            check(FR, 'setup refused by name after the restart failed [%s %s]' % (code, report.get('reason')),
                  code == 1 and report.get('reason') == 'unavailable_service:authority:upgrade_start')
            check(FR, 'the previous engine is back in bin', named(kill.home / 'bin') == old_engine)
            check(FR, 'its record is restored byte for byte', kill.record_path.read_bytes() == old_record)
            check(FR, 'the service was restarted once more, on the previous engine, and answers [%s]'
                  % [c for c in ran if c[0] == 'restart'],
                  [c for c in ran if c[0] == 'restart'] == [['restart', kill.unit]] * 2 and kill.answers())
            steps = [json.loads(line) for line in log.read_text().splitlines()] if log.is_file() else []
            check(FR, 'the step log records the switch back with its reason [%s]'
                  % [s.get('reason') for s in steps if s.get('point') == 'switched_back'],
                  [s.get('reason') for s in steps if s.get('point') == 'switched_back']
                  == ['unavailable_service:authority:upgrade_start'])
            kill.manager.fail_restart = 0

        # AC1 and AC2: an edited engine file, a file the record does not name, and a filesystem that cannot
        # exchange two directories are each refused by name, writing nothing.
        with section(RF):
            kill.manager.stop_all()

            def refused(prepare, expected, label, undo=None):
                restore(saved)
                path = prepare()
                # The store is read by the re-run's argument checks (its WAL files are SQLite's); its rows are
                # compared instead of its files.
                store_dir = str(kill.root / 'authority')

                def trees():
                    return {k: v for k, v in snapshot(*kill.trees()).items() if not k.startswith(store_dir)}
                before, rows_before = trees(), (journal(kill.store), entity_rows(kill.store))
                witness = io.StringIO()
                try:
                    code, report = kill.setup(stderr=witness)
                finally:
                    if undo:
                        undo()
                changed, added, removed = changes(before, trees())
                check(RF, '%s is refused as %s, writing nothing and printing nothing [%s %s %s]'
                      % (label, expected(path), code, report.get('reason'), (changed + added + removed)[:3]),
                      code == 1 and report.get('reason') == expected(path) and not (changed or added or removed)
                      and (journal(kill.store), entity_rows(kill.store)) == rows_before
                      and not witness.getvalue().strip())

            def edit():
                path = kill.home / 'bin' / 'control_store.py'
                os.chmod(str(path.parent), 0o700)
                os.chmod(str(path), 0o600)
                path.write_bytes(path.read_bytes() + b'# edited by hand\n')
                os.chmod(str(path), 0o400)
                os.chmod(str(path.parent), 0o500)
                return path
            refused(edit, lambda p: 'invalid_input:install_root:differs:' + str(p), 'an installed engine file edited by hand')

            def plant():
                path = kill.home / 'bin' / 'planted.py'
                os.chmod(str(path.parent), 0o700)
                path.write_text('# a file the record does not name\n')
                os.chmod(str(path.parent), 0o500)
                return path
            refused(plant, lambda p: 'invalid_input:install_root:unrecorded:' + str(p), 'a file the record does not name')
            import ctypes
            real_cdll = ctypes.CDLL

            class NoExchange:
                """The C library of a filesystem that refuses RENAME_EXCHANGE: renameat2 fails with EINVAL."""

                def __init__(self, *args, **kwargs):
                    self.real = real_cdll(*args, **kwargs)

                def __getattr__(self, name):
                    if name != 'renameat2':
                        return getattr(self.real, name)

                    class Call:
                        argtypes, restype = None, None

                        def __call__(self, *args):
                            ctypes.set_errno(22)
                            return -1
                    return Call()

            def unexchangeable():
                ctypes.CDLL = NoExchange
                return kill.home

            def exchangeable():
                ctypes.CDLL = real_cdll
            refused(unexchangeable, lambda p: 'unavailable_service:install_root:exchange',
                    'an install root whose filesystem cannot exchange two directories', exchangeable)
        # AC1: a current installation upgraded to an engine derived from the current one without one module it
        # installs; AC4: with the service running outside its unit, setup restarts nothing and names the command.
        with section(UR, RS):
            fixture = base / 'engine-fixture' / '.veldo'
            shutil.copytree(str(mods), str(fixture))
            dropped = 'control_keys_custody.py'
            text = (fixture / 'control_service.py').read_text()
            seeds = "ENTRY_POINTS = ('control_service.py', 'control_launch.py', 'control_keys_custody.py', 'control_client_api.py')"
            check(UR, 'the fixture engine is the current one with %s no longer an entry point and absent' % dropped,
                  text.count(seeds) == 1 and dropped in current)
            (fixture / 'control_service.py').write_text(
                text.replace(seeds, "ENTRY_POINTS = ('control_service.py', 'control_launch.py', 'control_client_api.py')"))
            (fixture / dropped).unlink()
            FX = load('v189_setup_fixture', fixture / 'control_factory_setup.py')
            config = fresh.record_path
            manual = subprocess.Popen([fresh.record()['python'], '-B', str(fresh.home / 'bin' / 'control_service.py'),
                                       'serve', str(config)], env=child_env(), stdin=subprocess.DEVNULL,
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=child_setup)
            try:
                until = time.monotonic() + 20
                up = fresh.answers()
                while not up and manual.poll() is None and time.monotonic() < until:
                    time.sleep(0.2)
                    up = fresh.answers()
                calls = len(fresh.manager.calls)
                out = io.StringIO()
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                    code = FX.main(fresh.argv(), runner=fresh.manager, **fresh.overrides())
                report = json.loads(out.getvalue().strip().splitlines()[-1]) if out.getvalue().strip() else {}
                ran = fresh.manager.calls[calls:]
            finally:
                manual.send_signal(signal.SIGTERM)
                with contextlib.suppress(subprocess.TimeoutExpired):
                    manual.wait(15)
                if manual.poll() is None:
                    manual.kill()
                    manual.wait(5)
            steps = {s.get('step'): s for s in report.get('steps') or []}
            upgrade = steps.get('engine_upgrade') or {}
            fixture_engine = {n: 'sha256:' + hashlib.sha256((fixture / n).read_bytes()).hexdigest()
                              for n in current if n != dropped}
            check(UR, 'the re-run from the fixture engine is accepted and upgrades [%s %s]'
                  % (report.get('outcome'), report.get('reason')), code == 0 and upgrade.get('outcome') == 'done')
            check(UR, 'the removed module is gone from the installed engine and from the record, and the upgrade names '
                  'it removed [%s]' % upgrade.get('removed'),
                  not (fresh.home / 'bin' / dropped).exists() and dropped not in fresh.record()['closure']
                  and upgrade.get('removed') == [dropped])
            check(UR, 'the installed engine is exactly the fixture engine\'s files',
                  named(fresh.home / 'bin') == fixture_engine == dict(fresh.record()['closure'], **fresh.record()['runtime_assets']))
            check(RS, 'with the service running outside its unit (the lock held, the unit inactive) setup restarted '
                  'nothing and names the one command to run [%s %s]' % (up, upgrade.get('next')),
                  up and upgrade.get('restart') == 'not_through_unit'
                  and not any(c[0] in ('start', 'stop', 'restart') for c in ran)
                  and 'systemctl --user start %s' % fresh.unit in str(upgrade.get('next')))

        check(IA, 'no connection beyond the loopback interface was attempted [%s]' % attempts[:3],
              not attempts and not (guard_log.is_file() and guard_log.read_text().strip()))
    except StopIteration:
        pass
    finally:
        os.environ['PATH'] = prior_path186
        socket.create_connection, socket.getaddrinfo = real_connect, real_resolve
        for bridge in bridges:
            bridge.close()
        for manager in managers:
            with contextlib.suppress(Exception):
                manager.close()
        stop_bot_api()
        if ts is not None:
            ts.close()
        remove(base)

    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        if not ok:
            for label, one in observed:
                if not one:
                    print('  VELDO-0189 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0189 %s detail: no check ran' % name)
        expect('VELDO-0189 ' + name, ok)
    print('VELDO-0189 suite seconds: %.3f' % (time.monotonic() - started))


_v189_suite()
