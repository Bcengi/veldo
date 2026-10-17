"""Round 16: one outbox contract on every read, plus bounded drain sleeps."""
import contextlib
import io
import json
import math
import sys
from types import SimpleNamespace
from unittest.mock import patch


def cases(T, helper):
    def invalid(base, value, reader, *, mismatch=False):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        state = '.active' if reader == 'recovery' else '.pending'
        directory = base / state
        directory.mkdir(parents=True)
        bad = directory / w.OUT.key('wrong-name' if mismatch else 'bad')
        original = json.dumps(value).encode()
        bad.write_bytes(original)
        w.OUT.enqueue(config, dict(dispatch_id='healthy'), w.CL.durable_json)
        calls, sleeps = [], []
        w.receive_locked = lambda config, request: calls.append(request['dispatch_id']) or dict(host_released=True)
        def sleep(seconds):
            sleeps.append(seconds)
            assert math.isfinite(seconds) and seconds > 0, 'unsafe drain sleep'
            raise AssertionError('invalid entry scheduled a retry')
        request = dict(dispatch_id='wrong-name' if mismatch else 'bad')
        errors = io.StringIO()
        with patch.object(w, 'sleep', sleep), contextlib.redirect_stderr(errors):
            if reader == 'recovery':
                assert not w.OUT.recover_active(config)
            elif reader == 'drain':
                w.resume_pending(config, drain=True)
            elif reader in ('receive', 'new-receive'):
                w.receive(config, request, queued=reader == 'receive')
            elif reader == 'enqueue':
                w.OUT.enqueue(config, request, w.CL.durable_json)
            elif reader == 'acknowledge':
                w.OUT.acknowledge(config, request['dispatch_id'])
            elif reader == 'failure':
                w.OUT.failure(config, request, OSError('offline'), w.CL.durable_json)
            elif reader == 'move':
                with w.OUT.locked(config) as root:
                    w.OUT.move(root, bad, '.active', w.CL.durable_json)
            assert not bad.exists(), reader + ': invalid entry retained'
            assert (base / '.parked' / bad.name).read_bytes() == original, reader + ': original bytes not quarantined'
            assert not any(call != 'healthy' for call in calls), reader + ': invalid entry delivered'
            assert not sleeps, reader + ': invalid entry reached sleep'
            w.resume_pending(config, drain=True)
        assert calls == ['healthy'] and not w.OUT.entries(config), reader + ': healthy peer failed to drain'
        records = [json.loads(line) for line in errors.getvalue().splitlines()]
        assert any(record.get('entry') == bad.name for record in records), 'missing quarantine diagnostic'

    valid = dict(request=dict(dispatch_id='bad'), attempts=0, due=0)
    required = {'name-key-mismatch': valid, 'infinity': dict(valid, due=float('inf')),
                'nan': dict(valid, due=float('nan')), 'out-of-float-range': dict(valid, due=int(sys.float_info.max) + 1),
                'negative-attempts': dict(valid, attempts=-1), 'string-attempts': dict(valid, attempts='1'),
                'unknown-field': dict(valid, unknown=True)}
    rows = {}
    readers = ('recovery', 'drain', 'receive', 'new-receive', 'enqueue', 'acknowledge', 'failure', 'move')
    for name, value in required.items():
        for reader in readers:
            rows['AC3/outbox-' + reader + '-' + name] = (
                lambda base, value=value, reader=reader, name=name:
                invalid(base, value, reader, mismatch=name == 'name-key-mismatch'))

    def contract(base, reader):
        more = {'empty-object': {}, 'array': [], 'null': None, 'string': 'bad',
                'missing-request': dict(attempts=0, due=0),
                'missing-attempts': dict(request=valid['request'], due=0),
                'missing-due': dict(request=valid['request'], attempts=0),
                'request-array': dict(valid, request=[]), 'request-null': dict(valid, request=None),
                'dispatch-missing': dict(valid, request={}),
                'dispatch-empty': dict(valid, request=dict(dispatch_id='')),
                'dispatch-number': dict(valid, request=dict(dispatch_id=1)),
                'dispatch-surrogate': dict(valid, request=dict(dispatch_id='\ud800')),
                'attempts-bool': dict(valid, attempts=True), 'attempts-float': dict(valid, attempts=1.0),
                'attempts-null': dict(valid, attempts=None), 'due-bool': dict(valid, due=False),
                'due-string': dict(valid, due='0'), 'due-null': dict(valid, due=None),
                'due-negative': dict(valid, due=-1), 'due-negative-infinity': dict(valid, due=-float('inf')),
                'due-huge-int': dict(valid, due=10 ** 400), 'due-over-float-bound': dict(valid, due=int(sys.float_info.max) + 1),
                'reason-number': dict(valid, reason=1), 'reason-null': dict(valid, reason=None)}
        # Freeze both queue and drain clocks without altering process-wide time.
        for name, value in more.items():
            with patch('time.time', return_value=1000):
                invalid(base / name, value, reader)
    for reader in ('recovery', 'drain', 'receive'):
        rows['AC3/outbox-complete-contract-' + reader] = lambda base, reader=reader: contract(base, reader)

    def valid_writer(base):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        w.OUT.time = SimpleNamespace(time=lambda: 1000)
        request = dict(dispatch_id='valid', action='resume', opaque={'writer': 'preserves request'})
        w.OUT.enqueue(config, request, w.CL.durable_json)
        assert w.OUT.entries(config) == [dict(request=request, attempts=0, due=0)]
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            for attempt in range(1, 13):
                w.OUT.failure(config, request, OSError('offline'), w.CL.durable_json)
                entry, = w.OUT.entries(config)
                assert type(entry['attempts']) is int and entry['attempts'] == attempt
                assert entry['due'] == 1000 + min(300, 2 ** (attempt - 1))
                assert entry['reason'] == 'offline' and entry['request'] == request
        # Both the maximum future deadline and old retries remain readable.
        assert entry['due'] == 1300
        w.OUT.time = SimpleNamespace(time=lambda: 100000)
        assert w.OUT.entries(config) == [entry]
        w.OUT.acknowledge(config, 'valid')
        assert not w.OUT.entries(config)
    rows['AC3/outbox-writer-contract-and-backoff-bound'] = valid_writer

    def defensive_sleep(base, delay):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        # Deliberately bypass entry validation to model a computation/clock bug.
        # No real sleep is allowed, and every iteration is bounded by this fixture.
        w.time = SimpleNamespace(time=lambda: 0)
        w.OUT.recover_active = lambda config: []
        batches = iter([[dict(valid, due=10)], [dict(valid, due=delay)], []])
        w.OUT.entries = lambda *args, **kwargs: next(batches)
        sleeps, errors = [], io.StringIO()
        w.sleep = sleeps.append
        with contextlib.redirect_stderr(errors):
            w.resume_pending(config, drain=True)
        assert len(sleeps) == 1 and math.isfinite(sleeps[0]) and 0 < sleeps[0] <= 300
        if not math.isfinite(delay) or delay < 0:
            records = [json.loads(line) for line in errors.getvalue().splitlines()]
            assert any(record['operation'] == 'worker_delivery_sleep_invalid' for record in records)
    for name, delay in (('infinity', float('inf')), ('nan', float('nan')), ('negative', -1),
                        ('zero', 0), ('huge', 1e300)):
        rows['AC3/drain-defensive-sleep-' + name] = lambda base, delay=delay: defensive_sleep(base, delay)
    return rows
