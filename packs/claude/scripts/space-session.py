#!/usr/bin/env python3
"""Record a client session notification, with a deadline shorter than the hook's 15 seconds.

The installer supplies VELDO_SPACE_STATE_ROOT (the authority's state root) and puts veldo on PATH,
or supplies VELDO_SPACE_CLI. VELDO_INSTALLATION retains its usual meaning. Installation in account
folders belongs to the installer ticket. This script creates no scratch and removes nothing.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import sys


def main():
    def expired(_number, _frame):
        raise TimeoutError('session hook deadline')

    signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, 12)
    try:
        cli = os.environ.get('VELDO_SPACE_CLI') or shutil.which('veldo')
        root = os.environ.get('VELDO_SPACE_STATE_ROOT')
        if not cli or not root:
            return 0
        path = Path(cli).resolve().parent.parent / '.veldo' / 'control_space_spool.py'
        spec = importlib.util.spec_from_file_location('veldo_session_spool', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = json.loads(sys.stdin.read(module.MAX_BYTES + 1))
        kind = {'SessionStart': 'session_started', 'SessionEnd': 'session_ended'}[sys.argv[1]]
        return module.session_hook(kind, payload, root)
    except Exception:
        return 0
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    sys.exit(main())
