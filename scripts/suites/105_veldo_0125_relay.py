"""0125: real signed relay/IPC/store boundaries; synthetic host observations."""


def _v125_suite():
    import copy
    import importlib.util
    import json
    import sqlite3
    import tempfile
    from pathlib import Path
    spec = importlib.util.spec_from_file_location('v125_checks', ROOT / 'proof/VELDO-0125/checks.py')
    T = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(T)

    def families(f):
        f.prepare(required=['macos'])
        f.start()
        client = f.client()
        binding = T.launch(client)
        result = client.result(binding, T.observation(), usage={'tokens': 7, 'wall_seconds': .1},
                               references={'output': 'sha256:output', 'proof': 'proof/synthetic'})
        assert {r['command']['command']['operation'] for r in client.sent} == set(T.CL.OPERATIONS)
        for request in client.sent:
            assert all(request[k] == f.binding[k] for k in ('domain_uuid', 'repository_uuid', 'store_uuid'))
            assert request['workspace'] == str(f.repo)
        with sqlite3.connect(f.store) as independent:
            data = json.loads(independent.execute('SELECT data FROM entities WHERE id=?',
                                                  ('worker:dispatch/test',)).fetchone()[0])
            assert data == result['record'] and data['state'] == 'exited'
            assert independent.execute('SELECT MAX(seq) FROM journal').fetchone()[0] == client.watermark
        assert data['host'] == 'mac' and data['unit'] == 'unit' and data['dispatch_id'] == 'dispatch/test'
        assert data['references']['proof'] == 'proof/synthetic' and data['usage']['tokens'] == 7
        invocation = f.res._records()[T.RES.entity('invocation', ['domain', data['invocation']])]
        assert invocation['dispatch'] == data['dispatch_id'] and invocation['context']['unit'] == data['unit']
        assert invocation['observed']['tokens'] == 7
        assert not T.D.completed(f.ds.record(data['dispatch_id']))

    def unavailable(f):
        local = f.base / 'mac-local'
        local.mkdir()
        before = set(local.rglob('*'))
        client = f.client(argv=[__import__('sys').executable, str(T.MODULES / 'control_relay.py'), str(local / 'absent.sock')])
        for op in T.CL.OPERATIONS:
            T.refused(lambda: client.send(op, {'dispatch_id': 'dispatch/test'}), 'AUTHORITY_UNAVAILABLE:')
        assert set(local.rglob('*')) == before, 'Mac-local fallback wrote authority state'
        assert not list(local.rglob('*.sqlite3'))

    def binding(f):
        f.prepare(required=['ios-build'])
        f.start()
        client = f.client()
        bound = T.launch(client)
        before = f.service.watermark()
        for key, value in (('dispatch_id', 'dispatch/other'), ('unit', 'other'), ('host', 'linux'),
                           ('contract_digest', T.D.digest('other'))):
            wrong = dict(bound, **{key: value})
            T.refused(lambda: client.result(wrong, T.observation(), usage={'tokens': 999}), 'binding_mismatch:')
        wrong = T.observation()
        wrong['process']['pid'] += 1
        T.refused(lambda: client.result(bound, wrong), 'binding_mismatch:')
        T.refused(lambda: f.client('outsider').result(bound, T.observation()), 'unauthorized:dispatch_host')
        assert f.service.watermark() == before
        client.result(bound, T.observation(), usage={'tokens': 7})
        T.refused(lambda: client.result(bound, T.observation(), usage={'tokens': 99}), 'binding_mismatch:')

    def auth(f):
        f.prepare(required=['macos'])
        f.start()
        for field in ('domain_uuid', 'store_uuid', 'repository_uuid', 'clone_uuid', 'binding_digest'):
            client = f.client()
            client.binding = dict(client.binding, **{field: 'wrong'})
            try:
                client.claim('dispatch/test')
            except T.CL.Refused:
                pass
            else:
                raise AssertionError('wrong coordinate accepted: ' + field)
        client = f.client()
        client.sign = lambda b: 'unsigned'
        T.refused(lambda: client.claim('dispatch/test'), 'command_signature_invalid')
        assert f.ds.record('dispatch/test')['state'] == 'prepared' and f.service.get('dispatch/test') is None

    def unknown(f):
        f.prepare(required=['macos'])
        f.start()
        client = f.client()
        bound = T.launch(client)
        client.result(bound, dict(state='unknown', process=T.process()), usage={'tokens': 0})
        assert f.ds.record(bound['dispatch_id'])['state'] == 'unknown'
        assert f.service.get(bound['dispatch_id'])['charge'] == 'unknown'
        assert not f.res.worker(bound['dispatch_id'])['retired']
        T.refused(lambda: client.claim(bound['dispatch_id']), 'stale_version:already_claimed')

    for row, test in {'AC1/command-families': families, 'AC1/one-authority': unavailable,
                      'AC1/authentication': auth, 'AC3/remote-result-binding': binding,
                      'AC3/unknown-charge': unknown}.items():
        with tempfile.TemporaryDirectory(prefix='v125-') as directory:
            fixture = None
            try:
                fixture = T.Fixture(Path(directory))
                test(fixture)
                expect('VELDO-0125 ' + row, True)
            except Exception as error:
                print(row + ': ' + type(error).__name__ + ': ' + str(error)[:2200])
                expect('VELDO-0125 ' + row, False)
            finally:
                if fixture:
                    fixture.close()


_v125_suite()
