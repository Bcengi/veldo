"""Isolated setup and launch fixtures adapted from suites 73 and 82.
Only construction is shared; callbacks execute VELDO-0182 assertions alone.
Fake engines, user manager and Tailscale; real setup, signing, Runner and receiver.
"""
def setup_fixture(callback):
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

    fast = fast_temp()
    base = Path(tempfile.mkdtemp(prefix='b139-', dir=fast))
    mods = base / 'src' / '.veldo'
    (mods / 'services').mkdir(parents=True)
    for source in sorted((ROOT / '.veldo').glob('*.py')):
        shutil.copyfile(source, mods / source.name)
    shutil.copyfile(ROOT / '.veldo' / 'services' / 'veldo-authority.service', mods / 'services' / 'veldo-authority.service')
    if (ROOT / '.veldo' / 'services' / 'veldo-api.service').is_file():
        shutil.copyfile(ROOT / '.veldo' / 'services' / 'veldo-api.service', mods / 'services' / 'veldo-api.service')
    for name, source in PRODUCTION.items():
        target = mods / name
        if target.exists():
            target.unlink()
        if Path(source).is_file():
            shutil.copyfile(source, target)
    # VELDO-0186: setup now requires qualified host engine bytes and runtime records.
    fixtures186 = load('v139_install_fixtures', ROOT / 'proof/VELDO-0186/fixtures.py')
    engines186 = fixtures186.install(ROOT, base, mods)
    fake = engines186['fake']
    compare_formats = load('v139_formats', ROOT / 'proof/VELDO-0172/compare_formats.py')
    prior_path186 = os.environ.get('PATH', '')
    H = load('v139_support', ROOT / 'scripts' / 'suites' / 'support' / 'v73_authority.py')
    # VELDO-0171: setup reads Tailscale; this suite's setups read the stand-in replaying the scrubbed capture,
    # never the host's real CLI.
    TS = load('v139_tailscale', ROOT / 'scripts' / 'suites' / 'support' / 'v171_tailscale.py')
    tailscale = TS.stand_in(ROOT / 'proof' / 'VELDO-0171' / 'tailscale-capture.json', sys.executable)
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
    # This suite exercises memory, not the host's cgroup/user-manager qualification.
    # The isolated manager above is the explicit process-control fixture.
    original_organ = F.organ
    def memory_fixture_organ(name):
        module = original_organ(name)
        if name == 'control_service':
            original_qualify = module.C.qualify
            def qualify(profile, environment=None):
                value = original_qualify(profile, environment)
                if value.get('refusal') == 'unavailable_service:profile:user_manager':
                    value.update(qualified=True, refusal=None)
                return value
            module.C.qualify = qualify
        return module
    F.organ = memory_fixture_organ


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
    ts_overrides = {'tailscale': [tailscale.path], 'api_port': TS.free_port()}
    if F is None or 'tailscale' not in __import__('inspect').signature(F.setup).parameters:
        ts_overrides = {}

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
                          writable=[], runner=manager, origin=url, **ts_overrides)
        try:
            shown = json.loads(out.getvalue().strip().splitlines()[-1])
        except (ValueError, IndexError):
            shown = {'unparsed': out.getvalue()[-300:]}
        return code, shown

    try:
        os.environ['PATH'] = str(engines186['path']) + os.pathsep + prior_path186
        callback(locals())
    finally:
        os.environ['PATH'] = prior_path186
        socket.create_connection, socket.getaddrinfo = real_connect, real_resolve
        with contextlib.suppress(Exception):
            if unit:
                CS.stop(unit, manager)
        manager.close()
        stop_api()
        tailscale.close()
        for handle in (getattr(ing, 'conn', None), conn):
            with contextlib.suppress(Exception):
                handle.close()
        for directory, _dirs, _files in os.walk(str(base)):
            with contextlib.suppress(OSError):
                os.chmod(directory, 0o700)
        shutil.rmtree(str(base), ignore_errors=True)


