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
        assert '(deny file-write*' in policy and '(require-not (require-any' in policy
        assert str(dirs['clone']) in policy and str(dirs['authority']) not in policy
        link = dirs['scratch'] / 'alias'
        link.symlink_to(dirs['authority'], target_is_directory=True)
        T.refused(lambda: P.sandbox([str(link)], [str(dirs['authority'])]), 'invalid_input:protected_overlap')
        assert P.overlaps('/Users/Owner/Key', '/users/owner/key/child')
        assert P.overlaps('/Users/caf\u00e9', '/Users/cafe\u0301/child')
        assert not P.overlaps('/private/var/key', '/private/var/keys')
        T.refused(lambda: P.sandbox([str(base)], [str(dirs['authority'])]), 'invalid_input:protected_overlap')

    def capacity(base):
        host, osx, request, paths = T.start(base, 'blocked')
        run = host.start(request)
        other = copy.deepcopy(request)
        other['contract']['dispatch_id'] = 'dispatch/second'
        other['contract_digest'] = P.digest(other['contract'])
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
        host, osx, request, paths = T.start(base, 'blocked')
        run = host.start(request)
        osx.finish(survivor=True)
        assert not run.poll()
        assert not run.retirement()['terminated']
        T.refused(run.release, 'unknown_outcome:retirement')
        result = run.wait()
        assert result['state'] == 'exited' and not osx.live
        assert any(s['stage'] == 'kill' for s in run.steps)

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
            assert run.wait()['state'] == 'unknown'  # KILL cannot fabricate a wrapper result.
            assert [s['stage'] for s in run.steps] == ['cooperative', 'terminate', 'kill']
            assert .1 <= run.steps[1]['monotonic'] - run.steps[0]['monotonic'] <= .121
            assert .1 <= run.steps[2]['monotonic'] - run.steps[1]['monotonic'] <= .121
            assert run.exit_seen and not osx.live and host.status()['pending'] == 1

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
            assert captured[0][1] == 'bootstrap' and captured[0][2].startswith('user/')
        finally:
            M.OS.command = old
        assert M.OS.parse_members('12 12 S\n13 12 Z\n14 99 R', 12) == [12]
        T.refused(lambda: M.OS.parse_members('unreadable', 12), 'process_table_unreadable')

    tests = {'AC1/qualification': qualification, 'AC1/profile': profile, 'AC1/bindings': bindings,
             'AC1/apfs-policy': paths, 'AC1/apple-interfaces': os_contract, 'AC2/capacity': capacity,
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
