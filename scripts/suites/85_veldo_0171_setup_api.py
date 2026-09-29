"""VELDO-0171: factory setup lays the API down behind Tailscale Serve, and a second run changes nothing.

Run: python3 scripts/selftest.py --suite 85_veldo_0171_setup_api

Only shared ROOT and expect are consumed. One temporary tree holds the .veldo copy the suite loads and the
installer copies its fixed executable from, so a registered mutation of a production file (the setup
module, its API steps, the service, the API, the scaffolder) reaches the run, the installed service and the
installed API process. Every path setup writes is scratch: the state roots, the host trust paths, the
install roots and the unit directories. Real: the owner's OpenSSH key generated here, Git clones, 0600
token files holding a stand-in token name, the setup module's own command surface (main) and every organ it
orders, the installed authority unit's ExecStart run as the service process and the installed API unit's
ExecStart run as the API process by a user manager stand-in of this run's own (Type=notify on its own
socket for the authority, Type=simple for the API, a unit's .wants links started with it, a BindsTo or
PartOf unit stopped with it, SIGTERM on stop), so nothing is installed into or started by the owner's real
systemd user manager. The Tailscale CLI setup runs is scripts/suites/support/v171_tailscale.py, which
replays proof/VELDO-0171/tailscale-capture.json exactly and logs every invocation where setup never looks;
the host's real Tailscale is never run. The host laid down by VELDO-0139 before this change is laid down by
the whole .veldo of commit 7fefdb9a (VELDO-0139 with VELDO-0140's delegation), taken from the repository's
history with `git archive`, so it holds that commit's engine and the re-run upgrades it (VELDO-0189) before
its API steps. Passkeys are software ES256 authenticators made with openssl, their ceremonies
assembled as WebAuthn lays them out and sent over HTTP to the API process's loopback listener with the
tailnet name as Host and Origin. Every Bot API exchange goes to a loopback stand-in, and a socket guard
refuses every connection beyond 127.0.0.1 in this process and in every process the stand-in manager starts.
No real key, token or credential is read; no private key byte, signature or token is printed.
"""


