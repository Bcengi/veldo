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
               'reuse_worker.py': ROOT / "scripts" / "reuse_worker.py"}

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
        for name in ('gate_fixtures.py', 'gate_changes.py', 'gate_reuse.py', 'case_trace.py'):
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
        (repo / 'data').mkdir()
        (repo / 'data/input').write_text('input')
        (repo / 'data/child').write_text('child')
        (repo / 'module367.py').write_text('value = 367\n')
        (repo / 'alias').symlink_to('data/input')
        for args in (['init', '-q'], ['add', '.'], ['-c', 'user.name=Dmitry Grinberg',
                     '-c', 'user.email=dmitry@bcengi.com', 'commit', '-qm', 'observer fixture']):
            subprocess.run(['git', '-C', str(repo), *args], check=True, stdout=subprocess.PIPE)
        commit = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
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
        row('runtime', dep['runtime_digest'] != O.DependencyReads(repo, {'NEW': 'value'}).record(item, commit)['runtime_digest'])

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
            complete = O.DependencyReads(repo, {}).trace(trace, all_syscalls=True).record(identity, commit)
            row('trace-' + leg, complete['complete'] and complete['unknown_reason'] is None and
                {'data/input', 'module367.py', 'data/child', 'alias'} <= set(complete['paths']) and
                complete['directories'] == ['data'] and complete['absent_paths'] == ['missing'] and
                complete['item_id'] == identity)
        row('filtered-unknown', not O.DependencyReads(repo, {}).trace(trace).record(item, commit)['complete'])
        row('lost-events', not O.DependencyReads(repo, {}).trace(trace, dropped=True, all_syscalls=True).record(item, commit)['complete'])
        trace.write_text('\n'.join(lines[:-2]) + '\n')
        broken = O.DependencyReads(repo, {}).trace(trace, all_syscalls=True).record(item, commit)
        row('incomplete-not-empty', not broken['complete'] and bool(broken['unknown_reason']))
        trace.write_text('11 openat(AT_FDCWD, "data/input", O_RDONLY <unfinished ...>\n11 +++ exited with 0 +++\n')
        row('unfinished', not O.DependencyReads(repo, {}).trace(trace, all_syscalls=True).record(item, commit)['complete'])
        trace.write_text('')
        row('empty-trace', not O.DependencyReads(repo, {}).trace(trace, all_syscalls=True).record(item, commit)['complete'])
        trace.write_text('11 openat(AT_FDCWD, "module367.py", O_RDONLY) = 3\n11 +++ exited with 0 +++\n')
        fresh = O.DependencyReads(repo, {}).trace(trace, all_syscalls=True)
        refreshed = fresh.record(item, commit)
        row('refresh', refreshed['complete'] and refreshed['paths'] == ['module367.py'] and
            refreshed['record_digest'] != complete['record_digest'])
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

        # Real children in either leg's environment are observed by the outside
        # kernel watch, beyond scripts/ and proof/. The dependency remains unknown
        # because inotify cannot attribute metadata probes or certify descendants.
        for leg in ('confined', 'unconfined'):
            taking = G.TakeOpened(repo, None, 'fixture-' + leg, store=store)
            env = taking.env(dict(os.environ, VELDO_GATE_LEG=leg))
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

        taking = G.TakeOpened(repo, None, 'overflow-fixture', store=store)
        real_stop = taking.watch.stop
        def dropped_stop():
            opened, late, overflowed = real_stop()
            return opened, late, True
        taking.watch.stop = dropped_stop
        row('overflow-finish', taking.finish('overflow-fixture', 0) == 0)
        values = [store.get(path.stem) for path in store.directory.glob('*.json')]
        overflow = next(value for value in values if value and value.get('dependency', {}).get('item_id') ==
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
        variables = ('VELDO_DEPENDENCY_COMMIT', 'VELDO_DEPENDENCY_LEG')
        saved = {name: os.environ.get(name) for name in variables}
        try:
            for leg in ('confined', 'unconfined'):
                W.dependency_context(repo, 'worker' if leg == 'confined' else leg)
                row('worker-' + leg, os.environ['VELDO_DEPENDENCY_COMMIT'] == commit and
                    os.environ['VELDO_DEPENDENCY_LEG'] == leg)
        finally:
            for name, value in saved.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value



_v367_observer()
