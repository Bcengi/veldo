"""VELDO-0211: offline token rotation through both borrowed-login integrations."""


def _v211_borrowed_login():
    from contextlib import ExitStack
    import fcntl
    import importlib.util
    import json
    import os
    from pathlib import Path
    import signal
    import stat
    import subprocess
    import sys
    import tempfile
    from types import SimpleNamespace
    from unittest.mock import patch

    spec = importlib.util.spec_from_file_location('v211_live', ROOT / 'proof/VELDO-0127/live.py')
    L = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(L)
    S = L.LOGIN
    expect('VELDO-0211 canonical/sandbox-copies-match',
           (ROOT / 'engine/scripts/agent_sandbox.py').read_bytes() == (ROOT / 'scripts/agent_sandbox.py').read_bytes())
    with tempfile.TemporaryDirectory(prefix='v211-') as temporary:
        top = Path(temporary)
        account = top / 'account'
        account.mkdir(mode=0o700)
        worktree = top / 'worktree'
        worktree.mkdir()
        fake = top / 'engine.py'
        fake.write_text('''import fcntl, json, os, pathlib, sys
source, target, marker = map(pathlib.Path, sys.argv[1:4])
with open(str(source) + '.veldo-lock', 'r') as lock:
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        held = False
    except BlockingIOError:
        held = True
value = json.loads(target.read_text())
key = 'claudeAiOauth' if 'claudeAiOauth' in value else 'tokens'
refresh = 'refreshToken' if key == 'claudeAiOauth' else 'refresh_token'
value[key][refresh] += '-rotated'
fresh = target.with_name('rotated.tmp')
fresh.write_text(json.dumps(value))
os.chmod(fresh, 0o600)
os.replace(fresh, target)
marker.write_text(json.dumps({'locked': held, 'source_old': source.read_text() != target.read_text(),
                             'copied': not target.is_symlink(), 'inode': source.stat().st_ino}))
sys.exit(int(sys.argv[4]))
''')
        marker = top / 'engine-ran'
        originals = {'claude': {'claudeAiOauth': {'accessToken': 'fixture-access', 'refreshToken': 'fixture-old'}},
                     'codex': {'tokens': {'access_token': 'fixture-access', 'refresh_token': 'fixture-old'}}}

        def source_for(engine):
            return account / ('.credentials.json' if engine == 'claude' else 'auth.json')

        def reset(engine):
            source = source_for(engine)
            source.write_text(json.dumps(originals[engine]))
            source.chmod(0o600)
            marker.unlink(missing_ok=True)
            return source

        def token(path, engine):
            data = json.loads(path.read_text())
            return data['claudeAiOauth']['refreshToken'] if engine == 'claude' else data['tokens']['refresh_token']

        def engine_run(engine, target, mode):
            result = subprocess.run([sys.executable, str(fake), str(source_for(engine)), str(target),
                                     str(marker), '7' if mode == 'nonzero' else '0'],
                                    capture_output=True, text=True, timeout=15)
            if result.returncode not in (0, 7):
                raise AssertionError(result.stderr[-300:])
            if mode == 'exception':
                raise RuntimeError('fixture engine failed after rotation')
            if mode == 'signal':
                os.kill(os.getpid(), signal.SIGTERM)
            return result.returncode

        def sandbox(engine, mode, base):
            # Keep real prepared_launch and credential lifecycle; replace only host policy/grants
            # and the process-tree boundary with a foreground fake engine. Suite 102 runs real trees.
            source = source_for(engine)
            relative = '.' + engine + '/' + source.name
            config = {'store': str(top / 'store'), 'seed_files': {}, 'clients': {engine: {
                'credentials': {str(source): relative}}}}
            policy = SimpleNamespace(__file__=str(top / 'policy.py'),
                                     configuration=lambda path: (Path(path), config), private=lambda *a, **k: None)

            def tree(worktree, command, env, *args, after=None, **kwargs):
                try:
                    return engine_run(engine, Path(env['CLAUDE_CONFIG_DIR' if engine == 'claude' else 'CODEX_HOME'])
                                      / source.name, mode)
                finally:
                    if after:
                        after()

            with ExitStack() as stack:
                for name, replacement in [('policy_module', lambda: policy), ('project_roots', lambda c: []),
                                          ('grants_for', lambda *a: ([], [])), ('resolver_grants', lambda: []),
                                          ('toolchain_environment', lambda *a: None), ('run_tree', tree)]:
                    stack.enter_context(patch.object(S, name, replacement))
                return S.prepared_launch(top / 'config.json', worktree, ['fake'], 'agent', base, engine)

        def live(engine, mode, base):
            args = {'claude_profile': str(account), 'codex_profile': str(account)}
            with L.borrowed_profiles(base, args, [engine]):
                return engine_run(engine, base / (engine + '-login') / source_for(engine).name, mode)

        for caller, invoke in [('live', live), ('sandbox', sandbox)]:
            for engine in ('claude', 'codex'):
                for mode in ('success', 'nonzero', 'exception', 'signal'):
                    source = reset(engine)
                    with tempfile.TemporaryDirectory(dir=top) as tmp:
                        base = Path(tmp)
                        error, result = None, None
                        try:
                            # Sandbox's outer launch normally installs Stop; mirror it for this seam.
                            with S.Stop():
                                result = invoke(engine, mode, base)
                        except (RuntimeError, S.Interrupted) as caught:
                            error = caught
                        seen = json.loads(marker.read_text()) if marker.exists() else {}
                        expect('VELDO-0211 rotation/%s/%s/%s' % (caller, engine, mode),
                               token(source, engine) == 'fixture-old-rotated'
                               and seen.get('locked') and seen.get('copied') and seen.get('source_old')
                               and source.stat().st_ino != seen.get('inode')
                               and stat.S_IMODE(source.stat().st_mode) == 0o600
                               and ((mode == 'success' and result == 0)
                                    or (mode == 'nonzero' and result == 7)
                                    or (mode == 'exception' and isinstance(error, RuntimeError))
                                    or (mode == 'signal' and isinstance(error, S.Interrupted))))
                        with open(str(source) + '.veldo-lock') as lock:
                            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)

                for refusal in ('busy', 'preflight'):
                    source = reset(engine)
                    with tempfile.TemporaryDirectory(dir=top) as tmp, ExitStack() as stack:
                        if refusal == 'busy':
                            lock = stack.enter_context(open(str(source) + '.veldo-lock', 'w'))
                            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        else:
                            stack.enter_context(patch.object(S, 'replace_atomically', side_effect=PermissionError('fixture denied')))
                        rejected = False
                        try:
                            invoke(engine, 'success', Path(tmp))
                        except (OSError, ValueError):
                            rejected = True
                        expect('VELDO-0211 refused-before-launch/%s/%s/%s' % (caller, engine, refusal),
                               rejected and not marker.exists() and token(source, engine) == 'fixture-old')

        # Drive the real live command orchestration too: capture and discovery execute our fake
        # engine, while the factory and systemd transport are local fixtures.
        for engine in ('claude', 'codex'):
            for mode in ('success', 'exception', 'signal'):
                source = reset(engine)
                events = []
                factory = SimpleNamespace(src=worktree, slice_name='fixture.slice', inherited={},
                                          connections=[SimpleNamespace(close=lambda: events.append('closed'))],
                                          role=lambda *a: {'instructions': []}, save=lambda *a: None)
                args_seen = {}

                def make_factory(*args, live=None, **kwargs):
                    args_seen.update(live)
                    return factory

                def captured(*args, **kwargs):
                    profile = args_seen['claude_code_profile' if engine == 'claude' else 'codex_profile']
                    engine_run(engine, Path(profile) / source.name, mode)
                    events.append('captured')
                    return {}

                def discovery(binary, profile, evidence):
                    engine_run('claude', Path(profile) / source.name, 'success')
                    events.append('discovery')
                    return {}

                real_load, real_run, real_temp = L.load, subprocess.run, tempfile.TemporaryDirectory

                def load(name, path):
                    if name == 'role_live_evidence':
                        return SimpleNamespace(MODULES=[], production=lambda root: {}, problems=lambda *a: [])
                    if name == 'role_live_factory':
                        return SimpleNamespace(factory=make_factory)
                    return real_load(name, path)

                def run(command, **kwargs):
                    if command[0] != 'systemctl':
                        return real_run(command, **kwargs)
                    with open(str(source) + '.veldo-lock') as held:
                        try:
                            fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            events.append('unlocked-at-teardown')
                        except BlockingIOError:
                            events.append('locked-at-teardown')
                    events.append('stopped')
                    return subprocess.CompletedProcess(command, 0)

                def temporary_directory(*args, **kwargs):
                    kwargs['dir'] = top
                    return real_temp(*args, **kwargs)

                argv = ['live.py']
                for name, value in [('claude', 'fake'), ('codex', 'fake'), ('claude-profile', str(account)),
                                    ('codex-profile', str(account)), ('claude-model', 'fixture'),
                                    ('codex-model', 'fixture'), ('only', engine)]:
                    argv += [L.P + name, value]
                factory.L = SimpleNamespace(HANDOFF=None)
                failure = None
                with ExitStack() as stack:
                    for obj, name, value in [(L, 'load', load), (L, 'capture', captured),
                                             (L, 'discovery_control', discovery), (L, 'HERE', top),
                                             (L, 'codex_model', lambda *a: None),
                                             (subprocess, 'run', run), (tempfile, 'TemporaryDirectory', temporary_directory),
                                             (sys, 'argv', argv)]:
                        stack.enter_context(patch.object(obj, name, value))
                    try:
                        L.main()
                    except (RuntimeError, S.Interrupted) as error:
                        failure = error
                rotations = (5 if engine == 'claude' else 4) if mode == 'success' else 1
                expect('VELDO-0211 live-main/%s/%s' % (engine, mode),
                       token(source, engine) == 'fixture-old' + '-rotated' * rotations
                       and events[-3:] == ['closed', 'locked-at-teardown', 'stopped']
                       and ((mode == 'success' and failure is None)
                            or (mode == 'exception' and isinstance(failure, RuntimeError))
                            or (mode == 'signal' and isinstance(failure, S.Interrupted))))

        # Resolve aliases before choosing the lock, so two profile spellings cannot borrow at once.
        source = reset('claude')
        alias = top / 'alias'
        alias.symlink_to(account, target_is_directory=True)
        with tempfile.TemporaryDirectory(dir=top) as first, tempfile.TemporaryDirectory(dir=top) as second:
            with S.borrowed_credentials(Path(first), [(source, 'login')], top / 'store'):
                rejected = False
                try:
                    with S.borrowed_credentials(Path(second), [(alias / source.name, 'login')], top / 'store'):
                        pass
                except ValueError:
                    rejected = True
                expect('VELDO-0211 locking/canonical-alias-refused', rejected)

        # A real permission denial, without mocks, must prevent the first engine execution.
        for caller, invoke in [('live', live), ('sandbox', sandbox)]:
            source = reset('claude')
            account.chmod(0o500)
            try:
                with tempfile.TemporaryDirectory(dir=top) as tmp:
                    rejected = False
                    try:
                        invoke('claude', 'success', Path(tmp))
                    except PermissionError:
                        rejected = True
                    expect('VELDO-0211 refused-before-launch/%s/read-only-source-directory' % caller,
                           rejected and not marker.exists())
            finally:
                account.chmod(0o700)

        # Retain the rotated token when storage becomes unavailable after the engine was admitted.
        source = reset('claude')
        with tempfile.TemporaryDirectory(dir=top) as tmp:
            base = Path(tmp)
            real_replace = S.replace_atomically

            def late_failure(target, data, expected=None, locked=False):
                if b'fixture-old-rotated' in data:
                    raise PermissionError('fixture storage failure after launch')
                return real_replace(target, data, expected, locked)

            recovery = None
            with patch.object(S, 'replace_atomically', late_failure):
                try:
                    live('claude', 'success', base)
                except S.CredentialRecovery:
                    recovery = base.with_name('veldo-login-recovery-' + base.name)
            expect('VELDO-0211 recovery/live-retains-private-rotated-token',
                   recovery is not None and token(recovery / 'claude-login/.credentials.json', 'claude')
                   == 'fixture-old-rotated' and stat.S_IMODE(recovery.stat().st_mode) == 0o700)
            if recovery:
                S.remove_tree(recovery)

        source = reset('claude')
        real_prepared = S.prepared_launch
        real_mkdtemp = tempfile.mkdtemp
        held_scratch = []

        def mkdtemp(*args, **kwargs):
            kwargs['dir'] = top
            result = real_mkdtemp(*args, **kwargs)
            held_scratch.append(Path(result))
            return result

        def prepared(config_path, tree, command, profile, scratch, client, stop):
            with patch.object(S, 'prepared_launch', real_prepared):
                return sandbox('claude', 'success', scratch)

        recovery = None
        with patch.object(S, 'prepared_launch', prepared), patch.object(S, 'replace_atomically', late_failure), \
                patch.object(tempfile, 'mkdtemp', mkdtemp), patch.object(tempfile, 'gettempdir', lambda: str(top)):
            try:
                S.launch(top / 'config.json', worktree, ['fake'], client='claude')
            except S.CredentialRecovery:
                base = held_scratch[0]
                recovery = base.with_name('veldo-login-recovery-' + base.name)
        expect('VELDO-0211 recovery/sandbox-retains-private-rotated-token',
               recovery is not None and token(recovery / '.claude/.credentials.json', 'claude')
               == 'fixture-old-rotated' and stat.S_IMODE(recovery.stat().st_mode) == 0o700)
        if recovery:
            S.remove_tree(recovery)

        # Missing refresh fields in either supported format must never replace the source.
        for engine in ('claude', 'codex'):
            source = reset(engine)
            with tempfile.TemporaryDirectory(dir=top) as tmp:
                scratch = Path(tmp)
                rejected = False
                try:
                    with S.borrowed_credentials(scratch, [(source, source.name)], top / 'store'):
                        (scratch / source.name).write_text('{}')
                except S.CredentialRecovery:
                    rejected = True
                expect('VELDO-0211 recovery/%s/missing-refresh-token' % engine,
                       rejected and token(source, engine) == 'fixture-old')

        # Executed falsifier: remove the production write-back call and require the same rotation
        # observation to detect the stale original. This is deliberately an in-process mutation,
        # never either repository mutation runner.
        for caller, invoke in [('live', live), ('sandbox', sandbox)]:
            source = reset('claude')
            with tempfile.TemporaryDirectory(dir=top) as tmp, patch.object(S, 'write_back', lambda *a, **k: None):
                invoke('claude', 'success', Path(tmp))
                rotation_passed = token(source, 'claude') == 'fixture-old-rotated'
                expect('VELDO-0211 falsifier/%s/missing-write-back-detected' % caller,
                       marker.exists() and not rotation_passed)


if leg_runs():
    _v211_borrowed_login()
