#!/usr/bin/env python3
"""The probes: the observers the safety rules read (design section 7; VELDO-0299, and for rules 1 and
2 VELDO-0330).

WHAT IS HERE. Functions that look at the host and return facts. None of them decides, defers, removes
or writes: a rule reads the facts and the rule decides (VELDO-0330). Every call looks again; no fact is
kept from an earlier call.

  located(kind, locator)       rule 1: what is at an item's locator now: where its path leads, the
                               repository a worktree there belongs to, the object id a Docker name has
  repository(path)             rule 1: the repository a path belongs to, as its common git folder
  protected(kind, locator, protect)
                               rule 2: the protect entry that covers a locator, and how
  process(pid)                 rule 3: the start time the kernel reports for a process, or None when the
                               kernel no longer shows it
  processes(path)              rule 4: the processes with their working directory, an open file or a
                               mapped file at or beneath the path
  containers(path, engines)    rule 4: the containers, running or stopped, with a bind mount at or
                               beneath the path, on each named engine context
  git_lock(path)               rule 4: the lock files git holds on a worktree
  in_use(path, engines)        rule 4: the three above together
  scratch(path)                rule 4, a sandbox launcher's scratch: its scratch lock and its borrowed
                               login
  unique_work(path, ...)       rule 5: the five cases, read in the worktree
  agent_repository(path, ...)  rule 5: the branches of an agent repository the shared repository does
                               not hold under the same name

WHAT IS AT A LOCATOR (rule 1). For a path: whether anything is there, whether the path itself is a link,
and where the path leads with every link in it followed. A path that leads somewhere else than its own
text goes through a link. For a worktree also the repository the folder is a worktree of now, as that
repository's common git folder; None when the folder is not the top of a worktree. For a Docker object
the id the engine gives the name now: read is False when the engine could not be asked, and id is None
when the engine holds no object of that name or its record carries no id.

THE PROTECT LIST (rule 2). The list is the declarations' (the installation's entries, then each
project's); this module is given it and says whether an entry covers a locator. A path is protected
when it is at an entry, above one (an entry lies beneath it) or beneath one, read as written and where
it leads, against each entry as written and where it leads. A Docker object is protected when, on an
engine the entry names, its name matches a pattern for its type or the compose project its locator
records is a protected one. What an engine itself says of an object (its label, its mounts, its image
and networks) is VELDO-0341.

PROCESS USE is read from the kernel's process table: for each process its cwd link, the links under fd
and the paths in maps. A command line that names the path is not read at all, so it is not use. A
process whose command name is in HELPERS (the file-sharing helper of a desktop container engine, which
holds descriptors on every path a container ever mounted) is not counted: the containers' own mount
lists are read instead. A process this user may not read is counted in unread, not as a user.

CONTAINERS are read through the docker client: the list of all containers of a context, then their
inspect records. A bind mount whose host source is at or beneath the path is use, whatever the
container's state. An engine that cannot be read is named in unread with what the client said.

UNIQUE WORK. The five cases of rule 5, each with what was found; `cases` lists the numbers that hold.
The rule that reads them leaves case 3 out for a review worktree. Case 5 tests the checked-out commit,
which is the tip of the worktree's branch, or of nothing when the worktree is detached:

  - in a worktree of the shared repository itself, against every ref of that repository other than the
    worktree's own branch (a branch always reaches its own tip, so its own ref proves nothing);
  - in an agent's worktree, when `shared` names the shared repository, against the refs of the shared
    repository and of no other: a commit the shared repository does not yet hold is unique;
  - and in both, against `landed`, the source commits the completion receipts of completed landings
    name: a tip that is one of them, or an ancestor of one, is landed. That is the squash landing, whose
    tip the trunk never reaches. The caller reads the receipts; this module opens no store.

File names are returned. File contents never are.

A SANDBOX LAUNCHER'S SCRATCH is in use while a launcher or its confined command holds the lock on the
scratch folder (each holds a shared lock for as long as it runs), or while the journal of its borrowed
login is not settled: the journal folder named for the scratch holds borrow.json and no recovery.json.
The lock is tested by asking for it without waiting and giving it back at once.

THE TEST SEAM. SEAM['after_in_use'], when set, is called with the facts of every in_use call before
they are returned. It is for tests that need something to happen between two probes. Nothing in the
engine sets it.

GIT is run with optional locks off, so a status never writes the index, with the file monitor off, and
with no GIT_ variable of the caller's environment. A repository git cannot read comes back with read
False and what git said; it is never reported as having no unique work.

Standard library only.
"""
import fcntl
import fnmatch
import json
import os
import re
import subprocess

