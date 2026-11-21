"""Round 17: operational read failures retain entries; clocks do not define validity."""
import contextlib
import errno
import io
import json
import math
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch


def cases(T, helper):
    def read_failure(base, reader, code):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        request = dict(dispatch_id='read-retry')
        state = '.active' if reader == 'recovery' else '.pending'
        with w.OUT.locked(config) as root:
            path = w.OUT.move(root, w.OUT.locate(root, request['dispatch_id']), state,
                              w.CL.durable_json, dict(request=request, attempts=0, due=0))
        original = path.read_bytes()
        healthy = None
        if reader != 'receive':
            # Both readers sort filenames: prove continuation AFTER the failed read.
            dispatch = next('healthy-' + str(i) for i in range(1000)
                            if w.OUT.key('healthy-' + str(i)) > path.name)
            healthy = dict(dispatch_id=dispatch)
            with w.OUT.locked(config) as root:
                peer = w.OUT.move(root, w.OUT.locate(root, dispatch), state,
                                 w.CL.durable_json, dict(request=healthy, attempts=0, due=0))
        # Exercise opening in recovery and reading in entries().
        method = 'open' if reader == 'recovery' else 'read_text'
        real_read = getattr(Path, method)
        failure = OSError(code, 'injected transient entry read failure')
        def broken_read(target, *args, **kwargs):
            if target == path:
                raise failure
            return real_read(target, *args, **kwargs)
        calls = []
        w.receive_locked = lambda config, request: calls.append(request['dispatch_id']) or dict(host_released=True)
        errors = io.StringIO()
        with patch.object(Path, method, broken_read), contextlib.redirect_stderr(errors):
            if reader == 'recovery':
                failures = w.OUT.recover_active(config)
                assert failures == [], 'read error escaped recovery as a failure'
                assert not peer.exists(), 'recovery stopped before the healthy peer'
                assert (base / '.pending' / peer.name).exists()
            elif reader == 'receive':
                w.receive(config, request, queued=True)
            elif reader == 'entries':
                assert w.OUT.entries(config) == [dict(request=healthy, attempts=0, due=0)]
            if healthy:
                w.resume_pending(config, drain=True)
                assert calls == [healthy['dispatch_id']], 'drain failed to skip unread entry and deliver peer'
        assert 'read-retry' not in calls, 'entry delivered despite failed read'
        assert path.exists(), 'valid entry parked on transient read failure'
        assert path.read_bytes() == original, 'read failure changed original bytes'
        assert not list((base / '.parked').glob('*.json')), 'read error quarantined valid content'
        records = [json.loads(line) for line in errors.getvalue().splitlines()]
        assert any(record.get('entry') == path.name and str(failure) in record.get('reason', '')
                   for record in records), 'read failure was not logged'
        w.resume_pending(config, drain=True)
        expected = ([healthy['dispatch_id']] if healthy else []) + ['read-retry']
        assert calls == expected and not w.OUT.entries(config), 'entry did not drain after read recovered'
        assert not path.exists() and not list((base / '.parked').glob('*.json'))

    def future_retry(base, due=None):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        now = [1000.0]
        w.OUT.time = w.time = SimpleNamespace(time=lambda: now[0])
        request = dict(dispatch_id='future-retry')
        w.OUT.enqueue(config, request, w.CL.durable_json)
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            if due is None:
                # The writer itself creates a retry four seconds away.
                for _ in range(3):
                    w.OUT.failure(config, request, OSError('offline'), w.CL.durable_json)
                due = 1004.0
                now[0] -= 600
            else:
                with w.OUT.locked(config) as root:
                    w.OUT.move(root, w.OUT.locate(root, request['dispatch_id']), '.pending',
                               w.CL.durable_json, dict(request=request, attempts=3, due=due))
            entry, = w.OUT.entries(config)
            assert entry['due'] == due and entry['attempts'] == 3, 'valid retry deadline changed'
            calls, sleeps = [], []
            w.receive_locked = lambda config, request: calls.append((request['dispatch_id'], now[0])) or dict(host_released=True)
            def sleep(seconds):
                assert math.isfinite(seconds) and 1 <= seconds <= 300, 'unbounded drain sleep'
                sleeps.append(seconds)
                assert len(sleeps) <= 3, 'retry never drained'
                # Huge timestamps cannot be advanced by 300 in float precision;
                # simulate clock resync after observing the first bounded sleep.
                now[0] = due if due > 2000 else now[0] + seconds
            w.sleep = sleep
            w.resume_pending(config, drain=True)
        assert calls == [('future-retry', due)], 'retry was lost or delivered before due'
        assert sleeps == ([300, 300, 4] if due == 1004 else [300])
        assert not w.OUT.entries(config) and not list((base / '.parked').glob('*.json'))

    rows = {}
    for reader in ('recovery', 'entries', 'drain'):
        for name in ('EIO', 'EMFILE', 'ENFILE', 'EACCES'):
            rows['AC3/outbox-' + reader + '-read-' + name.lower() + '-retries'] = (
                lambda base, reader=reader, code=getattr(errno, name): read_failure(base, reader, code))
    rows['AC3/outbox-receive-read-eio-retries'] = lambda base: read_failure(base, 'receive', errno.EIO)
    rows['AC3/outbox-retry-survives-backward-clock-step'] = future_retry
    for name, due in (('huge-finite', 1e300), ('max-float', sys.float_info.max),
                      ('max-int', int(sys.float_info.max))):
        rows['AC3/outbox-future-' + name + '-bounded-sleep'] = lambda base, due=due: future_retry(base, due)
    return rows
