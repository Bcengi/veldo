"""VELDO-0153 process boundaries and local Git config isolation; no transport starts."""


def _v153_global_config_rows():
    """Observe global isolation independently of the integration fixture's credentials.

    A refusal is a failed isolation assertion, not an uncaught fixture exception.
    Only credential lookup is substituted; Git reads and resolves the actual config.
    """
    import importlib.util
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    from unittest.mock import patch

    with tempfile.TemporaryDirectory(prefix='global153-') as directory:
        base = Path(directory)
        installed = base / 'installed'
        installed.mkdir()
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, installed / source.name)
        # Literal source paths let the mutation worker substitute both real modules.
        shutil.copyfile(ROOT / ".veldo" / "git_process.py", installed / 'git_process.py')
        shutil.copyfile(ROOT / ".veldo" / "control_git_identity_transport.py",
                        installed / 'control_git_identity_transport.py')
        spec = importlib.util.spec_from_file_location('global153', installed / 'git_process.py')
        G = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(G)
        transport = G.identity_transport()
        home, repo = base / 'home', base / 'repo'
        home.mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(HOME=str(home), XDG_CONFIG_HOME=str(home), GIT_CONFIG_NOSYSTEM='1')
        record = dict(id='alpha', remote_host='github.com', remote_owner='alpha',
                      push_credential=dict(kind='token', reference='keychain:fixture/alpha/token'))
        url = 'https://github.com/alpha/repo.git'
        global_config = base / 'global.config'
        global_config.write_text('[url "https://github.com/intruder/"]\n'
                                 '\tinsteadOf = https://github.com/alpha/\n')
        with patch.dict(os.environ, env, clear=True):
            G.run(['/usr/bin/git', 'init', '-q', str(repo)], check=True, capture_output=True)
        args = ['/usr/bin/git', '-C', str(repo), 'ls-remote', '--get-url', url]
        outcomes = {}
        for name, selection in (('unset', {}), ('selected', {'GIT_CONFIG_GLOBAL': str(global_config)})):
            with patch.dict(os.environ, dict(env, **selection), clear=True), \
                 patch.object(transport, 'credential', return_value='fixture-token'):
                plain = subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()
                expect('VELDO-0153 profile/global-config-control/' + name,
                       plain == (url if name == 'unset' else 'https://github.com/intruder/repo.git'))
                try:
                    result = G.run(args, profile='identity', push_identity=record, remote_url=url,
                                   capture_output=True, text=True)
                    isolated = result.returncode == 0 and result.stdout.strip() == url
                    outcomes[name] = 'isolated' if isolated else 'wrong-destination'
                except transport.Refused as error:
                    isolated = False
                    outcomes[name] = error.code
                expect('VELDO-0153 profile/global-config' + ('-unset' if name == 'unset' else ''), isolated)
        import json
        print('VELDO-0153 global config observations: ' + json.dumps(outcomes, sort_keys=True))


def _v153_process_boundary_rows():
    import importlib.util
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    from types import SimpleNamespace
    from unittest.mock import patch

    with tempfile.TemporaryDirectory(prefix='process153-') as directory:
        installed = Path(directory) / 'installed'
        installed.mkdir()
        for source in (ROOT / '.veldo').glob('*.py'):
            shutil.copyfile(source, installed / source.name)
        shutil.copyfile(ROOT / ".veldo" / "control_effect_executor.py", installed / 'control_effect_executor.py')
        shutil.copyfile(ROOT / ".veldo" / "control_git_identity_transport.py",
                        installed / 'control_git_identity_transport.py')
        spec = importlib.util.spec_from_file_location('process153', installed / 'control_effect_executor.py')
        X = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(X)
        contract = dict(kind='publication', target='git', domain_uuid='domain', repository_uuid='alpha',
                        payload=dict(commit='1' * 40, tree='2' * 40, old_tip='0' * 40),
                        dispatch_id='unit-profile', request_digest='unit-digest')
        record = dict(id='alpha', remote_host='github.com', remote_owner='alpha')
        identity = SimpleNamespace(resolve=lambda *a: record, Refused=type('IdentityRefused', (ValueError,), {}))
        organ = X.E.organ
        store = Path(directory) / 'store'
        store.touch()
        config = dict(store=str(store), journal_key='unused-unit-key', receivers={'git': dict(
            kind='publication', repository=directory, remote='https://github.com/alpha/repo.git',
            ref='refs/heads/main')})
        # Observe the real receive path's profile selection without starting transport.
        # A missing identity profile must fail a row, not escape the wire's URL translation.
        operations = []
        def process(args, **kwargs):
            operations.append((args, kwargs))
            if 'rev-parse' in args:
                output = contract['payload']['tree'] + '\n'
            elif 'ls-remote' in args:
                output = (contract['payload']['commit'] + '\trefs/heads/main\n'
                          if any('push' in a for a, _ in operations) else '')
            elif 'push' in args:
                output = ''
            else:
                raise AssertionError('unexpected Git command')
            return subprocess.CompletedProcess(args, 0, output, '')
        with patch.object(X._git_process, 'run', process), \
             patch.object(X.E, 'organ', lambda name: identity if name == 'control_git_identity' else organ(name)), \
             patch.object(X.E.S, 'open_store', lambda *a: SimpleNamespace(close=lambda: None)):
            answer = X.receive(config, contract, contract)
        transports = [(args, kwargs) for args, kwargs in operations if 'rev-parse' not in args]
        expect('VELDO-0153 executor-unit/identity-profile', answer['status'] == 'completed'
               and len(transports) == 3 and all(kwargs['profile'] == 'identity'
                   and kwargs['remote_url'] == config['receivers']['git']['remote']
                   for args, kwargs in transports))
        # Invalid config values still reach this live host guard, with a named refusal.
        transport = X._git_process.identity_transport()
        hosts = {}
        for remote in ('https://elsewhere.invalid/alpha/repo.git', ''):
            try:
                transport.check_remote(record, remote)
                hosts[remote] = 'accepted'
            except transport.Refused as error:
                hosts[remote] = error.code
        expect('VELDO-0153 owner-unit/host', all(value == 'binding_mismatch:remote_host'
               for value in hosts.values()) and transport.check_remote(record,
                   'https://github.com/alpha/repo.git')['owner'] == 'alpha')


_v153_global_config_rows()
_v153_process_boundary_rows()
