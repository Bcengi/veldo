#!/usr/bin/env python3
"""The removers: one remover per removal action, each using the owning tool's own remove and returning
what it measured (design section 6.5, VELDO-0300).

WHAT IS HERE. `remove` carries out one removal of one item and returns its figures. `tool` gives the
same thing in the form the safety rules call as rule 7 (control_space_signal.rules, tool(identity,
record)). A remover is called only after the other rules of the removal have passed. It writes nothing
to the ledger: the outcome is the caller's (VELDO-0301).

THE REMOVERS, by the table's action and the item's kind (REMOVERS):

  remove            scratch, build_output   the folder remover
  remove            worktree                the keep step, git's worktree move to a marked name, the last
                                            look there, then git's worktree remove, never forced
  remove            agent_repository        the keep step, then the folder remover with a last look
  remove            volume                  the engine's volume remove
  remove            network                 the engine's network remove
  remove            container               the engine's stop, then its container remove
  stop_then_remove  container               the same
  remove_tag        image_tag               the engine's image remove, on the tag
  drop_caches       evidence                the folder remover on each sub-folder the project declares as
                                            a cache, and on nothing else
  save              worktree                settled Save, snapshot, owner commit, non-forced removal
  discard           worktree                settled Discard, kept branch for a detached worktree whose
                                            commit no ref holds, snapshot, forced removal of this worktree

Any other pair has no remover and is refused. A branch is marked, never removed, and that is a ledger
write. Review scratch is saved by the keep step, compared file by file and removed before the
non-forced worktree remove (VELDO-0336). Copied evidence removal belongs to VELDO-0347.

Only the settled Discard passes a force option. No remover runs a prune command. Each names the one thing it
removes to the owning tool and lets the tool refuse. Every command a call ran, the probes' reads
included, is returned under commands, in order.

THE FOLDER REMOVER. Rename, second probe, delete, in that order:

  1. the folder is renamed to a marked name beside itself, <name>.veldo-removing.<item id>, so a
     process that looks for it by its path after the first probe finds nothing, and one that got in
     before the rename holds a file the second probe sees under the new name;
  2. the in-use probe is run again, on the marked name. A user, or anything the probe could not read
     that could hold the path, puts the folder back under its own name, and the item is deferred as
     in_use;
  3. the folder is measured and then deleted, through descriptors and without following a link.
     Directories a confined process left unreadable or unwritable are opened up first, the same way.

It refuses by itself, before the rename, when the path is not a plain one (it is relative, it holds
`..`, or a link is on its way: the remover does not rely on rule 1 for that), when it is not a folder
(a link is not one), when it is a mount point, when it is not on the item's pool, and when something
is already at the marked name. The folder its path is in is opened from / down with no link followed,
and the rename, the delete and the put back are made by name inside that one descriptor, so a parent
swapped for a link afterwards leads nowhere else. It stops, and puts back what is there, when another
filesystem is mounted inside the folder, when a delete fails, and when the folder is a git repository
or holds one: a folder with a .git entry, or one that is itself a git folder (HEAD, objects and refs),
found by the walk that measures the folder before the first delete. Scratch, build output and a cache
hold no repository; an agent repository holds its own and no other. When the folder cannot be put
back (something has appeared at its path), it stays under the marked name, the answer names it in
left_at, and nothing touches what is at the path. The marked name holds the item's id, written so
that no two ids share a name (marked, unmarked), and `left` finds a folder left under it: reconcile
looks there before it marks an item gone (VELDO-0315).

THE KEEP STEP IS GIVEN, AND WITHOUT IT NOTHING THAT HOLDS COMMITS IS REMOVED (design section 0.2). A
worktree and an agent repository are removed only after `keep(identity, record)` has answered
{ok: True, tips: ...}: the keeper has recorded every commit on kept refs in the main repository, read
them back and had the keep record written. With no keeper, or any other answer, the item is deferred
as keep_failed and nothing is touched. The keeper itself is VELDO-0345. This module only refuses to
run without it.

THE KEEP STEP'S ANSWER IS CHECKED AGAINST THE ITEM AT THE MOMENT OF THE REMOVE. tips is what `tips`
of this module read in the item when the keeper recorded it: the checked-out commit and branch, the
commits an operation in progress names, the item's own refs and every commit its log names; for an
agent repository every ref, every stash entry and every log. The remover reads them again as its last
look, under the marked name, and any difference is keep_failed with the item moved back: a commit
made after the keep step is on no kept ref. snapshot, when the answer holds one, is {files: {path:
{mode, sha256}}}, the files the keep step saved outside git.

THE WORKTREE REMOVER enforces the save itself. git's non-forced worktree remove refuses a modified
tracked file, an untracked file, a lock and a submodule, and it deletes ignored files without a word
(measured in this ticket's proof). So, after the keep step:

  1. the worktree is moved to its marked name by git's worktree move, with no force option. A refusal
     (a locked worktree, a submodule) is remove_refused with the worktree at its path;
  2. the in-use probe is run again there; a user moves it back, in_use;
  3. git's status is read there with every ignored path. An ignored folder that a committed ignore
     file of the worktree or a build output pattern the project declares covers is build output; in
     a worktree reconcile adopted, whose history nobody saw, only the declared patterns count (design
     6.3). Every other ignored path is work (design 0.1): a file only info/exclude ignores, a loose
     ignored file such as a local settings file, whatever rule covers it. So is a tracked file git
     was told not to look at (the assume-unchanged or the skip-worktree bit) whose content on disk is
     not the index's or cannot be read: git's status and git's own remove are blind to it, so it is
     never left to git. Each such file must be in the keep step's snapshot with the same mode and
     digest, or the worktree is moved back, keep_failed;
  4. the tips are read again and compared with the keep step's;
  5. git's worktree remove is run on the marked name, with no force option. Its refusal moves the
     worktree back and is remove_refused.

A repository inside the worktree stops it as it stops a folder. Every git command is run through the
one Git boundary (git_process.py, the sibling of this file): no GIT_ variable of the caller and no
system or global configuration reaches it, so a file only a personal excludes file ignores is an
untracked file to it. The probes' git reads go through the same boundary.

THE AGENT REPOSITORY REMOVER makes its last look under the marked name too, after the second probe:
a repository with a work tree is refused, keep_failed, on any modified, staged or untracked entry, on
any ignored path that is work and on any tracked file hidden from git's status whose content is not
the index's, because nothing has saved them (the snapshot of a worker clone and its file by file
comparison are VELDO-0347); then the tips are compared. A repository that has linked worktrees, any
entry of git's worktree list besides its own, one git could clear away included, is refused,
keep_failed, whether it is bare or not: the index, the HEAD and git's record of each linked worktree
are files inside the repository's folder, and no keep step saves a linked worktree's index yet.

THE DOCKER REMOVERS name one object to the engine, on the item's engine context: a container by its
id, an image by its tag, a volume by its name, a network by its id. A DOCKER OBJECT IS REMOVED ONLY
WHEN THE OBJECT FOUND NOW IS PROVABLY THE ONE THE ITEM RECORDED. A name proves nothing: a volume or a
tag can be removed and made again under the same name, holding new data. So the item's locator must
hold the identity seen when the object was made (IDENTITY):

  container, network   id, the engine's Id of the object
  image_tag            id, the Id of the image the tag named; never the tag alone
  volume               created_at, the engine's CreatedAt of the volume (an engine gives a volume no
                       Id), and with it the label that made it the run's: run_label, the value of the
                       run's label (RUN_LABEL, design 6.4), or compose_project

A locator without it is remove_refused, with the reason, and the engine is asked nothing: such an
item waits and is never removed. A compose project label alone is no identity, because the same
project makes the object again under the same name and label. With the identity there, the engine
shows the object and every recorded field is compared with it: the Id, CreatedAt, the run's label
and the compose project label. An object the engine cannot show and one that differs in any of them
is not the object the item recorded, and is remove_refused with nothing but the inspect asked of the
engine. The engine's refusal (a container uses the image or the volume, an endpoint is attached) is
remove_refused. A container that does not stop is not removed.

WHAT EACH ANSWER HOLDS (design 4.1, removal). bytes: the item's bytes measured just before, with
bytes_source (measured; last_measurement when the engine gives no figure and the ledger's last
measurement is used; None when there is neither). pool, pool_free_before and pool_free_after: the free
space of the item's pool, read through `free(pool record)` before and after. freed: the difference of
those two readings and nothing else; no figure a tool reports as reclaimed is used. host: for an item
on an engine image pool, the backing filesystem pool with its own free_before, free_after and freed,
kept apart, because a removal inside an engine's image does not grow the host's free space. A free
reading that fails before the removal refuses it; one that fails after it leaves that figure None.

A REFUSAL is {ok: False, reason: space_deferred:<deferral>, deferral, said} with the figures read so
far. The deferrals: remove_refused (the tool refused, or the remover refused by itself), in_use (the
second probe), keep_failed (the keep step, and a last look that finds work the keep step did not
save).

Standard library only. The ledger is the control_space.Ledger and the probe the control_space_probe
module the caller passes in.
"""
import fnmatch
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess


