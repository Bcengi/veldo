"""VELDO-0210: the agent profile runs a real builder and keeps today's capabilities."""


def _v210_agent_profile():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys
    import tempfile

    launcher = ROOT / 'scripts/agent_sandbox.py'
    # The real launcher's main() with module constants replaced (fixture resolver paths, a short
    # grace): the code under test is the launcher's own, only its host paths move into the fixture.
    wrapper = '''import importlib.util, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('agent_sandbox', sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
for name, value in json.loads(sys.argv[2]).items():
    setattr(m, name, Path(value) if isinstance(value, str) else value)
sys.argv = [sys.argv[1], *sys.argv[3:]]
sys.exit(m.main())
'''
    spec = importlib.util.spec_from_file_location('v210_sandbox', launcher)
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)

    def run(config, worktree, command, patch=None, client=None, env=None, timeout=60, **kwargs):
        """One launch through the real launcher, stdin /dev/null, output captured."""
        argv = [sys.executable, '-I', '-S', '-c', wrapper, str(launcher), json.dumps(patch or {}),
                '--config', str(config), '--worktree', str(worktree)]
        if client:
            argv += ['--client', client]
        return subprocess.run(argv + ['--', *command], capture_output=True, text=True, timeout=timeout,
                              stdin=subprocess.DEVNULL, env=dict(os.environ if env is None else env),
                              **kwargs)

    def results(result):
        try:
            return json.loads(result.stdout.strip().splitlines()[-1])
        except (IndexError, ValueError):
            return {}

    expect('VELDO-0210 spec/contract', V.check_spec(ROOT / 'specs/VELDO-0210-agent-profile-runtime.md') == 0)
    real = json.loads((ROOT / 'scripts/agent_sandbox.json').read_text())
    with tempfile.TemporaryDirectory(prefix='v210-profile-') as temporary:
        top = Path(temporary)
        worktree, store, runner = top / 'worktree', top / 'store', top / 'runner.sh'
        worktree.mkdir()
        runner.write_text('trusted runner')
        policy = {'schema': 'veldo.agent-sandbox/v1', 'store': str(store), 'read_roots': real['read_roots'],
                  'write_roots': ['{worktree}', '{scratch}'], 'deny_write': [str(runner)], 'seed_files': {}}
        config = top / 'config.json'
        config.write_text(json.dumps(policy))
        probe = worktree / 'probe.py'
        probe.write_text(r'''import errno, json, os, sys
r = {}
def readable(name, path):
    try:
        with open(path, 'rb') as handle:
            handle.read()
        r[name] = True
    except OSError as error:
        r[name] = errno.errorcode.get(error.errno, str(error.errno))
def refused(name, operation):
    try:
        operation()
        r[name] = False
    except OSError as error:
        r[name] = error.errno in (errno.EACCES, errno.EPERM, errno.EXDEV, errno.ELOOP)
for item in sys.argv[1:]:
    kind, name, path = item.split(':', 2)
    if kind == 'read':
        readable(name, path)
    elif kind == 'list':
        refused(name, lambda path=path: os.listdir(path))
    elif kind == 'deny':
        refused(name, lambda path=path: open(path, 'rb').read())
    elif kind == 'write':
        refused(name, lambda path=path: open(path, 'w').write('forged'))
    elif kind == 'make':
        refused(name, lambda path=path: open(path, 'x').write('forged'))
print(json.dumps(r))
''')

        def probe_run(items, **kwargs):
            return run(config, worktree, [sys.executable, '-I', '-S', str(probe), *items], **kwargs)

        # ---- runtime: /proc read only, the resolver file and nothing else under /run -------------
        resolve = top / 'run/systemd/resolve'
        resolve.mkdir(parents=True)
        (resolve / 'stub-resolv.conf').write_text('nameserver 127.0.0.53\n')
        (resolve / 'resolv.conf').write_text('nameserver 192.0.2.1\n')
        (top / 'etc').mkdir()
        (top / 'etc/resolv.conf').symlink_to('../run/systemd/resolve/stub-resolv.conf')
        resolver = {'RESOLVER': str(top / 'etc/resolv.conf'), 'RESOLVER_RUNTIME': str(resolve)}
        result = probe_run(['read:proc-status:/proc/self/status', 'read:proc-mounts:/proc/self/mounts',
                            'write:proc-comm:/proc/self/comm',
                            'deny:launcher-environ:/proc/%d/environ' % os.getpid(),
                            'read:resolver-link:%s' % (top / 'etc/resolv.conf'),
                            'read:resolver-target:%s' % (resolve / 'stub-resolv.conf'),
                            'deny:resolver-sibling:%s' % (resolve / 'resolv.conf'),
                            'list:resolver-directory:%s' % resolve,
                            'list:run-user:/run/user/%d' % os.getuid(),
                            'deny:run-user-bus:/run/user/%d/bus' % os.getuid(),
                            'write:worktree-outside:%s' % (top / 'outside'),
                            'write:runner:%s' % runner, 'write:authority:%s' % launcher,
                            'make:store:%s' % (store / 'planted.json')],
                           patch=resolver)
        found = results(result)
        expect('VELDO-0210 runtime/launcher-starts: ' + result.stderr[-300:], result.returncode == 0)
        for name in ('proc-status', 'proc-mounts', 'resolver-link', 'resolver-target'):
            expect('VELDO-0210 runtime/%s-readable: %s' % (name, found.get(name)), found.get(name) is True)
        for name in ('proc-comm', 'launcher-environ', 'resolver-sibling', 'resolver-directory', 'run-user',
                     'run-user-bus', 'worktree-outside', 'runner', 'authority', 'store'):
            expect('VELDO-0210 runtime/%s-refused: %s' % (name, found.get(name)), found.get(name) is True)
        expect('VELDO-0210 runtime/refusals-left-nothing',
               not (top / 'outside').exists() and runner.read_text() == 'trusted runner'
               and not (store / 'planted.json').exists())
        # A resolver that is a plain file, or a link outside /run/systemd/resolve, adds no grant.
        (top / 'etc/plain.conf').write_text('nameserver 192.0.2.2\n')
        (top / 'etc/elsewhere.conf').symlink_to(top / 'run/systemd/resolv-elsewhere.conf')
        (top / 'run/systemd/resolv-elsewhere.conf').write_text('nameserver 192.0.2.3\n')
        saved = S.RESOLVER, S.RESOLVER_RUNTIME
        try:
            S.RESOLVER_RUNTIME = resolve
            S.RESOLVER = top / 'etc/plain.conf'
            plain = S.resolver_grants()
            S.RESOLVER = top / 'etc/elsewhere.conf'
            elsewhere = S.resolver_grants()
            S.RESOLVER = top / 'etc/resolv.conf'
            linked = S.resolver_grants()
        finally:
            S.RESOLVER, S.RESOLVER_RUNTIME = saved
        expect('VELDO-0210 runtime/resolver-grant-is-one-file',
               plain == [] and elsewhere == [] and linked == [((resolve / 'stub-resolv.conf'), S.READ)])
        host = S.resolver_grants()
        expect('VELDO-0210 runtime/host-resolver-constants',
               S.RESOLVER == Path('/etc/resolv.conf') and S.RESOLVER_RUNTIME == Path('/run/systemd/resolve')
               and len(host) <= 1 and all(access == S.READ and path.is_file()
                                          and S.beneath(path, Path('/run/systemd/resolve').resolve())
                                          for path, access in host))
        # The gate profile does not take the resolver grant: it stays as VELDO-0208 left it.
        source = launcher.read_text()
        expect('VELDO-0210 runtime/resolver-agent-profile-only',
               "    if profile == 'agent':\n        grants += resolver_grants()\n" in source
               and source.count('resolver_grants()') == 2)


if leg_runs():
    _v210_agent_profile()
