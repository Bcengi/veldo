#!/usr/bin/env python3
"""The event spool, and what a git hook records through it (VELDO-0311, design 4.5, 4.6, 6.9, 8.4, 8.5).

SESSION NOTIFICATIONS (VELDO-0314). SessionStart and SessionEnd carry the session, the working
folder (cwd), client pid and kernel start ticks: the subject is exactly the Ledger's event subject
(VELDO-0323, as VELDO-0335 extended it). submit persists before any key lookup or socket call. A start
asks Local.session for a declaration derived from the authority's scratch pattern, then sends the
declaration and event as space-observer. An end sends only the event. Neither calls Signal or a
remover. Session events reach the Ledger only from this spool, through VELDO-0323's consumer.
A released entry holds the paths alone, as the Ledger takes them; who released is the emitter's,
never the subject's. Installation in
client accounts remains VELDO-0329's. Invalid notifications are never treated as removal permission.

NO NOTIFICATION IS DROPPED WITHOUT A RECORD. The client's folder is resolved first (resolved: links
followed, a trailing slash and dot segments gone), so a folder named through a link is the folder it
leads to. A notification that is still no entry (a session id that is no path component, no folder,
a client process the kernel does not show) is written whole under refused/ with why (refuse). A
spool folder that is not this account's alone is refused and noted beside it, and the entry is
spooled under the fallback state root (the user's XDG state folder, veldo). When neither root takes
it, one line with the notification and why is appended to <state root>/space-session.unspooled.jsonl
(unspooled). A deadline that fires while an entry is read (TimeoutError, the hook's timer) ends the
replay: the entry stays whole in the spool. A write a crash cut short (a .partial file of this
account's, PARTIAL_SECONDS old) is set aside under refused/ by the next replay, under its lock.

WHAT THIS MODULE IS. A worktree added with plain git, a branch switched in it and a trunk moved by hand
all happen outside Veldo. Two git hooks (engine/hooks/post-checkout and reference-transaction) start the
CLI, and the CLI calls this module. It writes down what the hook saw as one entry, hands it to the
authority, and returns. It removes nothing of anybody's: no worktree, no folder, no ref, no branch. The
only git commands it runs are the four that read (READS), each in the whole forms _reads names and in
no other form. Whatever goes wrong, the git command it rides
on ends as it would without it.

AN ENTRY is what a hook saw, {schema, id, type, subject, emitter, at, tries}:

  worktree_added    post-checkout with the null commit as the previous HEAD, in a linked worktree:
                    repository, path, branch (None when detached) and start, the commit checked out.
  branch_switched   post-checkout with a real previous HEAD and the branch flag, in a linked worktree:
                    the same four fields, for the branch and commit the worktree is on now.
  ref_changed       reference-transaction in its committed state, for the declared trunk or a declared
                    landing ref: repository, ref, old and new. The old commit is the hook's word and
                    git is never asked to confirm it, so the event that is signed carries old as null.

THE TRUNK IS NEVER GUESSED. The hook names the trunk only from the repository's git configuration
(veldo.space.trunk, which VELDO-0329 sets from the declared land trunk). With none it writes no entry for
any branch, and the repository is noted once under undeclared/ with why. The authority judges again: at
a replay a ref_changed entry is sent only when its ref is the trunk the work configuration's land entry
declares for that repository (about's trunk) or a landing ref the space file declares; any other ref is
"nothing", so a stale or wrong git configuration cannot make a branch a trunk.

The repository's own checkout is never an item (design 0.1), so a checkout there is no entry. A checkout
git makes while a rebase is in progress is no entry: the worktree's branch is the same when it ends. A
ref under refs/veldo/ is no entry (design 0.2: the hook sends nothing for a kept ref).

AN ENTRY IS A HINT, NEVER A FACT. The spool is a folder of files, and this account is the trust boundary:
the folder is made 0700; a folder or an entry file that is another account's, or that group or others
can write, is refused and never replayed (a file is set aside in refused/ with why; a folder is left as
it is and noted beside it, <state root>/space-spool.refused.json). The hook's side sends only to a socket
the kernel says this account serves. And before anything is signed the replay reads the facts from git
itself (read_git): the worktree is in that repository's own list at that path, with the branch and the
commit it is on now; the commit of a ref change is on the named ref now. It records only what it read.
What git does not confirm is "nothing". No key authenticates an entry: a key this account can read adds
nothing on a single-user host. Whoever records an entry after this module (VELDO-0323's consumer) has
the same duty.

THE SPOOL (design 4.6) is <state root>/space-spool: one file per entry, written whole under a temporary
name, synced and renamed into place, named by the time it was written, so the files in name order are
the entries in the order the hooks ran. Every entry is written there first and delivered from there, so
there is no moment in which an entry exists only in a process. With the authority not reachable the
file stays. It is replayed, oldest first, by the next call that reaches the authority (deliver, and the
CLI's replay verb) and by start, which the service calls before reconcile.

WHAT BECOMES OF AN ENTRY at a replay:

  recorded   the authority wrote what the entry says. The file is unlinked, and only then.
  nothing    there is nothing to write: the repository is neither bound nor plain, a switch was seen
             in a worktree no item records (reconcile adopts it), the ref is not the declared trunk or a
             declared landing ref, or git does not confirm what the entry says. One line with the entry
             and why is appended to observations.jsonl, and only then is the file unlinked.
  refused    the Ledger refused it by a name that will not change (a path outside every known root, a
             protected path, a locator through a link), or a live item of another repository is at the
             path (it is never given this worktree's branch). The entry and the answer are written to
             refused/ under the same name, and the file leaves the spool. Nothing drops it silently.
  waits      the authority answered but cannot take it yet: the Ledger has no such command (the event
             command is VELDO-0323's), the observer's key is missing or not enrolled, the packet was
             judged late. The file stays, its count of tries goes up by one, and later entries about the
             same worktree or the same ref stay behind it, so the order of one thing's entries is kept.
  not reachable  the replay stops there. Every file from that one on stays.
  out of time    a replay has an overall deadline (HOOK_SECONDS for a hook's call, REPLAY_SECONDS for the
             replay verb and start). Past it the replay stops between two entries; the rest stay. A
             read of git inside an entry is given only the time that is left, and when none is left
             the entry stays as it is, with the rest.

THE COMMANDS ARE THE LEDGER'S, SIGNED AS space-observer. This module verifies no signature and judges no
command: each one is a packet {command, signature} the Ledger's own accept takes, verifies and applies
(VELDO-0326). For a worktree added: declare (kind worktree, creator hook, the owner its branch pattern
gives), confirm, and rebranch to the same branch, which records the branch item when it has none. A live
item already at the path (a worktree removed by hand and made again) is given the new branch and start
by rebranch. For a switch: rebranch of the item at the path. For a ref: the event command with type
ref_changed, the repository, the ref, the old and the new commit, and the emitter.

A PACKET IS THE SAME PACKET WHEN IT IS SENT AGAIN. Its command id and nonce are a digest of the entry's
id, the step and the entry's count of tries. A replay after a crash between the answer and the unlink
signs the same packet again, and the Ledger answers it with the original answer and writes nothing. An
entry that waited is signed with a new nonce, because the Ledger keeps the old one as refused for good.

THE OWNER A BRANCH PATTERN GIVES. The authority's about answers, for a repository and a path, the scope
(the project as the Ledger knows it, or the plain repository), the project's branch patterns, its
declared trunk and landing refs, and the live worktree item at the path in that repository. An item is
found by repository and path, never by path alone: a live item of another repository at the path is
answered as `other`, and the entry is refused. Paths are compared in the Ledger's own canonical form
(control_space.canonical_path). A branch that matches a pattern is owned by the scope and the ticket the
pattern names; other branches and detached worktrees outside a run belong to the scope alone.
A newly detached worktree with a run label belongs to that run. Its station is read from the wrapper
scratch record in this scope, never from the hook. Unknown runs stay spooled without a guessed owner.

HOW LONG A HOOK CAN WAIT. The hook's side gives the authority REACH_SECONDS for each answer, another
call's replay LOCK_SECONDS, and its whole replay HOOK_SECONDS (no answer is waited for past that
deadline); past any of them, the entries stay in the spool and the git command goes on.

THE AUTHORITY is anything with accept(packet) and about(repository, path) that raises Unreachable when it
cannot be reached. Local is the one in the authority's own process, over a Ledger. Remote is the hook's
side of a local socket, <state root>/space-spool/authority.sock, one JSON request per connection; serve_one
is the authority's side; each side asks the kernel who the other is and goes on only when it is this
account: the peer must be this account (the kernel's answer), the answer is sent and the
connection closed, and only then is `after` called with the request and the answer. That is where the
service's event consumer goes (VELDO-0323); nothing called there can delay the git command. Wiring the
socket into the service is that ticket's; until then no authority answers and every entry waits in the
spool.

Standard library only. The Ledger, the store's canonical bytes and the declarations reader are loaded as
siblings, and only by the calls that need them.
"""
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import socket
import stat
import string
import subprocess
import sys
import time
import uuid

