"""0125 capability set, actual supervisor launch binding and identical pack assets."""


def _v125_routing_suite():
    import copy
    import importlib.util
    import os
    import tempfile
    import types
    from pathlib import Path

    def helper(name, relative):
        spec = importlib.util.spec_from_file_location(name, ROOT / relative)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    T = helper('v125_routing_checks', 'proof/VELDO-0125/checks.py')

    def selection(base):
        f = T.Fixture(base)
        try:
            for i, (required, host) in enumerate((([], 'linux'), (['macos'], 'mac'),
                                                 (['macos', 'ios-build'], 'mac'))):
                result = f.prepare('dispatch/' + str(i), required)
                assert result['state'] == 'prepared' and result['host'] == host
                contract = result['contract']
                assert contract['input']['context']['host_route']['required'] == sorted(required)
                f.ds.refuse(contract['dispatch_id'], T.D.digest(contract), 'fixture_end', now=__import__('time').time())
        finally:
            f.close()

    def blocked(base):
        f = T.Fixture(base)
        try:
            f.profiles[1]['available'] = False
            for i, required in enumerate((['macos'], ['ios-build'], ['shell', 'ios-build'])):
                result = f.prepare('dispatch/' + str(i), required)
                assert result['state'] == 'blocked' and result['required'] == sorted(required), 'Linux fallback selected'
                assert result['reason'] == 'blocked:no_qualified_host'
                assert f.ds.record(result['dispatch_id']) is None
                import json
                stored = json.loads(f.conn.execute('SELECT data FROM entities WHERE id=?',
                    ('routing:' + result['dispatch_id'],)).fetchone()[0])
                assert stored['state'] == 'blocked' and stored['required'] == sorted(required)
        finally:
            f.close()

    def qualification(base):
        f = T.Fixture(base)
        try:
            good = copy.deepcopy(f.profiles[1])
            for i, change in enumerate(({'qualification': {}}, {'revision': 2},
                                        {'capabilities': ['macos']}, {'engines': {'codex': 'wrong'}})):
                f.profiles[1] = dict(good, **change)
                assert f.prepare('dispatch/q' + str(i), ['ios-build'])['state'] == 'blocked'
            f.profiles[1] = good
            forged = T.profile('linux', 'linux', ['ios-build', 'macos'], f.configuration)
            assert not T.R.qualified(forged), 'Linux asserted a Mac-only capability'
            f.start()
            prepared = f.prepare(required=['macos'])
            bound = f.client().claim('dispatch/test')['binding']
            f.service.profiles[1]['available'] = False
            T.refused(lambda: f.client().launch(bound, 'accept', receiver=T.process(), runtime_seconds=5), 'blocked:')
            assert f.ds.record('dispatch/test')['state'] == 'prepared'
        finally:
            f.close()

    def actual_launch(base):
        P = helper('v124_host', 'proof/VELDO-0124/checks.py')
        host, backend, request, paths = P.start(base / 'mac')
        f = T.Fixture(base / 'linux')
        worker = T.load('control_worker')
        try:
            f.profiles[1] = T.profile(backend.facts()['host'], 'darwin', ['macos', 'ios-build'],
                                       f.configuration, principal='mac')
            f.profiles[1]['runtime_profile'] = P.P.digest(host.profile)
            f.profiles[1]['qualification']['profile_digest'] = T.D.digest(T.R.definition(f.profiles[1]))
            f.prepare(required=['macos', 'ios-build'], source=request['contract']['source'])
            f.start()
            old = backend.bootstrap
            seen = []
            def bootstrap(*args):
                record = f.ds.record('dispatch/test')
                assert record['state'] == 'accepted' and f.ds.receipt('dispatch/test', 'accept')
                calls = [v for v in f.res._records().values() if v['type'] == 'invocation']
                assert len(calls) == 1 and calls[0]['state'] == 'pending'
                seen.append(record['contract']['input']['context']['host_route']['host'])
                return old(*args)
            backend.bootstrap = bootstrap
            real = worker.C.organ
            worker.C.organ = lambda name: types.SimpleNamespace(identity=lambda pid: dict(backend.process, pid=pid)) if name == 'project_runner_macos_os' else real(name)
            result = worker.run(f.client(), host, 'dispatch/test', str(paths['clone']), str(paths['scratch']),
                dict(id='account', status='active', provider='codex', profiles={backend.facts()['host']: str(paths['login'])}),
                collect=lambda run, result: ({'tokens': 3}, {'output': result['termination']['output_digest'], 'proof': 'fixture'}))
            assert seen == [backend.facts()['host']] and backend.bootstraps == 1
            assert result['record']['host'] == backend.facts()['host'] and result['record']['usage']['tokens'] == 3
            assert result['record']['state'] == 'exited' and host.status()['pending'] == 1
        finally:
            f.close()

    def sync(base):
        pack = T.load('pack')
        names = ['control_routing.py', 'control_worker.py', 'control_worker_client.py', 'control_worker_service.py']
        inventory = pack.engine_files(str(ROOT / 'engine'))
        for name in names:
            assert '.veldo/' + name in inventory
            assert (ROOT / 'engine/.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes()
        count = 0
        for wrapper in sorted((ROOT / 'packs').iterdir()):
            if not wrapper.is_dir():
                continue
            destination = base / wrapper.name
            pack.assemble_pack(str(ROOT / 'engine'), str(wrapper), str(ROOT / 'engine/AGENTS.md'), str(destination))
            for name in names:
                assert (destination / '.veldo' / name).read_bytes() == (ROOT / '.veldo' / name).read_bytes()
            count += 1
        assert count == 7

    def native_declared(base):
        import ast
        import json
        import subprocess
        import sys
        for name in ('native_checks.py', 'native_authority.py', 'native_roundtrip.py', 'ipc_checks.py'):
            ast.parse((ROOT / 'proof/VELDO-0125' / name).read_text())
        if sys.platform != 'darwin':
            result = subprocess.run([sys.executable, str(ROOT / 'proof/VELDO-0125/native_checks.py'),
                                     'run', 'codex', 'unused.json'], capture_output=True, text=True)
            assert result.returncode == 2 and json.loads(result.stdout)['status'] == 'not_run'

    for row, test in {'AC2/capability-selection': selection, 'AC2/host-routing-refusal': blocked,
                      'AC2/qualification': qualification, 'AC2/actual-worker-launch': actual_launch,
                      'AC1/template-sync': sync, 'AC1/native-declared': native_declared}.items():
        with tempfile.TemporaryDirectory(prefix='v125-routing-') as directory:
            try:
                test(Path(directory))
                expect('VELDO-0125 ' + row, True)
            except Exception as error:
                print(row + ': ' + type(error).__name__ + ': ' + str(error)[:1200])
                expect('VELDO-0125 ' + row, False)


_v125_routing_suite()
