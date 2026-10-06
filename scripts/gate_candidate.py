#!/usr/bin/env python3
"""Authority-only entry to candidate execution; no candidate imports before confinement."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    authority = Path(__file__).resolve().parents[1]
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    config = os.environ.get('VELDO_AGENT_CONFIG', str(authority / 'scripts/agent_sandbox.json'))
    result = subprocess.run([sys.executable, '-I', '-S',
        str(authority / 'scripts/agent_sandbox.py'), '--profile', 'gate',
        '--config', config, '--worktree', args.root, '--', *command], close_fds=True)
    if result.returncode:
        print('candidate execution failed in store-denied domain (publication forbidden)', file=sys.stderr)
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
