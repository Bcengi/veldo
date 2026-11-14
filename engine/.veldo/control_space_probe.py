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
                               mapped file at or beneath the path, and the processes it could not read
  reach(path, uid, gids)       rule 4: whether the path's own permissions let a process through to it
  containers(path, engines)    rule 4: the containers, running or stopped, with a bind mount at or
                               beneath the path, or above it, on each named engine context
  git_lock(path)               rule 4: the lock files git holds on a worktree
  in_use(path, engines)        rule 4: the three above together
  worktrees(path)              rule 6: the worktrees a repository's own git folder registers
  nested(path, skip)           rule 6: the git repositories on disk beneath a path
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

EVERY PROBE FAILS CLOSED. What a probe cannot read or cannot decide is in use, or is unique work,
never free: a process it may not read that could reach the path, a process table that hides processes,
an engine the client cannot read, a worktree git cannot read, a scratch folder it cannot open, a
journal it cannot look into, an agent repository given no shared repository to compare with. Each
comes back named (read False, or an entry of unread), and in_use or unique_work says so.

PROCESS USE is read from the kernel's process table: for each process its cwd link, the links under fd
and the paths in maps. A command line that names the path is not read at all, so it is not use. A
process whose entry is gone when it is read ended meanwhile. A kernel thread (the PF_KTHREAD flag in
its stat file, which every user may read) holds no working directory, descriptor or map of a user's
path, and is left out: that is a fact of the kernel, not a judgement. Every other process the probe
could not read in full (its name, its working directory, its descriptors or its maps) is listed in
unread, by its process id and uid, never as a count.

A HELPER is not counted: the file-sharing helper of a desktop container engine holds descriptors on
every path a container ever mounted, and the containers' own mount lists are read instead. A name alone
does not make a process a helper, since any process may take any name. Each entry of HELPERS pins an
identity, and a process is that helper only when all of it holds: its command name, the probing user's
uid, the exact unit of that user's manager its cgroup file names (`{uid}` stands for the uid), and,
when the link can be read, the program its exe link leads to. Any other process of that name is read
and counted like every process.

WHICH UNREAD PROCESS COUNTS (design section 7, bounded fail closed). An unread process counts as use of
a path only when it could reach that path; its entry in unread carries reach, the reason it could, or
None when it could not. The uid, the groups and the parent of a process come from its status file,
which every user may read without root. It counts when:

  unknown_identity  its status or its cgroup file cannot be read
  container         its cgroup file names a container (an id of 64 hexadecimal digits) that no engine
                    the probe read holds: its mounts are not known. A process of a container an engine
                    does hold is judged by that container's mounts and by nothing of the host: not by
                    its uid, which is a number of the container's own, and not by the host's modes. It
                    has no reach of its own, and container_mount below is what counts it
  same_uid          it runs as the probing user: such a process is readable, and one that is not
                    (it made itself not dumpable) can still be anywhere that user can
  privileged_login  it is root, or holds CAP_DAC_OVERRIDE or CAP_DAC_READ_SEARCH in the effective
                    capabilities its status file gives (or they cannot be read), and a login started
                    it: its loginuid file, which every user may read, holds a uid, or cannot be read.
                    The kernel checks no mode for such a process, so the mode says nothing of where it
                    is, and the loginuid, set at login and kept across fork, exec and sudo, says a
                    person or a cron job started it: a command this user ran through sudo counts as
                    this user's, also after the shell that started it has ended
  permissions       the path's own permissions let it through: search permission, for its uid and
                    groups, on every directory from / down, and any permission on the path itself.
                    Owner, group and mode are read with os.stat. A root-owned or capable process whose
                    loginuid is unset, a system daemon, is judged this way too. That is a stated
                    policy and not a reading: the kernel would let such a process into a directory
                    closed to it, and the policy is that a daemon no login started does not go into a
                    user's folder it was not given. The design names what the policy does not see
  special           a directory of the way cannot be judged by owner, group and mode: it cannot be
                    read, or it carries an access list. A directory that plainly shuts the process
                    out decides before that
  inherited         a parent, or a parent's parent, could reach it: a child keeps the working
                    directory and the descriptors it was started with, so a command this user runs
                    through sudo or su counts while the process that started it lives
  container_mount   a container, running or stopped, has a bind mount at, beneath or above the path,
                    or an engine could not be read: a mount is a way to the path that the path's own
                    permissions do not describe, and the engine's own processes and the container's
                    come through it. in_use adds this one, for every unread process with no reach of
                    its own

