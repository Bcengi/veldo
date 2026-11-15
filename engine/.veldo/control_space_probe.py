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
  reader_read()                rule 4: the process reader's table, or why it is not used (VELDO-0344)
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

EVERY THREAD (VELDO-0344 AC8). The entries directly under /proc/<pid> are the first thread's. A thread
that left the shared file system state has a working directory of its own, and one that left the shared
descriptor table has open files of its own. So the working directory and the open files are read for
every task under /proc/<pid>/task, and a process with a task that cannot be read is unread. A task that
ended while it was read holds nothing. A table with no task folders (a test's) is read at the process's
own entries. Most threads share both with the first thread, and reading the same table once per thread
costs as many reads as the process has threads times descriptors. So the kernel is asked, with kcmp,
whether a task shares its file system state or its descriptor table with the first thread, and a task
that does is not read a second time. Only the kernel's plain answer that the two are the same one
leaves a task out: any other answer, an error or a kernel without the call has it read.

THE PROCESS READER (design section 7.1, VELDO-0344). A process the probe may not read (root's, another
user's, the owner's own that is not dumpable) is read through a separate program, the process reader:
/usr/local/lib/veldo/veldo-procread, which holds the one file capability cap_sys_ptrace and prints, for
every process and every task, the device and inode numbers of its working directory, its open files
and its mapped files, and the run label the task's environment carries (THE RUN LABEL, below). The
probe never executes it. It connects to the socket of the reader's own user
unit, /run/user/<uid>/veldo-procread.sock; both paths are fixed here and come from no environment,
installation or project. The reader's answer is used only when every check holds, and reader_read says
which state it is in:

  used                    every check held and the table was read
  absent                  nothing is at the reader's path
  refused:not_regular     the path is a link, or no regular file
  refused:owner           the file's owner is not root
  refused:mode            its group is not the probing user's own, or its mode is not exactly 0750
  refused:folder          a folder from / down to it is a link, belongs to another account than root
                          or may be written by one
  refused:capability      its capability attribute is not exactly cap_sys_ptrace, permitted and
                          effective, nothing inheritable, in version 2 or in version 3 with root id 0
  refused:no_pin          the installation's space section names no digest (process_reader)
  refused:digest          the file's SHA-256 digest, read through the same descriptor, is another one
  refused:no_socket       the socket cannot be connected to
  refused:writer          the kernel does not name one writer for the whole output that is a process of
                          the probing user's, holds exactly cap_sys_ptrace permitted and effective,
                          shows NoNewPrivs 1 and Seccomp 2, and that a pidfd names as alive before and
                          after its status was read, at the header and at the end line; or anything
                          but the one header line arrived before the probe sent its byte
  refused:no_capability   the header says cap=0
  refused:failed          the connection failed or gave no answer in time, or a reader that was run
                          directly ended with another status than 0
  refused:output          the output is not whole: a line outside the format, no end line, an end
                          count other than the number of blocks, bytes after the end line

The file's facts are read from one open descriptor, reached folder by folder with no link followed.
The probe sets SO_PASSCRED and SO_PASSPIDFD before it connects, so the kernel attaches to each part it
receives the writer's process id and uid and a pidfd, which stands for that one process and for no
later one of the same number. The reader writes its header only once it has locked itself (no_new_privs
and its seccomp filter) and then waits for one byte; the probe sends that byte only after it has seen
the header's writer locked and nothing more waiting, and it takes the table that follows. After the
end line the probe looks at the writer once more, shuts down its side and reads to the end of the
connection, which must give nothing more.

A reader that is not used changes nothing: every unread process is judged by the bound below, as
before. With the reader used, an unread process whose block is whole (no x line, not ended, and the
start time the probe itself reads for that process id) is read: it uses the path when the working
directory or a descriptor of any of its tasks, or a mapped file, has the inode number of the path or of
something beneath it, and otherwise it does not count, whatever its uid. It is named by process id,
task and fact, with the device and inode number the reader printed. The match is by inode number
alone: a file held through an overlay shows another device. The item's own numbers are read by listing
its folder and everything beneath it, following no link, and a folder that cannot be listed makes the
path in use. A process with no block, a block with an unread fact or another start time stays unread.

THE RUN LABEL. For every task it reads, the reader reads the task's environment and prints the value
of one variable, the run label a wrapped run gives its command (RUN_LABEL_VARIABLE, the name
control_space_docker.py and the CLI use), and nothing else of that environment: l - when the
environment was read to its end and holds no such entry, l =HEX with the value in hexadecimal for each
entry that is the variable, and x env when it could not be read. reader_table gives each block
label: the values its tasks carry, as bytes, each once, in order; an empty list when the environment
was read and carries none; and None when the label was not read. It is not read when a task of the
block has an x env line, when no task of the block has an l line, when the block was closed with g, or
when the process id opens two blocks. A label that was not read is never taken as no label: the
caller that asks whether a process is a run's (the CLI's run wrapper, VELDO-0313) holds the run for
it. An x env line leaves whole as it is: whole speaks for the files, which rule 4 reads, and label for
the environment. Nothing here logs a label, and the probe uses it for nothing itself.

