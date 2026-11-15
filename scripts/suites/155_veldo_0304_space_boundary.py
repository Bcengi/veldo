"""VELDO-0304 boundary and planted-work rows. Only fixture repositories are used."""


def _v304_suite():
    import importlib.util
    from pathlib import Path
    import tempfile
    import traceback

    def load(label, path):
        spec = importlib.util.spec_from_file_location('v304_' + label, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    boundary = load('boundary', ROOT / 'scripts/check_space_boundary.py')
    git_process = load('git', ROOT / '.veldo/git_process.py')
    fleet = load('fleet', ROOT / '.veldo/fleet.py')

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
            errors = boundary.problems((ROOT / path).read_text(), path)
            assert not [error for error in errors if 'WorktreeProvisioner.remove:' in error], errors

    row('fleet/unique-work', fleet_work)
    row('fleet/boundary', fleet_boundary)

    def ref_keep():
        from types import SimpleNamespace
        remove = load('remove', ROOT / '.veldo/control_space_remove.py')
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
        clones = load('clones', ROOT / '.veldo/control_clone.py')
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
            errors = boundary.problems((ROOT / path).read_text(), path)
            assert not [error for error in errors if any(function + ':' in error for function in functions)], errors

    row('clone/unique-work', clone_work)
    row('clone/boundary', lambda: module_boundary('control_clone', ('Clones._release', 'Clones._standalone')))

    def batch_work():
        from types import SimpleNamespace
        batch = load('batch', ROOT / '.veldo/control_batch.py')
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
        provisioner = load('provisioner', ROOT / '.veldo/control_repository_provisioner.py')
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
        launch = load('launch', ROOT / '.veldo/control_launch.py')
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
        runtime = load('runtime', ROOT / '.veldo/control_launch_work.py')
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
        lander = load('lander', ROOT / '.veldo/lander.py')
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
        module = load(filename, ROOT / 'scripts' / (filename + '.py'))
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
        errors = boundary.problems((ROOT / path).read_text(), path)
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
        memory = load('memory', ROOT / '.veldo/control_memory_check.py')
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
        spool = load('spool', ROOT / '.veldo/control_space_spool.py')
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


_v304_suite()