A process table mounted with hidepid shows only some processes: it is reported in table, and the path
is in use. What this bound does not see is said in the design: a process of another uid, without
privilege, that outlived every parent that could reach the path and kept a working directory or a
descriptor from it; and a system service no login started that was configured to work in the path.

CONTAINERS are read through the docker client: the list of all containers of a context, then their
inspect records. A bind mount whose host source is at or beneath the path is use, whatever the
container's state. One whose source is above the path is returned in above: it is not use of the path,
and it is a way to it. An engine that cannot be read is named in unread with what the client said.
known holds the id of every container of the engines that were read, whatever it mounts.

NESTED REPOSITORIES. A git repository on disk beneath a worktree or an agent repository goes with it
when it is removed, with every commit only it holds, and git's status says nothing of one in an ignored
folder. nested walks the folder itself, ignored or not, following no link, and names every folder
beneath the path that holds a .git entry (a folder or a file) or is itself a git folder (HEAD, objects
and refs). It does not look inside one it found, inside the path's own .git folder, or inside a folder
of `skip`. A folder it cannot list makes read False.

GIT'S LOCKS are read in the git folder of the worktree whose top the path is, or of the repository
whose own folder it is. A path with no git at all, or inside a worktree and not its top, has none.
When git cannot say which it is, or the folder cannot be looked into, read is False and locked is True:
a lock that cannot be read is a lock.

UNIQUE WORK. The five cases of rule 5, each with what was found; `cases` lists the numbers that hold.
The rule that reads them leaves case 3 out for a review worktree. Case 5 tests the checked-out commit,
which is the tip of the worktree's branch, or of nothing when the worktree is detached. Only a branch,
a tag or a remote-tracking ref holds a commit (HOLDING_REFS). A stash does not: the stash entry made in
the worktree has the checked-out commit as its parent, so refs/stash reaches it, and dropping the stash
after the worktree is gone would lose the commit. Nor do git's per-worktree refs or any other ref.
The number of stash entries is returned as a fact, stashes. The commit is tested:

  - in a worktree of the shared repository itself, against every ref of that repository other than the
    worktree's own branch (a branch always reaches its own tip, so its own ref proves nothing);
  - in an agent's worktree, when `shared` names the shared repository, against the refs of the shared
    repository and of no other: a commit the shared repository does not yet hold is unique;
  - and in both, against `landed`, the source commits the completion receipts of completed landings
    name: a tip that is one of them, or an ancestor of one, is landed. That is the squash landing, whose
    tip the trunk never reaches. The caller reads the receipts; this module opens no store.

AN AGENT REPOSITORY is compared with the shared repository, and with nothing else: given no shared
repository it is unread, and its unique work is unknown. A branch is across when the shared repository
holds its commit under the same name. Every other ref of it (a tag, a stash) is across when a holding
ref of the shared repository reaches its commit; refs/stash never is, and any stash entry is unique
work, because the repository's stashes go with it.

File names are returned. File contents never are.

A SANDBOX LAUNCHER'S SCRATCH is in use while a launcher or its confined command holds the lock on the
scratch folder (each holds a shared lock for as long as it runs), or while the journal of its borrowed
login is not settled: the journal folder named for the scratch holds borrow.json and no recovery.json.
The lock is tested by asking for it without waiting and giving it back at once. A folder that is not
there, or is a link, is one no launcher locked. A folder the probe cannot open reads as locked, and a
journal it cannot look into reads as not settled; read is False and said names what failed.

THE TEST SEAM. SEAM['after_in_use'], when set, is called with the facts of every in_use call before
they are returned. It is for tests that need something to happen between two probes. Nothing in the
engine sets it.

GIT is run through the one Git boundary (git_process.py, the sibling of this file), in its isolated
profile: no GIT_ variable of the caller's environment and no system or global configuration reaches
it. So a file that only a personal global excludes file ignores is an untracked file to rule 5, as it
is to the removers' git, and design section 0.1 calls it work. Optional locks are off, so a status
never writes the index, and the file monitor is off. A runner a caller gives is handed the same
argument vector; the default runner, and the removers' own, send a git vector through the boundary. A
repository git cannot read comes back with read False and what git said; it is never reported as
having no unique work.

