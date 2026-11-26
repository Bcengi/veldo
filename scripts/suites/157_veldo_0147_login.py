"""VELDO-0147 main-node login delivery rows. The real Mac run is proof/VELDO-0147/mac-claude-leg.json."""


def _v147_login():
    import importlib.util
    import io
    import json
    from pathlib import Path
    import tempfile
    import time

    spec = importlib.util.spec_from_file_location('v147_login', ROOT / 'engine/.veldo/project_runner_macos_login.py')
    L = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(L)
    now = time.time()

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
        assert b'ref-147' not in body and b'refresh_token' not in body and sorted(values) == ['acc-147', 'id-147']
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

    # The registered falsifiers (scripts/check_teeth_mutations.py, finding 147) replace these two production
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

    for name, test in {'AC4/claude-frame-access-only': claude_frame, 'AC1/claude-frame-refusals': claude_refusals,
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