def _v171_suite():
    import base64
    import contextlib
    import hashlib
    import http.client
    import importlib.util
    import inspect
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
        'control_factory_setup_api.py': ROOT / ".veldo" / "control_factory_setup_api.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_api.py': ROOT / ".veldo" / "control_api.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    ROWS = ('install/assets', 'tailscale/capture', 'tailscale/fixed-paths', 'tailscale/refusals',
            'tailscale/serve-bg', 'api-edge/enrolled-by-owner', 'api/service-configuration', 'api/unit',
            'rerun/changes-nothing', 'rerun/arguments-compared', 'rerun/differs-refused',
            'api-edge/installed-api-call', 'api/loopback-only', 'passkey/first-enrollment',
            'api/content-security-policy', 'api-edge/running-service', 'rerun/over-0139-host', 'api/start-rules')
    IA, CA, FP, TR, TB, AE, SC, UN, RR, AR, DF, IC, LB, PK, CP, RS, OB, SR = ROWS
    rows = {name: [] for name in ROWS}
    # The setup module as VELDO-0139 (with VELDO-0140's delegation) shipped it, before this change.
    BEFORE = '7fefdb9a'

    # Attribute elapsed work between observations to the row that consumes it.
    timing_path = os.environ.get('VELDO_ROW_TIMINGS')
    timings = {name: 0.0 for name in ROWS}
    last_check = [time.monotonic()]

    def check(row, label, condition):
        now = time.monotonic()
        timings[row] += now - last_check[0]
        last_check[0] = now
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
    profiler = None
    if os.environ.get('VELDO_SUITE_PROFILE'):
        import cProfile
        profiler = cProfile.Profile()
        profiler.enable()
    prior_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    base = Path(tempfile.mkdtemp(prefix='b171-', dir=fast))
    support_path = Path(globals().get('__setup_support__', ROOT / 'scripts/suites/support/setup_runtime.py'))
    runtime = load('v171_runtime', support_path)
    close_runtime = runtime.install(base)
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
    fixtures186 = load('v171_install_fixtures', ROOT / 'proof/VELDO-0186/fixtures.py')
    engines186 = fixtures186.install(ROOT, base, mods)
    prior_path186 = os.environ.get('PATH', '')
    os.environ['PATH'] = str(engines186['path']) + os.pathsep + prior_path186
    H = load('v171_support', ROOT / 'scripts' / 'suites' / 'support' / 'v73_authority.py')
    STAND_IN = ROOT / 'scripts' / 'suites' / 'support' / 'v171_tailscale.py'
    TS = load('v171_tailscale', STAND_IN) if STAND_IN.is_file() else None
    _git_process = load('v171_git', mods / 'git_process.py')
    CS = load('v171_service', mods / 'control_service.py')
    CC = load('v171_client', mods / 'control_client.py')
    CEN = load('v171_enrollment', mods / 'control_enrollment.py')
    EL = load('v171_eligibility', mods / 'control_eligibility.py')
    IN = load('v171_ingress', mods / 'control_channel_ingress.py')
    claims = load('v171_claims', mods / 'control_claim.py')
    S, CM, AC = claims.S, claims.CM, claims.AC
    K = load('v171_keys', mods / 'control_keys.py')
    E = load('v171_edge', mods / 'control_channel_enrollment.py')
    AS = load('v171_assertion', mods / 'control_api_assertion.py')
    W = load('v171_webauthn', mods / 'control_api_webauthn.py')
    SA = load('v171_service_api', mods / 'control_service_api.py')
    CA_ = load('v171_client_api', mods / 'control_client_api.py')
    F = load('v171_setup', mods / 'control_factory_setup.py') if (mods / 'control_factory_setup.py').is_file() else None
    FA = (load('v171_setup_api', mods / 'control_factory_setup_api.py')
          if (mods / 'control_factory_setup_api.py').is_file() else None)
    API = load('v171_api', mods / 'control_api.py')
    CAPTURE = ROOT / 'proof' / 'VELDO-0171' / 'tailscale-capture.json'

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

    # The same guard, armed in every process the manager stand-in starts.
    guard_dir, guard_log, guard_armed = base / 'guard', base / 'guard-attempts', base / 'guard-armed'
    guard_dir.mkdir()
    (guard_dir / 'sitecustomize.py').write_text(
        'import os, socket\n'
        '_log, _armed = os.environ.get("VELDO_V171_GUARD_LOG"), os.environ.get("VELDO_V171_GUARD_ARMED")\n'
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

    with (guard_dir / 'sitecustomize.py').open('a') as handle:
        handle.write(
            '\nimport importlib.util\n'
            's = importlib.util.spec_from_file_location("setup_runtime", %r)\n'
            'r = importlib.util.module_from_spec(s); s.loader.exec_module(r)\n'
            'r.install(%r)\n'
            'if os.environ.get("VELDO_LISTEN_EVENT"): r.notify_listen(os.environ["VELDO_LISTEN_EVENT"])\n'
            % (str(support_path), str(base)))

    # Every store connection this process opens, recorded while `capturing` is set (the running-service row).
    connects, capturing = [], [False]

    def audit(event, args):
        if capturing[0] and event == 'sqlite3.connect':
            connects.append(str(args[0]) if args else '')
    sys.addaudithook(audit)

    def child_setup():
        os.umask(0o077)
        with contextlib.suppress(Exception):
            import ctypes
            ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM)

    class Manager:
        """A stand-in for the owner's systemd user manager answering the systemctl calls setup and the
        service's lifecycle make: start runs a unit's ExecStart (Type=notify waits for READY=1, Type=simple
        for its real inet listen event or its exit) and then starts every unit its .wants directory links; a unit whose
        BindsTo names an inactive unit does not start; stop stops every unit bound to or part of it first,
        with SIGTERM; show reports the unit's state; daemon-reload is recorded."""

        def __init__(self, unit_dir):
            self.unit_dir, self.procs, self.calls, self.logs = Path(unit_dir), {}, [], []

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
                self.stop(unit)
                return 0, '', ''
            if args[0] == 'restart':
                self.stop(unit)
                return self.start(unit)
            return 0, '', ''

        def start(self, unit):
            if not (self.unit_dir / unit).is_file():
                return 5, '', 'unit not found'
            if any(not self.alive(bound) for bound in self._field(unit, 'BindsTo')):
                return 1, '', 'a unit it binds to is inactive'
            if not self.alive(unit):
                kind = (self._field(unit, 'Type') or ['simple'])[0]
                env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': os.environ.get('HOME', str(base)),
                       'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC', 'PYTHONDONTWRITEBYTECODE': '1',
                       'PYTHONPATH': str(guard_dir), 'VELDO_V171_GUARD_LOG': str(guard_log),
                       'VELDO_V171_GUARD_ARMED': str(guard_armed)}
                if os.environ.get('XDG_RUNTIME_DIR'):
                    env['XDG_RUNTIME_DIR'] = os.environ['XDG_RUNTIME_DIR']
                notify = base / ('n%d.sock' % len(self.logs))
                listener = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
                listener.bind(str(notify))
                env['NOTIFY_SOCKET' if kind == 'notify' else 'VELDO_LISTEN_EVENT'] = str(notify)
                log = base / ('unit-%d-%s.log' % (len(self.logs), unit[:18]))
                self.logs.append(log)
                with open(log, 'wb') as out:
                    proc = subprocess.Popen(shlex.split(self._field(unit, 'ExecStart')[0]), env=env,
                                            stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                                            preexec_fn=child_setup)
                self.procs[unit] = proc
                try:
                    ready = runtime.ready(proc, listener, b'READY=1' if kind == 'notify' else b'LISTEN')
                finally:
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
                runtime.wake_authority(shlex.split(self._field(unit, 'ExecStart')[0])[-1])
                try:
                    proc.wait(15)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(5)

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
        return ' '.join(subprocess.run(['ssh-keygen', '-y', '-f', str(path)], capture_output=True, text=True,
                                       timeout=10, stdin=subprocess.DEVNULL).stdout.split()[:2])

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
        (path / 'README').write_text('v171 %s\n' % name)
        _git_process.run(['git', '-C', str(path), 'add', 'README'], check=True, capture_output=True)
        _git_process.run(['git', '-C', str(path), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'v171'], check=True,
                         capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        return path

    def fresh_root(name):
        path = base / name
        path.mkdir(mode=0o700)
        os.chmod(str(path), 0o700)
        return path

    def snapshot(*roots):
        """Every file, link and directory under `roots`: its mode and, for a file, its content digest."""
        seen = {}
        for top in roots:
            top = Path(top)
            if not os.path.lexists(str(top)):
                continue
            if top.is_file() or top.is_symlink():
                paths = [str(top)]
            else:
                paths = [str(top)]
                for directory, dirs, files in os.walk(str(top)):
                    paths += [os.path.join(directory, name) for name in dirs + files]
            for path in paths:
                info = os.lstat(path)
                digest = None
                if stat.S_ISREG(info.st_mode) and info.st_mode & 0o400:
                    with open(path, 'rb') as handle:
                        digest = hashlib.sha256(handle.read()).hexdigest()
                elif stat.S_ISLNK(info.st_mode):
                    digest = 'link:' + os.readlink(path)
                seen[path] = (stat.S_IMODE(info.st_mode), digest)
        return seen

    def changes(before, after):
        return (sorted(k for k in before if k in after and before[k] != after[k]),
                sorted(k for k in after if k not in before), sorted(k for k in before if k not in after))

    def mode_of(path):
        try:
            info = os.lstat(str(path))
        except OSError:
            return None
        return oct(stat.S_IMODE(info.st_mode)), info.st_uid

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

    def state_of(store):
        return read_store(store, lambda c: CM.authority_state(S, c))

    owner = 'dmitry'
    chat = 5590171
    token = 'v171tok' + os.urandom(8).hex()
    bot_user = {'id': 8000000171, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_api_bot'}
    url, bot_api, stop_bot_api = H.stand_in({token: bot_user})
    bot_api['chats'][chat] = {'id': chat, 'type': 'private', 'first_name': 'Owner'}
    person = base / 'person'
    person.mkdir(mode=0o700)
    owner_key = person / 'owner'
    keygen(owner_key, 'v171-owner')
    other_key = person / 'other'
    keygen(other_key, 'v171-other')
    token_file = private(person / 'bot-token', token + '\n')
    other_token = private(person / 'other-token', 'v171tok' + os.urandom(8).hex() + '\n')
    profile = {'kind': 'linux-systemd', 'slice': 'v171%s.slice' % os.urandom(3).hex(), 'lock': str(base / 'workers.lock'),
               'concurrency': 1, 'runtime_seconds': 600, 'memory_bytes': 256 << 20, 'cpu_percent': 100,
               'file_bytes': 64 << 20, 'tasks_max': 256, 'stop_grace_seconds': 1, 'kill_grace_seconds': 1}
    ts = TS.stand_in(CAPTURE, sys.executable) if TS is not None and CAPTURE.is_file() else None
    port = TS.free_port() if TS is not None else 0
    managers = []

    def setup(state_root, workspace, host_trust, install, units, manager, tailscale=None, module=None, **replace):
        """veldo factory setup through the module's own command surface, into this run's scratch, with the
        user manager stand-in, the loopback Bot API and the Tailscale stand-in: (exit code, JSON answer)."""
        argv = {'--state-root': str(state_root), '--owner': owner, '--owner-key': str(owner_key),
                '--workspace': str(workspace), '--chat': str(chat), '--token-file': str(token_file)}
        argv.update(replace)
        overrides = dict(host_trust=str(host_trust), install_root=str(install), unit_dir=str(units), profile=profile,
                         writable=[], runner=manager, origin=url)
        if module is None:
            module = F
            overrides.update(tailscale=[ts.path] if tailscale is None else tailscale, api_port=port)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = module.main(['setup'] + [x for pair in argv.items() for x in pair], **overrides)
        try:
            shown = json.loads(out.getvalue().strip().splitlines()[-1])
        except (ValueError, IndexError):
            shown = {'unparsed': out.getvalue()[-300:]}
        return code, shown

    def passkey(state_root, *extra):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = F.main(['passkey', '--state-root', str(state_root), '--owner', owner, '--owner-key', str(owner_key)]
                          + list(extra))
        try:
            return code, json.loads(out.getvalue().strip().splitlines()[-1])
        except (ValueError, IndexError):
            return code, {'unparsed': out.getvalue()[-300:]}

    capture = json.loads(CAPTURE.read_text()) if CAPTURE.is_file() else {}
    ready = next((s['outputs'] for s in capture.get('derived_states') or [] if s.get('name') == 'ready'), {})
    NAME = str(((ready.get('status') or {}).get('Self') or {}).get('DNSName') or '').rstrip('.')
    ORIGIN = 'https://' + NAME
    TARGET = 'http://127.0.0.1:%d' % port
    SERVE = ['serve', '--bg', '--https=443', TARGET]
    READS = (['version'], ['status', '--json'], ['serve', 'status', '--json'], ['debug', 'prefs'], ['serve', '--help'])

    class Browser:
        """A local passkey stand-in: an openssl P-256 key, and ceremony results assembled as WebAuthn lays them
        out. authenticatorData is SHA-256(rp id), the flags byte (user present and verified) and a zero
        counter; the signature is openssl's over authenticatorData || SHA-256(clientDataJSON)."""

        def __init__(self, name):
            self.key = person / (name + '.pem')
            subprocess.run(['openssl', 'genpkey', '-algorithm', 'EC', '-pkeyopt', 'ec_paramgen_curve:P-256', '-out',
                            str(self.key)], check=True, capture_output=True, timeout=10)
            self.der = subprocess.run(['openssl', 'pkey', '-in', str(self.key), '-pubout', '-outform', 'DER'], check=True,
                                      capture_output=True, timeout=10).stdout
            self.credential_id = b64(os.urandom(32))
            self.user_handle = None

        def public_key(self):
            return b64(self.der)

        def sign(self, message):
            return subprocess.run(['openssl', 'dgst', '-sha256', '-sign', str(self.key)], input=message, check=True,
                                  capture_output=True, timeout=10).stdout

        def create(self, challenge, origin):
            client = json.dumps({'type': 'webauthn.create', 'challenge': challenge, 'origin': origin,
                                 'crossOrigin': False}, separators=(',', ':')).encode()
            return {'credential_id': self.credential_id, 'public_key': self.public_key(), 'algorithm': -7,
                    'client_data_json': b64(client)}

        def get(self, challenge, origin, rp_id):
            client = json.dumps({'type': 'webauthn.get', 'challenge': challenge, 'origin': origin, 'crossOrigin': False},
                                separators=(',', ':')).encode()
            auth = hashlib.sha256(rp_id.encode()).digest() + bytes([0x05]) + b'\x00\x00\x00\x00'
            return {'credential_id': self.credential_id, 'client_data_json': b64(client), 'authenticator_data': b64(auth),
                    'signature': b64(self.sign(auth + hashlib.sha256(client).digest())), 'user_handle': self.user_handle}

    def b64(data):
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

    responses = []

    def call(method, path, body=None, cookie=None):
        """One HTTP request to the API process's loopback listener with the tailnet name as Host (and Origin for
        a write): (status, headers, JSON). Every response's headers are kept for the policy row."""
        headers = {'Host': NAME}
        if method == 'POST':
            headers.update({'Origin': ORIGIN, 'Sec-Fetch-Site': 'same-origin', 'Content-Type': 'application/json'})
        if cookie:
            headers['Cookie'] = '__Host-veldo-session=' + cookie
        try:
            conn = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
            conn.request(method, path, body=json.dumps(body).encode() if body is not None else None, headers=headers)
            answer = conn.getresponse()
            raw = answer.read()
            got = (answer.status, answer.getheaders(), json.loads(raw) if raw else None)
            conn.close()
        except (OSError, ValueError, http.client.HTTPException) as exc:
            got = (0, [], {'refusal': 'no_answer:%s' % type(exc).__name__})
        responses.append((method, path, got[0], got[1]))
        return got

    def header(got, name):
        return next((v for k, v in got[1] if k.lower() == name.lower()), None)

    def register(browser, label):
        """The registration and possession ceremonies over the API: (last answer, pending fingerprint or None)."""
        begun = call('POST', '/api/v1/auth/registration/begin', {'label': label})
        if begun[0] != 200:
            return begun, None
        browser.user_handle = begun[2]['user_handle']
        offered = call('POST', '/api/v1/auth/registration/credential',
                       dict(browser.create(begun[2]['challenge'], ORIGIN), registration_id=begun[2]['registration_id']))
        if offered[0] != 200:
            return offered, None
        proof = browser.get(offered[2]['possession_challenge'], ORIGIN, NAME)
        proved = call('POST', '/api/v1/auth/registration/possession',
                      dict({k: v for k, v in proof.items() if k != 'credential_id'},
                           registration_id=begun[2]['registration_id']))
        return proved, ((proved[2] or {}).get('fingerprint') if proved[0] == 200 else None)

    def sign_in(browser):
        issued = call('POST', '/api/v1/auth/challenge', {})
        if issued[0] != 200:
            return issued, None
        done = call('POST', '/api/v1/auth/sign-in', browser.get(issued[2]['challenge'], ORIGIN, NAME))
        cookie = (header(done, 'Set-Cookie') or '').split(';')[0].partition('=')[2]
        return done, cookie or None

    def listening(pid):
        """The inet sockets process `pid` listens on: [(address, port)]."""
        inodes = set()
        with contextlib.suppress(OSError):
            for fd in os.listdir('/proc/%d/fd' % pid):
                with contextlib.suppress(OSError):
                    target = os.readlink('/proc/%d/fd/%s' % (pid, fd))
                    if target.startswith('socket:['):
                        inodes.add(target[8:-1])
        found = []
        for table, width in (('/proc/net/tcp', 8), ('/proc/net/tcp6', 32)):
            with contextlib.suppress(OSError):
                for line in Path(table).read_text().splitlines()[1:]:
                    fields = line.split()
                    if len(fields) > 9 and fields[3] == '0A' and fields[9] in inodes:
                        address, _, hex_port = fields[1].partition(':')
                        if width == 8:
                            text = '.'.join(str(b) for b in bytes.fromhex(address)[::-1])
                        else:
                            text = 'v6:' + address
                        found.append((text, int(hex_port, 16)))
        return found

    def service_send(state_root, packet, key=owner_key, namespace='veldo-command'):
        """One request to the authority service of the factory at `state_root`, signed with `key`."""
        laid = json.loads((Path(state_root) / 'host' / 'ingress.json').read_text())
        trust, workspace = EL.load_host_trust(laid['host_trust']), laid['workspace']
        verify = trust.verifier(owner, workspace)
        try:
            return CC.send(workspace, packet, CEN, verify, lambda data: sign_with(key, data, namespace),
                           trust.host_identity, timeout=30)
        except CC.RoutingRefused as exc:
            return {'accepted': False, 'reason': 'routing:' + exc.reason}

    try:
        takes = (F is not None and FA is not None and ts is not None
                 and 'tailscale' in inspect.signature(F.setup).parameters)
        if not takes:
            for name in ROWS:
                check(name, 'veldo factory setup lays the API down (.veldo/control_factory_setup_api.py, setup takes the '
                      'Tailscale CLI\'s system paths, and the capture and its stand-in exist)', False)
            raise StopIteration

        # AC1 to AC3: the module, its template and its routing travel with the engine.
        with section(IA):
            scaffold = load('v171_scaffold', mods / 'init_scaffold.py')
            for rel in ('.veldo/control_factory_setup_api.py', '.veldo/services/veldo-api.service'):
                check(IA, rel + ' installed by the scaffold, not claimed as validator substrate',
                      rel in scaffold._FILES and rel not in scaffold.REQUIRED_SUBSTRATE)
            for rel in ('.veldo/control_factory_setup.py', '.veldo/control_factory_setup_api.py', '.veldo/control_service.py',
                        '.veldo/control_api.py', '.veldo/init_scaffold.py', '.veldo/services/veldo-api.service', 'bin/veldo'):
                engine = ROOT / 'engine' / rel
                check(IA, rel + ' engine copy identical', engine.is_file() and engine.read_bytes() == (ROOT / rel).read_bytes())
            check(IA, 'the API process is an entry point of the installed fixed executable',
                  'control_client_api.py' in CS.ENTRY_POINTS and 'control_client_api.py' in CS.closure())
            env = dict(os.environ, XDG_CONFIG_HOME=str(base / 'cli-xdg'), XDG_DATA_HOME=str(base / 'cli-data'))
            done = subprocess.run([sys.executable, '-B', str(ROOT / 'bin' / 'veldo'), 'factory', 'passkey', '--state-root',
                                   str(base / 'nowhere'), '--owner', owner, '--owner-key', str(owner_key)],
                                  capture_output=True, text=True, timeout=60, env=env, stdin=subprocess.DEVNULL)
            shown = json.loads(done.stdout.strip().splitlines()[-1]) if done.stdout.strip() else {}
            check(IA, 'bin/veldo factory passkey reaches the passkey command, which refuses a state root setup did not '
                  'lay down by name [%s %s]' % (done.returncode, shown.get('reason')),
                  done.returncode == 1 and shown.get('action') == 'passkey'
                  and shown.get('reason') == 'missing_authority:state_root:not_set_up')

        # AC2: the committed capture is the scrubbed read-only capture, and every state is a listed field edit.
        with section(CA):
            check(CA, 'the capture names the five read-only commands it was taken with [%s]' % capture.get('capture_commands'),
                  capture.get('capture_commands') == ['version', 'status --json', 'serve status --json', 'debug prefs',
                                                      'serve --help'])
            states = {s['name']: s for s in capture.get('derived_states') or []}
            edits = {e['state']: e['edits'] for e in capture.get('field_edits') or []}
            check(CA, 'each state the stand-in replays is listed with its field edits [%s]' % sorted(states),
                  set(states) == {'ready', 'operator', 'https', 'persistence', 'logged-out', 'served', 'occupied'}
                  and set(edits) == set(states))
            for name, found in sorted(states.items()):
                rebuilt = json.loads(json.dumps(capture['captured'] if found['base'] == 'captured' else states[found['base']]['outputs']))
                for edit in edits.get(name, []):
                    parent = rebuilt[edit['source']] if edit['path'] else rebuilt
                    for key in edit['path'][:-1]:
                        parent = parent[key]
                    key = edit['path'][-1] if edit['path'] else edit['source']
                    check(CA, '%s: the edit of %s %s names the value it replaces' % (name, edit['source'], edit['path']),
                          parent.get(key) == edit['before'])
                    parent[key] = edit['after']
                check(CA, '%s: its outputs are its base with exactly its listed edits' % name, rebuilt == found['outputs'])

            def leaves(value, key=''):
                if isinstance(value, dict):
                    for k, v in value.items():
                        yield from leaves(v, k)
                elif isinstance(value, list):
                    for v in value:
                        yield from leaves(v, key)
                elif isinstance(value, str):
                    yield key, value
            allowed = set(capture.get('field_allowlist') or [])
            constants = capture.get('constant_allowlist') or {}
            captured = capture.get('captured') or {}
            loose = []
            for part in ('status', 'serve-status'):
                for key, value in leaves(captured.get(part)):
                    if value != '<string>' and value not in (constants.get(key) or []):
                        loose.append(key)

            def keys_of(value):
                if isinstance(value, dict):
                    for k, v in value.items():
                        yield k
                        yield from keys_of(v)
                elif isinstance(value, list):
                    for v in value:
                        yield from keys_of(v)
            dynamic = [k for part in ('status', 'serve-status') for k in keys_of(captured.get(part))
                       if k not in allowed and not k.startswith('<string:')]
            check(CA, 'the captured JSON keeps only allowlisted field names and constants; every other string is a '
                  'placeholder [%s %s]' % (loose[:3], dynamic[:3]), captured and not loose and not dynamic)
            check(CA, 'the captured prefs keep only the OperatorUser presence, never a value [%s]'
                  % (captured.get('prefs') or {}).get('OperatorUser'),
                  (captured.get('prefs') or {}).get('OperatorUser') == '<string>'
                  and all(v in (None, '<string>') for _k, v in leaves(captured.get('prefs'))))
            check(CA, 'the captured serve help keeps only the --bg flag', captured.get('serve-help') == '--bg\n')
            # The stand-in prints exactly the ready state's outputs.
            printed = {tuple(c): subprocess.run([ts.path] + c, capture_output=True, text=True, timeout=30) for c in READS}
            outputs = states.get('ready', {}).get('outputs', {})
            check(CA, 'the stand-in prints the ready state\'s outputs exactly for each read-only command',
                  json.loads(printed[('status', '--json')].stdout) == outputs.get('status')
                  and json.loads(printed[('serve', 'status', '--json')].stdout) == outputs.get('serve-status')
                  and json.loads(printed[('debug', 'prefs')].stdout) == outputs.get('prefs')
                  and printed[('serve', '--help')].stderr == outputs.get('serve-help')
                  and printed[('version',)].stdout == outputs.get('version'))
            ts.clear()

        # AC2: the CLI comes from the fixed system locations, never PATH.
        with section(FP):
            check(FP, 'every location is an absolute system path [%s]' % (FA.TAILSCALE_PATHS,),
                  FA.TAILSCALE_PATHS and all(os.path.isabs(p) and not p.startswith(('/home', '/tmp', '/dev/shm'))
                                             for p in FA.TAILSCALE_PATHS))
            planted = base / 'on-path'
            planted.mkdir()
            shutil.copyfile(ts.path, planted / 'tailscale')
            os.chmod(str(planted / 'tailscale'), 0o700)
            saved = os.environ.get('PATH', '')
            os.environ['PATH'] = str(planted) + os.pathsep + saved
            try:
                try:
                    FA.Tailscale([])
                    found = 'resolved'
                except FA.Refused as exc:
                    found = exc.code
                try:
                    FA.Tailscale(['tailscale'])
                    relative = 'resolved'
                except FA.Refused as exc:
                    relative = exc.code
            finally:
                os.environ['PATH'] = saved
            check(FP, 'a CLI only on PATH, or named relatively, is not used: unavailable_service:tailscale [%s %s]'
                  % (found, relative), found == relative == 'unavailable_service:tailscale')
            check(FP, 'the planted CLI on PATH was never run', ts.invocations() == [])

        # AC2: the three refusals, a logged-out and an absent Tailscale and an occupied Serve, before any write.
        with section(TR), contextlib.ExitStack() as reset:
            reset.callback(ts.clear)
            reset.callback(ts.set, 'ready')
            clone_t = clone('clone-t')
            trust_t = base / 'xdg-t' / 'veldo' / 'host_trust.json'
            manager_t = Manager(base / 'units-t')
            for state, expected, paths in (
                    ('operator', 'unavailable_service:tailscale:operator', None),
                    ('https', 'unavailable_service:tailscale:https', None),
                    ('persistence', 'unavailable_service:tailscale:persistence', None),
                    ('logged-out', 'unavailable_service:tailscale', None),
                    ('occupied', 'invalid_input:tailscale_serve:occupied', None),
                    ('ready', 'unavailable_service:tailscale', [str(base / 'no-such-bin' / 'tailscale')])):
                ts.set(state)
                ts.clear()
                root_t = fresh_root('state-t-' + state + ('-absent' if paths else ''))
                before = snapshot(base)
                code, shown = setup(root_t, clone_t, trust_t, base / 'install-t', base / 'units-t', manager_t, tailscale=paths)
                changed, added, removed = changes(before, snapshot(base))
                seen = ts.invocations()
                check(TR, '%s%s: refused as %s, writing nothing [%s %s]' % (state, ' with no CLI' if paths else '', expected,
                                                                          shown.get('reason'), (changed + added + removed)[:3]),
                      code == 1 and shown.get('reason') == expected and not (changed or added or removed))
                check(TR, '%s: only read-only commands ran [%s]' % (state, seen),
                      all(c in [list(r) for r in READS] for c in seen) and (paths is not None or seen))

        # The fresh host.
        clone_a = clone('clone-a')
        root_a = fresh_root('state-a')
        trust_a = base / 'xdg-a' / 'veldo' / 'host_trust.json'
        install_a, units_a = base / 'install-a', base / 'units-a'
        manager_a = Manager(units_a)
        managers.append(manager_a)
        code, report = setup(root_a, clone_a, trust_a, install_a, units_a, manager_a)
        log_a = ts.invocations()
        calls_a = list(manager_a.calls)
        ok = code == 0 and report.get('outcome') == 'set_up'
        if not ok:
            for name in ROWS:
                if not rows[name] or name in (TB, AE, SC, UN, RR, AR, DF, IC, LB, PK, CP, RS, OB, SR):
                    check(name, 'veldo factory setup completed over an empty 0700 state root [%s]'
                          % {k: report.get(k) for k in ('outcome', 'reason', 'detail')}, False)
            raise StopIteration
        unit_a, home_a = report['unit'], Path(report['home'])
        store_a, keys_a, host_a = root_a / 'authority' / 'control.sqlite3', root_a / 'keys', root_a / 'host'
        laid_a = json.loads((host_a / 'ingress.json').read_text())
        api_unit_a = 'veldo-api-' + unit_a[len('veldo-authority-'):]

        # AC2 (declared falsifier): one successful `serve --bg` naming the API port, and never Funnel.
        with section(TB):
            serves = [c for c in log_a if c[:1] == ['serve'] and '--bg' in c]
            check(TB, 'the invocation log shows exactly one `serve --bg --https=443 %s` [%s]' % (TARGET, serves),
                  serves == [SERVE])
            check(TB, 'the stand-in accepted it: the Serve status now maps the tailnet name to the API port [%s]'
                  % ts.target(), ts.target() == TARGET)
            check(TB, 'no `funnel` invocation [%s]' % [c for c in log_a if c[:1] == ['funnel']],
                  not any(c[:1] == ['funnel'] for c in log_a))
            check(TB, 'every other invocation is one of the read-only commands [%s]'
                  % [c for c in log_a if c != SERVE and c not in [list(r) for r in READS]],
                  all(c == SERVE or c in [list(r) for r in READS] for c in log_a))
            status = json.loads(subprocess.run([ts.path, 'serve', 'status', '--json'], capture_output=True, text=True,
                                               timeout=30).stdout)
            check(TB, 'the Serve status read back names the tailnet name\'s HTTPS and the loopback port',
                  status == {'TCP': {'443': {'HTTPS': True}}, 'Web': {NAME + ':443': {'Handlers': {'/': {'Proxy': TARGET}}}}})
            check(TB, 'setup reports the Serve step done, with the tailnet name and port it used [%s]' % report.get('api'),
                  {'step': 'tailscale_serve', 'outcome': 'done'} in report.get('steps', [])
                  and (report.get('api') or {}).get('tailnet_name') == NAME and (report.get('api') or {}).get('port') == port)
            ts.clear()

        # AC1: the api edge key, enrolled by the owner's signed command with its possession co-signature.
        with section(AE):
            state = state_of(store_a)
            record = E.edge_record(state, E.edge_key_id('api')) or {}
            key, connection = keys_a / E.edge_key_id('api'), root_a / 'edge' / 'api-auth'
            check(AE, 'the api edge key is a 0600 file in the protected key directory, its connection key beside the '
                  'Telegram edge\'s', mode_of(key) == ('0o600', os.getuid()) and mode_of(connection) == ('0o600', os.getuid())
                  and (root_a / 'edge' / 'edge-auth').is_file())
            check(AE, 'the enrolled record is those keys, for the api edge principal the ingress names [%s]'
                  % record.get('principal'),
                  record.get('public_key') == derived(key) and record.get('connection_public_key') == derived(connection)
                  and record.get('principal') == laid_a.get('api_edge') == 'api-edge' and record.get('channel') == 'api')
            proof = record.get('possession') or {}
            check(AE, 'enrolled by the owner, its possession proof the edge key\'s own signature over the envelope',
                  record.get('enrolled_by') == owner and (proof.get('envelope') or {}).get('principal') == owner
                  and AC.ssh_keygen_verify(AC.canonical_envelope_bytes(proof.get('envelope') or {}), proof.get('signature') or '',
                                           AC.allowed_signers_line(record.get('principal'), record.get('public_key'),
                                                                   E.POSSESSION_NAMESPACE),
                                           record.get('principal'), E.POSSESSION_NAMESPACE)[0])
            member = AC.membership_entry(state['membership'], 'api-edge') or {}
            check(AE, 'the api edge is a service member', member.get('principal_type') == 'service')
            enrolled = [r for r in journal(store_a) if 'api-edge' in str(r.get('command_id'))]
            check(AE, 'the journal holds one api edge enrollment [%d]' % len(enrolled), len(enrolled) == 1)
            projection = (host_a / 'allowed_signers').read_text()
            check(AE, 'the key projection is republished with the api edge key',
                  projection == K.projection(state) and record.get('public_key', 'absent') in projection)

        # AC2: the API service and process configurations, the tailnet name as rp_id and origin.
        with section(SC):
            service_path, copied = host_a / 'api-service.json', home_a / 'config' / 'api-service.json'
            config = json.loads(service_path.read_text())
            check(SC, 'host/api-service.json is a 0600 veldo.api_service/v1 the service constructs the API from [%s]'
                  % config.get('schema'), mode_of(service_path) == ('0o600', os.getuid())
                  and SA.load_config(str(service_path)).get('schema') == 'veldo.api_service/v1')
            check(SC, 'its rp_id is the tailnet name and its origin https://<tailnet name> [%s %s]'
                  % (config.get('rp_id'), config.get('origin')), config.get('rp_id') == NAME and config.get('origin') == ORIGIN)
            check(SC, 'it rides on the Telegram ingress\'s api edge', config.get('api_edge') == laid_a.get('api_edge'))
            shown = json.loads((home_a / 'config' / 'service.json').read_text())
            check(SC, 'installed with the authority service: copied 0600 and named by its service configuration',
                  copied.read_bytes() == service_path.read_bytes() and mode_of(copied) == ('0o600', os.getuid())
                  and shown.get('api_service') == str(copied))
            process_path = home_a / 'config' / 'api-process.json'
            process = CA_.load_config(str(process_path))
            check(SC, 'the 0600 veldo.api_process/v1 listens on loopback at the API port [%s]' % process.get('listen'),
                  mode_of(process_path) == ('0o600', os.getuid()) and process.get('listen') == {'host': '127.0.0.1', 'port': port})
            check(SC, 'its API origin, relying party and Host are the tailnet name',
                  (process.get('api') or {}).get('origin') == ORIGIN and (process.get('api') or {}).get('rp_id') == NAME
                  and (process.get('api') or {}).get('host') == NAME)
            check(SC, 'it signs through the protected signer with the api edge\'s key id and connection key',
                  process.get('signer') == {'config': str(host_a / 'signer.json'), 'edge_key_id': E.edge_key_id('api'),
                                            'connection_key': str(root_a / 'edge' / 'api-auth')})

        # AC2: the API unit, from its template beside the authority's, wanted by and bound to the authority unit.
        with section(UN):
            unit_path = units_a / api_unit_a
            text = unit_path.read_text() if unit_path.is_file() else ''
            fields = dict(line.split('=', 1) for line in text.splitlines() if '=' in line and not line.startswith('#'))
            python = json.loads((home_a / 'config' / 'service.json').read_text()).get('python')
            check(UN, 'the API unit is the template beside veldo-authority.service, every field filled',
                  text == FA.unit_text(unit_a, python, str(home_a / 'bin' / 'control_client_api.py'),
                                       str(home_a / 'config' / 'api-process.json'))
                  and (mods / 'services' / 'veldo-api.service').is_file() and '@' not in text.split('\n[Unit]')[-1])
            check(UN, 'it binds to, is part of, follows and is wanted by the authority unit [%s]'
                  % {k: fields.get(k) for k in ('BindsTo', 'PartOf', 'After', 'WantedBy')},
                  all(fields.get(k) == unit_a for k in ('BindsTo', 'PartOf', 'After', 'WantedBy')))
            check(UN, 'it runs the installation\'s own API process on its configuration [%s]' % fields.get('ExecStart'),
                  fields.get('ExecStart') == '%s -B %s serve %s' % (python, home_a / 'bin' / 'control_client_api.py',
                                                                     home_a / 'config' / 'api-process.json')
                  and (home_a / 'bin' / 'control_client_api.py').is_file()
                  and (home_a / 'bin' / 'control_client_api.py').read_bytes() == (mods / 'control_client_api.py').read_bytes())
            wants = units_a / (unit_a + '.wants') / api_unit_a
            check(UN, 'the authority unit wants it (the link enable writes)',
                  wants.is_symlink() and os.readlink(str(wants)) == os.path.join('..', api_unit_a))
            check(UN, 'setup started, stopped and restarted nothing [%s]' % [c[0] for c in calls_a],
                  not any(c[0] in ('start', 'stop', 'restart', 'enable') for c in calls_a)
                  and not manager_a.alive(unit_a) and not manager_a.alive(api_unit_a))

        # The fresh host's service is started by the owner: the API unit starts with it.
        began = CS.start(unit_a, manager_a)
        api_pid = manager_a.pid(api_unit_a)
        check(LB, 'the API reached its listen event before exiting or the bounded startup deadline',
              api_pid is not None and bool(listening(api_pid)))
        with section(UN):
            check(UN, 'starting the authority unit starts the API unit it wants [%s %s]'
                  % (began.get('ActiveState'), manager_a.alive(api_unit_a)),
                  began.get('ActiveState') == 'active' and api_pid is not None)

        # AC1 (declared falsifier): the installed API's calls are accepted; a call signed by any other key is not.
        with section(IC):
            inspected = service_send(root_a, {'operation': 'inspect', 'entity_ids': []})
            api_status = (inspected.get('result') or {}).get('api') or {}
            check(IC, 'the service runs the API and the installed API process subscribed with a call signed through the '
                  'protected signer\'s api purpose [%s]' % {k: api_status.get(k) for k in ('available', 'subscribers', 'refusal')},
                  api_status.get('available') is True and api_status.get('subscribers', 0) >= 1)
            observed = [json.loads(line) for line in (home_a / 'state' / 'observations.jsonl').read_text().splitlines()] \
                if (home_a / 'state' / 'observations.jsonl').is_file() else []
            calls = [o for o in observed if o.get('operation') == AS.CALL]
            check(IC, 'the service accepted the API process\'s calls [%s]' % [(o.get('call'), o.get('outcome')) for o in calls][:4],
                  any(o.get('outcome') == 'accepted' for o in calls))
            probe = AS.call_command('inspect', {'entity_ids': []})
            by_edge = service_send(root_a, probe, key=keys_a / E.edge_key_id('api'), namespace=AS.REQUEST_NAMESPACE)
            check(IC, 'a call signed with the enrolled api edge key in the API request namespace is accepted [%s]'
                  % by_edge.get('reason'), by_edge.get('accepted') is True)
            for label, key, namespace in (('the owner\'s key', owner_key, AS.REQUEST_NAMESPACE),
                                          ('the Telegram edge key', keys_a / E.edge_key_id('telegram_chat'), AS.REQUEST_NAMESPACE),
                                          ('an unenrolled key', other_key, AS.REQUEST_NAMESPACE)):
                refused = service_send(root_a, probe, key=key, namespace=namespace)
                check(IC, 'a call signed by %s is refused by the service [%s]' % (label, refused.get('reason')),
                      refused.get('accepted') is False and refused.get('reason') == 'command_signature_invalid')

        # AC2: the API listens on loopback only, and the authority service on no inet socket at all.
        with section(LB):
            found = listening(api_pid or 0)
            check(LB, 'the API process listens on 127.0.0.1:%d and nowhere else [%s]' % (port, found),
                  found == [('127.0.0.1', port)])
            check(LB, 'the authority service listens on no inet socket [%s]' % listening(manager_a.pid(unit_a) or 0),
                  manager_a.pid(unit_a) is not None and listening(manager_a.pid(unit_a)) == [])
            check(LB, 'no process tried to reach beyond loopback [%s %s]'
                  % (attempts, guard_log.read_text().split() if guard_log.is_file() else []),
                  attempts == [] and not (guard_log.is_file() and guard_log.read_text().strip()))

        # AC3 (declared falsifier): the owner's first passkey, signed at the host by the one fingerprint he names.
        with section(PK):
            phone, tablet = Browser('phone'), Browser('tablet')
            first, phone_print = register(phone, 'phone')
            second, tablet_print = register(tablet, 'tablet')
            check(PK, 'two passkeys register through the API with the tailnet name as Host and Origin [%s %s]'
                  % ((first[2] or {}).get('refusal') or first[0], (second[2] or {}).get('refusal') or second[0]),
                  phone_print is not None and tablet_print is not None)
            check(PK, 'each registration shows the fingerprint of the key its phone holds',
                  phone_print == W.fingerprint(phone.public_key()) and tablet_print == W.fingerprint(tablet.public_key()))
            code, listed = passkey(root_a)
            shown = sorted((p.get('label'), p.get('fingerprint'), p.get('principal')) for p in listed.get('pending') or [])
            check(PK, 'veldo factory passkey lists both, each with its label, fingerprint and principal [%s]' % shown,
                  code == 0 and shown == sorted([('phone', phone_print, owner), ('tablet', tablet_print, owner)]))
            head = journal(store_a)
            code, unknown = passkey(root_a, '--sign', 'SHA256:0000:0000')
            check(PK, 'a fingerprint no pending registration has is refused by name, signing nothing [%s]'
                  % unknown.get('reason'), code == 1 and unknown.get('reason') == 'invalid_input:passkey:unknown'
                  and journal(store_a) == head)
            # A failed listener still exercises the real command with this browser's fingerprint;
            # it must refuse by assertion, not pass None to argparse and abort the row.
            code, signed = passkey(root_a, '--sign', phone_print or W.fingerprint(phone.public_key()))
            enrolled = (signed.get('enrolled') or {})
            check(PK, 'the owner signs the ONE registration he names, and the running service admits it [%s %s]'
                  % (signed.get('outcome'), signed.get('reason')),
                  code == 0 and signed.get('outcome') == 'enrolled' and enrolled.get('fingerprint') == phone_print
                  and enrolled.get('principal') == owner and enrolled.get('credential_id') == phone.credential_id)
            credentials = [r for r in journal(store_a)[len(head):] if 'passkey-' in str(r.get('command_id'))]
            check(PK, 'exactly one credential enrollment was committed [%d]' % len(credentials), len(credentials) == 1)
            done, cookie = sign_in(phone)
            session = call('GET', '/api/v1/auth/session', cookie=cookie) if cookie else (0, [], {})
            check(PK, 'he signs in with it and the session names him [%s %s]'
                  % (done[0], (session[2] or {}).get('principal')),
                  done[0] == 200 and session[0] == 200 and (session[2] or {}).get('principal') == owner)
            other, other_cookie = sign_in(tablet)
            check(PK, 'the other registration cannot sign in [%s %s]' % (other[0], (other[2] or {}).get('refusal')),
                  other[0] == 401 and other_cookie is None)
            code, listed = passkey(root_a)
            check(PK, 'and it is still the one pending registration [%s]'
                  % [p.get('label') for p in listed.get('pending') or []],
                  code == 0 and [p.get('fingerprint') for p in listed.get('pending') or []] == [tablet_print])

        # AC3: every API response carries the same-origin content security policy.
        with section(CP):
            policy = API.CSP if hasattr(API, 'CSP') else ''
            directives = {d.split()[0]: d.split()[1:] for d in policy.split(';') if d.strip()}
            check(CP, 'the policy is same-origin with no framing, no base and no inline script [%s]' % policy,
                  directives == {'default-src': ["'self'"], 'script-src': ["'self'"], 'connect-src': ["'self'"],
                                 'form-action': ["'self'"], 'frame-ancestors': ["'none'"], 'base-uri': ["'none'"]}
                  and 'unsafe' not in policy)
            call('GET', '/api/v1/auth/session')
            call('POST', '/api/v1/auth/registration/begin', {'label': ''})
            ceremony = [r for r in responses if '/auth/' in r[1]]
            missing = [(m, p, s) for m, p, s, h in responses
                       if [v for k, v in h if k.lower() == 'content-security-policy'] != [policy]]
            check(CP, 'every one of the %d API responses, the %d ceremony ones among them, carries the policy once [%s]'
                  % (len(responses), len(ceremony), missing[:3]),
                  policy and len(ceremony) >= 10 and not missing
                  and {s for _m, _p, s, _h in responses} >= {200, 400, 401})
            raw = []
            for request in (b'PUT /api/v1/auth/session HTTP/1.1\r\nHost: ' + NAME.encode() + b'\r\nContent-Length: 0\r\n\r\n',
                            b'GET /api/v1/auth/session extra HTTP/1.1\r\nHost: ' + NAME.encode() + b'\r\n\r\n'):
                data = b''
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=10) as sock:
                        sock.sendall(request)
                        sock.shutdown(socket.SHUT_WR)
                        while True:
                            chunk = sock.recv(65536)
                            if not chunk:
                                break
                            data += chunk
                except OSError:
                    data = b''
                raw.append(data)
            check(CP, 'the responses http.server writes itself (an unsupported method, a malformed request line) carry it '
                  'too',
                  all(('Content-Security-Policy: ' + policy).encode() in data for data in raw) and all(raw))

        # AC2: the API unit stops with the authority unit.
        CS.stop(unit_a, manager_a)
        with section(UN):
            check(UN, 'stopping the authority unit stops the API unit bound to it',
                  not manager_a.alive(unit_a) and not manager_a.alive(api_unit_a))

        # AC4 (declared falsifier): a second run over the complete host changes nothing.
        binding_a = Path(CEN.binding_path(str(clone_a)))
        trees_a = (root_a, install_a, units_a, trust_a.parent, binding_a)
        with section(RR):
            head = journal(store_a)
            before = snapshot(*trees_a)
            keys_before = {p.name: p.read_bytes() for p in sorted(keys_a.iterdir())}
            code2, again = setup(root_a, clone_a, trust_a, install_a, units_a, manager_a)
            changed, added, removed = changes(before, snapshot(*trees_a))
            check(RR, 'a second run with the same arguments is accepted and reports every step already done [%s %s]'
                  % (again.get('outcome'), again.get('reason')),
                  code2 == 0 and again.get('outcome') == 'already_set_up'
                  and all(s.get('outcome') in ('already_done', 'deferred') for s in again.get('steps') or [])
                  and [s.get('step') for s in again.get('steps') or []][:13] == ['engine_upgrade'] + list(F.BASE_STEPS))
            check(RR, 'every file under the state root, install root, unit directory, host trust and workspace binding '
                  'is byte for byte the same [%s]' % (changed + added + removed)[:4], not (changed or added or removed))
            keys_after = {p.name: p.read_bytes() for p in sorted(keys_a.iterdir())}
            check(RR, 'no key was generated and none changed', keys_after == keys_before)
            after = journal(store_a)
            check(RR, 'the journal head is unchanged and it still holds one api edge enrollment [%d %d]'
                  % (len(head), len(after)), after == head
                  and len([r for r in after if 'api-edge' in str(r.get('command_id'))]) == 1)
            check(RR, 'the Serve status is unchanged and no `serve --bg` ran again [%s]' % ts.invocations(),
                  ts.target() == TARGET and not any(c[:1] in (['serve'], ['funnel']) and '--bg' in c for c in ts.invocations()))
            ts.clear()

        # AC4: a run whose arguments differ from what is laid down is refused by name, writing nothing.
        with section(AR):
            other_clone = clone('clone-other')
            variants = (('owner', {'--owner': 'someone'}), ('owner_key', {'--owner-key': str(other_key)}),
                        ('workspace', {'--workspace': str(other_clone)}), ('chat', {'--chat': str(chat + 1)}),
                        ('token_file', {'--token-file': str(other_token)}))
            for name, replace in variants:
                before = snapshot(base)
                got, shown = setup(root_a, clone_a, trust_a, install_a, units_a, manager_a, **replace)
                changed, added, removed = changes(before, snapshot(base))
                check(AR, 'another %s: refused as invalid_input:state_root:holds_%s, writing nothing [%s %s]'
                      % (name, name, shown.get('reason'), (changed + added + removed)[:3]),
                      got == 1 and shown.get('reason') == 'invalid_input:state_root:holds_' + name
                      and not (changed or added or removed))
            for name, place in (('host_trust', dict(trust=base / 'xdg-other' / 'veldo' / 'host_trust.json')),
                                ('install_root', dict(install=base / 'install-other')),
                                ('unit_dir', dict(units=base / 'units-other'))):
                before = snapshot(base)
                got, shown = setup(root_a, clone_a, place.get('trust', trust_a), place.get('install', install_a),
                                   place.get('units', units_a), manager_a)
                changed, added, removed = changes(before, snapshot(base))
                check(AR, 'another %s: refused as invalid_input:state_root:holds_%s, writing nothing [%s %s]'
                      % (name, name, shown.get('reason'), (changed + added + removed)[:3]),
                      got == 1 and shown.get('reason') == 'invalid_input:state_root:holds_' + name
                      and not (changed or added or removed))
            kept = profile['concurrency']
            profile['concurrency'] = 2
            before = snapshot(base)
            try:
                got, shown = setup(root_a, clone_a, trust_a, install_a, units_a, manager_a)
            finally:
                profile['concurrency'] = kept
            changed, added, removed = changes(before, snapshot(base))
            check(AR, 'another profile: refused as invalid_input:state_root:holds_profile, writing nothing [%s]'
                  % shown.get('reason'), got == 1 and shown.get('reason') == 'invalid_input:state_root:holds_profile'
                  and not (changed or added or removed))
            check(AR, 'every argument was judged before Tailscale was read [%s]' % ts.invocations(), ts.invocations() == [])

        # AC4: an existing file the run would write differently is refused by name and never overwritten.
        with section(DF):
            for path in (home_a / 'config' / 'api-process.json', units_a / api_unit_a, host_a / 'signer.json'):
                original = path.read_bytes()
                os.chmod(str(path), 0o600)
                path.write_bytes(original.replace(b'127.0.0.1', b'127.0.0.2') if b'127.0.0.1' in original
                                 else original + b'\n# changed\n')
                os.chmod(str(path), 0o644 if path.suffix == '.service' else 0o600)
                planted = path.read_bytes()
                before = snapshot(base)
                got, shown = setup(root_a, clone_a, trust_a, install_a, units_a, manager_a)
                changed, added, removed = changes(before, snapshot(base))
                check(DF, '%s differs: refused as invalid_input:state_root:differs:<its path>, left as it is, nothing '
                      'written [%s %s]' % (path.name, shown.get('reason'), (changed + added + removed)[:3]),
                      got == 1 and shown.get('reason') == 'invalid_input:state_root:differs:' + str(path)
                      and path.read_bytes() == planted and not (changed or added or removed))
                path.write_bytes(original)
                os.chmod(str(path), 0o644 if path.suffix == '.service' else 0o600)
            ts.clear()

        # AC1: with the service running, a store write the service takes no command for is refused by name.
        with section(RS):
            ids_a = {k: laid_a['authority_ids'][k] for k in ('domain_uuid', 'repository_uuid', 'store_uuid')}
            conn = S.open_store(str(store_a))
            try:
                CM.attach(S)
                K.attach(S)
                journal_signer = IN.journal_signer({'principal': 'authority', 'key': str(keys_a / 'journal')})
                writer = E.Enrollment(S, conn, ids_a, journal_signer[0], journal_signer[1])
                now = CM.authority_state(S, conn)
                command = {'command_id': 'v171-retire-telegram', 'operation': E.RETIRE, 'target': E.target('telegram_chat'),
                           'parameters': {'channel': 'telegram_chat', 'edge_key_id': E.edge_key_id('telegram_chat')},
                           'artifact_digests': [], 'expected_versions': {}}
                env = dict(ids_a, schema=AC.ENVELOPE_SCHEMA, command_id=command['command_id'], principal=owner,
                           request_revision=1, nonce='nonce-v171-retire', expires_at=time.time() + 600,
                           membership_version=now['membership_version'], delegation_version=now['delegation_version'],
                           command_digest=AC.canonical_command_digest(command))
                retired = writer.admit(env, command, sign_with(owner_key, AC.canonical_envelope_bytes(env)))
            finally:
                conn.close()
            CS.start(unit_a, manager_a)
            before = snapshot(root_a / 'host', root_a / 'keys', root_a / 'edge', install_a / home_a.name / 'config',
                              install_a / home_a.name / 'bin', units_a, trust_a.parent, binding_a)
            head = journal(store_a)
            capturing[0] = True
            try:
                got, shown = setup(root_a, clone_a, trust_a, install_a, units_a, manager_a)
            finally:
                capturing[0] = False
            changed, added, removed = changes(before, snapshot(root_a / 'host', root_a / 'keys', root_a / 'edge',
                                                               install_a / home_a.name / 'config', install_a / home_a.name / 'bin',
                                                               units_a, trust_a.parent, binding_a))
            check(RS, 'with the Telegram edge retired and the service running, the edge enrollment setup would write is '
                  'refused as invalid_input:state_root:service_running:edge_enrollment, writing nothing [%s %s %s]'
                  % (retired.get('outcome'), shown.get('reason'), (changed + added + removed)[:3]),
                  retired.get('outcome') == 'accepted' and manager_a.alive(unit_a) and got == 1
                  and shown.get('reason') == 'invalid_input:state_root:service_running:edge_enrollment'
                  and not (changed or added or removed) and journal(store_a) == head)
            CS.stop(unit_a, manager_a)
            connects.clear()
            ts.clear()

        # The host VELDO-0139 laid down before this change, with its service running.
        clone_b = clone('clone-b')
        root_b = fresh_root('state-b')
        trust_b = base / 'xdg-b' / 'veldo' / 'host_trust.json'
        install_b, units_b = base / 'install-b', base / 'units-b'
        manager_b = Manager(units_b)
        managers.append(manager_b)
        # The whole engine of that commit, never its setup module alone over the current engine: the host holds
        # the older engine, which the re-run's upgrade (VELDO-0189) replaces before its API steps.
        shipped = _git_process.run(['git', '-C', str(ROOT), 'archive', '--format=tar', BEFORE, '.veldo'],
                                   capture_output=True)
        F0 = None
        older = base / ('engine-' + BEFORE)
        older.mkdir()
        if shipped.returncode == 0 and shipped.stdout:
            import tarfile
            with tarfile.open(fileobj=io.BytesIO(shipped.stdout)) as archive:
                archive.extractall(str(older), filter='data')
            F0 = load('v171_setup_before', older / '.veldo' / 'control_factory_setup.py')
        code, laid = setup(root_b, clone_b, trust_b, install_b, units_b, manager_b, module=F0) if F0 else (None, {})
        if code != 0 or laid.get('outcome') != 'set_up':
            for name in (RS, OB, SR):
                check(name, 'the setup of %s laid a host down [%s]' % (BEFORE, {k: laid.get(k) for k in ('outcome', 'reason')}),
                      False)
            raise StopIteration
        unit_b, home_b = laid['unit'], Path(laid['home'])
        store_b, host_b, keys_b = root_b / 'authority' / 'control.sqlite3', root_b / 'host', root_b / 'keys'
        api_unit_b = 'veldo-api-' + unit_b[len('veldo-authority-'):]
        binding_b = Path(CEN.binding_path(str(clone_b)))
        CS.start(unit_b, manager_b)
        ts.set('ready')
        ts.clear()
        # The store and the service's own state directory are the running service's to write; every other file
        # under these trees is setup's.
        own = (str(root_b / 'authority'), str(home_b / 'state'))

        def trees_b():
            return {k: v for k, v in snapshot(root_b, install_b, units_b, trust_b.parent, binding_b).items()
                    if not k.startswith(own)}
        before, head = trees_b(), journal(store_b)
        before_config = json.loads((home_b / 'config' / 'service.json').read_text())
        receivers_before = {path: json.loads(Path(path).read_text())
                            for path in sorted(((before_config.get('receiver') or {}).get('configs') or {}).values())}
        calls_before = len(manager_b.calls)
        capturing[0] = True
        try:
            code, report_b = setup(root_b, clone_b, trust_b, install_b, units_b, manager_b)
        finally:
            capturing[0] = False
        store_connects = list(connects)
        after = trees_b()
        calls_b = manager_b.calls[calls_before:]
        steps_b = {s.get('step'): s for s in report_b.get('steps') or []}

        # AC1: with the service running, the enrollment went to the service; setup opened no store for writing.
        with section(RS):
            check(RS, 'the run over the running host is accepted [%s %s]' % (report_b.get('outcome'), report_b.get('reason')),
                  code == 0 and report_b.get('outcome') == 'set_up' and manager_b.alive(unit_b))
            check(RS, 'the api edge enrollment went through the running service [%s]' % steps_b.get('api_edge_enrollment'),
                  steps_b.get('api_edge_enrollment') == {'step': 'api_edge_enrollment', 'outcome': 'done', 'through_service': True}
                  and (report_b.get('api') or {}).get('store_write_through_service') is True)
            check(RS, 'setup opened no store connection for writing: every one it opened was read-only [%s]'
                  % [c.rsplit('/', 1)[-1] for c in store_connects],
                  store_connects and all(c.startswith('file:') and c.endswith('?mode=ro') for c in store_connects))
            observed = [json.loads(line) for line in (home_b / 'state' / 'observations.jsonl').read_text().splitlines()]
            accepted = [o for o in observed if o.get('operation') == 'enroll_channel_edge' and o.get('outcome') == 'accepted']
            new = journal(store_b)[len(head):]
            check(RS, 'the journal shows the service committed the enrollment the service accepted [%s %s]'
                  % ([o.get('command_id') for o in accepted], [r.get('command_id') for r in new]),
                  len(accepted) == 1 and [r.get('command_id') for r in new] == [accepted[0].get('command_id')]
                  and journal(store_b)[:len(head)] == head)
            state = state_of(store_b)
            record = E.edge_record(state, E.edge_key_id('api')) or {}
            check(RS, 'the enrolled api edge is the owner\'s enrollment of the key setup generated',
                  record.get('enrolled_by') == owner and record.get('public_key') == derived(keys_b / E.edge_key_id('api')))
            check(RS, 'setup republished the key projection from the committed store',
                  (host_b / 'allowed_signers').read_text() == K.projection(state))

        # AC4: over the host VELDO-0139 laid down with the engine of 7fefdb9a, only VELDO-0189's upgrade and the API
        # steps wrote.
        with section(OB):
            changed, added, removed = changes(before, after)
            config_b, bin_b = home_b / 'config', str(home_b / 'bin')
            outside = [p for p in changed if not p.startswith(bin_b + '/')]
            receivers = sorted(p for p in outside if os.path.basename(p).startswith('receiver-'))
            check(OB, 'the earlier files that changed outside the installed engine are only the service configuration, the '
                  'key projection and the receiver configuration the upgrade adds a key to [%s]' % outside,
                  sorted(set(outside) - set(receivers)) == sorted([str(config_b / 'service.json'), str(host_b / 'allowed_signers')])
                  and receivers == sorted(receivers_before))
            gained = {}
            for path, held in receivers_before.items():
                now_held = json.loads(Path(path).read_text())
                gained[os.path.basename(path)] = sorted(set(now_held) - set(held))
                check(OB, 'the receiver configuration %s kept every value it held and only gained keys [%s]'
                      % (os.path.basename(path), gained[os.path.basename(path)]),
                      all(now_held.get(k) == v for k, v in held.items()) and gained[os.path.basename(path)])
            now_config = json.loads((config_b / 'service.json').read_text())
            record_a = json.loads((install_a / home_a.name / 'config' / 'service.json').read_text())
            engine_keys = ('closure', 'runtime_assets', 'template')
            check(OB, 'the service configuration kept every other value, names the current engine, gained the keys it '
                  'lacked and names the API configuration in the api_service key it held as null [%s]'
                  % sorted(set(now_config) - set(before_config)),
                  'api_service' in before_config and before_config['api_service'] is None
                  and {k: v for k, v in now_config.items() if k in before_config and k not in engine_keys + ('api_service',)}
                  == {k: v for k, v in before_config.items() if k not in engine_keys + ('api_service',)}
                  and all(now_config.get(k) == record_a.get(k) for k in engine_keys)
                  and all(now_config.get(k) == record_a.get(k) for k in set(now_config) - set(before_config))
                  and now_config.get('api_service') == str(config_b / 'api-service.json'))
            expected = sorted(str(p) for p in (host_b / 'api-service.json', keys_b / E.edge_key_id('api'),
                                               keys_b / (E.edge_key_id('api') + '.pub'), root_b / 'edge' / 'api-auth',
                                               root_b / 'edge' / 'api-auth.pub', config_b / 'api-service.json',
                                               config_b / 'api-process.json', units_b / api_unit_b,
                                               units_b / (unit_b + '.wants'), units_b / (unit_b + '.wants') / api_unit_b,
                                               host_b / 'engines.json', root_b / 'engines', root_b / 'engines/claude_code',
                                               root_b / 'engines/claude_code' / engines186['version']))
            added_outside = [p for p in added if not p.startswith(bin_b + '/')]
            check(OB, 'the files it added outside the installed engine are exactly the API steps\' [%s]'
                  % sorted(set(added_outside) ^ set(expected))[:4],
                  added_outside == expected and not [p for p in removed if not p.startswith(bin_b + '/')])

            def engine_of(directory):
                return {str(p.relative_to(directory)): (oct(stat.S_IMODE(p.lstat().st_mode)),
                        hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else 'directory')
                        for p in sorted(Path(directory).rglob('*'))}
            check(OB, 'the installed engine is now the current one, name for name, byte for byte and mode for mode',
                  engine_of(bin_b) == engine_of(install_a / home_a.name / 'bin')
                  and oct(stat.S_IMODE(os.lstat(bin_b).st_mode)) == '0o500')
            upgrade_b = steps_b.get('engine_upgrade') or {}
            check(OB, 'the upgrade ran first and restarted the running service once [%s %s]'
                  % (upgrade_b.get('outcome'), upgrade_b.get('restart')),
                  (report_b.get('steps') or [{}])[0].get('step') == 'engine_upgrade'
                  and upgrade_b.get('outcome') == 'done' and upgrade_b.get('restart') == 'restarted')
            check(OB, 'every earlier step is reported already done and every API step done [%s]'
                  % {k: v.get('outcome') for k, v in steps_b.items()},
                  all(steps_b.get(s, {}).get('outcome') == 'already_done' for s in F.BASE_STEPS)
                  and all(steps_b.get(s, {}).get('outcome') == 'done' for s in
                          ('api_edge_key', 'api_edge_enrollment', 'api_service_configuration', 'api_service_install',
                           'api_process_configuration', 'api_unit', 'tailscale_serve')))

        # AC2: this run added the API configuration, so it restarts nothing for it and names the one restart
        # command (the one restart is the engine upgrade's, VELDO-0189, before the API steps); once the
        # installation names it and the authority runs, setup starts the API unit itself.
        with section(SR):
            check(SR, 'setup started and stopped nothing and restarted only the authority, once, for the engine '
                  'upgrade [%s]' % [c for c in calls_b if c[0] in ('start', 'stop', 'restart')],
                  [c for c in calls_b if c[0] in ('start', 'stop', 'restart')] == [['restart', unit_b]]
                  and steps_b.get('api_start', {}).get('outcome') == 'deferred' and not manager_b.alive(api_unit_b))
            check(SR, 'it names the one restart command [%s]' % report_b.get('next'),
                  'systemctl --user restart %s' % unit_b in str(report_b.get('next')))
            CS.stop(unit_b, manager_b)
            CS.start(unit_b, manager_b)
            up = listening(manager_b.pid(api_unit_b) or 0)
            check(SR, 'after that restart the API unit runs with the authority service [%s]' % up,
                  manager_b.alive(unit_b) and up == [('127.0.0.1', port)])
            manager_b.stop(api_unit_b)
            calls_before = len(manager_b.calls)
            code, third = setup(root_b, clone_b, trust_b, install_b, units_b, manager_b)
            calls = manager_b.calls[calls_before:]
            steps = {s.get('step'): s.get('outcome') for s in third.get('steps') or []}
            up = listening(manager_b.pid(api_unit_b) or 0)
            check(SR, 'with the installation naming the API and the authority running, setup starts the API unit '
                  'itself [%s %s %s]' % (third.get('reason'), steps.get('api_start'), [c[0] for c in calls]),
                  code == 0 and steps.get('api_start') == 'done' and ['start', api_unit_b] in calls
                  and not any(c[0] in ('stop', 'restart') or c == ['start', unit_b] for c in calls)
                  and up == [('127.0.0.1', port)])
            CS.stop(unit_b, manager_b)
    except StopIteration:
        pass
    finally:
        close_runtime()
        sys.dont_write_bytecode = prior_bytecode
        os.environ['PATH'] = prior_path186
        socket.create_connection, socket.getaddrinfo = real_connect, real_resolve
        capturing[0] = False
        for manager in managers:
            with contextlib.suppress(Exception):
                manager.close()
        stop_bot_api()
        if ts is not None:
            ts.close()
        for directory, _dirs, _files in os.walk(str(base)):
            with contextlib.suppress(OSError):
                os.chmod(directory, 0o700)
        shutil.rmtree(str(base), ignore_errors=True)

    if profiler is not None:
        profiler.disable()
        profiler.dump_stats(os.environ['VELDO_SUITE_PROFILE'])
    if timing_path:
        Path(timing_path).write_text(json.dumps(dict(rows=timings, seconds=time.monotonic() - started), indent=2) + '\n')

    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        if not ok:
            for label, one in observed:
                if not one:
                    print('  VELDO-0171 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0171 %s detail: no check ran' % name)
        expect('VELDO-0171 ' + name, ok)
    print('VELDO-0171 suite seconds: %.3f' % (time.monotonic() - started))


_v171_suite()
