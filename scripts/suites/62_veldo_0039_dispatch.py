"""VELDO-0039: durable dispatch contracts, launch results and bound observations, over a real store.

Only shared ROOT and expect are consumed. One temporary tree holds the installed .veldo copy the
runner loads AND the receiver process executes, so a registered mutation of either production
module reaches both. Real SQLite store, OpenSSH journal signatures, a real Git source repository,
VELDO-0052's eligibility Gate, VELDO-0036 reservations, the VELDO-0031 claim transition, and real
receiver and worker processes whose OS identity is read back from /proc. The worker is a fixture
engine (it reads the store to report what it saw at its start, prints claims and exits); it
qualifies no live engine.
"""


def _v39_suite():
    import contextlib
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
    import time

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

    fast = '/dev/shm' if os.path.isdir('/dev/shm') and os.access('/dev/shm', os.W_OK) else None
    with tempfile.TemporaryDirectory(prefix='v39-', dir=fast) as directory:
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
        EL = load('v39_eligibility', mods / 'control_eligibility.py')
        RES = load('v39_reservations', mods / 'control_reservations.py')
        SIG = load('v39_signer', mods / 'control_signer.py')
        GP = load('v39_git', mods / 'git_process.py')
        CLM = D.CLM
        DOMAIN, REPOSITORY, ACCOUNT, HOLDER = 'domain-39', 'repository-39', 'acct-39', 'builder-1'
        private = base / 'private'
        private.mkdir(mode=0o700)
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(private / 'journal')],
                       check=True, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)

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
                                   dict(capacity=50, invocations=50, wall_seconds=5000), now=time.time())
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
        # was launched under) and what the store holds for its dispatch at its start, then reads its
        # packet, waits for a release file when told to, prints its payload's claims plus a token of
        # its own and exits with the payload's code. It records what it printed, byte for byte.
        markers = base / 'markers'
        markers.mkdir()
        worker = base / 'engine.py'
        worker.write_text('''import json, os, sqlite3, sys, time
from pathlib import Path
store, markers = sys.argv[1], Path(sys.argv[2])
dispatch = os.environ.get('VELDO_DISPATCH_ID', '')
printed = b''
if sys.argv[3:] == ['forge']:
    # A worker claiming to be another process, in the same line format the wrapper uses.
    printed = (json.dumps({'schema': 'veldo.launch_identity/v1', 'process': {
        'platform': 'linux', 'host': 'forged', 'boot_id': 'forged', 'pid': 1, 'start': '1'}}) + '\\n').encode()
    sys.stdout.buffer.write(printed)
    sys.stdout.flush()
try:
    db = sqlite3.connect('file:%s?mode=ro' % store, uri=True, timeout=10)
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
if payload.get('release'):
    end = time.time() + 60
    while not Path(payload['release']).exists() and time.time() < end:
        time.sleep(0.02)
out = json.dumps(dict(payload.get('say', {}), worker_token=os.urandom(8).hex())).encode()
(markers / ('%d.out' % os.getpid())).write_bytes(printed + out)
sys.stdout.buffer.write(out)
sys.stdout.flush()
sys.exit(payload.get('code', 0))
''')
        config = base / 'receiver.json'
        config.write_text(json.dumps({
            'store': str(db), 'journal_key': str(private / 'journal'), 'principal': 'launch-receiver',
            'domain': DOMAIN, 'repository': REPOSITORY, 'authority_generation': 1,
            'adapters': {'fixture-engine': {'argv': [sys.executable, '-B', str(worker), str(db), str(markers)],
                                            'environment': {'ENGINE_PROFILE': 'configured-profile'}},
                         'missing-engine': {'argv': [str(base / 'no-such-engine')]},
                         # Through the trusted wrapper, as a launch on another host runs it (the
                         # transport prefix, ssh to the Mac, is configuration; here it is local).
                         'wrapped-engine': {'identity': 'reported', 'argv': [
                             sys.executable, '-B', str(mods / 'control_launch.py'), 'exec',
                             sys.executable, '-B', str(worker), str(db), str(markers), 'forge']},
                         'wrapped-missing': {'identity': 'reported', 'argv': [
                             sys.executable, '-B', str(mods / 'control_launch.py'), 'exec', str(base / 'no-such-engine')]}}}))
        CONFIGURATION = {'mcp_servers': {'veldo': {'command': 'veldo-mcp', 'args': ['serve', REPOSITORY]},
                                         'tracker': {'command': 'tracker-mcp', 'args': []}},
                         'tools': ['Read', 'Edit', 'Bash', 'WebFetch'], 'model': 'configured-model'}
        events = []
        gate = EL.Gate(S, reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY)
        dispatches = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='runner',
                                  signer='runner', sign=sign, observe=events.append)
        receiving = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal='launch-receiver',
                                 signer='launch-receiver', sign=sign)
        # The same writer connection: both services register the one dispatch operation on it.
        launches = []

        def invoke(contract, environment=None, before=None):
            if before:
                before()
            launch = L.invoke(config, contract, dispatches, accept_seconds=20, environment=environment)
            launches.append(launch)
            return launch

        runner = L.Runner(gate, reservations, dispatches, invoke, account=ACCOUNT)
        releases = []

        def job(release=None, say=None, code=0, adapter='fixture-engine', deadline=120):
            payload = {'task': 'build the unit', 'code': code, 'say': say or {'status': 'working'}}
            if release:
                payload['release'] = str(base / ('release-' + release))
                releases.append(Path(payload['release']))
            return dict(holder=HOLDER, source=str(src), revision='HEAD', payload=payload, adapter=adapter,
                        configuration=CONFIGURATION, deadline=time.time() + deadline)

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

        def marker_for(dispatch_id, timeout=10.0):
            end = time.time() + timeout
            while time.time() < end:
                for data in worker_markers():
                    if data.get('dispatch') == dispatch_id:
                        return data
                time.sleep(0.02)
            return {}

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

        def check(label, condition):
            emitted.add(label)
            expect('VELDO-0039 ' + label, bool(condition))

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
                seen_record = seen.get('seen') or {}
                packet_path = markers / ('%s.packet' % seen.get('pid'))
                end = time.time() + 10
                while not packet_path.exists() and time.time() < end:
                    time.sleep(0.02)
                packet = json.loads(packet_path.read_text()) if packet_path.exists() else {}
                order = [journal_seq('dispatch/%s/%s/' % (a, first.dispatch_id)) for a in ('prepare', 'accept', 'run')]
                given = contract.get('input') or {}
                decision = given.get('decision') or {}
                bindings = {
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
                    'deadline': isinstance(contract.get('deadline'), float) and contract['deadline'] > time.time(),
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
                                            now=time.time())
                rslot = entity(RES.entity('worker', [DOMAIN, rival['dispatch_id']]))
                rival['reservation'] = dict(contract.get('reservation') or {}, entity=RES.entity('worker', [DOMAIN, rival['dispatch_id']]),
                                            version=rslot['version'], digest=rslot['digest'])
                # The next attempt number, so only the active dispatch can refuse it.
                rival['attempt'] = 2
                direct = attempt(lambda: dispatches.prepare(rival, now=time.time()))
                release('u1-a')
                ended = runner.wait(first)
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
                                barrier.wait(timeout=20)
                                return original(*args, **kwargs)
                            mine_dispatches.prepare = together
                            racer = L.Runner(EL.Gate(store, mine_reader, domain_uuid=DOMAIN, repository_uuid=REPOSITORY),
                                             mine_reservations, mine_dispatches,
                                             lambda c: L.invoke(config, c, mine_dispatches, accept_seconds=20),
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
                    racer_thread.join(timeout=60)
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
                # engine's own process after exec; the line the worker forges after it is output.
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

            with region('dispatch/unknown-never-relaunched'):
                before = dispatches.version(lost.dispatch_id)
                resubmit = attempt(lambda: runner.submit(u6, 'build', **job()))
                fresh = dict(rec(lost.dispatch_id).get('contract') or {}, dispatch_id='dispatch/%s/fresh' % u6, attempt=2)
                reservations.reserve_worker('worker/' + fresh['dispatch_id'], fresh['dispatch_id'], ACCOUNT, 'p1', u6,
                                            now=time.time())
                fslot = entity(RES.entity('worker', [DOMAIN, fresh['dispatch_id']]))
                fresh['reservation'] = dict(fresh.get('reservation') or {}, entity=RES.entity('worker', [DOMAIN, fresh['dispatch_id']]),
                                            version=fslot['version'], digest=fslot['digest'])
                direct = attempt(lambda: dispatches.prepare(fresh, now=time.time()))
                again = invoke(rec(lost.dispatch_id).get('contract'))
                ended_again = invoke(rec(first.dispatch_id).get('contract'))
                time.sleep(0.2)
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
                # The receiver that owns the running worker is stopped: the outcome is unknown.
                orphaned.child.kill()
                orphaned.child.wait(timeout=10)
                r7 = runner.wait(orphaned) or {}
                p7 = r7.get('process') or {}
                if p7.get('pid') and proc_identity(p7['pid']) == p7.get('start'):
                    os.killpg(p7['pid'], signal.SIGKILL)
                u8, u9 = admitted('VELDO-9308'), admitted('VELDO-9309')
                prepared_only = runner.prepare(u8, 'build', **job())
                accepted_only = runner.prepare(u9, 'build', **job())
                me = dict(L.process_identity(os.getpid()), principal='launch-receiver')
                receiving.accept(accepted_only['dispatch_id'], D.digest(accepted_only), me, now=time.time())
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
                        call = {'prepare': lambda: dispatches.prepare(r.get('contract'), now=time.time()),
                                'accept': lambda: receiving.accept(target, digest_, me, now=time.time()),
                                'run': lambda: receiving.run(target, digest_, L.process_identity(os.getpid()), now=time.time()),
                                'exit': lambda: receiving.exit(target, digest_, r.get('process'), termination, now=time.time()),
                                'refuse': lambda: receiving.refuse(target, digest_, 'probe', now=time.time()),
                                'unknown': lambda: receiving.unknown(target, digest_, 'probe', now=time.time())}[action]
                        refusals[(state, action)] = attempt(call)
                        unchanged &= dispatches.version(target) == version
                expected_refusals = {(state, action): ('refused', 'duplicate_dispatch' if action == 'prepare'
                                                       else 'transition_refused:%s:%s' % (state, action))
                                     for (state, action) in refusals}
                observed['transitions'] = {'derived': sorted(map(str, derived)), 'walked_by_real_records': sorted(map(str, walked)),
                                           'disallowed': {'%s/%s' % k: v for k, v in sorted(refusals.items())},
                                           'running_lost': r7.get('state')}
                check('dispatch/transitions-from-schema',
                      set(D.STATES) == {'prepared', 'accepted', 'running', 'exited', 'refused', 'unknown'}
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
                                                                    a_result, now=time.time())),
                    'a_process_under_b_digest': attempt(lambda: receiving.exit(b.dispatch_id, rb.get('contract_digest'),
                                                                               ra.get('process'), a_result, now=time.time())),
                    'a_stop_to_b': attempt(lambda: receiving.unknown(b.dispatch_id, ra.get('contract_digest'), 'lost',
                                                                     now=time.time())),
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

            # Authority: only an active service member of this repository writes a record
            with region('dispatch/service-principals-only'):
                outsiders = {}
                target = accepted.dispatch_id
                version = dispatches.version(target)
                for principal in ('agent-worker', 'revoked-service', 'elsewhere-service', 'nobody'):
                    outsider = D.Dispatches(S, writer, domain=DOMAIN, repository=REPOSITORY, principal=principal,
                                            signer=principal, sign=sign)
                    outsiders[principal] = attempt(lambda: outsider.unknown(target, rec(target).get('contract_digest'),
                                                                            'forged', now=time.time()))
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
                obs_ok = (status['accepted'] > 0 and status['refused'] > 0
                          and set(status['stopped']) == {lost.dispatch_id, orphaned.dispatch_id}
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
                check('dispatch/observations', obs_ok)

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
                    launch.child.wait(timeout=10)
                    launch.child.stdout.close()
            for conn in connections:
                conn.close()
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


_v39_started = __import__('time').monotonic()
_v39_suite()
_V39_SECONDS = __import__('time').monotonic() - _v39_started