SCHEMA = 'veldo.control_space_spool/v1'
SPOOL = 'space-spool'  # under the state root (design 4.6 and section 9)
REFUSED = 'refused'
SOCKET = 'authority.sock'
LOCK = 'lock'
SUFFIX = '.json'
SESSION_TYPES = ('session_started', 'session_ended')
TYPES = ('worktree_added', 'branch_switched', 'ref_changed') + SESSION_TYPES + ('released',)
FIELDS = {'worktree_added': ('repository', 'path', 'branch', 'start'),
          'branch_switched': ('repository', 'path', 'branch', 'start'),
          'ref_changed': ('repository', 'ref', 'old', 'new'),
          'session_started': ('session', 'cwd', 'pid', 'started'),
          'session_ended': ('session', 'cwd', 'pid', 'started'),
          'released': ('paths',)}
HOOKS = ('post-checkout', 'reference-transaction', 'SessionStart', 'SessionEnd', 'event')
# The Ledger's own names (control_space.py); the suite holds them equal.
OBSERVER = 'space-observer'
DECLARE, CONFIRM, REBRANCH, EVENT = 'space_declare', 'space_confirm', 'space_rebranch', 'space_event'
TAKEN = 'space_locator_taken:'
ENDED = ('removed', 'gone')
# A refusal that says "not yet", never "no": the entry stays in the spool.
WAITS = ('space_no_command:', 'space_packet_', 'space_no_key', 'space_no_installation', 'not_authorized',
         'unavailable_service')
KEPT_REFS = 'refs/veldo/'
UNDECLARED = 'undeclared'  # under the spool: one file for each repository whose hook names no trunk
OBSERVATIONS = 'observations.jsonl'  # one line for each entry that came to nothing
FOLDER_REFUSED = SPOOL + '.refused.json'  # beside a spool folder that was refused, with why
OTHER = 'space_path_of_another_repository:'
# The only git commands this module runs: each reads, none writes. Only the whole forms of _reads run.
READS = ('rev-parse', 'symbolic-ref', 'merge-base', 'worktree')
GIT_SECONDS = 5.0     # the longest one read of git is waited for
REBASING = ('rebase-merge', 'rebase-apply')
MAX_BYTES = 1 << 20
REACH_SECONDS = 5.0   # the longest a hook waits for the authority's answer
LOCK_SECONDS = 2.0    # the longest a call waits for another call's replay
HOOK_SECONDS = 5.0    # the longest a hook's whole replay goes on; what is left stays spooled
REPLAY_SECONDS = 60.0  # the same for the replay verb and for start
PARTIAL = '.partial'  # the end of a temporary name (_write)
PARTIAL_SECONDS = 600.0  # a write that has not ended after this long was cut short by a crash
UNSPOOLED = 'space-session.unspooled.jsonl'  # under a state root: notifications no spool took
_LOADED = {}


class Unreachable(Exception):
    """The authority could not be reached, or gave no answer."""


class _Late(Exception):
    """The replay's deadline passed before git could be read: the entry stays as it is."""


class Malformed(Exception):
    """Something that is not an entry."""


class Unsafe(Malformed):
    """A spool folder or file that is not this account's alone: it is refused, never read as an entry."""


class _Waits(Exception):
    def __init__(self, reason):
        Exception.__init__(self, reason)
        self.reason = reason


