"""VELDO-0317: real child output, dispatch accounting, admission and run-finished cleanup.
Only generous hang detectors (120 seconds or longer); no sleeps or speed assertions.
Eligibility, account policy, kernel process enumeration and free bytes are fixture seams.
"""

def _v317_suite():
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
    import time
    from unittest.mock import patch

    PRODUCTION = {
        'control_space_admission.py': ROOT / ".veldo" / "control_space_admission.py",
        'control_space.py': ROOT / ".veldo" / "control_space.py",
        'control_space_signal.py': ROOT / ".veldo" / "control_space_signal.py",
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_dispatch.py': ROOT / ".veldo" / "control_dispatch.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
    }
    rows = {name: [] for name in (
        'ac1/not-charged', 'ac1/behind-admission', 'ac1/numbers-before-cleanup',
        'ac2/repeated-once', 'ac2/repeat-red', 'ac3/edit-kept', 'ac3/next-brief',
        'ac4/two-stop', 'ac4/restart-stop', 'ac4/owner-request',
        'classify/controls', 'classify/streams', 'classify/unread', 'history/reset',
        'history/latest', 'artifact/no-verdict', 'wiring/installed-receiver')}

    def check(row, condition):
        rows.setdefault(row, []).append(bool(condition))

    run_process = subprocess.run

    def generous_run(*args, **kwargs):
        # Production Git/signature helpers have their own small operational timeouts.
        # Here they are hang detectors only; this suite measures no elapsed time.
        if kwargs.get('timeout') is not None:
            kwargs['timeout'] = max(120, kwargs['timeout'])
        return run_process(*args, **kwargs)

    with patch.object(subprocess, 'run', side_effect=generous_run):
        with tempfile.TemporaryDirectory(prefix='veldo-0317-') as temporary:
            root = Path(temporary)
            mods = root / 'installed'
            mods.mkdir()
            for source in (ROOT / '.veldo').glob('*.py'):
                shutil.copyfile(source, mods / source.name)
            for name, source in PRODUCTION.items():
                shutil.copyfile(source, mods / name)

            def load(name):
                spec = importlib.util.spec_from_file_location('v317_' + name, mods / (name + '.py'))
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
                    self.now, self.serial, self.started = time.time(), 0, []
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
                    original = self.runner.prepare
                    self.next_id = 999999
                    def ordered(*args, **kwargs):
                        self.next_id -= 1
                        with patch.object(L.uuid, 'uuid4', return_value=types.SimpleNamespace(hex='%032x' % self.next_id)):
                            return original(*args, **kwargs)
                    self.runner.prepare = ordered

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
                                configuration={}, deadline=self.now + 600)

                def prepare(self, unit='unit', station='build'):
                    with patch.object(L.CFG, 'bind', side_effect=lambda *args: args[-1]):
                        return self.runner.prepare(unit, station, **self.job())

                def receive(self, contract):
                    self.started.append(contract['dispatch_id'])
                    return types.SimpleNamespace(contract=contract, dispatch_id=contract['dispatch_id'],
                        result='accepted', owned=True, record={'state': 'running'}, pump=lambda read=False: False)

                def close(self):
                    self.conn.close()

            def row(name, body):
                try:
                    body()
                except Exception as error:
                    check(name, False)
                    print('space317 detail', name, type(error).__name__, str(error))

            def report():
                return {key: [] for key in ('waiting', 'refused', 'offered', 'asked', 'stopped', 'decisions')}

            def line(f):
                obj = object.__new__(SV.Line)
                obj.repository, obj.workspace = 'repository', str(f.repo)
                obj.gate, obj.runner, obj.hosts = f.gate, f.runner, {}
                obj.service = types.SimpleNamespace(conn=f.conn, domain='domain', space=f.space)
                obj.roles = {'builder': dict(identity='builder', adapter='fixture', payload={}, configuration={}, seconds=600)}
                obj.invocation = lambda identity: None
                obj.service.inbox = lambda repository: types.SimpleNamespace(read=lambda identity: None)
                obj.open_question = lambda *args: ('owner', {'ok': True})
                return obj

            def end(f, free=0, text='No space left on device', code=1, contract=None, stream='stderr', edits=True):
                contract = contract or f.prepare()
                did, digest = contract['dispatch_id'], D.digest(contract)
                work = f.root / ('work-' + str(len(f.started)))
                gp = load('git_process')
                gp.run(['git', '-C', str(f.repo), 'worktree', 'add', '--detach', str(work), 'HEAD'],
                       check=True, capture_output=True, timeout=120)
                if edits:
                    (work / 'unfinished.txt').write_text('unique uncommitted work')
                owner = {'scope': f.scope, 'ticket': contract['unit'], 'run': {'id': did, 'station': contract['station']}}
                made = f.ledger.declare('worktree', {'path': str(work)}, owner, 'seam', start=contract['source']['commit'])
                assert made['ok'], made
                assert f.ledger.confirm(made['item'])['ok']
                run = f.root / ('run-' + str(len(f.started)))
                scratch = f.ledger.declare('scratch', {'path': str(run)}, owner, 'seam')
                assert scratch['ok'], scratch
                run.mkdir()
                assert f.ledger.confirm(scratch['item'])['ok']
                proc = f.root / 'proc'
                proc.mkdir(exist_ok=True)
                f.space.update(probe=load('control_space_probe'), kinds=K, remover=load('control_space_remove'),
                               proc=str(proc), owner_live=lambda owner: dict(conclusive=True, group_empty=True))
                f.ledger.engines = []
                r = object.__new__(L.Receiver)
                r.config = {'store': str(f.state / 'store.sqlite3'), 'state_root': str(f.state)}
                r.conn, r.dispatches, r.space, r.emit = f.conn, f.dispatches, f.space, lambda event: None
                r.metering, r.recorder, r.committed, r.control, r.binding = None, None, None, None, None
                r.qualification, r.supervision, r.role_skills = None, None, []
                r.contract, r.run, r.run_dispatch = contract, str(run), did
                r.space_run = {'worktree': str(work), 'owner': owner}
                r.run_sent, r.run_removal, r.run_census = False, None, None
                # A worker cannot exit before the receiver reads its identity: it waits for stdin EOF.
                program = "import sys; sys.stdin.read(); print(sys.argv[1], file=getattr(sys,sys.argv[3]), flush=True); sys.exit(int(sys.argv[2]))"
                child = subprocess.Popen([sys.executable, '-c', program, text, str(code), stream],
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                         start_new_session=True)
                process = L.process_identity(child.pid)
                f.dispatches.accept(did, digest, dict(process, principal='runner'), now=f.now)
                f.dispatches.run(did, digest, process, now=f.now)
                f.started.append(did)
                termination = r._reap(child, contract, process=process, contract_digest=digest)
                f.free['host'] = free
                f.space['free'] = lambda pool: (f.free[pool['name']] if pool['name'] != 'host' or run.exists() else 1000)
                if edits:
                    assert (work / 'unfinished.txt').exists()
                r._finish(termination, contract, digest, process, False)
                f.space['free'] = lambda pool: f.free[pool['name']]
                return f.dispatches.record(did), work, run, r

            def rerun(f, record, obj=None):
                obj = obj or line(f)
                out = report()
                with patch.object(SV.L.CFG, 'bind', side_effect=lambda *args: args[-1]), patch.object(L.CFG, 'bind', side_effect=lambda *args: args[-1]):
                    launch = obj.limited(record, out)
                return launch, out

            def confirmed():
                for mode in ('act', 'report'):
                    f = Fixture('confirmed-' + mode, mode)
                    try:
                        rec, work, run, receiver = end(f)
                        failure = rec.get('space_failure') or {}
                        check('ac1/not-charged', f.dispatches.attempts('unit', 'build') == 0)
                        check('ac1/numbers-before-cleanup', failure.get('classification') == ADM.NO_SPACE
                              and failure.get('taxonomy') == 'unavailable_service'
                              and failure.get('pools') == [{'pool': 'host', 'free': 0, 'floor': 20},
                                                         {'pool': 'image', 'free': 1000, 'floor': 5}]
                              and f.ledger.hold(rec['contract']['space']['hold'])['state'] == 'released')
                        check('ac3/edit-kept', (work / 'unfinished.txt').is_file()
                              and (work / 'unfinished.txt').read_text() == 'unique uncommitted work'
                              and f.ledger.item(receiver.run_census['worktree'])['state'] in ('due', 'deferred'))
                        launch, out = rerun(f, rec)
                        if mode == 'act':
                            check('ac1/behind-admission', launch is None and len(out['waiting']) == 1
                                  and len(f.started) == 1 and len(f.dispatches.status()['states']) > 0)
                            f.free['host'] = 1000
                            assert f.ledger.reconcile('console', [], [], {key: 0 for key in SP.RECONCILE_COUNTS})['ok']
                            launch, out = rerun(f, rec)
                        payload = launch.contract['input']['payload'] if launch else {}
                        check('ac3/next-brief', str(work) in payload.get('retained_worktrees', [])
                              and 'uncommitted changes' in payload.get('space_recovery', '')
                              and (work / 'unfinished.txt').exists())
                    finally:
                        f.close()
            row('ac1/not-charged', confirmed)

            def unconfirmed():
                f = Fixture('unconfirmed')
                try:
                    rec, _, _, _ = end(f, free=1000, text='No space left on device; assertion failed for my own reason')
                    launch, _ = rerun(f, rec)
                    check('ac2/repeated-once', (rec.get('space_failure') or {}).get('classification') == ADM.UNCONFIRMED
                          and launch is not None and len(f.started) == 2)
                    if launch is None:
                        return
                    # The fixture receiver only records its start count; the real reap/finish runs now.
                    f.started.pop()
                    second, _, _, _ = end(f, free=1000, text='No space left on device; assertion failed for my own reason',
                                           contract=launch.contract)
                    third, out = rerun(f, second)
                    check('ac2/repeat-red', second['termination']['returncode'] == 1
                          and not D.completed(second) and not second['space_failure']['retry']
                          and not second['space_failure']['andon']
                          and third is None and not out['asked'] and len(f.started) == 2)
                    check('history/latest', line(f).latest()[('unit', 'build')]['dispatch_id'] == second['dispatch_id'])
                finally:
                    f.close()
            row('ac2/repeat-red', unconfirmed)

            def bounded():
                f = Fixture('bounded', 'report')
                try:
                    first, _, _, _ = end(f)
                    launch, _ = rerun(f, first)
                    assert launch is not None
                    f.started.pop()
                    second, _, _, _ = end(f, contract=launch.contract)
                    obj = line(f)
                    f.put('project:project', 'project', {'owner': 'owner'})
                    f.put('runner-key', 'verification_key', dict(principal='runner',
                        public_key=key.with_suffix('.pub').read_text(), effective_at=0, revoked_at=None))
                    obj.service.store, obj.service.principal, obj.service.generation = 'store', 'runner', 1
                    obj.service.sign, obj.service.config = f.sign, {'journal_key': str(key)}
                    obj.service.inbox = lambda repository: SV.Service.inbox(obj.service, repository)
                    obj.open_question = types.MethodType(SV.Line.open_question, obj)
                    third, out = rerun(f, second, obj)
                    again, repeated = rerun(f, second, obj)
                    check('ac4/two-stop', third is None and again is None and len(f.started) == 2
                          and bool(out['stopped']) and second['space_failure']['consecutive'] == 2)
                    requests = [json.loads(raw) for (raw,) in f.conn.execute(
                        'SELECT data FROM entities WHERE kind=?', (SV.I.ENTITY_KIND,))]
                    check('ac4/owner-request', len(requests) == 1 and len(out['asked']) == 1 and not repeated['asked']
                          and out['asked'][0]['outcome'] and requests[0]['owner'] == 'owner'
                          and 'Andon' in requests[0]['brief'])
                    check('history/latest', obj.latest()[('unit', 'build')]['dispatch_id'] == second['dispatch_id'])
                    # A fresh connection and Runner still cannot prepare a third run, even with space free.
                    f.conn.close()
                    f.conn = S.open_store(str(f.state / 'store.sqlite3'))
                    f.dispatches = D.Dispatches(S, f.conn, domain='domain', repository='repository',
                                                principal='runner', signer='runner', sign=f.sign)
                    f.runner.dispatches = f.dispatches
                    f.free['host'] = 1000
                    stopped = False
                    try:
                        f.prepare()
                    except D.Refused as error:
                        stopped = error.code == ADM.NO_SPACE
                    check('ac4/restart-stop', stopped and f.dispatches.attempts('unit', 'build') == 0)
                finally:
                    f.close()
            row('ac4/two-stop', bounded)

            def controls():
                f = Fixture('controls')
                try:
                    contract = {'domain': 'domain', 'repository': 'repository', 'unit': 'unit', 'station': 'build'}
                    f.free['host'] = 0
                    check('classify/controls', ADM.classify(f.space, contract, False, True) is None
                          and ADM.classify(f.space, contract, True, False) is None)
                    f.config['enabled'] = False
                    check('classify/controls', ADM.classify(f.space, contract, True, True) is None)
                    f.config['enabled'] = True
                    f.free['host'] = 20
                    check('classify/controls', ADM.classify(f.space, contract, True, True)['classification'] == ADM.UNCONFIRMED)
                    observed = ADM.Output()
                    observed.feed('engine', b'No space left ')
                    observed.feed('stderr', b'on device')
                    check('classify/streams', not observed.found)
                    observed.feed('engine', b'on device')
                    check('classify/streams', observed.found and len(observed.tails['engine']) <= 64)
                    f.space['free'] = lambda pool: (_ for _ in ()).throw(OSError('unread'))
                    check('classify/unread', ADM.classify(f.space, contract, True, True)['classification'] == ADM.UNCONFIRMED)
                finally:
                    f.close()
            row('classify/controls', controls)

            def reset():
                f = Fixture('reset', 'report')
                try:
                    end(f)
                    f.free['host'] = 1000
                    end(f, free=1000, text='ordinary unsuccessful end')
                    last, _, _, _ = end(f)
                    check('history/reset', last['space_failure']['consecutive'] == 1 and last['space_failure']['retry'])
                finally:
                    f.close()
            row('history/reset', reset)

            def installed_receiver():
                f = Fixture('installed-receiver')
                try:
                    (f.root / 'service.json').write_text(json.dumps({'store_path': str(f.state / 'store.sqlite3'),
                        'domain_uuid': 'domain', 'repositories': {'repository': [str(f.repo)]},
                        'host_identity': 'fixture', 'installation': str(f.root / 'installation')}))
                    r = object.__new__(L.Receiver)
                    r.space, r.conn, r.sign = None, f.conn, f.sign
                    r.configuration_path = str(f.root / 'receiver.json')
                    r.config = {'store': str(f.state / 'store.sqlite3'), 'domain': 'domain', 'repository': 'repository',
                                'state_root': str(f.state), 'principal': 'runner'}
                    r.dispatches, r.emit = types.SimpleNamespace(record=lambda identity: None), lambda event: None
                    organ = L._organ
                    with patch.object(CFG, 'read', return_value=f.config), patch.object(
                            L, '_organ', side_effect=lambda name: CFG if name == 'control_space_config' else organ(name)):
                        r.launch({'dispatch_id': 'not-prepared'})
                    check('wiring/installed-receiver', r.space is not None and r.space['ledger'].conn is f.conn
                          and r.space['ledger'].pool('host')['floor'] == 20
                          and type(r.space['free'](r.space['ledger'].pool('host'))) is int)
                finally:
                    f.close()
            row('wiring/installed-receiver', installed_receiver)

            def artifacts():
                # The metering seam owns artifact publication; unjudged ends still settle usage.
                for failure, expected in (({'retry': True}, False), ({'andon': True}, False), ({'retry': False}, True)):
                    m = object.__new__(L.Metering)
                    m.settled, m.start, m.sequence, m.receipts, m.file, m.errors = False, None, 0, [], None, []
                    m.receiver = types.SimpleNamespace(space_failure=failure)
                    m.meter = types.SimpleNamespace(close=lambda: [], final=lambda: {}, session=lambda: None, limit=lambda: None)
                    m.guard = types.SimpleNamespace(observe=lambda *args, **kwargs: None)
                    m.dispatch_id, m.invocation = 'dispatch', 'invocation'
                    made = []
                    m._artifact = lambda *args: made.append(True) or {'complete': False}
                    m.settle({'returncode': 1, 'deadline_stop': False}, None)
                    check('artifact/no-verdict', bool(made) == expected and not m.errors)
            row('artifact/no-verdict', artifacts)

    for name, answers in rows.items():
        expect('VELDO-0317 space317/' + name, bool(answers) and all(answers))


_v317_suite()
