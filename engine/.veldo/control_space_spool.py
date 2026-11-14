#!/usr/bin/env python3
"""The event spool, and what a git hook records through it (VELDO-0311, design 4.5, 4.6, 6.9, 8.4, 8.5).

WHAT THIS MODULE IS. A worktree added with plain git, a branch switched in it and a trunk moved by hand
all happen outside Veldo. Two git hooks (engine/hooks/post-checkout and reference-transaction) start the
CLI, and the CLI calls this module. It writes down what the hook saw as one entry, hands it to the
authority, and returns. It removes nothing of anybody's: no worktree, no folder, no ref, no branch. It
runs no git command. Whatever goes wrong, the git command it rides on ends as it would without it.

AN ENTRY is what a hook saw, {schema, id, type, subject, emitter, at, tries}:

  worktree_added    post-checkout with the null commit as the previous HEAD, in a linked worktree:
                    repository, path, branch (None when detached) and start, the commit checked out.
  branch_switched   post-checkout with a real previous HEAD and the branch flag, in a linked worktree:
                    the same four fields, for the branch and commit the worktree is on now.
  ref_changed       reference-transaction in its committed state, for the trunk or a declared landing
                    ref: repository, ref, old and new.

The repository's own checkout is never an item (design 0.1), so a checkout there is no entry. A checkout
git makes while a rebase is in progress is no entry: the worktree's branch is the same when it ends. A
ref under refs/veldo/ is no entry (design 0.2: the hook sends nothing for a kept ref).

THE SPOOL (design 4.6) is <state root>/space-spool: one file per entry, written whole under a temporary
name, synced and renamed into place, named by the time it was written, so the files in name order are
the entries in the order the hooks ran. Every entry is written there first and delivered from there, so
there is no moment in which an entry exists only in a process. With the authority not reachable the
file stays. It is replayed, oldest first, by the next call that reaches the authority (deliver, and the
CLI's replay verb) and by start, which the service calls before reconcile.

WHAT BECOMES OF AN ENTRY at a replay:

  recorded   the authority wrote what the entry says. The file is unlinked, and only then.
  nothing    there is nothing to write: the repository is neither bound nor plain, or a switch was seen
             in a worktree no item records (reconcile adopts it). The file is unlinked.
  refused    the Ledger refused it by a name that will not change (a path outside every known root, a
             protected path, a locator through a link). The entry and the answer are written to
             refused/ under the same name, and the file leaves the spool. Nothing drops it silently.
  waits      the authority answered but cannot take it yet: the Ledger has no such command (the event
             command is VELDO-0323's), the observer's key is missing or not enrolled, the packet was
             judged late. The file stays, its count of tries goes up by one, and later entries about the
             same worktree or the same ref stay behind it, so the order of one thing's entries is kept.
  not reachable  the replay stops there. Every file from that one on stays.

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
(the project as the Ledger knows it, or the plain repository), the project's branch patterns and the live
worktree item at the path. A branch that matches a pattern is owned by the scope and the ticket the
pattern names; any other branch, a detached worktree and a worktree of a plain repository by the scope
alone. A worktree a run owns (the run's label in the hook's environment) is VELDO-0336's.

HOW LONG A HOOK CAN WAIT. The hook's side gives the authority REACH_SECONDS for each answer and another
call's replay LOCK_SECONDS; past either, the entry stays in the spool and the git command goes on.

THE AUTHORITY is anything with accept(packet) and about(repository, path) that raises Unreachable when it
cannot be reached. Local is the one in the authority's own process, over a Ledger. Remote is the hook's
side of a local socket, <state root>/space-spool/authority.sock, one JSON request per connection; serve_one
is the authority's side: the peer must be this account (the kernel's answer), the answer is sent and the
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
import string
import sys
import time
import uuid

SCHEMA = 'veldo.control_space_spool/v1'
SPOOL = 'space-spool'  # under the state root (design 4.6 and section 9)
REFUSED = 'refused'
SOCKET = 'authority.sock'
LOCK = 'lock'
SUFFIX = '.json'
TYPES = ('worktree_added', 'branch_switched', 'ref_changed')
FIELDS = {'worktree_added': ('repository', 'path', 'branch', 'start'),
          'branch_switched': ('repository', 'path', 'branch', 'start'),
          'ref_changed': ('repository', 'ref', 'old', 'new')}
HOOKS = ('post-checkout', 'reference-transaction')
# The Ledger's own names (control_space.py); the suite holds them equal.
OBSERVER = 'space-observer'
DECLARE, CONFIRM, REBRANCH, EVENT = 'space_declare', 'space_confirm', 'space_rebranch', 'space_event'
TAKEN = 'space_locator_taken:'
ENDED = ('removed', 'gone')
# A refusal that says "not yet", never "no": the entry stays in the spool.
WAITS = ('space_no_command:', 'space_packet_', 'space_no_key', 'space_no_installation', 'not_authorized',
         'unavailable_service')
KEPT_REFS = 'refs/veldo/'
TRUNK = 'main'  # the trunk when the hook names none (git config veldo.space.trunk)
REBASING = ('rebase-merge', 'rebase-apply')
MAX_BYTES = 1 << 20
REACH_SECONDS = 5.0   # the longest a hook waits for the authority's answer
LOCK_SECONDS = 2.0    # the longest a call waits for another call's replay
_LOADED = {}


class Unreachable(Exception):
    """The authority could not be reached, or gave no answer."""


class Malformed(Exception):
    """Something that is not an entry."""


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


# ---------------------------------------------------------------------------------------------
# Entries: what a hook saw.
# ---------------------------------------------------------------------------------------------

def checked(entry):
    """The entry, when it is one. Raises Malformed."""
    if not isinstance(entry, dict) or entry.get('schema') != SCHEMA or entry.get('type') not in TYPES:
        raise Malformed('not an entry of ' + SCHEMA)
    subject, emitter = entry.get('subject'), entry.get('emitter')
    fields = FIELDS[entry['type']]
    if not isinstance(subject, dict) or set(subject) != set(fields):
        raise Malformed('the subject of %s holds %s' % (entry['type'], ', '.join(fields)))
    for field in fields:
        if not _text(subject[field]) and not (field == 'branch' and subject[field] is None):
            raise Malformed('subject.%s is a name' % field)
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


def repository_of(common_dir):
    """The repository a git common directory belongs to: the folder that holds .git, or the directory
    itself for a bare repository."""
    common = os.path.normpath(common_dir)
    return os.path.dirname(common) if os.path.basename(common) == '.git' else common


def checkout(previous, new, flag, worktree, git_dir, common_dir, branch, host, at=None):
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
    return entry(kind, {'repository': repository_of(common_dir), 'path': os.path.normpath(worktree),
                        'branch': branch or None, 'start': new}, 'post-checkout', host, at)


def full_ref(name):
    return name if name.startswith('refs/') else 'refs/heads/' + name


def watched(repository, trunk=None):
    """The refs whose change is recorded for `repository`: its trunk, and the landing refs its space
    file declares. A space file that cannot be read declares none here."""
    refs = [full_ref(trunk or TRUNK)]
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
    landing ref. `lines` are git's own, "<old> <new> <ref>". A kept ref gives none."""
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


