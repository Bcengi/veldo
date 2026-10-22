"""The repository provisioner's adoption steps (VELDO-0161): the remote owner check, the scaffold as one
recorded commit, and its push under the repository identity.

BEFORE THE OWNER ANSWERS (prepare). For an existing repository the owner names and the identity he chose,
the provisioner checks the remote's owner against the identity with VELDO-0153's one owner check
(control_git_identity_transport.check_remote, operation `adoption`), refusing binding_mismatch:remote_owner
before anything is written; reads the repository's default branch and its tip; and, when the tree at that
tip lacks any of the scaffold's required substrate (init_scaffold.REQUIRED_SUBSTRATE), lays the scaffold as
ONE commit on top of the tip, authored by the identity, in a private clone, and records it in the
repository under SCAFFOLD_REF (never on a branch, never pushed). The proposal it returns names that commit,
so the owner's answer approves exactly the commit that will be pushed; a repository that carries the
scaffold gets a proposal whose scaffold commit is None and nothing is committed.

Every local Git step runs under git_process's isolated profile with no hook of the repository.

ON HIS SETTLED ANSWER (scaffold_problems, advance, push). The effect checks that the commit the proposal
names is the one recorded under SCAFFOLD_REF, that its one parent is the proposal's base, that it only adds
files and that the substrate is complete at it; fast-forwards the default branch to it (refused by name
when the branch moved or the working tree is in the way); and pushes it through git_process's `identity`
profile (VELDO-0153) to the literal remote URL the owner check accepted, with a lease on the base, then
reads the remote's branch back. A rejected push is push_refused:remote.

Standard library only; organs are loaded as siblings by path.
"""
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile


