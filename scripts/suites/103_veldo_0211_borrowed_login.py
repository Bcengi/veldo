"""VELDO-0211: offline token rotation through both borrowed-login integrations."""


def _v211_borrowed_login():
    from contextlib import ExitStack, contextmanager, redirect_stderr
    import fcntl
    import io
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
    S = L.login()
    expect('VELDO-0211 canonical/sandbox-copies-match',
           (ROOT / 'engine/scripts/agent_sandbox.py').read_bytes() == (ROOT / 'scripts/agent_sandbox.py').read_bytes())
    # Every journal and recovery this suite makes lies under its own temporary directory.
    with tempfile.TemporaryDirectory(prefix='v211-') as temporary, \
            patch.dict(os.environ, {'XDG_STATE_HOME': str(Path(temporary) / 'state')}):
        top = Path(temporary)
        account = top / 'account'
        account.mkdir(mode=0o700)
        # The login's lease file, as a runner's account_lease.sh leaves it in every login it used.
        lease = account / '.runner-lease'
        lease.touch(mode=0o600)
        borrows = S.borrow_root()

        def journals():
            return sorted(p.name for p in borrows.iterdir()) if borrows.is_dir() else []

        def lease_free():
            with open(lease) as other:
                try:
                    fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    return True
                except BlockingIOError:
                    return False

        def account_untouched():
            return set(p.name for p in account.iterdir()) <= {'.runner-lease', '.credentials.json', 'auth.json'}

        @contextmanager
        def held_by_another_run():
            # Another run's runner: a separate process holding the login's lease.
            holder = subprocess.Popen([sys.executable, '-I', '-S', '-c',
                                       'import fcntl, sys, time\n'
                                       'f = open(sys.argv[1])\nfcntl.flock(f, fcntl.LOCK_EX)\n'
                                       'print("held", flush=True)\ntime.sleep(60)', str(lease)],
                                      stdout=subprocess.PIPE, text=True)
            holder.stdout.readline()
            try:
                yield
            finally:
                holder.kill()
                holder.wait()
        worktree = top / 'worktree'
        worktree.mkdir()
        fake = top / 'engine.py'
        fake.write_text('''import fcntl, json, os, pathlib, sys
source, target, marker = map(pathlib.Path, sys.argv[1:4])
with open(source.parent / '.runner-lease', 'r') as lock:
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

        # Reproduce the original symlink failure with the same engine's atomic save.
        source = reset('claude')
        with tempfile.TemporaryDirectory(dir=top) as tmp:
            copied = Path(tmp) / source.name
            copied.symlink_to(source)
            engine_run('claude', copied, 'success')
            expect('VELDO-0211 root-cause/symlink-replacement-strands-original',
                   token(source, 'claude') == 'fixture-old'
                   and token(copied, 'claude') == 'fixture-old-rotated' and not copied.is_symlink())

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
                        # Locked by the login's runner lease during the run (the engine is another
                        # process), released after it, no journal and no file left in the login.
                        expect('VELDO-0211 rotation/%s/%s/%s' % (caller, engine, mode),
                               token(source, engine) == 'fixture-old-rotated'
                               and seen.get('locked') and seen.get('copied') and seen.get('source_old')
                               and source.stat().st_ino != seen.get('inode')
                               and stat.S_IMODE(source.stat().st_mode) == 0o600
                               and lease_free() and journals() == [] and account_untouched()
                               and ((mode == 'success' and result == 0)
                                    or (mode == 'nonzero' and result == 7)
                                    or (mode == 'exception' and isinstance(error, RuntimeError))
                                    or (mode == 'signal' and isinstance(error, S.Interrupted))))

                for refusal in ('busy', 'preflight'):
                    source = reset(engine)
                    before = source.stat()
                    with tempfile.TemporaryDirectory(dir=top) as tmp, ExitStack() as stack:
                        if refusal == 'busy':
                            stack.enter_context(held_by_another_run())
                        else:
                            stack.enter_context(patch.object(S, 'replace_problem', lambda target: 'fixture denied'))
                        rejected = False
                        try:
                            invoke(engine, 'success', Path(tmp))
                        except (OSError, ValueError) as caught:
                            rejected = ('busy' if refusal == 'busy' else 'fixture denied') in str(caught)
                        after = source.stat()
                        expect('VELDO-0211 refused-before-launch/%s/%s/%s' % (caller, engine, refusal),
                               rejected and not marker.exists() and token(source, engine) == 'fixture-old'
                               and (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)
                               and journals() == [])

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
                        return SimpleNamespace(MODULES=[], MARKER_REPETITIONS=1, production=lambda root: {}, problems=lambda *a: [])
                    if name == 'role_live_factory':
                        return SimpleNamespace(factory=make_factory)
                    return real_load(name, path)

                def run(command, **kwargs):
                    if command[0] != 'systemctl':
                        return real_run(command, **kwargs)
                    events.append('unlocked-at-teardown' if lease_free() else 'locked-at-teardown')
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
                       and lease_free() and journals() == []
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
                    except (PermissionError, S.CredentialRecovery):
                        rejected = True
                    expect('VELDO-0211 refused-before-launch/%s/read-only-source-directory' % caller,
                           rejected and not marker.exists())
            finally:
                account.chmod(0o700)

        # A login without a lease file has never been leased by a runner: refused, nothing created.
        for caller, invoke in [('live', live), ('sandbox', sandbox)]:
            source = reset('claude')
            lease.unlink()
            try:
                with tempfile.TemporaryDirectory(dir=top) as tmp:
                    rejected = False
                    try:
                        invoke('claude', 'success', Path(tmp))
                    except ValueError as caught:
                        rejected = 'has no lease file' in str(caught)
                    expect('VELDO-0211 locking/%s/login-without-lease-refused' % caller,
                           rejected and not marker.exists() and not lease.exists() and journals() == [])
            finally:
                lease.touch(mode=0o600)

        # The runner's own lease, inherited by the launcher: checked, never taken twice, never released.
        for caller, invoke in [('live', live), ('sandbox', sandbox)]:
            source = reset('claude')
            with open(lease) as runner, tempfile.TemporaryDirectory(dir=top) as tmp:
                fcntl.flock(runner, fcntl.LOCK_EX)
                result = invoke('claude', 'success', Path(tmp))
                seen = json.loads(marker.read_text()) if marker.exists() else {}
                expect('VELDO-0211 locking/%s/runner-lease-inherited-counts-as-held' % caller,
                       result == 0 and seen.get('locked') and token(source, 'claude') == 'fixture-old-rotated'
                       and not lease_free())
            expect('VELDO-0211 locking/%s/runner-lease-left-to-the-runner' % caller, lease_free())

        # The start-time check probes with a sibling temporary file: the credential is never rewritten.
        source = reset('claude')
        before = source.stat()
        with tempfile.TemporaryDirectory(dir=top) as tmp:
            with S.borrowed_credentials(Path(tmp), [(source, source.name)], top / 'store'):
                during = source.stat()
                siblings = sorted(p.name for p in account.iterdir())
        after = source.stat()
        expect('VELDO-0211 preflight/credential-never-rewritten',
               (before.st_ino, before.st_mtime_ns) == (during.st_ino, during.st_mtime_ns)
               == (after.st_ino, after.st_mtime_ns) and set(siblings) <= {'.credentials.json', '.runner-lease', 'auth.json'})

        # Write-back runs with the stop signals blocked and restores the mask afterwards.
        source = reset('claude')
        masks = []
        real_replace = S.replace_atomically

        def recording(target, data, expected=None):
            masks.append(signal.SIGTERM in signal.pthread_sigmask(signal.SIG_BLOCK, []))
            return real_replace(target, data, expected)

        with tempfile.TemporaryDirectory(dir=top) as tmp, patch.object(S, 'replace_atomically', recording):
            sandbox('claude', 'success', Path(tmp))
        expect('VELDO-0211 write-back/stop-signals-blocked: %s' % masks,
               masks == [True] and signal.SIGTERM not in signal.pthread_sigmask(signal.SIG_BLOCK, [])
               and token(source, 'claude') == 'fixture-old-rotated')

        # A recovery is its own outcome: not a refusal any start handler catches, its own status.
        message = S.recovery_message(S.CredentialRecovery(top / 'kept', ['x'], 7))
        expect('VELDO-0211 exit/recovery-distinct-from-refusal',
               S.RECOVERY_EXIT not in (0, 1, 2)
               and not issubclass(S.CredentialRecovery, (OSError, ValueError, RuntimeError, KeyError, TypeError))
               and 'refused' not in message and 'exit status 7' in message and 'restore-login' in message)

        # Retain the rotated token when storage becomes unavailable after the engine was admitted:
        # privately, on persistent storage (the state directory), never in the run's scratch.
        def late_failure(target, data, expected=None):
            if b'fixture-old-rotated' in data:
                raise PermissionError('fixture storage failure after launch')
            return real_replace(target, data, expected)

        def kept(recovery, engine='claude'):
            try:
                manifest = json.loads((recovery / 'recovery.json').read_text())
                entry = manifest['entries'][0]
                copy = recovery / entry['file']
                token(copy, engine)
            except (OSError, ValueError, KeyError, IndexError, TypeError):
                return False
            return (token(copy, engine) == 'fixture-old-rotated' and entry['source'] == str(source_for(engine))
                    and stat.S_IMODE(recovery.stat().st_mode) == 0o700
                    and stat.S_IMODE(copy.stat().st_mode) == 0o600 and recovery.parent == borrows)

        source = reset('claude')
        with tempfile.TemporaryDirectory(dir=top) as tmp:
            base = Path(tmp)
            recovery = None
            with patch.object(S, 'replace_atomically', late_failure):
                try:
                    live('claude', 'success', base)
                except S.CredentialRecovery as caught:
                    recovery = caught.location
            expect('VELDO-0211 recovery/live-retains-private-rotated-token',
                   recovery is not None and kept(recovery) and not recovery.is_relative_to(base)
                   and token(source, 'claude') == 'fixture-old' and lease_free())

        # The restore command, under the lease: refused while another run holds the login or once the
        # source changed, then restores the kept rotation and removes the recovery.
        if recovery is not None:
            launcher = [sys.executable, '-I', '-S', str(ROOT / 'scripts/agent_sandbox.py'), 'restore-login']
            env = dict(os.environ)
            listed = subprocess.run(launcher, capture_output=True, text=True, env=env, timeout=30)
            with held_by_another_run():
                busy = subprocess.run(launcher + [str(recovery)], capture_output=True, text=True, env=env, timeout=30)
            relogged = json.dumps({'claudeAiOauth': {'accessToken': 'login', 'refreshToken': 'fixture-new-login'}})
            source.write_text(relogged)
            changed = subprocess.run(launcher + [str(recovery)], capture_output=True, text=True, env=env, timeout=30)
            expect('VELDO-0211 restore/refused-while-busy-or-changed: %s %s' % (busy.stderr[-200:], changed.stderr[-200:]),
                   str(recovery) in listed.stdout and busy.returncode == 2 and 'busy' in busy.stderr
                   and changed.returncode == 2 and 'changed since the run started' in changed.stderr
                   and source.read_text() == relogged and kept(recovery))
            source.write_text(json.dumps(originals['claude']))
            restored = subprocess.run(launcher + [str(recovery)], capture_output=True, text=True, env=env, timeout=30)
            expect('VELDO-0211 restore/kept-rotation-restored: %s' % restored.stderr[-200:],
                   restored.returncode == 0 and token(source, 'claude') == 'fixture-old-rotated'
                   and not recovery.exists() and stat.S_IMODE(source.stat().st_mode) == 0o600
                   and account_untouched() and lease_free())
        else:
            expect('VELDO-0211 restore/refused-while-busy-or-changed', False)
            expect('VELDO-0211 restore/kept-rotation-restored', False)

        source = reset('claude')
        real_prepared = S.prepared_launch
        real_mkdtemp = tempfile.mkdtemp
        held_scratch = []
        parent = top / 'tmp-parent'
        parent.mkdir()

        def mkdtemp(*args, **kwargs):
            kwargs['dir'] = parent
            result = real_mkdtemp(*args, **kwargs)
            held_scratch.append(Path(result))
            return result

        def prepared(config_path, tree, command, profile, scratch, client, stop):
            with patch.object(S, 'prepared_launch', real_prepared):
                return sandbox('claude', 'nonzero', scratch)

        def launch_failing(extra=()):
            held_scratch.clear()
            with ExitStack() as stack:
                for name, value in [('prepared_launch', prepared), ('replace_atomically', late_failure), *extra]:
                    stack.enter_context(patch.object(S, name, value))
                stack.enter_context(patch.object(tempfile, 'mkdtemp', mkdtemp))
                stack.enter_context(patch.object(tempfile, 'gettempdir', lambda: str(parent)))
                try:
                    S.launch(top / 'config.json', worktree, ['fake'], client='claude')
                except S.CredentialRecovery as caught:
                    return caught
            return None

        error = launch_failing()
        expect('VELDO-0211 recovery/sandbox-retains-private-rotated-token',
               error is not None and not error.retained and kept(error.location)
               and not held_scratch[0].exists() and token(source, 'claude') == 'fixture-old')
        expect('VELDO-0211 recovery/sandbox-keeps-run-exit-status', error is not None and error.code == 7)
        if error is not None and error.location.exists():
            S.remove_tree(error.location)

        # The recovery store itself failing: the scratch, the only copy, is kept, and so is its
        # journal; the stale sweep leaves it until the next start turns it into a recovery.
        source = reset('claude')
        error = launch_failing([('keep_recovery', lambda *a, **k: (_ for _ in ()).throw(OSError('fixture store failure')))])
        scratch = held_scratch[0] if held_scratch else top / 'missing'
        old = __import__('time').time() - 2 * 24 * 60 * 60
        if scratch.exists():
            os.utime(scratch, (old, old))
        S.remove_stale_scratch(parent)
        swept_early = not scratch.exists()
        report = io.StringIO()
        with redirect_stderr(report):
            S.recover_orphans()
        recovered = borrows / scratch.name
        expect('VELDO-0211 recovery/scratch-kept-when-store-fails: %s' % report.getvalue()[-200:],
               error is not None and error.retained and error.location == scratch and not swept_early
               and token(scratch / '.claude/.credentials.json', 'claude') == 'fixture-old-rotated'
               and (recovered / 'recovery.json').is_file() and kept(recovered)
               and 'CREDENTIAL RECOVERY REQUIRED' in report.getvalue())
        S.remove_stale_scratch(parent)
        expect('VELDO-0211 recovery/scratch-swept-once-recovered', not scratch.exists())
        if recovered.exists():
            S.remove_tree(recovered)

        # A run killed outright (SIGKILL, no write-back): the next start's sweep keeps a rotated copy
        # as a recovery and reports it, drops an unchanged one, and only then may remove the scratch.
        killed = '''import importlib.util, json, os, signal, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('s', sys.argv[1]); S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)