SCHEMA = 'veldo.control_space_probe/v1'

PROC = '/proc'
SECONDS = 60
USES = ('cwd', 'open', 'mapped')
HELPERS = ('virtiofsd',)
NAMED = 20  # the most paths, refs or files named for one process or one case

LOCK_FILES = ('index.lock', 'HEAD.lock', 'config.lock', 'shallow.lock')
OPERATIONS = (('merge', 'MERGE_HEAD'), ('rebase', 'rebase-merge'), ('rebase', 'rebase-apply'),
              ('cherry-pick', 'CHERRY_PICK_HEAD'), ('revert', 'REVERT_HEAD'), ('sequence', 'sequencer'))
COMMIT = re.compile(r'[0-9a-f]{40}([0-9a-f]{24})?')

# The engine's word for each Docker kind, which is also the type of its protect entries.
DOCKER_TYPE = {'container': 'container', 'volume': 'volume', 'network': 'network', 'image_tag': 'image'}

SEAM = {'after_in_use': None}


def _run(argv, cwd=None):
    """Run a client and return (exit code, output). A client that is missing or does not end in time
    gives (None, what happened)."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    environment.update(GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0', LC_ALL='C')
    try:
        done = subprocess.run(argv, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=SECONDS)
    except (OSError, subprocess.SubprocessError) as error:
        return None, type(error).__name__ + ': ' + str(error)[:200]
    if done.returncode:
        return done.returncode, done.stderr.decode('utf-8', 'replace').strip()[-300:]
    return 0, done.stdout.decode('utf-8', 'surrogateescape')


def _git(run, repository, *argv):
    return run(['git', '-c', 'core.fsmonitor=false', '-C', str(repository)] + list(argv))


def _beneath(candidate, root):
    return candidate == root or candidate.startswith(root.rstrip('/') + '/')


# What is at a locator, and the protect list.

def repository(path, run=None):
    """The repository `path` belongs to, as its common git folder with every link followed: the same
    for a repository, for each of its worktrees and for a bare one. None when git reads none there."""
    run = run or _run
    code, folder = _git(run, path, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    return os.path.realpath(folder.rstrip('\n')) if code == 0 and folder.strip() else None


def located(kind, locator, run=None):
    """Rule 1's facts: what is at the locator of an item of `kind` now.

    A path (a branch is read at its repository): {path, exists, link, resolved}, and for a worktree
    repository, the common git folder of the repository the folder is a worktree of, None when it is
    not the top of one. A Docker object: {engine, name, type, read, id, said}."""
    run = run or _run
    if kind in DOCKER_TYPE:
        facts = {'kind': kind, 'engine': locator.get('engine'), 'name': locator.get('name'),
                 'type': DOCKER_TYPE[kind], 'read': False, 'id': None, 'said': None}
        code, out = run(['docker', '--context', str(facts['engine']), facts['type'], 'inspect', str(facts['name'])])
        if code == 0:
            try:
                records = json.loads(out)
            except ValueError:
                records = None
            if isinstance(records, list) and len(records) == 1 and isinstance(records[0], dict):
                found = records[0].get('Id')
                facts.update(read=True, id=found if isinstance(found, str) and found else None)
            else:
                facts['said'] = 'the inspect record is not one JSON record'
        elif code is not None and 'no such' in str(out).lower():
            facts.update(read=True, said=str(out)[:300])
        else:
            facts['said'] = str(out)[:300]
        return facts
    path = locator.get('path') or locator.get('repository')
    facts = {'kind': kind, 'path': path, 'exists': os.path.lexists(path), 'link': os.path.islink(path),
             'resolved': os.path.realpath(path)}
    if kind == 'worktree':
        facts['repository'] = repository(path, run) if _git_folder(run, path) else None
    return facts


def protected(kind, locator, protect):
    """Rule 2's facts: {protected, entry, how}. entry is the covering protect entry as type:value and
    how is at, above or beneath for a path, name or compose_project for a Docker object. `protect` is
    the protect list in force: [{type, value, engines}]."""
    if kind in DOCKER_TYPE:
        for entry in protect:
            if locator.get('engine') not in entry.get('engines', ()):
                continue
            how = None
            if entry['type'] == DOCKER_TYPE[kind] and fnmatch.fnmatchcase(str(locator.get('name')), entry['value']):
                how = 'name'
            elif entry['type'] == 'compose_project' and locator.get('compose_project') == entry['value']:
                how = 'compose_project'
            if how:
                return {'protected': True, 'entry': entry['type'] + ':' + entry['value'], 'how': how}
        return {'protected': False, 'entry': None, 'how': None}
    path = os.path.normpath(locator.get('path') or locator.get('repository'))
    for entry in protect:
        if entry['type'] != 'path':
            continue
        value = os.path.normpath(entry['value'])
        for mine in (path, os.path.realpath(path)):
            for theirs in (value, os.path.realpath(value)):
                how = ('at' if mine == theirs else 'above' if _beneath(theirs, mine)
                       else 'beneath' if _beneath(mine, theirs) else None)
                if how:
                    return {'protected': True, 'entry': 'path:' + entry['value'], 'how': how}
    return {'protected': False, 'entry': None, 'how': None}


# Process use.

def _cwd(base):
    return [os.readlink(os.path.join(base, 'cwd'))]


def _open(base):
    found = []
    for name in os.listdir(os.path.join(base, 'fd')):
        try:
            found.append(os.readlink(os.path.join(base, 'fd', name)))
        except FileNotFoundError:
            continue  # closed meanwhile
    return found


def _mapped(base):
    found = []
    with open(os.path.join(base, 'maps'), 'rb') as maps:
        for line in maps:
            parts = line.rstrip(b'\n').split(None, 5)
            if len(parts) == 6 and parts[5].startswith(b'/'):
                found.append(os.fsdecode(parts[5].replace(b'\\012', b'\n')))
    return found


READERS = {'cwd': _cwd, 'open': _open, 'mapped': _mapped}


def process(pid, proc=PROC):
    """The kernel's record of one process: its id, its start time in clock ticks since boot (field 22
    of stat) and whether it is live. None when the kernel does not show it. A zombie is not live."""
    try:
        with open(os.path.join(proc, str(int(pid)), 'stat'), 'rb') as stat:
            fields = stat.read().rsplit(b')', 1)[1].split()
        return {'pid': int(pid), 'start': int(fields[19]), 'live': fields[0] not in (b'Z', b'X')}
    except (OSError, ValueError, IndexError):
        return None


def processes(path, proc=PROC, helpers=HELPERS):
    """The processes that use `path`: {users: [{pid, command, uses: [{how, path}], more}], unread}.
    how is cwd, open or mapped. unread counts the processes whose table this user may not read."""
    root = os.path.realpath(path)
    users, unread = [], 0
    for name in sorted((name for name in os.listdir(proc) if name.isdigit()), key=int):
        base = os.path.join(proc, name)
        try:
            with open(os.path.join(base, 'comm'), 'rb') as comm:
                command = comm.read().decode('utf-8', 'replace').strip()
        except OSError:
            continue  # ended meanwhile
        if command in helpers:
            continue
        uses, denied = [], False
        for how in USES:
            try:
                uses.extend({'how': how, 'path': where} for where in READERS[how](base)
                            if _beneath(where, root))
            except PermissionError:
                denied = True
            except OSError:
                continue  # ended meanwhile
        unread += 1 if denied else 0
        if uses:
            users.append({'pid': int(name), 'command': command, 'uses': uses[:NAMED],
                          'more': max(0, len(uses) - NAMED)})
    return {'users': users, 'unread': unread}


def containers(path, engines=(), run=None):
    """The containers with a bind mount at or beneath `path`, on each engine context named:
    {users: [{engine, id, name, state, source, destination}], unread: [{engine, said}]}."""
    run = run or _run
    root = os.path.realpath(path)
    users, unread = [], []
    for engine in engines:
        client = ['docker', '--context', str(engine), 'container']
        code, listed = run(client + ['ls', '--all', '--quiet', '--no-trunc'])
        records = []
        if code == 0 and listed.split():
            code, listed = run(client + ['inspect'] + listed.split())
            try:
                records = json.loads(listed) if code == 0 else []
            except ValueError:
                code, listed = None, 'the inspect records are not JSON'
        if code != 0 or not isinstance(records, list):
            unread.append({'engine': engine, 'said': str(listed)[:300]})
            continue
        for record in records:
            for mount in record.get('Mounts') or ():
                source = mount.get('Source') or ''
                if mount.get('Type') == 'bind' and source.startswith('/') and (
                        _beneath(os.path.normpath(source), root) or _beneath(os.path.realpath(source), root)):
                    users.append({'engine': engine, 'id': record.get('Id'),
                                  'name': (record.get('Name') or '').lstrip('/'),
                                  'state': (record.get('State') or {}).get('Status'),
                                  'source': source, 'destination': mount.get('Destination')})
    return {'users': users, 'unread': unread}


def git_lock(path, run=None):
    """The locks git holds on the worktree at `path`: {files, worktree_locked, locked}. files are the
    lock files in the worktree's own git folder; worktree_locked says git's worktree lock is set. A
    path that is not the top of a worktree has neither."""
    run = run or _run
    folder = _git_folder(run, path)
    files = [name for name in LOCK_FILES if folder and os.path.lexists(os.path.join(folder, name))]
    locked = bool(folder) and os.path.lexists(os.path.join(folder, 'locked'))
    return {'files': files, 'worktree_locked': locked, 'locked': bool(files) or locked}


def _git_folder(run, path):
    """The git folder of the worktree whose top is `path`, or None when `path` is not one."""
    code, top = _git(run, path, 'rev-parse', '--show-toplevel')
    if code != 0 or os.path.realpath(top.rstrip('\n')) != os.path.realpath(path):
        return None
    code, folder = _git(run, path, 'rev-parse', '--absolute-git-dir')
    return folder.rstrip('\n') if code == 0 else None


def in_use(path, engines=(), proc=PROC, helpers=HELPERS, run=None):
    """Rule 4's facts for a path: the processes, the containers and the git locks that use it, what
    could not be read, and in_use, which is true when any of the three found a user."""
    found, mounted, lock = processes(path, proc, helpers), containers(path, engines, run), git_lock(path, run)
    facts = {'path': str(path), 'resolved': os.path.realpath(path),
             'in_use': bool(found['users'] or mounted['users'] or lock['locked']),
             'processes': found['users'], 'containers': mounted['users'], 'git': lock,
             'unread': {'processes': found['unread'], 'engines': mounted['unread']}}
    if SEAM['after_in_use']:
        SEAM['after_in_use'](facts)
    return facts


# A sandbox launcher's scratch.

def _borrow_root():
    """Where the launcher keeps its borrow journals (agent_sandbox.py, borrow_root)."""
    state = os.environ.get('XDG_STATE_HOME', '')
    if not os.path.isabs(state):
        state = os.path.join(os.path.expanduser('~'), '.local/state')
    return os.path.join(state, 'veldo', 'borrowed-logins')


def _lock_held(path):
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except OSError:
        return False  # no folder, or a link: there is nothing a launcher locked
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return True
    finally:
        os.close(descriptor)
    return False


def scratch(path, borrow_root=None):
    """Rule 4's facts for a sandbox launcher's scratch: {lock_held, login_unsettled, journal, in_use}.
    in_use is true while the lock is held or the borrowed login is not settled."""
    held = _lock_held(path)
    journal = os.path.join(str(borrow_root or _borrow_root()), os.path.basename(os.path.normpath(str(path))))
    unsettled = (os.path.isfile(os.path.join(journal, 'borrow.json'))
                 and not os.path.lexists(os.path.join(journal, 'recovery.json')))
    return {'path': str(path), 'lock_held': held, 'login_unsettled': unsettled, 'journal': journal,
            'in_use': held or unsettled}


# Unique work.

def _compared(own, shared):
    """The repository whose refs say whether a commit is held: the shared repository when there is
    one, and the worktree's own repository otherwise."""
    return own if shared is None else shared


