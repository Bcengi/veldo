#!/usr/bin/env python3
"""Read Claude Code 2.1.281's own login status command and fields from its bytes and its answers (VELDO-0185 AC4).

Run: python3 proof/VELDO-0185/extract_login_status.py <path of the 2.1.281 binary>

The binary is run only as `auth status --help` and `auth status`, each in a fresh empty profile directory
(CLAUDE_CONFIG_DIR and HOME), so no login of this host is read: once with no login at all, once with a stand-in
ANTHROPIC_API_KEY value that is no key, which shows a login that is not the claude.ai subscription. Its bytes are
read for the code that prints the answer, which names the authMethod the subscription reports. Prints the record
this specification adds to the version's qualification entry, and the observations it is read from.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def run(binary, argv, extra=None):
    with tempfile.TemporaryDirectory(prefix='v185-profile-') as profile:
        env = {'PATH': '/usr/bin:/bin', 'HOME': profile, 'CLAUDE_CONFIG_DIR': profile, 'LANG': 'C.UTF-8'}
        env.update(extra or {})
        done = subprocess.run([binary] + argv, capture_output=True, text=True, timeout=60, env=env,
                              stdin=subprocess.DEVNULL)
        out = done.stdout.replace(profile, '<profile>')
        return {'argv': argv, 'returncode': done.returncode, 'stdout': out}


def main(binary):
    data = Path(binary).read_bytes()
    found = re.search(rb'else if\(d==="claude\.ai"\)p="claude\.ai";.{0,1500}?s=\{loggedIn:C,authMethod:p.{0,40}', data, re.S)
    help_run = run(binary, ['auth', 'status', '--help'])
    logged_out = run(binary, ['auth', 'status', '--json'])
    api_key = run(binary, ['auth', 'status', '--json'], {'ANTHROPIC_API_KEY': 'not-a-key'})
    record = {'argv': ['auth', 'status', '--json'], 'logged_in': 'loggedIn', 'method': 'authMethod',
              'subscription': 'claude.ai',
              'source': 'proof/VELDO-0185/login-status.json: read from the 2.1.281 bytes and its answers in a fresh '
                        'empty profile; exit 0 when loggedIn, 1 otherwise'}
    print(json.dumps({'schema': 'veldo.login_status_extraction/v1', 'binary_sha256': hashlib.sha256(data).hexdigest(),
                      'code': found.group(0).decode('latin1') if found else None,
                      'observations': [help_run, logged_out, api_key], 'record': record}, indent=1, sort_keys=True))
    return 0 if found and '--json' in help_run['stdout'] else 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1]))