def _folder(folder):
    """The spool folder, made 0700 when it is not there. A link is refused: an entry is never written
    through one."""
    if os.path.islink(folder):
        raise Malformed('the spool folder is a link: ' + folder)
    os.makedirs(folder, mode=0o700, exist_ok=True)
    return folder


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
    with open(os.path.join(folder, name), 'rb') as handle:
        data = handle.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise Malformed('an entry of more than %d bytes' % MAX_BYTES)
    try:
        return checked(json.loads(data.decode()))
    except ValueError as error:
        raise Malformed(str(error))


def refused(folder):
    """The names under refused/: entries the Ledger refused for good, each with the answer."""
    return pending(os.path.join(folder, REFUSED))


def _set_aside(folder, name, document):
    """Move an entry out of the spool into refused/, with why. It is written there before it leaves."""
    aside = os.path.join(folder, REFUSED)
    os.makedirs(aside, mode=0o700, exist_ok=True)
    _write(os.path.join(aside, name), document)
    os.unlink(os.path.join(folder, name))


def _locked(folder, seconds):
    """The spool's lock, held by one replay at a time, or None when another call still holds it after
    `seconds`."""
    descriptor = os.open(os.path.join(_folder(folder), LOCK), os.O_RDWR | os.O_CREAT, 0o600)
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


