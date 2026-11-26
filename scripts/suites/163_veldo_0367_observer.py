"""VELDO-0367 AC2: item attribution and explicit unknowns at coverage boundaries."""


def _v367_observer():
    import importlib.util
    import json
    import os
    from pathlib import Path
    import shutil
    import subprocess
    import sys
    import tempfile

    sources = {'mutation_observer.py': ROOT / "scripts" / "mutation_observer.py",
               'gate_legs.py': ROOT / "scripts" / "gate_legs.py",
               'case_trace.py': ROOT / "scripts" / "case_trace.py",
               'reuse_worker.py': ROOT / "scripts" / "reuse_worker.py",
               'check_gate_mutations.py': ROOT / "scripts" / "check_gate_mutations.py"}

    shared_source = ROOT / "scripts/suites" / "shared.py"

    def load(path):
        spec = importlib.util.spec_from_file_location('observer367_' + path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def row(name, condition):
        expect('VELDO-0367 observer/' + name, condition)

    with tempfile.TemporaryDirectory(prefix='v367-observer-') as directory:
        top = Path(directory)
        authority, repo = top / 'authority', top / 'repo'
        (authority / 'scripts').mkdir(parents=True)
        (authority / '.veldo').mkdir()
        repo.mkdir()
        for name, source in sources.items():
            shutil.copyfile(source, authority / 'scripts' / name)
        for name in ('gate_fixtures.py', 'gate_changes.py', 'gate_reuse.py'):
            shutil.copyfile(ROOT / 'scripts' / name, authority / 'scripts' / name)
        shutil.copyfile(ROOT / '.veldo/reuse_evidence.py', authority / '.veldo/reuse_evidence.py')
        O = load(authority / 'scripts/mutation_observer.py')
        G = load(authority / 'scripts/gate_legs.py')
        W = load(authority / 'scripts/reuse_worker.py')
        R = load(authority / 'scripts/gate_reuse.py')
        C = O.dependency_module('gate_changes')
        for relative in R.E.AUTHORITY_FILES:
            path = authority / relative
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('# fixture authority input\n')
        (repo / '.gitignore').write_text('__pycache__/\n')
        (repo / 'data').mkdir()
        (repo / 'data/input').write_text('input')
        (repo / 'data/child').write_text('child')
        (repo / 'module367.py').write_text('value = 367\n')
        (repo / 'alias').symlink_to('data/input')
        for args in (['init', '-q'], ['add', '.'], ['-c', 'user.name=Dmitry Grinberg',
                     '-c', 'user.email=dmitry@bcengi.com', 'commit', '-qm', 'observer fixture']):
            subprocess.run(['git', '-C', str(repo), *args], check=True, stdout=subprocess.PIPE)
        commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        declaration = authority / 'scripts/gate_unconfined.json'
        declaration.write_text(json.dumps({'suites': [
            {'suite': 'plain', 'reason': 'native command'},
            {'suite': 'traced', 'reason': 'nested strace'},
            {'suite': 'tree', 'reason': 'nested namespace confinement'}]}))
        tracer = O.dependency_module('case_trace')
        row('trace-compatible', tracer['compatible'](authority, ['plain']) and
            not tracer['compatible'](authority, ['traced', 'plain']) and
            not tracer['compatible'](authority, ['tree']) and not tracer['compatible'](authority, ['missing']))
        item = C['identity']('suite', 'unit', 'confined', 'fixture')
        reads = O.DependencyReads(repo, {}).start()
        (repo / 'data/input').read_text()
        load(repo / 'module367.py')
        list((repo / 'data').iterdir())
        try:
            (repo / 'missing').read_text()
        except FileNotFoundError:
            pass
        (repo / 'alias').read_text()
        subprocess.run(['/bin/cat', str(repo / 'data/child')], check=True, stdout=subprocess.PIPE)
        reads.stop()
        dep = reads.record(item, commit)
        row('python-import', {'data/input', 'module367.py'} <= set(dep['paths']))
        row('discovery', 'data' in dep['directories'])
        row('missing', 'missing' in dep['absent_paths'])
        row('symlink', {'alias', 'data/input'} <= set(dep['paths']))
        row('python-unknown', not dep['complete'] and 'syscall' in dep['unknown_reason'])
        row('child-unknown', not dep['complete'] and 'native child' in dep['unknown_reason'])
        row('runtime', dep['runtime_digest'] != O.DependencyReads(repo, {'LANG': 'different'}).record(item, commit)['runtime_digest'])

        import py_compile
        prefix = sys.pycache_prefix
        sys.pycache_prefix = None
        try:
            py_compile.compile(str(repo / 'module367.py'), doraise=True)
            warm = O.DependencyReads(repo, {}).start()
            load(repo / 'module367.py')
            warm.stop()
        finally:
            sys.pycache_prefix = prefix
        row('warm-bytecode', 'module367.py' in warm.paths and
            any('__pycache__' in path for path in warm.paths))
        cold_runtime = O.DependencyReads(repo, {'LANG': 'C', 'TMPDIR': str(top / 'scratch-a'),
                                               'VELDO_OPENED_LEDGER_FD': '7'})
        warm_runtime = O.DependencyReads(repo, {'LANG': 'C', 'TMPDIR': str(top / 'scratch-b'),
                                               'VELDO_OPENED_LEDGER_FD': '19'})
        for capture, scratch in ((cold_runtime, top / 'scratch-a'), (warm_runtime, top / 'scratch-b')):
            scratch.mkdir()
            (scratch / 'input').write_text(str(scratch))
            capture.read(scratch / 'input')
        row('runtime-stable', cold_runtime.record(item, commit)['runtime_digest'] ==
            warm_runtime.record(item, commit)['runtime_digest'])
        private_runtime = O.DependencyReads(repo, {'LANG': 'C', 'TMPDIR': str(top / 'scratch-a')},
                                             private_scratch=(top / 'scratch-a',))
        private_runtime.read(top / 'scratch-a/input')
        row('private-scratch', private_runtime.runtime == O.DependencyReads(repo, {'LANG': 'C'}).runtime and
            private_runtime.reasons == {'observation coverage unavailable'})
        authority_runtime = O.DependencyReads(repo, {})
        authority_runtime.read(authority / 'scripts/mutation_observer.py')
        row('authority-runtime', 'authority:scripts/mutation_observer.py' in authority_runtime.runtime and
            not any(str(top) in key for key in authority_runtime.runtime))
        row('scratch-unknown', 'scratch' in cold_runtime.record(item, commit)['unknown_reason'])

        # Both legs have identical completeness rules. Closed trace fixtures include
        # forked native children, an imported module, a directory and a failed lookup.
        lines = [
            '11 openat(AT_FDCWD, "data/input", O_RDONLY) = 3',
            '11 openat(AT_FDCWD, "module367.py", O_RDONLY) = 4',
            '11 getdents64(5<%s/data>, [], 32768) = 0' % repo,
            '11 newfstatat(AT_FDCWD, "missing", 0x0, 0) = -1 ENOENT (No such file)',
            '11 openat(AT_FDCWD, "alias", O_RDONLY) = 6',
            '11 clone(child_stack=NULL, flags=SIGCHLD) = 12',
            '12 openat(AT_FDCWD, "data/child", O_RDONLY) = 3',
            '12 +++ exited with 0 +++', '11 +++ exited with 0 +++']
        trace = top / 'trace'
        trace.write_text('\n'.join(lines) + '\n')
        for leg in ('confined', 'unconfined'):
            identity = C['identity']('suite', 'unit', leg, 'fixture')
            complete = O.DependencyReads(repo, {}).trace(trace, launched_argv=O.dependency_module('case_trace')['command'](trace, ['/bin/true'])).record(identity, commit)
            row('trace-' + leg, complete['complete'] and complete['unknown_reason'] is None and
                {'data/input', 'module367.py', 'data/child', 'alias'} <= set(complete['paths']) and
                complete['directories'] == ['data'] and complete['absent_paths'] == ['missing'] and
                complete['item_id'] == identity)
        row('filtered-unknown', not O.DependencyReads(repo, {}).trace(trace).record(item, commit)['complete'])
        row('lost-events', not O.DependencyReads(repo, {}).trace(trace, dropped=True, launched_argv=O.dependency_module('case_trace')['command'](trace, ['/bin/true'])).record(item, commit)['complete'])
        trace.write_text('\n'.join(lines[:-2]) + '\n')
        broken = O.DependencyReads(repo, {}).trace(trace, launched_argv=O.dependency_module('case_trace')['command'](trace, ['/bin/true'])).record(item, commit)
        row('incomplete-not-empty', not broken['complete'] and bool(broken['unknown_reason']))
        trace.write_text('11 openat(AT_FDCWD, "data/input", O_RDONLY <unfinished ...>\n11 +++ exited with 0 +++\n')
        row('unfinished', not O.DependencyReads(repo, {}).trace(trace, launched_argv=O.dependency_module('case_trace')['command'](trace, ['/bin/true'])).record(item, commit)['complete'])
        trace.write_text('')
        row('empty-trace', not O.DependencyReads(repo, {}).trace(trace, launched_argv=O.dependency_module('case_trace')['command'](trace, ['/bin/true'])).record(item, commit)['complete'])
        trace.write_text('11 openat(AT_FDCWD, "module367.py", O_RDONLY) = 3\n11 +++ exited with 0 +++\n')
        fresh = O.DependencyReads(repo, {}).trace(trace, launched_argv=O.dependency_module('case_trace')['command'](trace, ['/bin/true']))
        refreshed = fresh.record(item, commit)
        row('refresh', refreshed['complete'] and refreshed['paths'] == ['module367.py'] and
            refreshed['record_digest'] != complete['record_digest'])
        trace.write_text('11 clone(child_stack=NULL, flags=SIGCHLD <unfinished ...>\n'
                         '11 <... clone resumed>) = 12\n11 +++ exited with 0 +++\n')
        row('unfinished-clone', not O.DependencyReads(repo, {}).trace(trace,
            launched_argv=O.dependency_module('case_trace')['command'](trace, ['/bin/true'])).record(item, commit)['complete'])
        # VELDO-0367 N1: real buffers carry markers, forbidden words and truncation; only the
        # anchored call and its non-data text are judged. A Python watchdog thread shares fs.
        module_file = str(repo / 'module367.py')
        # X1: a closed two-line failed-connect trace must retain its negative lookup.
        for name, endpoint in [('repository', str(repo / 'endpoint')),
                               ('external', str(top / 'external-endpoint')),
                               ('relative', 'endpoint'), ('descriptor', '/proc/self/fd/99')]:
            trace.write_text('11 connect(3<UNIX-STREAM:[99]>, {sa_family=AF_UNIX, sun_path=' +
                             json.dumps(endpoint) + '}, 110) = -1 ENOENT (No such file or directory)\n'
                             '11 +++ exited with 0 +++\n')
            socket_reads = O.DependencyReads(repo, {}).trace(trace,
                launched_argv=tracer['command'](trace, ['/bin/true']))
            socket_dep = socket_reads.record(item, commit)
            if name == 'repository':
                row('socket-repository', socket_dep['complete'] and 'endpoint' in socket_dep['absent_paths']
                    and C['intersects'](socket_dep, ['endpoint']))
            elif name == 'external':
                row('socket-external', socket_dep['complete'] and socket_reads.runtime.get(endpoint) == ['absent'])
            else:
                row('socket-' + name, not socket_dep['complete'])

        payload = ('x <unfinished ...> y\\n11 <... read resumed> mount( ptrace( CLONE_FS CLONE_NEWNS '
                   'def is_mount(... \\"...')
        trace.write_text(
            '11 clone3({flags=CLONE_VM|CLONE_FS|CLONE_FILES|CLONE_SIGHAND|CLONE_THREAD|CLONE_SYSVSEM, '
            'exit_signal=0, stack=0x7f, stack_size=0x1000}, 88) = 12\n'
            '11 openat(AT_FDCWD, "module367.py", O_RDONLY|O_CLOEXEC) = 3<' + module_file + '>\n'
            '11 read(3<' + module_file + '>, "' + payload + '"..., 65535) = 65535\n'
            '12 read(3<' + module_file + '>,  <unfinished ...>\n'
            '11 write(1</dev/null>, "<... x resumed> <unfinished ...>", 32) = 32\n'
            '12 <... read resumed>"' + payload + '", 4096) = 4096\n'
            '12 +++ exited with 0 +++\n11 +++ exited with 0 +++\n')
        tracer = O.dependency_module('case_trace')
        try:
            joined = len(list(tracer['syscall_lines'](trace))) == 5
        except ValueError:
            joined = False
        row('payload-lines', joined)
        payloaded = O.DependencyReads(repo, {}).trace(trace, launched_argv=tracer['command'](trace, ['/bin/true'])).record(item, commit)
        row('payload-complete', payloaded['complete'] and 'module367.py' in payloaded['paths'])
        for name, body in (
                ('process-shared-fs', '11 clone(child_stack=NULL, flags=CLONE_FS|SIGCHLD) = 12\n'
                                      '12 +++ exited with 0 +++\n11 +++ exited with 0 +++\n'),
                ('thread-chdir', '11 clone3({flags=CLONE_VM|CLONE_FS|CLONE_THREAD}, 88) = 12\n'
                                 '12 chdir("data") = 0\n12 +++ exited with 0 +++\n11 +++ exited with 0 +++\n'),
                ('truncated-name', '11 openat(AT_FDCWD, "data/inp"..., O_RDONLY) = 3\n11 +++ exited with 0 +++\n'),
                ('namespace-call', '11 unshare(CLONE_NEWNS) = 0\n11 +++ exited with 0 +++\n')):
            trace.write_text(body)
            row(name, not O.DependencyReads(repo, {}).trace(trace,
                launched_argv=tracer['command'](trace, ['/bin/true'])).record(item, commit)['complete'])
        for name, path in (('git-directory', repo / '.git/index'),):
            metadata = O.DependencyReads(repo, {})
            metadata.read(path)
            row(name, 'git metadata read' in metadata.record(item, commit)['unknown_reason'])
        linked = top / 'linked'
        linked.mkdir()
        (linked / '.git').write_text('gitdir: ' + str(repo / '.git/worktrees/linked'))
        (repo / '.git/worktrees/linked').mkdir(parents=True)
        (repo / '.git/worktrees/linked/commondir').write_text('../..')
        metadata = O.DependencyReads(linked, {})
        metadata.read(repo / '.git/index')
        row('git-common-directory', 'git metadata read' in metadata.record(item, commit)['unknown_reason'])
        filtered = O.dependency_module('case_trace')['command'](trace, ['/bin/true'])
        row('tracer-command', '-f' in filtered and '-yy' in filtered and 'trace=all' in filtered)
        trace.write_text('11 openat(AT_FDCWD, "module367.py", O_RDONLY) = 3\n11 +++ exited with 0 +++\n')
        for option in ('-yy', 'trace=all'):
            altered = [word for word in filtered if word != option]
            row('trace-provenance-' + option, not O.DependencyReads(repo, {}).trace(trace,
                launched_argv=altered).record(item, commit)['complete'])

        external = O.DependencyReads(repo, {})
        external.read('/proc/self/status')
        row('external-unknown', 'unrecordable external input' in external.record(item, commit)['unknown_reason'])
        union = O.combine_dependencies([complete, refreshed], item, commit)
        row('union', set(union['paths']) == set(complete['paths']) | set(refreshed['paths']))
        retained = O.combine_dependencies([refreshed], item, commit, prior=complete, rows=True)
        row('rows-retain', retained['paths'] == union['paths'])
        row('rows-no-prior', not O.combine_dependencies([refreshed], item, commit, rows=True)['complete'])
        row('union-unknown', not O.combine_dependencies([complete, broken], item, commit)['complete'])

        store = R.Store(top / 'store', repo)
        outcome = {'returncode': 0, 'rows': [4, 0]}
        envelope = O.publish_dependencies(store, complete, outcome)
        row('atomic-result', store.get(envelope['record_digest']) == envelope and
            envelope['dependency'] == complete and envelope['result'] == outcome)
        original = store._publish
        def interrupted(*args, **kwargs):
            raise OSError('fixture interruption before publication')
        store._publish = interrupted
        failed = False
        try:
            O.publish_dependencies(store, refreshed, outcome)
        except OSError:
            failed = True
        store._publish = original
        pending = C['sealed']('veldo.change-observation/v1', dependency=refreshed, result=outcome)
        row('atomic-interrupted', failed and store.get(pending['record_digest']) is None and
            store.get(envelope['record_digest']) == envelope)

        # Execute the coordinator's publication seam with real Store writes. Its
        # caller runs after Workers.finish has reaped descendants and allocations.
        import ast
        from types import SimpleNamespace
        coordinator = sources['check_gate_mutations.py']
        tree = ast.parse(coordinator.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and
                        node.name == 'publish_case_dependencies')
        namespace = dict(ROOT=authority, load=load, _load_audit=load, os=os, sys=sys, Refused=RuntimeError,
                         in_leg=lambda leg, case: leg == 'unconfined')
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(coordinator), 'exec'), namespace)
        publish = namespace['publish_case_dependencies']
        case = dict(identity='fixture', suite='fixture.py', driver='check_teeth_mutations.py', name='fixture')
        workers = SimpleNamespace(active={}, meters={}, owned_snapshots={}, outcomes=[], leg=None,
                                  observed_commit=commit)
        def python_claim(record):
            return C['sealed'](C['DEPENDENCY'], **{k: v for k, v in record.items()
                if k not in ('schema', 'record_digest', 'complete', 'unknown_reason')},
                complete=False, unknown_reason='Python audit lacks complete syscall coverage')
        first, second = python_claim(complete), python_claim(refreshed)
        workers.authority_dependencies = {first['record_digest']: complete, second['record_digest']: refreshed}
        result = dict(baseline={'dependency': first}, noop={'dependency': second},
                      mutant={'dependency': dep})
        for field, pending_value in (('active', {'worker': True}), ('meters', {'worker': True}),
                                     ('owned_snapshots', {'worker': True}),
                                     ('outcomes', [{'error': 'worker_cleanup_error'}])):
            original = getattr(workers, field)
            setattr(workers, field, pending_value)
            refused = False
            try:
                publish(repo, commit, [case], {'fixture': result}, workers, store=store)
            except RuntimeError:
                refused = True
            setattr(workers, field, original)
            row('coordinator-cleanup-' + field, refused)
        for leg in ('confined', 'unconfined'):
            workers.leg = leg
            publish(repo, commit, [case], {'fixture': result}, workers, store=store)
            identity = C['identity']('case', 'mutation', leg, case['suite'], case['driver'], case['name'])
            expected = O.combine_dependencies([complete, refreshed, dep], identity, commit)
            entry = C['sealed']('veldo.change-observation/v1', dependency=expected, result=result)
            row('coordinator-union-' + leg, store.get(entry['record_digest']) == entry)
        # VELDO-0367 N2/N4/F5: the authority's worker-trace reader keeps per-run coordinator files and
        # the worker's fixture allocation private and maps materialized copies back to their source.
        method = next(node for klass in tree.body if isinstance(klass, ast.ClassDef) and klass.name == 'Workers'
                      for node in klass.body if isinstance(node, ast.FunctionDef) and node.name == 'attribution_reads')
        scope = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(coordinator), 'exec'), scope)
        run_directory = top / 'veldo-mutations-run'
        worker_home = run_directory / 'home0'
        allocation = top / 'fixture-allocation'
        for directory in (worker_home / 'fixtures', allocation / 'g0001'):
            directory.mkdir(parents=True)
        for path in (run_directory / '0-stdout', run_directory / '0-stderr', run_directory / 'ownership-0.jsonl',
                     allocation / 'g0001/state', worker_home / 'fixtures/fixture367.py'):
            path.write_text('per-run ' + path.name)
        fixture_case = dict(fixture=True, module='fixture367.py', suite='fixture.py', name='fixture367')
        holder = SimpleNamespace(observation_context={'w': (repo, {'TMPDIR': str(worker_home)}, fixture_case, 'noop')},
                                 private_files={'w': (run_directory / '0-stdout', run_directory / '0-stderr',
                                                      run_directory / 'ownership-0.jsonl', allocation)})
        attributed = scope['attribution_reads'](holder, O, 'w', worker_home)
        for path in (*holder.private_files['w'][:3], allocation / 'g0001/state', worker_home / 'fixtures/fixture367.py'):
            attributed.read(path)
        attributed.reasons.discard('observation coverage unavailable')
        private = attributed.record(item, commit)
        row('private-run-files', private['complete'] and set(attributed.runtime) == {'environment'})
        row('materialized-copy', 'scripts/fixtures/fixture367.py' in private['paths'])

        # The ledger reaches only the authority's own runners: a stand-in takes three arguments.
        taking = G.TakeOpened(repo, None, 'stand-in-fixture', store=store)
        try:
            handed = taking.run(lambda root, command, env: 0, repo, 'true', taking.env(dict(os.environ)), taking.fd)
        except TypeError:
            handed = None
        taking.finish('stand-in-fixture', 1)
        row('stand-in-runner', handed == 0)
        # VELDO-0367 N4: a checkout dirtied before publication never stamps HEAD on the envelope.
        workers.leg = 'unconfined'
        (repo / 'dirty-publication').write_text('uncommitted')
        before = {path.name for path in store.directory.glob('*.json')}
        publish(repo, commit, [case], {'fixture': result}, workers, store=store)
        (repo / 'dirty-publication').unlink()
        stamped = [store.get(path.stem) for path in store.directory.glob('*.json') if path.name not in before]
        stamped = [value['dependency'] for value in stamped if value and 'dependency' in value]
        row('coordinator-dirty-commit', len(stamped) == 1 and stamped[0]['observed_commit'] == '0' * 40
            and not stamped[0]['complete'])
        mixed = O.combine_dependencies([complete, C['sealed'](C['DEPENDENCY'], **{k: v for k, v in complete.items()
            if k not in ('schema', 'record_digest', 'observed_commit')}, observed_commit='1' * 40)],
            complete['item_id'], commit)
        row('combine-mixed-commit', mixed['observed_commit'] == '0' * 40 and not mixed['complete'])
        forged = dict(result, baseline={'dependency': complete})
        refused = False
        try:
            publish(repo, commit, [case], {'fixture': forged}, workers, store=store)
        except ValueError:
            refused = True
        row('coordinator-python-complete', refused)
        class BrokenStore:
            def change_put(self, envelope):
                raise OSError('fixture Store unavailable')

            def put(self, key, value):
                raise OSError('fixture Store unavailable')
        stored = True
        try:
            publish(repo, commit, [case], {'fixture': result}, workers, store=BrokenStore())
        except OSError:
            stored = False
        row('coordinator-store-failure', stored)

        result['noop'] = {}
        publish(repo, commit, [case], {'fixture': result}, workers, store=store)
        entries = [store.get(path.stem) for path in store.directory.glob('*.json')]
        row('coordinator-missing', any(isinstance(entry, dict) and entry.get('result') == result and
            not entry['dependency']['complete'] and 'missing noop observation' in
            entry['dependency']['unknown_reason'] for entry in entries))

        tree = ast.parse(coordinator.read_text())
        stage = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'run_stage')
        row('coordinator-wired', any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
            node.func.id == 'publish_case_dependencies' for node in ast.walk(stage)))

        # Real children in either leg's environment are observed by the outside
        # kernel watch, beyond scripts/ and proof/. The dependency remains unknown
        # because inotify cannot attribute metadata probes or certify descendants.
        for leg in ('confined', 'unconfined'):
            taking = G.TakeOpened(repo, None, 'fixture-' + leg, store=store)
            env = taking.env(dict(os.environ, VELDO_GATE_LEG=leg,
                                  VELDO_EXPECTED_GIT_COMMON=str(repo / '.git')))
            import shlex
            command = shlex.join([sys.executable, '-c',
                'import pathlib, subprocess; pathlib.Path("module367.py").read_text(); '
                'subprocess.run(["/bin/cat", "data/child"], check=True, stdout=subprocess.PIPE)'])
            here = G.HERE
            G.HERE = ROOT / 'scripts'
            try:
                code = (G.confined if leg == 'confined' else G.unconfined)(repo, command, env, taking.fd)
            finally:
                G.HERE = here
            row('stage-' + leg, taking.finish('fixture-' + leg, code) == 0)
            observed = [store.get(path.stem) for path in store.directory.glob('*.json')]
            stage = next(value for value in observed if value and
                value.get('dependency', {}).get('item_id') == C['identity']('stage', 'fixture-' + leg))
            row('native-' + leg, {'module367.py', 'data/child'} <= set(stage['dependency']['paths']) and
                not stage['dependency']['complete'] and bool(stage['dependency']['unknown_reason']))

        # Exercise the actual authority launch/publication seam with a deterministic
        # kernel transcript. The process.args value is the argv received by run().
        from unittest.mock import patch
        trace_body = ('11 openat(AT_FDCWD, "data/child", O_RDONLY) = 3\n'
                      '11 +++ exited with 0 +++\n')
        sessions = []
        def traced_process(argv, **kwargs):
            sessions.append(kwargs.get('start_new_session'))
            Path(argv[argv.index('-o') + 1]).write_text(trace_body)
            return subprocess.CompletedProcess(argv, 0)

        def traced_stage(stage, listed, opened=()):
            # The fixture's leg list stands in for the authority's compatible declaration.
            taking = G.TakeOpened(repo, None, stage, store=store)
            real_stop = taking.watch.stop
            def stop():
                found, late, overflowed = real_stop()
                return set(found) | set(opened), late, overflowed
            taking.watch.stop = stop
            with patch.object(G.subprocess, 'run', traced_process), patch.dict(
                    taking.observer.dependency_module('case_trace'), compatible=lambda authority, suites: True):
                code = taking.run(G.unconfined, repo, 'cat data/child', taking.env(dict(os.environ,
                                  VELDO_GATE_LEG='unconfined', VELDO_GATE_UNCONFINED=listed)), taking.fd)
            identity = C['identity']('suite', stage, 'unconfined', 'fixture')
            claim = python_claim(C['sealed'](C['DEPENDENCY'], **{k: v for k, v in complete.items()
                if k not in ('schema', 'record_digest', 'item_id', 'observed_commit')}, item_id=identity,
                observed_commit=taking.commit))
            os.write(taking.fd, (json.dumps(dict(dependency_claim=claim, result={'rows': [1, 0]})) + '\n').encode())
            finished = taking.finish(stage, code)
            entries = [store.get(path.stem) for path in store.directory.glob('*.json')]
            def stored(item):
                return next((entry['dependency'] for entry in entries if isinstance(entry, dict) and
                             entry.get('dependency', {}).get('item_id') == item), None)
            return finished, stored(identity), stored(C['identity']('stage', stage))

        finished, shared_suite, shared_stage = traced_stage('shared-fixture', 'fixture,other.py')
        row('native-shared-leg', finished == 0 and shared_suite is not None and not shared_suite['complete']
            and not shared_stage['complete'] and 'traced suite without dependency claim' in shared_stage['unknown_reason'])
        finished, alone_suite, alone_stage = traced_stage('alone-fixture', 'fixture.py', opened={'data/stage-only'})
        row('suite-no-stage-opens', alone_suite is not None and alone_suite['complete'] and
            'data/stage-only' not in alone_suite['paths'] and 'data/stage-only' in alone_stage['paths'])
        row('native-session', sessions and all(value is True for value in sessions))
        taking = G.TakeOpened(repo, None, 'native-fixture', store=store)
        with patch.object(G.subprocess, 'run', traced_process), patch.dict(
                taking.observer.dependency_module('case_trace'), compatible=lambda authority, suites: True):
            code = taking.run(G.unconfined, repo, 'cat data/child', taking.env(dict(os.environ,
                              VELDO_GATE_LEG='unconfined', VELDO_GATE_UNCONFINED='fixture')), taking.fd)
        suite_identity = C['identity']('suite', 'native-fixture', 'unconfined', 'fixture')
        claim = python_claim(C['sealed'](C['DEPENDENCY'], **{k: v for k, v in complete.items()
            if k not in ('schema', 'record_digest', 'item_id')}, item_id=suite_identity))
        os.write(taking.fd, (json.dumps(dict(dependency_claim=claim, result={'rows': [1, 0]})) + '\n').encode())
        row('native-stage-finish', taking.finish('native-fixture', code) == 0)
        native_entries = [store.get(path.stem) for path in store.directory.glob('*.json')]
        row('native-stage-complete', any(isinstance(entry, dict) and entry.get('dependency', {}).get('item_id') ==
            C['identity']('stage', 'native-fixture') and entry['dependency']['complete'] and
            'data/child' in entry['dependency']['paths'] for entry in native_entries))
        row('native-suite-complete', any(isinstance(entry, dict) and entry.get('dependency', {}).get('item_id') ==
            suite_identity and entry['dependency']['complete'] and 'data/child' in entry['dependency']['paths']
            for entry in native_entries))
        native_result = dict(baseline={'dependency': first}, noop={'dependency': second}, mutant={'dependency': first})
        publish(repo, commit, [case], {'fixture': native_result}, workers, store=store)
        native_entries = [store.get(path.stem) for path in store.directory.glob('*.json')]
        row('native-worker-complete', any(isinstance(entry, dict) and entry.get('result') == native_result and
            entry['dependency']['complete'] for entry in native_entries))

        taking = G.TakeOpened(repo, None, 'forged-fixture', store=store)
        refused = False
        try:
            taking.publish('forged-fixture', 0, [dict(dependency_claim=complete, result=outcome)], [], [], False)
        except G.Invalid:
            refused = True
        taking.finish('forged-fixture', 1)
        row('stage-python-complete', refused)
        taking = G.TakeOpened(repo, None, 'store-failure-fixture', store=BrokenStore())
        row('stage-store-failure', taking.finish('store-failure-fixture', 0) == 0)
        taking = G.TakeOpened(repo, None, 'failed-fixture', store=store)
        row('failed-stage-status', taking.finish('failed-fixture', 7) == 7 and not any(
            (lambda value: value if isinstance(value, dict) else {})(store.get(path.stem)).get('dependency', {}).get('item_id') == C['identity']('stage', 'failed-fixture')
            for path in store.directory.glob('*.json')))
        from unittest.mock import patch
        import ctypes
        import errno
        fake = G.OpenWatch.__new__(G.OpenWatch)
        fake.root, fake.fd, fake.overflowed = repo, -1, False
        fake.libc = SimpleNamespace(inotify_add_watch=lambda *args: -1)
        ctypes.set_errno(errno.ENOSPC)
        fake._watch(repo, False)
        row('watch-failure', fake.overflowed)
        fake.overflowed = False
        def failed_walk(*args, **kwargs):
            kwargs['onerror'](PermissionError('fixture unreadable directory'))
            return []
        with patch.object(G.os, 'walk', failed_walk):
            fake._tree(repo, False)
        row('walk-failure', fake.overflowed)
        (repo / 'dirty').write_text('uncommitted')
        taking = G.TakeOpened(repo, None, 'dirty-fixture', store=store)
        row('dirty-stage', taking.commit == '0' * 40)
        taking.finish('dirty-fixture', 0)
        (repo / 'dirty').unlink()

        taking = G.TakeOpened(repo, None, 'overflow-fixture', store=store)
        real_stop = taking.watch.stop
        def dropped_stop():
            opened, late, overflowed = real_stop()
            return opened, late, True
        taking.watch.stop = dropped_stop
        row('overflow-finish', taking.finish('overflow-fixture', 0) == 0)
        values = [store.get(path.stem) for path in store.directory.glob('*.json')]
        overflow = next(value for value in values if isinstance(value, dict) and value.get('dependency', {}).get('item_id') ==
                        C['identity']('stage', 'overflow-fixture'))
        row('overflow-unknown', not overflow['dependency']['complete'] and
            'lost events' in overflow['dependency']['unknown_reason'])

        # The real shared collector attributes fragments and names their common
        # setup group. Only its installation seam is isolated from preamble rows.
        import ast
        (repo / 'scripts').mkdir()
        for name in ('mutation_observer.py', 'gate_fixtures.py', 'gate_changes.py', 'case_trace.py'):
            shutil.copyfile(authority / 'scripts' / name, repo / 'scripts' / name)
        tree = ast.parse(shared_source.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_dependency_capture')
        namespace = dict(ROOT=repo, Path=Path, sys=sys, os=os, json=json,
                         importlib=__import__('importlib'), __file__=str(repo / 'scripts/suites/shared.py'))
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(shared_source), 'exec'), namespace)
        main = sys.modules['__main__']
        old_ledger = getattr(main, '_LEDGER', None)
        fd = os.open(top / 'suite-ledger', os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        try:
            main._LEDGER = fd
            capture = namespace['_dependency_capture']()
            namespace['__suite_file__'] = 'first.py'
            (repo / 'data/input').read_text()
            capture[0](True)
            namespace['__suite_file__'] = 'second.py'
            (repo / 'data/child').read_text()
            capture[0](False)
            capture[1]()
        finally:
            main._LEDGER = old_ledger
            os.close(fd)
        claims = [json.loads(line) for line in (top / 'suite-ledger').read_text().splitlines()]
        row('suite-attribution', len(claims) == 2 and
            {tuple(c['result']['rows']) for c in claims} == {(1, 0), (0, 1)} and
            all(c['result']['group'] == ['first', 'second'] and
                {'data/input', 'data/child'} <= set(c['dependency_claim']['paths']) and
                not c['dependency_claim']['complete'] for c in claims))

        # The worker binds coordinates before entering confinement. Store writes
        # stay with the authority after cleanup, never in this bootstrap seam.
        subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Dmitry Grinberg',
                        '-c', 'user.email=dmitry@bcengi.com', 'commit', '-qm', 'worker fixture'], check=True)
        commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        variables = ('VELDO_DEPENDENCY_COMMIT', 'VELDO_DEPENDENCY_LEG')
        saved = {name: os.environ.get(name) for name in variables}
        try:
            for leg in ('confined', 'unconfined'):
                W.dependency_context(repo, 'worker' if leg == 'confined' else leg)
                row('worker-' + leg, os.environ['VELDO_DEPENDENCY_COMMIT'] == commit and
                    os.environ['VELDO_DEPENDENCY_LEG'] == leg)
            (repo / 'dirty-worker').write_text('uncommitted')
            W.dependency_context(repo, 'worker')
            row('dirty-worker', os.environ['VELDO_DEPENDENCY_COMMIT'] == '0' * 40)
            (repo / 'dirty-worker').unlink()
        finally:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value



_v367_observer()
