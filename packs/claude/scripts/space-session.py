#!/usr/bin/env python3
"""Record a client session notification, with a deadline shorter than the hook's 15 seconds.

The installer supplies VELDO_SPACE_STATE_ROOT (the authority's state root) and puts veldo on PATH,
or supplies VELDO_SPACE_CLI. VELDO_INSTALLATION retains its usual meaning. Installation in account
folders belongs to the installer ticket. This script creates no scratch and removes nothing.

No notification is dropped without a record. With no VELDO_SPACE_STATE_ROOT the state root is the
one `veldo space event` falls back to: $XDG_STATE_HOME/veldo, else ~/.local/state/veldo. The same
folder is where the entry is spooled when the state root's spool folder is refused (the refusal is
noted beside that folder). When the spool module cannot be loaded, the input is no JSON or the
deadline passes before the entry is written, one line with what the hook was given and why is
appended to space-session.unspooled.jsonl under the state root, else under the fallback.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

MAX_BYTES = 1 << 20
UNSPOOLED = 'space-session.unspooled.jsonl'


def note(roots, document):
    """One line under the first root that takes it. Nothing it does reaches the client."""
    try:
        data = (json.dumps(dict(document, at=time.time()), sort_keys=True, default=repr) + '\n').encode()
    except Exception:
        return None
    for root in roots:
        try:
            if not root or not os.path.isabs(root):
                continue
            os.makedirs(root, mode=0o700, exist_ok=True)
            path = os.path.join(root, UNSPOOLED)
            descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            try:
                os.write(descriptor, data)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return path
        except Exception:
            continue
    return None


def main():
    def expired(_number, _frame):
        raise TimeoutError('session hook deadline')

    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 12)
    base = os.environ.get('XDG_STATE_HOME') or os.path.join(
        os.environ.get('HOME') or os.path.expanduser('~'), '.local', 'state')
    fallback = os.path.join(base, 'veldo')
    root = os.environ.get('VELDO_SPACE_STATE_ROOT') or fallback
    seen = {'hook': sys.argv[1:2], 'pid': os.getppid()}
    try:
        seen['input'] = sys.stdin.buffer.read(MAX_BYTES + 1).decode(errors='replace')
        cli = os.environ.get('VELDO_SPACE_CLI') or shutil.which('veldo')
        if not cli:
            raise RuntimeError('no veldo on PATH and no VELDO_SPACE_CLI')
        path = Path(cli).resolve().parent.parent / '.veldo' / 'control_space_spool.py'
        spec = importlib.util.spec_from_file_location('veldo_session_spool', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = json.loads(seen['input'])
        kind = {'SessionStart': 'session_started', 'SessionEnd': 'session_ended'}[sys.argv[1]]
        return module.session_hook(kind, payload, root, fallback=fallback)
    except Exception as error:
        signal.setitimer(signal.ITIMER_REAL, 0)
        note((root, fallback), dict(seen, reason=str(error) or type(error).__name__))
        return 0
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    sys.exit(main())