def _sibling(name):
    spec = importlib.util.spec_from_file_location('veldo_space_remove_' + name,
                                                  Path(__file__).resolve().with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_git_process = _sibling('git_process')

SCHEMA = 'veldo.control_space_remove/v1'

MARK = '.veldo-removing.'  # between a folder's own name and its item's id, in its marked name
SECONDS = 3600  # the longest one command of a tool may take
REFUSED, IN_USE, KEEP_FAILED = 'remove_refused', 'in_use', 'keep_failed'
BLOCK = 512  # the unit of st_blocks
DIRECTORY = os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
NAMED = 20  # the most paths named in one refusal
GIT_FOLDER = frozenset(('HEAD', 'objects', 'refs'))  # a folder holding these is a git folder
# What an operation in progress names, and the refs a worktree has of its own.
OPERATION_REFS = ('ORIG_HEAD', 'MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'REBASE_HEAD', 'BISECT_HEAD')
OWN_REFS = ('refs/bisect', 'refs/worktree', 'refs/rewritten')
PLAIN = frozenset('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_')


class _Refusal(Exception):
    def __init__(self, deferral, said, **more):
        Exception.__init__(self, said)
        self.deferral, self.said, self.more = deferral, said, more


class _Stop(Exception):
    """A delete or a measurement that may not go on."""


def _run(argv, cwd=None):
    """Run a client and return (exit code, output). A client that is missing or does not end in time
    gives (None, what happened). A git argument vector, which the probes hand to this runner, is run
    through the one Git boundary and by nothing else."""
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


def _said(error):
    return type(error).__name__ + ': ' + str(error)[:300]


def _git(commands, *argv, feed=None):
    """One git command of the remover's own, through the Git boundary: (exit code, output). The
    command the process was given is added to `commands`."""
    given = dict(env=dict(os.environ, LC_ALL='C'), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                 timeout=SECONDS)
    given.update({'stdin': subprocess.DEVNULL} if feed is None else {'input': feed})
    try:
        done = _git_process.run(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false']
                                + [str(word) for word in argv], **given)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        if commands is not None and getattr(error, 'cmd', None):
            commands.append([str(word) for word in error.cmd])
        return None, _said(error)
    if commands is not None:
        commands.append([str(word) for word in done.args])
    if done.returncode:
        return done.returncode, done.stderr.decode('utf-8', 'replace').strip()[-300:]
    return 0, done.stdout.decode('utf-8', 'surrogateescape')


def marked(path, identity):
    """The marked name of the folder `path` of the item `identity`: beside it, with the item's id. A
    character of the id that is not a letter, a digit, - or _ is written as ~ and its code in
    hexadecimal, so two ids never share a marked name and `unmarked` reads the id back."""
    path = path.rstrip('/')
    tail = ''.join(c if c in PLAIN else ''.join('~%02x' % byte for byte in c.encode('utf-8'))
                   for c in str(identity).rsplit(':', 1)[-1])
    return os.path.join(os.path.dirname(path), os.path.basename(path) + MARK + tail)


def unmarked(name):
    """The path and the id's last part a marked name was made from: (path, id part), or None when
    `name` is not a marked name."""
    folder, base = os.path.split(name.rstrip('/'))
    own, mark, tail = base.rpartition(MARK)
    if not mark or not own or not tail:
        return None
    try:
        raw = bytearray()
        while tail:
            if tail[0] == '~':
                raw.append(int(tail[1:3], 16))
                tail = tail[3:]
            elif tail[0] in PLAIN:
                raw.extend(tail[0].encode())
                tail = tail[1:]
            else:
                return None
        return os.path.join(folder, own), raw.decode('utf-8')
    except (ValueError, IndexError):
        return None


def left(path, identity):
    """The marked name of the item when something is there now, a folder or a worktree a removal that
    stopped or was killed left under it; None only when the kernel said nothing is (ENOENT). Any
    other answer of os.lstat (a folder above it that may not be searched, a failing disk) is raised
    as the OSError it is: a name that could not be read is not a name with nothing under it, and the
    caller must not mark the item gone on it. Signal and reconcile ask before they mark an item gone
    (design 8.8)."""
    name = marked(path, identity)
    try:
        os.lstat(name)
    except FileNotFoundError:
        return None
    return name


def _plain(path):
    """The path, when it is absolute and leads where its own text says: no `.`, no `..`, no doubled
    slash and no link on the way. Anything else is refused: the remover follows no link by itself."""
    if not isinstance(path, str) or not path:
        raise _Refusal(REFUSED, 'the locator names no path')
    path = path.rstrip('/')
    if not os.path.isabs(path) or os.path.normpath(path) != path:
        raise _Refusal(REFUSED, 'the path is not a plain absolute path: ' + path)
    if os.path.realpath(path) != path:
        raise _Refusal(REFUSED, 'the path is reached through a link: ' + path)
    return path


def _parent(path):
    """A descriptor of the folder the plain path `path` is in, opened from / down with no link
    followed. The caller closes it."""
    descriptor = os.open('/', os.O_PATH | DIRECTORY)
    try:
        for part in os.path.dirname(path).split('/'):
            if part:
                inner = os.open(part, os.O_PATH | DIRECTORY, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = inner
    except OSError as error:
        os.close(descriptor)
        raise _Refusal(REFUSED, 'the folder the path is in could not be opened with no link followed: '
                       + _said(error))
    return descriptor


def _there(name, dir_fd):
    try:
        os.lstat(name, dir_fd=dir_fd)
    except FileNotFoundError:
        return False
    return True


def mount_point(path):
    """Whether a filesystem is mounted at the folder `path`."""
    return os.path.ismount(path)


# ---------------------------------------------------------------------------------------------
# Measuring and deleting a folder, through descriptors and without following a link.
# ---------------------------------------------------------------------------------------------

def _open_up(name, dir_fd=None):
    """Give the owner every permission on a directory, through a descriptor of the directory itself."""
    inner = os.open(name, os.O_PATH | DIRECTORY, dir_fd=dir_fd)
    try:
        mode = stat.S_IMODE(os.fstat(inner).st_mode)
        if mode & 0o700 != 0o700:
            os.chmod('/proc/self/fd/%d' % inner, mode | 0o700)
    finally:
        os.close(inner)


def _walk(name, dir_fd, device, seen, open_up, own=None, depth=0, allowed=None, relative=''):
    if open_up:
        _open_up(name, dir_fd)
    descriptor = os.open(name, os.O_RDONLY | DIRECTORY, dir_fd=dir_fd)
    try:
        here = os.fstat(descriptor)
        if here.st_dev != device:
            raise _Stop('another filesystem is mounted inside the folder, at %s' % name)
        total = here.st_blocks * BLOCK
        with os.scandir(descriptor) as entries:
            listing = list(entries)
        names = set(entry.name for entry in listing)
        pushed = False
        if own is not None and ('.git' in names or GIT_FOLDER <= names):
            # The item's own repository is its top, and the git folder right beneath its top.
            if not (own and (depth == 0 or (depth == 1 and name == '.git'))):
                # A clean clone the last look read (VELDO-0347 AC2) goes with the folder; no other does.
                if allowed is None or relative not in allowed:
                    raise _Stop('a git repository is in the folder, at %s' % name)
                pushed = True
        for entry in listing:
            if entry.is_dir(follow_symlinks=False):
                # The git folder of a clean clone is not looked into: the look read its refs and logs.
                inner = None if pushed and ('.git' not in names or entry.name == '.git') else own
                total += _walk(entry.name, descriptor, device, seen, open_up, inner, depth + 1, allowed,
                               os.path.join(relative, entry.name))
                continue
            found = entry.stat(follow_symlinks=False)
            if found.st_nlink > 1:
                if (found.st_dev, found.st_ino) in seen:
                    continue
                seen.add((found.st_dev, found.st_ino))
            total += found.st_blocks * BLOCK
        return total
    finally:
        os.close(descriptor)


def measure(path, device=None, open_up=False, own=None, dir_fd=None, allowed=None):
    """The bytes the folder `path` takes on disk: every file and directory in it, a file with several
    names counted once, no link followed. With `open_up`, directories the owner cannot enter are opened
    up on the way. `own` says what the walk does with a git repository: None, nothing; False, any
    folder that is one or holds one stops it; True, the same but for the folder's own, at its top.
    `path` is a name inside `dir_fd` when one is given. `allowed` names, by their paths inside the
    folder, the repositories that do not stop the walk: the clean clones the last look read. Raises
    OSError for what cannot be read and _Stop for a filesystem mounted inside and for a repository."""
    device = os.lstat(path, dir_fd=dir_fd).st_dev if device is None else device
    return _walk(path, dir_fd, device, set(), open_up, own, allowed=allowed)


def _delete(name, dir_fd, device, before_file=None, relative='', last=None):
    """Delete the folder `name` of `dir_fd` and everything in it, through descriptors, no link
    followed. `before_file(path inside, descriptor, name)` is called for each file immediately before
    it is deleted and may raise to stop the delete there. `last` names the entry of the top folder
    that is deleted after every other: a repository's git folder, so that a delete that stops leaves
    a repository git can still read."""
    descriptor = os.open(name, os.O_RDONLY | DIRECTORY, dir_fd=dir_fd)
    try:
        if os.fstat(descriptor).st_dev != device:
            raise _Stop('another filesystem is mounted inside the folder, at %s' % name)
        with os.scandir(descriptor) as entries:
            listing = [(entry.name, entry.is_dir(follow_symlinks=False)) for entry in entries]
        for inner, directory in sorted(listing, key=lambda entry: (entry[0] == last, entry)):
            child = os.path.join(relative, inner)
            if directory:
                if before_file is None:
                    _delete(inner, descriptor, device)
                else:
                    _delete(inner, descriptor, device, before_file, child)
            else:
                deleted = None
                if before_file is not None:
                    deleted = before_file(child, descriptor, inner)
                os.unlink(inner, dir_fd=descriptor)
                if deleted is not None:
                    deleted()
    finally:
        os.close(descriptor)
    os.rmdir(name, dir_fd=dir_fd)


# ---------------------------------------------------------------------------------------------
# The figures.
# ---------------------------------------------------------------------------------------------

def _free(ctx, pool):
    try:
        value = ctx['free'](pool)
    except Exception:  # noqa: BLE001 - a reader that fails has read nothing
        return None
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _before(ctx, record, answer):
    """Read the free space of the item's pool, and of the filesystem behind an engine image pool,
    before anything is removed. A figure that cannot be read refuses the removal."""
    ledger = ctx['ledger']
    pool = ledger.pool(record.get('pool'))
    if pool is None:
        raise _Refusal(REFUSED, 'the item names no pool of this host')
    answer['pool_free_before'] = _free(ctx, pool)
    backing = None
    if pool.get('type') == 'engine_image':
        backing = ledger.pool(pool.get('backing'))
        if backing is None:
            raise _Refusal(REFUSED, 'the engine image pool %s names no backing pool' % pool.get('name'))
        answer['host'] = {'pool': backing['name'], 'free_before': _free(ctx, backing), 'free_after': None,
                          'freed': None}
    if answer['pool_free_before'] is None or (backing is not None and answer['host']['free_before'] is None):
        raise _Refusal(REFUSED, 'the free space of the pool could not be read before the removal')
    return pool, backing


def _after(ctx, pools, answer):
    pool, backing = pools
    before, after = answer['pool_free_before'], _free(ctx, pool)
    answer['pool_free_after'] = after
    answer['freed'] = after - before if after is not None else None
    if backing is not None:
        host = answer['host']
        host['free_after'] = _free(ctx, backing)
        host['freed'] = host['free_after'] - host['free_before'] if host['free_after'] is not None else None


# ---------------------------------------------------------------------------------------------
# The folder remover.
# ---------------------------------------------------------------------------------------------

def _second_probe(ctx, path):
    """The in-use probe on `path`, read as rule 4 reads it: what it found, or None for no user."""
    reads = {'run': ctx['run']}
    if ctx['proc']:
        reads['proc'] = ctx['proc']
    facts = ctx['probe'].in_use(path, ctx['ledger'].engines, **reads)
    unread = facts['unread']
    reaching = [entry for entry in unread['processes'] if entry.get('reach') is not None]
    if (facts['in_use'] or reaching or unread['engines'] or unread['table'] is not None
            or unread['git'] is not None or not facts['git']['read']):
        return {'processes': facts['processes'], 'containers': facts['containers'], 'git': facts['git'],
                'unread': dict(unread, processes=reaching)}
    return None


def _put_back(parent, tail, base):
    """Rename what is left under the marked name back to its own name, both names inside the one
    folder `parent` is a descriptor of. None, or why it could not be."""
    try:
        if not _there(tail, parent):
            return None
        if _there(base, parent):
            raise FileExistsError('something is at the path now')
        os.rename(tail, base, src_dir_fd=parent, dst_dir_fd=parent)
    except OSError as error:
        return _said(error)
    return None


def _folder(ctx, identity, record, path, own=False, look=None, before_file=None, last=None, open_first=False):
    """Rename, second probe, last look, delete. Returns the bytes measured just before the delete.
    `own` is measure's: whether the folder may be a repository of its own. `look(marked name)`, when
    given, is the last look at the folder under its marked name; its refusal puts the folder back,
    and a set it returns names the clean clones inside the folder that go with it (measure's
    allowed). With `open_first` the directories a confined process left shut are opened up before
    the look, which has to list them. `before_file` and `last` are _delete's. A refusal `before_file` raises stops the
    delete there, and the folder, with what is left in it, is renamed back to its path before the
    refusal is answered (design 0.3): the item keeps its locator."""
    ledger = ctx['ledger']
    path = _plain(path)
    name = marked(path, identity)
    base, tail = os.path.basename(path), os.path.basename(name)
    parent = _parent(path)
    try:
        try:
            found = os.lstat(base, dir_fd=parent)
        except OSError as error:
            raise _Refusal(REFUSED, 'the path could not be read: ' + _said(error))
        if not stat.S_ISDIR(found.st_mode):
            raise _Refusal(REFUSED, 'the path is not a folder')
        if mount_point(path):
            raise _Refusal(REFUSED, 'the folder is a mount point')
        pool = ledger.pool(record.get('pool'))
        if pool is None or pool.get('type') != 'filesystem' or ledger.device(path) != pool.get('device'):
            raise _Refusal(REFUSED, 'the folder is not on the item\'s pool')
        if _there(tail, parent):
            raise _Refusal(REFUSED, 'something is already at the marked name', marked=name)
        try:
            os.rename(base, tail, src_dir_fd=parent, dst_dir_fd=parent)
        except OSError as error:
            raise _Refusal(REFUSED, 'the folder could not be renamed: ' + _said(error))
        try:
            use = _second_probe(ctx, name)
            if use is None:
                if open_first:
                    measure(tail, found.st_dev, open_up=True, dir_fd=parent)
                looked = look(name) if look is not None else None
                clones = {'allowed': looked} if isinstance(looked, (set, frozenset)) and looked else {}
                size = measure(tail, found.st_dev, open_up=True, own=own, dir_fd=parent, **clones)
                given = ([] if before_file is None else [before_file])
                _delete(tail, parent, found.st_dev, *given, **({} if last is None else {'last': last}))
                return size
            refusal = _Refusal(IN_USE, 'the folder is in use under its marked name', found=use)
        except _Refusal as refused:
            refusal = refused
        except (OSError, RecursionError, _Stop) as error:
            refusal = _Refusal(REFUSED, 'the delete stopped: ' + _said(error))
        except BaseException:
            _put_back(parent, tail, base)
            raise
        stuck = _put_back(parent, tail, base)
        if stuck is not None:
            refusal.more.update(left_at=name, not_put_back=stuck)
        raise refusal
    finally:
        os.close(parent)


# ---------------------------------------------------------------------------------------------
# The keep step, given, and the last look that holds it to its answer.
# ---------------------------------------------------------------------------------------------

def _kept(ctx, identity, record):
    """The keep step, given. Anything but {ok: True, tips: {...}} is keep_failed and nothing is
    touched. Returns the answer."""
    if ctx['keep'] is None:
        raise _Refusal(KEEP_FAILED, 'no keep step was given: the commits of this item are recorded nowhere')
    try:
        said = ctx['keep'](identity, record)
    except Exception as error:  # noqa: BLE001 - a keeper that fails has kept nothing
        raise _Refusal(KEEP_FAILED, 'the keep step failed: ' + _said(error))
    if not isinstance(said, dict) or said.get('ok') is not True:
        raise _Refusal(KEEP_FAILED, 'the keep step did not keep the item', keep=said)
    if not isinstance(said.get('tips'), dict):
        raise _Refusal(KEEP_FAILED, 'the keep step did not say which tips it recorded', keep=said)
    return said


def tips(path, kind='worktree', commands=None):
    """What names a commit in the item at `path`, read now through the Git boundary: {head, branch,
    operations: {name: commit}, refs: [commit and ref], log: [commits], stash: [commits]}. For a
    worktree refs are its own (OWN_REFS) and log is its HEAD log; for an agent repository, or any
    other private repository, refs are every ref, log is every log and stash is every stash entry.
    None when git could not read any of it. The keeper answers with what this read when it recorded
    the commits, and the remover reads it again just before it removes."""
    private = kind != 'worktree'

    def read(*argv, absent=False):
        code, out = _git(commands, '-C', path, *argv)
        if code == 0:
            return out
        if absent and code == 1 and not str(out).strip():
            return None
        raise _Stop('git could not read the item: ' + str(out)[:200])

    def one(*argv):
        out = read(*argv, absent=True)
        return out.strip() if out is not None else None

    try:
        found = {'head': one('rev-parse', '--verify', '--quiet', 'HEAD^{commit}'),
                 'branch': one('symbolic-ref', '--quiet', 'HEAD'), 'operations': {}}
        for name in OPERATION_REFS:
            commit = one('rev-parse', '--verify', '--quiet', name)
            if commit is not None:
                found['operations'][name] = commit
        found['refs'] = sorted(read('for-each-ref', '--format=%(objectname) %(refname)',
                                    *(() if private else OWN_REFS)).split('\n')[:-1])
        found['log'] = sorted(set(read('rev-list', '--walk-reflogs', *(['--all'] if private else ['HEAD'])).split()))
        stashed = private and any(line.endswith(' refs/stash') for line in found['refs'])
        found['stash'] = read('rev-list', '--walk-reflogs', 'refs/stash').split() if stashed else []
    except _Stop:
        return None
    return found


def _declared(ctx, record, key):
    """What the project that owns the item declares under `key`."""
    scope = (record.get('owner') or {}).get('scope') or {}
    declared = [project.get(key) or [] for project in ctx['ledger'].projects
                if scope.get('type') == 'project' and project.get('project') == scope.get('id')]
    return list(declared[0]) if declared else []


def _digest(path):
    """The mode and the SHA-256 of one file, no link followed; a link's digest is of where it points."""
    found = os.lstat(path)
    digest = hashlib.sha256()
    if stat.S_ISLNK(found.st_mode):
        digest.update(os.fsencode(os.readlink(path)))
    elif stat.S_ISREG(found.st_mode):
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(descriptor, 'rb') as file:
            for block in iter(lambda: file.read(1 << 20), b''):
                digest.update(block)
    return {'mode': found.st_mode, 'sha256': digest.hexdigest()}


def _hidden(commands, read, where):
    """The tracked files git was told not to look at, by the assume-unchanged or the skip-worktree bit,
    that are on disk with content that is not the index's, or that cannot be read. git's status names
    none of them and git's worktree remove takes them without a word."""
    hidden = []
    for entry in read('ls-files', '-v', '-s', '-z').split('\0')[:-1]:
        head, _, name = entry.partition('\t')
        tag, mode, blob = (head.split(' ') + ['', ''])[:3]
        if not (tag.islower() or tag.upper() == 'S'):
            continue  # neither bit: git's status reads this file
        full = os.path.join(where, name)
        try:
            found = os.lstat(full)
        except (FileNotFoundError, NotADirectoryError):
            continue  # not on disk: nothing of it is only here
        except OSError:
            hidden.append(name)
            continue
        code, out = None, ''
        if stat.S_ISLNK(found.st_mode) and mode == '120000':
            code, out = _git(commands, '-C', where, 'hash-object', '--stdin', feed=os.fsencode(os.readlink(full)))
        elif stat.S_ISREG(found.st_mode) and mode.startswith('100'):
            code, out = _git(commands, '-C', where, 'hash-object', '--', name)
        if code != 0 or out.strip() != blob:
            hidden.append(name)  # other content, another type, or a file that cannot be read
    return hidden


def _looked(ctx, record, where):
    """_looked_all without the build output folders: (changed, work)."""
    return _looked_all(ctx, record, where)[:2]


def _looked_all(ctx, record, where):
    """The work tree at `where` as git reads it now, every ignored path included: (changed, work,
    build), build naming the ignored folders that are build output.
    changed names the modified, staged and untracked entries. work names every ignored file that is
    work: all but what lies in an ignored folder that a committed ignore file of this work tree or a
    build output pattern the project declares covers (design 0.1); for a worktree reconcile adopted
    only the declared patterns count (design 6.3). work also names every tracked file hidden from
    git's status whose content is not the index's (_hidden). Raises _Stop when git cannot say."""
    commands = ctx['commands']

    def read(*argv, feed=None):
        code, out = _git(commands, '-C', where, *argv, feed=feed)
        if code != 0:
            raise _Stop('git could not read the work tree: ' + str(out)[:200])
        return out

    entries = read('status', '--porcelain=v1', '-z', '--ignored=matching', '--untracked-files=all').split('\0')[:-1]
    changed, ignored = [], []
    while entries:
        entry = entries.pop(0)
        state, name = entry[:2], entry[3:]
        if 'R' in state or 'C' in state:
            entries.pop(0)  # the name it was renamed or copied from
        (ignored if state == '!!' else changed).append(name)
    folders = [name for name in ignored if name.endswith('/')]
    work = [name for name in ignored if not name.endswith('/')]  # a loose ignored file is work
    work.extend(_hidden(commands, read, where))
    build = []
    if folders:
        rules = read('check-ignore', '-v', '-z', '--stdin',
                     feed=b''.join(os.fsencode(name) + b'\0' for name in folders)).split('\0')[:-1]
        source = {rules[at + 3]: rules[at] for at in range(0, len(rules) - 3, 4)}
        named = sorted(set(found for found in source.values()
                           if not os.path.isabs(found) and os.path.basename(found) == '.gitignore'))
        committed = set(read('ls-files', '-z', '--', *named).split('\0')[:-1]) if named else set()
        if record.get('adopted'):
            committed = set()  # nobody saw what was made in it: its ignore files prove nothing (design 6.3)
        patterns = _declared(ctx, record, 'build_output')
        for folder in folders:
            base = os.path.basename(folder.rstrip('/'))
            if source.get(folder) in committed or any(fnmatch.fnmatchcase(base, pattern) for pattern in patterns):
                build.append(folder)
                continue  # build output: a build makes it again
            top, inside = os.path.join(where, folder.rstrip('/')), []
            for at, _, files in os.walk(top, onerror=_raise):
                inside.extend(os.path.relpath(os.path.join(at, name), where) for name in files)
            work.extend(inside)  # an empty folder holds no work
    return changed, sorted(set(work)), build


def _raise(error):
    raise error


def _unsaved(where, work, snapshot):
    """The paths of `work` the keep step's snapshot does not hold with the same mode and digest."""
    files = snapshot.get('files') if isinstance(snapshot, dict) else None
    files = files if isinstance(files, dict) else {}
    return [name for name in work
            if not isinstance(files.get(name), dict)
            or {key: files[name].get(key) for key in ('mode', 'sha256')} != _digest(os.path.join(where, name))]


def _linked(ctx, where):
    """The linked worktrees of the repository at `where`: every entry of git's worktree list besides
    the first, which is the repository itself, one git could clear away included."""
    code, out = _git(ctx['commands'], '-C', where, 'worktree', 'list', '--porcelain', '-z')
    entries = [field[len('worktree '):] for field in str(out).split('\0') if field.startswith('worktree ')]
    if code != 0 or not entries:
        raise _Stop('git could not list the worktrees of the repository: ' + str(out)[:200])
    return entries[1:]


def _last_look(ctx, record, kept, where):
    """The last look at a worktree or an agent repository under its marked name `where`, after the
    in-use probe: the work nothing saved, then the tips against the keep step's. Raises the refusal."""
    private = record.get('kind') != 'worktree'
    try:
        bare = False
        if private:
            code, out = _git(ctx['commands'], '-C', where, 'rev-parse', '--is-bare-repository')
            if code != 0:
                raise _Stop('git could not read the repository: ' + str(out)[:200])
            bare = out.strip() == 'true'
            linked = _linked(ctx, where)
            if linked:
                raise _Refusal(KEEP_FAILED, 'the repository has linked worktrees, and no keep step saves the '
                               'index of one: ' + ', '.join(linked[:3]), linked=linked[:NAMED],
                               more=max(0, len(linked) - NAMED))
        changed, work = ([], []) if bare else _looked(ctx, record, where)
        # git's own remove refuses a worktree's changed entries; nothing refuses a repository's.
        unsaved = (changed + work) if private else _unsaved(where, work, kept.get('snapshot'))
    except (OSError, ValueError, RecursionError, _Stop) as error:
        raise _Refusal(KEEP_FAILED, 'the last look could not be made: ' + _said(error))
    if unsaved:
        raise _Refusal(KEEP_FAILED, 'files that are work are in no snapshot of the keep step: '
                       + ', '.join(unsaved[:3]), unsaved=unsaved[:NAMED], more=max(0, len(unsaved) - NAMED))
    now = tips(where, record.get('kind'), ctx['commands'])
    if now is None or now != kept['tips']:
        differ = sorted(key for key in set(now or {}) | set(kept['tips'])
                        if (now or {}).get(key) != kept['tips'].get(key))
        raise _Refusal(KEEP_FAILED, 'the item is not as the keep step recorded it: ' + ', '.join(differ),
                       differ=differ, tips=now)


def _clean_clones(ctx, where):
    """The last look at a scratch or build output folder under its marked name `where` (VELDO-0347
    AC2): every git repository beneath it, read now by the probe. Returns the paths inside the folder
    of those that are clean clones, which go with it. One that is not a clean clone, one that cannot
    be read and a folder that cannot be listed refuse, in_use: the repository holds the folder."""
    probe = ctx['probe']
    beneath = probe.nested(where)
    if not beneath.get('read'):
        raise _Refusal(IN_USE, 'a folder beneath the item could not be listed', found=beneath)
    allowed = set()
    for repository in beneath.get('repositories') or ():
        read = probe.clean_clone(repository, ctx['run'])
        inside = os.path.relpath(repository, where)
        if read.get('read') is not True or read.get('clean_clone') is not True:
            raise _Refusal(IN_USE, 'a git repository in the folder is not a clean clone: ' + inside,
                           repository=inside, why=read.get('why'), commits=read.get('commits'),
                           unread=read.get('said'))
        allowed.add(inside)
        allowed.update(os.path.relpath(inner, where) for inner in read.get('inside') or ())
    return allowed


def _r_folder(ctx, identity, record, answer):
    answer['method'] = 'rename_probe_delete'
    pools = _before(ctx, record, answer)
    answer['bytes'], answer['bytes_source'] = _folder(
        ctx, identity, record, record['locator']['path'], look=lambda name: _clean_clones(ctx, name),
        open_first=True), 'measured'
    _after(ctx, pools, answer)


WORKER_CLONE = 'worker_clone'


def _signature(found):
    """What says a file is the one that was looked at and has not been written since."""
    return (found.st_dev, found.st_ino, found.st_mode, found.st_size, found.st_mtime_ns, found.st_ctime_ns)


def _clone_look(ctx, record, kept, where, state):
    """The last look at a worker clone under its marked name `where` (VELDO-0347 AC3): every file of
    its work tree that is work is in the keep step's snapshot with the same mode and digest, and the
    tips are the keep step's. It fills `state` with what the delete compares each file with:
    files, the snapshot's rows; unchanged, the tracked files git reads as unchanged, each with what
    os.lstat said of it before git's status was read; build, the ignored folders that are build
    output. Raises the refusal."""
    commands = ctx['commands']
    try:
        linked = _linked(ctx, where)
        if linked:
            raise _Refusal(KEEP_FAILED, 'the repository has linked worktrees, and no keep step saves the '
                           'index of one: ' + ', '.join(linked[:3]), linked=linked[:NAMED],
                           more=max(0, len(linked) - NAMED))
        code, out = _git(commands, '-C', where, 'ls-files', '-z')
        if code != 0:
            raise _Stop('git could not list the tracked files: ' + str(out)[:200])
        seen = {}
        for name in out.split('\0')[:-1]:
            try:
                seen[name] = _signature(os.lstat(os.path.join(where, name)))
            except (FileNotFoundError, NotADirectoryError):
                pass  # deleted in the work tree: there is nothing to delete
        changed, work, build = _looked_all(ctx, record, where)
        snapshot = kept.get('snapshot') if isinstance(kept.get('snapshot'), dict) else {}
        there = [name for name in sorted(set(changed) | set(work)) if os.path.lexists(os.path.join(where, name))]
        unsaved = _unsaved(where, there, snapshot)
    except (OSError, ValueError, RecursionError, _Stop) as error:
        raise _Refusal(KEEP_FAILED, 'the last look could not be made: ' + _said(error))
    if unsaved:
        raise _Refusal(KEEP_FAILED, 'files that are work are in no snapshot of the keep step: '
                       + ', '.join(unsaved[:3]), unsaved=unsaved[:NAMED], more=max(0, len(unsaved) - NAMED))
    now = tips(where, record.get('kind'), commands)
    if now is None or now != kept['tips']:
        differ = sorted(key for key in set(now or {}) | set(kept['tips'])
                        if (now or {}).get(key) != kept['tips'].get(key))
        raise _Refusal(KEEP_FAILED, 'the item is not as the keep step recorded it: ' + ', '.join(differ),
                       differ=differ, tips=now)
    files = snapshot.get('files') if isinstance(snapshot.get('files'), dict) else {}
    state.update(files=files, build=build,
                 unchanged={name: found for name, found in seen.items() if name not in changed and name not in work})


def _clone_compare(state, relative, descriptor, name):
    """Called for each file of a worker clone immediately before it is deleted (design 0.3). A file of
    the git folder is covered by the kept refs. A file the snapshot holds must have the mode and the
    SHA-256 its manifest row records. A tracked file git read as unchanged must be as os.lstat found
    it before that read. A file in a build output folder is build output. Any other file, and one that
    differs, is work nothing saved: the delete stops there, keep_failed."""
    if relative.split('/', 1)[0] == '.git':
        return None
    expected = state['files'].get(relative)
    if isinstance(expected, dict):
        # Read by the descriptor used for the unlink, so a replaced parent cannot redirect the read.
        try:
            found = _digest('/proc/self/fd/%d/%s' % (descriptor, name))
        except OSError as error:
            raise _Refusal(KEEP_FAILED, 'a file of the worker clone could not be read: ' + relative, said=_said(error))
        if found != {key: expected.get(key) for key in ('mode', 'sha256')}:
            raise _Refusal(KEEP_FAILED, 'a file of the worker clone differs from its snapshot: ' + relative,
                           changed=relative)
        return None
    if relative in state['unchanged']:
        if _signature(os.lstat(name, dir_fd=descriptor)) != state['unchanged'][relative]:
            raise _Refusal(KEEP_FAILED, 'a tracked file of the worker clone changed after the last look: '
                           + relative, changed=relative)
        return None
    if any(relative.startswith(folder) for folder in state['build']):
        return None
    raise _Refusal(KEEP_FAILED, 'a file of the worker clone is in no snapshot: ' + relative, changed=relative)


def _r_agent_repository(ctx, identity, record, answer):
    answer['method'] = 'keep_then_rename_probe_delete'
    path = _plain(record['locator']['path'])
    saved = False
    if record.get('form') == WORKER_CLONE and ctx['keep'] is not None:
        # A worker clone of a run that has ended (VELDO-0347 AC3; rule 3 passed before this remover
        # was called): its uncommitted state is saved in the snapshot store by the keep step, and
        # each file is compared with the manifest immediately before it is deleted. One that cannot
        # be shown to be a worker clone is removed as any agent repository is, or not at all.
        shown = ctx['probe'].worker_clone(path, ((record.get('owner') or {}).get('run') or {}).get('id'),
                                          ctx['ledger'].state_root)
        saved = isinstance(shown, dict) and shown.get('clone') is True
    if saved:
        ctx['keep'] = _sibling('control_space_keep').keeper(ctx['ledger'], snapshot=True)
        answer['method'] = 'keep_snapshot_then_rename_probe_compare_delete'
    kept = _kept(ctx, identity, record)
    pools = _before(ctx, record, answer)
    if saved:
        state = {}
        answer['snapshot'] = (kept.get('snapshot') or {}).get('path')
        answer['bytes'], answer['bytes_source'] = _folder(
            ctx, identity, record, path, own=True,
            look=lambda name: _clone_look(ctx, record, kept, name, state),
            before_file=lambda relative, descriptor, name: _clone_compare(state, relative, descriptor, name),
            last='.git'), 'measured'
    else:
        answer['bytes'], answer['bytes_source'] = _folder(
            ctx, identity, record, path, own=True,
            look=lambda name: _last_look(ctx, record, kept, name)), 'measured'
    _after(ctx, pools, answer)


def clone_proposal(ledger, probe, identity, record, run=None):
    """The terms of the request a batch clone or a candidate workspace with files in no commit raises
    (VELDO-0347 AC3): the clone named as a clone, with its form and those files, read now. No remover
    carries a Save or a Discard of a private repository, so the terms offer Keep alone."""
    settlement = _sibling('control_request_settlement')
    path = record['locator']['path']
    patterns = [list(project.get('build_output') or ()) for project in ledger.projects
                if ((record.get('owner') or {}).get('scope') or {}).get('type') == 'project'
                and project.get('project') == record['owner']['scope'].get('id')]
    tree = probe.private_work(path, patterns[0] if patterns else (), bool(record.get('adopted')), run)
    if tree.get('read') is not True or not tree.get('files'):
        raise _Refusal(KEEP_FAILED, 'the clone\'s work tree could not be read for its files')
    return {'keep': settlement.SPACE_CLONE_KEEP,
            'clones': [{'item': identity, 'path': path, 'form': record.get('form'), 'files': list(tree['files'])}]}


def _worktree_remove(ctx, repository, path):
    """git's worktree remove; only the authenticated Discard context permits force."""
    if ctx.get('disposition') == 'discard':
        return _git(ctx['commands'], '-C', repository, 'worktree', 'remove', '--force', path)
    return _git(ctx['commands'], '-C', repository, 'worktree', 'remove', path)


def _worktree_move(ctx, repository, path, to):
    """git's own worktree move, with no force option: None, or why it was not made. git moves a
    worktree into a folder that is at the target, so a target that is there refuses first."""
    if os.path.lexists(to):
        return 'something is at ' + to
    code, out = _git(ctx['commands'], '-C', repository, 'worktree', 'move', path, to)
    if code != 0:
        return str(out)[:300] or 'git gave no answer'
    return None if os.path.isdir(to) and not os.path.lexists(path) else 'git said it moved the worktree and it is not there'


def _r_worktree(ctx, identity, record, answer):
    answer['method'] = 'keep_then_git_worktree_remove'
    path = _plain(record['locator']['path'])
    kept = _kept(ctx, identity, record)
    owner = record.get('owner') or {}
    review = (not record.get('branch') and not owner.get('ticket')
              and (owner.get('run') or {}).get('station') == 'review')
    if review:
        _review_scratch(ctx, identity, record, kept, answer)
    repository = ctx['probe'].repository(path, ctx['run'])
    if repository is None:
        raise _Refusal(REFUSED, 'git reads no repository at the worktree')
    name = marked(path, identity)
    if os.path.lexists(name):
        raise _Refusal(REFUSED, 'something is already at the marked name', marked=name)
    try:
        answer['bytes'], answer['bytes_source'] = measure(path, own=True), 'measured'
    except (OSError, RecursionError, _Stop) as error:
        raise _Refusal(REFUSED, 'the worktree could not be measured: ' + _said(error))
    pools = _before(ctx, record, answer)
    refused = _worktree_move(ctx, repository, path, name)
    if refused is not None:
        raise _Refusal(REFUSED, 'git refused the move to the marked name: ' + refused)
    try:
        use = _second_probe(ctx, name)
        if use is not None:
            raise _Refusal(IN_USE, 'the worktree is in use under its marked name', found=use)
        if ctx.get('disposition'):
            nested = ctx['probe'].nested(name)
            if not nested.get('read') or nested.get('repositories'):
                raise _Refusal(IN_USE, 'the worktree now holds a repository', found=nested)
        if ctx.get('disposition') == 'discard':
            _snapshot_equal(ctx, record, kept, name)
        else:
            _last_look(ctx, record, kept, name)
            if ctx.get('disposition') == 'save':
                _save_equal(ctx, record, kept, name)
        code, out = _worktree_remove(ctx, repository, name)
        if code != 0:
            raise _Refusal(REFUSED, 'git refused the remove: ' + str(out)[:300], code=code)
        if os.path.lexists(name):
            raise _Refusal(REFUSED, 'git said it removed the worktree and the folder is still there')
    except BaseException as stopped:
        stuck = _worktree_move(ctx, repository, name, path) if os.path.lexists(name) else None
        if stuck is not None and isinstance(stopped, _Refusal):
            stopped.more.update(left_at=name, not_put_back=stuck)
        raise
    _after(ctx, pools, answer)


def disposition_files(ledger, record, path):
    """The uncommitted files Discard would remove, as the owner is shown them.

    These are the names the snapshot saves: changed, untracked and ignored work, and deleted names
    too, because the index and the deletion are part of that state. A clean tracked file is in a
    commit and is not listed: a clean tree whose only unique work is unlanded commits has an empty
    list here and is asked about by its commits (VELDO-0327 AC2).
    """
    keeper = _sibling('control_space_keep')
    listing = keeper.listing(ledger, record, path)
    return sorted(set(listing['files']) | set(listing['deleted_worktree']) | set(listing['deleted_index']))


def disposition_commits(probe, path, landed=(), shared=None, run=None):
    """The tips of the unlanded commits that make the work unique (rule 5, case 5), or None when
    the worktree cannot be read."""
    facts = probe.unique_work(path, landed, shared, run)
    if facts.get('read') is not True:
        return None
    return [facts['unlanded']] if facts.get('unlanded') else []


def disposition_branch(record, taken=None):
    """The kept branch Save writes: named for the ticket, or for the owning run. With `taken`, the
    first such name it does not refuse: the name itself, then the name with -2, -3 and so on, so a
    second worktree of one ticket is saved beside the first and never onto it."""
    space = _sibling('control_space')
    owner = record.get('owner') or {}
    base = 'space-saved-' + space.kept_part(owner.get('ticket') or (owner.get('run') or {}).get('id') or 'none')
    if taken is None:
        return base
    for number in range(1, BRANCH_NAMES + 1):
        name = base if number == 1 else '%s-%d' % (base, number)
        if not taken(name):
            return name
    raise _Refusal(REFUSED, 'no kept branch name is free for this ticket')


BRANCH_NAMES = 1000
BRANCH_LEAVING = ('due', 'deferred', 'removing')  # a live branch item keep_branch does not record onto


def _kept_home(ledger, identity, record, path):
    """The repository the kept branch of a Discard is written in. A worktree of the main repository
    reaches it through its own path. A worktree inside an agent repository does not: that repository
    is private and is removed later, so its kept branch goes in the main repository, where the keep
    step has already put the commit on a kept ref (design 0.2, VELDO-0343 fix round 1). With no main
    repository at its path there is nowhere to keep the branch, and that is a refusal."""
    parent = ledger.item(record['parent']) if record.get('parent') else None
    if parent is None or parent.get('kind') != 'agent_repository':
        return path
    main = ledger.main_repository(identity)
    if not main or not os.path.isdir(main):
        raise _Refusal(REFUSED, 'no main repository is at its path to hold the kept branch of an agent worktree')
    return main


def _branch_holds(commands, path, branch, home=None):
    """What the kept branch `branch` is to the worktree at `path`: None when no such branch exists,
    False when it holds exactly the worktree's HEAD, True when it holds other work. The branch is
    read in the repository at `home`, or in the worktree's own."""
    code, held = _git(commands, '-C', home or path, 'rev-parse', '--verify', '--quiet', 'refs/heads/' + branch)
    if code == 1 and not str(held).strip():
        return None
    if code != 0:
        raise _Refusal(REFUSED, 'git could not read the kept branch: ' + str(held)[:200])
    code, head = _git(commands, '-C', path, 'rev-parse', '--verify', '--quiet', 'HEAD^{commit}')
    return not (code == 0 and held.strip() == head.strip())


def _free_branch(ledger, identity, record, path, commands):
    """The next kept branch name free for this worktree: one that no branch holding other work has,
    that no other item's open request has named for its detached commits, and that no branch item
    on its way out (due, deferred or removing) has: the Ledger records no kept branch onto such an
    item, so its name is taken whether or not the branch holds this commit (VELDO-0343 fix round 2)."""
    named = set()
    main = ledger.main_repository(identity)
    for other, item in ledger.items().items():
        if (item.get('kind') == 'branch' and item.get('state') in BRANCH_LEAVING
                and (item.get('locator') or {}).get('repository') == main):
            named.add(item['locator'].get('ref'))
        decision = item.get('disposition') or {}
        if other != identity and decision.get('state') in ('requested', 'authorized'):
            for tree in (decision.get('proposal') or {}).get('worktrees') or ():
                if tree.get('kept_branch'):
                    named.add(tree['kept_branch'])
    home = _kept_home(ledger, identity, record, path)
    if home != path:
        # An agent worktree's name is free in both repositories: Save writes it in the agent
        # repository, and the kept branch of a Discard is written in the main one.
        return disposition_branch(record, lambda name: name in named or any(
            _branch_holds(commands, path, name, where) is True for where in (path, home)))
    return disposition_branch(record, lambda name: name in named or _branch_holds(commands, path, name) is True)


def disposition_head(path, commands=None):
    """The commit the worktree's HEAD names as the request is built, or None for a HEAD with no
    commit. The request records it beside its terms, and Save and Discard run only at that commit."""
    code, head = _git(commands or [], '-C', path, 'rev-parse', '--verify', '--quiet', 'HEAD^{commit}')
    if code == 0:
        return head.strip()
    if code == 1 and not str(head).strip():
        return None
    raise _Refusal(KEEP_FAILED, 'git could not read the commit of the worktree')


def disposition_proposal(ledger, identity, record, commits):
    import shlex
    settlement = _sibling('control_request_settlement')
    path = record['locator']['path']
    code, branch = _git([], '-C', path, 'symbolic-ref', '-q', '--short', 'HEAD')
    if code not in (0, 1):
        raise _Refusal(KEEP_FAILED, 'git could not read the branch')
    branch = branch.strip() if code == 0 else None
    return {'discard': settlement.SPACE_DISCARD, 'worktrees': [{
        'item': identity, 'path': path, 'branch': branch, 'unheld_commits': branch is None,
        'kept_branch': _free_branch(ledger, identity, record, path, []) if branch is None else None,
        'files': disposition_files(ledger, record, path), 'commits': list(commits),
        'restore': 'veldo space restore ' + shlex.quote(identity)}]}


def _snapshot_equal(ctx, record, kept, path):
    keeper = _sibling('control_space_keep')
    try:
        now = keeper.listing(ctx['ledger'], record, path)
        if keeper._comparable(now) != keeper._comparable(kept.get('snapshot') or {}):
            raise _Refusal(KEEP_FAILED, 'the worktree differs from the saved snapshot')
        if tips(path, 'worktree', ctx['commands']) != kept['tips']:
            raise _Refusal(KEEP_FAILED, 'the commits differ from the keep record')
    except keeper._Failed as error:
        raise _Refusal(KEEP_FAILED, str(error)) from error


def _save_equal(ctx, record, kept, path):
    changed, work = _looked(ctx, record, path)
    saved = {name: row for name, row in (kept.get('snapshot') or {}).get('files', {}).items()
             if row.get('what') == 'ignored_work'}
    if changed or set(work) != set(saved) or _unsaved(path, work, {'files': saved}):
        raise _Refusal(KEEP_FAILED, 'the ignored work differs from the saved snapshot')
    # Rule 5 is read again under the marked name. The saved branch holds this HEAD.
    facts = ctx['probe'].unique_work(path, (), None, ctx['run'])
    cases = set(facts.get('cases') or [])
    if not facts.get('read') or facts.get('operation') or cases - {3}:
        raise _Refusal(KEEP_FAILED, 'rule 5 refused the saved worktree', found=facts)


def _r_disposition(ctx, identity, record, answer):
    ledger = ctx['ledger']
    current = ledger.item(identity) or {}
    decision = current.get('disposition') or {}
    choice = ctx['action']
    if (current.get('state') != 'removing' or decision.get('state') != 'authorized'
            or decision.get('choice') != choice):
        raise _Refusal(REFUSED, 'no signed disposition authorizes this removal')
    try:
        effect, owner = ledger.disposition_effect(identity, decision['request'])
    except Exception as error:
        raise _Refusal(REFUSED, 'the disposition is not settled: ' + _said(error)) from error
    if effect['choice'] != 'accept ' + choice or owner != decision['by']:
        raise _Refusal(REFUSED, 'the settled choice is not this removal')
    path = _plain(record['locator']['path'])
    shown = decision['proposal']['worktrees'][0]
    if 'head' not in decision:
        raise _Refusal(KEEP_FAILED, 'the request does not record the commit it was shown at')
    keeper = _sibling('control_space_keep')
    ctx['keep'] = keeper.keeper(ledger, event='space_disposition', snapshot=True)
    before = _kept(ctx, identity, record)
    saved = before.get('snapshot') or {}
    attempts = (ledger.item(identity).get('kept') or {}).get('snapshots') or []
    if saved.get('path'):
        attempt = next((one for one in attempts if one['path'] == saved['path']), None)
        manifest = keeper._manifest(attempt) if attempt else None
        if manifest is None:
            raise _Refusal(KEEP_FAILED, 'the saved manifest cannot be read back')
    else:
        manifest = {'files': {}, 'deleted_worktree': [], 'deleted_index': []}
    # What the owner was shown is compared with what was saved, never with a look made before the
    # save: a file written, or a commit made, at any moment up to the snapshot is in the manifest
    # and the keep record, and is not in the terms. Nothing runs, the worktree stays with everything
    # in it, and the next request names it. Below, the worktree is compared with this same snapshot,
    # here and again under the marked name, so what is removed is exactly what was shown.
    saved_names = sorted(set(manifest['files']) | set(manifest['deleted_worktree']) | set(manifest['deleted_index']))
    if saved_names != shown['files']:
        raise _Refusal(KEEP_FAILED, 'the file list differs from the list shown to the owner')
    if before['tips'].get('head') != decision['head']:
        raise _Refusal(KEEP_FAILED, 'the commits differ from the commits shown to the owner')
    before = dict(before, snapshot=manifest)
    _snapshot_equal(ctx, record, before, path)
    if choice == 'discard':
        # Discard never loses a commit (design 6.5, VELDO-0343): the kept branch of a detached
        # worktree is there, read back and on the Ledger before anything is moved or removed.
        _discard_branch(ctx, identity, record, path, answer, shown, before['tips'])
    if choice == 'save':
        _save_commit(ctx, identity, record, path, answer, shown)
        ctx['keep'] = keeper.keeper(ledger, event='space_disposition')
        after = _kept(ctx, identity, record)
        before = dict(after, snapshot=before['snapshot'])
    ctx['keep'] = lambda item, current: before
    ctx['disposition'] = choice
    _r_worktree(ctx, identity, record, answer)


# Only a branch holds a commit for a Discard: Veldo never deletes one. A tag can be moved or deleted
# and a remote-tracking ref goes with a prune (design 0), so neither is trusted alone, and a kept ref
# and a stash hold nothing (lead decision, VELDO-0343 fix round 2).
HOLDING_REFS = ('refs/heads/',)


def _discard_branch(ctx, identity, record, path, answer, shown, kept):
    """Only the settled Discard path calls this, before the worktree is moved or removed. For a
    detached worktree whose checked-out commit no branch of its repository reaches, create the kept
    branch at that commit, read it back, and have the Ledger record it as a branch item in state kept.
    A commit only a tag or a remote-tracking ref reaches gets a kept branch like any other. The branch
    is written in the main repository, for an agent's worktree too (_kept_home): never in the agent
    repository, which is removed later. The branch is named as Save names one: the name the terms
    showed, or the next one free. It is a ref write: no commit is made and nothing is removed. Any failure is the
    refusal remove_refused, and the worktree stays with everything in it.

    A worktree on a branch needs none: Discard removes the worktree and never the branch, in an agent
    repository as anywhere else. `kept` is what the keep step read: the commit is the one it recorded,
    which the caller has compared with the commit the owner was shown."""
    commit = kept.get('head')
    if kept.get('branch') is not None or not commit:
        return  # on a branch, which holds its commits and stays; or no commit at all
    commands = ctx['commands']
    home = _kept_home(ctx['ledger'], identity, record, path)
    branch = shown.get('kept_branch') or _free_branch(ctx['ledger'], identity, record, path, commands)
    ref = 'refs/heads/' + branch
    holders = []
    for where in dict.fromkeys((path, home)):
        code, out = _git(commands, '-C', where, 'for-each-ref', '--format=%(refname)', '--contains', commit,
                         *(prefix.rstrip('/') for prefix in HOLDING_REFS))
        if code != 0:
            raise _Refusal(REFUSED, 'git could not say which refs hold the commit: ' + str(out)[:200])
        holders += [name for name in out.split('\n')[:-1] if name.startswith(HOLDING_REFS)]
    # None: no such branch; False: it is at this commit. A branch at this commit under the kept name
    # is the one a Discard that stopped before its record left: it is recorded, never counted a holder.
    holds = _branch_holds(commands, path, branch, home)
    if holds is not False:
        if holders:
            answer['commit_held_by'] = holders[:NAMED]
            return  # a branch reaches the commit: it survives the worktree
        if holds:
            raise _Refusal(REFUSED, 'the kept branch name is taken by a branch that does not hold the commit',
                           kept_branch=branch, commit=commit)
        code, out = _git(commands, '-C', home, 'check-ref-format', '--branch', branch)
        if code != 0:
            raise _Refusal(REFUSED, 'git refused the kept branch name: ' + str(out)[:200], kept_branch=branch)
        # Created and never moved: the empty old value lets the write through only when no such ref is there.
        code, out = _git(commands, '-C', home, 'update-ref', '-m', 'veldo: kept branch before a Discard',
                         ref, commit, '')
        if code != 0:
            raise _Refusal(REFUSED, 'git refused the kept branch: ' + str(out)[:300], kept_branch=branch,
                           commit=commit)
    code, out = _git(commands, '-C', home, 'rev-parse', '--verify', '--quiet', ref + '^{commit}')
    if code != 0 or out.strip() != commit:
        raise _Refusal(REFUSED, 'the kept branch was not read back at the commit', kept_branch=branch, commit=commit)
    try:
        recorded = ctx['ledger'].keep_branch(identity, branch, commit)
    except Exception as error:  # noqa: BLE001 - a branch the Ledger did not record is not a kept branch
        raise _Refusal(REFUSED, 'the kept branch could not be recorded: ' + _said(error), kept_branch=branch)
    if not isinstance(recorded, dict) or recorded.get('ok') is not True:
        raise _Refusal(REFUSED, 'the Ledger did not record the kept branch', kept_branch=branch, found=recorded)
    answer['kept_branch'], answer['kept_branch_item'] = branch, recorded.get('branch_item')


def record_left_branch(ledger, identity, record, commands=None):
    """Reconcile calls this for a removing item it is about to defer. A Discard that stopped between
    its kept branch's write and the Ledger's record left a branch no item records. When the item is
    a worktree removing under an authorized Discard and the kept branch its terms named is there at
    the worktree's HEAD, the Ledger records it now, so an owner's Keep that follows cannot leave it
    unrecorded (VELDO-0343 fix round 2). It writes no ref and removes nothing; the Ledger reads the
    HEAD, the attachment and the branch itself and refuses what it does not find. Returns the
    Ledger's answer, or None when there is nothing to record or it could not be read."""
    decision = record.get('disposition') or {}
    if (record.get('kind') != 'worktree' or record.get('state') != 'removing'
            or decision.get('state') != 'authorized' or decision.get('choice') != 'discard'):
        return None
    try:
        branch = decision['proposal']['worktrees'][0].get('kept_branch')
        if not branch:
            return None
        commands = [] if commands is None else commands
        path = _plain(record['locator']['path'])
        home = _kept_home(ledger, identity, record, path)
        if _branch_holds(commands, path, branch, home) is not False:
            return None  # no such branch, or one that holds other work
        commit = disposition_head(path, commands)
        held = record.get('kept_branch') or {}
        if not commit or (held.get('branch'), held.get('commit')) == (branch, commit):
            return None  # no commit, or already recorded
        return ledger.keep_branch(identity, branch, commit)
    except Exception:  # noqa: BLE001 - reconcile defers the item whatever this read found
        return None


def _save_commit(ctx, identity, record, path, answer, shown):
    """Only the settled Save path calls this. Ignored files are never added."""
    def git(*args):
        code, out = _git(ctx['commands'], '-C', path, *args)
        if code != 0:
            raise _Refusal(REFUSED, 'Save refused: ' + str(out)[:300])
        return out.strip()
    ledger = ctx['ledger']
    # A detached worktree's terms name its kept branch, and Save writes that name or nothing. A
    # worktree on a branch is shown no kept name: Save takes the next one free for the ticket.
    branch = shown.get('kept_branch') or _free_branch(ledger, identity, record, path, ctx['commands'])
    git('check-ref-format', '--branch', branch)
    identity = _sibling('control_git_identity')
    bound = []
    if identity.exists(ledger.conn, 'git_identity_repositories'):
        bound = ledger.conn.execute('SELECT domain, repository FROM git_identity_repositories WHERE path=?',
                                    (ledger._main_of(record),)).fetchall()
    if len(bound) == 1:
        configured = identity.resolve(ledger.conn, *bound[0], path=ledger._main_of(record))
        name, email = identity.author(configured)
    elif record['owner']['scope']['type'] == 'plain_repository' and not bound:
        name, email = git('config', 'user.name'), git('config', 'user.email')
    else:
        raise _Refusal(REFUSED, 'the owner git identity is not configured for this repository')
    if not name or not email:
        raise _Refusal(REFUSED, 'the owner git identity is not configured')
    changed, _work = _looked(ctx, record, path)
    if ctx['probe'].unique_work(path, (), None, ctx['run']).get('operation'):
        raise _Refusal(REFUSED, 'Save does not finish a git operation in progress')
    holds = _branch_holds(ctx['commands'], path, branch)
    if holds:
        raise _Refusal(REFUSED, 'the kept branch already holds other work')
    exists = holds is not None
    if changed:
        git('switch', *([branch] if exists else ['-c', branch]))
        git('add', '-A')
        git('-c', 'user.name=' + name, '-c', 'user.email=' + email,
            'commit', '-m', 'Save work for ' + branch)
        answer['commit'] = git('rev-parse', 'HEAD')
        git('switch', '--detach')
    else:
        # No invented commit for a worktree whose unique work is already committed.
        if not exists:
            git('branch', branch, 'HEAD')
    answer['kept_branch'] = branch


def _review_scratch(ctx, identity, record, kept, answer):
    """Saved review scratch only, through the existing folder remover and its file delete.

    The parent worktree passes rules 1, 2, 3, 4 and 6 afresh for each path. This conservative look
    covers every contained path, including owner-kept children. Only the final link is unlinked;
    every parent is opened without following links. A refused folder is put back by _folder.
    """
    path = _plain(record['locator']['path'])
    removed = answer['review_scratch'] = []
    check = ctx.get('review_check')
    if check is None:
        raise _Refusal(IN_USE, 'review scratch has no ledger rules reader')

    def judged():
        result = check()
        if not isinstance(result, dict) or result.get('ok') is not True:
            raise _Refusal(IN_USE, 'a review scratch rule refused', found=result)

    def compare(relative, descriptor, name):
        judged()
        # Read by the descriptor used for unlink, so a replaced parent cannot redirect the read.
        at = '/proc/self/fd/%d/%s' % (descriptor, name)
        expected = (kept.get('snapshot') or {}).get('files', {}).get(relative)
        if not expected or _digest(at) != {key: expected.get(key) for key in ('mode', 'sha256')}:
            raise _Refusal(KEEP_FAILED, 'review scratch differs from its snapshot: ' + relative)
        return lambda: removed.append(relative)

    judged()
    try:
        _changed, work = _looked(ctx, record, path)
        if work:
            raise _Refusal(KEEP_FAILED, 'review worktree holds files outside review scratch', unsaved=work)
        code, out = _git(ctx['commands'], '-C', path, 'ls-files', '--others', '--exclude-standard',
                         '--directory', '-z')
        if code != 0:
            raise _Refusal(KEEP_FAILED, 'git could not list review scratch')
        for relative in out.split('\0')[:-1]:
            relative = relative.rstrip('/')
            if os.path.isabs(relative) or any(part in ('', '.', '..') for part in relative.split('/')):
                raise _Refusal(KEEP_FAILED, 'review scratch does not stay in the worktree')
            target = os.path.join(path, relative)
            judged()
            parent = _parent(target)
            try:
                base = os.path.basename(target)
                found = os.stat(base, dir_fd=parent, follow_symlinks=False)
                if stat.S_ISDIR(found.st_mode):
                    _folder(ctx, identity, record, target,
                            before_file=lambda child, fd, leaf: compare(relative + '/' + child, fd, leaf))
                    removed.append(relative + '/')
                elif stat.S_ISREG(found.st_mode) or stat.S_ISLNK(found.st_mode):
                    deleted = compare(relative, parent, base)
                    os.unlink(base, dir_fd=parent)
                    deleted()
                else:
                    raise _Refusal(KEEP_FAILED, 'review scratch is not a file or link: ' + relative)
            finally:
                os.close(parent)
    except (OSError, ValueError, _Stop) as error:
        raise _Refusal(KEEP_FAILED, 'review scratch could not be read: ' + _said(error))


class _Copies:
    """Where a copy of an evidence file is held, asked at the removal (design 0.4, VELDO-0347 AC4). A
    file has a copy when the SHA-256 of its content, read now, is the digest of a blob the store holds,
    or of a file in a commit that the trunk or a kept ref of the main repository reaches. Nothing
    recorded at an earlier measurement is read. A store or a commit that cannot be read is no copy.

    THE STORE holds a blob with a digest when a row of its entities has that digest and the row's
    own content, encoded again as the store encodes it, has it too.

    A COMMIT holds the file when a blob with the file's git object name is in a tree of a commit
    reached from the trunk or from a ref under refs/veldo/kept/ of the item's main repository, and
    that blob, read back from the repository, has the file's SHA-256. The trunk is the one
    `trunk(repository)` names; it is never guessed, and with none given only kept refs are read."""

    KEPT = 'refs/veldo/kept/'

    def __init__(self, ctx, record):
        self.ctx, self.record = ctx, record
        self.objects, self.counts, self.unread = None, {'store': 0, 'commit': 0}, []
        self.main = None

    def _said(self, what):
        if what not in self.unread and len(self.unread) < NAMED:
            self.unread.append(what)

    def _store(self, sha):
        ledger = self.ctx['ledger']
        try:
            rows = ledger.conn.execute('SELECT kind, version, data FROM entities WHERE digest=?',
                                       ('sha256:' + sha,)).fetchall()
            for kind, version, raw in rows:
                blob = ledger.store.canonical_bytes({'kind': kind, 'data': json.loads(raw), 'version': version})
                if hashlib.sha256(blob).hexdigest() == sha:
                    return True
        except Exception as error:  # noqa: BLE001 - a store that cannot be read is no copy
            self._said('the store could not be read: ' + _said(error))
        return False

    def _reached(self):
        """The object names of everything the trunk and the kept refs of the main repository reach,
        read once for this removal; an empty set when that cannot be read."""
        if self.objects is not None:
            return self.objects
        self.objects = frozenset()
        commands = self.ctx['commands']
        try:
            main = self.ctx['ledger']._main_of(self.record)
            if not main or os.path.realpath(main) != main or not os.path.isdir(main):
                self._said('no main repository is at its path')
                return self.objects
            refs = ['--glob=' + self.KEPT]
            trunk = self.ctx.get('trunk')
            named = trunk(main) if callable(trunk) else None
            if isinstance(named, str) and named:
                ref = named if named.startswith('refs/') else 'refs/heads/' + named
                code, out = _git(commands, '-C', main, 'rev-parse', '--verify', '--quiet', ref + '^{commit}')
                if code == 0:
                    refs.append(out.strip())
                else:
                    self._said('the trunk %s could not be read' % ref)
            code, out = _git(commands, '-C', main, 'rev-list', '--objects', '--no-object-names', *refs)
            if code != 0:
                self._said('the commits could not be read: ' + str(out)[:200])
                return self.objects
            self.main, self.objects = main, frozenset(out.split())
        except Exception as error:  # noqa: BLE001 - commits that cannot be read are no copy
            self._said('the commits could not be read: ' + _said(error))
        return self.objects

    def _commit(self, at, sha):
        reached = self._reached()
        if not reached:
            return False
        commands = self.ctx['commands']
        code, name = _git(commands, '-C', self.main, 'hash-object', '--no-filters', '--', at)
        if code != 0 or name.strip() not in reached:
            return False
        code, out = _git(commands, '-C', self.main, 'cat-file', 'blob', name.strip())
        return code == 0 and hashlib.sha256(out.encode('utf-8', 'surrogateescape')).hexdigest() == sha

    def find(self, at, sha):
        """Where a copy of the file open at `at`, whose content has the SHA-256 `sha`, is held: store,
        commit, or None."""
        for where, held in (('store', self._store), ('commit', lambda digest: self._commit(at, digest))):
            if held(sha):
                self.counts[where] += 1
                return where
        return None


def _held_file(ctx, copies, name, dir_fd, relative, answer, removed, kept):
    """One evidence file: its digest is read now, through one descriptor; it is deleted only when a
    copy with that digest is held and the file is still as it was when it was read. A link, anything
    that is no regular file, a file that cannot be read and a file with no copy stay."""
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=dir_fd)
    except OSError:
        kept.append(relative)
        return
    try:
        found = os.fstat(descriptor)
        if not stat.S_ISREG(found.st_mode):
            kept.append(relative)
            return
        digest = hashlib.sha256()
        for block in iter(lambda: os.read(descriptor, 1 << 20), b''):
            digest.update(block)
        held = copies.find('/proc/self/fd/%d' % descriptor, digest.hexdigest())
        if held is None or _signature(os.lstat(name, dir_fd=dir_fd)) != _signature(found):
            kept.append(relative)  # no copy, or written since it was read: it stays
            return
        os.unlink(name, dir_fd=dir_fd)
        removed.append(relative)
        answer['bytes'] += found.st_blocks * BLOCK
    except OSError:
        kept.append(relative)
    finally:
        os.close(descriptor)


def _held_folder(ctx, copies, name, dir_fd, device, relative, answer, removed, kept):
    try:
        descriptor = os.open(name, os.O_RDONLY | DIRECTORY, dir_fd=dir_fd)
    except OSError:
        kept.append(relative + '/')
        return
    try:
        if os.fstat(descriptor).st_dev != device:
            kept.append(relative + '/')  # another filesystem is mounted here: nothing in it is touched
            return
        with os.scandir(descriptor) as entries:
            listing = sorted((entry.name, entry.is_dir(follow_symlinks=False)) for entry in entries)
        names = set(inner for inner, _directory in listing)
        if '.git' in names or GIT_FOLDER <= names:
            kept.append(relative + '/')  # a repository is never taken apart file by file
            return
        for inner, directory in listing:
            child = os.path.join(relative, inner)
            if directory:
                _held_folder(ctx, copies, inner, descriptor, device, child, answer, removed, kept)
            else:
                _held_file(ctx, copies, inner, descriptor, child, answer, removed, kept)
    except OSError:
        kept.append(relative + '/')
    finally:
        os.close(descriptor)


def _r_remove_held(ctx, identity, record, answer):
    """The evidence remover (design 0.4 and section 5, VELDO-0347 AC4): at a ticket's or a project's
    end, remove the files of an evidence item that a copy holds, and keep the rest. The item stays.
    No folder is removed and nothing is renamed: a file with no copy is where it was."""
    answer['method'] = 'remove_files_a_copy_holds'
    root = _plain(record['locator']['path'])
    pools = _before(ctx, record, answer)
    copies, removed, kept = _Copies(ctx, record), [], []
    answer['bytes'], answer['bytes_source'] = 0, 'measured'
    parent = _parent(root)
    try:
        base = os.path.basename(root)
        try:
            found = os.lstat(base, dir_fd=parent)
        except OSError as error:
            raise _Refusal(REFUSED, 'the path could not be read: ' + _said(error))
        if stat.S_ISDIR(found.st_mode):
            if mount_point(root):
                raise _Refusal(REFUSED, 'the folder is a mount point')
            _held_folder(ctx, copies, base, parent, found.st_dev, '', answer, removed, kept)
        else:
            _held_file(ctx, copies, base, parent, base, answer, removed, kept)
    finally:
        os.close(parent)
    answer.update(removed_files=len(removed), kept_files=len(kept), removed=removed[:NAMED], kept=kept[:NAMED],
                  copies=dict(copies.counts), unread=list(copies.unread))
    _after(ctx, pools, answer)


def _r_drop_caches(ctx, identity, record, answer):
    answer['method'] = 'drop_caches'
    root = _plain(record['locator']['path'])
    pools = _before(ctx, record, answer)
    answer['bytes'], answer['bytes_source'], answer['dropped'] = 0, 'measured', []
    for relative in _declared(ctx, record, 'evidence_caches'):
        cache = os.path.normpath(os.path.join(root, relative))
        if not cache.startswith(root + '/'):
            raise _Refusal(REFUSED, 'a declared cache leads out of the evidence folder: ' + str(relative))
        if not os.path.lexists(cache):
            continue
        if os.path.realpath(os.path.dirname(cache)) != os.path.dirname(cache):
            raise _Refusal(REFUSED, 'a declared cache is reached through a link: ' + str(relative))
        answer['bytes'] += _folder(ctx, identity, record, cache)
        answer['dropped'].append(cache)
    _after(ctx, pools, answer)


# ---------------------------------------------------------------------------------------------
# The Docker removers.
# ---------------------------------------------------------------------------------------------

def _engine(ctx, locator, *argv):
    return ctx['run'](['docker', '--context', str(locator['engine'])] + list(argv))


def _inspected(ctx, locator, *argv):
    """The one record an inspect command gives, or None."""
    code, out = _engine(ctx, locator, *argv)
    if code != 0:
        return None
    try:
        records = json.loads(out)
    except ValueError:
        return None
    return records[0] if isinstance(records, list) and len(records) == 1 and isinstance(records[0], dict) else None


def _figure(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _size_container(shown):
    return _figure(shown.get('SizeRw'))


def _size_image(shown):
    return _figure(shown.get('Size'))


def _size_volume(shown):
    where = shown.get('Mountpoint')
    try:
        return measure(where) if isinstance(where, str) and where.startswith('/') else None
    except (OSError, RecursionError, _Stop):
        return None


def _size_network(shown):
    return 0


COMPOSE_PROJECT = 'com.docker.compose.project'
RUN_LABEL = 'veldo.space.run'  # the run's label (design 6.4): its value is the run's space label
# The locator fields that hold what the engine said of the object when it was made, by kind. Without
# them nothing proves that the object now under the name is the one the item recorded.
IDENTITY = {
    'container': ('id',),
    'network': ('id',),
    'image_tag': ('id',),
    'volume': ('created_at',),
}
# The labels that say whose an object is, as (locator field, label). A volume's record holds one.
OWNER_LABELS = (
    ('run_label', RUN_LABEL),
    ('compose_project', COMPOSE_PROJECT),
)


def _unproven(kind, locator):
    """Why the item's record cannot prove which object it means, or None. Asked before the engine is."""
    missing = [field for field in IDENTITY.get(kind, ('id',))
               if not (isinstance(locator.get(field), str) and locator[field])]
    if missing:
        return ('the item\'s record does not hold the identity seen when the object was made (%s): the object '
                'now under its name cannot be proved to be the one recorded' % ', '.join(missing))
    if kind == 'volume' and not any(isinstance(locator.get(field), str) and locator[field]
                                    for field, _ in OWNER_LABELS):
        return ('the item\'s record holds neither the run\'s label nor a compose project: nothing says whose '
                'the volume was when it was made')
    return None


def _recorded(locator, shown):
    """Why the object the engine shows is not the one the item recorded, or None. Every field of the
    record that names the object's identity is compared: the Id, CreatedAt, the run's label and the
    compose project label."""
    if shown is None:
        return 'the engine could not show the object'
    if 'id' in locator and shown.get('Id') != locator['id']:
        return 'the object has another Id than the item recorded'
    if 'created_at' in locator and shown.get('CreatedAt') != locator['created_at']:
        return 'the object was made at another time than the item recorded: it was made again'
    labels = shown.get('Labels') if isinstance(shown.get('Labels'), dict) else (shown.get('Config') or {}).get('Labels')
    for field, label in OWNER_LABELS:
        if field in locator and (labels or {}).get(label) != locator[field]:
            return 'the object does not carry the label %s the item recorded' % label
    return None


def _pulled_image(ledger, locator):
    """A pull can follow a build. Its durable kept report holds the image on this engine.

    Read the ledger at removal, including after adapter or service restart. An unread ledger raises
    out of remove() and nothing is removed; Signal defers the item. A built tag never takes the only
    copy of a subsequently pulled image.
    """
    for record in ledger.items().values():
        where = record.get('locator') or {}
        found = (record.get('report') or {}).get('found') or {}
        if (record.get('kind') == 'image_tag' and where.get('engine') == locator.get('engine')
                and where.get('id') == locator.get('id') and found.get('why') == 'pulled_image'
                and found.get('disposition') == 'kept'):
            return True
    return False


def _docker(method, needs, show, size, steps):
    def remover(ctx, identity, record, answer):
        answer['method'] = method
        locator = record.get('locator') or {}
        if not all(isinstance(locator.get(field), str) and locator[field] for field in ('engine',) + needs):
            raise _Refusal(REFUSED, 'the locator does not name the object: ' + ', '.join(('engine',) + needs))
        unproven = _unproven(record.get('kind'), locator)
        if unproven is not None:
            raise _Refusal(REFUSED, unproven + ': it is not removed')
        shown = _inspected(ctx, locator, *[locator[word[1:]] if word.startswith('$') else word for word in show])
        other = _recorded(locator, shown)
        if other is not None:
            raise _Refusal(REFUSED, other + ': it is not removed')
        if record.get('kind') == 'image_tag' and _pulled_image(ctx['ledger'], locator):
            raise _Refusal(REFUSED, 'the image was pulled and is kept on this engine')
        measured = size(shown)
        if measured is not None:
            answer['bytes'], answer['bytes_source'] = measured, 'measured'
        elif isinstance(record.get('size'), dict) and _figure(record['size'].get('bytes')) is not None:
            answer['bytes'], answer['bytes_source'] = record['size']['bytes'], 'last_measurement'
        pools = _before(ctx, record, answer)
        for step in steps:
            argv = [locator[word[1:]] if word.startswith('$') else word for word in step]
            code, out = _engine(ctx, locator, *argv)
            if code != 0:
                raise _Refusal(REFUSED, 'the engine refused %s: %s' % (' '.join(step[:2]), str(out)[:300]),
                               code=code)
        _after(ctx, pools, answer)
    return remover


_r_container = _docker('engine_stop_then_remove', ('id',), ('container', 'inspect', '--size', '$id'), _size_container,
                       (('container', 'stop', '$id'), ('container', 'rm', '$id')))
# --no-prune: the engine removes the tag and nothing else. Without it a classic image store also
# deletes the image's untagged parents, which Veldo did not build.
_r_image_tag = _docker('engine_image_remove', ('name',), ('image', 'inspect', '$name'), _size_image,
                       (('image', 'rm', '--no-prune', '$name'),))
_r_volume = _docker('engine_volume_remove', ('name',), ('volume', 'inspect', '$name'), _size_volume,
                    (('volume', 'rm', '$name'),))
_r_network = _docker('engine_network_remove', ('id',), ('network', 'inspect', '$id'), _size_network,
                     (('network', 'rm', '$id'),))


# ---------------------------------------------------------------------------------------------
# The one entry.
# ---------------------------------------------------------------------------------------------

REMOVERS = {
    ('remove', 'scratch'): _r_folder,
    ('remove', 'build_output'): _r_folder,
    ('remove', 'review_run_scratch'): _r_folder,
    ('remove', 'review_run_build_output'): _r_folder,
    ('remove', 'worktree'): _r_worktree,
    ('remove', 'agent_repository'): _r_agent_repository,
    ('remove', 'volume'): _r_volume,
    ('remove', 'network'): _r_network,
    ('remove', 'container'): _r_container,
    ('stop_then_remove', 'container'): _r_container,
    ('remove_tag', 'image_tag'): _r_image_tag,
    ('drop_caches', 'evidence'): _r_drop_caches,
    ('remove_held', 'evidence'): _r_remove_held,
}


def remove(ledger, probe, identity, record, action='remove', free=None, keep=None, run=None, proc=None,
           review_check=None, trunk=None):
    """Carry out one removal of the item `identity`, whose ledger record is `record`, by the remover
    of `action` and the item's kind, and return what it measured.

    `probe` is the control_space_probe module. `free(pool record)` returns the free bytes of one pool
    at the moment of the call; without it nothing is removed. `keep(identity, record)` is the keep
    step of a worktree and an agent repository; without it neither is removed, and it answers
    {ok: True, tips: what `tips` read in the item when its commits were recorded, snapshot: the files
    it saved, when it saved any}. `run` and `proc` are the probes' own parameters, the client runner
    and the process table; `run` also runs the engine's client. The remover's own git commands, the
    worktree move and remove among them, are run through the Git boundary and not through `run`.

    Returns {ok: True, ...} or the refusal {ok: False, reason, deferral, said, ...}, each with item,
    action, kind, method, bytes, bytes_source, pool, pool_free_before, pool_free_after, freed, host and
    commands. `trunk(repository)` names the declared trunk of a main repository, for the evidence
    remover and nothing else; with none, only the store and the kept refs hold a copy."""
    commands, given = [], run or _run

    def logged(argv, cwd=None):
        commands.append([str(word) for word in argv])
        return given(argv, cwd)

    ctx = {'ledger': ledger, 'probe': probe, 'free': free, 'keep': keep, 'run': logged, 'proc': proc, 'action': action,
           'commands': commands, 'review_check': review_check, 'trunk': trunk}
    answer = {'item': identity, 'action': action, 'kind': record.get('kind'), 'method': None, 'bytes': None,
              'bytes_source': None, 'pool': record.get('pool'), 'pool_free_before': None,
              'pool_free_after': None, 'freed': None, 'host': None, 'commands': commands}
    try:
        kind = record.get('kind')
        if action == 'remove_held':
            # Evidence files are deleted one by one and nothing is renamed first, so the kind that
            # picks this remover is the Ledger's own word for the item, never the record handed in.
            kind = (ledger.item(identity) or {}).get('kind')
        remover = (_r_disposition if action in ('save', 'discard') and kind == 'worktree'
                   else REMOVERS.get((action, kind)))
        if remover is None:
            raise _Refusal(REFUSED, 'no remover for the action %s on the kind %s' % (action, kind))
        if free is None:
            raise _Refusal(REFUSED, 'no reader of free space was given: the removal could not be measured')
        remover(ctx, identity, record, answer)
    except _Refusal as refusal:
        return dict(answer, ok=False, reason='space_deferred:' + refusal.deferral, deferral=refusal.deferral,
                    said=refusal.said, **refusal.more)
    return dict(answer, ok=True)


def tool(ledger, probe, action='remove', free=None, keep=None, run=None, proc=None):
    """The remover in the form rule 7 calls: tool(identity, record)."""
    def call(identity, record):
        return remove(ledger, probe, identity, record, action=action, free=free, keep=keep, run=run, proc=proc)
    return call


def remove_ref(repository, ref, ledger=None, identity=None, standalone=None, main=None):
    """Release an internal pin only after its owner's recorded removal and verified keep.

    The authority is an ended ledger item or a standalone keep result.
    A missing or unverifiable keep refuses and leaves the ref.
    The main repository must still reach its commit through a kept ref or branch.
    Standalone scaffold cleanup keeps an unheld commit there before releasing its ref. Branches,
    tags, stashes and kept refs are never accepted by this entry.
    """
    commands = []
    answer = {'item': identity, 'ref': ref, 'commands': commands, 'ok': False,
              'deferral': 'keep_failed'}
    try:
        repository = _plain(str(repository))
        if not isinstance(ref, str) or not ref.startswith(
                ('refs/veldo/pins/', 'refs/veldo/batch/', 'refs/veldo/adoption/')):
            raise ValueError('not an internal temporary ref')
        code, out = _git(commands, '-c', 'core.hooksPath=' + os.devnull, '-C', repository, 'check-ref-format', ref)
        if code != 0:
            raise ValueError('invalid ref name')
        keeper = _sibling('control_space_keep')
        if ledger is not None:
            record = ledger.item(identity) if identity else None
            if (not record or not record.get('owner') or record.get('owner_keep')
                    or record.get('state') != 'removed' or not (record.get('due') or {}).get('event')):
                return dict(answer, deferral='not_in_ledger', said='no ended owner item authorizes this ref removal')
            if keeper.verify(ledger, identity).get('ok') is not True:
                raise ValueError('the keep record could not be verified')
            main = _plain(ledger.main_repository(identity))
        else:
            if not standalone or standalone.get('state') not in SPACE_SAFE:
                raise ValueError('no standalone keep result authorizes this ref removal')
            main = _plain(str(main or standalone.get('repository')))
            for kept_ref, commit in (standalone.get('refs') or {}).items():
                code, out = _git(commands, '-c', 'core.hooksPath=' + os.devnull, '-C', main, 'show-ref', '--verify', '--hash', kept_ref)
                if code != 0 or out.strip() != commit:
                    raise ValueError('the standalone keep could not be verified')
        code, out = _git(commands, '-c', 'core.hooksPath=' + os.devnull, '-C', repository, 'symbolic-ref', '-q', ref)
        if code != 1:
            raise ValueError('a symbolic or unreadable ref is not removable')
        code, out = _git(commands, '-c', 'core.hooksPath=' + os.devnull, '-C', repository, 'show-ref', '--verify', '--hash', ref)
        if code != 0 or not out.strip():
            raise ValueError('the temporary ref could not be read')
        old = out.strip()
        code, out = _git(commands, '-c', 'core.hooksPath=' + os.devnull, '-C', main, 'for-each-ref', '--format=%(objectname)',
                         'refs/heads/', 'refs/veldo/kept/')
        if code != 0:
            raise ValueError('the main repository holding refs could not be read')
        code, beyond = _git(commands, '-c', 'core.hooksPath=' + os.devnull, '-C', main, 'rev-list', '--stdin',
                            feed=('\n'.join([old, '--not', *out.split()]) + '\n').encode())
        if code != 0:
            raise ValueError('the temporary ref reachability could not be read')
        if beyond.strip() and ledger is None and (standalone or {}).get('keep_unheld') is True:
            if keeper._common(commands, repository) != keeper._common(commands, main):
                raise ValueError('standalone ref keeping requires its main repository')
            kept = keeper.keep_ref(main, ref, old)
            commands.extend(kept.get('commands') or ())
            if kept.get('ok') is not True or not kept.get('refs'):
                raise ValueError('the temporary ref keep failed: ' + str(kept.get('said')))
            for name, commit in kept['refs'].items():
                code, value = _git(commands, '-C', main, 'show-ref', '--verify', '--hash', name)
                if code != 0 or value.strip() != commit:
                    raise ValueError('the temporary ref keep could not be read back')
            code, beyond = _git(commands, '-C', main, 'rev-list', '--stdin',
                                feed=('\n'.join([old, '--not', *kept['refs'].values()]) + '\n').encode())
            answer['kept'] = kept['refs']
        if code != 0 or beyond.strip():
            raise ValueError('the temporary ref has work no main repository branch or kept ref reaches')
        # Compare the value under git's ref lock. Never follow a symbolic ref and never force.
        code, out = _git(commands, '-c', 'core.hooksPath=' + os.devnull, '-C', repository, 'update-ref', '--no-deref', '-d', ref, old)
        if code != 0:
            raise ValueError('git refused the ref removal: ' + str(out)[:200])
        return dict(answer, ok=True, deferral=None, commit=old, repository=main)
    except Exception as error:  # noqa: BLE001 - no unread fact permits a delete
        return dict(answer, said=_said(error))


SPACE_SAFE = ('gone', 'clear', 'kept')


def remove_standalone(path, kind, main=None, event='run_finished', ticket=None,
                      candidate=None, projected=(), remote=None, filesystem=None, worktree=None):
    """No ledger: make the accepted standalone look and keep step here, then remove.

    A caller cannot supply an earlier safe answer. Rebuildable landing candidates
    use the accepted candidate look; every other repository needs its kept refs.
    Folder deletion uses the descriptor-based folder remover; worktrees use git's
    non-forced remover. The answer retains the look's state and adds removed.
    """
    look = _sibling('control_space_standalone')
    path = str(path)
    answer = None
    if candidate is not None:
        answer = look.candidate(path, str(main) if main is not None else None,
                                candidate, projected, remote)
    if answer is None or answer['state'] != look.REBUILDABLE:
        answer = look.standalone(path, kind, main=None if main is None else str(main),
                                 event=event, ticket=ticket)
    if answer['state'] not in (*SPACE_SAFE, look.REBUILDABLE):
        return answer
    if answer['state'] == 'gone':
        return dict(answer, removed=True)
    try:
        path = _plain(path)
        if kind == 'worktree':
            if answer['state'] != 'kept':
                raise ValueError('the worktree has no verified keep')
            if worktree is None:
                code, out = _worktree_remove({'commands': []}, str(main), path)
                if code != 0:
                    raise ValueError(out)
            else:
                worktree(['remove', path], cwd=str(main))
        else:
            if mount_point(path):
                raise ValueError('the folder is a mount point')
            parent = _parent(path)
            try:
                base = os.path.basename(path)
                device = os.lstat(base, dir_fd=parent).st_dev
                measure(base, device, open_up=True, own=kind == 'agent_repository', dir_fd=parent)
                if filesystem is None:
                    _delete(base, parent, device)
                else:
                    filesystem.rmtree(base, dir_fd=parent)
            finally:
                os.close(parent)
        return dict(answer, removed=True)
    except Exception as error:
        return dict(answer, state=None, deferral='remove_refused', said=_said(error), removed=False)
