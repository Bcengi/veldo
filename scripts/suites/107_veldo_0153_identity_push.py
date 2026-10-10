"""VELDO-0153 offline boundaries. Real Git, helper processes and disposable bare refs.

The SSH wire is an explicit test adapter after profile construction, not live authentication.
Real GitHub, SSH agent and Secret Service qualification is proof/VELDO-0153/host_check.py.
"""


def _v153_fence_rows(W, base):
    """The hermetic fence (support/identity_wire.py) every 0153 and consumer identity fixture runs in:
    each way out is refused, recorded and raised when the fence closes; local work passes."""
    import http.server
    import json
    import os
    import socket
    import subprocess
    import threading

    def denied(call):
        try:
            call()
        except W['HermeticViolation']:
            return True
        return False

    base.mkdir(parents=True)
    bare = base / 'local.git'
    subprocess.run(['/usr/bin/git', 'init', '-q', '--bare', str(bare)], check=True, capture_output=True)
    control = W['Fence'](base / 'control')
    with control.active():
        local = subprocess.run(['git', 'ls-remote', str(bare)], capture_output=True, text=True)
    expect('VELDO-0153 fence/local-passes', local.returncode == 0 and control.violations() == [])
    # A planted "real" global configuration whose credential helper stands for the host's real store.
    home = base / 'real-home'
    home.mkdir()
    marker = base / 'real-store-asked'
    (home / '.gitconfig').write_text('[credential]\n\thelper = !touch %s\n' % marker)

    class Challenge(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(401)
            self.send_header('WWW-Authenticate', 'Basic realm="fixture"')
            self.send_header('Content-Length', '0')
            self.end_headers()

        def log_message(self, *args):
            pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Challenge)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    fence = W['Fence'](base / 'fence', configs=[str(home / '.gitconfig')])
    outcome = {}
    try:
        with fence.active():
            off_host = subprocess.run(['git', 'ls-remote', 'https://github.com/fixture/unregistered.git'],
                                      capture_output=True, text=True, timeout=30)
            outcome['git'] = off_host.returncode == 97 and 'VELDO HERMETIC FENCE' in off_host.stderr
            outcome['socket'] = denied(lambda: socket.create_connection(('192.0.2.1', 9), timeout=1))
            outcome['lookup'] = denied(lambda: socket.getaddrinfo('github.com', 443))
            keyring = os.path.join(os.environ.get('XDG_RUNTIME_DIR') or '/run/user/%d' % os.getuid(), 'keyring', 'control')
            outcome['keyring'] = denied(lambda: socket.socket(socket.AF_UNIX).connect(keyring))
            with socket.socket(socket.AF_UNIX) as agent:
                agent.connect(os.environ['SSH_AUTH_SOCK'])
            asked = subprocess.run(['git', 'ls-remote', 'http://127.0.0.1:%d/fixture.git' % server.server_port],
                                   capture_output=True, text=True, timeout=30,
                                   env=dict(os.environ, HOME=str(home), XDG_CONFIG_HOME=str(home)))
            outcome['credential'] = asked.returncode != 0 and not marker.exists()
        outcome['raised'] = False
    except W['HermeticViolation'] as error:
        outcome['raised'] = 'violation(s)' in str(error)
    finally:
        server.shutdown()
        server.server_close()
    kinds = [v['kind'] for v in fence.violations()]
    expect('VELDO-0153 fence/network-git-refused', outcome.get('git') and 'network' in kinds)
    expect('VELDO-0153 fence/network-socket-refused', outcome.get('socket') and outcome.get('lookup'))
    expect('VELDO-0153 fence/keyring-socket-refused', outcome.get('keyring') and kinds.count('keyring') >= 2)
    expect('VELDO-0153 fence/real-credential-store-refused', outcome.get('credential') and 'credential-store' in kinds)
    expect('VELDO-0153 fence/fails-loudly', outcome.get('raised') is True)
    print('VELDO-0153 fence observations: ' + json.dumps({'outcome': outcome, 'kinds': kinds}, sort_keys=True))


