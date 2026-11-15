#!/usr/bin/env python3
"""Isolated worker clones at the accepted commit, one read-only pinned object cache per repository,
and a worker kept from writing directly to anything another run depends on (PLAN-0019 W27, VELDO-0042,
R45, C13).

EACH RUN ITS OWN CLONE. `Clones` provisions one clone per dispatch at the commit the dispatch contract
accepted (contract.source.commit, checked against contract.source.tree), never at the source
repository's HEAD. A clone is a new repository (`git init` with no template) whose object store
borrows, through Git alternates, the cache of every repository the contract names, followed by a
detached checkout of the accepted commit. It shares no Git metadata with the authority: no worktree
link, no hardlinked object, no remote, no enrollment binding. Clone paths are fresh identities and are
never reused. The repository a clone is made from is the one the store binds for it
(control_store.bound_repository).

ONE CACHE PER REPOSITORY. A repository's cache is a bare repository under the cache root, named from
its domain and repository identity, holding only objects fetched from that repository. It is never
pooled: an alternate exposes every object it holds, so a clone's alternates list exactly the caches
of its own repository and of the attachments its contract names, and no object of an unnamed
repository is reachable from it. A cache holds Git objects and its own pin refs, no authority
metadata and no credentials.

ATTACHMENTS (C13). Another repository appears only as the contract names it, in
input.payload.attachments: each {name, domain, repository, commit} with an exact commit id, bound in
the store. Each is fetched into its own repository's cache and appears in the clone as
refs/attachments/<name> at that commit, read through the alternate; nothing of it is writable.

PINS. Provisioning fetches each named commit into its cache under a ref of this clone's own,
refs/veldo/pins/<clone id>, so ordinary garbage collection of the cache (git gc, whatever the prune
age) keeps every object the clone can reach. Retirement, the provisioner's teardown, releases a
clone's pins only after every dispatch using it has ended: its worker and each consumer attached to
it. A dispatch has ended when its record is conclusive (exited or refused) AND the kernel says now
that its process is gone and its containment group is empty (control_containment.retirement over the
group the VELDO-0039 receiver reported, recorded with `record_group`). A user that `enter` started on
this host during this boot is still in use while its group is unknown, or is not the group its
process was entered in: without the group the kernel cannot say its descendants are gone, so
retirement fails closed. A clone still in use is refused `clone_in_use` and keeps everything.

WRITE CONFINEMENT (`enter`). A worker starts through the receiver's containment wrapper and then this
module's `enter`, the adapter's configured argv prefix (`Clones.adapter`). It finds the clone its
dispatch uses, records that it entered (its process identity and cgroup, in the clone root, before
anything is confined), confines itself with Linux Landlock and becomes the engine by exec inside the
clone, with the Git variables that select a repository removed. The confinement denies only what the
threat model names and grants everything else, so an engine keeps what it can do today:

- Writes are denied beneath exactly these protected targets, recorded in the clone's manifest at
  provisioning: the clone root (every clone, including this clone's own manifest, pins record and
  entrance records), the cache root (every cache), the store's directory, the configured protected
  directories (the keys), the configured engines directories (VELDO-0060/0061: the pinned engine
  copies under the factory state root and the engine packages, so no worker replaces what the next
  dispatch runs; still readable and executable), and the Git metadata of every repository the store
  binds (its git directory, common directory and .git entry). A worker's own work tree and scratch directory (its
  TMPDIR) are granted back beneath the clone root; a consumer's scratch directory only, so it reads
  the clone and writes none of it.
- Reads of file content are denied beneath the cache root and the configured protected directories.
  The caches of the repositories this clone names are granted back, so its alternates resolve and an
  unnamed repository's cache stays unreadable even when a worker appends it to its own alternates.
- Everything else stays readable, writable, executable and listable as before: the home directory's
  existing entries (an engine's state directory such as ~/.claude or ~/.codex, ~/.cache), the
  temporary directories (/tmp, /var/tmp, /dev/shm), the devices and every other repository's work
  tree. Changing a file's mode is not a Landlock right.

Landlock grants by directory hierarchy and cannot deny a single path, so each denial is built from its
targets' ancestor chains, as control_keys_custody (VELDO-0067) builds its read denial: every entry
beside a chain, at every level of every chain, is granted as a whole hierarchy (an existing file
beside a chain is granted its content rights), and nothing on a chain is granted. What that still
denies, stated rather than hidden: a NEW entry created, removed, renamed or linked directly in an
ancestor directory of a protected target after the worker starts (an existing file there stays
writable in place), and, for a read-protected target's ancestors, the content of a file created there
after the worker starts. `ancestors` names every such directory this account can write, and each
manifest records them. So the layout keeps everyday locations off the chains: no protected target
may be beneath a temporary directory (refused `invalid_input:layout`), and the clone root, cache root,
store and keys belong in one directory of Veldo's own whose ancestors the owner's account cannot write
anyway (for example /var/lib/veldo, made once by the installation). The bound repositories' Git
metadata is where the owner keeps them, usually under the home directory, which puts the home
directory and each repository's parent on the write chain: an engine that saves a file directly in
the home directory by write-and-rename (Claude Code's ~/.claude.json) is refused the rename and its
lock directory. The proof README records what the installed engines do there. Landlock also requires
no_new_privs, so a setuid program cannot gain privilege in a confined worker. `enter` refuses to start
the engine on a kernel without Landlock ABI 3, where truncation is first handled.

WHAT IT IS NOT. It does not stop a worker that deliberately leaves its group, or writes through the
owner's own unconfined processes (the user service manager, shell startup files, ssh to this host);
only a separate worker account closes those (Release 2, Telegram 28578/28580). Interrupted
provisioning or retirement and recovery from concurrent garbage collection are Release 2. Linux only;
the Mac's worker profile is VELDO-0124. Standard library only (ctypes for Landlock).
"""
import ctypes
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid


