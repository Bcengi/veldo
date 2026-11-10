#!/usr/bin/env python3
"""The login lease (VELDO-0211): borrow a login, write a rotated credential back, recover what a
killed run left.

A login is a directory that holds an engine's subscription credential. Every user of a login
first takes the lock on <login>/.runner-lease (take_lease), so two runs never rotate the same
credential at once. A borrower copies the credential into its own scratch under that lease
(borrowed_credentials), lets its engine run, and writes a rotation back before the lease is
released (settle_borrow, write_back). A rotation that cannot be written back is kept as a private
recovery (keep_recovery) and reported with RECOVERY_EXIT; a borrow whose run was killed outright
is turned into one at the next start (recover_orphans). `restore-login` puts a kept rotation
back under the lease.

proof/VELDO-0127/live.py loads this file by path for its captures, and the owner's runners take
the same lease and call the same restore-login command. Nothing here confines or launches a
process, and no gate script loads this file (VELDO-0271).

  agent_sandbox.py restore-login [--force] [recovery]
"""
import argparse
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import sys
import tempfile
import time


def beneath(path, root):
    return path == root or root in path.parents


CREDENTIAL_LIMIT = 1 << 20


def scratch_directory(scratch, parts):
    """A descriptor of the directory scratch/<parts>, each component opened (and created 0700 when
    absent) without following a link: a link anywhere on the path refuses, never redirects."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    directory = os.open(scratch, flags)
    try:
        for part in parts:
            try:
                os.mkdir(part, 0o700, dir_fd=directory)
            except FileExistsError:
                pass
            inner = os.open(part, flags, dir_fd=directory)
            os.close(directory)
            directory = inner
    except BaseException:
        os.close(directory)
        raise
    return directory


def seed(scratch, source, relative, store, protected=None):
    """Copy one private state file into the scratch. Returns (resolved source, bytes copied), or
    None when the source is absent. A source in the store, or, for a credential that is written
    back, in a protected path, refuses the start. The destination is created component by component
    without following a link."""
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('invalid private state seed')
    if not source.is_file():
        return None
    real = source.resolve(strict=True)
    if beneath(real, store):
        raise ValueError('private state seed exposes the reuse store')
    if protected is not None and any(beneath(real, p) for p in protected):
        raise ValueError('credential source lies in a protected path: ' + str(real))
    data = real.read_bytes()
    parts = Path(relative).parts
    directory = scratch_directory(scratch, parts[:-1])
    try:
        descriptor = os.open(parts[-1], os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                             0o600, dir_fd=directory)
    finally:
        os.close(directory)
    with os.fdopen(descriptor, 'wb') as handle:
        handle.write(data)
    return real, data


def read_scratch_file(scratch, relative):
    """The bytes of scratch/relative, opened one component at a time without following any link:
    a link an engine planted anywhere on the path is refused, so only the file the borrower
    copied in can be read back. One link, a regular file, at most CREDENTIAL_LIMIT bytes."""
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    directory = os.open(scratch, flags | os.O_DIRECTORY)
    try:
        parts = Path(relative).parts
        for part in parts[:-1]:
            inner = os.open(part, flags | os.O_DIRECTORY, dir_fd=directory)
            os.close(directory)
            directory = inner
        descriptor = os.open(parts[-1], flags | os.O_NONBLOCK, dir_fd=directory)
    finally:
        os.close(directory)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > CREDENTIAL_LIMIT:
            raise ValueError('not a private regular file')
        data = b''
        while len(data) <= CREDENTIAL_LIMIT:
            chunk = os.read(descriptor, CREDENTIAL_LIMIT + 1 - len(data))
            if not chunk:
                return data
            data += chunk
        raise ValueError('larger than %d bytes' % CREDENTIAL_LIMIT)
    finally:
        os.close(descriptor)


class Superseded(Exception):
    """The source no longer holds the bytes copied in at the start: something else wrote it."""


def current_bytes(path):
    """The bytes of `path` now, without following a final link, or None when it is absent, not a
    regular file or larger than CREDENTIAL_LIMIT."""
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    except FileNotFoundError:
        return None
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_size > CREDENTIAL_LIMIT:
            return None
        data = b''
        while len(data) <= CREDENTIAL_LIMIT:
            chunk = os.read(descriptor, CREDENTIAL_LIMIT + 1 - len(data))
            if not chunk:
                return data
            data += chunk
        return None
    finally:
        os.close(descriptor)


def replace_atomically(target, data, expected=None):
    """Replace `target` with `data`: a temporary file beside it, fsync, rename, fsync the directory.
    A reader sees the old file or the new one, never a partial write. The mode stays the source's
    owner bits (credentials are 0600). With `expected`, the target is read again just before the
    rename and is replaced only if it still holds exactly those bytes; otherwise Superseded is
    raised and the target is left as it is. The caller holds the login's lease (take_lease) for the
    whole run, so no other borrower writes the file between the two steps; a CLI used directly on
    the login, outside every lease, is not stopped by it (VELDO-0211)."""
    try:
        mode = stat.S_IMODE(os.stat(target).st_mode) & 0o700 or 0o600
    except FileNotFoundError:
        mode = 0o600
    descriptor, temporary = tempfile.mkstemp(prefix='.' + target.name + '.', suffix='.veldo-tmp',
                                             dir=target.parent)
    try:
        try:
            os.fchmod(descriptor, mode)
            view = memoryview(data)
            while view:
                view = view[os.write(descriptor, view):]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        if expected is not None and current_bytes(target) != expected:
            raise Superseded('the source changed during the run')
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise
    directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def replace_problem(target):
    """Why `target` cannot be replaced the way write-back replaces it, or None: a temporary file is
    created beside it and removed again. The credential itself is never opened for writing, renamed
    or rewritten, so a check at the start of a run cannot overwrite a newer login (VELDO-0211)."""
    try:
        descriptor, temporary = tempfile.mkstemp(prefix='.' + target.name + '.', suffix='.veldo-tmp',
                                                 dir=target.parent)
    except OSError as error:
        return 'write-back to %s is not possible: %s' % (target, error)
    os.close(descriptor)
    os.unlink(temporary)
    return None


def write_back(scratch, credentials):
    """After the run: each credential file the borrower copied in that the CLI changed (a token
    refresh) and that is still one JSON object replaces its source atomically (VELDO-0210).
    Nothing else in the scratch is ever written back, and an unchanged copy leaves the source as it
    is. A source that no longer holds the bytes copied in (a separate login wrote it meanwhile) wins
    over the borrowed copy. Returns what must be kept for recovery instead (VELDO-0211): an
    unreadable or invalid copy, a rotation that drops the refresh token, a failed replacement; each
    as (source, relative, the copy's bytes or None, why)."""
    failures = []
    for real, relative, original in credentials:
        try:
            data = read_scratch_file(scratch, relative)
        except (OSError, ValueError) as error:
            print('agent sandbox: credential %s not written back: %s' % (relative, error),
                  file=sys.stderr, flush=True)
            failures.append((real, relative, None, 'the copy is unreadable: %s' % error))
            continue
        if data == original:
            continue
        try:
            if not isinstance(json.loads(data), dict):
                raise ValueError('not a JSON object')
            require_refresh_tokens(json.loads(original), json.loads(data))
        except Exception as error:  # ValueError, and RecursionError for a deeply nested document
            print('agent sandbox: credential %s changed but not written back: %s' % (relative, error),
                  file=sys.stderr, flush=True)
            failures.append((real, relative, data, 'the copy is not a usable login: %s' % error))
            continue
        try:
            replace_atomically(real, data, expected=original)
        except Superseded as error:
            print('agent sandbox: credential %s changed but not written back: %s' % (relative, error),
                  file=sys.stderr, flush=True)
            continue
        except OSError as error:
            print('agent sandbox: credential %s write-back to %s failed: %s' % (relative, real, error),
                  file=sys.stderr, flush=True)
            failures.append((real, relative, data, 'the write-back failed: %s' % error))
            continue
        print('agent sandbox: credential %s refreshed during the run, written back to %s' % (relative, real),
              file=sys.stderr, flush=True)
    return failures


def require_refresh_tokens(original, rotated):
    """Never replace a refreshable login with a JSON object that silently loses its refresh token."""
    if not isinstance(original, dict):
        return
    for key, value in original.items():
        next_value = rotated.get(key) if isinstance(rotated, dict) else None
        if key in ('refreshToken', 'refresh_token') and value and not next_value:
            raise ValueError('rotated credential is missing a refresh token')
        if isinstance(value, dict):
            require_refresh_tokens(value, next_value)


RECOVERY_EXIT = 74  # EX_IOERR: distinct from a refusal (2) and reported with the run's own status
LEASE_NAME = '.runner-lease'
BORROW_SCHEMA = 'veldo.borrowed-login/v1'


class CredentialRecovery(Exception):
    """A rotated login could not be persisted to its source. `location` holds what was kept: a
    private recovery directory, or (`retained`) the run's scratch when even that could not be
    written. `code` is the run's own exit status. Never a refusal: main reports it with
    RECOVERY_EXIT and the restore command."""

    def __init__(self, location, names, code=None, retained=False):
        super().__init__('credential recovery required for ' + ', '.join(names))
        self.location, self.names, self.code, self.retained = location, names, code, retained


def recovery_message(error, launcher=None):
    launcher = launcher or Path(__file__).resolve()
    status = 'without an exit status' if error.code is None else 'with exit status %s' % error.code
    if error.retained:
        kept = 'the run\'s scratch %s is kept as it is (the recovery store was not writable)' % error.location
    else:
        kept = 'kept privately at %s; restore it with: python3 %s restore-login %s' % (
            error.location, launcher, error.location)
    return ('agent sandbox: CREDENTIAL RECOVERY REQUIRED: %s was not written back to its login '
            '(the run ended %s); %s' % (', '.join(error.names), status, kept))


def borrow_root():
    """Where borrow journals and credential recoveries live: persistent, private, outside every
    login, scratch and tree ($XDG_STATE_HOME/veldo/borrowed-logins, ~/.local/state by default)."""
    state = os.environ.get('XDG_STATE_HOME', '')
    if not os.path.isabs(state):
        state = str(Path.home() / '.local/state')
    return Path(state) / 'veldo' / 'borrowed-logins'


def private_directory(path):
    """`path` as a directory of this uid with mode 0700, made if missing; a link or anything else
    there is refused."""
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = os.lstat(path)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise ValueError('not a private directory of this user: %s' % path)
    os.chmod(path, 0o700)
    return path


def write_private(path, data):
    """A new 0600 file holding `data`, synced, never following or replacing anything at `path`."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(descriptor, view):]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def digest(data):
    return __import__('hashlib').sha256(data).hexdigest()


def same_file(descriptor, info):
    try:
        other = os.fstat(descriptor)
    except OSError:
        return False
    return (other.st_dev, other.st_ino) == (info.st_dev, info.st_ino)


TAKEN_LEASES = set()  # the lease descriptors take_lease opened in this process, never a runner's


def take_lease(login):
    """Hold <login>/.runner-lease, the one lock every user of a login takes: the runners
    (account_lease.sh flocks it before their engine starts and the engine inherits it) and live
    capture (VELDO-0211). A descriptor this process inherited that holds it (the
    runner's) counts: it is checked, not taken again; one a borrow in this process took does not, so
    a second borrow of the login here is busy. Otherwise the lease is taken here,
    never waiting. The file is never created: a login with none has never been leased by a runner,
    and borrowing it must not leave a file in it. Returns the descriptor to close afterwards, or
    None for the runner's own."""
    path = login / LEASE_NAME
    try:
        info = os.stat(path, follow_symlinks=False)
    except FileNotFoundError:
        raise ValueError('borrowed login %s has no lease file %s: borrow it through a runner '
                         '(scripts/account_lease.sh), or create the empty file first' % (login, path)) from None
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('the lease %s is not a regular file' % path)
    for name in os.listdir('/proc/self/fd'):
        descriptor = int(name)
        if descriptor not in TAKEN_LEASES and same_file(descriptor, info):
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                continue  # this process's descriptor, but not the one holding the lease
            return None
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        if not same_file(descriptor, info):
            raise ValueError('the lease %s changed while it was opened' % path)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('borrowed login is busy: %s is held by another run' % path) from None
    except BaseException:
        os.close(descriptor)
        raise
    TAKEN_LEASES.add(descriptor)
    return descriptor


def release(descriptors):
    for descriptor in reversed(descriptors):
        TAKEN_LEASES.discard(descriptor)
        os.close(descriptor)


class Borrow:
    """One borrowed-login run: its scratch, the credentials copied in as (source, relative, bytes),
    the journal that names them outside the scratch, and the descriptors that hold the leases and
    the scratch. `code` is the run's exit status once it is known."""

    def __init__(self, scratch):
        self.scratch, self.credentials, self.journal, self.code = scratch, [], None, None
        self.descriptors = []


def borrow_journal(borrow, root=None):
    """Record the borrow at `root`/<scratch name>/borrow.json before an engine can rotate anything:
    the sources and digests of what was copied in. A run killed outright leaves it, and the next
    start turns its rotated copies into a recovery (recover_orphans) instead of losing them."""
    root = private_directory(root or borrow_root())
    journal = root / borrow.scratch.name
    journal.mkdir(mode=0o700)
    borrow.journal = journal
    write_private(journal / 'borrow.json', json.dumps({
        'schema': BORROW_SCHEMA, 'scratch': str(borrow.scratch), 'pid': os.getpid(), 'started': int(time.time()),
        'credentials': [{'source': str(real), 'relative': relative, 'sha256': digest(data)}
                        for real, relative, data in borrow.credentials]}, indent=1).encode())


def keep_recovery(journal, failures, code=None):
    """Turn `journal` into a recovery: each failed credential's bytes in a private file beside a
    recovery.json naming its source and the digest it held when the run started. The manifest is
    written last, by rename, so a recovery is either complete or still a journal."""
    entries = []
    record = json.loads((journal / 'borrow.json').read_text())
    started = {entry['source']: entry['sha256'] for entry in record['credentials']}
    for number, (real, relative, data, why) in enumerate(failures):
        name = None
        if data is not None:
            name = 'credential-%d.json' % number
            write_private(journal / name, data)
        entries.append({'source': str(real), 'relative': relative, 'file': name,
                        'original_sha256': started.get(str(real)), 'reason': why})
    temporary = journal / 'recovery.json.tmp'
    write_private(temporary, json.dumps({'schema': BORROW_SCHEMA, 'exit': code, 'entries': entries},
                                        indent=1).encode())
    os.replace(temporary, journal / 'recovery.json')
    return journal


def discard_journal(journal):
    if journal is not None:
        shutil.rmtree(journal, ignore_errors=True)


def settle_borrow(borrow):
    """After every engine of the run has stopped, under the leases, with the stop signals blocked
    so a handled signal cannot cut it short: write the rotations back, then drop the journal, or
    keep what could not be written back and raise CredentialRecovery."""
    mask = signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)
    try:
        failures = write_back(borrow.scratch, borrow.credentials)
        if not failures:
            discard_journal(borrow.journal)
            borrow.journal = None
            return
        names = [relative for _, relative, _, _ in failures]
        try:
            location = keep_recovery(borrow.journal, failures, borrow.code)
        except (OSError, ValueError, TypeError) as error:
            print('agent sandbox: the recovery could not be written: %s' % error, file=sys.stderr, flush=True)
            raise CredentialRecovery(borrow.scratch, names, borrow.code, retained=True) from None
        borrow.journal = None
        raise CredentialRecovery(location, names, borrow.code)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)


