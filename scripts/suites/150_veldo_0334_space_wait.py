"""VELDO-0334: waiting holds, freeing transactions and the space wake.

Real temporary store, Ledger, Signal, rules, folder remover, Runner, FactoryLoop and Consumer.
Eligibility, source, free bytes, empty engine responses and the process table are fixtures.
Only scratch made in this suite is removed. No live engine or host process reader is used.
"""


def _v334_suite():
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
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
        'control_space_admission.py': ROOT / ".veldo" / "control_space_admission.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_dispatch.py': ROOT / ".veldo" / "control_dispatch.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }
    rows = {}

    def check(row, label, good):
        rows.setdefault(row, []).append((label, bool(good)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location('v334_' + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    with tempfile.TemporaryDirectory(prefix='veldo-0334-') as temporary:
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
        SIG = load('signal', mods / 'control_space_signal.py')

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

        def mark(f, why, pool='host', freed=1):
            if why == 'reconcile':
                return f.ledger.reconcile('console', [], [], {key: 0 for key in SP.RECONCILE_COUNTS})
            if why == 'release':
                A.accepted(f.ledger.place_hold('released/' + pool, {pool: 1}, {pool: 'default'}))
                return f.ledger.release('released/' + pool)
            item = scratch(f, 'outcome/' + pool + '/' + str(len(f.ledger.items())), pool=pool)
            A.accepted(f.ledger.signal('run_finished', {'run': item[1]}))
            return f.ledger.outcome(item[0], 'removed', {'freed': freed})

        def scratch(f, name, pool='host'):
            path = f.root / 'scratch' / name
            path.mkdir(parents=True)
            (path / 'payload').write_bytes(b'x' * 4096)
            run = 'fixture/' + name
            made = A.accepted(f.ledger.declare('scratch', {'path': str(path)},
                {'scope': f.scope, 'run': {'id': run, 'station': 'build'}}, 'seam', pool=pool))
            A.accepted(f.ledger.confirm(made['item']))
            return made['item'], run, path

        def factory(svc, offer):
            loop = object.__new__(SV.FactoryLoop)
            loop.service, loop.wakes, loop.ended, loop.trees = svc, [], [], {}
            loop.passes, loop.timer, loop.counts, loop.conversation = 0, None, {}, None
            loop.lines = {'repository': types.SimpleNamespace(run=lambda report, ended: offer(report))}
            loop.provision = lambda *args: None
            loop.follow_store = lambda *args: {}
            loop.remove_closed = lambda: []
            loop.pipes = lambda: {}
            return loop

        def wired(f):
            svc = object.__new__(SV.Service)
            svc.conn, svc.loop, svc.api, svc.projects_due = f.conn, None, None, False
            svc.config, svc.domain, svc.space_seen, svc.principal = {}, 'domain', None, 'runner'
            svc.space_docker = None
            svc._log = lambda *args: None
            svc.space = f.space
            loop = factory(svc, lambda report: None)
            svc.loop = loop
            return svc, loop, A.Requests(svc, loop)

        def drain(svc):
            while svc.space_consumer.active:
                descriptor = svc.space_consumer.active[0]
                poller = select.poll()
                poller.register(descriptor, select.POLLIN | select.POLLHUP)
                if not poller.poll(10000):
                    raise RuntimeError('worker did not complete')
                svc.space_readable(descriptor)

        given = dict(repository='repository', project='project', unit='unit', station='build', attempt=1)
        real_organ = A._organ
        calls = []
        real_signal = SIG.signal
        def counted(*args, **kwargs):
            calls.append((args[1], args[2]))
            return real_signal(*args, **kwargs)
        SIG.signal = counted
        A._organ = lambda name: SIG if name == 'control_space_signal' else real_organ(name)
        try:
            f = fixture('four-offers')
            first = f.request()
            identity = first['space']['hold']
            nreads, journal = len(f.reads), f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
            reports = []
            svc = types.SimpleNamespace(domain='domain', principal='runner', _log=lambda *args: None)
            loop = factory(svc, lambda report: reports.append(f.request()))
            for source in ('journal', 'account_reset', 'run_end'):
                if source == 'account_reset':
                    loop.timer = 0
                    check('ac1/one-signal', 'timer is due', loop.due(0))
                loop.wake(source)
                report = loop.run()
                check('ac1/one-signal', source + ' recorded answer', reports[-1] == first
                      and source in report['sources'])
            del svc
            check('ac1/one-signal', 'four offers one Signal', calls == [('admission_requested', {'pool': 'host'})])
            check('ac1/one-signal', 'asked persisted', f.ledger.hold(identity)['retry_asked'])
            check('ac2/no-read-or-write', 'no free reads or writes on three passes', len(f.reads) == nreads
                  and journal == f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0])
            f.free['host'] = 10000
            loop.wake('account_reset')
            loop.run()
            check('ac2/manual-free-timer', 'manual freeing does not admit', reports[-1] == first
                  and len(f.reads) == nreads)
            # The public admit entry, also used outside Runner, obeys the same rule.
            direct = A.admit(f.ledger, identity, f.read_free)
            check('ac2/public-admit', 'cached waiting answer', direct['answer'] == 'waiting' and len(f.reads) == nreads)

            for why in ('outcome', 'release', 'reconcile'):
                f = fixture('mark-' + why)
                first = f.request()
                identity = first['space']['hold']
                svc, loop, requests = wired(f)
                requests.answers[tuple(given[k] for k in ('repository', 'unit', 'station', 'attempt'))] = first
                A.accepted(mark(f, why))
                check('ac3/' + why, 'mark set by commit', f.ledger.hold(identity)['freed'])
                svc.hint_after(0)
                check('ac3/' + why, 'space wake source', any(w['source'] == 'space' for w in loop.wakes))
                loop.wakes.clear()
                svc.hint_after(0)
                check('ac3/' + why, 'notification read once', not any(w['source'] == 'space' for w in loop.wakes))
                before_calls = len(calls)
                f.request()
                check('ac3/' + why, 'short pool clears mark after judging', not f.ledger.hold(identity)['freed']
                      and len(calls) == before_calls)
                svc.space_stop()

            f = fixture('pool-isolation')
            host = f.request()['space']['hold']
            A.accepted(f.ledger.place_hold('image-only', {'image': 5000}, {'image': 'default'}))
            A.accepted(f.ledger.admit('image-only', 'waiting', dict(pool='image', need=5000, free=0, held=0, floor=10)))
            for amount in (0, -1, None):
                A.accepted(mark(f, 'outcome', freed=amount))
                check('ac3/nonfreeing', str(amount), not f.ledger.hold(host)['freed'])
            A.accepted(mark(f, 'release', pool='host'))
            check('ac3/pool-isolation', 'unrelated pool stays clear', f.ledger.hold(host)['freed']
                  and not f.ledger.hold('image-only')['freed'])
            # A refused freeing command changes neither hold nor journal.
            f.request()
            before = f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
            refusal = f.ledger.reconcile('not-a-source', [], [], {})
            check('ac3/refusal-atomic', 'no mark on refused write', not refusal['ok']
                  and not f.ledger.hold(host)['freed'] and before == f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0])

            f = fixture('waiting-set-race')
            identity = f.request()['space']['hold']
            execute = f.ledger.store.execute
            injected = []
            def concurrent_hold(conn, command, *args, **kwargs):
                if command['operation'] == SP.RECONCILE and not injected:
                    injected.append(True)
                    A.accepted(f.ledger.place_hold('arrived', {'host': 100}, {'host': 'default'}))
                return execute(conn, command, *args, **kwargs)
            with patch.object(f.ledger.store, 'execute', concurrent_hold):
                A.accepted(mark(f, 'reconcile'))
            check('ac3/waiting-set-race', 'new hold marked with the freeing transaction',
                  f.ledger.hold(identity)['freed'] and f.ledger.hold('arrived')['freed'])
            transition = json.loads(f.conn.execute('SELECT transition FROM journal ORDER BY seq DESC LIMIT 1').fetchone()[0])
            check('ac3/waiting-set-race', 'cause and both marks in one record',
                  sum(v['kind'] == SP.HOLD_KIND for v in transition.values()) == 2
                  and any(v['kind'] == SP.RECONCILE_KIND for v in transition.values()))

            f = fixture('backing')
            identity = f.request()['space']['hold']
            image = A.accepted(f.ledger.declare('image_tag', {'engine': 'fixture', 'name': 'fixture:owned'},
                {'scope': f.scope, 'run': {'id': 'fixture-image', 'station': 'build'}}, 'seam', pool='image'))['item']
            A.accepted(f.ledger.confirm(image))
            A.accepted(f.ledger.signal('ticket_ended', {'run': 'fixture-image'}))
            A.accepted(f.ledger.outcome(image, 'removed', {'freed': 0, 'host': {'pool': 'host', 'freed': 1}}))
            check('ac3/backing-pool', 'positive host delta marks host waiter', f.ledger.hold(identity)['freed'])

            f = fixture('race')
            identity = f.request()['space']['hold']
            A.accepted(mark(f, 'release'))
            fired = []
            def racing_free(pool):
                answer = f.free[pool['name']]
                if not fired:
                    fired.append(True)
                    f.free['host'] = 10000
                    A.accepted(mark(f, 'reconcile'))
                return answer
            f.space['free'] = racing_free
            result = f.request()
            check('ac3/free-during-judgment', 'new mark not lost by old judgment', result['ok']
                  and f.ledger.hold(identity)['state'] == 'admitted' and not f.ledger.hold(identity)['freed'])

            # Exercise real Signal, rules and folder remover on only fixture-owned scratch.
            f = fixture('signal-removes')
            item, run, path = scratch(f, 'deferred')
            A.accepted(f.ledger.signal('run_finished', {'run': run}))
            A.accepted(f.ledger.outcome(item, 'deferred', {'rule': 'in_use'}))
            keep_item, keep_run, keep_path = scratch(f, 'stays')
            P = load('probe', mods / 'control_space_probe.py')
            R = load('remove', mods / 'control_space_remove.py')
            proc = f.root / 'proc'
            proc.mkdir()
            f.space.update(probe=P, kinds=K, remover=R, proc=str(proc),
                           owner_live=lambda owner: {'conclusive': True, 'group_empty': True},
                           run=lambda argv, cwd=None: (0, '') if argv[0] == 'docker' else P._run(argv, cwd))
            f.space['free'] = lambda pool: 119 if path.exists() else 10000
            result = f.request()
            check('ac1/signal-can-admit', 'retry goes through real remover: ' + repr((result, f.ledger.item(item))), result['ok']
                  and not path.exists() and f.ledger.item(item)['state'] == 'removed')
            check('ac1/signal-can-admit', 'present scratch untouched', keep_path.exists()
                  and f.ledger.item(keep_item)['state'] == 'present')

            # Clock stopped: only the freeing task pipe and space wake drive preparation.
            f = fixture('frozen-loop')
            item, run, path = scratch(f, 'finished')
            proc = f.root / 'proc'
            proc.mkdir()
            f.space.update(probe=P, kinds=K, remover=R, proc=str(proc),
                owner_live=lambda owner: {'conclusive': True, 'group_empty': True},
                run=lambda argv, cwd=None: (0, '') if argv[0] == 'docker' else P._run(argv, cwd))
            f.space['free'] = lambda pool: 119 if path.exists() and pool['name'] == 'host' else 10000
            first = f.request(station='review')
            identity = first['space']['hold']
            svc, loop, requests = wired(f)
            f.runner.admission = requests.prepare
            key = ('repository', 'unit', 'review', 1)
            requests.answers[key] = first
            def removal():
                return real_signal(f.ledger, 'run_finished', {'run': run},
                    **{key: value for key, value in f.space.items() if key != 'ledger'})
            svc.space_consumer.submit(('fixture-removal',), removal)
            drain(svc)
            # Stop the clock and drive the real factory pass only from the required source.
            offered = []
            loop.lines['repository'].run = lambda report, ended: offered.append(refused(f.offer))
            check('ac3/stopped-clock', 'worker outcome: ' + repr(svc.space_consumer.last_answer),
                  svc.space_consumer.last_answer.get('ok') and not path.exists())
            loop.wakes = [wake for wake in loop.wakes if wake['source'] == 'space']
            with patch.object(SV, 'time', types.SimpleNamespace(time=lambda: 12345)):
                report = loop.run()
                if offered:
                    check('ac3/stopped-clock', 'retry queued off loop', getattr(offered[-1][1], 'code', '') == 'space_pending')
                    drain(svc)
                    loop.run()
            prepared = offered[-1][0] if offered else None
            check('ac3/stopped-clock', 'removal alone prepares with clock stopped', prepared is not None
                  and f.ledger.hold(identity)['state'] == 'admitted' and len(f.slots()) == 1)
            svc.space_stop()
            # Existing one-shot gate/wrapper adapters keep their admission signature.
            f = fixture('legacy-adapter', act=False)
            class Adapter:
                def __getattr__(self, name):
                    return getattr(f.ledger, name)
                def admit(self, identity, answer, reason=None, principal=None, command_id=None):
                    return f.ledger.admit(identity, answer, reason, principal=principal, command_id=command_id)
            A.accepted(f.ledger.place_hold('wrapped', {'host': 100}, {'host': 'default'}))
            result = A.admit(Adapter(), 'wrapped', f.read_free)
            check('compat/one-shot-adapter', 'existing report adapter remains advised', result['answer'] == 'advised')
            seen = {'operation': SP.RELEASE, 'command_id': 'fixture-release',
                    'wrote': {SP.hold_id('waiting'): {'state': 'waiting'}, SP.hold_id('wrapped'): {'state': 'released'}}}
            result = f.ledger._original(seen, {'parameters': {'hold': 'wrapped'}})
            check('ac3/release-replay', 'release replay answers the target hold', result['state'] == 'released')

            # Fix round 1, finding 1: report mode never blocks, whatever Signal does.
            def refusing(*args, **kwargs):
                calls.append((args[1], args[2]))
                return {'ok': False, 'reason': 'space_fixture_refused'}
            def dying(*args, **kwargs):
                raise RuntimeError('fixture: the worker is lost inside Signal')
            for name, broken in (('refused', refusing), ('lost', dying)):
                f = fixture('report-' + name, act=False)
                SIG.signal = broken
                try:
                    first = f.request()
                finally:
                    SIG.signal = counted
                identity = next(iter(f.ledger.holds()))
                hold = f.ledger.hold(identity)
                check('fix1/report-refused-signal', name + ': the hold is advised with its one request claimed: '
                      + repr((first, hold['state'])), hold['state'] == 'advised' and hold['retry_asked']
                      and hold['reason']['pool'] == 'host' and (first['ok'] or name == 'lost'))
                before_calls = len(calls)
                second = f.request()
                check('fix1/report-refused-signal', name + ': the next offer is advised and asks nothing',
                      second['ok'] and second['answer'] == 'advised' and second['space']['hold'] == identity
                      and len(calls) == before_calls)
            f = fixture('act-refused')
            SIG.signal = refusing
            try:
                first = f.request()
            finally:
                SIG.signal = counted
            hold = f.ledger.hold(first['space']['hold']) if first.get('space') else {}
            check('fix1/act-refused-signal', 'a refused Signal still answers waiting, by numbers: ' + repr(first),
                  first.get('code') == 'space_wait:host' and hold.get('state') == 'waiting'
                  and hold.get('retry_asked') and hold['reason']['pool'] == 'host')

            f = fixture('completion-race')
            svc, loop, requests = wired(f)
            result = requests.prepare(**given)
            check('ac3/completion-race', 'initial request queued', result['code'] == 'space_pending')
            pid = svc.space_consumer.active[1]
            descriptor = os.pidfd_open(pid)
            poller = select.poll()
            poller.register(descriptor, select.POLLIN)
            try:
                if not poller.poll(10000):
                    raise RuntimeError('initial worker did not end')
            finally:
                os.close(descriptor)
            # The child committed waiting, but the parent still has no answer cached.
            A.accepted(mark(f, 'reconcile'))
            drain(svc)
            f.free['host'] = 10000
            result = requests.prepare(**given)
            check('ac3/completion-race', 'old answer cannot hide newer mark', result['code'] == 'space_pending')
            drain(svc)
            check('ac3/completion-race', 'retry admitted', requests.prepare(**given)['ok'])
            svc.space_stop()
        except Exception:
            check('setup', traceback.format_exc(), False)
        finally:
            if consumer is not None:
                consumer.stop()
            if 'svc' in locals() and hasattr(svc, 'space_stop'):
                svc.space_stop()
            for f in fixtures:
                f.close()
        for row, checks in sorted(rows.items()):
            bad = '; '.join(label for label, good in checks if not good)
            if bad:
                print('DETAIL space334/' + row + ': ' + bad)
            expect('space334/' + row, bool(checks) and all(good for _, good in checks))


_v334_suite()
