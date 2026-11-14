#!/usr/bin/env python3
"""The keeper: the keep step every remover of a worktree or a private repository runs first (design
sections 0.2 and 0.3, VELDO-0345). No work is ever lost: before anything is removed, every commit the
item reaches is on a kept ref in its main repository, and what was never committed is saved as plain
files outside git. When either cannot be done and read back, the answer is keep_failed and nothing is
removed.

WHAT IS HERE. `keep` carries out the keep step for one item and answers. `keeper` gives the same thing
in the form the removers are given, keep(identity, record) (control_space_remove.remove). `verify`
reads an item's keep record against the disk: what reconcile asks before it completes a removing item.
`attempts` counts every folder an item has in the snapshot store, and `listing` reads what a snapshot
of a work tree would hold.

THE ANSWER. {ok: True, tips, repository, refs, snapshot} or the refusal {ok: False, reason:
space_deferred:keep_failed, deferral: keep_failed, said, ref, git}. tips is what
control_space_remove.tips read in the item when its commits were recorded: the keeper calls that one
function and no other, because the remover reads the same thing again under the marked name and
refuses on any difference. snapshot, when the step saved files, is {files: {path: {mode, sha256}},
path, number}. ref and git, in a refusal, are the kept ref and git's own words.

THE MAIN REPOSITORY is the one the ledger gives for the item (Ledger.main_repository): the repository
the declarations name for the item's scope. It is never a private repository, and for an agent's
worktree it is the shared repository, never the agent repository the worktree is linked to, which is
removed later. An item the declarations name no repository for cannot be kept and stays. So does an
item whose main repository is not at its path any more: the step has nowhere to write.

THE KEPT REFS, refs/veldo/kept/<ticket>/<item>/<attempt>/<what> (the ledger's kept_prefix, then the
number of the attempt that wrote the ref, from 1):

  head         the checked-out commit; for a private repository its HEAD
  ref/<name>   a worktree's own refs (a bisect, a rewritten ref); every ref of a private repository,
               branches, tags and remote-tracking refs alike, by its full name
  op/<name>    each commit an operation in progress names
  stash/<n>    every stash entry of a private repository, not the newest alone
  log/<n>      each commit only a log names: a commit a reset left behind is named by nothing else,
               and git's worktree remove takes the log

A log commit that one of the item's own other tips reaches gets no ref of its own: the ref at that tip
keeps it. Nothing else is tested. A ref is written whether or not some other ref of the repository
holds the commit.

HOW THEY ARE WRITTEN. When the item's objects are not in the main repository's own store (a private
repository, an agent's worktree), they are first fetched from the item's repository by hash, with
uploadpack.allowAnySHA1InWant set for that one call, following no tag, recursing into no submodule and
checking every object received. Each ref is then created with git's update-ref, which names the event
in the ref's own log, and is never moved. Every ref is read back from the main repository and every
object is read there, and only then is the keep record written by the Ledger, which reads the refs
again itself and adds them to the record: no ref is ever taken off it.

EVERY ATTEMPT WRITES ITS OWN REFS (the design's append-only rule; the lead's decision of 2026-11-14).
An attempt reads the refs the item already has. When the newest attempt holds every ref this one
would write, each at the same commit, nothing is written and those refs are the answer: a second
attempt after a crash finds the refs it wrote and passes, and an item that is deferred and tried
again with nothing changed gets no new ref. In every other case (the head moved, a ref was added, a
reset left one more commit behind, the earlier attempt was killed half way) the whole set is written
under the next number, and no ref of an earlier attempt is touched. So a worktree whose head moved
after an attempt that was then deferred is kept again at its new head and can be removed, and the
head it had before is still on its own ref. A number of a log or a stash ref counts within its
attempt. A name of the attempt's own that turns up at another commit between the read and the
write is a failure, and is not moved.

THE SNAPSHOT (design 0.3), written when the keeper is made with snapshot=True, by the removals that
save uncommitted state first. Plain files in the snapshot store, <state root>/space-saved/<ticket>/
<item>/<n>/, outside every repository; the store and every folder in it have mode 0700:

  manifest.json   the item, its ticket, its main repository, the path it had, the checked-out commit,
                  the event; one row per saved path with what it is (tracked_edit, untracked,
                  ignored_work), its mode, its size and its SHA-256, and its staged state; the tracked
                  paths deleted in the work tree and those deleted in the index
  work/           each tracked file that differs from the checked-out commit, each untracked file and
                  each ignored file that is work, at its own path, byte for byte; a link as a link
  staged/         for each path whose staged content differs from the working file, the staged content

It is written without touching what it saves. The lists are read with git's status and ls-files and
the staged contents with git's cat-file; none of them adds an object, and git's stash command is never
run. The files are copied by this module. The attempt is written under a temporary name, <n>.partial:
a write that comes back short stops it, each file is read back and compared with the manifest and with
the item's own file, every file and folder is synced, the folder is renamed to <n>, and the item's
folder is synced. Any failure is keep_failed, and what the attempt wrote stays under its temporary
name: nothing in the store is ever deleted, replaced or written a second time by this module. n is the
next number no folder of the item has, whole or temporary.

A RETRY first looks at the newest attempt the keep record lists. When that attempt's manifest has the
recorded digest, its files are as the manifest says and the item equals it path by path, in mode and
in digest, the attempt is used and nothing is written. In every other case the next number is written
and the Ledger adds it to the record; no attempt is ever taken off the record.

Standard library only. The ledger is the control_space.Ledger the caller passes in; git is run through
the one Git boundary, by the removers' own runner.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat


def _sibling(name):
    spec = importlib.util.spec_from_file_location('veldo_space_keep_' + name,
                                                  Path(__file__).resolve().with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_remove = _sibling('control_space_remove')
_space = _sibling('control_space')

SCHEMA = 'veldo.control_space_keep/v1'
SNAPSHOT_SCHEMA = 'veldo.space_snapshot/v1'
KEEP_FAILED = 'keep_failed'
KEEP_KINDS = ('worktree', 'agent_repository')
MANIFEST = 'manifest.json'
PARTIAL = '.partial'
ATTEMPT = re.compile(r'([1-9][0-9]*)(\.partial)?\Z')
BLOCK = 1 << 20
FOLDER_MODE, FILE_MODE = 0o700, 0o600
STAGED = 'MARCT'  # the index states of git's status that hold staged content
UNMERGED = ('DD', 'AU', 'UD', 'UA', 'DU', 'AA', 'UU')
# Points a test stops the step at, as a process that is killed there would: each is called when set.
SEAM = {'after_refs': None, 'in_snapshot': None, 'after_snapshot': None, 'after_record': None}


class _Failed(Exception):
    def __init__(self, said, **more):
        Exception.__init__(self, said)
        self.said, self.more = said, more


def _seam(name):
    if SEAM.get(name):
        SEAM[name]()


def _write(descriptor, data):
    """One write to a file of the snapshot store: the number of bytes written."""
    return os.write(descriptor, data)


def _sync(descriptor):
    os.fsync(descriptor)


def _rename(source, target):
    os.rename(source, target)


def _git(commands, where, *argv, feed=None):
    return _remove._git(commands, '-C', where, *argv, feed=feed)


def _read(commands, where, *argv, feed=None):
    code, out = _git(commands, where, *argv, feed=feed)
    if code != 0:
        raise _Failed('git could not read %s: %s' % (where, str(out)[:300]), git=str(out)[:300])
    return out


def _common(commands, where):
    """The folder that holds the objects and refs of the repository or worktree at `where`, or None."""
    code, out = _git(commands, where, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    return os.path.realpath(out.strip()) if code == 0 and out.strip() else None


# ---------------------------------------------------------------------------------------------
# The kept refs.
# ---------------------------------------------------------------------------------------------

def _ref_name(name):
    """A ref's or an operation's name as the tail of a kept ref: each part as the ledger writes one."""
    return '/'.join(_space.kept_part(part) for part in name.split('/'))


def _only_logged(commands, path, logged, others):
    """The commits of `logged` that none of the item's own other tips reaches. When git cannot say,
    every logged commit that is not itself a tip: one ref too many loses nothing."""
    wanted = [commit for commit in logged if commit not in others]
    if not wanted or not others:
        return wanted
    code, out = _git(commands, path, 'rev-list', '--stdin',
                     feed=('\n'.join(wanted + ['--not'] + sorted(others)) + '\n').encode())
    if code != 0:
        return wanted
    beyond = set(out.split())
    return [commit for commit in wanted if commit in beyond]


def _plan(commands, path, tips):
    """What the item's tips need kept, in order: [(what, object)], with None as the number of a log or
    a stash entry, given when the refs the main repository already holds are known."""
    plan = []
    if tips.get('head'):
        plan.append(('head', tips['head']))
    for line in tips.get('refs') or ():
        commit, _, name = line.partition(' ')
        plan.append(('ref/' + _ref_name(name), commit))
    for name in sorted(tips.get('operations') or {}):
        plan.append(('op/' + _ref_name(name), tips['operations'][name]))
    for commit in reversed(tips.get('stash') or ()):  # the oldest entry first
        plan.append(('stash/', commit))
    others = set(commit for _what, commit in plan)
    for commit in _only_logged(commands, path, sorted(tips.get('log') or ()), others):
        plan.append(('log/', commit))
    return plan


def _numbered(plan, prefix, held):
    """The plan with each log and stash entry given its number: the one a ref of the attempt
    already has at that commit, else the next number no ref has. `prefix` is the attempt's own and
    `held` the refs under it. Returns {ref: object}."""
    refs = {}
    for group in ('stash/', 'log/'):
        at = {}
        highest = 0
        for name, commit in held.items():
            tail = name[len(prefix):]
            if tail.startswith(group) and tail[len(group):].isdigit():
                at.setdefault(commit, name)
                highest = max(highest, int(tail[len(group):]))
        for what, commit in plan:
            if what != group:
                continue
            if commit not in at:
                highest += 1
                at[commit] = prefix + group + str(highest)
            refs[at[commit]] = commit
    for what, commit in plan:
        if what not in ('stash/', 'log/'):
            refs[prefix + what] = commit
    return refs


def _attempt(plan, prefix, held):
    """The kept refs of this attempt, {ref: object}, each under <prefix><n>/. n is the newest attempt
    the item has when that attempt already holds every ref of the plan at the same commit: there is
    nothing to write. Otherwise n is the next number, and the whole plan is written under it: no ref
    of an earlier attempt is moved, reused or added to."""
    numbers = [int(part) for part in set(name[len(prefix):].split('/', 1)[0] for name in held)
               if ATTEMPT.match(part) and part.isdigit()]
    newest = max(numbers) if numbers else 0
    if newest:
        own = prefix + '%d/' % newest
        refs = _numbered(plan, own, {name: commit for name, commit in held.items() if name.startswith(own)})
        if all(held.get(name) == commit for name, commit in refs.items()):
            return refs
    return _numbered(plan, prefix + '%d/' % (newest + 1), {})


def _held(commands, main, prefix):
    out = _read(commands, main, 'for-each-ref', '--format=%(objectname) %(refname)', prefix)
    return {name: commit for commit, _, name in (line.partition(' ') for line in out.split('\n')[:-1])}


def _record_refs(commands, main, source, refs, held, note):
    """Bring the objects across when they are in another store, create each ref that is not there, and
    read every ref and every object back from the main repository. Raises _Failed with the ref and
    git's words."""
    for name in sorted(refs):
        if name in held and held[name] != refs[name]:
            raise _Failed('the kept ref %s exists at another commit: %s' % (name, held[name]), ref=name,
                          git='the ref is at %s, not %s' % (held[name], refs[name]))
    if source is not None and refs:
        code, out = _git(commands, main, '-c', 'uploadpack.allowAnySHA1InWant=true', '-c', 'fetch.fsckObjects=true',
                         'fetch', '--quiet', '--no-tags', '--no-recurse-submodules', '--no-write-fetch-head',
                         '--stdin', source, feed=('\n'.join(sorted(set(refs.values()))) + '\n').encode())
        if code != 0:
            raise _Failed('the fetch into the main repository failed: ' + str(out)[:300], git=str(out)[:300])
    for name in sorted(refs):
        if name in held:
            continue  # the newest attempt already holds it, at the same commit: left as it is
        code, out = _git(commands, main, '-c', 'user.name=Veldo', '-c', 'user.email=veldo@localhost',
                         'update-ref', '--create-reflog', '-m', note, name, refs[name], '')
        if code != 0:
            raise _Failed('the kept ref %s could not be written: %s' % (name, str(out)[:300]), ref=name,
                          git=str(out)[:300])
    back = _held(commands, main, name_prefix(refs)) if refs else {}
    for name in sorted(refs):
        if back.get(name) != refs[name]:
            raise _Failed('the kept ref %s reads back as %s' % (name, back.get(name)), ref=name,
                          git='read back %s, wrote %s' % (back.get(name), refs[name]))
    if refs:
        wanted = sorted(set(refs.values()))
        out = _read(commands, main, 'cat-file', '--batch-check', feed=('\n'.join(wanted) + '\n').encode())
        there = set(line.split(' ')[0] for line in out.split('\n')[:-1] if not line.endswith(' missing'))
        absent = [commit for commit in wanted if commit not in there]
        if absent:
            name = sorted(name for name in refs if refs[name] == absent[0])[0]
            raise _Failed('the main repository does not hold the object of %s' % name, ref=name,
                          git='missing ' + absent[0])


