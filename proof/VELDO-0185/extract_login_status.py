#!/usr/bin/env python3
"""Read a Claude Code binary's own login status command and fields from its bytes and its answers (VELDO-0185 AC4).

    python3 proof/VELDO-0185/extract_login_status.py [--claude PATH]            # write login-status.json
    python3 proof/VELDO-0185/extract_login_status.py --check [--claude PATH]    # compare, exit 1 on a change

The default binary is the one the engines record names, and the version the record names is that binary's
(both through .veldo/qualify.py). The binary is run only as `auth status --help` and `auth status`, each in a
fresh empty profile directory (CLAUDE_CONFIG_DIR and HOME), so no login of this host is read: once with no
login at all, once with a stand-in ANTHROPIC_API_KEY value that is no key, which shows a login that is not the
claude.ai subscription. Its bytes are read for the code that prints the answer, which names the authMethod the
subscription reports; minified names in that code are read as patterns. Writes login-status.json beside this
file: the record this specification adds to the version's qualification entry, and the observations it is
read from.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'login-status.json'
IDENT = rb'[A-Za-z_$][\w$]*'
# The method chosen for a claude.ai login, then the JSON answer whose loggedIn and authMethod it fills.
CODE = re.compile(rb'else if\((' + IDENT + rb')==="claude\.ai"\)(' + IDENT + rb')="(claude\.ai)";.{0,1500}?'
                  + IDENT + rb'=\{(loggedIn):' + IDENT + rb',(authMethod):\2.{0,40}', re.S)


def _qualify():
    spec = importlib.util.spec_from_file_location('veldo_qualify', ROOT / '.veldo' / 'qualify.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


Q = _qualify()


def run(binary, argv, extra=None):
    with tempfile.TemporaryDirectory(prefix='v185-profile-') as profile:
        env = {'PATH': '/usr/bin:/bin', 'HOME': profile, 'CLAUDE_CONFIG_DIR': profile, 'LANG': 'C.UTF-8'}
        env.update(extra or {})
        done = subprocess.run([str(binary)] + argv, capture_output=True, text=True, timeout=60, env=env,
                              stdin=subprocess.DEVNULL)
        out = done.stdout.replace(profile, '<profile>')
        return {'argv': argv, 'returncode': done.returncode, 'stdout': out}


def extract(binary):
    """(table, problem): the table, and what is missing from the binary when it does not read as one."""
    data = Path(binary).read_bytes()
    found = CODE.search(data)
    help_run = run(binary, ['auth', 'status', '--help'])
    logged_out = run(binary, ['auth', 'status', '--json'])
    api_key = run(binary, ['auth', 'status', '--json'], {'ANTHROPIC_API_KEY': 'not-a-key'})
    version = Q.claude_version(Path(binary).resolve())
    logged_in, method, subscription = (found.group(4), found.group(5), found.group(3)) if found else (
        b'loggedIn', b'authMethod', b'claude.ai')
    record = {'argv': ['auth', 'status', '--json'], 'logged_in': logged_in.decode(), 'method': method.decode(),
              'subscription': subscription.decode(),
              'source': 'proof/VELDO-0185/login-status.json: read from the %s bytes and its answers in a fresh '
                        'empty profile; exit 0 when loggedIn, 1 otherwise' % version}
    table = {'schema': 'veldo.login_status_extraction/v1', 'binary_sha256': hashlib.sha256(data).hexdigest(),
             'code': found.group(0).decode('latin1') if found else None,
             'observations': [help_run, logged_out, api_key], 'record': record}
    problem = None
    if not found:
        problem = 'the binary holds no code that answers loggedIn and authMethod for a claude.ai login'
    elif '--json' not in help_run['stdout']:
        problem = '`auth status --help` offers no --json'
    return table, problem


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--claude', default=None, help="the Claude Code binary (default: the engines record's)")
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    table, problem = extract(args.claude or str(Q.binary('claude_code')))
    if problem:
        sys.stderr.write('moved: %s\n' % problem)
        return 1
    text = json.dumps(table, indent=1, sort_keys=True) + '\n'
    if args.check:
        same = OUT.is_file() and OUT.read_text() == text
        print('login-status.json %s' % ('matches the binary' if same else 'differs from the binary'))
        return 0 if same else 1
    OUT.write_text(text)
    print('wrote %s' % OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
