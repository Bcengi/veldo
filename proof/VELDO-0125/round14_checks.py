"""Round 14 queue recovery regressions; no native macOS qualification claimed."""
import contextlib
import errno
import io
import json
from pathlib import Path
from unittest.mock import patch


def cases(T, helper):
    def orphan(w, base, dispatch):
        config = dict(runs=str(base))
        with w.OUT.locked(config) as root:
            path = w.OUT.move(root, w.OUT.locate(root, dispatch), '.active', w.CL.durable_json,
                              dict(request=dict(dispatch_id=dispatch), due=0, attempts=0))
        return config, path

    def lock_full(base):
        w = T.load('control_worker')
        config, path = orphan(w, base, 'disk-full')
        original = path.read_bytes()
        real_open = Path.open
        def open_file(path, *args, **kwargs):
            if path.parent == base / '.locks':
                raise OSError(errno.ENOSPC, 'No space left on device')
            return real_open(path, *args, **kwargs)
        errors = io.StringIO()
        with patch.object(Path, 'open', open_file), contextlib.redirect_stderr(errors):
            w.resume_pending(config, drain=True)
        assert path.exists(), 'healthy orphan parked after lock-file ENOSPC'
        assert path.read_bytes() == original, 'recovery changed the retained delivery'
        assert not list((base / '.pending').glob('*.json'))
        assert not list((base / '.parked').glob('*.json'))
        assert 'worker_recovery_failed' in errors.getvalue(), 'lock failure was silent'
        calls = []
        w.receive_locked = lambda config, request: calls.append(request['dispatch_id']) or dict(host_released=True)
        w.resume_pending(config, drain=True)
        assert calls == ['disk-full'] and not w.OUT.entries(config), 'restored space did not drain orphan'

    def undecodable(base):
        w = T.load('control_worker')
        config, path = orphan(w, base, 'undecodable')
        path.write_bytes(b'\xffnot-json')
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            w.resume_pending(config, drain=True)
        assert not path.exists() and not w.OUT.entries(config)
        assert (base / '.parked' / path.name).read_bytes() == b'\xffnot-json'
        assert 'worker_recovery_failed' in errors.getvalue()

    def blocked_recovery_sleeps(base, corrupt):
        w = T.load('control_worker')
        config, path = orphan(w, base, 'blocked')
        if corrupt:
            path.write_text('{broken json')
        original = path.read_bytes()
        now = [1000.0]
        for dispatch, due in (('later', 1040.0), ('earlier', 1020.0)):
            with w.OUT.locked(config) as root:
                w.OUT.move(root, w.OUT.locate(root, dispatch), '.pending', w.CL.durable_json,
                           dict(request=dict(dispatch_id=dispatch), due=due, attempts=1))
        real_replace = w.OUT.os.replace
        def replace(source, target):
            if Path(source) == path:
                raise PermissionError(errno.EACCES, 'entry cannot be moved or parked')
            return real_replace(source, target)
        calls, sleeps = [], []
        w.receive_locked = lambda config, request: calls.append((request['dispatch_id'], now[0])) or dict(host_released=True)
        def sleep(seconds):
            sleeps.append(seconds)
            assert seconds > 0, 'recovery failure caused a busy loop'
            now[0] += seconds
        errors = io.StringIO()
        with patch.object(w.OUT.os, 'replace', replace), patch.object(w.time, 'time', lambda: now[0]), \
                patch.object(w, 'sleep', sleep), contextlib.redirect_stderr(errors):
            w.resume_pending(config, drain=True)
        assert sleeps == [20.0, 20.0], 'drain did not wait for earliest due entry'
        assert calls == [('earlier', 1020.0), ('later', 1040.0)]
        assert path.read_bytes() == original and not w.OUT.entries(config, ready_only=True)
        records = [json.loads(line) for line in errors.getvalue().splitlines()]
        assert any(record['operation'] == 'worker_recovery_failed' for record in records)
        if corrupt:
            assert any(record['operation'] == 'worker_delivery_park_failed' for record in records)

    return {'AC3/recovery-lock-enospc-retries': lock_full,
            'AC3/undecodable-active-quarantined': undecodable,
            'AC3/unmovable-recovery-sleeps-until-due': lambda base: blocked_recovery_sleeps(base, False),
            'AC3/unparkable-recovery-sleeps-until-due': lambda base: blocked_recovery_sleeps(base, True)}
