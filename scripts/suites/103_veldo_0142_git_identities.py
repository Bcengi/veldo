"""VELDO-0142: two explicit identities, real stores, clones and landed Git objects.

Only ROOT and expect are shared. The gate and policy are controlled acceptance seams:
this suite proves commit authorship, and never invokes a repository gate or a provider.
Every remote is a disposable local bare repository. No account credential is resolved.
"""


def _v142_suite():
    import contextlib
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import tempfile
    from types import SimpleNamespace
    from unittest.mock import patch

    PRODUCTION = {
        'control_git_identity.py': ROOT / ".veldo" / "control_git_identity.py",
        'control_clone.py': ROOT / ".veldo" / "control_clone.py",
        'control_launch.py': ROOT / '.veldo' / 'control_launch.py',
        'control_factory_setup.py': ROOT / ".veldo" / "control_factory_setup.py",
        'lander.py': ROOT / ".veldo" / "lander.py",
    }

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    observations, facts = {}, {'worker_commits': [], 'landed_commits': []}

    def check(name, condition):
        observations[name] = bool(condition)
        expect('VELDO-0142 ' + name, bool(condition))

    @contextlib.contextmanager
    def row(name):
        try:
            yield
        except Exception as error:
            print('VELDO-0142 diagnostic', name, type(error).__name__, str(error)[:300])
            check(name, False)

    def refusal(call):
        try:
            call()
        except Exception as error:
            return getattr(error, 'code', type(error).__name__)
        return None

    # Clones correctly refuse a protected root under /tmp. Use this checkout's scratch.
    scratch = ROOT / '.veldo' / 'tmp'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='identity142-', dir=scratch) as temporary:
        base = Path(temporary)
        mods = base / 'installed'
        mods.mkdir()
        for source in (ROOT / '.veldo').iterdir():
            if source.is_file():
                shutil.copyfile(source, mods / source.name)
        shutil.copytree(ROOT / '.veldo/runtime', mods / 'runtime')
        shutil.copytree(ROOT / '.veldo/services', mods / 'services')
        for name, source in PRODUCTION.items():
            shutil.copyfile(source, mods / name)
        GI = load('identity142_records', mods / 'control_git_identity.py')
        F = load('identity142_setup', mods / 'control_factory_setup.py')
        CL = load('identity142_clone', mods / 'control_clone.py')
        L = load('identity142_launch', mods / 'control_launch.py')
        LD = load('identity142_lander', mods / 'lander.py')
        S = load('identity142_store', mods / 'control_store.py')
        GP = load('identity142_git', mods / 'git_process.py')
        state = base / 'store'
        state.mkdir()
        conn = S.open_store(str(state / 'control.sqlite3'))
        domain = 'factory-142'
        identities = [dict(id=identity, label=label, author_name=label + ' Author',
                           author_email=identity + '@example.invalid', remote_host='github.com',
                           remote_owner=identity, api_token='keychain:fixture/' + identity,
                           push_credential=dict(kind=kind, reference='keychain:fixture/' + identity + '/' + kind),
                           projects_root=str(base / identity), default_visibility=visibility)
                      for identity, label, kind, visibility in (
                          ('bcengi', 'Work', 'token', 'private'), ('personal', 'Personal', 'ssh', 'public'))]
        events = []
        repos = {}
        outsider = ('Ambient Caller', 'ambient@example.invalid')

        def git(repo, *args, identity=outsider, environment=None):
            result = GP.run(['git', '-C', str(repo), *args], identity=identity, env=environment,
                            capture_output=True, text=True, timeout=20)
            if result.returncode:
                raise AssertionError('fixture git failed: ' + result.stderr[:250])
            return result.stdout.strip()

        def authors(repo, commit='HEAD'):
            return git(repo, 'show', '-s', '--format=%an%n%ae%n%cn%n%ce', commit).splitlines()

        for record in identities:
            repo = base / record['id']
            repo.mkdir()
            git(repo, 'init', '-q', '-b', 'main')
            git(repo, 'config', 'user.name', outsider[0])
            git(repo, 'config', 'user.email', outsider[1])
            (repo / 'base').write_text('base\n')
            (repo / 'scripts').mkdir()
            (repo / 'specs').mkdir()
            (repo / 'scripts/update_index.py').write_text(
                'from pathlib import Path\n'
                'Path("specs/index.md").write_text("projected:" + " ".join(sorted(p.name for p in Path(".").glob("unit*"))) + "\\n")\n')
            (repo / 'specs/index.md').write_text('initial\n')
            git(repo, 'add', '.')
            git(repo, 'commit', '-qm', 'fixture base')
            repos[record['id']] = repo
        GI.configure(conn, domain, identities, {key: dict(path=str(value), identity=key) for key, value in repos.items()})
        S.bind_repositories(conn, domain, {key: str(value) for key, value in repos.items()})

        with row('setup/full-command-and-rerun'):
            import io
            engines = load('identity142_engines', ROOT / 'proof/VELDO-0186/fixtures.py').install(ROOT, base, mods)
            TS = load('identity142_tailscale', ROOT / 'scripts/suites/support/v171_tailscale.py')
            tailscale = TS.stand_in(ROOT / 'proof/VELDO-0171/tailscale-capture.json', __import__('sys').executable)
            service = load('identity142_service', mods / 'control_service.py')
            service.C.qualify = lambda profile: {'qualified': True, 'refusal': None}
            original_organ = F.organ
            setup_temp = tempfile.TemporaryDirectory(prefix='f142-')
            root, person = Path(setup_temp.name), base / 'person'
            person.mkdir(mode=0o700)
            key, token = person / 'owner', person / 'token'
            F._keygen(str(key), 'identity fixture owner')
            F._private(str(token), 'fixture-value-' + os.urandom(16).hex())
            config_file = person / 'identities.json'
            config_file.write_text(json.dumps(identities))
            units = base / 'units'

            class Manager:
                def run(self, args):
                    if args[0] == 'show':
                        return 0, ('LoadState=loaded\nActiveState=inactive\nMainPID=0\nFragmentPath='
                                   + str(units / args[-1]) + '\n'), ''
                    return 0, '', ''

            options = dict(host_trust=str(base / 'trust/host.json'), install_root=str(base / 'factory-install'),
                           unit_dir=str(units), profile={}, writable=[], runner=Manager(),
                           tailscale=[tailscale.path], api_port=TS.free_port())
            argv = ['setup', '--state-root', str(root), '--owner', 'owner', '--owner-key', str(key),
                    '--workspace', str(repos['bcengi']), '--chat', '12345', '--token-file', str(token)]
            try:
                with patch.object(F, 'organ', side_effect=lambda name: service if name == 'control_service' else original_organ(name)), \
                        patch.dict(os.environ, PATH=str(engines['path']) + os.pathsep + os.environ.get('PATH', '')):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        refused = F.main(argv, **options)
                    assert refused == 1 and not list(root.iterdir()), output.getvalue()
                    assert json.loads(output.getvalue())['reason'] == 'missing_authority:git_identities', output.getvalue()
                    argv += ['--git-identities', str(config_file), '--workspace-identity', 'bcengi']
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        code = F.main(argv, **options)
                    report = json.loads(output.getvalue())
                    assert code == 0, (report.get('reason'), report.get('detail'))
                    reader = S.open_store(report['store'], mode='r')
                    try:
                        actual = GI.records(reader, report['authority_ids']['domain_uuid'])
                        bound = GI.repository_record(reader, report['authority_ids']['domain_uuid'],
                                                     report['authority_ids']['repository_uuid'])
                    finally:
                        reader.close()
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        replay = F.main(argv, **options)
                    assert replay == 0, output.getvalue()
                    check('setup/full-command-and-rerun', actual == identities and bound['identity'] == 'bcengi')
                    check('setup/configured-log', {e.get('identity') for e in report['steps']
                          if e.get('step') == 'git_identity_configured' and e.get('outcome') == 'accepted'}
                          == {'bcengi', 'personal'})
                    # Model an existing VELDO-0139 store with repository paths but no identity metadata.
                    writer = S.open_store(report['store'])
                    writer.execute('DROP TABLE git_identity_repositories')
                    writer.execute('DROP TABLE git_identities')
                    writer.close()
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        rebound = F.main(argv, **options)
                    assert rebound == 0, output.getvalue()
                    upgraded = json.loads(output.getvalue())
                    reader = S.open_store(report['store'], mode='r')
                    check('setup/existing-store-adds-binding', GI.records(reader, report['authority_ids']['domain_uuid']) == identities
                          and GI.resolve(reader, report['authority_ids']['domain_uuid'],
                                         report['authority_ids']['repository_uuid'], repos['bcengi']) == identities[0]
                          and any(e['step'] == 'git_identities' and e['outcome'] == 'done' for e in upgraded['steps']))
                    before = list(reader.iterdump())
                    reader.close()
                    added = dict(identities[1], id='extra', label='Extra')
                    config_file.write_text(json.dumps(identities + [added]))
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        code = F.main(argv, **options)
                    assert code == 0, output.getvalue()
                    reader = S.open_store(report['store'], mode='r')
                    check('setup/rerun-adds-identity', GI.records(reader, report['authority_ids']['domain_uuid'])
                          == sorted(identities + [added], key=lambda r: r['id'])
                          and GI.resolve(reader, report['authority_ids']['domain_uuid'],
                                         report['authority_ids']['repository_uuid']) == identities[0])
                    unchanged = list(reader.iterdump())
                    reader.close()
                    added['author_name'] = 'Changed Extra'
                    config_file.write_text(json.dumps(identities + [added]))
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        code = F.main(argv, **options)
                    reader = S.open_store(report['store'], mode='r')
                    check('setup/rerun-change-refused', code == 1
                          and json.loads(output.getvalue())['reason'] == 'binding_mismatch:git_identity_change'
                          and unchanged == list(reader.iterdump()))
                    reader.close()
            finally:
                tailscale.close()
                setup_temp.cleanup()

        with row('setup/two-identities-and-replay'):
            first = F.setup_identities(conn, domain, 'bcengi', repos['bcengi'], identities, 'bcengi', observe=events.append)
            F.setup_identities(conn, domain, 'personal', repos['personal'], identities, 'personal', observe=events.append)
            before = list(conn.iterdump())
            repeated = F.setup_identities(conn, domain, 'bcengi', repos['bcengi'], identities, 'bcengi',
                                          check_only=True, observe=events.append)
            check('setup/two-identities-and-replay', first == repeated == identities
                  and before == list(conn.iterdump()) and len(GI.records(conn, domain)) == 2
                  and all(GI.repository_record(conn, domain, r['id'])['identity'] == r['id'] for r in identities)
                  and {e.get('identity') for e in events} == {'bcengi', 'personal'})
            facts['setup_identities'] = first

        for label, choice, expected in (
                ('missing', None, 'missing_authority:repository_identity'),
                ('second', ['bcengi', 'personal'], 'invalid_input:second_repository_identity'),
                ('immutable', 'personal', 'binding_mismatch:repository_identity_change')):
            with row('binding/' + label):
                before = list(conn.iterdump())
                code = refusal(lambda: GI.configure(conn, domain, identities,
                               {'bcengi': dict(path=str(repos['bcengi']), identity=choice)}))
                check('binding/' + label, code == expected and list(conn.iterdump()) == before)

        with row('setup/reference-only-and-unchanged'):
            before = list(conn.iterdump())
            altered = json.loads(json.dumps(identities))
            altered[0]['author_name'] = 'Replacement'
            changed = refusal(lambda: F.setup_identities(conn, domain, 'bcengi', repos['bcengi'], altered,
                                                        'bcengi', check_only=True))
            altered[0]['api_token'] = 'literal-value'
            literal = refusal(lambda: F.setup_identities(conn, domain, 'bcengi', repos['bcengi'], altered, 'bcengi'))
            check('setup/reference-only-and-unchanged', changed == 'binding_mismatch:git_identity_change'
                  and literal == 'invalid_input:git_identity' and before == list(conn.iterdump()))

        with row('binding/store-and-callers-missing'):
            AL = load('identity142_alias', mods / 'control_alias.py')
            RS = load('identity142_readset', mods / 'control_readset.py')
            before = list(conn.iterdump())
            missing = {'bcengi': str(repos['bcengi']), 'unbound': str(repos['personal'])}
            codes = [refusal(call) for call in (
                lambda: S.bind_repositories(conn, domain, missing),
                lambda: AL.attach(S, conn, domain, missing),
                lambda: RS.attach_revisions(S, conn, domain, missing))]
            check('binding/store-and-callers-missing', codes == ['missing_authority:repository_identity'] * 3
                  and before == list(conn.iterdump()))

        with row('setup/keychain-reference-pattern'):
            check('setup/keychain-reference-pattern', all(GI.reference(v) for v in ('keychain:a', 'keychain:a/b.c-d_0'))
                  and not any(GI.reference(v) for v in ('keychain: a', 'keychain:a b', 'keychain:/a', 'keychain:a@b')))

        polluted = dict(os.environ)
        global_config = base / 'global.gitconfig'
        global_config.write_text(''.join('[' + role + ']\n name = Global Stranger\n email = global@example.invalid\n'
                                          for role in ('user', 'author', 'committer')))
        polluted['GIT_CONFIG_GLOBAL'] = str(global_config)
        for prefix in ('GIT_AUTHOR_', 'GIT_COMMITTER_'):
            for key, value in (('NAME', 'Environment Stranger'), ('EMAIL', 'env@example.invalid'),
                               ('DATE', '2000-01-01T00:00:00Z'), ('FUTURE_OVERRIDE', 'stranger')):
                polluted[prefix + key] = value

        with row('launch/no-author-overrides'):
            normal = L.engine_environment(dict(polluted))
            injected = dict(polluted)
            injected[L.ENGINE_RUNTIME] = str(base / 'runtime')
            injected[L.ENGINE_OVERRIDES] = json.dumps({'GIT_AUTHOR_NAME': 'Adapter Stranger', 'KEEP': 'yes'})
            stripped = L.engine_environment(injected)
            check('launch/no-author-overrides', all(not k.startswith(('GIT_AUTHOR_', 'GIT_COMMITTER_'))
                                                     for k in list(normal) + list(stripped))
                  and stripped['KEEP'] == 'yes')

        injections = [
            {'GIT_CONFIG_COUNT': '4', **{'GIT_CONFIG_KEY_' + str(i): key for i, key in enumerate(
                ('author.name', 'author.email', 'committer.name', 'committer.email'))},
             **{'GIT_CONFIG_VALUE_' + str(i): value for i, value in enumerate(
                ('Injected Stranger', 'inject@example.invalid', 'Injected Stranger', 'inject@example.invalid'))}},
            {'GIT_CONFIG_PARAMETERS': "'author.name=Param Stranger' 'author.email=param@example.invalid' "
                                      "'committer.name=Param Stranger' 'committer.email=param@example.invalid'"}]
        with row('launch/no-config-overrides'):
            environments = []
            for injection in injections:
                environments.append(L.engine_environment(dict(polluted, **injection)))
                environments.append(L.engine_environment(dict(polluted, **{
                    L.ENGINE_RUNTIME: str(base / 'runtime'),
                    L.ENGINE_OVERRIDES: json.dumps(dict(injection, KEEP='yes'))}, **injection)))
            check('launch/no-config-overrides', all(GI.environment(env) == env for env in environments)
                  and all(env['KEEP'] == 'yes' for env in environments[1::2]))

        dispatches = SimpleNamespace(store=S, conn=conn, domain=domain)
        clones = CL.Clones(dispatches, clones=base / 'clones', caches=base / 'caches')
        with row('clone/identity-authors'):
            dispatches = SimpleNamespace(store=S, conn=conn, domain=domain)
            clones = CL.Clones(dispatches, clones=base / 'clones', caches=base / 'caches')
            seen = []
            for record in identities:
                repo = repos[record['id']]
                contract = dict(domain=domain, repository=record['id'], dispatch_id='worker/' + record['id'],
                                unit='VELDO-0142', source=dict(commit=git(repo, 'rev-parse', 'HEAD'),
                                                             tree=git(repo, 'rev-parse', 'HEAD^{tree}')))
                with patch.dict(os.environ, polluted, clear=True):
                    handle = clones._create(contract)
                # Find through the dispatch contract, as the worker entrance does.
                manifest, _user = CL.find(clones.clones, contract['dispatch_id'])
                work = Path(manifest['work'])
                environment = L.engine_environment(dict(polluted))
                # A real engine tool runs Git in the provisioned clone with the receiver's environment.
                done = subprocess.run(['git', '-C', str(work), 'commit', '--allow-empty', '-qm', 'worker tool'],
                                      env=environment, capture_output=True, text=True, timeout=20)
                expected = list(GI.author(record)) * 2
                assert done.returncode == 0, done.stderr
                assert authors(work) == expected, ('author comparison', authors(work), expected)
                local = [git(work, 'config', '--local', '--get', key) for key in ('user.name', 'user.email')]
                seen.append(done.returncode == 0 and local == expected[:2] and authors(work) == expected
                            and manifest['identity'] == record['id'])
                facts['worker_commits'].append(dict(identity=record['id'], commit=git(work, 'rev-parse', 'HEAD'),
                                                     authors=authors(work)))
            check('clone/identity-authors', seen == [True, True])

        with row('launch/spawn-config-commit-authors'):
            seen = []
            for record in identities:
                manifest, _ = CL.find(clones.clones, 'worker/' + record['id'])
                work = Path(manifest['work'])
                for injection in injections:
                    for bound in (False, True):
                        for transport in ('local', 'reported'):
                            receiver = object.__new__(L.Receiver)
                            receiver.login = None
                            receiver.binding = (dict(argv=['git', '-C', str(work), 'commit', '--allow-empty', '-qm', 'spawn worker'],
                                environment=dict(injection, **{L.ENGINE_RUNTIME: str(base / 'runtime'),
                                    L.ENGINE_OVERRIDES: json.dumps(injection)}), path='fixture', sha256='fixture')
                                if bound else None)
                            receiver._resolve_credentials = lambda adapter: None
                            receiver._baseline = lambda dispatch, argv, env, reported: (argv, env)
                            receiver._record = lambda adapter, env: None
                            receiver._contained = lambda dispatch, argv, env: subprocess.Popen(argv,
                                env=L.engine_environment(env), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            adapter = dict(argv=['git', '-C', str(work), 'commit', '--allow-empty', '-qm', 'spawn worker'],
                                           environment=injection, identity=transport)
                            with patch.dict(os.environ, dict(polluted, **injection), clear=True):
                                process = receiver._spawn('spawn/' + record['id'], None, adapter)
                                out, err = process.communicate(timeout=20)
                            seen.append(process.returncode == 0 and authors(work) == list(GI.author(record)) * 2)
            check('launch/spawn-config-commit-authors', len(seen) == 16 and all(seen))

        with row('clone/unbound-refused'):
            contract = dict(domain=domain, repository='unbound', dispatch_id='unbound-worker', unit='VELDO-0142',
                            source=dict(commit=git(repos['bcengi'], 'rev-parse', 'HEAD'),
                                        tree=git(repos['bcengi'], 'rev-parse', 'HEAD^{tree}')))
            # A legacy store path has no identity, as on an upgrade before setup is rerun.
            conn.execute('INSERT INTO repository_bindings VALUES (?,?,?)', (domain, 'unbound', str(repos['bcengi'])))
            before = sorted(str(p) for p in clones.clones.iterdir())
            code = refusal(lambda: clones._create(contract))
            check('clone/unbound-refused', code == 'missing_authority:repository_identity'
                  and before == sorted(str(p) for p in clones.clones.iterdir()))

        with row('lander/identity-and-reland-authors'):
            seen = []
            for record in identities:
                repo = repos[record['id']]
                remote = base / (record['id'] + '.git')
                git(base, 'init', '-q', '--bare', str(remote))
                git(repo, 'remote', 'add', 'origin', str(remote))
                git(repo, 'push', '-q', 'origin', 'main')
                for index in (1, 2):
                    sid = 'VELDO-%04d' % (9000 + index)
                    git(repo, 'checkout', '-q', '-B', 'build' + str(index), 'main')
                    (repo / ('unit' + str(index))).write_text('implementation\n')
                    git(repo, 'add', '.')
                    git(repo, 'commit', '-qm', 'implementation', identity=GI.author(record))
                    implementation = git(repo, 'rev-parse', 'HEAD')
                    proof = repo / 'proof' / sid
                    proof.mkdir(parents=True)
                    (proof / 'manifest.json').write_text(json.dumps({'commit': implementation}))
                    git(repo, 'add', '.')
                    git(repo, 'commit', '-qm', 'evidence', identity=GI.author(record))
                    evidence = git(repo, 'rev-parse', 'HEAD')

                    def candidate():
                        ops = LD.GitLandOps(repo, evidence, domain=domain, repository=record['id'],
                                            identity_conn=conn,
                                            policy=lambda *_: {'ok': True}, observe=events.append)
                        assert ops.sync_main()['ok']
                        assert ops.reconcile({'spec': sid})['ok']
                        return ops

                    with patch.dict(os.environ, polluted, clear=True):
                        ops = candidate()
                        if index == 2:
                            # Another push moves trunk after construction; refuse the old lease,
                            # then construct the re-land on its new watermark with the same evidence.
                            git(repo, 'fetch', '-q', 'origin', 'main')
                            git(repo, 'checkout', '-q', '-B', 'colleague', 'FETCH_HEAD')
                            (repo / 'colleague').write_text('moved\n')
                            git(repo, 'add', '.')
                            git(repo, 'commit', '-qm', 'colleague push')
                            git(repo, 'push', '-q', 'origin', 'HEAD:main')
                            old_watermark = ops.record()['watermark']
                            ops.candidate['state'] = 'verified'
                            with patch.object(LD, 'verification_organ', return_value=SimpleNamespace(accept=lambda *a, **k: [])):
                                assert not ops.finalize({'spec': sid})['pushed']
                            ops.discard()
                            ops = candidate()
                            assert ops.record()['watermark'] != old_watermark
                        candidate_record = ops.record()
                        created = [entry['merge'] for entry in candidate_record['merges']]
                        created.append(candidate_record['projection_commit'])
                        assert len(created) == 3 and all(created)
                        ops.candidate['state'] = 'verified'
                        with patch.object(LD, 'verification_organ', return_value=SimpleNamespace(accept=lambda *a, **k: [])):
                            assert ops.finalize({'spec': sid})['pushed']
                        expected = list(GI.author(record)) * 2
                        seen.extend(authors(remote, commit) == expected for commit in created)
                        facts['landed_commits'].extend(dict(identity=record['id'], reland=index == 2,
                                                           commit=commit, authors=authors(remote, commit))
                                                       for commit in created)
                        assert ops.status()['identities'][record['id']]['commits'] == 3
                        ops.discard()
            check('lander/identity-and-reland-authors', len(seen) == 12 and all(seen)
                  and {e.get('identity') for e in events if e['operation'] == 'reconcile'} == {'bcengi', 'personal'})

        with row('lander/worker-commit-mismatch'):
            repo = repos['bcengi']
            expected = GI.author(identities[0])
            results = []
            # Both roles and both author fields, including a hidden implementation ancestor.
            for bad_role, bad_field in (('implementation', 'author'), ('implementation', 'committer'),
                                       ('evidence', 'author'), ('evidence', 'committer'), ('ancestor', 'author')):
                git(repo, 'fetch', '-q', 'origin', 'main')
                git(repo, 'checkout', '-q', '-B', 'bad-worker', 'FETCH_HEAD')
                sid = 'VELDO-9999'
                def commit(message, bad=False):
                    env = {}
                    if bad:
                        prefix = 'GIT_AUTHOR_' if bad_field == 'author' else 'GIT_COMMITTER_'
                        env = {prefix + 'NAME': outsider[0], prefix + 'EMAIL': outsider[1]}
                    environment = dict(os.environ, GIT_AUTHOR_NAME=expected[0], GIT_AUTHOR_EMAIL=expected[1],
                                       GIT_COMMITTER_NAME=expected[0], GIT_COMMITTER_EMAIL=expected[1])
                    environment.update(env)
                    result = subprocess.run(['git', '-C', str(repo), 'commit', '--allow-empty', '-qm', message],
                                            env=environment, capture_output=True, text=True, timeout=20)
                    assert result.returncode == 0, result.stderr
                    return git(repo, 'rev-parse', 'HEAD')
                if bad_role == 'ancestor':
                    commit('hidden wrong ancestor', True)
                implementation = commit('implementation', bad_role == 'implementation')
                proof = repo / 'proof' / sid
                proof.mkdir(parents=True, exist_ok=True)
                (proof / 'manifest.json').write_text(json.dumps({'commit': implementation}))
                git(repo, 'add', '.')
                evidence = commit('evidence', bad_role == 'evidence')
                ops = LD.GitLandOps(repo, evidence, domain=domain, repository='bcengi', identity_conn=conn)
                assert ops.sync_main()['ok']
                watermark = ops.record()['watermark']
                result = ops.reconcile({'spec': sid})
                results.append(result.get('refusal') == 'binding_mismatch:worker_commit_identity'
                               and git(ops.record()['workspace'], 'rev-parse', 'HEAD') == watermark
                               and not ops.record()['merges'])
                ops.discard()
            check('lander/worker-commit-mismatch', results == [True] * 5)

        with row('lander/caller-identity-refused'):
            ops = LD.GitLandOps(repos['bcengi'], 'HEAD', push=False, identity=outsider,
                                identity_conn=conn, domain=domain, repository='bcengi')
            result = ops.sync_main()
            check('lander/caller-identity-refused', result.get('refusal') == 'invalid_input:caller_git_identity'
                  and ops.record()['workspace'] is None)

        with row('lander/unbound-before-commit'):
            ops = LD.GitLandOps(repos['bcengi'], 'HEAD', push=False,
                                identity_conn=conn, domain=domain, repository='unbound')
            result = ops.sync_main()
            check('lander/unbound-before-commit', result.get('refusal') == 'missing_authority:repository_identity'
                  and ops.record()['workspace'] is None)
        conn.close()
    if os.environ.get('VELDO_0142_OBSERVATIONS'):
        Path(os.environ['VELDO_0142_OBSERVATIONS']).write_text(json.dumps(dict(rows=observations, facts=facts), indent=2) + '\n')


_v142_suite()
