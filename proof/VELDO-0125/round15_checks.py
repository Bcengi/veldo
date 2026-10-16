"""Round 15: invalid decoded outbox entries are quarantined before recovery."""
import contextlib
import io
import json


def cases(T, helper):
    def invalid_entry(base, value):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        with w.OUT.locked(config) as root:
            active = root / '.active'
            active.mkdir()
            bad = active / 'invalid.json'
            original = json.dumps(value).encode()
            bad.write_bytes(original)
            healthy = dict(request=dict(dispatch_id='healthy'), due=0, attempts=0)
            w.OUT.move(root, w.OUT.locate(root, 'healthy'), '.active', w.CL.durable_json, healthy)
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            recovery_errors = w.OUT.recover_active(config)
        assert not bad.exists(), 'invalid decoded entry retained in .active'
        assert (base / '.parked' / bad.name).read_bytes() == original, 'quarantine changed original bytes'
        assert not recovery_errors, 'invalid entry treated as an operational error'
        assert w.OUT.entries(config, ready_only=True) == [healthy], 'healthy peer was not scheduled'
        records = [json.loads(line) for line in errors.getvalue().splitlines()]
        assert len(records) == 1 and records[0]['operation'] == 'worker_recovery_failed'
        assert records[0]['entry'] == bad.name
        calls = []
        w.receive_locked = lambda config, request: calls.append(request['dispatch_id']) or dict(host_released=True)
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            w.resume_pending(config, drain=True)
            w.OUT.recover_active(config)
        assert calls == ['healthy'] and not w.OUT.entries(config), 'healthy peer did not drain'
        assert not errors.getvalue(), 'quarantined entry caused repeated recovery errors'

    valid = dict(request=dict(dispatch_id='invalid'), due=0, attempts=0)
    values = {'empty-object': {}, 'array': [], 'string': 'x', 'missing-dispatch': {'request': {}},
              'missing-request': dict(due=0, attempts=0),
              'invalid-request': dict(valid, request=[]),
              'invalid-dispatch': dict(valid, request=dict(dispatch_id=123)),
              'missing-due': dict(request=valid['request'], attempts=0),
              'invalid-due': dict(valid, due='later'),
              'missing-attempts': dict(request=valid['request'], due=0),
              'invalid-attempts': dict(valid, attempts='one')}
    return {'AC3/invalid-active-' + name + '-quarantined':
            lambda base, value=value: invalid_entry(base, value) for name, value in values.items()}
