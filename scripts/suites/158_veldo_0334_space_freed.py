"""VELDO-0334: event-driven admission on real ledger, Runner and factory loop.

Fixture clock is stopped. Worker completion uses a pipe, never a sleep; every
subprocess timeout is a 120-second hang detector. Eligibility and account policy
are fixture seams; Signal, removal rules, dispatch and journal wakes are production.
"""


def _v334_suite():
    import copy
    import importlib.util
    import io
    import json
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile
    import types
    from unittest.mock import patch

    PRODUCTION = {
        'control_space_admission.py': ROOT / ".veldo" / "control_space_admission.py",
        'control_space.py': ROOT / '.veldo' / 'control_space.py',
        'control_space_signal.py': ROOT / '.veldo' / 'control_space_signal.py',
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_dispatch.py': ROOT / ".veldo" / "control_dispatch.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }
    # A mutant must retain the complete row inventory, including checks after a refused launch.
    rows = {name: [] for name in (
        'ac1/one-signal', 'ac1/retry-removes', 'ac1/pool-only',
        'ac2/timer-still-waits', 'ac2/no-read-write', 'ac2/clear-after-judgment',
        'ac3/removal-wakes', 'ac3/release-wakes', 'ac3/reconcile-wakes',
        'ac3/pool-only', 'ac3/nonfreeing-no-mark', 'ac3/journal-marks',
        'race/freeing-during-judgment', 'ac3/worker-wakes')}

    def check(row, condition):
        rows.setdefault(row, []).append(bool(condition))

    with tempfile.TemporaryDirectory(prefix='veldo-0334-') as temporary:
        root = Path(temporary)
        mods = root / 'installed'
        mods.mkdir()
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)

        def load(name):
            spec = importlib.util.spec_from_file_location('v334_' + name, mods / (name + '.py'))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

        L, SV, ADM, SP, CFG, YAML, K = map(load, ('control_launch', 'control_service',
            'control_space_admission', 'control_space', 'control_space_config', 'yamlish', 'control_space_kinds'))
        D, S, CM = L.D, L.D.S, L.D.CM
        D._claim_bound = lambda conn, contract: None  # fixture eligibility/claim authority
        key = root / 'owner'
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(key)],
                       check=True, capture_output=True, timeout=120)

        def sign(message):
            return subprocess.run(['ssh-keygen', '-Y', 'sign', '-f', str(key), '-n', CM.AC.SIGNATURE_NAMESPACE],
                                  input=message, capture_output=True, check=True, timeout=120).stdout.decode()

        class Fixture:
            def __init__(self, name, mode='act'):
                self.root = root / name
                self.repo = self.root / 'orchard'
                self.state = self.root / 'state'
                (self.repo / '.veldo').mkdir(parents=True)
                self.state.mkdir()
                self.now, self.serial, self.started = 1000, 0, []
                gp = load('git_process')
                for args in (['init', '-q', '-b', 'main'], ['add', '.'], ['commit', '--allow-empty', '-q', '-m', 'fixture']):
                    gp.run(['git', '-C', str(self.repo), *args], check=True, capture_output=True,
                           timeout=120, identity=('Fixture', 'fixture@example.invalid'))
                self.conn = S.open_store(str(self.state / 'store.sqlite3'))
                self.sign = lambda message: 'stub:' + S.digest_of(message.decode())
                self.put('runner', 'membership', dict(principal_type='service', roles=['reservation_service'],
                    scope=['repository'], revoked_at=None, expires_at=None))
                self.put('owner', 'membership', dict(principal_type='person', roles=['project_owner'], scope='*',
                    public_key=key.with_suffix('.pub').read_text(), revoked_at=None, expires_at=None))
                self.put('owner-key', 'verification_key', dict(principal='owner',
                    public_key=key.with_suffix('.pub').read_text(), effective_at=0, revoked_at=None))
                self.units = set()
                self.config = dict(present=True, enabled=True, time_zone='UTC',
                    pools={'host': {'floor': 20, 'needs': {'build': 100, 'review': 100, 'gate': 100}},
                           'image': {'floor': 5, 'needs': {'build': 30, 'review': 30, 'gate': 30}}},
                    engines=['fixture'], scratch_roots={'roots': [str(self.root)], 'session_pattern': 'sessions/{session_id}'},
                    build_roots=[], plain_repositories=[], client_accounts=[], protect=[])
                self.project = dict(CFG.read_project(str(self.repo), YAML.read, config=self.config,
                                                      stream=io.StringIO()), repository=str(self.repo))
                self.scope = {'type': 'project', 'id': 'orchard'}
                self.ledger = SP.Ledger(S, self.conn, 'runner', self.sign, config=self.config,
                    projects=[self.project], state_root=str(self.state), host='fixture', lifecycle=K.LIFECYCLE,
                    act_checks={name: lambda scope: None for name, _ticket in SP.ACT_CONDITIONS})
                assert self.ledger.set_pool('host', 'filesystem', device=self.ledger.device(str(self.root)))['ok']
                assert self.ledger.set_pool('image', 'engine_image', engine='fixture', backing='host')['ok']
                self.mode(mode)
                self.free = {'host': 1000, 'image': 1000}
                self.space = {'ledger': self.ledger, 'free': lambda pool: self.free[pool['name']]}
                self.dispatches = D.Dispatches(S, self.conn, domain='domain', repository='repository',
                                              principal='runner', signer='runner', sign=self.sign)
                self.reservations = D.RES.Reservations(S, self.conn, domain='domain', repository='repository',
                    principal='runner', signer='runner', sign=self.sign, authorize=lambda conn, command: True)
                for scope, subject in [('account', 'account'), ('project', 'project')]:
                    self.reservations.configure('policy/' + subject, scope, subject,
                        dict(capacity=100, invocations=100, wall_seconds=100000), now=self.now)
                self.gate = types.SimpleNamespace(require=self.decision, decide=self.decision,
                                                   unit_record=lambda unit: {'project': 'project'})
                self.runner = L.Runner(self.gate, self.reservations, self.dispatches, self.receive,
                                       account='account', clock=lambda: self.now, space=self.space)
                self.runner.sweep = lambda: None  # no old workers in this fixture

            def put(self, identity, kind, data):
                self.serial += 1
                prior = self.conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()
                S.execute(self.conn, dict(command_id='fixture/' + str(self.serial), nonce='fixture/' + str(self.serial),
                    principal='runner', operation='upsert_entity', artifact_digests=[],
                    expected_versions={identity: prior[0] if prior else 0},
                    parameters={'entity_id': identity, 'kind': kind, 'data': data}), 'runner', self.sign, 1)

            def mode(self, mode):
                if self.ledger.mode_of(self.scope) == mode:
                    return
                self.serial += 1
                command = dict(command_id='mode/' + str(self.serial), nonce='mode/' + str(self.serial),
                    principal='owner', operation='space_mode', parameters={'scope': self.scope, 'mode': mode})
                result = self.ledger.set_mode({'command': command, 'signature': sign(S.canonical_bytes(command))}, CM, self.now)
                assert result['ok'], result

            def decision(self, station, unit, context=None):
                if unit not in self.units:
                    self.reservations.configure('policy/' + unit, 'unit', unit,
                        dict(capacity=100, invocations=100, wall_seconds=100000), now=self.now)
                    self.units.add(unit)
                return dict(eligible=True, refusals=[], decision_id='decision/' + unit, station=station, unit=unit,
                            domain_uuid='domain', watermark=1, inputs={'team_assignment': 'fixture'})

            def job(self):
                return dict(holder='builder', source=str(self.repo), revision='HEAD', payload={}, adapter='fixture',
                            configuration={}, deadline=10000)

            def prepare(self, unit='unit', station='build'):
                with patch.object(L.CFG, 'bind', side_effect=lambda *args: args[-1]):
                    return self.runner.prepare(unit, station, **self.job())

            def receive(self, contract):
                identity = {'platform': 'linux', 'host': 'fixture', 'boot_id': 'fixture', 'pid': 1, 'start': 'fixture'}
                digest = D.digest(contract)
                self.dispatches.accept(contract['dispatch_id'], digest, dict(identity, principal='runner'), now=self.now)
                # The child reports the record it observes at birth; its end is synchronized by communicate.
                program = "import sqlite3,json,sys; c=sqlite3.connect(sys.argv[1]); print(json.loads(c.execute('SELECT data FROM entities WHERE id=?',(sys.argv[2],)).fetchone()[0])['state'])"
                child = subprocess.Popen([sys.executable, '-c', program, str(self.state / 'store.sqlite3'),
                                          D.record_id(contract['dispatch_id'])], stdout=subprocess.PIPE, text=True)
                output, _ = child.communicate(timeout=120)
                assert child.returncode == 0 and output.strip() == 'accepted', output
                process = dict(identity, pid=child.pid)
                record = self.dispatches.run(contract['dispatch_id'], digest, process, now=self.now)
                self.started.append(contract['dispatch_id'])
                return types.SimpleNamespace(contract=contract, dispatch_id=contract['dispatch_id'], record=record,
                                             result='accepted', owned=True, pump=lambda read=False: False)

            def finish(self, contract, sizes):
                self.receive(contract)
                record = self.dispatches.record(contract['dispatch_id'])
                self.now += 1
                self.dispatches.exit(contract['dispatch_id'], record['contract_digest'], record['process'],
                    dict(returncode=0, signal=None, output_digest=D.digest(''), output_bytes=0, deadline_stop=False), now=self.now)
                assert self.ledger.release(contract['space']['hold'], used=sizes)['ok']

            def tables(self):
                return {kind: self.conn.execute('SELECT count(*) FROM entities WHERE kind=?', (kind,)).fetchone()[0]
                        for kind in ('dispatch', 'dispatch_active', 'subscription_reservation')}

            def close(self):
                self.conn.close()

        def run(row, body):
            try:
                body()
            except Exception as error:
                check(row, False)
                print('space334 detail', row, type(error).__name__, str(error))

        def wired(name):
            f = Fixture(name)
            f.reads, f.signals, f.logs = [], [], []
            def free(pool):
                f.reads.append(pool['name'])
                return f.free[pool['name']]
            f.space['free'] = free
            signal = f.ledger.signal
            def counted(event, subject, **kwargs):
                f.signals.append((event, subject))
                return signal(event, subject, **kwargs)
            f.ledger.signal = counted
            service = object.__new__(SV.Service)
            service.conn, service.domain, service.principal = f.conn, 'domain', 'runner'
            service._space, service.space_seen = f.space, service.watermark()
            service._log = f.logs.append
            loop = object.__new__(SV.FactoryLoop)
            loop.service, loop.wakes, loop.ended, loop.timer = service, [], [], None
            loop.passes, loop.counts, loop.last, loop.conversation = 0, {}, None, None
            loop.provision = lambda report, caller: None
            loop.follow_store = lambda cause: {}
            loop.remove_closed = lambda: []
            line = object.__new__(SV.Line)
            line.repository, line.workspace, line.gate, line.runner = 'repository', str(f.repo), f.gate, f.runner
            line.service, line.hosts, line.loop = service, {}, loop
            role = dict(identity='builder', adapter='fixture', payload={}, configuration={}, seconds=10000)
            def offer(report, ended):
                with patch.object(L.CFG, 'bind', side_effect=lambda *args: args[-1]):
                    SV.Line.offer(line, report, 'unit', 'build', role, revision='HEAD')
            line.run = offer
            loop.lines, service.loop = {'repository': line}, loop
            f.service, f.loop = service, loop
            return f

        def pass_from(f, source):
            f.loop.wake(source)
            with patch.object(SV.time, 'time', return_value=f.now):
                return f.loop.run()

        def waiting(f):
            f.free['host'] = 110
            report = pass_from(f, 'journal')
            assert len(report['waiting']) == 1, report
            return next(iter(f.ledger.holds()))

        def repeated():
            f = wired('repeated')
            try:
                identity = waiting(f)
                before = (len(f.reads), f.service.watermark())
                reports = [pass_from(f, source) for source in ('run_end', 'account_reset', 'working_tree')]
                check('ac1/one-signal', f.signals == [('admission_requested', {'pool': 'host'})]
                      and f.ledger.hold(identity)['retry_asked'] and all(r['waiting'] for r in reports))
                check('ac2/no-read-write', before == (len(f.reads), f.service.watermark()))
                numbers = dict(f.ledger.hold(identity)['reason'])
                f.free['host'] = 1000  # owner freed bytes by hand, no ledger write
                report = pass_from(f, 'account_reset')
                check('ac2/timer-still-waits', bool(report['waiting']) and not report['offered']
                      and f.ledger.hold(identity)['state'] == 'waiting'
                      and report['waiting'][0]['space'] == numbers)
            finally:
                f.close()
        run('ac1/one-signal', repeated)

        def item(f, name, pool='host'):
            path = f.root / name
            path.mkdir()
            (path / 'payload').write_bytes(b'fixture output')
            owner = {'scope': f.scope, 'run': {'station': 'build', 'id': name}}
            placed = f.ledger.declare('scratch', {'path': str(path)}, owner, 'seam', pool=pool)
            assert placed['ok'], placed
            assert f.ledger.confirm(placed['item'])['ok']
            assert f.ledger.signal('run_finished', {'run': name})['ok']
            return placed['item'], path

        def freeing(kind):
            f = wired('freeing-' + kind)
            try:
                removed, path = item(f, 'output')
                assert f.ledger.place_hold('running', {'host': 1}, {'host': 'default'}, scope=f.scope)['ok']
                assert f.ledger.admit('running', 'admitted')['ok']
                assert f.ledger.place_hold('other-pool', {'image': 2000}, {'image': 'default'}, scope=f.scope)['ok']
                assert ADM.admit(f.ledger, 'other-pool', f.space['free'])['answer'] == 'waiting'
                identity = waiting(f)
                f.service.space_seen = f.service.watermark()
                f.loop.wakes.clear()
                f.free['host'] = 1000
                if kind == 'removal':
                    result = f.ledger.outcome(removed, 'removed', {'freed': 890})
                elif kind == 'release':
                    result = f.ledger.release('running')
                else:
                    result = f.ledger.reconcile('console', [], [], {key: 0 for key in SP.RECONCILE_COUNTS})
                assert result['ok'], result
                check('ac3/pool-only', f.ledger.hold('other-pool')['freed'] == (kind == 'reconcile'))
                marked = f.ledger.hold(identity)['freed']
                f.service.space_pass()
                wakes = list(f.loop.wakes)
                with patch.object(SV.time, 'time', return_value=f.now):
                    report = f.loop.run()
                check('ac3/' + kind + '-wakes', marked and any(w['source'] == 'space' for w in wakes)
                      and report is not None and bool(report['offered']) and not report['waiting']
                      and f.ledger.hold(identity)['state'] == 'admitted' and f.now == 1000)
                check('ac2/clear-after-judgment', not f.ledger.hold(identity)['freed'])
                transitions = [json.loads(raw) for (raw,) in f.conn.execute('SELECT transition FROM journal ORDER BY seq')]
                states = [t['space:hold:' + identity]['data'] for t in transitions if 'space:hold:' + identity in t]
                check('ac3/journal-marks', any(h['freed'] for h in states) and not states[-1]['freed']
                      and any(h['retry_asked'] for h in states))
            finally:
                f.close()
        for kind in ('removal', 'release', 'reconcile'):
            run('ac3/' + kind + '-wakes', lambda kind=kind: freeing(kind))

        def retry_removes():
            f = wired('retry-removes')
            try:
                identity, path = item(f, 'deferred')
                assert f.ledger.outcome(identity, 'deferred', {'rule': 'in_use', 'event': 'run_finished'})['ok']
                other, other_path = item(f, 'present')
                # A due item is not deferred and admission must leave it alone.
                f.signals.clear()
                f.ledger.engines = []  # this filesystem fixture has no Docker engine
                proc = f.root / 'proc'
                proc.mkdir()
                f.space.update(probe=load('control_space_probe'), kinds=K, remover=load('control_space_remove'),
                               proc=str(proc), owner_live=lambda owner: dict(conclusive=True, group_empty=True))
                def free(pool):
                    return 110 if pool['name'] == 'host' and path.exists() else 1000
                f.space['free'] = free
                report = pass_from(f, 'journal')
                if not report['offered']:
                    print('retry detail', report['refused'], (f.ledger.item(identity) or {}).get('deferral'))
                check('ac1/retry-removes', bool(report['offered']) and not path.exists()
                      and f.ledger.item(identity)['state'] == 'removed'
                      and f.signals == [('admission_requested', {'pool': 'host'})])
                check('ac1/pool-only', other_path.exists() and f.ledger.item(other)['state'] == 'due')
            finally:
                f.close()
        run('ac1/retry-removes', retry_removes)

        def no_freeing():
            f = wired('no-freeing')
            try:
                identity = waiting(f)
                f.service.space_seen = f.service.watermark()
                for amount in (0, None, -1):
                    removed, _path = item(f, 'output-' + str(amount))
                    assert f.ledger.outcome(removed, 'removed', {'freed': amount})['ok']
                f.service.space_pass()
                check('ac3/nonfreeing-no-mark', not f.ledger.hold(identity)['freed'] and not f.loop.wakes)
                # A marked wait consumes its mark even if the pool remains too small.
                assert f.ledger.reconcile('console', [], [], {key: 0 for key in SP.RECONCILE_COUNTS})['ok']
                f.service.space_pass()
                report = f.loop.run()
                check('ac2/clear-after-judgment', bool(report and report['waiting'])
                      and not f.ledger.hold(identity)['freed'])
            finally:
                f.close()
        run('ac3/nonfreeing-no-mark', no_freeing)

        def racing_free():
            f = wired('racing-free')
            try:
                identity = waiting(f)
                assert f.ledger.reconcile('console', [], [], {key: 0 for key in SP.RECONCILE_COUNTS})['ok']
                once = []
                def free(pool):
                    if not once:
                        once.append(True)
                        assert f.ledger.reconcile('console', [], [], {key: 0 for key in SP.RECONCILE_COUNTS})['ok']
                    return f.free[pool['name']]
                result = ADM.admit(f.ledger, identity, free)
                check('race/freeing-during-judgment', not result['ok'] and result['reason'] == 'stale_version'
                      and f.ledger.hold(identity)['freed'])
            finally:
                f.close()
        run('race/freeing-during-judgment', racing_free)

        def worker():
            f = wired('worker')
            consumer = None
            try:
                identity = waiting(f)
                removed, _path = item(f, 'output')
                f.service.space_seen = f.service.watermark()
                consumer = load('control_space_consumer').Consumer(f.ledger, given={})
                f.service.space_consumer, f.service.api = consumer, None
                f.free['host'] = 1000
                consumer.submit(('fixture',), lambda: f.ledger.outcome(removed, 'removed', {'freed': 890}))
                import select
                ready = select.select(list(consumer.pipes()), [], [], 120)[0]
                assert ready, 'worker pipe hang detector'
                f.service.space_readable(ready[0])
                # A pipe may yield its result before EOF; wait for completion, never a delay.
                while consumer.active is not None:
                    ready = select.select(list(consumer.pipes()), [], [], 120)[0]
                    assert ready, 'worker EOF hang detector'
                    f.service.space_readable(ready[0])
                report = f.loop.run()
                check('ac3/worker-wakes', report is not None and 'space' in report['sources']
                      and bool(report['offered']) and f.ledger.hold(identity)['state'] == 'admitted')
            finally:
                if consumer is not None:
                    consumer.stop()
                f.close()
        run('ac3/worker-wakes', worker)

    for row, answers in rows.items():
        expect('VELDO-0334 space334/' + row, bool(answers) and all(answers))


_v334_suite()
