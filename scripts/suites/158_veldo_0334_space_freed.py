"""VELDO-0334: event-driven admission on real ledger, Runner and factory loop.

Fix round 1 rows: a second writer on its own connection commits inside the freeing command's
own store call (an event, never a delay); a refused retry Signal; a released hold's older mark.

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
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_dispatch.py': ROOT / ".veldo" / "control_dispatch.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }
    # A mutant must retain the complete row inventory, including checks after a refused launch.
    rows = {name: [] for name in (
        'ac1/one-signal',
        'ac1/retry-removes',
        'ac1/pool-only',
        'ac2/timer-still-waits',
        'ac2/no-read-write',
        'ac2/clear-after-judgment',
        'ac3/removal-wakes',
        'ac3/release-wakes',
        'ac3/reconcile-wakes',
        'ac3/pool-only',
        'ac3/nonfreeing-no-mark',
        'ac3/journal-marks',
        'race/freeing-during-judgment',
        'ac3/worker-wakes',
        'race/release-resent',
        'race/removal-resent',
        'race/reconcile-resent',
        'race/own-version-refused',
        'race/refusal-atomic',
        'race/resend-bounded',
        'report/signal-refused-advised',
        'act/signal-refused-waits',
        'ac3/released-mark-no-wake',
        'ac3/release-replay',
        'fix1/report-lost-signal',
        'fix1/report-recovers-persisted-wait',
        'fix2/release-marks-per-pool',
        'fix2/waiting-release-no-mark',
    )}

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

            def second(self):
                # Another writer of the same store on its own connection, as the forked space worker is.
                self.second_conn = S.open_store(str(self.state / 'store.sqlite3'))
                return SP.Ledger(S, self.second_conn, 'runner', self.sign, config=self.config,
                    projects=[self.project], state_root=str(self.state), host='fixture', lifecycle=K.LIFECYCLE)

            def close(self):
                if getattr(self, 'second_conn', None) is not None:
                    self.second_conn.close()
                self.conn.close()

        def run(row, body):
            try:
                body()
            except Exception as error:
                check(row, False)
                print('space334 detail', row, type(error).__name__, str(error))

        def wired(name, mode='act'):
            f = Fixture(name, mode)
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
                reports = []
                first = None
                for source in ('run_end', 'account_reset', 'working_tree'):
                    if source == 'account_reset':
                        f.loop.timer = 0
                        check('ac1/one-signal', f.loop.due(0))
                    report = pass_from(f, source)
                    reports.append(report)
                    first = first or report['waiting']
                    check('ac1/one-signal', report['waiting'] == first and source in report['sources'])
                check('ac1/one-signal', f.signals == [('admission_requested', {'pool': 'host'})]
                      and f.ledger.hold(identity)['retry_asked'] and all(r['waiting'] for r in reports))
                check('ac2/no-read-write', before == (len(f.reads), f.service.watermark()))
                numbers = dict(f.ledger.hold(identity)['reason'])
                f.free['host'] = 1000  # owner freed bytes by hand, no ledger write
                report = pass_from(f, 'account_reset')
                check('ac2/timer-still-waits', bool(report['waiting']) and not report['offered']
                      and f.ledger.hold(identity)['state'] == 'waiting'
                      and report['waiting'][0]['space'] == numbers and report['waiting'] == first
                      and before == (len(f.reads), f.service.watermark()))
                direct = ADM.admit(f.ledger, identity, f.space['free'])
                check('ac2/no-read-write', direct['answer'] == 'waiting' and direct['reason'] == numbers
                      and before == (len(f.reads), f.service.watermark()))
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
                calls = len(f.signals)
                f.service.space_pass()
                wakes = list(f.loop.wakes)
                f.service.space_pass()
                check('ac3/' + kind + '-wakes', f.loop.wakes == wakes and len(f.signals) == calls)
                with patch.object(SV.time, 'time', return_value=f.now):
                    report = f.loop.run()
                check('ac3/' + kind + '-wakes', marked and any(w['source'] == 'space' for w in wakes)
                      and report is not None and bool(report['offered']) and not report['waiting']
                      and f.ledger.hold(identity)['state'] == 'admitted' and f.now == 1000)
                check('ac2/clear-after-judgment', not f.ledger.hold(identity)['freed'])
                f.loop.wakes.clear()
                calls = len(f.signals)
                f.service.space_pass()
                check('ac3/' + kind + '-wakes', not f.loop.wakes and len(f.signals) == calls
                      and not f.ledger.hold(identity)['freed'])
                transitions = [json.loads(raw) for (raw,) in f.conn.execute('SELECT transition FROM journal ORDER BY seq')]
                states = [t['space:hold:' + identity]['data'] for t in transitions if 'space:hold:' + identity in t]
                check('ac3/journal-marks', any(h['freed'] for h in states) and not states[-1]['freed']
                      and any(h['retry_asked'] for h in states))
            finally:
                f.close()
        for kind in ('removal', 'release', 'reconcile'):
            run('ac3/' + kind + '-wakes', lambda kind=kind: freeing(kind))

        def release_only_promises():
            f = wired('release-only-promises')
            try:
                for identity, needs in (('host-wait', {'host': 10}), ('image-wait', {'image': 10}),
                                        ('not-counted', {'host': 10}), ('partial', {'host': 10, 'image': 20})):
                    assert f.ledger.place_hold(identity, needs, {k: 'default' for k in needs}, scope=f.scope)['ok']
                before = f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
                assert f.ledger.release('not-counted')['ok']
                transition = json.loads(f.conn.execute('SELECT transition FROM journal ORDER BY seq DESC LIMIT 1').fetchone()[0])
                check('fix2/waiting-release-no-mark', not f.ledger.hold('host-wait')['freed']
                      and not f.ledger.hold('image-wait')['freed'] and list(transition) == [SP.hold_id('not-counted')]
                      and f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0] == before + 1)
                assert f.ledger.admit('partial', 'admitted', used={'host': 10, 'image': 5})['ok']
                assert f.ledger.release('partial')['ok']
                check('fix2/release-marks-per-pool', not f.ledger.hold('host-wait')['freed']
                      and f.ledger.hold('image-wait')['freed'])
            finally:
                f.close()
        run('fix2/release-marks-per-pool', release_only_promises)

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

        # Fix round 1 (F1). A second writer commits between the freeing command's read of the waiters
        # and its commit. The interleaving is an event, the first writer's own store call: no clock.
        def interleaved(f, operation, between, body):
            real, sent = S.execute, []
            def execute(conn, command, *args, **kwargs):
                if conn is f.conn and command['operation'] == operation:
                    sent.append(command['command_id'])
                    between(len(sent))
                return real(conn, command, *args, **kwargs)
            with patch.object(S, 'execute', execute):
                return body(), sent

        def counts():
            return {key: 0 for key in SP.RECONCILE_COUNTS}

        def resent(kind):
            f = wired('resent-' + kind)
            try:
                removed, _path = item(f, 'output')
                assert f.ledger.place_hold('running', {'host': 1}, {'host': 'default'}, scope=f.scope)['ok']
                assert f.ledger.admit('running', 'admitted')['ok']
                identity = waiting(f)
                other = f.second()
                def between(attempt):
                    if attempt != 1:
                        return
                    if kind == 'release':
                        # The waiter's version moves: another freeing write marks it.
                        assert other.reconcile('console', [], [], counts())['ok']
                    else:
                        # A hold nobody had read is placed on the pool.
                        assert other.place_hold('new', {'host': 5}, {'host': 'default'}, scope=f.scope)['ok']
                if kind == 'removal':
                    result, sent = interleaved(f, SP.OUTCOME, between,
                                               lambda: f.ledger.outcome(removed, 'removed', {'freed': 890}))
                    ended = f.ledger.item(removed)['state'] == 'removed' and f.ledger.hold('new')['freed']
                elif kind == 'release':
                    result, sent = interleaved(f, SP.RELEASE, between, lambda: f.ledger.release('running'))
                    ended = f.ledger.hold('running')['state'] == 'released'
                else:
                    result, sent = interleaved(f, SP.RECONCILE, between,
                                               lambda: f.ledger.reconcile('console', [], [], counts()))
                    ended = f.ledger.hold('new')['freed']
                if not result['ok']:
                    print('space334 detail', kind, result)
                if kind == 'reconcile':
                    transition = json.loads(f.conn.execute('SELECT transition FROM journal ORDER BY seq DESC LIMIT 1').fetchone()[0])
                    check('race/reconcile-resent', sum(v['kind'] == SP.HOLD_KIND for v in transition.values()) == 2
                          and any(v['kind'] == SP.RECONCILE_KIND for v in transition.values()))
                check('race/' + kind + '-resent', result['ok'] and ended and len(sent) == 2
                      and f.ledger.hold(identity)['freed'] and f.ledger.observations[-1].get('attempts') == 2
                      and f.ledger.observations[-1]['outcome'] == 'accepted')
            finally:
                f.close()
        for kind in ('release', 'removal', 'reconcile'):
            run('race/' + kind + '-resent', lambda kind=kind: resent(kind))

        def own_version():
            f = wired('own-version')
            try:
                assert f.ledger.place_hold('running', {'host': 1}, {'host': 'default'}, scope=f.scope)['ok']
                assert f.ledger.admit('running', 'admitted')['ok']
                identity = waiting(f)
                other = f.second()
                def between(attempt):
                    # The released hold itself moves (and so does the waiter it marks).
                    if attempt == 1:
                        assert other.release('running')['ok']
                result, sent = interleaved(f, SP.RELEASE, between, lambda: f.ledger.release('running', used={'host': 7}))
                check('race/own-version-refused', not result['ok'] and result['reason'] == 'stale_version'
                      and len(sent) == 1 and f.ledger.hold('running').get('used') != {'host': 7}
                      and f.ledger.hold(identity)['freed'])
            finally:
                f.close()
        run('race/own-version-refused', own_version)

        def refusal_atomic():
            f = wired('refusal-atomic')
            try:
                identity = waiting(f)
                before = f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
                refusal = f.ledger.release(identity, expected_version=0)
                check('race/refusal-atomic', not refusal['ok'] and not f.ledger.hold(identity)['freed']
                      and f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0] == before)
            finally:
                f.close()
        run('race/refusal-atomic', refusal_atomic)

        def bounded():
            f = wired('bounded')
            try:
                assert f.ledger.place_hold('running', {'host': 1}, {'host': 'default'}, scope=f.scope)['ok']
                assert f.ledger.admit('running', 'admitted')['ok']
                waiting(f)
                other = f.second()
                limit = SP.FREEING_ATTEMPTS
                def between(attempt):
                    # A writer that wins every race, a few more times than the bound allows.
                    if attempt <= limit + 3:
                        assert other.reconcile('console', [], [], counts())['ok']
                result, sent = interleaved(f, SP.RELEASE, between, lambda: f.ledger.release('running'))
                check('race/resend-bounded', not result['ok'] and result['reason'] == 'stale_version'
                      and len(sent) == limit and limit > 1 and f.ledger.hold('running')['state'] == 'admitted')
                # Nothing was consumed by the refused attempts: the same release commits once the writer rests.
                check('race/resend-bounded', f.ledger.release('running')['ok']
                      and f.ledger.hold('running')['state'] == 'released')
            finally:
                f.close()
        run('race/resend-bounded', bounded)

        # Fix round 1 (F2). The one retry is refused by the ledger; the hold is judged all the same.
        def signal_refused(mode, row):
            f = wired('signal-refused-' + mode, mode)
            try:
                counted = f.ledger.signal
                def refused(event, subject, **kwargs):
                    if event == 'admission_requested':
                        f.signals.append((event, subject))
                        return {'ok': False, 'reason': 'space_not_permitted:space_signal', 'detail': 'fixture'}
                    return counted(event, subject, **kwargs)
                f.ledger.signal = refused
                f.free['host'] = 110
                report = pass_from(f, 'journal')
                identity = next(iter(f.ledger.holds()))
                hold = f.ledger.hold(identity)
                again = pass_from(f, 'run_end')
                asked = f.signals == [('admission_requested', {'pool': 'host'})] and hold['retry_asked']
                if mode == 'report':
                    check(row, asked and hold['state'] == 'advised' and hold['reason']['pool'] == 'host'
                          and bool(report['offered']) and not report['waiting'] and not again['waiting']
                          and len(f.started) == 1)
                else:
                    check(row, asked and hold['state'] == 'waiting' and hold['reason']['pool'] == 'host'
                          and bool(report['waiting']) and bool(again['waiting']) and not f.started)
            finally:
                f.close()
        run('report/signal-refused-advised', lambda: signal_refused('report', 'report/signal-refused-advised'))
        run('act/signal-refused-waits', lambda: signal_refused('act', 'act/signal-refused-waits'))

        def signal_lost():
            for mode in ('act', 'report'):
                f = wired('signal-lost-' + mode, mode)
                try:
                    def lost(event, subject, **kwargs):
                        f.signals.append((event, subject))
                        raise RuntimeError('fixture cleanup lost')
                    f.ledger.signal = lost
                    f.free['host'] = 110
                    result = pass_from(f, 'journal')
                    hold = next(iter(f.ledger.holds().values()))
                    check('fix1/' + mode + '-lost-signal', hold['retry_asked'] and len(f.signals) == 1
                          and hold['state'] == ('advised' if mode == 'report' else 'waiting')
                          and bool(result['offered']) == (mode == 'report'))
                    seen = {'operation': SP.RELEASE, 'command_id': 'fixture-release',
                            'wrote': {SP.hold_id('waiting'): {'state': 'waiting'},
                                      SP.hold_id('wrapped'): {'state': 'released'}}}
                    answer = f.ledger._original(seen, {'parameters': {'hold': 'wrapped'}})
                    check('ac3/release-replay', answer['state'] == 'released')
                    if mode == 'act':
                        f.mode('report')
                        continued = pass_from(f, 'journal')
                        check('fix1/report-recovers-persisted-wait', bool(continued['offered'])
                              and not continued['waiting'] and len(f.signals) == 1
                              and next(iter(f.ledger.holds().values()))['state'] == 'advised')
                finally:
                    f.close()
        run('fix1/report-lost-signal', signal_lost)

        # Fix round 1 (F3). A marked hold that is released carries its older mark; nobody waits, no wake.
        def released_mark():
            f = wired('released-mark')
            try:
                identity = waiting(f)
                f.service.space_seen = f.service.watermark()
                f.loop.wakes.clear()
                assert f.ledger.reconcile('console', [], [], counts())['ok']
                f.service.space_pass()
                woken = [w for w in f.loop.wakes if w['source'] == 'space']
                f.loop.wakes.clear()
                assert f.ledger.release(identity)['ok']
                (raw,) = f.conn.execute('SELECT transition FROM journal ORDER BY seq DESC LIMIT 1').fetchone()
                carried = json.loads(raw)['space:hold:' + identity]['data']
                f.service.space_pass()
                check('ac3/released-mark-no-wake', len(woken) == 1 and carried['state'] == 'released'
                      and carried['freed'] is True and not f.loop.wakes
                      and f.service.space_seen == f.service.watermark()
                      and not any(entry.get('operation') == 'space_pass' for entry in f.logs))
            finally:
                f.close()
        run('ac3/released-mark-no-wake', released_mark)

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
