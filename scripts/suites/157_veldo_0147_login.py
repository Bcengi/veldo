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

    for name, test in {'AC4/claude-frame-access-only': claude_frame, 'AC1/claude-frame-refusals': claude_refusals,
                       'AC2/codex-frame-access-only': codex_frame, 'AC4/mac-frame-refusals': mac_side_refusals}.items():
        with tempfile.TemporaryDirectory(prefix='v147-login-') as directory:
            try:
                test(Path(directory))
                expect('VELDO-0147 ' + name, True)
            except Exception as error:
                print('  ' + name + ': ' + type(error).__name__ + ': ' + str(error)[:250])
                expect('VELDO-0147 ' + name, False)


_v147_login()