def _refs_holding(run, repository, commit, pattern=None):
    """The refs of `repository` that reach `commit`, among those matching `pattern` when one is given.
    An empty list when the repository does not hold the commit; None when it cannot be read."""
    code, _ = _git(run, repository, 'rev-parse', '--git-dir')
    if code != 0:
        return None
    code, _ = _git(run, repository, 'cat-file', '-e', commit + '^{commit}')
    if code != 0:
        return []
    code, out = _git(run, repository, 'for-each-ref', '--format=%(refname)', '--contains', commit,
                     *([pattern] if pattern else []))
    return out.split('\n')[:-1] if code == 0 else None


def _landed_by(run, repository, commit, landed):
    """The first source commit of a completed landing that is `commit` or has it as an ancestor."""
    for source in landed:
        if not isinstance(source, str) or not COMMIT.fullmatch(source):
            continue
        if source == commit:
            return source
        code, out = _git(run, repository, 'rev-list', '--max-count=1', commit, '--not', source)
        if code == 0 and not out.strip():
            return source
    return None


def _unread(path, said):
    return {'path': str(path), 'read': False, 'said': str(said)[:300], 'unique_work': None}


def unique_work(path, landed=(), shared=None, run=None):
    """Rule 5's facts for the worktree at `path`.

    `landed` holds the source commits the completion receipts of completed landings name. `shared` is
    the shared repository, given for an agent's worktree and for nothing else.

    Returns read, branch (the full ref, None when detached), commit, and per case: modified (1), staged
    (2), untracked (3: what git does not ignore, a folder as one name), operation (4), unlanded (5: the
    commit, when no other ref, no landing and so not the trunk holds it), with held_by (the refs that
    hold it) and landed_by (the source commit that covers it). cases lists the numbers that hold and
    unique_work is true when any does. When git cannot read the worktree or the shared repository, read
    is False and unique_work is None."""
    run = run or _run
    folder = _git_folder(run, path)
    if not folder:
        return _unread(path, 'not the top of a git worktree')
    code, status = _git(run, path, 'status', '--porcelain=v1', '-z', '--untracked-files=normal')
    if code != 0:
        return _unread(path, status)
    modified, staged, untracked = [], [], []
    entries = status.split('\0')[:-1]
    while entries:
        entry = entries.pop(0)
        state, name = entry[:2], entry[3:]
        if 'R' in state or 'C' in state:
            entries.pop(0)  # the name it was renamed or copied from
        if state == '??':
            untracked.append(name)
        elif state != '!!':
            if state[0] != ' ':
                staged.append(name)
            if state[1] != ' ':
                modified.append(name)
    operation = next((name for name, marker in OPERATIONS if os.path.lexists(os.path.join(folder, marker))), None)
    code, commit = _git(run, path, 'rev-parse', '--quiet', '--verify', 'HEAD^{commit}')
    commit = commit.strip() if code == 0 else None  # None: a branch with no commit yet
    code, branch = _git(run, path, 'symbolic-ref', '--quiet', 'HEAD')
    branch = branch.strip() if code == 0 else None
    refs, landed_by = [], None
    if commit:
        compared = _compared(path, shared)
        refs = _refs_holding(run, compared, commit)
        if refs is None:
            return _unread(path, 'the refs of %s cannot be read' % compared)
        if shared is None:
            refs = [ref for ref in refs if ref != branch]
        landed_by = _landed_by(run, path, commit, landed)
    unlanded = commit if commit and not refs and not landed_by else None
    cases = [number for number, holds in enumerate((modified, staged, untracked, operation, unlanded), 1)
             if holds]
    return {'path': str(path), 'read': True, 'branch': branch, 'commit': commit,
            'modified': modified[:NAMED], 'staged': staged[:NAMED], 'untracked': untracked[:NAMED],
            'more': {'modified': max(0, len(modified) - NAMED), 'staged': max(0, len(staged) - NAMED),
                     'untracked': max(0, len(untracked) - NAMED)},
            'operation': operation, 'unlanded': unlanded, 'held_by': refs[:NAMED], 'landed_by': landed_by,
            'compared': str(_compared(path, shared)), 'cases': cases, 'unique_work': bool(cases)}


def agent_repository(path, shared, run=None):
    """Rule 5's facts for the agent repository at `path`: its branches, each with whether the shared
    repository holds its commit under the same name, and not_across, the branches it does not.
    unique_work is true while not_across names any; None, with read False, when either repository
    cannot be read."""
    run = run or _run
    code, listed = _git(run, path, 'for-each-ref', '--format=%(objectname) %(refname)', 'refs/heads')
    if code != 0:
        return _unread(path, listed)
    branches = []
    for line in listed.split('\n')[:-1]:
        commit, ref = line.split(' ', 1)
        holders = _refs_holding(run, _compared(path, shared), commit, ref)
        if holders is None:
            return _unread(path, 'the refs of %s cannot be read' % shared)
        branches.append({'ref': ref, 'commit': commit, 'held': ref in holders})
    not_across = [branch['ref'] for branch in branches if not branch['held']]
    return {'path': str(path), 'read': True, 'shared': str(shared), 'branches': branches[:NAMED],
            'not_across': not_across[:NAMED], 'more': max(0, len(not_across) - NAMED),
            'unique_work': bool(not_across)}
