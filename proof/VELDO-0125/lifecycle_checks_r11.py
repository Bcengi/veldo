"""Round 10 regressions: event holds, retained usage and live capacity indexing."""
import contextlib
import io
import json
import os
from pathlib import Path
import time
import types
from unittest.mock import patch


def cases(T, helper):
    @contextlib.contextmanager
    def crashed(base, *, output=True):
        P = helper('v125_lifecycle_host', 'proof/VELDO-0124/checks.py')
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
                raise KeyboardInterrupt('receiver lost before result evidence')
            try:
                worker.run(client, host, 'dispatch/test', str(paths['clone']), str(paths['scratch']),
                    dict(id='account', provider='codex', status='active',
                         profiles={backend.facts()['host']: str(paths['login'])}), collect=crash)
            except KeyboardInterrupt:
                pass
            binding = client.status('dispatch/test')['binding']
            runs = base / 'runs'
            directory = runs / worker.C.P.digest('dispatch/test').split(':')[-1]
            directory.mkdir(parents=True)
            (directory / 'run-context.json').write_bytes((paths['clone'].parent / 'run-context.json').read_bytes())
            slot_output = host.root / host.label('dispatch/test') / 'engine.out'
            measured = slot_output.read_bytes()
            if not output:
                slot_output.unlink()
            original = worker.organ
            worker.organ = lambda name: types.SimpleNamespace(Client=lambda *a, **k: client, durable_json=worker.CL.durable_json) \
                if name == 'control_worker_client' else types.SimpleNamespace(Supervisor=lambda *a: host) \
                if name == 'project_runner_macos' else original(name)
            config = dict(runs=str(runs), profile=host.profile, qualification=host.qualification,
                binding=f.binding, workspace=str(f.repo), signing_key=str(f.keys / 'mac'), principal='mac', ssh_argv=[])
            wake = dict(domain='domain', repository='repo', dispatch_id='dispatch/test',
                        contract_digest=binding['contract_digest'])
            yield types.SimpleNamespace(worker=worker, config=config, wake=wake, client=client, f=f,
                host=host, backend=backend, binding=binding, directory=directory,
                output=slot_output, measured=measured)
        finally:
            f.close()

    def authorize(c):
        c.f.client('operator').release(c.binding, reason='operator inspected stopped engine and collected output',
            cleanup=dict(terminated=True, cleaned=True, clone_removed=True))

    def measured_and_released(c):
        record = c.f.service.get('dispatch/test')
        assert record['usage']['tokens'] == 21, 'retained measurement discarded'
        invocation = c.f.res._records()[T.RES.entity('invocation', ['domain', record['invocation']])]
        assert invocation['charge']['tokens'] == 21 and len(invocation['reports']) == 2
        assert c.host.status()['pending'] == 0 and c.f.res.worker('dispatch/test')['retired']
        assert c.backend.bootstraps == 1

    def active_no_timer(base):
        worker = T.load('control_worker')
        config = dict(runs=str(base))
        request = dict(dispatch_id='healthy')
        delivered = []
        def receiver(config, request):
            delivered.append(request)
            if request.get('action') != 'release':
                assert not list((base / '.pending').glob('*.json')), 'healthy run woke QueueDirectories'
                worker.receive(config, dict(request, action='release'))
                for _ in range(15):
                    worker.resume_pending(config, drain=True)
                assert not worker.OUT.entries(config, ready_only=True)
                assert not list((base / '.parked').glob('*.json'))
            return dict(host_released=request.get('action') == 'release')
        worker.receive_locked = receiver
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors), patch.object(worker, 'sleep',
                side_effect=AssertionError('timer while receiver holds lock')):
            worker.receive(config, request)
            assert len(delivered) == 1
            assert worker.OUT.entries(config, ready_only=True)[0]['request']['action'] == 'release'
            worker.resume_pending(config, drain=True)
        assert len(delivered) == 2 and not worker.OUT.entries(config)
        assert not errors.getvalue(), 'healthy receiver logged a delivery error'

    def waiting_no_status_timer(base):
        with crashed(base) as c:
            statuses = []
            status = c.client.status
            c.client.status = lambda dispatch: statuses.append(dispatch) or status(dispatch)
            c.worker.OUT.enqueue(c.config, dict(c.wake, action='resume'), c.worker.CL.durable_json)
            with patch.object(c.worker, 'sleep', side_effect=AssertionError('operator wait timer')):
                # A child timeout wait must retain the real stdlib sleep.
                import subprocess, sys
                subprocess.run([sys.executable, '-c', 'import time; time.sleep(.03)'], timeout=5, check=True)
                for _ in range(15):
                    c.worker.resume_pending(c.config, drain=True)
            assert len(statuses) == 1, 'worker_status repeated while waiting for operator'
            waiting = Path(c.config['runs']) / '.waiting' / c.worker.OUT.key('dispatch/test')
            assert waiting.exists() and not c.worker.OUT.entries(c.config)
            assert c.host.status()['pending'] == 1 and not c.f.res.worker('dispatch/test')['retired']
            authorize(c)
            c.worker.receive(c.config, dict(c.wake, action='release'))
            measured_and_released(c)
            assert not waiting.exists()

    def evidence_release_wait(base):
        with crashed(base) as c:
            c.worker.CL.durable_json(c.directory / 'result-evidence.json', dict(
                binding=c.binding, observation={'state': 'unknown'}, usage=None, references={}))
            c.client.result = lambda **kwargs: {'host_released': False}
            statuses = []
            status = c.client.status
            c.client.status = lambda dispatch: statuses.append(dispatch) or status(dispatch)
            with patch.object(c.worker, 'sleep', side_effect=AssertionError('release hold timer')):
                c.worker.receive(c.config, dict(c.wake, action='release'))
                for _ in range(3):
                    c.worker.resume_pending(c.config, drain=True)
            waiting = Path(c.config['runs']) / '.waiting' / c.worker.OUT.key('dispatch/test')
            assert waiting.exists(), 'evidence plus release event was acknowledged before authorization'
            assert len(statuses) == 1 and not c.worker.OUT.entries(c.config)
            assert not (c.directory / 'delivery-complete.json').exists()
            assert c.host.status()['pending'] == 1

    def status_not_result_ack(base):
        with crashed(base, output=False) as c:
            c.worker.OUT.enqueue(c.config, dict(c.wake, action='resume'), c.worker.CL.durable_json)
            c.worker.resume_pending(c.config)
            assert not (c.directory / 'delivery-complete.json').exists()
            waiting = Path(c.config['runs']) / '.waiting' / c.worker.OUT.key('dispatch/test')
            assert waiting.exists(), 'status response dequeued unfinished work'
            c.output.write_bytes(c.measured)  # The orphan wrapper finishes after the receiver crash.
            authorize(c)
            c.worker.receive(c.config, dict(c.wake, action='release'))
            measured_and_released(c)

    def original_replay_usage(base):
        with crashed(base) as c:
            authorize(c)
            c.worker.receive(c.config, c.wake)  # Original dispatch identity, no action override.
            measured_and_released(c)
            c.worker.receive(c.config, c.wake)
            measured_and_released(c)

    def upgraded_release_attempted(base):
        with crashed(base) as c:
            authorize(c)
            c.worker.retain_crashed_output(c.host, c.client, c.wake, c.directory)
            result = c.client.result
            attempted = []
            def refused_result(*args, **kwargs):
                attempted.append('result')
                if len(attempted) == 1:
                    assert c.worker.receive(c.config, dict(c.wake, action='release')) is None
                raise c.worker.CL.Refused('binding_mismatch:remote_result')
            c.client.result = refused_result
            try:
                c.worker.receive(c.config, c.wake)
            except c.worker.CL.Refused:
                pass
            else:
                raise AssertionError('permanent result refusal hidden')
            pending = c.worker.OUT.entries(c.config)
            assert len(pending) == 1 and pending[0]['request']['action'] == 'release', 'unattempted release parked'
            c.worker.resume_pending(c.config, drain=True)
            assert len(attempted) == 2, 'stored release was not attempted'
            assert c.host.status()['pending'] == 0 and c.f.res.worker('dispatch/test')['retired']
            assert (c.directory / 'result-refusal.json').exists()
            assert (c.directory / 'result-evidence.json').exists()
            assert not c.worker.OUT.entries(c.config)
            c.client.result = result
            c.worker.receive(c.config, dict(c.wake, action='release'))
            measured_and_released(c)

    def lock_error_bounded(base):
        worker = T.load('control_worker')
        config = dict(runs=str(base))
        request = dict(action='resume', dispatch_id='locked')
        worker.OUT.enqueue(config, request, worker.CL.durable_json)
        original = Path.open
        count = []
        def denied(path, *args, **kwargs):
            if path.parent.name == '.locks':
                count.append(path)
                raise PermissionError('lock_open_denied')
            return original(path, *args, **kwargs)
        errors = io.StringIO()
        with patch.object(Path, 'open', denied), contextlib.redirect_stderr(errors):
            worker.resume_pending(config)
            worker.resume_pending(config)
        entry = worker.OUT.entries(config)[0]
        assert len(count) == 1 and entry['attempts'] == 1 and entry['due'] > time.time()
        assert 'lock_open_denied' in errors.getvalue() and 'retry_pending' in errors.getvalue()
        worker.receive_locked = lambda *args: {'host_released': True}
        with patch.object(worker, 'time', types.SimpleNamespace(time=lambda: time.time() + 301)):
            worker.resume_pending(config)
        assert not worker.OUT.entries(config)

    def live_admission_index(base):
        P = helper('v125_live_slots', 'proof/VELDO-0124/checks.py')
        host, backend, request, paths = P.start(base)
        host.status()  # One-time migration/initialization, outside admission.
        for i in range(500):
            directory = host.root / ('historical-' + str(i))
            directory.mkdir()
            (directory / 'slot.json').write_text(json.dumps(dict(state='retired')))
        scanned = os.scandir
        opened = Path.open
        def no_history_scan(path):
            assert isinstance(path, int) or Path(path) != host.root, 'admission enumerated completed slot history'
            return scanned(path)
        def no_history_read(path, *args, **kwargs):
            assert not path.parent.name.startswith('historical-'), 'admission read completed slot history'
            return opened(path, *args, **kwargs)
        with patch('os.scandir', no_history_scan), patch.object(Path, 'open', no_history_read):
            run = host.start(request)
            restarted = P.M.Supervisor(host.profile, host.qualification, backend=backend)
            assert restarted.status()['pending'] == 1
            run.wait()
            assert restarted.status()['pending'] == 1
            run.release()
            assert restarted.status()['pending'] == 0
            run.save('unknown')
            assert restarted.status()['pending'] == 0
        assert json.loads((host.root / '.live-slots.json').read_text()) == {}

    def park_parent_sync(base):
        worker = T.load('control_worker')
        config = dict(runs=str(base))
        request = dict(action='resume', dispatch_id='permanent')
        worker.OUT.enqueue(config, request, worker.CL.durable_json)
        fsync, replace, unlink = os.fsync, os.replace, Path.unlink
        synced = set()
        def sync(fd):
            # Linux fixture records which directory inode has reached stable storage.
            synced.add(os.fstat(fd).st_ino)
            return fsync(fd)
        def removal():
            parked = base / '.parked'
            assert base.stat().st_ino in synced and parked.exists(), 'park parent not synced before dequeue'
        def rename(source, target):
            if Path(source).parent.name == '.pending' and Path(target).parent.name == '.parked':
                removal()
            return replace(source, target)
        def remove(path, *args, **kwargs):
            if path.parent.name == '.pending':
                removal()
            return unlink(path, *args, **kwargs)
        with patch('os.fsync', sync), patch('os.replace', rename), patch.object(Path, 'unlink', remove):
            worker.OUT.failure(config, request, worker.CL.Refused('binding_mismatch:permanent'), worker.CL.durable_json)
        assert not worker.OUT.entries(config)
        assert json.loads((base / '.parked' / worker.OUT.key('permanent')).read_text())['reason'].startswith('binding_mismatch')

    return {'AC3/evidence-release-awaits-authorization': evidence_release_wait,
            'AC3/active-receiver-no-timer': active_no_timer,
            'AC3/operator-wait-no-status-timer': waiting_no_status_timer,
            'AC3/status-is-not-result-ack': status_not_result_ack,
            'AC3/original-replay-retains-usage': original_replay_usage,
            'AC3/upgraded-release-attempted': upgraded_release_attempted,
            'AC3/lock-errors-bounded-recorded': lock_error_bounded,
            'AC2/live-slot-admission-index': live_admission_index,
            'AC3/park-parent-durable': park_parent_sync}
