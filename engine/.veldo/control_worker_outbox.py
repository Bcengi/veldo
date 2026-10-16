"""Durable event queue for Mac deliveries; completed run history is never read."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def key(dispatch):
    return hashlib.sha256(dispatch.encode()).hexdigest() + '.json'


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
    destination = root / state
    destination.mkdir(exist_ok=True)
    # Persist the new directory name before removing the old recovery record.
    sync_directory(root)
    target = destination / path.name
    value = entry or json.loads(path.read_text())
    if path.exists() and target != path:
        replace_entry(root, path, value, write)
        os.replace(path, target)
        sync_directory(target.parent)
        sync_directory(path.parent)
    else:
        replace_entry(root, target, value, write)
    return target


def park_recorder_failure(config, dispatch):
    """Retain the original bytes without calling the failed JSON recorder again."""
    with locked(config) as root:
        path = locate(root, dispatch)
        if path.exists():
            target = root / '.parked'
            target.mkdir(exist_ok=True)
            sync_directory(root)
            os.replace(path, target / path.name)
            sync_directory(target)
            sync_directory(path.parent)


def recover_active(config):
    """Schedule every orphan, including retries whose deadline is still future."""
    with locked(config) as root:
        locks = root / '.locks'
        locks.mkdir(exist_ok=True)
        for path in sorted((root / '.active').glob('*.json')):
            request = json.loads(path.read_text())['request']
            lock_key = hashlib.sha256(json.dumps(request['dispatch_id']).encode()).hexdigest()
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


def enqueue_locked(root, request, write):
    path = locate(root, request['dispatch_id'])
    previous = json.loads(path.read_text()) if path.exists() else None
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
            if not release and json.loads(path.read_text())['request'].get('action') == 'release':
                return
            sync_remove(path)


def entries(config, *, ready_only=False):
    with locked(config) as root:
        states = ('.pending',) if ready_only else ('.pending', '.active')
        return [json.loads(path.read_text()) for state in states
                for path in sorted((root / state).glob('*.json'))]


def failure(config, request, error, write):
    reason = getattr(error, 'code', str(error))
    transient = isinstance(error, (OSError, TimeoutError)) or reason.startswith('AUTHORITY_UNAVAILABLE:')
    with locked(config) as root:
        path = locate(root, request['dispatch_id'])
        if not path.exists():
            return
        entry = json.loads(path.read_text())
        entry.update(reason=reason, attempts=entry['attempts'] + 1)
        upgraded = entry['request'].get('action') == 'release' and request.get('action') != 'release'
        if upgraded:
            # The failed result attempt says nothing about the new release event.
            entry['due'] = 0
            state = '.pending'
        elif isinstance(error, WaitingForRelease):
            state = '.waiting'
        elif transient:
            entry['due'] = time.time() + min(300, 2 ** min(entry['attempts'] - 1, 9))
            state = '.pending'
        else:
            state = '.parked'
        move(root, path, state, write, entry)
    print(json.dumps(dict(operation='worker_delivery', dispatch_id=request['dispatch_id'],
        state={'.pending': 'retry_pending', '.waiting': 'waiting', '.parked': 'parked'}[state],
        reason=reason)), file=sys.stderr, flush=True)
