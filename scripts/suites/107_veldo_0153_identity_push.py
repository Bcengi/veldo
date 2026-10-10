"""VELDO-0153 offline boundaries. Real Git, helper processes and disposable bare refs.

The SSH wire is an explicit test adapter after profile construction, not live authentication.
Real GitHub, SSH agent and Secret Service qualification is proof/VELDO-0153/host_check.py.
"""


def _v153_suite():
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
        key = base / 'identity-key'; key.write_text('fixture identity key')
        token = 'fixture-value-' + os.urandom(16).hex()
        marker = base / 'planted-helper-ran'
        (home / '.gitconfig').write_text('[credential]\n\thelper = !touch ' + str(marker) + '\n')
        system = base / 'system.gitconfig'
        system.write_text('[url "https://github.com/intruder/"]\n\tinsteadOf = https://github.com/alpha/\n')
        secret = tools / 'secret-tool'
        secret.write_text('#!/usr/bin/env python3\nimport sys\nvalues=' + repr({'fixture/token': token, 'fixture/ssh': str(key)})
                          + '\nvalue=values.get(sys.argv[-1])\nif value is None: sys.exit(1)\nsys.stdout.write(value)\n')
        secret.chmod(0o700)
        clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        planted = dict(clean, HOME=str(home), XDG_CONFIG_HOME=str(home), PATH=str(tools) + ':' + os.defpath,
                       GIT_CONFIG_GLOBAL=str(home / '.gitconfig'), GIT_CONFIG_SYSTEM=str(system),
                       GIT_SSH_COMMAND='/bin/false planted', SSH_AUTH_SOCK=str(base / 'other-agent'),
                       GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='credential.helper', GIT_CONFIG_VALUE_0='!false',
                       GIT_TRACE='1', GIT_DIR='/nonexistent/planted')
        records = [dict(id=owner, label=owner, author_name='Fixture', author_email='fixture@example.invalid',
                        remote_host='github.com', remote_owner=owner, api_token='keychain:fixture/token',
                        push_credential={'kind': 'token', 'reference': 'keychain:fixture/token'},
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
            helpers = G.run(['git', '-C', str(repo), 'config', '--get-all', 'credential.helper'],
                            profile='identity', push_identity=record, remote_url=url, capture_output=True, text=True)
            filled = G.run(['git', '-C', str(repo), 'credential', 'fill'], input='protocol=https\nhost=github.com\npath=alpha/repo.git\n\n',
                           profile='identity', push_identity=record, remote_url=url, capture_output=True, text=True)
            row('profile/planted-helper', helpers.returncode == 0 and str(marker) not in helpers.stdout
                and filled.returncode == 0 and 'password=' + token in filled.stdout and not marker.exists())
            routed = G.run(['git', '-C', str(repo), 'ls-remote', '--get-url', url], profile='identity',
                           push_identity=record, remote_url=url, capture_output=True, text=True)
            row('profile/system-rewrite', routed.stdout.strip() == url)
            operator = G.run(['git', '-C', str(repo), 'ls-remote', '--get-url', url], profile='network', capture_output=True, text=True)
            row('profile/network-preserved', operator.stdout.strip() == 'https://github.com/intruder/repo.git'
                and G.clean_env(profile='network')['SSH_AUTH_SOCK'] == planted['SSH_AUTH_SOCK'])
            missing = dict(record, push_credential={'kind': 'token', 'reference': 'keychain:missing'})
            row('profile/credential-unavailable', refusal(lambda: G.run(['git', '-C', str(repo), 'status'], profile='identity',
                push_identity=missing, remote_url=url)) == 'unavailable_service:push_credential')
            git('config', 'credential.https://github.com.helper', '!false')
            row('profile/local-auth-refused', refusal(lambda: G.run(['git', '-C', str(repo), 'status'], profile='identity',
                push_identity=record, remote_url=url)) == 'binding_mismatch:identity_transport_config')
            git('config', '--unset-all', 'credential.https://github.com.helper')

            # Test adapter for the SSH wire. Git still performs real receive-pack publication.
            # It verifies the selected key and isolation, but does not implement SSH cryptography.
            adapter = base / 'ssh-wire'
            wirelog = base / 'wire.jsonl'
            adapter.write_text('#!/usr/bin/env python3\nimport os,sys,json,shlex\n'
                + 'a=sys.argv[1:]\n'
                + 'assert a[a.index("-i")+1] == ' + repr(str(key)) + '\n'
                + 'assert "IdentitiesOnly=yes" in a and "IdentityAgent=none" in a and "BatchMode=yes" in a\n'
                + 'assert "SSH_AUTH_SOCK" not in os.environ and "GIT_SSH_COMMAND" not in os.environ\n'
                + 'command=shlex.split(a[-1])\nassert command[0] in ("git-receive-pack","git-upload-pack")\n'
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

            ssh_records = [dict(r, push_credential={'kind': 'ssh', 'reference': 'keychain:fixture/ssh'}) for r in records]
            conn = sqlite3.connect(base / 'identities.db', isolation_level=None)
            for r in ssh_records:
                I.configure_identities(conn, 'domain', [r], {r['id']: {'path': str(repo) if r['id'] == 'alpha' else str(base / 'beta'), 'identity': r['id']}})
            conn.close()
            conn = sqlite3.connect(base / 'identities.db', isolation_level=None)
            before = lambda: git('rev-parse', 'refs/heads/main', cwd=bare)
            reset = lambda: git('update-ref', 'refs/heads/main', old, cwd=bare)
            with patch.object(subprocess, 'run', wire), patch.object(L, 'verification_organ', lambda: SimpleNamespace(accept=lambda *a, **k: [])):
                for r in ssh_records:
                    url = 'git@github.com:' + r['id'] + '/repo.git'
                    reset()
                    done = G.run(['git', '-C', str(repo), 'push', url, 'HEAD:refs/heads/main'], profile='identity',
                                 push_identity=r, remote_url=url, capture_output=True, text=True)
                    row('profile/direct-push/' + r['id'], done.returncode == 0 and before() == tip)
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
                        if own:
                            row('lander/' + r['id'] + '/observability', ops.identity_counts[r['id']]['pushes'] == 1
                                and any(e['operation'] == 'push' and e['remote_owner'] == destination for e in logs))
                for destination in ('alpha', 'beta', 'third'):
                    reset()
                    contract = dict(kind='publication', target='git', domain_uuid='domain', repository_uuid='alpha',
                                    payload={'commit': tip, 'tree': tree, 'old_tip': old})
                    config = {'store': str(base / 'identities.db'), 'receivers': {'git': dict(kind='publication', repository=str(repo),
                              remote='git@github.com:' + destination + '/repo.git', ref='refs/heads/main')}}
                    accepted = {'dispatch_id': 'dispatch', 'target': 'git', 'request_digest': 'digest'}
                    count = len(invocations)
                    if destination == 'alpha':
                        answer = X.receive(config, contract, accepted)
                        row('executor/own', answer['status'] == 'completed' and before() == tip
                            and answer['evidence']['identity'] == 'alpha')
                    else:
                        row('executor/' + destination, refusal(lambda: X.receive(config, contract, accepted)) == 'binding_mismatch:remote_owner'
                            and before() == old and len(invocations) == count)
                row('profile/ssh-only', bool(invocations) and all('SSH_AUTH_SOCK' not in env and 'GIT_SSH_COMMAND' not in env
                    and env.get('GIT_CONFIG_GLOBAL') == os.devnull for args, env in invocations))
            conn.close()
        scaffold = load('init_scaffold')
        row('install/asset', '.veldo/control_git_identity_transport.py' in scaffold.ASSETS if hasattr(scaffold, 'ASSETS') else
            '".veldo/control_git_identity_transport.py"' in (ROOT / '.veldo/init_scaffold.py').read_text())
        row('install/template-sync', all((ROOT / '.veldo' / n).read_bytes() == (ROOT / 'engine/.veldo' / n).read_bytes()
            for n in ('git_process.py', 'control_git_identity_transport.py', 'lander.py', 'control_effect_executor.py', 'init_scaffold.py')))
        if os.environ.get('VELDO_0153_OBSERVATIONS'):
            Path(os.environ['VELDO_0153_OBSERVATIONS']).write_text(json.dumps(results, indent=2) + '\n')


_v153_suite()
