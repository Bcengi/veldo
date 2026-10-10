"""The one test adapter that lets a suite publish to a local bare remote through VELDO-0153's
identity transport, inside a hermetic fence that keeps every fixture off the network and away from
the real keyring and credential stores.

Every push, watermark fetch and remote listing the factory makes for a repository goes through
git_process's `identity` profile, which accepts only https/ssh remotes on github.com under the
repository identity's owner and resolves the identity's credential from the Secret Service. A suite
cannot reach GitHub or the owner's keyring, so this adapter substitutes the two endpoints at the
process boundary and nothing else:

    W = __import__('runpy').run_path(str(ROOT / 'scripts/suites/support/identity_wire.py'))
    wire = W['Wire'](directory)
    url = wire.remote('origin', bare_path)    # https://github.com/fixture/origin.git
    with wire.active():                       # PATH carries the stand-ins; the fence is up
        ...

A stand-in `git` on PATH replaces a registered URL by its bare path ONLY in an invocation that
carries the identity transport's options (`credential.interactive=false`, which the identity profile
alone passes, for a token and an ssh credential alike), after git_process has run every check on the
literal URL (owner, local overrides, argv binding); it runs a suite's `before_push` program ahead of
an identity push. A stand-in `secret-tool` answers the fixture identity's references
(support/git_identity.py) and those a suite passes as `secrets` (an ssh credential names a key file
that exists), and refuses every other lookup, so no suite reads or writes the real keyring. Each
identity invocation is appended to `wire.log` for rows that assert the profile ran.

THE FENCE (`Fence`, which a Wire is). While `active()`:
- Every Git transport command run by name from PATH goes through support/hermetic_git.py, which
  refuses, records and reports (exit 97) any repository that is not local: a path, a file URL,
  http on a loopback host, ssh through a test adapter rather than the real ssh client, or ext::.
- A credential helper from the real user's global or system configuration is replaced by the
  fence's guard, which records a violation if Git ever asks it for a credential.
- SSH_AUTH_SOCK names the fence's own agent socket, which records every connection.
- An audit hook in this process refuses and records a socket connection or name lookup for a
  non-loopback host, and a connection to the real SSH agent or keyring sockets.
When `active()` ends, any recorded violation raises HermeticViolation naming each one, so a fixture
that would have reached the network or a real store fails its suite loudly, whatever its own row
expected. `violations()` lists them for a row that asserts the fence itself.

Stated limit: the fence sees Git started by name from PATH and sockets opened by this Python
process. A child that runs /usr/bin/git by absolute path, or opens sockets itself, is outside it;
the identity profile, git_process and the factory start Git as `git`.

The PATH entry is inherited by processes a suite starts inside `active()`. The helper lives with
the suites and is never installed.
"""
import contextlib
import json
import os
from pathlib import Path
import pwd
import shlex
import socket
import sys
import tempfile
import threading
import types

OWNER = 'fixture'
TOKEN = 'fixture-identity-token'
LOOPBACK = ('127.0.0.1', 'localhost', '::1')
GUARD = Path(__file__).resolve().with_name('hermetic_git.py')


def url(name, owner=OWNER, scheme='https'):
    host = 'git@github.com' if scheme == 'ssh' else 'github.com'
    return '%s://%s/%s/%s.git' % (scheme, host, owner, name)


class HermeticViolation(AssertionError):
    pass


def real_configs():
    """The real user's global and system Git configuration files, where a host's real credential
    stores are configured."""
    home = pwd.getpwuid(os.getuid()).pw_dir
    xdg = os.environ.get('XDG_CONFIG_HOME') or os.path.join(home, '.config')
    return [os.path.join(home, '.gitconfig'), os.path.join(xdg, 'git', 'config'), '/etc/gitconfig']


def _audit_state():
    """One audit hook per process, however often runpy loads this file; it judges for the
    innermost active fence."""
    state = sys.modules.get('_veldo_hermetic_fence')
    if state is None:
        state = types.ModuleType('_veldo_hermetic_fence')
        state.stack = []

        def hook(event, args):
            if state.stack and event in ('socket.connect', 'socket.getaddrinfo'):
                state.stack[-1]._audit(event, args)
        sys.addaudithook(hook)
        sys.modules[state.__name__] = state
    return state


def _loopback(host):
    host = host.decode() if isinstance(host, bytes) else str(host or '')
    return host in LOOPBACK or host.startswith('127.') or host == ''


