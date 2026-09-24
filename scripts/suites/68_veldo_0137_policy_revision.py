"""policy_check reads a VELDO-0050 proof's digest-form spec revision (VELDO-0137).

VELDO-0050 records a proof's accepted spec revision as 'sha256:' and the digest of the exact spec
bytes. policy_check.spec_revision_stale read every revision with int(), so every such proof counted
as stale, and because the check reads every manifest in the repository, one factory proof on trunk
refused every later policy_check run there. The rows drive the real policy_check over a temporary
repository laid from this tree's own .veldo/ modules.
"""
import importlib.util as _p137_ilu
import json as _p137_json
import shutil as _p137_shutil
import tempfile as _p137_tempfile
from pathlib import Path as _P137Path


def _p137_load(name, path):
    spec = _p137_ilu.spec_from_file_location(name, path)
    mod = _p137_ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_git_process = _p137_load('p137_git', ROOT / '.veldo' / 'git_process.py')
_P137_ID = ('Veldo Suite', 'suite@example.invalid')


def _p137_suite():
    with _p137_tempfile.TemporaryDirectory(prefix='p137-') as directory:
        repo = _P137Path(directory) / 'repo'
        (repo / '.veldo').mkdir(parents=True)
        for source in sorted((ROOT / '.veldo').glob('*.py')):
            _p137_shutil.copyfile(source, repo / '.veldo' / source.name)
        # The module under test, from its production anchor (the mutation driver points it at each mutant).
        _p137_shutil.copyfile(ROOT / ".veldo" / "policy_check.py", repo / '.veldo' / 'policy_check.py')
        (repo / 'specs').mkdir()
        (repo / 'proof' / 'VELDO-9137').mkdir(parents=True)
        (repo / 'proof' / 'VELDO-9138').mkdir(parents=True)

        def git(*args):
            return _git_process.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True,
                                    identity=_P137_ID).stdout.strip()

        def spec(sid, revision, tail=''):
            body = ('---\nschema: veldo.spec/v1\nid: %s\ntitle: fixture\nstatus: ready\nrisk: standard\nowner: dmitry\n'
                    'human_approval: not_required\nlane: standalone\nrevision: %d\nprotected_paths: []\n'
                    'acceptance_criteria:\n  - id: AC1\n    text: a fixture criterion\n'
                    '    falsified_by: a fixture falsifier\nrequired_evidence: [unit]\nrollback: revert\n---\n\n'
                    '## Intent\n\nFixture.\n%s' % (sid, revision, tail))
            path = repo / 'specs' / ('%s-fixture.md' % sid)
            path.write_text(body)
            return path

        def manifest(sid, commit, revision):
            (repo / 'proof' / sid / 'manifest.json').write_text(_p137_json.dumps(
                {'schema': 'veldo.proof/v1', 'spec_id': sid, 'commit': commit, 'spec_revision': revision}))

        def stale():
            PC = _p137_load('p137_policy_%d' % stale.calls, repo / '.veldo' / 'policy_check.py')
            stale.calls += 1
            return sorted(PC.spec_revision_stale())
        stale.calls = 0

        git('init', '-q')
        spec_path = spec('VELDO-9137', 1)
        spec('VELDO-9138', 1)
        git('add', '-A')
        git('commit', '-q', '-m', 'the accepted specs')
        accepted = git('rev-parse', 'HEAD')
        import hashlib as _p137_hash
        digest = 'sha256:' + _p137_hash.sha256(spec_path.read_bytes()).hexdigest()

        # A digest-form proof bound to the spec at its own commit, beside an integer-form proof.
        manifest('VELDO-9137', accepted, digest)
        manifest('VELDO-9138', accepted, 1)
        fresh = stale()
        # A later edit that raises nothing (a History line at landing) leaves it current.
        spec('VELDO-9137', 1, '\n## History\n\n2026-09-24: landed.\n')
        git('commit', '-q', '-am', 'a History line at landing')
        after_history = stale()
        # Raising the spec's declared revision makes it stale, as for the integer form.
        spec('VELDO-9137', 2)
        spec('VELDO-9138', 2)
        raised = stale()
        spec('VELDO-9137', 1)
        spec('VELDO-9138', 1)
        # A digest that names no committed spec, a short commit and an absent commit are stale.
        manifest('VELDO-9137', accepted, 'sha256:' + '0' * 64)
        wrong_digest = stale()
        manifest('VELDO-9137', accepted[:12], digest)
        short_commit = stale()
        manifest('VELDO-9137', 'f' * 40, digest)
        absent_commit = stale()
        # A spec committed without readable front matter, bound by the digest of those exact bytes.
        bare = repo / 'specs' / 'VELDO-9137-fixture.md'
        bare.write_text('schema: veldo.spec/v1\nid: VELDO-9137\nrevision: 1\n---\n\nno opening marker\n')
        git('commit', '-q', '-am', 'a spec with no readable front matter')
        bare_commit = git('rev-parse', 'HEAD')
        bare_digest = 'sha256:' + _p137_hash.sha256(bare.read_bytes()).hexdigest()
        spec('VELDO-9137', 1)  # the working tree readable again: only the committed spec is bare
        manifest('VELDO-9137', bare_commit, bare_digest)
        no_front_matter = stale()
        observed = {'fresh': fresh, 'after_history': after_history, 'raised': raised, 'wrong_digest': wrong_digest,
                    'short_commit': short_commit, 'absent_commit': absent_commit, 'no_front_matter': no_front_matter}
        globals()['_P137_OBSERVED'] = observed
        expect('VELDO-0137 policy/digest-revision-current: a VELDO-0050 proof whose digest is the spec committed at '
               'its own commit is current, before and after a History-only edit, beside a current integer proof',
               fresh == [] and after_history == [])
        expect('VELDO-0137 policy/digest-revision-stale: raising the declared revision makes both forms stale, and a '
               'digest naming no committed spec, a short commit id, an absent commit and a spec with no readable front '
               'matter at the commit are each stale',
               raised == ['VELDO-9137', 'VELDO-9138'] and wrong_digest == ['VELDO-9137']
               and short_commit == ['VELDO-9137'] and absent_commit == ['VELDO-9137']
               and no_front_matter == ['VELDO-9137'])


_p137_suite()
