"""The one test adapter that lets a suite publish to a local bare remote through VELDO-0153's
identity transport.

Every push, watermark fetch and remote listing the factory makes for a repository goes through
git_process's `identity` profile, which accepts only https/ssh remotes on github.com under the
repository identity's owner and resolves the identity's credential from the Secret Service. A suite
cannot reach GitHub or the owner's keyring, so this adapter substitutes the two endpoints at the
process boundary and nothing else:

    W = __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/identity_wire.py'))
    wire = W['Wire'](directory)
    url = wire.remote('origin', bare_path)    # https://github.com/fixture/origin.git
    with wire.active():                       # PATH carries the two stand-ins
        ...

A stand-in `git` on PATH replaces a registered URL by its bare path ONLY in an invocation that
carries the identity transport's options (`credential.interactive=false`, which the identity profile
alone passes, for a token and an ssh credential alike), after git_process has run every check on the
literal URL (owner, local overrides, argv binding). Any other invocation of a registered URL is
passed to Git unchanged, so an ambient-profile push to one fails rather than reaching the bare
remote. A stand-in `secret-tool` answers the fixture identity's references (support/git_identity.py)
and those a suite passes as `secrets` (an ssh credential names a key file that exists), and refuses
every other lookup, so no suite reads or writes the real keyring. Each identity
invocation is appended to `wire.log` for rows that assert the identity profile was used.

The PATH entry is inherited by processes a suite starts inside `active()`. The helper lives with
the suites and is never installed.
"""
import contextlib
import json
import os
from pathlib import Path
import shlex
import sys

OWNER = 'fixture'
TOKEN = 'fixture-identity-token'


def url(name, owner=OWNER, scheme='https'):
    host = 'git@github.com' if scheme == 'ssh' else 'github.com'
    return '%s://%s/%s/%s.git' % (scheme, host, owner, name)


class Wire:
    def __init__(self, directory, secrets=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.map = self.directory / 'remotes.json'
        self.log = self.directory / 'identity-invocations.jsonl'
        self.map.write_text('{}')
        values = {'fixture/api': TOKEN}
        values.update(secrets or {})
        # Every Git call of the suite meets the stand-in, so the pass-through is a shell exec; only an
        # identity invocation pays for the interpreter that rewrites its registered URLs.
        rewrite = self.directory / 'identity-git.py'
        rewrite.write_text('import json, os, sys\n'
                           'args = sys.argv[1:]\n'
                           'remotes = json.load(open(%r))\n'
                           'with open(%r, "a") as log:\n'
                           '    log.write(json.dumps(args) + "\\n")\n'
                           'os.execv("/usr/bin/git", ["git", *[remotes.get(a, a) for a in args]])\n'
                           % (str(self.map), str(self.log)))
        git = self.directory / 'git'
        git.write_text('#!/bin/sh\nfor a in "$@"; do\n'
                       '  case "$a" in credential.interactive=false)\n'
                       '    exec %s -I %s "$@";;\n  esac\ndone\nexec /usr/bin/git "$@"\n'
                       % (shlex.quote(sys.executable), shlex.quote(str(rewrite))))
        secret = self.directory / 'secret-tool'
        secret.write_text('#!%s -I\nimport sys\nvalues = %r\n'
                          'if sys.argv[1:2] != ["lookup"] or sys.argv[-1] not in values:\n'
                          '    sys.exit(1)\n'
                          'sys.stdout.write(values[sys.argv[-1]])\n' % (sys.executable, values))
        for path in (git, secret):
            path.chmod(0o700)

    def remote(self, name, path, owner=OWNER, scheme='https'):
        """Register a bare repository under `owner` and return the URL the factory is given: https for
        an identity whose push credential is a token, ssh for one whose credential is a key."""
        remotes = json.loads(self.map.read_text())
        remotes[url(name, owner, scheme)] = str(path)
        self.map.write_text(json.dumps(remotes))
        return url(name, owner, scheme)

    def invocations(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    @contextlib.contextmanager
    def active(self):
        saved = os.environ.get('PATH')
        os.environ['PATH'] = str(self.directory) + os.pathsep + (saved or os.defpath)
        try:
            yield self
        finally:
            if saved is None:
                os.environ.pop('PATH', None)
            else:
                os.environ['PATH'] = saved