def name_prefix(refs):
    """The item's own prefix, from its refs: refs/veldo/kept/<ticket>/<item>/."""
    return '/'.join(sorted(refs)[0].split('/')[:5]) + '/'


# ---------------------------------------------------------------------------------------------
# The snapshot.
# ---------------------------------------------------------------------------------------------

def _file(where, name):
    """The row of one file of the item: its mode, size and SHA-256. A link is read as a link."""
    full = os.path.join(where, name)
    found = os.lstat(full)
    if not (stat.S_ISREG(found.st_mode) or stat.S_ISLNK(found.st_mode)):
        raise _Failed('not a file or a link, and nothing saves it: ' + name)
    digest = _remove._digest(full)
    size = len(os.fsencode(os.readlink(full))) if stat.S_ISLNK(found.st_mode) else found.st_size
    return {'mode': digest['mode'], 'size': size, 'sha256': digest['sha256']}


def listing(ledger, record, path, commands=None):
    """What a snapshot of the work tree at `path` holds, read now and written nowhere: {files: {path:
    {what, mode, size, sha256, staged}}, deleted_worktree, deleted_index}. what is tracked_edit,
    untracked or ignored_work; staged is None, or {mode, blob, saved}: the index's entry, and whether
    its content differs from the working file and is saved apart. Raises _Failed for what cannot be
    read and for what cannot be saved."""
    ctx = {'ledger': ledger, 'commands': commands if commands is not None else []}
    try:
        _changed, work = _remove._looked(ctx, record, path)
    except _remove._Stop as stopped:
        raise _Failed(str(stopped))
    entries = _read(commands, path, 'status', '--porcelain=v1', '-z', '--untracked-files=all').split('\0')[:-1]
    index = {}
    for entry in _read(commands, path, 'ls-files', '-s', '-z').split('\0')[:-1]:
        head, _, name = entry.partition('\t')
        mode, blob, stage = (head.split(' ') + ['', ''])[:3]
        if stage == '0':
            index[name] = {'mode': mode, 'blob': blob}
    files, gone_tree, gone_index = {}, [], []

    def staged(name, differs):
        if name not in index:
            raise _Failed('git lists a staged path the index does not hold: ' + name)
        return dict(index[name], saved=bool(differs))

    while entries:
        entry = entries.pop(0)
        state, name = entry[:2], entry[3:]
        if 'R' in state or 'C' in state:
            source = entries.pop(0)
            if 'R' in state:
                gone_index.append(source)
        if name.endswith('/'):
            raise _Failed('a folder git does not list file by file, and nothing saves it: ' + name)
        on_disk = os.path.lexists(os.path.join(path, name))
        if state == '??':
            files[name] = dict(_file(path, name), what='untracked', staged=None)
        elif state in UNMERGED:
            if on_disk:
                files[name] = dict(_file(path, name), what='tracked_edit', staged=None, unmerged=state)
            else:
                gone_tree.append(name)
        elif state[0] == 'D':
            gone_index.append(name)
        elif not on_disk:
            gone_tree.append(name)
            if state[0] in STAGED:
                files[name] = {'what': 'staged_only', 'mode': None, 'size': 0, 'sha256': None,
                               'staged': staged(name, True)}
        else:
            files[name] = dict(_file(path, name), what='tracked_edit',
                               staged=staged(name, state[1] != ' ') if state[0] in STAGED else None)
    for name in work:
        if name not in files:
            files[name] = dict(_file(path, name), what='ignored_work', staged=None)
    for name in files:
        parts = name.split('/')
        if os.path.isabs(name) or '..' in parts or '' in parts or '.' in parts:
            raise _Failed('a path that does not stay inside the item: ' + name)
    return {'files': files, 'deleted_worktree': sorted(gone_tree), 'deleted_index': sorted(set(gone_index))}


