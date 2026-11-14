#!/usr/bin/env python3
"""The removers: one remover per removal action, each using the owning tool's own remove and returning
what it measured (design section 6.5, VELDO-0300).

WHAT IS HERE. `remove` carries out one removal of one item and returns its figures. `tool` gives the
same thing in the form the safety rules call as rule 7 (control_space_signal.rules, tool(identity,
record)). A remover is called only after the other rules of the removal have passed. It writes nothing
to the ledger: the outcome is the caller's (VELDO-0301).

THE REMOVERS, by the table's action and the item's kind (REMOVERS):

  remove            scratch, build_output   the folder remover
  remove            worktree                the keep step, then git's worktree remove, never forced
  remove            agent_repository        the keep step, then the folder remover
  remove            volume                  the engine's volume remove
  remove            network                 the engine's network remove
  remove            container               the engine's stop, then its container remove
  stop_then_remove  container               the same
  remove_tag        image_tag               the engine's image remove, on the tag
  drop_caches       evidence                the folder remover on each sub-folder the project declares as
                                            a cache, and on nothing else

Any other pair has no remover and is refused. A branch is marked, never removed, and that is a ledger
write. The discard remover (the one forced removal), the review scratch remover and the removal of
evidence files a copy holds are not here: they save first, and they are VELDO-0318, 0336 and 0347.

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

It refuses by itself, before the rename, when the path is not a folder (a link is not one), when it
is a mount point, when it is not on the item's pool, and when something is already at the marked name.
It stops, and puts back what is there, when another filesystem is mounted inside the folder or a
delete fails. When the folder cannot be put back (something has appeared at its path), it stays under
the marked name, the answer names it in left_at, and nothing touches what is at the path. The marked
name holds the item's id so that reconcile finds a folder left under it.

THE KEEP STEP IS GIVEN, AND WITHOUT IT NOTHING THAT HOLDS COMMITS IS REMOVED (design section 0.2). A
worktree and an agent repository are removed only after `keep(identity, record)` has answered
{ok: True}: the keeper has recorded every commit on kept refs in the main repository, read them back
and had the keep record written. With no keeper, or any other answer, the item is deferred as
keep_failed and nothing is touched. The keeper itself is VELDO-0345. This module only refuses to run
without it.

THE WORKTREE REMOVER runs git's worktree remove in the worktree's repository, with no force option. git
refuses a worktree with a modified tracked file, an untracked file, a lock or a submodule, and that
refusal is the deferral remove_refused with the worktree untouched. git's non-forced remove does delete
ignored files without a word (measured in this ticket's proof); what an ignored file is worth is
rule 5's to say before this remover is called.

THE DOCKER REMOVERS name one object to the engine, on the item's engine context: a container by its
id, an image by its tag, a volume by its name, a network by its id. The engine's refusal (a container
uses the image or the volume, an endpoint is attached) is remove_refused. A container that does not
stop is not removed.

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
second probe), keep_failed (the keep step).

Standard library only. The ledger is the control_space.Ledger and the probe the control_space_probe
module the caller passes in.
"""
import json
import os
import stat
import subprocess

SCHEMA = 'veldo.control_space_remove/v1'

MARK = '.veldo-removing.'  # between a folder's own name and its item's id, in its marked name
SECONDS = 3600  # the longest one command of a tool may take
REFUSED, IN_USE, KEEP_FAILED = 'remove_refused', 'in_use', 'keep_failed'
BLOCK = 512  # the unit of st_blocks


class _Refusal(Exception):
    def __init__(self, deferral, said, **more):
        Exception.__init__(self, said)
        self.deferral, self.said, self.more = deferral, said, more


class _Stop(Exception):
    """A delete or a measurement that may not go on."""


def _run(argv, cwd=None):
    """Run a client and return (exit code, output). A client that is missing or does not end in time
    gives (None, what happened)."""
    environment = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    environment.update(GIT_TERMINAL_PROMPT='0', LC_ALL='C')
    try:
        done = subprocess.run(argv, cwd=cwd, env=environment, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=SECONDS)
    except (OSError, subprocess.SubprocessError) as error:
        return None, type(error).__name__ + ': ' + str(error)[:200]
    if done.returncode:
        return done.returncode, done.stderr.decode('utf-8', 'replace').strip()[-300:]
    return 0, done.stdout.decode('utf-8', 'surrogateescape')


def _said(error):
    return type(error).__name__ + ': ' + str(error)[:300]


def marked(path, identity):
    """The marked name of the folder `path` of the item `identity`: beside it, with the item's id."""
    path = path.rstrip('/')
    tail = ''.join(c if c.isalnum() or c in '-_' else '-' for c in str(identity).rsplit(':', 1)[-1])
    return os.path.join(os.path.dirname(path), os.path.basename(path) + MARK + tail)


