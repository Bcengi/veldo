"""The repository provisioner's adoption steps (VELDO-0161): the remote owner check, the scaffold as one
recorded commit, and its push under the repository identity.

BEFORE THE OWNER ANSWERS (prepare). For an existing repository the owner names and the identity he chose,
the provisioner checks that the repository id is one ref component (invalid_input:proposal:repository), checks
the remote's owner against the identity with VELDO-0153's one owner check (control_git_identity_transport.
check_remote, operation `adoption`), refusing binding_mismatch:remote_owner before anything is written; reads
the repository's default branch and its tip; checks that the remote it was given is the one the repository
itself is configured with for that branch (invalid_input:remote_not_configured) and that the repository's own
configuration names no command a local step could run (invalid_input:repository_command:<key>); and, when the tree at that
tip lacks any of the scaffold's required substrate (init_scaffold.REQUIRED_SUBSTRATE), lays the scaffold as
ONE commit on top of the tip, authored by the identity, in a private clone, and records it in the
repository under SCAFFOLD_REF (never on a branch, never pushed). The proposal it returns names that commit,
so the owner's answer approves exactly the commit that will be pushed; a repository that carries the
scaffold gets a proposal whose scaffold commit is None and nothing is committed.

Every local Git step runs under git_process's isolated profile with no hook of the repository and with
core.fsmonitor off. The repository's own configuration is judged against an allowlist (LOCAL_CONFIGURATION):
every key it sets must be one a local step reads as data, never one that names a command (a filter's clean or
smudge, an fsmonitor, core.alternateRefsCommand, an editor, a pager, an ssh command, a URL rewrite, an include)
or a key not known to be data. Anything else is refused by name (invalid_input:repository_command:<key>,
repository_commands), and so is a repository that borrows objects from another (objects/info/alternates,
invalid_input:repository_alternates: a fetch into it runs core.alternateRefsCommand and reads the other
repository's refs), rather than having a command of its own run by the prepare fetch, a checkout or a merge.

ON HIS SETTLED ANSWER (scaffold_problems, advance, push). The effect checks that the commit the proposal
names is the one recorded under SCAFFOLD_REF, that its one parent is the proposal's base, that it only adds
files and that the substrate is complete at it; fast-forwards the default branch to it (refused by name
when the branch moved or the working tree is in the way); and pushes it through git_process's `identity`
profile (VELDO-0153) to the literal remote URL the owner check accepted, with a lease on the base, then
reads the remote's branch back. A rejected push is push_refused:remote; a push Git accepted whose branch
cannot be read back as the commit is push_unconfirmed:remote (it may have landed). The ref the scaffold was
recorded under is removed once the push is done or the adoption refused (remove_scaffold_ref).

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
    done = GP.run(['git', '-C', str(path), '-c', 'core.hooksPath=' + os.devnull, '-c', 'core.fsmonitor=false', *args],
                  capture_output=True, text=True, timeout=STEP_SECONDS, **kwargs)
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


# THE ALLOWLIST: the keys of the repository's own configuration a local step (the prepare fetch and clone, the
# fast-forward's checkout, the push) may find there, by section and name, each read as data and none naming a
# command. A section listed with None allows every name in it. Anything else is refused by name.
LOCAL_CONFIGURATION = {
    'core': ('repositoryformatversion', 'filemode', 'bare', 'logallrefupdates', 'ignorecase', 'precomposeunicode',
             'symlinks', 'autocrlf', 'eol', 'safecrlf', 'checkstat', 'trustctime'),
    'extensions': ('objectformat', 'worktreeconfig', 'refstorage', 'preciousobjects', 'noop'),
    'remote': ('url', 'pushurl', 'fetch', 'push', 'tagopt', 'prune', 'prunetags', 'mirror', 'skipdefaultupdate',
               'skipfetchall'),
    'branch': ('remote', 'pushremote', 'merge', 'rebase', 'description'),
    'user': None, 'author': None, 'committer': None, 'color': None, 'advice': None, 'i18n': None,
    'init': ('defaultbranch',), 'pull': ('rebase', 'ff'), 'push': ('default', 'autosetupremote', 'followtags'),
    'fetch': ('prune', 'prunetags'), 'commit': ('gpgsign',), 'tag': ('gpgsign',),
}


def repository_commands(path):
    """The keys of the repository's own configuration outside LOCAL_CONFIGURATION, any of which could name
    a command a local step would run (a filter's clean, smudge or process command, an fsmonitor,
    core.alternateRefsCommand, an editor, a pager, an ssh command, a URL rewrite, an include) or is not known
    to be data. Read as Git reads it, includes followed; the values this module passes on the command line
    (scope `command`) are not the repository's."""
    listed = git(path, 'config', '--includes', '--show-scope', '--name-only', '-z', '--list', check=False)
    if listed.returncode:
        raise Refused('invalid_input:repository_config', listed.stderr.strip()[:200])
    fields = listed.stdout.split('\0')
    found = []
    for scope, key in zip(fields[0::2], fields[1::2]):
        lowered = key.strip().lower()
        if scope == 'command' or not lowered:
            continue
        section, name = lowered.split('.', 1)[0], lowered.rsplit('.', 1)[-1]
        allowed = LOCAL_CONFIGURATION.get(section, ())
        if '.' not in lowered or (allowed is not None and name not in allowed):
            found.append(lowered)
    return sorted(set(found))


