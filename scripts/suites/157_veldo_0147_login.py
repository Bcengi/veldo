"""VELDO-0147 main-node login delivery rows. The real Mac run is proof/VELDO-0147/mac-claude-leg.json."""


def _v147_login():
    import importlib.util
    import io
    import json
    from pathlib import Path
    import tempfile

    spec = importlib.util.spec_from_file_location('v147_login', ROOT / 'engine/.veldo/project_runner_macos_login.py')
    L = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(L)
    now = 1_900_000_000.0  # a fixed instant: frame() takes the clock as an argument

    def refused(call, code):
        try:
            call()
        except L.Refused as error:
            assert error.code == code, error.code
            return
        raise AssertionError('not refused: ' + code)

    def claude(base, **oauth):
        values = dict(accessToken='access-value-147', refreshToken='refresh-value-147', subscriptionType='pro',
                      expiresAt=(now + 7200) * 1000, scopes=['user:inference'])
        values.update(oauth)
        Path(base, '.credentials.json').write_text(json.dumps({'claudeAiOauth': values}))
        return base

    def claude_frame(base):
        body, values = L.frame('claude_code', claude(base), 'd-147', 'acct-test', now=now)
        document = json.loads(body)
        assert document['schema'] == L.SCHEMA and set(document['files']) == {'.credentials.json'}
        assert values == ['access-value-147']
        assert b'refresh-value-147' not in body and b'refreshToken' not in body
        assert json.loads(document['files']['.credentials.json'])['claudeAiOauth']['accessToken'] == 'access-value-147'

    def claude_refusals(base):
        refused(lambda: L.frame('claude_code', claude(base, expiresAt=(now + 60) * 1000), 'd', 'a', now=now),
                'unavailable_service:login_expires_before_run')
        refused(lambda: L.frame('claude_code', claude(base, subscriptionType=None), 'd', 'a', now=now),
                'unsupported_configuration:no_subscription_login')
        refused(lambda: L.frame('gemini', claude(base), 'd', 'a', now=now), 'unsupported_configuration:engine')

    def codex_frame(base):
        auth = dict(OPENAI_API_KEY=None, last_refresh='2026-11-26T00:00:00Z',
                    tokens=dict(id_token='id-147', access_token='acc-147', refresh_token='ref-147', account_id='x'))
        Path(base, 'auth.json').write_text(json.dumps(auth))
        body, values = L.frame('codex', base, 'd', 'codex-test', now=now)
        assert b'ref-147' not in body and sorted(values) == ['acc-147', 'id-147']
        # The field the pinned binary requires is present and empty: nothing on the Mac can rotate the login.
        assert json.loads(json.loads(body)['files']['auth.json'])['tokens']['refresh_token'] == ''
        Path(base, 'auth.json').write_text(json.dumps(dict(auth, OPENAI_API_KEY='sk-147')))
        refused(lambda: L.frame('codex', base, 'd', 'a', now=now), 'unsupported_configuration:no_subscription_login')

    def mac_side_refusals(base):
        # Every malformed frame is refused before a directory or RAM disk is made.
        class Stream:
            def __init__(self, data):
                self.buffer = io.BytesIO(data)
        good = json.dumps(dict(schema=L.SCHEMA, engine='claude_code', files={'.credentials.json': '{}'}))
        for data, code in ((json.dumps(dict(json.loads(good), schema='other')), 'invalid_input:frame'),
                           (json.dumps(dict(json.loads(good), files={'.credentials.json': '{}', 'x': ''})),
                            'invalid_input:frame_files'),
                           ('x' * (L.MAX_FRAME + 1), 'invalid_input:frame_size')):
            target = Path(base, 'login')
            refused(lambda: L.open_profile(target, Stream(data.encode())), code)
            assert not target.exists()
        Path(base, 'exists').mkdir()
        refused(lambda: L.open_profile(Path(base, 'exists'), Stream(good.encode())), 'stale_version:profile_base_exists')

    # The registered falsifiers (scripts/check_teeth_mutations.py, finding 147) replace these production
    # paths with a defective copy inside a complete module tree; every row below loads its modules from there.
    profile_module = ROOT / ".veldo" / "project_runner_macos_profile.py"
    control_module = ROOT / ".veldo" / "project_runner_macos_control.py"

    def mac_checks(directory):
        import os
        os.environ['VELDO_0124_MODULES'] = str(Path(directory))
        try:
            loaded = importlib.util.spec_from_file_location('v147_checks', ROOT / 'proof/VELDO-0124/checks.py')
            checks = importlib.util.module_from_spec(loaded)
            loaded.loader.exec_module(checks)
            return checks
        finally:
            os.environ.pop('VELDO_0124_MODULES', None)

    def unexpected_launch(base):
        # AC1 falsifier: the Mac's pinned executable changes after it was bound; the Mac host must refuse
        # before anything is launched, so no engine the qualification did not bind ever runs.
        T = mac_checks(profile_module.parent)
        host, osx, request, paths = T.start(base)
        engine = request['engine']
        pinned = base / 'pinned-engine'
        pinned.write_bytes(b'#!/bin/sh\nexit 0\n')
        host.profile['engines'][engine]['argv'][0] = str(pinned)
        host.profile['engines'][engine]['binary_digest'] = T.P.file_digest(str(pinned))
        T.evidence_fixture(host.profile, host.qualification)
        T.P.qualify(host.profile, host.qualification, host.os.facts(), engine,
                    request['contract']['capability']['configuration_digest'])  # bound: admitted
        with open(pinned, 'ab') as stream:
            stream.write(b'# changed after binding\n')
        T.refused(lambda: host.start(request), 'stale_version:engine_binary')
        assert osx.bootstraps == 0

    def paid_api_stop(base):
        # AC2 falsifier: OPENAI_API_KEY must never reach the Mac engine environment: an adapter that
        # configures it is refused by name, and the inherited set never carries it.
        loaded = importlib.util.spec_from_file_location('v147_control', control_module)
        C = importlib.util.module_from_spec(loaded)
        loaded.loader.exec_module(C)

        class Host:
            class os:
                @staticmethod
                def facts():
                    return {'host': 'mac-147'}

            @staticmethod
            def run_environment(dispatch, scratch):
                return {'HOME': scratch + '/home'}
        account = dict(id='codex-147', status='active', provider='codex', profiles={'mac-147': str(base / 'login')})
        login, environment = C.engine_environment(Host, account, 'd-147', str(base), {})
        assert login == str(base / 'login') and environment['CODEX_HOME'] == login
        assert 'OPENAI_API_KEY' not in environment and 'CODEX_API_KEY' not in environment
        for key in ('OPENAI_API_KEY', 'CODEX_API_KEY'):
            try:
                C.engine_environment(Host, account, 'd-147', str(base), {key: 'sk-planted-147'})
            except Exception as error:
                assert getattr(error, 'code', '') == 'invalid_input:adapter_environment:' + key, error
            else:
                raise AssertionError('paid-API key reached the Mac engine environment: ' + key)

    launch_module = ROOT / ".veldo" / "control_launch.py"

    def relay_fixture(base):
        """The VELDO-0125 authority fixture over this tree's modules, with one prepared Claude dispatch whose
        account's main-node profile holds a subscription login good far past any run."""
        import os
        import types
        os.environ['VELDO_0125_MODULES'] = str(launch_module.parent)
        try:
            loaded = importlib.util.spec_from_file_location('v147_relay', ROOT / 'proof/VELDO-0125/checks.py')
            T = importlib.util.module_from_spec(loaded)
            loaded.loader.exec_module(T)
        finally:
            os.environ.pop('VELDO_0125_MODULES', None)
        f = T.Fixture(base / 'authority')
        launch = T.W.SV.L
        profile = base / 'main-profile'
        profile.mkdir()
        claude(profile, expiresAt=4_102_444_800_000)
        record = dict(id='account', status='active', provider='claude_code', profiles={'main': str(profile)})
        launch.ACC.read = lambda conn, account: record if account == 'account' else None
        server = dict(id='tracker', revision=1, transport='http', command=None, arguments=[], url='https://tracker.invalid/mcp',
                      environment={}, headers={'Authorization': {'credential': 'tracker-token', 'handle':
                                                                 types.SimpleNamespace(reveal=lambda: 'Bearer mcp-value-147')}})
        launch.DL.selections = lambda configuration: [('tracker', 1)]
        launch.DL.resolve = lambda conn, domain, configuration, keystore=None: [server]
        return T, f, launch

    def sink(base):
        import sys
        received = base / 'received'
        return received, dict(argv=[sys.executable, '-c', 'import sys; open(sys.argv[1], "wb").write(sys.stdin.buffer.read())',
                                    str(received)], login='delivered', main_host='main')

    def relay_frames(base):
        # AC4 on the relay transport: the binding line is identity only; the login and the one secrets frame
        # follow it on the same channel; what is kept names ids, never a value.
        T, f, launch = relay_fixture(base)
        try:
            contract = f.prepare(required=['macos'], engine='claude_code')['contract']
            assert launch.remote_frames(dict(argv=['x']), contract, f.conn) == ([], None)
            received, receiver = sink(base)
            started = launch.invoke_remote(receiver, contract, f.ds)
            assert started.result == 'pending', (started.result, (started.record or {}).get('refusal'))
            started.child.wait(timeout=T.WAIT_HANG_SECONDS)
            lines = received.read_bytes().splitlines()
            assert len(lines) == 3, len(lines)
            packet = json.loads(lines[0])
            assert set(packet) == {'dispatch_id', 'contract_digest', 'domain', 'repository'}, sorted(packet)
            values = (b'access-value-147', b'mcp-value-147', b'refresh-value-147')
            assert not any(value in lines[0] for value in values), 'a credential value is in the packet'
            login, secrets = json.loads(lines[1]), json.loads(lines[2])
            assert login['schema'] == L.SCHEMA and login['dispatch'] == contract['dispatch_id'] and login['account'] == 'account'
            assert b'access-value-147' in lines[1] and b'refresh' not in lines[1] and b'mcp-value-147' not in lines[1]
            assert secrets['schema'] == L.SECRETS_SCHEMA and secrets['credentials'] == ['tracker-token']
            assert secrets['dispatch'] == contract['dispatch_id'] and set(secrets['files']) == {L.SECRETS_FILE}
            entry = json.loads(secrets['files'][L.SECRETS_FILE])['mcpServers']['tracker']
            assert entry['headers'] == {'Authorization': 'Bearer mcp-value-147'} and b'access-value-147' not in lines[2]
            report = started.delivered
            assert report['credentials'] == ['tracker-token'] and report['account'] == 'account'
            assert report['login_frame'] and report['secrets_frame']
            assert [route['route'] for route in report['routes']] == ['private_file']
            kept = json.dumps([report, contract, f.ds.record(contract['dispatch_id'])]).encode()
            f.conn.commit()
            kept += b''.join(path.read_bytes() for path in sorted(f.store.parent.glob(f.store.name + '*')))
            assert not any(value in kept for value in values), 'a credential value was kept on the main node'
        finally:
            f.close()

    def relay_refusal(base):
        # A login that cannot be delivered refuses the dispatch by name and contacts no receiver.
        T, f, launch = relay_fixture(base)
        try:
            contract = f.prepare(required=['macos'], engine='claude_code')['contract']
            launch.ACC.read = lambda conn, account: None
            received, receiver = sink(base)
            refused_launch = launch.invoke_remote(receiver, contract, f.ds)
            assert refused_launch.result == 'refused' and refused_launch.child is None
            assert refused_launch.record['refusal'] == 'missing_authority:account', refused_launch.record['refusal']
            assert not received.exists()
        finally:
            f.close()

    def mac_delivery(base):
        # The Mac receiver's side: frames checked before a disk is made, the secrets file 0600 in a 0700
        # directory on the mounted login only, and nothing left after close.
        login, _ = L.frame('claude_code', claude(base), 'd-147', 'acct-test', now=now)
        secrets = L.secrets_frame('d-147', 'acct-test', {'tracker': {'type': 'http', 'url': 'https://tracker.invalid/mcp',
                                  'headers': {'Authorization': 'Bearer mcp-value-147'}}}, {'tracker-token'})
        target = base / 'login'
        for lines, arguments, code in (
                (None, ('d-147', 'acct-test', 'claude_code'), 'missing_evidence:login_frame'),
                ([secrets], ('d-147', 'acct-test', 'claude_code'), 'missing_evidence:login_frame'),
                ([login], ('d-other', 'acct-test', 'claude_code'), 'binding_mismatch:login_frame'),
                ([login], ('d-147', 'acct-other', 'claude_code'), 'binding_mismatch:login_frame'),
                ([login], ('d-147', 'acct-test', 'codex'), 'binding_mismatch:login_frame'),
                ([login, L.secrets_frame('d-other', 'acct-test', {}, [])], ('d-147', 'acct-test', 'claude_code'),
                 'binding_mismatch:secrets_frame'),
                ([login, login], ('d-147', 'acct-test', 'claude_code'), 'invalid_input:frame'),
                ([login, secrets, secrets], ('d-147', 'acct-test', 'claude_code'), 'invalid_input:frame'),
                ([login, b'{"schema": "other"}'], ('d-147', 'acct-test', 'claude_code'), 'invalid_input:frame'),
                ([login, b'x' * (L.MAX_FRAME + 1)], ('d-147', 'acct-test', 'claude_code'), 'invalid_input:frame_size')):
            refused(lambda: L.Delivery(lines, target, *arguments), code)
        assert not target.exists()
        delivery = L.Delivery([login.decode(), secrets.decode()], target, 'd-147', 'acct-test', 'claude_code')
        mounted = []

        def fake_open(directory, stream):
            # Linux has no hdiutil: the mount is a plain directory here; the real one is the Mac run's evidence.
            assert json.loads(stream.read())['files']
            (Path(directory) / 'profile').mkdir(parents=True, mode=0o700)
            mounted.append(Path(directory) / 'profile')
            return dict(status='open')

        def fake_close(directory):
            import shutil
            shutil.rmtree(directory)
            mounted.clear()
            return dict(status='closed')
        real = L.open_profile, L.close_profile, L._mounted
        L.open_profile, L.close_profile, L._mounted = fake_open, fake_close, lambda path: Path(path) in [m.resolve() for m in mounted]
        try:
            refused(lambda: L.write_secrets(target, secrets), 'unavailable_service:ram_disk_mount')
            assert delivery.open() == str(target / 'profile')
            assert not (target / 'profile' / L.SECRETS_DIRECTORY).exists(), 'the secrets file was written before acceptance'
            delivery.secrets()
            written = delivery.report['secrets']
            assert written['file_mode'] == '0o600' and written['directory_mode'] == '0o700'
            assert written['credentials'] == ['tracker-token'] and 'mcp-value-147' not in json.dumps(delivery.report)
            text = (target / 'profile' / L.SECRETS_DIRECTORY / L.SECRETS_FILE).read_text()
            assert json.loads(text)['mcpServers']['tracker']['headers']['Authorization'] == 'Bearer mcp-value-147'
            assert delivery.close() == dict(status='closed') and not target.exists()
            assert delivery.close() == dict(status='closed')  # a second close finds nothing and changes nothing
        finally:
            L.open_profile, L.close_profile, L._mounted = real

    for name, test in {'AC4/mac-no-value-in-packet': relay_frames, 'AC4/relay-login-refused-by-name': relay_refusal,
                       'AC4/mac-delivery-checked-and-removed': mac_delivery,
                       'AC4/claude-frame-access-only': claude_frame, 'AC1/claude-frame-refusals': claude_refusals,
                       'AC2/codex-frame-access-only': codex_frame, 'AC4/mac-frame-refusals': mac_side_refusals,
                       'AC1/mac-unexpected-launch': unexpected_launch, 'AC2/mac-paid-api-stop': paid_api_stop}.items():
        with tempfile.TemporaryDirectory(prefix='v147-login-') as directory:
            try:
                test(Path(directory))
                expect('VELDO-0147 ' + name, True)
            except Exception as error:
                print('  ' + name + ': ' + type(error).__name__ + ': ' + str(error)[:250])
                expect('VELDO-0147 ' + name, False)


_v147_login()
