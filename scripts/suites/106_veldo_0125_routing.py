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
            stored = __import__('json').loads(f.conn.execute('SELECT data FROM entities WHERE id=?',
                ('routing:dispatch/test',)).fetchone()[0])
            assert stored['state'] == 'blocked' and stored['reason'].startswith('blocked:')
        finally:
            f.close()

    def signing_key_read(base):
        P = helper('v125_key_host', 'proof/VELDO-0124/checks.py')
        host, backend, request, paths = P.start(base)
        signing_key = paths['authority'] / 'worker-signing'
        signing_key.write_text('synthetic signing material')
        host.profile['signing_keys'] = [str(signing_key)]
        assert '(deny file-read-data (require-any (subpath "%s")))' % signing_key in host.policy(request)

    def release_endpoint(base, f, host, backend, paths):
        import json
        import sys
        exchange = base / 'release-exchange'
        exchange.mkdir()
        endpoint = base / 'release-endpoint.json'
        endpoint.write_text(json.dumps(dict(profile=host.profile, qualification=host.qualification,
            signing_key=str(f.keys / 'mac'), principal='mac', workspace=str(f.repo), binding=f.binding,
            ssh_argv=[], runs=str(base / 'runs'), fixture_facts=backend.facts(),
            fixture_temp=str(paths['usertemp']), fixture_marker=str(base / 'release-marker.json'),
            fixture_exchange=str(exchange))))
        f.config['receiver'] = dict(remote_receivers={backend.facts()['host']: dict(argv=[sys.executable,
            str(ROOT / 'proof/VELDO-0125/receiver_fixture.py'), str(endpoint)])})
        return exchange

    def finish_release(f, host, exchange):
        import json
        import time
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            for request in exchange.glob('*.request'):
                response = request.with_suffix('.response')
                if not response.exists():
                    answer = f.authority.judge(json.loads(request.read_text()), os.getuid())
                    temporary = response.with_suffix('.tmp')
                    temporary.write_text(json.dumps(answer))
                    temporary.replace(response)
            if not any(thread.is_alive() for thread in f.service.release_deliveries.values()):
                break
            time.sleep(.01)
        assert host.status()['pending'] == 0, 'authority release leaked the Mac slot'
        assert not any(thread.is_alive() for thread in f.service.release_deliveries.values())

    def actual_launch(base, lost_result=False, default_collect=False, empty_collect=False, cleanup_failed=False,
                      unknown=False, lost_running=False, incomplete_retirement=False):
        P = helper('v124_host', 'proof/VELDO-0124/checks.py')
        host, backend, request, paths = P.start(base / 'mac', mode='killed' if unknown else 'natural')
        f = T.Fixture(base / 'linux')
        worker = T.load('control_worker')
        host.profile['signing_keys'] = [str(f.keys / 'mac')]
        host.qualification['profile_digest'] = P.P.digest(host.profile)
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
                (paths['clone'] / 'generated.bin').write_bytes(b'generated deliverable')
                (paths['scratch'] / 'proof.txt').write_text('generated proof')
                temporary = Path(host.run_paths('dispatch/test', str(paths['scratch']))['temp'])
                (temporary / 'deliverable.bin').write_bytes(b'temporary deliverable')
                (paths['clone'] / 'temporary-output').symlink_to(temporary / 'deliverable.bin')
                result = old(*args)
                (host.root / host.label('dispatch/test') / 'engine.out').write_bytes(
                    b'{"type":"turn.started"}\n{"type":"turn.completed","usage":{"input_tokens":13,"output_tokens":8}}\n')
                return result
            backend.bootstrap = bootstrap
            real = worker.C.organ
            worker.C.organ = lambda name: types.SimpleNamespace(identity=lambda pid: dict(backend.process, pid=pid)) if name == 'project_runner_macos_os' else real(name)
            client = f.client()
            client.retry_seconds = 0
            if lost_running:
                send_launch = client.launch
                def dropped_running(binding, phase, **fields):
                    if phase == 'running':
                        raise OSError('running request lost')
                    return send_launch(binding, phase, **fields)
                client.launch = dropped_running
            deliveries = []
            if lost_result and lost_result != 'stored':
                deliver = client.deliver
                def dropped(request):
                    if request['command']['command']['operation'] != 'worker_result':
                        return deliver(request)
                    import json
                    assert json.loads(client.outbox.read_text()) == request, 'result was not durable before send'
                    deliveries.append(request)
                    if len(deliveries) == 1:
                        if lost_result in ('restart', 'release', 'resumer'):
                            raise KeyboardInterrupt('receiver restarted before result delivery')
                        raise client.deliver_error('AUTHORITY_UNAVAILABLE:dropped_request')
                    answer = deliver(request)
                    if len(deliveries) == 2:
                        raise client.deliver_error('AUTHORITY_UNAVAILABLE:dropped_ack')
                    return answer
                # Match the exception class owned by this client's module.
                client.deliver_error = client.retry_result.__globals__['Refused']
                client.deliver = dropped
            if cleanup_failed:
                worker.shutil = types.SimpleNamespace(rmtree=lambda path: (_ for _ in ()).throw(OSError('busy')))
            if incomplete_retirement:
                start = host.start
                def uncertain_start(request):
                    started = start(request)
                    started.retirement = lambda: dict(terminated=False, cleaned=False, outcome_known=True)
                    return started
                host.start = uncertain_start
            def run():
                return worker.run(client, host, 'dispatch/test', str(paths['clone']), str(paths['scratch']),
                    dict(id='account', status='active', provider='codex', profiles={backend.facts()['host']: str(paths['login'])}),
                    collect=None if default_collect else (lambda run, result: ({'tokens': 3}, {} if empty_collect else
                        {'output': result['termination']['output_digest'], 'proof': 'fixture'})))
            if lost_result == 'stored':
                release = host.release_authority
                host.release_authority = lambda *args: (_ for _ in ()).throw(KeyboardInterrupt('before local retirement'))
            if lost_result in ('restart', 'stored', 'release', 'resumer'):
                try:
                    run()
                    raise AssertionError('receiver did not restart')
                except KeyboardInterrupt:
                    pass
                assert host.status()['pending'] == 1, 'Mac slot released before authority acknowledged cleanup'
                resumed = f.client()
                if lost_result == 'stored':
                    host.release_authority = release
                    assert not f.res.worker('dispatch/test')['retired'], 'Linux released before Mac retirement'
                    assert f.res.balances('account', 'account')['capacity'] == 1
                import json
                import shutil
                retained = json.loads((paths['clone'].parent / 'result-evidence.json').read_text())
                directory = base / 'restarted-receiver' / worker.C.P.digest('dispatch/test').split(':')[-1]
                directory.mkdir(parents=True)
                shutil.copyfile(client.outbox, directory / 'result-request.json')
                if lost_result == 'stored':
                    shutil.copyfile(str(client.outbox) + '.ack', directory / 'result-request.json.ack')
                shutil.copyfile(paths['clone'].parent / 'result-evidence.json', directory / 'result-evidence.json')
                original = worker.organ
                worker.organ = lambda name: types.SimpleNamespace(Client=lambda *args, **kwargs: resumed) if name == 'control_worker_client' else (
                    types.SimpleNamespace(Supervisor=lambda *args: host) if name == 'project_runner_macos' else original(name))
                config = dict(profile=host.profile, qualification=host.qualification,
                    signing_key=str(f.keys / 'mac'), workspace=str(f.repo), binding=f.binding, principal='mac',
                    ssh_argv=[], runs=str(directory.parent))
                if lost_result == 'release':
                    f.client('operator').release(retained['binding'], reason='operator inspected cleanup',
                        cleanup=dict(terminated=True, cleaned=True, clone_removed=True))
                    assert f.service.get('dispatch/test')['usage'] is None
                    f.conn.close()
                    f.conn = T.S.open_store(str(f.store))
                    f.service = T.W.Service(f.config, f.conn)
                    f.ds, f.res = f.service.records('repo')
                    f.start()
                if lost_result == 'resumer':
                    worker.resume_pending(config)
                    result = resumed.status('dispatch/test')
                    assert (directory / 'delivery-complete.json').exists()
                    count = len(resumed.sent)
                    worker.resume_pending(config)
                    assert len(resumed.sent) == count, 'completed result replayed on every startup'
                else:
                    result = worker.receive(config, dict(domain='domain', repository='repo', dispatch_id='dispatch/test',
                        action='release' if lost_result == 'release' else 'result',
                        contract_digest=retained['binding']['contract_digest']))
                assert f.service.get('dispatch/test')['usage'] == {'tokens': 3}
                calls = [v for v in f.res._records().values() if v['type'] == 'invocation']
                assert calls[0]['observed']['tokens'] == 3, 'saved usage was not reported'

            else:
                result = run()
            if lost_result is True:
                assert len(deliveries) == 3 and all(item == deliveries[0] for item in deliveries)
                assert Path(str(client.outbox) + '.ack').exists()
            assert seen == [backend.facts()['host']] and backend.bootstraps == 1
            assert result['record']['host'] == backend.facts()['host']
            if default_collect:
                import tarfile
                with tarfile.open(paths['clone'].parent / 'deliverables.tar') as archive:
                    assert archive.extractfile('clone/generated.bin').read() == b'generated deliverable'
                    assert archive.extractfile('scratch/proof.txt').read() == b'generated proof'
                    assert archive.extractfile('tmp/deliverable.bin').read() == b'temporary deliverable'
                    assert archive.getmember('clone/temporary-output').issym()
                assert result['record']['references']['output'].startswith('file:')
                if not unknown and not lost_running:
                    assert result['record']['usage'] == {'tokens': 21, 'messages': 1}
                    calls = [v for v in f.res._records().values() if v['type'] == 'invocation']
                    assert calls[0]['observed']['tokens'] == 21, 'engine usage never reached spend report'
            else:
                assert result['record']['usage']['tokens'] == 3
            if empty_collect or cleanup_failed or incomplete_retirement:
                assert paths['clone'].exists() and paths['scratch'].exists()
                assert not f.res.worker('dispatch/test')['retired']
                import shutil
                shutil.copytree(paths['clone'], base / 'operator-collected-clone')
                shutil.copytree(paths['scratch'], base / 'operator-collected-scratch')
                shutil.rmtree(paths['clone'])
                shutil.rmtree(paths['scratch'])
                # Unknown slots cannot be rebuilt with recover(); release must
                # consume the committed authority outcome directly.
                if cleanup_failed:
                    slot_path = host.root / host.label('dispatch/test') / 'slot.json'
                    P.M.write(slot_path, dict(P.M.read(slot_path), state='unknown'))
                exchange = release_endpoint(base, f, host, backend, paths)
                f.client('operator').release(result['binding'], reason='files collected and host cleaned by operator',
                    cleanup=dict(terminated=True, cleaned=True, clone_removed=True))
                assert not f.res.worker('dispatch/test')['retired'], 'Linux released before Mac confirmed'
                finish_release(f, host, exchange)
                restarted = P.M.Supervisor(host.profile, host.qualification, backend=backend)
                assert restarted.status()['pending'] == 0, 'Mac slot retirement was not durable'
                return
            assert result['record']['state'] == ('unknown' if unknown else 'exited') and host.status()['pending'] == 0
            assert f.res.worker('dispatch/test')['retired'], 'signed cleanup retained account capacity'
            assert not paths['clone'].exists() and not paths['scratch'].exists()
        finally:
            f.close()

    def production(base):
        f = T.Fixture(base)
        L = T.load('control_launch')
        L.CFG.bind = lambda conn, domain, repository, configuration: configuration
        requirements = []
        gate = types.SimpleNamespace(
            require=lambda station, unit, context: dict(decision_id='accepted', station=station, unit=unit,
                domain_uuid='domain', watermark=0, inputs=dict(required_host_capabilities=list(requirements))),
            unit_record=lambda unit: dict(project='project', required_host_capabilities=list(requirements)))
        local = []
        runner = L.Runner(gate, f.res, f.ds, lambda contract: local.append(contract),
                          account='account', worker_profiles=f.profiles, local_host='linux',
                          remote_receivers={'mac': {'argv': [__import__('sys').executable, '-c', 'import sys; sys.stdin.readline()']}})
        try:
            for i, required in enumerate((['macos'], ['ios-build'])):
                requirements[:] = required
                launch = runner.submit('unit', 'review', holder='authority', source=str(f.repo),
                    revision=T.git(f.repo, 'rev-parse', 'HEAD'), payload={}, adapter='codex',
                    configuration=f.configuration, deadline=__import__('time').time() + 60)
                assert not local, 'Mac dispatch reached Linux receiver'
                assert launch.contract['input']['context']['host_route']['host'] == 'mac'
                assert launch.owned and launch.result == 'pending' and launch.fileno() is not None
                assert runner.wait(launch, timeout=5)['state'] == 'refused'
            f.profiles[1]['available'] = False
            T.refused(lambda: runner.prepare('unit', 'review', holder='authority', source=str(f.repo),
                revision=T.git(f.repo, 'rev-parse', 'HEAD'), payload={}, adapter='codex',
                configuration=f.configuration, deadline=__import__('time').time() + 60), 'blocked:')
            decisions = [__import__('json').loads(row[0]) for row in f.conn.execute(
                "SELECT data FROM entities WHERE kind='host_routing'")]
            assert any(row['state'] == 'blocked' and row['required'] == ['ios-build'] for row in decisions)
        finally:
            f.close()

    def production_pool(base):
        f = T.Fixture(base)
        L = T.load('control_launch')
        L.CFG.bind = lambda conn, domain, repository, configuration: configuration
        gate = types.SimpleNamespace(
            require=lambda station, unit, context: dict(decision_id='accepted', station=station, unit=unit,
                domain_uuid='domain', watermark=0, inputs={'source': 'accepted'}),
            unit_record=lambda unit: dict(project='project', required_host_capabilities=['ios-build']))
        f.put('account:account', 'account', dict(id='account', provider='codex', status='active',
            profiles={'mac': '/synthetic/mac/login'}, concurrency=1, windows={}))
        pool = L.D.RES.POOL.Pool({'codex': dict(engine='codex', host='linux')})
        runner = L.Runner(gate, f.res, f.ds, lambda contract: (_ for _ in ()).throw(
            AssertionError('Mac work reached Linux')), account=pool, worker_profiles=f.profiles, local_host='linux',
            remote_receivers={'mac': {'argv': [__import__('sys').executable, '-c', 'import sys; sys.stdin.readline()']}})
        try:
            launch = runner.submit('unit', 'review', holder='authority', source=str(f.repo),
                revision=T.git(f.repo, 'rev-parse', 'HEAD'), payload={}, adapter='codex',
                configuration=f.configuration, deadline=__import__('time').time() + 60)
            assert launch.contract['input']['context']['host_route']['host'] == 'mac'
            assert launch.contract['reservation']['account'] == 'account'
            assert launch.contract['input']['decision']['inputs'] == {'source': 'accepted'}
            assert runner.wait(launch, timeout=5)['state'] == 'refused'
        finally:
            f.close()

    def factory_delivery(base):
        import json
        import select
        import sys
        import time
        P = helper('v125_delivery_host', 'proof/VELDO-0124/checks.py')
        host, backend, request, paths = P.start(base / 'mac')
        f = T.Fixture(base / 'linux')
        service_module = T.W.SV
        L = service_module.L
        L.CFG.bind = lambda conn, domain, repository, configuration: configuration
        launched, line = None, None
        try:
            host.profile['signing_keys'] = [str(f.keys / 'mac')]
            host.qualification['profile_digest'] = P.P.digest(host.profile)
            remote_host = backend.facts()['host']
            f.profiles[1] = T.profile(remote_host, 'darwin', ['macos', 'ios-build'], f.configuration, principal='mac')
            f.profiles[1]['runtime_profile'] = P.P.digest(host.profile)
            f.profiles[1]['qualification']['profile_digest'] = T.D.digest(T.R.definition(f.profiles[1]))
            seeded = f.prepare(required=['ios-build'])['contract']
            f.ds.refuse(seeded['dispatch_id'], T.D.digest(seeded), 'fixture_setup', now=time.time())
            L.Runner(None, f.res, f.ds, None, account='account')._retire(
                seeded['dispatch_id'], 'cancelled', 'never_spawned')
            account = dict(id='account', provider='codex', status='active',
                           profiles={remote_host: str(paths['login'])}, concurrency=20, windows={})
            f.put('account:account', 'account', account)
            endpoint = dict(profile=host.profile, qualification=host.qualification,
                signing_key=str(f.keys / 'mac'), principal='mac', workspace=str(f.repo), binding=f.binding,
                ssh_argv=[sys.executable, str(T.MODULES / 'control_relay.py'), f.config['socket']],
                source=str(f.repo), runs=str(paths['projects'] / 'runs'), accounts={'account': account},
                fixture_facts=backend.facts(), fixture_temp=str(paths['usertemp']),
                fixture_marker=str(base / 'contacted.json'), fixture_exchange=str(base / 'exchange'))
            (base / 'exchange').mkdir()
            endpoint_path = base / 'endpoint.json'
            endpoint_path.write_text(json.dumps(endpoint))
            receiver_path = base / 'receiver.json'
            receiver_path.write_text(json.dumps(dict(workspace=str(f.repo), store=str(f.store), host='linux',
                host_trust=f.config['host_trust'], adapters={'codex': {'engine': 'codex'}},
                remote_receivers={remote_host: {'argv': [sys.executable,
                    str(ROOT / 'proof/VELDO-0125/receiver_fixture.py'), str(endpoint_path)]}})))
            loop = service_module.FactoryLoop.__new__(service_module.FactoryLoop)
            loop.service, loop.deadlines, loop.wakes, loop.ended = f.service, {}, [], []
            line = service_module.Line(loop, 'repo', {}, str(receiver_path))
            f.start()
            report = dict(offered=[], refused=[], waiting=[])
            role = dict(identity='reviewer', adapter='codex', payload={}, configuration=f.configuration, seconds=30)
            launched = line.offer(report, 'unit', 'review', role,
                revision=T.git(f.repo, 'rev-parse', 'HEAD'), context={'reviewer': 'reviewer'})
            assert launched is not None, report
            assert launched.owned and launched.result == 'pending', 'remote dispatch not owned/pending'
            assert launched.dispatch_id in line.runner.launches, 'Line.offer dropped prepared remote work'
            assert launched.fileno() is not None, 'remote receiver was not contacted'
            assert loop.deadlines[launched.dispatch_id] == (launched.ends_at, line, launched), \
                'production offer did not register the launch deadline'
            assert report['offered'][0]['host'] == remote_host
            until = time.monotonic() + 20
            while not launched.ended and time.monotonic() < until:
                # File transport fixture: the confined suite cannot create IPC sockets.
                # Both signatures, enrollment, dispatch and reservation writes remain real.
                for message in sorted((base / 'exchange').glob('*.request')):
                    answer = f.authority.judge(json.loads(message.read_text()), os.getuid())
                    temporary = message.with_suffix('.tmp')
                    temporary.write_text(json.dumps(answer))
                    temporary.replace(message.with_suffix('.response'))
                    message.unlink()
                if select.select([launched.fileno()], [], [], .2)[0]:
                    launched.pump()
            assert launched.ended, 'remote receiver did not finish'
            terminal = line.runner.wait(launched, timeout=0)
            marker = json.loads((base / 'contacted.json').read_text())
            assert marker['bootstraps'] == 1, marker
            assert terminal['state'] == 'exited', (terminal['state'], terminal.get('reason'), marker)
            assert launched.dispatch_id not in line.runner.launches
            stored = f.service.get(launched.dispatch_id)
            assert stored['state'] == 'exited' and stored['host'] == remote_host
            assert stored['dispatch_id'] == launched.dispatch_id and stored['unit'] == 'unit'
            assert stored['charge'] == 'unknown', 'missing usage became invented spend'
        finally:
            for pending in list(line.runner.launches.values()) if line else []:
                pending._end_receiver()
            if launched and launched.child:
                launched._end_receiver()
            f.close()

    def missing_receiver(base):
        f = T.Fixture(base)
        L = T.load('control_launch')
        try:
            contract = f.prepare(required=['macos'])['contract']
            launch = L.invoke_remote(None, contract, f.ds)
            assert launch.owned and launch.result == 'refused'
            assert launch.record['state'] == 'refused'
            assert launch.record['refusal'] == 'unavailable_service:remote_receiver'
            runner = L.Runner(None, f.res, f.ds, None, account='account')
            runner.launches[launch.dispatch_id] = launch
            runner.wait(launch, timeout=0)
            slot = f.res._records()[T.RES.entity('worker', ['domain', launch.dispatch_id])]
            assert slot['retired'], 'unlaunched remote work kept its reservation'
        finally:
            f.close()

    def remote_retirement(base):
        import sys
        f = T.Fixture(base)
        L = T.load('control_launch')
        launch = None
        try:
            contract = f.prepare(required=['macos'])['contract']
            f.start()
            client = f.client()
            binding = T.launch(client)
            client.result(binding, T.observation(), usage=None, references={})
            launch = L.invoke_remote({'argv': [sys.executable, '-c', 'import sys; sys.stdin.readline()']},
                                     contract, f.ds)
            runner = L.Runner(None, f.res, f.ds, None, account='account', local_host='linux')
            runner.launches[launch.dispatch_id] = launch
            assert runner.wait(launch, timeout=5)['state'] == 'exited'
            assert not f.res.worker(launch.dispatch_id)['retired']
            # The old local observer mistakes the foreign boot/PID for a dead worker,
            # and cannot see the Mac clone. Settle accounting to expose that release.
            f.res.report('late-usage', 'remote/' + launch.dispatch_id, 1, {'tokens': 0}, final=True,
                         outcome='completed', receipts=[], now=__import__('time').time())
            T.refused(lambda: f.res.retire('unsafe-local-retire', launch.dispatch_id,
                lambda dispatch: dict(terminated=True, cleaned=True, outcome='completed'),
                now=__import__('time').time()), 'missing_evidence:remote_cleanup')
            runner.sweep()
            runner._retire(launch.dispatch_id, 'failed', 'retry')
            slot = f.res.worker(launch.dispatch_id)
            assert not slot['retired'], 'remote cleanup inferred from the Linux kernel after accounting'
            assert not slot.get('account_released'), 'remote account released without cleanup evidence'
            assert launch.dispatch_id not in runner.retirements.entries, 'remote entered Linux retirement'
            assert runner.remote_retirements[launch.dispatch_id]['open'] == ['termination', 'group', 'clone']
            assert runner.observations[-1]['refusal'] == 'missing_evidence:remote_cleanup'
        finally:
            if launch and launch.child:
                launch._end_receiver()
            f.close()

    def stalled_remote(f, state):
        import sys
        contract = f.prepare(required=['macos'])['contract']
        f.start()
        client = f.client()
        binding = None
        if state == 'accepted':
            binding = client.claim(contract['dispatch_id'])['binding']
            client.launch(binding, 'accept', receiver=T.process(), runtime_seconds=5)
        elif state in ('running', 'exited'):
            binding = T.launch(client)
        L = T.W.SV.L
        launch = L.invoke_remote({'argv': [sys.executable, '-c',
            'import sys,time; sys.stdin.readline(); time.sleep(120)']}, contract, f.ds)
        runner = L.Runner(None, f.res, f.ds, None, account='account', local_host='linux')
        runner.launches[launch.dispatch_id] = launch
        return launch, runner, client, binding

    def remote_loop(f, runner):
        # Exercise the production factory poll/timer pass with no unrelated work to offer.
        service = T.W.SV
        loop = service.FactoryLoop.__new__(service.FactoryLoop)
        loop.service = types.SimpleNamespace(domain='domain', principal='authority', _log=lambda event: None)
        loop.wakes, loop.ended, loop.timer = [], [], None
        loop.deadlines = {}
        loop.passes, loop.last, loop.counts = 0, None, {}
        loop.provision = lambda report, caller: None
        def run(report, ended):
            for launch in ended:
                record = runner.wait(launch, timeout=0)
                report['ended'].append(record)
        loop.lines = {'repo': types.SimpleNamespace(runner=runner, run=run, finish=run)}
        f.service.loop = loop
        for launch in runner.launches.values():
            loop.watch_remote(loop.lines['repo'], launch)
        return loop

    def remote_factory_deadline(base):
        import select
        import time
        for state in ('prepared', 'accepted', 'running'):
            f = T.Fixture(base / state)
            launch = None
            try:
                launch, runner, _, _ = stalled_remote(f, state)
                if state == 'prepared':
                    f.res.configure('one-slot', 'account', 'account', dict(capacity=1, invocations=20, wall_seconds=1000),
                                    now=time.time())
                    T.refused(lambda: f.res.reserve_worker('waiting-slot', 'dispatch/waiting', 'account', 'project',
                              'unit', now=time.time()), 'usage_cap:account:capacity')
                loop = remote_loop(f, runner)
                loop.wake('fixture')
                report = loop.run()
                assert not report['faults'] and not report['ended'], report
                assert launch.child.poll() is None and not select.select([launch.fileno()], [], [], 0)[0]
                assert loop.timer is None, 'remote work installed an account reset timer'
                assert loop.next_timer() == launch.contract['deadline'] + T.W.SV.L.ACCEPT_SECONDS
                # Deadline processing must touch only this launch, with no provisioning or scans.
                def unrelated(*args):
                    raise AssertionError('deadline ran a full factory pass')
                loop.provision = unrelated
                runner.sweep = unrelated
                loop.lines['repo'].run = unrelated
                later = types.SimpleNamespace(dispatch_id='later-launch', ends_at=launch.ends_at + 100,
                                              pump=unrelated)
                loop.lines['unrelated'] = types.SimpleNamespace(
                    runner=types.SimpleNamespace(launches={later.dispatch_id: later}), run=unrelated, finish=unrelated)
                loop.watch_remote(loop.lines['unrelated'], later)
                launch.clock = lambda: launch.ends_at
                loop.expire(launch.ends_at)
                report = loop.run()
                assert not report['faults'], report
                assert report['ended'], 'silent remote transport kept dispatch pending past deadline'
                assert launch.child.poll() is not None, 'deadline left transport alive'
                assert launch.dispatch_id not in runner.launches
                assert launch.dispatch_id not in loop.deadlines and loop.next_timer() == later.ends_at
                passes = loop.passes
                loop.expire(launch.ends_at + 1)
                if state == 'prepared':
                    offered = []
                    loop.provision = lambda *args: None
                    def offer_waiting(report, ended):
                        f.res.reserve_worker('waiting-slot', 'dispatch/waiting', 'account', 'project',
                                             'unit', now=time.time())
                        offered.append('waiting work')
                    loop.lines['repo'].run = offer_waiting
                    loop.lines['unrelated'].run = lambda report, ended: None
                    next_pass = loop.run()
                    assert next_pass['sources'] == ['remote_capacity_released'] and offered, \
                        'freed account did not wake waiting work'
                    passes += 1
                assert loop.run() is None and loop.passes == passes, 'deadline fired more than once'
                assert f.ds.record(launch.dispatch_id)['state'] == ('refused' if state == 'prepared' else 'unknown')
                assert f.res.worker(launch.dispatch_id)['retired'] == (state == 'prepared'), \
                    'never accepted work must release; accepted work must retain cleanup obligations'
                assert not runner.orphans and not runner.leftovers
            finally:
                if launch:
                    launch._end_receiver()
                f.close()

    def remote_authority_end(base):
        import select
        f = T.Fixture(base)
        launch = None
        try:
            launch, runner, client, binding = stalled_remote(f, 'exited')
            loop = remote_loop(f, runner)
            loop.wake('fixture')
            loop.run()
            client.result(binding, T.observation(), usage={'tokens': 0}, references={})
            assert launch.child.poll() is not None, 'signed result did not wake the launch directly'
            report = loop.run()
            assert not report['faults'] and len(report['ended']) == 1, 'authority completion waited for pipe EOF'
            assert report['ended'][0]['state'] == 'exited'
            assert launch.child.poll() is not None and launch.dispatch_id not in runner.launches
            assert loop.timer is None, 'finished transport kept factory timer active'
            assert not f.res.worker(launch.dispatch_id)['retired'], 'result alone released remote slot'
        finally:
            if launch:
                launch._end_receiver()
            f.close()

    def remote_no_polling(base):
        f = T.Fixture(base)
        launch = None
        try:
            launch, runner, _, _ = stalled_remote(f, 'running')
            loop = remote_loop(f, runner)
            loop.wake('fixture')
            loop.run()
            passes = loop.passes
            reads = []
            original = runner.dispatches.record
            def counted(dispatch):
                reads.append(dispatch)
                return original(dispatch)
            runner.dispatches.record = counted
            start = launch.clock()
            for elapsed in (0, .25, 1, 2, 10, 30):
                loop.next_timer()  # The service asks for the next wake before every wait.
                loop.expire(start + elapsed)
                loop.run()
            assert loop.passes - passes == 0, 'pending remote launch caused factory passes without an event'
            assert reads == [], 'idle serve iterations polled dispatch state'
            assert len(loop.deadlines) == 1 and loop.next_timer() == launch.ends_at
        finally:
            if launch:
                launch._end_receiver()
            f.close()

    def remote_deadline_grace(base):
        from unittest.mock import patch
        f = T.Fixture(base)
        launch = None
        try:
            launch, runner, client, binding = stalled_remote(f, 'running')
            loop = remote_loop(f, runner)
            launch.clock = lambda: launch.contract['deadline'] + T.W.SV.L.ACCEPT_SECONDS / 2
            loop.expire(launch.clock())
            assert not launch.pump(read=False), 'remote deadline omitted acceptance grace'
            assert f.ds.record(launch.dispatch_id)['state'] == 'running'
            # Advance the authority too: the signed result and its spend must actually
            # commit after the execution deadline, not merely after a launch-local clock.
            with patch.object(T.W, 'time', types.SimpleNamespace(time=launch.clock)):
                client.result(binding, T.observation(), usage={'tokens': 7}, references={})
            report = loop.run()
            assert not report['faults'] and report['ended'][0]['state'] == 'exited'
            assert f.service.get(launch.dispatch_id)['usage']['tokens'] == 7
            invocation = f.res._records()[T.RES.entity('invocation', ['domain', 'remote/' + launch.dispatch_id])]
            assert invocation['reports']['1']['final'] is True
            assert invocation['observed']['tokens'] == invocation['charge']['tokens'] == 7
            assert loop.next_timer() is None
        finally:
            if launch:
                launch._end_receiver()
            f.close()

    def remote_wait_timeout(base):
        for state in ('prepared', 'accepted', 'running'):
            f = T.Fixture(base / state)
            launch = None
            try:
                launch, runner, _, _ = stalled_remote(f, state)
                try:
                    runner.wait(launch, timeout=.02)
                except TimeoutError:
                    pass
                else:
                    raise AssertionError('connected receiver did not time out')
                assert launch.child.poll() is not None, 'wait timeout left transport alive'
                assert launch.ended and launch.lost
                assert launch.dispatch_id not in runner.launches, 'timed-out dispatch kept factory tracking'
                record = runner.wait(launch, timeout=0)
                assert record['state'] == ('refused' if state == 'prepared' else 'unknown')
                assert f.res.worker(launch.dispatch_id)['retired'] == (state == 'prepared'), \
                    'never accepted work must release; accepted work must retain cleanup obligations'
                assert not runner.orphaned(launch) and not runner.orphans
            finally:
                if launch:
                    launch._end_receiver()
                f.close()

    def cleanup_observation():
        return dict(T.observation(), cleanup=dict(terminated=True, cleaned=True, clone_removed=True))

    def remote_hold_restart(base):
        for state in ('accepted', 'running', 'accepted_started'):
            f = T.Fixture(base / state)
            launch = None
            try:
                launch, runner, _, binding = stalled_remote(f, 'accepted' if state == 'accepted_started' else state)
                dispatch = launch.dispatch_id
                held = runner.remote_retirements[dispatch]
                assert held['open'] == ['termination', 'group', 'clone']
                assert held['contract_digest'] == T.D.digest(launch.contract)
                try:
                    runner.wait(launch, timeout=.01)
                except TimeoutError:
                    pass
                assert f.ds.record(dispatch)['state'] == 'unknown'
                # Close SQLite and reconstruct the service and Runner, not just its Python hold map.
                f.conn.close()
                f.conn = T.S.open_store(str(f.store))
                f.service = T.W.Service(f.config, f.conn)
                f.ds, f.res = f.service.records('repo')
                f.start()
                restored = T.W.SV.L.Runner(None, f.res, f.ds, None, account='account', local_host='linux')
                assert restored.remote_retirements[dispatch] == held, 'restart lost remote obligations'
                assert f.res.balances('account', 'account')['capacity'] == 1
                observation = cleanup_observation() if state != 'accepted' else dict(
                    state='refused', refusal='host_start_refused', cleanup=dict(
                        terminated=True, cleaned=True, clone_removed=True))
                before = f.service.watermark()
                T.refused(lambda: f.client('outsider').result(binding, observation, usage={'tokens': 2}),
                          'unauthorized:dispatch_host')
                assert f.service.watermark() == before
                if state == 'accepted_started':
                    T.refused(lambda: f.client().result(binding, dict(observation, process=T.process(host='other')),
                              usage={'tokens': 2}), 'binding_mismatch:remote_result')
                    f.client().result(binding, T.observation(), usage={'tokens': 2})
                    assert not f.res.worker(dispatch)['retired']
                f.client().result(binding, observation, usage={'tokens': 2} if state != 'accepted' else None)
                assert not f.res.worker(dispatch)['retired']
                f.client().retired(binding)
                slot = f.res.worker(dispatch)
                assert slot['retired'] and slot['remote_hold']['open'] == []
                assert slot['retirement']['observer'] == 'mac'
                assert not restored.remote_retirements and f.res.balances('account', 'account')['capacity'] == 0
                assert f.ds.record(dispatch)['state'] == 'unknown', 'late cleanup invented recovered completion'
                if state != 'accepted':
                    assert f.service.get(dispatch)['usage'] == {'tokens': 2}, 'late final spend discarded'
            finally:
                if launch:
                    launch._end_receiver()
                f.close()

    def host_release_recovery(base):
        # A pending bootstrap has a durable local slot but cannot be recovered
        # as a Run. Drive the real receiver's release-only endpoint for each
        # authority release, including a crash before its post-commit wake.
        P = helper('v125_release_host', 'proof/VELDO-0124/checks.py')
        for kind in ('operator', 'unknown', 'refused'):
            for recovery in ('replay', 'restart'):
                directory = base / kind / recovery
                host, backend, request, paths = P.start(directory / 'mac')
                f = T.Fixture(directory / 'linux')
                try:
                    host.profile['signing_keys'] = [str(f.keys / 'mac')]
                    host.qualification['profile_digest'] = P.P.digest(host.profile)
                    f.profiles[1] = T.profile(backend.facts()['host'], 'darwin', ['macos'],
                                              f.configuration, principal='mac')
                    f.prepare(required=['macos'])
                    f.start()
                    client = f.client()
                    binding = client.claim('dispatch/test')['binding']
                    client.launch(binding, 'accept', receiver=backend.process, runtime_seconds=5)
                    slot = host.root / host.label('dispatch/test')
                    slot.mkdir()
                    P.M.write(slot / 'slot.json', dict(dispatch_id='dispatch/test', state='unknown'))
                    P.M.write(slot / 'request.json', dict(dispatch_id='dispatch/test',
                                                        contract_digest=binding['contract_digest']))
                    assert host.status()['pending'] == 1
                    exchange = release_endpoint(directory, f, host, backend, paths)
                    # Simulate death immediately after the atomic release commit,
                    # before notification or scheduling, rather than a lost input.
                    notify = f.service.notify_release
                    f.service.notify_release = lambda *args: (_ for _ in ()).throw(KeyboardInterrupt())
                    cleanup = dict(terminated=True, cleaned=True, clone_removed=True)
                    sender = f.client('operator') if kind == 'operator' else client
                    try:
                        if kind == 'operator':
                            sender.release(binding, reason='operator verified cleanup', cleanup=cleanup)
                        else:
                            sender.result(binding, dict(state=kind, cleanup=cleanup, refusal='bootstrap_refused'))
                        raise AssertionError('post-commit crash did not occur')
                    except KeyboardInterrupt:
                        pass
                    assert not f.res.worker('dispatch/test')['retired'] and host.status()['pending'] == 1
                    if recovery == 'restart':
                        f.service = T.W.Service(f.config, f.conn)
                        f.ds, f.res = f.service.records('repo')
                        f.start()
                    else:
                        f.service.notify_release = notify
                        wakes = []
                        f.service.loop = types.SimpleNamespace(remote_result=lambda *args: None,
                            wake=lambda *args: wakes.append(args))
                        answer = sender.deliver(sender.sent[-1])
                        assert answer['replayed'] and answer['host_released']
                        assert not wakes, 'capacity wake preceded Mac retirement'
                    finish_release(f, host, exchange)
                    assert f.res.worker('dispatch/test')['retired']
                    assert f.service.get('dispatch/test')['release_state'] == 'confirmed'
                    restarted = P.M.Supervisor(host.profile, host.qualification, backend=backend)
                    assert restarted.status()['pending'] == 0
                    stale = P.M.Run(host, slot, 'dispatch/test', host.label('dispatch/test'))
                    stale.save('unknown')
                    assert restarted.status()['pending'] == 0, 'late observer resurrected released slot'
                    # An arbitrary input cannot retire a different contract's slot.
                    answer = client.status('dispatch/test')
                    T.refused(lambda: restarted.release_authority('dispatch/test', 'sha256:wrong', answer),
                              'binding_mismatch:authority_release')
                    assert backend.bootstraps == 0, 'release endpoint re-executed work'
                    queries = []
                    f.conn.set_trace_callback(queries.append)
                    f.service = T.W.Service(f.config, f.conn)
                    f.conn.set_trace_callback(None)
                    assert not f.service.release_sent, 'restart sent confirmed release again'
                    assert not any('reservation_record' in query for query in queries), 'startup rescanned reservations'
                    reads = [query for query in queries if 'SELECT data FROM entities' in query]
                    assert all('worker_release_pending' in query for query in reads), 'startup rescanned worker history'
                    plan = f.conn.execute("EXPLAIN QUERY PLAN SELECT data FROM entities INDEXED BY worker_release_pending "
                        "WHERE kind='worker_observation' AND json_extract(data, '$.release_state')='pending'").fetchall()
                    assert any('worker_release_pending' in str(row) for row in plan)

                finally:
                    f.close()

    def release_queue_once(base):
        import threading
        f = T.Fixture(base)
        original = T.W.subprocess
        entered, unblock = threading.Event(), threading.Event()
        calls = []
        def delivery(argv, **kwargs):
            calls.append(kwargs['input'])
            entered.set()
            assert unblock.wait(5)
            return types.SimpleNamespace(returncode=1)
        T.W.subprocess = types.SimpleNamespace(run=delivery, TimeoutExpired=original.TimeoutExpired,
                                               DEVNULL=original.DEVNULL)
        try:
            f.config['receiver'] = dict(remote_receivers={'mac': dict(argv=['fixture'])})
            bindings = [dict(dispatch_id='dispatch/' + str(i), contract_digest='sha256:fixture', host='mac')
                        for i in range(20)]
            for binding in bindings:
                f.service.notify_release('repo', binding)
            assert entered.wait(5)
            assert len(calls) == 1 and len(f.service.release_deliveries) == 1, 'release connection storm'
            sender = next(iter(f.service.release_deliveries.values()))
            unblock.set()
            sender.join(5)
            assert not sender.is_alive() and len(calls) == 20
            for binding in bindings:
                f.service.notify_release('repo', binding)
            assert len(calls) == 20 and not f.service.release_deliveries, 'release wake sent more than once'
        finally:
            unblock.set()
            T.W.subprocess = original
            f.close()

    def release_before_start(base):
        P = helper('v125_early_release', 'proof/VELDO-0124/checks.py')
        host, backend, request, paths = P.start(base)
        dispatch = request['contract']['dispatch_id']
        outcome = dict(ok=True, host_released=True, binding=dict(dispatch_id=dispatch,
            contract_digest=request['contract_digest'], host=backend.facts()['host']))
        host.release_authority(dispatch, request['contract_digest'], outcome)
        restarted = P.M.Supervisor(host.profile, host.qualification, backend=backend)
        slot = P.M.read(host.root / host.label(dispatch) / 'slot.json')
        assert slot['state'] == 'retired' and slot['contract_digest'] == request['contract_digest']
        T.refused(lambda: restarted.start(request), 'stale_version:dispatch_already_attempted')
        assert backend.bootstraps == 0 and restarted.status()['pending'] == 0

    def delivery_agent(base):
        import json
        import plistlib
        worker = T.load('control_worker')
        config = dict(profile=dict(home=str(base)), runs=str(base / 'runs'))
        path = base / 'receiver.json'
        path.write_text(json.dumps(config))
        calls = []
        def launchctl(argv, **kwargs):
            calls.append(argv)
            return types.SimpleNamespace(returncode=1 if argv[1] == 'print' else 0)
        worker.subprocess = types.SimpleNamespace(run=launchctl)
        worker.install_resumer(path, config)
        jobs = list((base / 'Library' / 'LaunchAgents').glob('*.plist'))
        assert len(jobs) == 1
        job = plistlib.loads(jobs[0].read_bytes())
        assert job['RunAtLoad'] and job['KeepAlive'] and job['ThrottleInterval'] >= 30
        assert job['ProgramArguments'][-2:] == [str(path), '--resume']
        assert calls[-1][1] == 'bootstrap'
        invoked = []
        worker.resume_pending = lambda config: invoked.append(config)
        worker.time = types.SimpleNamespace(sleep=lambda seconds: (_ for _ in ()).throw(KeyboardInterrupt()))
        try:
            worker.main(str(path), resume=True)
        except KeyboardInterrupt:
            pass
        assert invoked == [config], 'installed startup entrypoint did not drain outbox'

    def retry_backoff(base):
        client = T.CL.Client('/workspace', {}, 'mac', lambda *args: '', [])
        client.outbox = base / 'outbox.json'
        T.CL.durable_json(client.outbox, {'same': 'command'})
        sent, sleeps = [], []
        def unavailable(request):
            sent.append(request)
            if len(sent) <= 25:
                raise T.CL.Refused('AUTHORITY_UNAVAILABLE:offline')
            return {'ok': True}
        client.deliver = unavailable
        old = T.CL.time
        T.CL.time = types.SimpleNamespace(sleep=sleeps.append)
        try:
            assert client.retry_result() == {'ok': True}
        finally:
            T.CL.time = old
        assert len(sent) == 26 and len(sleeps) == 25, 'delivery stopped during a long authority outage'
        assert all(request == sent[0] for request in sent)
        assert all(min(300, 2 ** i) / 2 <= value <= min(300, 2 ** i) for i, value in enumerate(sleeps))
        assert sleeps[-1] > 1 and client.outbox.exists()
        assert Path(str(client.outbox) + '.ack').exists()

    def late_usage(base):
        for release in ('operator', 'unknown'):
            for initial in ('accepted', 'running', 'exited'):
                if release == 'unknown' and initial == 'exited':
                    continue  # An unknown observation cannot overwrite a signed exit.
                f = T.Fixture(base / release / initial)
                try:
                    f.prepare(required=['macos'])
                    f.start()
                    client = f.client()
                    binding = client.claim('dispatch/test')['binding']
                    client.launch(binding, 'accept', receiver=T.process(), runtime_seconds=5)
                    if initial in ('running', 'exited'):
                        client.launch(binding, 'running', process=T.process())
                    if initial == 'exited':
                        client.result(binding, T.observation())  # Exit known; usage not yet collected.
                    cleanup = dict(terminated=True, cleaned=True, clone_removed=True)
                    if release == 'operator':
                        f.client('operator').release(binding, reason='inspected cleanup', cleanup=cleanup)
                    else:
                        client.result(binding, dict(state='unknown', cleanup=cleanup))
                    usage = dict(tokens=7, messages=1, invocations=1, wall_seconds=2)
                    result = client.result(binding, T.observation(), usage=usage)
                    calls = [v for v in f.res._records().values() if v['type'] == 'invocation']
                    assert len(calls) == 1 and calls[0]['observed'] == usage, 'late usage lost after release'
                    assert calls[0]['charge'] == usage and calls[0]['sequence'] == 2
                    assert result['record']['usage'] == usage and result['record']['charge'] == 'reported'
                    receipt = result['record']['spend_receipt']
                    client.result(binding, T.observation(), usage=usage)
                    assert f.service.get('dispatch/test')['spend_receipt'] == receipt
                    call = [v for v in f.res._records().values() if v['type'] == 'invocation'][0]
                    assert call == calls[0], 'duplicate delivery charged again'
                    assert f.res.balances('account', 'account')['tokens'] == 7
                finally:
                    f.close()

    def unknown_cleanup(base):
        for initial in ('accepted', 'running'):
            f = T.Fixture(base / initial)
            try:
                f.res.configure('one-slot', 'account', 'account', dict(capacity=1, invocations=20, wall_seconds=1000),
                                now=__import__('time').time())
                f.prepare(required=['macos'])
                f.start()
                client = f.client()
                binding = client.claim('dispatch/test')['binding']
                client.launch(binding, 'accept', receiver=T.process(), runtime_seconds=5)
                if initial == 'running':
                    client.launch(binding, 'running', process=T.process())
                    client.result(binding, dict(state='unknown', process=T.process()))
                # Neither process nor termination can be recovered. Cleanup itself is the evidence.
                observation = dict(state='unknown', cleanup=dict(terminated=True, cleaned=True, clone_removed=True))
                client.result(binding, observation)
                assert not f.res.worker('dispatch/test')['retired']
                client.retired(binding)
                assert f.res.worker('dispatch/test')['retired']
                assert f.res.balances('account', 'account')['capacity'] == 0
                assert f.ds.record('dispatch/test')['state'] == 'unknown'
                assert f.service.get('dispatch/test')['observation'] == observation
                assert f.service.get('dispatch/test')['charge'] == 'unknown'
                f.conn.close()
                f.conn = T.S.open_store(str(f.store))
                f.service = T.W.Service(f.config, f.conn)
                f.ds, f.res = f.service.records('repo')
                assert f.res.worker('dispatch/test')['remote_hold']['open'] == []
                assert f.service.get('dispatch/test')['observation'] == observation
                f.res.reserve_worker('next-slot', 'dispatch/next', 'account', 'project', 'unit',
                                     now=__import__('time').time())
            finally:
                f.close()

    def operator_release(base):
        for initial in ('accepted', 'running', 'unknown', 'exited'):
            f = T.Fixture(base / initial)
            try:
                f.prepare(required=['macos'])
                f.start()
                client = f.client()
                binding = client.claim('dispatch/test')['binding']
                client.launch(binding, 'accept', receiver=T.process(), runtime_seconds=5)
                if initial != 'accepted':
                    client.launch(binding, 'running', process=T.process())
                if initial in ('exited', 'unknown'):
                    client.result(binding, T.observation() if initial == 'exited' else
                                  dict(state='unknown', process=T.process()))
                cleanup = dict(terminated=True, cleaned=True, clone_removed=True)
                before = f.service.watermark()
                T.refused(lambda: client.release(binding, reason='not an operator', cleanup=cleanup), 'command_signature_invalid')
                operator = f.client('operator')
                T.refused(lambda: operator.release(dict(binding, host='wrong'), reason='wrong binding', cleanup=cleanup),
                          'binding_mismatch:remote_release')
                T.refused(lambda: operator.release(binding, reason='incomplete', cleanup=dict(cleanup, cleaned=False)),
                          'missing_evidence:remote_cleanup')
                assert f.service.watermark() == before
                wakes = []
                f.service.loop = types.SimpleNamespace(remote_result=lambda *args: None,
                    wake=lambda *args: wakes.append(args))
                result = operator.release(binding, reason='host inspected, files collected, process and clone removed',
                                          cleanup=cleanup)
                assert not result['released'] and not f.res.worker('dispatch/test')['retired']
                assert not [wake for wake in wakes if wake[0] == 'remote_capacity_released']
                result = client.retired(binding)
                assert result['released'] and f.res.worker('dispatch/test')['retired']
                assert f.res.worker('dispatch/test')['retirement']['observer'] == 'operator'
                assert f.service.get('dispatch/test')['release']['reason'].startswith('host inspected')
                assert f.ds.record('dispatch/test')['state'] == ('exited' if initial == 'exited' else 'unknown')
                again = operator.release(binding, reason='duplicate attestation', cleanup=cleanup)
                assert not again['released']
                assert f.res.balances('account', 'account')['capacity'] == 0
                assert [wake for wake in wakes if wake[0] == 'remote_capacity_released'] == [
                    ('remote_capacity_released', 'dispatch/test')], 'late cleanup did not wake idle work once'
            finally:
                f.close()

    def remote_signed_cleanup(base):
        f = T.Fixture(base)
        try:
            f.res.configure('one-slot', 'account', 'account', dict(capacity=1, invocations=20, wall_seconds=1000),
                            now=__import__('time').time())
            f.start()
            client = f.client()
            for index in range(3):
                dispatch = 'dispatch/reuse/' + str(index)
                f.prepare(dispatch, required=['macos'])
                binding = T.launch(client, dispatch)
                observation = T.observation()
                client.result(binding, observation, usage={'tokens': 3, 'messages': 1, 'invocations': 1, 'wall_seconds': 1})
                assert not f.res.worker(dispatch)['retired'], 'unsigned cleanup inferred from a signed exit'
                before = f.service.watermark()
                T.refused(lambda: client.result(binding, dict(observation, cleanup=dict(
                    terminated=True, cleaned=False, clone_removed=True)), usage={'tokens': 3, 'messages': 1, 'invocations': 1, 'wall_seconds': 1}),
                    'invalid_input:remote_cleanup')
                assert f.service.watermark() == before
                client.result(binding, cleanup_observation(), usage={'tokens': 3, 'messages': 1, 'invocations': 1, 'wall_seconds': 1})
                assert not f.res.worker(dispatch)['retired']
                client.retired(binding)
                slot = f.res.worker(dispatch)
                assert slot['retired'] and slot['remote_hold']['open'] == []
                assert f.res.balances('account', 'account')['capacity'] == 0
                identity = T.RES.entity('worker', ['domain', dispatch])
                version = f.conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()[0]
                client.result(binding, cleanup_observation(), usage={'tokens': 3, 'messages': 1, 'invocations': 1, 'wall_seconds': 1})
                assert f.conn.execute('SELECT version FROM entities WHERE id=?', (identity,)).fetchone()[0] == version
                assert f.res.balances('account', 'account')['capacity'] == 0
        finally:
            f.close()

    def remote_signed_refusal(base):
        f = T.Fixture(base)
        try:
            f.prepare(required=['macos'])
            f.start()
            client = f.client()
            binding = client.claim('dispatch/test')['binding']
            client.result(binding, dict(state='refused', refusal='host_preflight_refused'))
            assert f.ds.record('dispatch/test')['state'] == 'refused'
            assert not f.res.worker('dispatch/test')['retired']
            client.retired(binding)
            assert f.res.worker('dispatch/test')['retired']
            assert f.res.balances('account', 'account')['capacity'] == 0
            T.refused(lambda: client.launch(binding, 'accept', receiver=T.process(), runtime_seconds=5),
                      'stale_version:launch_phase')
        finally:
            f.close()

    def transport_is_not_evidence(base):
        import sys
        for state in ('prepared', 'accepted', 'running'):
            f = T.Fixture(base / state)
            L = T.load('control_launch')
            launch = None
            try:
                contract = f.prepare(required=['macos'])['contract']
                f.start()
                client = f.client()
                if state == 'accepted':
                    binding = client.claim('dispatch/test')['binding']
                    client.launch(binding, 'accept', receiver=T.process(), runtime_seconds=5)
                elif state == 'running':
                    T.launch(client)
                launch = L.invoke_remote({'argv': [sys.executable, '-c',
                    'import sys,json; sys.stdin.readline(); print(json.dumps(dict(event="exited",returncode=0)))']},
                    contract, f.ds)
                assert launch.owned and launch.result == 'pending'
                record = launch.wait(timeout=5)
                assert record['state'] == ('refused' if state == 'prepared' else 'unknown'), record['state']
                assert not T.D.completed(record), 'transport stdout or exit invented completion'
            finally:
                if launch and launch.child:
                    launch._end_receiver()
                f.close()

    def installed_routing(base):
        target = base / 'adopter'
        T.load('init_scaffold').scaffold(target, templates=ROOT / 'engine')
        installed = target / '.veldo/control_routing.py'
        assert installed.is_file(), 'scaffold omitted the production routing dependency'
        assert installed.read_bytes() == (ROOT / 'engine/.veldo/control_routing.py').read_bytes()
        spec = importlib.util.spec_from_file_location('v125_installed_launch', target / '.veldo/control_launch.py')
        launch = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launch)
        assert callable(launch._organ('control_routing').prepare)

    def sync(base):
        pack = T.load('pack')
        names = ['control_routing.py', 'control_worker.py', 'control_worker_client.py', 'control_worker_service.py',
                 'control_service.py', 'project_runner_macos.py']
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

    for row, test in {'AC1/installed-routing': installed_routing,
                      'AC1/worker-signing-key-read': signing_key_read,
                      'AC2/capability-selection': selection, 'AC2/host-routing-refusal': blocked,
                      'AC2/qualification': qualification, 'AC2/factory-remote-delivery': factory_delivery,
                      'AC2/missing-remote-receiver': missing_receiver,
                      'AC3/remote-cleanup-held': remote_retirement,
                      'AC3/remote-hold-restart': remote_hold_restart,
                      'AC3/remote-result-transport-failure': lambda base: actual_launch(base, lost_result=True),
                      'AC3/release-flushes-saved-usage': lambda base: actual_launch(base, lost_result='release'),
                      'AC3/startup-resumes-outbox': lambda base: actual_launch(base, lost_result='resumer'),
                      'AC3/delivery-launch-agent': delivery_agent,
                      'AC3/release-wakes-bounded-once': release_queue_once,
                      'AC3/release-before-start': release_before_start,
                      'AC3/remote-result-restart': lambda base: actual_launch(base, lost_result='restart'),
                      'AC3/stored-release-restart': lambda base: actual_launch(base, lost_result='stored'),
                      'AC3/default-collector-retains-files': lambda base: actual_launch(base, default_collect=True),
                      'AC3/unknown-host-cleanup': lambda base: actual_launch(base, default_collect=True, unknown=True),
                      'AC3/running-notification-lost': lambda base: actual_launch(base, default_collect=True, lost_running=True),
                      'AC3/empty-collector-preserves-files': lambda base: actual_launch(base, empty_collect=True),
                      'AC3/cleanup-failure-release': lambda base: actual_launch(base, cleanup_failed=True),
                      'AC3/incomplete-retirement-release': lambda base: actual_launch(base, incomplete_retirement=True),
                      'AC3/unknown-cleanup-releases': unknown_cleanup,
                      'AC3/operator-release': operator_release,
                      'AC3/late-usage-amends-spend': late_usage,
                      'AC3/result-retry-backoff': retry_backoff,
                      'AC3/host-release-replay-and-restart': host_release_recovery,
                      'AC3/remote-signed-cleanup': remote_signed_cleanup,
                      'AC3/remote-signed-refusal': remote_signed_refusal,
                      'AC2/remote-factory-deadline': remote_factory_deadline,
                      'AC2/remote-no-polling': remote_no_polling,
                      'AC3/remote-deadline-grace': remote_deadline_grace,
                      'AC3/remote-authority-end': remote_authority_end,
                      'AC2/remote-wait-timeout': remote_wait_timeout,
                      'AC3/transport-is-not-evidence': transport_is_not_evidence, 'AC2/production-routing': production, 'AC2/production-account-host': production_pool, 'AC2/actual-worker-launch': actual_launch,
                      'AC1/template-sync': sync, 'AC1/native-declared': native_declared}.items():
        with tempfile.TemporaryDirectory(prefix='v125-routing-') as directory:
            try:
                test(Path(directory))
                expect('VELDO-0125 ' + row, True)
            except Exception as error:
                __import__('traceback').print_exc()
                print(row + ': ' + type(error).__name__ + ': ' + str(error)[:1200])
                expect('VELDO-0125 ' + row, False)


_v125_routing_suite()
