"""Repeated parks preserve every record, including uninterpretable original bytes."""
import contextlib
import io
import json
import os
from pathlib import Path
from unittest.mock import patch


def cases(T, helper):
    def parked(base):
        # Count files, not dispatch identities: one dispatch may have many records.
        return [path.read_bytes() for path in sorted((base / '.parked').glob('*.json'))]

    def corrupt_then_failure(base, recorder=False):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        request = dict(dispatch_id='same-dispatch', action='release')
        path = base / '.waiting' / w.OUT.key(request['dispatch_id'])
        path.parent.mkdir()
        original = b'{broken'
        path.write_bytes(original)
        def fail(*args):
            raise w.CL.Refused('binding_mismatch:x')
        w.receive_locked = fail
        if recorder:
            w.OUT.failure = lambda *args: (_ for _ in ()).throw(OSError('recorder failed'))
        with contextlib.redirect_stderr(io.StringIO()):
            try:
                w.receive(config, request)
            except (w.CL.Refused, w.RecorderFailure):
                pass
            else:
                raise AssertionError('failed delivery was acknowledged')
        records = parked(base)
        assert len(records) == 2 and original in records, 'later park destroyed corrupt bytes'
        fresh, = [json.loads(raw) for raw in records if raw != original]
        assert fresh['request'] == request
        if not recorder:
            assert fresh['reason'] == 'binding_mismatch:x' and fresh['attempts'] == 1
        assert not w.OUT.entries(config)
        assert not list((base / '.waiting').glob('*.json'))

    def repeated(base, kind):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        expected = []
        for number in range(3):
            request = dict(dispatch_id='same-dispatch', sequence=number)
            w.OUT.enqueue(config, request, w.CL.durable_json)
            path = w.OUT.locate(base, request['dispatch_id'])
            with contextlib.redirect_stderr(io.StringIO()):
                if kind == 'quarantine':
                    raw = b'{broken-' + str(number).encode()
                    path.write_bytes(raw)
                    assert w.OUT.read_entry(base, path) is None
                    expected.append(raw)
                elif kind == 'recorder':
                    expected.append(path.read_bytes())
                    w.OUT.park_recorder_failure(config, request['dispatch_id'])
                else:
                    w.OUT.failure(config, request, w.CL.Refused('binding_mismatch:' + str(number)),
                                  w.CL.durable_json)
            records = parked(base)
            assert len(records) == number + 1, 'same dispatch replaced an earlier park'
            if kind != 'failure':
                assert set(records) == set(expected)
            else:
                values = [json.loads(raw) for raw in records]
                assert {value['request']['sequence'] for value in values} == set(range(number + 1))
                assert all(value['reason'] == 'binding_mismatch:' + str(value['request']['sequence'])
                           and value['attempts'] == 1 for value in values)
            assert not w.OUT.entries(config)

    def durability(base, interrupted=False):
        w = T.load('control_worker')
        config = dict(runs=str(base))
        w.OUT.enqueue(config, dict(dispatch_id='durable'), w.CL.durable_json)
        path = w.OUT.locate(base, 'durable')
        original = path.read_bytes()
        synced = set()
        fsync, unlink = os.fsync, Path.unlink
        def sync(fd):
            inode = os.fstat(fd).st_ino
            if interrupted and inode == (base / '.parked').stat().st_ino:
                raise OSError('interrupted parked directory sync')
            synced.add(inode)
            return fsync(fd)
        def remove(source, *args, **kwargs):
            if source == path:
                assert source.stat().st_ino in synced, 'file bytes not synced before dequeue'
                assert base.stat().st_ino in synced, 'park directory creation not synced'
                assert (base / '.parked').stat().st_ino in synced, 'park link not synced before dequeue'
                assert original in parked(base), 'source removed before evidence published'
            return unlink(source, *args, **kwargs)
        with patch('os.fsync', sync), patch.object(Path, 'unlink', remove):
            try:
                w.OUT.park_path(base, path)
            except OSError:
                assert interrupted and path.read_bytes() == original
            else:
                assert not interrupted and not path.exists()
        assert parked(base) == [original]
        if not interrupted:
            retained, = (base / '.parked').glob('*.json')
            assert retained.stat().st_ino in synced, 'parked file bytes were never fsynced'
        if interrupted:
            w.OUT.park_path(base, path)
            assert parked(base) == [original, original], 'recovery overwrote the already published park'

    return {
        'AC3/corrupt-bytes-survive-failure-park': corrupt_then_failure,
        'AC3/corrupt-bytes-survive-recorder-park': lambda base: corrupt_then_failure(base, True),
        **{'AC3/repeated-' + kind + '-parks-retained': lambda base, kind=kind: repeated(base, kind)
           for kind in ('quarantine', 'failure', 'recorder')},
        'AC3/park-bytes-and-link-durable-before-dequeue': durability,
        'AC3/interrupted-park-preserves-source-and-prior-park': lambda base: durability(base, True),
    }