def alternates(path):
    """Whether the repository borrows objects from another (objects/info/alternates in its common
    directory)."""
    listed = git(path, 'rev-parse', '--path-format=absolute', '--git-path', 'objects/info/alternates', check=False)
    if listed.returncode or not listed.stdout.strip():
        raise Refused('invalid_input:repository_config', listed.stderr.strip()[:200])
    return os.path.lexists(listed.stdout.strip())


def refuse_commands(path, code='invalid_input:repository_command'):
    """Refuse, by name, a repository whose own configuration has a key outside LOCAL_CONFIGURATION, or that
    borrows objects from another (`code`'s first part with repository_alternates)."""
    found = repository_commands(path)
    if found:
        raise Refused('%s:%s' % (code, found[0]), ', '.join(found))
    if alternates(path):
        raise Refused('%s:repository_alternates' % code.split(':', 1)[0], 'objects/info/alternates')


def configured_remote(path, branch):
    """The URL of the remote the repository is configured with for `branch` (its upstream remote, else
    origin), or None."""
    name = git(path, 'config', '--get', 'branch.%s.remote' % branch, check=False).stdout.strip() or 'origin'
    url = git(path, 'config', '--get', 'remote.%s.url' % name, check=False)
    return url.stdout.strip() if not url.returncode and url.stdout.strip() else None


def check_configured_remote(path, branch, remote):
    if configured_remote(path, branch) != remote:
        raise Refused('invalid_input:remote_not_configured', 'the repository is not configured with this remote')


def remove_scaffold_ref(path, repository):
    """Remove the ref the scaffold commit was recorded under, when there is one. Never raises."""
    if R.repository_id_problems(repository):
        return False
    try:
        return git(path, 'update-ref', '-d', SCAFFOLD_REF + repository, check=False).returncode == 0
    except Exception:  # noqa: BLE001 - removing the record of a laid commit never decides an outcome
        return False


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
    laid = None
    try:
        problems = R.repository_id_problems(repository)
        if problems:
            raise Refused(problems[0], str(repository))
        record = identity_record(conn, domain, identity)
        check_remote(record, remote, repository=repository, observe=observe)
        state = repository_state(path)
        event['path'] = state['path']
        check_configured_remote(state['path'], state['branch'], remote)
        refuse_commands(state['path'])
        if enrolled(state['path']):
            raise Refused('invalid_input:already_enrolled', state['path'])
        scaffold = None
        if missing_scaffold(state['path'], state['head']):
            scaffold = laid = lay_scaffold(state['path'], state['head'], record, templates, SCAFFOLD_REF + repository)
            if missing_scaffold(state['path'], scaffold):
                raise Refused('invalid_input:scaffold_incomplete', state['path'])
        proposal = R.adoption_proposal(repository=repository, name=name, owner=owner, identity=identity,
                                       path=state['path'], remote=remote, default_branch=state['branch'],
                                       base_commit=state['head'], scaffold_commit=scaffold)
    except Refused as error:
        if laid is not None:
            remove_scaffold_ref(event['path'], repository)
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
        # The checkout a fast-forward makes runs the repository's filters: none may be configured.
        refuse_commands(path, 'stale_subject:repository_command')
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
    if pushed.returncode:
        raise Refused('push_refused:remote', (pushed.stderr or '').strip()[:200])
    if tip != proposal['scaffold_commit']:
        raise Refused('push_unconfirmed:remote', 'the push was accepted; the remote branch reads back as %s' % tip)
    return tip
