"""VELDO-0304 boundary and planted-work rows. Only fixture repositories are used."""


def _v304_suite():
    import importlib.util
    from pathlib import Path
    import tempfile
    import traceback
    import shutil

    PRODUCTION = {
        '.veldo/action_executor.py': ROOT / ".veldo" / "action_executor.py",
        '.veldo/control_agent_config_handoff.py': ROOT / ".veldo" / "control_agent_config_handoff.py",
        '.veldo/control_api_webauthn.py': ROOT / ".veldo" / "control_api_webauthn.py",
        '.veldo/control_batch.py': ROOT / ".veldo" / "control_batch.py",
        '.veldo/control_clone.py': ROOT / ".veldo" / "control_clone.py",
        '.veldo/control_launch.py': ROOT / ".veldo" / "control_launch.py",
        '.veldo/control_launch_work.py': ROOT / ".veldo" / "control_launch_work.py",
        '.veldo/control_memory_check.py': ROOT / ".veldo" / "control_memory_check.py",
        '.veldo/control_repository_provisioner.py': ROOT / ".veldo" / "control_repository_provisioner.py",
        '.veldo/control_service.py': ROOT / ".veldo" / "control_service.py",
        '.veldo/control_space_remove.py': ROOT / ".veldo" / "control_space_remove.py",
        '.veldo/control_space_spool.py': ROOT / ".veldo" / "control_space_spool.py",
        '.veldo/fleet.py': ROOT / ".veldo" / "fleet.py",
        '.veldo/lander.py': ROOT / ".veldo" / "lander.py",
        '.veldo/pack_conformance.py': ROOT / ".veldo" / "pack_conformance.py",
        'scripts/check_space_boundary.py': ROOT / "scripts" / "check_space_boundary.py",
        'scripts/gate_legs.py': ROOT / "scripts" / "gate_legs.py",
        'scripts/migrate_to_veldo.py': ROOT / "scripts" / "migrate_to_veldo.py",
        'scripts/mutation_ownership.py': ROOT / "scripts" / "mutation_ownership.py",
        'scripts/parser_corpus_audit.py': ROOT / "scripts" / "parser_corpus_audit.py",
        'scripts/publish.py': ROOT / "scripts" / "publish.py",
        'scripts/rename_migration.py': ROOT / "scripts" / "rename_migration.py",
        'scripts/render_pdfs.py': ROOT / "scripts" / "render_pdfs.py",
        'scripts/verify.sh': ROOT / "scripts" / "verify.sh",
    }

    def source_path(relative):
        return PRODUCTION.get(relative, ROOT / relative)

    installation = None
    changed = {relative: path for relative, path in PRODUCTION.items()
               if relative.startswith('.veldo/') and path != ROOT / relative}
    if changed:
        installation = tempfile.TemporaryDirectory(prefix='v304-installed-')
        modules = Path(installation.name) / '.veldo'
        shutil.copytree(ROOT / '.veldo', modules, ignore=shutil.ignore_patterns('__pycache__'))
        for relative, source in changed.items():
            shutil.copyfile(source, Path(installation.name) / relative)

    def load(label, path):
        if installation is not None and (ROOT / '.veldo' / path.name).is_file():
            path = Path(installation.name) / '.veldo' / path.name
        spec = importlib.util.spec_from_file_location('v304_' + label, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    boundary = load('boundary', source_path('scripts/check_space_boundary.py'))
    git_process = load('git', source_path('.veldo/git_process.py'))
    fleet = load('fleet', source_path('.veldo/fleet.py'))

    def row(label, operation):
        try:
            operation()
            expect('VELDO-0304 ' + label, True)
        except Exception:
            expect('VELDO-0304 ' + label + ': ' + traceback.format_exc()[-1800:], False)

    def git(where, *args):
        return git_process.run(['git', '-C', str(where), *args], capture_output=True,
                               text=True, check=True, identity=('Fixture', 'fixture@example.invalid')).stdout.strip()

    def fleet_work():
        with tempfile.TemporaryDirectory(prefix='v304-fleet-') as temporary:
            base = Path(temporary)
            main = base / 'main'
            main.mkdir()
            git(main, 'init', '-q', '-b', 'main')
            (main / 'base').write_text('base\n')
            git(main, 'add', '.')
            git(main, 'commit', '-q', '-m', 'base')
            worker = fleet.WorktreeProvisioner(main, str(base / 'workers'))
            path = Path(worker.add('unique'))
            (path / 'unique').write_text('only this worktree has this work\n')
            git(path, 'add', '.')
            git(path, 'commit', '-q', '-m', 'unique')
            tip = git(path, 'rev-parse', 'HEAD')
            (path / 'draft').write_bytes(b'not in git\n')
            answer = worker.remove(str(path))
            assert answer['deferral'] == 'not_in_ledger', answer
            assert (path / 'draft').read_bytes() == b'not in git\n'
            assert git(path, 'rev-parse', 'HEAD') == tip
            assert worker.deferred[-1] == answer

    def fleet_boundary():
        for path in ('.veldo/fleet.py', 'engine/.veldo/fleet.py'):
            errors = boundary.problems(source_path(path).read_text(), path)
            assert not [error for error in errors if 'WorktreeProvisioner.remove:' in error], errors

    row('fleet/unique-work', fleet_work)
    row('fleet/boundary', fleet_boundary)

    def ref_keep():
        from types import SimpleNamespace
        remove = load('remove', source_path('.veldo/control_space_remove.py'))
        with tempfile.TemporaryDirectory(prefix='v304-ref-') as temporary:
            main = Path(temporary)
            git(main, 'init', '-q', '-b', 'main')
            (main / 'work').write_text('only copy\n')
            git(main, 'add', '.')
            tree = git(main, 'write-tree')
            tip = git(main, 'commit-tree', tree, '-m', 'unique commit')
            ref = 'refs/veldo/batch/test'
            git(main, 'update-ref', ref, tip)
            answer = remove.remove_ref(main, ref)
            assert not answer['ok'] and git(main, 'rev-parse', ref) == tip
            kept = 'refs/veldo/kept/none/fixture/1/head'
            record = {'kind': 'agent_repository', 'owner': {'ticket': 'VELDO-0304'},
                      'state': 'removed', 'due': {'event': 'run_finished'},
                      'kept': {'repository': str(main), 'refs': {kept: tip}, 'snapshots': [],
                               'attempt': {'number': 1, 'head': tip}}}
            # The journal's returned record is a stand-in; all git and keep verification are real.
            ledger = SimpleNamespace(item=lambda identity: record, main_repository=lambda identity: str(main))
            answer = remove.remove_ref(main, ref, ledger, 'fixture')
            assert not answer['ok'] and git(main, 'rev-parse', ref) == tip, answer
            git(main, 'update-ref', kept, tip)
            record['owner_keep'] = {'by': 'owner'}
            assert not remove.remove_ref(main, ref, ledger, 'fixture')['ok']
            record.pop('owner_keep')
            answer = remove.remove_ref(main, ref, ledger, 'fixture')
            assert answer['ok'], answer
            assert git(main, 'for-each-ref', '--format=%(refname)', ref) == ''
            assert git(main, 'rev-parse', kept) == tip
            assert git(main, 'show', kept + ':work') == 'only copy'

    row('ref/keep-before-delete', ref_keep)

    def clone_work():
        clones = load('clones', source_path('.veldo/control_clone.py'))
        with tempfile.TemporaryDirectory(prefix='v304-clone-') as temporary:
            root = Path(temporary)
            work = root / 'work'
            work.mkdir()
            git(work, 'init', '-q', '-b', 'main')
            (work / 'unique').write_text('unique clone commit\n')
            git(work, 'add', '.')
            tip = git(work, 'commit-tree', git(work, 'write-tree'), '-m', 'unique')
            ref = 'refs/veldo/pins/fixture/repository'
            git(work, 'update-ref', ref, tip)
            obj = object.__new__(clones.Clones)
            obj.space = None
            answer = obj._release(work, ref)
            assert not answer['ok'] and git(work, 'rev-parse', ref) == tip, answer
            (work / 'draft').write_bytes(b'only copy of clone draft\n')
            looked, released = obj._standalone(root, work, [{'cache': str(work), 'ref': ref}], work, None)
            assert not released and all(entry['deferral'] == 'not_in_ledger' for entry in looked)
            assert (work / 'draft').read_bytes() == b'only copy of clone draft\n'
            assert git(work, 'show', ref + ':unique') == 'unique clone commit'

    def module_boundary(module, functions):
        for prefix in ('.veldo/', 'engine/.veldo/'):
            path = prefix + module + '.py'
            errors = boundary.problems(source_path(path).read_text(), path)
            assert not [error for error in errors if any(function + ':' in error for function in functions)], errors

    row('clone/unique-work', clone_work)
    row('clone/boundary', lambda: module_boundary('control_clone', ('Clones._release', 'Clones._standalone')))

    def batch_work():
        from types import SimpleNamespace
        batch = load('batch', source_path('.veldo/control_batch.py'))
        with tempfile.TemporaryDirectory(prefix='v304-batch-') as temporary:
            main = Path(temporary)
            git(main, 'init', '-q', '-b', 'main')
            (main / 'unique').write_text('unique staged commit\n')
            git(main, 'add', '.')
            tip = git(main, 'commit-tree', git(main, 'write-tree'), '-m', 'unique')
            ref = 'refs/veldo/batch/fixture'
            git(main, 'update-ref', ref, tip)
            obj = object.__new__(batch.Batch)
            obj.record = {'id': 'fixture', 'tip': tip, 'watermark': '0' * 40, 'clone': str(main)}
            obj.destination, obj.trunk, obj.repo_root = 'local', 'main', str(main)
            obj.space = None
            # The trunk swap is refused. The production finally block releases the staging ref.
            obj._git = lambda *args, **kwargs: SimpleNamespace(returncode=1, stderr='fixture refusal')
            obj._read_trunk = lambda: ('0' * 40, True)
            try:
                obj._swap()
            except batch.Refused:
                pass
            assert not obj.record['ref_outcomes'][ref]['ok']
            assert git(main, 'rev-parse', ref) == tip
            assert git(main, 'show', ref + ':unique') == 'unique staged commit'

    row('batch/unique-work', batch_work)
    row('batch/boundary', lambda: module_boundary('control_batch', ('Batch._swap',)))

    def scaffold_work():
        provisioner = load('provisioner', source_path('.veldo/control_repository_provisioner.py'))
        with tempfile.TemporaryDirectory(prefix='v304-scaffold-') as temporary:
            main = Path(temporary)
            git(main, 'init', '-q', '-b', 'main')
            (main / 'unique').write_text('unique scaffold commit\n')
            git(main, 'add', '.')
            tip = git(main, 'commit-tree', git(main, 'write-tree'), '-m', 'unique')
            repository = 'fixture'
            ref = provisioner.SCAFFOLD_REF + repository
            git(main, 'update-ref', ref, tip)
            assert not provisioner.remove_scaffold_ref(str(main), repository)
            assert git(main, 'rev-parse', ref) == tip
            assert git(main, 'show', ref + ':unique') == 'unique scaffold commit'

    row('scaffold/unique-work', scaffold_work)
    row('scaffold/boundary', lambda: module_boundary('control_repository_provisioner', ('remove_scaffold_ref',)))

    def launch_work():
        from unittest.mock import patch
        launch = load('launch', source_path('.veldo/control_launch.py'))
        with tempfile.TemporaryDirectory(prefix='v304-launch-') as temporary:
            receiver = object.__new__(launch.Receiver)
            path = Path(temporary) / 'receiver'
            path.mkdir()
            draft = path / 'draft'
            draft.write_bytes(b'only receiver copy\n')
            receiver.run, receiver.space, receiver.supervision = str(path), None, {'empty': True}
            receiver._unstage_skills = lambda: None
            receiver._remove_run()
            assert receiver.run_removal['deferral'] == 'not_in_ledger'
            assert draft.read_bytes() == b'only receiver copy\n'
            runner = object.__new__(launch.Runner)
            runner.runs, runner.space, runner.profile = temporary, None, None
            runner.leftovers = {'fixture': {'group': {}, 'process': {}}}
            runner.observations = []
            place = Path(launch.run_directory(runner.runs, 'fixture'))
            place.mkdir(parents=True)
            (place / 'draft').write_bytes(b'only sweep copy\n')
            with patch.object(launch.C, 'retirement', return_value={'terminated': True, 'cleaned': True}):
                assert runner.clear_runs() == []
            assert runner.observations[-1]['space']['deferral'] == 'not_in_ledger'
            assert (place / 'draft').read_bytes() == b'only sweep copy\n'

    row('launch/unique-work', launch_work)
    row('launch/boundary', lambda: module_boundary('control_launch', ('Runner.clear_runs', 'Receiver._remove_run')))

    def runtime_work():
        from types import SimpleNamespace
        runtime = load('runtime', source_path('.veldo/control_launch_work.py'))
        with tempfile.TemporaryDirectory(prefix='v304-runtime-') as temporary:
            path = Path(temporary) / 'candidate'
            path.mkdir()
            git(path, 'init', '-q', '-b', 'main')
            (path / 'unique').write_text('only candidate work\n')
            git(path, 'add', '.')
            git(path, 'commit', '-q', '-m', 'unique')
            tip = git(path, 'rev-parse', 'HEAD')
            obj = object.__new__(runtime.Runtime)
            obj.candidates, obj.space, obj.kept = [str(path)], None, []
            obj.floor = obj.conn = SimpleNamespace(close=lambda: None)
            obj.close()
            assert obj.kept[-1]['deferral'] == 'not_in_ledger'
            assert git(path, 'rev-parse', 'HEAD') == tip
            assert (path / 'unique').read_text() == 'only candidate work\n'

    row('runtime/unique-work', runtime_work)
    row('runtime/boundary', lambda: module_boundary('control_launch_work', ('Runtime.close',)))

    def lander_work():
        lander = load('lander', source_path('.veldo/lander.py'))
        with tempfile.TemporaryDirectory(prefix='v304-lander-') as temporary:
            base = Path(temporary)
            path, observations = base / 'candidate', base / 'observations'
            path.mkdir()
            observations.mkdir()
            git(path, 'init', '-q', '-b', 'main')
            (path / 'unique').write_text('only landing candidate work\n')
            git(path, 'add', '.')
            git(path, 'commit', '-q', '-m', 'unique')
            tip = git(path, 'rev-parse', 'HEAD')
            (observations / 'proof').write_bytes(b'only proof\n')
            obj = object.__new__(lander.GitLandOps)
            obj.space, obj.observations = None, None
            obj.candidate = {'workspace': str(path), 'observation_dir': str(observations)}
            obj.discard()
            assert not obj.candidate['discarded']
            assert all(value['deferral'] == 'not_in_ledger' for value in obj.candidate['space'].values())
            assert git(path, 'rev-parse', 'HEAD') == tip
            assert (observations / 'proof').read_bytes() == b'only proof\n'

    row('lander/unique-work', lander_work)
    row('lander/boundary', lambda: module_boundary('lander', ('GitLandOps.discard',)))

    def output_work(filename, operation):
        module = load(filename, source_path('scripts/' + filename + '.py'))
        with tempfile.TemporaryDirectory(prefix='v304-output-') as temporary:
            path = Path(temporary) / 'existing'
            path.mkdir()
            (path / 'unique').write_bytes(b'only existing output copy\n')
            try:
                operation(module, path)
            except SystemExit:
                pass
            else:
                raise AssertionError('existing output was not refused')
            assert (path / 'unique').read_bytes() == b'only existing output copy\n'

    def script_boundary(filename, functions):
        path = 'scripts/' + filename + '.py'
        errors = boundary.problems(source_path(path).read_text(), path)
        assert not [error for error in errors if any(function + ':' in error for function in functions)], errors

    row('migration/unique-work', lambda: output_work('migrate_to_veldo', lambda module, path:
                                                   module.build(path, {}, 'path', [])))
    row('migration/boundary', lambda: script_boundary('migrate_to_veldo', ('build',)))
    row('publish/unique-work', lambda: output_work('publish', lambda module, path: module.build(path)))
    row('publish/boundary', lambda: script_boundary('publish', ('build', 'main')))
    row('rename/unique-work', lambda: output_work('rename_migration', lambda module, path: module.verify(path)))
    row('rename/boundary', lambda: script_boundary('rename_migration', ('verify',)))

    def memory_work():
        import sqlite3
        from unittest.mock import patch
        memory = load('memory', source_path('.veldo/control_memory_check.py'))
        with tempfile.TemporaryDirectory(prefix='v304-memory-') as temporary:
            source, target = Path(temporary) / 'source.db', Path(temporary) / 'copy.db'
            with sqlite3.connect(source) as conn:
                conn.execute('CREATE TABLE work (value TEXT)')
                conn.execute('INSERT INTO work VALUES (?)', ('only memory work',))
            with patch.object(memory, 'ATTEMPTS', 1), patch.object(memory, 'idle', return_value=False), patch.object(
                    memory, 'source_uri', return_value=(source.as_uri() + '?mode=ro', True)):
                try:
                    memory.backup(source, target, sleep=lambda seconds: None)
                except memory.M.Refused:
                    pass
                else:
                    raise AssertionError('a changing source was accepted')
            with sqlite3.connect(target) as conn:
                assert conn.execute('SELECT value FROM work').fetchone() == ('only memory work',)

    row('memory/unique-work', memory_work)
    row('memory/boundary', lambda: module_boundary('control_memory_check', ('backup',)))

    def spool_work():
        spool = load('spool', source_path('.veldo/control_space_spool.py'))
        with tempfile.TemporaryDirectory(prefix='v304-spool-') as temporary:
            folder = Path(temporary)
            name = 'fixture.json'
            kept = []
            for value in (b'first unique event\n', b'second unique event\n'):
                (folder / name).write_bytes(value)
                saved = spool.retain_delivered(str(folder), name)
                kept.append((Path(saved), value))
            assert all(path.read_bytes() == value for path, value in kept)
            assert kept[0][0] != kept[1][0] and not (folder / name).exists()

    row('spool/unique-work', spool_work)
    row('spool/boundary', lambda: module_boundary('control_space_spool', ('replay',)))

    def service_work():
        import ast
        import contextlib
        import os
        from types import SimpleNamespace
        source = (source_path('.veldo/control_service.py')).read_text()
        serve = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'serve')
        block = next(node.finalbody for node in ast.walk(serve) if isinstance(node, ast.Try) and any(
            isinstance(call, ast.Call) and ast.unparse(call.func) == 'listener.close'
            for statement in node.finalbody for call in ast.walk(statement)))
        with tempfile.TemporaryDirectory(prefix='v304-service-') as temporary:
            path = Path(temporary) / 'socket'
            path.write_bytes(b'work now at the socket path\n')
            closed = []
            # Execute the production shutdown block. No service or host socket is started.
            exec(compile(ast.Module(body=block, type_ignores=[]), '<service shutdown>', 'exec'),
                 {'notify': lambda message: None, 'listener': SimpleNamespace(close=lambda: closed.append(True)),
                  'service': SimpleNamespace(channel=None), 'contextlib': contextlib, 'os': os,
                  'config': {'socket': str(path)}, 'inode': path.stat().st_ino})
            assert closed == [True] and path.read_bytes() == b'work now at the socket path\n'

    row('service/unique-work', service_work)
    row('service/boundary', lambda: module_boundary('control_service', ('serve',)))

    def mutation_work():
        ownership = load('ownership', source_path('scripts/mutation_ownership.py'))
        with tempfile.TemporaryDirectory(prefix='v304-meter-') as temporary:
            path = Path(temporary) / 'group'
            path.mkdir()
            (path / 'cgroup.events').write_text('populated 0\n')
            (path / 'unique').write_bytes(b'not a disposable kernel directory\n')
            meter = object.__new__(ownership.WorkerMeter)
            meter.dropins, meter.retained, meter.accounting_slice = [], {}, None
            meter.peer = meter.lifecycle = None
            meter.path = path
            try:
                meter.close()
            except OSError:
                pass
            else:
                raise AssertionError('a nonempty ordinary directory was removed')
            assert (path / 'unique').read_bytes() == b'not a disposable kernel directory\n'

    row('mutation/unique-work', mutation_work)
    row('mutation/boundary', lambda: script_boundary('mutation_ownership', ('WorkerMeter.close',)))

    def render_work():
        import ast
        source = (source_path('scripts/render_pdfs.py')).read_text()
        main = next(node for node in ast.parse(source).body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'main')
        context = next(node for node in ast.walk(main) if isinstance(node, ast.With)).items[0].context_expr
        with tempfile.TemporaryDirectory(prefix='v304-render-') as temporary:
            external = Path(temporary) / 'unique'
            external.write_bytes(b'work outside the browser profile\n')
            manager = eval(compile(ast.Expression(body=context), '<production browser profile>', 'eval'),
                           {'tempfile': tempfile})
            with manager as directory:
                assert Path(directory).name.startswith('veldo-pdf-')
                (Path(directory) / 'browser-scratch').write_text('rebuildable scratch')
            assert not Path(directory).exists()
            assert external.read_bytes() == b'work outside the browser profile\n'

    row('render/owned-temporary', render_work)
    row('render/boundary', lambda: script_boundary('render_pdfs', ('main',)))

    repository_cache = []

    def repository_errors():
        if not repository_cache:
            repository_cache.append(boundary.check(ROOT, read=lambda path:
                                                   source_path(str(path.relative_to(ROOT))).read_text()))
        return repository_cache[0]

    def repository_boundary(category=None):
        errors = repository_errors()
        if category is not None:
            errors = [error for error in errors if category in error]
        assert not errors, errors

    def creation_forms():
        forms = [
            "git('worktree', 'add', path)",
            "subprocess.run(['git', 'worktree', 'add', path])",
            "tempfile.mkdtemp(prefix='new-')",
            "client.containers.run('image')",
            "client.volumes.create('new')",
            "client.networks.create('new')",
            "client.images.build(path='.')",
        ]
        for command in forms:
            errors = boundary.problems('def new_creator(path):\n    ' + command + '\n', 'engine/.veldo/new.py')
            assert any('new_creator:' in error and 'create:' in error for error in errors), command
        assert boundary.problems('create_new() {\n git worktree add "$1"\n}\n', 'scripts/new.sh')
        # Prose and comments are not executable calls.
        assert not boundary.problems('def documentation():\n    """git worktree add; shutil.rmtree(x)"""\n',
                                     'engine/.veldo/new.py')

    def removal_forms():
        forms = [
            "shutil.rmtree(path)",
            "git('worktree', 'remove', path)",
            "git('update-ref', '-d', ref)",
            "git('branch', '-D', ref)",
            "git('stash', 'drop')", "git('stash', 'clear')",
            "git('reflog', 'expire', ref)", "git('prune')",
            "subprocess.run('rm -rf /fixture', shell=True)",
            "client.volumes.get('fixture').remove()",
            "docker('volume', 'rm', 'fixture')",
        ]
        for command in forms:
            errors = boundary.problems('def new_remover(path):\n    ' + command + '\n', 'engine/.veldo/new.py')
            assert errors, command
        assert boundary.problems('import shutil as s\ndef new(path):\n    s.rmtree(path)\n', 'scripts/new.py')
        assert boundary.problems('from shutil import rmtree as wipe\ndef new(path):\n    wipe(path)\n',
                                 'scripts/new.py')
        assert boundary.problems('def new(path):\n    wipe = shutil.rmtree\n    wipe(path)\n', 'scripts/new.py')
        assert boundary.problems('def new(path):\n    return lambda: shutil.rmtree(path)\n', 'scripts/new.py')
        assert boundary.problems('new() {\n rm -rf "$1"\n}\n', 'scripts/new.sh')
        # A reviewed folder remover cannot expire objects or drop stashes.
        for command in ("git('stash', 'drop')", "git('reflog', 'expire', ref)", "git('prune')"):
            assert boundary.problems('def remove_ref():\n    ' + command + '\n',
                                     'engine/.veldo/control_space_remove.py')

    def stale_entries():
        path = 'scripts/example.py'
        reviewed = {(path, 'removed_function'): 'The call owns its temporary tree.'}
        errors = boundary.problems('def removed_function():\n    pass\n', path, reviewed=reviewed)
        assert any('stale reviewed entry' in error for error in errors), errors
        errors = boundary.problems('def removed_function():\n    shutil.rmtree(path)\n', path,
                                   reviewed={(path, 'removed_function'): ''})
        assert any('missing reason' in error for error in errors), errors
        assert all(function and reason for (_, function), reason in boundary.REVIEWED.items())
        with tempfile.TemporaryDirectory(prefix='v304-empty-') as empty:
            assert any('stale reviewed entry, file absent' in error for error in boundary.check(Path(empty)))

    def age_forms():
        for action in ('path.unlink()', 'os.remove(path)', 'shutil.rmtree(path)',
                       'remove_ref(repo, ref)', 'space_signal(space, event, paths, emitter)'):
            for timing in ('path.stat().st_mtime', 'os.path.getmtime(path)',
                           'time.time() > deadline', 'time.monotonic() > deadline'):
                source = 'def prune_times(path):\n    observed = ' + timing + '\n    ' + action + '\n'
                errors = boundary.problems(source, 'scripts/new.py',
                                           reviewed={('scripts/new.py', 'prune_times'): 'An alleged exception.'})
                assert any('removal reads a file time or compares the clock' in error for error in errors), source
        indirect = 'def cleanup(path):\n    started = time.monotonic()\n    deadline = started + 30\n    if deadline > 40:\n        path.unlink()\n'
        assert any('compares the clock' in error for error in boundary.problems(indirect, 'scripts/new.py'))
        unrelated = 'def cleanup(path):\n    worker = Worker(time.monotonic())\n    if worker is not None:\n        path.unlink()\n'
        assert not boundary.problems(unrelated, 'scripts/new.py')
        assert not boundary.problems('def read_resources(path):\n    return path.stat().st_mtime\n', 'scripts/new.py')

    def gate_wired():
        source = source_path('scripts/verify.sh').read_text()
        assert 'CHECK_extra="required:bash scripts/check_template_sync.sh && python3 scripts/check_space_boundary.py"' in source

    row('ac1/forms', creation_forms)
    row('ac1/repository', lambda: repository_boundary('create:'))
    row('ac2/forms', removal_forms)
    row('ac2/repository', lambda: repository_boundary('remove:'))
    row('ac3/stale-entries', stale_entries)
    row('ac4/forms', age_forms)
    row('ac4/repository', lambda: repository_boundary('removal reads'))
    row('integration/boundary', repository_boundary)
    row('integration/gate-wired', gate_wired)
    if installation is not None:
        installation.cleanup()


_v304_suite()
