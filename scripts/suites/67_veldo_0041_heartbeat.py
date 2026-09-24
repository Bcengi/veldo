"""VELDO-0041: the trusted wrapper's heartbeat independent of a blocked model call (in a session of its
own, on a channel the engine does not hold), the receiver's claim renewal and missed-heartbeat stop, the
bounded escalation of an accepted stop over the whole VELDO-0040 group, and a retirement that follows
actual termination, keeps each open obligation, is retried by the runner itself once an obligation is
completed and releases the capacity slot once, over real processes on this host. Every release reaches
the slot through the runner's production paths (submit, wait, its sweep, its teardown and its listener
on the reservation service); no row calls the runner's private retirement.

Only shared ROOT and expect are consumed. One temporary tree, in the owner's runtime directory so the
VELDO-0042 clone layout has no protected target beneath a temporary directory, holds the installed
.veldo copy the runner loads and the receiver, trusted wrapper and clone entrance execute, so a
registered mutation of a production module reaches all of them. Real SQLite store, OpenSSH journal
signatures, a Git source repository, VELDO-0052's eligibility Gate, VELDO-0036 reservations, the
VELDO-0031 claim transition, VELDO-0042 clones with their teardown, the owner's systemd user manager
(transient scopes in a slice of this run's own, stopped at its end) and the kernel's cgroup, pidfd and
/proc files. The worker is a fixture engine: its "model call" is a child it waits on with one blocking
read, and it starts cooperative and signal-ignoring descendants; it qualifies no live engine. The
shipped timings (ten-second heartbeat, thirty-second window, ten and five seconds of stop graces) are
asserted exactly as the profile's defaults and as a real receiver reports them; the timed rows drive
the same code with shorter configured values, record every monotonic time and assert the configured
values were the ones used.
"""


