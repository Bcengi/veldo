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

Any other pair has no remover and is refused. A branch is marked, never removed, and that is a ledger
write. Review scratch is saved by the keep step, compared file by file and removed before the
non-forced worktree remove (VELDO-0336). Discard and copied evidence removal are VELDO-0318 and 0347.

NO REMOVER HERE PASSES A FORCE OPTION, AND NONE RUNS A PRUNE COMMAND. Each names the one thing it
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


def _walk(name, dir_fd, device, seen, open_up, own=None, depth=0):
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
        if own is not None and ('.git' in names or GIT_FOLDER <= names):
            # The item's own repository is its top, and the git folder right beneath its top.
            if not (own and (depth == 0 or (depth == 1 and name == '.git'))):
                raise _Stop('a git repository is in the folder, at %s' % name)
        for entry in listing:
            if entry.is_dir(follow_symlinks=False):
                total += _walk(entry.name, descriptor, device, seen, open_up, own, depth + 1)
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


def measure(path, device=None, open_up=False, own=None, dir_fd=None):
    """The bytes the folder `path` takes on disk: every file and directory in it, a file with several
    names counted once, no link followed. With `open_up`, directories the owner cannot enter are opened
    up on the way. `own` says what the walk does with a git repository: None, nothing; False, any
    folder that is one or holds one stops it; True, the same but for the folder's own, at its top.
    `path` is a name inside `dir_fd` when one is given. Raises OSError for what cannot be read and
    _Stop for a filesystem mounted inside and for a repository."""
    device = os.lstat(path, dir_fd=dir_fd).st_dev if device is None else device
    return _walk(path, dir_fd, device, set(), open_up, own)


def _delete(name, dir_fd, device, before_file=None, relative=''):
    descriptor = os.open(name, os.O_RDONLY | DIRECTORY, dir_fd=dir_fd)
    try:
        if os.fstat(descriptor).st_dev != device:
            raise _Stop('another filesystem is mounted inside the folder, at %s' % name)
        with os.scandir(descriptor) as entries:
            listing = [(entry.name, entry.is_dir(follow_symlinks=False)) for entry in entries]
        for inner, directory in sorted(listing):
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


def _folder(ctx, identity, record, path, own=False, look=None, before_file=None):
    """Rename, second probe, last look, delete. Returns the bytes measured just before the delete.
    `own` is measure's: whether the folder may be a repository of its own. `look(marked name)`, when
    given, is the last look at the folder under its marked name; its refusal puts the folder back."""
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
                if look is not None:
                    look(name)
                size = measure(tail, found.st_dev, open_up=True, own=own, dir_fd=parent)
                if before_file is None:
                    _delete(tail, parent, found.st_dev)
                else:
                    _delete(tail, parent, found.st_dev, before_file)
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
    """The work tree at `where` as git reads it now, every ignored path included: (changed, work).
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
                continue  # build output: a build makes it again
            top, inside = os.path.join(where, folder.rstrip('/')), []
            for at, _, files in os.walk(top, onerror=_raise):
                inside.extend(os.path.relpath(os.path.join(at, name), where) for name in files)
            work.extend(inside)  # an empty folder holds no work
    return changed, sorted(set(work))


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


def _r_folder(ctx, identity, record, answer):
    answer['method'] = 'rename_probe_delete'
    pools = _before(ctx, record, answer)
    answer['bytes'], answer['bytes_source'] = _folder(ctx, identity, record, record['locator']['path']), 'measured'
    _after(ctx, pools, answer)


def _r_agent_repository(ctx, identity, record, answer):
    answer['method'] = 'keep_then_rename_probe_delete'
    _plain(record['locator']['path'])
    kept = _kept(ctx, identity, record)
    pools = _before(ctx, record, answer)
    answer['bytes'], answer['bytes_source'] = _folder(
        ctx, identity, record, record['locator']['path'], own=True,
        look=lambda name: _last_look(ctx, record, kept, name)), 'measured'
    _after(ctx, pools, answer)


def _worktree_remove(ctx, repository, path):
    """git's own worktree remove, with no force option: (exit code, output)."""
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
        _last_look(ctx, record, kept, name)
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
_r_image_tag = _docker('engine_image_remove', ('name',), ('image', 'inspect', '$name'), _size_image,
                       (('image', 'rm', '$name'),))
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
    ('remove', 'worktree'): _r_worktree,
    ('remove', 'agent_repository'): _r_agent_repository,
    ('remove', 'volume'): _r_volume,
    ('remove', 'network'): _r_network,
    ('remove', 'container'): _r_container,
    ('stop_then_remove', 'container'): _r_container,
    ('remove_tag', 'image_tag'): _r_image_tag,
    ('drop_caches', 'evidence'): _r_drop_caches,
}


def remove(ledger, probe, identity, record, action='remove', free=None, keep=None, run=None, proc=None,
           review_check=None):
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
    commands."""
    commands, given = [], run or _run

    def logged(argv, cwd=None):
        commands.append([str(word) for word in argv])
        return given(argv, cwd)

    ctx = {'ledger': ledger, 'probe': probe, 'free': free, 'keep': keep, 'run': logged, 'proc': proc,
           'commands': commands, 'review_check': review_check}
    answer = {'item': identity, 'action': action, 'kind': record.get('kind'), 'method': None, 'bytes': None,
              'bytes_source': None, 'pool': record.get('pool'), 'pool_free_before': None,
              'pool_free_after': None, 'freed': None, 'host': None, 'commands': commands}
    try:
        remover = REMOVERS.get((action, record.get('kind')))
        if remover is None:
            raise _Refusal(REFUSED, 'no remover for the action %s on the kind %s' % (action, record.get('kind')))
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
