"""VELDO-0040: each Linux worker in its dispatch's own systemd scope and cgroup v2 group under the
trusted wrapper, the profile's caps installed before it runs, a stop of the whole group and exit
detection from OS notifications, over real processes on this host.

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy the
runner loads and the receiver and trusted wrapper execute, so a registered mutation of a production
module reaches all three. Real SQLite store, OpenSSH journal signatures, a Git source repository,
VELDO-0052's eligibility Gate, VELDO-0036 reservations, the VELDO-0031 claim transition, the owner's
systemd user manager (transient scopes in slices of this run's own) and the kernel's cgroup, pidfd
and /proc files. The worker is a fixture engine: it starts ordinary descendants (a child, a new
session, a new process group, a double-forked daemon, a signal-ignoring one), allocates memory,
burns CPU, writes a file, handles a stop, and writes what it saw; it qualifies no live engine.
"""


def _v40_suite():
    import contextlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import signal
    import subprocess
    import sys
    import tempfile
    import time
    import types

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_containment.py': ROOT / ".veldo" / "control_containment.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    run_id = os.urandom(4).hex()
    slices = ['v40%sa.slice' % run_id, 'v40%sb.slice' % run_id]
    tools = dict(os.environ)
    tools['XDG_RUNTIME_DIR'] = tools.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()

    def systemctl(*args):
        return subprocess.run(['systemctl', '--user', *args], capture_output=True, text=True, timeout=20,
                              env=tools, stdin=subprocess.DEVNULL)

    def show(unit, *names):
        out = systemctl('show', *[a for n in names for a in ('-p', n)], unit).stdout
        return dict(line.split('=', 1) for line in out.splitlines() if '=' in line)

    with tempfile.TemporaryDirectory(prefix='v40-', dir=fast) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        S = load('v40_store', mods / 'control_store.py')
        L = load('v40_launch', mods / 'control_launch.py')
        C = load('v40_containment', mods / 'control_containment.py')
        D = L.D
        EL = load('v40_eligibility', mods / 'control_eligibility.py')
        RES = load('v40_reservations', mods / 'control_reservations.py')
        SIG = load('v40_signer', mods / 'control_signer.py')
        GP = load('v40_git', mods / 'git_process.py')
        CLM = D.CLM
        DOMAIN, REPOSITORY, ACCOUNT, HOLDER = 'domain-40', 'repository-40', 'acct-40', 'builder-1'
        private = base / 'private'
        private.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / 'journal')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        db = base / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        reader = S.open_store(str(db), mode='r')
        serial = [0]

        def entity(identity):
            row = writer.execute('SELECT kind, version, digest, data FROM entities WHERE id=?', (identity,)).fetchone()
            return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

        def put(identity, kind, data):
            serial[0] += 1
            current = entity(identity)
            S.execute(writer, dict(command_id='setup-%d' % serial[0], principal='owner', operation='upsert_entity',
                                   nonce='setup-%d' % serial[0], artifact_digests=[],
                                   expected_versions={identity: current['version'] if current else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), 'owner', sign, 1)

        for principal in ('runner', 'launch-receiver'):
            put(principal, 'membership', dict(principal_type='service', roles=['reservation_service'],
                                              scope=[REPOSITORY], revoked_at=None, expires_at=None))
        put('project:p1', 'project', dict(name='containment'))
        writer.command_registry['claim_operation'] = {'transition': CLM.transition,
                                                      'writes': ('entities', 'journal', 'commands', 'nonces')}

        def authority(conn, command):
            row = conn.execute('SELECT data FROM entities WHERE id=?', (command['principal'],)).fetchone()
            data = json.loads(row[0]) if row else {}
            return 'reservation_service' in (data.get('roles') or []) and data.get('revoked_at') is None

        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=authority, signer='runner', sign=sign)
        for scope, subject in (('account', ACCOUNT), ('project', 'p1')):
            reservations.configure('policy/' + subject, scope, subject,
                                   dict(capacity=100, invocations=100, wall_seconds=10 ** 6), now=time.time())

        def admitted(unit):
            """A real admitted unit, claimed through VELDO-0031's own transition."""
            put(unit, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + unit,
                                             requirements=[], eligible_holders=[HOLDER], project='p1',
                                             scope_digest='sha256:scope-' + unit, revision=1, depends_on=[]))
            put('backlog:' + unit, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
            put('admission:' + unit, 'admission', dict(unit=unit, state='accepted', scope_digest='sha256:scope-' + unit))
            reservations.configure('policy/' + unit, 'unit', unit, dict(capacity=5, invocations=50, wall_seconds=10 ** 5),
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
        (src / 'README').write_text('containment source\n')
        GP.run(['git', '-C', str(src), 'add', 'README'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))

        # The fixture engine and its descendants. Every process writes <tag>.<name>.json with what the
        # kernel says about it (pid, start, session, group, cgroup, ids, capabilities, file limit),
        # logs each SIGTERM it gets and, when told, a heartbeat, so the suite reads the escalation from
        # the processes themselves.
        markers = base / 'markers'
        markers.mkdir()
        common = '''import json, os, resource, signal, sys, time
from pathlib import Path
def facts(role):
    status = dict(l.split(':\\t', 1) for l in Path('/proc/self/status').read_text().splitlines() if ':\\t' in l)
    stat = Path('/proc/self/stat').read_text()
    return {'role': role, 'pid': os.getpid(), 'start': stat[stat.rindex(')') + 2:].split()[19], 'ppid': os.getppid(),
            'sid': os.getsid(0), 'pgid': os.getpgid(0),
            'cgroup': next(l[3:] for l in Path('/proc/self/cgroup').read_text().splitlines() if l.startswith('0::')),
            'uid': status['Uid'].split(), 'gid': status['Gid'].split(),
            'caps': {k: status[k].strip() for k in ('CapInh', 'CapPrm', 'CapEff', 'CapAmb')},
            'fsize': list(resource.getrlimit(resource.RLIMIT_FSIZE)), 'at': time.time()}
def mark(markers, tag, name, data):
    path = Path(markers) / ('%s.%s' % (tag, name))
    temporary = Path(markers) / ('%s.%s.%d.tmp' % (tag, name, os.getpid()))
    temporary.write_text(json.dumps(data))
    os.replace(temporary, path)
def log(markers, tag, name, what):
    with open(Path(markers) / ('%s.%s.%s' % (tag, name, what)), 'a') as handle:
        handle.write('%r\\n' % time.time())
def beat(markers, tag, name, seconds):
    end = time.time() + seconds
    while time.time() < end:
        log(markers, tag, name, 'beat')
        time.sleep(0.1)
'''
        child = base / 'child40.py'
        child.write_text(common + '''markers, tag, name, kind, hold = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
if kind == 'daemon':
    if os.fork():
        os._exit(0)
    os.setsid()
    if os.fork():
        os._exit(0)
elif kind in ('session', 'stubborn'):
    os.setsid()
elif kind == 'pgroup':
    os.setpgid(0, 0)
def on_term(signum, frame):
    log(markers, tag, name, 'term')
    if kind != 'stubborn':
        os._exit(143)
def on_usr1(signum, frame):
    log(markers, tag, name, 'usr1')
    os._exit(0)
signal.signal(signal.SIGTERM, on_term)
signal.signal(signal.SIGUSR1, on_usr1)
if kind == 'alloc':
    mark(markers, tag, name, facts(name))
    block = bytearray(int(hold) * 1024 * 1024)
    for i in range(0, len(block), 4096):
        block[i] = 1
    mark(markers, tag, name + '.allocated', {'bytes': len(block)})
    time.sleep(5)
    sys.exit(0)
if kind == 'burn':
    mark(markers, tag, name, facts(name))
    end = time.time() + hold
    while time.time() < end:
        pass
    mark(markers, tag, name + '.burned', {'cpu': time.process_time()})
    sys.exit(0)
mark(markers, tag, name, facts(name))
beat(markers, tag, name, hold)
''')
        engine = base / 'engine40.py'
        engine.write_text(common + '''import subprocess
markers = sys.argv[1]
dispatch = os.environ.get('VELDO_DISPATCH_ID', '')
tag = dispatch.rsplit('/', 1)[-1]
raw = sys.stdin.buffer.read()
payload = (json.loads(raw) if raw.strip() else {}).get('payload') or {}
children = []
def on_term(signum, frame):
    log(markers, tag, 'worker', 'term')
    if payload.get('on_term') == 'flush':
        # A cooperative adapter: it ends what it started itself, flushes and exits 0.
        for proc in children:
            proc.send_signal(signal.SIGUSR1)
        for proc in children:
            proc.wait()
        mark(markers, tag, 'flushed', {'at': time.time()})
        os._exit(0)
    if payload.get('on_term') != 'ignore':
        os._exit(143)
signal.signal(signal.SIGTERM, on_term)
own = facts('worker')
own.update(dispatch=dispatch, environment={k: os.environ.get(k) for k in ('V40_OWNER', 'VELDO_DISPATCH_ID')})
if payload.get('write_bytes'):
    try:
        with open(Path(markers) / (tag + '.big'), 'wb') as handle:
            handle.write(b'x' * payload['write_bytes'])
        own['write'] = 'written'
    except OSError as error:
        own['write'] = 'refused:' + str(error.errno)
    own['written'] = (Path(markers) / (tag + '.big')).stat().st_size
for name, kind, hold in payload.get('descendants') or []:
    children.append(subprocess.Popen([sys.executable, '-B', sys.argv[2], markers, tag, name, kind, str(hold)],
                                     stdin=subprocess.DEVNULL, stdout=None if kind == 'stubborn' else subprocess.DEVNULL))
mark(markers, tag, 'worker', own)
if payload.get('burn'):
    path = Path('/sys/fs/cgroup') / own['cgroup'].lstrip('/') / 'cpu.stat'
    before = dict(l.split() for l in path.read_text().splitlines())
    started, end = time.time(), time.time() + payload['burn']
    while time.time() < end:
        pass
    for proc in children:
        proc.wait()
    after = dict(l.split() for l in path.read_text().splitlines())
    mark(markers, tag, 'cpu', {'wall': time.time() - started, 'usage_usec': int(after['usage_usec']) - int(before['usage_usec']),
                               'nr_throttled': int(after['nr_throttled']) - int(before['nr_throttled'])})
if payload.get('say'):
    sys.stdout.write(payload['say'])
    sys.stdout.flush()
if payload.get('beat'):
    beat(markers, tag, 'worker', payload['hold'])
else:
    end = time.time() + payload.get('hold', 0)
    while time.time() < end and not (payload.get('release') and Path(payload['release']).exists()):
        time.sleep(0.02)
for proc in children:
    if payload.get('wait_children'):
        proc.wait()
mark(markers, tag, 'exit', {'at': time.time()})
sys.exit(payload.get('code', 0))
''')

        def profile(**changes):
            value = {'kind': 'linux-systemd', 'slice': slices[0], 'lock': str(base / 'a.lock'), 'concurrency': 16,
                     'runtime_seconds': 60, 'memory_bytes': 256 << 20, 'cpu_percent': 150, 'file_bytes': 8 << 20,
                     'tasks_max': 128, 'stop_grace_seconds': 0.6, 'kill_grace_seconds': 0.6}
            value.update(changes)
            return {k: v for k, v in value.items() if v is not None}

        os.environ['V40_OWNER'] = 'owner-session'
        adapters = {'engine': {'argv': [sys.executable, '-B', str(engine), str(markers), str(child)]}}
        configs = {}

        def config(name, prof, **extra):
            path = base / ('receiver-%s.json' % name)
            body = {'store': str(db), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
                    'workspace': str(base), 'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1,
                    'adapters': adapters}
            if prof is not None:
                body['profile'] = prof
            body.update(extra)
            path.write_text(json.dumps(body))
            configs[name] = path
            return path

        MAIN = profile()
        config('main', MAIN)
        config('memory', profile(memory_bytes=64 << 20))
        config('cpu', profile(cpu_percent=30))
        config('runtime', profile(runtime_seconds=1.2, kill_grace_seconds=0.5))
        config('concurrency', profile(slice=slices[1], lock=str(base / 'b.lock'), concurrency=2))
        gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
        launches, runners = [], {}

        def runner(name):
            if name not in runners:
                def receive(contract, path=configs[name]):
                    launch = L.invoke(path, contract, dispatches, accept_seconds=20)
                    launches.append(launch)
                    return launch
                runners[name] = L.Runner(gate, reservations, dispatches, receive, account=ACCOUNT)
            return runners[name]

        releases = []

        def job(deadline=60, **payload):
            if payload.get('release'):
                payload['release'] = str(base / ('release-' + payload['release']))
                releases.append(Path(payload['release']))
            return dict(holder=HOLDER, source=str(src), revision='HEAD', payload=payload, adapter='engine',
                        configuration={'tools': ['Read', 'Bash'], 'model': 'configured-model'},
                        deadline=time.time() + deadline)

        def release(launch):
            path = Path((rec(launch.dispatch_id).get('contract') or {}).get('input', {}).get('payload', {}).get('release', ''))
            if path.name:
                path.write_text('go')

        def rec(dispatch_id):
            return dispatches.record(dispatch_id) or {}

        def tag(launch):
            return launch.dispatch_id.rsplit('/', 1)[-1]

        def marker(launch, name, timeout=10.0):
            path = markers / ('%s.%s' % (tag(launch), name))
            end = time.time() + timeout
            while not path.exists() and time.time() < end:
                time.sleep(0.02)
            return json.loads(path.read_text()) if path.exists() else {}

        def times(launch, name, what):
            path = markers / ('%s.%s.%s' % (tag(launch), name, what))
            return [float(x) for x in path.read_text().split()] if path.exists() else []

        def proc_start(pid):
            try:
                stat = Path('/proc/%d/stat' % pid).read_text()
                return stat[stat.rindex(')') + 2:].split()[19]
            except (OSError, ValueError, IndexError, TypeError):
                return None

        def living(facts):
            return bool(facts) and proc_start(facts.get('pid') or 0) == facts.get('start')

        def cgroup_of(pid):
            try:
                text = Path('/proc/%d/cgroup' % pid).read_text()
            except (OSError, TypeError):
                return None
            return next((line[3:] for line in text.splitlines() if line.startswith('0::')), None)

        def read(path):
            try:
                return Path(path).read_text().strip()
            except OSError:
                return None

        def group_path(cgroup):
            return Path('/sys/fs/cgroup') / str(cgroup or '/nonexistent').lstrip('/')

        def procs(cgroup):
            return sorted(int(x) for x in (read(group_path(cgroup) / 'cgroup.procs') or '').split())

        def slot(launch):
            return (entity(RES.entity('worker', [DOMAIN, launch.dispatch_id])) or {}).get('data') or {}

        def states(launch):
            return [h.get('state') for h in rec(launch.dispatch_id).get('history', [])]

        def emptied(cgroup):
            """The group is gone or reports nothing left in it (systemd removes the directory just after)."""
            events = read(group_path(cgroup) / 'cgroup.events')
            return bool(cgroup) and (events is None or 'populated 0' in events.splitlines())

        def wakes_of(pid):
            """How many times the process's main thread has slept and been woken (voluntary switches)."""
            text = read('/proc/%d/task/%d/status' % (pid, pid)) or ''
            return next((int(line.split()[1]) for line in text.splitlines()
                         if line.startswith('voluntary_ctxt_switches')), None)

        def span(text):
            """Microseconds in a span as systemctl prints it (1.500000s, 500ms, 1min); None otherwise."""
            units = {'us': 1, 'ms': 10 ** 3, 's': 10 ** 6, 'min': 6 * 10 ** 7, 'h': 36 * 10 ** 8}
            total = 0.0
            for token in (text or 'infinity').split():
                number = token.rstrip('abcdefghijklmnopqrstuvwxyz')
                if token[len(number):] not in units or not number:
                    return None
                total += float(number) * units[token[len(number):]]
            return round(total)

        def status_of(pid):
            try:
                return dict(line.split(':\t', 1) for line in Path('/proc/%d/status' % pid).read_text().splitlines()
                            if ':\t' in line)
            except OSError:
                return {}

        emitted, raised, regions, observed = set(), [], [], {}

        def check(label, condition):
            emitted.add(label)
            expect('VELDO-0040 ' + label, bool(condition))

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

        started = {}
        try:
            # Started first, checked later: the runtime cap and the idle receiver run beside the rest. A
            # raise here leaves `started` short, which reds the rows that read it.
            with contextlib.suppress(Exception):
                started['runtime'] = (time.time(), runner('runtime').submit(admitted('VELDO-9420'), 'build', **job(
                    descendants=[['stubborn', 'stubborn', 10]], hold=10, beat=True)))
                started['idle'] = runner('main').submit(admitted('VELDO-9421'), 'build', **job(hold=8, release='idle'))

            # AC1: the worker and its ordinary descendants in the dispatch's own group
            with region('containment/dedicated-group', 'containment/ordinary-exit'):
                u1, u2 = admitted('VELDO-9401'), admitted('VELDO-9402')
                kinds = [['child', 'child', 20], ['session', 'session', 20], ['daemon', 'daemon', 20],
                         ['pgroup', 'pgroup', 20]]
                one = runner('main').submit(u1, 'build', **job(descendants=kinds, hold=30, release='u1'))
                two = runner('main').submit(u2, 'build', **job(descendants=[['child', 'child', 0.2]], hold=0.5,
                                                              wait_children=True))
                seen = {name: marker(one, name) for name in ['worker'] + [k[0] for k in kinds]}
                other = marker(two, 'worker')
                unit = C.unit_name(one.dispatch_id)
                cgroup = cgroup_of((seen['worker'] or {}).get('pid'))
                shown = show(unit, 'ControlGroup', 'Slice', 'Description', 'ActiveState')
                live = {name: dict(f, cgroup_now=cgroup_of(f.get('pid')), status=status_of(f.get('pid') or 0))
                        for name, f in seen.items()}
                members = procs(cgroup)
                record = rec(one.dispatch_id)
                process = record.get('process') or {}
                me = [str(os.getuid())] * 4, [str(os.getgid())] * 4
                qualification = C.qualify(MAIN)
                identity = qualification.get('identity') or {}
                observed['group'] = {'unit': unit, 'cgroup': cgroup, 'systemd': shown, 'members': members,
                                     'processes': {n: {k: f.get(k) for k in ('pid', 'sid', 'pgid', 'cgroup_now', 'uid', 'caps',
                                                                             'fsize')} for n, f in live.items()},
                                     'reported': getattr(one, 'group', None), 'other': other.get('cgroup'),
                                     'identity': identity}
                sessions = {f.get('sid') for f in seen.values()}
                check('containment/dedicated-group',
                      one.result == 'accepted' and all(seen.values()) and len(seen) == 5
                      and cgroup == shown.get('ControlGroup') and cgroup.endswith('/' + slices[0] + '/' + unit)
                      and shown.get('Slice') == slices[0] and shown.get('Description') == 'Veldo dispatch ' + one.dispatch_id
                      and all(f['cgroup'] == cgroup and f['cgroup_now'] == cgroup for f in live.values())
                      and members == sorted(f['pid'] for f in live.values())
                      and len(sessions) == 3 and len({f.get('pgid') for f in seen.values()}) == 4
                      and process.get('pid') == seen['worker']['pid'] and process.get('start') == seen['worker']['start']
                      and seen['worker']['ppid'] == one.child.pid
                      and seen['worker']['fsize'] == [8 << 20, 8 << 20]
                      and (getattr(one, 'group', None) or {}).get('cgroup') == cgroup
                      and (getattr(one, 'group', None) or {}).get('unit') == unit
                      and bool(other) and other.get('cgroup') not in (None, cgroup)
                      and other.get('cgroup', '').endswith('/' + C.unit_name(two.dispatch_id))
                      and all(f['uid'] == me[0] and f['gid'] == me[1] and set(f['caps'].values()) == {'0000000000000000'}
                              for f in live.values())
                      and identity.get('worker_uid') == os.getuid() and identity.get('privileged_helper') is False)

                # The worker's exit ends its dispatch: the four descendants still running are ended with it,
                # and the exit is recorded only once the group is empty.
                release(one)
                ended = runner('main').wait(one) or {}
                gone = {name: living(f) for name, f in seen.items()}
                slot_one = slot(one)
                ended_two = runner('main').wait(two) or {}
                observed['ordinary_exit'] = {'state': ended.get('state'), 'termination': ended.get('termination'),
                                             'supervision': getattr(one, 'supervision', None), 'alive_after': gone,
                                             'group_after': read(group_path(cgroup) / 'cgroup.events'),
                                             'retirement': slot_one.get('retirement'),
                                             'two': [ended_two.get('state'), getattr(two, 'supervision', None)]}
                supervision = getattr(one, 'supervision', None) or {}
                check('containment/ordinary-exit',
                      ended.get('state') == 'exited' and (ended.get('termination') or {}).get('returncode') == 0
                      and ended.get('process') == record.get('process') and not any(gone.values())
                      and emptied(cgroup) and supervision.get('empty') is True
                      and supervision.get('cause') == 'exit'
                      and [s['step'] for s in supervision.get('steps', [])][:1] == ['terminate']
                      and slot_one.get('retired') is True and (slot_one.get('retirement') or {}).get('cleaned') is True
                      and ((slot_one.get('retirement') or {}).get('group') or {}).get('observed') in ('absent', 'unpopulated')
                      and ended_two.get('state') == 'exited' and (getattr(two, 'supervision', None) or {}).get('steps') == []
                      and (ended_two.get('termination') or {}).get('returncode') == 0)

            # AC1 and AC2: an unqualified profile is refused before anything is spawned
            with region('containment/unqualified-profile-refused', 'containment/required-settings-refused'):
                idle = started.get('idle')
                idle_facts = marker(idle, 'worker') if idle else {}
                counted = [(time.time(), wakes_of(idle.child.pid))] if idle else []
                u3 = admitted('VELDO-9403')
                cases = {
                    'absent': (None, 'invalid_input:profile:absent'),
                    'unknown_setting': (profile(memory_limit=1 << 20), 'invalid_input:profile:unknown:memory_limit'),
                    'required_absent': (profile(memory_bytes=None), 'invalid_input:profile:memory_bytes:absent'),
                    'invalid_value': (profile(runtime_seconds=0), 'invalid_input:profile:runtime_seconds:invalid'),
                    'other_host_kind': (profile(kind='darwin-launchd'), 'unavailable_service:profile:kind'),
                    'missing_systemd_run': (profile(systemd_run=str(base / 'no-systemd-run')),
                                            'unavailable_service:profile:systemd_run'),
                }
                refusals = {}
                for name, (prof, expected) in cases.items():
                    config('refuse-' + name, prof)
                    try:
                        launch = runner('refuse-' + name).submit(u3, 'build', **job(hold=5))
                    except D.Refused as error:
                        # The unit is still held by a worker an earlier case launched: nothing was refused here.
                        refusals[name] = {'expected': expected, 'refusal': 'runner:' + error.code}
                        continue
                    refusals[name] = {'expected': expected, 'refusal': rec(launch.dispatch_id).get('refusal'),
                                      'states': states(launch), 'worker': bool(marker(launch, 'worker', timeout=0.05)),
                                      'unit': show(C.unit_name(launch.dispatch_id), 'LoadState').get('LoadState'),
                                      'retired': slot(launch).get('retired')}
                if idle:
                    # The idle receiver is watched for at least 1.5 s, longer than any periodic wake of 1 s.
                    time.sleep(max(0.0, counted[0][0] + 1.5 - time.time()))
                    counted.append((time.time(), wakes_of(idle.child.pid)))
                observed['unqualified'] = refusals
                check('containment/unqualified-profile-refused',
                      all(r['refusal'] == r['expected'] and r.get('states') == ['prepared', 'refused'] and not r.get('worker')
                          and r.get('unit') == 'not-found' and r.get('retired') is True for r in refusals.values()))
                # Every required setting of the profile schema, absent and with each invalid value of its kind,
                # is refused by the qualification the receiver runs before acceptance; the spec's five are
                # among them.
                invalid = {'count': [0, -1, 1.5, True, '2'], 'seconds': [0, -1, float('inf'), True, '1'],
                           'bytes': [0, 1, -4096, True, 4096.0], 'percent': [0, -5, 10 ** 6, True, 1.5]}
                matrix, required = {}, sorted(n for n, r in C.SETTINGS.items() if r.get('required'))
                for name, rule in sorted(C.SETTINGS.items()):
                    outcomes = []
                    if rule.get('required'):
                        outcomes.append((None, C.qualify(profile(**{name: None})).get('refusal')))
                    for value in invalid.get(rule.get('kind'), [None]):
                        outcomes.append((repr(value), C.qualify(profile(**{name: value})).get('refusal')))
                    matrix[name] = outcomes
                observed['required_settings'] = {'required': required, 'matrix': matrix,
                                                 'qualified': C.qualify(MAIN).get('qualified')}
                check('containment/required-settings-refused',
                      {'concurrency', 'runtime_seconds', 'memory_bytes', 'cpu_percent', 'file_bytes'} <= set(required)
                      and C.qualify(MAIN).get('qualified') is True
                      and all(outcomes and all(code == 'invalid_input:profile:%s:%s' % (name, 'absent' if v is None else 'invalid')
                                               for v, code in outcomes)
                              for name, outcomes in matrix.items())
                      and all(matrix[name][0] == (None, 'invalid_input:profile:%s:absent' % name) for name in required)
                      and refusals.get('required_absent', {}).get('refusal') == 'invalid_input:profile:memory_bytes:absent'
                      and refusals.get('invalid_value', {}).get('refusal') == 'invalid_input:profile:runtime_seconds:invalid')

            # AC3: the receiver sleeps until an OS notification; an exit is seen when it happens
            with region('containment/exit-notified'):
                idle = started['idle']
                release(idle)
                ended = runner('main').wait(idle) or {}
                exit_at = marker(idle, 'exit').get('at')
                recorded_at = next((h['at'] for h in ended.get('history', []) if h.get('state') == 'exited'), None)
                window = counted[-1][0] - counted[0][0] if len(counted) == 2 else 0
                wakes = counted[-1][1] - counted[0][1] if len(counted) == 2 else None
                observed['exit_notified'] = {'window_seconds': round(window, 2), 'receiver_wakes': wakes,
                                             'exit_at': exit_at, 'recorded_at': recorded_at,
                                             'latency': round(recorded_at - exit_at, 3) if exit_at and recorded_at else None,
                                             'idle_worker_alive_in_window': bool(idle_facts)}
                check('containment/exit-notified',
                      ended.get('state') == 'exited' and bool(idle_facts) and window >= 1.5 and wakes == 0
                      and exit_at is not None and recorded_at is not None
                      and 0 <= recorded_at - exit_at < 0.75)

            # AC2: every declared cap installed before the worker runs, and holding against real descendants
            with region('containment/caps-installed'):
                u4, u5, u6 = admitted('VELDO-9404'), admitted('VELDO-9405'), admitted('VELDO-9406')
                memory = runner('memory').submit(u5, 'build', **job(descendants=[['alloc', 'alloc', 160]], hold=3))
                burning = runner('cpu').submit(u6, 'build', **job(descendants=[['burn', 'burn', 1.0]], burn=1.0))
                held = runner('main').submit(u4, 'build', **job(descendants=[['child', 'child', 20]], hold=30,
                                                               release='u4', write_bytes=(8 << 20) + 65536))
                facts = marker(held, 'worker')
                descendant = marker(held, 'child')
                path = group_path(cgroup_of(facts.get('pid')))
                shown = show(C.unit_name(held.dispatch_id), 'RuntimeMaxUSec', 'TimeoutStopUSec', 'OOMPolicy', 'KillMode')
                page = os.sysconf('SC_PAGE_SIZE')
                installed = {
                    'memory_bytes': [read(path / 'memory.max'), read(path / 'memory.swap.max'), shown.get('OOMPolicy')],
                    'cpu_percent': read(path / 'cpu.max'), 'tasks_max': read(path / 'pids.max'),
                    'runtime_seconds': span(shown.get('RuntimeMaxUSec')),
                    'kill_grace_seconds': [span(shown.get('TimeoutStopUSec')), shown.get('KillMode')],
                    'file_bytes': [facts.get('fsize'), descendant.get('fsize'), facts.get('write'), facts.get('written')],
                }
                declared = {
                    'memory_bytes': [str((256 << 20) // page * page), '0', 'stop'], 'cpu_percent': '150000 100000',
                    'tasks_max': '128', 'runtime_seconds': 60 * 10 ** 6, 'kill_grace_seconds': [600000, 'control-group'],
                    'file_bytes': [[8 << 20, 8 << 20], [8 << 20, 8 << 20], 'refused:27', 8 << 20],
                }
                # The concurrency cap, in a slice of its own with a cap of two.
                ca = runner('concurrency').submit(admitted('VELDO-9407'), 'build', **job(hold=30, release='ca'))
                cb = runner('concurrency').submit(admitted('VELDO-9408'), 'build', **job(hold=30, release='cb'))
                cc = runner('concurrency').submit(admitted('VELDO-9409'), 'build', **job(hold=1))
                release(ca)
                runner('concurrency').wait(ca)
                runner('concurrency').wait(cc)
                cd = runner('concurrency').submit(rec(cc.dispatch_id).get('contract', {}).get('unit', 'VELDO-9409'),
                                                  'build', **job(hold=0.2))
                live_groups = C.status(profile(slice=slices[1], lock=str(base / 'b.lock'), concurrency=2)).get('groups')
                release(cb)
                concurrency = {'first': ca.result, 'second': cb.result, 'third': [cc.result, rec(cc.dispatch_id).get('refusal'),
                                                                                    states(cc)],
                               'after_one_ended': cd.result, 'live_while_two_ran': live_groups}
                release(held)
                runner('main').wait(held)
                ended_memory = runner('memory').wait(memory) or {}
                ended_cpu = runner('cpu').wait(burning) or {}
                runner('concurrency').wait(cb)
                runner('concurrency').wait(cd)
                cpu = marker(burning, 'cpu')
                live = {
                    'memory_bytes': ended_memory.get('state') == 'exited'
                                    and (getattr(memory, 'supervision', None) or {}).get('cause') == 'memory_cap'
                                    and bool(marker(memory, 'alloc')) and not marker(memory, 'alloc.allocated', timeout=0.05)
                                    and not living(marker(memory, 'alloc')),
                    'cpu_percent': ended_cpu.get('state') == 'exited' and bool(cpu)
                                   and cpu.get('usage_usec', 10 ** 9) <= (0.30 + 0.1) * cpu.get('wall', 0) * 10 ** 6
                                   and cpu.get('nr_throttled', 0) >= 1,
                    'concurrency': ca.result == 'accepted' and cb.result == 'accepted' and cc.result == 'refused'
                                   and rec(cc.dispatch_id).get('refusal') == 'unavailable_service:concurrency'
                                   and states(cc) == ['prepared', 'accepted', 'refused']
                                   and not marker(cc, 'worker', timeout=0.05) and cd.result == 'accepted'
                                   and len(live_groups or []) == 2,
                    'file_bytes': facts.get('write') == 'refused:27' and facts.get('written') == 8 << 20,
                }
                statements = C.qualify(MAIN)
                settings = statements.get('settings') or {}
                rows = {}
                for name in C.SETTINGS:
                    if name in MAIN:
                        rows[name] = {'declared': declared.get(name), 'installed': installed.get(name),
                                      'mechanism': (settings.get(name) or {}).get('mechanism'),
                                      'live': live.get(name)}
                observed['caps'] = {'settings': rows, 'cpu': cpu, 'concurrency': concurrency,
                                    'memory': getattr(memory, 'supervision', None), 'unbounded': statements.get('unbounded')}
                check('containment/caps-installed',
                      set(rows) == set(MAIN) & set(C.SETTINGS) and len(rows) == 8
                      and all(r['installed'] == r['declared'] for n, r in rows.items() if n in declared)
                      and all(isinstance(r['mechanism'], str) and len(r['mechanism']) > 20 for r in rows.values())
                      and all(live.values()) and 'storage_total' in (statements.get('unbounded') or {}))

            # AC2: the elapsed-runtime cap ends a bounded live descendant that would outlast it
            with region('containment/runtime-cap'):
                began, capped = started['runtime']
                ended = runner('runtime').wait(capped) or {}
                stubborn = marker(capped, 'stubborn')
                beats = times(capped, 'stubborn', 'beat')
                running_at = next((h['at'] for h in ended.get('history', []) if h.get('state') == 'running'), None)
                supervision = getattr(capped, 'supervision', None) or {}
                observed['runtime_cap'] = {'state': ended.get('state'), 'termination': ended.get('termination'),
                                           'supervision': supervision, 'running_at': running_at,
                                           'last_beat_after_running': round(beats[-1] - running_at, 2) if beats and running_at else None,
                                           'terms': times(capped, 'stubborn', 'term'),
                                           'unit_after': show(C.unit_name(capped.dispatch_id), 'LoadState').get('LoadState')}
                check('containment/runtime-cap',
                      ended.get('state') == 'exited' and (ended.get('termination') or {}).get('deadline_stop') is True
                      and supervision.get('cause') == 'runtime_cap' and supervision.get('result') == 'timeout'
                      and bool(stubborn) and not living(stubborn) and bool(beats) and running_at is not None
                      and beats[-1] - running_at <= 1.2 + 0.5 + 1.0 and len(times(capped, 'stubborn', 'term')) >= 1
                      and supervision.get('empty') is True
                      and show(C.unit_name(capped.dispatch_id), 'LoadState').get('LoadState') == 'not-found')

            # AC3: a cooperative stop, and the escalation past a signal-ignoring descendant
            with region('containment/cooperative-stop', 'containment/stop-escalation'):
                u7, u8 = admitted('VELDO-9410'), admitted('VELDO-9411')
                polite = runner('main').submit(u7, 'build', **job(descendants=[['owned', 'child', 20]], hold=30,
                                                                  on_term='flush', deadline=4))
                owned = marker(polite, 'owned')
                asked_at = time.time()
                asked = getattr(polite, 'stop', lambda: False)()
                ended = runner('main').wait(polite) or {}
                supervision = getattr(polite, 'supervision', None) or {}
                slot_polite = slot(polite)
                observed['cooperative'] = {'asked': asked, 'state': ended.get('state'), 'termination': ended.get('termination'),
                                           'supervision': supervision, 'flushed': marker(polite, 'flushed', timeout=0.05),
                                           'owned_usr1': times(polite, 'owned', 'usr1'), 'owned_term': times(polite, 'owned', 'term'),
                                           'retirement': slot_polite.get('retirement')}
                check('containment/cooperative-stop',
                      asked is True and ended.get('state') == 'exited'
                      and (ended.get('termination') or {}).get('returncode') == 0
                      and (ended.get('termination') or {}).get('deadline_stop') is False
                      and bool(marker(polite, 'flushed', timeout=0.05)) and times(polite, 'worker', 'term')
                      and times(polite, 'worker', 'term')[0] >= asked_at
                      and times(polite, 'owned', 'usr1') and not times(polite, 'owned', 'term') and not living(owned)
                      and supervision.get('cause') == 'requested'
                      and [s['step'] for s in supervision.get('steps', [])] == ['cooperative']
                      and supervision.get('empty') is True and slot_polite.get('retired') is True
                      and (slot_polite.get('retirement') or {}).get('outcome') == 'cancelled'
                      and (slot_polite.get('retirement') or {}).get('cleaned') is True)

                stubborn = runner('main').submit(u8, 'build', **job(descendants=[['stubborn', 'stubborn', 20]], hold=20,
                                                                    beat=True, on_term='ignore', deadline=8))
                worker = marker(stubborn, 'worker')
                hidden = marker(stubborn, 'stubborn')
                running = rec(stubborn.dispatch_id)
                group = getattr(stubborn, 'group', None) or {}
                asked_at = time.time()
                asked = getattr(stubborn, 'stop', lambda: False)()
                ended = runner('main').wait(stubborn) or {}
                supervision = getattr(stubborn, 'supervision', None) or {}
                slot_stubborn = slot(stubborn)
                worker_terms, hidden_terms = times(stubborn, 'worker', 'term'), times(stubborn, 'stubborn', 'term')
                worker_beats, hidden_beats = times(stubborn, 'worker', 'beat'), times(stubborn, 'stubborn', 'beat')
                observed['escalation'] = {
                    'asked': asked, 'state': ended.get('state'), 'reason': ended.get('reason'),
                    'termination': ended.get('termination'), 'supervision': supervision,
                    'worker_terms': [round(t - asked_at, 2) for t in worker_terms],
                    'descendant_terms': [round(t - asked_at, 2) for t in hidden_terms],
                    'worker_last_beat': round(worker_beats[-1] - asked_at, 2) if worker_beats else None,
                    'descendant_last_beat': round(hidden_beats[-1] - asked_at, 2) if hidden_beats else None,
                    'descendant_alive_after': living(hidden), 'group_after': read(group_path(group.get('cgroup')) / 'cgroup.events'),
                    'retirement': slot_stubborn.get('retirement')}
                steps = {s['step']: s['at'] for s in supervision.get('steps', [])}
                check('containment/stop-escalation',
                      asked is True and ended.get('state') == 'exited' and bool(worker) and bool(hidden)
                      and ended.get('process') == running.get('process')
                      and (running.get('process') or {}).get('pid') == worker.get('pid')
                      and (running.get('process') or {}).get('start') == worker.get('start')
                      and (ended.get('termination') or {}).get('signal') == 9
                      and (ended.get('termination') or {}).get('deadline_stop') is False
                      and len(worker_terms) >= 2 and len(hidden_terms) >= 1
                      and worker_terms[0] >= asked_at and hidden_terms[0] - worker_terms[0] >= 0.6 - 0.1
                      and bool(hidden_beats) and hidden_beats[-1] - hidden_terms[0] >= 0.6 - 0.25
                      and hidden_beats[-1] - asked_at <= 0.6 + 0.6 + 1.5
                      and not living(hidden) and not living(worker) and emptied(group.get('cgroup'))
                      and list(steps) == ['cooperative', 'terminate', 'kill'] and supervision.get('empty') is True
                      and supervision.get('cause') == 'requested'
                      and supervision.get('group') == group and group.get('unit') == C.unit_name(stubborn.dispatch_id)
                      and slot_stubborn.get('retired') is True
                      and (slot_stubborn.get('retirement') or {}).get('outcome') == 'cancelled'
                      and (slot_stubborn.get('retirement') or {}).get('cleaned') is True
                      and (slot_stubborn.get('retirement') or {}).get('observed_at', 0) >= supervision.get('empty_at', 1e18))

            # AC3: the worker slot is returned only on the runner's own observation of an empty group
            with region('containment/retire-after-empty'):
                u9 = admitted('VELDO-9412')
                prepared = runner('main').prepare(u9, 'build', **job())
                unit = C.unit_name(prepared['dispatch_id'])
                holder = subprocess.Popen(['systemd-run', '--user', '--scope', '--quiet', '--unit=' + unit,
                                           '--slice=' + slices[0], '--', 'sleep', '30'], env=tools,
                                          stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                          stderr=subprocess.DEVNULL, start_new_session=True)
                end = time.time() + 10
                while cgroup_of(holder.pid) is None or not cgroup_of(holder.pid).endswith(unit):
                    if time.time() > end:
                        break
                    time.sleep(0.02)
                held_group = {'unit': unit, 'slice': slices[0], 'cgroup': cgroup_of(holder.pid)}
                probe = types.SimpleNamespace(group=held_group, stop_requested=False, supervision=None)
                pending = getattr(runner('main'), 'launches', {})
                pending[prepared['dispatch_id']] = probe
                runner('main').launches = pending
                refused = runner('main')._retire(prepared['dispatch_id'], 'cancelled', 'probe')
                still = entity(RES.entity('worker', [DOMAIN, prepared['dispatch_id']]))['data']
                with contextlib.suppress(OSError):
                    (group_path(held_group['cgroup']) / 'cgroup.kill').write_text('1')
                holder.wait(timeout=10)
                end = time.time() + 10
                while group_path(held_group['cgroup']).exists() and time.time() < end:
                    time.sleep(0.02)
                runner('main').launches[prepared['dispatch_id']] = probe
                retired = runner('main')._retire(prepared['dispatch_id'], 'cancelled', 'probe')
                after = entity(RES.entity('worker', [DOMAIN, prepared['dispatch_id']]))['data']
                observed['retire_after_empty'] = {'while_populated': [refused, still.get('retired')],
                                                  'after_empty': [retired, after.get('retired'), after.get('retirement')],
                                                  'runner_observations': runner('main').observations[-2:]}
                check('containment/retire-after-empty',
                      held_group['cgroup'] is not None and refused is False and still.get('retired') is False
                      and any(o.get('refusal') == 'cleanup_incomplete' for o in runner('main').observations[-2:])
                      and retired is True and after.get('retired') is True
                      and (after.get('retirement') or {}).get('cleaned') is True
                      and ((after.get('retirement') or {}).get('group') or {}).get('observed') in ('absent', 'unpopulated'))

            with region('containment/observations', 'containment/installed-assets'):
                seen_codes = [str(r['refusal']) for r in observed.get('unqualified', {}).values()]
                seen_codes.append(str(rec(cc.dispatch_id).get('refusal')))
                classes = {code: D.taxonomy(code) for code in seen_codes + ['containment_not_empty',
                                                                            'spawn_failed:containment:group']}
                expected_classes = {code: ('invalid_input' if code.startswith('invalid_input:') else
                                           'unknown_outcome' if code == 'containment_not_empty' else 'unavailable_service')
                                    for code in classes}
                trace = [m.get('event') for m in stubborn.messages]
                joined = (((stubborn.messages[1] if len(stubborn.messages) > 1 else {}).get('group') or {}).get('unit')
                          == C.unit_name(stubborn.dispatch_id)
                          == ((slot_stubborn.get('retirement') or {}).get('group') or {}).get('unit'))
                after = C.status(MAIN)
                observed['observations'] = {'taxonomy': classes, 'trace': trace, 'joined': joined,
                                            'pending_after': after.get('groups')}
                check('containment/observations',
                      classes == expected_classes and trace == ['accepted', 'running', 'exited'] and joined
                      and after.get('qualified') is True and after.get('groups') == []
                      and live_groups and all(g.get('description', '').startswith('Veldo dispatch dispatch/')
                                              for g in live_groups))
                scaffold = load('v40_scaffold', mods / 'init_scaffold.py')
                check('containment/installed-assets', '.veldo/control_containment.py' in scaffold._FILES
                      and '.veldo/control_launch.py' in scaffold._FILES)
        finally:
            for path in releases:
                with contextlib.suppress(OSError):
                    path.write_text('go')
            for launch in launches:
                with contextlib.suppress(Exception):
                    if launch.child.poll() is None:
                        launch.child.kill()
                    launch.child.wait(timeout=10)
                    launch.child.stdout.close()
                    launch.child.stdin.close()
            for name in slices:
                with contextlib.suppress(Exception):
                    systemctl('stop', name)
            # Whatever a defective build left running (a descendant that escaped its stop) is ended here.
            for leftover in sorted(markers.iterdir()):
                with contextlib.suppress(Exception):
                    facts = json.loads(leftover.read_text())
                    if living(facts):
                        os.kill(facts['pid'], signal.SIGKILL)
            writer.close()
            reader.close()
            os.environ.pop('V40_OWNER', None)
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V40_OBSERVED'] = observed


_v40_started = __import__('time').monotonic()
_v40_suite()
_V40_SECONDS = __import__('time').monotonic() - _v40_started
