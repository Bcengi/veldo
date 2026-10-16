"""VELDO-0124 Linux logic rows. Apple interface fixtures are not native qualification."""


def _v124_suite():
    import copy
    import importlib.util
    import math
    import os
    from pathlib import Path
    import signal
    import tempfile

    spec = importlib.util.spec_from_file_location('v124_checks', ROOT / 'proof/VELDO-0124/checks.py')
    T = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(T)
    M, P = T.M, T.P

    def qualification(base):
        host, osx, request, paths = T.start(base)
        for bad in (None, {}, dict(host.qualification, kind='fixture'),
                    dict(host.qualification, os_version='another'), dict(host.qualification, rows={})):
            host.qualification = bad
            T.refused(lambda: host.start(request), 'missing_evidence:macos_qualification')
        assert osx.bootstraps == 0

    def profile(base):
        host, osx, request, paths = T.start(base)
        original = copy.deepcopy(host.profile)
        for name in P.CAPS + ('max_workers',):
            for value in (None, 0, -1, float('inf'), float('nan'), True):
                host.profile = copy.deepcopy(original)
                host.profile[name] = value
                T.refused(lambda: host.start(request), 'unsupported_configuration:')
        assert osx.bootstraps == 0

    def bindings(base):
        host, osx, request, paths = T.start(base)
        for field in ('contract_digest', 'acceptance'):
            bad = dict(request, **{field: ''})
            T.refused(lambda: host.start(bad), 'binding_mismatch:accepted_dispatch')
        bad = copy.deepcopy(request)
        bad['contract']['capability']['configuration_digest'] = 'changed'
        T.refused(lambda: host.start(bad), 'binding_mismatch:configuration')
        bad = copy.deepcopy(request)
        bad['contract']['source']['commit'] = '0' * 40
        bad['contract_digest'] = P.digest(bad['contract'])
        T.refused(lambda: host.start(bad), 'binding_mismatch:clone_commit')
        (paths['clone'] / 'source.txt').write_text('unaccepted edit')
        T.refused(lambda: host.start(request), 'binding_mismatch:clone_dirty')
        (paths['clone'] / 'source.txt').write_text('accepted source\n')
        host.profile['engines']['codex']['binary_digest'] = 'changed'
        host.qualification['profile_digest'] = P.digest(host.profile)
        T.refused(lambda: host.start(request), 'stale_version:engine_binary')
        assert osx.bootstraps == 0

    def paths(base):
        host, osx, request, dirs = T.start(base)
        policy = host.preflight(request)[1]
        lines = policy.splitlines()
        assert lines[:2] == ['(version 1)', '(allow default)']
        assert lines[2].startswith('(deny file-write* (require-not (require-any')
        assert '(literal "/dev/null") (literal "/dev/tty")' in lines[2]
        environment = request['environment']
        for granted in (dirs['clone'], dirs['scratch'], dirs['login'], environment['HOME'], environment['TMPDIR']):
            assert '(subpath "%s")' % granted in lines[2], granted
        assert str(dirs['authority']) not in policy and str(host.root) not in lines[2]

        owner = str(dirs['owner'].resolve())
        reads = [line for line in lines if line.startswith('(deny file-read-data')]
        assert [r.split(' (require-not')[0] for r in reads] == [
            '(deny file-read-data (require-all (subpath "%s/.ssh")' % owner,
            '(deny file-read-data (require-all (regex #"^%s/\\.claude")' % owner.replace('.', '\\.'),
            '(deny file-read-data (require-all (regex #"^%s/\\.codex")' % owner.replace('.', '\\.'),
            '(deny file-read-data (require-all (require-any (subpath "%s"))' % dirs['accounts'],
            '(deny file-read-data (require-all (require-any (subpath "%s"))' % dirs['projects'],
            '(deny file-read-data (require-all (require-any (subpath "%s"))' % host.root], reads
        # Every read denial exempts exactly the run's grants, including its own login.
        prefix, suffix = '(deny file-write* (require-not (require-any ', ' (literal "/dev/null") (literal "/dev/tty"))))'
        assert lines[2].startswith(prefix) and lines[2].endswith(suffix)
        grants = lines[2][len(prefix):-len(suffix)]
        assert all(r.endswith(' (require-not %s)))' % grants) for r in reads), reads
        assert lines[-4:] == ['(deny process-exec (literal "/bin/launchctl"))', '(deny job-creation)',
                              '(deny mach-lookup (global-name "com.apple.SecurityServer") (global-name '
                              '"com.apple.securityd") (global-name "com.apple.securityd.xpc"))',
                              '(deny signal (require-not (target same-sandbox)))']
        link = dirs['scratch'] / 'alias'
        link.symlink_to(dirs['authority'], target_is_directory=True)
        T.refused(lambda: P.sandbox([str(link)], [str(dirs['authority'])], str(base)), 'invalid_input:protected_overlap')
        T.refused(lambda: P.sandbox([str(base) + '/q"uote'], [str(dirs['authority'])], str(base)), 'invalid_input:path')
        assert P.overlaps('/Users/Owner/Key', '/users/owner/key/child')
        assert P.overlaps('/Users/caf\u00e9', '/Users/cafe\u0301/child')
        assert not P.overlaps('/private/var/key', '/private/var/keys')
        T.refused(lambda: P.sandbox([str(base)], [str(dirs['authority'])], str(base)), 'invalid_input:protected_overlap')

    def signing_key_read(base):
        host, osx, request, dirs = T.start(base)
        signing_key = dirs['authority'] / 'worker-signing'
        signing_key.write_text('synthetic private key')
        host.profile['signing_keys'] = [str(signing_key)]
        key_policy = host.policy(request)
        assert '(deny file-read-data (require-any (subpath "%s")))' % signing_key in key_policy


    def run_environment(base):
        host, osx, request, dirs = T.start(base)
        environment = request['environment']
        assert environment['HOME'] == str(dirs['scratch'].resolve()) + '/home'
        assert environment['TMPDIR'] == environment['TMP'] == environment['TEMP']
        assert environment['TMPDIR'].startswith(str(dirs['usertemp'].resolve()) + '/veldo-')
        for name in ('HOME', 'TMPDIR'):
            bad = copy.deepcopy(request)
            bad['environment'][name] = str(dirs['login'])
            T.refused(lambda: host.start(bad), 'binding_mismatch:run_environment')
        assert osx.bootstraps == 0 and not Path(environment['TMPDIR']).exists()
        run = host.start(request)
        for path in (environment['TMPDIR'], environment['HOME'] + '/Library/Developer/Xcode/DerivedData',
                     environment['HOME'] + '/Library/Developer/CoreSimulator'):
            assert Path(path).is_dir(), path
        assert run.wait()['state'] == 'exited'
        run.release()
        assert not Path(environment['TMPDIR']).exists()

    def interpreter(base):
        host, osx, request, dirs = T.start(base)
        old = base / 'python3.9'
        old.write_text('#!/bin/sh\necho 3 9\n')
        old.chmod(0o755)
        for path in (str(base / 'missing-python'), str(old)):
            host.profile['interpreter'] = path
            host.qualification['profile_digest'] = P.digest(host.profile)
            T.refused(lambda: host.start(request), 'unsupported_configuration:interpreter')
        host.profile['interpreter'] = 'python3'
        T.refused(lambda: host.start(request), 'unsupported_configuration:interpreter')
        assert osx.bootstraps == 0
        host.profile['interpreter'] = T.sys.executable
        host.qualification['profile_digest'] = P.digest(host.profile)
        host.start(request)
        assert osx.calls[0][2] == T.sys.executable

    def nested(base):
        host, osx, request, dirs = T.start(base)
        host.profile['engines']['codex']['argv'] = host.profile['engines']['codex']['argv'][:3]
        T.refused(lambda: host.start(request), 'unsupported_configuration:nested_sandbox')
        for flags in (['-s', 'danger-full-access'], ['--dangerously-bypass-approvals-and-sandbox']):
            host.profile['engines']['codex']['argv'] = host.profile['engines']['codex']['argv'][:3] + flags
            P.validate(host.profile)

    def capacity(base):
        host, osx, request, paths = T.start(base, 'blocked')
        run = host.start(request)
        other = copy.deepcopy(request)
        other['contract']['dispatch_id'] = 'dispatch/second'
        other['contract_digest'] = P.digest(other['contract'])
        other['environment'].update(host.run_environment('dispatch/second', other['scratch']))
        T.refused(lambda: host.start(other), 'unavailable_service:concurrency')
        T.refused(lambda: host.start(request), 'stale_version:dispatch_already_attempted')
        assert osx.bootstraps == 1 and host.status()['pending'] == 1
        osx.finish()
        assert run.wait()['state'] == 'exited'
        assert host.status()['pending'] == 1
        run.release()
        assert host.status()['pending'] == 0
        T.refused(run.release, 'stale_version:already_retired')

    def deadline(base):
        host, osx, request, paths = T.start(base, 'blocked')
        run = host.start(request)
        result = run.wait()
        assert result['state'] == 'exited' and result['termination']['deadline_stop']
        assert [s['stage'] for s in run.steps] == ['terminate']
        assert 0.3 <= run.steps[0]['monotonic'] <= 0.321
        assert not osx.live

    def descendant(base):
        host, osx, request, paths = T.start(base, 'descendant')
        run = host.start(request)
        # The wrapper is gone; a setsid survivor outside the engine group lives on.
        osx.finish(survivor=True)
        assert osx.exit_event and list(osx.live) == [T.SURVIVOR]
        assert not run.poll()
        assert not run.retirement()['terminated']
        T.refused(run.release, 'unknown_outcome:retirement')
        result = run.wait()
        assert result['state'] == 'exited' and not osx.live, (result, osx.live)
        assert [s['stage'] for s in run.steps] == ['terminate', 'kill']
        assert any(c[:4] == ('signal', T.SURVIVOR, signal.SIGKILL, False) for c in osx.calls), osx.calls
        run.release()

    def contract_deadline(base):
        host, osx, request, paths = T.start(base, 'blocked')
        request['contract']['deadline'] = 1000.12
        request['contract_digest'] = P.digest(request['contract'])
        run = host.start(request)
        assert run.wait()['state'] == 'exited'
        assert .12 <= run.steps[0]['monotonic'] <= .141

    def notification_lost(base):
        host, osx, request, paths = T.start(base, 'lost')
        run = host.start(request)
        osx.finish()
        osx.exit_event = False
        assert run.wait()['state'] == 'unknown'
        assert not run.retirement()['terminated']

    def ignoring(base):
        for engine in P.ENGINES:
            host, osx, request, paths = T.start(base / engine, 'ignoring')
            request['engine'] = request['contract']['capability']['adapter'] = engine
            request['contract_digest'] = P.digest(request['contract'])
            run = host.start(request)
            run.stop()
            # A hard kill of the engine group leaves the wrapper to record it.
            result = run.wait()
            assert result['state'] == 'exited' and result['termination']['signal'] == signal.SIGKILL, result
            assert [s['stage'] for s in run.steps] == ['cooperative', 'terminate', 'kill']
            assert .1 <= run.steps[1]['monotonic'] - run.steps[0]['monotonic'] <= .121
            assert .1 <= run.steps[2]['monotonic'] - run.steps[1]['monotonic'] <= .121
            assert run.exit_seen and not osx.live and host.status()['pending'] == 1
            run.release()
            assert host.status()['pending'] == 0

    def killed(base):
        host, osx, request, paths = T.start(base, 'killed')
        run = host.start(request)
        result = run.wait()
        assert result['state'] == 'unknown' and run.exit_seen and not osx.live
        assert run.retirement() == dict(terminated=True, cleaned=True, outcome_known=False, observer='macos_supervisor')
        T.refused(run.release, 'unknown_outcome:retirement')
        T.refused(lambda: host.recover(run.dispatch), 'unknown_outcome:slot_unknown')

    def recover(base):
        host, osx, request, paths = T.start(base, 'blocked')
        run = host.start(request)
        # The supervisor process is gone; a new one rebuilds the Run from slot.json.
        again = M.Supervisor(host.profile, host.qualification, backend=osx)
        rebuilt = again.recover(run.dispatch)
        assert (rebuilt.process, rebuilt.coalition, rebuilt.state) == (run.process, T.JOB, 'running')
        assert abs(rebuilt.deadline - run.deadline) < 1e-6 and not rebuilt.exit_seen
        result = rebuilt.wait()
        assert result['state'] == 'exited' and result['termination']['deadline_stop'], result
        rebuilt.release()
        assert again.status()['pending'] == 0
        T.refused(lambda: again.recover(run.dispatch), 'stale_version:already_retired')
        T.refused(lambda: again.recover('dispatch/none'), 'missing_evidence:slot')

    def sync(base):
        pack = T.load('pack')
        names = sorted(p.name for p in (ROOT / 'engine/.veldo').glob('project_runner_macos*.py'))
        assert len(names) == 5
        inventory = pack.engine_files(str(ROOT / 'engine'))
        for name in names:
            assert '.veldo/' + name in inventory
            assert (ROOT / '.veldo' / name).read_bytes() == (ROOT / 'engine/.veldo' / name).read_bytes()
        for wrapper in sorted((ROOT / 'packs').iterdir()):
            if not wrapper.is_dir():
                continue
            destination = base / wrapper.name
            pack.assemble_pack(str(ROOT / 'engine'), str(wrapper), str(ROOT / 'engine/AGENTS.md'),
                               str(destination), globs=('.veldo/project_runner_macos*.py',))
            for name in names:
                assert (destination / '.veldo' / name).read_bytes() == (ROOT / 'engine/.veldo' / name).read_bytes()

    def native_declared(base):
        import ast
        import json
        import subprocess
        import sys
        path = ROOT / 'proof/VELDO-0124/native_checks.py'
        ast.parse(path.read_text())
        if sys.platform != 'darwin':
            result = subprocess.run([sys.executable, str(path), 'lifecycle'], capture_output=True, text=True, timeout=5)
            assert result.returncode == 2
            assert json.loads(result.stdout) == {'status': 'not_run', 'reason': 'requires_real_macos'}

    def natural(base):
        for engine in P.ENGINES:
            host, osx, request, paths = T.start(base / engine)
            request['engine'] = request['contract']['capability']['adapter'] = engine
            request['contract_digest'] = P.digest(request['contract'])
            run = host.start(request)
            result = run.wait()
            assert result['state'] == 'exited' and not run.steps and run.exit_seen
            assert result['worker']['process']['pid'] != result['process']['pid']

    def stop(base):
        for engine in P.ENGINES:
            host, osx, request, paths = T.start(base / engine, 'cooperative')
            request['engine'] = request['contract']['capability']['adapter'] = engine
            request['contract_digest'] = P.digest(request['contract'])
            run = host.start(request)
            run.stop()
            assert run.wait()['state'] == 'exited'
            assert [s['stage'] for s in run.steps] == ['cooperative']

    def unknown(base):
        host, osx, request, paths = T.start(base, 'lost')
        run = host.start(request)
        assert run.wait()['state'] == 'unknown'
        assert host.status()['pending'] == host.status()['stopped'] == 1
        T.refused(run.release, 'unknown_outcome:retirement')
        T.refused(lambda: host.start(request), 'stale_version:dispatch_already_attempted')
        osx.mode = 'ps_error'
        assert not run.retirement()['cleaned']

    def heartbeat(base):
        host, osx, request, paths = T.start(base, 'blocked')
        run = host.start(request)
        osx.heartbeat = False
        result = run.wait()
        assert result['state'] == 'exited' and run.cause == 'heartbeat_missing'
        assert run.steps[0]['monotonic'] <= .101 and run.steps[0]['stage'] == 'cooperative'

    def os_contract(base):
        host, osx, request, paths = T.start(base)
        captured = []
        native = M.OS.Native()
        old = M.OS.command
        M.OS.command = lambda argv: captured.append(argv) or ''
        try:
            native.bootstrap('org.veldo.test', ['/usr/bin/true'], base, 5)
            import plistlib
            plist = plistlib.loads((base / 'org.veldo.test.plist').read_bytes())
            assert plist['KeepAlive'] is False and plist['AbandonProcessGroup'] is False
            assert plist['ExitTimeOut'] == 5 and 'TimeOut' not in plist
            # macOS 26 user/<uid> refuses jobs outside the Background session type.
            assert plist['LimitLoadToSessionType'] == 'Background'
            assert captured[0][1] == 'bootstrap' and captured[0][2] == 'user/%d' % os.getuid()
        finally:
            M.OS.command = old
        # Coalition membership, not process group: zombies have exited and are left out.
        assert M.OS.live_members([(12, 7, 2), (13, 7, M.OS.SZOMB), (14, 9, 2), (15, 7, 3)], 7) == [12, 15]

    tests = {'AC1/qualification': qualification, 'AC1/profile': profile, 'AC1/bindings': bindings,
             'AC1/apfs-policy': paths, 'AC1/worker-signing-key-read': signing_key_read, 'AC1/apple-interfaces': os_contract, 'AC1/run-environment': run_environment,
             'AC1/interpreter': interpreter, 'AC1/nested-sandbox': nested, 'AC3/hard-kill-unknown': killed,
             'AC3/recover': recover, 'AC2/capacity': capacity,
             'AC1/template-sync': sync, 'AC1/native-declared': native_declared,
             'AC2/deadline': deadline, 'AC2/contract-deadline': contract_deadline,
             'AC3/descendant': descendant, 'AC3/natural': natural, 'AC3/notification-lost': notification_lost,
             'AC3/cooperative': stop, 'AC3/unknown': unknown, 'AC3/ignoring': ignoring, 'AC3/heartbeat': heartbeat}
    for name, test in tests.items():
        with tempfile.TemporaryDirectory(prefix='v124-') as directory:
            try:
                test(Path(directory))
                expect('VELDO-0124 ' + name, True)
            except Exception as error:
                print('  ' + name + ': ' + type(error).__name__ + ': ' + str(error)[:220])
                expect('VELDO-0124 ' + name, False)


_v124_suite()
