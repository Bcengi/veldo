"""One private safety copy and a fresh light check around every memory switch."""
import contextlib
import fcntl
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

from importlib.util import spec_from_file_location, module_from_spec
_spec = spec_from_file_location('check_memory', Path(__file__).with_name('control_memory.py'))
M = module_from_spec(_spec)
_spec.loader.exec_module(M)


def private_dir(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    M.checked(str(path), 'copies')
    if path.stat().st_mode & 0o077:
        raise M.Refused('invalid_input:memory:copies:permissions')


SIDECARS = ('-wal', '-shm', '-journal')
CHROMA = 'chroma.sqlite3'
QUIET, ATTEMPTS = 1.0, 8


def idle(source):
    """A WAL database no one holds open: no shared memory, and no WAL or an empty one, so its file holds
    every commit. Any open but an immutable one would create the missing files in the owner's directory."""
    source = Path(source)
    wal, shm = Path(str(source) + '-wal'), Path(str(source) + '-shm')
    with source.open('rb') as stream:
        return (stream.read(20)[18:20] == b'\x02\x02' and not shm.exists()
                and (not wal.exists() or wal.stat().st_size == 0))


def source_uri(source):
    """How a store's SQLite database is opened without writing beside it: a live store's shared memory
    read-only, an idle one as it lies. Returns the URI and whether it is idle."""
    quiet = idle(source)
    return Path(source).as_uri() + ('?mode=ro&immutable=1' if quiet else '?mode=ro&readonly_shm=1'), quiet


def backup(source, target, part='copy', sleep=time.sleep):
    """SQLite's online backup in one step, which holds one read transaction, so the copy is whole while the
    owner's assistant commits. An idle database read as it lies is kept only when no writer opened or
    changed it meanwhile; otherwise it is read again."""
    source, target = Path(source), Path(target)
    for attempt in range(ATTEMPTS):
        uri, quiet = source_uri(source)
        before = source.stat()
        with contextlib.closing(sqlite3.connect(uri, uri=True)) as src:
            with contextlib.closing(sqlite3.connect(target)) as dst:
                src.backup(dst)
        after = source.stat()
        if not quiet or ((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns) and idle(source)):
            target.chmod(0o600)
            return
        target.unlink()
        sleep(QUIET)
    raise M.Refused('unavailable_service:memory:%s:copy_busy' % part, str(source))


def is_sqlite(path):
    with Path(path).open('rb') as stream:
        return stream.read(16) == b'SQLite format 3\x00'


def copy_data(source, target, part='copy'):
    source, target = Path(source), Path(target)
    M.checked(str(source), part, 'directory' if source.is_dir() else 'file')
    if source.is_dir() and (source / CHROMA).is_file():
        copy_chroma(source, target, part)
    elif source.is_dir():
        target.mkdir(mode=0o700)
        for child in source.iterdir():
            if child.is_symlink():
                # A link inside a store is copied as the link, never followed.
                os.symlink(os.readlink(child), target / child.name)
            elif not child.name.endswith(SIDECARS):
                copy_data(child, target / child.name, part)
    elif is_sqlite(source):
        backup(source, target, part)
    else:
        shutil.copyfile(source, target)
        target.chmod(0o600)


def segment_stamps(source):
    """Chroma's index segment files: everything beside its SQLite database except SQLite's own. A link is
    stamped as the link, never followed."""
    stamps = {}
    for child in M.listed(str(source), 'copy'):
        if child.name != CHROMA and not child.name.endswith(SIDECARS) and (
                child.is_symlink() or child.is_file(follow_symlinks=False)):
            info = child.stat(follow_symlinks=False)
            stamps[os.path.relpath(child.path, source)] = (info.st_ino, info.st_size, info.st_mtime_ns, child.is_symlink())
    return stamps


def copy_link(source, name, target, part):
    """A link inside a Chroma directory is kept as a link into the copy, to the same place; one leading out
    of the store is never followed and refused."""
    resolved = os.path.realpath(source / name)
    if not M.within(resolved, source):
        raise M.Refused('invalid_input:memory:%s:link_outside' % part, str(source / name))
    destination = target / name
    os.symlink(os.path.relpath(target / os.path.relpath(resolved, os.path.realpath(source)), destination.parent), destination)


def copy_chroma(source, target, part, attempts=None, sleep=time.sleep):
    """A consistent copy of a Chroma directory that another Chroma may hold open.

    Chroma rewrites its index segment files only when it persists them and replays newer writes from its
    SQLite log. chromadb 1.x persists through its Rust local HNSW writer (rust/segment/src/local_hnsw.rs,
    apply_log_chunk): it writes the index files in place with write(2), so their mtime changes, then
    index_metadata.pickle, and only then records the persisted sequence in SQLite's max_seq_id table; the log
    is purged after that, never past the lowest persisted sequence, and replayed above it on open. So the
    segment files are copied first, then the SQLite database through the online backup, and the copy is kept
    only when no segment file changed from before the first byte to after the backup and none changed within
    QUIET seconds before it; otherwise it is retried. A SQLite copy then never claims a sequence its index
    files lack. Links are copied as links that stay inside the copy, never followed."""
    for attempt in range(attempts or ATTEMPTS):
        before = segment_stamps(source)
        newest = max((stamp[2] for stamp in before.values()), default=0)
        if time.time_ns() - newest >= QUIET * 1e9:
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(mode=0o700)
            for name, stamp in before.items():
                destination = target / name
                for parent in reversed(destination.relative_to(target).parents[:-1]):
                    (target / parent).mkdir(mode=0o700, exist_ok=True)
                if stamp[3]:
                    copy_link(source, name, target, part)
                    continue
                shutil.copyfile(source / name, destination, follow_symlinks=False)
                destination.chmod(0o600)
            backup(source / CHROMA, target / CHROMA, part)
            if segment_stamps(source) == before:
                return attempt + 1
        sleep(min(QUIET * 2 ** attempt, 30))
    if target.exists():
        shutil.rmtree(target)
    raise M.Refused('unavailable_service:memory:%s:copy_busy' % part, str(source))


def cause(error):
    """The adapter's named reason a check could not run, if it gave one."""
    named = error.args[1] if isinstance(error, ValueError) and len(error.args) > 1 else None
    return 'cause=%s' % named if named else ''


def preflight(definition):
    """Exercise readers and search dependencies before setup writes host state."""
    for part, entry in definition['parts'].items():
        try:
            result = probe(part, entry, 'preflight')
        except (OSError, ValueError, KeyError, sqlite3.Error, subprocess.SubprocessError) as error:
            raise M.Refused('unavailable_service:memory:%s:adapter' % part, cause(error)) from None
        if not result['found']:
            raise M.Refused('missing_evidence:memory:%s:lost' % part)


def snapshot(entry, scratch):
    """claude-mem's search runs in a worker that writes its data directory, so it gets its own private
    home holding a consistent copy of the named store, never the store itself."""
    home = Path(scratch) / 'home'
    data = home / '.claude-mem'
    data.mkdir(mode=0o700, parents=True)
    backup(Path(entry['data']) / 'claude-mem.db', data / 'claude-mem.db', 'claude_mem')
    if (Path(entry['data']) / 'chroma').is_dir():
        copy_chroma(Path(entry['data']) / 'chroma', data / 'chroma', 'claude_mem')
    return home


def probe(part, entry, operation, sample=None, scratch=None):
    interpreter = entry.get('interpreter', sys.executable)
    request = dict(part=part, entry=entry, operation=operation, sample=sample or [])
    adapter = Path(__file__).with_name('control_memory_adapter.py')
    with tempfile.TemporaryDirectory(prefix='probe-', dir=scratch) as private:
        try:
            if part == 'claude_mem':
                request['home'] = str(snapshot(entry, private))
            result = subprocess.run([interpreter, '-B', str(adapter)], input=json.dumps(request), capture_output=True,
                                    text=True, timeout=3600 if part == 'claude_mem' else 180)
        finally:
            if 'home' in request:
                # The worker runs in sessions of its own, so a check cut short leaves it to this sweep.
                spec = spec_from_file_location('memory_adapter', adapter)
                module = module_from_spec(spec)
                spec.loader.exec_module(module)
                module.stop(request['home'])
    if result.returncode:
        raise ValueError('adapter failed')
    answer = json.loads(result.stdout)
    if 'error' in answer:
        raise ValueError('adapter unavailable', answer.get('cause'))
    return answer


def check(root, definition, part, phase):
    if part not in M.PARTS or phase not in ('before', 'after'):
        raise M.Refused('invalid_input:memory:check')
    entry = definition['parts'][part]
    directory = Path(root) / 'memory'
    private_dir(directory)
    copies = directory / 'copies'
    private_dir(copies)
    target, evidence = copies / part, copies / (part + '.json')
    detail = 'store=%s copy=%s' % (entry['data'], target)
    fd = os.open(directory / (part + '.lock'), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        if phase == 'before':
            if not target.exists():
                staging = Path(tempfile.mkdtemp(prefix='copy-', dir=copies))
                try:
                    try:
                        copy_data(entry['data'], staging / part, part)
                    except M.Refused as error:
                        raise M.Refused(error.code, detail) from None
                    (staging / part).rename(target)
                finally:
                    shutil.rmtree(staging)
            result = probe(part, entry, 'before', scratch=directory)
            saved = dict(result, source=entry['data'])
            tmpfd, temporary = tempfile.mkstemp(dir=copies)
            with os.fdopen(tmpfd, 'w') as out:
                json.dump(saved, out)
            os.replace(temporary, evidence)
            sample_size = len(result['sample'])
        else:
            saved = json.loads(evidence.read_text())
            result = probe(part, entry, 'after', saved['sample'], scratch=directory)
            if result['count'] < saved['count'] or not result['found']:
                raise M.Refused('missing_evidence:memory:%s:lost' % part, detail)
            sample_size = len(saved['sample'])
        return dict(part=part, phase=phase, outcome='passed', path=entry['data'], copy=str(target),
                    count=result['count'], sample_size=sample_size, metrics=dict(memory_checks_passed=1))
    except (OSError, ValueError, KeyError, sqlite3.Error, subprocess.SubprocessError) as error:
        raise M.Refused('unavailable_service:memory:%s:adapter' % part, ' '.join(filter(None, (detail, cause(error))))) from None
    finally:
        os.close(fd)