THE COMMANDS (the owner's, docs/veldo-procread-setup.txt): `reader` runs the reader check, which prints
the reader's state, reads one undumpable process it starts itself, whose second thread sits in another
folder, and requires a whole block for process 1, which is root's and which the probe cannot read
itself; `reader-units` lays the two unit templates into the owner's systemd user unit folder,
through install(1), and is the one thing in this file that writes; `reader-exec` is the unit's entry:
it opens the reader once, makes the file's checks on that descriptor and executes that same descriptor
with an empty environment, or executes nothing. No probe function calls any of the three.

THE TEST SEAM. SEAM['after_in_use'], when set, is called with the facts of every in_use call before
they are returned. It is for tests that need something to happen between two probes. SEAM['reader'],
when set, gives the reader's checks what a suite cannot have without root: path and socket (where the
reader and its socket are), pin (the digest), file (the owner, group and mode read for the file),
folder (the owner and mode read for a folder of the way), capability (the capability attribute),
status (the status text read for the writer) and before_exec (called between the check and the
execution in the unit's entry). Nothing in the engine sets either.

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
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import select
import socket
import stat
import struct
import subprocess
import sys
import time


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

# The process reader (VELDO-0344). Both paths are fixed here; {uid} is the probing user's uid.
READER = '/usr/local/lib/veldo/veldo-procread'
READER_SOCKET = '/run/user/{uid}/veldo-procread.sock'
READER_MODE = 0o750
READER_SECONDS = 60  # the longest one answer of the reader is waited for
READER_BYTES = 1 << 30  # an output longer than this is not one table
READER_UNITS = ('veldo-procread.socket', 'veldo-procread@.service')
PTRACE = 1 << 19  # CAP_SYS_PTRACE
CAPABILITY_ATTRIBUTE = 'security.capability'
CAPABILITY_VERSION_2, CAPABILITY_VERSION_3 = 0x02000000, 0x03000000  # VFS_CAP_REVISION_2 and _3
CAPABILITY_EFFECTIVE = 0x000001  # VFS_CAP_FLAGS_EFFECTIVE
SO_PASSPIDFD, SCM_PIDFD = 76, 4  # the socket option and the message type of the writer's pidfd
HEADER = re.compile(rb'veldo-procread 1 cap=([01])')
TABLE_LINE = re.compile(rb'p (\d+) (\d+)|t (\d+)|c (\d+:\d+) (\d+)|f (\d+) (\d+) (\d+:\d+|-) (\d+)'
                        rb'|m (\d+:\d+) (\d+)|x (cwd|fd|stat|mnt|maps|task|env) (\d+)|(g)|end (\d+)'
                        rb'|l (-|=(?:[0-9a-f]{2})*)')
RUN_LABEL_VARIABLE = 'VELDO_SPACE_LABEL'  # the one variable the reader prints the value of
END_LINE = re.compile(rb'(?:\A|\n)end [^\n]*\n')

# kcmp, by its call number on the two machines the reader is built for; None elsewhere.
_KCMP = {'x86_64': 312, 'aarch64': 272}.get(os.uname().machine)
KCMP_FILES, KCMP_FS = 2, 3
_LIBC = {}

SEAM = {'after_in_use': None, 'reader': None}


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
    A Docker object: {engine, name, type, read, id, created_at, labels, said}. created_at is the
    engine's CreatedAt of the object shown: what a volume, to which an engine gives no Id, is known by
    (VELDO-0306). labels are the labels the engine shows on it now, None when it showed none."""
    run = run or _run
    if kind in DOCKER_TYPE:
        facts = {'kind': kind, 'engine': locator.get('engine'), 'name': locator.get('name'),
                 'type': DOCKER_TYPE[kind], 'read': False, 'id': None, 'created_at': None, 'labels': None,
                 'said': None}
        code, out = run(['docker', '--context', str(facts['engine']), facts['type'], 'inspect', str(facts['name'])])
        if code == 0:
            try:
                records = json.loads(out)
            except ValueError:
                records = None
            if isinstance(records, list) and len(records) == 1 and isinstance(records[0], dict):
                found = records[0].get('Id')
                made = records[0].get('CreatedAt')
                labels = records[0].get('Labels')
                if not isinstance(labels, dict):
                    labels = (records[0].get('Config') or {}).get('Labels') if isinstance(
                        records[0].get('Config'), dict) else None
                facts.update(read=True, id=found if isinstance(found, str) and found else None,
                             created_at=made if isinstance(made, str) and made else None,
                             labels=dict(labels) if isinstance(labels, dict) else None)
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


def image_repository(name):
    """(repository, whether a tag or a digest follows it) of an image name or pattern. The digest is
    what follows @; the tag is what follows the last colon when no / comes after it, so the port of a
    registry is no tag."""
    plain, _, digest = name.partition('@')
    tagged = ':' in plain and '/' not in plain.rsplit(':', 1)[1]
    return (plain.rsplit(':', 1)[0] if tagged else plain), bool(tagged or digest)


def name_matches(kind, name, pattern):
    """Whether a protect pattern for the type of `kind` covers the name of an object, as the Ledger
    reads it (control_space.name_matches). An image pattern with no tag and no digest covers every tag
    and every digest of the repository it names; one that names a tag or a digest covers that one
    only. Every other name is matched in full."""
    if fnmatch.fnmatchcase(name, pattern):
        return True
    if kind != 'image_tag' or image_repository(pattern)[1]:
        return False
    return fnmatch.fnmatchcase(image_repository(name)[0], pattern)


def protected(kind, locator, protect):
    """Rule 2's facts: {protected, entry, how}. entry is the covering protect entry as type:value and
    how is at, above or beneath for a path, name or compose_project for a Docker object. `protect` is
    the protect list in force: [{type, value, engines}]."""
    if kind in DOCKER_TYPE:
        for entry in protect:
            if locator.get('engine') not in entry.get('engines', ()):
                continue
            how = None
            if entry['type'] == DOCKER_TYPE[kind] and name_matches(kind, str(locator.get('name')), entry['value']):
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


COMPOSE_PROJECT = 'com.docker.compose.project'  # the label compose stamps on what it creates


def _inspect_one(run, engine, kind, name):
    """The one inspect record of an object of `engine`, or (None, what was said)."""
    code, out = run(['docker', '--context', str(engine), kind, 'inspect', str(name)])
    if code != 0:
        return None, str(out)[:300] or 'the client gave no answer'
    try:
        records = json.loads(out)
    except ValueError:
        records = None
    if isinstance(records, list) and len(records) == 1 and isinstance(records[0], dict):
        return records[0], None
    return None, 'the inspect record is not one JSON record'


def mounts(locator, protect, run=None):
    """Rule 2's facts for a container (design section 7, the protect list; the review of VELDO-0306,
    finding 2): whether it mounts what the protect list covers, read from the engine now:
    {read, protected, entry, how, mount, said}. A volume the list covers by its name or by its compose
    project label, or a bind source at, above or beneath a protected path, makes the container
    protected; how is mounted_volume or mounted_path and mount names what is mounted. read is False,
    with what was said, when the container, its mounts or a mounted volume could not be read: the
    caller refuses then."""
    run = run or _run
    engine = locator.get('engine')
    facts = {'read': False, 'protected': False, 'entry': None, 'how': None, 'mount': None, 'said': None}
    shown, facts['said'] = _inspect_one(run, engine, 'container', locator.get('id') or locator.get('name'))
    if shown is None:
        return facts
    held = shown.get('Mounts')
    if not isinstance(held, list) or not all(isinstance(mount, dict) for mount in held):
        return dict(facts, said='the engine showed the container without its mounts')
    entries = [entry for entry in protect if engine in entry.get('engines', ())]
    composed = [entry['value'] for entry in entries if entry['type'] == 'compose_project']
    for mount in held:
        name, source = mount.get('Name'), mount.get('Source')
        if mount.get('Type') == 'volume' or (isinstance(name, str) and name):
            if not (isinstance(name, str) and name):
                return dict(facts, said='a volume mount has no name')
            for entry in entries:
                if entry['type'] == 'volume' and fnmatch.fnmatchcase(name, entry['value']):
                    return dict(facts, read=True, protected=True, entry='volume:' + entry['value'],
                                how='mounted_volume', mount=name)
            if composed:
                volume, said = _inspect_one(run, engine, 'volume', name)
                if volume is None:
                    return dict(facts, said='the mounted volume %s could not be read: %s' % (name, said))
                labels = volume.get('Labels')
                project = labels.get(COMPOSE_PROJECT) if isinstance(labels, dict) else None
                if project in composed:
                    return dict(facts, read=True, protected=True, entry='compose_project:' + project,
                                how='mounted_volume', mount=name)
        elif mount.get('Type') == 'bind':
            if not (isinstance(source, str) and source.startswith('/')):
                return dict(facts, said='a bind mount has no source path')
            # A protected path is protected on every engine: the snapshot store, which the Ledger adds
            # with no engine, is covered like a configured path.
            for entry in protect:
                if entry['type'] != 'path':
                    continue
                value = os.path.normpath(entry['value'])
                for mine in (os.path.normpath(source), os.path.realpath(source)):
                    for theirs in (value, os.path.realpath(value)):
                        if mine == theirs or _beneath(theirs, mine) or _beneath(mine, theirs):
                            return dict(facts, read=True, protected=True, entry='path:' + entry['value'],
                                        how='mounted_path', mount=source)
    return dict(facts, read=True)


# The labels compose stamps with a path: the folder it ran in, and the files it read (comma separated).
COMPOSE_PATHS = (('compose_working_dir', 'com.docker.compose.project.working_dir'),
                 ('compose_config_file', 'com.docker.compose.project.config_files'))


def labelled(kind, locator, protect, run=None):
    """Rule 2's facts for the labels of a Docker object (design section 7, the protect list;
    VELDO-0307), read from the engine now, whatever was seen when it was recorded:
    {read, protected, entry, how, path, said}. The object is protected when the compose project label
    it carries now is a protected one on its engine (how compose_project), or when compose's working
    folder or one of the files compose read is at, above or beneath a protected path, as written or
    where it leads (how compose_working_dir or compose_config_file, with the path). A protected path
    is protected on every engine. read is False, with what was said, when the engine did not show the
    object, and when a path one of the two labels holds is not an absolute path and no other path of
    the object is protected: such a path cannot be placed, so it is not known to be free, as a bind
    mount with no source path is not. The caller refuses then."""
    facts = {'read': False, 'protected': False, 'entry': None, 'how': None, 'path': None, 'said': None}
    seen = located(kind, locator, run)
    if not seen['read'] or seen['said'] is not None:
        return dict(facts, said=seen['said'] or 'the engine did not show the object')
    labels = seen['labels'] if isinstance(seen['labels'], dict) else {}
    for entry in protect:
        if (entry['type'] == 'compose_project' and locator.get('engine') in entry.get('engines', ())
                and labels.get(COMPOSE_PROJECT) == entry['value']):
            return dict(facts, read=True, protected=True, entry='compose_project:' + entry['value'],
                        how='compose_project')
    # A protected path is protected on every engine, as it is for a mount.
    paths = [entry for entry in protect if entry['type'] == 'path']
    unplaced = None
    for how, label in COMPOSE_PATHS:
        held = labels.get(label)
        for path in (held.split(',') if how == 'compose_config_file' else [held]) if isinstance(held, str) else ():
            path = path.strip()
            if not path:
                continue  # the label holds nothing here: it names no path
            if not path.startswith('/'):
                unplaced = unplaced or 'the label %s holds a path that is not absolute: %s' % (label, path[:200])
                continue
            for entry in paths:
                value = os.path.normpath(entry['value'])
                for mine in (os.path.normpath(path), os.path.realpath(path)):
                    for theirs in (value, os.path.realpath(value)):
                        if mine == theirs or _beneath(theirs, mine) or _beneath(mine, theirs):
                            return dict(facts, read=True, protected=True, entry='path:' + entry['value'],
                                        how=how, path=path)
    if unplaced is not None:
        return dict(facts, said=unplaced)
    return dict(facts, read=True)


# Process use.

def _same(first, other, what):
    """Whether the kernel says the tasks `first` and `other` share `what` (KCMP_FILES, the descriptor
    table, or KCMP_FS, the file system state): True only on its plain answer 0."""
    if _KCMP is None:
        return False
    try:
        return _libc().syscall(_KCMP, int(first), int(other), what, 0, 0) == 0
    except Exception:  # no such call, or no library to make it with: not known to be the same
        return False


def _libc():
    if 'libc' not in _LIBC:
        import ctypes
        _LIBC['libc'] = ctypes.CDLL(None, use_errno=True)
    return _LIBC['libc']


def _tasks(base, shared=None):
    """The entries of every task of the process at `base`: /proc/<pid>/task/<tid>, the first thread
    first. A table that holds no task folder (a test's) is read at the process's own entries. With
    `shared` (KCMP_FS or KCMP_FILES) a task that shares that with the first thread is left out: what
    it holds was read at the first thread."""
    try:
        names = os.listdir(os.path.join(base, 'task'))
    except FileNotFoundError:
        os.lstat(base)  # raises when the process itself is gone
        return [base]
    names = sorted((name for name in names if name.isdigit()), key=int)
    leader = os.path.basename(base)
    if leader in names:
        names = [leader] + [name for name in names if name != leader]
    if shared is not None:
        names = names[:1] + [name for name in names[1:] if not _same(names[0], name, shared)]
    return [os.path.join(base, 'task', name) for name in names]


def _cwd(base):
    found = []
    for task in _tasks(base, KCMP_FS):
        try:
            where = os.readlink(os.path.join(task, 'cwd'))
        except GONE:
            continue  # the task ended meanwhile: it holds nothing
        if where not in found:
            found.append(where)
    if not found:
        raise FileNotFoundError(base)  # every task ended: the process did
    return found


def _open(base):
    found = {}
    for task in _tasks(base, KCMP_FILES):
        try:
            names = os.listdir(os.path.join(task, 'fd'))
        except GONE:
            continue  # the task ended meanwhile
        for name in names:
            try:
                found[os.readlink(os.path.join(task, 'fd', name))] = True
            except FileNotFoundError:
                continue  # closed meanwhile
    return list(found)


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


# The process reader (VELDO-0344, design section 7.1).

class _Refused(Exception):
    """The reader is not used: the check that failed, and what was seen."""

    def __init__(self, check, said=''):
        self.check, self.said = check, str(said)[:300]
        super().__init__(check)


class _Absent(Exception):
    """Nothing is at the reader's path."""


def _reader_seam():
    return SEAM.get('reader') or {}


def _config():
    return _sibling('control_space_config')


def _reader_pin(seam):
    """The digest the installation's space section names for the reader, or None when it names none
    or cannot be read. A suite's seam gives its own."""
    if 'pin' in seam:
        pin = seam['pin']
    else:
        try:
            pin = _config().read(stream=io.StringIO()).get('process_reader')
        except Exception:  # an installation that cannot be read names no digest
            pin = None
    return pin if isinstance(pin, str) and re.fullmatch(r'[0-9a-f]{64}', pin) else None


def _folder_checked(descriptor, where, seam):
    """Check 2 for one folder of the way: root owns it and nobody else may write it."""
    found = os.fstat(descriptor)
    owner, mode = seam['folder'](where, found) if seam.get('folder') else (found.st_uid, stat.S_IMODE(found.st_mode))
    if owner != 0 or mode & 0o022:
        raise _Refused('folder', '%s: owner %s, mode %o' % (where, owner, mode))


def _capability_checked(descriptor, seam):
    """Check 3: the capability attribute holds exactly cap_sys_ptrace, permitted and effective, and
    nothing inheritable, in version 2 or in version 3 with root id 0."""
    try:
        value = seam['capability'](descriptor) if seam.get('capability') else os.getxattr(descriptor,
                                                                                         CAPABILITY_ATTRIBUTE)
    except OSError as error:
        raise _Refused('capability', 'no capability attribute: ' + _said(error)) from None
    if not isinstance(value, bytes) or len(value) not in (20, 24):
        raise _Refused('capability', 'a capability attribute of another form')
    words = struct.unpack('<%dI' % (len(value) // 4), value)
    version, flags = words[0] & 0xff000000, words[0] & 0x00ffffff
    if (version, len(value)) not in ((CAPABILITY_VERSION_2, 20), (CAPABILITY_VERSION_3, 24)):
        raise _Refused('capability', 'version %#x' % version)
    if version == CAPABILITY_VERSION_3 and words[5] != 0:
        raise _Refused('capability', 'version 3 with root id %d' % words[5])
    permitted, inheritable = words[1] | words[3] << 32, words[2] | words[4] << 32
    if permitted != PTRACE or inheritable != 0 or flags != CAPABILITY_EFFECTIVE:
        raise _Refused('capability', 'permitted %#x, inheritable %#x, flags %#x' % (permitted, inheritable, flags))


def _reader_checked(seam):
    """Checks 2 to 4 on the reader's file, read from one open descriptor that is reached folder by
    folder with no link followed: (the descriptor, its digest). The caller closes the descriptor.
    Raises _Absent when nothing is at the path and _Refused with the check that failed."""
    path = seam.get('path', READER)
    names = [name for name in str(path).split('/') if name]
    if not str(path).startswith('/') or not names or '..' in names or '.' in names:
        raise _Refused('not_regular', 'the path is not a plain absolute one')
    walked, descriptor = '/', os.open('/', os.O_PATH | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for name in names[:-1]:
            _folder_checked(descriptor, walked, seam)
            walked = os.path.join(walked, name)
            try:
                inner = os.open(name, os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=descriptor)
            except FileNotFoundError:
                raise _Absent(walked) from None
            except OSError as error:
                raise _Refused('folder', '%s: %s' % (walked, _said(error))) from None
            os.close(descriptor)
            descriptor = inner
        _folder_checked(descriptor, walked, seam)
        try:
            opened = os.open(names[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=descriptor)
        except FileNotFoundError:
            raise _Absent(path) from None
        except OSError as error:
            raise _Refused('not_regular' if error.errno == errno.ELOOP else 'mode', _said(error)) from None
    finally:
        os.close(descriptor)
    try:
        found = os.fstat(opened)
        if not stat.S_ISREG(found.st_mode):
            raise _Refused('not_regular', 'not a regular file')
        owner, group, mode = (seam['file'](found) if seam.get('file')
                              else (found.st_uid, found.st_gid, stat.S_IMODE(found.st_mode)))
        if owner != 0:
            raise _Refused('owner', 'owner %s' % owner)
        if group != os.getgid() or mode != READER_MODE:
            raise _Refused('mode', 'group %s, mode %o' % (group, mode))
        _capability_checked(opened, seam)
        pin = _reader_pin(seam)
        if pin is None:
            raise _Refused('no_pin', 'the space section names no digest for the reader')
        digest, at = hashlib.sha256(), 0
        while True:
            block = os.pread(opened, 1 << 20, at)
            if not block:
                break
            digest.update(block)
            at += len(block)
        if digest.hexdigest() != pin:
            raise _Refused('digest', 'the file reads %s' % digest.hexdigest())
        return opened, digest.hexdigest()
    except BaseException:
        os.close(opened)
        raise


def _pidfd_pid(pidfd):
    """The process id a pidfd names, from its own fdinfo entry; None once that process has ended (the
    kernel writes -1 there) or when the entry cannot be read."""
    try:
        with open('/proc/self/fdinfo/%d' % pidfd, 'rb') as about:
            for row in about.read().split(b'\n'):
                if row.startswith(b'Pid:'):
                    found = int(row[4:])
                    return found if found > 0 else None
    except (OSError, ValueError):
        pass
    return None


def _alive(pidfd, pid):
    """Whether the pidfd names the live process `pid` now: its fdinfo gives that id and it does not
    poll as ended."""
    if pid is None or _pidfd_pid(pidfd) != pid:
        return False
    return not select.select([pidfd], [], [], 0)[0]


def _locked(pidfd, pid, me, seam):
    """Check 5 for the writer the pidfd names: alive before and after its status file was read, and
    that file shows the probing user's uid, exactly cap_sys_ptrace permitted and effective,
    NoNewPrivs 1 and Seccomp 2. Raises _Refused('writer')."""
    if not _alive(pidfd, pid):
        raise _Refused('writer', 'the writer has ended')
    try:
        with open(os.path.join(PROC, str(pid), 'status'), 'rb') as status:
            text = status.read().decode('utf-8', 'replace')
    except OSError as error:
        text = ''
        if not seam.get('status'):
            raise _Refused('writer', 'the status of the writer cannot be read: ' + _said(error)) from None
    if seam.get('status'):
        text = seam['status'](pid, text)
    fields = dict((key, value.split()) for key, _, value in (row.partition(':') for row in text.split('\n')))
    try:
        seen = {'uid': [int(uid) for uid in fields['Uid']], 'permitted': int(fields['CapPrm'][0], 16),
                'effective': int(fields['CapEff'][0], 16), 'no_new_privs': int(fields['NoNewPrivs'][0]),
                'seccomp': int(fields['Seccomp'][0])}
    except (KeyError, ValueError, IndexError):
        raise _Refused('writer', 'the status of the writer does not show what it is') from None
    if seen != {'uid': [me] * 4, 'permitted': PTRACE, 'effective': PTRACE, 'no_new_privs': 1, 'seccomp': 2}:
        raise _Refused('writer', 'the writer is not the locked reader: %s' % seen)
    if not _alive(pidfd, pid):
        raise _Refused('writer', 'the writer ended while its status was read')


def _part(connection, held):
    """One part of what the connection gives: (bytes, the writer's process id and uid, its pidfd).
    Every descriptor received is put into `held`, which the caller closes."""
    data, ancillary, _, _ = connection.recvmsg(1 << 16, socket.CMSG_SPACE(12) + socket.CMSG_SPACE(4) * 4,
                                               socket.MSG_CMSG_CLOEXEC)
    writer, pidfd = None, None
    for level, kind, value in ancillary:
        if level != socket.SOL_SOCKET:
            continue
        if kind == socket.SCM_CREDENTIALS and len(value) >= 12:
            writer = struct.unpack('3i', value[:12])[:2]
        elif kind in (SCM_PIDFD, socket.SCM_RIGHTS):
            received = [number for (number,) in struct.iter_unpack('i', value[:len(value) - len(value) % 4])]
            held.extend(received)
            if kind == SCM_PIDFD and len(received) == 1:
                pidfd = received[0]
    return data, writer, pidfd


def _one_writer(writer, pidfd, first, pid, me):
    """Whether a part came from the writer the first part named: the kernel's process id and uid for
    it, and a pidfd that names the same live process."""
    if writer is None or pidfd is None or writer != (pid, me):
        return False
    if os.fstat(pidfd).st_ino != os.fstat(first).st_ino:
        return False
    return _alive(pidfd, pid) and _alive(first, pid)


def _converse(seam, me):
    """Checks 5 and 6 on one connection to the reader's socket: the table's bytes and what was seen of
    the writer. Raises _Refused."""
    where = seam.get('socket', READER_SOCKET.replace('{uid}', str(me)))
    held = []
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM | socket.SOCK_CLOEXEC)
    try:
        connection.settimeout(READER_SECONDS)
        try:
            connection.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            connection.setsockopt(socket.SOL_SOCKET, SO_PASSPIDFD, 1)
        except OSError as error:
            raise _Refused('writer', 'the kernel does not hand over the writer: ' + _said(error)) from None
        try:
            connection.connect(where)
        except OSError as error:
            raise _Refused('no_socket', _said(error)) from None
        try:
            # The header: one line, and nothing else, before the probe's byte.
            data, writer, first = _part(connection, held)
            if not data:
                raise _Refused('failed', 'the connection gave nothing')
            pid = _pidfd_pid(first) if first is not None else None
            if writer is None or first is None or pid is None or writer != (pid, me):
                raise _Refused('writer', 'the kernel names no live writer of the probing user: %s' % (writer,))
            before = bytearray(data)
            while b'\n' not in before and len(before) < 64:
                data, writer, pidfd = _part(connection, held)
                if not data:
                    raise _Refused('failed', 'the connection ended in the header')
                if not _one_writer(writer, pidfd, first, pid, me):
                    raise _Refused('writer', 'a second writer in the header')
                before += data
            head, _, early = bytes(before).partition(b'\n')
            header = HEADER.fullmatch(head) if b'\n' in before else None
            if header is None or early:
                raise _Refused('writer', 'more than the one header line before the byte: %r' % bytes(before[:60]))
            _locked(first, pid, me, seam)
            # Nothing may be waiting behind the header once its writer has been seen locked.
            connection.setblocking(False)
            try:
                waiting = connection.recv(1, socket.MSG_PEEK)
            except (BlockingIOError, InterruptedError):
                waiting = None
            finally:
                connection.settimeout(READER_SECONDS)
            if waiting is not None:
                raise _Refused('writer', 'bytes after the header before the byte' if waiting
                               else 'the connection ended before the byte')
            if header.group(1) != b'1':
                raise _Refused('no_capability', 'the header says cap=0')
            connection.sendall(b'\n')
            # The table, to its end line.
            table = bytearray()
            while not END_LINE.search(table, max(0, len(table) - (1 << 16) - 32)):
                data, writer, pidfd = _part(connection, held)
                if not data:
                    raise _Refused('output', 'the connection ended with no end line')
                if not _one_writer(writer, pidfd, first, pid, me):
                    raise _Refused('writer', 'a second writer in the table')
                table += data
                if len(table) > READER_BYTES:
                    raise _Refused('output', 'the output is longer than a table')
            _locked(first, pid, me, seam)  # the last look, while the reader waits
            connection.shutdown(socket.SHUT_WR)
            while True:
                data, writer, pidfd = _part(connection, held)
                if not data:
                    break
                raise _Refused('output', 'bytes after the end line')
        except socket.timeout:
            raise _Refused('failed', 'the reader gave no answer in %d seconds' % READER_SECONDS) from None
        except OSError as error:
            raise _Refused('failed', _said(error)) from None
        return bytes(table), {'pid': pid, 'uid': me}
    finally:
        connection.close()
        for descriptor in held:
            try:
                os.close(descriptor)
            except OSError:
                pass


def reader_table(data, status=None, header=False):
    """Check 6: the reader's table from its bytes, as (blocks, None), or (None, the refused state and
    what was seen) when the output is not whole. Nothing of an output that is not whole is used.
    blocks is {pid: {start, whole, facts, label}}: whole is False when the block holds an x line
    other than x env, or a g line, or the process id opens two blocks, and facts are (how, tid, device,
    inode) with how cwd, fd or maps. label is the run label the block's tasks carry (THE RUN LABEL): a
    list of bytes values, empty when the environment was read and holds none, and None when it was
    not read. `status` is the exit status of a reader that was run directly, and `header` says the
    bytes start with the header line, which must say cap=1."""
    if status not in (None, 0):
        return None, ('refused:failed', 'the reader ended with status %s' % status)
    rows = bytes(data).split(b'\n')
    if rows[-1] != b'':
        return None, ('refused:output', 'the output does not end in a line feed')
    rows.pop()
    if header:
        found = HEADER.fullmatch(rows.pop(0)) if rows else None
        if found is None:
            return None, ('refused:output', 'no header line')
        if found.group(1) != b'1':
            return None, ('refused:no_capability', 'the header says cap=0')
    blocks, block, task, count, ended = {}, None, None, 0, None
    for number, row in enumerate(rows):
        found = TABLE_LINE.fullmatch(row)
        if found is None:
            return None, ('refused:output', 'line %d is outside the format' % (number + 1))
        if ended is not None:
            return None, ('refused:output', 'bytes after the end line')
        kind = row[:1]
        if kind == b'p':
            pid = int(found.group(1))
            block, task = {'start': int(found.group(2)), 'whole': pid not in blocks, 'facts': [], 'label': None}, None
            if pid in blocks:
                blocks[pid]['whole'] = False  # one id, two blocks: neither is that process for certain
                blocks[pid]['label'] = False
            else:
                blocks[pid] = block
            count += 1
        elif kind == b'e':
            ended = int(found.group(15))
        elif block is None:
            return None, ('refused:output', 'line %d is in no block' % (number + 1))
        elif kind == b't':
            task = int(found.group(3))
        elif kind == b'c' or kind == b'f':
            if task is None:
                return None, ('refused:output', 'line %d is in no task' % (number + 1))
            block['facts'].append(('cwd', task, found.group(4).decode(), int(found.group(5))) if kind == b'c'
                                  else ('fd', task, found.group(8).decode(), int(found.group(9))))
        elif kind == b'm':
            block['facts'].append(('maps', None, found.group(10).decode(), int(found.group(11))))
        elif kind == b'l':
            if task is None:
                return None, ('refused:output', 'line %d is in no task' % (number + 1))
            value = found.group(16)
            if block['label'] is None:
                block['label'] = []
            if block['label'] is not False and value != b'-' and bytes.fromhex(value[1:].decode()) not in block['label']:
                block['label'].append(bytes.fromhex(value[1:].decode()))
        elif kind == b'x' and found.group(12) == b'env':
            if task is None:
                return None, ('refused:output', 'line %d is in no task' % (number + 1))
            block['label'] = False  # the environment of a task was not read: the label is not read
        elif kind == b'x':
            if found.group(12) in (b'cwd', b'fd') and task is None:
                return None, ('refused:output', 'line %d is in no task' % (number + 1))
            block['whole'] = False
        else:  # g: the process ended while it was read, and its block is closed
            block['whole'] = False
            block['label'] = False
            block = task = None
    if ended is None:
        return None, ('refused:output', 'no end line')
    if ended != count:
        return None, ('refused:output', 'the end line counts %d blocks of %d' % (ended, count))
    for block in blocks.values():
        if block['label'] is False:
            block['label'] = None  # not read is never no label
    return blocks, None


def reader_read(proc=PROC):
    """The process reader's table, or why it is not used: {state, said, blocks, writer, seconds}. state
    is used, absent, or refused:<the check that failed> (THE PROCESS READER); said is what was seen;
    blocks is the table when the state is used and None otherwise. Without a suite's seam the reader
    is asked only about the host's own process table."""
    seam, started = _reader_seam(), time.monotonic()
    answer = {'state': 'absent', 'said': None, 'blocks': None, 'writer': None, 'digest': None}
    try:
        if not seam and os.path.realpath(proc) != os.path.realpath(PROC):
            raise _Absent('the reader reads the host\'s process table, and %s is another' % proc)
        descriptor, answer['digest'] = _reader_checked(seam)
        os.close(descriptor)
        data, answer['writer'] = _converse(seam, os.geteuid())
        blocks, refused = reader_table(data)
        if refused:
            raise _Refused(refused[0][len('refused:'):], refused[1])
        answer.update(state='used', blocks=blocks)
    except _Absent as absent:
        answer.update(state='absent', said=str(absent)[:300])
    except _Refused as refused:
        answer.update(state='refused:' + refused.check, said=refused.said)
    except Exception as error:  # a check that could not be made is a check that failed
        answer.update(state='refused:failed', said=_said(error))
    answer['seconds'] = round(time.monotonic() - started, 3)
    return answer


def _device(found):
    return '%d:%d' % (os.major(found.st_dev), os.minor(found.st_dev))


def _inodes(root):
    """The inode number of `root` and of everything beneath it, following no link, each with the
    device of that entry for the record: ({inode: device}, None), or (what was read, what was said)
    when a folder could not be listed or an entry not read."""
    found, said = {}, None
    try:
        top = os.lstat(root)
    except OSError as error:
        return found, 'the path %s cannot be read: %s' % (root, _said(error))
    found[top.st_ino] = _device(top)
    waiting = [root] if stat.S_ISDIR(top.st_mode) else []
    while waiting:
        folder = waiting.pop()
        try:
            with os.scandir(folder) as listed:
                for entry in listed:
                    seen = entry.stat(follow_symlinks=False)
                    found[seen.st_ino] = _device(seen)
                    if stat.S_ISDIR(seen.st_mode):
                        waiting.append(entry.path)
        except OSError as error:
            said = said or 'the folder %s cannot be listed: %s' % (folder, _said(error))
    return found, said


def _by_reader(reader, pid, proc, inodes):
    """How the reader's table judges the unread process `pid`: (uses, None) when its block is whole
    and is this process's, uses being the facts whose inode number is one of `inodes`; (None, why)
    when the process stays unread: no_block, unread_fact or start_time."""
    block = reader['blocks'].get(pid)
    if block is None:
        return None, 'no_block'
    if not block['whole']:
        return None, 'unread_fact'
    seen = process(pid, proc)
    if seen is None or seen['start'] != block['start']:
        return None, 'start_time'
    # By inode number alone: a file held through an overlay shows another device. item_device is the
    # device of the item's own entry of that number, kept beside the device the reader printed.
    return [{'how': how, 'tid': tid, 'device': device, 'inode': inode, 'item_device': inodes[inode]}
            for how, tid, device, inode in block['facts'] if inode in inodes], None


def processes(path, proc=PROC, helpers=HELPERS, mountinfo=None, containers=(), reader=None):
    """The processes that use `path`: {users: [{pid, command, uses: [{how, path}], more}], unread:
    [{pid, uid, command, reach}], table: {read, hidden, said}}. how is cwd, open or mapped. unread
    lists every process the probe could not read in full: its uid (None when its status cannot be
    read either), its name (None when that cannot be read) and reach, why it could hold the path, or
    None when it could not. table says whether the table shows every process. `containers` holds the
    ids of the containers whose mounts the caller read: an unread process of any other container
    counts. A kernel thread and a helper (HELPERS) are left out.

    `reader` is what reader_read returned. When its state is used, a process the probe could not read
    is judged by its block (THE PROCESS READER): one that holds the path is a user, {pid, uid, command,
    by: reader, uses: [{how, tid, device, inode, item_device}], more}, how being cwd, fd or maps; one that does not
    is in neither list; and one that stays unread carries reader, the reason. folders is what was
    said when the path's own folders could not all be listed, which makes the path in use; read is
    the number of processes the reader's table judged."""
    root = os.path.realpath(path)
    me, known = os.geteuid(), {}
    table = _table(proc, mountinfo)
    try:
        names = sorted((name for name in os.listdir(proc) if name.isdigit()), key=int)
    except OSError as error:
        names, table = [], {'read': False, 'hidden': table['hidden'],
                            'said': 'the process table cannot be listed: ' + _said(error)}
    users, unread = [], []
    used = bool(reader) and reader.get('state') == 'used' and isinstance(reader.get('blocks'), dict)
    inodes, folders, judged = None, None, 0
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
            entry = {'pid': int(name), 'uid': who['uid'] if who else None, 'command': command}
            if used:
                if inodes is None:
                    inodes, folders = _inodes(root)
                held, why = _by_reader(reader, int(name), proc, inodes)
                if why is None:
                    judged += 1
                    if held:
                        users.append(dict(entry, by='reader', uses=held[:NAMED], more=max(0, len(held) - NAMED)))
                    continue  # where it is has been read
                entry['reader'] = why
            entry['reach'] = _could_hold(proc, int(name), root, me, known, containers)
            unread.append(entry)
    return {'users': users, 'unread': unread, 'table': table, 'folders': folders, 'read': judged}


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


def in_use(path, engines=(), proc=PROC, helpers=HELPERS, run=None, mountinfo=None, reader=None):
    """Rule 4's facts for a path: the processes, the containers and the git locks that use it, and
    what could not be read. found is true when a user was seen. unknown is true when something that
    could not be read could hold the path: an unread process that could reach it, a process table that
    hides processes, an engine or a worktree that cannot be read. in_use is true when either is: what
    cannot be read is in use. unread names all of it: every unread process with its uid and its reach
    (container_mount added here, when a container mount is a way to the path or an engine is unread),
    the table, the engines and what git said. The containers are read first: an unread process of a
    container they hold is judged by the mounts alone.

    reader is the process reader's state for this call, {state, said, writer, digest, seconds, read}:
    used, absent or refused with the check that failed (THE PROCESS READER); read is the number of
    unread processes its table judged. `reader` may give what reader_read returned; without it the
    reader is asked here. unread also names folders, what was said when the reader was used and a
    folder of the path could not be listed: the path is then in use."""
    mounted, lock = containers(path, engines, run), git_lock(path, run)
    asked = reader if isinstance(reader, dict) else reader_read(proc)
    found = processes(path, proc, helpers, mountinfo, mounted['known'], asked)
    way_in = 'container_mount' if mounted['users'] or mounted['above'] or mounted['unread'] else None
    unread = {'processes': [dict(entry, reach=entry['reach'] or way_in) for entry in found['unread']],
              'table': found['table']['said'], 'engines': mounted['unread'], 'git': lock['said'],
              'folders': found['folders']}
    seen = bool(found['users'] or mounted['users'] or lock['files'] or lock['worktree_locked'])
    unknown = bool(any(entry['reach'] for entry in unread['processes']) or not found['table']['read']
                   or mounted['unread'] or not lock['read'] or found['folders'] is not None)
    facts = {'path': str(path), 'resolved': os.path.realpath(path), 'in_use': seen or unknown,
             'found': seen, 'unknown': unknown,
             'processes': found['users'], 'containers': mounted['users'], 'mounted_above': mounted['above'],
             'git': lock, 'table': found['table'], 'unread': unread,
             'reader': dict({key: value for key, value in asked.items() if key != 'blocks'}, read=found['read'])}
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


# The owner's commands for the process reader (docs/veldo-procread-setup.txt).

# The process the reader check starts: not dumpable, in the folder it is started in, with a second
# thread that leaves the shared file system state and sits in the folder it is given.
_CHECK_PROCESS = """
import ctypes, os, sys, threading
libc = ctypes.CDLL(None, use_errno=True)
libc.prctl(4, 0, 0, 0, 0)  # PR_SET_DUMPABLE, 0
def second():
    if libc.unshare(0x200) != 0:  # CLONE_FS: a working directory of this thread's own
        raise OSError(ctypes.get_errno(), 'unshare')
    os.chdir(sys.argv[1])
    print(threading.get_native_id(), flush=True)
    threading.Event().wait()
threading.Thread(target=second, daemon=True).start()
sys.stdin.read()
"""


def reader_check(out=None):
    """The reader check: prints the reader's state, starts one process that is not dumpable, in a
    folder, whose second thread sits in another, and reads it through the reader's socket as every
    probe does. 0 when the state is used, each thread was found in its folder and in no other, and
    process 1, root's and closed to the probe's own reading, has a whole block in the reader's table,
    and the run label the undumpable process was started with is read, and process 1's is read too.
    The first four rows read a process of the owner's own uid. The fifth is the one that shows the
    capability reading an entry of another uid: the kernel checks that on another branch. The sixth
    shows the label read where the probe itself is refused the environment."""
    import tempfile
    out = out or sys.stdout
    with tempfile.TemporaryDirectory(prefix='veldo-procread-check-') as first, \
            tempfile.TemporaryDirectory(prefix='veldo-procread-check-') as second, \
            tempfile.TemporaryDirectory(prefix='veldo-procread-check-') as other:
        mark = 'veldo-procread-check:%d' % os.getpid()
        started = subprocess.Popen([sys.executable, '-I', '-c', _CHECK_PROCESS, second], cwd=first,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   env=dict(os.environ, **{RUN_LABEL_VARIABLE: mark}))
        try:
            thread = int(started.stdout.readline().strip() or 0)
            asked = reader_read()
            seen = {where: in_use(where, reader=asked) for where in (first, second, other)}
            try:
                open(os.path.join(PROC, str(started.pid), 'environ'), 'rb').close()
                refused = False
            except PermissionError:
                refused = True
            except OSError:
                refused = False
        finally:
            started.stdin.close()
            started.wait()
            started.stdout.close()
        reader = seen[first]['reader']
        print('veldo-procread: state %s%s%s, read in %s seconds, %d processes judged by it'
              % (reader['state'], ' cap=1' if reader['state'] == 'used' else '',
                 ' (%s)' % reader['said'] if reader['said'] else '', reader['seconds'], reader['read']), file=out)

        def tasks(where):
            return sorted(use['tid'] for user in seen[where]['processes']
                          if user['pid'] == started.pid and user.get('by') == 'reader'
                          for use in user['uses'] if use['how'] == 'cwd')

        # Process 1: root's, and the probe itself is refused its working directory. Its block must be
        # whole (no x line, no g line, one block) and carry the start time the probe reads itself.
        who, block, own = _identity(os.path.join(PROC, '1')), (asked['blocks'] or {}).get(1), process(1)
        marked = (asked['blocks'] or {}).get(started.pid) or {}
        try:
            os.stat(os.path.join(PROC, '1', 'cwd'))
            closed = False
        except PermissionError:
            closed = True
        except OSError:
            closed = False
        rows = (('the reader is used', reader['state'] == 'used'),
                ('the first thread of the undumpable process is read in its folder', tasks(first) == [started.pid]),
                ('its second thread is read in the other folder', thread > 0 and tasks(second) == [thread]),
                ('it is not counted in a folder it does not hold', tasks(other) == []
                 and not any(entry['pid'] == started.pid for entry in seen[other]['unread']['processes'])),
                ('process 1, root-owned and closed to the probe itself, has a whole block with its start time',
                 who is not None and who['uid'] == 0 and closed and block is not None and block['whole']
                 and own is not None and own['start'] == block['start']),
                ('the run label of the undumpable process, whose environment is closed to the probe itself, is '
                 'read and is the one it was started with, and the label of process 1 is read',
                 refused and marked.get('label') == [mark.encode()] and block is not None
                 and isinstance(block.get('label'), list)))
        for label, passed in rows:
            print('%s: %s' % ('PASS' if passed else 'FAIL', label), file=out)
    return 0 if all(passed for _, passed in rows) else 1


def reader_units(folder=None, out=None):
    """Lay the two unit templates of the reader into the owner's systemd user unit folder, with the
    interpreter and this file's own path filled in. Written through install(1). Starts nothing."""
    out = out or sys.stdout
    if folder is None:
        home = os.environ.get('XDG_CONFIG_HOME', '')
        if not os.path.isabs(home):
            home = os.path.join(os.path.expanduser('~'), '.config')
        folder = os.path.join(home, 'systemd', 'user')
    here = Path(__file__).resolve()
    for name in READER_UNITS:
        with open(here.with_name('services') / name, 'rb') as template:
            text = template.read().decode('utf-8')
        text = text.replace('@PYTHON@', os.path.realpath(sys.executable)).replace('@EXECUTABLE@', str(here))
        target = os.path.join(str(folder), name)
        done = subprocess.run(['/usr/bin/install', '-D', '-m', '0644', '/dev/stdin', target],
                              input=text.encode('utf-8'), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=SECONDS)
        if done.returncode:
            print('veldo-procread: %s was not installed: %s'
                  % (target, done.stderr.decode('utf-8', 'replace').strip()[-300:]), file=sys.stderr)
            return 1
        print('veldo-procread: installed %s' % target, file=out)
    return 0


def reader_exec():
    """The entry of veldo-procread@.service: open the reader once, make checks 2 to 4 on that
    descriptor and execute that same descriptor, with an empty environment and the standard output
    the unit gave, which is the connection. When a check fails nothing is executed: 1 is returned
    and the connection closes with the process."""
    seam = _reader_seam()
    try:
        descriptor, _ = _reader_checked(seam)
    except (_Absent, _Refused):
        return 1
    if seam.get('before_exec'):
        seam['before_exec']()
    os.execve(descriptor, ['veldo-procread'], {})
    return 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv == ['reader']:
        return reader_check()
    if argv[:1] == ['reader-units'] and len(argv) <= 2:
        return reader_units(*argv[1:])
    if argv == ['reader-exec']:
        return reader_exec()
    print('usage: control_space_probe.py reader | reader-units [FOLDER] | reader-exec', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
