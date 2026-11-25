"""VELDO-0316: real ledger, dispatch and reservations; deterministic boundary rows.

Eligibility/configuration and containment are fixture seams. Report-mode startup uses
an actual child process after durable dispatch acceptance. No sleeps or speed assertions.
The only subprocess timeout is a 120-second hang detector. Act prerequisites are fixture
checks; mode records are signed by a temporary owner's key. No live installation is read.
"""


def _v316_suite():
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
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_dispatch.py': ROOT / ".veldo" / "control_dispatch.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }
    # A mutant must retain the complete row inventory, including checks after a refused launch.
    rows = {name: [] for name in (
        'ac1/boundaries',
        'ac1/metrics',
        'ac1/numbers',
        'ac1/second-pool',
        'ac2/pre-reservation',
        'ac2/stable-hold',
        'ac2/waiting-pass',
        'ac3/advised-counts',
        'ac3/started-advised',
        'ac4/declared-first',
        'ac4/digest',
        'ac4/five-before-measured',
        'ac4/last-five',
        'ac4/legacy',
        'ac4/legacy-history',
        'ac4/measured-at-five',
        'metrics/exposed',
        'recovery/next-offer',
        'recovery/orphan-released',
        'ac4/project-station',
        'accept/released-hold',
        'disabled/no-hold',
        'release/cancelled',
        'release/measurements',
        'release/preparation-failed',
        'ac1/concurrent',
        'ac1/unread-pool',
        'ac2/completion-wakes',
        'ac2/racing-prepare',
        'ac2/service-wiring',
        'ac2/worker-responsive',
        'ac3/completion-race',
        'ac4/unread-declaration',
        'fix1/failed-judgment',
        'fix1/spent-answer',
        'fix2/left-backlog',
        'fix3/requests-unrelated-passes',
        'fix4/no-account-keeps-hold',
    )}

    def check(row, condition):
        rows.setdefault(row, []).append(bool(condition))

    with tempfile.TemporaryDirectory(prefix='veldo-0316-') as temporary:
        root = Path(temporary)
        mods = root / 'installed'
        mods.mkdir()
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, mods / source.name)
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)

        def load(name):
            spec = importlib.util.spec_from_file_location('v316_' + name, mods / (name + '.py'))
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

            def slots(self):
                # Worker slots only: the subscription policies configured above are not reservations.
                return [json.loads(raw) for (raw,) in self.conn.execute(
                    "SELECT data FROM entities WHERE kind='subscription_reservation'")
                    if json.loads(raw).get('type') == 'worker']

            def close(self):
                self.conn.close()

        def run(row, body):
            try:
                body()
            except Exception as error:
                check(row, False)
                print('space316 detail', row, type(error).__name__, str(error))

        def boundaries():
            f = Fixture('boundary')
            try:
                assert f.ledger.place_hold('other', {'host': 40}, {'host': 'default'}, scope=f.scope)['ok']
                assert f.ledger.admit('other', 'admitted', used={'host': 10})['ok']
                assert f.ledger.place_hold('own', {'host': 100, 'image': 30},
                    {'host': 'default', 'image': 'default'}, scope=f.scope)['ok']
                for free in (99, 100, 119, 120, 149, 150, 151):
                    f.free['host'] = free
                    answer = ADM.judge(f.ledger, 'own', f.space['free'])
                    check('ac1/boundaries', (answer is None) == (free >= 150))
                    if free == 149:
                        check('ac1/numbers', answer == dict(pool='host', need=100, free=149, held=30, floor=20))
                f.free.update(host=1000, image=34)
                check('ac1/second-pool', ADM.judge(f.ledger, 'own', f.space['free'])['pool'] == 'image')
                try:
                    f.prepare('image-wait')
                    check('ac1/second-pool', False)
                except Exception as error:
                    check('ac1/second-pool', getattr(error, 'code', None) == 'space_wait:image')
                for identity in list(f.ledger.holds()):
                    if identity not in ('other', 'own'):
                        assert f.ledger.release(identity)['ok']
                f.free['image'] = 35
                check('ac1/second-pool', ADM.judge(f.ledger, 'own', f.space['free']) is None)
                check('ac1/metrics', ADM.status(f.ledger, f.space['free']) == {
                    'pools': {'host': {'free': 1000, 'floor': 20, 'held': 30},
                              'image': {'free': 35, 'floor': 5, 'held': 0}},
                    'holds': {'admitted': 1, 'waiting': 1, 'advised': 0}})
                # The same metrics are exposed on the factory loop's status, which the service reports.
                loop = object.__new__(SV.FactoryLoop)
                loop.passes, loop.timer, loop.counts, loop.trees, loop.lines, loop.last = 0, None, {}, set(), {}, None
                loop.refused_lines, loop.line_counts, loop.conversation = {}, {}, None
                loop.wakes, loop.unwatched = [], []
                loop.service = types.SimpleNamespace(space=f.space)
                check('metrics/exposed', SV.FactoryLoop.status(loop).get('space_admission') == ADM.status(
                    f.ledger, f.space['free']) and SV.FactoryLoop.status(loop)['space_admission']['holds']['admitted'] == 1)
                loop.service = types.SimpleNamespace(space=None)
                check('metrics/exposed', SV.FactoryLoop.status(loop).get('space_admission', 'absent') is None)
            finally:
                f.close()
        run('ac1/boundaries', boundaries)

        def waiting():
            f = Fixture('waiting')
            try:
                reads = []
                f.space['free'] = lambda pool: reads.append(pool['name']) or f.free[pool['name']]
                f.free['host'] = 110
                f.decision('build', 'unit')
                before = f.tables()
                line = object.__new__(SV.Line)
                line.repository, line.workspace, line.gate, line.runner = 'repository', str(f.repo), f.gate, f.runner
                line.service, line.hosts = types.SimpleNamespace(space=f.space), {}
                role = dict(identity='builder', adapter='fixture', payload={}, configuration={}, seconds=10000)
                for attempt in range(2):
                    report = {'offered': [], 'refused': [], 'waiting': []}
                    with patch.object(L.CFG, 'bind', side_effect=lambda *args: args[-1]):
                        SV.Line.offer(line, report, 'unit', 'build', role, revision='HEAD')
                    check('ac2/pre-reservation', f.tables() == before and not f.started
                          and not report['offered'] and not report['refused'])
                    check('ac2/waiting-pass', len(report['waiting']) == 1 and
                          report['waiting'][0].get('space') == dict(pool='host', need=100, free=110, held=0, floor=20))
                    if attempt == 0:
                        journal = f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
                        read_count = len(reads)
                    check('ac2/stable-hold', len(reads) == read_count
                          and f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0] == journal)
                    try:
                        f.prepare()
                        check('ac2/pre-reservation', False)
                    except Exception as error:
                        check('ac2/pre-reservation', getattr(error, 'code', None) == 'space_wait:host')
                check('ac2/stable-hold', len(f.ledger.holds()) == 1 and
                      all('deadline' not in hold and hold['state'] == 'waiting' for hold in f.ledger.holds().values()))
            finally:
                f.close()
        run('ac2/pre-reservation', waiting)

        def report():
            f = Fixture('report', 'report')
            try:
                f.free['host'] = 110
                with patch.object(L.CFG, 'bind', side_effect=lambda *args: args[-1]):
                    launch = f.runner.submit('unit', 'build', **f.job())
                binding = launch.contract['space']
                hold = f.ledger.hold(binding['hold'])
                check('ac3/started-advised', bool(f.started) and launch.record['state'] == 'running'
                      and hold['state'] == 'advised' and hold['source'] == {'host': 'default', 'image': 'default'}
                      and hold['reason'] == dict(pool='host', need=100, free=110, held=0, floor=20))
                check('ac3/advised-counts', ADM.held(f.ledger, 'host') == 100)
                check('ac3/started-advised', len(f.slots()) == 1)
                check('ac1/metrics', ADM.status(f.ledger, f.space['free'])['holds'] ==
                      dict(admitted=0, waiting=0, advised=1))
            finally:
                f.close()
        run('ac3/started-advised', report)

        def history():
            f = Fixture('history')
            try:
                # The first five are small, so a need measured after one or after four runs admits early;
                # the outlier is among the newest five and not among the oldest five.
                for number, size in enumerate((10, 11, 12, 13, 14, 900, 15)):
                    contract = f.prepare('past-' + str(number))
                    f.finish(contract, {'host': size, 'image': 2})
                    if number == 0:
                        values, sources = ADM.needs(f.ledger, f.dispatches, 'project', 'build', {})
                        check('ac4/five-before-measured', values['host'] == 100 and sources['host'] == 'default')
                    if number in (0, 3):
                        f.free['host'] = 110
                        code = None
                        try:
                            f.prepare('threshold-' + str(number))
                        except Exception as error:
                            code = getattr(error, 'code', None)
                        check('ac4/five-before-measured', code == 'space_wait:host')
                        f.free['host'] = 1000
                    if number == 4:
                        values, sources = ADM.needs(f.ledger, f.dispatches, 'project', 'build', {})
                        check('ac4/measured-at-five', values == {'host': 14, 'image': 2}
                              and sources == {'host': 'measured', 'image': 'measured'})
                values, sources = ADM.needs(f.ledger, f.dispatches, 'project', 'build', {})
                check('ac4/last-five', values == {'host': 900, 'image': 2}
                      and sources == {'host': 'measured', 'image': 'measured'})
                for project, station in [('another-project', 'build'), ('project', 'review')]:
                    values, sources = ADM.needs(f.ledger, f.dispatches, project, station, {})
                    check('ac4/project-station', values == {'host': 100, 'image': 30}
                          and set(sources.values()) == {'default'})
                (f.repo / '.veldo' / 'space.yaml').write_text(YAML.dump({'needs': {'build': {'host': 7}}}))
                f.free['host'] = 27
                try:
                    contract = f.prepare('declared')
                except Exception:
                    check('ac4/declared-first', False)
                    return
                hold = f.ledger.hold(contract['space']['hold'])
                check('ac4/declared-first', hold['needs'] == {'host': 7, 'image': 2}
                      and hold['source'] == {'host': 'declared', 'image': 'measured'})
                (f.repo / '.veldo' / 'space.yaml').write_text(YAML.dump({'needs': {'build': {'host': 0}}}))
                zero = f.prepare('declared-zero')
                check('ac4/declared-first', zero['space']['needs']['host'] == 0
                      and f.ledger.hold(zero['space']['hold'])['source']['host'] == 'declared')
                record = f.dispatches.record(contract['dispatch_id'])
                changed = copy.deepcopy(contract)
                changed['space']['needs']['host'] += 1
                check('ac4/digest', record['contract_digest'] == D.digest(contract)
                      and D.digest(changed) != record['contract_digest'] and 'space' in D.CONTRACT_FIELDS)
                changed = copy.deepcopy(contract)
                changed['space']['hold'] += '-other'
                check('ac4/digest', D.digest(changed) != record['contract_digest'])
                legacy = copy.deepcopy(contract)
                legacy.pop('space')
                check('ac4/legacy', D.contract_problems(legacy) == [])
                assert f.ledger.release(contract['space']['hold'])['ok']
                started = list(f.started)
                try:
                    f.receive(contract)
                    check('accept/released-hold', False)
                except Exception as error:
                    check('accept/released-hold', getattr(error, 'code', '') == 'space_hold_state:released'
                          and f.dispatches.record(contract['dispatch_id'])['state'] == 'prepared' and f.started == started)
            finally:
                f.close()
        run('ac4/five-before-measured', history)

        def legacy_history():
            f = Fixture('legacy')
            try:
                # Runs that exited without a space binding (the ledger disabled, or before admission) give the
                # last measurements of their own items.
                for number in range(5):
                    f.config['enabled'] = False
                    contract = f.prepare('legacy-' + str(number))
                    f.config['enabled'] = True
                    assert contract['space'] is None
                    launch = f.receive(contract)
                    f.now += 1
                    f.dispatches.exit(contract['dispatch_id'], D.digest(contract), launch.record['process'],
                        dict(returncode=0, signal=None, output_digest=D.digest(''), output_bytes=0, deadline_stop=False), now=f.now)
                    path = f.root / ('legacy-' + str(number))
                    path.mkdir()
                    (path / 'output').write_bytes(b'output')
                    owner = {'scope': f.scope, 'run': {'station': 'build', 'id': contract['dispatch_id']}}
                    placed = f.ledger.declare('scratch', {'path': str(path)}, owner, 'seam')
                    assert placed['ok'], placed
                    assert f.ledger.confirm(placed['item'])['ok']
                    assert f.ledger.measure(placed['item'], 40 + number, 'run_finished')['ok']
                    values, sources = ADM.needs(f.ledger, f.dispatches, 'project', 'build', {})
                    if number < 4:
                        check('ac4/legacy-history', sources == {'host': 'default', 'image': 'default'})
                check('ac4/legacy-history', values == {'host': 44, 'image': 30}
                      and sources == {'host': 'measured', 'image': 'default'})
            finally:
                f.close()
        run('ac4/legacy-history', legacy_history)

        def recovery():
            f = Fixture('recovery')
            try:
                bound = f.prepare('bound')
                # A service that died after admission and before the dispatch was written: the answer is
                # committed and nothing else names the hold.
                orphan = ADM.prepare(f.space, f.dispatches, 'unit', 'build', 'project', str(f.repo))['hold']
                f.free['host'] = 300
                try:
                    f.prepare('waits')
                except Exception as error:
                    assert getattr(error, 'code', None) == 'space_wait:host', error
                f.free['host'] = 1000
                waits = [i for i, hold in f.ledger.holds().items() if hold['state'] == 'waiting']
                code = None
                try:
                    f.prepare('unit')
                except Exception as error:
                    code = getattr(error, 'code', None)
                assert code == 'space_hold_state:admitted' and ADM.held(f.ledger, 'host') == 200, code
                logs = []
                loop = object.__new__(SV.FactoryLoop)
                loop.conversation, loop.started_lines = None, []
                loop.provision = lambda report, caller: None
                f.runner.space = None  # as a line's Runner before its first offer: the service gives the ledger
                loop.lines = {'repository': types.SimpleNamespace(runner=f.runner)}
                loop.service = types.SimpleNamespace(space=f.space, domain='domain', _log=logs.append)
                SV.FactoryLoop.start(loop)
                f.runner.space = f.space
                check('recovery/orphan-released', f.ledger.hold(orphan)['state'] == 'released'
                      and f.ledger.hold(bound['space']['hold'])['state'] == 'admitted'
                      and len(waits) == 1 and f.ledger.hold(waits[0])['state'] == 'waiting'
                      and ADM.held(f.ledger, 'host') == 100
                      and logs[-1]['holds_recovered'] == {'repository': [
                          {'hold': orphan, 'state': 'admitted', 'released': True, 'refusal': None}]})
                contract = f.prepare('unit')
                check('recovery/next-offer', contract['space']['hold'] == orphan + '/1'
                      and f.ledger.hold(orphan + '/1')['state'] == 'admitted'
                      and f.dispatches.record(contract['dispatch_id'])['state'] == 'prepared' and not f.started)
            finally:
                f.close()
        run('recovery/orphan-released', recovery)

        def recovery_report():
            f = Fixture('recovery-report', 'report')
            try:
                f.free['host'] = 119
                held = ADM.prepare(f.space, f.dispatches, 'orphan', 'build', 'project', str(f.repo))['hold']
                assert f.ledger.hold(held)['state'] == 'advised'
                assert f.ledger.place_hold('foreign', {'host': 5}, {'host': 'default'}, scope=f.scope)['ok']
                assert f.ledger.admit('foreign', 'admitted')['ok']
                result = ADM.recover(f.space, f.dispatches)
                check('recovery/orphan-released', result == [dict(hold=held, state='advised', released=True, refusal=None)]
                      and f.ledger.hold(held)['state'] == 'released'
                      and f.ledger.hold('foreign')['state'] == 'admitted')
                head = f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0]
                check('recovery/orphan-released', ADM.recover(f.space, f.dispatches) == []
                      and f.conn.execute('SELECT COUNT(*) FROM journal').fetchone()[0] == head)
            finally:
                f.close()
        run('recovery/orphan-released', recovery_report)

        def disabled_and_failure():
            f = Fixture('disabled')
            try:
                f.config['enabled'] = False
                f.free['host'] = 0
                reads = []
                f.space['free'] = lambda pool: reads.append(pool['name']) or f.free[pool['name']]
                contract = f.prepare()
                check('disabled/no-hold', not reads)
                legacy = copy.deepcopy(contract)
                legacy.pop('space')
                record = f.dispatches.record(contract['dispatch_id'])
                record.update(contract=legacy, contract_digest=D.digest(legacy))
                f.put(D.record_id(contract['dispatch_id']), D.RECORD_KIND, record)
                f.dispatches.accept(contract['dispatch_id'], D.digest(legacy),
                    dict(platform='linux', host='fixture', boot_id='fixture', pid=1, start='fixture', principal='runner'), now=f.now)
                accepted = f.dispatches.record(contract['dispatch_id'])
                check('ac4/legacy', not D.contract_problems(legacy) and accepted['state'] == 'accepted'
                      and accepted['contract_digest'] == D.digest(legacy))
                check('disabled/no-hold', contract['space'] is None and not f.ledger.holds())
                f.config['enabled'] = True
                f.free['host'] = 1000
                with patch.object(L, 'resolve_source', side_effect=ValueError('fixture source failure')):
                    try:
                        f.prepare('failure')
                    except ValueError:
                        pass
                check('release/preparation-failed', len(f.ledger.holds()) == 1 and
                      all(hold['state'] == 'released' for hold in f.ledger.holds().values()))
            finally:
                f.close()
        run('release/preparation-failed', disabled_and_failure)

        def capacity_failure():
            f = Fixture('capacity-failure')
            try:
                with patch.object(f.reservations, 'reserve_worker', side_effect=D.Refused('capacity_exceeded')):
                    try:
                        f.prepare()
                        check('release/preparation-failed', False)
                    except Exception as error:
                        check('release/preparation-failed', getattr(error, 'code', None) == 'capacity_exceeded'
                              and [h['state'] for h in f.ledger.holds().values()] == ['released']
                              and not f.slots())
                contract = f.prepare()
                check('release/preparation-failed', contract['attempt'] == 1
                      and f.ledger.hold(contract['space']['hold'])['state'] == 'admitted')
            finally:
                f.close()
        run('release/preparation-failed', capacity_failure)

        def receiver_measurements():
            f = Fixture('measurements')
            try:
                contract = f.prepare()
                launch = f.receive(contract)
                f.dispatches.exit(contract['dispatch_id'], D.digest(contract), launch.record['process'],
                    dict(returncode=1, signal=None, output_digest=D.digest(''), output_bytes=0, deadline_stop=False), now=f.now)
                owner = {'scope': f.scope, 'run': {'station': 'build', 'id': contract['dispatch_id']}}
                path = f.root / 'run-output'
                path.mkdir()
                (path / 'output').write_bytes(b'output')
                placed = f.ledger.declare('scratch', {'path': str(path)}, owner, 'seam')
                assert placed['ok'], placed
                assert f.ledger.confirm(placed['item'])['ok']
                receiver = object.__new__(L.Receiver)
                receiver.space, receiver.dispatches = f.space, f.dispatches
                receiver._group_empty = lambda: True
                receiver._unstage_skills = lambda: None
                def census_and_signal():
                    assert f.ledger.measure(placed['item'], 6, 'run_finished')['ok']
                    receiver.run_sent, receiver.run_census, receiver.run_removal = True, {}, {}
                receiver._remove_run = census_and_signal
                receiver._space_end(contract['dispatch_id'], contract)
                check('release/measurements', f.ledger.hold(contract['space']['hold'])['used'] == {'host': 6}
                      and f.ledger.hold(contract['space']['hold'])['state'] == 'released'
                      and ADM.finished(f.ledger, f.dispatches, 'project', 'build') == [{'host': 6}])
                # Refused prepared dispatches return their hold before a later attempt.
                cancelled = f.prepare('cancelled')
                f.runner.cancel_prepared(cancelled, 'fixture_cancel')
                check('release/cancelled', f.ledger.hold(cancelled['space']['hold'])['state'] == 'released')
                f.runner.cancel_prepared(cancelled, 'fixture_cancel')
                again = f.prepare('cancelled')
                check('release/cancelled', f.ledger.hold(cancelled['space']['hold'])['state'] == 'released'
                      and again['space']['hold'] != cancelled['space']['hold'])
            finally:
                f.close()
        run('release/measurements', receiver_measurements)

        # Space V1: distinct assertions of the retired 150 fixture, against the current API.
        def no_account():
            for code in ('no_account', 'no_account_until:1900000000'):
                f = Fixture('account-' + code.split(':')[0])
                try:
                    reads = []
                    f.space['free'] = lambda pool: reads.append(pool['name']) or f.free[pool['name']]
                    with patch.object(f.reservations, 'reserve_worker', side_effect=D.Refused(code)):
                        for attempt in range(3):
                            try:
                                f.prepare()
                            except Exception as error:
                                assert getattr(error, 'code', None) == code, error
                            if attempt == 0:
                                holds = copy.deepcopy(f.ledger.holds())
                                head, count = f.conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0], len(reads)
                            check('fix4/no-account-keeps-hold', f.ledger.holds() == holds and len(holds) == 1
                                  and next(iter(holds.values()))['state'] == 'admitted'
                                  and len(reads) == count
                                  and f.conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0] == head
                                  and f.tables()['dispatch'] == 0 and f.tables()['dispatch_active'] == 0
                                  and not f.slots())
                    bound = f.prepare()
                    check('fix4/no-account-keeps-hold', bound['space']['hold'] in holds)
                finally:
                    f.close()
        run('fix4/no-account-keeps-hold', no_account)

        def async_admission(mode='act'):
            import os
            import select
            consumer_module = load('control_space_consumer')
            f = Fixture('async-' + mode, mode)
            consumer = consumer_module.Consumer(f.ledger)
            read, write = os.pipe()
            try:
                seen = f.root / 'reader-pid'
                def free(pool):
                    seen.write_text(str(os.getpid()))
                    os.read(read, 1)
                    return f.free[pool['name']]
                f.space['free'] = free
                wakes = []
                service = types.SimpleNamespace(space=f.space, space_consumer=consumer)
                requests = ADM.Requests(service, types.SimpleNamespace(wake=lambda *args: wakes.append(args)),
                                        f.dispatches)
                f.runner.admission = requests.prepare
                def offer():
                    try:
                        return f.prepare()
                    except Exception as error:
                        return getattr(error, 'code', None)
                check('ac2/worker-responsive', offer() == 'space_pending' and consumer.active is not None)
                check('ac2/worker-responsive', offer() == 'space_pending' and len(consumer.tasks) == 1)
                pid = consumer.active[1]
                # Completion is impossible before these bytes; returning above proves nonblocking admission.
                os.write(write, b'xxxxxxxx')
                def pump():
                    while consumer.active:
                        descriptor = consumer.active[0]
                        assert select.select([descriptor], [], [], WAITS.WAIT_HANG_SECONDS)[0], 'worker hang'
                        consumer.readable(descriptor)
                pump()
                check('ac2/completion-wakes', len(wakes) == 1 and int(seen.read_text()) == pid
                      and pid != os.getpid() and not Path('/proc/%d' % pid).exists())
                with patch.object(f.reservations, 'reserve_worker', side_effect=D.Refused('no_account')):
                    check('ac2/completion-wakes', offer() == 'no_account' and not f.runner.space_waiting_accounts)
                held = next(iter(f.ledger.holds()))
                requests.passed()  # this pass asked for the offer
                left = requests.passed()  # the next pass no longer offers it
                pump()
                check('fix2/left-backlog', bool(left) and f.ledger.hold(held)['state'] == 'released')
                f.runner.space_waiting_accounts.clear()
                f.space['free'] = lambda pool: (_ for _ in ()).throw(OSError('fixture unread'))
                check('fix1/failed-judgment', offer() == 'space_pending')
                pump()
                check('fix1/failed-judgment', offer() == 'OSError')
                f.space['free'] = lambda pool: f.free[pool['name']]
                check('fix1/failed-judgment', offer() == 'space_pending')
                pump()
                given = (f.space, f.dispatches, 'unit', 'build', 'project', str(f.repo))
                healthy = requests.prepare(*given)
                head = f.conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0]
                check('fix1/failed-judgment', requests.prepare(*given) == healthy
                      and f.ledger.hold(healthy['hold'])['state'] == 'admitted'
                      and consumer.active is None and not consumer.tasks
                      and f.conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0] == head)
                check('fix1/failed-judgment', isinstance(offer(), dict))
                receiver = f.root / 'receiver.json'
                receiver.write_text(json.dumps({'workspace': str(f.repo), 'state_root': str(f.state), 'adapters': {}}))
                service.domain, service.principal, service.sign, service.generation = 'domain', 'runner', f.sign, 1
                service.conn = f.conn
                actual_loop = types.SimpleNamespace(service=service, wake=lambda *args: wakes.append(args))
                actual_line = SV.Line(actual_loop, 'repository', {}, str(receiver))
                check('ac2/service-wiring', actual_line.runner.admission.__self__ is actual_line.space_requests
                      and actual_line.space_requests.service.space is f.space)
            finally:
                consumer.stop()
                os.close(read)
                os.close(write)
                f.close()
        run('ac2/worker-responsive', async_admission)
        run('ac2/worker-responsive', lambda: async_admission('report'))

        def racing_prepare():
            f = Fixture('racing-prepare')
            try:
                original = f.dispatches.prepare
                winners = []
                def competing(contract, **kwargs):
                    other = copy.deepcopy(contract)
                    other['dispatch_id'] += '-winner'
                    f.reservations.reserve_worker('worker/' + other['dispatch_id'], other['dispatch_id'],
                        'account', 'project', 'unit', now=f.now)
                    entity, version, digest = f.runner._slot(other['dispatch_id'])
                    other['reservation'].update(entity=entity, version=version, digest=digest)
                    original(other, **kwargs)
                    winners.append(other)
                    return original(contract, **kwargs)
                error = None
                with patch.object(f.dispatches, 'prepare', competing):
                    try:
                        f.prepare()
                    except Exception as caught:
                        error = caught
                check('ac2/racing-prepare', bool(winners) and str(getattr(error, 'code', '')).startswith('active_dispatch:')
                      and f.ledger.hold(winners[0]['space']['hold'])['state'] == 'admitted')
            finally:
                f.close()
        run('ac2/racing-prepare', racing_prepare)

        def worker_wait():
            import select
            f = Fixture('worker-wait')
            consumer = load('control_space_consumer').Consumer(f.ledger)
            try:
                f.free['host'] = 119
                reads = f.root / 'free-reads'
                def free(pool):
                    with reads.open('a') as stream:
                        stream.write(pool['name'] + '\n')
                    return f.free[pool['name']]
                f.space['free'] = free
                wakes = []
                service = types.SimpleNamespace(space=f.space, space_consumer=consumer)
                requests = ADM.Requests(service, types.SimpleNamespace(wake=lambda *args: wakes.append(args)), f.dispatches)
                f.runner.admission = requests.prepare
                def offer():
                    try:
                        return f.prepare()
                    except Exception as error:
                        return getattr(error, 'code', None)
                def pump():
                    while consumer.active:
                        ready, _, _ = select.select(list(consumer.pipes()), [], [], WAITS.WAIT_HANG_SECONDS)
                        assert ready
                        for fd in ready:
                            consumer.readable(fd)
                assert offer() == 'space_pending'
                pump()
                assert offer() == 'space_wait:host'
                held = next(iter(f.ledger.holds()))
                check('ac2/completion-wakes', consumer.active is None
                      and f.ledger.hold(held)['reason']['free'] == 119 and len(wakes) == 1)
                nreads = reads.read_text()
                head = f.conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0]
                f.free['host'] = 1000
                for _ in range(3):
                    requests.passed()
                    check('fix3/requests-unrelated-passes', offer() == 'space_wait:host'
                          and consumer.active is None and not consumer.tasks and len(wakes) == 1
                          and reads.read_text() == nreads
                          and f.conn.execute('SELECT MAX(seq) FROM journal').fetchone()[0] == head)
                assert f.ledger.reconcile('console', [], [], {key: 0 for key in SP.RECONCILE_COUNTS})['ok']
                f.space['free'] = lambda pool: -1
                check('fix1/failed-judgment', offer() == 'space_pending' and consumer.active is not None)
                pump()
                check('fix1/failed-judgment', offer() == 'space_free_unread:host'
                      and consumer.active is None and f.ledger.hold(held)['state'] == 'waiting'
                      and f.ledger.hold(held)['freed'])
                f.space['free'] = free
                check('ac3/completion-race', offer() == 'space_pending' and consumer.active is not None)
                pump()
                bound = offer()
                check('ac3/completion-race', isinstance(bound, dict) and len(wakes) == 3
                      and reads.read_text() != nreads and f.ledger.hold(held)['state'] == 'admitted'
                      and not f.ledger.hold(held)['freed'])
                requests.taken(bound)
                check('fix1/spent-answer', not requests.answers)
                submitted = []
                submit = consumer.submit
                def observe(key, *args, **kwargs):
                    submitted.append(key)
                    return submit(key, *args, **kwargs)
                with patch.object(consumer, 'submit', observe):
                    try:
                        requests.prepare(f.space, f.dispatches, 'unit', 'build', 'project', str(f.repo))
                        check('fix1/spent-answer', False)
                    except Exception as error:
                        check('fix1/spent-answer', getattr(error, 'code', None) == 'space_pending'
                              and submitted == [('admission', 'repository', 'unit', 'build', 2)])
                pump()
            finally:
                consumer.stop()
                f.close()
        run('fix3/requests-unrelated-passes', worker_wait)

        def concurrent():
            import os
            import select
            f = Fixture('concurrent')
            children = []
            go_read, go_write = os.pipe()
            registry = dict(f.conn.command_registry)
            f.free['host'] = 120
            try:
                for number in range(2):
                    read, write = os.pipe()
                    pid = os.fork()
                    if pid == 0:
                        try:
                            os.close(read)
                            os.close(go_write)
                            f.conn.close()
                            f.conn = S.open_store(str(f.state / 'store.sqlite3'))
                            f.conn.command_registry.update(registry)
                            f.ledger.conn = f.dispatches.conn = f.conn
                            os.read(go_read, 1)
                            try:
                                result = ADM.prepare(f.space, f.dispatches, 'unit-' + str(number), 'build',
                                                     'project', str(f.repo))
                                answer = 'admitted' if result else 'disabled'
                            except Exception as error:
                                answer = getattr(error, 'code', type(error).__name__)
                            os.write(write, answer.encode())
                            os._exit(0)
                        except BaseException:
                            os._exit(1)
                    os.close(write)
                    children.append((pid, read))
                os.write(go_write, b'xx')
                answers = []
                for pid, read in children:
                    assert select.select([read], [], [], WAITS.WAIT_HANG_SECONDS)[0], 'concurrent admission hang'
                    answers.append(os.read(read, 4096).decode())
                    assert os.waitpid(pid, 0)[1] == 0
                check('ac1/concurrent', sorted(answers) == ['admitted', 'space_wait:host']
                      and ADM.held(f.ledger, 'host') == 100)
            finally:
                for pid, read in children:
                    os.close(read)
                    try:
                        os.kill(pid, 9)
                        os.waitpid(pid, 0)
                    except ProcessLookupError:
                        pass
                os.close(go_read)
                os.close(go_write)
                f.close()
        run('ac1/concurrent', concurrent)

        def unread_free():
            f = Fixture('unread-free')
            try:
                f.space['free'] = lambda pool: -1
                try:
                    f.prepare()
                    check('ac1/unread-pool', False)
                except Exception as error:
                    check('ac1/unread-pool', str(getattr(error, 'code', '')).startswith('space_free_unread:'))
            finally:
                f.close()
        run('ac1/unread-pool', unread_free)

        def unread_declaration():
            f = Fixture('bad-declaration')
            try:
                (f.repo / '.veldo' / 'space.yaml').write_text('needs: invalid\n')
                error = None
                try:
                    f.prepare()
                except Exception as caught:
                    error = caught
                check('ac4/unread-declaration', error is not None and not f.ledger.holds() and not f.started)
            finally:
                f.close()
        run('ac4/unread-declaration', unread_declaration)

    for row, answers in rows.items():
        expect('VELDO-0316 space316/' + row, bool(answers) and all(answers))


_v316_suite()
