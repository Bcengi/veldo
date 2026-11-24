"""VELDO-0039: durable dispatch contracts, launch results and bound observations, over a real store.

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy the
runner loads AND the receiver process executes, so a registered mutation of either production
module reaches both. Real SQLite store, OpenSSH journal signatures, a real Git source repository,
VELDO-0052's eligibility Gate, VELDO-0036 reservations, the VELDO-0031 claim transition, and real
receiver and worker processes whose OS identity is read back from /proc. The worker is a fixture
engine (it reports its birth acceptance digest, proves the store read is denied, prints claims and exits); it
qualifies no live engine.
"""


def _v39_suite():
    import contextlib
    import datetime
    import hashlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import signal
    import subprocess
    import sys
    import tempfile
    import threading

    # VELDO-0358: this suite blocks only through the wait primitive (WAITS) and names no duration but the two hang
    # bounds. The wall time it hands the product as data is the support module's stamp.
    def now():
        """The wall time now, as data (a record's time, a deadline the product judges): the support stamp's."""
        return datetime.datetime.fromisoformat(WAITS.stamp().iso().replace('Z', '+00:00')).timestamp()

    def joined(thread, what):
        """A thread joined under the wait hang bound; past it the row is hung, never read as ended."""
        thread.join(timeout=WAITS.WAIT_HANG_SECONDS)
        if thread.is_alive():
            here = sys._getframe(1)
            WAITS.hung(WAITS.next_row(here, what), what, '%s:%d' % (here.f_code.co_filename, here.f_lineno),
                       'thread %s still alive after the wait hang bound' % thread.name)

    # Literal anchors: the registered mutation driver substitutes each production copy here.
    PRODUCTION = {
        'control_dispatch.py': ROOT / ".veldo" / "control_dispatch.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    fast = fast_temp()
    with tempfile.TemporaryDirectory(prefix='v39-', dir=os.environ.get('VELDO_FIXTURE_ROOT', '/var/lib/veldo')) as directory:
        base = Path(directory)
        mods = base / 'installed' / '.veldo'
        mods.mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        S = load('v39_store', mods / 'control_store.py')
        # The runner raises the dispatch module IT loaded; the suite uses that same instance.
        L = load('v39_launch', mods / 'control_launch.py')
        D = L.D
        # VELDO-0358 AC15: the timers profile. Every entry of the timers table is at the wait hang bound in this
        # process, in the receiver (its configuration) and in the wrapper (the receiver passes it on); no row of this
        # suite tests a table timer, so none is excepted.
        TIMERS = L.TIMERS
        TIMERS.set_profile(None, hang_seconds=WAITS.WAIT_HANG_SECONDS)
        TIMERS_PROFILE = {'except': None, 'hang_seconds': WAITS.WAIT_HANG_SECONDS}
        # The supplied clock and the check request of the receiver (control_launch, VELDO-0358 C4) are honoured
        # only under the test harness.
        harness = os.environ.get('VELDO_CONTROL_TEST_HARNESS')
        os.environ['VELDO_CONTROL_TEST_HARNESS'] = '1'
        EL = load('v39_eligibility', mods / 'control_eligibility.py')
        RES = load('v39_reservations', mods / 'control_reservations.py')
        SIG = load('v39_signer', mods / 'control_signer.py')
        GP = load('v39_git', mods / 'git_process.py')
        CLM = D.CLM
        DOMAIN, REPOSITORY, ACCOUNT, HOLDER = 'domain-39', 'repository-39', 'acct-39', 'builder-1'
        private = base / 'private'
        private.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / 'journal')],
                       check=True, capture_output=True, timeout=WAITS.WAIT_HANG_SECONDS,
                       stdin=subprocess.DEVNULL)

        def sign(data):
            return SIG.sign_bytes(private / 'journal', data, 'veldo-journal')

        # A variable of the owner's session: the receiver and the worker it launches inherit it.
        owner_session = os.environ.get('V39_OWNER_SESSION')
        os.environ['V39_OWNER_SESSION'] = 'owner-session'
        db = base / 'authority' / 'control.sqlite3'
        writer = S.open_store(str(db))
        reader = S.open_store(str(db), mode='r')
        connections = [writer, reader]
        serial = [0]

        def entity(identity, conn=None):
            row = (conn or writer).execute('SELECT kind, version, digest, data FROM entities WHERE id=?',
                                           (identity,)).fetchone()
            return {'kind': row[0], 'version': row[1], 'digest': row[2], 'data': json.loads(row[3])} if row else None

        def put(identity, kind, data):
            serial[0] += 1
            current = entity(identity)
            S.execute(writer, dict(command_id='setup-%d' % serial[0], principal='owner', operation='upsert_entity',
                                   nonce='setup-%d' % serial[0], artifact_digests=[],
                                   expected_versions={identity: current['version'] if current else 0},
                                   parameters=dict(entity_id=identity, kind=kind, data=data)), 'owner', sign, 1)

        # Accepted authority records: members, the project, units, admissions and policies.
        def member(principal, kind='service', **extra):
            put(principal, 'membership', dict(dict(principal_type=kind, roles=['reservation_service'],
                                                   scope=[REPOSITORY], revoked_at=None, expires_at=None), **extra))
        member('runner')
        member('launch-receiver')
        member('agent-worker', kind='agent_run')
        member('revoked-service', revoked_at=1)
        member('elsewhere-service', scope=['another-repository'])
        put('project:p1', 'project', dict(name='dispatch'))
        writer.command_registry['claim_operation'] = {'transaction_transition': CLM.transition,
                                                      'writes': ('entities', 'journal', 'commands', 'nonces')}

        def authority(conn, command):
            row = conn.execute('SELECT data FROM entities WHERE id=?', (command['principal'],)).fetchone()
            data = json.loads(row[0]) if row else {}
            return 'reservation_service' in (data.get('roles') or []) and data.get('revoked_at') is None

        reservations = RES.Reservations(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                        authorize=authority, signer='runner', sign=sign)
        for scope, subject in (('account', ACCOUNT), ('project', 'p1')):
            reservations.configure('policy/' + subject, scope, subject,
                                   dict(capacity=50, invocations=50, wall_seconds=5000), now=now())
        units = []

        def admitted(unit):
            """A real admitted unit, claimed through VELDO-0031's own transition just before use."""
            units.append(unit)
            put(unit, 'execution_unit', dict(state='READY', repository_uuid=REPOSITORY, backlog_item_uuid='backlog:' + unit,
                                             requirements=[], eligible_holders=[HOLDER], project='p1',
                                             scope_digest='sha256:scope-' + unit, revision=1, depends_on=[]))
            put('backlog:' + unit, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=REPOSITORY))
            put('admission:' + unit, 'admission', dict(unit=unit, state='accepted', scope_digest='sha256:scope-' + unit))
            reservations.configure('policy/' + unit, 'unit', unit, dict(capacity=5, invocations=5, wall_seconds=500),
                                   now=now())
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

        # A real Git source repository; the contract's source is resolved from it.
        src = base / 'source'
        GP.run(['git', 'init', '-q', str(src)], check=True, capture_output=True)
        (src / 'README').write_text('dispatch source\n')
        GP.run(['git', '-C', str(src), 'add', 'README'], check=True, capture_output=True)
        GP.run(['git', '-C', str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'source'], check=True,
               capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        head = {k: GP.run(['git', '-C', str(src), 'rev-parse', 'HEAD^{%s}' % k], check=True,
                          capture_output=True, text=True).stdout.strip() for k in ('commit', 'tree')}

        # The fixture engine. It records its birth environment (its dispatch and the acceptance it
        # was launched under) and proves its store read is denied; the parent joins the birth digest to the journal. It then reads its
        # packet, waits for a release file when told to, prints its payload's claims plus a token of
        # its own and exits with the payload's code. It records what it printed, byte for byte.
        markers = base / 'markers'
        markers.mkdir()
        worker = base / 'engine.py'
        worker.write_text('''import ctypes, hashlib, json, os, select, sqlite3, sys
from pathlib import Path


def released(path):
    """Block until `path` exists, woken only by inotify on its directory (no clock, no bound: a worker that is
    never released ends by its stop)."""
    libc = ctypes.CDLL(None, use_errno=True)
    fd = libc.inotify_init1(os.O_CLOEXEC)
    libc.inotify_add_watch(fd, os.path.dirname(path).encode(), 0x100 | 0x80 | 0x8)  # create, moved to, close write
    (markers / ('%d.waiting' % os.getpid())).write_text(path)
    while not Path(path).exists():
        select.select([fd], [], [])
        os.read(fd, 65536)
    os.close(fd)
store, markers = sys.argv[1], Path(sys.argv[2])
dispatch = os.environ.get('VELDO_DISPATCH_ID', '')
printed = b''
if sys.argv[3:] == ['forge']:
    # A worker claiming to be another process, in the same line format the wrapper uses.
    printed = (json.dumps({'schema': 'veldo.launch_identity/v1', 'process': {
        'platform': 'linux', 'host': 'forged', 'boot_id': 'forged', 'pid': 1, 'start': '1'}}) + '\\n').encode()
    sys.stdout.buffer.write(printed)
    sys.stdout.flush()
if os.environ.get('VELDO_RUN_QUERY'):
    # The real default guard must deny the worker's store read. The parent joins the
    # birth acceptance digest to the immutable journal entry, outside the worker.
    try:
        fd = os.open(store, os.O_RDONLY)
    except PermissionError:
        seen = {'store_denied': True}
    else:
        os.close(fd)
        seen = {'store_denied': False}
else:
    # The explicitly reported remote adapter is outside this host's guard.
    try:
        db = sqlite3.connect('file:%s?mode=ro' % store, uri=True, timeout=WAIT_HANG_SECONDS)
        row = db.execute('SELECT data FROM entities WHERE id=?', ('dispatch:' + dispatch,)).fetchone()
        seen = json.loads(row[0]) if row else None
        db.close()
    except Exception as error:
        seen = {'error': repr(error)}
stat = Path('/proc/self/stat').read_text()
own = {'pid': os.getpid(), 'start': stat[stat.rindex(')') + 2:].split()[19],
       'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'dispatch': dispatch, 'seen': seen,
       'acceptance': os.environ.get('VELDO_DISPATCH_ACCEPTANCE'),
       'environment': {k: os.environ.get(k) for k in ('V39_OWNER_SESSION', 'ENGINE_PROFILE')}}
(markers / ('%d.tmp' % os.getpid())).write_text(json.dumps(own))
(markers / ('%d.tmp' % os.getpid())).rename(markers / ('%d.json' % os.getpid()))
raw = sys.stdin.buffer.read()
packet = json.loads(raw) if raw.strip() else {}
(markers / ('%d.packet' % os.getpid())).write_text(json.dumps(packet))
payload = packet.get('payload') or {}
if payload.get('close_stdout'):
    # A worker that closes its output and keeps running: the receiver must still hold it to its deadline. It says
    # it has closed (its marker), then either works a fixed amount (hashing, no clock) or waits for its release.
    os.close(1)
    (markers / ('%d.closed' % os.getpid())).write_text('closed')
    if payload.get('work'):
        digest = hashlib.sha256()
        block = bytes(1 << 20)
        for _ in range(payload['work']):
            digest.update(block)
    if payload.get('release'):
        released(payload['release'])
    sys.exit(payload.get('code', 0))
if payload.get('release'):
    released(payload['release'])
out = json.dumps(dict(payload.get('say', {}), worker_token=os.urandom(8).hex())).encode()
(markers / ('%d.out' % os.getpid())).write_bytes(printed + out)
sys.stdout.buffer.write(out)
sys.stdout.flush()
sys.exit(payload.get('code', 0))
'''.replace('timeout=WAIT_HANG_SECONDS', 'timeout=' + repr(WAITS.WAIT_HANG_SECONDS)))
        host_trust = private / 'host_trust.json'
        enrollment_signers = private / 'enrollment_signers'
        enrollment_signers.write_text('')
        host_trust.write_text(json.dumps(dict(schema='veldo.host_trust/v1', host_identity='host-39',
                                              enrollment_signers=str(enrollment_signers))))
        # A transport may coalesce the trusted wrapper's identity and the engine's first output
        # line. Forward both in one pipe write so the receiver deterministically sees that case.
        # This runs only after the outer contained wrapper is released; neither line is invented
        # by the transport, and stdin still reaches the real wrapped engine unchanged.
        transport = base / 'transport.py'
        transport.write_text('''import os, shutil, subprocess, sys
child = subprocess.Popen(sys.argv[1:], stdin=sys.stdin, stdout=subprocess.PIPE, stderr=sys.stderr)
opening = child.stdout.readline() + child.stdout.readline()
assert len(opening) <= os.fpathconf(sys.stdout.fileno(), 'PC_PIPE_BUF')
assert os.write(sys.stdout.fileno(), opening) == len(opening)
shutil.copyfileobj(child.stdout, sys.stdout.buffer)
sys.stdout.buffer.flush()
sys.exit(child.wait())
''')
        config = base / 'receiver.json'
        # This host's worker profile (VELDO-0040): every local worker runs in its own systemd scope in a
        # slice of this run's own, with caps far above what these fixture engines use.
        worker_slice = 'v39s%s.slice' % os.urandom(4).hex()
        config.write_text(json.dumps({
            'store': str(db), 'runs': str(base / 'runs'), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
            'workspace': str(base), 'host_trust': str(host_trust),
            'profile': {'kind': 'linux-systemd', 'slice': worker_slice, 'lock': str(base / 'containment.lock'),
                        'concurrency': 64, 'runtime_seconds': 600, 'memory_bytes': 1 << 30, 'cpu_percent': 400,
                        'file_bytes': 1 << 30},
            'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1, 'timers_profile': TIMERS_PROFILE,
            'adapters': {'fixture-engine': {'argv': [sys.executable, '-B', str(worker), str(db), str(markers)],
                                            'environment': {'ENGINE_PROFILE': 'configured-profile'}},
                         'missing-engine': {'argv': [str(base / 'no-such-engine')]},
                         # Through the trusted wrapper, as a launch on another host runs it (the
                         # transport prefix, ssh to the Mac, is configuration; here it is local).
                         'wrapped-engine': {'identity': 'reported', 'argv': [
                             sys.executable, '-B', str(transport),
                             sys.executable, '-B', str(mods / 'control_launch.py'), 'exec',
                             sys.executable, '-B', str(worker), str(db), str(markers), 'forge']},
                         'wrapped-missing': {'identity': 'reported', 'argv': [
                             sys.executable, '-B', str(mods / 'control_launch.py'), 'exec', str(base / 'no-such-engine')]}}}))
        CONFIGURATION = {'mcp_servers': {'veldo': {'command': 'veldo-mcp', 'args': ['serve', REPOSITORY]},
                                         'tracker': {'command': 'tracker-mcp', 'args': []}},
                         'tools': ['Read', 'Edit', 'Bash', 'WebFetch'], 'model': 'configured-model'}
        events = []
        gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base))
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign, observe=events.append)
        receiving = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='launch-receiver',
                                 signer='launch-receiver', sign=sign)
        # The same writer connection: both services register the one dispatch operation on it.
        launches = []

        def invoke(contract, environment=None, before=None):
            if before:
                before()
            launch = L.invoke(config, contract, dispatches, environment=environment)
            launches.append(launch)
            return launch

        runner = L.Runner(gate, reservations, dispatches, invoke, account=ACCOUNT)
        releases = []

        def job(release=None, say=None, code=0, adapter='fixture-engine', deadline=3600):
            payload = {'task': 'build the unit', 'code': code, 'say': say or {'status': 'working'}}
            if release:
                payload['release'] = str(base / ('release-' + release))
                releases.append(Path(payload['release']))
            return dict(holder=HOLDER, source=str(src), revision='HEAD', payload=payload, adapter=adapter,
                        configuration=CONFIGURATION, deadline=now() + deadline)

        def release(name):
            (base / ('release-' + name)).write_text('go')

        def rec(dispatch_id):
            return (dispatches.record(dispatch_id) if isinstance(dispatch_id, str) else None) or {}

        def worker_markers(prefix=None):
            found = []
            for path in sorted(markers.glob('*.json')):
                data = json.loads(path.read_text())
                if prefix is None or str(data.get('dispatch', '')).startswith(prefix):
                    found.append(data)
            return found

        def marker_for(dispatch_id):
            """The marker the worker of a dispatch wrote at its start, or {}. The wait (VELDO-0358) wakes on the
            markers directory and on the store, and ends on the marker (done) or on the dispatch's own record
            (impossible): a worker is started only under a record that is prepared, accepted or running
            (D.STOPPABLE), so a record in any other state (refused, exited, unknown) says no worker is still to
            start; the markers are read once more after it and that reading is the answer."""
            found = {}

            def mine():
                for data in worker_markers():
                    if data.get('dispatch') == dispatch_id:
                        found.update(data)
                        return True
                return False

            def ended():
                # The state is read BEFORE the markers: a record that had ended by then has no later worker.
                state = rec(dispatch_id).get('state')
                return (state is not None and state not in D.STOPPABLE and not mine()), {'state': state}
            WAITS.wait('the marker of the worker of dispatch %s' % dispatch_id, mine, ended,
                       [WAITS.PathAppears(markers / '.any-marker'), WAITS.Store(db)])
            return found

        def file_of(path, pid, what):
            """`path`, once its worker (`pid`) has written it: woken on its directory and on the worker's exit, which
            is the terminal condition (a worker that has ended writes nothing more)."""
            if not isinstance(pid, int):
                return path.exists()  # no worker: nothing is to come
            sources = [WAITS.PathAppears(path)]
            with contextlib.suppress(OSError):
                sources.append(WAITS.Pidfd(pid))
            WAITS.wait(what, path.exists, lambda: proc_identity(pid) is None, sources)
            return path.exists()

        def attempt(fn):
            try:
                return ('ok', fn())
            except (D.Refused, EL.Refused, S.StoreRefused, RES.Refused) as error:
                return ('refused', getattr(error, 'code', str(error)))

        def of_unit(kind, unit):
            found = []
            for (identity, data) in writer.execute('SELECT id, data FROM entities WHERE kind=?', (kind,)):
                data = json.loads(data)
                value = data.get('contract', {}).get('unit') if kind == 'dispatch' else (data.get('context') or {}).get('unit')
                if value == unit and (kind != 'subscription_reservation' or data.get('type') == 'worker'):
                    found.append((identity, data))
            return found

        def states(dispatch_id):
            return [h.get('state') for h in rec(dispatch_id).get('history', [])]

        def proc_identity(pid):
            try:
                stat = Path('/proc/%d/stat' % pid).read_text()
                return stat[stat.rindex(')') + 2:].split()[19]
            except (OSError, ValueError, IndexError):
                return None

        def journal_seq(prefix):
            row = writer.execute('SELECT MIN(seq) FROM journal WHERE substr(command_id, 1, ?) = ?',
                                 (len(prefix), prefix)).fetchone()
            return row[0] if row else None

        emitted, raised, regions = set(), [], []
        observed = {}
        first_messages = []

        def check(label, condition, detail=''):
            """One row; a false one carries `detail`, what it saw, after its name's colon (VELDO-0261)."""
            emitted.add(label)
            expect('VELDO-0039 ' + label + (': ' + detail if detail and not condition else ''), bool(condition))

        # VELDO-0261: the region each dispatch was made in, so a row that finds a dispatch it did not expect names
        # where that dispatch came from.
        born = {}

        def dispatch_ids():
            return {json.loads(data)['dispatch_id']
                    for (data,) in writer.execute('SELECT data FROM entities WHERE kind=?', (D.RECORD_KIND,))}

        @contextlib.contextmanager
        def region(*labels):
            regions.append(labels[0])
            before = dispatch_ids()
            try:
                yield
            except Exception as error:  # noqa: BLE001 - a raise reds its rows, never skips them
                raised.append((labels[0], repr(error)))
                for label in labels:
                    if label not in emitted:
                        check(label, False, 'raised ' + repr(error))
            finally:
                for made in dispatch_ids() - before:
                    born.setdefault(made, labels[0])

        # VELDO-0261: the two owner stop rows' workers are held to this contract deadline. An asked stop is begun
        # within seconds of the worker's start and its cause is then fixed, so the deadline never decides a stop
        # that was asked; a stop never asked, or ignored, ends at it as a deadline stop, which the rows name.
        # VELDO-0358: an hour away. Whether the stop was honoured is the receiver's check answer, never the deadline.
        STOP_ROW_DEADLINE = 3600

        class LaunchPipe(WAITS.Source):
            """The receiver's output (the launch pipe), taken by Launch.pump so the launch keeps every message; watched
            until the run's end is seen on it."""

            def __init__(self, launch):
                self.launch = launch

            def fileno(self):
                return self.launch.child.stdout.fileno()

            def fired(self):
                return not self.launch.pump()

            def describe(self):
                return 'launch-pipe(%s)' % self.launch.dispatch_id

        def check_request(launch, name, *, advance=None):
            """VELDO-0358 C4: ask the receiver whether a stop is begun (the test harness's check request). Its answer, a
            `checked` message naming the cause it began a stop for, or None, comes on the launch pipe."""
            message = {'check': name}
            if advance is not None:
                message['advance'] = advance
            try:
                launch.child.stdin.write((json.dumps(message) + '\n').encode())
                launch.child.stdin.flush()
            except BrokenPipeError:
                # The requested stop can finish before this diagnostic reaches the receiver.
                # settle_stopped still judges the durable end, receiver exit and stop cause;
                # a closed pipe alone is never evidence that the stop succeeded.
                pass

        def answered(launch, name):
            return [m for m in launch.messages if isinstance(m, dict) and m.get('event') == 'checked'
                    and m.get('check') == name]

        def settle_stopped(launch):
            """VELDO-0261, VELDO-0358: once the runner has asked the receiver to stop, ask the receiver whether it has
            begun a stop (a check request) and wait for the dispatch's record to reach a terminal state, woken by the
            store, the launch pipe and the receiver's exit. The wait is impossible when the receiver answers that it
            began no stop (nothing will end the worker but its deadline, so the stop was not honoured), or when the
            receiver has ended with the record still open (no one is left to record the end). None, or the report;
            then the runner's wait settles it (at once, timeout 0, after a report)."""
            name = 'stop-%s' % launch.dispatch_id
            check_request(launch, name)

            def ended():
                state = rec(launch.dispatch_id).get('state')
                return state not in D.STOPPABLE, {'state': state}

            def impossible():
                state = rec(launch.dispatch_id).get('state')
                receiver = launch.child.poll()
                nothing_begun = any(m.get('due') is None for m in answered(launch, name))
                return (state in D.STOPPABLE and (receiver is not None or nothing_begun),
                        {'state': state, 'receiver_exit': receiver, 'answer': answered(launch, name)})
            # An earlier terminal observation may already have reaped the receiver. Its
            # returncode and remaining output still settle it; that PID can no longer be opened.
            exited = [] if launch.child.returncode is not None else [WAITS.Pidfd(launch.child)]
            result = WAITS.wait('dispatch %s to reach a terminal state' % launch.dispatch_id, ended, impossible,
                                [WAITS.Store(db), *exited, LaunchPipe(launch)])
            if result.done:
                runner.wait(launch)
                return None
            runner.wait(launch, timeout=0)  # nothing more will come: the runner records what it finds now
            return result.report()

        def stop_cause(launch, record):
            """What ended a stopped dispatch, as the row judges it: the cause, never the speed."""
            termination = record.get('termination') or {}
            return {'state': record.get('state'), 'asked': ((record.get('stop_request') or {}).get('result') or {}).get('asked'),
                    'deadline_stop': termination.get('deadline_stop'), 'cause': (launch.supervision or {}).get('cause'),
                    'returncode': termination.get('returncode'), 'signal': termination.get('signal')}

        def stopped_by_request(cause):
            return (cause['state'] == 'exited' and cause['asked'] is True and cause['deadline_stop'] is False
                    and cause['cause'] == 'requested')

        try:
            # AC1: the complete contract before any worker; one active dispatch per unit/station
            with region('dispatch/contract-before-launch', 'dispatch/one-active-per-unit-station'):
                u1 = admitted('VELDO-9301')
                first = runner.submit(u1, 'build', **job(release='u1-a'))
                second = attempt(lambda: runner.submit(u1, 'build', **job()))
                seen = marker_for(first.dispatch_id)
                record = rec(first.dispatch_id)
                contract = record.get('contract') or {}
                slot = entity(RES.entity('worker', [DOMAIN, first.dispatch_id])) or {}
                claim = entity(CLM.claim_id(REPOSITORY, u1)) or {}
                # The worker's birth digest can exist only after acceptance committed.
                # Read that exact immutable transition as the authority-side observer;
                # the worker proves separately that it cannot open the protected store.
                birth = writer.execute('SELECT transition FROM journal WHERE record_digest=?',
                                       (seen.get('acceptance'),)).fetchone()
                seen_record = (json.loads(birth[0]) if birth else {}).get(
                    D.record_id(first.dispatch_id), {}).get('data', {})
                packet_path = markers / ('%s.packet' % seen.get('pid'))
                # The packet is the file of the worker the marker names; with no marker there is no worker whose
                # packet could come, and nothing to wait for.
                file_of(packet_path, seen.get('pid'), 'the packet of the worker of %s' % first.dispatch_id)
                packet = json.loads(packet_path.read_text()) if packet_path.exists() else {}
                order = [journal_seq('dispatch/%s/%s/' % (a, first.dispatch_id)) for a in ('prepare', 'accept', 'run')]
                given = contract.get('input') or {}
                decision = given.get('decision') or {}
                bindings = {
                    'store_guard': (seen.get('seen') or {}).get('store_denied') is True,
                    'source': contract.get('source') == dict(head, repository_uuid=REPOSITORY),
                    'input': (given.get('payload') == {'task': 'build the unit', 'code': 0, 'say': {'status': 'working'},
                                                       'release': str(base / 'release-u1-a')}
                              and given.get('payload_digest') == D.digest(given.get('payload'))
                              and packet.get('payload') == given.get('payload')
                              and decision.get('station') == 'build' and decision.get('unit') == u1
                              and (decision.get('inputs') or {}).get('admission', {}).get('version')
                              == entity('admission:' + u1)['version']
                              and (decision.get('inputs') or {}).get('unit', {}).get('version') == entity(u1)['version']
                              and given.get('context') == {'holder': HOLDER}),
                    # Exactly the configured capabilities, never reduced: the recorded configuration
                    # unchanged, the owner's session and the adapter's configured environment.
                    'capability': (contract.get('capability') or {}).get('configuration') == CONFIGURATION
                                  and packet.get('configuration') == CONFIGURATION
                                  and seen.get('environment') == {'V39_OWNER_SESSION': 'owner-session',
                                                                  'ENGINE_PROFILE': 'configured-profile'}
                                  and (contract.get('capability') or {}).get('adapter') == 'fixture-engine',
                    'reservation': (contract.get('reservation') or {}) == {
                        'entity': RES.entity('worker', [DOMAIN, first.dispatch_id]), 'version': slot.get('version'),
                        'digest': slot.get('digest'), 'account': ACCOUNT, 'project': 'p1'}
                        and slot.get('data', {}).get('dispatch') == first.dispatch_id,
                    'claim': (contract.get('claim') or {}) == {'entity': CLM.claim_id(REPOSITORY, u1), 'holder': HOLDER,
                                                               'generation': claim.get('data', {}).get('generation')},
                    'deadline': isinstance(contract.get('deadline'), float) and contract['deadline'] > now(),
                    'complete': D.contract_problems(contract) == [] and record.get('contract_digest') == D.digest(contract),
                }
                # The worker's birth environment names the journal digest of the acceptance it was
                # launched under, a value that exists only once that acceptance committed; that
                # acceptance's own journal record carries the prepared contract's digest.
                accept_row = writer.execute('SELECT record_digest, transition FROM journal WHERE seq=?',
                                            (order[1],)).fetchone() if order[1] else None
                accepted_record = (json.loads(accept_row[1]) if accept_row else {}).get(D.record_id(first.dispatch_id), {})
                order_ok = (getattr(first, 'result', None) == 'accepted'
                            and bool(seen.get('acceptance')) and accept_row is not None
                            and seen.get('acceptance') == accept_row[0]
                            and accepted_record.get('data', {}).get('state') == 'accepted'
                            and accepted_record.get('data', {}).get('contract_digest') == record.get('contract_digest')
                            and seen_record.get('state') in ('accepted', 'running')
                            and seen_record.get('contract_digest') == record.get('contract_digest')
                            and D.contract_problems(seen_record.get('contract')) == []
                            and None not in order and order == sorted(order))
                workers_u1 = worker_markers('dispatch/%s/' % u1)
                observed['contract'] = {'bindings': bindings, 'seen_at_start': seen_record.get('state'),
                                        'birth_acceptance': seen.get('acceptance'),
                                        'acceptance_record': accept_row[0] if accept_row else None,
                                        'journal_order': order, 'workers': len(workers_u1),
                                        'second': [second[0], getattr(second[1], 'result', second[1])]}
                check('dispatch/contract-before-launch', order_ok and all(bindings.values()) and len(workers_u1) == 1
                      and len(of_unit('dispatch', u1)) == 1 and len(of_unit('subscription_reservation', u1)) == 1)

                # A second complete contract for the held unit and station, at the authority itself.
                rival = dict(contract, dispatch_id='dispatch/%s/rival' % u1)
                reservations.reserve_worker('worker/' + rival['dispatch_id'], rival['dispatch_id'], ACCOUNT, 'p1', u1,
                                            now=now())
                rslot = entity(RES.entity('worker', [DOMAIN, rival['dispatch_id']]))
                rival['reservation'] = dict(contract.get('reservation') or {}, entity=RES.entity('worker', [DOMAIN, rival['dispatch_id']]),
                                            version=rslot['version'], digest=rslot['digest'])
                # The next attempt number, so only the active dispatch can refuse it.
                rival['attempt'] = 2
                direct = attempt(lambda: dispatches.prepare(rival, now=now()))
                release('u1-a')
                ended = runner.wait(first)
                first_messages = list(first.messages)
                # A conclusive end frees the unit and station: the next attempt is attempt 2.
                third_try = attempt(lambda: runner.submit(u1, 'build', **job(release='u1-b')))
                third = third_try[1] if third_try[0] == 'ok' else None
                release('u1-b')
                third_end = runner.wait(third) if third else {}
                third_id = getattr(third, 'dispatch_id', None)
                # Two runners on their own connections race past their own pre-checks.
                u2 = admitted('VELDO-9302')
                barrier = threading.Barrier(2)
                outcomes, errors = [], []

                def contender(n):
                    try:
                        # Its own store module: VELDO-0036 registers its command on the module.
                        store = load('v39_store_race_%d' % n, mods / 'control_store.py')
                        mine = store.open_store(str(db))
                        mine_reader = store.open_store(str(db), mode='r')
                        try:
                            mine_reservations = RES.Reservations(store, mine, domain=DOMAIN, repository=REPOSITORY,
                                                                 principal='runner', authorize=authority,
                                                                 signer='runner', sign=sign)
                            mine_dispatches = D.Dispatches(store, mine, domain=DOMAIN, repository=REPOSITORY,
                                                           principal='runner', signer='runner', sign=sign)
                            original = mine_dispatches.prepare

                            def together(*args, **kwargs):
                                barrier.wait(timeout=WAITS.WAIT_HANG_SECONDS)
                                return original(*args, **kwargs)
                            mine_dispatches.prepare = together
                            racer = L.Runner(EL.Gate(store, mine_reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY, workspace=str(base)),
                                             mine_reservations, mine_dispatches,
                                             lambda c: L.invoke(config, c, mine_dispatches),
                                             account=ACCOUNT)
                            got = attempt(lambda: racer.submit(u2, 'build', **job(release='u2')))
                            if got[0] == 'ok':
                                release('u2')
                                racer.wait(got[1])
                                got = ('ok', got[1].result)
                            outcomes.append(got)
                        finally:
                            mine.close()
                            mine_reader.close()
                    except Exception as error:  # noqa: BLE001
                        errors.append(repr(error))
                racers = [threading.Thread(target=contender, args=(n,)) for n in range(2)]
                for racer_thread in racers:
                    racer_thread.start()
                for racer_thread in racers:
                    joined(racer_thread, 'a racing runner of %s' % u2)
                balance = reservations.balances('unit', u2)
                observed['uniqueness'] = {'second': [second[0], getattr(second[1], 'result', second[1])],
                                          'direct': [direct[0], getattr(direct[1], 'get', lambda k: direct[1])('state')],
                                          'third': third_try[0],
                                          'third_attempt': rec(third_id).get('contract', {}).get('attempt'),
                                          'race': outcomes, 'race_errors': errors, 'race_workers': len(worker_markers('dispatch/%s/' % u2)),
                                          'race_capacity_after': balance['capacity']}
                check('dispatch/one-active-per-unit-station',
                      second[0] == 'refused' and str(second[1]).startswith('active_dispatch:' + first.dispatch_id)
                      and direct[0] == 'refused' and str(direct[1]).startswith('active_dispatch:' + first.dispatch_id)
                      and (ended or {}).get('state') == 'exited' and (third_end or {}).get('state') == 'exited'
                      and rec(third_id).get('contract', {}).get('attempt') == 2
                      and len(worker_markers('dispatch/%s/' % u1)) == 2
                      and not errors and sorted(o[0] for o in outcomes) == ['ok', 'refused']
                      and ('ok', 'accepted') in outcomes and len(worker_markers('dispatch/%s/' % u2)) == 1
                      and balance['capacity'] == 0)

            # AC2: accepted, refused and unknown launch results under the original identity
            with region('dispatch/launch-results'):
                u3 = admitted('VELDO-9303')
                accepted = runner.submit(u3, 'build', **job(release='u3'))
                own = marker_for(accepted.dispatch_id)
                r3 = rec(accepted.dispatch_id)
                process = r3.get('process') or {}
                independent = proc_identity(process.get('pid') or 0)
                boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
                accepted_ok = (accepted.result == 'accepted' and r3.get('state') == 'running'
                               and process.get('pid') == own.get('pid') and process.get('start') == own.get('start')
                               and independent is not None and process.get('start') == independent
                               and process.get('boot_id') == boot == own.get('boot_id')
                               and (r3.get('receiver') or {}).get('principal') == 'launch-receiver'
                               and (r3.get('receiver') or {}).get('pid') not in (None, process.get('pid'))
                               and states(accepted.dispatch_id) == ['prepared', 'accepted', 'running'])
                u4 = admitted('VELDO-9304')
                spawn = runner.submit(u4, 'build', **job(adapter='missing-engine'))
                r4 = rec(spawn.dispatch_id)
                spawn_ok = (spawn.result == 'refused' and r4.get('state') == 'refused'
                            and r4.get('refusal') == 'spawn_failed:ENOENT'
                            and states(spawn.dispatch_id) == ['prepared', 'accepted', 'refused']
                            and not worker_markers(spawn.dispatch_id)
                            and reservations.balances('unit', u4)['capacity'] == 0)
                u5 = admitted('VELDO-9305')
                withdrawn = L.Runner(gate, reservations, dispatches, lambda c: invoke(c, before=lambda: put(
                    'admission:' + u5, 'admission', dict(unit=u5, state='withdrawn', scope_digest='sha256:scope-' + u5))),
                    account=ACCOUNT).submit(u5, 'build', **job())
                r5 = rec(withdrawn.dispatch_id)
                withdrawn_ok = (withdrawn.result == 'refused' and r5.get('state') == 'refused'
                                and 'stale_input:admission' in str(r5.get('refusal'))
                                and states(withdrawn.dispatch_id) == ['prepared', 'refused']
                                and not worker_markers(withdrawn.dispatch_id)
                                and reservations.balances('unit', u5)['capacity'] == 0)
                u6 = admitted('VELDO-9306')
                # The receiver's answer is lost after its acceptance commits: under the store's crash
                # harness it ends itself right after that commit, before any spawn.
                lost = L.Runner(gate, reservations, dispatches, lambda c: invoke(c, environment=dict(
                    os.environ, VELDO_CONTROL_TEST_HARNESS='1', VELDO_CONTROL_KILL_AT='after_commit')),
                    account=ACCOUNT).submit(u6, 'build', **job())
                r6 = rec(lost.dispatch_id)
                unknown_ok = (lost.result == 'unknown' and r6.get('state') == 'unknown' and r6.get('stop') == D.STOP
                              and r6.get('reason') == 'launch_evidence_missing'
                              and states(lost.dispatch_id) == ['prepared', 'accepted', 'unknown']
                              and not worker_markers(lost.dispatch_id)
                              and reservations.balances('unit', u6)['capacity'] == 1)
                # Through the trusted wrapper: the identity is the wrapper's first line, which is the
                # engine's own process after exec; the line the worker forges after it is output,
                # even when the transport delivers both lines together after containment setup.
                uw = admitted('VELDO-9312')
                wrapped = runner.submit(uw, 'build', **job(release='uw', adapter='wrapped-engine'))
                wown = marker_for(wrapped.dispatch_id)
                rw = rec(wrapped.dispatch_id)
                wprocess = rw.get('process') or {}
                wproc = proc_identity(wprocess.get('pid') or 0)
                release('uw')
                ew = runner.wait(wrapped) or {}
                wpath = markers / ('%s.out' % wown.get('pid'))
                wout = wpath.read_bytes() if wpath.exists() else b''
                wrapped_ok = (wrapped.result == 'accepted' and wprocess.get('pid') == wown.get('pid')
                              and wprocess.get('start') == wown.get('start') == wproc
                              and wprocess.get('boot_id') == boot and wprocess.get('host') not in (None, 'forged')
                              and ew.get('state') == 'exited' and ew.get('process') == wprocess
                              and wout.startswith(b'{"schema": "veldo.launch_identity/v1"')
                              and (ew.get('termination') or {}).get('output_bytes') == len(wout)
                              and (ew.get('termination') or {}).get('output_digest') == 'sha256:' + hashlib.sha256(wout).hexdigest())
                um = admitted('VELDO-9313')
                wmissing = runner.submit(um, 'build', **job(adapter='wrapped-missing'))
                rm = rec(wmissing.dispatch_id)
                wrapped_ok &= (wmissing.result == 'refused' and rm.get('refusal') == 'spawn_failed:ENOENT'
                               and states(wmissing.dispatch_id) == ['prepared', 'accepted', 'refused']
                               and reservations.balances('unit', um)['capacity'] == 0)
                identity_ok = all(
                    len(of_unit('dispatch', u)) == 1 and of_unit('dispatch', u)[0][1]['dispatch_id'] == launch.dispatch_id
                    and len(of_unit('subscription_reservation', u)) == 1
                    and of_unit('subscription_reservation', u)[0][1]['dispatch'] == launch.dispatch_id
                    for u, launch in ((u3, accepted), (u4, spawn), (u5, withdrawn), (u6, lost), (uw, wrapped),
                                      (um, wmissing)))
                observed['launch_results'] = {
                    'accepted': {'result': accepted.result, 'stored_process': process, 'worker_reported': {k: own.get(k) for k in ('pid', 'start', 'boot_id')},
                                 'proc_start': independent, 'receiver_pid': (r3.get('receiver') or {}).get('pid')},
                    'refused_spawn': {'result': spawn.result, 'refusal': r4.get('refusal'), 'states': states(spawn.dispatch_id)},
                    'refused_recheck': {'result': withdrawn.result, 'refusal': r5.get('refusal'), 'states': states(withdrawn.dispatch_id)},
                    'unknown': {'result': lost.result, 'reason': r6.get('reason'), 'stop': r6.get('stop'), 'states': states(lost.dispatch_id)},
                    'wrapped': {'result': wrapped.result, 'stored_process': wprocess, 'worker_reported': {
                        k: wown.get(k) for k in ('pid', 'start', 'boot_id')}, 'proc_start': wproc,
                        'missing': [wmissing.result, rm.get('refusal')]},
                    'one_identity_each': identity_ok}
                check('dispatch/launch-results', accepted_ok and spawn_ok and withdrawn_ok and unknown_ok and wrapped_ok
                      and identity_ok)

            with region('dispatch/deadline-after-closed-output', 'dispatch/remote-stop-holds-unit'):
                # A worker that closes its output early is still stopped at its deadline, and recorded as
                # stopped, not as a clean exit. VELDO-0358: the deadline is an hour away and the receiver's clock is
                # supplied. Once the worker says its output is closed, the clock is moved one second past the
                # deadline and the receiver is asked whether a stop is due (C4): it stops the worker for the
                # deadline, or answers that nothing was due (the terminal condition). The worker then works a fixed
                # amount and exits by itself, which only a receiver that did not stop it lets happen.
                uc = admitted('VELDO-9321')
                closing = runner.submit(uc, 'build', **dict(job(deadline=3600), payload={
                    'task': 'build the unit', 'close_stdout': True, 'work': 16384}))
                closing_marker = marker_for(closing.dispatch_id)
                file_of(markers / ('%s.closed' % closing_marker.get('pid')), closing_marker.get('pid'),
                        'the worker of %s to close its output' % closing.dispatch_id)
                check_request(closing, 'past-deadline', advance=closing.contract['deadline'] - now() + 1)

                def deadline_stopped():
                    state = rec(closing.dispatch_id).get('state')
                    return state not in D.STOPPABLE, {'state': state}

                def nothing_due():
                    answer = answered(closing, 'past-deadline')
                    return any(m.get('due') is None for m in answer), {'answer': answer}
                judged = WAITS.wait('the deadline stop of %s on the supplied clock' % closing.dispatch_id,
                                    deadline_stopped, nothing_due,
                                    [WAITS.Store(db), WAITS.Pidfd(closing.child), LaunchPipe(closing)])
                if judged.done:
                    ec = runner.wait(closing) or {}
                else:
                    ec = runner.wait(closing, timeout=0) or {}  # nothing will stop it: recorded as found now
                rc = rec(closing.dispatch_id)
                term = rc.get('termination') or {}
                observed['closed_output'] = {'result': closing.result, 'state': rc.get('state'), 'termination': term,
                                             'answer': answered(closing, 'past-deadline'), 'wait': judged.report()}
                # And a worker that closes its output early but finishes before its deadline is not cut short:
                # its own exit code is recorded, with no deadline stop. It ends when the test releases it, after it
                # said its output is closed; its deadline is an hour away.
                un = admitted('VELDO-9323')
                early = runner.submit(un, 'build', **dict(job(deadline=3600), payload={
                    'task': 'build the unit', 'close_stdout': True, 'code': 4,
                    'release': str(base / 'release-closed-early')}))
                releases.append(base / 'release-closed-early')
                early_marker = marker_for(early.dispatch_id)
                closed_early = file_of(markers / ('%s.closed' % early_marker.get('pid')), early_marker.get('pid'),
                                       'the worker of %s to close its output' % early.dispatch_id)
                release('closed-early')
                runner.wait(early)
                rn = rec(early.dispatch_id)
                early_term = rn.get('termination') or {}
                observed['closed_output_normal'] = {'state': rn.get('state'), 'termination': early_term,
                                                    'closed_before_release': closed_early}
                check('dispatch/deadline-after-closed-output',
                      closing.result == 'accepted' and judged.done and rc.get('state') == 'exited'
                      and term.get('deadline_stop') is True and term.get('returncode') is None
                      and [m.get('due') for m in answered(closing, 'past-deadline')] == ['deadline']
                      and early.result == 'accepted' and closed_early and rn.get('state') == 'exited'
                      and early_term.get('returncode') == 4 and early_term.get('deadline_stop') is False,
                      'closed %r; early %r' % (observed['closed_output'], observed['closed_output_normal']))
                # Through the wrapper (a remote engine), stopping the local transport at the deadline does not
                # show the far engine ended: the outcome is unknown and the unit stays held.
                # VELDO-0358: its deadline is an hour away and is reached on the receiver's supplied clock once the
                # far engine runs (its marker), as in the closed-output row above; a receiver that stops nothing for
                # it answers the check that nothing was due.
                ur = admitted('VELDO-9322')
                remote = runner.submit(ur, 'build', **job(release='never-9322', adapter='wrapped-engine'))
                marker_for(remote.dispatch_id)
                check_request(remote, 'remote-past-deadline', advance=remote.contract['deadline'] - now() + 1)
                remote_judged = WAITS.wait(
                    'the deadline stop of %s on the supplied clock' % remote.dispatch_id,
                    lambda: rec(remote.dispatch_id).get('state') not in D.STOPPABLE,
                    lambda: any(m.get('due') is None for m in answered(remote, 'remote-past-deadline')),
                    [WAITS.Store(db), WAITS.Pidfd(remote.child), LaunchPipe(remote)])
                if remote_judged.done:
                    runner.wait(remote)
                else:
                    runner.wait(remote, timeout=0)  # nothing will stop it: recorded as found now
                rr = rec(remote.dispatch_id)
                again = attempt(lambda: runner.submit(ur, 'build', **job(adapter='wrapped-engine')))
                observed['remote_stop'] = {'result': remote.result, 'state': rr.get('state'), 'reason': rr.get('reason'),
                                           'again': [again[0], str(again[1])]}
                check('dispatch/remote-stop-holds-unit',
                      remote.result == 'accepted' and rr.get('state') == 'unknown'
                      and rr.get('reason') == 'remote_stop_unconfirmed' and again[0] == 'refused'
                      and 'dispatch_outcome_unknown' in str(again[1]))

            with region('dispatch/unknown-never-relaunched'):
                before = dispatches.version(lost.dispatch_id)
                resubmit = attempt(lambda: runner.submit(u6, 'build', **job()))
                fresh = dict(rec(lost.dispatch_id).get('contract') or {}, dispatch_id='dispatch/%s/fresh' % u6, attempt=2)
                reservations.reserve_worker('worker/' + fresh['dispatch_id'], fresh['dispatch_id'], ACCOUNT, 'p1', u6,
                                            now=now())
                fslot = entity(RES.entity('worker', [DOMAIN, fresh['dispatch_id']]))
                fresh['reservation'] = dict(fresh.get('reservation') or {}, entity=RES.entity('worker', [DOMAIN, fresh['dispatch_id']]),
                                            version=fslot['version'], digest=fslot['digest'])
                direct = attempt(lambda: dispatches.prepare(fresh, now=now()))
                again = invoke(rec(lost.dispatch_id).get('contract'))
                ended_again = invoke(rec(first.dispatch_id).get('contract'))
                # VELDO-0358 pattern W: the absence of a worker is read after both receivers have ended (each
                # refused not_prepared, and Launch.start reaped it), with no window of time.
                observed['unknown_relaunch'] = {'resubmit': [resubmit[0], getattr(resubmit[1], 'result', resubmit[1])],
                                                'direct': [direct[0], getattr(direct[1], 'get', lambda k: direct[1])('state')],
                                                'reinvoke': [again.result, again.refusal, again.owned],
                                                'reinvoke_exited': [ended_again.result, ended_again.refusal]}
                check('dispatch/unknown-never-relaunched',
                      resubmit[0] == 'refused' and str(resubmit[1]).startswith('dispatch_outcome_unknown:' + lost.dispatch_id)
                      and direct[0] == 'refused' and str(direct[1]).startswith('dispatch_outcome_unknown:' + lost.dispatch_id)
                      and again.owned is False and again.refusal == 'not_prepared:unknown'
                      and ended_again.owned is False and ended_again.refusal == 'not_prepared:exited'
                      and dispatches.version(lost.dispatch_id) == before and rec(lost.dispatch_id).get('state') == 'unknown'
                      and not worker_markers(lost.dispatch_id) and len(worker_markers('dispatch/%s/' % u1)) == 2
                      and len(of_unit('dispatch', u6)) == 1)

            # AC3: every ordinary transition from the schema, and nothing else
            with region('dispatch/transitions-from-schema'):
                u7 = admitted('VELDO-9307')
                orphaned = runner.submit(u7, 'build', **job(release='u7'))
                o7 = marker_for(orphaned.dispatch_id)
                # Birth precedes the stdin read. Killing the receiver before its feeder sends the packet
                # gives the worker EOF with no release instruction: it exits and its group can disappear
                # before the orphan stop. Wait until the worker has consumed the packet and armed its wait.
                waiting = file_of(markers / ('%s.waiting' % o7.get('pid')), o7.get('pid'),
                                  'the orphan worker to wait for its release')
                orphan_packet = json.loads((markers / ('%s.packet' % o7.get('pid'))).read_text()) if waiting else {}
                check('dispatch/orphan-worker-ready',
                      waiting and (orphan_packet.get('payload') or {}).get('release') == str(base / 'release-u7'))
                # The receiver that owns the running worker is stopped: the outcome is unknown.
                orphaned.child.kill()
                orphaned.child.wait()  # killed: its exit is certain
                r7 = runner.wait(orphaned) or {}
                # VELDO-0154: the dead receiver's stop is made by the runner, which then waits for the kernel to show
                # the worker gone (its group's cgroup.events and its pidfd, VELDO-0358) and frees the account slot.
                runner.orphaned(orphaned)
                p7 = r7.get('process') or {}
                if p7.get('pid') and proc_identity(p7['pid']) == p7.get('start'):
                    os.killpg(p7['pid'], signal.SIGKILL)
                u8, u9 = admitted('VELDO-9308'), admitted('VELDO-9309')
                prepared_only = runner.prepare(u8, 'build', **job())
                accepted_only = runner.prepare(u9, 'build', **job())
                me = dict(L.process_identity(os.getpid()), principal='launch-receiver')
                receiving.accept(accepted_only['dispatch_id'], D.digest(accepted_only), me, now=now())
                derived = {(frm, action, to) for action, (froms, to) in D.TRANSITIONS.items() for frm in (froms or (None,))}
                walked = set()
                for (identity, data) in writer.execute('SELECT id, data FROM entities WHERE kind=?', ('dispatch',)):
                    history = json.loads(data).get('history', [])
                    for n, step in enumerate(history):
                        walked.add((history[n - 1]['state'] if n else None, step['action'], step['state']))
                in_state = {'prepared': prepared_only['dispatch_id'], 'accepted': accepted_only['dispatch_id'],
                            'running': accepted.dispatch_id, 'exited': first.dispatch_id, 'refused': spawn.dispatch_id,
                            'unknown': lost.dispatch_id}
                termination = {'returncode': 0, 'signal': None, 'output_digest': 'sha256:' + '0' * 64,
                               'output_bytes': 0, 'deadline_stop': False}
                refusals, unchanged = {}, True
                for action, (froms, to) in D.TRANSITIONS.items():
                    for state in D.STATES:
                        if state in froms:
                            continue
                        target = in_state[state]
                        r = rec(target)
                        version = dispatches.version(target)
                        digest_ = r.get('contract_digest')
                        call = {'prepare': lambda: dispatches.prepare(r.get('contract'), now=now()),
                                'accept': lambda: receiving.accept(target, digest_, me, now=now()),
                                'run': lambda: receiving.run(target, digest_, L.process_identity(os.getpid()), now=now()),
                                'exit': lambda: receiving.exit(target, digest_, r.get('process'), termination, now=now()),
                                'refuse': lambda: receiving.refuse(target, digest_, 'probe', now=now()),
                                'unknown': lambda: receiving.unknown(target, digest_, 'probe', now=now())}[action]
                        refusals[(state, action)] = attempt(call)
                        unchanged &= dispatches.version(target) == version
                # An observation that names the state it ends is refused once the record has left it.
                moved_version = dispatches.version(accepted_only['dispatch_id'])
                moved = attempt(lambda: receiving.refuse(accepted_only['dispatch_id'], D.digest(accepted_only), 'probe',
                                                         now=now(), expected_state='prepared'))
                unchanged &= dispatches.version(accepted_only['dispatch_id']) == moved_version
                expected_refusals = {(state, action): ('refused', 'duplicate_dispatch' if action == 'prepare'
                                                       else 'transition_refused:%s:%s' % (state, action))
                                     for (state, action) in refusals}
                observed['transitions'] = {'derived': sorted(map(str, derived)), 'walked_by_real_records': sorted(map(str, walked)),
                                           'disallowed': {'%s/%s' % k: v for k, v in sorted(refusals.items())},
                                           'running_lost': r7.get('state')}
                observed['transitions']['moved_on'] = moved
                check('dispatch/transitions-from-schema',
                      moved == ('refused', 'transition_refused:accepted:refuse')
                      and set(D.STATES) == {'prepared', 'accepted', 'running', 'exited', 'refused', 'unknown'}
                      and derived == walked and len(derived) >= 8 and all(to in D.STATES for _, _, to in derived)
                      and refusals == expected_refusals and len(refusals) == len(D.TRANSITIONS) * len(D.STATES) - (len(derived) - 1)
                      and unchanged and r7.get('state') == 'unknown' and r7.get('reason') == 'outcome_unknown'
                      and states(orphaned.dispatch_id) == ['prepared', 'accepted', 'running', 'unknown']
                      and o7.get('pid') == p7.get('pid'))

            # AC3: one worker's result never moves another dispatch; output is not completion
            with region('dispatch/result-binding', 'dispatch/terminal-not-completion'):
                ub = admitted('VELDO-9311')
                b = runner.submit(ub, 'build', **job(release='ub'))
                ua = admitted('VELDO-9310')
                nonce = 'claimed-landed-%s' % os.urandom(6).hex()
                a = runner.submit(ua, 'build', **job(release='ua', say={
                    'status': 'completed', 'landed': True, 'dispatch_id': b.dispatch_id, 'revision_landed': nonce}))
                marker_for(a.dispatch_id)
                marker_for(b.dispatch_id)
                ra, rb = rec(a.dispatch_id), rec(b.dispatch_id)
                a_version, b_version, unit_version = (dispatches.version(a.dispatch_id), dispatches.version(b.dispatch_id),
                                                      entity(ua)['version'])
                # A's result as its receiver records one: exit status and what the worker printed.
                a_result = {'returncode': 0, 'signal': None, 'output_digest': 'sha256:' + hashlib.sha256(b'{}').hexdigest(),
                            'output_bytes': 2, 'deadline_stop': False}
                probes = {
                    'a_result_to_b': attempt(lambda: receiving.exit(b.dispatch_id, ra.get('contract_digest'), ra.get('process'),
                                                                    a_result, now=now())),
                    'a_process_under_b_digest': attempt(lambda: receiving.exit(b.dispatch_id, rb.get('contract_digest'),
                                                                               ra.get('process'), a_result, now=now())),
                    'a_stop_to_b': attempt(lambda: receiving.unknown(b.dispatch_id, ra.get('contract_digest'), 'lost',
                                                                     now=now())),
                }
                untouched = (dispatches.version(b.dispatch_id) == b_version and dispatches.version(a.dispatch_id) == a_version)
                release('ua')
                ea = runner.wait(a) or {}
                printed_path = markers / ('%s.out' % (ea.get('process') or {}).get('pid'))
                a_out = printed_path.read_bytes() if printed_path.exists() else b''
                b_after = rec(b.dispatch_id)
                binding_ok = (probes['a_result_to_b'][0] == 'refused' and str(probes['a_result_to_b'][1]).startswith('binding_mismatch:')
                              and probes['a_process_under_b_digest'] == ('refused', 'binding_mismatch:process')
                              and probes['a_stop_to_b'] == ('refused', 'binding_mismatch:contract_digest')
                              and untouched and ea.get('state') == 'exited' and ea.get('process') == ra.get('process')
                              and b_after.get('state') == 'running' and dispatches.version(b.dispatch_id) == b_version
                              and b_after.get('process') == rb.get('process'))
                release('ub')
                eb = runner.wait(b) or {}
                binding_ok &= eb.get('state') == 'exited' and eb.get('process') == rb.get('process')
                observed['binding'] = {'probes': probes, 'a': ea.get('state'), 'b_while_a_ended': b_after.get('state'),
                                       'b': eb.get('state')}
                check('dispatch/result-binding', binding_ok)
                receipts = writer.execute("SELECT COUNT(*) FROM entities WHERE kind='completion_receipt'").fetchone()[0]
                facts = gate.completion(ua)
                terminal = ea.get('termination') or {}
                printed = json.loads(a_out or b'{}')
                observed['terminal'] = {'termination': terminal, 'completion': facts, 'receipts': receipts,
                                        'worker_printed': printed}
                check('dispatch/terminal-not-completion',
                      receipts == 0 and not any(facts.values()) and ea.get('state') == 'exited'
                      and printed.get('revision_landed') == nonce and printed.get('landed') is True
                      and printed.get('dispatch_id') == b.dispatch_id and len(printed.get('worker_token') or '') == 16
                      and printed['worker_token'] not in json.dumps(ea) and printed['worker_token'] not in json.dumps(eb)
                      and terminal.get('returncode') == 0
                      and terminal.get('output_digest') == 'sha256:' + hashlib.sha256(a_out).hexdigest()
                      and terminal.get('output_bytes') == len(a_out) and entity(ua)['version'] == unit_version
                      and entity(ua)['data'].get('state') == 'CLAIMED')

            # VELDO-0131 (owner, Telegram 38184): the owner's signed stop request asks the existing stop mechanism.
            # A stale version and a member outside the project are refused and write nothing; the accepted request
            # is recorded on the dispatch with its state unchanged; the runner's sweep asks the receiver it holds
            # (Launch.stop) and records the ask; the receiver ends the worker and records its end as every end is;
            # nothing is recovered, retried or restarted.
            with region('dispatch/owner-stop'):
                member('owner-person', kind='person', roles=['project_owner'], scope=['p1'])
                member('stranger-person', kind='person', roles=['project_owner'], scope=['p9'])
                member('plain-person', kind='person', roles=[], scope=['p1'])
                us = admitted('VELDO-9340')
                stopping = runner.submit(us, 'build', **job(release='never-9340', deadline=STOP_ROW_DEADLINE))
                running_seen = marker_for(stopping.dispatch_id)
                sid = stopping.dispatch_id
                version = dispatches.version(sid)
                stale = attempt(lambda: dispatches.request_stop(sid, version + 1, 'owner-person', now=now(),
                                                                request='stop-stale'))
                outside = attempt(lambda: dispatches.request_stop(sid, version, 'stranger-person', now=now(),
                                                                  request='stop-outside'))
                roleless = attempt(lambda: dispatches.request_stop(sid, version, 'plain-person', now=now(),
                                                                   request='stop-roleless'))
                untouched = dispatches.version(sid) == version and not rec(sid).get('stop_request')
                started = WAITS.stamp()
                requested = attempt(lambda: dispatches.request_stop(sid, version, 'owner-person', now=now(),
                                                                    request='stop-1', channel='api'))
                held = rec(sid)
                pending_before = dispatches.stop_requests()
                swept = runner.honor_stops()
                # VELDO-0261: the end is waited on, bounded by the product's own obligation, and judged by its cause:
                # an unasked or ignored stop ends the worker otherwise, and the cause says so.
                waited = settle_stopped(stopping)
                finished = WAITS.stamp()
                ended = rec(sid)
                cause = stop_cause(stopping, ended)
                again = attempt(lambda: dispatches.request_stop(sid, dispatches.version(sid), 'owner-person',
                                                                now=now(), request='stop-2'))
                actors = [r[0] for r in writer.execute(
                    "SELECT principal FROM journal WHERE command_id LIKE ? ORDER BY seq",
                    ('dispatch/%stop%' + sid + '%',))]
                observed['owner_stop'] = {'stale': stale, 'outside': outside, 'roleless': roleless, 'requested': requested[0],
                                          'swept': swept, 'state': ended.get('state'), 'again': again,
                                          'stop_request': ended.get('stop_request'), 'asked_at': started.iso(),
                                          'ended_seen_at': finished.iso(),
                                          'actors': actors, 'termination': ended.get('termination'),
                                          'stop_requested': stopping.stop_requested, 'cause': cause, 'waited': waited}
                check('dispatch/owner-stop',
                      running_seen.get('dispatch') == sid
                      and stale == ('refused', 'stale_version') and outside == ('refused', 'not_authorized:scope')
                      and roleless == ('refused', 'not_authorized:role') and untouched
                      and requested[0] == 'ok' and held.get('state') == 'running'
                      and (held.get('stop_request') or {}).get('by') == 'owner-person'
                      and (held.get('stop_request') or {}).get('result') is None
                      and pending_before == [(sid, 'owner_stop')] and swept == [(sid, True)]
                      and waited is None and stopped_by_request(cause) and stopping.stop_requested is True
                      and dispatches.stop_requests() == []
                      and again[0] == 'refused' and str(again[1]).startswith('transition_refused:exited')
                      and actors == ['owner-person', 'runner']
                      and len(of_unit('dispatch', us)) == 1,
                      'cause %r; wait %s; observed %r' % (cause, waited or 'held', {k: v for k, v in observed['owner_stop'].items()
                                                                                 if k not in ('cause', 'waited')}))

            # A runner on the same store that does not hold the running dispatch leaves its stop request waiting
            # (another runner, e.g. control_launch_work's, may hold it); the holder asks on its own sweep.
            with region('dispatch/owner-stop-other-runner'):
                uo = admitted('VELDO-9341')
                held_run = runner.submit(uo, 'build', **job(release='never-9341', deadline=STOP_ROW_DEADLINE))
                oid = held_run.dispatch_id
                marker_for(oid)
                bystander = L.Runner(gate, reservations, dispatches, invoke, account=ACCOUNT)
                asked_by = attempt(lambda: dispatches.request_stop(oid, dispatches.version(oid), 'owner-person',
                                                                   now=now(), request='stop-other'))
                by_bystander = bystander.honor_stops()
                still = dispatches.stop_requests()
                by_holder = runner.honor_stops()
                waited = settle_stopped(held_run)  # waited on and judged as in dispatch/owner-stop
                settled = rec(oid)
                cause = stop_cause(held_run, settled)
                observed['owner_stop_other_runner'] = {'requested': asked_by[0], 'bystander': by_bystander,
                                                       'still': still, 'holder': by_holder,
                                                       'state': settled.get('state'),
                                                       'stop_request': settled.get('stop_request'), 'cause': cause,
                                                       'waited': waited}
                check('dispatch/owner-stop-other-runner',
                      asked_by[0] == 'ok' and by_bystander == [] and still == [(oid, 'owner_stop')]
                      and by_holder == [(oid, True)] and waited is None and stopped_by_request(cause),
                      'cause %r; wait %s; requested %r, bystander %r, still %r, holder %r'
                      % (cause, waited or 'held', asked_by, by_bystander, still, by_holder))

            # VELDO-0358: the order a busy machine showed in dispatch/owner-stop, made by the row. The runner asks the
            # receiver, which ends the worker and records the end; the runner's result reads the record's version
            # before that end and commits after it. The result is still the ask that was made, recorded by this
            # sweep: never refused as stale and left for a later sweep to record as not asked.
            with region('dispatch/owner-stop-ends-first'):
                ue = admitted('VELDO-9342')
                ending = runner.submit(ue, 'build', **job(release='never-9342', deadline=STOP_ROW_DEADLINE))
                eid = ending.dispatch_id
                marker_for(eid)
                requested_end = attempt(lambda: dispatches.request_stop(eid, dispatches.version(eid), 'owner-person',
                                                                        now=now(), request='stop-ends-first'))
                original_result, interleaved = dispatches.stop_result, {}

                def result_after_end(dispatch_id, asked, *, now):
                    if dispatch_id != eid or interleaved:
                        return original_result(dispatch_id, asked, now=now)
                    read = dispatches.version(eid)  # the version the result reads, before the end

                    def gone():
                        state = rec(eid).get('state')
                        return state not in D.STOPPABLE, {'state': state}
                    interleaved['end'] = WAITS.wait(
                        'the receiver of %s to record the end it was asked for' % eid, gone,
                        lambda: (ending.child.poll() is not None and rec(eid).get('state') in D.STOPPABLE,
                                 {'receiver_exit': ending.child.poll()}),
                        [WAITS.Store(db), WAITS.Pidfd(ending.child)]).outcome
                    interleaved['moved'] = (read, dispatches.version(eid))
                    dispatches.version = lambda _dispatch_id: read  # the read made before the end, now stale
                    try:
                        return original_result(dispatch_id, asked, now=now)
                    finally:
                        del dispatches.version
                dispatches.stop_result = result_after_end
                try:
                    swept_end = runner.honor_stops()
                finally:
                    del dispatches.stop_result
                if interleaved.get('end') == 'done' and ending.child.returncode is None:
                    # Exercise the closed-reader ordering on every run, before the diagnostic
                    # write in settle_stopped. Observe exit without reaping: settlement owns that.
                    WAITS.wait('the stopped receiver to exit before its diagnostic',
                               lambda: os.waitid(os.P_PID, ending.child.pid,
                                                 os.WEXITED | os.WNOWAIT | os.WNOHANG) is not None,
                               sources=[WAITS.Pidfd(ending.child)])
                waited_end = settle_stopped(ending)
                ended_first = rec(eid)
                cause_end = stop_cause(ending, ended_first)
                observed['owner_stop_ends_first'] = {'requested': requested_end[0], 'swept': swept_end,
                                                     'interleaved': interleaved, 'cause': cause_end,
                                                     'stop_request': ended_first.get('stop_request'),
                                                     'pending': dispatches.stop_requests(), 'waited': waited_end}
                check('dispatch/owner-stop-ends-first',
                      requested_end[0] == 'ok' and interleaved.get('end') == 'done'
                      and interleaved['moved'][1] > interleaved['moved'][0]
                      and swept_end == [(eid, True)] and waited_end is None and stopped_by_request(cause_end)
                      and ((ended_first.get('stop_request') or {}).get('result') or {}).get('by') == 'runner'
                      and dispatches.stop_requests() == [],
                      'observed %r' % (observed['owner_stop_ends_first'],))

            # Authority: only an active service member of this repository writes a record
            with region('dispatch/service-principals-only'):
                outsiders = {}
                target = accepted.dispatch_id
                version = dispatches.version(target)
                for principal in ('agent-worker', 'revoked-service', 'elsewhere-service', 'nobody'):
                    outsider = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal=principal,
                                            signer=principal, sign=sign)
                    outsiders[principal] = attempt(lambda: outsider.unknown(target, rec(target).get('contract_digest'),
                                                                            'forged', now=now()))
                receiving_ok = rec(target).get('state') == 'running' and dispatches.version(target) == version
                observed['authority'] = outsiders
                check('dispatch/service-principals-only',
                      all(v == ('refused', 'missing_authority') for v in outsiders.values()) and receiving_ok)
                # Registered for the next row: the accepted worker is released and ends normally.
                release('u3')
                runner.wait(accepted)

            with region('dispatch/observations'):
                status = dispatches.status()
                fields = {'schema', 'operation', 'domain', 'repository', 'unit', 'station', 'dispatch_id', 'request',
                          'accepted_versions', 'outcome'}
                refused_events = [e for e in events if e['outcome'] == 'refused']
                # The three dispatches this suite makes unknown on purpose; any other is named with its state and
                # the region that made it, so another row's failure is attributed to that row.
                made_unknown = {lost.dispatch_id, orphaned.dispatch_id, remote.dispatch_id}
                stray = {'extra': [(d, rec(d).get('state'), born.get(d, 'outside any region'))
                                   for d in sorted(set(status['stopped']) - made_unknown)],
                         'missing': [(d, rec(d).get('state'), born.get(d, 'outside any region'))
                                     for d in sorted(made_unknown - set(status['stopped']))]}
                obs_ok = (status['accepted'] > 0 and status['refused'] > 0
                          and set(status['stopped']) == made_unknown
                          and set(status['pending']) == {prepared_only['dispatch_id'], accepted_only['dispatch_id']}
                          and all(fields <= set(e) for e in events)
                          and all(e.get('refusal') and e.get('taxonomy') for e in refused_events)
                          and any(e['refusal'].startswith('active_dispatch:') and e['taxonomy'] == 'stale_subject' for e in refused_events)
                          and any(e['refusal'].startswith('dispatch_outcome_unknown:') and e['taxonomy'] == 'unknown_outcome'
                                  for e in refused_events)
                          and D.taxonomy('launch_evidence_missing') == 'unknown_outcome'
                          and D.taxonomy('spawn_failed:ENOENT') == 'unavailable_service'
                          and D.taxonomy('missing_authority:claim') == 'missing_authority'
                          and D.taxonomy('stale_input:admission') == 'stale_subject'
                          and D.taxonomy('incomplete_contract:source') == 'invalid_input'
                          and D.taxonomy('something-unnamed') == 'unknown_outcome')
                observed['status'] = status
                observed['event_sample'] = [e for e in events if e.get('unit') == u6][:4]
                check('dispatch/observations', obs_ok,
                      'unknown dispatches differ from the three made unknown on purpose: %r' % stray
                      if stray['extra'] or stray['missing'] else 'status %r' % status)

            # VELDO-0358 AC15: the profile reached every arming site this suite crosses, read from where each value
            # was used: the table in this process, the receiver's and the wrapper's start records (the running
            # message), the receiver-exit wait of a launch whose receiver ended by itself, and the orphan release.
            with region('timers/profile-applied'):
                hang = WAITS.WAIT_HANG_SECONDS
                launch_path = {'control_launch.' + n for n in (
                    'ACCEPT_SECONDS', 'RECEIVER_EXIT_SECONDS', 'ORPHAN_SECONDS', 'REQUEST_SECONDS', 'CENSUS_SECONDS',
                    'SOURCE_SECONDS', 'IDENTITY_SECONDS', 'NAMESPACE_SECONDS', 'FEEDER_SETTLE_SECONDS', 'FEEDER_SECONDS')} | {
                    'control_containment.SETTLE_SECONDS', 'control_containment.TOOL_SECONDS',
                    'control_heartbeat.SETTLE_SECONDS', 'control_heartbeat.SETUP_SECONDS',
                    'control_engine_claude.LOGIN_SECONDS', 'control_engine_claude.INIT_SECONDS',
                    'control_engine_codex.LOGIN_SECONDS', 'control_engine_codex.CATALOG_SECONDS'}

                def unset(report):
                    """timer_unset: each entry of a report not at the hang bound, and each launch-path timer absent."""
                    report = report or []
                    named = {r['name']: r['value'] for r in report}
                    return sorted([n for n, v in named.items() if v != hang] + [n + ':absent' for n in launch_path - set(named)])
                running = next((m for m in first_messages if m.get('event') == 'running'), {}) if first_messages else {}
                started = (running.get('timers') or {})
                orphan_release = [o for o in runner.observations if o.get('operation') == 'release_account'
                                  and o.get('dispatch_id') == orphaned.dispatch_id]
                profile = {'in_process': unset(TIMERS.report()), 'receiver': unset(started.get('receiver')),
                           'wrapper': unset(started.get('wrapper')), 'receiver_exit': first.receiver_exit,
                           'orphan': [(o.get('outcome'), o.get('awaited')) for o in orphan_release]}
                observed['timers'] = profile
                check('timers/profile-applied',
                      profile['in_process'] == [] and profile['receiver'] == [] and profile['wrapper'] == []
                      and first.receiver_exit == {'awaited': 'pidfd', 'bound': hang, 'ended_by': 'exit'}
                      and len(orphan_release) == 1 and orphan_release[0].get('outcome') == 'released'
                      and 'bound' not in orphan_release[0].get('awaited', ['bound'])
                      and set(orphan_release[0]['awaited']) <= {'cgroup.events', 'pidfd', 'none'},
                      'timer_unset %r' % profile)

            # VELDO-0358 AC10, AC15: the census over brief E's files finds no site outside the declared exceptions:
            # the four suites (every rule, each read through its literal anchor, which the mutation driver substitutes
            # for a registered mutant of it) and the launch path's engine modules (R3, read from the copies this suite
            # installed). Suite 63 holds the same row, so a mutant of this suite's own file is read there.
            with region('wave1/no-sites'):
                census = load('v39_census', ROOT / 'scripts' / 'check_wallclock.py')
                suites = {'62_veldo_0039_dispatch.py': ROOT / "scripts/suites" / "62_veldo_0039_dispatch.py",
                          '63_veldo_0040_containment.py': ROOT / "scripts/suites" / "63_veldo_0040_containment.py",
                          '78_veldo_0060_claude_adapter.py': ROOT / "scripts/suites" / "78_veldo_0060_claude_adapter.py",
                          '106_veldo_0185_dispatch_setup.py': ROOT / "scripts/suites" / "106_veldo_0185_dispatch_setup.py"}
                engine = ('control_launch.py', 'control_containment.py', 'control_heartbeat.py',
                          'control_engine_claude.py', 'control_engine_codex.py', 'policy_contract.py')
                found = []
                for name, path in suites.items():
                    rel = 'scripts/suites/' + name
                    found += census.Python(rel, Path(path).read_text(), census.RULES).scan()
                for name in engine:
                    rel = 'engine/.veldo/' + name
                    found += census.Python(rel, (mods / name).read_text(), ('R3',), engine=True).scan()
                excepted = census.load_list(ROOT / census.EXCEPTIONS, True)[0]
                counts, first_site = census.counted(found)
                over = sorted('%s:%s %s (%s) in %s' % (first_site[k]['file'], first_site[k]['line'], k[1],
                                                       first_site[k]['form'], k[3])
                              for k, n in counts.items() if n > excepted.get(k, 0))
                observed['no_sites'] = over
                check('wave1/no-sites', not over, 'sites outside the declared exceptions: %r' % over[:20])

            with region('dispatch/installed-assets'):
                scaffold = load('v39_scaffold', mods / 'init_scaffold.py')
                check('dispatch/installed-assets', '.veldo/control_dispatch.py' in scaffold._FILES
                      and '.veldo/control_launch.py' in scaffold._FILES)
        finally:
            for path in releases:
                path.write_text('go')
            for data in worker_markers():
                if proc_identity(data['pid']) == data['start']:
                    with contextlib.suppress(OSError):
                        os.killpg(data['pid'], signal.SIGKILL)
            for launch in launches:
                with contextlib.suppress(Exception):
                    if launch.child.poll() is None:
                        launch.child.kill()
                    launch.child.wait()  # killed above, or already ended
                    launch.child.stdout.close()
            for conn in connections:
                conn.close()
            with contextlib.suppress(Exception):
                subprocess.run(['systemctl', '--user', 'stop', worker_slice], capture_output=True,
                               timeout=WAITS.WAIT_HANG_SECONDS,
                               stdin=subprocess.DEVNULL, env=dict(os.environ, XDG_RUNTIME_DIR=os.environ.get(
                                   'XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()))
            TIMERS.reset_profile()
            if harness is None:
                os.environ.pop('VELDO_CONTROL_TEST_HARNESS', None)
            else:
                os.environ['VELDO_CONTROL_TEST_HARNESS'] = harness
            if owner_session is None:
                os.environ.pop('V39_OWNER_SESSION', None)
            else:
                os.environ['V39_OWNER_SESSION'] = owner_session
        # One row per region saying it ran to its end: a driven mutation must red its named row by
        # a failed assertion while that row's own region still completes.
        for first_label in regions:
            check('ran/' + first_label, first_label not in {label for label, _ in raised})
        observed['raised'] = raised
        globals()['_V39_OBSERVED'] = observed


_v39_suite()
