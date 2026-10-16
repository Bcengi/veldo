"""Round 11 crash boundaries and event-driven waits. Linux logic evidence only."""
import contextlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time
import types
from unittest.mock import patch


class Crash(BaseException):
    pass


def cases(T, helper):
    def host_fixture(base):
        P = helper('v125_crash_host', 'proof/VELDO-0125/macos_event_fixture.py')
        return P, P.start(base)

    def slot_crash(base, boundary, after, restart):
        P, (host, backend, request, paths) = host_fixture(base)
        original = P.M.write
        writes = []
        def write(path, value):
            writes.append((path.name, value.get('state')))
            if len(writes) == boundary and not after:
                raise Crash()
            original(path, value)
            if len(writes) == boundary and after:
                raise Crash()
        with patch.object(P.M, 'write', write):
            try:
                host.start(request)
            except Crash:
                pass
            else:
                raise AssertionError('crash boundary not reached')
        # Starting intent and its index can be retired; a durable launch intent
        # must retain capacity even if bootstrap's response never returned.
        record = P.M.read(host.root / host.label('dispatch/test') / 'slot.json')
        expected = int(bool(record and record['state'] not in ('starting', 'retired')))
        if restart:
            host = P.M.Supervisor(host.profile, host.qualification, backend=backend)
        assert host.status()['pending'] == expected, (writes, record)
        live = P.M.read(host.root / '.live-slots.json')
        assert len(live) == expected
        for label, state in live.items():
            assert P.M.read(host.root / label / 'slot.json')['state'] == state
        if not expected:
            assert backend.bootstraps == 0, 'launched work silently retired'
            request['contract']['dispatch_id'] = 'dispatch/next'
            request['contract_digest'] = P.P.digest(request['contract'])
            request['environment'].update(host.run_environment('dispatch/next', request['scratch']))
            host.start(request)
            assert backend.bootstraps == 1, 'crash permanently consumed capacity'

    def retirement_crash(base, authority, after, restart):
        P, (host, backend, request, paths) = host_fixture(base)
        run = host.start(request)
        assert run.wait()['state'] == 'exited'
        original = P.M.write
        def write(path, value):
            if path.name == '.live-slots.json':
                if after:
                    original(path, value)
                raise Crash()
            original(path, value)
        with patch.object(P.M, 'write', write):
            try:
                if authority:
                    host.release_authority(run.dispatch, request['contract_digest'], dict(ok=True,
                        host_released=True, binding=dict(dispatch_id=run.dispatch,
                        contract_digest=request['contract_digest'], host=backend.facts()['host'])))
                else:
                    run.release()
            except Crash:
                pass
            else:
                raise AssertionError('retirement crash not injected')
        if restart:
            host = P.M.Supervisor(host.profile, host.qualification, backend=backend)
        # Admission itself reconciles, with no status/release_authority repair call.
        request['contract']['dispatch_id'] = 'dispatch/next'
        request['contract_digest'] = P.P.digest(request['contract'])
        request['environment'].update(host.run_environment('dispatch/next', request['scratch']))
        host.start(request)
        assert host.status()['pending'] == 1 and backend.bootstraps == 2

    def migrate_before_admission(base):
        P, (host, backend, request, paths) = host_fixture(base)
        (host.root / '.live-slots.json').unlink()
        for i in range(500):
            directory = host.root / ('historical-' + str(i))
            directory.mkdir()
            (directory / 'slot.json').write_text('{"state":"retired"}')
        reads = []
        read = P.M.read
        def counted(path):
            if path.parent.name.startswith('historical-'):
                reads.append(path)
            return read(path)
        with patch.object(P.M, 'read', counted):
            host = P.M.Supervisor(host.profile, host.qualification, backend=backend)
        assert len(reads) == 500, 'legacy pool was not migrated once at initialization'
        scanned = os.scandir
        def bounded(path):
            assert isinstance(path, int) or Path(path) != host.root, 'history enumeration during admission'
            return scanned(path)
        def bounded_read(path):
            assert not path.parent.name.startswith('historical-'), 'historical slot read during admission'
            return read(path)
        with patch('os.scandir', bounded), patch.object(P.M, 'read', bounded_read):
            host.start(request)
            P.M.Supervisor(host.profile, host.qualification, backend=backend)

    def active_crash(base, drain):
        worker = T.load('control_worker')
        config = dict(runs=str(base))
        request = dict(dispatch_id='orphan')
        if drain:
            worker.OUT.enqueue(config, request, worker.CL.durable_json)
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(read_fd)
            def held(*args):
                os.write(write_fd, b'active')
                signal.pause()
            worker.receive_locked = held
            if drain:
                worker.resume_pending(config, drain=True)
            else:
                worker.receive(config, request)
            os._exit(2)
        os.close(write_fd)
        try:
            assert os.read(read_fd, 6) == b'active'
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        finally:
            os.close(read_fd)
        assert not worker.OUT.entries(config, ready_only=True)
        assert (base / '.active' / worker.OUT.key('orphan')).exists()
        delivered = []
        worker.receive_locked = lambda config, request: delivered.append(request) or {'host_released': True, 'record': {'state': 'exited'}}
        worker.install_resumer = lambda *args: None
        path = base / 'config.json'
        path.write_text(json.dumps(config))
        with patch.object(worker.sys, 'stdin', io.StringIO('{"dispatch_id":"new"}\n')), \
                patch.object(worker, 'sleep', side_effect=AssertionError('crash recovery timer')), \
                contextlib.redirect_stdout(io.StringIO()):
            worker.main(str(path))
        assert delivered == [dict(request, action='resume'), {'dispatch_id': 'new'}], delivered
        assert not worker.OUT.entries(config)

    def recorder_failure(base, finalizer):
        worker = T.load('control_worker')
        config = dict(runs=str(base))
        request = dict(dispatch_id='cannot-record')
        worker.OUT.enqueue(config, request, worker.CL.durable_json)
        attempted = []
        def fail(*args):
            attempted.append(1)
            raise PermissionError('unwritable_outbox')
        def receive(*args):
            if finalizer:
                worker.CL.durable_json = fail
            raise OSError('delivery_offline')
        worker.receive_locked = receive
        if not finalizer:
            worker.OUT.failure = fail
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors), patch.object(worker, 'sleep', side_effect=AssertionError('retry loop')):
            try:
                worker.resume_pending(config, drain=True)
            except worker.RecorderFailure:
                pass
            else:
                raise AssertionError('recorder failure did not stop drain')
        assert 1 <= len(attempted) <= 2
        assert 'worker_delivery_recorder_failed' in errors.getvalue() and 'unwritable_outbox' in errors.getvalue()

    def startup_ready_event(base):
        P, (host, backend, request, paths) = host_fixture(base)
        bootstrap = backend.bootstrap
        ready, waits = [], []
        def start(*args):
            bootstrap(*args)
            path = backend.directory / 'ready.json'
            ready.append(path.read_bytes())
            path.unlink()
        def wait_file(path, seconds):
            waits.append((path.name, seconds))
            path.write_bytes(ready[0])
            return True
        backend.bootstrap, backend.wait_file = start, wait_file
        backend.sleep = lambda seconds: (_ for _ in ()).throw(AssertionError('startup polling'))
        assert host.start(request).state == 'running'
        assert waits == [('ready.json', host.profile['startup_seconds'])]

    def supervisor_exit_wait(base):
        P, (host, backend, request, paths) = host_fixture(base)
        run = host.start(request)
        waits, scans = [], []
        members = backend.members
        backend.members = lambda group: scans.append(group) or members(group)
        def exited(watch, seconds):
            waits.append(seconds)
            if seconds:
                backend.now = .06
                backend.finish()
            return backend.exit_event
        backend.exited = exited
        backend.sleep = lambda seconds: (_ for _ in ()).throw(AssertionError('healthy process sleep loop'))
        assert run.wait()['state'] == 'exited'
        assert len([seconds for seconds in waits if seconds > 0]) == 1
        assert waits[-1] == run.deadline and len(scans) == 2
        assert not (run.directory / 'heartbeat.json').exists()

    def wrapper_exit_wait(base):
        wrapper = T.load('project_runner_macos_wrapper')
        executable = str(Path(sys.executable).resolve())
        import hashlib
        request = dict(argv=[executable], binary_digest='sha256:' + hashlib.sha256(Path(executable).read_bytes()).hexdigest(),
            startup_seconds=2, dispatch_id='wrapper', clone=str(base), environment=dict(os.environ), sandbox='',
            heartbeat_seconds=.001, kill_grace_seconds=.1, settle_seconds=.1)
        (base / 'request.json').write_text(json.dumps(request))
        identity = lambda pid: {'pid': pid}
        real_popen = subprocess.Popen
        calls, scans = [], []
        def launch(*args, **kwargs):
            child = real_popen([executable, '-c', 'import time; time.sleep(.05)'], **{k:v for k,v in kwargs.items() if k != 'process_group'}, start_new_session=True)
            wait = child.wait
            def blocking(timeout=None):
                calls.append(timeout)
                assert timeout is None, 'wrapper used subprocess timeout polling'
                return wait()
            child.wait = blocking
            return child
        wrapper.identity = identity
        wrapper.coalition = lambda pid: 1
        wrapper.coalition_members = lambda job: scans.append(job) or [os.getpid()]
        file_waits = []
        def wait_file(path, seconds):
            file_waits.append(path.name)
            path.write_text('{"runtime_seconds": 5}')
            return True
        wrapper.wait_file = wait_file
        with patch.object(wrapper.os, 'getpgrp', return_value=os.getpid()), patch.object(wrapper.subprocess, 'Popen', launch):
            assert wrapper.main(base) == 0
        assert file_waits == ['go']
        assert calls == [None] and len(scans) == 1
        assert not (base / 'heartbeat.json').exists()
        assert json.loads((base / 'result.json').read_text())['returncode'] == 0

    rows = {'AC2/upgrade-migrates-before-admission': migrate_before_admission,
            'AC3/receiver-crash-start-event': lambda base: active_crash(base, False),
            'AC3/drain-crash-start-event': lambda base: active_crash(base, True),
            'AC3/recorder-failure-stops-drain': lambda base: recorder_failure(base, False),
            'AC3/finalizer-failure-stops-drain': lambda base: recorder_failure(base, True),
            'AC3/startup-ready-event': startup_ready_event,
            'AC3/supervisor-blocking-exit': supervisor_exit_wait,
            'AC3/wrapper-blocking-exit': wrapper_exit_wait}
    # request, admission index/record, launch-intent index/record, ready, worker,
    # running index/record and go. Each side of every write is a crash boundary.
    for boundary in range(1, 11):
        for after in (False, True):
            for restart in (False, True):
                name = f'AC2/slot-crash-{boundary}-{"after" if after else "before"}-{"restart" if restart else "admission"}'
                rows[name] = lambda base, b=boundary, a=after, r=restart: slot_crash(base, b, a, r)
    for authority in (False, True):
        for after in (False, True):
            for restart in (False, True):
                name = f'AC2/retirement-crash-{authority}-{after}-{restart}'
                rows[name] = lambda base, a=authority, b=after, r=restart: retirement_crash(base, a, b, r)
    return rows