Standard library only, and the Git boundary beside this file.
"""
import errno
import fcntl
import fnmatch
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess


def _sibling(name):
    spec = importlib.util.spec_from_file_location('veldo_space_probe_' + name,
                                                  Path(__file__).resolve().with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_git_process = _sibling('git_process')

SCHEMA = 'veldo.control_space_probe/v1'

PROC = '/proc'
SECONDS = 60
USES = ('cwd', 'open', 'mapped')
# The identity of each helper: every field must hold. {uid} is the probing user's uid.
HELPERS = ({'name': 'virtiofsd', 'exe': '/opt/docker-desktop/bin/virtiofsd',
            'cgroup': '/user.slice/user-{uid}.slice/user@{uid}.service/app.slice/docker-desktop.service'},)
NAMED = 20  # the most paths, refs or files named for one process or one case

LOCK_FILES = ('index.lock', 'HEAD.lock', 'config.lock', 'shallow.lock')
OPERATIONS = (('merge', 'MERGE_HEAD'), ('rebase', 'rebase-merge'), ('rebase', 'rebase-apply'),
              ('cherry-pick', 'CHERRY_PICK_HEAD'), ('revert', 'REVERT_HEAD'), ('sequence', 'sequencer'))
COMMIT = re.compile(r'[0-9a-f]{40}([0-9a-f]{24})?')

# The engine's word for each Docker kind, which is also the type of its protect entries.
DOCKER_TYPE = {'container': 'container', 'volume': 'volume', 'network': 'network', 'image_tag': 'image'}

# What the kernel says of a process that ended while it was being read.
GONE = (FileNotFoundError, ProcessLookupError)
# The refs that hold a commit. A stash, a per-worktree ref and every other ref do not.
HOLDING_REFS = ('refs/heads/', 'refs/tags/', 'refs/remotes/')
ACCESS_LIST = 'system.posix_acl_access'
SHOWN = (None, '0', 'off')  # the hidepid values under which the table shows every process
KERNEL_THREAD = 0x00200000  # PF_KTHREAD, in the flags of a process's stat file
PASSES_MODE = (1 << 1) | (1 << 2)  # CAP_DAC_OVERRIDE and CAP_DAC_READ_SEARCH: no mode is checked
NO_LOGIN = 4294967295  # the loginuid of a process no login started
CONTAINER = re.compile(r'[0-9a-f]{64}')  # a container's id, in the cgroup a process is in
GIT_FOLDER = frozenset(('HEAD', 'objects', 'refs'))

SEAM = {'after_in_use': None}


def _run(argv, cwd=None, via=None):
    """Run a client and return (exit code, output). A client that is missing or does not end in time
    gives (None, what happened). A git argument vector is run through the one Git boundary and by
    nothing else. `via` is the runner a caller gave: it is handed the vector as it is."""
    if via is not None and via is not _run:
        return via(argv)
    environment = dict(os.environ, LC_ALL='C')
    given = dict(cwd=cwd, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                 stderr=subprocess.PIPE, timeout=SECONDS)
    try:
        if argv and argv[0] == 'git':
            done = _git_process.run([str(word) for word in argv], **given)  # the isolated profile
        else:
            environment = {key: value for key, value in environment.items() if not key.startswith('GIT_')}
            done = subprocess.run(argv, **dict(given, env=environment))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return None, type(error).__name__ + ': ' + str(error)[:200]
    if done.returncode:
        return done.returncode, done.stderr.decode('utf-8', 'replace').strip()[-300:]
    return 0, done.stdout.decode('utf-8', 'surrogateescape')


def _git(run, repository, *argv):
    return _run(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-C', str(repository)] + list(argv),
                via=run)


def _beneath(candidate, root):
    return candidate == root or candidate.startswith(root.rstrip('/') + '/')


def _there(path):
    """Whether anything is at `path`: True, False, or None when that cannot be read."""
    try:
        os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        return False
    except OSError:
        return None
    return True


def _said(error):
    return type(error).__name__ + ': ' + str(error)[:200]


# What is at a locator, and the protect list.

def repository(path, run=None):
    """The repository `path` belongs to, as its common git folder with every link followed: the same
    for a repository, for each of its worktrees and for a bare one. None when git reads none there."""
    run = run or _run
    code, folder = _git(run, path, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    return os.path.realpath(folder.rstrip('\n')) if code == 0 and folder.strip() else None


def there(path):
    """Whether something is at `path`, read with os.lstat: (True, None) when something is, (False,
    None) only when the kernel said not found (ENOENT), and (None, what was said) for any other
    answer: a folder above it that may not be searched (EACCES), a failing disk (EIO), a name that
    is too long, a parent that is no folder. What could not be read is not missing: os.path.lexists
    answers False for all of these, and an item must never be marked gone on that word."""
    try:
        os.lstat(path)
    except FileNotFoundError:
        return False, None
    except (OSError, ValueError) as error:
        return None, _said(error)
    return True, None


def carrier(proc=PROC):
    """The process that is running now, as the carrier of a removal: {pid, started}, its id and its
    start time in clock ticks since boot, the two facts `process` reads again to tell whether the
    same process is still live. started is None when the kernel does not show this process."""
    seen = process(os.getpid(), proc)
    return {'pid': os.getpid(), 'started': seen['start'] if seen else None}


def located(kind, locator, run=None):
    """Rule 1's facts: what is at the locator of an item of `kind` now.

    A path (a branch is read at its repository): {path, exists, unread, link, resolved}, and for a
    worktree repository, the common git folder of the repository the folder is a worktree of, None
    when it is not the top of one. exists is True when something is there, False only when the kernel
    said not found, and None when the path could not be read, with what was said in unread (`there`).
    A Docker object: {engine, name, type, read, id, said}."""
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
    exists, unread = there(path)
    facts = {'kind': kind, 'path': path, 'exists': exists, 'unread': unread, 'link': os.path.islink(path),
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


def _identity(base):
    """Who the process at `base` is, from its status file, which every user may read: the uid and the
    groups the kernel checks a path against, its parent, and privileged: it is root, or its effective
    capabilities pass every mode check, or they cannot be read. None when the status cannot be read."""
    try:
        with open(os.path.join(base, 'status'), 'rb') as status:
            fields = dict(line.split(b':', 1) for line in status.read().split(b'\n') if b':' in line)
        who = {'uid': int(fields[b'Uid'].split()[3]),
               'gids': [int(fields[b'Gid'].split()[3])] + [int(group) for group in fields[b'Groups'].split()],
               'parent': int(fields[b'PPid'])}
    except (OSError, ValueError, KeyError, IndexError):
        return None
    try:
        who['privileged'] = who['uid'] == 0 or bool(int(fields[b'CapEff'].strip(), 16) & PASSES_MODE)
    except (ValueError, KeyError):
        who['privileged'] = True  # capabilities that cannot be read are capabilities
    return who


def _cgroup(base):
    """The text of the cgroup file of the process at `base`, which every user may read; None when it
    cannot be read."""
    try:
        with open(os.path.join(base, 'cgroup'), 'rb') as cgroup:
            return cgroup.read().decode('utf-8', 'replace')
    except OSError:
        return None


def _login_started(base):
    """Whether a login started the process at `base`: its loginuid file holds a uid. True as well when
    the file cannot be read; False only when it reads as unset."""
    try:
        with open(os.path.join(base, 'loginuid'), 'rb') as loginuid:
            return int(loginuid.read().strip()) != NO_LOGIN
    except (OSError, ValueError):
        return True


def _kernel_thread(base):
    """Whether the process at `base` is a kernel thread: the PF_KTHREAD flag in its stat file. False
    when the file cannot be read: only the flag, read, leaves a process out."""
    try:
        with open(os.path.join(base, 'stat'), 'rb') as stat:
            return bool(int(stat.read().rsplit(b')', 1)[1].split()[6]) & KERNEL_THREAD)
    except (OSError, ValueError, IndexError):
        return False


def _helper(base, command, helpers, me):
    """Whether the process at `base`, named `command`, is one of `helpers`, by its whole identity: the
    name, the probing user's uid, the exact unit its cgroup file names and, when its exe link can be
    read, the program it leads to."""
    for helper in helpers:
        if not isinstance(helper, dict) or command != helper.get('name'):
            continue
        who, group = _identity(base), _cgroup(base)
        if who is None or who['uid'] != me or group is None:
            continue
        units = [line[len('0::'):] for line in group.split('\n') if line.startswith('0::')]
        if units != [str(helper.get('cgroup')).replace('{uid}', str(me))]:
            continue
        try:
            if os.readlink(os.path.join(base, 'exe')) != helper.get('exe'):
                continue
        except OSError:
            pass  # a link that cannot be read is not another program
        return True
    return False


def _lets_through(where, uid, gids, last):
    """Whether the permissions of `where` let a process of `uid` and `gids` through: search permission
    on a directory of the way, any permission on the path itself (`last`). None when owner, group and
    mode do not decide it: it cannot be read, or it carries an access list."""
    try:
        found = os.lstat(where)
        try:
            listed = ACCESS_LIST in os.listxattr(where, follow_symlinks=False)
        except OSError as error:
            if error.errno not in (errno.ENOTSUP, errno.EOPNOTSUPP):
                return None
            listed = False  # a file system that keeps no access lists
    except (OSError, AttributeError):
        return None
    if listed:
        return None
    mode = found.st_mode >> (6 if found.st_uid == uid else 3 if found.st_gid in gids else 0)
    return bool(mode & (7 if last else 1))


def reach(path, uid, gids=()):
    """How a process of `uid` and `gids` could get to `path` by the path's own permissions: the word
    permissions when every directory from / down lets it through, special when none shuts it out and
    one of them cannot be judged by owner, group and mode, and None when one shuts it out. Root is
    judged as any other uid, by the mode and not by its privilege."""
    root = os.path.realpath(path)
    names = [name for name in root.split('/') if name]
    answer = 'permissions'
    for depth in range(len(names) + 1):
        through = _lets_through('/' + '/'.join(names[:depth]), uid, gids, depth == len(names))
        if through is False:
            return None
        if through is None:
            answer = 'special'
    return answer


def _could_hold(proc, pid, root, me, known, containers=()):
    """Why the unread process `pid` could hold `root`, or None when it could not (WHICH UNREAD PROCESS
    COUNTS). `known` keeps what this call has already worked out; `containers` holds the ids of the
    containers whose mounts the caller read."""
    if pid in known:
        return known[pid]
    known[pid] = 'unknown_identity'  # until decided, and for a chain of parents that leads back here
    base = os.path.join(proc, str(pid))
    who, group = _identity(base), _cgroup(base)
    why = None
    if who is None or group is None:
        why = 'unknown_identity'
    elif CONTAINER.search(group):
        # Judged by its container's mounts, which in_use reads, and by nothing of the host.
        why = None if CONTAINER.findall(group)[-1] in containers else 'container'
    elif who['uid'] == me:
        why = 'same_uid'
    elif who['privileged'] and _login_started(base):
        why = 'privileged_login'
    else:
        key = (who['uid'], tuple(who['gids']))
        if key not in known:
            known[key] = reach(root, who['uid'], who['gids'])
        why = known[key]
        if why is None and who['parent'] > 0 and _could_hold(proc, who['parent'], root, me, known, containers):
            why = 'inherited'
    known[pid] = why
    return why


def _table(proc, mountinfo=None):
    """Whether the process table at `proc` shows every process: {read, hidden, said}. hidden is the
    hidepid option the table is mounted with, read from the kernel's list of mounts, and read is False
    under any value that hides processes and when the mounts cannot be read. A folder that is not a
    mount of the process file system (a test's table) hides nothing."""
    where = os.path.realpath(proc)
    try:
        with open(mountinfo or os.path.join(PROC, 'self', 'mountinfo'), 'rb') as mounts:
            lines = mounts.read().split(b'\n')
    except OSError as error:
        return {'read': False, 'hidden': None, 'said': 'the mounts cannot be read: ' + _said(error)}
    mounted, hidden = False, None
    for line in lines:
        head, _, tail = line.partition(b' - ')
        fields, after = head.split(), tail.split()
        if len(fields) > 5 and len(after) > 2 and after[0] == b'proc' and os.fsdecode(fields[4]) == where:
            mounted, hidden = True, None  # a later mount at the same place covers an earlier one
            for option in fields[5].split(b',') + after[2].split(b','):
                if option.startswith(b'hidepid='):
                    hidden = option[len(b'hidepid='):].decode('utf-8', 'replace')
    if where == os.path.realpath(PROC) and not mounted:
        return {'read': False, 'hidden': None, 'said': 'the mounts do not name the process table'}
    if hidden not in SHOWN:
        return {'read': False, 'hidden': hidden, 'said': 'the process table is mounted hidepid=%s' % hidden}
    return {'read': True, 'hidden': hidden, 'said': None}


def processes(path, proc=PROC, helpers=HELPERS, mountinfo=None, containers=()):
    """The processes that use `path`: {users: [{pid, command, uses: [{how, path}], more}], unread:
    [{pid, uid, command, reach}], table: {read, hidden, said}}. how is cwd, open or mapped. unread
    lists every process the probe could not read in full: its uid (None when its status cannot be
    read either), its name (None when that cannot be read) and reach, why it could hold the path, or
    None when it could not. table says whether the table shows every process. `containers` holds the
    ids of the containers whose mounts the caller read: an unread process of any other container
    counts. A kernel thread and a helper (HELPERS) are left out."""
    root = os.path.realpath(path)
    me, known = os.geteuid(), {}
    table = _table(proc, mountinfo)
    try:
        names = sorted((name for name in os.listdir(proc) if name.isdigit()), key=int)
    except OSError as error:
        names, table = [], {'read': False, 'hidden': table['hidden'],
                            'said': 'the process table cannot be listed: ' + _said(error)}
    users, unread = [], []
    for name in names:
        base = os.path.join(proc, name)
        command, denied = None, False
        try:
            with open(os.path.join(base, 'comm'), 'rb') as comm:
                command = comm.read().decode('utf-8', 'replace').strip()
        except GONE:
            continue  # ended meanwhile
        except OSError:
            denied = True  # a process whose name cannot be read is a process all the same
        if _kernel_thread(base) or _helper(base, command, helpers, me):
            continue
        uses = []
        for how in USES:
            try:
                uses.extend({'how': how, 'path': where} for where in READERS[how](base)
                            if _beneath(where, root))
            except GONE:
                continue  # ended meanwhile
            except OSError:
                denied = True
        if uses:
            users.append({'pid': int(name), 'command': command, 'uses': uses[:NAMED],
                          'more': max(0, len(uses) - NAMED)})
        if denied:
            who = _identity(base)
            unread.append({'pid': int(name), 'uid': who['uid'] if who else None, 'command': command,
                           'reach': _could_hold(proc, int(name), root, me, known, containers)})
    return {'users': users, 'unread': unread, 'table': table}


def containers(path, engines=(), run=None):
    """The containers with a bind mount at or beneath `path`, on each engine context named:
    {users: [{engine, id, name, state, source, destination}], above: [the same, for a bind mount whose
    source is above the path], unread: [{engine, said}], known: [the id of every container of the
    engines that were read]}."""
    run = run or _run
    root = os.path.realpath(path)
    users, above, unread, known = [], [], [], []
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
            unread.append({'engine': engine, 'said': str(listed)[:300] or 'the client gave no answer'})
            continue
        for record in records:
            known.append(record.get('Id'))
            for mount in record.get('Mounts') or ():
                source = mount.get('Source') or ''
                if mount.get('Type') != 'bind' or not source.startswith('/'):
                    continue
                sources = (os.path.normpath(source), os.path.realpath(source))
                found = {'engine': engine, 'id': record.get('Id'),
                         'name': (record.get('Name') or '').lstrip('/'),
                         'state': (record.get('State') or {}).get('Status'),
                         'source': source, 'destination': mount.get('Destination')}
                if any(_beneath(where, root) for where in sources):
                    users.append(found)
                elif any(_beneath(root, where) for where in sources):
                    above.append(found)
    return {'users': users, 'above': above, 'unread': unread, 'known': known}


def git_lock(path, run=None):
    """The locks git holds on the worktree at `path`: {read, said, files, worktree_locked, locked}.
    files are the lock files in the worktree's own git folder, or in the repository's when `path` is a
    repository's own folder; worktree_locked says git's worktree lock is set. A path with no git, or
    inside a worktree and not its top, has neither. When git cannot say what the path is, or its git
    folder cannot be looked into, read is False, said is what failed and locked is True."""
    run = run or _run

    def facts(said=None, files=(), locked=False):
        return {'read': said is None, 'said': said, 'files': list(files), 'worktree_locked': locked,
                'locked': bool(files) or locked or said is not None}

    code, folder = _git(run, path, 'rev-parse', '--absolute-git-dir')
    if code != 0:
        if (code is not None and 'not a git repository (or any' in str(folder)
                and _there(os.path.join(str(path), '.git')) is False):
            return facts()  # no git here at all
        return facts(said=str(folder)[:300] or 'git gave no answer')
    folder = folder.rstrip('\n')
    code, top = _git(run, path, 'rev-parse', '--show-toplevel')
    if code == 0:
        if os.path.realpath(top.rstrip('\n')) != os.path.realpath(path):
            return facts()  # inside a worktree, and not its top
    elif os.path.realpath(folder) != os.path.realpath(path):
        return facts(said=str(top)[:300] or 'git gave no answer')
    there = {name: _there(os.path.join(folder, name)) for name in LOCK_FILES + ('locked',)}
    if None in there.values():
        return facts(said='the git folder %s cannot be looked into' % folder)
    return facts(files=[name for name in LOCK_FILES if there[name]], locked=there['locked'])


def _git_folder(run, path):
    """The git folder of the worktree whose top is `path`, or None when `path` is not one."""
    code, top = _git(run, path, 'rev-parse', '--show-toplevel')
    if code != 0 or os.path.realpath(top.rstrip('\n')) != os.path.realpath(path):
        return None
    code, folder = _git(run, path, 'rev-parse', '--absolute-git-dir')
    return folder.rstrip('\n') if code == 0 else None


def worktrees(path, run=None):
    """The worktrees the repository at `path` registers in its own git folder, other than `path`
    itself: {read, said, worktrees: [{path, there}]}, there saying the folder is on disk (None when
    that cannot be read). read is False, with what git said, when git cannot list them."""
    run = run or _run
    code, listed = _git(run, path, 'worktree', 'list', '--porcelain', '-z')
    if code != 0:
        return {'read': False, 'said': str(listed)[:300] or 'git gave no answer', 'worktrees': []}
    own = os.path.realpath(path)
    found = [entry[len('worktree '):] for entry in listed.split('\0') if entry.startswith('worktree ')]
    return {'read': True, 'said': None,
            'worktrees': [{'path': where, 'there': _there(where)} for where in found
                          if os.path.realpath(where) != own]}


def nested(path, skip=()):
    """The git repositories on disk beneath `path`, other than `path` itself: {read, said,
    repositories: [their folders]}. A folder is one when it holds a .git entry or is itself a git
    folder (NESTED REPOSITORIES). Nothing is looked for inside one that was found, inside the path's
    own .git folder or inside a folder of `skip`; no link is followed. read is False, with the first
    folder that could not be listed, when the walk could not finish."""
    top, found, said = str(path), [], None
    waiting = [top]
    while waiting:
        folder = waiting.pop()
        try:
            with os.scandir(folder) as listed:
                entries = sorted(listed, key=lambda entry: entry.name)
            inner = [entry.path for entry in entries
                     if entry.is_dir(follow_symlinks=False) and not (folder == top and entry.name == '.git')]
        except OSError as error:
            said = said or 'the folder %s cannot be listed: %s' % (folder, _said(error))
            continue
        names = set(entry.name for entry in entries)
        if folder != top and ('.git' in names or GIT_FOLDER <= names):
            found.append(folder)
            continue
        waiting.extend(where for where in reversed(inner) if where not in skip)
    return {'read': said is None, 'said': said, 'repositories': found}


def in_use(path, engines=(), proc=PROC, helpers=HELPERS, run=None, mountinfo=None):
    """Rule 4's facts for a path: the processes, the containers and the git locks that use it, and
    what could not be read. found is true when a user was seen. unknown is true when something that
    could not be read could hold the path: an unread process that could reach it, a process table that
    hides processes, an engine or a worktree that cannot be read. in_use is true when either is: what
    cannot be read is in use. unread names all of it: every unread process with its uid and its reach
    (container_mount added here, when a container mount is a way to the path or an engine is unread),
    the table, the engines and what git said. The containers are read first: an unread process of a
    container they hold is judged by the mounts alone."""
    mounted, lock = containers(path, engines, run), git_lock(path, run)
    found = processes(path, proc, helpers, mountinfo, mounted['known'])
    way_in = 'container_mount' if mounted['users'] or mounted['above'] or mounted['unread'] else None
    unread = {'processes': [dict(entry, reach=entry['reach'] or way_in) for entry in found['unread']],
              'table': found['table']['said'], 'engines': mounted['unread'], 'git': lock['said']}
    seen = bool(found['users'] or mounted['users'] or lock['files'] or lock['worktree_locked'])
    unknown = bool(any(entry['reach'] for entry in unread['processes']) or not found['table']['read']
                   or mounted['unread'] or not lock['read'])
    facts = {'path': str(path), 'resolved': os.path.realpath(path), 'in_use': seen or unknown,
             'found': seen, 'unknown': unknown,
             'processes': found['users'], 'containers': mounted['users'], 'mounted_above': mounted['above'],
             'git': lock, 'table': found['table'], 'unread': unread}
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
    """(held, said): whether a lock is held on the folder at `path`. held is None, with what failed,
    when the folder cannot be opened to ask."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        return False, None  # no folder: there is nothing a launcher locked
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR):
            return False, None  # a link, or no folder: there is nothing a launcher locked
        return None, 'the scratch folder cannot be opened: ' + _said(error)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return True, None
    finally:
        os.close(descriptor)
    return False, None


def scratch(path, borrow_root=None):
    """Rule 4's facts for a sandbox launcher's scratch: {read, said, lock_held, login_unsettled,
    journal, in_use}. in_use is true while the lock is held or the borrowed login is not settled. A
    folder that cannot be opened reads as locked and a journal that cannot be looked into as not
    settled; read is then False and said names what failed."""
    locked, said = _lock_held(path)
    journal = os.path.join(str(borrow_root or _borrow_root()), os.path.basename(os.path.normpath(str(path))))
    borrowed, recovered = _there(os.path.join(journal, 'borrow.json')), _there(os.path.join(journal, 'recovery.json'))
    if said is None and (borrowed is None or recovered is None):
        said = 'the journal %s cannot be looked into' % journal
    held = locked is not False
    unsettled = borrowed is not False and recovered is not True
    return {'path': str(path), 'read': said is None, 'said': said, 'lock_held': held,
            'login_unsettled': unsettled, 'journal': journal,
            'in_use': held or unsettled}


# Unique work.

def _compared(own, shared):
    """The repository whose refs say whether a commit is held: the shared repository when there is
    one, and the worktree's own repository otherwise."""
    return own if shared is None else shared


def _refs_holding(run, repository, commit, pattern=None):
    """The holding refs of `repository` (HOLDING_REFS: a branch, a tag, a remote-tracking ref) that
    reach `commit`, among those matching `pattern` when one is given. An empty list when the repository
    does not hold the commit; None when it cannot be read."""
    code, _ = _git(run, repository, 'rev-parse', '--git-dir')
    if code != 0:
        return None
    code, _ = _git(run, repository, 'cat-file', '-e', commit + '^{commit}')
    if code != 0:
        return []
    code, out = _git(run, repository, 'for-each-ref', '--format=%(refname)', '--contains', commit,
                     *([pattern] if pattern else []))
    return [ref for ref in out.split('\n')[:-1] if ref.startswith(HOLDING_REFS)] if code == 0 else None


def _stashes(run, repository):
    """The number of stash entries of `repository`; None when that cannot be read."""
    code, out = _git(run, repository, 'rev-parse', '--verify', '--quiet', 'refs/stash')
    if code == 1 and not str(out).strip():
        return 0
    if code != 0:
        return None
    code, out = _git(run, repository, 'rev-list', '--walk-reflogs', '--count', 'refs/stash')
    return int(out) if code == 0 and out.strip().isdigit() else None


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
    commit, when no other holding ref, no landing and so not the trunk holds it), with held_by (the
    refs that hold it) and landed_by (the source commit that covers it), and stashes, the number of
    stash entries of the worktree's repository (None when it cannot be read), which is no case. cases lists the numbers that hold and
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
            'compared': str(_compared(path, shared)), 'stashes': _stashes(run, path), 'cases': cases,
            'unique_work': bool(cases)}


