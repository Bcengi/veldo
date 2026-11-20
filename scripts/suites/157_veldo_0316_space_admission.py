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
    rows = {}

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
                f.free['image'] = 35
                check('ac1/second-pool', ADM.judge(f.ledger, 'own', f.space['free']) is None)
                check('ac1/metrics', ADM.status(f.ledger, f.space['free']) == {
                    'pools': {'host': {'free': 1000, 'floor': 20, 'held': 30},
                              'image': {'free': 35, 'floor': 5, 'held': 0}},
                    'holds': {'admitted': 1, 'waiting': 1, 'advised': 0}})
            finally:
                f.close()
        run('ac1/boundaries', boundaries)

        def waiting():
            f = Fixture('waiting')
            try:
                f.free['host'] = 110
                f.decision('build', 'unit')
                before = f.tables()
                line = object.__new__(SV.Line)
                line.repository, line.workspace, line.gate, line.runner = 'repository', str(f.repo), f.gate, f.runner
                line.service, line.hosts = types.SimpleNamespace(space=f.space), {}
                role = dict(identity='builder', adapter='fixture', payload={}, configuration={}, seconds=10000)
                for _ in range(2):
                    report = {'offered': [], 'refused': [], 'waiting': []}
                    with patch.object(L.CFG, 'bind', side_effect=lambda *args: args[-1]):
                        SV.Line.offer(line, report, 'unit', 'build', role, revision='HEAD')
                    check('ac2/pre-reservation', f.tables() == before and not f.started
                          and not report['offered'] and not report['refused'])
                    check('ac2/waiting-pass', len(report['waiting']) == 1 and
                          report['waiting'][0].get('space') == dict(pool='host', need=100, free=110, held=0, floor=20))
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
            finally:
                f.close()
        run('ac3/started-advised', report)

        def history():
            f = Fixture('history')
            try:
                for number, size in enumerate((10, 900, 11, 12, 13, 14, 15)):
                    contract = f.prepare('past-' + str(number))
                    f.finish(contract, {'host': size, 'image': 2})
                    if number in (0, 3):
                        f.free['host'] = 110
                        code = None
                        try:
                            f.prepare('threshold-' + str(number))
                        except Exception as error:
                            code = getattr(error, 'code', None)
                        check('ac4/five-before-measured', code == 'space_wait:host')
                        f.free['host'] = 1000
                values, sources = ADM.needs(f.ledger, f.dispatches, 'project', 'build', {})
                check('ac4/last-five', values == {'host': 15, 'image': 2}
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
                record = f.dispatches.record(contract['dispatch_id'])
                changed = copy.deepcopy(contract)
                changed['space']['needs']['host'] += 1
                check('ac4/digest', record['contract_digest'] == D.digest(contract)
                      and D.digest(changed) != record['contract_digest'] and 'space' in D.CONTRACT_FIELDS)
                legacy = copy.deepcopy(contract)
                legacy.pop('space')
                check('ac4/legacy', D.contract_problems(legacy) == [])
                assert f.ledger.release(contract['space']['hold'])['ok']
                try:
                    f.receive(contract)
                    check('accept/released-hold', False)
                except Exception as error:
                    check('accept/released-hold', getattr(error, 'code', '') == 'space_hold_state:released'
                          and f.dispatches.record(contract['dispatch_id'])['state'] == 'prepared')
            finally:
                f.close()
        run('ac4/five-before-measured', history)

        def disabled_and_failure():
            f = Fixture('disabled')
            try:
                f.config['enabled'] = False
                f.free['host'] = 0
                contract = f.prepare()
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
                placed = f.ledger.declare('scratch', {'path': str(path)}, owner, 'fixture')
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
            finally:
                f.close()
        run('release/measurements', receiver_measurements)

    for row, answers in rows.items():
        expect('VELDO-0316 space316/' + row, bool(answers) and all(answers))


_v316_suite()
