"""Round 12 behavioural regressions. Synthetic interfaces do not qualify macOS."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import threading
import types
from unittest.mock import patch


def cases(T, helper):
    def fixture(base, mode='natural'):
        P = helper('round12_host', 'proof/VELDO-0125/macos_event_fixture.py')
        return P, P.start(base, mode)

    def recorder_park(base):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        request = dict(dispatch_id='recorder-loop')
        calls = []
        def offline(*args):
            calls.append(1)
            raise OSError('offline')
        w.receive_locked = offline
        w.OUT.failure = lambda *args: (_ for _ in ()).throw(OSError('recorder broken'))
        w.OUT.enqueue(config, request, w.CL.durable_json)
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                w.resume_pending(config, drain=True)
            except w.RecorderFailure:
                pass
            else:
                raise AssertionError('recorder error hidden')
        assert not list((base / '.pending').iterdir()), 'launchd would respawn the drain'
        parked = base / '.parked' / w.OUT.key(request['dispatch_id'])
        assert json.loads(parked.read_text())['request'] == request
        # RunAtLoad and repeated worker starts must not revive the parked item.
        for _ in range(3):
            w.resume_pending(config, drain=True)
        assert len(calls) == 1, 'persistent recorder failure caused a relaunch loop'

    def request_first(base):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        path = base / 'config.json'
        path.write_text(json.dumps(config))
        for i in range(20):
            w.OUT.enqueue(config, dict(dispatch_id='old-' + str(i)), w.CL.durable_json)
        w.install_resumer = lambda *args: None
        calls = []
        def receive(config, request, **kwargs):
            calls.append(request['dispatch_id'])
            if request['dispatch_id'] != 'new':
                raise w.RecorderFailure('old recorder unavailable')
            return dict(record=dict(state='running'))
        w.receive = receive
        output = io.StringIO()
        with patch.object(w.sys, 'stdin', io.StringIO('{"dispatch_id":"new"}\n')), contextlib.redirect_stdout(output):
            w.main(path)
        assert calls == ['new'], 'incoming handoff waited for old network/recorder work'
        assert json.loads(output.getvalue()) == dict(state='running')
        # Even an old recorder failure must not prevent another due entry's attempt.
        calls.clear()
        try:
            w.resume_pending(config)
        except w.RecorderFailure:
            pass
        assert len(calls) == 20, 'one recorder failure starved its peers'

    def future_active(base):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        request = dict(dispatch_id='future-orphan')
        due = w.time.time() + 300
        with w.OUT.locked(config) as root:
            w.OUT.move(root, w.OUT.locate(root, request['dispatch_id']), '.active', w.CL.durable_json,
                       dict(request=request, due=due, attempts=7))
        w.receive_locked = lambda *args: (_ for _ in ()).throw(AssertionError('retried before due'))
        w.resume_pending(config)
        entries = w.OUT.entries(config, ready_only=True)
        assert entries == [dict(request=request, due=due, attempts=7)], 'future orphan has no scheduled wake'
        assert not list((base / '.active').iterdir())
        calls = []
        w.receive_locked = lambda config, request: calls.append(request) or dict(host_released=True)
        with patch.object(w.time, 'time', return_value=due):
            w.resume_pending(config, drain=True)
        assert len(calls) == 1 and not w.OUT.entries(config)

    def migration_receiver(base):
        P, (host, backend, request, paths) = fixture(base)
        (host.root / '.live-slots.json').unlink()
        for i in range(100):
            directory = host.root / ('history-' + str(i))
            directory.mkdir()
            (directory / 'slot.json').write_text('{"state":"retired"}')
        w = T.load('control_worker')
        config = dict(profile=host.profile, qualification=host.qualification, signing_key=str(base / 'key'),
                      runs=str(base / 'runs'), workspace='w', binding={}, principal='p', ssh_argv=[])
        Path(config['signing_key']).write_text('fixture key')
        host.profile['signing_keys'] = [config['signing_key']]
        host.qualification['profile_digest'] = P.P.digest(host.profile)
        class ReachedClient(Exception):
            pass
        def client(*args, **kwargs):
            raise ReachedClient()
        original = w.organ
        w.organ = lambda name: P.M if name == 'project_runner_macos' else types.SimpleNamespace(Client=client) if name == 'control_worker_client' else original(name)
        with patch.object(Path, 'glob', side_effect=AssertionError('receiver scanned history')):
            try:
                w.receive_locked(config, {'dispatch_id': 'new'})
            except P.P.Refused as error:
                assert error.code == 'unavailable_service:slot_migration_required'
            else:
                raise AssertionError('uninstalled receiver admitted work')
        assert not (host.root / '.live-slots.json').exists(), 'receiver performed migration'
        path = base / 'config.json'
        path.write_text(json.dumps(config))
        calls = []
        w.resume_pending = lambda *args, **kwargs: calls.append(P.M.read(host.root / '.live-slots.json'))
        w.main(path, resume=True)
        assert calls == [{}], 'delivery worker startup did not migrate before recovery'
        with patch.object(Path, 'glob', side_effect=AssertionError('admission scanned history')):
            host.start(request)

    def stop_deadline(base):
        P, (host, backend, request, paths) = fixture(base, 'ignoring')
        run = host.start(request)
        backend.now = .29
        run.stop()
        assert run.wait()['state'] == 'exited'
        assert run.steps[1]['stage'] == 'terminate'
        assert run.steps[1]['monotonic'] <= .301, 'cooperative grace overran runtime cap'
        assert run.cause == 'runtime_cap'

    def event_liveness(base):
        for mode in ('blocked', 'natural'):
            P, (host, backend, request, paths) = fixture(base / mode, mode)
            run = host.start(request)
            backend.heartbeat = False
            result = run.wait()
            assert result['state'] == 'exited'
            if mode == 'blocked':
                assert run.cause == 'runtime_cap' and run.steps[0]['stage'] == 'terminate'
                assert .299 <= run.steps[0]['monotonic'] <= .301
            else:
                assert run.exit_seen and not run.steps, 'NOTE_EXIT failed to catch natural exit'
            assert not (run.directory / 'heartbeat.json').exists()

    def profile_v2(base):
        P, (host, backend, request, paths) = fixture(base)
        assert P.P.SCHEMA == 'veldo.macos_worker_profile/v2'
        assert not any('heartbeat' in name for name in P.P.CAPS)
        assert not any('heartbeat' in name for name in host.profile)
        P.P.validate(host.profile)
        assert host.qualification['profile_digest'] == P.P.digest(host.profile)
        for name in ('heartbeat_seconds', 'heartbeat_window_seconds'):
            try:
                P.P.validate(dict(host.profile, **{name: .01}))
            except P.P.Refused as error:
                assert error.code == 'unsupported_configuration:removed_heartbeat_field'
            else:
                raise AssertionError('retired heartbeat field accepted')
        try:
            P.P.validate(dict(host.profile, schema='veldo.macos_worker_profile/v1'))
        except P.P.Refused:
            pass
        else:
            raise AssertionError('old qualification/profile silently accepted')

    def watch_module():
        module = T.load('project_runner_macos_os')
        queues = []
        class Queue:
            def __init__(self):
                self.closed = False
                queues.append(self)
            def control(self, *args):
                return []
            def close(self):
                self.closed = True
        module.select = types.SimpleNamespace(kqueue=Queue, kevent=lambda *args, **kwargs: None,
            KQ_FILTER_PROC=1, KQ_FILTER_READ=2, KQ_EV_ADD=1, KQ_EV_ONESHOT=2,
            KQ_EV_CLEAR=4, KQ_NOTE_EXIT=8)
        return module, queues

    def watch_init(base):
        for boundary in ('pipe', 'reader', 'writer'):
            module, queues = watch_module()
            descriptors = []
            pipe, blocking = os.pipe, os.set_blocking
            def make_pipe():
                if boundary == 'pipe':
                    raise OSError('pipe failed')
                descriptors.extend(pipe())
                return tuple(descriptors)
            def set_blocking(fd, value):
                if fd == descriptors[0 if boundary == 'reader' else 1]:
                    raise OSError('set_blocking failed')
                blocking(fd, value)
            with patch.object(module.os, 'pipe', make_pipe), patch.object(module.os, 'set_blocking', set_blocking):
                try:
                    module.ExitWatch(123)
                except OSError:
                    pass
                else:
                    raise AssertionError('fault not injected')
            assert queues[0].closed, 'initialization leaked kqueue at ' + boundary
            for fd in descriptors:
                try:
                    os.fstat(fd)
                except OSError:
                    pass
                else:
                    os.close(fd)
                    raise AssertionError('initialization leaked pipe at ' + boundary)

    def watch_close_race(base):
        module, queues = watch_module()
        watch = module.ExitWatch(123)
        entered, release, closed = threading.Event(), threading.Event(), threading.Event()
        write = os.write
        errors = []
        def held(fd, value):
            entered.set()
            assert release.wait(2)
            return write(fd, value)
        def wake():
            try:
                module.Native().wake(watch)
            except BaseException as error:
                errors.append(error)
        def close():
            watch.close()
            closed.set()
        with patch.object(module.os, 'write', held):
            writer = threading.Thread(target=wake)
            writer.start()
            assert entered.wait(2)
            closer = threading.Thread(target=close)
            closer.start()
            try:
                assert not closed.wait(.05), 'close recycled descriptor during wake'
            finally:
                release.set()
                writer.join(2)
                closer.join(2)
        assert closed.is_set() and not errors
        # A late stop must not write even if another resource has reused the fd.
        writes = []
        with patch.object(module.os, 'write', lambda *args: writes.append(args)):
            module.Native().wake(watch)
        assert not writes, 'late stop wrote to a closed/reused descriptor'
        watch.close()  # Idempotent, without closing recycled descriptors.

    def stop_watch_reference(base):
        P, (host, backend, request, paths) = fixture(base, 'ignoring')
        run = host.start(request)
        watch = run.watch
        wakes = []
        backend.wake = lambda current: wakes.append(current)
        original = P.M.Run.__getattribute__
        def racing(instance, name):
            value = original(instance, name)
            if instance is run and name == 'watch' and value is not None:
                value.close()
                object.__setattr__(instance, 'watch', None)
            return value
        with patch.object(P.M.Run, '__getattribute__', racing):
            run.stop()
        assert wakes == [watch], 'stop read a cleared watch after checking its lifetime'

    def proof_correction(base):
        root = Path(__file__).resolve().parent
        log = root / 'b2-crash-events/routing-corrected.log'
        record = json.loads(Path(os.environ.get('VELDO_0125_CORRECTION_OVERRIDE',
            root / 'b2-round12/routing-correction.json')).read_text())
        assert record['log_sha256'] == hashlib.sha256(log.read_bytes()).hexdigest()
        assert record['complete'] is True and record['passed'] == 138 and record['failed'] == 0
        assert '138 passed, 0 failed in 107.07s' in log.read_text()
        assert record['run'] == 'round11-routing-corrected-106_veldo_0125_routing'
        original = Path(__file__).resolve().parents[2] / 'scripts/suites/103_veldo_0124_macos.py'
        assert hashlib.sha256(original.read_bytes()).hexdigest() == record['restored_0124_sha256']

    return {'AC3/recorder-failure-no-relaunch': recorder_park,
            'AC3/new-request-independent-of-backlog': request_first,
            'AC3/future-active-scheduled': future_active,
            'AC2/receiver-never-migrates-history': migration_receiver,
            'AC3/cooperative-stop-runtime-bound': stop_deadline,
            'AC3/stalled-wrapper-event-or-runtime-cap': event_liveness,
            'AC2/profile-v2-no-heartbeat-fields': profile_v2,
            'AC3/exit-watch-init-closes-resources': watch_init,
            'AC3/exit-watch-close-serializes-wake': watch_close_race,
            'AC3/stop-captures-watch-lifetime': stop_watch_reference,
            'AC1/round11-log-correction-and-original-row': proof_correction}
