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
        'ac1/not-charged',
        'ac1/behind-admission',
        'ac1/numbers-before-cleanup',
        'ac1/rerun-accepted',
        'ac2/repeated-once',
        'ac2/repeat-red',
        'ac3/edit-kept',
        'ac3/next-brief',
        'ac3/brief-no-space-only',
        'ac3/brief-live-only',
        'ac4/two-stop',
        'ac4/restart-stop',
        'ac4/owner-request',
        'ac4/later-dispatch-open',
        'ac4/owner-clears',
        'classify/controls',
        'classify/streams',
        'classify/unread',
        'history/reset',
        'history/latest',
        'history/unit-scoped',
        'history/bounded-read',
        'history/unconfirmed-new-run',
        'artifact/no-verdict',
        'wiring/installed-receiver',
        'ac1/replayed-end',
        'ac3/reconnect',
        'ac4/off-loop',
        'fix2/andon-redelivery',
    )}

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
            mods = root / '.veldo'  # the floor module loads its organs from .veldo beside its parent
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

            L, SV, ADM, SP, CFG, YAML, K, FLOOR = map(load, ('control_launch', 'control_service',
                'control_space_admission', 'control_space', 'control_space_config', 'yamlish', 'control_space_kinds',
                'dispatch'))
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
                    self.now, self.serial, self.started, self.items = time.time(), 0, [], {}
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
                    self.next_id = 0
                    def ordered(*args, **kwargs):
                        self.next_id += 1
                        with patch.object(L, 'uuid', types.SimpleNamespace(
                                uuid4=lambda: types.SimpleNamespace(hex='%032x' % self.next_id))):
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

            IDS = {'domain_uuid': 'domain', 'repository_uuid': 'repository', 'store_uuid': 'store'}

            def owner_line(f, conn=None):
                # The Line over the real signed inbox: the owner's project, the service's key, one store.
                obj = line(f)
                if conn is not None:
                    obj.service.conn = conn
                else:
                    f.put('project:project', 'project', {'owner': 'owner'})
                    f.put('runner-key', 'verification_key', dict(principal='runner',
                        public_key=key.with_suffix('.pub').read_text(), effective_at=0, revoked_at=None))
                obj.service.store, obj.service.principal, obj.service.generation = 'store', 'runner', 1
                obj.service.sign, obj.service.config = f.sign, {'journal_key': str(key)}
                obj.service.inbox = lambda repository: SV.Service.inbox(obj.service, repository)
                obj.open_question = types.MethodType(SV.Line.open_question, obj)
                return obj

            def requests(conn):
                return [json.loads(raw) for (raw,) in conn.execute(
                    'SELECT data FROM entities WHERE kind=?', (SV.I.ENTITY_KIND,))]

            def answer(f, obj, request, ruling):
                # The owner's own signed answer, applied by the real inbox (VELDO-0064).
                f.serial += 1
                body = dict(IDS, operation='answer', alias=request['alias'], principal='owner',
                            command_id='answer/' + str(f.serial), nonce='answer/' + str(f.serial),
                            request_version=request['request_version'], ruling=ruling)
                return obj.service.inbox('repository').apply({'command': body, 'signature': sign(S.canonical_bytes(body))})

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
                f.items[str(work)] = made['item']
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
                # What Receiver.__init__ sets for a run that is no conversation turn and has no file memory, which
                # _finish and the refusal path read since VELDO-0231, VELDO-0176, VELDO-0177 and VELDO-0184 (as
                # the bring-up line gave suite 146's receiver).
                r.login = r.flags = r.flag_means = None
                r.conversation_record = r.held_session = r.placed = r.rendering = None
                r.start = r.resume_refusal = r.file_memory = None
                r.history_wanted, r.attached = False, []
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
                original_exit = f.dispatches.exit
                def remember_exit(*args, **kwargs):
                    r.exit_delivery = (copy.deepcopy(args), copy.deepcopy(kwargs))
                    return original_exit(*args, **kwargs)
                with patch.object(f.dispatches, 'exit', side_effect=remember_exit):
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
                        check('ac1/not-charged', f.dispatches.charged('unit', 'build') == 0
                              and f.dispatches.attempts('unit', 'build') == 1)
                        check('ac1/numbers-before-cleanup', failure.get('classification') == ADM.NO_SPACE
                              and failure.get('taxonomy') == 'unavailable_service'
                              and failure.get('pools') == [{'pool': 'host', 'free': 0, 'floor': 20},
                                                         {'pool': 'image', 'free': 1000, 'floor': 5}]
                              and f.ledger.hold(rec['contract']['space']['hold'])['state'] == 'released')
                        # Replay the exact delivery, including its timestamp and complete observation.
                        args, kwargs = receiver.exit_delivery
                        f.dispatches.exit(*args, **kwargs)
                        check('ac1/replayed-end', f.dispatches.charged('unit', 'build') == 0
                              and f.dispatches.attempts('unit', 'build') == 1
                              and f.dispatches.record(rec['dispatch_id']) == rec)
                        retained_state = f.ledger.item(receiver.run_census['worktree'])['state']
                        # A ticket worktree is measured on run_finished and can remain present.
                        retained_states = ('present', 'due', 'deferred', 'kept')
                        if retained_state not in retained_states or not (work / 'unfinished.txt').is_file():
                            print('space317 retention', mode, retained_state, (work / 'unfinished.txt').is_file())
                        check('ac3/edit-kept', (work / 'unfinished.txt').is_file()
                              and (work / 'unfinished.txt').read_text() == 'unique uncommitted work'
                              and retained_state in retained_states)
                        # Reconnecting starts the service's reconciler; reconnect is not a
                        # lifecycle event. Use the real service entry and its disk/store read.
                        service = object.__new__(SV.Service)
                        # This is the worker callback, after Service has wired its ledger.
                        service._space, service.repositories = f.space, {}
                        result = service.space_received_reconcile()
                        if not result['ok']:
                            print('space317 reconnect', mode, result)
                        check('ac3/reconnect', result['ok'] and (work / 'unfinished.txt').read_text() == 'unique uncommitted work')
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
                        if launch is None:
                            continue
                        # Review finding 1: the rerun has a number of its own, so the floor's newest build is
                        # the clean one and its acceptance finds the build dispatch.
                        f.started.pop()
                        clean, _, _, _ = end(f, free=1000, text='built', code=0, contract=launch.contract, edits=False)
                        bound = clean['contract']['claim'] or {}
                        params = {'domain': 'domain', 'repository': 'repository', 'unit': 'unit'}
                        try:
                            accepted = FLOOR._build_dispatch(f.conn, params, bound.get('holder'), bound.get('generation'))
                        except FLOOR.FloorRefused as error:
                            print('space317 floor', mode, error)
                            accepted = None
                        numbers = [r['contract']['attempt'] for r in FLOOR._dispatches(
                            f.conn, 'domain', 'repository', 'unit', 'build')]
                        check('ac1/rerun-accepted', D.completed(clean) and numbers == [2, 1]
                              and accepted is not None and accepted['dispatch_id'] == clean['dispatch_id']
                              and L.D.RES is not None and load('control_reservation_runtime').boundary(
                                  clean['contract']) == 'retry'
                              and f.dispatches.charged('unit', 'build') == 1
                              and line(f).latest()[('unit', 'build')]['dispatch_id'] == clean['dispatch_id'])
                    finally:
                        f.close()
            row('ac1/not-charged', confirmed)

            def released():
                # Review finding 3: the brief names a kept worktree only while the ledger holds it as a
                # live item; once it is gone, no later brief claims it.
                f = Fixture('released', 'report')
                try:
                    _, work, _, _ = end(f)
                    before = f.prepare(station='review')['input']['payload']
                    gone = f.ledger.gone(f.items[str(work)])
                    assert gone['ok'], gone
                    after = f.prepare()['input']['payload']
                    check('ac3/brief-live-only', before.get('retained_worktrees') == [str(work)]
                          and 'retained_worktrees' not in after and 'space_recovery' not in after)
                finally:
                    f.close()
            row('ac3/brief-live-only', released)

            def unconfirmed():
                f = Fixture('unconfirmed')
                try:
                    rec, _, _, _ = end(f, free=1000, text='No space left on device; assertion failed for my own reason')
                    launch, _ = rerun(f, rec)
                    check('ac2/repeated-once', (rec.get('space_failure') or {}).get('classification') == ADM.UNCONFIRMED
                          and launch is not None and len(f.started) == 2)
                    # Review finding 3: an unconfirmed end is no environment failure; its worktree is not claimed.
                    check('ac3/brief-no-space-only', launch is not None
                          and 'retained_worktrees' not in launch.contract['input']['payload']
                          and 'space_recovery' not in launch.contract['input']['payload'])
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
                    # Review finding 5: the repeat stood. A run started afresh that ends unconfirmed is a new
                    # run with a repeat of its own, not a third of the same chain.
                    fresh, _, _, _ = end(f, free=1000, text='No space left on device; a later run')
                    again, _ = rerun(f, fresh)
                    check('history/unconfirmed-new-run', fresh['space_failure']['classification'] == ADM.UNCONFIRMED
                          and fresh['space_failure']['consecutive'] == 1 and fresh['space_failure']['retry']
                          and again is not None and len(f.started) == 4)
                finally:
                    f.close()
            row('ac2/repeat-red', unconfirmed)

            def bounded():
                for mode in ('report', 'act'):
                    f = Fixture('bounded-' + mode, mode)
                    conn = None
                    try:
                        first, _, _, _ = end(f)
                        if mode == 'act':
                            f.free['host'] = 1000
                            assert f.ledger.reconcile('console', [], [], {key: 0 for key in SP.RECONCILE_COUNTS})['ok']
                        launch, _ = rerun(f, first)
                        assert launch is not None
                        f.started.pop()
                        second, _, _, _ = end(f, contract=launch.contract)
                        obj = owner_line(f)
                        third, out = rerun(f, second, obj)
                        again, repeated = rerun(f, second, obj)
                        check('ac4/two-stop', third is None and again is None and len(f.started) == 2
                              and bool(out['stopped']) and second['space_failure']['consecutive'] == 2
                              and second['space_failure']['andon'])
                        asked = requests(f.conn)
                        check('ac4/owner-request', len(asked) == 1 and len(out['asked']) == 1 and not repeated['asked']
                              and out['asked'][0]['outcome'] and asked[0]['owner'] == 'owner'
                              and 'Andon' in asked[0]['brief'] and asked[0]['choices'] == ['rerun', 'acknowledge']
                              and [w['reason'] for w in repeated.get('awaiting', [])] == ['not_answered'])
                        check('history/latest', obj.latest()[('unit', 'build')]['dispatch_id'] == second['dispatch_id'])
                        # A restart (a second connection, a new Line) finds the same stop and the same request.
                        conn = S.open_store(str(f.state / 'store.sqlite3'))
                        restarted = owner_line(f, conn)
                        stored = D.Dispatches(S, conn, domain='domain', repository='repository', principal='runner',
                                              signer='runner', sign=f.sign).record(second['dispatch_id'])
                        after, seen = rerun(f, stored, restarted)
                        check('ac4/restart-stop', after is None and len(f.started) == 2 and not seen['asked']
                              and bool(seen['stopped']) and len(requests(conn)) == 1
                              and f.dispatches.charged('unit', 'build') == 0)
                        conn.close()
                        conn = None
                        # Review finding 2: the andon stops the repeats and refuses no dispatch. While it is not
                        # cleared, another station of the unit prepares: in report mode with the pool still
                        # short (nothing is blocked there), in act mode once admission has the space.
                        if mode == 'act':
                            f.free['host'] = 1000
                            assert f.ledger.reconcile('console', [], [], {key: 0 for key in SP.RECONCILE_COUNTS})['ok']
                        opened = None
                        try:
                            opened = f.prepare(station='review')
                        except D.Refused as error:
                            print('space317 later dispatch', mode, error.code)
                        check('ac4/later-dispatch-open', opened is not None and opened['station'] == 'review'
                              and len(requests(f.conn)) == 1)
                        # The defined, recorded clear: the owner's signed answer in the inbox.
                        ruling = 'rerun' if mode == 'report' else 'acknowledge'
                        answered = answer(f, obj, asked[0], ruling)
                        cleared, shown = rerun(f, second, obj)
                        record = requests(f.conn)[0]
                        recorded = (record.get('answer') or {}).get('ruling') == ruling and answered.get('ok') is True
                        if not recorded:
                            print('space317 answer', mode, answered)
                        if mode == 'report':
                            # rerun: the station is dispatched once more, with the next attempt number.
                            check('ac4/owner-clears', recorded and cleared is not None and len(f.started) == 3
                                  and cleared.contract['attempt'] == 3 and not shown.get('awaiting')
                                  and not shown['asked'])
                        else:
                            # acknowledge: closed and left stopped; the owner's next dispatch is prepared.
                            entry = (shown['stopped'] or [{}])[-1]
                            later = None
                            try:
                                later = f.prepare()
                            except D.Refused as error:
                                print('space317 after acknowledge', error.code)
                            check('ac4/owner-clears', recorded and cleared is None and len(f.started) == 2
                                  and entry.get('cleared') is True and entry.get('ruling') == 'acknowledge'
                                  and not shown.get('awaiting') and not shown['asked']
                                  and later is not None and later['attempt'] == 3)
                    finally:
                        if conn is not None:
                            conn.close()
                        f.close()
            row('ac4/two-stop', bounded)

            def worker_andon():
                import os
                import select
                f = Fixture('worker-andon', 'report')
                consumer = load('control_space_consumer').Consumer(f.ledger)
                try:
                    first, _, _, _ = end(f)
                    launch, _ = rerun(f, first)
                    f.started.pop()
                    second, _, _, _ = end(f, contract=launch.contract)
                    obj = owner_line(f)
                    obj.service.space_consumer = consumer
                    wakes = []
                    obj.loop = types.SimpleNamespace(wake=lambda *args: wakes.append(args))
                    entered_r, entered_w = os.pipe()
                    release_r, release_w = os.pipe()
                    original = SV.Line.open_question
                    def blocked(one, *args):
                        os.write(entered_w, str(os.getpid()).encode())
                        os.read(release_r, 1)
                        return 'owner', {'ok': False, 'reason': 'delivery_unavailable'}
                    def drain():
                        while consumer.active:
                            ready, _, _ = select.select(list(consumer.pipes()), [], [], 120)
                            assert ready, 'worker did not complete'
                            for fd in ready:
                                consumer.readable(fd)
                    try:
                        with patch.object(SV.Line, 'open_question', blocked):
                            # Copying the line must retain the class method, not a fixture-bound override.
                            del obj.open_question
                            stopped, out = rerun(f, second, obj)
                            ready, _, _ = select.select([entered_r], [], [], 120)
                            assert ready
                            pid = int(os.read(entered_r, 100))
                            check('ac4/off-loop', stopped is None and pid != os.getpid()
                                  and len(f.started) == 2 and not requests(f.conn) and not wakes)
                            os.write(release_w, b'x')
                            drain()
                        stopped, out = rerun(f, second, obj)
                        failed = out['asked'] and out['asked'][0]['refusal'] == 'delivery_unavailable'
                        drain()
                        stopped, out = rerun(f, second, obj)
                        check('fix2/andon-redelivery', failed and stopped is None and len(requests(f.conn)) == 1
                              and len(f.started) == 2 and len(wakes) == 2 and consumer.active is None)
                    finally:
                        for fd in (entered_r, entered_w, release_r, release_w):
                            os.close(fd)
                finally:
                    consumer.stop()
                    f.close()
            row('ac4/off-loop', worker_andon)

            def scoped():
                # Review finding 4: the state is on the unit's own index slots, read by their key range.
                f = Fixture('scoped', 'report')
                try:
                    end(f, contract=f.prepare(unit='unit2'))
                    end(f, free=1000, text='built', code=0, contract=f.prepare(unit='uni'), edits=False)
                    own, _, _, _ = end(f)
                    check('history/unit-scoped', own['space_failure']['consecutive'] == 1
                          and own['space_failure']['retry'] and not own['space_failure']['andon'])
                    statements = []
                    f.conn.set_trace_callback(statements.append)
                    try:
                        slots = f.dispatches.unit_slots('unit')
                        ADM.disposition(slots, own['contract'], {'classification': ADM.NO_SPACE, 'pools': [],
                                                                 'worktree': None})
                        ADM.ended(slots, own['contract'], None)
                        ADM.brief(f.dispatches.unit_slots('uni'), f.ledger, {})
                    finally:
                        f.conn.set_trace_callback(None)
                    plans = [' '.join(str(part[-1]) for part in f.conn.execute(
                        'EXPLAIN QUERY PLAN ' + sql)) for sql in statements]
                    check('history/bounded-read', len(statements) == 2
                          and all('SEARCH' in plan and 'id>? AND id<?' in plan and 'SCAN' not in plan for plan in plans)
                          and [(slot['unit'], slot['station']) for slot in slots] == [('unit', 'build')]
                          and not hasattr(ADM, 'previous'))
                    if not all('id>? AND id<?' in plan for plan in plans):
                        print('space317 plans', plans)
                finally:
                    f.close()
            row('history/unit-scoped', scoped)

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
                    for message in (b'write: ENOSPC', b'[Errno 28]'):
                        token = ADM.Output()
                        token.feed('stderr', message)
                        check('classify/streams', token.found)
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
