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
        operator = f.client('operator')
        result = operator.release(binding, reason='operator collected files and completed host cleanup',
                                  cleanup=dict(terminated=True, cleaned=True, clone_removed=True))
        sent = client.sent + operator.sent
        assert {r['command']['command']['operation'] for r in sent} == set(T.CL.OPERATIONS)
        assert f.res.worker('dispatch/test')['retired']
        for request in sent:
            assert all(request[k] == f.binding[k] for k in ('domain_uuid', 'repository_uuid', 'store_uuid'))
            assert request['workspace'] == str(f.repo)
        with sqlite3.connect(f.store) as independent:
            data = json.loads(independent.execute('SELECT data FROM entities WHERE id=?',
                                                  ('worker:dispatch/test',)).fetchone()[0])
            assert data == result['record'] and data['state'] == 'exited'
            spend = json.loads(independent.execute('SELECT data FROM entities WHERE id=?',
                ('worker-spend:dispatch/test',)).fetchone()[0])
            assert all(spend[k] == data[k] for k in ('unit', 'host', 'dispatch_id', 'invocation', 'usage'))
            assert spend['receipt']['seq'] > 0
            assert independent.execute('SELECT MAX(seq) FROM journal').fetchone()[0] == operator.watermark
        assert data['host'] == 'mac' and data['unit'] == 'unit' and data['dispatch_id'] == 'dispatch/test'
        assert all(next(c for c in data['commands'] if c['command_id'] == r['command']['command']['command_id'])['digest']
                   == T.S.digest_of(r['command']['command']) for r in sent)
        assert data['references']['proof'] == 'proof/synthetic' and data['usage']['tokens'] == 7
        invocation = f.res._records()[T.RES.entity('invocation', ['domain', data['invocation']])]
        assert invocation['dispatch'] == data['dispatch_id'] and invocation['context']['unit'] == data['unit']
        assert invocation['observed']['tokens'] == 7
        assert not T.D.completed(f.ds.record(data['dispatch_id']))
        request = T.W.SV.CC.build_request(str(f.repo), f.binding, dict(operation='inspect',
            entity_ids=['worker:dispatch/test', 'worker-spend:dispatch/test']), lambda b: f.sign('authority', b))
        visible = f.authority.judge(request, __import__('os').getuid())['result']
        assert visible['ok'] and visible['entities']['worker:dispatch/test']['data'] == data
        assert visible['entities']['worker-spend:dispatch/test']['data'] == spend

    def unavailable(f):
        local = f.base / 'mac-local'
        local.mkdir()
        before = set(local.rglob('*'))
        client = f.client(argv=[__import__('sys').executable, str(T.MODULES / 'control_relay.py'), str(local / 'absent.sock')])
        for op in T.CL.OPERATIONS:
            T.refused(lambda: client.send(op, {'dispatch_id': 'dispatch/test'}), 'AUTHORITY_UNAVAILABLE:')
        assert set(local.rglob('*')) == before, 'Mac-local fallback wrote authority state'
        assert not list(local.rglob('*.sqlite3'))

    def binding(f, fields=None):
        f.prepare(required=['ios-build'])
        f.res.configure('policy/other', 'unit', 'other', dict(capacity=2, invocations=2, wall_seconds=200), now=__import__('time').time())
        f.prepare('dispatch/other', ['ios-build'], unit='other')
        f.start()
        client = f.client()
        bound = T.launch(client)
        T.launch(client, 'dispatch/other')
        before = f.service.watermark()
        for key, value in fields or [('dispatch_id', 'dispatch/other'), ('unit', 'other'), ('host', 'linux'),
                           ('contract_digest', T.D.digest('other'))]:
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
            except Exception:
                pass
            else:
                raise AssertionError('wrong coordinate accepted: ' + field)
        client = f.client()
        original, calls = client.sign, []
        def inner_unsigned(data, namespace='veldo-command'):
            calls.append(data)
            return 'unsigned' if len(calls) == 1 else original(data, namespace)
        client.sign = inner_unsigned
        T.refused(lambda: client.claim('dispatch/test'), 'unauthorized:worker_signature')
        client = f.client()
        client.sign = lambda b, namespace='veldo-command': 'unsigned'
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

    def precall(f):
        f.prepare(required=['macos'])
        f.start()
        client = f.client()
        bound = client.claim('dispatch/test')['binding']
        before = f.service.watermark()
        T.refused(lambda: client.launch(bound, 'accept', receiver=T.process(), runtime_seconds=-1), 'invalid_input:runtime_seconds')
        assert f.service.watermark() == before and f.ds.record('dispatch/test')['state'] == 'prepared'
        f.res.configure('exhausted', 'account', 'account', dict(capacity=20, invocations=0, wall_seconds=200), now=__import__('time').time())
        T.refused(lambda: client.launch(bound, 'accept', receiver=T.process(), runtime_seconds=5), 'usage_cap:')
        assert f.service.get('dispatch/test')['state'] == 'claimed'
        assert f.ds.record('dispatch/test')['state'] == 'prepared'
        after = f.service.watermark()
        T.refused(lambda: client.launch(bound, 'accept', receiver=T.process(), runtime_seconds=5), 'usage_cap:')
        assert f.service.watermark() == after

    def confinement(f, path):
        f.start()
        ids = dict(domain_uuid='domain', repository_uuid='repo', store_uuid='store')
        cmd = dict(command_id='forbidden/' + path, nonce='forbidden/' + path, principal='mac', **ids)
        if path == 'mutate':
            cmd.update(operation='upsert_entity', expected_versions={'unowned': 0}, artifact_digests=[],
                       parameters=dict(entity_id='unowned', kind='unowned', data={}))
            invoke = lambda packet: f.service.mutate(packet, cmd, 'repo')
        elif path == 'claim':
            cmd.update(operation='claim', unit_id='unit', capabilities=[], generation=0)
            invoke = lambda packet: f.service.receiver('repo').apply(packet)
        else:
            cmd.update(operation='open', alias='W1', assignment={})
            invoke = lambda packet: f.service.inbox('repo').apply(packet)
        packet = dict(command=cmd, signature=f.sign('mac', T.S.canonical_bytes(cmd)))
        before = f.service.watermark()
        try:
            result = invoke(packet)
        except Exception as error:
            assert error.code == 'not_authorized', str(error)
        else:
            assert result.get('reason') == 'not_authorized', result
        assert before == f.service.watermark()

    def request_only(f):
        f.start()
        before = T.S.table_snapshot(f.conn)
        for operation in ('inspect', T.W.SV.OWNERSHIP_COMMIT):
            request = T.W.SV.CC.build_request(str(f.repo), f.binding, dict(operation=operation),
                                             lambda data: f.sign('mac', data))
            response = f.authority.judge(request, __import__('os').getuid())
            assert not response['accepted'] and response['reason'] == 'command_signature_invalid', response
            assert T.S.table_snapshot(f.conn) == before

    def owners(f):
        f.prepare(required=['macos'])
        for identity, kind in [('dispatch:dispatch/test', T.D.RECORD_KIND),
                               ('dispatch:injected', 'unowned'), ('mac', 'membership'),
                               ('key:injected', 'verification_key'), ('injected', 'subscription_reservation')]:
            T.refused(lambda: f.put(identity, kind, {}), 'entity_owned')

    def owner_copies(f):
        # A relay installation declares ownership from its installed engine (T.MODULES); a setup
        # rerun from a checkout writes the same kinds through the checkout's own engine/.veldo copy.
        # Same bytes are the same owner wherever they live; one edited byte is not.
        import shutil

        def engine(directory, label):
            loaded = {}
            for name in ('control_store', 'control_membership'):
                spec = importlib.util.spec_from_file_location('v125_%s_%s' % (label, name), directory / (name + '.py'))
                loaded[name] = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(loaded[name])
            return loaded['control_store'], loaded['control_membership']

        def change_roles(store, membership, conn, label):
            membership.attach(store)
            touched = ['outsider', membership.VERSIONS_ENTITY]
            versions = {i: (conn.execute('SELECT version FROM entities WHERE id=?', (i,)).fetchone() or (0,))[0]
                        for i in touched}
            return store.execute(conn, dict(command_id='rerun/' + label, principal='authority', operation='change_roles',
                nonce='rerun/' + label, artifact_digests=[], expected_versions=versions,
                parameters=dict(principal='outsider', roles=['worker_receiver'], scope=['repo'])),
                'authority', lambda b: f.sign('authority', b, 'veldo-journal'), 1)

        checkout = ROOT / 'engine/.veldo'
        installed = T.MODULES.resolve() / 'control_membership.py'
        assert checkout.resolve() != T.MODULES.resolve()
        declared = {r[1]: r for r in T.S.entity_owners(f.conn) if r[2] == 'membership'}
        assert declared['membership'][4] == str(installed), declared
        S2, CM2 = engine(checkout, 'checkout')
        rerun = S2.open_store(str(f.store))
        CM2.protect(S2, rerun)
        assert change_roles(S2, CM2, rerun, 'checkout')['replayed'] is False
        assert {r[1]: r for r in S2.entity_owners(rerun) if r[2] == 'membership'} == declared
        rerun.close()
        edited = f.base / 'edited-engine'
        shutil.copytree(checkout, edited, ignore=shutil.ignore_patterns('__pycache__'))
        source = edited / 'control_membership.py'
        source.write_bytes(source.read_bytes() + b'\n# edited copy\n')
        S3, CM3 = engine(edited, 'edited')
        foreign = S3.open_store(str(f.store))
        before = T.S.table_snapshot(f.conn)
        T.refused(lambda: CM3.protect(S3, foreign), 'ownership_conflict')
        T.refused(lambda: change_roles(S3, CM3, foreign, 'edited'), 'foreign_transition')
        assert T.S.table_snapshot(f.conn) == before
        foreign.close()

    def remote_workspace(f):
        # The workspace names the Linux authority's enrolled path. The Mac's filesystem must not
        # rewrite it (macOS resolves /tmp to /private/tmp), so a local symlink of the same name
        # elsewhere changes nothing in the signed request.
        local = f.base / 'mac-view'
        local.mkdir()
        named = f.base / 'linux-workspace'
        named.symlink_to(local)
        client = T.CL.Client(str(named), f.binding, 'mac', lambda b, namespace='veldo-command': f.sign('mac', b, namespace),
                             ['false'])
        T.refused(lambda: client.claim('dispatch/test'), 'AUTHORITY_UNAVAILABLE:')
        sent = client.sent[-1]
        assert sent['workspace'] == str(named), sent['workspace']
        assert T.W.SV.AC.ssh_keygen_verify(T.W.SV.CC.signed_bytes(sent), sent['signature'],
            T.W.SV.AC.allowed_signers_line('mac', (f.keys / 'mac.pub').read_text().strip(), 'veldo-command'),
            'mac', 'veldo-command')[0]
        T.refused(lambda: T.CL.Client('relative/workspace', f.binding, 'mac', client.sign, ['false']).claim('dispatch/test'),
                  'invalid_input:workspace')

    def refused_report(f):
        f.prepare(required=['macos'])
        f.start()
        client = f.client()
        bound = T.launch(client)
        # An already finalized report refuses a second final report inside result handling.
        f.res.report('prior-spend', 'remote/dispatch/test', 1, {'tokens': 2}, final=True,
                     outcome='completed', receipts=[T.D.digest('prior')], now=__import__('time').time())
        before = T.S.table_snapshot(f.conn)
        for _ in range(2):
            T.refused(lambda: client.result(bound, T.observation(), usage={'tokens': 7}), 'report_')
            assert T.S.table_snapshot(f.conn) == before
            assert f.ds.record('dispatch/test')['state'] == 'running'
            assert f.service.get('dispatch/test')['state'] == 'running'
            assert f.conn.execute("SELECT 1 FROM entities WHERE id='worker-spend:dispatch/test'").fetchone() is None

    def eligibility_recheck(f):
        f.prepare(required=['macos'])
        f.start()
        client = f.client()
        bound = client.claim('dispatch/test')['binding']
        f.put('admission:unit', 'admission', dict(unit='unit', state='withdrawn', scope_digest=T.D.digest('unit')))
        before = T.S.table_snapshot(f.conn)
        T.refused(lambda: client.launch(bound, 'accept', receiver=T.process(), runtime_seconds=5),
                  'stale_input:admission')
        assert T.S.table_snapshot(f.conn) == before, 'refused acceptance wrote authority state'
        assert f.ds.record('dispatch/test')['state'] == 'prepared'
        assert f.service.get('dispatch/test')['state'] == 'claimed'
        assert not any(r['type'] == 'invocation' for r in f.res._records().values())
        # Re-admitting the same scope still invalidates the preparation's ticket.
        f.put('admission:unit', 'admission', dict(unit='unit', state='accepted', scope_digest=T.D.digest('unit')))
        before = T.S.table_snapshot(f.conn)
        T.refused(lambda: client.launch(bound, 'accept', receiver=T.process(), runtime_seconds=5),
                  'stale_input:admission')
        assert T.S.table_snapshot(f.conn) == before

    def namespaces(f):
        f.prepare(required=['macos'])
        f.start()
        client = f.client()
        client.sign = lambda data, namespace='veldo-command': f.sign('mac', data)
        T.refused(lambda: client.claim('dispatch/test'), 'unauthorized:worker_signature')
        client = f.client()
        client.sign = lambda data, namespace='veldo-command': f.sign('mac', data, T.CL.COMMAND_NAMESPACE)
        T.refused(lambda: client.claim('dispatch/test'), 'command_signature_invalid')

    for row, test in {'AC1/command-families': families, 'AC1/one-authority': unavailable,
                      'AC1/authentication': auth, 'AC1/worker-mutate-only': lambda f: confinement(f, 'mutate'),
                      'AC1/worker-claim-only': lambda f: confinement(f, 'claim'),
                      'AC1/worker-inbox-only': lambda f: confinement(f, 'inbox'),
                      'AC1/worker-request-only': request_only, 'AC1/entity-owners': owners,
                      'AC1/owner-copies': owner_copies, 'AC1/remote-workspace': remote_workspace,
                      'AC1/signature-namespaces': namespaces, 'AC2/accept-eligibility-recheck': eligibility_recheck,
                      'AC3/refused-report-atomic': refused_report, 'AC2/precall-caps': precall, 'AC3/remote-result-binding': binding,
                      'AC3/dispatch-other': lambda f: binding(f, [('dispatch_id', 'dispatch/other')]),
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