def _v41_suite():
    import contextlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import select
    import shutil
    import signal
    import subprocess
    import sys
    import tempfile
    import threading
    import time
    import types

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_heartbeat.py': ROOT / ".veldo" / "control_heartbeat.py",
        'control_retirement.py': ROOT / ".veldo" / "control_retirement.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_containment.py': ROOT / ".veldo" / "control_containment.py",
        'control_reservations.py': ROOT / ".veldo" / "control_reservations.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    # The declared measurement tolerance of every timed observation (a late wake of a loaded host).
    TOL = 0.35
    SHIPPED = {'heartbeat_seconds': 10, 'heartbeat_window_seconds': 30, 'stop_grace_seconds': 10,
               'kill_grace_seconds': 5}

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    run_id = os.urandom(4).hex()
    slice_name = 'v41%s.slice' % run_id
    tools = dict(os.environ)
    runtime = tools['XDG_RUNTIME_DIR']
    now_m = time.monotonic

    def systemctl(*args):
        return subprocess.run(['systemctl', '--user', *args], capture_output=True, text=True, timeout=20,
                              env=tools, stdin=subprocess.DEVNULL)

    def show(unit, *names):
        out = systemctl('show', *[a for n in names for a in ('-p', n)], unit).stdout
        return dict(line.split('=', 1) for line in out.splitlines() if '=' in line)

    with tempfile.TemporaryDirectory(prefix='v41-', dir=runtime if os.path.isdir(runtime) else None) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        S = load('v41_store', mods / 'control_store.py')
        L = load('v41_launch', mods / 'control_launch.py')
        C = load('v41_containment', mods / 'control_containment.py')
        HB = load('v41_heartbeat', mods / 'control_heartbeat.py')
        D = L.D
        EL = load('v41_eligibility', mods / 'control_eligibility.py')
        RES = load('v41_reservations', mods / 'control_reservations.py')
        RR = load('v41_reservation_runtime', mods / 'control_reservation_runtime.py')
        SIG = load('v41_signer', mods / 'control_signer.py')
        _git_process = load('v41_git', mods / 'git_process.py')
        CL = load('v41_clone', mods / 'control_clone.py') if (mods / 'control_clone.py').exists() else None
        CLM = D.CLM
        DOMAIN, REPOSITORY, ACCOUNT, HOLDER = 'domain-41', 'repository-41', 'acct-41', 'builder-1'
        GROUP = getattr(HB, 'GROUP', 'veldo-wrapper')
        state = base / 'state'
        private = state / 'keys'
        private.mkdir(parents=True, mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / 'journal')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        db = state / 'authority' / 'control.sqlite3'
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
        put('project:p1', 'project', dict(name='heartbeat'))
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

        home = base / 'home'
        (home / 'projects').mkdir(parents=True)
        src = home / 'projects' / 'source'
        _git_process.run(['git', 'init', '-q', str(src)], check=True, capture_output=True, stdin=subprocess.DEVNULL)
        (src / 'README').write_text('heartbeat source\n')
        _git_process.run(['git', '-C', str(src), 'add', 'README'], check=True, capture_output=True, stdin=subprocess.DEVNULL)
        _git_process.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
                         capture_output=True, identity=('Fixture', 'fixture@example.invalid'), stdin=subprocess.DEVNULL)

        # The fixture engine and its descendants. Each process writes <tag>.<name> with its pid, start
        # time and cgroup, and logs each SIGTERM it takes (and, when stubborn, a beat every 50 ms) as
        # monotonic times, the clock the receiver times its heartbeat and its stop on.
        markers = base / 'markers'
        markers.mkdir()
        common = '''import json, os, signal, sys, time
from pathlib import Path
def facts(role):
    stat = Path('/proc/self/stat').read_text()
    return {'role': role, 'pid': os.getpid(), 'start': stat[stat.rindex(')') + 2:].split()[19],
            'cgroup': next(l[3:] for l in Path('/proc/self/cgroup').read_text().splitlines() if l.startswith('0::')),
            'monotonic': time.monotonic()}
def mark(markers, tag, name, data):
    temporary = Path(markers) / ('%s.%s.%d.tmp' % (tag, name, os.getpid()))
    temporary.write_text(json.dumps(data))
    os.replace(temporary, Path(markers) / ('%s.%s' % (tag, name)))
def log(markers, tag, name, what):
    with open(Path(markers) / ('%s.%s.%s' % (tag, name, what)), 'a') as handle:
        handle.write('%r\\n' % time.monotonic())
'''
        child = base / 'child41.py'
        child.write_text(common + '''markers, tag, name, kind, hold = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
def on_term(signum, frame):
    log(markers, tag, name, 'term')
    if kind != 'stubborn':
        os._exit(143)
signal.signal(signal.SIGTERM, on_term)
mark(markers, tag, name, facts(name))
if kind == 'model':
    # The model: it answers after `hold` seconds.
    time.sleep(hold)
    sys.stdout.write('answer')
    sys.stdout.flush()
    sys.exit(0)
end = time.monotonic() + hold
while time.monotonic() < end:
    if kind == 'stubborn':
        log(markers, tag, name, 'beat')
    time.sleep(0.05)
''')
        engine = base / 'engine41.py'
        engine.write_text(common + '''import subprocess
markers, child = sys.argv[1], sys.argv[2]
dispatch = os.environ.get('VELDO_DISPATCH_ID', '')
tag = dispatch.rsplit('/', 1)[-1]
raw = sys.stdin.buffer.read()
payload = (json.loads(raw) if raw.strip() else {}).get('payload') or {}
def on_term(signum, frame):
    log(markers, tag, 'worker', 'term')
    if payload.get('on_term') != 'ignore':
        os._exit(143)
signal.signal(signal.SIGTERM, on_term)
children = [subprocess.Popen([sys.executable, '-B', child, markers, tag, name, kind, str(hold)], stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL) for name, kind, hold in payload.get('descendants') or []]
own = facts('worker')
own['cwd'] = os.getcwd()
mark(markers, tag, 'worker', own)
if payload.get('block'):
    # THE MODEL CALL: one blocking read of a child that answers after `block` seconds.
    model = subprocess.Popen([sys.executable, '-B', child, markers, tag, 'model', 'model', str(payload['block'])],
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE)
    mark(markers, tag, 'call', {'started': time.monotonic(), 'pid': model.pid})
    answer = model.stdout.read()
    model.wait()
    mark(markers, tag, 'answer', {'returned': time.monotonic(), 'bytes': len(answer)})
end = time.monotonic() + payload.get('hold', 0)
while time.monotonic() < end and not (payload.get('release') and Path(payload['release']).exists()):
    time.sleep(0.02)
if payload.get('signal_group'):
    # The engine signals its own process group, as an engine ending its own children does, and lives on.
    mark(markers, tag, 'signalled', {'at': time.monotonic(), 'pgrp': os.getpgrp()})
    os.killpg(0, signal.SIGTERM)
    time.sleep(payload['signal_group'])
mark(markers, tag, 'exit', {'at': time.monotonic()})
sys.exit(payload.get('code', 0))
''')

        def profile(**changes):
            value = {'kind': 'linux-systemd', 'slice': slice_name, 'lock': str(base / 'slice.lock'), 'concurrency': 16,
                     'runtime_seconds': 120, 'memory_bytes': 256 << 20, 'cpu_percent': 200, 'file_bytes': 8 << 20,
                     'tasks_max': 128, 'stop_grace_seconds': 0.5, 'kill_grace_seconds': 0.5}
            value.update(changes)
            return {k: v for k, v in value.items() if v is not None}

        engine_argv = [sys.executable, '-B', str(engine), str(markers), str(child)]
        adapters = {'engine': {'argv': engine_argv}}
        configs = {}

        def config(name, prof, adapter_table=None):
            path = base / ('receiver-%s.json' % name)
            path.write_text(json.dumps({'store': str(db), 'journal_key': str(private / 'journal'),
                                        'principal': 'launch-receiver', 'workspace': str(base), 'domain': DOMAIN,
                                        'repository': REPOSITORY, 'authority_generation': 1,
                                        'adapters': adapter_table or adapters, 'profile': prof}))
            configs[name] = path
            return path

        # The configured values the timed rows drive, each different from the shipped default.
        FAST = profile(heartbeat_seconds=0.25, heartbeat_window_seconds=1.0, stop_grace_seconds=0.4, kill_grace_seconds=0.4)
        SHIPPED_PROFILE = profile(stop_grace_seconds=None, kill_grace_seconds=None)
        ESCALATE = profile(stop_grace_seconds=1.0, kill_grace_seconds=0.5)
        LINGER = profile(stop_grace_seconds=0.3, kill_grace_seconds=2.0)
        MAIN = profile()
        for name, prof in (('fast', FAST), ('shipped', SHIPPED_PROFILE), ('escalate', ESCALATE), ('linger', LINGER),
                           ('main', MAIN)):
            config(name, prof)
        gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign)
        launches, runners = [], {}

        def receive_with(path):
            def receive(contract):
                launch = L.invoke(path, contract, dispatches, accept_seconds=20)
                launches.append(launch)
                return launch
            return receive

        def runner(name, receive=None, **extra):
            if name not in runners:
                receive = receive or receive_with(configs[name])
                try:
                    runners[name] = L.Runner(gate, reservations, dispatches, receive, account=ACCOUNT, **extra)
                except TypeError:
                    # A runner that takes no clone provisioner retires without one.
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

        def rec(dispatch_id):
            return dispatches.record(dispatch_id) or {}

        def release(launch):
            path = Path((rec(launch.dispatch_id).get('contract') or {}).get('input', {}).get('payload', {}).get('release', ''))
            if path.name:
                path.write_text('go')

        def tag(launch):
            return launch.dispatch_id.rsplit('/', 1)[-1]

        def marker(launch, name, timeout=10.0):
            path = markers / ('%s.%s' % (tag(launch), name))
            if getattr(launch, 'result', None) != 'accepted':
                timeout = 0.05  # nothing of a launch that was not accepted is waited for
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

        def read(path):
            try:
                return Path(path).read_text().strip()
            except OSError:
                return None

        def group_path(cgroup):
            return Path('/sys/fs/cgroup') / str(cgroup or '/nonexistent').lstrip('/')

        def procs(cgroup):
            return sorted(int(x) for x in (read(group_path(cgroup) / 'cgroup.procs') or '').split())

        def slot_entity(dispatch_id):
            return RES.entity('worker', [DOMAIN, dispatch_id])

        def slot(dispatch_id):
            return (entity(slot_entity(dispatch_id)) or {}).get('data') or {}

        def retired_commits(dispatch_id):
            """Journal records whose transition writes this slot as retired: exactly one per release."""
            key = slot_entity(dispatch_id)
            found = []
            for seq, transition in writer.execute('SELECT seq, transition FROM journal ORDER BY seq').fetchall():
                written = json.loads(transition).get(key)
                if written and (written.get('data') or {}).get('retired') is True:
                    found.append(seq)
            return found

        def capacity(unit):
            return reservations.balances('unit', unit)['capacity']

        def links(pid):
            """What each open descriptor of process `pid` refers to, read from /proc by this suite."""
            found = []
            with contextlib.suppress(OSError, TypeError):
                for name in os.listdir('/proc/%d/fd' % pid):
                    with contextlib.suppress(OSError):
                        found.append(os.readlink('/proc/%d/fd/%s' % (pid, name)))
            return sorted(found)

        def events(name, dispatch_id, since=0):
            """The retirement events one runner recorded for one dispatch, from index `since` of its list."""
            listed = getattr(runners.get(name), 'observations', None) or []
            return [dict(e) for e in listed[since:] if e.get('operation') == 'retire' and e.get('dispatch_id') == dispatch_id]

        def heartbeats(dispatch_id):
            return writer.execute('SELECT command_id, principal FROM journal WHERE command_id LIKE ? ORDER BY seq',
                                  ('heartbeat/' + dispatch_id + '/%',)).fetchall()

        def claim_version(unit):
            return (entity(CLM.claim_id(REPOSITORY, unit)) or {}).get('version')

        def retirements(name):
            return getattr(runners.get(name), 'retirements', None)

        def pending(name):
            service = retirements(name)
            return service.pending() if service is not None else {}

        def deaths(facts_list, seconds=20.0):
            """Watch processes end through pidfds opened while they run: {pid: [monotonic, wall]}."""
            fds, seen = {}, {}
            for facts in facts_list:
                with contextlib.suppress(OSError, TypeError):
                    fd = os.pidfd_open(facts['pid'])
                    if proc_start(facts['pid']) == facts.get('start'):
                        fds[fd] = facts['pid']
                    else:
                        os.close(fd)

            def run():
                poller = select.poll()
                for fd in fds:
                    poller.register(fd, select.POLLIN)
                end, left = now_m() + seconds, set(fds)
                while left and now_m() < end:
                    for fd, _ in poller.poll(100):
                        seen[fds[fd]] = [now_m(), time.time()]
                        poller.unregister(fd)
                        left.discard(fd)
                for fd in fds:
                    os.close(fd)
            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            return seen, thread

        def wait_for(predicate, seconds=10.0):
            end = time.time() + seconds
            while time.time() < end:
                if predicate():
                    return True
                time.sleep(0.02)
            return bool(predicate())

        def within(value, low, high):
            return isinstance(value, (int, float)) and low <= value <= high

        def minus(a, b):
            """a - b of two observed times; NaN (never within any bound) when either is absent."""
            number = (int, float)
            return a - b if isinstance(a, number) and isinstance(b, number) and not isinstance(a, bool) else float('nan')

        emitted, raised, regions, observed = set(), [], [], {}

        def check(label, condition):
            emitted.add(label)
            expect('VELDO-0041 ' + label, bool(condition))

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

        started, made = {}, []
        try:
            # Started first, examined later, so they run beside one another. A raise here leaves `started`
            # short, which reds the rows that read it.
            with contextlib.suppress(Exception):
                units = {name: admitted(unit) for name, unit in (('blocked', 'VELDO-9501'), ('missing', 'VELDO-9502'),
                                                                 ('shipped', 'VELDO-9503'), ('orphan', 'VELDO-9508'),
                                                                 ('signal', 'VELDO-9511'))}
                claims = {name: claim_version(unit) for name, unit in units.items()}
                started['blocked'] = runner('fast').submit(units['blocked'], 'build', **job(block=2.0))
                started['missing'] = runner('fast').submit(units['missing'], 'build', **job(block=8))
                started['shipped'] = runner('shipped').submit(units['shipped'], 'build', **job(block=1.5))
                started['orphan'] = runner('main').submit(units['orphan'], 'build', **job(hold=30))
                # Waits for its release, then signals its own process group and runs two seconds more.
                started['signal'] = runner('fast').submit(units['signal'], 'build', **job(
                    hold=30, release='signal', signal_group=2.0, on_term='ignore'))

            # AC1: the heartbeat comes from the trusted wrapper while the model call is still blocked, and
            # each one renews the claim.
            with region('heartbeat/blocked-call-liveness'):
                blocked = started['blocked']
                call, answer = marker(blocked, 'call'), marker(blocked, 'answer', timeout=15)
                ended = runner('fast').wait(blocked) or {}
                supervision = getattr(blocked, 'supervision', None) or {}
                beat = supervision.get('heartbeat') or {}
                recent = beat.get('recent') or []
                inside = [b for b in recent if call.get('started', 1e18) <= b['taken'] <= answer.get('returned', 0)]
                gaps = [round(b['taken'] - a['taken'], 3) for a, b in zip(inside, inside[1:])]
                sent = [round(b['sent'] - a['sent'], 3) for a, b in zip(recent, recent[1:])]
                renewals = heartbeats(blocked.dispatch_id)
                claimed = claim_version(units['blocked'])
                observed['blocked_call'] = {
                    'configured': getattr(blocked, 'heartbeat', None), 'call': call, 'answer': answer,
                    'blocked_seconds': round(minus(answer.get('returned'), call.get('started')), 3),
                    'beats': beat.get('beats'), 'beats_during_call': len(inside), 'taken_gaps_during_call': gaps,
                    'sent_intervals': sent, 'renewed': beat.get('renewed'), 'renewal_refusals': beat.get('renewal_refusals'),
                    'claim_version': [claims['blocked'], claimed], 'journal_renewals': len(renewals),
                    'liveness': beat.get('liveness'), 'state': ended.get('state'), 'termination': ended.get('termination'),
                    'cause': supervision.get('cause'), 'heartbeat_pid': beat.get('pid'), 'worker_pid': marker(blocked, 'worker').get('pid')}
                check('heartbeat/blocked-call-liveness',
                      getattr(blocked, 'heartbeat', None) == {'interval_seconds': 0.25, 'window_seconds': 1.0}
                      and minus(answer.get('returned'), call.get('started')) >= 1.9
                      and len(inside) >= 7 and bool(gaps) and max(gaps) <= 0.25 + TOL
                      and all(b.get('renewed') is True for b in inside)
                      and bool(sent) and all(within(x, 0.25 - 0.05, 0.25 + TOL) for x in sent)
                      and beat.get('pid') not in (None, marker(blocked, 'worker').get('pid'))
                      and beat.get('liveness') == 'live' and beat.get('uncertain_at') is None
                      and beat.get('renewed') == beat.get('beats') and beat.get('renewal_refusals') == []
                      and minus(claimed, claims['blocked']) == beat.get('renewed') and len(renewals) == beat.get('renewed')
                      and all(principal == 'launch-receiver' for _, principal in renewals)
                      and ended.get('state') == 'exited' and (ended.get('termination') or {}).get('returncode') == 0
                      and supervision.get('cause') is None and slot(blocked.dispatch_id).get('retired') is True)

            # AC1: a worker whose heartbeats stop for the configured window is stopped.
            with region('heartbeat/missing-heartbeat-stop'):
                missing = started['missing']
                worker = marker(missing, 'worker')
                cgroup = (getattr(missing, 'group', None) or {}).get('cgroup')
                renewed_three = wait_for(lambda: len(heartbeats(missing.dispatch_id)) >= 3, 10)
                beaters = procs(str(cgroup) + '/' + GROUP) if cgroup else []
                stopped_at = now_m()
                for pid in beaters:
                    os.kill(pid, signal.SIGSTOP)  # the wrapper's heartbeat stops answering
                ended = runner('fast').wait(missing) or {}
                supervision = getattr(missing, 'supervision', None) or {}
                beat = supervision.get('heartbeat') or {}
                steps = supervision.get('steps') or []
                terms = times(missing, 'worker', 'term')
                lapse = minus(beat.get('uncertain_at'), beat.get('last'))
                observed['missing_heartbeat'] = {
                    'configured': getattr(missing, 'heartbeat', None), 'heartbeat_pids': beaters, 'sigstop_at': stopped_at,
                    'beats': beat.get('beats'), 'last_taken': beat.get('last'), 'uncertain_at': beat.get('uncertain_at'),
                    'lapse_after_last': round(lapse, 3), 'steps': steps, 'worker_terms': terms,
                    'cause': supervision.get('cause'), 'liveness': beat.get('liveness'), 'state': ended.get('state'),
                    'termination': ended.get('termination'), 'empty': supervision.get('empty'),
                    'retired': slot(missing.dispatch_id).get('retired')}
                check('heartbeat/missing-heartbeat-stop',
                      renewed_three and bool(beaters) and bool(worker) and beat.get('beats', 0) >= 3
                      and supervision.get('cause') == 'heartbeat_missing' and beat.get('liveness') == 'uncertain'
                      and (beat.get('last') or 1e18) <= stopped_at + 0.3
                      and within(lapse, 1.0, 1.0 + TOL)
                      and [s.get('step') for s in steps][:1] == ['cooperative']
                      and within(minus(steps[0].get('monotonic'), beat.get('uncertain_at')), 0, 0.05)
                      and bool(terms) and within(minus(terms[0], beat.get('uncertain_at')), -0.01, TOL)
                      and not living(worker) and all(proc_start(pid) is None for pid in beaters)
                      and ended.get('state') == 'exited' and supervision.get('empty') is True
                      and slot(missing.dispatch_id).get('retired') is True)

            # AC1: the engine never holds the heartbeat channel. Its open descriptors, read from /proc while it
            # runs, include no end of the one pipe the heartbeat writes and the receiver reads.
            with region('heartbeat/channel-not-held'):
                signalled = started['signal']
                worker = marker(signalled, 'worker')
                cgroup = (getattr(signalled, 'group', None) or {}).get('cgroup')
                beating = wait_for(lambda: len(heartbeats(signalled.dispatch_id)) >= 2, 10)
                beaters = procs(str(cgroup) + '/' + GROUP) if cgroup else []
                held = {pid: links(pid) for pid in beaters}
                channels = sorted({link for found in held.values() for link in found if link.startswith('pipe:')})
                engine_links = links(worker.get('pid'))
                receiver_links = links(getattr(getattr(signalled, 'child', None), 'pid', None))
                observed['channel'] = {'heartbeat_pids': beaters, 'heartbeat_descriptors': held, 'channels': channels,
                                       'engine_pid': worker.get('pid'), 'engine_descriptors': engine_links,
                                       'receiver_holds_channel': bool(channels) and channels[0] in receiver_links}
                check('heartbeat/channel-not-held',
                      beating and living(worker) and len(beaters) == 1 and len(channels) == 1
                      and channels[0].startswith('pipe:[') and len(channels[0]) > len('pipe:[]')
                      and channels[0] in receiver_links
                      and any(link.startswith('pipe:') for link in engine_links)
                      and channels[0] not in engine_links)

            # AC1: an engine that signals its own process group leaves the heartbeat beating: the heartbeat has
            # a session and group of its own, so the worker is never stopped as heartbeat_missing for it.
            with region('heartbeat/engine-group-signal'):
                signalled = started['signal']
                worker = marker(signalled, 'worker')
                cgroup = (getattr(signalled, 'group', None) or {}).get('cgroup')
                before = procs(str(cgroup) + '/' + GROUP) if cgroup else []
                release(signalled)
                sent = marker(signalled, 'signalled')
                ended = runner('fast').wait(signalled) or {}
                supervision = getattr(signalled, 'supervision', None) or {}
                beat = supervision.get('heartbeat') or {}
                recent = beat.get('recent') or []
                at = sent.get('at')
                after = [b for b in recent if isinstance(at, (int, float)) and b['taken'] > at]
                spanning = [b for b in recent if isinstance(at, (int, float)) and b['taken'] > at - 0.5]
                gaps = [round(b['taken'] - a['taken'], 3) for a, b in zip(spanning, spanning[1:])]
                terms = times(signalled, 'worker', 'term')
                observed['group_signal'] = {'signalled': sent, 'engine_pgrp_is_its_pid': sent.get('pgrp') == worker.get('pid'),
                                            'heartbeat_pids': before, 'beats_after_signal': len(after),
                                            'gaps_around_signal': gaps, 'engine_terms': terms, 'heartbeat_pid': beat.get('pid'),
                                            'cause': supervision.get('cause'), 'liveness': beat.get('liveness'),
                                            'state': ended.get('state'), 'termination': ended.get('termination')}
                check('heartbeat/engine-group-signal',
                      bool(sent) and sent.get('pgrp') == worker.get('pid') and len(before) == 1
                      and bool(terms) and within(minus(terms[0], at), 0, TOL)
                      and len(after) >= 6 and bool(gaps) and max(gaps) <= 0.25 + TOL
                      and beat.get('pid') == before[0] and beat.get('liveness') == 'live' and beat.get('uncertain_at') is None
                      and supervision.get('cause') is None and ended.get('state') == 'exited'
                      and (ended.get('termination') or {}).get('returncode') == 0
                      and slot(signalled.dispatch_id).get('retired') is True)

            # AC1 and AC2: the shipped values exactly, and the timed rows used their configured ones.
            with region('heartbeat/shipped-defaults'):
                shipped = started['shipped']
                ended = runner('shipped').wait(shipped) or {}
                supervision = getattr(shipped, 'supervision', None) or {}
                beat = supervision.get('heartbeat') or {}
                running = next((m for m in shipped.messages if m.get('event') == 'running'), {})
                defaults = {name: (C.SETTINGS.get(name) or {}).get('default') for name in SHIPPED}
                qualified = {name: ((C.qualify(SHIPPED_PROFILE).get('settings') or {}).get(name) or {}).get('value')
                             for name in SHIPPED}
                observed['shipped'] = {'defaults': defaults, 'qualified': qualified, 'running': running,
                                       'beats': beat.get('beats'),
                                       'first_after_release': round(minus(beat.get('first'), beat.get('released')), 3),
                                       'state': ended.get('state'),
                                       'configured_runs': {'blocked': observed.get('blocked_call', {}).get('configured'),
                                                           'missing': observed.get('missing_heartbeat', {}).get('configured')}}
                check('heartbeat/shipped-defaults',
                      defaults == SHIPPED and qualified == SHIPPED
                      and running.get('heartbeat') == {'interval_seconds': 10, 'window_seconds': 30}
                      and running.get('graces') == {'stop_grace_seconds': 10, 'kill_grace_seconds': 5}
                      and beat.get('beats') == 1 and within(minus(beat.get('first'), beat.get('released')), 0, 1.0)
                      and beat.get('liveness') == 'live' and ended.get('state') == 'exited'
                      and observed.get('blocked_call', {}).get('configured') == {'interval_seconds': 0.25, 'window_seconds': 1.0}
                      and observed.get('missing_heartbeat', {}).get('configured') == {'interval_seconds': 0.25,
                                                                                     'window_seconds': 1.0}
                      and C.qualify(profile(heartbeat_seconds=2, heartbeat_window_seconds=2)).get('refusal')
                      == 'invalid_input:profile:heartbeat_window_seconds:invalid')

            # AC2: an accepted stop terminates the whole group after the stop grace and kills what remains
            # after the kill grace.
            with region('stop/bounded-group-exit'):
                unit = admitted('VELDO-9504')
                target = runner('escalate').submit(unit, 'build', **job(
                    descendants=[['coop', 'coop', 30], ['stubborn', 'stubborn', 30]], hold=30, on_term='ignore'))
                worker, coop, stubborn = marker(target, 'worker'), marker(target, 'coop'), marker(target, 'stubborn')
                seen, watcher = deaths([worker, coop, stubborn])
                wait_for(lambda: len(times(target, 'stubborn', 'beat')) >= 3, 5)
                asked_at = now_m()
                asked = getattr(target, 'stop', lambda: False)()
                ended = runner('escalate').wait(target) or {}
                watcher.join(timeout=10)
                supervision = getattr(target, 'supervision', None) or {}
                at = {s.get('step'): s.get('monotonic') for s in supervision.get('steps') or []}
                w_terms, c_terms = times(target, 'worker', 'term'), times(target, 'coop', 'term')
                s_terms, s_beats = times(target, 'stubborn', 'term'), times(target, 'stubborn', 'beat')
                died = {name: (seen.get(f.get('pid')) or [None])[0] for name, f in
                        (('worker', worker), ('coop', coop), ('stubborn', stubborn))}
                c0, t0, k0 = (at.get(k) if isinstance(at.get(k), (int, float)) else float('nan')
                              for k in ('cooperative', 'terminate', 'kill'))

                def rel(value):
                    return round(value - asked_at, 3) if isinstance(value, (int, float)) else None
                observed['escalation'] = {
                    'tolerance_seconds': TOL, 'configured': supervision.get('graces'), 'asked': asked,
                    'steps': {k: rel(v) for k, v in at.items()}, 'worker_terms': [rel(t) for t in w_terms],
                    'coop_terms': [rel(t) for t in c_terms], 'stubborn_terms': [rel(t) for t in s_terms],
                    'stubborn_last_beat': rel(s_beats[-1]) if s_beats else None,
                    'died': {k: rel(v) for k, v in died.items()},
                    'empty_at': rel(supervision.get('empty_monotonic')), 'state': ended.get('state'),
                    'termination': ended.get('termination'), 'cause': supervision.get('cause')}
                check('stop/bounded-group-exit',
                      asked is True and bool(worker) and bool(coop) and bool(stubborn)
                      and supervision.get('graces') == {'stop_grace_seconds': 1.0, 'kill_grace_seconds': 0.5}
                      and list(at) == ['cooperative', 'terminate', 'kill'] and supervision.get('cause') == 'requested'
                      and within(minus(c0, asked_at), 0, TOL) and within(minus(t0, c0), 1.0, 1.0 + TOL)
                      and within(minus(k0, t0), 0.5, 0.5 + TOL)
                      # the requested stop reaches the worker alone first, then termination reaches the group
                      and len(w_terms) >= 2 and within(minus(w_terms[0], c0), -0.01, TOL)
                      and within(minus(w_terms[1], t0), -0.01, TOL)
                      and len(c_terms) == 1 and within(minus(c_terms[0], t0), -0.01, TOL)
                      and within(minus(died['coop'], c_terms[0]), 0, TOL) and minus(k0, died['coop']) > 0
                      and len(s_terms) == 1 and within(minus(s_terms[0], t0), -0.01, TOL)
                      and bool(s_beats) and minus(s_beats[-1], t0) >= 0.5 - 0.15
                      and within(minus(died['stubborn'], k0), 0, TOL) and within(minus(died['worker'], k0), 0, TOL)
                      and within(minus(supervision.get('empty_monotonic'), k0), 0, TOL)
                      and supervision.get('empty') is True and ended.get('state') == 'exited'
                      and (ended.get('termination') or {}).get('signal') == 9
                      and (ended.get('termination') or {}).get('deadline_stop') is False
                      and slot(target.dispatch_id).get('retired') is True)

            # AC3: retirement follows the actual end of the whole group, not the worker's own exit, and a
            # refused retirement is retried by the runner itself once its group has ended.
            with region('retirement/live-descendant'):
                # A launch whose refusal reports its group while a process it left is still in the dispatch's own
                # scope: the receiver seam hands the runner that report (a receiver that could not start, as
                # VELDO-0039's invoke settles it, with the group a refusal reports, as VELDO-0040's does). Only
                # the runner's own kernel observation stands between that report and the release.
                planted = {}

                def linger_receive(contract):
                    if not contract['input']['payload'].get('plant'):
                        return receive_with(configs['linger'])(contract)
                    scope = C.unit_name(contract['dispatch_id'])
                    made.append(scope)
                    holder = subprocess.Popen(['systemd-run', '--user', '--scope', '--quiet', '--unit=' + scope,
                                               '--slice=' + slice_name, '--', 'sleep', '30'], env=tools,
                                              stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                              stderr=subprocess.DEVNULL, start_new_session=True)
                    wait_for(lambda: (C.cgroup_of(holder.pid) or '').endswith(scope), 10)
                    planted.update(holder=holder, facts={'pid': holder.pid, 'start': proc_start(holder.pid)},
                                   group={'unit': scope, 'slice': slice_name, 'cgroup': C.cgroup_of(holder.pid)})
                    launch = L.invoke(base / 'receiver-absent.json', contract, dispatches, accept_seconds=20)
                    launch.group = planted['group']
                    launches.append(launch)
                    return launch
                lingerer = runner('linger', receive=linger_receive)
                planted_unit = admitted('VELDO-9506')
                planted_launch = lingerer.submit(planted_unit, 'build', **job(plant=True))
                planted_id = planted_launch.dispatch_id
                planted_first = events('linger', planted_id)
                planted_held = slot(planted_id).get('retired')
                unit = admitted('VELDO-9505')
                capacity_before = capacity(unit)
                # Its preparation sweeps the pending retirements: the planted group is still populated, so
                # nothing it waits on has changed and nothing is attempted.
                lingering = lingerer.submit(unit, 'build', **job(descendants=[['stubborn', 'stubborn', 30]], hold=30))
                planted_at_submit = {'alive': living(planted.get('facts')), 'pending': pending('linger').get(planted_id),
                                     'events': len(events('linger', planted_id))}
                worker, stubborn = marker(lingering, 'worker'), marker(lingering, 'stubborn')
                seen, watcher = deaths([worker, stubborn, planted.get('facts') or {'pid': None}])
                wait_for(lambda: len(times(lingering, 'stubborn', 'beat')) >= 3, 5)
                asked = getattr(lingering, 'stop', lambda: False)()
                # The worker ends on the cooperative stop; its signal-ignoring descendant lives on until the kill.
                wait_for(lambda: worker.get('pid') in seen, 5)
                # The process left in the planted group ends; the runner is not told.
                cgroup = (planted.get('group') or {}).get('cgroup')
                with contextlib.suppress(OSError):
                    (group_path(cgroup) / 'cgroup.kill').write_text('1')
                with contextlib.suppress(Exception):
                    planted['holder'].wait(timeout=10)
                wait_for(lambda: not group_path(cgroup).exists(), 10)
                mark = len(lingerer.observations)
                ended = lingerer.wait(lingering) or {}
                watcher.join(timeout=10)
                during_wait = [(e['dispatch_id'], e['outcome'], e.get('basis')) for e in lingerer.observations[mark:]
                               if e.get('operation') == 'retire']
                retirement = slot(lingering.dispatch_id).get('retirement') or {}
                planted_retirement = slot(planted_id).get('retirement') or {}
                death, planted_death = seen.get(stubborn.get('pid')), seen.get((planted.get('facts') or {}).get('pid'))
                commits = retired_commits(lingering.dispatch_id)
                mark = len(lingerer.observations)
                again_record = lingerer.wait(lingering) or {}
                again = events('linger', lingering.dispatch_id, mark)
                observed['live_descendant'] = {
                    'planted': {'group': planted.get('group'), 'first': planted_first, 'held_after_submit': planted_held,
                                'at_next_submit': planted_at_submit, 'died': planted_death,
                                'retirement_observed_at': planted_retirement.get('observed_at'),
                                'retirement_group': planted_retirement.get('group'),
                                'retirement_basis': planted_retirement.get('basis'),
                                'commits': retired_commits(planted_id)},
                    'asked': asked, 'state': ended.get('state'), 'descendant_died': death,
                    'retirement_observed_at': retirement.get('observed_at'), 'retirement_group': retirement.get('group'),
                    'retirements_during_wait': during_wait, 'release_commits': commits,
                    'second_wait': {'state': again_record.get('state'), 'events': again},
                    'capacity': [capacity_before, capacity(unit)]}
                check('retirement/live-descendant',
                      planted.get('group', {}).get('cgroup') is not None and len(planted_first) == 1
                      and planted_first[0].get('outcome') == 'refused' and planted_first[0].get('basis') == 'never_spawned'
                      and planted_first[0].get('refusal') == 'cleanup_incomplete'
                      and planted_first[0].get('observed') == 'populated'
                      and planted_first[0].get('open', [])[:1] == ['group'] and planted_held is False
                      and planted_at_submit['alive'] is True and planted_at_submit['events'] == 1
                      and (planted_at_submit['pending'] or {}).get('open', [])[:1] == ['group']
                      and during_wait == [(lingering.dispatch_id, 'retired', 'worker_reaped'), (planted_id, 'retired', 'sweep')]
                      and bool(planted_death) and minus(planted_retirement.get('observed_at'), planted_death[1]) >= 0
                      and (planted_retirement.get('group') or {}).get('observed') in ('absent', 'unpopulated')
                      and len(retired_commits(planted_id)) == 1
                      and asked is True and ended.get('state') == 'exited' and bool(death)
                      and minus(retirement.get('observed_at'), death[1]) >= 0 and retirement.get('cleaned') is True
                      and (retirement.get('group') or {}).get('observed') in ('absent', 'unpopulated')
                      and len(commits) == 1 and again_record.get('state') == 'exited'
                      and [(e.get('outcome'), e.get('refusal')) for e in again] == [('refused', 'already_retired')]
                      and retired_commits(lingering.dispatch_id) == commits and capacity(unit) == capacity_before)

            # AC3: a model call with no final report keeps the slot until its accounting is complete, and the
            # final report landing on the reservation service is what retries the retirement.
            with region('retirement/missing-accounting'):
                unit = admitted('VELDO-9507')
                capacity_before = capacity(unit)
                accounted = runner('main').submit(unit, 'build', **job(hold=30, release='accounting'))
                marker(accounted, 'worker')
                invocation = 'invocation/' + tag(accounted)
                capacity_running = capacity(unit)
                # The adapter's side of the model call: VELDO-0036's InvocationGuard over the same reservation
                # service, reserving at its initial boundary and reporting the call's usage.
                launched, stops = [], []
                guard = RR.InvocationGuard(reservations, 'claude_code', lambda call, configuration: launched.append(call),
                                           stops.append)
                guard.invoke('call/' + invocation, accounted.dispatch_id, invocation, 'initial', 60,
                             {'tools': ['Read', 'Bash'], 'model': 'configured-model'}, now=time.time())
                release(accounted)
                ended = runner('main').wait(accounted) or {}
                first = events('main', accounted.dispatch_id)
                held = slot(accounted.dispatch_id).get('retired')
                waiting = pending('main').get(accounted.dispatch_id)
                mark = len(runner('main').observations)
                reported = guard.observe('report/' + invocation, invocation, 1, {'invocations': 1, 'wall_seconds': 1.5},
                                         now=time.time(), final=True, outcome='completed')
                # Read before the runner is called again: the release came with the report.
                at_report = slot(accounted.dispatch_id).get('retired')
                with_report = events('main', accounted.dispatch_id, mark)
                retirement = slot(accounted.dispatch_id).get('retirement') or {}
                commits = retired_commits(accounted.dispatch_id)
                mark = len(runner('main').observations)
                again_record = runner('main').wait(accounted) or {}
                again = events('main', accounted.dispatch_id, mark)
                observed['missing_accounting'] = {
                    'state': ended.get('state'), 'first': first, 'held': held, 'pending': waiting,
                    'report': {k: reported.get(k) for k in ('replayed', 'stop_required')},
                    'released_with_report': at_report, 'events_with_report': with_report,
                    'retained': retirement.get('retained'), 'basis': retirement.get('basis'),
                    'obligations': retirement.get('obligations'), 'commits': commits,
                    'second_wait': {'state': again_record.get('state'), 'events': again},
                    'commits_after_second_wait': retired_commits(accounted.dispatch_id),
                    'launched': launched, 'stops': stops,
                    'capacity': [capacity_before, capacity_running, capacity(unit)]}
                check('retirement/missing-accounting',
                      ended.get('state') == 'exited' and launched == [invocation] and stops == []
                      and len(first) == 1 and first[0].get('refusal') == 'missing_accounting' and held is False
                      and first[0].get('open', [])[:1] == ['accounting'] and (waiting or {}).get('open') == ['accounting']
                      and at_report is True
                      and [(e.get('outcome'), e.get('basis')) for e in with_report] == [('retired', 'accounting_reported')]
                      and retirement.get('basis') == 'accounting_reported' and len(commits) == 1
                      and again_record.get('state') == 'exited'
                      and [(e.get('outcome'), e.get('refusal')) for e in again] == [('refused', 'already_retired')]
                      and retired_commits(accounted.dispatch_id) == commits
                      and (retirement.get('retained') or {}).get('accounting_unknown') == {invocation: ['messages', 'tokens']}
                      and ((retirement.get('obligations') or {}).get('accounting') or {}).get('open') is False
                      and capacity_running == capacity_before + 1 and capacity(unit) == capacity_before
                      and accounted.dispatch_id not in pending('main'))

            # AC3: the clone files are removed through VELDO-0042's teardown before the slot is released, and the
            # teardown that removes them is what retries the retirement waiting on them.
            with region('retirement/clone-files'):
                clone_state = {}
                if CL is None:
                    raise RuntimeError('control_clone.py (VELDO-0042) is not installed')
                S.bind_repositories(writer, DOMAIN, {REPOSITORY: str(src)})
                provisioner = CL.Clones(dispatches, clones=str(state / 'clones'), caches=str(state / 'caches'),
                                        protected=[str(private)])
                config('clone', MAIN, {'engine': {'argv': provisioner.adapter(engine_argv)}})
                shared_clone = {}

                def clone_receive(contract):
                    # The runner's receiver seam composed with the provisioner, as VELDO-0129 wires it: the first
                    # dispatch's clone is created, and the second dispatch is attached to it as its consumer.
                    if 'handle' in shared_clone:
                        provisioner.attach(shared_clone['handle'].env_id, contract)
                    else:
                        shared_clone['handle'] = provisioner.create(contract)
                    return receive_with(configs['clone'])(contract)
                cloned = runner('clone', receive=clone_receive, clones=provisioner)
                owner_unit, consumer_unit = admitted('VELDO-9509'), admitted('VELDO-9510')
                owner = cloned.submit(owner_unit, 'build', **job(hold=0.3))
                handle = shared_clone['handle']
                root = Path(handle.paths['root'])
                consumer = cloned.submit(consumer_unit, 'build', **job(hold=30, release='consumer'))
                owner_worker, consumer_worker = marker(owner, 'worker'), marker(consumer, 'worker')
                # The owner ends while its consumer still runs in the clone: its retirement is refused.
                ended = cloned.wait(owner) or {}
                first = events('clone', owner.dispatch_id)
                held = slot(owner.dispatch_id).get('retired')
                files_while_held = root.exists()
                waiting = pending('clone').get(owner.dispatch_id)
                # The consumer ends; its own retirement removes the clone every user of which has ended.
                release(consumer)
                mark = len(cloned.observations)
                consumer_ended = cloned.wait(consumer) or {}
                during_wait = [(e['dispatch_id'], e['outcome'], e.get('basis'), (e.get('clone') or {}).get('removed_by'))
                               for e in cloned.observations[mark:] if e.get('operation') == 'retire']
                files_after_consumer = root.exists()
                retirement = slot(owner.dispatch_id).get('retirement') or {}
                commits = [retired_commits(owner.dispatch_id), retired_commits(consumer.dispatch_id)]
                mark = len(cloned.observations)
                again_record = cloned.wait(owner) or {}
                again = events('clone', owner.dispatch_id, mark)
                pins = []
                for cache in sorted((state / 'caches').glob('*.git')):
                    listed = _git_process.run(['git', '-C', str(cache), 'for-each-ref', 'refs/veldo/pins/'],
                                              capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout
                    pins += [line for line in listed.splitlines() if line.strip()]
                clone_state = {
                    'clone_id': handle.env_id, 'owner_cwd': owner_worker.get('cwd'), 'consumer_cwd': consumer_worker.get('cwd'),
                    'owner_state': ended.get('state'), 'first': first, 'held': held, 'files_while_held': files_while_held,
                    'pending': waiting, 'consumer_state': consumer_ended.get('state'),
                    'retirements_during_consumer_wait': during_wait, 'files_after_consumer': files_after_consumer,
                    'owner_basis': retirement.get('basis'), 'clone_obligation': (retirement.get('obligations') or {}).get('clone'),
                    'second_wait': {'state': again_record.get('state'), 'events': again},
                    'pins_left': pins, 'commits': commits,
                    'provisioner_events': [{k: e.get(k) for k in ('operation', 'outcome', 'refusal', 'dispatch_id')}
                                           for e in provisioner.observations]}
                observed['clone_files'] = clone_state
                check('retirement/clone-files',
                      owner_worker.get('cwd') == str(root / 'work') and consumer_worker.get('cwd') == str(root / 'work')
                      and ended.get('state') == 'exited' and len(first) == 1
                      and first[0].get('refusal') == 'cleanup_incomplete:clone'
                      and (first[0].get('clone') or {}).get('refusal') == 'clone_in_use'
                      and held is False and files_while_held is True and (waiting or {}).get('open') == ['clone']
                      and consumer_ended.get('state') == 'exited'
                      and during_wait == [(consumer.dispatch_id, 'retired', 'worker_reaped', consumer.dispatch_id),
                                          (owner.dispatch_id, 'retired', 'clone_removed', consumer.dispatch_id)]
                      and files_after_consumer is False and retirement.get('basis') == 'clone_removed'
                      and ((retirement.get('obligations') or {}).get('clone') or {}).get('present') is False
                      and pins == [] and [len(c) for c in commits] == [1, 1]
                      and again_record.get('state') == 'exited'
                      and [(e.get('outcome'), e.get('refusal')) for e in again] == [('refused', 'already_retired')]
                      and retired_commits(owner.dispatch_id) == commits[0])

            # AC3: an unknown outcome is kept: the slot stays held even once everything of the worker ended. The
            # runner's sweep retries the retirement once its group has ended, and then leaves it alone.
            with region('retirement/unknown-outcome'):
                orphan = started['orphan']
                worker = marker(orphan, 'worker')
                cgroup = (getattr(orphan, 'group', None) or {}).get('cgroup')
                orphan.child.kill()  # the receiver ends without recording how the dispatch ended
                orphan.child.wait(timeout=10)
                ended = runner('main').wait(orphan, timeout=5) or {}
                first = events('main', orphan.dispatch_id)
                alive_then = living(worker)
                with contextlib.suppress(OSError):
                    (group_path(cgroup) / 'cgroup.kill').write_text('1')
                wait_for(lambda: not living(worker) and not group_path(cgroup).exists(), 10)
                # The next two preparations each sweep: the first finds the termination and group completed and
                # tries again; the second finds nothing changed and tries nothing.
                mark = len(runner('main').observations)
                runner('main').prepare(admitted('VELDO-9512'), 'build', **job())
                swept = events('main', orphan.dispatch_id, mark)
                mark = len(runner('main').observations)
                runner('main').prepare(admitted('VELDO-9513'), 'build', **job())
                swept_again = events('main', orphan.dispatch_id, mark)
                observed['unknown_outcome'] = {'state': ended.get('state'), 'reason': ended.get('reason'), 'first': first,
                                               'alive_at_first': alive_then, 'swept': swept, 'swept_again': swept_again,
                                               'pending': pending('main').get(orphan.dispatch_id),
                                               'slot_retired': slot(orphan.dispatch_id).get('retired'),
                                               'commits': retired_commits(orphan.dispatch_id)}
                check('retirement/unknown-outcome',
                      ended.get('state') == 'unknown' and alive_then is True and len(first) == 1
                      and first[0].get('refusal') == 'worker_alive' and first[0].get('basis') == 'outcome_unknown'
                      and [(e.get('outcome'), e.get('basis'), e.get('refusal'), e.get('open')) for e in swept]
                      == [('refused', 'sweep', 'outcome_unknown', ['outcome'])]
                      and swept_again == [] and not living(worker)
                      and (pending('main').get(orphan.dispatch_id) or {}).get('open') == ['outcome']
                      and slot(orphan.dispatch_id).get('retired') is False and retired_commits(orphan.dispatch_id) == [])

            with region('retirement/observations', 'retirement/installed-assets'):
                every = [e for name in sorted(runners) for e in runners[name].observations if e.get('operation') == 'retire']
                fields = ('schema', 'domain', 'repository', 'unit', 'dispatch_id', 'request', 'accepted_versions',
                          'outcome', 'open')
                refused = [e for e in every if e.get('outcome') == 'refused']
                classes = {e['refusal']: e.get('taxonomy') for e in refused}
                expected = {'cleanup_incomplete': 'stale_subject', 'already_retired': 'stale_subject',
                            'missing_accounting': 'missing_evidence', 'cleanup_incomplete:clone': 'stale_subject',
                            'worker_alive': 'stale_subject', 'outcome_unknown': 'unknown_outcome'}
                status = getattr(retirements('main'), 'status', lambda: {})()
                observed['observations'] = {'events': len(every), 'refusal_classes': classes, 'status': status,
                                            'sample': every[:1]}
                check('retirement/observations',
                      bool(every) and all(all(f in e for f in fields) for e in every)
                      and all(e['request'] == 'retire/' + e['dispatch_id'] and e['unit'] for e in every)
                      and all(e.get('refusal') and e.get('taxonomy') for e in refused)
                      and {k: classes.get(k) for k in expected} == expected
                      and status.get('accepted', 0) >= 1 and status.get('refused', 0) >= 1 and status.get('retried', 0) >= 1
                      and list((status.get('pending') or {})) == [started['orphan'].dispatch_id])
                scaffold = load('v41_scaffold', mods / 'init_scaffold.py')
                check('retirement/installed-assets', '.veldo/control_heartbeat.py' in scaffold._FILES
                      and '.veldo/control_retirement.py' in scaffold._FILES and '.veldo/control_launch.py' in scaffold._FILES)
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
            with contextlib.suppress(Exception):
                systemctl('stop', slice_name)
            # A scope a defective build left populated ends failed when its slice stops; this run's own are
            # cleared so nothing it made stays loaded.
            mine = sorted({C.unit_name(launch.dispatch_id) for launch in launches if hasattr(launch, 'dispatch_id')}
                          | set(made))
            with contextlib.suppress(Exception):
                loaded = [line.split()[0] for line in systemctl('list-units', '--all', '--plain', '--no-legend',
                                                                *mine).stdout.splitlines() if line.split()]
                if loaded:
                    systemctl('reset-failed', *loaded)
            # Whatever a defective build left running (a descendant that escaped its stop) is ended here.
            for leftover in sorted(markers.iterdir()):
                with contextlib.suppress(Exception):
                    facts = json.loads(leftover.read_text())
                    if living(facts):
                        os.kill(facts['pid'], signal.SIGKILL)
            writer.close()
            reader.close()
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V41_OBSERVED'] = observed


_v41_started = __import__('time').monotonic()
# The owner's session. The gate's mutation stage runs every suite without XDG_RUNTIME_DIR; the receiver, its
# systemd tools and this suite's own systemctl reach the user manager through /run/user/<uid> for this run.
_v41_session = __import__('os').environ.get('XDG_RUNTIME_DIR')
__import__('os').environ['XDG_RUNTIME_DIR'] = _v41_session or '/run/user/%d' % __import__('os').getuid()
try:
    _v41_suite()
finally:
    if _v41_session is None:
        __import__('os').environ.pop('XDG_RUNTIME_DIR', None)
    else:
        __import__('os').environ['XDG_RUNTIME_DIR'] = _v41_session
_V41_SECONDS = __import__('time').monotonic() - _v41_started