scratch, source = Path(sys.argv[2]), Path(sys.argv[3])
with S.borrowed_credentials(scratch, [(source, '.claude/.credentials.json')], Path(sys.argv[4])):
    if sys.argv[5] == 'rotate':
        copy = scratch / '.claude/.credentials.json'
        value = json.loads(copy.read_text()); value['claudeAiOauth']['refreshToken'] += '-rotated'
        copy.write_text(json.dumps(value))
    os.kill(os.getpid(), signal.SIGKILL)
'''
        for mode in ('rotate', 'unchanged'):
            source = reset('claude')
            scratch = parent / ('veldo-agent-killed-' + mode)
            scratch.mkdir(mode=0o700)
            subprocess.run([sys.executable, '-I', '-S', '-c', killed, str(ROOT / 'scripts/agent_sandbox.py'),
                            str(scratch), str(source), str(top / 'store'), mode], timeout=30)
            pending = S.pending_borrow(scratch.name)
            report = io.StringIO()
            with redirect_stderr(report):
                S.recover_orphans()
            os.utime(scratch, (old, old))
            S.remove_stale_scratch(parent)
            recovered = borrows / scratch.name
            if mode == 'rotate':
                expect('VELDO-0211 sweep/killed-run-rotation-kept-and-reported: %s' % report.getvalue()[-200:],
                       pending and kept(recovered) and 'CREDENTIAL RECOVERY REQUIRED' in report.getvalue()
                       and 'restore-login' in report.getvalue() and not scratch.exists()
                       and token(source, 'claude') == 'fixture-old' and lease_free())
                if recovered.exists():
                    S.remove_tree(recovered)
            else:
                expect('VELDO-0211 sweep/killed-run-unchanged-dropped',
                       pending and not recovered.exists() and report.getvalue() == '' and not scratch.exists())

        # live.py killed outright: its guard stops the slice while still holding the lease, then
        # writes the rotation back, then releases the lease.
        source = reset('claude')
        stop_record = top / 'slice-stopped'
        guarded = '''import importlib.util, json, os, signal, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('live', sys.argv[1]); L = importlib.util.module_from_spec(spec)