class Fence:
    def __init__(self, directory, secrets=None, configs=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.violations_log = self.directory / 'hermetic-violations.jsonl'
        self.violations_log.touch()
        values = dict(secrets or {})
        self.guard = self.directory / 'credential-guard'
        self.guard.write_text('#!/bin/sh\n[ "$1" = get ] || exit 0\n'
                              'printf \'{"kind": "credential-store", "detail": "a real credential helper was asked"}\\n\' >> %s\n'
                              'echo "VELDO HERMETIC FENCE: refused (credential-store) a real credential helper was asked" >&2\n'
                              'printf "quit=true\\n"\n' % shlex.quote(str(self.violations_log)))
        self.conf = dict(violations=str(self.violations_log), guard=str(self.guard),
                         real_configs=list(real_configs() if configs is None else configs),
                         map=None, log=None, hook=None)
        self._write_conf()
        git = self.directory / 'git'
        git.write_text('#!/bin/sh\nfor a in "$@"; do\n  case "$a" in\n'
                       '    credential.interactive=false|push|fetch|pull|ls-remote|clone|fetch-pack|send-pack|remote|archive)\n'
                       '      exec %s -I %s %s "$@";;\n  esac\ndone\nexec /usr/bin/git "$@"\n'
                       % (shlex.quote(sys.executable), shlex.quote(str(GUARD)), shlex.quote(str(self.directory))))
        secret = self.directory / 'secret-tool'
        secret.write_text('#!%s -I\nimport sys\nvalues = %r\n'
                          'if sys.argv[1:2] != ["lookup"] or sys.argv[-1] not in values:\n'
                          '    sys.exit(1)\n'
                          'sys.stdout.write(values[sys.argv[-1]])\n' % (sys.executable, values))
        for path in (git, secret, self.guard):
            path.chmod(0o700)
        home = pwd.getpwuid(os.getuid()).pw_dir
        runtime = os.environ.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid()
        self.protected = [p for p in (os.environ.get('SSH_AUTH_SOCK'), os.path.join(runtime, 'keyring'),
                                      os.path.join(home, '.local/share/keyrings')) if p]

    def _write_conf(self):
        (self.directory / 'fence.json').write_text(json.dumps(self.conf))

    def _record(self, kind, detail):
        with self.violations_log.open('a') as log:
            log.write(json.dumps({'kind': kind, 'detail': detail}) + '\n')

    def _audit(self, event, args):
        if event == 'socket.getaddrinfo':
            if not _loopback(args[0]):
                self._record('network', 'name lookup for %r' % (args[0],))
                raise HermeticViolation('VELDO HERMETIC FENCE: refused (network) name lookup for %r' % (args[0],))
            return
        sock, address = args
        if sock.family in (socket.AF_INET, socket.AF_INET6) and not _loopback(address[0]):
            self._record('network', 'connection to %r' % (address,))
            raise HermeticViolation('VELDO HERMETIC FENCE: refused (network) connection to %r' % (address,))
        if sock.family == socket.AF_UNIX and isinstance(address, (str, bytes)):
            path = os.fsdecode(address)
            if any(path == p or path.startswith(p.rstrip('/') + '/') for p in self.protected):
                self._record('keyring', 'connection to %s' % path)
                raise HermeticViolation('VELDO HERMETIC FENCE: refused (keyring) connection to %s' % path)

    def violations(self):
        return [json.loads(line) for line in self.violations_log.read_text().splitlines() if line.strip()]

    @contextlib.contextmanager
    def active(self):
        state = _audit_state()
        saved = {k: os.environ.get(k) for k in ('PATH', 'SSH_AUTH_SOCK')}
        # The fence's own agent: a short path (sun_path is bounded) that records every connection.
        agent_dir = tempfile.mkdtemp(prefix='vfa-')
        agent_path = os.path.join(agent_dir, 'agent')
        agent = socket.socket(socket.AF_UNIX)
        agent.bind(agent_path)
        agent.listen(8)
        stop = threading.Event()

        def serve():
            while not stop.is_set():
                try:
                    peer, _ = agent.accept()
                except OSError:
                    return
                if not stop.is_set():
                    # Name the process that asked, so the fixture that reached for an agent is found.
                    try:
                        pid = __import__('struct').unpack('3i', peer.getsockopt(
                            socket.SOL_SOCKET, socket.SO_PEERCRED, 12))[0]
                        asked = Path('/proc/%d/cmdline' % pid).read_bytes().replace(b'\0', b' ').decode(errors='replace')
                    except OSError:
                        asked = 'unknown process'
                    self._record('keyring', 'the SSH agent was contacted by: ' + asked.strip()[:300])
                peer.close()
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        os.environ['PATH'] = str(self.directory) + os.pathsep + (saved['PATH'] or os.defpath)
        os.environ['SSH_AUTH_SOCK'] = agent_path
        state.stack.append(self)
        clean = False
        try:
            yield self
            clean = True
        finally:
            state.stack.remove(self)
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            stop.set()
            with contextlib.suppress(OSError):
                waker = socket.socket(socket.AF_UNIX)
                waker.connect(agent_path)
                waker.close()
            agent.close()
            thread.join(timeout=5)
            with contextlib.suppress(OSError):
                os.unlink(agent_path)
                os.rmdir(agent_dir)
            found = self.violations()
            if found:
                message = 'VELDO HERMETIC FENCE: %d violation(s): %s' % (len(found), json.dumps(found)[:2000])
                if clean:
                    raise HermeticViolation(message)
                sys.stderr.write(message + '\n')


class Wire(Fence):
    def __init__(self, directory, secrets=None, configs=None):
        values = {'fixture/api': TOKEN}
        values.update(secrets or {})
        super().__init__(directory, values, configs)
        self.map = self.directory / 'remotes.json'
        self.log = self.directory / 'identity-invocations.jsonl'
        self.hook = self.directory / 'before-push.json'
        self.map.write_text('{}')
        self.conf.update(map=str(self.map), log=str(self.log), hook=str(self.hook))
        self._write_conf()

    def remote(self, name, path, owner=OWNER, scheme='https'):
        """Register a bare repository under `owner` and return the URL the factory is given: https for
        an identity whose push credential is a token, ssh for one whose credential is a key."""
        remotes = json.loads(self.map.read_text())
        remotes[url(name, owner, scheme)] = str(path)
        self.map.write_text(json.dumps(remotes))
        return url(name, owner, scheme)

    def before_push(self, argv):
        """Run `argv` before each identity push, its standard input the lines a pre-push hook reads.

        The identity profile disables the clone's hooks (VELDO-0153), so a suite that injects work
        between the listing and the push (another pusher moving the trunk, VELDO-0148) does it here,
        at the process boundary, rather than through a hook the factory no longer runs."""
        self.hook.write_text(json.dumps([str(a) for a in argv]))

    def invocations(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]