def agent_repository(path, shared, run=None):
    """Rule 5's facts for the agent repository at `path`: its branches, each with whether the shared
    repository holds its commit under the same name, and not_across, the branches it does not; refs,
    its other refs that the shared repository does not hold (refs/stash always), and stashes, the
    number of its stash entries. unique_work is true while not_across or refs names any or a stash
    entry exists; None, with read False, when no shared repository is given or either repository
    cannot be read."""
    run = run or _run
    if shared is None:
        return _unread(path, 'no shared repository given')
    code, listed = _git(run, path, 'for-each-ref', '--format=%(objectname) %(objecttype) %(refname)')
    if code != 0:
        return _unread(path, listed)
    branches, others = [], []
    for line in listed.split('\n')[:-1]:
        commit, kind, ref = line.split(' ', 2)
        if ref.startswith('refs/heads/'):
            holders = _refs_holding(run, shared, commit, ref)
            if holders is None:
                return _unread(path, 'the refs of %s cannot be read' % shared)
            branches.append({'ref': ref, 'commit': commit, 'held': ref in holders})
            continue
        if kind != 'commit':
            code, peeled = _git(run, path, 'rev-parse', '--verify', '--quiet', ref + '^{commit}')
            commit = peeled.strip() if code == 0 else None  # None: a ref that leads to no commit
        holders = _refs_holding(run, shared, commit) if commit and ref != 'refs/stash' else []
        if holders is None:
            return _unread(path, 'the refs of %s cannot be read' % shared)
        if not holders:
            others.append(ref)
    stashes = _stashes(run, path)
    if stashes is None:
        return _unread(path, 'the stashes of %s cannot be read' % path)
    not_across = [branch['ref'] for branch in branches if not branch['held']]
    return {'path': str(path), 'read': True, 'shared': str(shared), 'branches': branches[:NAMED],
            'not_across': not_across[:NAMED], 'more': max(0, len(not_across) - NAMED),
            'refs': others[:NAMED], 'stashes': stashes,
            'unique_work': bool(not_across or others or stashes)}