def _sibling(name):
    if name not in _LOADED:
        spec = importlib.util.spec_from_file_location(
            'veldo_space_spool_' + name, os.path.join(os.path.dirname(os.path.abspath(__file__)), name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _LOADED[name] = module
    return _LOADED[name]


def _text(value):
    return isinstance(value, str) and bool(value)


def _null(commit):
    return _text(commit) and set(commit) == {'0'}


def _hex(commit):
    return _text(commit) and re.fullmatch(r'[0-9a-f]{40,64}', commit) is not None


def canonical(path):
    """A path in the one form the Ledger records and compares it in: the Ledger's own function."""
    return _sibling('control_space').canonical_path(path)


# ---------------------------------------------------------------------------------------------
# Entries: what a hook saw.
# ---------------------------------------------------------------------------------------------

def checked(entry):
    """The entry, when it is one. Raises Malformed."""
    if not isinstance(entry, dict) or entry.get('schema') != SCHEMA or entry.get('type') not in TYPES:
        raise Malformed('not an entry of ' + SCHEMA)
    subject, emitter = entry.get('subject'), entry.get('emitter')
    fields = FIELDS[entry['type']]
    optional = {'run_label'} if entry['type'] == 'worktree_added' else set()
    if not isinstance(subject, dict) or not set(fields) <= set(subject) or set(subject) - set(fields) - optional:
        raise Malformed('the subject of %s holds %s' % (entry['type'], ', '.join(fields)))
    if 'run_label' in subject and not _text(subject['run_label']):
        raise Malformed('subject.run_label is a name')
    for field in fields:
        if field in ('pid', 'started'):
            if type(subject[field]) is not int or subject[field] <= 0:
                raise Malformed('subject.%s is a positive integer' % field)
            continue
        if field == 'paths':
            if not isinstance(subject[field], list) or not subject[field]:
                raise Malformed('released names paths')
            for path in subject[field]:
                plain_path(path)
            continue
        if not _text(subject[field]) and not (field in ('branch', 'old') and subject[field] is None):
            raise Malformed('subject.%s is a name' % field)
    if entry['type'] in SESSION_TYPES:
        plain_path(subject['cwd'])
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,199}', subject['session']):
            raise Malformed('session is one safe path component')
    for field in ('repository', 'path'):
        if field in subject and not os.path.isabs(subject[field]):
            raise Malformed('subject.%s is an absolute path' % field)
    if (not isinstance(emitter, dict) or set(emitter) != {'hook', 'host'} or emitter['hook'] not in HOOKS
            or not _text(emitter['host'])):
        raise Malformed('the emitter is a hook and the host it ran on')
    if not _text(entry.get('id')) or not re.fullmatch(r'[0-9a-f]{32}', entry['id']):
        raise Malformed('an entry has an id of its own')
    if type(entry.get('tries')) is not int or entry['tries'] < 0 or not isinstance(entry.get('at'), (int, float)):
        raise Malformed('an entry has the time it was seen at and its count of tries')
    return entry


def entry(kind, subject, hook, host, at=None):
    """One entry for what `hook` saw on `host`."""
    return checked({'schema': SCHEMA, 'id': uuid.uuid4().hex, 'type': kind, 'subject': dict(subject),
                    'emitter': {'hook': hook, 'host': host}, 'at': time.time() if at is None else at,
                    'tries': 0})


def plain_path(path):
    """Never turn a link or a dot segment into a different locator."""
    if (not _text(path) or not os.path.isabs(path) or '..' in path.split(os.sep)
            or os.path.normpath(path) != path or os.path.realpath(path) != path):
        raise Malformed('path must be absolute, normalized and without links')
    return path


def resolved(path):
    """Where a folder a client names is: every link followed, a trailing slash and dot segments gone.
    What is not an absolute path is returned as it is, for checked to refuse."""
    return os.path.realpath(path) if _text(path) and os.path.isabs(path) else path


def _inside(path, root):
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def session_entry(kind, session, cwd, pid, started, host):
    one = entry(kind, {'session': session, 'cwd': cwd,
                       'pid': pid, 'started': started},
                'SessionStart' if kind == 'session_started' else 'SessionEnd', host)
    # Duplicate delivery of the same client notification uses the same command identity.
    one['id'] = hashlib.sha256(json.dumps([kind, one['subject'], host], sort_keys=True).encode()).hexdigest()[:32]
    return one


def repository_of(common_dir):
    """The repository a git common directory belongs to: the folder that holds .git, or the directory
    itself for a bare repository."""
    common = os.path.normpath(common_dir)
    return os.path.dirname(common) if os.path.basename(common) == '.git' else common


def checkout(previous, new, flag, worktree, git_dir, common_dir, branch, host, at=None, run_label=None):
    """The entry for one post-checkout call, or None when there is nothing to record. `worktree` is the
    working tree git ran the hook in, `git_dir` and `common_dir` its git directory and the repository's
    common directory, `branch` the short name of the branch HEAD is on (empty when detached)."""
    if str(flag) != '1' or not all(_text(value) for value in (previous, new, worktree, git_dir, common_dir)):
        return None  # a file checkout, or a call that names nothing
    if _null(new) or os.path.normpath(git_dir) == os.path.normpath(common_dir):
        return None  # the repository's own checkout is never an item (design 0.1)
    if any(os.path.lexists(os.path.join(git_dir, name)) for name in REBASING):
        return None  # a rebase in progress: the worktree's branch is the same when it ends
    kind = 'worktree_added' if _null(previous) else 'branch_switched'
    subject = {'repository': repository_of(common_dir), 'path': os.path.normpath(worktree),
               'branch': branch or None, 'start': new}
    if kind == 'worktree_added' and not branch and _text(run_label):
        subject['run_label'] = run_label
    return entry(kind, subject, 'post-checkout', host, at)


def full_ref(name):
    return name if name.startswith('refs/') else 'refs/heads/' + name


def watched(repository, trunk=None):
    """The refs whose change is recorded for `repository`: the trunk the hook was given, and the landing
    refs its space file declares. With no trunk given none is taken: the trunk is never guessed. A space
    file that cannot be read declares none here."""
    refs = [full_ref(trunk)] if _text(trunk) else []
    try:
        import io
        config = _sibling('control_space_config')
        project = config.read_project(repository, _sibling('yamlish').read, config=config.off(),
                                      stream=io.StringIO())
        refs += [full_ref(name) for name in project['landing_refs']]
    except Exception:
        pass
    return refs


def ref_changes(lines, common_dir, host, trunk=None, at=None):
    """The entries for one committed reference transaction: one for each changed trunk or declared
    landing ref. `lines` are git's own, "<old> <new> <ref>". A kept ref gives none, and with no trunk
    given no branch is taken for one."""
    repository, refs, out = repository_of(common_dir), None, []
    for line in lines:
        parts = line.split()
        if len(parts) != 3 or parts[2].startswith(KEPT_REFS) or parts[0] == parts[1]:
            continue
        if refs is None:
            refs = watched(repository, trunk)
        if parts[2] in refs:
            out.append(entry('ref_changed', {'repository': repository, 'ref': parts[2], 'old': parts[0],
                                             'new': parts[1]}, 'reference-transaction', host, at))
    return out


# ---------------------------------------------------------------------------------------------
# The spool.
# ---------------------------------------------------------------------------------------------

def spool_folder(state_root):
    if not _text(state_root) or not os.path.isabs(state_root):
        raise Malformed('the state root is an absolute path')
    return os.path.join(os.path.normpath(state_root), SPOOL)


def _unsafe(status, folder):
    """Why what `status` describes is not this account's alone, or None. `folder`: a folder is wanted,
    else a plain file. A link is neither."""
    if not (stat.S_ISDIR if folder else stat.S_ISREG)(status.st_mode):
        return 'not a folder' if folder else 'not a plain file'
    if status.st_uid != os.getuid():
        return 'owned by another account'
    if status.st_mode & 0o022:
        return 'writable by group or others'
    return None


def _folder(folder):
    """The spool folder, made 0700 when it is not there. A link, a folder of another account and one
    group or others can write are refused (Unsafe): nothing is written into one or replayed from one."""
    try:
        status = os.lstat(folder)
    except FileNotFoundError:
        os.makedirs(folder, mode=0o700, exist_ok=True)
        status = os.lstat(folder)
    why = _unsafe(status, True)
    if why is not None:
        raise Unsafe('the spool folder is %s: %s' % (why, folder))
    return folder


def note_refused_folder(state_root, why):
    """One file beside a spool folder that was refused, saying why, written once. The folder itself is
    left exactly as it is: it may not be this account's to touch."""
    try:
        root = os.path.normpath(state_root)
        path = os.path.join(root, FOLDER_REFUSED)
        status = os.lstat(root)
        if stat.S_ISDIR(status.st_mode) and status.st_uid == os.getuid() and not os.path.lexists(path):
            _write(path, {'refused': why, 'folder': os.path.join(root, SPOOL), 'at': time.time()})
    except (OSError, TypeError, ValueError):
        pass


def _write(path, document):
    """One file, written whole under a temporary name, synced, and renamed into place."""
    temporary = '%s.%d.%s.partial' % (path, os.getpid(), uuid.uuid4().hex[:8])
    data = (json.dumps(document, sort_keys=True) + '\n').encode()
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        written = os.write(descriptor, data)
        if written != len(data):
            raise OSError('a short write of ' + temporary)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.rename(temporary, path)
    descriptor = os.open(os.path.dirname(path), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def put(folder, one):
    """Write one entry into the spool and return its file's name."""
    checked(one)
    name = '%020d-%s%s' % (time.time_ns(), one['id'], SUFFIX)
    _write(os.path.join(_folder(folder), name), one)
    return name


def pending(folder):
    """The names of the spooled entries, oldest first."""
    try:
        names = os.listdir(folder)
    except FileNotFoundError:
        return []
    return sorted(name for name in names if name.endswith(SUFFIX))


def read(folder, name):
    """One spooled entry. The file is opened without following a link, and it is read only when it is a
    plain file of this account's that group and others cannot write (else Unsafe)."""
    path = os.path.join(folder, name)
    if os.path.islink(path):
        raise Unsafe('the spooled file is a link')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        why = _unsafe(os.fstat(descriptor), False)
        if why is not None:
            raise Unsafe('the spooled file is ' + why)
        data = b''
        while len(data) <= MAX_BYTES:
            chunk = os.read(descriptor, MAX_BYTES + 1 - len(data))
            if not chunk:
                break
            data += chunk
    finally:
        os.close(descriptor)
    if len(data) > MAX_BYTES:
        raise Malformed('an entry of more than %d bytes' % MAX_BYTES)
    try:
        return checked(json.loads(data.decode()))
    except ValueError as error:
        raise Malformed(str(error))


def refused(folder):
    """The names under refused/: entries the Ledger refused for good, each with the answer."""
    return pending(os.path.join(folder, REFUSED))


def observe(folder, document):
    """Append one line to the spool's observations: an entry that came to nothing, whole, with why."""
    data = (json.dumps(dict(document, at=time.time()), sort_keys=True) + '\n').encode()
    descriptor = os.open(os.path.join(_folder(folder), OBSERVATIONS),
                         os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        if os.write(descriptor, data) != len(data):
            raise OSError('a short write of the observations')
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def observations(folder):
    """The spool's observations, oldest first."""
    try:
        with open(os.path.join(folder, OBSERVATIONS), 'rb') as handle:
            lines = handle.read().decode(errors='replace').splitlines()
    except FileNotFoundError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            out.append({'unread': line})
    return out


def note_undeclared(folder, repository, ref):
    """Record, once for a repository, that its hook names no trunk and so sent nothing for a changed
    branch. Returns the file's name."""
    name = hashlib.sha256(repository.encode()).hexdigest()[:32] + SUFFIX
    aside = _folder(os.path.join(_folder(folder), UNDECLARED))
    if not os.path.lexists(os.path.join(aside, name)):
        _write(os.path.join(aside, name), {'reason': 'trunk_undeclared', 'repository': repository, 'ref': ref,
                                           'at': time.time()})
    return name


def undeclared(folder):
    """The names under undeclared/: one for each repository whose hook names no trunk."""
    return pending(os.path.join(folder, UNDECLARED))


def _set_aside(folder, name, document):
    """Move an entry out of the spool into refused/, with why. It is written there before it leaves."""
    aside = _folder(os.path.join(folder, REFUSED))
    _write(os.path.join(aside, name), document)
    os.unlink(os.path.join(folder, name))


def refuse(state_root, notification, why):
    """A notification that is no entry is not dropped: it is written whole under refused/, with why.
    Returns the file's name."""
    folder = spool_folder(state_root)
    data = json.dumps(notification, sort_keys=True, default=repr)
    name = '%020d-%s%s' % (time.time_ns(), hashlib.sha256(data.encode()).hexdigest()[:32], SUFFIX)
    aside = _folder(os.path.join(_folder(folder), REFUSED))
    _write(os.path.join(aside, name), {'notification': json.loads(data),
                                       'refused': {'outcome': 'refused', 'reason': why}})
    return name


def unspooled(roots, document):
    """The last record of a notification no spool took: one line appended to UNSPOOLED under the first
    of `roots` that takes it. Returns the file's path. Raises when none does."""
    data = (json.dumps(dict(document, at=time.time()), sort_keys=True, default=repr) + '\n').encode()
    last = Malformed('no state root')
    for root in roots:
        if not _text(root) or not os.path.isabs(root):
            continue
        try:
            os.makedirs(root, mode=0o700, exist_ok=True)
            path = os.path.join(os.path.normpath(root), UNSPOOLED)
            descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            try:
                if os.write(descriptor, data) != len(data):
                    raise OSError('a short write of ' + path)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return path
        except OSError as error:
            last = error
    raise last


def _sweep(folder, now=None):
    """Set aside, under refused/ with why, each write a crash cut short: a .partial file of this
    account's that is PARTIAL_SECONDS old. Called under the replay's lock. Returns their names."""
    now = time.time() if now is None else now
    out = []
    for name in sorted(os.listdir(folder)):
        if not name.endswith(PARTIAL):
            continue
        try:
            status = os.lstat(os.path.join(folder, name))
            if _unsafe(status, False) is None and now - status.st_mtime >= PARTIAL_SECONDS:
                _set_aside_raw(folder, name, 'a write that did not finish')
                out.append(name)
        except TimeoutError:
            raise
        except OSError:
            continue
    return out


def _locked(folder, seconds):
    """The spool's lock, held by one replay at a time, or None when another call still holds it after
    `seconds`."""
    descriptor = os.open(os.path.join(_folder(folder), LOCK), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    deadline = time.monotonic() + seconds
    while True:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return descriptor
        except OSError:
            if time.monotonic() >= deadline:
                os.close(descriptor)
                return None
            time.sleep(0.02)


# ---------------------------------------------------------------------------------------------
# From an entry to the Ledger's commands.
# ---------------------------------------------------------------------------------------------

def ticket_of(branch, patterns):
    """The ticket a branch name gives under the project's branch patterns, or None. Each field of a
    pattern is one segment of the name."""
    if not _text(branch):
        return None
    for pattern in patterns or ():
        try:
            parts = list(string.Formatter().parse(pattern))
        except ValueError:
            continue
        regex = ''.join(re.escape(literal) + ('' if field is None else '(?P<%s>[^/]+)' % field)
                        for literal, field, _spec, _conversion in parts)
        try:
            match = re.fullmatch(regex, branch)
        except re.error:
            continue
        if match and match.groupdict().get('ticket'):
            return match.group('ticket')
    return None


def owner_of(branch, about, run_label=None):
    """The owner the branch pattern gives: the scope, and the ticket when the branch names one."""
    owner = {'scope': dict(about['scope'])}
    if not branch and run_label:
        run = (about.get('runs') or {}).get(run_label)
        if not isinstance(run, dict):
            raise _Waits('space_run_unknown:' + run_label)
        owner['run'] = dict(run)
        return owner
    ticket = ticket_of(branch, about.get('patterns'))
    if ticket:
        owner['ticket'] = ticket
    return owner


def waits(reason):
    return _text(reason) and reason.startswith(WAITS)


def _key(one):
    subject = one['subject']
    if one['type'] in SESSION_TYPES:
        return ('session', one['emitter']['host'], subject['session'])
    if one['type'] == 'released':
        return ('released', tuple(subject['paths']))
    return ('ref', subject['repository'], subject['ref']) if one['type'] == 'ref_changed' else (
        'path', subject['path'])


# ---------------------------------------------------------------------------------------------
# What git itself says: an entry is a hint, and only what is read here is recorded.
# ---------------------------------------------------------------------------------------------

def _reads(argv):
    """Whether argv is, whole, one of the five forms this module runs. Each only reads. A command is
    never allowed by its first word: any other form of the same command, any other command and any
    option before the command (-c, -C, --git-dir) is not one of them."""
    revision, symbolic, ancestry, worktree = READS
    return (argv == (revision, '--absolute-git-dir')
            or (len(argv) == 5 and argv[:4] == (revision, '--verify', '--quiet', '--end-of-options')
                and _text(argv[4]) and argv[4].endswith('^{commit}'))
            or argv == (symbolic, '-q', '--short', 'HEAD')
            or (len(argv) == 4 and argv[:2] == (ancestry, '--is-ancestor') and bool(_hex(argv[2]))
                and bool(_hex(argv[3])))
            or argv == (worktree, 'list', '--porcelain'))


def _git(where, *argv, until=None, clock=time.monotonic):
    """(status, output) of one git command that only reads, run in `where` through the one Git boundary
    (git_process.py, its isolated profile: no inherited GIT_ variable selects a repository); (None, '')
    when it is not one of the whole forms of _reads or could not be run. `until`, when given, is the
    replay's deadline on `clock`: the read is given only the time that is left, and raises _Late when
    none is left or the read did not end in it."""
    if not _reads(argv):
        return None, ''
    seconds = GIT_SECONDS
    if until is not None:
        seconds = min(GIT_SECONDS, until - clock())
        if seconds <= 0:
            raise _Late('out of time')
    _git_process = _sibling('git_process')
    try:
        done = _git_process.run(['git', '-C', where] + list(argv), env=dict(os.environ, LC_ALL='C'),
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                timeout=seconds)
    except subprocess.TimeoutExpired:
        if seconds < GIT_SECONDS:
            raise _Late('out of time')  # the deadline cut the read short: nothing is concluded from it
        return None, ''
    except (OSError, ValueError, subprocess.SubprocessError):
        return None, ''
    return done.returncode, done.stdout.decode(errors='replace').strip()


def _commit(where, name, **time_left):
    """The commit `name` is at in `where`, or None."""
    status, out = _git(where, 'rev-parse', '--verify', '--quiet', '--end-of-options', name + '^{commit}',
                       **time_left)
    return out if status == 0 and _hex(out) else None


def _holds(where, commit, tip, **time_left):
    """Whether `tip` is `commit` or has it as an ancestor: True, False, or None when git did not say."""
    if commit == tip:
        return True
    status, _out = _git(where, 'merge-base', '--is-ancestor', commit, tip, **time_left)
    return True if status == 0 else False if status == 1 else None


def read_git(one, until=None, clock=time.monotonic):
    """What git itself says of what an entry names, read now: (subject, None), or (None, why) when git
    does not confirm it. For a ref change the subject is the entry's repository, ref and new commit when
    that commit is on the named ref, and old as None: git is not asked for the old commit, and what was
    not read is never passed on. For a worktree it is the repository, the path, the branch the worktree is on now (None when
    detached) and its start: the entry's commit when the worktree is still on the entry's branch and
    that commit is in its history, else the commit it is at now. Raises _Waits while a rebase is in
    progress in the worktree: its branch is read when the rebase has ended. `until` is the replay's
    deadline on `clock`: every read of git is given only the time that is left (_Late when none is)."""
    subject = one['subject']
    time_left = {'until': until, 'clock': clock}
    repository = subject['repository']
    if one['type'] == 'ref_changed':
        if not subject['ref'].startswith('refs/') or not _hex(subject['new']):
            return None, 'not_a_ref_and_a_commit'
        tip = _commit(repository, subject['ref'], **time_left)
        held = None if tip is None else _holds(repository, subject['new'], tip, **time_left)
        if held is not True:
            return None, 'commit_not_on_ref' if held is False else 'ref_unread'
        return dict(subject, old=None), None  # the old commit was not read from git: never passed on
    path = subject['path']
    status, out = _git(repository, 'worktree', 'list', '--porcelain', **time_left)
    if status != 0:
        return None, 'repository_unread'
    listed = [canonical(line[len('worktree '):]) for line in out.splitlines() if line.startswith('worktree ')]
    if canonical(path) not in listed[1:] or not os.path.isdir(path):
        return None, 'worktree_not_in_that_repository'
    status, git_dir = _git(path, 'rev-parse', '--absolute-git-dir', **time_left)
    head = _commit(path, 'HEAD', **time_left)
    if status != 0 or not git_dir or head is None:
        return None, 'worktree_unread'
    if [name for name in REBASING if os.path.lexists(os.path.join(git_dir, name))]:
        raise _Waits('worktree_rebasing')
    status, branch = _git(path, 'symbolic-ref', '-q', '--short', 'HEAD', **time_left)
    if status not in (0, 1):
        return None, 'worktree_unread'
    branch = branch if status == 0 and branch else None
    same = (branch == subject['branch'] and _hex(subject['start'])
            and _holds(path, subject['start'], head, **time_left) is True)
    return {'repository': repository, 'path': path, 'branch': branch,
            'start': subject['start'] if same else head}, None


def send(one, authority, sign, facts=None, until=None, clock=time.monotonic):
    """Hand one entry to the authority as the Ledger's commands, each signed by `sign(operation,
    parameters, command_id, nonce)`. Returns {outcome, reason, answers}: recorded, nothing or refused.
    Raises Unreachable when the authority is not reachable and _Waits when it cannot take the entry yet.
    `facts(one)` reads what git says of the entry (default: read_git); only what it answers is signed.
    `until` is a replay's deadline on `clock`: read_git is given it, and raises _Late when it has passed."""
    kind, subject, answers = one['type'], one['subject'], []
    facts = facts or (lambda one: read_git(one, until=until, clock=clock))

    def ask(step, operation, parameters):
        token = hashlib.sha256(('%s:%s:%d' % (one['id'], step, one['tries'])).encode()).hexdigest()
        answer = authority.accept(sign(operation, parameters, 'space:hook:' + token[:32], token))
        if not isinstance(answer, dict) or type(answer.get('ok')) is not bool:
            raise Unreachable('the authority gave no answer')
        if not answer['ok'] and waits(answer.get('reason')):
            raise _Waits(answer['reason'])
        answers.append({'step': step, 'ok': answer['ok'], 'reason': answer.get('reason'),
                        'item': answer.get('item')})
        return answer

    def result(outcome, reason=None):
        return {'outcome': outcome, 'reason': reason, 'answers': answers}

    if kind in SESSION_TYPES or kind == 'released':
        checked(one)
        if kind == 'session_started':
            declaration = authority.session(subject)
            if not isinstance(declaration, dict):
                raise Unreachable('the authority gave no session declaration')
            if declaration.get('reason'):
                return result('refused', declaration['reason'])
            if declaration.get('item') is None:
                answer = ask('declare', DECLARE, declaration['declare'])
                if not answer['ok']:
                    return result('refused', answer.get('reason'))
        answer = ask('event', EVENT, {'type': kind, 'subject': dict(subject),
                                     'emitter': dict(one['emitter'])})
        return result('recorded') if answer['ok'] else result('refused', answer.get('reason'))

    about = authority.about(subject['repository'], subject.get('path'))
    if about is None:
        return result('nothing', 'the repository is neither bound nor plain')
    if not isinstance(about, dict) or not isinstance(about.get('scope'), dict):
        raise Unreachable('the authority gave no answer')
    if kind == 'ref_changed':
        # The authority's own declarations say what a trunk is, never the entry and never a guess.
        declared = [full_ref(about['trunk'])] if _text(about.get('trunk')) else []
        declared += [full_ref(name) for name in about.get('landing_refs') or () if _text(name)]
        if subject['ref'] not in declared:
            return result('nothing', 'ref_not_declared' if _text(about.get('trunk')) else 'trunk_undeclared')
    subject, why = facts(one)
    if subject is None:
        return result('nothing', why)
    if kind == 'ref_changed':
        answer = ask('event', EVENT, {'type': 'ref_changed', 'subject': dict(subject),
                                      'emitter': dict(one['emitter'])})
        return result('recorded') if answer['ok'] else result('refused', answer.get('reason'))
    item = about.get('item')
    if item is None and _text(about.get('other')):
        # A live item of another repository is at the path: it is never given this worktree's branch.
        return result('refused', OTHER + about['other'])
    # Only an item a hook declared is confirmed here: one a creator of Veldo's declared is its own.
    state = about.get('state') if about.get('creator') == 'hook' else None
    if kind == 'branch_switched':
        if item is None:
            return result('nothing', 'no item records this worktree')
        answer = ask('rebranch', REBRANCH, {'item': item, 'branch': subject['branch'], 'start': subject['start']})
        return result('recorded') if answer['ok'] else result('refused', answer.get('reason'))
    there = item is not None
    if not there:
        answer = ask('declare', DECLARE, {'kind': 'worktree', 'locator': {'path': subject['path']},
                                          'owner': owner_of(subject['branch'], about,
                                                            one['subject'].get('run_label')), 'creator': 'hook',
                                          'branch': subject['branch'], 'start': subject['start']})
        if answer['ok']:
            item, state = answer.get('item'), 'declared'
        elif _text(answer.get('reason')) and answer['reason'].startswith(TAKEN):
            # Another call recorded the path since about was read: that item is given the branch, when
            # the authority says it is this repository's.
            item, state, there = answer['reason'][len(TAKEN):], None, True
            again = authority.about(subject['repository'], subject['path'])
            if not isinstance(again, dict) or again.get('item') != item:
                return result('refused', OTHER + item)
        else:
            return result('refused', answer.get('reason'))
    if state == 'declared':
        answer = ask('confirm', CONFIRM, {'item': item})
        if not answer['ok']:
            return result('refused', answer.get('reason'))
    if there or subject['branch'] is not None:
        # For a new item this records the branch item; for one already there, the branch it is on now.
        answer = ask('rebranch', REBRANCH, {'item': item, 'branch': subject['branch'], 'start': subject['start']})
        if not answer['ok']:
            return result('refused', answer.get('reason'))
    return result('recorded')


def replay(folder, authority, sign, wait=LOCK_SECONDS, seconds=REPLAY_SECONDS, clock=time.monotonic,
           facts=None):
    """Deliver the spooled entries, oldest first. Returns one {name, type, outcome, reason} for each
    entry it handled; an entry it could not reach the authority for, and every one after it, stays.
    `seconds` is the replay's overall deadline: past it no further entry is started, a read of git is
    given only the time that is left, and the rest stay in the spool for the next replay."""
    done = []
    until = None if seconds is None else clock() + seconds
    lock = _locked(folder, wait)
    if lock is None:
        return done  # another call is replaying; what it does not take stays for the next call
    try:
        _sweep(folder)
        blocked, seen = set(), set()
        while True:
            names = [name for name in pending(folder) if name not in seen]
            if not names:
                return done
            for name in names:
                if until is not None and clock() >= until:
                    return done  # out of time: this entry and every later one stay for the next replay
                seen.add(name)
                try:
                    one = read(folder, name)
                except FileNotFoundError:
                    continue
                except TimeoutError:
                    raise  # a caller's deadline fired in the read: the entry stays whole, with the rest
                except (Malformed, OSError) as error:
                    _set_aside_raw(folder, name, str(error))
                    done.append({'name': name, 'type': None, 'outcome': 'refused',
                                 'reason': 'unsafe' if isinstance(error, Unsafe) else 'malformed'})
                    continue
                key = _key(one)
                if key in blocked:
                    continue  # an older entry about the same thing waits: this one stays behind it
                try:
                    result = send(one, authority, sign, facts, until=until, clock=clock)
                except Unreachable:
                    return done
                except _Late:
                    return done  # out of time while git was read: this entry stays whole, and every later one
                except _Waits as waiting:
                    blocked.add(key)
                    _write(os.path.join(folder, name), dict(one, tries=one['tries'] + 1))
                    done.append({'name': name, 'type': one['type'], 'outcome': 'waits', 'reason': waiting.reason})
                    continue
                if result['outcome'] == 'refused':
                    _set_aside(folder, name, {'entry': one, 'refused': result})
                else:
                    if result['outcome'] == 'nothing':
                        observe(folder, {'outcome': 'nothing', 'reason': result['reason'], 'entry': one})
                    remove_delivered(folder, name)  # delivery acknowledgement, never age, authorizes cleanup
                done.append({'name': name, 'type': one['type'], 'outcome': result['outcome'],
                             'reason': result['reason']})
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        os.close(lock)


def remove_delivered(folder, name):
    """An acknowledged delivery no longer needs its pending input; this event has no clock."""
    if os.path.basename(name) != name or name in ('.', '..'):
        raise Unsafe('not a spool entry name')
    os.unlink(os.path.join(_folder(folder), name))


def _set_aside_raw(folder, name, why):
    """A spooled file that is no entry: renamed into refused/ as it is, with why beside it."""
    aside = _folder(os.path.join(folder, REFUSED))
    os.rename(os.path.join(folder, name), os.path.join(aside, name + '.malformed'))
    _write(os.path.join(aside, name + '.why'), {'refused': why})


def deliver(entries, folder, authority, sign, seconds=HOOK_SECONDS):
    """Record what a hook saw: each entry is written into the spool, then the spool is replayed, the
    entries of earlier calls first, for `seconds` at most. With no authority given, or none reachable,
    they stay spooled. Returns the names written and what the replay did."""
    names = [put(folder, one) for one in entries]
    done = replay(folder, authority, sign, seconds=seconds) if authority is not None else []
    return {'spooled': names, 'replayed': done}


def submit(one, state_root, installation=None, authority=None, sign=None):
    """Persist before resolving a key or contacting the authority. Failures leave the entry whole.
    The caller may provide the authority for an in-process call; ordinary hooks use the local socket.
    """
    folder = spool_folder(state_root)
    name = put(folder, one)
    try:
        installation = installation or _sibling('installation').resolve()['folder']
        remote = authority if authority is not None else Remote(
            socket_path(folder), until=time.monotonic() + HOOK_SECONDS)
        done = replay(folder, remote, sign or signer(installation), seconds=HOOK_SECONDS)
        return {'spooled': name, 'replayed': done, 'pending': name in pending(folder)}
    except Exception as error:
        return {'spooled': name, 'replayed': [], 'pending': True, 'reason': str(error)}


def session_record(kind, payload, state_root, installation=None, pid=None, fallback=None):
    """Record one client notification and say where: {spooled, replayed, pending, root} for an entry,
    {refused, reason, root} for a notification that is no entry. The client supplies session_id and
    cwd. The exec hook's parent is the client process. A start time is the kernel's field 22, in
    ticks, as the owner-live probe records it. The folder is resolved first. What is still no entry
    (no event is invented when the process cannot be read) is written under refused/ with why. A root
    whose spool folder is refused is noted beside it and `fallback` is the next root. Raises when no
    root took it."""
    host = socket.gethostname() or 'unknown'
    seen = {'type': kind, 'payload': payload, 'pid': pid, 'host': host}
    one = why = None
    try:
        pid = os.getppid() if pid is None else pid
        seen['pid'] = pid
        with open('/proc/%d/stat' % pid, 'rb') as stream:
            fields = stream.read().rsplit(b')', 1)[1].split()
        seen['started'] = int(fields[19])
        where = resolved(payload['cwd'])
        one = session_entry(kind, payload['session_id'], where, pid, seen['started'], host)
    except TimeoutError:
        raise
    except Exception as error:
        why = 'space_session_invalid:' + (str(error) or type(error).__name__)
    last = Malformed('no state root')
    for root in [state_root] + ([fallback] if fallback and fallback != state_root else []):
        try:
            if one is None:
                return {'refused': refuse(root, seen, why), 'reason': why, 'root': root}
            return dict(submit(one, root, installation), root=root)
        except TimeoutError:
            raise
        except Unsafe as error:
            note_refused_folder(root, str(error))
            last = error
        except (Malformed, OSError) as error:
            last = error
    raise last


def session_hook(kind, payload, state_root, installation=None, pid=None, fallback=None):
    """session_record for a hook: no failure escapes to the client, and the status is 0. A
    notification no root took is left as one line under a state root (unspooled)."""
    try:
        session_record(kind, payload, state_root, installation, pid, fallback)
    except Exception as error:
        try:
            unspooled([state_root, fallback], {'type': kind, 'payload': payload,
                                               'pid': os.getppid() if pid is None else pid,
                                               'reason': str(error) or type(error).__name__})
        except Exception:
            pass
    return 0


def start(folder, authority, sign, reconcile=None, seconds=REPLAY_SECONDS):
    """What the service does at its start: replay the spool, and only then reconcile (design section 9).
    Returns (what the replay did, reconcile's answer)."""
    done = replay(folder, authority, sign, seconds=seconds)
    return done, (reconcile() if reconcile is not None else None)


# ---------------------------------------------------------------------------------------------
# The authority.
# ---------------------------------------------------------------------------------------------

class Local:
    """The authority in its own process: a Ledger, the membership module and the clock accept is given.
    `landing` is the work configuration's land entry (control_service.landing_names, the mapping
    control_api_authority.landing_of reads): a mapping, or a call that returns one, from an execution
    repository's path or a project's name to {trunk}. It is the only place a trunk is read from."""

    def __init__(self, ledger, membership, clock=time.time, landing=None):
        self.ledger, self.membership, self.clock, self.landing = ledger, membership, clock, landing

    def accept(self, packet):
        """The Ledger's own accept: it verifies the signature, the packet's age and nonce, the rule for
        the principal, and runs the command."""
        return self.ledger.accept(packet, self.membership, self.clock())

    def session(self, subject):
        """Derive the declaration from the authority's roots, never a caller's scratch path.

        The first scratch root holds new sessions. cwd is encoded as UTF-8 hex ({working_folder}) in the
        pattern so two folders cannot alias. An existing unrecorded folder is never made scratch.
        This reads and declares only; creation and event consumption are separate operations.
        """
        try:
            checked(entry('session_started', subject, 'SessionStart', self.ledger.host))
            where = plain_path(subject['cwd'])
            scopes = []
            for project in self.ledger.projects:
                for root in (project['repository'], project['worktree_root']):
                    if _inside(where, canonical(root)):
                        scopes.append((len(canonical(root)), {'type': 'project', 'id': project['project']}))
            for plain in self.ledger.config.get('plain_repositories') or ():
                for root in (plain['repository'], plain['worktree_root']):
                    if _inside(where, canonical(root)):
                        scopes.append((len(canonical(root)),
                                       {'type': 'plain_repository', 'id': canonical(plain['repository'])}))
            scopes.sort(key=lambda pair: pair[0], reverse=True)
            scope = scopes[0][1] if scopes else {'type': 'no_project'}
            if any(length == scopes[0][0] and other != scope for length, other in scopes):
                return {'reason': 'space_session_scope_ambiguous'}
            scratch = self.ledger.config['scratch_roots']
            root = plain_path(scratch['roots'][0])
            relative = scratch['session_pattern'].format(
                session_id=subject['session'], working_folder=where.encode().hex())
            path = plain_path(os.path.join(root, relative))
            if path == root or not _inside(path, root):
                return {'reason': 'space_outside_roots'}
            owner = {'scope': scope, 'session': subject['session']}
            process = {name: subject[name] for name in ('pid', 'started')}
            for identity, record in self.ledger.items().items():
                if record.get('locator') != {'path': path} or record.get('state') in ENDED:
                    continue
                if (record.get('kind') == 'scratch' and record.get('creator') == 'hook'
                        and record.get('owner') == owner and record.get('process') == process):
                    return {'item': identity}
                return {'reason': TAKEN + identity}
            if os.path.lexists(path):
                return {'reason': 'space_session_exists'}
            return {'item': None, 'declare': {'kind': 'scratch', 'locator': {'path': path},
                                             'owner': owner, 'creator': 'hook', 'process': process}}
        except (Malformed, KeyError, IndexError, TypeError, ValueError) as error:
            return {'reason': 'space_session_invalid:' + str(error)}

    def trunk(self, repository, scope):
        """The trunk the land entry declares for a repository, or None: no declaration, no trunk."""
        try:
            lands = self.landing() if callable(self.landing) else self.landing
        except Exception:
            return None
        if not isinstance(lands, dict):
            return None
        for key, land in sorted(lands.items(), key=lambda pair: str(pair[0])):
            if not _text(key) or not isinstance(land, dict) or not _text(land.get('trunk')):
                continue
            if (canonical(key) == repository if os.path.isabs(key)
                    else scope['type'] == 'project' and key == scope['id']):
                return land['trunk']
        return None

    def about(self, repository, path=None):
        """{scope, patterns, trunk, landing_refs, item, state, creator, other} for a repository the
        declarations name, else None. trunk is the one the land entry declares (None when none does).
        item is the live worktree item at `path` in that repository, with its state and who recorded
        it; other is a live worktree item at the path that is another repository's."""
        if not _text(repository) or not (path is None or _text(path)):
            return None
        repository, path = canonical(repository), None if path is None else canonical(path)
        scope = patterns = None
        landing_refs = []
        for project in self.ledger.projects:
            if canonical(str(project.get('repository'))) == repository:
                scope = {'type': 'project', 'id': project['project']}
                patterns = list(project.get('branch_pattern') or ())
                landing_refs = [name for name in project.get('landing_refs') or () if _text(name)]
        if scope is None:
            for plain in self.ledger.config.get('plain_repositories') or ():
                if canonical(str(plain.get('repository'))) == repository:
                    scope, patterns = {'type': 'plain_repository', 'id': repository}, []
        if scope is None:
            return None
        item = state = creator = other = None
        for identity, record in sorted(self.ledger.items().items()) if path is not None else ():
            if (record.get('kind') == 'worktree' and record.get('state') not in ENDED
                    and (record.get('locator') or {}).get('path') == path):
                if self.ledger._repository_of(record) == repository:
                    item, state, creator = identity, record.get('state'), record.get('creator')
                else:
                    other = identity
        # The wrapper's scratch declaration records the station. Never take a station from a hook's
        # environment. Retired records remain useful when an offline hook is replayed after the run.
        runs, conflicts = {}, set()
        for record in self.ledger.items().values():
            owner = record.get('owner') or {}
            run = owner.get('run') or {}
            if (record.get('kind') != 'scratch' or record.get('creator') != 'wrapper'
                    or owner.get('scope') != scope or not run.get('id')
                    or self.ledger.issued_to(run['id']) != 'space-runner'):
                continue
            if run['id'] in runs and runs[run['id']] != run:
                conflicts.add(run['id'])
            runs[run['id']] = dict(run)
        for identity in conflicts:
            runs.pop(identity, None)
        return {'scope': scope, 'patterns': patterns, 'runs': runs, 'trunk': self.trunk(repository, scope),
                'landing_refs': landing_refs, 'item': item, 'state': state, 'creator': creator,
                'other': other if item is None else None}


def socket_path(folder):
    return os.path.join(folder, SOCKET)


class Remote:
    """The hook's side of the authority's local socket. Anything but an answer is Unreachable. Nothing
    is sent before the kernel has said the socket is served by `uid`, this account. `until`, when
    given, is a time.monotonic() deadline no answer is waited for past."""

    def __init__(self, address, timeout=REACH_SECONDS, uid=None, until=None):
        self.address, self.timeout, self.until = address, timeout, until
        self.uid = os.getuid() if uid is None else uid

    def _call(self, request):
        timeout = self.timeout if self.until is None else min(self.timeout, self.until - time.monotonic())
        if timeout <= 0:
            raise Unreachable('out of time')
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(timeout)
        try:
            connection.connect(self.address)
            if _sibling('control_client').peer_uid(connection) != self.uid:
                raise Unreachable('the socket is not served by this account')
            connection.sendall(json.dumps(request).encode())
            connection.shutdown(socket.SHUT_WR)
            chunks, total = [], 0
            while True:
                chunk = connection.recv(65536)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_BYTES:
                    raise Unreachable('the answer is too long')
                chunks.append(chunk)
            answer = json.loads(b''.join(chunks).decode())
        except (OSError, ValueError) as error:
            raise Unreachable(str(error))
        finally:
            connection.close()
        if not isinstance(answer, dict) or answer.get('served') is not True:
            raise Unreachable('the authority did not serve the request')
        return answer.get('answer')

    def accept(self, packet):
        return self._call({'call': 'accept', 'packet': packet})

    def about(self, repository, path=None):
        return self._call({'call': 'about', 'repository': repository, 'path': path})

    def session(self, subject):
        return self._call({'call': 'session', 'subject': subject})


def listen(folder):
    """The authority's listening socket in the spool folder, which only this account can enter."""
    return _sibling('control_client').bind(socket_path(_folder(folder)))


def serve_one(listener, authority, after=None, timeout=REACH_SECONDS):
    """Take one connection: judge the peer, answer one request, close. Then, and only then, call
    `after(request, answer)` for a served request: the caller on the other end has its answer and is
    gone, so nothing `after` does can delay it."""
    connection, _address = listener.accept()
    request, response = None, {'served': False}
    try:
        connection.settimeout(timeout)
        if _sibling('control_client').peer_uid(connection) == os.getuid():
            try:
                chunks, total = [], 0
                while total <= MAX_BYTES:
                    chunk = connection.recv(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    chunks.append(chunk)
                request = json.loads(b''.join(chunks).decode()) if total <= MAX_BYTES else None
            except (OSError, ValueError):
                request = None
            try:
                if isinstance(request, dict) and request.get('call') == 'accept':
                    response = {'served': True, 'answer': authority.accept(request.get('packet'))}
                elif isinstance(request, dict) and request.get('call') == 'about':
                    response = {'served': True, 'answer': authority.about(request.get('repository'),
                                                                          request.get('path'))}
                elif isinstance(request, dict) and request.get('call') == 'session':
                    response = {'served': True, 'answer': authority.session(request.get('subject'))}
            except Exception:  # the hook is told it was not served, and its entry stays in the spool
                response = {'served': False}
        try:
            connection.sendall(json.dumps(response).encode())
        except OSError:
            pass
    finally:
        connection.close()
    if after is not None and response['served']:
        after(request, response['answer'])
    return response


def signer(installation):
    """sign(operation, parameters, command_id, nonce) with space-observer's own key from the
    installation folder (VELDO-0326). A key that is missing or does not sign makes the entry wait."""
    def sign(operation, parameters, command_id, nonce):
        space = _sibling('control_space')
        try:
            return space.signed(OBSERVER, operation, parameters, installation,
                                _sibling('control_store').canonical_bytes, time.time(), command_id, nonce)
        except space.Refused as refusal:
            raise _Waits(refusal.code)
    return sign


# ---------------------------------------------------------------------------------------------
# The CLI's verbs: veldo space record, veldo space event, veldo space replay.
# ---------------------------------------------------------------------------------------------

def main(argv=None, stdin=None, stdout=None, stderr=None):
    """veldo space record --state-root R --worktree W --git-dir G --common-dir C [--branch B] OLD NEW FLAG
    is what the post-checkout hook runs; veldo space event --state-root R --common-dir C [--trunk T], with
    git's "<old> <new> <ref>" lines on standard input, is what the reference-transaction hook runs in
    the committed state (with no trunk named it sends nothing for any branch and notes the repository
    once); veldo space replay --state-root R delivers what is spooled. Each takes
    --installation F for the folder the observer's key is in (default: the resolved one).

    record and event exit 0 whatever happens: nothing of theirs reaches the git command."""
    import argparse
    stdin, stdout, stderr = stdin or sys.stdin, stdout or sys.stdout, stderr or sys.stderr
    parser = argparse.ArgumentParser(prog='veldo space')
    verbs = parser.add_subparsers(dest='verb', required=True)
    for name in ('record', 'event', 'replay'):
        verb = verbs.add_parser(name)
        verb.add_argument('--state-root', required=True)
        verb.add_argument('--installation')
        if name == 'record':
            verb.add_argument('--worktree', required=True)
            verb.add_argument('--git-dir', required=True)
            verb.add_argument('--common-dir', required=True)
            verb.add_argument('--branch', default='')
            verb.add_argument('previous')
            verb.add_argument('new')
            verb.add_argument('flag')
        elif name == 'event':
            verb.add_argument('--common-dir', required=True)
            verb.add_argument('--trunk')
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 0 if argv and argv[0] in ('record', 'event') else 2
    try:
        host = socket.gethostname() or 'unknown'
        if args.verb == 'record':
            one = checkout(args.previous, args.new, args.flag, args.worktree, args.git_dir, args.common_dir,
                           args.branch, host, run_label=os.environ.get('VELDO_SPACE_LABEL'))
            entries = [one] if one is not None else []
        elif args.verb == 'event':
            lines = stdin.read().splitlines()
            entries = ref_changes(lines, args.common_dir, host, args.trunk or None)
            if not _text(args.trunk):
                # The trunk is never guessed: nothing is sent for a branch, and the repository is noted.
                sent = [one['subject']['ref'] for one in entries]
                moved = [parts[2] for parts in (line.split() for line in lines)
                         if len(parts) == 3 and parts[0] != parts[1] and parts[2].startswith('refs/heads/')
                         and parts[2] not in sent]
                if moved:
                    note_undeclared(spool_folder(args.state_root), repository_of(args.common_dir), moved[0])
        else:
            entries = []
        if not entries and args.verb != 'replay':
            return 0
        folder = spool_folder(args.state_root)
        installation = args.installation
        if not installation:
            resolved = _sibling('installation').resolve()
            installation = resolved['folder']
        seconds = REPLAY_SECONDS if args.verb == 'replay' else HOOK_SECONDS
        remote = Remote(socket_path(folder), until=time.monotonic() + seconds)
        done = deliver(entries, folder, remote, signer(installation), seconds=seconds)
        if args.verb == 'replay':
            stdout.write(json.dumps({'replayed': done['replayed'], 'pending': pending(folder),
                                     'refused': refused(folder), 'undeclared': undeclared(folder),
                                     'observations': len(observations(folder))}, sort_keys=True) + '\n')
    except Unsafe as error:  # a spool that is not this account's alone: refused, and noted beside it
        note_refused_folder(args.state_root, str(error))
        if args.verb == 'replay':
            stderr.write('veldo space replay: %s\n' % error)
            return 1
    except Exception as error:  # nothing of this module's reaches the git command
        if args.verb == 'replay':
            stderr.write('veldo space replay: %s\n' % error)
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