def mount_point(path):
    """Whether a filesystem is mounted at the folder `path`."""
    return os.path.ismount(path)


# ---------------------------------------------------------------------------------------------
# Measuring and deleting a folder, through descriptors and without following a link.
# ---------------------------------------------------------------------------------------------

DIRECTORY = os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


def _open_up(name, dir_fd=None):
    """Give the owner every permission on a directory, through a descriptor of the directory itself."""
    inner = os.open(name, os.O_PATH | DIRECTORY, dir_fd=dir_fd)
    try:
        mode = stat.S_IMODE(os.fstat(inner).st_mode)
        if mode & 0o700 != 0o700:
            os.chmod('/proc/self/fd/%d' % inner, mode | 0o700)
    finally:
        os.close(inner)


def _walk(name, dir_fd, device, seen, open_up):
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
        for entry in listing:
            if entry.is_dir(follow_symlinks=False):
                total += _walk(entry.name, descriptor, device, seen, open_up)
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


def measure(path, device=None, open_up=False):
    """The bytes the folder `path` takes on disk: every file and directory in it, a file with several
    names counted once, no link followed. With `open_up`, directories the owner cannot enter are opened
    up on the way. Raises OSError for what cannot be read and _Stop for a filesystem mounted inside."""
    device = os.lstat(path).st_dev if device is None else device
    return _walk(path, None, device, set(), open_up)


def _delete(name, dir_fd, device):
    descriptor = os.open(name, os.O_RDONLY | DIRECTORY, dir_fd=dir_fd)
    try:
        if os.fstat(descriptor).st_dev != device:
            raise _Stop('another filesystem is mounted inside the folder, at %s' % name)
        with os.scandir(descriptor) as entries:
            listing = [(entry.name, entry.is_dir(follow_symlinks=False)) for entry in entries]
        for inner, directory in listing:
            if directory:
                _delete(inner, descriptor, device)
            else:
                os.unlink(inner, dir_fd=descriptor)
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


def _put_back(name, path):
    """Rename what is left under the marked name back to its path. None, or why it could not be."""
    if not os.path.lexists(name):
        return None
    try:
        if os.path.lexists(path):
            raise FileExistsError('something is at the path now: ' + path)
        os.rename(name, path)
    except OSError as error:
        return _said(error)
    return None


def _folder(ctx, identity, record, path):
    """Rename, second probe, delete. Returns the bytes measured just before the delete."""
    ledger = ctx['ledger']
    path = path.rstrip('/')
    try:
        found = os.lstat(path)
    except OSError as error:
        raise _Refusal(REFUSED, 'the path could not be read: ' + _said(error))
    if not stat.S_ISDIR(found.st_mode):
        raise _Refusal(REFUSED, 'the path is not a folder')
    if mount_point(path):
        raise _Refusal(REFUSED, 'the folder is a mount point')
    pool = ledger.pool(record.get('pool'))
    if pool is None or pool.get('type') != 'filesystem' or ledger.device(path) != pool.get('device'):
        raise _Refusal(REFUSED, 'the folder is not on the item\'s pool')
    name = marked(path, identity)
    if os.path.lexists(name):
        raise _Refusal(REFUSED, 'something is already at the marked name', marked=name)
    try:
        os.rename(path, name)
    except OSError as error:
        raise _Refusal(REFUSED, 'the folder could not be renamed: ' + _said(error))
    try:
        use = _second_probe(ctx, name)
        if use is None:
            size = measure(name, found.st_dev, open_up=True)
            _delete(name, None, found.st_dev)
            return size
        refusal = _Refusal(IN_USE, 'the folder is in use under its marked name', found=use)
    except (OSError, RecursionError, _Stop) as error:
        refusal = _Refusal(REFUSED, 'the delete stopped: ' + _said(error))
    except BaseException:
        _put_back(name, path)
        raise
    stuck = _put_back(name, path)
    if stuck is not None:
        refusal.more.update(left_at=name, not_put_back=stuck)
    raise refusal


def _kept(ctx, identity, record):
    """The keep step, given. Anything but {ok: True} is keep_failed and nothing is touched."""
    if ctx['keep'] is None:
        raise _Refusal(KEEP_FAILED, 'no keep step was given: the commits of this item are recorded nowhere')
    try:
        said = ctx['keep'](identity, record)
    except Exception as error:  # noqa: BLE001 - a keeper that fails has kept nothing
        raise _Refusal(KEEP_FAILED, 'the keep step failed: ' + _said(error))
    if not isinstance(said, dict) or said.get('ok') is not True:
        raise _Refusal(KEEP_FAILED, 'the keep step did not keep the item', keep=said)