def launch_fixture(callback):
    import hashlib
    import importlib.util
    import json
    import os
    import re
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import time

    TREE = Path(globals().get('__suite_file__', str(ROOT / 'scripts/suites/x.py'))).resolve().parents[2]

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_engine_claude.py': ROOT / ".veldo" / "control_engine_claude.py",
        'control_engine_codex.py': ROOT / ".veldo" / "control_engine_codex.py",
    }
    EXTRACTOR = ROOT / "proof/VELDO-0165" / "extract_environment.py"
    ROWS = ('strip/claude', 'strip/codex', 'strip/future-names', 'strip/own-values',
            'refuse/claude', 'refuse/codex', 'mcp/prefixed-tools', 'evidence/qualified',
            'fixture/extraction', 'fixture/mcp-control', 'strip/configured', 'strip/unprefixed',
            'evidence/empty', 'evidence/completeness', 'evidence/prefixes', 'report/removed', 'report/refused',
            'strip/child-environment', 'mcp/configured-refused', 'evidence/not-a-list', 'evidence/outside-scan',
            'format/fake-lines')
    rows = {name: [] for name in ROWS}

    def check(row, label, condition):
        rows[row].append((label, bool(condition)))

    def attempt(fn):
        """(value, error): a refusal or a missing function is data for the row, never a raise."""
        try:
            return fn(), None
        except Exception as error:  # noqa: BLE001
            return None, error

    def code(error):
        return getattr(error, 'code', type(error).__name__) if error is not None else None

    def load(name, path):
        if not Path(path).is_file():
            return None
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    fake_spec = importlib.util.spec_from_file_location('v172_fake_formats', ROOT / 'proof/VELDO-0172/fake_formats.py')
    fake_formats = importlib.util.module_from_spec(fake_spec)
    fake_spec.loader.exec_module(fake_formats)
    # VELDO-0172: this suite checks its own fake engines against the live capture at its teardown.
    conform_spec = importlib.util.spec_from_file_location('v172_compare_formats', ROOT / 'proof/VELDO-0172/compare_formats.py')
    conform_formats = importlib.util.module_from_spec(conform_spec)
    conform_spec.loader.exec_module(conform_formats)
    live_step = fake_formats.live_step

    started = time.monotonic()
    fast = fast_temp()
    base = Path(tempfile.mkdtemp(prefix='v165-', dir=fast))
    connections = []
    try:
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            if Path(source).is_file():
                shutil.copyfile(source, mods / name)
        S = load('v165_store', mods / 'control_store.py')
        L = load('v165_launch', mods / 'control_launch.py')
        D = L.D
        RES = D.RES
        ACC = RES.ACC
        HELPER = load('v165_helper', mods / 'accounts.py')
        EL = load('v165_eligibility', mods / 'control_eligibility.py')
        SIG = load('v165_signer', mods / 'control_signer.py')
        GP = load('v165_git', mods / 'git_process.py')
        CLM = D.CLM
        DOMAIN, REPOSITORY, HOLDER, HOST = 'domain-165', 'repository-165', 'builder-165', 'linux-host-165'
        private = base / 'private'
        private.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / 'journal')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        db = base / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        connections.append(writer)
        serial = [0]

        def entity(identity):
            row = writer.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

        def put(identity, kind, data):
            serial[0] += 1
            current = entity(identity)
            S.execute(writer, dict(command_id='setup-%d' % serial[0], principal='setup', operation='upsert_entity',
                                   nonce='setup-%d' % serial[0], artifact_digests=[],
                                   expected_versions={identity: current['version'] if current else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), 'setup', sign, 1)

        def member(principal, kind, roles):
            put(principal, 'membership', dict(principal_type=kind, roles=roles, scope=[REPOSITORY],
                                              revoked_at=None, expires_at=None))
        member('runner', 'service', ['reservation_service'])
        member('launch-receiver', 'service', ['reservation_service'])
        member('owner', 'person', ['project_owner'])
        writer.command_registry['claim_operation'] = {'transaction_transition': CLM.transition,
                                                      'writes': ('entities', 'journal', 'commands', 'nonces')}

        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=RES.service_authority, signer='runner', sign=sign)
        BIG = dict(capacity=50, invocations=200, wall_seconds=10 ** 7)
        # The owner's account records, over profiles the local helper prepares for either provider.
        accounts = ACC.Accounts(S, writer, principal='owner', signer='owner', sign=sign)
        helper_root = base / 'helper'
        profiles = {}

        def register(account, provider, concurrency=1, directory=None):
            """Prepare the account's profile and register it once; the refusal's code, or None."""
            record, error = attempt(lambda: HELPER.account_add(account, root=str(helper_root), provider=provider,
                                                               config_dir=directory))
            if record is None:
                return code(error)
            profiles.setdefault(account, record['config_dir'])
            fields = HELPER.registration(account, host=HOST, root=str(helper_root))
            reservations.configure('policy/' + account, 'account', account, dict(BIG), now=time.time())
            _, error = attempt(lambda: accounts.register('register/' + account, fields['account'], fields['provider'],
                                                         fields['label'], fields['profiles'], concurrency=concurrency,
                                                         now=time.time()))
            return code(error)
        for account, provider in [('acct-c1', 'claude_code'), ('acct-x1', 'codex')]:
            error = register(account, provider)
            check('strip/' + ('claude' if provider == 'claude_code' else 'codex'),
                  'account registered by production writer', error is None)
        projects = set()

        def admitted(unit, proj='journey'):
            if proj not in projects:
                projects.add(proj)
                put('project:' + proj, 'project', dict(name=proj))
                reservations.configure('policy/' + proj, 'project', proj, dict(BIG), now=time.time())
            put(unit, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + unit,
                                             requirements=[], eligible_holders=[HOLDER], project=proj,
                                             scope_digest='sha256:scope-' + unit, revision=1, depends_on=[]))
            put('backlog:' + unit, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
            put('admission:' + unit, 'admission', dict(unit=unit, state='accepted', scope_digest='sha256:scope-' + unit))
            reservations.configure('policy/' + unit, 'unit', unit, dict(capacity=5, invocations=20, wall_seconds=10 ** 6),
                                   now=time.time())
            cid = CLM.claim_id(REPOSITORY, unit)
            serial[0] += 1
            S.execute(writer, dict(command_id='claim-%d' % serial[0], principal=HOLDER, operation='claim_operation',
                                   nonce='claim-%d' % serial[0], artifact_digests=[],
                                   expected_versions={unit: entity(unit)['version'],
                                                      'backlog:' + unit: entity('backlog:' + unit)['version'], cid: 0},
                                   parameters=dict(action='claim', unit_id=unit, backlog_item_uuid='backlog:' + unit,
                                                   claim_id=cid, holder=HOLDER, generation=0, capabilities=[],
                                                   repository_uuid=REPOSITORY)), HOLDER, sign, 1)
            return unit

        src = base / 'source'
        GP.run(['git', 'init', '-q', str(src)], check=True, capture_output=True)
        (src / 'README').write_text('session hygiene source\n')
        GP.run(['git', '-C', str(src), 'add', 'README'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))

        # The fake engines: each records its birth environment, then prints what its packet scripts,
        # waiting on a file where the script says, and exits with the scripted code.
        markers = base / 'markers'
        markers.mkdir()
        engines = base / 'bin'
        engines.mkdir()
        server = base / 'mcp-server.py'
        server.write_text('import json,sys\n'
                          'for line in sys.stdin:\n'
                          ' r=json.loads(line)\n'
                          ' print(json.dumps({"jsonrpc":"2.0","id":r["id"],"result":{"tools":['
                          '{"name":"read","inputSchema":{"type":"object"}},'
                          '{"name":"write","inputSchema":{"type":"object"}}]}}),flush=True)\n')
        fake = '''#!%s -B
import json, os, sys, time, subprocess
from pathlib import Path
if sys.argv[1:3] == ['login', 'status']:
    # VELDO-0156: the receiver's check before acceptance, on a ChatGPT login; the 0.154.0 binary prints its
    # login status on stderr.
    sys.stderr.write('Logged in using ChatGPT' + chr(10))
    sys.exit(0)
markers = Path(MARKERS)
dispatch = os.environ.get('VELDO_DISPATCH_ID', '')
own = {'engine': ENGINE, 'pid': os.getpid(), 'dispatch': dispatch, 'started': time.time(),
       'env': dict(os.environ)}
(markers / ('%%d.tmp' %% os.getpid())).write_text(json.dumps(own))
(markers / ('%%d.tmp' %% os.getpid())).rename(markers / ('%%d.json' %% os.getpid()))
def emit(event):
    text = json.dumps(event)
    with open(markers / ('%%d.out' %% os.getpid()), 'a') as out:
        out.write(text + chr(10))
    sys.stdout.write(text + chr(10))
    sys.stdout.flush()
def stream_input():
    # VELDO-0155: stream JSON input (--input-format stream-json) as the 2.1.281 binary reads it: the initialize
    # control request is answered with the login (the binary's Kfe(), a claude.ai subscription here), the user
    # message's content is the prompt; without it the whole input is the prompt.
    at = sys.argv.index('--input-format') if '--input-format' in sys.argv else -1
    if at < 0 or sys.argv[at + 1:at + 2] != ['stream-json']:
        raw = sys.stdin.buffer.read()
        return json.loads(raw) if raw.strip() else {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return {}
        message = json.loads(line)
        if message.get('type') == 'control_request' and (message.get('request') or {}).get('subtype') == 'initialize':
            answer = {'type': 'control_response', 'response': {'subtype': 'success', 'request_id': message['request_id'],
                      'response': {'account': {'subscriptionType': 'Claude Team', 'apiProvider': 'firstParty'},
                                   'pid': os.getpid()}}}
            emit(complete_event(answer))
        elif message.get('type') == 'user':
            content = (message.get('message') or {}).get('content')
            return json.loads(content) if isinstance(content, str) and content.strip() else {}
packet = stream_input()
if own['engine'] == 'claude':
    server_config = (packet.get('configuration') or {}).get('mcp_servers') or {}
    # The binary's built-in tools come first, as the live init listed them, then each MCP server's.
    tools = ['Read', 'Bash']
    for name, config in server_config.items():
        request = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/list'}) + chr(10)
        answer = subprocess.run([config['command']] + config['args'], input=request,
                                capture_output=True, text=True, check=True, timeout=5)
        for tool in json.loads(answer.stdout)['result']['tools']:
            # Exact gate in the binary: only SDK servers can opt out of Fa(server, tool).
            plain = config['type'] == 'sdk' and os.environ.get('CLAUDE_AGENT_SDK_MCP_NO_PREFIX')
            tools.append(tool['name'] if plain else 'mcp__' + name + '__' + tool['name'])
    own['init'] = complete_event({'type': 'system', 'subtype': 'init', 'apiKeySource': 'none', 'tools': tools,
                   'claude_code_version': '2.1.281', 'cwd': str(Path.cwd()),
                   'mcp_servers': [{'name': n, 'status': 'connected'} for n in server_config],
                   'model': 'fixture-model', 'permissionMode': 'default', 'slash_commands': [],
                   'output_style': 'default', 'skills': [], 'plugins': [],
                   'uuid': 'fixture-init', 'session_id': 'fixture-session'})
    (markers / ('%%d.json' %% os.getpid())).write_text(json.dumps(own))
    emit(own['init'])
payload = packet.get('payload') or {}
for step in payload.get('script') or []:
    if 'line' in step:
        emit(step['line'])
    elif 'sleep' in step:
        time.sleep(step['sleep'])
    elif 'wait' in step:
        end = time.time() + 30
        while not os.path.exists(step['wait']) and time.time() < end:
            time.sleep(0.02)
(markers / ('%%d.done' %% os.getpid())).write_text(json.dumps({'ended': time.time()}))
sys.exit(payload.get('code', 0))
''' % (sys.executable,)
        fake = fake_formats.embed(fake)

        def fake_engine(name):
            # The markers directory and the engine's name are written into the fake: a pinned engine's argv
            # is its qualified flags, so nothing of the suite's can ride on it.
            return (fake.replace('Path(MARKERS)', 'Path(%r)' % str(markers))
                        .replace("'engine': ENGINE,", "'engine': %r," % name))
        # VELDO-0060: a Claude Code adapter runs only its pinned, qualified version. The fake claude is
        # installed as that version, this installation's qualification record names its digest, and the
        # production pin copies it under the factory state root.
        versions = base / 'versions'
        versions.mkdir()
        (versions / '2.1.281').write_text(fake_engine('claude'))
        (versions / '2.1.281').chmod(0o755)
        # VELDO-0155: the version is qualified with stream JSON input (the fake answers the initialize handshake
        # with a subscription login) and, where the engine module has one, the everything-off baseline.
        claude_record = {'schema': 'veldo.engine_qualification/v1', 'engine': 'claude_code', 'versions': {'2.1.281': {
            'sha256': 'sha256:' + hashlib.sha256((versions / '2.1.281').read_bytes()).hexdigest(),
            'flags': ['--print', '--output-format', 'stream-json', '--verbose', '--input-format', 'stream-json'],
            'environment': {'DISABLE_AUTOUPDATER': '1'}}}}
        CLAUDE_ENGINE = getattr(L, 'ENGINES', {}).get('claude_code')
        if getattr(CLAUDE_ENGINE, 'BASELINE', None) is not None:
            claude_record['versions']['2.1.281']['baseline'] = CLAUDE_ENGINE.BASELINE
            if hasattr(CLAUDE_ENGINE, 'session_environment'):
                claude_record['versions']['2.1.281']['session_environment'] = CLAUDE_ENGINE.session_environment(versions / '2.1.281')
        if hasattr(CLAUDE_ENGINE, 'qualified_tools'):
            # VELDO-0173: the full tool registry and its classification, read from the pinned 2.1.281 bytes.
            tools173 = json.loads((ROOT / 'proof' / 'VELDO-0173' / 'claude-tools.json').read_text())
            claude_record['versions']['2.1.281'].update(tool_registry=tools173['tool_registry'],
                                                        tool_classification=tools173['tool_classification'])
        (mods / 'runtime').mkdir()
        (mods / 'runtime' / 'claude-qualification.json').write_text(json.dumps(claude_record))
        factory = base / 'factory'
        factory.mkdir(mode=0o700)
        pin = getattr(getattr(L, 'ENGINES', {}).get('claude_code'), 'pin', None)
        if pin is not None:
            pin('2.1.281', versions=str(versions), state_root=str(factory))
        # VELDO-0061: a Codex adapter launches a pinned vendor binary inside its package, with the qualified
        # flags, checked against a qualification record the production writer makes.
        package = engines / 'codex-package'
        vendored = package / 'vendor' / 'x86_64-unknown-linux-musl' / 'bin' / 'codex'
        vendored.parent.mkdir(parents=True)
        (package / 'package.json').write_text(json.dumps({'name': '@openai/codex', 'version': '0.154.0-linux-x64'}))
        vendored.write_text(fake_engine('codex'))
        vendored.chmod(0o755)
        CODEX_ENGINE = getattr(L, 'ENGINES', {}).get('codex')
        codex_qualification = base / 'codex-qualification.json'
        if hasattr(CODEX_ENGINE, 'qualification'):
            codex_qualification.write_text(json.dumps(CODEX_ENGINE.qualification(str(vendored))))
        config = base / 'receiver.json'
        wrapper = [sys.executable, '-B', str(mods / 'control_launch.py'), 'exec']
        # VELDO-0170: ordinary launch fixtures name installed host trust; no settlements are trusted.
        receiver_host_trust = Path(db).parent / 'receiver-host-trust.json'
        receiver_enrollment_signers = receiver_host_trust.with_name('receiver-enrollment-signers')
        receiver_enrollment_signers.write_text('')
        receiver_host_trust.write_text(json.dumps(dict(schema='veldo.host_trust/v1', host_identity='fixture-host',
                                                     enrollment_signers=str(receiver_enrollment_signers))))
        receiver_host_trust.chmod(0o600)
        config.write_text(json.dumps({'host_trust': str(receiver_host_trust),
            'store': str(db), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
            'workspace': str(base), 'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1,
            'host': HOST, 'receipts': str(base / 'receipts'), 'state_root': str(factory),
            'adapters': {
                'claude': {'identity': 'reported', 'engine': 'claude_code', 'environment': {'TZ': 'UTC'},
                           'executable': {'version': '2.1.281'}, 'argv': wrapper},
                'codex': {'identity': 'reported', 'engine': 'codex', 'environment': {'TZ': 'UTC'},
                          'executable': str(vendored), 'qualification': str(codex_qualification),
                          'argv': wrapper + [str(vendored)] + list(getattr(CODEX_ENGINE, 'FLAGS', ()))},
                # AC2: the MCP naming switch configured on the adapter itself, not inherited.
                'claude-renamed': {'identity': 'reported', 'engine': 'claude_code',
                                   'environment': {'TZ': 'UTC', 'CLAUDE_AGENT_SDK_MCP_NO_PREFIX': '1'},
                                   'executable': {'version': '2.1.281'}, 'argv': wrapper}}}))
        CONFIGURATION = {'mcp_servers': {'tracker': {'type': 'sdk', 'command': sys.executable, 'args': [str(server)]}}}
        gate = EL.Gate(S, writer, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)

        inherited = {'PATH': os.environ['PATH'], 'HOME': str(base / 'home'), 'TZ': 'UTC'}
        (base / 'home').mkdir()
        original = ('CLAUDECODE', 'CLAUDE_CODE_CHILD_SESSION', 'CLAUDE_CODE_SESSION_ID',
                    'CLAUDE_CODE_SESSION_ATTENDED', 'CLAUDE_CODE_ENTRYPOINT', 'CLAUDE_CODE_EXECPATH',
                    'CLAUDE_CODE_MESSAGING_SOCKET', 'CLAUDE_CODE_MESSAGING_TOKEN', 'CLAUDE_PID',
                    'CLAUDE_EFFORT', 'AI_AGENT', 'CODEX_THREAD_ID', 'CLAUDE_AGENT_SDK_MCP_NO_PREFIX')
        future = tuple(p + 'VELDO_FUTURE_' + os.urandom(5).hex().upper()
                       for p in ('CLAUDE', 'CLAUDECODE', 'AI_AGENT', 'CODEX', 'CLAUDE_CODE_'))
        unprefixed = ('GIT_CONFIG_PARAMETERS', 'TRACEPARENT', 'COREPACK_ENABLE_AUTO_PIN')
        planted = original + future + unprefixed
        inherited.update({n: 'planted-' + os.urandom(8).hex() for n in planted})
        inherited.update({'CLAUDE_CONFIG_DIR': str(base / 'wrong-claude'),
                          'CODEX_HOME': str(base / 'wrong-codex'),
                          'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '0', 'CLAUDE_CODE_DISABLE_CLAUDE_MDS': '0'})
        token = base / 'subscription-fixture'
        own_token = 'fixture-' + os.urandom(12).hex()
        token.write_text(own_token)
        token.chmod(0o600)
        configuration = json.loads(config.read_text())
        configuration['subscription_tokens'] = {'acct-c1': str(token)}
        config.write_text(json.dumps(configuration))
        configured_values = {'claude': {'CLAUDE_CODE_SUBAGENT_MODEL': 'fixture-' + os.urandom(8).hex()},
                             'codex': {'CODEX_CA_CERTIFICATE': 'fixture-' + os.urandom(8).hex()}}
        for engine, values in configured_values.items():
            configuration['adapters'][engine]['environment'].update(values)
            inherited.update({n: 'parent-' + os.urandom(8).hex() for n in values})
        config.write_text(json.dumps(configuration))
        inherited['CLAUDE_CODE_OAUTH_TOKEN'] = 'inherited-' + os.urandom(12).hex()
        # What a parent Codex sets on every command it runs, and Claude Code's metrics default, each with
        # a value of the parent's own; only LANG and TERM reach an engine, with its baseline's values.
        children = ('NO_COLOR', 'TERM', 'LANG', 'LC_CTYPE', 'LC_ALL', 'COLORTERM', 'PAGER', 'GIT_PAGER',
                    'GH_PAGER', 'CODEX_CI', 'OTEL_EXPORTER_OTLP_METRICS_TEMPORALITY_PREFERENCE')
        inherited.update({n: 'parent-' + os.urandom(8).hex() for n in children})

        def invoke(contract):
            return L.invoke(config, contract, dispatches, accept_seconds=30, environment=inherited)
        explicit = {}

        def pinned(account):
            if account not in explicit:
                explicit[account] = L.Runner(gate, reservations, dispatches, invoke, account=account)
            return explicit[account]

        # Stream lines in the shapes the installed CLIs print, on VELDO-0172's shared constructors: the fake
        # prints its own handshake answer and init, then these (the format row checks every printed line).
        SESSION = 'session-165-' + os.urandom(4).hex()

        def c_usage(inp, out):
            return {'input_tokens': inp, 'output_tokens': out, 'cache_creation_input_tokens': 0,
                    'cache_read_input_tokens': 0,
                    'cache_creation': {'ephemeral_5m_input_tokens': 0, 'ephemeral_1h_input_tokens': 0},
                    'service_tier': 'standard'}

        @live_step
        def c_msg(mid, inp, out):
            return {'line': {'type': 'assistant', 'parent_tool_use_id': None, 'uuid': 'uuid-' + os.urandom(6).hex(),
                             'session_id': SESSION,
                             'message': {'id': mid, 'type': 'message', 'role': 'assistant', 'model': 'fixture-model',
                                         'content': [], 'stop_reason': None, 'stop_sequence': None,
                                         'usage': c_usage(inp, out)}}}

        @live_step
        def c_rate(status, reset, kind='five_hour'):
            return {'line': {'type': 'rate_limit_event', 'uuid': 'uuid-' + os.urandom(6).hex(), 'session_id': SESSION,
                             'rate_limit_info': {'status': status, 'rateLimitType': kind, 'resetsAt': int(reset)}}}

        @live_step
        def c_result(inp, out, turns=1, text='done'):
            return {'line': {'type': 'result', 'subtype': 'success', 'duration_ms': 5, 'duration_api_ms': 4,
                             'is_error': False, 'num_turns': turns, 'result': text, 'stop_reason': 'end_turn',
                             'total_cost_usd': 0, 'usage': c_usage(inp, out),
                             'modelUsage': {'fixture-model': {'inputTokens': inp, 'outputTokens': out,
                                                              'cacheReadInputTokens': 0, 'cacheCreationInputTokens': 0,
                                                              'webSearchRequests': 0, 'costUSD': 0,
                                                              'contextWindow': 200000, 'maxOutputTokens': 32000}},
                             'permission_denials': [], 'uuid': 'uuid-' + os.urandom(6).hex(), 'session_id': SESSION}}

        @live_step
        def x_thread():
            return {'line': {'type': 'thread.started', 'thread_id': 'thread-165'}}

        @live_step
        def x_started():
            return {'line': {'type': 'turn.started'}}

        @live_step
        def x_message(text='done'):
            return {'line': {'type': 'item.completed', 'item': {'id': 'item_0', 'type': 'agent_message', 'text': text}}}

        @live_step
        def x_done(inp, out):
            return {'line': {'type': 'turn.completed', 'usage': {
                'input_tokens': inp, 'cached_input_tokens': 0, 'cache_write_input_tokens': 0, 'output_tokens': out,
                'reasoning_output_tokens': 0}}}

        # A whole normal turn of each engine, as the live runs printed it: the streamed output count is
        # lower than the final one.
        STREAMS = {'claude': lambda: [c_msg('msg-165', 3, 3), c_rate('allowed', 2000000000), c_result(3, 4)],
                   'codex': lambda: [x_started(), x_message(), x_done(3, 4)]}

        def job(adapter, script, code_=0, deadline=40):
            if adapter == 'codex':
                script = [x_thread()] + list(script)
            return dict(holder=HOLDER, source=str(src), revision='HEAD',
                        payload={'task': 'work the unit', 'script': script, 'code': code_}, adapter=adapter,
                        configuration=CONFIGURATION, deadline=time.time() + deadline)

        def submit(unit, adapter, script, code_=0, via=None):
            """(launch, error): a real dispatch on the account `via` names."""
            use = pinned(via)
            return attempt(lambda: use.submit(admitted(unit), 'build', **job(adapter, script, code_)))

        def finish(launch, via=None):
            if launch is None:
                return {}
            record, _ = attempt(lambda: pinned(via).wait(launch))
            return record or {}

        def markers_of(dispatch_id):
            found = []
            for path in sorted(markers.glob('*.json')):
                data = json.loads(path.read_text())
                if data.get('dispatch') == dispatch_id:
                    done = markers / ('%d.done' % data['pid'])
                    data['ended'] = json.loads(done.read_text())['ended'] if done.exists() else None
                    found.append(data)
            return found

        callback(locals())
    finally:
        for conn in connections:
            conn.close()
        shutil.rmtree(base, ignore_errors=True)