def _v153_suite(fence_dir):
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shlex
    import sqlite3
    import subprocess
    import tempfile
    from types import SimpleNamespace
    from unittest.mock import patch

    def load(name):
        spec = importlib.util.spec_from_file_location('v153_' + name, ROOT / '.veldo' / (name + '.py'))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    G, T, I, L, X = [load(n) for n in ('git_process', 'control_git_identity_transport',
                                       'control_git_identity', 'lander', 'control_effect_executor')]
    results = {}

    def row(name, value):
        results[name] = bool(value)
        expect('VELDO-0153 ' + name, bool(value))

    def refusal(call):
        try:
            call()
        except Exception as error:
            return getattr(error, 'code', type(error).__name__)
        return None

    host_spec = importlib.util.spec_from_file_location('host153', ROOT / 'proof/VELDO-0153/host_check.py')
    host = importlib.util.module_from_spec(host_spec)
    host_spec.loader.exec_module(host)
    row('host/agent-same-user-refused', refusal(lambda: host.require_distinct_agent('alpha', 'ALPHA')) == 'AssertionError')
    row('host/agent-unproven-refused', refusal(lambda: host.require_distinct_agent('alpha', None)) == 'AssertionError')
    row('host/agent-distinct', refusal(lambda: host.require_distinct_agent('alpha', 'beta')) is None)

    with tempfile.TemporaryDirectory(prefix='identity153-') as tmp:
        base = Path(tmp)
        repo, bare, home, tools = [base / n for n in ('repo', 'remote.git', 'home', 'tools')]
        for path in (repo, home, tools):
            path.mkdir()
        original_run = subprocess.run

        def git(*args, cwd=repo):
            done = G.run(['git', '-C', str(cwd), *args], capture_output=True, text=True,
                         identity=('Fixture', 'fixture@example.invalid'))
            if done.returncode:
                raise RuntimeError('fixture git failed: ' + args[0])
            return done.stdout.strip()

        git('init', '-q', '-b', 'main')
        git('commit', '--allow-empty', '-qm', 'initial')
        old = git('rev-parse', 'HEAD')
        git('init', '--bare', '-q', str(bare))
        git('push', '-q', str(bare), 'HEAD:refs/heads/main')
        git('commit', '--allow-empty', '-qm', 'candidate')
        tip, tree = git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')
        keys = {owner: base / (owner + '-key') for owner in ('alpha', 'beta')}
        for owner, path in keys.items():
            path.write_text('fixture key for ' + owner)
        tokens = {owner: 'fixture-value-' + os.urandom(16).hex() for owner in keys}
        token = tokens['alpha']
        marker = base / 'planted-helper-ran'
        (home / '.gitconfig').write_text('[credential]\n\thelper = !touch ' + str(marker) + '\n'
            + '[url "https://github.com/intruder/"]\n\tinsteadOf = https://github.com/alpha/\n')
        system = base / 'system.gitconfig'
        system.write_text('[url "https://github.com/intruder/"]\n\tinsteadOf = https://github.com/alpha/\n')
        secret = tools / 'secret-tool'
        secret.write_text('#!/usr/bin/env python3\nimport sys\nvalues=' + repr({**{'fixture/' + owner + '/token': value for owner, value in tokens.items()}, **{'fixture/' + owner + '/ssh': str(value) for owner, value in keys.items()}})
                          + '\nvalue=values.get(sys.argv[-1])\nif value is None: sys.exit(1)\nsys.stdout.write(value)\n')
        secret.chmod(0o700)
        clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        # The fence's Git stand-in stays on PATH behind the suite's own tools.
        planted = dict(clean, HOME=str(home), XDG_CONFIG_HOME=str(home), PATH=str(tools) + ':' + str(fence_dir) + ':' + os.defpath,
                       GIT_CONFIG_GLOBAL=str(home / '.gitconfig'), GIT_CONFIG_SYSTEM=str(system),
                       GIT_SSH_COMMAND='/bin/false planted', SSH_AUTH_SOCK=str(base / 'other-agent'),
                       GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='credential.helper', GIT_CONFIG_VALUE_0='!false',
                       GIT_TRACE='1', GIT_DIR='/nonexistent/planted')
        records = [dict(id=owner, label=owner, author_name='Fixture', author_email='fixture@example.invalid',
                        remote_host='github.com', remote_owner=owner, api_token='keychain:fixture/' + owner + '/token',
                        push_credential={'kind': 'token', 'reference': 'keychain:fixture/' + owner + '/token'},
                        projects_root=str(base), default_visibility='private') for owner in ('alpha', 'beta')]
        events = []
        for record in records:
            owner = record['remote_owner']
            own = 'https://github.com/' + owner + '/repo.git'
            for operation in ('push', 'remote_creation', 'adoption'):
                accepted = T.check_remote(record, own, operation=operation, repository='repo', request='dispatch', observe=events.append)
                row('owner/' + owner + '/' + operation + '/own', accepted['owner'] == owner)
                for other in ({'alpha', 'beta', 'third'} - {owner}):
                    row('owner/' + owner + '/' + operation + '/' + other,
                        refusal(lambda: T.check_remote(record, 'https://github.com/' + other + '/repo.git',
                            operation=operation, repository='repo', request='dispatch', observe=events.append)) == 'binding_mismatch:remote_owner')
        row('owner/observability', len(events) == 18 and all(e['repository'] == 'repo' and e['request'] == 'dispatch' and e['identity'] for e in events))
        for url in ('file:///repo', '/repo', 'https://evil.invalid/alpha/repo', 'https://user:password@github.com/alpha/repo',
                    'https://github.com/alpha%2fthird/repo', 'https://github.com/alpha/../repo', 'https://github.com/alpha/repo?token=x'):
            row('owner/invalid/' + str(len(results)), refusal(lambda: T.check_remote(records[0], url)) is not None)
        row('owner/unbound', refusal(lambda: T.check_remote(None, 'https://github.com/alpha/repo')) == 'missing_authority:repository_identity')
        row('owner/scp-and-case', T.check_remote(records[0], 'git@github.com:Alpha/repo.git')['owner'] == 'Alpha')

        with patch.dict(os.environ, planted, clear=True):
            record = records[0]
            url = 'https://github.com/alpha/repo.git'
            env = G.clean_env(profile='identity')
            row('profile/environment', 'SSH_AUTH_SOCK' not in env and 'GIT_SSH_COMMAND' not in env
                and 'GIT_DIR' not in env and 'GIT_CONFIG_COUNT' not in env and 'GIT_TRACE' not in env
                and env['GIT_CONFIG_GLOBAL'] == os.devnull and env['GIT_CONFIG_SYSTEM'] == os.devnull)
            try:
                global_routed = G.run(['git', '-C', str(repo), 'ls-remote', '--get-url', url], profile='identity',
                    push_identity=record, remote_url=url, capture_output=True, text=True)
                global_isolated = global_routed.returncode == 0 and global_routed.stdout.strip() == url
            except ValueError:
                global_isolated = False
            row('profile/global-config', global_isolated)
            helpers = G.run(['git', '-C', str(repo), 'config', '--get-all', 'credential.helper'],
                            profile='identity', push_identity=record, remote_url=url, capture_output=True, text=True)
            filled = G.run(['git', '-C', str(repo), 'credential', 'fill'], input='protocol=https\nhost=github.com\npath=alpha/repo.git\n\n',
                           profile='identity', push_identity=record, remote_url=url, capture_output=True, text=True)
            output_homes = []
            def output_wire(args, **kwargs):
                if args and args[0] in ('git', '/usr/bin/git'):
                    output_homes.append(kwargs['env']['HOME'])
                return original_run(args, **kwargs)
            with patch.object(subprocess, 'run', output_wire):
                username = G.check_output(['git', '-C', str(repo), 'config', '--get', 'credential.username'],
                    profile='identity', push_identity=record, remote_url=url, text=True).strip()
            output_home = output_homes[-1]
            row('profile/check-output-home', username == 'x-access-token' and output_home != str(home)
                and not Path(output_home).exists())
            row('profile/planted-helper', helpers.returncode == 0 and str(marker) not in helpers.stdout
                and filled.returncode == 0 and 'password=' + token in filled.stdout and not marker.exists())
            beta_filled = G.run(['git', '-C', str(repo), 'credential', 'fill'], input='protocol=https\nhost=github.com\npath=beta/repo.git\n\n',
                profile='identity', push_identity=records[1], remote_url='https://github.com/beta/repo.git', capture_output=True, text=True)
            row('profile/distinct-tokens', beta_filled.returncode == 0 and 'password=' + tokens['beta'] in beta_filled.stdout
                and token not in beta_filled.stdout and tokens['beta'] not in filled.stdout)
            routed = G.run(['git', '-C', str(repo), 'ls-remote', '--get-url', url], profile='identity',
                           push_identity=record, remote_url=url, capture_output=True, text=True)
            row('profile/system-rewrite', routed.stdout.strip() == url)
            operator = G.run(['git', '-C', str(repo), 'ls-remote', '--get-url', url], profile='network', capture_output=True, text=True)
            row('profile/network-preserved', operator.stdout.strip() == 'https://github.com/intruder/repo.git'
                and G.clean_env(profile='network')['SSH_AUTH_SOCK'] == planted['SSH_AUTH_SOCK'])
            operator_push = G.run(['git', '-C', str(repo), 'push', str(bare), 'HEAD:refs/heads/operator'],
                                  profile='network', capture_output=True, text=True)
            row('profile/network-push', operator_push.returncode == 0 and git('rev-parse', 'refs/heads/operator', cwd=bare) == tip)
            missing = dict(record, push_credential={'kind': 'token', 'reference': 'keychain:missing'})
            row('profile/credential-unavailable', refusal(lambda: G.run(['git', '-C', str(repo), 'status'], profile='identity',
                push_identity=missing, remote_url=url)) == 'unavailable_service:push_credential')
            git('config', 'credential.https://github.com.helper', '!false')
            row('profile/local-auth-refused', refusal(lambda: G.run(['git', '-C', str(repo), 'status'], profile='identity',
                push_identity=record, remote_url=url)) == 'binding_mismatch:identity_transport_config')
            git('config', '--unset-all', 'credential.https://github.com.helper')
            included = base / 'included.config'
            included.write_text('[url "https://github.com/third/"]\n\tinsteadOf = https://github.com/alpha/\n')
            for name, key in (('include', 'include.path'),
                              ('include-if', 'includeIf.gitdir:' + str(repo / '.git') + '.path')):
                git('config', key, str(included))
                row('profile/' + name, refusal(lambda: G.run(['git', '-C', str(repo), 'ls-remote', '--get-url', url],
                    profile='identity', push_identity=record, remote_url=url, capture_output=True)) == 'binding_mismatch:identity_transport_config')
                git('config', '--unset-all', key)
            git('config', 'extensions.worktreeConfig', 'true')
            git('config', '--worktree', 'http.extraHeader', 'Authorization: planted')
            row('profile/worktree-config', refusal(lambda: G.run(['git', '-C', str(repo), 'status'],
                profile='identity', push_identity=record, remote_url=url, capture_output=True)) == 'binding_mismatch:identity_transport_config')
            git('config', '--worktree', '--unset-all', 'http.extraHeader')
            git('config', '--unset-all', 'extensions.worktreeConfig')
            for field in ('url', 'pushurl'):
                key = 'remote.' + url + '.' + field
                git('config', key, 'https://github.com/third/repo.git')
                row('profile/url-section-' + field, refusal(lambda: G.run(['git', '-C', str(repo), 'ls-remote', '--get-url', url],
                    profile='identity', push_identity=record, remote_url=url, capture_output=True)) == 'binding_mismatch:identity_transport_config')
                git('config', '--unset-all', key)
            git('config', 'remote.' + url + '.receivepack', '/bin/false planted')
            row('profile/url-section-other', refusal(lambda: G.run(['git', '-C', str(repo), 'ls-remote', '--get-url', url],
                profile='identity', push_identity=record, remote_url=url, capture_output=True)) == 'binding_mismatch:identity_transport_config')
            git('config', '--remove-section', 'remote.' + url)
            # A remote of another name is never read for a literal URL, so it is no override: a clone that
            # publishes to two receivers, or keeps an upstream, pushes to each by its own URL.
            git('config', 'remote.upstream.url', 'https://github.com/third/repo.git')
            try:
                kept = G.run(['git', '-C', str(repo), 'ls-remote', '--get-url', url], profile='identity',
                             push_identity=record, remote_url=url, capture_output=True, text=True)
            except Exception:  # a refusal is this row's failure, not the suite's end
                kept = None
            row('profile/other-remote-kept', kept is not None and kept.returncode == 0 and kept.stdout.strip() == url)
            git('config', '--remove-section', 'remote.upstream')
            git('config', 'remote.origin.url', url)
            git('config', 'remote.origin.pushurl', url)
            def no_wire(args, **kwargs):
                if 'push' in args:
                    return subprocess.CompletedProcess(args, 0, b'', b'')
                return original_run(args, **kwargs)
            with patch.object(subprocess, 'run', no_wire):
                row('profile/literal-destination', refusal(lambda: G.run(['git', '-C', str(repo), 'push', 'origin', 'HEAD'],
                    profile='identity', push_identity=record, remote_url=url, capture_output=True)) == 'binding_mismatch:identity_destination')
            git('config', '--remove-section', 'remote.origin')

            # A loopback HTTP adapter observes libcurl's actual authentication choice.
            # Git and curl run unchanged; only the endpoint and fixture helper are substituted.
            import base64
            import http.server
            import threading
            auth = []
            class Handler(http.server.BaseHTTPRequestHandler):
                def do_GET(self):
                    value = self.headers.get('Authorization')
                    auth.append(value)
                    if value is None:
                        self.send_response(401)
                        self.send_header('WWW-Authenticate', 'Basic realm="fixture"')
                        self.end_headers()
                    else:
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/x-git-upload-pack-advertisement')
                        self.end_headers()
                        self.wfile.write(b'001e# service=git-upload-pack\n00000000')
                def log_message(self, *args):
                    pass
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            (home / '.netrc').write_text('machine 127.0.0.1 login planted password planted\n')
            (home / '.netrc').chmod(0o600)
            observed_homes = []
            def http_wire(args, **kwargs):
                args = list(args)
                if 'ls-remote' in args:
                    observed_homes.append(kwargs['env']['HOME'])
                    row('profile/private-home-live', kwargs['env']['HOME'] == kwargs['env']['XDG_CONFIG_HOME']
                        and Path(kwargs['env']['HOME']).stat().st_mode & 0o777 == 0o700)
                    args[args.index(url)] = 'http://127.0.0.1:' + str(server.server_port) + '/alpha/repo.git'
                    for i, value in enumerate(args):
                        if value.startswith('credential.helper=!'):
                            args[i] = "credential.helper=!printf 'username=identity\npassword=fixture\n'"
                return original_run(args, **kwargs)
            try:
                with patch.object(subprocess, 'run', http_wire):
                    G.run(['git', '-C', str(repo), 'ls-remote', url], profile='identity',
                          push_identity=record, remote_url=url, capture_output=True, text=True)
                row('profile/netrc', auth and auth[-1] == 'Basic ' + base64.b64encode(b'identity:fixture').decode()
                    and 'Basic ' + base64.b64encode(b'planted:planted').decode() not in auth)
                row('profile/private-home-cleaned', observed_homes and all(not Path(h).exists() and h != output_home for h in observed_homes))
            finally:
                server.shutdown(); server.server_close(); thread.join()


            # Test adapter for the SSH wire. Git still performs real receive-pack publication.
            # It verifies the selected key and isolation, but does not implement SSH cryptography.
            adapter = base / 'ssh-wire'
            wirelog = base / 'wire.jsonl'
            adapter.write_text('#!/usr/bin/env python3\nimport os,sys,json,shlex\n'
                + 'a=sys.argv[1:]\n'
                + 'keys=' + repr({owner: str(value) for owner, value in keys.items()}) + '\n'
                + 'assert "IdentitiesOnly=yes" in a and "IdentityAgent=none" in a and "BatchMode=yes" in a\n'
                + 'assert "SSH_AUTH_SOCK" not in os.environ and "GIT_SSH_COMMAND" not in os.environ\n'
                + 'command=shlex.split(a[-1])\nassert a[a.index("-i")+1] == keys[command[1].split("/")[0].casefold()]\nassert command[0] in ("git-receive-pack","git-upload-pack")\n'
                + 'with open(' + repr(str(wirelog)) + ',"a") as f: f.write(json.dumps(a)+"\\n")\n'
                + 'os.execv("/usr/bin/"+command[0],[command[0],' + repr(str(bare)) + '])\n')
            adapter.chmod(0o700)
            invocations = []

            def wire(args, **kwargs):
                args = list(args)
                if args and args[0] in ('git', '/usr/bin/git'):
                    for index, arg in enumerate(args):
                        if arg.startswith('core.sshCommand='):
                            invocations.append((list(args), dict(kwargs.get('env', {}))))
                            args[index] = arg.replace('/usr/bin/ssh', shlex.quote(str(adapter)), 1)
                return original_run(args, **kwargs)

            ssh_records = [dict(r, push_credential={'kind': 'ssh', 'reference': 'keychain:fixture/' + r['id'] + '/ssh'}) for r in records]
            conn = X.E.S.open_store(base / 'identities.db')
            for r in ssh_records:
                I.configure_identities(conn, 'domain', [r], {r['id']: {'path': str(repo) if r['id'] == 'alpha' else str(base / 'beta'), 'identity': r['id']}})
            conn.close()
            conn = X.E.S.open_store(base / 'identities.db')
            before = lambda: git('rev-parse', 'refs/heads/main', cwd=bare)
            reset = lambda: git('update-ref', 'refs/heads/main', old, cwd=bare)
            with patch.object(subprocess, 'run', wire), patch.object(L, 'verification_organ', lambda: SimpleNamespace(accept=lambda *a, **k: [])):
                planted_hook = repo / '.git/hooks/pre-push'
                hook_marker = base / 'pre-push-ran'
                planted_hook.write_text('#!/bin/sh\ntouch ' + str(hook_marker) + '\n')
                planted_hook.chmod(0o700)
                for r in ssh_records:
                    url = 'git@github.com:' + r['id'] + '/repo.git'
                    reset()
                    git('config', '--remove-section', 'remote.origin') if G.run(['git', '-C', str(repo), 'config', '--get', 'remote.origin.url'], capture_output=True).returncode == 0 else None
                    done = G.run(['git', '-C', str(repo), 'push', url, 'HEAD:refs/heads/main'], profile='identity',
                                 push_identity=r, remote_url=url, capture_output=True, text=True)
                    row('profile/direct-push/' + r['id'], done.returncode == 0 and before() == tip)
                    row('profile/pre-push-hook/' + r['id'], not hook_marker.exists())
                    for destination in ('alpha', 'beta', 'third'):
                        reset()
                        git('config', 'remote.origin.url', 'git@github.com:' + destination + '/repo.git')
                        logs = []
                        # Both repository records resolve explicitly; each has its own registered path.
                        ops = L.GitLandOps(repo if r['id'] == 'alpha' else base / 'beta', 'HEAD', domain='domain', repository=r['id'],
                            identity_conn=conn, policy=lambda *a: {'ok': True}, observe=logs.append)
                        if r['id'] == 'beta':
                            (base / 'beta').mkdir(exist_ok=True)
                            if not (base / 'beta' / '.git').exists():
                                git('init', '-q', cwd=base / 'beta')
                            git('config', 'remote.origin.url', 'git@github.com:' + destination + '/repo.git', cwd=base / 'beta')
                        ops.candidate = dict(id='candidate', state='verified', workspace=str(repo), commit=tip, tree=tree, watermark=old, gate={})
                        count = len(invocations)
                        landed = ops.finalize({'id': 'unit'})
                        own = destination == r['id']
                        row('lander/' + r['id'] + '/' + destination,
                            landed['ok'] and before() == tip if own else
                            landed.get('refusal') == 'binding_mismatch:remote_owner' and before() == old and len(invocations) == count)
                        if not own:
                            restarted = L.GitLandOps(ops.repo_root, 'HEAD', domain='domain', repository=r['id'])
                            row('lander/' + r['id'] + '/' + destination + '/refusals-durable',
                                restarted.status()['identities'].get(r['id'], {}).get('refusals', {}).get('binding_mismatch:remote_owner', 0) > 0)
                            row('lander/' + r['id'] + '/' + destination + '/observed-owner',
                                any(e['operation'] == 'push' and e.get('remote_owner') == destination for e in logs))
                        if own:
                            restarted = L.GitLandOps(ops.repo_root, 'HEAD', domain='domain', repository=r['id'])
                            row('lander/' + r['id'] + '/durable', restarted.status()['identities'].get(r['id'], {}).get('pushes') == 1)
                            row('lander/' + r['id'] + '/observability', ops.identity_counts[r['id']]['pushes'] == 1
                                and any(e['operation'] == 'push' and e['remote_owner'] == destination for e in logs))
                reset()
                git('config', 'remote.origin.url', 'git@github.com:Alpha/repo.git')
                logs = []
                ops = L.GitLandOps(repo, 'HEAD', domain='domain', repository='alpha', identity_conn=conn,
                                   policy=lambda *a: {'ok': True}, observe=logs.append)
                ops.candidate = dict(id='case-owner', state='verified', workspace=str(repo), commit=tip, tree=tree, watermark=old, gate={})
                case_result = ops.finalize({'id': 'unit'})
                row('lander/owner-spelling', case_result.get('ok') and any(
                    e['operation'] == 'push' and e.get('remote_owner') == 'Alpha' for e in logs))
                git('config', 'remote.origin.url', 'git@github.com:alpha/repo.git')
                for destination in ('alpha', 'beta', 'third'):
                    reset()
                    contract = dict(kind='publication', target='git', domain_uuid='domain', repository_uuid='alpha',
                                    payload={'commit': tip, 'tree': tree, 'old_tip': old})
                    config = {'store': str(base / 'identities.db'), '_identity_events': [], 'receivers': {'git': dict(kind='publication', repository=str(repo),
                              remote='git@github.com:' + destination + '/repo.git', ref='refs/heads/main')}}
                    accepted = {'dispatch_id': 'dispatch', 'target': 'git', 'request_digest': 'digest'}
                    count = len(invocations)
                    if destination == 'alpha':
                        answer = X.receive(config, contract, accepted)
                        row('executor/own', answer['status'] == 'completed' and before() == tip
                            and answer['evidence']['identity'] == 'alpha')
                        S = X.E.S
                        signed = []
                        T.record_operations(conn, config['_identity_events'], ('fixture', lambda data: signed.append(data) or 'fixture-signature'))
                        row('executor/signed-observations', len(signed) == 1
                            and conn.execute("SELECT count(*) FROM journal").fetchone()[0] > 0
                            and not conn.execute("SELECT 1 FROM sqlite_master WHERE name='git_identity_operations'").fetchone())
                        reopened = X.E.S.open_store(base / 'identities.db')
                        row('executor/durable', T.metrics(reopened)['alpha']['pushes'] == 1)
                        reopened.close()
                        row('executor/observability', T.metrics(conn)['alpha']['pushes'] == 1
                            and all(e['repository'] == 'alpha' and e['request'] == 'dispatch'
                                    and e['remote_owner'] == 'alpha' for e in config['_identity_events']))
                    else:
                        row('executor/' + destination, refusal(lambda: X.receive(config, contract, accepted)) == 'binding_mismatch:remote_owner'
                            and before() == old and len(invocations) == count)
                reset()
                config['receivers']['git']['remote'] = 'git@github.com:alpha/repo.git'
                signed_execute = []
                with patch.object(X.E, 'authenticate', lambda *a: None), \
                     patch.object(X.E, 'accept', lambda *a: (dict(contract, **accepted), True)), \
                     patch.object(X.E, 'finish', lambda conn, accepted, observation, journal: observation), \
                     patch.object(X.E.SIG, 'sign_bytes', lambda key, data, ns: signed_execute.append(data) or 'fixture-signature'):
                    executed = X.execute(dict(config, journal_key='fixture'), {'operation': 'execute'}, 'fixture', 'challenge', 'signature')
                    config['receivers']['git']['remote'] = 'git@github.com:third/repo.git'
                    refused_execute = X.execute(dict(config, journal_key='fixture'), {'operation': 'execute'}, 'fixture', 'challenge', 'signature')
                    config['receivers']['git']['remote'] = 'git@github.com:alpha/repo.git'
                row('executor/execute-signed', executed.get('accepted') and len(signed_execute) == 2
                    and T.metrics(conn)['alpha']['pushes'] == 2)
                row('executor/refused-signed', refused_execute.get('refusal') == 'binding_mismatch:remote_owner'
                    and T.metrics(conn)['alpha']['refusals'].get('binding_mismatch:remote_owner') == 1)
                reset()
                missing_contract = dict(contract, repository_uuid='unbound')
                count = len(invocations)
                row('executor/unbound', refusal(lambda: X.receive(config, missing_contract, accepted)) == 'missing_authority:repository_identity'
                    and before() == old and len(invocations) == count)
                git('config', 'remote.origin.url', 'git@github.com:alpha/repo.git')
                def alpha_lander(reader):
                    instance = L.GitLandOps(repo, 'HEAD', domain='domain', repository='alpha', identity_conn=reader,
                                           policy=lambda *a: {'ok': True})
                    instance.candidate = dict(id='candidate', state='verified', workspace=str(repo), commit=tip, tree=tree, watermark=old, gate={})
                    return instance
                synced = alpha_lander(conn)
                synced.candidate = None
                count_before_read = len(invocations)
                sync_result = synced.sync_main()
                row('lander/watermark-identity', sync_result.get('ok') and len(invocations) > count_before_read
                    and synced.candidate['watermark'] == old)
                synced.discard()
                B = load('control_landing')
                landing = B.Landing.__new__(B.Landing)
                landing.conn, landing.domain, landing.repository = conn, 'domain', 'alpha'
                landing.clone, landing.remote, landing.ref = str(repo), 'origin', 'refs/heads/main'
                count_before_read = len(invocations)
                row('landing/list-identity', landing._remote_tip() == old and len(invocations) > count_before_read)
                row('lander/unbound', alpha_lander(None).finalize({'id': 'unit'}).get('refusal') == 'missing_authority:repository_identity')
                count = len(invocations)
                key_bytes = keys['alpha'].read_bytes()
                keys['alpha'].unlink()
                try:
                    answer = alpha_lander(conn).finalize({'id': 'unit'})
                    row('lander/credential-unavailable', answer.get('refusal') == 'unavailable_service:push_credential'
                        and before() == old and len(invocations) == count)
                finally:
                    keys['alpha'].write_bytes(key_bytes)
                hook = bare / 'hooks/pre-receive'
                hook.write_text('#!/bin/sh\nexit 1\n'); hook.chmod(0o700)
                # The remote's refusal is named in the identity observation; the effect stays unknown, as
                # every receiver refusal does (VELDO-0028), and is never reported as a landed push.
                config['_identity_events'] = []
                try:
                    rejected = X.receive(config, contract, accepted)
                except Exception as error:  # a refusal raised is this row's failure, not the suite's end
                    rejected = {'status': 'refused', 'refusal': getattr(error, 'code', None), 'evidence': None}
                row('executor/remote-refused', rejected['status'] == 'unknown' and rejected['evidence'] is None
                    and before() == old and [(e['operation'], e['outcome'], e.get('refusal')) for e in config['_identity_events']
                                             if e['operation'] == 'push'] == [('push', 'refused', 'push_refused:remote')])
                # A push the remote refused, through the lander: named push_refused:remote, and its
                # error class is an unknown outcome, never a settled class or a landed push.
                refused_land = alpha_lander(conn).finalize({'id': 'unit'})
                row('lander/push-refused-unknown', refused_land.get('ok') is False
                    and refused_land.get('refusal') == 'push_refused:remote'
                    and L.taxonomy(refused_land.get('refusal')) == 'unknown_outcome'
                    and L.taxonomy('push_refused') == 'unknown_outcome' and before() == old)
                # The push's own report stays in the result beside the identity event (VELDO-0056).
                row('lander/push-detail', 'pre-receive hook declined' in (refused_land.get('detail') or ''))
                hook.unlink()
                row('profile/no-token-on-command-line', all(token not in str(args) and token not in str(env) for args, env in invocations))
                row('profile/ssh-only', bool(invocations) and all('SSH_AUTH_SOCK' not in env and 'GIT_SSH_COMMAND' not in env
                    and env.get('GIT_CONFIG_GLOBAL') == os.devnull for args, env in invocations))
            conn.close()
        scaffold = load('init_scaffold')
        row('install/asset', '.veldo/control_git_identity_transport.py' in scaffold.ASSETS if hasattr(scaffold, 'ASSETS') else
            '".veldo/control_git_identity_transport.py"' in (ROOT / '.veldo/init_scaffold.py').read_text())
        row('install/template-sync', all((ROOT / '.veldo' / n).read_bytes() == (ROOT / 'engine/.veldo' / n).read_bytes()
            for n in ('git_process.py', 'control_git_identity_transport.py', 'lander.py', 'control_landing.py', 'control_effect_executor.py', 'init_scaffold.py')))
        if os.environ.get('VELDO_0153_OBSERVATIONS'):
            Path(os.environ['VELDO_0153_OBSERVATIONS']).write_text(json.dumps(results, indent=2) + '\n')


def _v153_hermetic():
    """The suite runs inside the hermetic fence: nothing it starts reaches the network or a real
    keyring or credential store, and a fixture that would is a loud failure when the fence closes."""
    import runpy
    import tempfile
    from pathlib import Path
    W = runpy.run_path(str(ROOT / 'scripts/suites/support/identity_wire.py'))
    with tempfile.TemporaryDirectory(prefix='fence153-') as tmp:
        _v153_fence_rows(W, Path(tmp) / 'proof')
        fence = W['Fence'](Path(tmp) / 'fence')
        with fence.active():
            _v153_suite(fence.directory)


_v153_hermetic()
