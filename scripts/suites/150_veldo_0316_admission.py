"""VELDO-0316: real store, Ledger, reservations, Runner and dispatch transitions.

The eligibility decision, configuration binding and source resolver are fixtures. The receiver
seam accepts through Dispatches and starts a real short child. No live engine or process reader
is used. The asynchronous rows use the real serial Consumer and its pipe, without a timer loop.
"""


def _v316_suite():
    import copy
    import importlib.util
    import json
    import os
    from pathlib import Path
    import select
    import shutil
    import subprocess
    import sys
    import tempfile
    import time
    import traceback
    import types
    from unittest.mock import patch

    PRODUCTION = {
        'control_space_admission.py': ROOT / ".veldo" / "control_space_admission.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_dispatch.py': ROOT / ".veldo" / "control_dispatch.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }
    rows = {}

    def check(row, label, good):
        rows.setdefault(row, []).append((label, bool(good)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location('v316_' + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='veldo-0316-') as temporary:
        base = Path(temporary)
        mods = base / '.veldo'
        mods.mkdir()
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        L = load('launch', mods / 'control_launch.py')
        A, D, RES = L.ADMISSION, L.D, L.D.RES
        S = load('store', mods / 'control_store.py')
        SP = load('space', mods / 'control_space.py')
        CFG = load('config', mods / 'control_space_config.py')
        YAML = load('yaml', mods / 'yamlish.py')
        K = load('kinds', mods / 'control_space_kinds.py')
        SV = load('service', mods / 'control_service.py')
        CON = load('consumer', mods / 'control_space_consumer.py')
        serial = [0]

        def sign(message):
            return 'fixture:' + S.digest_of(message.decode())

        class Fixture:
            def __init__(self, name, act=True):
                self.root = base / name
                self.repo = self.root / 'project'
                (self.repo / '.veldo').mkdir(parents=True)
                self.file = self.repo / '.veldo' / 'space.yaml'
                self.file.write_text('needs: {}\n')
                self.state = self.root / 'state'
                self.state.mkdir()
                config = CFG.check({'enabled': True, 'time_zone': 'UTC',
                    'pools': {'host': {'floor': 20, 'needs': {'build': 100, 'review': 100, 'gate': 100}},
                              'image': {'floor': 10, 'needs': {'build': 40, 'review': 40, 'gate': 40}}},
                    'engines': ['fixture'], 'scratch_roots': {'roots': [str(self.root / 'scratch')],
                        'session_pattern': 'sessions/{working_folder}/{session_id}'},
                    'build_roots': [], 'plain_repositories': [], 'client_accounts': [],
                    'protect': {'paths': [], 'volumes': [], 'containers': [], 'images': [],
                                'networks': [], 'compose_projects': []}})
                project = dict(CFG.read_project(str(self.repo), YAML.read, config=config), repository=str(self.repo))
                self.conn = S.open_store(str(self.root / 'store.sqlite3'))
                self.ledger = SP.Ledger(S, self.conn, 'runner', sign, config=config,
                    state_root=str(self.state), host='fixture', projects=[project],
                    lifecycle={'version': K.REGISTRY['version'],
                               **{k: K.REGISTRY['tables'][K.REGISTRY['version']][k] for k in ('events', 'ends_on')}})
                A.accepted(self.ledger.set_pool('host', 'filesystem', device=self.ledger.device(str(self.repo))))
                A.accepted(self.ledger.set_pool('image', 'engine_image', engine='fixture', backing='host'))
                self.scope = {'type': 'project', 'id': 'project'}
                # Mode prerequisites have their own suites. Seed their accepted outcome here only.
                if act:
                    self.seed(SP.mode_id(self.scope), SP.MODE_KIND, {'scope': self.scope, 'mode': 'act'})
                self.seed('runner', 'membership', dict(principal_type='service', roles=['reservation_service'],
                    scope=['repository'], revoked_at=None, expires_at=None))
                self.seed('project:project', 'project', {'name': 'project'})
                self.free = {'host': 119, 'image': 1000}
                self.reads = []
                self.space = {'ledger': self.ledger, 'free': self.read_free}
                self.reservations = RES.Reservations(S, self.conn, domain='domain', repository='repository',
                    principal='runner', authorize=lambda conn, command: True, signer='runner', sign=sign)
                self.dispatches = D.Dispatches(S, self.conn, domain='domain', repository='repository',
                    principal='runner', signer='runner', sign=sign)
                for scope, subject in [('account', 'account'), ('project', 'project')]:
                    self.reservations.configure('policy/' + subject, scope, subject,
                        dict(capacity=50, invocations=100, wall_seconds=10000), now=time.time())
                self.gate = types.SimpleNamespace(unit_record=lambda unit: {'project': 'project'},
                    require=self.decision, decide=lambda station, unit, context=None:
                    dict(self.decision(station, unit, context), eligible=True))
                self.started = []
                self.units = set()
                self.runner = L.Runner(self.gate, self.reservations, self.dispatches, self.invoke,
                                       account='account', space=self.space)
                # Existing sweeps test containment and removal elsewhere. No run is left in this fixture.
                self.runner.sweep = lambda: None

            def seed(self, identity, kind, data):
                encoded = json.dumps(data, sort_keys=True)
                self.conn.execute('INSERT OR REPLACE INTO entities(id,kind,version,digest,data) VALUES(?,?,?,?,?)',
                                  (identity, kind, 1, D.digest(data), encoded))
                self.conn.commit()

            def read_free(self, pool):
                self.reads.append((os.getpid(), pool['name']))
                return self.free[pool['name']]

            def decision(self, station, unit, context=None):
                return dict(decision_id='decision', station=station, unit=unit, domain_uuid='domain',
                            watermark=1, inputs={'fixture': True})

            def offer(self, unit='unit', station='review', submit=False):
                if unit not in self.units:
                    self.reservations.configure('policy/' + unit, 'unit', unit,
                        dict(capacity=10, invocations=100, wall_seconds=10000), now=time.time())
                    self.units.add(unit)
                with patch.object(L.CFG, 'bind', lambda *args: args[-1]), patch.object(
                        L, 'resolve_source', lambda *args: {'commit': 'a' * 40, 'tree': 'b' * 40}):
                    return (self.runner.submit if submit else self.runner.prepare)(unit, station,
                        holder='builder', source=str(self.repo), revision='HEAD', payload={'task': 'fixture'},
                        adapter='fixture', configuration={}, deadline=time.time() + 60)

            def invoke(self, contract):
                identity = dict(platform='linux', host='fixture', boot_id='fixture', pid=os.getpid(), start='1')
                self.dispatches.accept(contract['dispatch_id'], D.digest(contract),
                                       dict(identity, principal='runner'), now=time.time())
                child = subprocess.run([sys.executable, '-c', 'print("started")'], capture_output=True, check=True)
                self.started.append(child.stdout)
                self.dispatches.run(contract['dispatch_id'], D.digest(contract), identity, now=time.time())
                record = self.dispatches.record(contract['dispatch_id'])
                return types.SimpleNamespace(owned=True, contract=contract, dispatch_id=contract['dispatch_id'],
                    record=record, result='accepted', pump=lambda **kwargs: False)

            def request(self, unit='unit', station='build'):
                return A.prepare(self.space, repository='repository', project='project', unit=unit,
                                 station=station, attempt=1)

            def no_dispatch(self):
                return not self.conn.execute("SELECT 1 FROM entities WHERE kind IN ('dispatch','dispatch_active')").fetchone()

            def slots(self):
                return [json.loads(row[0]) for row in self.conn.execute(
                    "SELECT data FROM entities WHERE kind='subscription_reservation'")
                    if json.loads(row[0]).get('type') == 'worker']

            def close(self):
                self.conn.close()

        fixtures = []
        consumer = None
        def fixture(name, act=True):
            f = Fixture(name, act)
            fixtures.append(f)
            return f

        def refused(call):
            try:
                return call(), None
            except Exception as error:
                return None, error

        try:
            for value in (99, 100, 119, 120, 121):
                f = fixture('boundary-' + str(value))
                f.free['host'] = value
                result = f.request()
                check('ac1/floor-boundaries', str(value), result['ok'] == (value >= 120))
                if value < 120:
                    check('ac1/floor-boundaries', 'numbers ' + str(value), result.get('reason') ==
                        dict(pool='host', need=100, free=value, held=0, floor=20))
            f = fixture('held')
            A.accepted(f.ledger.place_hold('other', {'host': 80, 'image': 30},
                                         {'host': 'default', 'image': 'default'}))
            A.accepted(f.ledger.admit('other', 'advised', dict(pool='host', need=80, free=0, held=0, floor=20),
                                     used={'host': 30, 'image': 99}))
            f.free.update(host=169, image=50)
            result = f.request()
            check('ac1/other-holds', 'advised counted and used subtracted', (result.get('reason') or {}).get('held') == 50)
            f.free['host'] = 170
            result = f.request('second')
            check('ac1/other-holds', 'exact boundary and usage clamped', result['ok'])
            f = fixture('image')
            f.free.update(host=1000, image=49)
            result = f.request()
            check('ac1/second-pool', 'engine pool waits', result.get('code') == 'space_wait:image')

            f = fixture('waiting')
            contract, error = refused(f.offer)
            check('ac2/before-reservation', 'wait code', getattr(error, 'code', '') == 'space_wait:host')
            check('ac2/before-reservation', 'no dispatch, deadline or active index', f.no_dispatch())
            check('ac2/before-reservation', 'no slot or reservation', not f.slots())
            check('ac2/before-reservation', 'no command started', not f.started)
            count = f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
            reads = len(f.reads)
            for _ in range(3):
                refused(f.offer)
            check('ac2/recorded-wait', 'no ledger writes', count ==
                  f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0])
            check('ac2/recorded-wait', 'no free-space polling', len(f.reads) == reads)
            check('ac2/recorded-wait', 'one hold only', len(f.ledger.holds()) == 1)
            line = object.__new__(SV.Line)
            line.repository, line.gate, line.runner, line.workspace = 'repository', f.gate, f.runner, str(f.repo)
            line.hosts = {'fixture': 'fixture'}
            line.loop = types.SimpleNamespace(saw_end=lambda *args: None)
            report = {'waiting': [], 'refused': [], 'offered': []}
            with patch.object(L.CFG, 'bind', lambda *args: args[-1]):
                SV.Line.offer(line, report, 'unit', 'review', {'identity': 'builder', 'adapter': 'fixture',
                    'configuration': {}, 'seconds': 60, 'payload': {}}, revision='HEAD')
            check('ac2/factory-waiting', 'only waiting', len(report['waiting']) == 1 and not report['refused'])
            check('ac2/factory-waiting', 'numbers preserved', report['waiting'] and report['waiting'][0].get('numbers') ==
                  dict(pool='host', need=100, free=119, held=0, floor=20))

            f = fixture('report', act=False)
            launch, error = refused(lambda: f.offer(submit=True))
            check('ac3/report-starts', 'prepared and started', launch is not None and f.started == [b'started\n'])
            holds = list(f.ledger.holds().values())
            check('ac3/report-starts', 'advised with numbers', len(holds) == 1 and holds[0]['state'] == 'advised'
                  and holds[0]['reason'] == dict(pool='host', need=100, free=119, held=0, floor=20))
            check('ac3/report-starts', 'reservation exists', len(f.slots()) == 1)
            f = fixture('contract-digest')
            f.free['host'] = 1000
            launch = f.offer(submit=True)
            if launch:
                original = f.dispatches.record(launch.dispatch_id)
                changed = copy.deepcopy(launch.contract)
                changed['space']['needs']['host'] += 1
                check('ac4/contract-digest', 'needs change digest', D.digest(changed) != original['contract_digest'])
                changed = copy.deepcopy(launch.contract)
                changed['space']['hold'] += '-other'
                check('ac4/contract-digest', 'identity changes digest', D.digest(changed) != original['contract_digest'])
                check('ac4/contract-digest', 'stored unchanged', original['contract_digest'] == D.digest(launch.contract))

            f = fixture('acceptance')
            f.free['host'] = 1000
            contract = f.offer()
            A.accepted(f.ledger.release(contract['space']['hold']))
            _, error = refused(lambda: f.invoke(contract))
            check('ac2/acceptance-rechecks', 'released promise stops start',
                  str(getattr(error, 'code', '')).startswith('space_hold_unavailable:') and not f.started)
            f.runner.cancel_prepared(contract, 'fixture_cancel')
            check('ac2/cancel-releases', 'cancelled hold released',
                  f.ledger.hold(contract['space']['hold'])['state'] == 'released')
            f = fixture('cancel')
            f.free['host'] = 1000
            contract = f.offer()
            f.runner.cancel_prepared(contract, 'fixture_cancel')
            check('ac2/cancel-releases', 'fresh promise released on refusal',
                  f.ledger.hold(contract['space']['hold'])['state'] == 'released')
            again = f.offer()
            check('ac2/cancel-releases', 'later attempt new promise', again['space']['hold'] != contract['space']['hold'])

            def history(f, sizes, project='project', station='build', state='exited', start=1):
                for index, used in enumerate(sizes, start):
                    identity = '%s-%s-%d' % (project, station, index)
                    A.accepted(f.ledger.place_hold(identity, {'host': 100, 'image': 40},
                                                  {'host': 'default', 'image': 'default'}))
                    A.accepted(f.ledger.release(identity, used=used))
                    f.seed('dispatch:' + identity, 'dispatch', dict(state=state, history=[{'at': index}],
                        contract=dict(dispatch_id=identity, station=station, reservation={'project': project},
                                      space={'hold': identity})))

            f = fixture('one-run')
            history(f, [{'host': 1, 'image': 1}])
            result = f.request()
            check('ac4/one-run-default', 'single small run does not admit', not result['ok'])
            check('ac4/one-run-default', 'default source and need', result['source']['host'] == 'default'
                  and result['space']['needs']['host'] == 100)
            f = fixture('five-runs')
            history(f, [{'host': n, 'image': n} for n in (999, 10, 30, 20, 40, 25)])
            history(f, [{'host': 9999, 'image': 9999}] * 5, project='foreign', start=20)
            history(f, [{'host': 8888, 'image': 8888}] * 5, station='review', start=30)
            history(f, [{'host': 7777, 'image': 7777}], state='refused', start=40)
            needs, sources = A.needs_of(f.ledger, 'project', 'build')
            check('ac4/last-five', 'largest of last five for same project and station',
                  needs == {'host': 40, 'image': 40} and sources == {'host': 'measured', 'image': 'measured'})
            f.file.write_text(YAML.dump({'needs': {'build': {'host': 7}}}))
            needs, sources = A.needs_of(f.ledger, 'project', 'build')
            check('ac4/project-file', 'declared wins per pool', needs == {'host': 7, 'image': 40}
                  and sources == {'host': 'declared', 'image': 'measured'})
            f.file.write_text(YAML.dump({'needs': {'build': {'host': 0}}}))
            check('ac4/project-file', 'zero is declared', A.needs_of(f.ledger, 'project', 'build')[0]['host'] == 0)
            f = fixture('unmeasured')
            history(f, [{'host': 1, 'image': 2}] * 4 + [{}])
            check('ac4/unmeasured-default', 'missing measurement is not zero',
                  A.needs_of(f.ledger, 'project', 'build')[1] == {'host': 'default', 'image': 'default'})
            f = fixture('legacy')
            f.ledger.config['enabled'] = False
            contract = f.offer()
            check('ac4/off-and-legacy', 'off reads no pool', contract['space'] is None and not f.reads)
            legacy = copy.deepcopy(contract)
            legacy.pop('space')
            check('ac4/off-and-legacy', 'old contract shape accepted', not D.contract_problems(legacy))
            stored = f.dispatches.record(contract['dispatch_id'])
            stored.update(contract=legacy, contract_digest=D.digest(legacy))
            f.seed(D.record_id(contract['dispatch_id']), D.RECORD_KIND, stored)
            f.dispatches.accept(contract['dispatch_id'], D.digest(legacy), dict(platform='linux', host='fixture',
                boot_id='fixture', pid=os.getpid(), start='1', principal='runner'), now=time.time())
            check('ac4/off-and-legacy', 'stored legacy accepts with original digest',
                  f.dispatches.record(contract['dispatch_id'])['state'] == 'accepted'
                  and f.dispatches.record(contract['dispatch_id'])['contract_digest'] == D.digest(legacy))

            f = fixture('measurement')
            f.free['host'] = 1000
            contract = f.offer()
            run = contract['dispatch_id']
            owner = {'scope': f.scope, 'ticket': 'VELDO-9001', 'run': {'id': run, 'station': 'review'}}
            item = A.accepted(f.ledger.declare('scratch', {'path': str(f.root / 'scratch' / 'run')},
                                             owner, 'seam'))['item']
            A.accepted(f.ledger.confirm(item))
            A.accepted(f.ledger.measure(item, 37, 'run_finished'))
            released = L.space_release(f.space, contract['space']['hold'], run=run)
            check('ac4/finished-measurement', 'measured run stored on released hold', released['released']
                  and f.ledger.hold(contract['space']['hold'])['used'] == {'host': 37, 'image': 0})

            f = fixture('pool-metrics', act=False)
            f.request()
            snapshot = A.metrics(f.ledger, f.read_free)
            check('ac1/metrics', 'free floor and held', snapshot['pools']['host'] ==
                  dict(free=119, floor=20, held=100))
            check('ac1/metrics', 'hold states', snapshot['holds'] == dict(admitted=0, waiting=0, advised=1))
            f = fixture('unread-free')
            f.free['host'] = -1
            result = f.request()
            check('ac1/unread-pool', 'negative free never admits', result.get('code') == 'space_free_unread:host')
            f = fixture('bad-file')
            f.file.write_text('needs: invalid\n')
            result = f.request()
            check('ac4/unread-declaration', 'bad declaration no hold', not result['ok'] and not f.ledger.holds())

            f = fixture('reservation-failure')
            f.free['host'] = 1000
            with patch.object(f.reservations, 'reserve_worker', side_effect=D.Refused('no_account')):
                _, error = refused(f.offer)
            check('ac2/reservation-failure', 'promise released', getattr(error, 'code', None) == 'no_account'
                  and all(h['state'] == 'released' for h in f.ledger.holds().values()) and not f.slots())
            contract = f.offer()
            check('ac2/reservation-failure', 'retry fresh promise same dispatch attempt', contract['attempt'] == 1
                  and f.ledger.hold(contract['space']['hold'])['state'] == 'admitted')

            f = fixture('racing-preparation')
            f.free['host'] = 1000
            original = f.dispatches.prepare
            winner = []
            def competing(contract, **kwargs):
                other = copy.deepcopy(contract)
                other['dispatch_id'] += '-winner'
                f.reservations.reserve_worker('worker/' + other['dispatch_id'], other['dispatch_id'],
                    'account', 'project', 'unit', now=time.time())
                entity, version, digest = f.runner._slot(other['dispatch_id'])
                other['reservation'].update(entity=entity, version=version, digest=digest)
                original(other, **kwargs)
                winner.append(other)
                return original(contract, **kwargs)
            with patch.object(f.dispatches, 'prepare', competing):
                _, error = refused(f.offer)
            check('ac2/racing-prepare', 'loser does not release winner promise', winner
                  and str(getattr(error, 'code', '')).startswith('active_dispatch:')
                  and f.ledger.hold(winner[0]['space']['hold'])['state'] == 'admitted')

            f = fixture('concurrent')
            f.free['host'] = 120
            children = []
            ready_read, ready_write = os.pipe()
            try:
                for name in ('first', 'second'):
                    read, write = os.pipe()
                    pid = os.fork()
                    if pid == 0:
                        try:
                            os.close(read)
                            os.close(ready_write)
                            registry = dict(f.conn.command_registry)
                            f.conn.close()
                            f.ledger.conn = S.open_store(str(f.root / 'store.sqlite3'))
                            f.ledger.conn.command_registry.update(registry)
                            os.read(ready_read, 1)
                            result = f.request(name)
                            os.write(write, json.dumps(result).encode())
                            os._exit(0)
                        except BaseException:
                            os._exit(1)
                    os.close(write)
                    children.append((pid, read))
                os.write(ready_write, b'xx')
                answers = []
                for pid, read in children:
                    poller = select.poll()
                    poller.register(read, select.POLLIN | select.POLLHUP)
                    if not poller.poll(10000):
                        raise RuntimeError('admission worker timeout')
                    answers.append(json.loads(os.read(read, 65536)))
                    _, status = os.waitpid(pid, 0)
                    check('ac1/concurrent', 'child completed', status == 0)
                check('ac1/concurrent', 'one promise at exact capacity',
                      sorted(a.get('answer') for a in answers) == ['admitted', 'waiting'])
            finally:
                os.close(ready_read)
                os.close(ready_write)
                for pid, read in children:
                    os.close(read)
                    try:
                        os.kill(pid, 9)
                        os.waitpid(pid, 0)
                    except ProcessLookupError:
                        pass

            f = fixture('async')
            seen = f.root / 'reader-pid'
            read, write = os.pipe()
            def blocked_free(pool):
                seen.write_text(str(os.getpid()))
                os.read(read, 1)
                return f.free[pool['name']]
            f.space['free'] = blocked_free
            wakes = []
            consumer = CON.Consumer(f.ledger)
            service = types.SimpleNamespace(space=f.space, space_consumer=consumer)
            requests = A.Requests(service, types.SimpleNamespace(wake=lambda *args: wakes.append(args)))
            given = dict(repository='repository', project='project', unit='unit', station='build', attempt=1)
            receiver = f.root / 'receiver.json'
            receiver.write_text(json.dumps({'workspace': str(f.repo), 'state_root': str(f.state),
                                             'adapters': {}}))
            service.domain, service.principal, service.sign, service.generation = 'domain', 'runner', sign, 1
            service.conn = f.conn
            loop = types.SimpleNamespace(service=service, wake=lambda *args: wakes.append(args))
            actual_line = SV.Line(loop, 'repository', {}, str(receiver))
            check('ac2/service-wiring', 'production line uses worker admission',
                  actual_line.runner.admission.__self__ is actual_line.space_admission
                  and actual_line.runner.space is f.space)
            before = time.monotonic()
            answer = requests.prepare(**given)
            check('ac2/worker-responsive', 'returns pending without reader wait', answer.get('code') == 'space_pending'
                  and time.monotonic() - before < 1)
            requests.prepare(**given)
            check('ac2/worker-responsive', 'coalesced task', len(consumer.tasks) == 1)
            pid = consumer.active[1]
            os.write(write, b'xx')
            deadline = time.monotonic() + 10
            while consumer.active and time.monotonic() < deadline:
                poller = select.poll()
                poller.register(consumer.active[0], select.POLLIN | select.POLLHUP)
                if poller.poll(10000):
                    consumer.readable(consumer.active[0])
            check('ac2/worker-responsive', 'reader ran in child', seen.exists() and int(seen.read_text()) == pid)
            check('ac2/completion-wakes', 'one completion wake', len(wakes) == 1)
            answer = requests.prepare(**given)
            check('ac2/completion-wakes', 'actual waiting answer with numbers', answer.get('code') == 'space_wait:host'
                  and answer.get('reason', {}).get('free') == 119 and consumer.active is None)
            check('ac2/completion-wakes', 'worker reaped', not Path('/proc/%d' % pid).exists())
            before = f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
            requests.prepare(**given)
            check('ac2/recorded-wait', 'completed task not resubmitted', consumer.active is None
                  and before == f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0])
            os.close(read)
            os.close(write)
            consumer.stop()
            consumer = None

            def pump(consumer):
                deadline = time.monotonic() + 10
                while consumer.active and time.monotonic() < deadline:
                    poller = select.poll()
                    poller.register(consumer.active[0], select.POLLIN | select.POLLHUP)
                    if poller.poll(10000):
                        consumer.readable(consumer.active[0])

            def worker(f, wakes):
                consumer = CON.Consumer(f.ledger)
                service = types.SimpleNamespace(space=f.space, space_consumer=consumer)
                return consumer, A.Requests(service, types.SimpleNamespace(wake=lambda *args: wakes.append(args)))

            # Fix 1: a failed first judgment is reported once and judged afresh on the next pass.
            for mode, act in (('act', True), ('report', False)):
                f = fixture('failed-reader-' + mode, act=act)
                f.free['host'] = -1
                wakes = []
                consumer, requests = worker(f, wakes)
                first = requests.prepare(**given)
                pump(consumer)
                failed = requests.prepare(**given)
                check('fix1/failed-judgment', mode + ' failure reported once', first.get('code') == 'space_pending'
                      and failed.get('code') == 'space_free_unread:host' and consumer.active is None)
                f.free['host'] = 1000
                again = requests.prepare(**given)
                check('fix1/failed-judgment', mode + ' second pass submits again',
                      again.get('code') == 'space_pending' and consumer.active is not None)
                pump(consumer)
                healthy = requests.prepare(**given)
                check('fix1/failed-judgment', mode + ' healthy reader judged afresh', healthy.get('ok') is True
                      and healthy.get('answer') == 'admitted' and len(wakes) == 2
                      and [h['state'] for h in f.ledger.holds().values()] == ['admitted'])
                kept = requests.prepare(**given)
                check('fix1/failed-judgment', mode + ' answer with a hold is kept', kept == healthy
                      and consumer.active is None and not consumer.tasks)
                consumer.stop()
                consumer = None
        except Exception:
            check('setup', traceback.format_exc(), False)
        finally:
            if consumer is not None:
                consumer.stop()
            for f in fixtures:
                f.close()
        for row, checks in sorted(rows.items()):
            bad = '; '.join(label for label, good in checks if not good)
            if bad:
                print('DETAIL space316/' + row + ': ' + bad)
            expect('space316/' + row, bool(checks) and all(good for _, good in checks))


_v316_suite()