def _comparable(found):
    """A listing or a manifest as the part two of them are compared by: path by path, what each is,
    its mode and digest and its staged entry, and the two lists of deleted paths."""
    files = {}
    for name, row in (found.get('files') or {}).items():
        held = row.get('staged')
        files[name] = (row.get('what'), row.get('mode'), row.get('sha256'),
                       (held.get('mode'), held.get('blob'), held.get('saved')) if held else None)
    return files, list(found.get('deleted_worktree') or ()), list(found.get('deleted_index') or ())


def _folder(path):
    """Make one folder of the store, mode 0700, or find it there as a real folder."""
    try:
        os.mkdir(path, FOLDER_MODE)
    except FileExistsError:
        pass
    found = os.lstat(path)
    if not stat.S_ISDIR(found.st_mode):
        raise _Failed('a folder of the snapshot store is not a folder: ' + path)


def _folders(top, name):
    """Make the folders the file `name` of an attempt lies in, beneath `top`, each with mode 0700."""
    at = top
    for part in name.split('/')[:-1]:
        at = os.path.join(at, part)
        _folder(at)


def _put(target, blocks):
    """Write one file of an attempt, new, block by block, and sync it. Returns (size, SHA-256) of what
    it was given. A write that comes back short stops the attempt."""
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, FILE_MODE)
    digest, size = hashlib.sha256(), 0
    try:
        for block in blocks:
            digest.update(block)
            size += len(block)
            if _write(descriptor, block) != len(block):
                raise _Failed('a write to the snapshot store came back short: ' + target)
        _sync(descriptor)
    finally:
        os.close(descriptor)
    return size, digest.hexdigest()