spec.loader.exec_module(L)
base = Path(sys.argv[2])
args = {'claude_profile': sys.argv[3], 'codex_profile': sys.argv[3]}
stop = [sys.executable, '-I', '-S', '-c', 'import fcntl, json, sys\\nf = open(sys.argv[1])\\n'
        'try:\\n    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB); held = False\\n'
        'except BlockingIOError:\\n    held = True\\n'
        'open(sys.argv[2], "w").write(json.dumps({"held": held}))', sys.argv[4], sys.argv[5]]
with L.borrowed_profiles(base, args, ['claude']) as borrowed:
    borrowed.guard(stop, dict(os.environ))
    copy = base / 'claude-login/.credentials.json'
    value = json.loads(copy.read_text()); value['claudeAiOauth']['refreshToken'] += '-rotated'
    copy.write_text(json.dumps(value))
    os.kill(os.getpid(), signal.SIGKILL)
'''
        with tempfile.TemporaryDirectory(dir=top) as tmp:
            subprocess.run([sys.executable, '-I', '-S', '-c', guarded, str(ROOT / 'proof/VELDO-0127/live.py'), tmp,
                            str(account), str(lease), str(stop_record)], timeout=30, env=dict(os.environ))
            deadline = __import__('time').time() + 20
            while not lease_free() and __import__('time').time() < deadline:
                __import__('time').sleep(0.05)
            stopped = json.loads(stop_record.read_text()) if stop_record.exists() else {}
            expect('VELDO-0211 live-guard/killed-capture-slice-stopped-under-lease-then-written-back: %s' % stopped,
                   stopped.get('held') is True and token(source, 'claude') == 'fixture-old-rotated'
                   and lease_free() and journals() == [])

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

        for corruption in ('invalid-json', 'array', 'missing-file', 'scratch-link'):
            source = reset('claude')
            with tempfile.TemporaryDirectory(dir=top) as tmp:
                scratch = Path(tmp)
                rejected = False
                try:
                    with S.borrowed_credentials(scratch, [(source, source.name)], top / 'store'):
                        target = scratch / source.name
                        if corruption == 'invalid-json':
                            target.write_text('{')
                        elif corruption == 'array':
                            target.write_text('[]')
                        else:
                            target.unlink()
                            if corruption == 'scratch-link':
                                target.symlink_to(source)
                except S.CredentialRecovery:
                    rejected = True
                expect('VELDO-0211 recovery/%s' % corruption,
                       rejected and token(source, 'claude') == 'fixture-old')

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