@contextmanager
def borrowed_credentials(scratch, sources, store, protected=None, root=None):
    """Lease, check and copy credentials, then persist rotations before releasing any lease
    (VELDO-0211). Sources are (path, scratch-relative name) pairs; a missing one stays absent.

    The lease is the login directory's .runner-lease (take_lease): of the directory the source is
    named in, canonical, and of the directory its file really lies in. The caller must stop every
    engine before leaving this context, including on exceptions; it yields a Borrow whose `code`
    the caller sets to the run's exit status."""
    borrow = Borrow(scratch)
    try:
        named = [(source, relative) for source, relative in sources if source.is_file()]
        resolved = [(source.resolve(strict=True), relative) for source, relative in named]
        if len({real for real, _ in resolved}) != len(resolved):
            raise ValueError('duplicate borrowed credential source')
        for real, _ in resolved:
            if beneath(real, store) or any(beneath(real, p) for p in (protected or [])):
                raise ValueError('credential source lies in a protected path: ' + str(real))
        if resolved:
            # Held from here to the end: a sweep sees a live borrow by this lock (recover_orphans).
            holder = os.open(scratch, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            borrow.descriptors.append(holder)
            fcntl.flock(holder, fcntl.LOCK_SH | fcntl.LOCK_NB)
        logins = {source.parent.resolve(strict=True) for source, _ in named} | {real.parent for real, _ in resolved}
        for login in sorted(logins):
            descriptor = take_lease(login)
            if descriptor is not None:
                borrow.descriptors.append(descriptor)
        for real, relative in sorted(resolved):
            original = current_bytes(real)
            try:
                valid = isinstance(json.loads(original), dict)
            except (TypeError, ValueError, RecursionError):
                valid = False
            if not valid:
                raise ValueError('borrowed credential is not a JSON object: ' + str(real))
            problem = replace_problem(real)
            if problem:
                raise PermissionError(problem)
            copied = seed(scratch, real, relative, store, protected)
            if copied is None:
                raise ValueError('borrowed credential disappeared: ' + str(real))
            borrow.credentials.append((real, relative, copied[1]))
        if borrow.credentials:
            borrow_journal(borrow, root)
        try:
            yield borrow
        finally:
            if borrow.credentials:
                settle_borrow(borrow)
    finally:
        release(borrow.descriptors)


def recover_orphans(root=None):
    """Turn the journal of every borrow whose run was killed outright (its scratch held by no
    process any more) into a recovery when a copy differs from what was copied in, and report it;
    an unchanged one is dropped. A journal whose scratch is gone is reported and dropped. Never
    writes a login: restore_login does that, under its lease. A borrower runs it before it borrows."""
    root = root or borrow_root()
    try:
        journals = sorted(p for p in root.iterdir() if (p / 'borrow.json').is_file()
                          and not (p / 'recovery.json').exists())
    except OSError:
        return
    for journal in journals:
        try:
            record = json.loads((journal / 'borrow.json').read_text())
            scratch = Path(record['scratch'])
        except FileNotFoundError:
            continue  # settled meanwhile
        except (OSError, ValueError, KeyError, TypeError) as error:
            print('agent sandbox: borrow journal %s not read: %s' % (journal, error), file=sys.stderr, flush=True)
            continue
        try:
            descriptor = os.open(scratch, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        except OSError as error:
            if (journal / 'borrow.json').is_file() and not (journal / 'recovery.json').exists():
                # Its run settled the journal before removing the scratch, so the scratch went first:
                # removed by hand, or a runtime directory gone with a reboot.
                print('agent sandbox: borrow %s lost its scratch %s (%s); nothing of it can be recovered'
                      % (journal, scratch, error.strerror), file=sys.stderr, flush=True)
                discard_journal(journal)
            continue
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                continue  # a live run
            if not (journal / 'borrow.json').is_file() or (journal / 'recovery.json').exists():
                continue  # it ended meanwhile
            failures = []
            for entry in record['credentials']:
                try:
                    data = read_scratch_file(scratch, entry['relative'])
                except (OSError, ValueError) as error:
                    failures.append((entry['source'], entry['relative'], None,
                                     'a killed run left an unreadable copy: %s' % error))
                    continue
                if digest(data) != entry['sha256']:
                    failures.append((entry['source'], entry['relative'], data,
                                     'a killed run left a rotated copy that was never written back'))
            if not failures:
                discard_journal(journal)
                continue
            keep_recovery(journal, failures)
            print(recovery_message(CredentialRecovery(journal, [r for _, r, _, _ in failures])),
                  file=sys.stderr, flush=True)
        except (OSError, ValueError, KeyError, TypeError) as error:
            print('agent sandbox: borrow %s not recovered: %s' % (journal, error), file=sys.stderr, flush=True)
        finally:
            os.close(descriptor)


def restore_login(recovery=None, force=False):
    """Restore a recovery (VELDO-0211): under each login's lease, the kept copy replaces its source
    when the source still holds the bytes it held when the run started (with `force`, whatever it
    holds), is one JSON object and keeps every refresh token the source has. Once every kept copy is
    restored, the recovery is removed. Without `recovery`, the recoveries waiting are listed."""
    root = borrow_root()
    if recovery is None:
        found = sorted(p for p in root.iterdir() if (p / 'recovery.json').is_file()) if root.is_dir() else []
        for path in found:
            for entry in json.loads((path / 'recovery.json').read_text())['entries']:
                print('%s\t%s\t%s' % (path, entry['source'], entry['reason']))
        if not found:
            print('no credential recovery is waiting in %s' % root)
        return 0
    recovery = Path(recovery)
    info = os.lstat(recovery)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError('not a private recovery directory of this user: %s' % recovery)
    manifest = json.loads((recovery / 'recovery.json').read_text())
    if manifest.get('schema') != BORROW_SCHEMA:
        raise ValueError('not a borrowed-login recovery: %s' % recovery)
    entries = [entry for entry in manifest['entries'] if entry.get('file')]
    for entry in manifest['entries']:
        if not entry.get('file'):
            print('%s: nothing was kept (%s)' % (entry['source'], entry['reason']))
    descriptors = []
    try:
        sources = [Path(entry['source']) for entry in entries]
        for login in sorted({source.parent for source in sources}):
            descriptor = take_lease(login)
            if descriptor is not None:
                descriptors.append(descriptor)
        for entry, source in zip(entries, sources):
            data = read_scratch_file(recovery, entry['file'])
            current = current_bytes(source)
            if current is None:
                raise ValueError('%s is missing or not a regular file' % source)
            if digest(current) != entry['original_sha256'] and not force:
                raise ValueError('%s changed since the run started (a new login?); it is left as it is. '
                                 'To overwrite it anyway: restore-login --force %s' % (source, recovery))
            value = json.loads(data)
            if not isinstance(value, dict):
                raise ValueError('the kept copy for %s is not a JSON object' % source)
            require_refresh_tokens(json.loads(current), value)
            replace_atomically(source, data, expected=current)
            print('restored %s' % source)
    finally:
        release(descriptors)
    shutil.rmtree(recovery)
    print('recovery %s removed' % recovery)
    return 0


GRACE_SECONDS = 10
STOP_SIGNALS = (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)


class Interrupted(Exception):
    pass


class Stop:
    """TERM, INT and HUP while a borrow is held. With no child registered (live capture), a signal
    raises Interrupted in the borrower, so its context exits and the credentials are written back;
    once the borrower set `closing`, a signal is recorded and the write-back is not cut short. A
    borrower that registered a child (child, tree_started) has the signal forwarded to the child's
    process group, and a group still alive GRACE_SECONDS later is killed. A signal the borrower
    inherited as ignored stays ignored."""

    def __init__(self):
        self.pid = self.number = None
        self.reaped = self.closing = self.started = False
        self.previous = {}

    def __enter__(self):
        threading = __import__('threading')
        if threading.current_thread() is threading.main_thread():
            for number in STOP_SIGNALS:
                if signal.getsignal(number) != signal.SIG_IGN:
                    self.previous[number] = signal.signal(number, self.stop)
            self.previous[signal.SIGALRM] = signal.signal(signal.SIGALRM, self.kill)
        return self

    def __exit__(self, *_):
        if self.previous:
            signal.alarm(0)
        for number, handler in self.previous.items():
            signal.signal(number, handler)

    def child(self, pid):
        self.pid = pid

    def tree_started(self):
        """The child reported its start: a stop recorded meanwhile goes on now."""
        self.started = True
        if self.number is not None:
            self.signal_group(self.number)
            signal.alarm(GRACE_SECONDS)

    def in_child(self):
        """In the forked child, before anything else: the default action for what this caught."""
        for number in self.previous:
            signal.signal(number, signal.SIG_DFL)

    def signal_group(self, number):
        if self.reaped:
            return  # the child is reaped: its pid may name another process now
        try:
            os.killpg(self.pid, number)
        except ProcessLookupError:
            try:
                os.kill(self.pid, number)  # not yet in its own session
            except ProcessLookupError:
                pass

    def stop(self, number, _frame):
        if self.number is not None:
            # Asked again: stop the group now. Cleanup is already under way and is not interrupted.
            if self.pid is not None:
                self.signal_group(signal.SIGKILL)
            return
        self.number = number
        if self.pid is None and not self.closing:
            raise Interrupted(number)
        if self.pid is None or not self.started:
            return  # still starting: the borrower ends the child once it sees the stop
        self.signal_group(number)
        signal.alarm(GRACE_SECONDS)

    def kill(self, _number, _frame):
        if self.pid is not None:
            self.signal_group(signal.SIGKILL)


def main():
    if sys.argv[1:2] == ['restore-login']:
        parser = argparse.ArgumentParser(prog='agent_sandbox.py restore-login', description=restore_login.__doc__)
        parser.add_argument('--force', action='store_true', help='replace a source that changed since the run')
        parser.add_argument('recovery', nargs='?', help='a recovery directory; none lists them')
        args = parser.parse_args(sys.argv[2:])
        try:
            return restore_login(args.recovery, args.force)
        except (OSError, ValueError, KeyError, TypeError) as error:
            print('restore-login refused: %s' % error, file=sys.stderr)
            return 2
    print('agent_sandbox.py: the only command is restore-login [--force] [recovery]', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main())