def _blocks(source):
    descriptor = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    with os.fdopen(descriptor, 'rb') as file:
        for block in iter(lambda: file.read(BLOCK), b''):
            yield block


def _stored(path):
    """The SHA-256 of one file of the store, read back; a link's is of where it points."""
    return _remove._digest(path)['sha256']


def _sync_folders(top):
    for at, _folders, _files in os.walk(top):
        descriptor = os.open(at, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            _sync(descriptor)
        finally:
            os.close(descriptor)


def _save(ledger, identity, path, found, header, commands):
    """Write one attempt: the next numbered folder of the item in the snapshot store. Returns the
    attempt {path, number, size, manifest}. Raises _Failed, or OSError, with what it wrote left under
    its temporary name."""
    folder = ledger.snapshot_folder(identity)
    _folder(ledger.snapshot_store)
    _folder(os.path.dirname(folder))
    _folder(folder)
    if os.path.realpath(folder) != folder:
        raise _Failed('the item\'s folder in the snapshot store is reached through a link: ' + folder)
    taken = [int(match.group(1)) for match in (ATTEMPT.match(name) for name in os.listdir(folder)) if match]
    number = 1 + max(taken + [0])
    partial, final = os.path.join(folder, str(number) + PARTIAL), os.path.join(folder, str(number))
    os.mkdir(partial, FOLDER_MODE)
    manifest = dict(header, schema=SNAPSHOT_SCHEMA, number=number, files={},
                    deleted_worktree=found['deleted_worktree'], deleted_index=found['deleted_index'])
    total = 0
    for name in sorted(found['files']):
        row = dict(found['files'][name])
        source = os.path.join(path, name)
        if row['sha256'] is not None:
            target = os.path.join(partial, 'work', name)
            _folders(partial, 'work/' + name)
            if stat.S_ISLNK(row['mode']):
                os.symlink(os.readlink(source), target)
            else:
                size, digest = _put(target, _blocks(source))
                if digest != row['sha256'] or size != row['size']:
                    raise _Failed('a file changed while it was saved: ' + name)
            _seam('in_snapshot')
            if _stored(target) != row['sha256']:
                raise _Failed('a file of the snapshot reads back as other content: ' + name)
            now = _remove._digest(source)
            if now != {'mode': row['mode'], 'sha256': row['sha256']}:
                raise _Failed('a file changed while it was saved: ' + name)
            total += row['size']
        if row['staged'] and row['staged']['saved']:
            target = os.path.join(partial, 'staged', name)
            _folders(partial, 'staged/' + name)
            content = _read(commands, path, 'cat-file', 'blob', row['staged']['blob']).encode('utf-8', 'surrogateescape')
            size, digest = _put(target, [content])
            if _stored(target) != digest:
                raise _Failed('a staged file of the snapshot reads back as other content: ' + name)
            row['staged'] = dict(row['staged'], size=size, sha256=digest)
            total += size
        manifest['files'][name] = row
    text = (json.dumps(manifest, sort_keys=True, indent=1) + '\n').encode()
    _size, digest = _put(os.path.join(partial, MANIFEST), [text])
    if _stored(os.path.join(partial, MANIFEST)) != digest:
        raise _Failed('the manifest of the snapshot reads back as other content')
    _sync_folders(partial)
    if os.path.lexists(final):
        raise _Failed('a folder is already at the attempt\'s number: ' + final)
    _rename(partial, final)
    descriptor = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        _sync(descriptor)
    finally:
        os.close(descriptor)
    if _stored(os.path.join(final, MANIFEST)) != digest:
        raise _Failed('the manifest of the snapshot reads back as other content')
    return {'path': final, 'number': number, 'size': total, 'manifest': digest}


def _manifest(attempt):
    """The manifest of an attempt a keep record lists, when its bytes still have the recorded digest
    and every file it names is in the attempt with its digest. None otherwise."""
    try:
        descriptor = os.open(os.path.join(attempt['path'], MANIFEST), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        with os.fdopen(descriptor, 'rb') as file:
            text = file.read()
        if hashlib.sha256(text).hexdigest() != attempt['manifest']:
            return None
        manifest = json.loads(text.decode())
        for name, row in manifest['files'].items():
            if row['sha256'] is not None and _stored(os.path.join(attempt['path'], 'work', name)) != row['sha256']:
                return None
            held = row.get('staged')
            if held and held.get('saved') and _stored(os.path.join(attempt['path'], 'staged', name)) != held['sha256']:
                return None
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return manifest


def _snapshot(ledger, identity, record, path, header, commands):
    """The snapshot part of the keep step. Returns (the attempt to add to the keep record or None, the
    answer's snapshot). Raises _Failed."""
    found = listing(ledger, record, path, commands)
    listed = sorted(((ledger.item(identity) or {}).get('kept') or {}).get('snapshots') or (),
                    key=lambda attempt: attempt['number'])
    if listed:
        manifest = _manifest(listed[-1])
        if manifest is not None and _comparable(manifest) == _comparable(found):
            return None, _answer(manifest, listed[-1])
    if not found['files'] and not found['deleted_worktree'] and not found['deleted_index']:
        return None, {'files': {}, 'path': None, 'number': None}
    try:
        attempt = _save(ledger, identity, path, found, header, commands)
    except OSError as error:
        raise _Failed('the snapshot could not be written: ' + _remove._said(error))
    return attempt, _answer(found, attempt)


def _answer(found, attempt):
    return {'files': {name: {'mode': row['mode'], 'sha256': row['sha256']}
                      for name, row in found['files'].items() if row['sha256'] is not None},
            'path': attempt['path'], 'number': attempt['number']}


# ---------------------------------------------------------------------------------------------
# The one entry.
# ---------------------------------------------------------------------------------------------

def _refused(failed, commands):
    return dict({'ok': False, 'reason': 'space_deferred:' + KEEP_FAILED, 'deferral': KEEP_FAILED,
                 'said': failed.said, 'ref': None, 'git': None, 'commands': commands}, **failed.more)


def keep(ledger, identity, record, event=None, snapshot=False):
    """Carry out the keep step for the worktree or private repository item `identity`, whose ledger
    record is `record`: every commit it reaches on a kept ref in its main repository, read back; with
    `snapshot`, its uncommitted state saved in the snapshot store, read back; then the keep record,
    written by the Ledger. `event` names the event in each ref's log; without it the item's own due
    event is used. Returns the answer (above). Nothing of the item is changed, and on a refusal
    nothing may be removed."""
    commands = []
    try:
        kind = record.get('kind')
        if kind not in KEEP_KINDS:
            raise _Failed('the keep step is for a worktree or a private repository, not for %s' % kind)
        try:
            path = _remove._plain((record.get('locator') or {}).get('path'))
        except _remove._Refusal as refusal:
            raise _Failed(refusal.said)
        stored = ledger.item(identity) or {}
        event = event or (stored.get('due') or {}).get('event') or 'no event'
        main = ledger.main_repository(identity)
        if main is None:
            raise _Failed('the declarations name no main repository for this item: it cannot be kept')
        store = _common(commands, main) if os.path.realpath(main) == main and os.path.isdir(main) else None
        if store is None:
            raise _Failed('the main repository is not at its path: ' + main, git='no repository at ' + main)
        own = _common(commands, path)
        if own is None:
            raise _Failed('git reads no repository at the item')
        tips = _remove.tips(path, kind, commands)
        if tips is None:
            raise _Failed('git could not read the tips of the item')
        prefix = ledger.kept_prefix(identity)
        held = _held(commands, main, prefix)
        refs = _attempt(_plan(commands, path, tips), prefix, held)
        _record_refs(commands, main, None if own == store else own, refs, held,
                     'veldo keep: %s %s' % (event, identity))
        _seam('after_refs')
        attempt, saved = None, None
        if snapshot:
            header = {'item': identity, 'ticket': prefix.split('/')[3], 'repository': main, 'path': path,
                      'head': tips.get('head'), 'event': event}
            attempt, saved = _snapshot(ledger, identity, record, path, header, commands)
            _seam('after_snapshot')
        wrote = ledger.keep(identity, main, refs, attempt)
        if not wrote.get('ok'):
            raise _Failed('the ledger refused the keep record: %s' % (wrote.get('reason'),),
                          ledger=wrote.get('reason'), git=wrote.get('detail'))
        _seam('after_record')
    except _Failed as failed:
        return _refused(failed, commands)
    except (OSError, ValueError, RecursionError) as error:
        return _refused(_Failed('the keep step stopped: ' + _remove._said(error)), commands)
    answer = {'ok': True, 'tips': tips, 'repository': main, 'refs': refs, 'commands': commands}
    if saved is not None:
        answer['snapshot'] = saved
    return answer


def keeper(ledger, event=None, snapshot=False):
    """The keep step in the form the removers are given: keep(identity, record)."""
    def call(identity, record):
        return keep(ledger, identity, record, event=event, snapshot=snapshot)
    return call


def attempts(ledger, identity):
    """Every folder the item has in the snapshot store, counted: [{name, path, number, partial, listed,
    bytes}], by number. partial is a temporary folder a failed or killed attempt left; listed is
    whether the keep record names the attempt. A folder no record lists and a temporary one are kept
    and counted like any other (design 0.3). Reads only."""
    folder = ledger.snapshot_folder(identity)
    listed = set(attempt['path'] for attempt in ((ledger.item(identity) or {}).get('kept') or {}).get('snapshots') or ())
    found = []
    try:
        names = os.listdir(folder) if folder else []
    except OSError:
        names = []
    for name in names:
        match = ATTEMPT.match(name)
        if not match:
            continue
        path = os.path.join(folder, name)
        try:
            size = _remove.measure(path)
        except (OSError, RecursionError, _remove._Stop):
            size = None
        found.append({'name': name, 'path': path, 'number': int(match.group(1)), 'partial': bool(match.group(2)),
                      'listed': path in listed, 'bytes': size})
    return sorted(found, key=lambda entry: (entry['number'], entry['partial']))


def verify(ledger, identity):
    """An item's keep record read against the disk: {ok, missing}. ok only when the record exists, the
    main repository is at its path, every kept ref the record lists resolves to its commit there, and
    every snapshot attempt it lists is in the store with the recorded manifest digest. Reconcile
    completes a removing worktree or private repository only when this is ok, and defers any other as
    keep_failed (design 0.2 and 4.1). Reads only."""
    kept = (ledger.item(identity) or {}).get('kept')
    if not kept:
        return {'ok': False, 'deferral': KEEP_FAILED, 'said': 'the item has no keep record', 'missing': []}
    missing, commands = [], []
    main = kept['repository']
    try:
        if os.path.realpath(main) != main or not os.path.isdir(main):
            raise _Failed('the main repository is not at its path: ' + main)
        held = _held(commands, main, name_prefix(kept['refs'])) if kept['refs'] else {}
    except _Failed as failed:
        return {'ok': False, 'deferral': KEEP_FAILED, 'said': failed.said, 'missing': sorted(kept['refs'])}
    missing += [name for name in sorted(kept['refs']) if held.get(name) != kept['refs'][name]]
    missing += [attempt['path'] for attempt in kept['snapshots'] if _manifest(attempt) is None]
    if missing:
        return {'ok': False, 'deferral': KEEP_FAILED, 'said': 'kept work is missing: ' + ', '.join(missing[:3]),
                'missing': missing}
    return {'ok': True, 'missing': []}
