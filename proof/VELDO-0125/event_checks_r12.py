"""Round 9 event-delivery regressions. Real signed authority, synthetic Mac backend."""
import fcntl
import json
from pathlib import Path
import threading
import time
import types
from unittest.mock import patch


def cases(T, helper, release_endpoint, finish_release):
    def indexed_idle(base):
        worker = T.load('control_worker')
        config = dict(runs=str(base / 'runs'), binding=dict(domain_uuid='domain', repository_uuid='repo'))
        runs = Path(config['runs'])
        runs.mkdir()
        for i in range(500):
            directory = runs / str(i)
            directory.mkdir()
            (directory / 'delivery-complete.json').write_text('{}')
        path = base / 'config.json'
        config.update(profile={}, qualification={})
        worker.organ = lambda name: types.SimpleNamespace(Supervisor=lambda *args: None)
        path.write_text(json.dumps(config))
        request = dict(action='resume', domain='domain', repository='repo',
                       dispatch_id='one-pending', contract_digest='sha256:one')
        worker.OUT.enqueue(config, request, worker.CL.durable_json)
        calls = []
        worker.receive_locked = lambda config, request: calls.append(request) or {'host_released': False}
        original_scandir = __import__('os').scandir
        def scandir(path):
            assert Path(path) != runs, 'startup enumerated historical run directories'
            return original_scandir(path)
        original_listdir = __import__('os').listdir
        def listdir(path):
            assert Path(path) != runs, 'startup enumerated historical run directories'
            return original_listdir(path)
        with patch('os.scandir', scandir), patch('os.listdir', listdir), patch.object(worker, 'sleep',
                side_effect=AssertionError('idle timer')):
            worker.main(str(path), resume=True)
            worker.main(str(path), resume=True)
        assert len(calls) == 1 and not worker.OUT.entries(config), 'acknowledged work stayed indexed'

    def dispatch_isolation(base):
        worker = T.load('control_worker')
        config = dict(runs=str(base))
        visited = []
        def deliver(config, request):
            dispatch = request['dispatch_id']
            visited.append(dispatch)
            if dispatch == 'bad':
                raise worker.CL.Refused('binding_mismatch:operator_required')
            if dispatch == 'offline' and visited.count(dispatch) < 3:
                raise worker.CL.Refused('AUTHORITY_UNAVAILABLE:offline')
            return {'host_released': False}
        worker.receive_locked = deliver
        for dispatch in ('bad', 'good', 'offline'):
            worker.OUT.enqueue(config, dict(action='resume', dispatch_id=dispatch), worker.CL.durable_json)
        now = [1000]
        clock = types.SimpleNamespace(time=lambda: now[0])
        with patch.object(worker, 'time', clock), patch.object(worker.OUT, 'time', clock):
            for attempt in range(3):
                worker.resume_pending(config)
                pending = worker.OUT.entries(config)
                if attempt < 2:
                    assert len(pending) == 1 and pending[0]['request']['dispatch_id'] == 'offline'
                    assert pending[0]['due'] - now[0] == 2 ** attempt
                now[0] += 300
        assert visited.count('bad') == visited.count('good') == 1 and visited.count('offline') == 3
        assert not worker.OUT.entries(config)
        parked = json.loads((base / '.parked' / worker.OUT.key('bad')).read_text())
        assert parked['reason'] == 'binding_mismatch:operator_required'
        # An explicit operator event reopens a parked delivery once configuration is repaired.
        worker.receive_locked = lambda *args: {'host_released': True}
        worker.receive(config, dict(action='release', dispatch_id='bad'))
        assert not worker.OUT.entries(config)

    def unknown_usage(base):
        for initial in ('accepted', 'running'):
            f = T.Fixture(base / initial)
            try:
                f.prepare(required=['macos'])
                f.start()
                client = f.client()
                binding = client.claim('dispatch/test')['binding']
                client.launch(binding, 'accept', receiver=T.process(), runtime_seconds=5)
                if initial == 'running':
                    client.launch(binding, 'running', process=T.process())
                observation = dict(state='unknown', process=T.process())
                if initial == 'accepted':
                    observation['cleanup'] = dict(terminated=True, cleaned=True, clone_removed=True)
                answer = client.result(binding, observation, usage={'tokens': 21})
                assert answer['record']['usage'] == {'tokens': 21} and answer['record']['charge'] == 'reported'
                observation['cleanup'] = dict(terminated=True, cleaned=True, clone_removed=True)
                client.result(binding, observation, usage={'tokens': 21})
                client.retired(binding)
                client.result(binding, observation)  # A later cleanup-only command cannot erase measurement.
                invocation = f.res._records()[T.RES.entity('invocation', ['domain', answer['record']['invocation']])]
                assert invocation['observed']['tokens'] == invocation['charge']['tokens'] == 21
                assert invocation['sequence'] == 1 and len(invocation['reports']) == 1, 'usage charged twice'
                assert f.service.get('dispatch/test')['usage'] == {'tokens': 21}
                assert f.res.worker('dispatch/test')['retired']
            finally:
                f.close()

    def crashed_usage(base):
        P = helper('v125_event_host', 'proof/VELDO-0124/checks.py')
        host, backend, request, paths = P.start(base / 'mac')
        f = T.Fixture(base / 'linux')
        worker = T.load('control_worker')
        try:
            host.profile['signing_keys'] = [str(f.keys / 'mac')]
            host.qualification['profile_digest'] = P.P.digest(host.profile)
            f.profiles[1] = T.profile(backend.facts()['host'], 'darwin', ['macos'], f.configuration, principal='mac')
            f.profiles[1]['runtime_profile'] = P.P.digest(host.profile)
            f.profiles[1]['qualification']['profile_digest'] = T.D.digest(T.R.definition(f.profiles[1]))
            f.prepare(required=['macos'], source=request['contract']['source'])
            f.start()
            client = f.client()
            original = worker.C.organ
            worker.C.organ = lambda name: types.SimpleNamespace(identity=lambda pid: dict(backend.process, pid=pid)) \
                if name == 'project_runner_macos_os' else original(name)
            def crash(started, observation):
                (started.directory / 'engine.out').write_text(
                    '{"type":"turn.started"}\n{"type":"turn.completed","usage":{"input_tokens":13,"output_tokens":8}}\n')
                raise KeyboardInterrupt('crash before evidence')
            try:
                worker.run(client, host, 'dispatch/test', str(paths['clone']), str(paths['scratch']),
                    dict(id='account', provider='codex', status='active',
                         profiles={backend.facts()['host']: str(paths['login'])}), collect=crash)
            except KeyboardInterrupt:
                pass
            assert host.status()['pending'] == 1 and not (paths['clone'].parent / 'result-evidence.json').exists()
            binding = client.status('dispatch/test')['binding']
            f.client('operator').release(binding, reason='operator verified stopped engine and cleanup',
                cleanup=dict(terminated=True, cleaned=True, clone_removed=True))
            runs = base / 'runs'
            directory = runs / worker.C.P.digest('dispatch/test').split(':')[-1]
            directory.mkdir(parents=True)
            (directory / 'run-context.json').write_bytes((paths['clone'].parent / 'run-context.json').read_bytes())
            original = worker.organ
            worker.organ = lambda name: types.SimpleNamespace(Client=lambda *a, **k: client) \
                if name == 'control_worker_client' else types.SimpleNamespace(Supervisor=lambda *a, **kw: host) \
                if name == 'project_runner_macos' else original(name)
            config = dict(runs=str(runs), profile=host.profile, qualification=host.qualification,
                binding=f.binding, workspace=str(f.repo), signing_key=str(f.keys / 'mac'), principal='mac', ssh_argv=[])
            wake = dict(action='release', domain='domain', repository='repo',
                        dispatch_id='dispatch/test', contract_digest=binding['contract_digest'])
            retired = client.retired
            def confirm(binding):
                assert f.service.get('dispatch/test')['usage']['tokens'] == 21, 'release preceded retained output flush'
                assert host.status()['pending'] == 0
                return retired(binding)
            client.retired = confirm
            worker.receive(config, wake)
            worker.receive(config, wake)
            record = f.service.get('dispatch/test')
            invocation = f.res._records()[T.RES.entity('invocation', ['domain', record['invocation']])]
            assert invocation['observed']['tokens'] == invocation['charge']['tokens'] == 21
            assert invocation['sequence'] == 2 and len(invocation['reports']) == 2  # placeholder + measured revision
            assert host.status()['pending'] == 0 and f.res.worker('dispatch/test')['retired']
            assert not worker.OUT.entries(config) and backend.bootstraps == 1
        finally:
            f.close()

    def failed_release_wakes(base):
        P = helper('v125_wake_host', 'proof/VELDO-0124/checks.py')
        host, backend, request, paths = P.start(base / 'mac')
        f = T.Fixture(base / 'linux')
        original = T.W.subprocess
        calls = []
        def transport(argv, **kwargs):
            calls.append(time.monotonic())
            if len(calls) == 1:
                return types.SimpleNamespace(returncode=255)
            if len(calls) == 2:
                raise original.TimeoutExpired(argv, 60)
            return original.run(argv, **kwargs)
        try:
            host.profile['signing_keys'] = [str(f.keys / 'mac')]
            f.profiles[1] = T.profile(backend.facts()['host'], 'darwin', ['macos'], f.configuration, principal='mac')
            f.prepare(required=['macos'])
            f.start()
            client = f.client()
            binding = client.claim('dispatch/test')['binding']
            client.launch(binding, 'accept', receiver=backend.process, runtime_seconds=5)
            slot = host.root / host.label('dispatch/test')
            slot.mkdir()
            P.M.write(slot / 'slot.json', dict(dispatch_id='dispatch/test', state='unknown'))
            P.M.write(slot / 'request.json', dict(dispatch_id='dispatch/test', contract_digest=binding['contract_digest']))
            exchange = release_endpoint(base, f, host, backend, paths)
            f.service.release_retry_seconds = .02
            f.service.release_retry_max_seconds = .04
            with patch.object(T.W, 'subprocess', types.SimpleNamespace(run=transport,
                    TimeoutExpired=original.TimeoutExpired, DEVNULL=original.DEVNULL)):
                f.client('operator').release(binding, reason='release after receiver crash',
                    cleanup=dict(terminated=True, cleaned=True, clone_removed=True))
                f.service.notify_release('repo', binding)  # replay cannot suppress the scheduled retry
                finish_release(f, host, exchange)
            assert len(calls) == 3, 'failed/timeout release wake was marked sent'
            assert calls[1] - calls[0] >= .018 and calls[2] - calls[1] >= .038
            assert host.status()['pending'] == 0 and f.res.worker('dispatch/test')['retired']
            assert not f.service.release_queue
        finally:
            f.close()

    def busy_release(base):
        worker = T.load('control_worker')
        config = dict(runs=str(base))
        request = dict(action='release', dispatch_id='busy', contract_digest='sha256:busy')
        locks = base / '.locks'
        locks.mkdir()
        path = locks / worker.C.P.digest('busy').split(':')[-1]
        with path.open('a') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            started = time.monotonic()
            assert worker.receive(config, request) is None
            assert time.monotonic() - started < 1, 'release waited behind the engine lock'
            assert worker.OUT.entries(config)[0]['request'] == request
        worker.receive_locked = lambda *args: {'host_released': True}
        with patch.object(worker, 'time', types.SimpleNamespace(time=lambda: time.time() + 301)):
            worker.resume_pending(config)
        assert not worker.OUT.entries(config), 'busy release was never drained'

    return {'AC3/event-index-idle-and-history': indexed_idle,
            'AC3/event-dispatch-error-isolation': dispatch_isolation,
            'AC3/unknown-measured-usage-once': unknown_usage,
            'AC3/crash-before-evidence-usage': crashed_usage,
            'AC3/failed-release-wake-retry': failed_release_wakes,
            'AC3/busy-release-durable-event': busy_release}
