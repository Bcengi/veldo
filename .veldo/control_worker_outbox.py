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


def enqueue(config, request, write):
    with locked(config) as root:
        pending = root / '.pending'
        pending.mkdir(exist_ok=True)
        path = pending / key(request['dispatch_id'])
        if path.exists():
            previous = json.loads(path.read_text())
            # A release event upgrades an ordinary result delivery, never the reverse.
            if previous['request'].get('action') == 'release':
                return
        write(path, dict(request=request, attempts=0, due=0))


def acknowledge(config, dispatch, *, release=False):
    with locked(config) as root:
        pending = root / '.pending'
        if pending.exists():
            path = pending / key(dispatch)
            if path.exists() and not release and json.loads(path.read_text())['request'].get('action') == 'release':
                return
            sync_remove(path)


def entries(config):
    with locked(config) as root:
        pending = root / '.pending'
        return [json.loads(path.read_text()) for path in sorted(pending.glob('*.json'))]


def failure(config, request, error, write):
    reason = getattr(error, 'code', str(error))
    transient = isinstance(error, (OSError, TimeoutError)) or reason.startswith('AUTHORITY_UNAVAILABLE:')
    with locked(config) as root:
        path = root / '.pending' / key(request['dispatch_id'])
        if not path.exists():
            return
        entry = json.loads(path.read_text())
        entry.update(reason=reason, attempts=entry['attempts'] + 1)
        if transient:
            entry['due'] = time.time() + min(300, 2 ** min(entry['attempts'] - 1, 9))
            write(path, entry)
        else:
            parked = root / '.parked'
            parked.mkdir(exist_ok=True)
            write(parked / path.name, entry)
            sync_remove(path)
    print(json.dumps(dict(operation='worker_delivery', dispatch_id=request['dispatch_id'],
        state='retry_pending' if transient else 'parked', reason=reason)), file=sys.stderr, flush=True)
