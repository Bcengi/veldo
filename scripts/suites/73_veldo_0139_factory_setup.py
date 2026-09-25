"""VELDO-0139: veldo factory setup lays a real factory down on this host from the owner's own signed commands.

Run: python3 scripts/selftest.py --suite 73_veldo_0139_factory_setup

Only shared ROOT and expect are consumed. One temporary tree holds the .veldo copy the suite loads and the
installer copies its fixed executable from, so a registered mutation of a production file (the setup
module, the scaffolder) reaches the run. Every path the setup writes is scratch: the state roots, the host
trust path (the setup is given it, as XDG_CONFIG_HOME would place it), the install root and the unit
directory. Real: the owner's OpenSSH key generated here, a Git clone, the 0600 token file holding a
stand-in token name, the setup module's own command surface (main) and every organ it orders (store,
membership bootstrap, key projection, chat enrollment, VELDO-0067 edge enrollment, delegation, host trust,
VELDO-0029 enrollment, VELDO-0073 ingress configuration, VELDO-0047 install), then the installed unit's
ExecStart run as the service process by a user manager stand-in of this run's own (Type=notify on its own
socket, SIGTERM on stop), so nothing is installed into or started by the owner's real systemd user
manager; only the installer's host qualification reads it. bin/veldo runs as a separate process for a
refusal (with XDG_CONFIG_HOME and XDG_DATA_HOME pointed at scratch) and for the owner's channel qualify
and activate. Every Bot API exchange goes to a loopback stand-in (scripts/suites/support/v73_authority.py);
a socket guard refuses and counts every connection beyond 127.0.0.1 in this process, and the same guard
is armed in the service process and every process it starts. The real Telegram leg is PENDING and never
counted here. No real key or token file is read; no private key byte, signature or token is printed.
"""


