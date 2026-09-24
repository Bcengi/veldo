"""VELDO-0047: the authority service installed, started and stopped explicitly on this Linux host,
one instance under the store's stable lock, signed local commands applied to the configured SQLite
store, and nothing starting in its place or writing locally while it is absent.

Only shared ROOT and expect are consumed. One temporary tree holds the .veldo copy the suite loads and
the installer copies its fixed executable from, so a registered mutation of a production file (the
service, the client, the scaffolder or the unit template) reaches the installed instance as well.
Real: two enrolled Git clones and a third in another domain, OpenSSH enrollment, request, command and
journal signatures, this host's trust file, the configured SQLite store read back through its own
separate connection, the owner's systemd user manager (units of this run's own, in the runtime unit
directory, uninstalled at the end), the kernel's lock table and socket table, the real claim client,
and a real launch through the INSTALLED receiver on the configuration the installer wrote, whose worker
runs in a transient scope of this run's own slice (stopped at the end). The key directory is passed
explicitly with an explicit set of worker directories, because this account can create no directory
outside the home and temporary directories without root; the default placement's refusal and its
guidance are asserted separately, and the one-time steps it prints are run without sudo below an
ancestor of this run's own.
"""


def _v47_suite():
    import contextlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import pwd
    import shutil
    import signal
    import socket
    import sqlite3
    import subprocess
    import sys
    import tempfile
    import time

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_client.py': ROOT / ".veldo" / "control_client.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
        'services/veldo-authority.service': ROOT / ".veldo" / "services/veldo-authority.service",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    run_id = os.urandom(4).hex()
    tools = dict(os.environ)
    tools['XDG_RUNTIME_DIR'] = tools.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()
    unit_dir = Path(tools['XDG_RUNTIME_DIR']) / 'systemd' / 'user'

    def systemctl(*args):
        return subprocess.run(['systemctl', '--user', *args], capture_output=True, text=True, timeout=30,
                              env=tools, stdin=subprocess.DEVNULL)

    def show(unit):
        if not unit:
            return {}
        out = systemctl('show', '-p', 'LoadState', '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID',
                        '-p', 'NRestarts', '-p', 'Result', unit).stdout
        return dict(line.split('=', 1) for line in out.splitlines() if '=' in line)

    emitted, raised, regions, observed = set(), [], [], {}

    def check(label, condition):
        emitted.add(label)
        expect('VELDO-0047 ' + label, bool(condition))

    @contextlib.contextmanager
    def region(*labels):
        regions.append(labels[0])
        try:
            yield
        except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
            raised.append((labels[0], repr(error)))
            for label in labels:
                if label not in emitted:
                    check(label, False)

    with tempfile.TemporaryDirectory(prefix='v47-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'src' / '.veldo'
        (mods / 'services').mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        CS = load('v47_service', mods / 'control_service.py')
        CC = load('v47_client', mods / 'control_client.py')
        CCL = load('v47_claim_client', mods / 'control_claim_client.py')
        E = load('v47_enrollment', mods / 'control_enrollment.py')
        S = load('v47_store', mods / 'control_store.py')
        AC = load('v47_contract', mods / 'authority_contract.py')
        EL = load('v47_eligibility', mods / 'control_eligibility.py')
        C = load('v47_containment', mods / 'control_containment.py')
        _git_process = load('v47_git', mods / 'git_process.py')
        HOST = 'host-47'
        REFUSED = getattr(CS, 'Refused', Exception)
        # The installer's own judgment of a key directory (None where a build has none).
        judge = getattr(CS, 'key_directory_problems', lambda path, writable: None)

        private = base / 'private'
        private.mkdir(mode=0o700)
        public = {}
        for who in ('owner', 'member', 'intruder', 'scoped', 'worker'):
            subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / who)], check=True,
                           capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
            public[who] = (private / (who + '.pub')).read_text().strip()

        def signer(who, namespace):
            def sign(data):
                return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(private / who), '-n', namespace],
                                      input=data, capture_output=True, check=True, timeout=20,
                                      stdin=None).stdout.decode()
            return sign

        trust_dir = base / 'trust'
        trust_dir.mkdir(mode=0o700)
        signers_file = trust_dir / 'enrollment_signers'
        signers_file.write_text(AC.allowed_signers_line('owner', public['owner'], EL.ENROLLMENT_NAMESPACE) + '\n')
        trust_file = trust_dir / 'host_trust.json'
        trust_file.write_text(json.dumps({'schema': EL.HOST_TRUST_SCHEMA, 'host_identity': HOST,
                                          'enrollment_signers': str(signers_file)}))
        enroll_sign = signer('owner', EL.ENROLLMENT_NAMESPACE)

        def repo(name):
            path = base / name
            _git_process.run(['git', 'init', '-q', str(path)], check=True, capture_output=True)
            (path / 'README').write_text(name + '\n')
            _git_process.run(['git', '-C', str(path), 'add', 'README'], check=True, capture_output=True)
            _git_process.run(['git', '-C', str(path), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', name],
                             check=True, capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
            return path

        DOMAIN, STORE, REPOSITORY = 'dom47' + run_id, 'store47' + run_id, 'repo47' + run_id
        OTHER_REPOSITORY = 'repo47b' + run_id
        store_path = base / 'authority' / 'control.sqlite3'
        other_store = base / 'authorityB' / 'control.sqlite3'
        A, A2, B = repo('clone-a'), repo('clone-a2'), repo('clone-b')
        bind_a = E.enroll(str(A), DOMAIN, STORE, str(store_path), HOST, 1, enroll_sign, 'owner', 'enrolled',
                          repository_uuid=REPOSITORY)
        bind_a2 = E.enroll(str(A2), DOMAIN, STORE, str(store_path), HOST, 1, enroll_sign, 'owner', 'enrolled',
                           repository_uuid=OTHER_REPOSITORY)
        bind_b = E.enroll(str(B), 'dom47x' + run_id, 'store47x' + run_id, str(other_store), HOST, 1, enroll_sign,
                          'owner', 'enrolled', repository_uuid='repo47x' + run_id)
        verify = EL.HostTrust(HOST, str(signers_file)).verifier('owner', str(A))

        # The store the service is configured with, set up by the owner before installation: members,
        # their keys, and one admitted unit for a claim.
        journal_sign = signer('owner', 'veldo-journal')
        setup = S.open_store(str(store_path))
        serial = [0]

        def version_of(conn, identity):
            row = conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
            return row[0] if row else 0

        def put(identity, kind, data, conn=None):
            conn = conn or setup
            serial[0] += 1
            S.execute(conn, dict(command_id='setup-%d' % serial[0], principal='owner', operation='upsert_entity',
                                 nonce='setup-%d' % serial[0], artifact_digests=[],
                                 expected_versions={identity: version_of(conn, identity)},
                                 parameters=dict(entity_id=identity, kind=kind, data=data)), 'owner', journal_sign, 1)

        for who, kind, scope in (('member', 'person', '*'), ('scoped', 'person', ['elsewhere']),
                                 ('worker', 'agent_run', '*')):
            put(who, 'membership', dict(principal_type=kind, roles=[], scope=scope))
            put('key:%s:1' % who, 'verification_key', dict(principal=who, public_key=public[who], effective_at=0))
        put('backlog-47', 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
        put('unit-47', 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog-47',
                                              requirements=[], eligible_holders=['worker']))
        setup.close()

        keys = base / 'keys' / 'authority'
        keys.mkdir(parents=True, mode=0o700)
        os.chmod(str(keys), 0o700)
        workers = [str(base / 'work')]
        install_root = base / 'install'

        def profile(**changes):
            value = {'kind': 'linux-systemd', 'slice': 'v47%s.slice' % run_id, 'lock': str(base / 'workers.lock'),
                     'concurrency': 2, 'runtime_seconds': 600, 'memory_bytes': 256 << 20, 'cpu_percent': 100,
                     'file_bytes': 64 << 20, 'tasks_max': 256, 'stop_grace_seconds': 1, 'kill_grace_seconds': 1}
            value.update(changes)
            return {k: v for k, v in value.items() if v is not None}

        PROFILE = profile()
        # The engine the installed receiver launches reports where it ran: its pid, its cgroup, the
        # caps on that cgroup and the dispatch its environment names.
        markers = base / 'markers'
        markers.mkdir()
        marker = markers / 'ran.json'
        engine = base / 'engine.py'
        engine.write_text(
            'import json, os, sys\n'
            'group = open("/proc/self/cgroup").read().strip().split("::", 1)[-1]\n'
            'def read(name):\n'
            '    try:\n'
            '        return open("/sys/fs/cgroup" + group + "/" + name).read().strip()\n'
            '    except OSError as error:\n'
            '        return repr(error)\n'
            'facts = {"pid": os.getpid(), "cgroup": group, "dispatch": os.environ.get("VELDO_DISPATCH_ID"),\n'
            '         "memory.max": read("memory.max"), "pids.max": read("pids.max")}\n'
            'with open(sys.argv[1] + ".part", "w") as out:\n'
            '    json.dump(facts, out)\n'
            'os.rename(sys.argv[1] + ".part", sys.argv[1])\n')
        ADAPTERS = {'engine': {'argv': [sys.executable, '-B', str(engine), str(marker)]}}

        class Fake:
            """A runner that records systemctl calls and answers nothing, for installs that must refuse."""
            def __init__(self):
                self.calls = []

            def run(self, args):
                self.calls.append(list(args))
                return 0, '', ''

        def attempt(service=None, **kwargs):
            """An installation expected to refuse, into a probe tree systemd does not read, by `service` (an
            installer module; the suite's own by default)."""
            service = service or CS
            probe = base / 'probe' / str(len(list((base / 'probe').iterdir())) if (base / 'probe').is_dir() else 0)
            arguments = dict(host_trust=str(trust_file), key_directory=str(keys), install_root=str(probe / 'install'),
                             unit_dir=str(probe / 'units'), profile=PROFILE, adapters=ADAPTERS, writable=workers,
                             runner=Fake())
            arguments.update(kwargs)
            try:
                result = service.install([str(A)], **arguments)
                outcome = {'refused': None, 'report': bool(result)}
            except getattr(service, 'Refused', Exception) as error:
                outcome = {'refused': getattr(error, 'code', None), 'guidance': getattr(error, 'guidance', None),
                           'detail': getattr(error, 'detail', None)}
            left = sorted(str(p.relative_to(probe)) for p in probe.rglob('*')) if probe.is_dir() else []
            return dict(outcome, left=left)

        def snapshot(*roots):
            """Every path under each root: mode, size, modification time and content digest."""
            out = {}
            for root in roots:
                root = Path(root)
                if not root.is_dir():
                    continue
                for path in sorted(root.rglob('*')):
                    info = path.lstat()
                    content = None
                    if path.is_file() and not path.is_symlink():
                        content = __import__('hashlib').sha256(path.read_bytes()).hexdigest()
                    out[str(path)] = (info.st_mode, info.st_size, info.st_mtime_ns, content)
            return out

        def independent(sql, *params):
            """The configured store read through a connection of this suite's own, never the service's."""
            if not store_path.exists():
                return []
            conn = sqlite3.connect('file:%s?mode=ro' % store_path, uri=True, timeout=10)
            try:
                return conn.execute(sql, params).fetchall()
            finally:
                conn.close()

        def bound_at(address):
            try:
                text = Path('/proc/net/unix').read_text()
            except OSError:
                return None
            return [line for line in text.splitlines()[1:] if line.split() and line.split()[-1] == str(address)]

        def flock_holders(path):
            """Every flock on the file, from the kernel's own lock table: (mode, pid), matched by device
            and inode."""
            try:
                info = os.stat(str(path))
                text = Path('/proc/locks').read_text()
            except OSError:
                return None
            identity = '%02x:%02x:%d' % (os.major(info.st_dev), os.minor(info.st_dev), info.st_ino)
            holders = []
            for line in text.splitlines():
                parts = line.split()
                if len(parts) >= 6 and parts[1] == 'FLOCK' and parts[5] == identity:
                    holders.append((parts[3], int(parts[4])))
            return holders

        def mode(path):
            try:
                return oct(os.lstat(str(path)).st_mode & 0o7777)
            except OSError:
                return None

        member_sign = signer('member', AC.SIGNATURE_NAMESPACE)
        serial_cmd = [0]

        def command(principal='member', entity='note:1', data=None, expected=0, **coordinates):
            serial_cmd[0] += 1
            body = dict(command_id='cmd-%s-%d' % (run_id, serial_cmd[0]), principal=principal,
                        operation='upsert_entity', nonce='nonce-%s-%d' % (run_id, serial_cmd[0]), artifact_digests=[],
                        expected_versions={entity: expected},
                        parameters=dict(entity_id=entity, kind='note', data=data or {'n': serial_cmd[0]}),
                        domain_uuid=DOMAIN, store_uuid=STORE, repository_uuid=REPOSITORY)
            body.update(coordinates)
            return body

        def packet(body, who='member'):
            return {'command': body, 'signature': signer(who, AC.SIGNATURE_NAMESPACE)(S.canonical_bytes(body))}

        def send(workspace, payload, sign=None, seen_at=None):
            try:
                return {'answer': CC.send(str(workspace), payload, E, verify, sign or member_sign, HOST, timeout=10,
                                          seen_at=seen_at)}
            except CC.RoutingRefused as error:
                return {'refused': error.reason, 'coordinates': dict(error.coordinates), 'message': error.message}

        def raw(address, request):
            """A request written straight to a socket, for coordinates no client would build."""
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as conn:
                    conn.settimeout(10)
                    conn.connect(str(address))
                    conn.sendall(json.dumps(request).encode())
                    conn.shutdown(socket.SHUT_WR)
                    out = b''
                    while True:
                        chunk = conn.recv(65536)
                        if not chunk:
                            break
                        out += chunk
                return json.loads(out.decode())
            except (OSError, ValueError) as error:
                return {'error': repr(error)}

        def inspect(now=None):
            try:
                return CC.inspect(str(A), E, verify, member_sign, HOST, now=now, timeout=10)
            except CC.RoutingRefused as error:
                return {'refused': error.reason}

        worker_client = CCL.Client(str(A), 'worker', signer('worker', AC.SIGNATURE_NAMESPACE), verify, HOST, timeout=10)

        def claim(operation='claim'):
            try:
                if operation == 'claim':
                    return {'result': worker_client.claim('unit-47', 'worker')}
                return {'result': worker_client.request(operation, 'unit-47')}
            except CCL.CL.ClaimStopped as error:
                cause = error.__cause__
                return {'stopped': error.reason, 'coordinates': dict(getattr(cause, 'coordinates', {}) or {})}

        def refused_by_name(result, unit, watermark):
            coordinates = result.get('coordinates') or {}
            return (result.get('refused') == 'authority_unavailable' or result.get('stopped') == 'authority_unavailable') \
                and coordinates.get('code') == 'AUTHORITY_UNAVAILABLE' and coordinates.get('service') == STORE \
                and bool(unit) and coordinates.get('unit') == unit \
                and 'systemctl --user start %s' % unit in (coordinates.get('start') or '') \
                and coordinates.get('last_watermark') == watermark and watermark is not None

        socket_path = CC.socket_path_for(bind_a)
        report, seconds, children = {}, [], []
        # What later regions read from earlier ones, so a region that raised leaves them empty, never unbound.
        recorded, receiver_path, home_dir = {}, base / 'no-receiver.json', base / 'nowhere'
        launches, connections = [], []
        started_at = time.monotonic()
        precondition = C.qualify(PROFILE)
        if not precondition.get('qualified'):
            expect('VELDO-0047 STOOD DOWN by name - the systemd user manager, cgroup v2 or systemd-run is not '
                   'available here (%s), so no authority instance can be installed' % precondition.get('refusal'), True)
            return
        try:
            # AC1: the key directory is placed outside every directory a worker writes into directly
            with region('authority/key-directory-placement'):
                user = pwd.getpwuid(os.getuid()).pw_name
                # A directory the ENVIRONMENT names as home, never the real one: a defective build that
                # accepted it would write a key there.
                home = base / 'home'
                home.mkdir(mode=0o700)
                writable_for = getattr(CS, 'worker_writable', lambda environment=None: [])
                in_temp = base / 'tempkeys'
                in_temp.mkdir(mode=0o700)
                loose = base / 'loose'
                loose.mkdir(mode=0o700)
                os.chmod(str(loose), 0o755)
                linked = base / 'linked'
                linked.symlink_to(keys)
                cases = {
                    'absent': (attempt(key_directory=None), 'missing_authority:key_directory:absent'),
                    'home': (attempt(key_directory=str(home), writable=writable_for({'HOME': str(home)})),
                             'invalid_input:key_directory:worker_writable'),
                    'temporary': (attempt(key_directory=str(in_temp), writable=None),
                                  'invalid_input:key_directory:worker_writable'),
                    'mode': (attempt(key_directory=str(loose)), 'invalid_input:key_directory:mode'),
                    'symlink': (attempt(key_directory=str(linked)), 'invalid_input:key_directory:symlink'),
                }
                absent = cases['absent'][0]
                observed['placement'] = {name: dict(result, expected=code) for name, (result, code) in cases.items()}
                check('authority/key-directory-placement',
                      all(result.get('refused') == code and result.get('left') == [] for result, code in cases.values())
                      and 'sudo install -d -m 0700 -o %s' % user in (absent.get('guidance') or '')
                      and '/var/lib/veldo/keys/' in (absent.get('guidance') or '')
                      and 'chmod' not in (cases['mode'][0].get('guidance') or 'chmod')
                      and '/var/lib/veldo/keys/<service id>' in (cases['mode'][0].get('guidance') or '')
                      and not list(in_temp.iterdir()) and not list(loose.iterdir()) and not list(home.iterdir())
                      and os.path.realpath(pwd.getpwuid(os.getuid()).pw_dir) in writable_for({})
                      and os.path.realpath(str(home)) in writable_for({'HOME': str(home)})
                      and all(os.path.realpath(t) in writable_for({}) for t in ('/tmp', '/var/tmp', tempfile.gettempdir())))

            # AC1: an ABSENT key directory is judged by where it would be before whether it exists, so one
            # inside a directory workers write into is refused as that, never handed a step to create it
            with region('authority/key-directory-location-before-existence'):
                real_home = os.path.realpath(pwd.getpwuid(os.getuid()).pw_dir)
                located = {
                    'directly-under-tmp': (os.path.join('/tmp', 'veldo-keys-47-' + run_id), None),
                    'under-the-home': (os.path.join(real_home, '.veldo-keys-47-' + run_id, 'authority'), None),
                    'under-a-worker-directory': (str(base / 'work' / 'keys-47'), workers),
                }
                results = {name: attempt(key_directory=path, writable=writable)
                           for name, (path, writable) in located.items()}
                observed['located'] = {name: dict(result, path=located[name][0]) for name, result in results.items()}
                check('authority/key-directory-location-before-existence',
                      all(result.get('refused') == 'invalid_input:key_directory:worker_writable'
                          and result.get('left') == [] and 'sudo' not in (result.get('guidance') or 'sudo')
                          and 'install -d' not in (result.get('guidance') or 'install -d')
                          and '/var/lib/veldo/keys/<service id>' in (result.get('guidance') or '')
                          for result in results.values())
                      and not any(os.path.lexists(path) for path, _ in located.values()))

            # AC1: the one-time step for a missing key directory creates only the directories below its
            # first existing ancestor, and no printed step changes the mode or owner of one that exists.
            # The steps are run here without sudo, where this account may create them, so what they do is
            # observed rather than read.
            with region('authority/key-directory-guidance-changes-no-directory'):
                user = pwd.getpwuid(os.getuid()).pw_name
                group = __import__('grp').getgrgid(os.getgid()).gr_name
                open_to_others = base / 'open-to-others'
                open_to_others.mkdir()
                os.chmod(str(open_to_others), 0o755)
                shared = base / 'shared'
                shared.mkdir()
                os.chmod(str(shared), 0o1777)
                deep_root = base / 'deep'
                deep_root.mkdir(mode=0o755)
                os.chmod(str(deep_root), 0o755)
                created = {'beside': (shared / 'keys', [shared / 'keys']),
                           'deep': (deep_root / 'veldo' / 'keys' / 'svc',
                                    [deep_root / 'veldo', deep_root / 'veldo' / 'keys', deep_root / 'veldo' / 'keys' / 'svc'])}
                guided = {}
                for name, (path, missing) in created.items():
                    ancestor = missing[0].parent
                    before = (os.lstat(str(ancestor)).st_mode, os.lstat(str(ancestor)).st_uid)
                    result = attempt(key_directory=str(path))
                    text = result.get('guidance') or ''
                    steps = [__import__('shlex').split(step) for step in text[text.find('sudo '):].split(' && ')] if 'sudo ' in text else []
                    named = [Path(step[-1]) for step in steps if step]
                    existing = [str(n) for n in named if os.path.lexists(str(n))]
                    safe = bool(steps) and all(step[:3] == ['sudo', 'install', '-d'] and str(Path(step[-1])).startswith(str(base) + '/')
                                               for step in steps)
                    runs = []
                    if safe:
                        for step in steps:
                            ran = subprocess.run(step[1:], capture_output=True, text=True, timeout=20, stdin=subprocess.DEVNULL)
                            runs.append(ran.returncode)
                    after = (os.lstat(str(ancestor)).st_mode, os.lstat(str(ancestor)).st_uid)
                    guided[name] = {'refused': result.get('refused'), 'named': [str(n) for n in named],
                                    'expected': [str(m) for m in missing], 'existing_named': existing, 'runs': runs,
                                    'ancestor_before': oct(before[0] & 0o7777), 'ancestor_after': oct(after[0] & 0o7777),
                                    'owner_unchanged': before[1] == after[1], 'key_mode': mode(path),
                                    'key_owner_is_this_account': os.path.isdir(str(path)) and os.lstat(str(path)).st_uid == os.getuid(),
                                    'intermediate_modes': [mode(m) for m in missing[:-1]],
                                    'accepted_after': judge(str(path), workers) if os.path.isdir(str(path)) else None,
                                    'last_step': steps[-1][1:] if steps else None}
                others = {'mode': attempt(key_directory=str(open_to_others)), 'owner': attempt(key_directory='/usr/share')}
                guided['others'] = {name: {'refused': result.get('refused'), 'guidance': result.get('guidance')}
                                    for name, result in others.items()}
                observed['guided'] = guided
                check('authority/key-directory-guidance-changes-no-directory',
                      all(g['refused'] == 'missing_authority:key_directory:absent' and g['named'] == g['expected']
                          and g['existing_named'] == [] and g['runs'] == [0] * len(g['expected'])
                          and g['ancestor_before'] == g['ancestor_after'] and g['owner_unchanged']
                          and g['key_mode'] == '0o700' and g['key_owner_is_this_account']
                          and g['intermediate_modes'] == ['0o755'] * (len(g['expected']) - 1)
                          and g['accepted_after'] == [] and g['last_step'][:2] == ['install', '-d']
                          and g['last_step'][2:8] == ['-m', '0700', '-o', user, '-g', group]
                          for name, g in guided.items() if name != 'others')
                      and guided['beside']['ancestor_after'] == '0o1777'
                      and others['mode'].get('refused') == 'invalid_input:key_directory:mode'
                      and others['owner'].get('refused') in ('invalid_input:key_directory:owner', 'invalid_input:key_directory:mode')
                      and all(not any(word in (result.get('guidance') or 'chmod') for word in ('chmod', 'chown', 'install -d'))
                              and '/var/lib/veldo/keys/<service id>' in (result.get('guidance') or '')
                              for result in others.values()))

            # AC1: a relative key directory is refused as relative, before anything resolves it against the
            # working directory, even when it would resolve to a directory the installation would accept
            with region('authority/key-directory-relative-refused'):
                resolvable = base / 'relkeys' / 'authority'
                resolvable.mkdir(parents=True, mode=0o700)
                os.chmod(str(resolvable), 0o700)
                relative = {'resolves-to-an-acceptable-directory': os.path.relpath(str(resolvable), os.getcwd()),
                            'names-nothing': 'veldo-keys-47-' + run_id}
                refusals = {name: attempt(key_directory=path) for name, path in relative.items()}
                observed['relative'] = {name: dict(result, path=relative[name],
                                                   judged_acceptable_absolute=judge(str(resolvable), workers))
                                        for name, result in refusals.items()}
                check('authority/key-directory-relative-refused',
                      all(result.get('refused') == 'invalid_input:key_directory:relative' and result.get('left') == []
                          for result in refusals.values())
                      and not os.path.isabs(relative['resolves-to-an-acceptable-directory'])
                      and judge(str(resolvable), workers) == [] and not list(resolvable.iterdir())
                      and not os.path.lexists(os.path.join(os.getcwd(), relative['names-nothing'])))

            # The installation itself: one instance, into this run's own unit in the runtime unit directory
            with region('authority/installed-fixed-and-protected'):
                try:
                    report = CS.install([str(A)], host_trust=str(trust_file), key_directory=str(keys),
                                        install_root=str(install_root), unit_dir=str(unit_dir), profile=PROFILE,
                                        adapters=ADAPTERS, writable=workers) or {}
                except REFUSED as error:
                    report = {'refused': getattr(error, 'code', None)}
                unit = report.get('unit')
                home_dir = Path(report.get('home') or base / 'nowhere')
                config_path = Path(report.get('config') or base / 'nowhere.json')
                before_start = show(unit)
                try:
                    config = json.loads(config_path.read_text())
                except (OSError, ValueError):
                    config = {}
                unit_file = unit_dir / unit if unit else None
                unit_lines = unit_file.read_text().splitlines() if unit_file and unit_file.is_file() else []
                bin_dir = home_dir / 'bin'
                # What the installer recorded it copied, each file with its digest.
                recorded = config.get('closure') if isinstance(config.get('closure'), dict) else {}
                closure = sorted(recorded)
                entry = {'control_service.py', 'control_launch.py', 'control_keys_custody.py'}
                # The architecture validator the receiver's recheck runs from its own directory
                # (control_eligibility.ValidatorSnapshot), by the files the eligibility module declares.
                validator = {name for _role, name in EL.VALIDATOR_ROLES}
                installed = sorted(p.name for p in bin_dir.iterdir()) if bin_dir.is_dir() else []
                copies = bool(closure) and installed == closure and all(
                    (bin_dir / n).read_bytes() == (mods / n).read_bytes()
                    and recorded[n] == 'sha256:' + __import__('hashlib').sha256((bin_dir / n).read_bytes()).hexdigest()
                    and mode(bin_dir / n) == ('0o500' if n in entry else '0o400') for n in closure)
                executable = str(bin_dir / 'control_service.py')
                exec_start = '%s -B %s serve %s' % (os.path.realpath(sys.executable), executable, config_path)
                started = CS.start(unit) if unit else {}
                after_start = show(unit)
                pid = int(after_start.get('MainPID') or 0)
                try:
                    cmdline = Path('/proc/%d/cmdline' % pid).read_bytes().split(b'\0')[:-1] if pid else []
                except OSError:
                    cmdline = []
                observed['install'] = {
                    'report_keys': sorted(report), 'unit': unit, 'before_start': before_start, 'after_start': after_start,
                    'unit_lines': [l for l in unit_lines if l and not l.startswith('#')],
                    'modes': {n: mode(p) for n, p in (('home', home_dir), ('bin', bin_dir), ('config', home_dir / 'config'),
                                                     ('service.json', config_path), ('signers', home_dir / 'config' / 'enrollment_signers'),
                                                     ('state', home_dir / 'state'), ('keys', keys), ('journal', keys / 'journal'),
                                                     ('socket', socket_path), ('store_dir', store_path.parent))},
                    'closure': len(closure), 'installed': len(installed), 'copies_exact': copies,
                    'validator_installed': sorted(validator & set(installed)), 'validator_declared': sorted(validator),
                    'cmdline_matches': [c.decode() for c in cmdline] == exec_start.split()}
                check('authority/installed-fixed-and-protected',
                      bool(unit) and report.get('started') is False
                      and before_start.get('LoadState') == 'loaded' and before_start.get('ActiveState') == 'inactive'
                      and 'ExecStart=' + exec_start in unit_lines and 'Type=notify' in unit_lines
                      and 'Restart=no' in unit_lines and '[Install]' not in unit_lines
                      and copies and entry <= set(installed) and validator <= set(installed)
                      and mode(bin_dir) == '0o500' and mode(home_dir) == '0o700'
                      and mode(home_dir / 'config') == '0o700' and mode(config_path) == '0o600'
                      and mode(home_dir / 'config' / 'enrollment_signers') == '0o600'
                      and (home_dir / 'config' / 'enrollment_signers').read_bytes() == signers_file.read_bytes()
                      and config.get('store_path') == bind_a['store_path'] and config.get('socket') == socket_path
                      and config.get('enrollments') == {str(A): E.binding_digest(bind_a)}
                      and config.get('repositories') == {REPOSITORY: [str(A)]}
                      and config.get('lock') == str(store_path.parent / 'authority.lock')
                      and config.get('journal_key') == str(keys / 'journal')
                      and mode(keys) == '0o700' and mode(keys / 'journal') == '0o600'
                      and started.get('ActiveState') == 'active' and after_start.get('ActiveState') == 'active'
                      and [c.decode() for c in cmdline] == exec_start.split()
                      and Path(socket_path).is_socket() and mode(socket_path) == '0o600'
                      and mode(store_path.parent) == '0o700')

            # AC1 (the launch receiver's configuration, handed on by VELDO-0040): this host's qualified
            # profile, and the installed receiver itself qualifies it
            with region('authority/receiver-configured-with-host-profile'):
                # An unqualified worker profile refuses installation and leaves nothing behind.
                unqualified = attempt(profile=profile(memory_bytes=None))
                observed['unqualified_profile'] = unqualified
                receivers = (report.get('receiver') or {}).get('configs') or {}
                receiver_path = Path(receivers.get(REPOSITORY) or receiver_path)
                try:
                    receiver_config = json.loads(receiver_path.read_text())
                except (OSError, ValueError):
                    receiver_config = {}
                consumer = {}
                executable = (report.get('receiver') or {}).get('executable')
                if executable and receiver_config:
                    L = load('v47_installed_launch', executable)
                    rec = L.Receiver(receiver_config, lambda message: None)
                    try:
                        consumer = {'refusal': rec._qualify({}), 'qualified': (rec.qualification or {}).get('qualified'),
                                    'executable': str(Path(L.__file__).resolve())}
                    finally:
                        rec.close()
                observed['receiver'] = {'config': {k: v for k, v in receiver_config.items() if k != 'adapters'},
                                        'mode': mode(receiver_path), 'consumer': consumer}
                check('authority/receiver-configured-with-host-profile',
                      unqualified.get('refused') == 'invalid_input:profile:memory_bytes:absent'
                      and unqualified.get('left') == []
                      and list(receivers) == [REPOSITORY] and mode(receiver_path) == '0o600'
                      and receiver_config.get('profile') == PROFILE and C.qualify(receiver_config.get('profile'))['qualified']
                      and receiver_config.get('store') == bind_a['store_path']
                      and receiver_config.get('journal_key') == str(keys / 'journal')
                      and receiver_config.get('domain') == DOMAIN and receiver_config.get('repository') == REPOSITORY
                      and receiver_config.get('workspace') == str(A) and receiver_config.get('authority_generation') == 1
                      and receiver_config.get('adapters') == ADAPTERS
                      and consumer.get('refusal') is None and consumer.get('qualified') is True
                      and consumer.get('executable') == str(home_dir / 'bin' / 'control_launch.py'))

            # AC1, declared falsifier: a second scheduling instance under the same stable lock refuses
            with region('authority/one-instance-under-the-lock'):
                lock = store_path.parent / 'authority.lock'
                state = show(unit)
                pid = int(state.get('MainPID') or 0)
                lock_inode = os.stat(str(lock)).st_ino if lock.exists() else None
                socket_inode = os.stat(socket_path).st_ino if os.path.exists(socket_path) else None
                holders_before = flock_holders(lock)
                second = subprocess.Popen([os.path.realpath(sys.executable), '-B', str(home_dir / 'bin' / 'control_service.py'),
                                           'serve', str(config_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                          stdin=subprocess.DEVNULL, env=tools)
                children.append(second)
                try:
                    code = second.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    code = 'still running'
                holders_during = flock_holders(lock)
                if code == 'still running':
                    second.terminate()
                    with contextlib.suppress(subprocess.TimeoutExpired):
                        second.wait(timeout=3)
                    if second.poll() is None:
                        second.kill()
                        second.wait(timeout=5)
                err = second.stderr.read().decode('utf-8', 'replace')
                second.stdout.close()
                second.stderr.close()
                try:
                    refusal = json.loads(err.strip().splitlines()[-1]) if err.strip() else {}
                except ValueError:
                    refusal = {'text': err[-300:]}
                after = show(unit)
                live = inspect()
                observed['lock'] = {'second_exit': code, 'refusal': {k: refusal.get(k) for k in ('refusal', 'taxonomy')},
                                    'holders_before': holders_before, 'holders_during': holders_during,
                                    'first_pid': pid, 'first_after': after.get('MainPID'),
                                    'lock_inode_stable': lock_inode is not None and os.stat(str(lock)).st_ino == lock_inode,
                                    'socket_inode_stable': socket_inode is not None and os.path.exists(socket_path)
                                    and os.stat(socket_path).st_ino == socket_inode, 'live_after': live.get('stale')}
                check('authority/one-instance-under-the-lock',
                      pid > 0 and code == getattr(CS, 'EXIT_LOCK_HELD', 'none') and code != 0
                      and refusal.get('refusal') == 'authority_lock_held' and refusal.get('taxonomy') == 'unavailable_service'
                      and holders_before == [('WRITE', pid)] and holders_during == [('WRITE', pid)]
                      and observed['lock']['lock_inode_stable'] and observed['lock']['socket_inode_stable']
                      and after.get('ActiveState') == 'active' and int(after.get('MainPID') or 0) == pid
                      and live.get('stale') is False)

            # AC2, declared falsifier: a signed mutation through production IPC changes the configured
            # store itself, read back through a connection of this suite's own
            with region('authority/mutation-reaches-the-configured-store'):
                first = command(entity='note:1', data={'v': 1})
                answer = send(A, packet(first), seen_at='live-1').get('answer') or {}
                receipt = ((answer.get('result') or {}).get('receipt')) or {}
                entity = independent('SELECT kind, version, data FROM entities WHERE id=?', 'note:1')
                journal = independent('SELECT seq, record_digest, principal, signer FROM journal WHERE command_id=?',
                                      first['command_id'])
                top = independent('SELECT MAX(seq) FROM journal')
                claimed = claim()
                claim_row = independent('SELECT data FROM entities WHERE id=?', 'claim:%s:unit-47' % REPOSITORY)
                claim_data = json.loads(claim_row[0][0]) if claim_row else {}
                observed['mutation'] = {'answer_accepted': answer.get('accepted'), 'result_ok': (answer.get('result') or {}).get('ok'),
                                        'watermark': answer.get('watermark'), 'receipt_seq': receipt.get('seq'),
                                        'entity': entity, 'journal': [row[:1] + row[2:] for row in journal],
                                        'journal_digest_matches': bool(journal) and journal[0][1] == receipt.get('record_digest'),
                                        'top': top, 'claim': claimed, 'claim_entity': {k: claim_data.get(k) for k in ('state', 'holder', 'generation')},
                                        'other_store_exists': other_store.exists()}
                check('authority/mutation-reaches-the-configured-store',
                      answer.get('accepted') is True and (answer.get('result') or {}).get('ok') is True
                      and receipt.get('committed') is True and receipt.get('command_id') == first['command_id']
                      and entity == [('note', 1, json.dumps({'v': 1}, sort_keys=True))]
                      and len(journal) == 1 and journal[0][0] == receipt.get('seq') == answer.get('watermark') == top[0][0]
                      and journal[0][1] == receipt.get('record_digest') and journal[0][2:] == ('member', 'authority')
                      and claimed.get('result') == (True, 'granted')
                      and claim_data.get('state') == 'owned' and claim_data.get('holder') == 'worker'
                      and claim_data.get('generation') == 1 and not other_store.exists())

            # AC2: wrong coordinates or the wrong actor refuse, and the store does not change
            with region('authority/wrong-coordinates-or-actor-refused'):
                before = independent('SELECT seq, record_digest FROM journal ORDER BY seq')
                entities_before = independent('SELECT id, version, digest FROM entities ORDER BY id')
                outer_b = CC.build_request(str(B), bind_b, packet(command(entity='note:x')), member_sign)
                forged = CC.build_request(str(B), bind_b, packet(command(entity='note:y')), member_sign)
                forged.update(domain_uuid=DOMAIN, store_uuid=STORE)
                forged['signature'] = member_sign(CC.signed_bytes(forged))
                intruder_sign = signer('intruder', AC.SIGNATURE_NAMESPACE)

                def result_of(outcome):
                    answer = outcome.get('answer') or outcome
                    if answer.get('accepted') is True:
                        inner = answer.get('result') or {}
                        return 'ok' if inner.get('ok') else inner.get('reason')
                    return answer.get('reason') or outcome.get('refused') or answer.get('error')

                outcomes = {
                    'other-domain': result_of(raw(socket_path, outer_b)),
                    'forged-coordinates': result_of(raw(socket_path, forged)),
                    'unserved-repository': result_of(send(A2, packet(command(entity='note:z', repository_uuid=OTHER_REPOSITORY)))),
                    'inner-repository': result_of(send(A, packet(command(entity='note:r', repository_uuid=OTHER_REPOSITORY)))),
                    'inner-domain': result_of(send(A, packet(command(entity='note:d', domain_uuid='dom47x' + run_id)))),
                    'not-a-member': result_of(send(A, packet(command(principal='intruder', entity='note:i'), 'intruder'))),
                    'impersonation': result_of(send(A, packet(command(principal='member', entity='note:p'), 'intruder'))),
                    'out-of-scope': result_of(send(A, packet(command(principal='scoped', entity='note:s'), 'scoped'))),
                    'type-not-admitted': result_of(send(A, packet(command(principal='worker', entity='note:w'), 'worker'))),
                    'unsigned-request': result_of(send(A, packet(command(entity='note:u')), sign=intruder_sign)),
                }
                expected = {'other-domain': 'coordinate_not_served', 'forged-coordinates': 'coordinate_not_served',
                            'unserved-repository': 'missing_authority:repository_not_served',
                            'inner-repository': 'invalid_input:coordinates', 'inner-domain': 'invalid_input:coordinates',
                            'not-a-member': 'not_authorized', 'impersonation': 'not_authorized',
                            'out-of-scope': 'not_authorized', 'type-not-admitted': 'not_authorized',
                            'unsigned-request': 'command_signature_invalid'}
                after = independent('SELECT seq, record_digest FROM journal ORDER BY seq')
                entities_after = independent('SELECT id, version, digest FROM entities ORDER BY id')
                observed['refusals'] = outcomes
                check('authority/wrong-coordinates-or-actor-refused',
                      outcomes == expected and bool(before) and after == before and entities_after == entities_before)

            # AC3, declared falsifier: with the service stopped, every client refuses by name, starts
            # nothing and writes nothing
            with region('authority/absent-service-refuses-by-name'):
                live = inspect(now='live-2')
                watermark = live.get('watermark')
                stopped = CS.stop(unit) if unit else {}
                clone_control = Path(E.git_common_dir(str(A))) / 'veldo' / 'control'
                listing = snapshot(store_path.parent, clone_control)
                mutated = send(A, packet(command(entity='note:2')), seen_at='down-1')
                claimed = claim('renew')
                stale = inspect(now='down-2')
                listing_after = snapshot(store_path.parent, clone_control)
                state = show(unit)
                observed['absent'] = {'stopped': stopped.get('ActiveState'), 'state': state, 'watermark': watermark,
                                      'mutation': {k: mutated.get('coordinates', {}).get(k) for k in ('code', 'service', 'unit', 'last_watermark')},
                                      'claim': claimed.get('stopped'), 'stale': {k: stale.get(k) for k in ('stale', 'code', 'watermark', 'read_only')},
                                      'socket_exists': os.path.exists(socket_path), 'bound': bound_at(socket_path),
                                      'unchanged': listing == listing_after}
                check('authority/absent-service-refuses-by-name',
                      live.get('stale') is False and isinstance(watermark, int) and watermark > 0
                      and stopped.get('ActiveState') == 'inactive'
                      and refused_by_name(mutated, unit, watermark) and refused_by_name(claimed, unit, watermark)
                      and stale.get('stale') is True and stale.get('code') == 'AUTHORITY_UNAVAILABLE'
                      and stale.get('unit') == unit and 'systemctl --user start %s' % unit in (stale.get('start') or '')
                      and stale.get('watermark') == watermark and stale.get('as_of') == 'live-2'
                      and (stale.get('state') or {}).get('watermark') == watermark and stale.get('read_only') is True
                      and bool(listing) and listing == listing_after
                      and state.get('ActiveState') == 'inactive' and state.get('NRestarts') == '0'
                      and not os.path.exists(socket_path) and bound_at(socket_path) == [])

            # AC3: an unexpected exit leaves the authority stopped until an explicit start
            with region('authority/unexpected-exit-waits-for-an-operator'):
                restarted = CS.start(unit) if unit else {}
                third = command(entity='note:3', data={'v': 3})
                accepted = send(A, packet(third), seen_at='live-3').get('answer') or {}
                watermark = accepted.get('watermark')
                pid = int(show(unit).get('MainPID') or 0)
                killed = False
                if pid:
                    os.kill(pid, signal.SIGKILL)
                    killed = True
                end = time.monotonic() + 5
                while time.monotonic() < end and show(unit).get('ActiveState') in ('active', 'deactivating'):
                    time.sleep(0.05)
                time.sleep(1.5)  # longer than any restart delay a unit would carry
                crashed = show(unit)
                clone_control = Path(E.git_common_dir(str(A))) / 'veldo' / 'control'
                listing = snapshot(store_path.parent, clone_control)
                mutated = send(A, packet(command(entity='note:4')))
                claimed = claim('renew')
                stale = inspect()
                listing_after = snapshot(store_path.parent, clone_control)
                still = show(unit)
                bound = bound_at(socket_path)
                operator = CS.start(unit) if unit else {}
                back = inspect(now='live-4')
                fourth = command(entity='note:5', data={'v': 5})
                resumed = send(A, packet(fourth)).get('answer') or {}
                observed['exit'] = {'restarted': restarted.get('ActiveState'), 'killed': killed, 'crashed': crashed,
                                    'still': still, 'watermark': watermark,
                                    'mutation': {k: mutated.get('coordinates', {}).get(k) for k in ('code', 'unit', 'last_watermark')},
                                    'claim': claimed.get('stopped'), 'stale': stale.get('stale'),
                                    'dead_socket': Path(socket_path).is_socket() if os.path.exists(socket_path) else None,
                                    'unchanged': listing == listing_after, 'bound': bound, 'operator': operator.get('ActiveState'),
                                    'back': {k: back.get(k) for k in ('stale', 'watermark')},
                                    'resumed_seq': ((resumed.get('result') or {}).get('receipt') or {}).get('seq')}
                check('authority/unexpected-exit-waits-for-an-operator',
                      restarted.get('ActiveState') == 'active' and accepted.get('accepted') is True
                      and isinstance(watermark, int) and killed
                      and crashed.get('ActiveState') == 'failed' and crashed.get('NRestarts') == '0'
                      and crashed.get('MainPID') == '0' and still.get('ActiveState') == 'failed'
                      and refused_by_name(mutated, unit, watermark) and refused_by_name(claimed, unit, watermark)
                      and stale.get('stale') is True and stale.get('watermark') == watermark
                      and bool(listing) and listing == listing_after and bound == []
                      and operator.get('ActiveState') == 'active' and back.get('stale') is False
                      and back.get('watermark') == watermark
                      and ((resumed.get('result') or {}).get('receipt') or {}).get('seq') == watermark + 1)

            # Observability: every accepted and refused operation, by name and class, without secrets
            with region('authority/observations'):
                log = Path(report.get('home') or base / 'nowhere') / 'state' / 'observations.jsonl'
                text = log.read_text() if log.is_file() else ''
                lines = [json.loads(line) for line in text.splitlines() if line.strip()]
                by_command = {line.get('command_id'): line for line in lines if line.get('command_id')}
                refused = [line for line in lines if line.get('outcome') == 'refused']
                live = inspect(now='live-5')
                counts = ((live.get('state') or {}).get('counts')) or {}
                pending = ((live.get('state') or {}).get('pending')) or {}
                noted = by_command.get(first['command_id']) or {}
                classes = {(line.get('refusal'), line.get('taxonomy')) for line in refused}
                observed['observations'] = {'lines': len(lines), 'refused': len(refused), 'classes': sorted(map(str, classes)),
                                            'first': {k: noted.get(k) for k in ('operation', 'outcome', 'accepted_versions',
                                                                                  'domain_uuid', 'repository_uuid')},
                                            'counts': counts, 'pending': pending}
                taxonomy = getattr(CS, 'taxonomy', lambda code: None)
                check('authority/observations',
                      noted.get('operation') == 'upsert_entity' and noted.get('outcome') == 'accepted'
                      and noted.get('accepted_versions') == {'note:1': 0} and noted.get('domain_uuid') == DOMAIN
                      and noted.get('repository_uuid') == REPOSITORY and noted.get('refusal') is None
                      and ('not_authorized', 'missing_authority') in classes
                      and ('invalid_input:coordinates', 'invalid_input') in classes
                      and ('missing_authority:repository_not_served', 'missing_authority') in classes
                      and ('coordinate_not_served', 'invalid_input') in classes
                      and ('command_signature_invalid', 'missing_authority') in classes
                      and all(line.get('taxonomy') in ('invalid_input', 'missing_authority', 'stale_subject',
                                                       'unavailable_service', 'missing_evidence', 'unknown_outcome')
                              for line in refused)
                      and taxonomy('a_code_nobody_named') == 'unknown_outcome'
                      and 'SSH SIGNATURE' not in text and 'PRIVATE KEY' not in text and str(keys) not in text
                      and counts.get('accepted', 0) >= 4 and counts.get('refused', 0) >= 8
                      and (counts.get('refusals') or {}).get('not_authorized') == 4
                      and pending.get('claims') == 1)

            # AC1 end to end (VELDO-0040's handover): a real launch through the INSTALLED receiver, the
            # VELDO-0039 Runner invoking it on the configuration the installer wrote, whose worker runs
            # contained in the profile's slice. The scheduler's side (the Runner's own Gate and the
            # reservations) runs in this suite; everything past the invocation is the installed program.
            with region('authority/installed-receiver-launches'):
                LAUNCH_UNIT, HOLDER, ACCOUNT = 'unit-47-launch', 'builder-47', 'acct-47'
                CLM = load('v47_claim', mods / 'control_claim.py')
                RES = load('v47_reservations', mods / 'control_reservations.py')
                launch_writer = S.open_store(str(store_path))
                connections.append(launch_writer)
                launch_reader = S.open_store(str(store_path), mode='r')
                connections.append(launch_reader)
                launch_writer.command_registry['claim_operation'] = {
                    'transition': CLM.transition, 'writes': ('entities', 'journal', 'commands', 'nonces')}
                for principal in ('runner', 'launch-receiver'):
                    put(principal, 'membership', dict(principal_type='service', roles=['reservation_service'],
                                                      scope=[REPOSITORY], revoked_at=None, expires_at=None), conn=launch_writer)
                put('project:p47', 'project', dict(name='authority-launch'), conn=launch_writer)
                reservations = RES.Reservations(S, launch_writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                                authorize=lambda conn, command: True, signer='runner', sign=journal_sign)
                for scope, subject in (('account', ACCOUNT), ('project', 'p47'), ('unit', LAUNCH_UNIT)):
                    reservations.configure('policy/' + subject, scope, subject,
                                           dict(capacity=5, invocations=50, wall_seconds=10 ** 5), now=time.time())
                put(LAUNCH_UNIT, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY,
                                                        backlog_item_uuid='backlog:' + LAUNCH_UNIT, requirements=[],
                                                        eligible_holders=[HOLDER], project='p47',
                                                        scope_digest='sha256:scope-' + LAUNCH_UNIT, revision=1, depends_on=[]),
                    conn=launch_writer)
                put('backlog:' + LAUNCH_UNIT, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY),
                    conn=launch_writer)
                put('admission:' + LAUNCH_UNIT, 'admission', dict(unit=LAUNCH_UNIT, state='accepted',
                                                                  scope_digest='sha256:scope-' + LAUNCH_UNIT), conn=launch_writer)
                claim_entity = CLM.claim_id(REPOSITORY, LAUNCH_UNIT)
                S.execute(launch_writer, dict(
                    command_id='claim-launch-' + run_id, principal=HOLDER, operation='claim_operation',
                    nonce='claim-launch-' + run_id, artifact_digests=[],
                    expected_versions={LAUNCH_UNIT: version_of(launch_writer, LAUNCH_UNIT),
                                       'backlog:' + LAUNCH_UNIT: version_of(launch_writer, 'backlog:' + LAUNCH_UNIT),
                                       claim_entity: 0},
                    parameters=dict(action='claim', unit_id=LAUNCH_UNIT, backlog_item_uuid='backlog:' + LAUNCH_UNIT,
                                    claim_id=claim_entity, holder=HOLDER, generation=0, capabilities=[],
                                    repository_uuid=REPOSITORY)), HOLDER, journal_sign, 1)
                receiver_config_path = ((report.get('receiver') or {}).get('configs') or {}).get(REPOSITORY)
                installed_receiver = (report.get('receiver') or {}).get('executable')
                IL, runner, launch, errors = None, None, None, {}
                result, refusal, group, record = None, None, {}, {}
                # An installed receiver that cannot even be loaded, or a launch that cannot be submitted, is the
                # finding, recorded by name, never a raise.
                try:
                    IL = load('v47_installed_receiver', installed_receiver)
                except Exception as error:  # noqa: BLE001
                    errors['load'] = '%s: %s' % (type(error).__name__, str(error)[:300])
                if IL is not None:
                    try:
                        dispatches = IL.D.Dispatches(S, launch_writer, domain=DOMAIN, repository=REPOSITORY,
                                                     principal='runner', signer='runner', sign=journal_sign)
                        gate = EL.Gate(S, launch_reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(A))
                        runner = IL.Runner(gate, reservations, dispatches,
                                           lambda contract: IL.invoke(receiver_config_path, contract, dispatches,
                                                                      accept_seconds=20),
                                           account=ACCOUNT)
                        launch = runner.submit(LAUNCH_UNIT, 'build', holder=HOLDER, source=str(A), revision='HEAD',
                                               payload={}, adapter='engine', configuration={'tools': ['Read'], 'model': 'm'},
                                               deadline=time.time() + 60)
                        launches.append(launch)
                        result, refusal, group = launch.result, launch.refusal, dict(launch.group or {})
                        record = runner.wait(launch, timeout=30) if result == 'accepted' else (launch.record or {})
                    except Exception as error:  # noqa: BLE001
                        errors['launch'] = '%s: %s' % (type(error).__name__, str(error)[:300])
                record = record or {}
                ran = json.loads(marker.read_text()) if marker.is_file() else {}
                scope = C.unit_name(launch.dispatch_id) if launch is not None else None
                termination = record.get('termination') or {}
                observed['launch'] = {'receiver': getattr(IL, 'RECEIVER', None), 'errors': errors, 'result': result,
                                      'refusal': refusal, 'group': group,
                                      'state': record.get('state'), 'record_refusal': record.get('refusal'),
                                      'termination': {k: termination.get(k) for k in ('returncode', 'signal', 'deadline_stop')},
                                      'process_pid': (record.get('process') or {}).get('pid'), 'worker': ran,
                                      'scope': scope, 'scope_after': show(scope).get('ActiveState') if scope else None,
                                      'retired': [o.get('outcome') for o in getattr(runner, 'observations', [])
                                                  if o.get('operation') == 'retire']}
                check('authority/installed-receiver-launches',
                      not errors and getattr(IL, 'RECEIVER', None) == str(home_dir / 'bin' / 'control_launch.py') == installed_receiver
                      and receiver_config_path == str(receiver_path)
                      and result == 'accepted' and refusal is None and record.get('state') == 'exited'
                      and termination.get('returncode') == 0 and termination.get('deadline_stop') is False
                      and bool(ran) and ran.get('pid') == (record.get('process') or {}).get('pid')
                      and ran.get('dispatch') == getattr(launch, 'dispatch_id', False)
                      and ran.get('cgroup', '').endswith('/%s/%s' % (PROFILE['slice'], scope))
                      and group.get('slice') == PROFILE['slice'] and group.get('unit') == scope
                      and ran.get('memory.max') == str(PROFILE['memory_bytes']) and ran.get('pids.max') == str(PROFILE['tasks_max'])
                      and observed['launch']['retired'] == ['retired']
                      and observed['launch']['scope_after'] in ('inactive', '', None))

            # Distribution: the installer's fixed executable and its template are installed assets. A tree
            # holding exactly the modules the scaffolder lays down (an adopter's) derives the installer's
            # whole closure with nothing absent, and finds its default unit directory
            with region('authority/installed-assets'):
                scaffold = load('v47_scaffold', mods / 'init_scaffold.py')
                files = set(getattr(scaffold, '_FILES', []))
                laid = base / 'laid' / '.veldo'
                (laid / 'services').mkdir(parents=True)
                for rel in sorted(files):
                    if rel.startswith('.veldo/') and (rel.endswith('.py') or rel.endswith('.service')) and (mods / rel[len('.veldo/'):]).is_file():
                        shutil.copyfile(mods / rel[len('.veldo/'):], laid / rel[len('.veldo/'):])
                adopter, LCS = {}, None
                # Each question an adopter's installer must answer, asked on its own: a failure to answer is
                # the finding, recorded by name, never a raise.
                for question in ('load', 'closure', 'unit_dir'):
                    try:
                        if question == 'load':
                            LCS = load('v47_laid_service', laid / 'control_service.py')
                        elif LCS is not None:
                            adopter[question] = LCS.closure() if question == 'closure' else LCS.default_unit_dir()
                    except Exception as error:  # noqa: BLE001
                        adopter.setdefault('errors', {})[question] = '%s: %s' % (type(error).__name__, str(error)[:300])
                installed_closure = sorted(recorded)
                observed['assets'] = {'adopter': dict(adopter, closure=len(adopter.get('closure') or [])),
                                      'installed': len(installed_closure),
                                      'not_laid': sorted(n for n in installed_closure if '.veldo/' + n not in files)}
                check('authority/installed-assets',
                      '.veldo/control_service.py' in files and '.veldo/services/veldo-authority.service' in files
                      and bool(installed_closure) and all('.veldo/' + name in files for name in installed_closure)
                      and LCS is not None and 'errors' not in adopter and adopter.get('closure') == installed_closure
                      and isinstance(adopter.get('unit_dir'), str) and os.path.isabs(adopter['unit_dir'])
                      and adopter['unit_dir'].endswith(os.path.join('systemd', 'user')))

            # AC1: an engine whose programs load a module the installer cannot derive, or one the engine
            # lacks, refuses installation by name and lays nothing down: the installed program is never
            # short of a module it loads, and never finds that out when it runs
            with region('authority/installation-refuses-an-underivable-closure'):
                late = {'unresolved': ('\n\ndef _late_organ(name):\n    return _organ(name)\n',
                                       'invalid_input:closure:unresolved', 'control_launch.py:'),
                        'absent': ('\n\ndef _late_organ():\n    return _organ(\'control_never_shipped\')\n',
                                   'invalid_input:closure:absent', 'control_never_shipped.py')}
                underivable = {}
                for name, (addition, code, named) in late.items():
                    engine_copy = base / ('engine-' + name) / '.veldo'
                    shutil.copytree(mods, engine_copy)
                    with open(engine_copy / 'control_launch.py', 'a') as handle:
                        handle.write(addition)
                    try:
                        refused = attempt(service=load('v47_engine_' + name, engine_copy / 'control_service.py'))
                    except Exception as error:  # noqa: BLE001 - an installer that cannot even answer is the finding
                        refused = {'error': '%s: %s' % (type(error).__name__, str(error)[:300])}
                    underivable[name] = dict(refused, expected=code, names=named)
                observed['underivable'] = underivable
                check('authority/installation-refuses-an-underivable-closure',
                      all(r.get('refused') == r['expected'] and r['names'] in (r.get('detail') or '')
                          and r.get('left') == [] and 'error' not in r for r in underivable.values()))
        finally:
            for child in children:
                with contextlib.suppress(Exception):
                    if child.poll() is None:
                        child.kill()
                    child.wait(timeout=5)
            for launch in launches:
                with contextlib.suppress(Exception):
                    if launch.child is not None:
                        if launch.child.poll() is None:
                            launch.child.kill()
                        launch.child.wait(timeout=10)
                        for pipe in (launch.child.stdin, launch.child.stdout):
                            if pipe is not None:
                                pipe.close()
            # Whatever a defective build left of this run's worker is ended, and this run's slice and
            # dispatch scopes are stopped and cleared so nothing it made stays loaded.
            with contextlib.suppress(Exception):
                facts = json.loads(marker.read_text())
                if os.path.exists('/proc/%d' % facts['pid']) and str(engine) in Path('/proc/%d/cmdline' % facts['pid']).read_text():
                    os.kill(facts['pid'], signal.SIGKILL)
            with contextlib.suppress(Exception):
                systemctl('stop', PROFILE['slice'])
            with contextlib.suppress(Exception):
                scopes = [C.unit_name(launch.dispatch_id) for launch in launches]
                loaded = [line.split()[0] for line in systemctl('list-units', '--all', '--plain', '--no-legend',
                                                                *scopes).stdout.splitlines() if line.split()] if scopes else []
                if loaded:
                    systemctl('reset-failed', *loaded)
            for conn in connections:
                with contextlib.suppress(Exception):
                    conn.close()
            unit = report.get('unit')
            if unit:
                with contextlib.suppress(Exception):
                    systemctl('stop', unit)
                with contextlib.suppress(Exception):
                    CS.uninstall(unit, install_root=str(install_root), unit_dir=str(unit_dir))
                # Whatever a defective build left of this run's own unit is removed here as well.
                with contextlib.suppress(Exception):
                    if (unit_dir / unit).exists():
                        (unit_dir / unit).unlink()
                        systemctl('daemon-reload')
                with contextlib.suppress(Exception):
                    systemctl('reset-failed', unit)
            seconds.append(time.monotonic() - started_at)
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        observed['seconds'] = round(seconds[0], 3) if seconds else None
        globals()['_V47_OBSERVED'] = observed


_v47_started = __import__('time').monotonic()
# The operator's session. In production a client runs where XDG_RUNTIME_DIR names the owner's user
# manager, so a client that tried to start the authority itself would succeed there; the gate's mutation
# stage runs this suite without one, which would make that defect fail silently and pass. The suite's own
# process gets the same session for its run, so the defect is observed, never masked.
_v47_session = __import__('os').environ.get('XDG_RUNTIME_DIR')
__import__('os').environ['XDG_RUNTIME_DIR'] = _v47_session or '/run/user/%d' % __import__('os').getuid()
try:
    _v47_suite()
finally:
    if _v47_session is None:
        __import__('os').environ.pop('XDG_RUNTIME_DIR', None)
    else:
        __import__('os').environ['XDG_RUNTIME_DIR'] = _v47_session
_V47_SECONDS = __import__('time').monotonic() - _v47_started
