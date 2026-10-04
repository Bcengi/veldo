"""VELDO-0170: installed receiver refusal, status, and the setup re-run's trust repair.

Only ROOT and expect are shared. All keys and tokens are generated. Setup and the installer
write the configurations, signed settlement writes the governing binding, Runner prepares the
dispatch, and the real receiver process accepts or refuses it. No model or real manager runs.
"""


def _v170_suite():
    import contextlib
    import importlib.util
    import io
    import json
    import os
    from pathlib import Path
    import shutil
    import stat
    import subprocess
    import sys
    import tempfile
    import time

    PRODUCTION = {
        'control_launch.py': ROOT / ".veldo" / "control_launch.py",
        'control_service.py': ROOT / ".veldo" / "control_service.py",
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
        'control_factory_setup_trust.py': ROOT / ".veldo" / "control_factory_setup_trust.py",
        'control_factory_setup_upgrade.py': ROOT / ".veldo" / "control_factory_setup_upgrade.py",
        'init_scaffold.py': ROOT / ".veldo" / "init_scaffold.py",
    }
    names = ('launch/governed', 'launch/ungoverned', 'status/configurations',
             'rerun/launch-after-repair', 'rerun/no-installed-trust', 'rerun/host-identity',
             'rerun/differs', 'rerun/differs/workspace', 'rerun/differs/store',
             'rerun/differs/journal_key', 'rerun/default-trust', 'rerun/records')
    rows = {name: [] for name in names}

    def check(row, label, ok):
        rows[row].append((label, bool(ok)))

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def write(path, value):
        path.write_text(json.dumps(value, indent=2) + '\n')
        path.chmod(0o600)

    def differences(before, after):
        return str([k for k in sorted(set(before) | set(after)) if before.get(k) != after.get(k)])

    def snapshot(root):
        import sqlite3
        files = {str(p): (p.read_bytes(), stat.S_IMODE(p.stat().st_mode), p.stat().st_mtime_ns)
                for p in root.rglob('*') if p.is_file() and not p.is_symlink() and not p.name.endswith(('-shm', '-wal'))}
        for path in root.rglob('*.sqlite3'):
            with contextlib.closing(sqlite3.connect('file:' + str(path) + '?mode=ro', uri=True)) as db:
                files[str(path) + ':logical'] = tuple(db.iterdump())
        return files

    base = Path(tempfile.mkdtemp(prefix='v170-', dir='/dev/shm'))
    cache = Path(tempfile.mkdtemp(prefix='d170-', dir='/dev/shm'))
    runtime = load('v170_runtime', ROOT / 'scripts/suites/support/setup_runtime.py')
    close_runtime = runtime.install(base, cache)
    prior_bytecode = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    prior_path = os.environ.get('PATH', '')
    prior_xdg = os.environ.get('XDG_CONFIG_HOME')
    stop_bot = None
    ts = None
    writer = reader = None
    try:
        mods = base / 'src' / '.veldo'
        shutil.copytree(ROOT / '.veldo', mods, ignore=shutil.ignore_patterns('__pycache__'))
        for name, source in PRODUCTION.items():
            if source.is_file():
                shutil.copyfile(source, mods / name)
            elif (mods / name).exists():
                (mods / name).unlink()
        engines = load('v170_engines', ROOT / 'proof/VELDO-0186/fixtures.py').install(ROOT, base, mods)
        os.environ['PATH'] = str(engines['path']) + os.pathsep + prior_path
        os.environ['XDG_CONFIG_HOME'] = str(base / 'xdg')
        F = load('v170_setup', mods / 'control_factory_setup.py')
        CS = load('v170_service', mods / 'control_service.py')
        EL = load('v170_eligibility', mods / 'control_eligibility.py')
        CE = load('v170_enrollment', mods / 'control_enrollment.py')
        ACT = load('v170_activation', mods / 'control_channel_activation.py')
        GP = load('v170_git', mods / 'git_process.py')
        H = load('v170_bot', ROOT / 'scripts/suites/support/v73_authority.py')
        TS = load('v170_tailscale', ROOT / 'scripts/suites/support/v171_tailscale.py')
        ts = TS.stand_in(ROOT / 'proof/VELDO-0171/tailscale-capture.json', sys.executable)
        token = 'fixture' + os.urandom(10).hex()
        chat = 5590170
        url, bot, stop_bot = H.stand_in({token: {'id': 8000000170, 'is_bot': True,
                                               'first_name': 'Veldo', 'username': 'fixture_bot'}})
        bot['chats'][chat] = {'id': chat, 'type': 'private', 'first_name': 'Owner'}
        person = base / 'person'
        person.mkdir(mode=0o700)
        key = person / 'owner'
        F._keygen(key, 'fixture-owner')
        token_file = person / 'token'
        F._private(token_file, token + '\n')
        root, repo, install, units = [base / n for n in ('state', 'repo', 'install', 'units')]
        root.mkdir(mode=0o700)
        trust = base / 'xdg/veldo/host_trust.json'
        trust.parent.mkdir(mode=0o700, parents=True)
        GP.run(['git', 'init', '-q', str(repo)], check=True, capture_output=True)
        (repo / 'README').write_text('receiver source\n')
        GP.run(['git', '-C', str(repo), 'add', 'README'], check=True, capture_output=True)
        GP.run(['git', '-C', str(repo), '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture'],
               check=True, capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        profile = {'kind': 'linux-systemd', 'slice': 'v170' + os.urandom(3).hex() + '.slice',
                   'lock': str(base / 'worker.lock'), 'concurrency': 1, 'runtime_seconds': 600,
                   'memory_bytes': 256 << 20, 'cpu_percent': 100, 'file_bytes': 64 << 20,
                   'tasks_max': 256, 'stop_grace_seconds': 1, 'kill_grace_seconds': 1}

        class Manager:
            def run(self, args):
                if args[0] == 'show':
                    return 0, 'LoadState=loaded\nActiveState=inactive\nMainPID=0\nFragmentPath=' + str(units / args[-1]) + '\n', ''
                return 0, '', ''
        manager = Manager()
        options = dict(host_trust=str(trust), install_root=str(install), unit_dir=str(units),
                       profile=profile, writable=[], runner=manager, origin=url,
                       tailscale=[ts.path], api_port=TS.free_port())

        def setup():
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    return F.setup(str(root), 'owner', str(key), str(repo), chat, str(token_file), **options)
            except F.Refused as error:
                return {'outcome': 'refused', 'reason': error.code}

        fresh = setup()
        check('rerun/launch-after-repair', 'fresh production setup succeeded: ' + str(fresh.get('reason')),
              fresh.get('outcome') == 'set_up')
        if not fresh.get('home'):
            return rows
        home = Path(fresh['home'])
        config_path = home / 'config/service.json'
        installed = json.loads(config_path.read_text())
        ids = fresh['authority_ids']
        # A second repository, enrolled by the owner and written by the same real installer.
        other = base / 'other'
        GP.run(['git', 'init', '-q', str(other)], check=True, capture_output=True)
        GP.run(['git', '-C', str(other), '-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-qm', 'fixture'],
               check=True, capture_output=True, identity=('Fixture', 'fixture@example.invalid'))
        CE.enroll(str(other), ids['domain_uuid'], ids['store_uuid'], fresh['store'], fresh['host_identity'], 1,
                  ACT.ssh_signer(str(key), EL.ENROLLMENT_NAMESPACE), 'owner', time.time(), repository_uuid='repository-other')
        CS.uninstall(fresh['unit'], install_root=str(install), unit_dir=str(units), runner=manager)
        CS.install([str(repo), str(other)], host_trust=str(trust), install_root=str(install), unit_dir=str(units),
                   state_root=str(root), key_directory=str(root / 'keys'), profile=profile, writable=[], runner=manager,
                   channel_ingress=fresh['ingress'], api_service=str(root / 'host/api-service.json'),
                   adapters={'owner-worker': {'argv': ['/bin/true']}})
        installed = json.loads(config_path.read_text())
        paths = [Path(installed['receiver']['configs'][r]) for r in (ids['repository_uuid'], 'repository-other')]
        # Reinstalling the service replaces every receiver. A setup rerun must add
        # record configuration to both repositories before the trust-only snapshots.
        result = setup()
        check('rerun/records', 'all installed repositories share the record directory and service',
              result.get('outcome') == 'set_up' and all(
                  json.loads(path.read_text()).get('records') == str(root / 'records')
                  and json.loads(path.read_text()).get('record_hint_service') == installed['socket']
                  for path in paths))
        old, current = paths
        legacy = json.loads(old.read_text())
        legacy.pop('host_trust')
        write(old, legacy)
        current_bytes = current.read_bytes()
        old_bytes = old.read_bytes()
        # The canonical status surfaces read actual installed files, including after repair.
        lifecycle = CS.status(fresh['unit'], manager).get('receivers', {})
        service = CS.Service(installed, CS.S.open_store(fresh['store']))
        try:
            observed = service.inspect({'entity_ids': []}).get('receivers', {})
        finally:
            service.conn.close()
        missing = lifecycle.get('refusals', [])
        check('status/configurations', 'both service status surfaces list exactly the old receiver with one repair',
              lifecycle == observed and len(missing) == 1 and missing[0].get('configuration') == str(old)
              and missing[0].get('repository') == ids['repository_uuid']
              and missing[0].get('refusal') == 'host_trust_required:receiver_configuration'
              and 'veldo factory setup' in missing[0].get('repair', '')
              and lifecycle.get('metrics', {}).get('host_trust_required') == 1)

        # Real setup refuses before changing any host file, for each malformed installation.
        ingress_path = Path(installed['channel_ingress'])
        ingress_bytes = ingress_path.read_bytes()
        for row, mode in (('rerun/no-installed-trust', 'absent'), ('rerun/no-installed-trust', 'unreadable'),
                          ('rerun/host-identity', 'identity')):
            ingress = json.loads(ingress_bytes)
            if mode == 'identity':
                foreign = base / 'foreign.json'
                data = json.loads(trust.read_text())
                data['host_identity'] = 'another-host'
                write(foreign, data)
                ingress['host_trust'] = str(foreign)
            else:
                named = base / 'missing-trust.json'
                if mode == 'unreadable':
                    named.write_text('invalid json')
                ingress['host_trust'] = str(named)
            write(ingress_path, ingress)
            before = snapshot(base)
            refused = setup()
            check(row, mode + ': refused by name without any file changes: ' + str(refused.get('reason')) + differences(before, snapshot(base)),
                  refused.get('reason') == ('host_trust_required:host_identity' if mode == 'identity' else 'host_trust_required')
                  and snapshot(base) == before)
            ingress_path.write_bytes(ingress_bytes)
        for field in ('principal', 'workspace', 'store', 'journal_key'):
            # Start from the same legacy file each time so every comparison stands alone.
            changed = dict(legacy, **{field: legacy[field] + '-different'})
            write(old, changed)
            before = snapshot(base)
            refused = setup()
            after = snapshot(base)
            row = 'rerun/differs' if field == 'principal' else 'rerun/differs/' + field
            check(row, 'changed ' + field + ' is refused before any writes: '
                  + str(refused.get('reason')) + differences(before, after),
                  refused.get('reason') == 'invalid_input:state_root:differs:' + str(old) and after == before)
            old.write_bytes(old_bytes)
        # Missing ingress key uses the installed default, with its identity still checked.
        ingress = json.loads(ingress_bytes)
        ingress.pop('host_trust')
        write(ingress_path, ingress)
        result = setup()
        step = next((s for s in result.get('steps', []) if s['step'] == 'receiver_host_trust'), {})
        check('rerun/default-trust', 'default trust comes from the host and is reported by the repair step',
              step.get('host_trust') == str(trust) and step.get('added') == [str(old)]
              and json.loads(old.read_text()).get('host_trust') == str(trust))
        ingress_path.write_bytes(ingress_bytes)
        old.write_bytes(old_bytes)
        before = snapshot(home / 'config')
        result = setup()
        step = next((s for s in result.get('steps', []) if s['step'] == 'receiver_host_trust'), {})
        repaired = json.loads(old.read_text())
        check('rerun/launch-after-repair', 'only the missing key is added at 0600; current bytes stay unchanged',
              result.get('outcome') == 'set_up' and repaired == dict(legacy, host_trust=str(trust))
              and stat.S_IMODE(old.stat().st_mode) == 0o600 and current.read_bytes() == current_bytes
              and step.get('added') == [str(old)] and step.get('current') == [str(current)]
              and step.get('metrics') == {'added': 1, 'current': 1})
        after = snapshot(home / 'config')
        check('rerun/launch-after-repair', 'other installed configuration files are untouched',
              {k: v for k, v in before.items() if k != str(old)} == {k: v for k, v in after.items() if k != str(old)})
        before = snapshot(base)
        again = setup()
        check('rerun/launch-after-repair', 'a second re-run changes nothing and reports both current: ' + str(again.get('outcome')) + differences(before, snapshot(base)),
              again.get('outcome') == 'already_set_up' and snapshot(base) == before)
        check('status/configurations', 'status clears on the next read without a service restart',
              CS.status(fresh['unit'], manager).get('receivers', {}).get('refusals') == [])

        # The launch evidence uses the production dispatch and settlement interfaces.
        L = load('v170_launch', mods / 'control_launch.py')
        D, S = L.D, L.S
        CLM = D.CLM
        CM = CLM.CM
        writer = S.open_store(fresh['store'])
        serial = [0]
        sign = ACT.ssh_signer(str(root / 'keys/journal'), 'veldo-journal')

        def next_id():
            serial[0] += 1
            return 'v170-' + str(serial[0])

        def put(eid, kind, data):
            held = writer.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()
            return S.execute(writer, dict(command_id=next_id(), principal='authority', operation='upsert_entity',
                             nonce=next_id(), artifact_digests=[], expected_versions={eid: held[0] if held else 0},
                             parameters=dict(entity_id=eid, kind=kind, data=data)), 'authority', sign, 1)

        for principal in ('runner', 'launch-receiver'):
            put(principal, 'membership', dict(principal_type='service', roles=[], scope=[ids['repository_uuid'], 'repository-other'],
                                             revoked_at=None, expires_at=None))
        put('project:p1', 'project', {'name': 'receiver trust'})
        put('authority:' + ids['domain_uuid'], 'authority', {'state': 'active', 'generation': 1})
        reservations_by_repo = {}
        for repository in (ids['repository_uuid'], 'repository-other'):
            reservations = D.RES.Reservations(S, writer, domain=ids['domain_uuid'], repository=repository,
                principal='runner', authorize=lambda c, cmd: True, signer='authority', sign=sign)
            reservations_by_repo[repository] = reservations
            for scope, subject in (('account', 'acct-170'), ('project', 'p1')):
                reservations.configure(next_id(), scope, subject,
                                       dict(capacity=50, invocations=50, wall_seconds=5000), now=time.time())
        for sid, repository in (('VELDO-9701', ids['repository_uuid']), ('VELDO-9702', ids['repository_uuid']),
                                ('VELDO-9703', 'repository-other')):
            put(sid, 'execution_unit', dict(state='READY', repository_uuid=repository,
                backlog_item_uuid='backlog:' + sid, requirements=[], eligible_holders=['worker'], project='p1',
                scope_digest='sha256:scope-' + sid, revision=1, depends_on=[]))
            put('backlog:' + sid, 'backlog_item', dict(state='PRIORITIZED', repository_uuid=repository))
            put('admission:' + sid, 'admission', dict(unit=sid, state='accepted', scope_digest='sha256:scope-' + sid))
            reservations_by_repo[repository].configure(next_id(), 'unit', sid,
                dict(capacity=20, invocations=20, wall_seconds=2000), now=time.time())
            claim = CLM.claim_id(repository, sid)
            writer.command_registry['claim_operation'] = {'transaction_transition': CLM.transition,
                                                          'writes': ('entities', 'journal', 'commands', 'nonces')}
            versions = {eid: writer.execute('SELECT version FROM entities WHERE id=?', (eid,)).fetchone()[0]
                        for eid in (sid, 'backlog:' + sid)}
            S.execute(writer, dict(command_id=next_id(), principal='worker', operation='claim_operation', nonce=next_id(),
                artifact_digests=[], expected_versions=dict(versions, **{claim: 0}), parameters=dict(action='claim',
                unit_id=sid, backlog_item_uuid='backlog:' + sid, claim_id=claim, holder='worker', generation=0,
                capabilities=[], repository_uuid=repository)), 'authority', sign, 1)
        _v170_settle(load, mods, writer, ids, root, repo, url, token, bot, chat, H, F, put, next_id, sign)
        reader = S.open_store(fresh['store'], mode='r')
        gates, dispatches_by_repo = {}, {}
        for repository, workspace in ((ids['repository_uuid'], repo), ('repository-other', other)):
            gates[repository] = EL.Gate(S, reader, domain_uuid=ids['domain_uuid'], repository_uuid=repository,
                workspace=str(workspace), settlement_trust=EL.load_host_trust(str(trust)).settlement_trust(str(workspace)))
            dispatches_by_repo[repository] = D.Dispatches(S, writer, domain=ids['domain_uuid'], repository=repository,
                                                          principal='runner', signer='authority', sign=sign)
        markers = base / 'markers'
        markers.mkdir()
        worker = base / 'worker.py'
        worker.write_text('import os,sys\nfrom pathlib import Path\nsys.stdin.buffer.read()\n'
                          '(Path(sys.argv[1])/os.environ["VELDO_DISPATCH_ID"].replace("/","_")).write_text("ran")\n')

        def launch(path, governed=True, missing=False):
            # Substitute only this suite's worker transport in the installer-produced configuration.
            config = json.loads(path.read_text())
            repository, workspace = config['repository'], config['workspace']
            gate, dispatches = gates[repository], dispatches_by_repo[repository]
            reservations = reservations_by_repo[repository]
            config['adapters'] = {'fixture': {'identity': 'reported', 'argv': [sys.executable, '-B',
                str(mods / 'control_launch.py'), 'exec', sys.executable, '-B', str(worker), str(markers)]}}
            if missing:
                config.pop('host_trust', None)
            launch_path = base / ('launch-' + next_id() + '.json')
            write(launch_path, config)
            runner = L.Runner(gate, reservations, dispatches, lambda c: L.invoke(launch_path, c, dispatches), account='acct-170')
            sid = ('VELDO-9701' if governed else 'VELDO-9702') if repository == ids['repository_uuid'] else 'VELDO-9703'
            job = runner.submit(sid, 'build', holder='worker', source=workspace,
                revision='HEAD', payload={'task': 'proceed'}, adapter='fixture', configuration={'tools': ['Read']},
                deadline=time.time() + 30)
            runner.wait(job, timeout=15)
            record = dispatches.record(job.dispatch_id) or {}
            record['messages'] = job.messages
            return job.result, record, (markers / job.dispatch_id.replace('/', '_')).exists()

        for row, governed in (('launch/governed', True), ('launch/ungoverned', False)):
            result, record, ran = launch(old, governed, missing=True)
            check(row, 'missing receiver trust is named before acceptance or spawn: ' + str(record.get('refusal')),
                  result == 'refused' and record.get('refusal') == 'host_trust_required:receiver_configuration'
                  and [h['state'] for h in record.get('history', [])] == ['prepared', 'refused'] and not ran)
            event = next((m for m in record['messages'] if m.get('event') == 'refused'), {})
            check(row, 'refusal records configuration, repository, dispatch and count',
                  event.get('repository') == ids['repository_uuid'] and event.get('configuration')
                  and event.get('dispatch_id') == record.get('dispatch_id')
                  and event.get('metrics', {}).get('host_trust_required') == 1)
        for path in paths:
            result, record, ran = launch(path)
            check('rerun/launch-after-repair', 'governed work launches under repaired/current trust: ' + str(record.get('refusal')),
                  result == 'accepted' and record.get('state') == 'exited' and ran)
        # Both configurations still obey the actual settlement signer, not a permissive Gate.
        signers = Path(json.loads(trust.read_text())['settlement_signers'])
        original_signers = signers.read_bytes()
        foreign_key = person / 'foreign'
        public = F._keygen(foreign_key, 'fixture-foreign')
        signers.write_text('settlement namespaces="veldo-decision-settlement" ' + public + '\n')
        for path in paths:
            result, record, ran = launch(path)
            check('rerun/launch-after-repair', 'another signer cannot clear governed work',
                  result == 'refused' and str(record.get('refusal', '')).startswith('unsigned_decision:') and not ran)
        signers.write_bytes(original_signers)
    except Exception as error:
        for row in rows:
            check(row, 'fixture ran to its end (raised %s: %s)' % (type(error).__name__, str(error)[:240]), False)
    finally:
        conform_formats = load('v170_formats', Path(globals().get('__suite_file__', __file__)).resolve().parents[2] / 'proof/VELDO-0172/compare_formats.py')
        fake = engines['fake']
        issues, trace = conform_formats.conform_fake(locals(), '0170_receiver_trust')
        check('rerun/launch-after-repair', 'inert installation engines use shared constructors and conform at teardown: ' + str(issues), not issues)
        if reader is not None:
            reader.close()
        if writer is not None:
            writer.close()
        if stop_bot is not None:
            stop_bot()
        if ts is not None:
            ts.close()
        os.environ['PATH'] = prior_path
        if prior_xdg is None:
            os.environ.pop('XDG_CONFIG_HOME', None)
        else:
            os.environ['XDG_CONFIG_HOME'] = prior_xdg
        close_runtime()
        sys.dont_write_bytecode = prior_bytecode
        for directory in base.rglob("*"):
            if directory.is_dir() and not directory.is_symlink():
                directory.chmod(0o700)
        shutil.rmtree(base)
        shutil.rmtree(cache)
    return rows


def _v170_settle(load, mods, conn, ids, root, repo, url, token, bot, chat, H, F, put, next_id, sign):
    """A real signed request and Telegram answer produce the governing settlement binding."""
    import json
    import time
    claims = load('v170_claims', mods / 'control_claim.py')
    S, CM = claims.S, claims.CM
    I = load('v170_inbox', mods / 'control_assignment.py')
    P = load('v170_projection', mods / 'control_channel_projection.py')
    V = load('v170_presentation', mods / 'control_channel_presentation.py')
    ST = load('v170_settlement', mods / 'control_request_settlement.py')
    EV = load('v170_attribution', mods / 'control_channel_attribution.py')
    A = load('v170_answers', mods / 'control_signer_answers.py')
    ACT = load('v170_signing', mods / 'control_channel_activation.py')
    contract = load('v170_contract', mods / 'entity_contract.py')
    inbox = I.Inbox(S, CM, claims, contract, conn, ids, 'authority', sign)
    presenter = V.Presenter(S, CM, P, inbox, V.TelegramPresentationEdge(P, url, token), conn,
                            'authority', sign, assignment=I)
    settlement = ST.Settlement(S, CM, inbox, presenter, conn, 'authority', sign, assignment=I, presentation=V,
        decision_signer=('settlement', ACT.ssh_signer(str(root / 'keys/settlement'), 'veldo-decision-settlement')))
    sid, rid = 'VELDO-9701', 'decision:D-9701'
    subject = json.loads(conn.execute('SELECT data FROM entities WHERE id=?', (sid,)).fetchone()[0])
    record = dict(schema=ST.DD.GOVERNING_SCHEMA, decision_id='D-9701', revision=1,
                  framing_digest=ST.digest({'question': 'proceed'}),
                  subject=dict(kind='spec', id=sid, digest=ST.DD.subject_digest('spec', subject)),
                  scope=dict(operation='proceed', target=sid, parameters={}), blocks=[sid, 'VELDO-9703'], obligations=[])
    put(rid, 'decision', record)
    requester = F.REQUESTER
    signer = ACT.ssh_signer(str(root / 'keys' / F.REQUESTER_KEY))

    def signed(command):
        return {'command': command, 'signature': signer(S.canonical_bytes(command))}

    terms = settlement.terms(signed(dict(ids, operation='terms', terms='proceed', principal=requester,
        command_id=next_id(), nonce=next_id(), touchpoint='decision_disposition', target=ST.governing_target(rid, record),
        proposal=None, required_roles=[], quorum=None)))
    inbox.apply(signed(dict(ids, operation='open', alias='proceed', principal=requester, command_id=next_id(),
        nonce=next_id(), assignment=dict(kind='decision', owner='owner', scope=[F.REQUESTER_SCOPE],
        deadline='2030-01-01T00:00:00Z', budget={'owner_minutes': 15}, brief='Proceed with this unit.',
        choices=['accept', 'reject', 'return_for_elaboration'], subject=terms.get('subject', {})))))
    request = I.assignment_id(ids['repository_uuid'], 'proceed')
    presenter.frame(signed(dict(ids, operation='frame', alias='proceed', principal=requester, request_version=1,
        risk_statement='Low: fixture worker only.', command_id=next_id(), nonce=next_id())))
    presenter.present(request)
    receipt = presenter.current(request) or {}
    H.deliver(bot, token, {'id': chat, 'is_bot': False, 'first_name': 'Owner'}, 'accept: proceed',
              (receipt.get('message_ids') or [None])[-1])
    config = json.loads((root / 'host/ingress.json').read_text())
    edge = config['signer']
    adapter = A.EdgeSigner(S, CM, conn, edge['config'], edge['edge_key_id'], edge['connection_key'])
    acquirer = EV.Acquirer(S, CM, P, V, presenter, EV.TelegramAcquisitionEdge(P, url, token), conn,
                          'authority', sign, config['edge_principal'], adapter)
    acquirer.acquire()
    settlement.settle(request)


_v170_rows = _v170_suite()
for _v170_name, _v170_checks in _v170_rows.items():
    for _v170_label, _v170_ok in _v170_checks:
        if not _v170_ok:
            print('  VELDO-0170 %s detail: %s' % (_v170_name, _v170_label))
    expect('VELDO-0170 ' + _v170_name, bool(_v170_checks) and all(ok for _, ok in _v170_checks))