def _v139_suite():
    import contextlib
    import gc
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
    import stat
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
        'control_service_channel.py': ROOT / ".veldo" / "control_service_channel.py",
    }
    ROWS = ('install/assets', 'setup/lays-down', 'refuse/writes-nothing', 'refuse/existing-store',
            'edge/enrolled-with-possession', 'chat/enrolled', 'ingress/configuration', 'token/never-copied',
            'service/starts-inert', 'journey/qualified-and-active', 'genesis/owner-signed',
            'qualification/one-request-across-restart', 'rollback/rerun', 'store/private-and-closed',
            'host-trust/directory-checked', 'qualification/opening-retried')
    IA, LD, RW, ES, EK, CE_, IC, TK, SI, JQ, GO, QR, RB, SP, HD, OR = ROWS
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    class section:
        """An exception is recorded as a failure of each named row and the run goes on."""

        def __init__(self, *names):
            self.names = names

        def __exit__(self, kind, value, trace):
            if kind is not None:
                for name in self.names:
                    check(name, 'the section ran to its end (it raised %s: %s)' % (kind.__name__, str(value)[:300]), False)
            return True

        def __enter__(self):
            return self

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    started = time.monotonic()
    budget = started + 90

    def wait(predicate, seconds=20):
        until = min(time.monotonic() + seconds, budget)
        while True:
            value = predicate()
            if value or time.monotonic() >= until:
                return value
            time.sleep(0.15)

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    base = Path(tempfile.mkdtemp(prefix='b139-', dir=fast))
    mods = base / 'src' / '.veldo'
    (mods / 'services').mkdir(parents=True)
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        shutil.copyfile(source, mods / source.name)
    shutil.copyfile(ROOT / '.veldo' / 'services' / 'veldo-authority.service', mods / 'services' / 'veldo-authority.service')
    for name, source in PRODUCTION.items():
        target = mods / name
        if target.exists():
            target.unlink()
        if Path(source).is_file():
            shutil.copyfile(source, target)
    H = load('v139_support', ROOT / 'scripts' / 'suites' / 'support' / 'v73_authority.py')
    git = load('v139_git', mods / 'git_process.py')
    CS = load('v139_service', mods / 'control_service.py')
    CC = load('v139_client', mods / 'control_client.py')
    CEN = load('v139_enrollment', mods / 'control_enrollment.py')
    EL = load('v139_eligibility', mods / 'control_eligibility.py')
    IN = load('v139_ingress', mods / 'control_channel_ingress.py')
    ACT = load('v139_activation', mods / 'control_channel_activation.py')
    claims = load('v139_claims', mods / 'control_claim.py')
    S, CM, AC = claims.S, claims.CM, claims.AC
    K = load('v139_keys', mods / 'control_keys.py')
    E = load('v139_edge', mods / 'control_channel_enrollment.py')
    F = load('v139_setup', mods / 'control_factory_setup.py') if (mods / 'control_factory_setup.py').is_file() else None
    CH = load('v139_channel', mods / 'control_service_channel.py') if (mods / 'control_service_channel.py').is_file() else None

    # The socket guard of this process: nothing but the loopback interface, every other attempt counted.
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

    # The same guard, armed in the service process and every process it starts.
    guard_dir, guard_log, guard_armed = base / 'guard', base / 'guard-attempts', base / 'guard-armed'
    guard_dir.mkdir()
    (guard_dir / 'sitecustomize.py').write_text(
        'import os, socket\n'
        '_log, _armed = os.environ.get("VELDO_V139_GUARD_LOG"), os.environ.get("VELDO_V139_GUARD_ARMED")\n'
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
        'if _log and _armed:\n'
        '    socket.socket.connect, socket.socket.connect_ex, socket.socket.sendto = connect, connect_ex, sendto\n'
        '    socket.getaddrinfo = getaddrinfo\n'
        '    with open(_armed, "a") as handle:\n'
        '        handle.write("%d\\n" % os.getpid())\n')

    def child_setup():
        os.umask(0o077)
        with contextlib.suppress(Exception):
            import ctypes
            ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM)

    class Manager:
        """A stand-in for the owner's systemd user manager answering the systemctl calls the installer and
        the service's lifecycle functions make: start runs the installed unit's ExecStart as a Type=notify
        service and waits for READY=1, stop sends SIGTERM and waits, show reports the unit's state."""

        def __init__(self, unit_dir):
            self.unit_dir, self.procs, self.calls, self.logs = Path(unit_dir), {}, [], []

        def _exec(self, unit):
            text = (self.unit_dir / unit).read_text()
            line = next(l for l in text.splitlines() if l.startswith('ExecStart='))
            return shlex.split(line[len('ExecStart='):])

        def run(self, args):
            args = list(args)
            self.calls.append(args[0])
            unit = args[-1]
            proc = self.procs.get(unit)
            if args[0] == 'show':
                if not (self.unit_dir / unit).is_file():
                    return 0, 'LoadState=not-found\nActiveState=inactive\nMainPID=0\n', ''
                alive = proc is not None and proc.poll() is None
                return 0, ('LoadState=loaded\nActiveState=%s\nSubState=%s\nMainPID=%d\nNRestarts=0\nResult=success\n'
                           % ('active' if alive else 'inactive', 'running' if alive else 'dead', proc.pid if alive else 0)), ''
            if args[0] == 'start':
                if proc is not None and proc.poll() is None:
                    return 0, '', ''
                notify = base / ('n%d.sock' % len(self.logs))
                listener = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                listener.bind(str(notify))
                log = base / ('service-%d.log' % len(self.logs))
                self.logs.append(log)
                env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': os.environ.get('HOME', str(base)),
                       'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'PYTHONDONTWRITEBYTECODE': '1',
                       'PYTHONPATH': str(guard_dir), 'VELDO_V139_GUARD_LOG': str(guard_log),
                       'VELDO_V139_GUARD_ARMED': str(guard_armed), 'NOTIFY_SOCKET': str(notify)}
                if os.environ.get('XDG_RUNTIME_DIR'):
                    env['XDG_RUNTIME_DIR'] = os.environ['XDG_RUNTIME_DIR']
                with open(log, 'wb') as out:
                    proc = subprocess.Popen(self._exec(unit), env=env, stdin=subprocess.DEVNULL, stdout=out,
                                            stderr=subprocess.STDOUT, preexec_fn=child_setup)
                self.procs[unit] = proc
                ready, deadline = False, time.monotonic() + 30
                try:
                    while not ready and proc.poll() is None and time.monotonic() < deadline:
                        if select.select([listener], [], [], 0.2)[0]:
                            ready = b'READY=1' in listener.recv(4096)
                finally:
                    listener.close()
                    notify.unlink()
                return (0, '', '') if ready else (1, '', 'the service did not report ready')
            if args[0] == 'stop':
                if proc is not None and proc.poll() is None:
                    proc.send_signal(signal.SIGTERM)
                    try:
                        proc.wait(15)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait(5)
                return 0, '', ''
            return 0, '', ''

        def close(self):
            for proc in self.procs.values():
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(5)

    def keygen(path, comment):
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', comment, '-f', str(path)], check=True,
                       capture_output=True, timeout=10, stdin=subprocess.DEVNULL)
        return ' '.join(Path(str(path) + '.pub').read_text().split()[:2])

    def derived(path):
        """The public key of a private key file, derived by ssh-keygen in this process."""
        return ' '.join(subprocess.run(['ssh-keygen', '-y', '-f', str(path)], capture_output=True, text=True,
                                       timeout=10, stdin=subprocess.DEVNULL).stdout.split()[:2])

    def sign_with(path, message, namespace='veldo-command'):
        return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(path), '-n', namespace], input=message,
                              capture_output=True, check=True, timeout=10, stdin=None).stdout.decode()

    def private(path, text, mode=0o600):
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(fd, 'w') as handle:
            handle.write(text)
        os.chmod(str(path), mode)
        return Path(path)

    def clone(name):
        path = base / name
        git.run(['git', 'init', '-q', str(path)], check=True, capture_output=True)
        (path / 'README').write_text('v139 %s\n' % name)
        git.run(['git', '-C', str(path), 'add', 'README'], check=True, capture_output=True)
        git.run(['git', '-C', str(path), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'v139'], check=True,
                capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        return path

    def snapshot(*roots):
        """Every file and directory under `roots`: its mode and, for a file, its content digest."""
        seen = {}
        for top in roots:
            top = Path(top)
            if not os.path.lexists(str(top)):
                continue
            for directory, dirs, files in os.walk(str(top)):
                for name in dirs + files:
                    path = os.path.join(directory, name)
                    info = os.lstat(path)
                    digest = None
                    if stat.S_ISREG(info.st_mode) and info.st_mode & 0o400:
                        with open(path, 'rb') as handle:
                            digest = hashlib.sha256(handle.read()).hexdigest()
                    seen[path] = (stat.S_IMODE(info.st_mode), digest)
            info = os.lstat(str(top))
            seen[str(top)] = (stat.S_IMODE(info.st_mode), None)
        return seen

    def mode_of(path):
        """(mode text, owner uid) of `path`, or None when it is absent."""
        try:
            info = os.lstat(str(path))
        except OSError:
            return None
        return oct(stat.S_IMODE(info.st_mode)), info.st_uid

    def holding(needle, *roots):
        """Every readable file under `roots` whose bytes contain `needle`."""
        found = []
        for top in roots:
            for directory, _dirs, files in os.walk(str(top)):
                for name in files:
                    path = os.path.join(directory, name)
                    with contextlib.suppress(OSError):
                        with open(path, 'rb') as handle:
                            if needle in handle.read():
                                found.append(path)
        return sorted(found)

    owner = 'dmitry'
    owner_user = {'id': 5590139, 'is_bot': False, 'first_name': 'Owner'}
    token = 'v139tok' + os.urandom(8).hex()
    bot_user = {'id': 8000000139, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_setup_bot'}
    url, api, stop_api = H.stand_in({token: bot_user})
    api['chats'][owner_user['id']] = {'id': owner_user['id'], 'type': 'private', 'first_name': 'Owner'}
    person = base / 'person'
    person.mkdir(mode=0o700)
    owner_key = person / 'owner'
    owner_public = keygen(owner_key, 'v139-owner')
    token_file = private(person / 'bot-token', token + '\n')
    profile = {'kind': 'linux-systemd', 'slice': 'v139%s.slice' % os.urandom(3).hex(), 'lock': str(base / 'workers.lock'),
               'concurrency': 1, 'runtime_seconds': 600, 'memory_bytes': 256 << 20, 'cpu_percent': 100,
               'file_bytes': 64 << 20, 'tasks_max': 256, 'stop_grace_seconds': 1, 'kill_grace_seconds': 1}
    manager = Manager(base / 'units')
    unit, home, conn, ing = None, None, None, None

    def setup(tag, state_root, workspace, host_trust, **replace):
        """veldo factory setup through the module's own command surface, into this run's scratch, with the
        user manager stand-in and the loopback origin: (exit code, the one JSON answer)."""
        argv = {'--state-root': str(state_root), '--owner': owner, '--owner-key': str(owner_key),
                '--workspace': str(workspace), '--chat': str(owner_user['id']), '--token-file': str(token_file)}
        argv.update(replace)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = F.main(['setup'] + [x for pair in argv.items() for x in pair], host_trust=str(host_trust),
                          install_root=str(base / 'install'), unit_dir=str(base / 'units'), profile=profile,
                          writable=[], runner=manager, origin=url)
        try:
            shown = json.loads(out.getvalue().strip().splitlines()[-1])
        except (ValueError, IndexError):
            shown = {'unparsed': out.getvalue()[-300:]}
        return code, shown

    try:
        if F is None:
            for name in ROWS:
                check(name, 'veldo factory setup exists in this tree (.veldo/control_factory_setup.py)', False)
            raise StopIteration
        workspace = clone('clone')
        state_root = base / 'state'
        state_root.mkdir(mode=0o700)
        os.chmod(str(state_root), 0o700)
        host_trust = base / 'xdg' / 'veldo' / 'host_trust.json'
        code, report = setup('main', state_root, workspace, host_trust)
        ok = code == 0 and report.get('outcome') == 'set_up'
        store = state_root / 'authority' / 'control.sqlite3'
        keys, host = state_root / 'keys', state_root / 'host'
        if store.is_file():
            conn = S.open_store(str(store))
            CM.attach(S)
            K.attach(S)

        def entity(eid):
            row = conn.execute('SELECT kind, version, data FROM entities WHERE id=?', (eid,)).fetchone()
            return None if row is None else {'kind': row[0], 'version': row[1], 'data': json.loads(row[2])}

        # AC3 (declared falsifier): the genesis is the owner's own enrollment, with the key he named.
        with section(GO):
            journal = S.export_journal(conn) if conn is not None else []
            first = journal[0] if journal else {}
            state = CM.authority_state(S, conn) if conn is not None else {'membership': [], 'keyring': []}
            keyring = [k for k in state['keyring'] if k.get('principal') == owner]
            check(GO, 'the store\'s first journal record is the owner\'s enroll_principal, committed under his name '
                  '[%s %s]' % (first.get('seq'), first.get('principal')),
                  first.get('seq') == 1 and first.get('principal') == owner and 'enroll_principal' in str(first.get('command_id')))
            check(GO, 'the owner\'s one enrolled key is the public key of the private key he named, derived here',
                  [k.get('public_key') for k in keyring] == [owner_public] and derived(owner_key) == owner_public)
            member = next((m for m in state['membership'] if m.get('principal') == owner), {})
            check(GO, 'he is the one person member, holding project_owner and membership_steward over every scope [%s]'
                  % sorted(member.get('roles') or []),
                  member.get('principal_type') == 'person' and {'project_owner', 'membership_steward'} <= set(member.get('roles') or [])
                  and member.get('scope') == '*'
                  and [m.get('principal') for m in state['membership'] if m.get('principal_type') == 'person'] == [owner])
            message = b'v139 genesis probe'
            check(GO, 'a command he signs verifies under the store\'s key for him, and one signed by another key does not',
                  bool(keyring) and AC.ssh_keygen_verify(message, sign_with(owner_key, message),
                                                         AC.allowed_signers_line(owner, keyring[0]['public_key']), owner)[0]
                  and not AC.ssh_keygen_verify(message, sign_with(keys / 'settlement', message) if (keys / 'settlement').is_file() else '',
                                               AC.allowed_signers_line(owner, keyring[0]['public_key']), owner)[0])
        if not ok:
            for name in ROWS:
                if name != GO:
                    check(name, 'veldo factory setup completed over an empty 0700 state root [%s]'
                          % {k: report.get(k) for k in ('outcome', 'reason', 'detail')}, False)
            raise StopIteration
        unit, home = report['unit'], Path(report['home'])
        trust = EL.load_host_trust(str(host_trust))
        binding = CEN.read_binding(str(workspace))

        # AC1: the command, its routing and its module travel with the engine.
        with section(IA):
            scaffold = load('v139_scaffold', mods / 'init_scaffold.py')
            rel = '.veldo/control_factory_setup.py'
            check(IA, rel + ' installed by the scaffold, not claimed as validator substrate',
                  rel in scaffold._FILES and rel not in scaffold.REQUIRED_SUBSTRATE)
            check(IA, rel + ' engine copy identical', (ROOT / 'engine' / rel).is_file()
                  and (ROOT / 'engine' / rel).read_bytes() == (ROOT / rel).read_bytes())
            check(IA, '.veldo/control_service_channel.py engine copy identical',
                  (ROOT / 'engine' / '.veldo' / 'control_service_channel.py').read_bytes()
                  == (ROOT / '.veldo' / 'control_service_channel.py').read_bytes())
            check(IA, 'bin/veldo engine copy identical', (ROOT / 'engine' / 'bin' / 'veldo').read_bytes()
                  == (ROOT / 'bin' / 'veldo').read_bytes())
            check(IA, 'bin/veldo routes factory to the setup module\'s own command surface',
                  '_mod("veldo_cli_factory", ".veldo/control_factory_setup.py")' in (ROOT / 'bin' / 'veldo').read_text()
                  and callable(getattr(F, 'main', None)))
            xdg, data = base / 'cli-xdg', base / 'cli-data'
            done = subprocess.run([sys.executable, '-B', str(ROOT / 'bin' / 'veldo'), 'factory', 'setup', '--state-root',
                                   str(base / 'cli-absent'), '--owner', owner, '--owner-key', str(owner_key),
                                   '--workspace', str(workspace), '--chat', str(owner_user['id']), '--token-file',
                                   str(token_file)], capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL,
                                  env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', XDG_CONFIG_HOME=str(xdg),
                                           XDG_DATA_HOME=str(data)))
            try:
                shown = json.loads(done.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                shown = {'stderr': done.stderr[-300:]}
            check(IA, 'bin/veldo factory setup over an absent state root is refused by name, writing nothing [%s]'
                  % shown.get('reason'), done.returncode == 1 and shown.get('reason') == 'missing_authority:state_root:absent'
                  and not xdg.exists() and not data.exists() and not (base / 'cli-absent').exists())

        # AC1: store, membership, trust, binding and the installed unit, read back.
        with section(LD):
            check(LD, 'the store is under the state root, its directories closed to everyone else',
                  store.is_file() and all(mode_of(state_root / d) == ('0o700', os.getuid())
                                          for d in ('', 'authority', 'keys', 'edge', 'host')))
            check(LD, 'every key the setup generated is a 0600 file of this account',
                  all(mode_of(p) == ('0o600', os.getuid())
                      for p in (keys / 'journal', keys / 'edge-telegram', keys / 'settlement', keys / 'qualification-requester',
                                state_root / 'edge' / 'edge-auth')))
            signers = Path(trust.enrollment_signers).read_text() if trust is not None else ''
            check(LD, 'this host\'s trust names its identity and the owner, with his key, as enrollment signer',
                  trust is not None and trust.host_identity == report.get('host_identity')
                  and signers.split() == [owner, 'namespaces="%s"' % EL.ENROLLMENT_NAMESPACE] + owner_public.split()
                  and mode_of(host_trust) == ('0o600', os.getuid()))
            problems = CEN.verify_binding(str(workspace), binding, trust.verifier(owner, str(workspace)), trust.host_identity)
            check(LD, 'the workspace binding names this store, is enrolled by the owner and verifies under the host trust '
                  '[%s]' % problems, binding is not None and problems == [] and binding.get('enrolled_by') == owner
                  and binding.get('store_path') == os.path.realpath(str(store)))
            service_json = json.loads((home / 'config' / 'service.json').read_text())
            check(LD, 'the authority service is installed through VELDO-0047: its unit, fixed executable and configuration',
                  (base / 'units' / unit).is_file() and (home / 'bin' / 'control_service.py').is_file()
                  and service_json.get('store_path') == binding.get('store_path') and service_json.get('unit') == unit
                  and service_json.get('key_directory') == str(keys))

        # AC1: every refusal is by name and writes nothing anywhere.
        with section(RW):
            def refused(label, expected, state=None, work=None, trust_path=None, row=RW, **replace):
                work = work or clone('w-' + label)
                before = snapshot(base)
                got, shown = setup('refusal', state or (base / 'absent'), work, trust_path or
                                   (base / ('xdg-' + label) / 'veldo' / 'host_trust.json'), **replace)
                after = snapshot(base)
                changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
                check(row, '%s: refused as %s, writing nothing [%s %s]' % (label, expected, shown.get('reason'), changed[:3]),
                      got == 1 and shown.get('outcome') == 'refused' and shown.get('reason') == expected and not changed)

            def root(label, mode=0o700):
                path = base / ('root-' + label)
                path.mkdir()
                os.chmod(str(path), mode)
                return path
            refused('absent', 'missing_authority:state_root:absent', state=base / 'nowhere')
            refused('mode', 'invalid_input:state_root:mode', state=root('mode', 0o755))
            refused('group-readable', 'invalid_input:state_root:mode', state=root('group', 0o750))
            refused('owner', 'invalid_input:state_root:owner', state=Path('/root'))
            link = base / 'root-link'
            link.symlink_to(root('target'))
            refused('symlink', 'invalid_input:state_root:symlink', state=link)
            held = root('trust')
            (held / 'host').mkdir(mode=0o700)
            private(held / 'host' / 'enrollment_signers', 'someone namespaces="veldo-enrollment" %s\n' % owner_public)
            refused('trust', 'invalid_input:state_root:holds_trust', state=held)
            other = root('other')
            private(other / 'notes', 'kept\n')
            refused('other', 'invalid_input:state_root:holds_other', state=other)
            # Filed 5: an empty host/ left by a removed factory is named for what it is, not a trust.
            leftover = root('empty-host')
            (leftover / 'host').mkdir(mode=0o700)
            refused('empty-host', 'invalid_input:state_root:holds_empty_host', state=leftover)
            refused('host-trust-exists', 'invalid_input:host_trust:exists', state=root('trust-exists'), trust_path=host_trust)
            refused('enrolled-workspace', 'invalid_input:workspace:enrolled', state=root('enrolled'), work=workspace)
            loose = private(base / 'loose-token', token + '\n', 0o644)
            refused('loose-token', 'invalid_input:token_file:unusable', state=root('loose'), **{'--token-file': str(loose)})
            refused('chat', 'invalid_input:chat:not_a_user_id', state=root('chat'), **{'--chat': '0'})
            refused('owner-key', 'invalid_input:owner_key:unreadable', state=root('key'), **{'--owner-key': str(token_file)})
            refused('service-name', 'invalid_input:owner:name', state=root('name'), **{'--owner': 'authority'})

        # AC1 (declared falsifier): a second setup over the state root of the first never touches its store.
        with section(ES):
            kept = store.read_bytes()
            before = snapshot(base)
            second = clone('second')
            before.update({k: v for k, v in snapshot(second).items()})
            got, shown = setup('again', state_root, second, base / 'xdg-again' / 'veldo' / 'host_trust.json')
            after = snapshot(base)
            changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
            check(ES, 'setup over a state root that holds a store is refused by name [%s]' % shown.get('reason'),
                  got == 1 and shown.get('reason') == 'invalid_input:state_root:holds_store')
            check(ES, 'the existing store is byte-identical and nothing else was written [%s]' % changed[:3],
                  store.read_bytes() == kept and not changed and CEN.read_binding(str(second)) is None)

        # AC2: the edge key in the protected key directory, enrolled by the owner with its possession proof.
        with section(EK):
            record = E.edge_record(CM.authority_state(S, conn), E.edge_key_id('telegram_chat')) or {}
            edge_key = keys / E.edge_key_id('telegram_chat')
            check(EK, 'the edge key is a 0600 file in the protected key directory, and its record is that key',
                  edge_key.is_file() and mode_of(edge_key) == ('0o600', os.getuid())
                  and record.get('public_key') == derived(edge_key)
                  and record.get('connection_public_key') == derived(state_root / 'edge' / 'edge-auth'))
            proof = record.get('possession') or {}
            check(EK, 'enrolled by the owner, its possession proof the edge key\'s own signature over the enrollment envelope',
                  record.get('enrolled_by') == owner and (proof.get('envelope') or {}).get('principal') == owner
                  and AC.ssh_keygen_verify(AC.canonical_envelope_bytes(proof.get('envelope') or {}), proof.get('signature') or '',
                                           AC.allowed_signers_line(record.get('principal'), record.get('public_key'),
                                                                   E.POSSESSION_NAMESPACE),
                                           record.get('principal'), E.POSSESSION_NAMESPACE)[0])
            secret = edge_key.read_bytes() if edge_key.is_file() else None
            check(EK, 'the edge private key exists nowhere but the protected key directory, which the signer names',
                  secret is not None and holding(secret, state_root, home, base / 'units', host_trust.parent, CEN.git_common_dir(str(workspace)))
                  == [str(edge_key)] and json.loads((host / 'signer.json').read_text()).get('key_directory') == str(keys))

        # AC2: the owner's chat, from the chat id he gave.
        with section(CE_):
            found = entity('channel-enrollment:telegram_chat:%s' % owner) or {}
            data = found.get('data') or {}
            P = load('v139_projection', mods / 'control_channel_projection.py')
            check(CE_, 'his chat enrollment names him and the chat id he gave, current [%s]' % data.get('chat_id'),
                  found.get('kind') == 'channel_enrollment' and data.get('principal') == owner
                  and data.get('chat_id') == owner_user['id'] and data.get('revoked_at') is None
                  and not P.enrollment_problems(found.get('kind'), data, owner))

        # AC2: the 0600 ingress configuration, naming the token file, copied by the installer.
        with section(IC):
            config_path = host / 'ingress.json'
            try:
                config = IN.load_config(str(config_path))
            except IN.Refused as exc:
                config = {'refused': exc.code}
            check(IC, 'the ingress configuration is a 0600 VELDO-0073 configuration naming the account\'s own token file',
                  mode_of(config_path) == ('0o600', os.getuid())
                  and (config.get('bot_api') or {}).get('token_file') == str(token_file)
                  and (config.get('bot_api') or {}).get('origin') == url and config.get('store_path') == str(store))
            copied = home / 'config' / 'channel-ingress.json'
            service_json = json.loads((home / 'config' / 'service.json').read_text())
            check(IC, 'the installer copied it 0600 into the protected configuration the service runs',
                  copied.is_file() and mode_of(copied) == ('0o600', os.getuid())
                  and copied.read_bytes() == config_path.read_bytes() and service_json.get('channel_ingress') == str(copied))

        # AC2: the service starts inert, and setup itself started nothing.
        with section(SI):
            check(SI, 'setup started nothing: the user manager was asked only to reload [%s]' % manager.calls,
                  manager.calls == ['daemon-reload'] and not manager.procs)
        began = CS.start(unit, manager)
        verify = trust.verifier(owner, str(workspace))

        def status():
            try:
                answer = CC.send(str(workspace), {'operation': 'inspect', 'entity_ids': []}, CEN, verify,
                                 lambda data: sign_with(owner_key, data), trust.host_identity, timeout=30)
            except CC.RoutingRefused as exc:
                return {'refused': exc.reason}
            return dict((answer.get('result') or {}).get('channel') or {}, _answer=bool(answer.get('accepted')))

        def passes(n):
            first = status().get('passes')
            if not isinstance(first, int):
                return False
            return bool(wait(lambda: (status().get('passes') or 0) >= first + n, 15))

        with section(SI):
            ran = passes(3)
            now = status()
            check(SI, 'the installed service started through its lifecycle and runs the channel with no record [%s]'
                  % {k: now.get(k) for k in ('available', 'refusal', 'record')},
                  began.get('ActiveState') == 'active' and now.get('available') is True and now.get('record') is None)
            check(SI, 'inert: each pass refused as not_activated, the platform never asked [%s %s]'
                  % ((now.get('last_pass') or {}).get('reason'), api['calls']),
                  ran and (now.get('last_pass') or {}).get('reason') == 'not_activated' and api['calls'] == [])

        def veldo(action, *extra):
            done = subprocess.run([sys.executable, '-B', str(ROOT / 'bin' / 'veldo'), 'channel', action, '--principal', owner,
                                   '--key', str(owner_key), '--workspace', str(workspace), '--host-trust', str(host_trust)]
                                  + list(extra), capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL,
                                  env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            try:
                return done.returncode, json.loads(done.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                return done.returncode, {'unparsed': done.stdout[-200:], 'stderr': done.stderr[-300:]}

        # AC3: the live qualification journey on the factory setup laid down, against the stand-in.
        with section(JQ):
            rc, shown = veldo('qualify', '--minutes', '15')
            check(JQ, 'bin/veldo channel qualify, signed by the owner\'s key, is applied by the running service [%s]'
                  % {k: shown.get(k) for k in ('outcome', 'state', 'reason')},
                  rc == 0 and shown.get('outcome') == 'accepted' and shown.get('state') == 'qualifying')
            # From here only shipped commands act: the running service opens the run's one qualification
            # request as the requester setup enrolled and presents it; the owner replies in his chat.
            bot = api['bots'][token]

            def presented():
                return sorted(mid for (chat, mid), m in list(bot['messages'].items())
                              if chat == owner_user['id'] and m['from']['id'] == bot_user['id'])
            sent = wait(presented, 20) or []
            run = status().get('run') or {}
            request = run.get('request') or {}
            rid = request.get('request_id')
            opened = ((entity(rid) or {}).get('data') or {}) if rid else {}
            check(JQ, 'the running service opened the run\'s one qualification request as the requester setup enrolled, '
                  'addressed to the owner, and presented it in his chat [%s %s %d]'
                  % (request.get('outcome'), opened.get('requested_by'), len(sent)),
                  request.get('outcome') == 'open' and opened.get('owner') == owner
                  and opened.get('requested_by') == 'qualification-requester' and bool(sent))
            answer = H.deliver(api, token, owner_user, 'accept: the first decision on this factory',
                               reply_to=sent[-1]) if sent else None
            done1 = answer
            q = (wait(lambda: status().get('qualification'), 20) if done1 else None) or {}
            stored = entity(q.get('id') or '') or {}
            data = stored.get('data') or {}
            settled = data.get('settlement') or {}
            check(JQ, 'the owner\'s reply settled that request through the running service under his delegation [%s %s]'
                  % (settled.get('choice'), settled.get('originating_channel')),
                  bool(data) and data.get('request_id') == rid and settled.get('choice') == 'accept'
                  and settled.get('originating_channel') == 'telegram_chat'
                  and (data.get('presentation') or {}).get('chat_id') == owner_user['id']
                  and (data.get('owner_answer') or {}).get('message_id') == (answer or {}).get('message', {}).get('message_id'))
            check(JQ, 'the service\'s own gate recorded the qualification, its digest the one it reports [%s]'
                  % {k: q.get(k) for k in ('id', 'platform')},
                  bool(data) and ACT.digest(data) == q.get('digest') and ACT.qualification_problems(data, url) == []
                  and all(x.get('origin') == url for x in data.get('exchanges') or []))

        # A restart of the service inside the run finds the run's one request by its alias.
        with section(QR):
            prefix = 'assignment:%s:qualification-' % report['authority_ids']['repository_uuid']

            def requests():
                return sorted(r[0] for r in conn.execute('SELECT id FROM entities').fetchall() if r[0].startswith(prefix))
            before, shown_before = requests(), presented()
            CS.stop(unit, manager)
            again = CS.start(unit, manager)
            ran = passes(3)
            later = status().get('run') or {}
            check(QR, 'the service restarted through its lifecycle and ran passes in the same qualification run [%s]'
                  % again.get('ActiveState'), again.get('ActiveState') == 'active' and ran and bool(run.get('id'))
                  and later.get('id') == run.get('id'))
            check(QR, 'after the restart the run still has exactly its one request, found by its alias [%d -> %d]'
                  % (len(before), len(requests())), bool(rid) and before == [rid] and requests() == [rid]
                  and (later.get('request') or {}).get('request_id') == rid and (later.get('request') or {}).get('outcome') == 'open')
            check(QR, 'and nothing was presented again [%d -> %d]' % (len(shown_before), len(presented())),
                  bool(shown_before) and presented() == shown_before)

        with section(JQ):
            rc, shown = veldo('activate')
            now = status()
            check(JQ, 'bin/veldo channel activate over the recorded qualification leaves the edge active [%s]'
                  % {k: shown.get(k) for k in ('outcome', 'state', 'reason')},
                  rc == 0 and shown.get('state') == 'active' and (now.get('record') or {}).get('state') == 'active'
                  and (now.get('record') or {}).get('qualification_digest') == q.get('digest') and bool(q.get('digest')))
            armed = guard_armed.read_text().split() if guard_armed.is_file() else []
            check(JQ, 'no connection beyond the loopback interface, here or in the service it started [%s %s %d]'
                  % (attempts, guard_log.read_text() if guard_log.is_file() else '', len(armed)),
                  not attempts and not (guard_log.is_file() and guard_log.read_text().strip()) and len(armed) >= 1)

        # AC2 (declared falsifier): after the whole journey the token is in its own file and nowhere else.
        with section(TK):
            needle = token.encode()
            check(TK, 'control: the search finds the token in the account\'s own token file',
                  holding(needle, person) == [str(token_file)])
            everywhere = holding(needle, state_root, home, base / 'units', host_trust.parent,
                                 CEN.git_common_dir(str(workspace)))
            check(TK, 'no copy of the token in the state root, the store, the install root, the unit, the host trust or '
                  'the workspace [%s]' % everywhere, everywhere == [])

        # Filed 4: an existing host trust directory is this account's own 0700 directory, or refused by name.
        # Review 2: an opening of the run's one request that fails part-way is retried on a later pass of
        # the same process until it is open, and never opens a second.
        with section(OR):
            op_root = base / 'root-opening'
            op_root.mkdir()
            os.chmod(str(op_root), 0o700)
            op_code, op_report = setup('opening', op_root, clone('w-opening'),
                                       base / 'xdg-opening' / 'veldo' / 'host_trust.json')
            op_prefix = 'assignment:%s:qualification-' % ((op_report or {}).get('authority_ids') or {}).get('repository_uuid')
            chan = CH.Channel(str(op_root / 'host' / 'ingress.json'))
            try:
                real_apply = chan.ingress.inbox.apply

                def cut(packet):
                    raise RuntimeError('suite: the opening is cut after the terms')
                chan.ingress.inbox.apply = cut
                shown = chan.status()
                env, cmd = ACT.owner_command('qualify', shown, owner, time.time(), minutes=15)
                accepted = chan.authorize({'envelope': env, 'command': cmd,
                                           'signature': ACT.ssh_signer(str(owner_key))(AC.canonical_envelope_bytes(env))})
                chan.tick()
                failed = dict(chan.run['request'] or {}) if chan.run else {}
                chan.ingress.inbox.apply = real_apply
                for _ in range(8):
                    chan.tick()
                    if ((chan.run or {}).get('request') or {}).get('outcome') == 'open':
                        break
                opened = dict((chan.run or {}).get('request') or {})
                for _ in range(3):
                    chan.tick()
                store_rows = [r[0] for r in chan.ingress.activations.conn.execute('SELECT id FROM entities').fetchall()]
                made = sorted(r for r in store_rows if r.startswith(op_prefix))
            finally:
                chan.close()
            check(OR, 'a fresh factory is set up and the owner\'s qualify is accepted while the opening is cut [%s %s]'
                  % (op_code, accepted.get('outcome')), op_code == 0 and accepted.get('outcome') == 'accepted'
                  and failed.get('outcome') == 'refused')
            check(OR, 'once the fault clears, a later pass of the same process opens the request [%s]' % opened.get('outcome'),
                  opened.get('outcome') == 'open')
            check(OR, 'and exactly one qualification request exists after further passes [%d]' % len(made), len(made) == 1)

        with section(HD):
            loose = base / 'xdg-loose' / 'veldo'
            loose.mkdir(parents=True)
            os.chmod(str(loose), 0o755)
            refused('trust-directory-mode', 'invalid_input:host_trust_directory:mode', state=root('hd-mode'),
                    trust_path=loose / 'host_trust.json', row=HD)
            refused('trust-directory-owner', 'invalid_input:host_trust_directory:owner', state=root('hd-owner'),
                    trust_path=Path('/') / ('v139-absent-%s.json' % os.urandom(4).hex()), row=HD)
            real_dir = base / 'xdg-real'
            real_dir.mkdir(mode=0o700)
            (base / 'xdg-link').mkdir(mode=0o700)
            (base / 'xdg-link' / 'veldo').symlink_to(real_dir)
            refused('trust-directory-symlink', 'invalid_input:host_trust_directory:symlink', state=root('hd-link'),
                    trust_path=base / 'xdg-link' / 'veldo' / 'host_trust.json', row=HD)

        # Filed 2 and 3: the store is 0600, and a failed store step leaves no connection open.
        with section(SP):
            files = [store] + [Path(str(store) + end) for end in ('-wal', '-shm') if Path(str(store) + end).exists()]
            check(SP, 'the store and its WAL and shared-memory files are 0600 files of this account [%s]'
                  % [(p.name, mode_of(p)) for p in files], all(mode_of(p) == ('0o600', os.getuid()) for p in files))
            real_organ = F.organ

            def faulty(name):
                module = real_organ(name)
                if name == 'control_claim':
                    inner = module.CM

                    class Faulty:
                        def __getattr__(self, attr):
                            return getattr(inner, attr)

                        def attach(self, *args, **kwargs):
                            raise RuntimeError('v139 injected fault after the store is opened')
                    module.CM = Faulty()
                return module
            broken = base / 'root-store-fault'
            broken.mkdir(mode=0o700)
            os.chmod(str(broken), 0o700)
            held, code, open_fds = None, None, None
            F.organ = faulty
            try:
                F.setup(str(broken), owner, str(owner_key), str(clone('w-store-fault')), owner_user['id'], str(token_file),
                        host_trust=str(base / 'xdg-store-fault' / 'veldo' / 'host_trust.json'),
                        install_root=str(base / 'install'), unit_dir=str(base / 'units'), profile=profile, writable=[],
                        runner=manager, origin=url)
                code = 'set_up'
            except F.Refused as exc:
                # The refusal is held while the process's descriptors are read: a connection the setup
                # left open is still reachable from it.
                held, code = exc, exc.code
                target = os.path.realpath(str(broken / 'authority' / 'control.sqlite3'))
                open_fds = []
                for fd in os.listdir('/proc/self/fd'):
                    with contextlib.suppress(OSError):
                        if os.path.realpath(os.readlink('/proc/self/fd/' + fd)).startswith(target):
                            open_fds.append(fd)
            finally:
                F.organ = real_organ
            check(SP, 'a setup whose store step fails after the store is opened is refused by name [%s]' % code,
                  code == 'setup_incomplete:store:RuntimeError')
            check(SP, 'while that refusal is held, no connection to its store is open [%s]' % open_fds,
                  held is not None and open_fds == [])
            held = None
            gc.collect()

        # Filed 1: the documented rollback names every file setup writes, and a second setup then succeeds.
        with section(RB):
            named = '.git/veldo/control/enrollment.json'
            spec_text = (ROOT / 'specs' / 'VELDO-0139-factory-setup-on-a-host.md').read_text()
            readme = (ROOT / 'proof' / 'VELDO-0139' / 'README.md').read_text()
            in_spec = spec_text.split('\nrollback: >', 1)[-1].split('\n---', 1)[0] if '\nrollback: >' in spec_text else ''
            in_readme = readme.split('\nRollback:', 1)[-1].split('\n\n', 1)[0] if '\nRollback:' in readme else ''
            binding_file = Path(CEN.binding_path(str(workspace)))
            check(RB, 'the spec\'s rollback and the README\'s name the workspace binding <clone>/%s' % named,
                  named in ' '.join(in_spec.split()) and named in ' '.join(in_readme.split())
                  and str(binding_file).endswith(named))
            conn.close()
            conn = None
            CS.stop(unit, manager)
            CS.uninstall(unit, install_root=str(base / 'install'), unit_dir=str(base / 'units'), runner=manager)
            for child in sorted(state_root.iterdir()):
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(str(child))
                else:
                    child.unlink()
            host_trust.unlink()
            binding_file.unlink()
            code2, rerun = setup('rerun', state_root, workspace, host_trust)
            check(RB, 'after that rollback a second setup over the same state root, host trust path and clone succeeds [%s]'
                  % {k: rerun.get(k) for k in ('outcome', 'reason')},
                  code2 == 0 and rerun.get('outcome') == 'set_up'
                  and (rerun.get('authority_ids') or {}).get('store_uuid') != report['authority_ids']['store_uuid'])
            unit = rerun.get('unit') or unit
            again_binding = CEN.read_binding(str(workspace))
            again_trust = EL.load_host_trust(str(host_trust))
            problems = CEN.verify_binding(str(workspace), again_binding, again_trust.verifier(owner, str(workspace)),
                                          again_trust.host_identity) if again_binding and again_trust else ['absent']
            check(RB, 'its binding names the new store and verifies under the new host trust [%s]' % problems,
                  problems == [] and again_binding.get('store_uuid') == (rerun.get('authority_ids') or {}).get('store_uuid'))
    except StopIteration:
        pass
    finally:
        socket.create_connection, socket.getaddrinfo = real_connect, real_resolve
        with contextlib.suppress(Exception):
            if unit:
                CS.stop(unit, manager)
        manager.close()
        stop_api()
        for handle in (getattr(ing, 'conn', None), conn):
            with contextlib.suppress(Exception):
                handle.close()
        for directory, _dirs, _files in os.walk(str(base)):
            with contextlib.suppress(OSError):
                os.chmod(directory, 0o700)
        shutil.rmtree(str(base), ignore_errors=True)

    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        if not ok:
            for label, one in observed:
                if not one:
                    print('  VELDO-0139 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0139 %s detail: no check ran' % name)
        expect('VELDO-0139 ' + name, ok)
    print('VELDO-0139 suite seconds: %.3f' % (time.monotonic() - started))


_v139_suite()