def _organ(name):
    spec = importlib.util.spec_from_file_location('clone_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_git_process = _organ('git_process')
EP = _organ('env_provision')
GI = _organ('control_git_identity')

SCHEMA = 'veldo.worker_clone/v1'
MANIFEST = 'clone.json'
ENTERED = 'entered'
# The pinned engine the receiver bound (control_launch's ENGINE PROTOCOL), re-hashed before the exec.
ENGINE_PATH, ENGINE_DIGEST = 'VELDO_ENGINE_PATH', 'VELDO_ENGINE_SHA256'
PIN_PREFIX = 'refs/veldo/pins/'
ATTACHMENT_PREFIX = 'refs/attachments/'
ATTACHMENT_FIELDS = ('name', 'domain', 'repository', 'commit')
ENDED = ('exited', 'refused')
GIT_SECONDS = 120
EXIT_REFUSED = 70

# The error class of each refusal code, by its first segment. The codes a dispatch is refused with use
# the dispatch record's own classes (control_dispatch.TAXONOMY). Unknown is never success.
TAXONOMY = {'invalid_input': 'invalid_input', 'binding_mismatch': 'invalid_input',
            'missing_authority': 'missing_authority', 'stale_input': 'stale_subject', 'clone_in_use': 'stale_subject',
            'space_deferred': 'stale_subject',
            'unavailable_service': 'unavailable_service', 'missing_evidence': 'missing_evidence'}

# Landlock (the generic syscall table numbers, the same on x86_64 and aarch64) and the rights it
# handles here: every way to change the file system's content or names, and reading a file's content.
# Listing and executing are not handled, so they stay as they were everywhere.
SYSCALLS = {'x86_64': (444, 445, 446), 'aarch64': (444, 445, 446)}
CREATE_RULESET_VERSION = 1
RULE_PATH_BENEATH = 1
WRITE_FILE, READ_FILE, REMOVE_DIR, REMOVE_FILE = 1 << 1, 1 << 2, 1 << 4, 1 << 5
MAKE = (1 << 6) | (1 << 7) | (1 << 8) | (1 << 9) | (1 << 10) | (1 << 11) | (1 << 12)  # char dir reg sock fifo block sym
REFER, TRUNCATE = 1 << 13, 1 << 14
WRITES = WRITE_FILE | REMOVE_DIR | REMOVE_FILE | MAKE | REFER | TRUNCATE
READS = READ_FILE
HANDLED = WRITES | READS
# The rights a rule on a non-directory may carry (a file, a device, a socket).
FILE_RIGHTS = WRITE_FILE | READ_FILE | TRUNCATE
MINIMUM_ABI = 3
PR_SET_NO_NEW_PRIVS = 38
O_PATH = getattr(os, 'O_PATH', 0o10000000)
TEMPORARY = ('/tmp', '/var/tmp', '/dev/shm')


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__(code + (': ' + detail if detail else ''))
        self.code, self.detail = code, detail


def taxonomy(code):
    return TAXONOMY.get(str(code).split(':', 1)[0], 'unknown_outcome')


def _hex(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', value) is not None


def _overlap(a, b):
    a, b = Path(a), Path(b)
    return a == b or a in b.parents or b in a.parents


def _beneath(path, root):
    path, root = Path(path), Path(root)
    return path == root or root in path.parents


def _git(*args, check=True, code='unavailable_service:provisioning'):
    result = _git_process.run(['git', *[str(a) for a in args]], capture_output=True, text=True, timeout=GIT_SECONDS,
                              stdin=subprocess.DEVNULL)
    if check and result.returncode:
        raise Refused(code, 'git %s failed' % next((str(a) for a in args if not str(a).startswith('-')
                                                    and '/' not in str(a)), 'command'))
    return result


def _scratch(root, dispatch_id):
    return Path(root) / 'scratch' / hashlib.sha256(str(dispatch_id).encode()).hexdigest()[:24]


def temporary_directories(environment=None):
    """The directories every engine creates files in directly: the system's temporary directories and
    the process's own. No protected target may be beneath one, or its chain would deny them."""
    source = os.environ if environment is None else environment
    found = {Path(p).resolve() for p in TEMPORARY + (tempfile.gettempdir(), source.get('TMPDIR') or '/tmp')
             if p and os.path.isdir(p)}
    return sorted(found)


# The worker side: find the clone, record the entrance, confine, become the engine.

class _RulesetAttr(ctypes.Structure):
    _fields_ = [('handled_access_fs', ctypes.c_uint64)]


class _PathBeneathAttr(ctypes.Structure):
    _pack_ = 1
    _fields_ = [('allowed_access', ctypes.c_uint64), ('parent_fd', ctypes.c_int32)]


def _libc():
    if sys.platform != 'linux' or platform.machine() not in SYSCALLS:
        raise Refused('unavailable_service:confinement', 'Landlock is a Linux kernel sandbox; this host has none')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    return libc, SYSCALLS[platform.machine()]


def abi():
    """The kernel's Landlock ABI version, or 0 when it has none."""
    try:
        libc, (create, _, _) = _libc()
    except Refused:
        return 0
    version = libc.syscall(ctypes.c_long(create), None, ctypes.c_size_t(0), ctypes.c_uint32(CREATE_RULESET_VERSION))
    return version if version > 0 else 0


def _chain(targets):
    """The targets and every ancestor of each."""
    chain = set(targets)
    for target in targets:
        chain.update(target.parents)
    return chain


def beside(targets):
    """[(path, is_directory)] beside the targets' ancestor chains, at every level of every chain. A path
    is on a chain when it is a target or one of its ancestors; nothing on a chain is returned, so no
    returned hierarchy holds a target. Symbolic links are not returned: their targets are granted, or
    not, at their own place in the tree."""
    targets = [Path(t) for t in targets]
    chain = _chain(targets)
    found = []
    for ancestor in sorted(p for p in chain if not any(_beneath(p, t) for t in targets)):
        try:
            entries = list(os.scandir(ancestor))
        except OSError:
            continue
        for entry in entries:
            path = Path(entry.path)
            if path in chain:
                continue
            try:
                if entry.is_symlink():
                    continue
                found.append((path, entry.is_dir(follow_symlinks=False)))
            except OSError:
                continue
    return found


def rules(deny_write, deny_read, write=(), read=()):
    """{path: (rights, is_directory)}: for each denial (writes beneath `deny_write`, reads beneath
    `deny_read`), its rights granted on every hierarchy beside its targets' chains and on the paths
    granted back beneath them (`write`, `read`); the whole file system when a denial has no target."""
    merged = {}

    def grant(path, is_directory, rights):
        held, _ = merged.get(path, (0, is_directory))
        merged[path] = (held | rights, is_directory)

    for rights, targets, back in ((WRITES, deny_write, write), (READS, deny_read, read)):
        targets = [Path(t) for t in targets]
        for path, is_directory in beside(targets) if targets else [(Path('/'), True)]:
            grant(path, is_directory, rights)
        for path in back:
            grant(Path(path), os.path.isdir(path), rights)
    return merged


def ancestors(deny_write, deny_read):
    """The directories on a denial's chains that this account can write: in each, a confined process
    cannot create, remove, rename or link an entry directly (write chain), or read a file created there
    after it started (read chain). The everyday cost of the layout, named."""
    cost = {}
    for name, targets in (('write', deny_write), ('read', deny_read)):
        targets = [Path(t) for t in targets]
        cost[name] = sorted(str(p) for p in _chain(targets)
                            if not any(_beneath(p, t) for t in targets) and os.access(p, os.W_OK))
    return cost


def confine(granted):
    """Confine this process and everything it starts to `granted` ({path: (rights, is_directory)}): each
    handled right is refused everywhere no rule grants it. Irrevocable. Refuses, confining nothing,
    below Landlock ABI 3."""
    libc, (create, add_rule, restrict_self) = _libc()
    version = abi()
    if version < MINIMUM_ABI:
        raise Refused('unavailable_service:confinement', 'Landlock ABI %d is below %d' % (version, MINIMUM_ABI))
    attr = _RulesetAttr(HANDLED)
    ruleset = libc.syscall(ctypes.c_long(create), ctypes.byref(attr), ctypes.c_size_t(ctypes.sizeof(attr)),
                           ctypes.c_uint32(0))
    if ruleset < 0:
        raise Refused('unavailable_service:confinement', 'landlock_create_ruleset failed (errno %d)' % ctypes.get_errno())
    added = 0
    try:
        for path, (rights, is_directory) in sorted(granted.items()):
            rights = rights if is_directory else rights & FILE_RIGHTS
            if not rights:
                continue
            try:
                fd = os.open(path, O_PATH | os.O_CLOEXEC | os.O_NOFOLLOW)
            except OSError:
                continue
            try:
                rule = _PathBeneathAttr(rights, fd)
                if libc.syscall(ctypes.c_long(add_rule), ctypes.c_int(ruleset), ctypes.c_int(RULE_PATH_BENEATH),
                                ctypes.byref(rule), ctypes.c_uint32(0)) < 0:
                    raise Refused('unavailable_service:confinement', 'landlock_add_rule failed (errno %d)' % ctypes.get_errno())
                added += 1
            finally:
                os.close(fd)
        if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            raise Refused('unavailable_service:confinement', 'no_new_privs could not be set')
        if libc.syscall(ctypes.c_long(restrict_self), ctypes.c_int(ruleset), ctypes.c_uint32(0)) < 0:
            raise Refused('unavailable_service:confinement', 'landlock_restrict_self failed (errno %d)' % ctypes.get_errno())
    finally:
        os.close(ruleset)
    return added


def find(clones, dispatch_id):
    """(manifest, user) of the one live clone `dispatch_id` uses under the clone root."""
    found = []
    for path in sorted(Path(clones).glob('*/' + MANIFEST)):
        try:
            manifest = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        found += [(manifest, user) for user in manifest.get('users') or [] if user.get('dispatch_id') == dispatch_id]
    if not dispatch_id or len(found) != 1:
        raise Refused('invalid_input:clone_unknown', 'no single clone names this dispatch')
    return found[0]


def grants(manifest, user):
    """The confinement of one user of a clone: the manifest's protected targets denied, and granted back
    beneath them a worker's work tree and scratch directory (a consumer's scratch directory) for
    writing, and the caches of the repositories the clone names for reading."""
    protected = manifest.get('protected')
    if not isinstance(protected, dict) or not protected.get('write') or not protected.get('read'):
        raise Refused('invalid_input:clone_unknown', 'the clone records no protected targets')
    write = [user['scratch']] + ([manifest['work']] if user.get('role') == 'worker' else [])
    return rules(protected['write'], protected['read'], write, [pin['cache'] for pin in manifest['pins']])


def _process(pid):
    """A process identity as control_containment.alive reads it: pid, boot and start time."""
    stat = Path('/proc/%d/stat' % pid).read_text()
    return {'pid': pid, 'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
            'start': stat[stat.rindex(')') + 2:].split()[19]}


def _entrance(manifest, user):
    """Record, in the clone root and before anything is confined, that this process entered for `user`:
    its identity and the cgroup it runs in. The clone root is protected, so no worker can remove it."""
    directory = Path(manifest['root']) / ENTERED
    directory.mkdir(mode=0o700, exist_ok=True)
    pid = os.getpid()
    cgroup = next((line[3:] for line in Path('/proc/self/cgroup').read_text().splitlines() if line.startswith('0::')),
                  None)
    record = dict(_process(pid), dispatch_id=user['dispatch_id'], cgroup=cgroup)
    name = '%s.%d.json' % (Path(user['scratch']).name, pid)
    temporary = directory / ('.%s.tmp' % name)
    temporary.write_text(json.dumps(record, sort_keys=True))
    os.replace(temporary, directory / name)


def enter(clones, argv, environment=None):
    """The worker side (`control_clone.py enter <clone root> -- <engine argv>`): record the entrance of
    the dispatch named by VELDO_DISPATCH_ID, confine it, then become the engine in the clone."""
    source = os.environ if environment is None else environment
    manifest, user = find(clones, source.get('VELDO_DISPATCH_ID'))
    granted = grants(manifest, user)
    _entrance(manifest, user)
    confine(granted)
    # The clone decides which repository the engine's Git reads: the variables that select a
    # repository, work tree, index or object store are removed by prefix; transport and
    # configuration variables stay (git_process's network profile).
    child = _git_process.clean_env(dict(source), profile='network')
    child.update(TMPDIR=user['scratch'], TMP=user['scratch'], TEMP=user['scratch'], VELDO_CLONE=manifest['work'])
    os.chdir(manifest['work'])
    pinned, expected = child.pop(ENGINE_PATH, None), child.pop(ENGINE_DIGEST, None)
    if pinned is not None:
        # VELDO-0060/0061: the receiver bound this pinned engine; the entrance execs it, so it re-hashes the
        # file now, immediately before the exec, and a changed one (or another program) never runs.
        if not argv or argv[0] != pinned:
            raise Refused('binding_mismatch:engine_executable', 'the entrance execs another program than the pinned one')
        if _file_digest(pinned) != expected:
            raise Refused('binding_mismatch:engine_digest', 'the pinned engine changed after it was bound')
    os.execvpe(argv[0], list(argv), child)


def _file_digest(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return 'sha256:' + digest.hexdigest()


# The provisioner.

SPACE_ENDED = ('removed', 'gone')  # the states of an item whose thing is no longer on disk
SPACE_SAFE = ('gone', 'clear', 'kept')  # the answers of the look with no ledger that allow a delete
SPACE_SIGNALLED = ('present', 'kept', 'deferred')  # the states the ledger's signal reaches
_SPACE = {}


def space_signal(space, event, paths, emitter, ended=False, confirm=False):
    """VELDO-0303: send `event` through Signal (control_space_signal.signal) for the things at `paths`
    and say what became of each: {path: {item, state, deferral}}. Nothing here deletes anything:
    whatever goes is removed by Signal's removers, after the safety rules and the keep step.

    `space` is what the installation wires in when it has a space ledger: a mapping with ledger (the
    control_space.Ledger) and, under their own names, the arguments Signal is given (probe, kinds,
    remover, free, keep, owner_live, landed, queued, run, proc, borrow_root). The items are the live
    ones the ledger records at or beneath `paths`.

    VELDO-0308: the event is sent once, and it names exactly the clone's own items, each at the version
    read here (space_named, the ledger's signal that names items): the ledger acts on those and on
    nothing else of their owner, so a run directory, a worktree or an agent repository of the same owner
    that is not at or beneath `paths` is never reached from here, and the run's own send (the receiver's,
    the sweep's) does not wait for this one. The ledger refuses the whole command, with nothing written,
    when one named item changed since it was read: every path then answers remove_refused with the
    ledger's reason, and nothing is sent in its place. With nothing to name no command is sent.

    A path the ledger records no live item for answers with no item and the deferral not_in_ledger, and
    nothing is done to it; when the kernel says nothing is at that path (not found, and no other answer)
    it answers gone, for there is nothing to remove. Whatever raises removes nothing: every path then
    answers with the deferral remove_refused and what was raised.

    `ended` says the caller has just read from the kernel that the runs owning these items are over:
    rule 3 is answered conclusive for those runs and for no other owner. `confirm` first confirms the
    items still in state declared (a creation that failed part way), so the event reaches them."""
    paths = [os.path.normpath(str(path)) for path in paths]
    found = {path: {'item': None, 'state': None, 'deferral': 'not_in_ledger'} for path in paths}

    try:
        ledger = space['ledger']
        given = {key: value for key, value in space.items() if key != 'ledger'}
        live = {identity: record for identity, record in ledger.items().items()
                if record.get('state') not in SPACE_ENDED and _space_beneath(record, paths)}
        runs = set()
        for identity, record in sorted(live.items()):
            if confirm and record.get('state') == 'declared':
                ledger.confirm(identity)
            run = (record.get('owner') or {}).get('run')
            if isinstance(run, dict):
                runs.add(run.get('id'))
        # Exactly the clone's own items, each at the version read now; never an item that is not here.
        named = space_named(ledger, event, paths)
        if ended:
            wired = given.get('owner_live')
            given['owner_live'] = lambda owner: (
                {'conclusive': True, 'group_empty': True} if (owner.get('run') or {}).get('id') in runs
                else wired(owner) if wired else None)
        if 'signal' not in _SPACE:
            _SPACE['signal'] = _organ('control_space_signal').signal
        if named['items']:
            answer = _SPACE['signal'](ledger, event, named, emitter=emitter, **given)
            if not (isinstance(answer, dict) and answer.get('ok') is True):
                # One named item changed since it was read: nothing was written, and nothing is sent in its place.
                raise ValueError('the ledger refused the send whole: %s'
                                 % ((answer or {}).get('reason') if isinstance(answer, dict) else answer,))
        for identity, record in live.items():
            where = record['locator']['path']
            if where in found:
                now = ledger.item(identity) or {}
                found[where] = {'item': identity, 'state': now.get('state'),
                                'deferral': (now.get('deferral') or {}).get('rule')
                                if now.get('state') == 'deferred' else None}
        for path in paths:
            if found[path]['item'] is None and space_absent(path):
                found[path] = {'item': None, 'state': 'gone', 'deferral': None}
    except Exception as error:  # noqa: BLE001 - what could not be signalled is not removed
        raised = '%s: %s' % (type(error).__name__, str(error)[:300])
        found = {path: {'item': None, 'state': None, 'deferral': 'remove_refused', 'raised': raised}
                 for path in paths}
    return found


def _space_beneath(record, places):
    where = (record.get('locator') or {}).get('path')
    return bool(where) and any(where == path or where.startswith(path + '/') for path in places)


def space_named(ledger, event, paths):
    """VELDO-0308: the subject of an event sent for exactly the items at or beneath `paths`, as the
    ledger's signal that names items takes it: {items: [{item, version}, ...]}. The items are those the
    event reaches there (present, kept or deferred, ending on `event`, not marked Keep by the owner),
    whoever else their owner owns. The versions are read before the records, so a record that changed
    between the two reads is named at the version it had, and the ledger refuses the whole command. An
    item that appeared between them was not read and is not named."""
    versions = {identity: version for identity, version in ledger.conn.execute('SELECT id, version FROM entities')}
    named = sorted(identity for identity, record in ledger.items().items()
                   if identity in versions and record.get('state') in SPACE_SIGNALLED and not record.get('owner_keep')
                   and event in ((record.get('ends_on') or {}).get('events') or ())
                   and _space_beneath(record, paths))
    return {'items': [{'item': identity, 'version': versions[identity]} for identity in named]}


def space_absent(path):
    """Whether the kernel says nothing is at `path`: not found, and nothing else. A path that could
    not be read (a folder above it that may not be searched, a failing disk) is not absent."""
    try:
        os.lstat(path)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def space_refusal(entry):
    """The name of the refusal for a thing Signal did not remove: space_deferred and the rule that
    deferred it; for an item no rule deferred, the state it is in (due in report mode, removing when
    it was left under its marked name, kept, present); not_in_ledger when no item records it."""
    return 'space_deferred:' + str(entry.get('deferral') or entry.get('state') or 'not_in_ledger')


def space_standalone(path, kind, main=None, event='run_finished', ticket=None, skip=()):
    """VELDO-0303: the look before a delete where no ledger is wired (control_space_standalone): the
    unique work probe and the keep step for the thing at `path`, {path, item, state, deferral, said,
    refs}. This module deletes the thing only when the state is one of SPACE_SAFE: nothing is there
    (gone), a folder holds no repository (clear), or the commits of a worktree or a private repository
    are on kept refs in `main` (kept). Anything else stays where it is. Whatever raises removes nothing."""
    try:
        if 'standalone' not in _SPACE:
            _SPACE['standalone'] = _organ('control_space_standalone').standalone
        return _SPACE['standalone'](str(path), kind, main=None if main is None else str(main), event=event,
                                    ticket=ticket, skip=tuple(str(where) for where in skip))
    except Exception as error:  # noqa: BLE001 - what could not be looked at is not removed
        return {'path': str(path), 'item': None, 'state': None, 'deferral': 'remove_refused',
                'said': '%s: %s' % (type(error).__name__, str(error)[:300]), 'refs': {}}


class SpaceCreationError(RuntimeError):
    code = 'unavailable_service:space_ledger'

    def __init__(self, detail):
        super().__init__(self.code + ': ' + detail)


def space_owner(contract):
    """The accepted dispatch supplies the owner; never infer it from a folder name."""
    reservation = contract.get('reservation') or {}
    context = (contract.get('input') or {}).get('context') or {}
    return {'scope': {'type': 'project', 'id': reservation.get('project')},
            'ticket': contract.get('unit'),
            'run': {'id': contract.get('dispatch_id'), 'station': contract.get('station')},
            'lane': context.get('lane') or reservation.get('lane') or contract.get('lane')}


def space_main_repository(main):
    """The repository a creator's source belongs to. A work tree, a linked worktree or a git
    directory is read through git's common directory, so a linked worktree gives its main
    repository. Anything else, a folder beneath a work tree included, is returned as given."""
    where = os.path.realpath(str(main))
    result = _git('-C', where, 'rev-parse', '--git-dir', '--git-common-dir', check=False)
    lines = [] if result.returncode else result.stdout.splitlines()
    if len(lines) != 2:
        return Path(main)
    git_dir, common = (os.path.realpath(os.path.join(where, line)) for line in lines)
    if where != git_dir and not os.path.lexists(os.path.join(where, '.git')):
        return Path(main)
    return Path(common)


class SpaceCreator:
    """VELDO-0302: supplied ledger, declare before creation, confirm after success.

    None means no central installation. An empty or broken mapping is not None and
    refuses creation. A failed partial creation stays recorded for recovery; only
    an absent thing is marked gone. This seam never removes anything.
    """

    def __init__(self, space, owner, refusal=None):
        self.space, self.owner, self.refusal = space, owner, refusal
        self.items = {}

    def call(self, operation, *args, **kwargs):
        try:
            result = getattr(self.space['ledger'], operation)(*args, **kwargs)
            if not isinstance(result, dict) or result.get('ok') is not True:
                raise ValueError(str(result))
            return result
        except Exception as error:
            if self.refusal is not None:
                raise self.refusal('unavailable_service:space_ledger', str(error)) from error
            raise SpaceCreationError(str(error)) from error

    @contextmanager
    def item(self, kind, path, *, main=None, parent=None, start=None, branch=None, form=None,
             provisioned=None):
        locator = ({'repository': str(main), 'ref': branch} if kind == 'branch'
                   else {'path': str(path)})
        identity = None
        if self.space is not None:
            if kind == 'agent_repository':
                try:
                    known = self.space['ledger']._main_of({'owner': self.owner})
                    if (known is None or os.path.realpath(known) != known
                            or space_main_repository(main) not in (Path(known), Path(known) / '.git')):
                        raise ValueError('the owner scope must name the creator main repository')
                except Exception as error:
                    if self.refusal is not None:
                        raise self.refusal('unavailable_service:space_ledger', str(error)) from error
                    raise SpaceCreationError(str(error)) from error
            if kind == 'worktree' and (self.owner or {}).get('ticket') and not callable(provisioned):
                raise SpaceCreationError('a ticket worktree requires space_provisioned')
            identity = self.call('declare', kind, locator, self.owner, 'seam', parent=parent,
                                 start=start, branch=branch, form=form)['item']
            self.items[str(path)] = identity
        try:
            yield identity
            if identity is not None:
                if kind == 'worktree' and (self.owner or {}).get('ticket'):
                    provisioned(self.owner['ticket'], str(path),
                                dispatch=(self.owner.get('run') or {}).get('id'))
                self.call('confirm', identity)
        except BaseException:
            # A branch is not a filesystem path. Its repository may have been partly made.
            if (identity is not None and kind != 'branch' and space_absent(path)
                    and (self.space['ledger'].item(identity) or {}).get('state') == 'declared'):
                self.call('gone', identity)
            raise

    def temporary(self, prefix, root=None):
        """Choose a fresh name without creating it. The caller declares before mkdir."""
        return Path(root or tempfile.gettempdir()) / (prefix + uuid.uuid4().hex)


class Clones(EP.EnvProvisioner):
    """Worker clones of one domain over the runner's control_dispatch.Dispatches (its store connection,
    bindings and dispatch records). `clones` and `caches` are the roots clones and repository caches live
    under; `protected` names the directories no worker may read or write (the key directories), and
    `engines` those it may read and execute but never write (the pinned engine copies and packages). The
    store's directory is never written by a worker either."""

    def __init__(self, dispatches, *, clones, caches, protected=(), engines=(), clock=None, space=None):
        super().__init__()
        # VELDO-0303: the installation's space ledger and what Signal is given (space_signal), or None
        # where the installation has none. With it, no clone folder is deleted here: it goes through Signal.
        self.space = space
        self.C = _organ('control_containment')  # VELDO-0040: a clone user's ending read from the kernel
        self.dispatches, self.store, self.conn = dispatches, dispatches.store, dispatches.conn
        self.domain, self.clock = dispatches.domain, clock or time.time
        self.clones, self.caches = Path(clones).resolve(), Path(caches).resolve()
        database = next((row[2] for row in self.conn.execute('PRAGMA database_list') if row[1] == 'main'), '')
        self.protected = [Path(p).resolve() for p in protected]
        self.engines = [Path(p).resolve() for p in engines]
        self.store_directory = [Path(database).resolve().parent] if database else []
        self.observations, self.counts = [], {'accepted': 0, 'refused': 0}
        roots = (self.clones, self.caches)
        if _overlap(*roots) or any(_overlap(r, p) for r in roots
                                   for p in self.protected + self.store_directory + self.engines):
            raise Refused('invalid_input:root', 'the clone and cache roots are separate and outside every protected path')
        self._layout(list(roots) + self.protected + self.store_directory + self.engines)
        for root in roots:
            root.mkdir(mode=0o700, parents=True, exist_ok=True)

    @staticmethod
    def _layout(targets):
        """No protected target beneath a temporary directory: its chain would deny every engine the
        files it creates there."""
        for target in targets:
            if any(_beneath(target, t) for t in temporary_directories()):
                raise Refused('invalid_input:layout', 'a protected target is not beneath a temporary directory')

    # What the launch path is configured with. VELDO-0129 wires the production adapters' argv to this
    # `adapter` prefix and composes create/attach/teardown with the VELDO-0039 runner and receiver; the
    # group the receiver reports is recorded on the clone's user with `record_group` so retirement can
    # read the clone user's ending through it.

    def adapter(self, argv):
        """The argv an adapter's worker is configured with: `enter` over this clone root, then the engine."""
        return [sys.executable, '-B', str(Path(__file__).resolve()), 'enter', str(self.clones), '--', *argv]

    def record_group(self, dispatch_id, group):
        """Record the containment group the receiver reported for a clone user, so `user_state` reads its
        ending through control_containment (VELDO-0040) as well as the process identity."""
        manifest, _ = find(self.clones, dispatch_id)
        for user in manifest['users']:
            if user['dispatch_id'] == dispatch_id:
                user['group'] = group
        self._write(manifest)

    # Provisioning.

    def _metadata(self):
        """The Git metadata of every repository the store binds, in any domain: its git directory, its
        common directory and its .git entry. A path Git cannot read is protected whole."""
        if not self.conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='repository_bindings'").fetchone():
            return []
        found = set()
        for (path,) in self.conn.execute('SELECT path FROM repository_bindings ORDER BY path'):
            result = _git('-C', path, 'rev-parse', '--path-format=absolute', '--git-dir', '--git-common-dir', check=False)
            lines = [line for line in result.stdout.splitlines() if line.strip()] if not result.returncode else []
            found.update(Path(line).resolve() for line in lines)
            if os.path.lexists(os.path.join(path, '.git')):
                found.add(Path(path).resolve() / '.git')
            if not lines:
                found.add(Path(path).resolve())
        return sorted(found)

    def _protection(self):
        """What every user of a new clone is denied (manifest `protected`) and what that costs
        (manifest `ancestors`)."""
        metadata = self._metadata()
        self._layout(metadata)
        write = sorted({self.clones, self.caches, *self.store_directory, *self.protected, *metadata, *self.engines})
        read = sorted({self.caches, *self.protected})
        protected = {'write': [str(p) for p in write], 'read': [str(p) for p in read]}
        return protected, ancestors(write, read)

    def _cache(self, domain, repository):
        """The one cache of a repository: a bare repository named from its domain and repository."""
        name = hashlib.sha256(('%s\n%s' % (domain, repository)).encode()).hexdigest()[:32]
        path = self.caches / (name + '.git')
        if not (path / 'objects').is_dir():
            _git('init', '-q', '--bare', '--template=', path)
        return path

    def _pin(self, cache, repository, source, commit, clone_id):
        """Fetch `commit` from `source` into `cache` under this clone's own pin ref for `repository`.
        The ref carries the repository so a clone that pins two repositories (its own and an attachment)
        never collides on one ref, even were a defect to point them at a single cache."""
        ref = PIN_PREFIX + clone_id + '/' + hashlib.sha256(str(repository).encode()).hexdigest()[:16]
        _git('-C', cache, 'fetch', '-q', '--no-tags', '--no-write-fetch-head', source, '%s:%s' % (commit, ref),
             code='stale_input:commit_unavailable')
        seen = _git('-C', cache, 'rev-parse', '--verify', '-q', ref + '^{commit}', check=False).stdout.strip()
        if seen != commit:
            self._release(cache, ref)
            raise Refused('stale_input:commit_unavailable', 'the pinned object is not the named commit')
        return {'cache': str(cache), 'ref': ref, 'commit': commit}

    def _release(self, cache, ref, identity=None):
        """Release only through the remover after the owning item's keep and outcome."""
        identity = identity or getattr(self, '_ref_items', {}).get((str(cache), ref))
        ledger = (self.space or {}).get('ledger')
        answer = _organ('control_space_remove').remove_ref(str(cache), ref, ledger, identity)
        if not hasattr(self, 'ref_outcomes'):
            self.ref_outcomes = {}
        self.ref_outcomes[ref] = answer
        return answer

    def _bound(self, domain, repository, code):
        path = self.store.bound_repository(self.conn, domain, repository)
        if path is None:
            raise Refused(code, 'no repository is bound for %s' % repository)
        if not os.path.isdir(path):
            raise Refused('unavailable_service:repository', 'the bound repository is not readable')
        if any(_overlap(root, path) for root in (self.clones, self.caches)):
            raise Refused('invalid_input:root', 'a clone or cache root overlaps a bound repository')
        return path

    def _accepted(self, contract):
        """The accepted inputs of a contract: its repository, commit and tree, and every attachment,
        each resolved to its bound repository. Refused by name when any is malformed or unbound."""
        if not isinstance(contract, dict) or not isinstance(contract.get('source'), dict):
            raise Refused('invalid_input:source', 'the contract names its accepted source')
        source = contract['source']
        commit, tree = source.get('commit'), source.get('tree')
        if not (_hex(commit) and _hex(tree)) or contract.get('domain') != self.domain:
            raise Refused('invalid_input:source', 'the accepted source is an exact commit and tree of this domain')
        domain, repository = contract['domain'], contract.get('repository')
        path = self._bound(domain, repository, 'missing_authority:repository_unbound')
        try:
            identity = GI.resolve(self.conn, domain, repository, path)
        except GI.Refused as error:
            raise Refused(error.code) from None
        listed = ((contract.get('input') or {}).get('payload') or {}).get('attachments') or []
        if not isinstance(listed, list):
            raise Refused('invalid_input:attachment', 'attachments are a list')
        attachments, names, seen = [], set(), {(domain, repository)}
        for entry in listed:
            if (not isinstance(entry, dict) or set(entry) != set(ATTACHMENT_FIELDS)
                    or not all(isinstance(entry[f], str) and entry[f] for f in ATTACHMENT_FIELDS)
                    or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', entry['name']) or not _hex(entry['commit'])):
                raise Refused('invalid_input:attachment', 'an attachment names a repository at an exact commit')
            if entry['name'] in names or (entry['domain'], entry['repository']) in seen:
                raise Refused('invalid_input:attachment', 'each repository and name is attached once')
            names.add(entry['name'])
            seen.add((entry['domain'], entry['repository']))
            attachments.append(dict(entry, path=self._bound(entry['domain'], entry['repository'],
                                                            'missing_authority:attachment_unbound')))
        commit = source['commit']
        return {'dispatch_id': contract.get('dispatch_id'), 'unit': contract.get('unit'), 'domain': domain,
                'repository': repository, 'path': path, 'commit': commit, 'tree': tree,
                'identity': identity, 'attachments': sorted(attachments, key=lambda a: a['name'])}

    def _create(self, contract):
        accepted = self._accepted_or_observed('provision', contract)
        clone_id = 'clone-' + uuid.uuid4().hex
        root = self.clones / clone_id
        work, pins = root / 'work', []
        scratch = _scratch(root, accepted['dispatch_id'])
        creation = SpaceCreator(self.space, space_owner(contract), Refused)
        with creation.item('scratch', root) as root_item, \
                creation.item('agent_repository', work, main=accepted['path'], parent=root_item,
                              start=accepted['commit'], form='worker_clone'), \
                creation.item('scratch', scratch, parent=root_item):
            root.mkdir(mode=0o700)  # exclusive: no path is ever provisioned twice
            try:
                protected, cost = self._protection()
                commit = accepted['commit']
                pins.append(self._pin(self._cache(accepted['domain'], accepted['repository']), accepted['repository'],
                                      accepted['path'], commit, clone_id))
                for attachment in accepted['attachments']:
                    pins.append(self._pin(self._cache(attachment['domain'], attachment['repository']),
                                          attachment['repository'], attachment['path'], attachment['commit'], clone_id))
                _git('init', '-q', '--template=', work)
                for section in ('user', 'author', 'committer'):
                    for field, value in zip(('name', 'email'), GI.author(accepted['identity'])):
                        _git('-C', work, 'config', '--local', section + '.' + field, value)
                info = work / '.git' / 'objects' / 'info'
                info.mkdir(parents=True, exist_ok=True)
                (info / 'alternates').write_text(''.join('%s\n' % (Path(p['cache']) / 'objects') for p in pins))
                for attachment in accepted['attachments']:
                    _git('-C', work, 'update-ref', ATTACHMENT_PREFIX + attachment['name'], attachment['commit'])
                _git('-C', work, 'checkout', '-q', '--detach', commit)
                self._verify(work, accepted)
                scratch.mkdir(parents=True)
                manifest = {'schema': SCHEMA, 'clone_id': clone_id, 'root': str(root), 'work': str(work),
                            'domain': accepted['domain'], 'repository': accepted['repository'], 'unit': accepted['unit'],
                            'commit': accepted['commit'], 'tree': accepted['tree'],
                            'identity': accepted['identity']['id'], 'space_items': dict(creation.items),
                            'attachments': [{f: a[f] for f in ATTACHMENT_FIELDS} for a in accepted['attachments']],
                            'pins': pins, 'protected': protected, 'ancestors': cost, 'created_at': self.clock(),
                            'users': [{'dispatch_id': accepted['dispatch_id'], 'role': 'worker', 'scratch': str(scratch),
                                       'group': None}]}
                self._write(manifest)
            except BaseException as error:
                if self.space is None:
                    # No ledger: the unique work probe and the keep step by themselves, then the delete; a
                    # clone the look does not answer for stays, with its pins.
                    self._standalone(root, work, pins, accepted.get('path'), accepted.get('unit'))
                else:
                    # VELDO-0303: the declared items go as at teardown, through Signal. No worker has entered.
                    self._through_space(root, work, pins, confirm=True)
                if isinstance(error, (Refused, OSError, subprocess.SubprocessError)):
                    self._event('provision', accepted, 'refused', refusal=getattr(error, 'code', 'unavailable_service:provisioning'))
                raise
        self._event('provision', accepted, 'accepted', clone_id=clone_id, ancestors=cost)
        return EP.EnvHandle(clone_id, 'clone', {'root': str(root), 'work': str(work)})

    def _accepted_or_observed(self, operation, contract):
        try:
            return self._accepted(contract)
        except Refused as error:
            self._event(operation, {'dispatch_id': (contract or {}).get('dispatch_id') if isinstance(contract, dict)
                                    else None, 'unit': (contract or {}).get('unit') if isinstance(contract, dict)
                                    else None, 'repository': (contract or {}).get('repository')
                                    if isinstance(contract, dict) else None}, 'refused', refusal=error.code)
            raise

    @staticmethod
    def _verify(work, accepted):
        """The checkout is the accepted commit and tree, with nothing else in its work tree."""
        head = _git('-C', work, 'rev-parse', 'HEAD', check=False).stdout.strip()
        tree = _git('-C', work, 'rev-parse', 'HEAD^{tree}', check=False).stdout.strip()
        status = _git('-C', work, 'status', '--porcelain', '--untracked-files=all', check=False)
        if head != accepted['commit'] or tree != accepted['tree'] or status.returncode or status.stdout.strip():
            raise Refused('stale_input:source_tree', 'the checkout is not the accepted commit and tree')

    def attach(self, clone_id, contract):
        """Attach a consumer dispatch to a live clone: its contract names the clone's own accepted source
        and exactly its attachments. Returns the clone's handle."""
        accepted = self._accepted_or_observed('attach', contract)
        manifest = self._manifest(clone_id)
        try:
            if manifest is None:
                raise Refused('invalid_input:clone_unknown', 'no live clone has this identity')
            if any(accepted[f] != manifest[f] for f in ('domain', 'repository', 'commit', 'tree')):
                raise Refused('binding_mismatch:clone_source', 'a consumer reads the clone at its accepted commit')
            if [{f: a[f] for f in ATTACHMENT_FIELDS} for a in accepted['attachments']] != manifest['attachments']:
                raise Refused('binding_mismatch:attachments', 'a consumer names exactly the clone attachments')
        except Refused as error:
            self._event('attach', accepted, 'refused', refusal=error.code, clone_id=clone_id)
            raise
        scratch = _scratch(manifest['root'], accepted['dispatch_id'])
        creation = SpaceCreator(self.space, space_owner(contract), Refused)
        with creation.item('scratch', scratch):
            scratch.mkdir(parents=True, exist_ok=True)
            manifest['users'].append({'dispatch_id': accepted['dispatch_id'], 'role': 'consumer', 'scratch': str(scratch),
                                      'group': None})
            self._write(manifest)
        manifest.setdefault('space_items', {}).update(creation.items)
        self._write(manifest)
        self._event('attach', accepted, 'accepted', clone_id=clone_id)
        return EP.EnvHandle(clone_id, 'clone', {'root': manifest['root'], 'work': manifest['work']})

    # The record and its readers.

    def _manifest(self, clone_id):
        path = self.clones / str(clone_id) / MANIFEST
        try:
            return json.loads(path.read_text())
        except FileNotFoundError:
            return None

    def _write(self, manifest):
        root = Path(manifest['root'])
        temporary = root / ('.%s.%d.tmp' % (MANIFEST, os.getpid()))
        temporary.write_text(json.dumps(manifest, indent=1, sort_keys=True))
        os.replace(temporary, root / MANIFEST)

    def handle(self, clone_id):
        manifest = self._manifest(clone_id)
        return EP.EnvHandle(clone_id, 'clone', {'root': manifest['root'], 'work': manifest['work']} if manifest else {})

    def clone_of(self, dispatch_id):
        """The handle of the live clone a dispatch uses, or None."""
        try:
            manifest, _ = find(self.clones, dispatch_id)
        except Refused:
            return None
        return self.handle(manifest['clone_id'])

    @staticmethod
    def entrances(root, user):
        """Every entrance `enter` recorded for one user of the clone at `root`."""
        found = []
        for path in sorted((Path(root) / ENTERED).glob(Path(user['scratch']).name + '.*.json')):
            try:
                found.append(json.loads(path.read_text()))
            except (OSError, ValueError):
                found.append({'unreadable': str(path.name)})
        return found

    def user_state(self, user, root=None):
        """Whether one user of a clone has ended: its record is conclusive and the kernel says now that its
        process is gone and its group empty. A user entered on this host during this boot has ended only
        when its group is known, is the group each of its entrances ran in, and is empty, and every
        entered process is gone: an unknown group fails closed."""
        record = self.dispatches.record(user['dispatch_id']) or {}
        group = user.get('group')
        seen = self.C.retirement(group, record.get('process'))
        boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        here = [e for e in self.entrances(root, user) if e.get('boot_id') in (boot, None)] if root else []
        cgroup = group.get('cgroup') if isinstance(group, dict) else None
        unknown = bool(here) and (not cgroup or any(e.get('cgroup') != cgroup for e in here))
        entered_alive = any(self.C.alive(e) for e in here)
        ended = (record.get('state') in ENDED and seen['terminated'] and seen['cleaned'] and not entered_alive
                 and not unknown)
        return {'dispatch_id': user['dispatch_id'], 'role': user['role'], 'state': record.get('state'),
                'ended': ended, 'entrances': len(here), 'group_unknown': unknown, 'entered_alive': entered_alive,
                'observation': seen}

    def _pins_held(self, clone_id):
        held = []
        for cache in sorted(self.caches.glob('*.git')):
            out = _git('-C', cache, 'for-each-ref', '--format=%(refname) %(objectname)', PIN_PREFIX + clone_id,
                       check=False).stdout.split()
            if out:
                held.append({'cache': str(cache), 'ref': out[0], 'commit': out[1]})
        return held

    # The EnvProvisioner surface (env_provision): liveness is observed from the file system and Git.

    def _is_live(self, handle):
        return (self.clones / handle.env_id).exists() or bool(self._pins_held(handle.env_id))

    def _observe(self, handle):
        manifest = self._manifest(handle.env_id) or {}
        work = manifest.get('work')
        head = _git('-C', work, 'rev-parse', 'HEAD', check=False).stdout.strip() if work else None
        return {'clone_id': handle.env_id, 'commit': manifest.get('commit'), 'tree': manifest.get('tree'), 'head': head,
                'attachments': manifest.get('attachments'), 'pins': self._pins_held(handle.env_id),
                'ancestors': manifest.get('ancestors'),
                'users': [self.user_state(u, manifest.get('root')) for u in manifest.get('users') or []]}

    def _paths(self, handle):
        manifest = self._manifest(handle.env_id)
        if manifest is None:
            return dict(handle.paths)
        return {'root': manifest['root'], 'work': manifest['work'],
                'scratch': {u['dispatch_id']: u['scratch'] for u in manifest['users']}}

    def _seed(self, handle, fixtures):
        raise Refused('invalid_input:seed', "a clone's content is its accepted commit")

    def _teardown(self, handle):
        """Retire a clone: once every worker and consumer has ended, remove it and release its pins.
        Idempotent; a clone still in use is refused clone_in_use and keeps its pins. With no ledger the
        unique work probe and the keep step run by themselves first (_standalone), and a clone that holds
        work they cannot keep is refused as space_deferred and stays, with its pins. With a space ledger
        (VELDO-0303) the removal is Signal's: clone_in_use stays first and unchanged, a thing a safety
        rule keeps is refused as space_deferred with the rule's name, and the pins are released only
        after the work tree's removal outcome is written."""
        manifest = self._manifest(handle.env_id)
        if manifest is None:
            return
        users = [self.user_state(u, manifest['root']) for u in manifest['users']]
        live = sorted(u['dispatch_id'] for u in users if not u['ended'])
        if live:
            self._event('retire', manifest, 'refused', refusal='clone_in_use', clone_id=handle.env_id, users=users)
            raise Refused('clone_in_use', ', '.join(live))
        root = Path(manifest['root'])
        if self.space is not None:
            # VELDO-0303: every user has ended, as the kernel says: run finished, through Signal.
            whole, released = self._through_space(root, manifest['work'], manifest['pins'])
            if whole['state'] not in SPACE_ENDED:
                refusal = space_refusal(whole)
                self._event('retire', manifest, 'refused', refusal=refusal, clone_id=handle.env_id, users=users,
                            space=whole, released=released)
                raise Refused(refusal, str(root))
            self._event('retire', manifest, 'retired', clone_id=handle.env_id, users=users, released=released)
            return
        # No ledger: the unique work probe and the keep step by themselves, before any delete. A build whose
        # result was refused leaves its commits and files only here, so nothing goes that the look did not
        # answer for: the commits are first read back from the bound repository's kept refs.
        try:
            main = self.store.bound_repository(self.conn, manifest['domain'], manifest['repository'])
        except Exception:  # noqa: BLE001 - a repository that cannot be named keeps the clone
            main = None
        looked, released = self._standalone(root, manifest['work'], manifest['pins'], main, manifest.get('unit'))
        stays = [entry for entry in looked if entry['state'] not in SPACE_SAFE] or (
            [{'path': str(root), 'state': None, 'deferral': 'remove_refused', 'said': 'the folder is still there'}]
            if not space_absent(root) else [])
        if stays:
            refusal = space_refusal(stays[0])
            self._event('retire', manifest, 'refused', refusal=refusal, clone_id=handle.env_id, users=users,
                        space=stays, released=released)
            raise Refused(refusal, '%s: %s' % (stays[0]['path'], stays[0].get('said')))
        self._event('retire', manifest, 'retired', clone_id=handle.env_id, users=users, released=released,
                    kept=looked[0].get('refs') or {})

    def _standalone(self, root, work, pins, main, ticket):
        """Without a ledger there is no item-naming event: keep the whole clone and its pins."""
        looked = [{'path': str(path), 'item': None, 'state': None, 'deferral': 'not_in_ledger',
                   'said': 'removal requires a recorded owner and item'} for path in (work, root)]
        return looked, []

    def _through_space(self, root, work, pins, confirm=False):
        """VELDO-0303: send run finished through Signal for the clone's items (its work tree, its scratch
        folder and its root, whatever the ledger records at or beneath the root; VELDO-0308: exactly
        those, named at their versions, and nothing else of the run that owns them) and release the pins
        only after the work tree's removal outcome is written, or when no live item records it and
        the kernel says nothing is at its path: while the work tree is on disk its objects are the
        caches', and a pin is what keeps them. Returns (the root's entry, the refs released). Nothing
        is deleted here."""
        found = space_signal(self.space, 'run_finished', [root, work], 'clone.' + ('provision' if confirm else 'teardown'),
                             ended=True, confirm=confirm)
        whole, tree = found[os.path.normpath(str(root))], found[os.path.normpath(str(work))]
        released = []
        if tree['state'] in SPACE_ENDED:
            for pin in pins:
                if not hasattr(self, '_ref_items'):
                    self._ref_items = {}
                self._ref_items[(str(pin['cache']), pin['ref'])] = tree.get('item')
                answer = self._release(Path(pin['cache']), pin['ref'])
                if answer['ok']:
                    released.append(pin['ref'])
        return whole, released

    def retire(self, handle):
        return self.teardown(handle if isinstance(handle, EP.EnvHandle) else self.handle(handle))

    # Observability.

    def _event(self, operation, subject, outcome, refusal=None, **extra):
        subject = subject or {}
        # The accepted source carries the identity record; a clone's manifest keeps only its id.
        identity = subject.get('identity')
        event = {'schema': SCHEMA, 'operation': operation, 'domain': self.domain,
                 'repository': subject.get('repository'), 'unit': subject.get('unit'),
                 'dispatch_id': subject.get('dispatch_id'), 'outcome': outcome,
                 'identity': identity.get('id') if isinstance(identity, dict) else identity,
                 'accepted': {'commit': subject.get('commit'), 'tree': subject.get('tree'),
                              'attachments': [{f: a.get(f) for f in ('name', 'repository', 'commit')}
                                              for a in subject.get('attachments') or []]}}
        if refusal is not None:
            event.update(refusal=refusal, taxonomy=taxonomy(refusal))
        event.update(extra)
        self.counts['refused' if outcome == 'refused' else 'accepted'] += 1
        self.observations.append(event)

    def metrics(self):
        """Accepted and refused operations, and the pending work: every live clone with its users and pins."""
        pending = []
        for path in sorted(self.clones.glob('*/' + MANIFEST)):
            manifest = json.loads(path.read_text())
            pending.append({'clone_id': manifest['clone_id'], 'unit': manifest['unit'],
                            'users': [u['dispatch_id'] for u in manifest['users']], 'pins': len(manifest['pins'])})
        return dict(self.counts, pending=pending, identities=GI.metrics(self.observations))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if len(argv) < 4 or argv[0] != 'enter' or argv[2] != '--':
            raise Refused('invalid_input:usage', 'enter <clone root> -- <engine argv>')
        enter(argv[1], argv[3:])
    except Refused as error:
        # The refusal's name only: no path, nothing the engine would have seen.
        sys.stderr.write('clone refused: %s\n' % error.code)
        return EXIT_REFUSED
    except OSError:
        sys.stderr.write('clone refused: unavailable_service:enter\n')
        return EXIT_REFUSED
    return EXIT_REFUSED


if __name__ == '__main__':
    sys.exit(main())
