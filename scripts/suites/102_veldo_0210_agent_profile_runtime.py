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

        # ---- credentials: copied in per client, a refresh written back atomically ---------------
        account, codex_home = top / 'account', top / 'codex-home'
        account.mkdir()
        codex_home.mkdir()
        old_token = json.dumps({'claudeAiOauth': {'accessToken': 'old', 'refreshToken': 'r1'}})
        new_token = {'claudeAiOauth': {'accessToken': 'new', 'refreshToken': 'r2'}}
        codex_token = json.dumps({'tokens': {'refresh_token': 'codex-r1'}})
        decoy = top / 'decoy'
        decoy.mkdir()
        (decoy / '.credentials.json').write_text(json.dumps({'forged': True}))
        client_policy = dict(policy, clients=real['clients'])
        client_config = top / 'client-config.json'
        client_config.write_text(json.dumps(client_policy))
        client_env = dict(os.environ, CLAUDE_CONFIG_DIR=str(account), CODEX_HOME=str(codex_home))
        act = worktree / 'act.py'
        # The confined CLI's side: what a token refresh (or a hostile rewrite) does to its copies.
        act.write_text(r'''import json, os, sys
from pathlib import Path
mode, claude, codex = sys.argv[1], Path(os.environ['CLAUDE_CONFIG_DIR']), Path(os.environ['CODEX_HOME'])
credentials = claude / '.credentials.json'
seen = {'claude': credentials.exists(), 'codex': (codex / 'auth.json').exists(),
        'settings': (claude / 'settings.json').exists(), 'state': (claude / '.claude.json').exists(),
        'codex-config': (codex / 'config.toml').exists()}
def rewrite(path, text):
    # The way the CLIs persist a refresh: a new file renamed over the old one.
    temporary = path.with_name(path.name + '.new')
    temporary.write_text(text)
    os.replace(temporary, path)
if mode == 'refresh':
    rewrite(credentials, sys.argv[4])
elif mode == 'invalid':
    rewrite(credentials, '{"claudeAiOauth": ')
elif mode == 'array':
    rewrite(credentials, '[1]')
elif mode == 'file-link':
    credentials.unlink()
    credentials.symlink_to(sys.argv[4])
elif mode == 'directory-link':
    claude.rename(claude.with_name('.claude-moved'))
    claude.symlink_to(sys.argv[4])
elif mode == 'settings':
    rewrite(claude / 'settings.json', '{"forged": true}')
print(json.dumps(seen))
''')

        def account_state():
            path = account / '.credentials.json'
            info = path.stat()
            return path.read_text(), info.st_ino, stat_mode(info)

        def stat_mode(info):
            return info.st_mode & 0o777

        def reset():
            for directory in (account, codex_home):
                for child in directory.iterdir():
                    child.unlink()
            (account / '.credentials.json').write_text(old_token)
            (account / '.credentials.json').chmod(0o600)
            (account / 'settings.json').write_text('{"theme": "auto"}')
            (account / '.claude.json').write_text('{"numStartups": 1}')
            (codex_home / 'auth.json').write_text(codex_token)
            (codex_home / 'config.toml').write_text('model = "fixture"\n')

        def act_run(mode, client='claude', extra=''):
            return run(client_config, worktree, [sys.executable, '-I', '-S', str(act), mode, '', '', extra],
                       client=client, env=client_env)

        reset()
        before = account_state()
        result = act_run('refresh', extra=json.dumps(new_token))
        after = account_state()
        expect('VELDO-0210 credentials/refresh-written-back: ' + result.stderr[-300:],
               result.returncode == 0 and json.loads(after[0]) == new_token
               and 'written back' in result.stderr)
        expect('VELDO-0210 credentials/write-back-is-atomic-replace',
               after[1] != before[1] and after[2] == 0o600
               and sorted(p.name for p in account.iterdir()) == ['.claude.json', '.credentials.json', 'settings.json'])
        seen = results(result)
        expect('VELDO-0210 credentials/claude-run-receives-claude-files',
               seen.get('claude') is True and seen.get('settings') is True and seen.get('state') is True)
        expect('VELDO-0210 credentials/claude-run-has-no-codex-credentials',
               seen.get('codex') is False and seen.get('codex-config') is False)
        result = act_run('unchanged')
        expect('VELDO-0210 credentials/unchanged-left-alone',
               result.returncode == 0 and account_state() == after and 'written back' not in result.stderr)
        for mode, reason in (('invalid', 'not written back'), ('array', 'not a JSON object')):
            reset()
            before = account_state()
            result = act_run(mode)
            expect('VELDO-0210 credentials/%s-not-written-back: %s' % (mode, result.stderr[-200:]),
                   result.returncode == 0 and account_state() == before and reason in result.stderr)
        for mode, target in (('file-link', decoy / '.credentials.json'), ('directory-link', decoy)):
            reset()
            before = account_state()
            result = act_run(mode, extra=str(target))
            expect('VELDO-0210 credentials/%s-not-followed: %s' % (mode, result.stderr[-200:]),
                   account_state() == before and 'not written back' in result.stderr
                   and json.loads((decoy / '.credentials.json').read_text()) == {'forged': True})
        reset()
        result = act_run('settings')
        expect('VELDO-0210 credentials/non-credential-never-written-back',
               result.returncode == 0 and (account / 'settings.json').read_text() == '{"theme": "auto"}')
        reset()
        result = act_run('refresh', client='codex', extra=json.dumps(new_token))
        seen = results(result)
        expect('VELDO-0210 credentials/codex-run-has-no-claude-credentials',
               result.returncode == 0 and seen.get('codex') is True and seen.get('codex-config') is True
               and seen.get('claude') is False and seen.get('settings') is False)
        expect('VELDO-0210 credentials/other-client-source-untouched',
               (account / '.credentials.json').read_text() == old_token
               and (codex_home / 'auth.json').read_text() == codex_token)
        result = run(client_config, worktree, [sys.executable, '-I', '-S', str(act), 'unchanged'],
                     env=client_env)
        seen = results(result)
        expect('VELDO-0210 credentials/no-client-no-credentials',
               result.returncode == 0 and seen.get('claude') is False and seen.get('codex') is False)
        # The sources are never readable in place, even under a read root that holds them.
        reachable = dict(client_policy, read_roots=[*real['read_roots'], str(top / 'account')])
        (top / 'reachable.json').write_text(json.dumps(reachable))
        result = run(top / 'reachable.json', worktree,
                     [sys.executable, '-I', '-S', str(probe), 'deny:source:%s' % (account / '.credentials.json'),
                      'read:settings:%s' % (account / 'settings.json')], client='claude', env=client_env)
        found = results(result)
        expect('VELDO-0210 credentials/source-unreadable-in-place: ' + result.stderr[-200:],
               found.get('source') is True and found.get('settings') is True)
        # Refusals before anything runs.
        marker = worktree / 'must-not-start'
        start = [sys.executable, '-I', '-S', '-c', 'open(%r, "w").close()' % str(marker)]
        refused = run(client_config, worktree, start, client='gemini', env=client_env)
        expect('VELDO-0210 credentials/unknown-client-refused',
               refused.returncode == 2 and 'unknown agent client' in refused.stderr and not marker.exists())
        crossed = json.loads(json.dumps(client_policy))
        crossed['clients']['claude']['credentials'] = {'{home}/.credentials.json': '.codex/auth.json'}
        (top / 'crossed.json').write_text(json.dumps(crossed))
        refused = run(top / 'crossed.json', worktree, start, client='claude', env=client_env)
        expect('VELDO-0210 credentials/cross-client-destination-refused',
               refused.returncode == 2 and 'must lie under .claude' in refused.stderr and not marker.exists())
        guarded = dict(client_policy, deny_write=[str(runner), str(account)])
        (top / 'guarded.json').write_text(json.dumps(guarded))
        refused = run(top / 'guarded.json', worktree, start, client='claude', env=client_env)
        expect('VELDO-0210 credentials/protected-source-refused',
               refused.returncode == 2 and 'protected path' in refused.stderr and not marker.exists())
        gate = subprocess.run([sys.executable, '-I', '-S', str(launcher), '--config', str(client_config),
                               '--profile', 'gate', '--client', 'claude', '--worktree', str(worktree), '--', *start],
                              capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL, env=client_env)
        expect('VELDO-0210 credentials/gate-takes-no-client',
               gate.returncode == 2 and 'takes no agent client' in gate.stderr and not marker.exists())
        defaults = real['seed_files']
        expect('VELDO-0210 credentials/shared-seeds-carry-no-credential',
               set(defaults.values()) == {'.gitconfig'}
               and set(real['clients']['claude']['credentials'].values()) == {'.claude/.credentials.json'}
               and set(real['clients']['codex']['credentials'].values()) == {'.codex/auth.json'})


if leg_runs():
    _v210_agent_profile()