def owner_of(branch, about):
    """The owner the branch pattern gives: the scope, and the ticket when the branch names one."""
    owner = {'scope': dict(about['scope'])}
    ticket = ticket_of(branch, about.get('patterns'))
    if ticket:
        owner['ticket'] = ticket
    return owner


def waits(reason):
    return _text(reason) and reason.startswith(WAITS)


def _key(one):
    subject = one['subject']
    return ('ref', subject['repository'], subject['ref']) if one['type'] == 'ref_changed' else (
        'path', subject['path'])


def send(one, authority, sign):
    """Hand one entry to the authority as the Ledger's commands, each signed by `sign(operation,
    parameters, command_id, nonce)`. Returns {outcome, reason, answers}: recorded, nothing or refused.
    Raises Unreachable when the authority is not reachable and _Waits when it cannot take the entry yet."""
    kind, subject, answers = one['type'], one['subject'], []

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

    if kind == 'ref_changed':
        answer = ask('event', EVENT, {'type': 'ref_changed', 'subject': dict(subject),
                                      'emitter': dict(one['emitter'])})
        return result('recorded') if answer['ok'] else result('refused', answer.get('reason'))
    about = authority.about(subject['repository'], subject['path'])
    if about is None:
        return result('nothing', 'the repository is neither bound nor plain')
    if not isinstance(about, dict) or not isinstance(about.get('scope'), dict):
        raise Unreachable('the authority gave no answer')
    item = about.get('item')
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
                                          'owner': owner_of(subject['branch'], about), 'creator': 'hook',
                                          'branch': subject['branch'], 'start': subject['start']})
        if answer['ok']:
            item, state = answer.get('item'), 'declared'
        elif _text(answer.get('reason')) and answer['reason'].startswith(TAKEN):
            # Another call recorded the path since about was read: that item is given the branch.
            item, state, there = answer['reason'][len(TAKEN):], None, True
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


def replay(folder, authority, sign, wait=LOCK_SECONDS):
    """Deliver the spooled entries, oldest first. Returns one {name, type, outcome, reason} for each
    entry it handled; an entry it could not reach the authority for, and every one after it, stays."""
    done = []
    lock = _locked(folder, wait)
    if lock is None:
        return done  # another call is replaying; what it does not take stays for the next call
    try:
        blocked, seen = set(), set()
        while True:
            names = [name for name in pending(folder) if name not in seen]
            if not names:
                return done
            for name in names:
                seen.add(name)
                try:
                    one = read(folder, name)
                except FileNotFoundError:
                    continue
                except (Malformed, OSError) as error:
                    _set_aside_raw(folder, name, str(error))
                    done.append({'name': name, 'type': None, 'outcome': 'refused', 'reason': 'malformed'})
                    continue
                key = _key(one)
                if key in blocked:
                    continue  # an older entry about the same thing waits: this one stays behind it
                try:
                    result = send(one, authority, sign)
                except Unreachable:
                    return done
                except _Waits as waiting:
                    blocked.add(key)
                    _write(os.path.join(folder, name), dict(one, tries=one['tries'] + 1))
                    done.append({'name': name, 'type': one['type'], 'outcome': 'waits', 'reason': waiting.reason})
                    continue
                if result['outcome'] == 'refused':
                    _set_aside(folder, name, {'entry': one, 'refused': result})
                else:
                    os.unlink(os.path.join(folder, name))  # delivered: the Ledger holds what it said
                done.append({'name': name, 'type': one['type'], 'outcome': result['outcome'],
                             'reason': result['reason']})
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        os.close(lock)


