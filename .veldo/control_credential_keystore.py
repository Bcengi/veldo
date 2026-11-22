"""Linux Secret Service through libsecret's secret-tool, never a file fallback.

Values go on standard input, never argv or environment. Diagnostics are classified
and discarded, including on failure. get implements secretref's runtime store seam.
"""
import os
import subprocess
import re


class Refused(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class SecretService:
    def __init__(self, executable='secret-tool'):
        self.executable = executable

    def _run(self, action, name, value=None):
        argv = [self.executable, action]
        if action == 'store':
            argv += ['-' * 2 + 'label=Veldo credential']
        argv += ['application', 'veldo', 'credential', name]
        environment = dict(os.environ, LC_ALL='C')
        try:
            done = subprocess.run(argv, input=value.encode() if value is not None else b'',
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15, env=environment)
        except (OSError, subprocess.SubprocessError):
            raise Refused('unavailable_service:keystore_unreachable') from None
        if done.returncode:
            if action == 'lookup' and done.returncode == 1 and not done.stderr and not done.stdout:
                return None
            reason = 'keystore_locked' if b'locked' in done.stderr.lower() or b'dismissed' in done.stderr.lower() \
                else 'keystore_unreachable'
            raise Refused('unavailable_service:' + reason)
        if action == 'lookup':
            return done.stdout.decode('utf-8')
        return None

    def set(self, name, value):
        self._run('store', name, value)

    def delete(self, name):
        self._run('clear', name)

    def get(self, scheme, name):
        if scheme != 'keychain':
            raise Refused('invalid_input:keystore_scheme')
        return self._run('lookup', name)

    def contains(self, name):
        """Search attributes only. SearchItems returns object paths and never secret bytes."""
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name):
            return False
        attributes = "{'application': 'veldo', 'credential': '%s'}" % name
        try:
            done = subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.freedesktop.secrets',
                '--object-path', '/org/freedesktop/secrets', '--method',
                'org.freedesktop.Secret.Service.SearchItems', attributes], capture_output=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            raise Refused('unavailable_service:keystore_unreachable') from None
        if done.returncode:
            raise Refused('unavailable_service:keystore_unreachable')
        return b'/org/freedesktop/secrets/' in done.stdout