def _r_folder(ctx, identity, record, answer):
    answer['method'] = 'rename_probe_delete'
    pools = _before(ctx, record, answer)
    answer['bytes'], answer['bytes_source'] = _folder(ctx, identity, record, record['locator']['path']), 'measured'
    _after(ctx, pools, answer)


def _r_agent_repository(ctx, identity, record, answer):
    answer['method'] = 'keep_then_rename_probe_delete'
    _kept(ctx, identity, record)
    pools = _before(ctx, record, answer)
    answer['bytes'], answer['bytes_source'] = _folder(ctx, identity, record, record['locator']['path']), 'measured'
    _after(ctx, pools, answer)


def _r_worktree(ctx, identity, record, answer):
    answer['method'] = 'keep_then_git_worktree_remove'
    path = record['locator']['path']
    _kept(ctx, identity, record)
    repository = ctx['probe'].repository(path, ctx['run'])
    if repository is None:
        raise _Refusal(REFUSED, 'git reads no repository at the worktree')
    try:
        answer['bytes'], answer['bytes_source'] = measure(path), 'measured'
    except (OSError, RecursionError, _Stop) as error:
        raise _Refusal(REFUSED, 'the worktree could not be measured: ' + _said(error))
    pools = _before(ctx, record, answer)
    code, out = ctx['run'](['git', '-C', repository, 'worktree', 'remove', path])
    if code != 0:
        raise _Refusal(REFUSED, 'git refused the remove: ' + str(out)[:300], code=code)
    if os.path.lexists(path):
        raise _Refusal(REFUSED, 'git said it removed the worktree and the folder is still there')
    _after(ctx, pools, answer)


def _r_drop_caches(ctx, identity, record, answer):
    answer['method'] = 'drop_caches'
    scope = (record.get('owner') or {}).get('scope') or {}
    declared = [project.get('evidence_caches') or [] for project in ctx['ledger'].projects
                if scope.get('type') == 'project' and project.get('project') == scope.get('id')]
    root = record['locator']['path'].rstrip('/')
    pools = _before(ctx, record, answer)
    answer['bytes'], answer['bytes_source'], answer['dropped'] = 0, 'measured', []
    for relative in (declared[0] if declared else []):
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


def _size_container(ctx, locator):
    return _figure((_inspected(ctx, locator, 'container', 'inspect', '--size', locator['id']) or {}).get('SizeRw'))


def _size_image(ctx, locator):
    return _figure((_inspected(ctx, locator, 'image', 'inspect', locator['name']) or {}).get('Size'))


def _size_volume(ctx, locator):
    where = (_inspected(ctx, locator, 'volume', 'inspect', locator['name']) or {}).get('Mountpoint')
    try:
        return measure(where) if isinstance(where, str) and where.startswith('/') else None
    except (OSError, RecursionError, _Stop):
        return None


def _size_network(ctx, locator):
    return 0


def _docker(method, needs, size, steps):
    def remover(ctx, identity, record, answer):
        answer['method'] = method
        locator = record.get('locator') or {}
        if not all(isinstance(locator.get(field), str) and locator[field] for field in ('engine',) + needs):
            raise _Refusal(REFUSED, 'the locator does not name the object: ' + ', '.join(('engine',) + needs))
        measured = size(ctx, locator)
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


_r_container = _docker('engine_stop_then_remove', ('id',), _size_container,
                       (('container', 'stop', '$id'), ('container', 'rm', '$id')))
_r_image_tag = _docker('engine_image_remove', ('name',), _size_image, (('image', 'rm', '$name'),))
_r_volume = _docker('engine_volume_remove', ('name',), _size_volume, (('volume', 'rm', '$name'),))
_r_network = _docker('engine_network_remove', ('id',), _size_network, (('network', 'rm', '$id'),))


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


def remove(ledger, probe, identity, record, action='remove', free=None, keep=None, run=None, proc=None):
    """Carry out one removal of the item `identity`, whose ledger record is `record`, by the remover
    of `action` and the item's kind, and return what it measured.

    `probe` is the control_space_probe module. `free(pool record)` returns the free bytes of one pool
    at the moment of the call; without it nothing is removed. `keep(identity, record)` is the keep
    step of a worktree and an agent repository; without it neither is removed. `run` and `proc` are the
    probes' own parameters, the client runner and the process table; `run` also runs the tools.

    Returns {ok: True, ...} or the refusal {ok: False, reason, deferral, said, ...}, each with item,
    action, kind, method, bytes, bytes_source, pool, pool_free_before, pool_free_after, freed, host and
    commands."""
    commands, given = [], run or _run

    def logged(argv, cwd=None):
        commands.append([str(word) for word in argv])
        return given(argv, cwd)

    ctx = {'ledger': ledger, 'probe': probe, 'free': free, 'keep': keep, 'run': logged, 'proc': proc}
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