def _set_aside_raw(folder, name, why):
    """A spooled file that is no entry: renamed into refused/ as it is, with why beside it."""
    aside = os.path.join(folder, REFUSED)
    os.makedirs(aside, mode=0o700, exist_ok=True)
    os.rename(os.path.join(folder, name), os.path.join(aside, name + '.malformed'))
    _write(os.path.join(aside, name + '.why'), {'refused': why})


def deliver(entries, folder, authority, sign):
    """Record what a hook saw: each entry is written into the spool, then the spool is replayed, the
    entries of earlier calls first. With no authority given, or none reachable, they stay spooled.
    Returns the names written and what the replay did."""
    names = [put(folder, one) for one in entries]
    done = replay(folder, authority, sign) if authority is not None else []
    return {'spooled': names, 'replayed': done}


def start(folder, authority, sign, reconcile=None):
    """What the service does at its start: replay the spool, and only then reconcile (design section 9).
    Returns (what the replay did, reconcile's answer)."""
    done = replay(folder, authority, sign)
    return done, (reconcile() if reconcile is not None else None)


# ---------------------------------------------------------------------------------------------
# The authority.
# ---------------------------------------------------------------------------------------------

class Local:
    """The authority in its own process: a Ledger, the membership module and the clock accept is given."""

    def __init__(self, ledger, membership, clock=time.time):
        self.ledger, self.membership, self.clock = ledger, membership, clock

    def accept(self, packet):
        """The Ledger's own accept: it verifies the signature, the packet's age and nonce, the rule for
        the principal, and runs the command."""
        return self.ledger.accept(packet, self.membership, self.clock())

    def about(self, repository, path):
        """{scope, patterns, item, state, creator} for a path in a repository the declarations name,
        else None. item is the live worktree item at the path, with its state and who recorded it."""
        if not _text(repository) or not _text(path):
            return None
        repository, path = os.path.normpath(repository), os.path.normpath(path)
        scope = patterns = None
        for project in self.ledger.projects:
            if os.path.normpath(str(project.get('repository'))) == repository:
                scope = {'type': 'project', 'id': project['project']}
                patterns = list(project.get('branch_pattern') or ())
        if scope is None:
            for plain in self.ledger.config.get('plain_repositories') or ():
                if os.path.normpath(str(plain.get('repository'))) == repository:
                    scope, patterns = {'type': 'plain_repository', 'id': repository}, []
        if scope is None:
            return None
        item = state = creator = None
        for identity, record in sorted(self.ledger.items().items()):
            if (record.get('kind') == 'worktree' and record.get('state') not in ENDED
                    and (record.get('locator') or {}).get('path') == path):
                item, state, creator = identity, record.get('state'), record.get('creator')
        return {'scope': scope, 'patterns': patterns, 'item': item, 'state': state, 'creator': creator}


def socket_path(folder):
    return os.path.join(folder, SOCKET)


class Remote:
    """The hook's side of the authority's local socket. Anything but an answer is Unreachable."""

    def __init__(self, address, timeout=REACH_SECONDS):
        self.address, self.timeout = address, timeout

    def _call(self, request):
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(self.timeout)
        try:
            connection.connect(self.address)
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

    def about(self, repository, path):
        return self._call({'call': 'about', 'repository': repository, 'path': path})


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
    the committed state; veldo space replay --state-root R delivers what is spooled. Each takes
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
                           args.branch, host)
            entries = [one] if one is not None else []
        elif args.verb == 'event':
            entries = ref_changes(stdin.read().splitlines(), args.common_dir, host, args.trunk)
        else:
            entries = []
        if not entries and args.verb != 'replay':
            return 0
        folder = spool_folder(args.state_root)
        installation = args.installation
        if not installation:
            resolved = _sibling('installation').resolve()
            installation = resolved['folder']
        done = deliver(entries, folder, Remote(socket_path(folder)), signer(installation))
        if args.verb == 'replay':
            stdout.write(json.dumps({'replayed': done['replayed'], 'pending': pending(folder),
                                     'refused': refused(folder)}, sort_keys=True) + '\n')
    except Exception as error:  # nothing of this module's reaches the git command
        if args.verb == 'replay':
            stderr.write('veldo space replay: %s\n' % error)
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
