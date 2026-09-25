"""VELDO-0138: the installed authority service runs the Telegram ingress and applies the owner's
activation commands.

Run: python3 scripts/selftest.py --suite 71_veldo_0138_channel_service

Only shared ROOT and expect are consumed. One temporary tree holds the .veldo copy the suite loads and
the installer copies its fixed executable from, so a registered mutation of a production file (the
service, its channel, the activation or ingress module, the scaffolder) reaches the installed instance.
Real: a signed SQLite store with membership, the owner's chat enrollment and the VELDO-0067 edge key
(scripts/suites/support/v73_authority.py), an enrolled Git clone and this host's trust file, the
installer (control_service.install) with the channel ingress configuration, the unit it renders, and
the service process that unit's ExecStart runs, started, stopped and restarted through the service's
own start and stop lifecycle functions. The user manager is a stand-in of this run's own that runs the
installed unit's ExecStart as a Type=notify service (READY=1 on its own notify socket, SIGTERM on
stop), so nothing is installed into or started by the owner's real systemd user manager; only the
installer's host qualification reads it. The owner's commands go through bin/veldo channel, a separate
process signing with his enrolled key; other principals' commands are signed and sent through the same
client. Every Bot API exchange goes to a loopback stand-in (scripts/suites/support/v73_authority.py);
a socket guard refuses and counts every connection beyond 127.0.0.1 in this process, and the same guard
is armed in the service process and every process it starts (a sitecustomize on the manager stand-in's
PYTHONPATH), so no row and no mutant can reach Telegram. The store is read through connections of this
suite's own process, never the service's. No real token file is read; no private key byte, signature or
token is printed.
"""