def organ(name):
    spec = importlib.util.spec_from_file_location('provisioner_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GP = organ('git_process')
R = organ('control_repository')
CE = R.CE
GI = R.GI
Refused = R.Refused
SCAFFOLD_REF = 'refs/veldo/adoption/'
STEP_SECONDS = 60


def _scaffold_module():
    return organ('init_scaffold')


def git(path, *args, check=True, **kwargs):
    """One local Git step in `path` under the isolated profile, running no hook of the repository (as no
    identity push does, VELDO-0153)."""
    done = GP.run(['git', '-C', str(path), '-c', 'core.hooksPath=' + os.devnull, *args], capture_output=True,
                  text=True, timeout=STEP_SECONDS, **kwargs)
    if check and done.returncode:
        raise Refused('invalid_input:git', '%s: %s' % (args[0], done.stderr.strip()[:200]))
    return done


def identity_record(conn, domain, identity):
    """The configured Git identity `identity` of `domain` (VELDO-0142), never one inferred from Git."""
    for record in GI.records(conn, domain):
        if record['id'] == identity:
            return record
    raise Refused('missing_authority:git_identity', str(identity))


def check_remote(record, remote, repository=None, request=None, observe=None):
    """VELDO-0153's one owner check, operation `adoption`; its refusal code is kept (binding_mismatch:...)."""
    transport = GP.identity_transport()
    try:
        return transport.check_remote(record, remote, operation='adoption', repository=repository,
                                      request=request, observe=observe)
    except transport.Refused as error:
        raise Refused(error.code) from None


def repository_state(path):
    """{path, branch, head} of the repository whose top level `path` is, refused by name otherwise."""
    path = os.path.realpath(str(path))
    top = git(path, 'rev-parse', '--show-toplevel', check=False)
    if top.returncode or os.path.realpath(top.stdout.strip()) != path:
        raise Refused('invalid_input:not_a_repository', path)
    branch = git(path, 'symbolic-ref', '--quiet', '--short', 'HEAD', check=False)
    if branch.returncode or not branch.stdout.strip():
        raise Refused('invalid_input:detached_head', path)
    head = git(path, 'rev-parse', '--verify', '--quiet', 'HEAD^{commit}', check=False)
    if head.returncode:
        raise Refused('invalid_input:no_commit', path)
    return {'path': path, 'branch': branch.stdout.strip(), 'head': head.stdout.strip()}


def enrolled(path):
    """Whether the repository already carries a VELDO-0029 binding (adoption never enrolls over one)."""
    try:
        return CE.read_binding(path) is not None or os.path.lexists(CE.binding_path(path))
    except CE.EnrollmentRefused:
        return True


def missing_scaffold(path, commit):
    """The scaffold's required substrate paths absent from the tree at `commit`, in declared order."""
    listed = git(path, 'ls-tree', '-r', '--name-only', '-z', commit)
    present = set(listed.stdout.split('\0'))
    return [rel for rel in _scaffold_module().required_substrate() if rel not in present]


def lay_scaffold(path, base, record, templates, ref):
    """Lay the scaffold as ONE commit whose parent is `base`, authored and committed by the identity, in a
    private clone; record it in the repository under `ref` (no branch moves, nothing is pushed). Returns
    the commit id."""
    work = tempfile.mkdtemp(prefix='veldo-scaffold-')
    try:
        clone = os.path.join(work, 'clone')
        git(work, 'clone', '-q', '--no-hardlinks', '--no-checkout', str(path), clone)
        git(clone, 'checkout', '-q', '--detach', base)
        try:
            _scaffold_module().scaffold(clone, templates=templates)
        except Exception as error:  # noqa: BLE001 - a scaffold that cannot be laid is a named refusal
            raise Refused('invalid_input:scaffold', type(error).__name__) from None
        git(clone, 'add', '-A')
        author = GI.author(record)
        git(clone, '-c', 'commit.gpgsign=false', 'commit', '-q', '--no-verify', '-m',
            'Lay the Veldo scaffold for adoption under identity %s' % record['id'], identity=author)
        commit = git(clone, 'rev-parse', 'HEAD').stdout.strip()
        git(path, 'fetch', '-q', '--no-tags', clone, '+%s:%s' % ('HEAD', ref))
        return commit
    finally:
        shutil.rmtree(work, ignore_errors=True)


def prepare(conn, domain, *, path, identity, remote, name, owner, repository, templates=None, observe=None):
    """The provisioner's steps before the owner answers (module docstring). Returns (proposal, observation)."""
    event = {'operation': 'prepare', 'repository': repository, 'identity': identity, 'path': None}
    try:
        record = identity_record(conn, domain, identity)
        check_remote(record, remote, repository=repository, observe=observe)
        state = repository_state(path)
        event['path'] = state['path']
        if enrolled(state['path']):
            raise Refused('invalid_input:already_enrolled', state['path'])
        scaffold = None
        if missing_scaffold(state['path'], state['head']):
            scaffold = lay_scaffold(state['path'], state['head'], record, templates, SCAFFOLD_REF + repository)
            if missing_scaffold(state['path'], scaffold):
                raise Refused('invalid_input:scaffold_incomplete', state['path'])
        proposal = R.adoption_proposal(repository=repository, name=name, owner=owner, identity=identity,
                                       path=state['path'], remote=remote, default_branch=state['branch'],
                                       base_commit=state['head'], scaffold_commit=scaffold)
    except Refused as error:
        event.update(outcome='refused', refusal=error.code, reason=R.reason(error.code))
        raise
    event.update(outcome='prepared', scaffold_commit=scaffold, base_commit=state['head'])
    return proposal, event


def scaffold_problems(proposal):
    """Why the commit the proposal names is not the one scaffold commit laid for it (empty when it is, or
    when the proposal names none and the repository carries the scaffold at its tip)."""
    path, base, commit = proposal['path'], proposal['base_commit'], proposal['scaffold_commit']
    if commit is None:
        head = git(path, 'rev-parse', '--verify', '--quiet', 'refs/heads/' + proposal['default_branch'], check=False)
        tip = head.stdout.strip() if not head.returncode else None
        if tip is None or missing_scaffold(path, tip):
            return ['stale_subject:scaffold_missing']
        return []
    recorded = git(path, 'rev-parse', '--verify', '--quiet', SCAFFOLD_REF + proposal['repository'], check=False)
    if recorded.returncode or recorded.stdout.strip() != commit:
        return ['stale_subject:scaffold_commit_not_named']
    parents = git(path, 'rev-list', '--parents', '-n', '1', commit).stdout.split()
    if parents[1:] != [base]:
        return ['stale_subject:scaffold_parent']
    changes = git(path, 'diff-tree', '--no-commit-id', '-r', '--name-status', '-z', base, commit).stdout.split('\0')
    if any(status not in ('A', '') for status in changes[0::2]):
        return ['stale_subject:scaffold_changes_files']
    if missing_scaffold(path, commit):
        return ['stale_subject:scaffold_incomplete']
    return []


def advance(proposal):
    """Fast-forward the default branch from the base to the named scaffold commit, in the working tree when
    the branch is checked out. Refused stale_subject:<why> by name, changing nothing, otherwise."""
    path, branch, base, commit = (proposal['path'], proposal['default_branch'], proposal['base_commit'],
                                  proposal['scaffold_commit'])
    tip = git(path, 'rev-parse', '--verify', '--quiet', 'refs/heads/' + branch, check=False).stdout.strip()
    if tip == commit:
        return commit
    if tip != base:
        raise Refused('stale_subject:branch_moved', branch)
    current = git(path, 'symbolic-ref', '--quiet', '--short', 'HEAD', check=False).stdout.strip()
    if current == branch:
        merged = git(path, 'merge', '--ff-only', '-q', commit, check=False)
        if merged.returncode:
            raise Refused('stale_subject:working_tree', merged.stderr.strip()[:200])
    else:
        git(path, 'update-ref', 'refs/heads/' + branch, commit, base)
    return commit


def push(proposal, record, observe=None):
    """Push the named scaffold commit to the default branch of the checked remote URL through the identity
    profile, leased on the base; the remote's branch is read back. Returns the remote tip."""
    path, branch, remote = proposal['path'], proposal['default_branch'], proposal['remote']
    transport = GP.identity_transport()
    ref = 'refs/heads/' + branch

    def run(*args):
        try:
            return GP.run(['git', '-C', path, *args], capture_output=True, text=True, timeout=STEP_SECONDS,
                          profile='identity', push_identity=record, remote_url=remote)
        except transport.Refused as error:
            raise Refused(error.code) from None
    pushed = run('push', '--porcelain', '--force-with-lease=%s:%s' % (ref, proposal['base_commit']), remote,
                 '%s:%s' % (proposal['scaffold_commit'], ref))
    listed = run('ls-remote', remote, ref)
    tip = listed.stdout.split('\t', 1)[0].strip() if not listed.returncode and listed.stdout.strip() else None
    if pushed.returncode or tip != proposal['scaffold_commit']:
        raise Refused('push_refused:remote', (pushed.stderr or '').strip()[:200])
    return tip
