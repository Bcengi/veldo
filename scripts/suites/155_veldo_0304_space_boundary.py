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


_v304_suite()