def _v138_suite():
    import contextlib
    import importlib.util
    import inspect as pyinspect
    import json
    import os
    from pathlib import Path
    import select
    import shlex
    import shutil
    import signal
    import socket
    import sqlite3
    import subprocess
    import sys
    import tempfile
    import time
    import urllib.request

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_service_channel.py': ROOT / ".veldo" / "control_service_channel.py",
        'control_channel_activation.py': ROOT / ".veldo" / "control_channel_activation.py",
        'control_channel_ingress.py': ROOT / ".veldo" / "control_channel_ingress.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    ROWS = ('install/assets', 'served/inert', 'served/settlement', 'qualification/recorded-by-service',
            'command/owner', 'command/owner-only', 'command/stop-live', 'command/stop-keeps-pending',
            'restart/active-stays-active', 'restart/stopped-stays-stopped', 'restart/never-activated-stays-inert',
            'qualification/transport-failure-named')
    IA, SI, SS, QR, CO, OO, SL, SP, RA, RS, RN, TF = ROWS
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
    budget = started + 80

    def wait(predicate, seconds=20):
        """Poll `predicate` until it holds, `seconds` pass or the suite's budget is spent."""
        until = min(time.monotonic() + seconds, budget)
        while True:
            value = predicate()
            if value or time.monotonic() >= until:
                return value
            time.sleep(0.15)

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    base = Path(tempfile.mkdtemp(prefix='b138-', dir=fast))
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
    CS = load('v138_service', mods / 'control_service.py')
    CC = load('v138_client', mods / 'control_client.py')
    CE = load('v138_enrollment', mods / 'control_enrollment.py')
    EL = load('v138_eligibility', mods / 'control_eligibility.py')
    ST = load('v138_settlement', mods / 'control_request_settlement.py')
    EV = load('v138_attribution', mods / 'control_channel_attribution.py')
    git = load('v138_git', mods / 'git_process.py')
    H = load('v138_support', ROOT / 'scripts' / 'suites' / 'support' / 'v73_authority.py')

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
        '_log, _armed = os.environ.get("VELDO_V138_GUARD_LOG"), os.environ.get("VELDO_V138_GUARD_ARMED")\n'
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
        """UMask=0077, and the service dies with this suite's process (PR_SET_PDEATHSIG), so a killed
        run can never leave an authority process behind."""
        os.umask(0o077)
        with contextlib.suppress(Exception):
            import ctypes
            ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGTERM)

    class Manager:
        """A stand-in for the owner's systemd user manager, answering the systemctl calls the service's
        lifecycle functions make: start runs the installed unit's ExecStart as a Type=notify service and
        waits for READY=1, stop sends SIGTERM and waits, show reports the unit's state."""

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
                       'PYTHONPATH': str(guard_dir), 'VELDO_V138_GUARD_LOG': str(guard_log),
                       'VELDO_V138_GUARD_ARMED': str(guard_armed), 'NOTIFY_SOCKET': str(notify)}
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

    owner_user = {'id': 5580138, 'is_bot': False, 'first_name': 'Owner'}
    deputy_chat = 5580139
    bot_user = {'id': 8000000138, 'is_bot': True, 'first_name': 'Veldo', 'username': 'veldo_service_bot'}
    url, api, stop_api = H.stand_in({'bot138': bot_user})
    api['chats'][owner_user['id']] = {'id': owner_user['id'], 'type': 'private', 'first_name': 'Owner'}
    manager = Manager(base / 'units')
    A = None
    ing = None
    unit, home = None, None
    try:
        A = H.build(base / 'a', mods, owner_user['id'], url, 'bot138')
        ids = A.ids
        # An agent_run principal, beside the owner, the steward (another member holding project_owner)
        # and the service principals the support authority enrolls.
        runner_key = A.keyfile['owner'].with_name('runner')
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v138-runner', '-f', str(runner_key)],
                       check=True, capture_output=True, timeout=10, stdin=subprocess.DEVNULL)
        A.keyfile['runner'] = runner_key
        A.public['runner'] = ' '.join(runner_key.with_name('runner.pub').read_text().split()[:2])
        A.admin('steward', 'enroll_principal', {'principal': 'runner', 'principal_type': 'agent_run',
                                                'roles': ['project_owner'], 'public_key': A.public['runner'],
                                                'independence_group': 'runner', 'scope': ['project-a']}, enrollee='runner')
        # A second person holding project_owner (and no steward role), enrolled the same way, whose own
        # chat enrollment is written when a row needs it.
        deputy_key = A.keyfile['owner'].with_name('deputy')
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'v138-deputy', '-f', str(deputy_key)],
                       check=True, capture_output=True, timeout=10, stdin=subprocess.DEVNULL)
        A.keyfile['deputy'] = deputy_key
        A.public['deputy'] = ' '.join(deputy_key.with_name('deputy.pub').read_text().split()[:2])
        A.admin('steward', 'enroll_principal', {'principal': 'deputy', 'principal_type': 'person',
                                                'roles': ['project_owner'], 'public_key': A.public['deputy'],
                                                'independence_group': 'deputy', 'scope': ['project-a']}, enrollee='deputy')
        # The enrolled clone the owner's commands name, bound to the support authority's store.
        clone = base / 'clone'
        git.run(['git', 'init', '-q', str(clone)], check=True, capture_output=True)
        (clone / 'README').write_text('v138\n')
        git.run(['git', '-C', str(clone), 'add', 'README'], check=True, capture_output=True)
        git.run(['git', '-C', str(clone), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'v138'], check=True,
                capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        host_trust = A.host / 'host_trust.json'
        CE.enroll(str(clone), ids['domain_uuid'], ids['store_uuid'], str(A.db), 'v73-host', 1,
                  lambda data: A.sign_as('steward', data, EL.ENROLLMENT_NAMESPACE), 'steward', time.time(),
                  repository_uuid=ids['repository_uuid'])
        trust = EL.load_host_trust(str(host_trust))
        verify = trust.verifier('steward', str(clone))
        # The service's key directory holds the store's journal key, and the ingress configuration names it.
        keys = base / 'keys'
        keys.mkdir(mode=0o700)
        shutil.copyfile(A.keyfile['authority'], keys / 'journal')
        os.chmod(str(keys / 'journal'), 0o600)
        ingress_config = A.host / 'service-ingress.json'
        fd = os.open(str(ingress_config), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as handle:
            handle.write(json.dumps(dict(A.config, journal={'principal': 'authority', 'key': str(keys / 'journal')})))
        profile = {'kind': 'linux-systemd', 'slice': 'v138%s.slice' % os.urandom(3).hex(), 'lock': str(base / 'workers.lock'),
                   'concurrency': 1, 'runtime_seconds': 600, 'memory_bytes': 256 << 20, 'cpu_percent': 100,
                   'file_bytes': 64 << 20, 'tasks_max': 256, 'stop_grace_seconds': 1, 'kill_grace_seconds': 1}
        takes_channel = 'channel_ingress' in pyinspect.signature(CS.install).parameters

        def install(root, units, ingress=ingress_config):
            arguments = dict(host_trust=str(host_trust), key_directory=str(keys), install_root=str(root),
                             unit_dir=str(units), profile=profile, adapters={}, writable=[], runner=manager)
            if takes_channel:
                arguments['channel_ingress'] = str(ingress)
            return CS.install([str(clone)], **arguments)

        # AC1: the channel module travels with the service, and installation takes the ingress it runs.
        with section(IA):
            scaffold = load('v138_scaffold', mods / 'init_scaffold.py')
            for rel in ('.veldo/control_service_channel.py', '.veldo/control_service.py',
                        '.veldo/control_channel_activation.py', '.veldo/control_channel_ingress.py'):
                check(IA, rel + ' installed by the scaffold', rel in scaffold._FILES)
                check(IA, rel + ' not claimed as validator substrate', rel not in scaffold.REQUIRED_SUBSTRATE)
                engine = ROOT / 'engine' / rel
                check(IA, rel + ' engine copy identical', engine.is_file() and (ROOT / rel).is_file()
                      and engine.read_bytes() == (ROOT / rel).read_bytes())
            check(IA, 'bin/veldo engine copy identical', (ROOT / 'engine' / 'bin' / 'veldo').read_bytes()
                  == (ROOT / 'bin' / 'veldo').read_bytes())
            foreign = A.host / 'foreign-ingress.json'
            fd = os.open(str(foreign), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as handle:
                handle.write(json.dumps(dict(A.config, store_path=str(base / 'elsewhere' / 'control.sqlite3'),
                                             journal={'principal': 'authority', 'key': str(keys / 'journal')})))
            try:
                install(base / 'probe' / 'install', base / 'probe' / 'units', foreign)
                refused = None
            except Exception as exc:  # noqa: BLE001 - the refusal is the observation
                refused = getattr(exc, 'code', type(exc).__name__)
            left = sorted(str(p) for p in (base / 'probe').rglob('*')) if (base / 'probe').exists() else []
            check(IA, 'an ingress configuration of another store refuses installation by name, leaving nothing [%s]' % refused,
                  takes_channel and refused == 'invalid_input:channel_ingress:store' and left == [])
        report = install(base / 'install', base / 'units')
        unit, home = report['unit'], Path(report['home'])
        installed = home / 'bin'
        service_json = json.loads((home / 'config' / 'service.json').read_text())
        with section(IA):
            copied = home / 'config' / 'channel-ingress.json'
            check(IA, 'the fixed executable holds the channel, the ingress and the activation modules',
                  all((installed / n).is_file() for n in ('control_service_channel.py', 'control_channel_ingress.py',
                                                          'control_channel_activation.py')))
            check(IA, 'the ingress configuration is copied 0600 into the protected configuration and named by service.json',
                  copied.is_file() and oct(copied.stat().st_mode & 0o777) == '0o600'
                  and service_json.get('channel_ingress') == str(copied)
                  and copied.read_bytes() == ingress_config.read_bytes())
            check(IA, 'bin/veldo routes channel to the activation module\'s own command surface',
                  "_mod(\"veldo_cli_channel\", \".veldo/control_channel_activation.py\")" in (ROOT / 'bin' / 'veldo').read_text()
                  and callable(getattr(load('v138_act_root', ROOT / '.veldo' / 'control_channel_activation.py'), 'main', None)))

        # The suite's own organs for opening requests, loaded from the installed executable, so every
        # ownership declaration names the code the service runs. Nothing here presents or acquires.
        organs = installed if (installed / 'control_channel_ingress.py').is_file() else mods
        IN = load('v138_ingress', organs / 'control_channel_ingress.py')
        ing = IN.open_ingress(str(ingress_config))

        def open_request(alias):
            """Signed terms, the inbox request and its framing, never its presentation: the request id."""
            target = {'kind': 'backlog_item', 'ref': 'backlog:%s' % alias,
                      'digest': 'sha256:' + __import__('hashlib').sha256(alias.encode()).hexdigest()}
            body = dict(ids, operation='terms', terms=alias, principal='pm', command_id=A.next_id('terms'),
                        nonce=A.next_id('terms-nonce'), touchpoint='grooming', target=target, proposal=None,
                        required_roles=[], quorum=None)
            subject = ing.settlement.terms(A.signed_command('pm', body)).get('subject')
            ing.inbox.apply(A.signed_command('pm', dict(ids, operation='open', alias=alias, principal='pm',
                                                        command_id=A.next_id('c'), nonce=A.next_id('n'), assignment=dict(
                                                            kind='decision', owner='owner', scope=['project-a'],
                                                            deadline='2026-10-01T17:00:00Z', budget={'owner_minutes': 15},
                                                            brief='VELDO-0138: decide %s.' % alias,
                                                            choices=['accept', 'return_for_elaboration', 'reject'],
                                                            subject=subject))))
            rid = A.assignment_id(alias)
            ing.presenter.frame(A.signed_command('pm', dict(ids, operation='frame', alias=alias, principal='pm',
                                                            request_version=1, command_id=A.next_id('f'),
                                                            nonce=A.next_id('fn'),
                                                            risk_statement='Low: a request with no effect beyond its record.')))
            return rid

        def calls(method=None):
            return len(api['calls']) if method is None else api['calls'].count(method)

        def status():
            try:
                answer = CC.send(str(clone), {'operation': 'inspect', 'entity_ids': []}, CE, verify,
                                 lambda data: A.sign_as('owner', data), 'v73-host', timeout=30)
            except CC.RoutingRefused as exc:
                return {'refused': exc.reason}
            result = answer.get('result') or {}
            return dict(result.get('channel') or {}, _answer=bool(answer.get('accepted')))

        def channel_runs():
            return bool(status().get('available'))

        def passes(n):
            """Wait for `n` more channel passes of the running service; False when none run."""
            first = status().get('passes')
            if not isinstance(first, int):
                return False
            return bool(wait(lambda: (status().get('passes') or 0) >= first + n, 15))

        def veldo(action, who='owner', *extra):
            """The owner's command path: bin/veldo channel, a separate process signing with `who`'s key."""
            done = subprocess.run([sys.executable, '-B', str(ROOT / 'bin' / 'veldo'), 'channel', action, '--principal', who,
                                   '--key', str(A.keyfile[who]), '--workspace', str(clone), '--host-trust', str(host_trust)]
                                  + list(extra), capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL,
                                  env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            try:
                shown = json.loads(done.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                shown = {'unparsed': done.stdout[-200:], 'stderr': done.stderr[-300:]}
            return done.returncode, shown

        def signed_as(who, action='qualify', signature=None, **params):
            """One channel_activation_authorize command for the OWNER's edge, its envelope signed by `who`
            (or carrying `signature`), sent in a request `who` signs, as any client would."""
            values = {'channel': 'telegram_chat', 'action': action, 'owner': 'owner', 'origin': url,
                      'edge_key_id': 'edge-telegram'}
            if action == 'qualify':
                values['expires_at'] = time.time() + 900
            values.update(params)
            command = {'command_id': A.next_id('v138-act'), 'operation': 'channel_activation_authorize',
                       'target': 'channel:telegram_chat', 'parameters': values, 'artifact_digests': [], 'expected_versions': {}}
            envelope = A.envelope(command, who)
            sig = A.sign_as(who, A.AC.canonical_envelope_bytes(envelope)) if signature is None else signature
            try:
                answer = CC.send(str(clone), {'command': command, 'envelope': envelope, 'signature': sig}, CE, verify,
                                 lambda data: A.sign_as(who, data), 'v73-host', timeout=30)
            except CC.RoutingRefused as exc:
                return {'refused': exc.reason}
            return answer

        def record():
            row = A.conn.execute("SELECT version, data FROM entities WHERE id='channel_activation:telegram_chat'").fetchone()
            return None if row is None else dict(json.loads(row[1]), entity_version=row[0])

        def presentations():
            return A.conn.execute("SELECT count(*) FROM entities WHERE kind='channel_presentation'").fetchone()[0]

        def head():
            return A.conn.execute('SELECT COALESCE(MAX(seq), 0) FROM journal').fetchone()[0]

        def published(rid):
            receipt = ing.presenter.current(rid) or {}
            return receipt if receipt.get('outcome') == 'published' else None

        def settled(rid):
            return ing.settlement.settlement(rid, 1)

        def pending(rid):
            return any(e['id'] == rid and e.get('category') == 'pending' for e in ing.inbox.index()['entries'])

        def pid():
            return int(CS.status(unit, manager).get('MainPID') or 0)

        def restart():
            before = pid()
            CS.stop(unit, manager)
            after = CS.start(unit, manager)
            return before, pid(), after.get('ActiveState')

        def reply(rid, text):
            receipt = published(rid) or {}
            return H.deliver(api, 'bot138', owner_user, text, reply_to=(receipt.get('message_ids') or [None])[-1])

        def evidence(update):
            return A.conn.execute('SELECT data FROM entities WHERE id=?',
                                  (EV.evidence_id(bot_user['id'], update['update_id']),)).fetchone()

        began = CS.start(unit, manager)
        first_pid = pid()

        # AC1 and AC3: started with no activation record, the running service's ingress is inert.
        with section(SI, RN):
            now = status()
            check(SI, 'the installed service started through its lifecycle and serves [%s]' % began.get('ActiveState'),
                  began.get('ActiveState') == 'active' and first_pid > 0 and now.get('_answer') is True)
            check(SI, 'the running service runs the ingress: its channel is available with no record [%s]'
                  % {k: now.get(k) for k in ('available', 'refusal', 'record')},
                  now.get('available') is True and now.get('record') is None and now.get('origin') == url)
            rid1 = open_request('S1')
            mark = head()
            ran = passes(3)
            after = status()
            check(SI, 'with no record each pass is refused as not_activated [%s]' % after.get('last_pass'),
                  ran and (after.get('last_pass') or {}).get('reason') == 'not_activated')
            check(SI, 'inert: nothing sent, nothing acquired, the platform never asked [%s]' % api['calls'],
                  ran and calls() == 0)
            check(SI, 'inert: the channel writes nothing, no presentation and no journal record [%d, %d -> %d]'
                  % (presentations(), mark, head()), ran and presentations() == 0 and head() == mark and pending(rid1))
        with section(RN):
            before, after_pid, state = restart()
            ran = passes(3)
            now = status()
            check(RN, 'restarted with no record: a new service process, still inert [%s -> %s]' % (before, after_pid),
                  state == 'active' and after_pid not in (0, before) and now.get('available') is True
                  and now.get('record') is None and (now.get('last_pass') or {}).get('reason') == 'not_activated')
            check(RN, 'nothing sent or acquired, the request still pending with no presentation',
                  ran and calls() == 0 and presentations() == 0 and pending(rid1))

        # AC2: no principal but the owner qualifies, activates or stops the edge; each is refused by name.
        with section(OO):
            cases = {
                'another member holding project_owner': (signed_as('steward'), 'missing_authority:channel:not_owner'),
                'an agent_run principal': (signed_as('runner'), 'missing_authority:channel:not_a_person'),
                'a service principal': (signed_as('pm'), 'missing_authority:channel:not_a_person'),
                'the owner\'s command with no envelope signature': (signed_as('owner', signature=''),
                                                                    'missing_authority:channel:signature_invalid'),
                'the owner\'s command signed by the steward': (signed_as('owner', signature=A.sign_as(
                    'steward', b'another message')), 'missing_authority:channel:signature_invalid'),
                'a stop signed by another member': (signed_as('steward', 'stop'), 'missing_authority:channel:not_owner'),
                'an activation signed by another member': (signed_as('steward', 'activate', qualification_id='x',
                                                                     qualification_digest='sha256:x'),
                                                           'missing_authority:channel:not_owner'),
            }
            for label, (answer, expected) in cases.items():
                got = (answer.get('result') or {}).get('reason')
                check(OO, '%s is refused by name (%s)' % (label, got), answer.get('accepted') is True and got == expected)
            unsigned = {}
            try:
                unsigned = CC.send(str(clone), {'command': {'operation': 'channel_activation_authorize'}}, CE, verify,
                                   lambda data: 'unsigned', 'v73-host', timeout=30)
            except CC.RoutingRefused as exc:
                unsigned = {'refused': exc.reason}
            check(OO, 'an unsigned request is refused before the channel sees it (%s)' % unsigned.get('reason'),
                  unsigned.get('accepted') is False and unsigned.get('reason') == 'command_signature_invalid')
            rc, shown = veldo('qualify', 'steward')
            check(OO, 'bin/veldo channel qualify signed by another member is refused (%s)' % shown.get('reason'),
                  rc == 1 and shown.get('outcome') == 'refused' and 'channel:' in str(shown.get('reason')))
            check(OO, 'every refusal left the activation record absent and nothing sent',
                  record() is None and calls() == 0 and status().get('record') is None)

        # AC2: the owner qualifies through bin/veldo; the running service applies it and presents.
        with section(CO, SS, QR):
            rc, shown = veldo('qualify', 'owner', '--minutes', '15')
            now = status()
            check(CO, 'bin/veldo channel qualify, signed by the owner\'s enrolled key, is applied by the running service [%s]'
                  % shown, rc == 0 and shown.get('outcome') == 'accepted' and shown.get('state') == 'qualifying'
                  and (now.get('record') or {}).get('state') == 'qualifying'
                  and (now.get('record') or {}).get('authorized_by') == 'owner' and pid() == after_pid)
            shown1 = wait(lambda: published(rid1), 15) if channel_runs() else None
            check(SS, 'the running service presents the pending request to the owner\'s enrolled chat',
                  bool(shown1) and shown1.get('chat_id') == owner_user['id'] and calls('sendMessage') == 1)
            answer1 = reply(rid1, 'accept: settled through the running service')
            done1 = wait(lambda: settled(rid1), 20) if shown1 else None
            source = ((done1 or {}).get('assertion') or {}).get('attribution') or {}
            check(SS, 'the owner\'s reply settles through the running service, read from the store in this process',
                  bool(done1) and done1.get('choice') == 'accept' and done1.get('originating_channel') == 'telegram_chat'
                  and source.get('platform_message_id') == answer1['message']['message_id'] and pid() == after_pid)
            q = wait(lambda: status().get('qualification'), 20) if done1 else None
            q = q or {}
            stored = A.conn.execute('SELECT data FROM entities WHERE id=?', (q.get('id') or '',)).fetchone()
            data = json.loads(stored[0]) if stored else {}
            ACT = load('v138_act_digest', mods / 'control_channel_activation.py')
            check(QR, 'the service recorded the run\'s qualification in the store, its digest the one it reports [%s]'
                  % {k: q.get(k) for k in ('id', 'platform', 'unauthorized_provenance')},
                  bool(data) and ACT.digest(data) == q.get('digest') and q.get('request_id') == rid1
                  and ACT.qualification_problems(data, url) == [])
            check(QR, 'it binds the service gate\'s own exchanges and the owner\'s acquired answer',
                  bool(data) and len(data.get('exchanges') or []) >= 3
                  and all(x.get('origin') == url for x in data.get('exchanges') or [])
                  and (data.get('owner_answer') or {}).get('update_id') == answer1['update_id'])
            check(QR, 'the unauthorized leg is the probe bot\'s stand-in update, marked stand_in, never moving the bot\'s cursor',
                  (data.get('unauthorized') or {}).get('provenance') == 'stand_in'
                  and (data.get('unauthorized') or {}).get('reason') == 'unknown_sender'
                  and ((ing.acquirer._entity(EV.cursor_id(bot_user['id'])) or {}).get('data') or {}).get('next_offset')
                  == answer1['update_id'] + 1)
            rc, shown = veldo('activate', 'owner')
            now = status()
            check(CO, 'bin/veldo channel activate signs over the recorded qualification and the service applies it [%s]'
                  % shown, rc == 0 and shown.get('state') == 'active' and (shown.get('qualification') or {}).get('digest')
                  == q.get('digest') and bool(q.get('digest')) and (now.get('record') or {}).get('state') == 'active'
                  and (now.get('record') or {}).get('qualification_digest') == q.get('digest') and pid() == after_pid)

        # AC1: with the edge active, a new request is presented and settles through the running service.
        with section(SS):
            rid2 = open_request('S2')
            shown2 = wait(lambda: published(rid2), 15) if channel_runs() else None
            answer2 = reply(rid2, 'reject: the active edge carried this')
            done2 = wait(lambda: settled(rid2), 20) if shown2 else None
            check(SS, 'the active edge presents a new request and the owner\'s answer settles it',
                  bool(done2) and done2.get('choice') == 'reject'
                  and ((done2.get('assertion') or {}).get('attribution') or {}).get('platform_message_id')
                  == answer2['message']['message_id'])

        # AC3: a restart keeps an active edge active.
        with section(RA):
            before, active_pid, state = restart()
            now = status()
            check(RA, 'restarted with the edge active: a new service process, the record still active [%s -> %s]'
                  % (before, active_pid), state == 'active' and active_pid not in (0, before)
                  and (now.get('record') or {}).get('state') == 'active')
            rid3 = open_request('S3')
            shown3 = wait(lambda: published(rid3), 15) if channel_runs() else None
            answer3 = reply(rid3, 'accept: after the restart')
            done3 = wait(lambda: settled(rid3), 20) if shown3 else None
            check(RA, 'after the restart it presents, acquires and settles', bool(done3) and done3.get('choice') == 'accept')

        # AC2: the owner's stop takes effect in the running service without a restart; pending stays pending.
        with section(SL, SP, OO):
            rid4 = open_request('S4')
            shown4 = wait(lambda: published(rid4), 15) if channel_runs() else None
            # AC2 over an existing record: another project_owner member who names himself as owner.
            held, sent = record(), calls()
            usurp = signed_as('steward', 'stop', owner='steward')
            got = (usurp.get('result') or {}).get('reason')
            check(OO, 'over the active record, a stop signed by the steward naming himself as owner is refused by name '
                  '(%s)' % got, usurp.get('accepted') is True and got == 'missing_authority:channel:not_owner')
            check(OO, 'that refusal left the active record unchanged [%s]' % ((record() or {}).get('authorized_by'),),
                  held is not None and held.get('state') == 'active' and record() == held
                  and (status().get('record') or {}).get('state') == 'active')
            rc, shown = veldo('stop', 'owner')
            at_stop = (calls(), pid())
            check(SL, 'bin/veldo channel stop, signed by the owner, is applied by the running service [%s]' % shown,
                  rc == 0 and shown.get('state') == 'stopped' and (record() or {}).get('state') == 'stopped' and bool(shown4))
            rid5 = open_request('S5')
            late = reply(rid4, 'accept: sent while the edge is stopped')
            ran = passes(3)
            now = status()
            check(SL, 'the same process stops at once: nothing sent or acquired, each pass refused as edge_stopped [%s]'
                  % (now.get('last_pass'),), ran and calls() == at_stop[0] and pid() == at_stop[1]
                  and (now.get('last_pass') or {}).get('reason') == 'edge_stopped' and published(rid5) is None
                  and evidence(late) is None)
            check(SP, 'the pending requests stay pending and unsettled, and the platform keeps the reply',
                  pending(rid4) and pending(rid5) and settled(rid4) is None
                  and any(u['update_id'] == late['update_id'] for u in api['bots']['bot138']['updates']))
            # AC2 after the owner's stop: a second project_owner person, with his own chat enrollment,
            # re-qualifies the edge onto his own chat by naming himself as owner.
            A.fixture('channel-enrollment:telegram_chat:deputy', 'channel_enrollment',
                      dict(schema='veldo.channel_enrollment/v1', channel='telegram_chat', principal='deputy',
                           chat_id=deputy_chat, revoked_at=None))
            api['chats'][deputy_chat] = {'id': deputy_chat, 'type': 'private', 'first_name': 'Deputy'}
            held, sent = record(), calls()
            usurp = signed_as('deputy', 'qualify', owner='deputy')
            got = (usurp.get('result') or {}).get('reason')
            check(OO, 'over the stopped record, a qualify signed by another project_owner person naming himself and '
                  'his own enrolled chat is refused by name (%s)' % got,
                  usurp.get('accepted') is True and got == 'missing_authority:channel:not_owner')
            ran = passes(2)
            check(OO, 'that refusal left the stopped record unchanged and nothing was sent [%s]'
                  % ((record() or {}).get('owner'),), held is not None and held.get('state') == 'stopped'
                  and record() == held and ran and calls() == sent
                  and (status().get('last_pass') or {}).get('reason') == 'edge_stopped')
            usurp = signed_as('deputy', 'stop', owner='deputy')
            got = (usurp.get('result') or {}).get('reason')
            check(OO, 'and his stop naming himself is refused by name too (%s), the record unchanged' % got,
                  usurp.get('accepted') is True and got == 'missing_authority:channel:not_owner' and record() == held)

        # AC3: a restart after the owner's stop keeps the edge stopped.
        with section(RS, SP):
            before, stopped_pid, state = restart()
            ran = passes(3)
            now = status()
            check(RS, 'restarted after the stop: a new process, the record still stopped [%s -> %s]' % (before, stopped_pid),
                  state == 'active' and stopped_pid not in (0, before) and (now.get('record') or {}).get('state') == 'stopped')
            check(RS, 'the stopped edge stays stopped: nothing sent or acquired, passes refused as edge_stopped',
                  ran and calls() == at_stop[0] and (now.get('last_pass') or {}).get('reason') == 'edge_stopped'
                  and evidence(late) is None and published(rid5) is None)
            check(RS, 'pending requests are kept across the restart', pending(rid4) and pending(rid5) and settled(rid4) is None)
            rc, shown = veldo('activate', 'owner', '--qualification-id', q.get('id') or '', '--qualification-digest',
                              q.get('digest') or '')
            done4 = wait(lambda: settled(rid4), 20) if rc == 0 else None
            check(SP, 'the owner\'s explicit activation resumes the edge and the kept request settles from the reply sent '
                  'while it was stopped', rc == 0 and bool(done4) and done4.get('choice') == 'accept'
                  and ((done4.get('assertion') or {}).get('attribution') or {}).get('platform_message_id')
                  == late['message']['message_id'])
            check(SP, 'the request opened while stopped is presented once the edge resumes',
                  bool(wait(lambda: published(rid5), 15)))

        # F2: in a run qualifying the Telegram origin, an exchange that fails in transport is named
        # unavailable_service, not fixture evidence, and the run still does not qualify. A separate authority
        # of this run's own, its record opened by the owner's signed qualify for https://api.telegram.org, and
        # the gate's own transport making the exchange; only the network is a stand-in: for the length of
        # each call the connection is refused, times out or its name does not resolve before any socket
        # opens, so nothing reaches the suite's guard, and the guard is back in place after each call.
        with section(TF):
            ACT = load('v138_act_transport', mods / 'control_channel_activation.py')
            telegram = 'https://api.telegram.org'
            T = H.build(base / 'transport', mods, deputy_chat, telegram, 'v138-not-a-token')
            acts = ACT.Activations(T.S, T.conn, T.ids, 'authority', T.journal_sign)
            opened = T.authorize(acts, 'qualify')
            gate = ACT.Gate(T.S, T.conn)
            asked, raised = [], []
            failures = (ConnectionRefusedError(111, 'refused'), TimeoutError('timed out'),
                        socket.gaierror(-2, 'Name or service not known'))
            for failure in failures:
                def network_down(address, *args, **kwargs):
                    asked.append(address[0])
                    raise failure
                socket.create_connection = network_down
                try:
                    gate.open(urllib.request.Request(telegram + '/botv138-not-a-token/getMe', data=b'{}'), 2, 'getMe', telegram)
                except Exception as exc:
                    raised.append(type(exc).__name__)
                finally:
                    socket.create_connection = guarded
            recorded = [x.get('transport_failure') for x in gate.exchanges]
            check(TF, 'the gate made each exchange for the Telegram origin through its own transport, and recorded '
                  'the failure by class [%s %s %s]' % (opened.get('outcome'), recorded, raised),
                  opened.get('outcome') == 'accepted' and asked == ['api.telegram.org'] * 3 and raised == ['URLError'] * 3
                  and recorded == ['ConnectionRefusedError', 'TimeoutError', 'gaierror']
                  and all(x.get('status') is None and x.get('tls') is None and x.get('origin') == telegram
                          for x in gate.exchanges))

            class Nothing:
                def current(self, *args):
                    return None

                evidence = settlement = current
            code = None
            try:
                acts.qualify(gate, Nothing(), Nothing(), Nothing(), 'v138-request', 'v138-owner', 'v138-other')
            except ACT.Refused as exc:
                code = exc.code
            stored = T.conn.execute("SELECT count(*) FROM entities WHERE kind='channel_qualification'").fetchone()[0]
            check(TF, 'the run is refused as unavailable_service, not fixture_only_evidence, and records nothing (%s)'
                  % code, code == 'unavailable_service' and stored == 0
                  and ACT.REFUSALS.get(code) == 'unavailable_service')
            fixture = dict(gate.exchanges[0], transport_failure=None, status=200)
            mixed = ACT.qualification_problems({'schema': ACT.QUALIFICATION_SCHEMA, 'origin': telegram, 'platform': 'telegram',
                                                'exchanges': [dict(gate.exchanges[0]), fixture]}, telegram)
            check(TF, 'control: an exchange with no TLS that did not fail in transport keeps the run fixture_only_evidence '
                  '[%s]' % mixed, mixed == ['fixture_only_evidence'])
            T.conn.close()

        with section(SI):
            armed = guard_armed.read_text().split() if guard_armed.is_file() else []
            check(SI, 'the socket guard was armed in every service process started [%d]' % len(armed), len(armed) >= 4)
            check(SI, 'no connection beyond the loopback interface, in this process or the service\'s [%s %s]'
                  % (attempts, guard_log.read_text() if guard_log.is_file() else ''),
                  not attempts and not (guard_log.is_file() and guard_log.read_text().strip()))
            logged = (home / 'state' / 'observations.jsonl').read_text() if (home / 'state' / 'observations.jsonl').is_file() else ''
            check(SI, 'the observation log records channel passes by name and never the token or message text',
                  '"operation": "channel_pass"' in logged and 'bot138' not in logged and 'settled through' not in logged)
    finally:
        socket.create_connection, socket.getaddrinfo = real_connect, real_resolve
        with contextlib.suppress(Exception):
            if unit:
                CS.stop(unit, manager)
        manager.close()
        stop_api()
        for conn in (getattr(ing, 'conn', None), getattr(A, 'conn', None)):
            with contextlib.suppress(Exception):
                conn.close()
        for directory, _dirs, _files in os.walk(str(base)):
            with contextlib.suppress(OSError):
                os.chmod(directory, 0o700)
        shutil.rmtree(str(base), ignore_errors=True)

    for name, observed in rows.items():
        ok = bool(observed) and all(one for _, one in observed)
        if not ok:
            for label, one in observed:
                if not one:
                    print('  VELDO-0138 %s detail: %s' % (name, label))
            if not observed:
                print('  VELDO-0138 %s detail: no check ran' % name)
        expect('VELDO-0138 ' + name, ok)
    print('VELDO-0138 suite seconds: %.3f' % (time.monotonic() - started))


_v138_suite()
