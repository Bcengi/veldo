"""Durable event queue for Mac deliveries; completed run history is never read."""
import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time


MAX_BACKOFF = 300


def key(dispatch):
    return hashlib.sha256(dispatch.encode()).hexdigest() + '.json'


def validate_entry(entry, path):
    """Writer contract: required request/attempts/due, optional failure reason.

    Request is an opaque dict except for its non-empty string dispatch_id, whose
    key must name this file. Attempts is a non-negative int (never bool); due is
    an int or float (never bool), finite and in [0, sys.float_info.max]. Zero is
    immediate; validity is independent of the clock. Only failure() adds reason, a str.
    """
    if (type(entry) is not dict or not {'request', 'attempts', 'due'} <= entry.keys()
            or entry.keys() - {'request', 'attempts', 'due', 'reason'}
            or type(entry['request']) is not dict
            or type(entry['request'].get('dispatch_id')) is not str
            or not entry['request']['dispatch_id']
            or type(entry['attempts']) is not int or entry['attempts'] < 0
            or type(entry['due']) not in (int, float)
            or ('reason' in entry and type(entry['reason']) is not str)):
        raise ValueError('invalid outbox entry shape')
    if path.name != key(entry['request']['dispatch_id']):
        raise ValueError('outbox filename does not match dispatch_id')
    due = entry['due']
    # Check the range first so an arbitrarily large JSON int never overflows
    # float conversion inside isfinite().
    if due < 0 or due > sys.float_info.max or not math.isfinite(due):
        raise ValueError('outbox due must be finite and in [0, sys.float_info.max]')
    return entry


def read_entry(root, path, *, operation='worker_delivery_invalid_entry', raise_read_errors=False):
    """Read under locked(); quarantine invalid content, retain operational failures."""
    try:
        return validate_entry(json.loads(path.read_text()), path)
    except OSError as error:
        print(json.dumps(dict(operation='worker_delivery_read_failed', entry=path.name,
            reason=str(error))), file=sys.stderr, flush=True)
        if raise_read_errors:
            raise
        return None
    except (ValueError, RecursionError) as error:
        print(json.dumps(dict(operation=operation, entry=path.name, reason=str(error))),
              file=sys.stderr, flush=True)
        try:
            park_path(root, path)
        except Exception as park_error:
            print(json.dumps(dict(operation='worker_delivery_park_failed', entry=path.name,
                reason=str(park_error))), file=sys.stderr, flush=True)
            raise
        return None


@contextlib.contextmanager
def locked(config):
    root = Path(config['runs'])
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.pending.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield root


def sync_remove(path):
    path.unlink(missing_ok=True)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def replace_entry(root, path, value, write):
    # A crash during serialization must not leave a .tmp file inside the watched
    # directory: QueueDirectories would otherwise keep launching an empty drain.
    staging = root / '.pending-write.json'
    write(staging, value)
    os.replace(staging, path)
    descriptor = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class WaitingForRelease(Exception):
    """A durable hold resumed only by a new receiver event."""


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def locate(root, dispatch):
    for state in ('.pending', '.active', '.waiting'):
        path = root / state / key(dispatch)
        if path.exists():
            return path
    return root / '.pending' / key(dispatch)


def move(root, path, state, write, entry=None):
    value = entry if entry is not None else read_entry(root, path)
    if value is None:
        return None
    destination = root / state
    destination.mkdir(exist_ok=True)
    # Persist the new directory name before removing the old recovery record.
    sync_directory(root)
    target = destination / path.name
    if path.exists() and target != path:
        replace_entry(root, path, value, write)
        os.replace(path, target)
        sync_directory(target.parent)
        sync_directory(path.parent)
    else:
        replace_entry(root, target, value, write)
    return target


def park_path(root, path):
    """Quarantine original bytes even when reading or serialization is broken."""
    target = root / '.parked'
    target.mkdir(exist_ok=True)
    sync_directory(root)
    os.replace(path, target / path.name)
    sync_directory(target)
    sync_directory(path.parent)


def park_recorder_failure(config, dispatch):
    """Retain the original bytes without calling the failed JSON recorder again."""
    with locked(config) as root:
        path = locate(root, dispatch)
        if path.exists():
            park_path(root, path)


def recover_active(config):
    """Schedule every orphan, including retries whose deadline is still future."""
    errors = []
    with locked(config) as root:
        locks = root / '.locks'
        for path in sorted((root / '.active').glob('*.json')):
            try:
                entry = read_entry(root, path, operation='worker_recovery_failed')
            except Exception as error:
                errors.append(error)
                continue
            if entry is None:
                continue
            try:
                # Operational failures must retain a readable orphan for the next recovery.
                request = entry['request']
                lock_key = hashlib.sha256(json.dumps(request['dispatch_id']).encode()).hexdigest()
                locks.mkdir(exist_ok=True)
                with (locks / lock_key).open('a') as stream:
                    try:
                        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        continue
                    target = root / '.pending'
                    target.mkdir(exist_ok=True)
                    sync_directory(root)
                    os.replace(path, target / path.name)
                    sync_directory(target)
                    sync_directory(path.parent)
            except Exception as error:
                print(json.dumps(dict(operation='worker_recovery_failed', entry=path.name,
                    reason=str(error))), file=sys.stderr, flush=True)
                errors.append(error)
    return errors


def enqueue_locked(root, request, write):
    path = locate(root, request['dispatch_id'])
    previous = None
    if path.exists():
        previous = read_entry(root, path, raise_read_errors=True)
        if previous is None:
            return None
    if previous and previous['request'].get('action') == 'release':
        request = previous['request']
    entry = dict(request=request, attempts=0, due=0)
    return move(root, path, '.active' if path.parent.name == '.active' else '.pending', write, entry)


def enqueue(config, request, write):
    with locked(config) as root:
        enqueue_locked(root, request, write)


def acknowledge(config, dispatch, *, release=False):
    with locked(config) as root:
        path = locate(root, dispatch)
        if path.exists():
            entry = read_entry(root, path)
            if entry is None:
                return
            if not release and entry['request'].get('action') == 'release':
                return
            sync_remove(path)


def entries(config, *, ready_only=False):
    with locked(config) as root:
        states = ('.pending',) if ready_only else ('.pending', '.active')
        return [entry for state in states for path in sorted((root / state).glob('*.json'))
                if (entry := read_entry(root, path)) is not None]


def retryable(error):
    reason = getattr(error, 'code', str(error))
    return (isinstance(error, (OSError, TimeoutError)) or reason.startswith('AUTHORITY_UNAVAILABLE:')
            or reason == 'unavailable_service:slot_migration_required')


def failure(config, request, error, write):
    reason = getattr(error, 'code', str(error))
    transient = retryable(error)
    with locked(config) as root:
        path = locate(root, request['dispatch_id'])
        if not path.exists():
            return
        entry = read_entry(root, path)
        if entry is None:
            return
        entry.update(reason=reason, attempts=entry['attempts'] + 1)
        upgraded = entry['request'].get('action') == 'release' and request.get('action') != 'release'
        if upgraded:
            # The failed result attempt says nothing about the new release event.
            entry['due'] = 0
            state = '.pending'
        elif isinstance(error, WaitingForRelease):
            state = '.waiting'
        elif transient:
            entry['due'] = time.time() + min(MAX_BACKOFF, 2 ** min(entry['attempts'] - 1, 9))
            state = '.pending'
        else:
            state = '.parked'
        move(root, path, state, write, entry)
    print(json.dumps(dict(operation='worker_delivery', dispatch_id=request['dispatch_id'],
        state={'.pending': 'retry_pending', '.waiting': 'waiting', '.parked': 'parked'}[state],
        reason=reason)), file=sys.stderr, flush=True)
