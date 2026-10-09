"""One private safety copy and a fresh light check around every memory switch."""
import fcntl
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

from importlib.util import spec_from_file_location, module_from_spec
_spec = spec_from_file_location('check_memory', Path(__file__).with_name('control_memory.py'))
M = module_from_spec(_spec)
_spec.loader.exec_module(M)


def private_dir(path):
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    M.checked(str(path), 'copies')
    if path.stat().st_mode & 0o077:
        raise M.Refused('invalid_input:memory:copies:permissions')


def copy_data(source, target):
    source, target = Path(source), Path(target)
    M.checked(str(source), 'copy', 'directory' if source.is_dir() else 'file')
    if source.is_dir():
        target.mkdir(mode=0o700)
        for child in source.iterdir():
            if child.name.endswith(('-wal', '-shm', '-journal')):
                continue
            copy_data(child, target / child.name)
    else:
        with source.open('rb') as stream:
            sqlite = stream.read(16) == b'SQLite format 3\x00'
        if sqlite:
            # Include committed WAL rows while the assistant still has a connection.
            with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src:
                with sqlite3.connect(target) as dst:
                    src.backup(dst)
        else:
            shutil.copyfile(source, target)
        target.chmod(0o600)


def copy_version(source):
    source = Path(source)
    paths = [source] + (list(source.rglob('*')) if source.is_dir() else [])
    return {str(p): (p.lstat().st_ino, p.lstat().st_size, p.lstat().st_mtime_ns,
                     p.lstat().st_ctime_ns) for p in paths}


def preflight(definition):
    """Exercise readers and search dependencies before setup writes host state."""
    M.no_nested_links(definition)
    for part, entry in definition['parts'].items():
        try:
            before = probe(part, entry, 'before')
            after = probe(part, entry, 'after', before['sample'])
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            raise M.Refused('unavailable_service:memory:%s:adapter' % part) from None
        if after['count'] < before['count'] or not after['found']:
            raise M.Refused('missing_evidence:memory:%s:lost' % part)


def probe(part, entry, operation, sample=None):
    interpreter = entry.get('interpreter', sys.executable)
    request = dict(part=part, entry=entry, operation=operation, sample=sample or [])
    result = subprocess.run([interpreter, '-B', str(Path(__file__).with_name('control_memory_adapter.py'))],
                            input=json.dumps(request), capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise ValueError('adapter failed')
    answer = json.loads(result.stdout)
    if 'error' in answer:
        raise ValueError('adapter unavailable')
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
                    initial = copy_version(entry['data'])
                    copy_data(entry['data'], staging / part)
                    if copy_version(entry['data']) != initial:
                        raise M.Refused('unavailable_service:memory:%s:copy_busy' % part, detail)
                    (staging / part).rename(target)
                finally:
                    shutil.rmtree(staging)
            result = probe(part, entry, 'before')
            saved = dict(result, source=entry['data'])
            tmpfd, temporary = tempfile.mkstemp(dir=copies)
            with os.fdopen(tmpfd, 'w') as out:
                json.dump(saved, out)
            os.replace(temporary, evidence)
            sample_size = len(result['sample'])
        else:
            saved = json.loads(evidence.read_text())
            result = probe(part, entry, 'after', saved['sample'])
            if result['count'] < saved['count'] or not result['found']:
                raise M.Refused('missing_evidence:memory:%s:lost' % part, detail)
            sample_size = len(saved['sample'])
        return dict(part=part, phase=phase, outcome='passed', path=entry['data'], copy=str(target),
                    count=result['count'], sample_size=sample_size)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError):
        raise M.Refused('unavailable_service:memory:%s:adapter' % part, detail) from None
    finally:
        os.close(fd)
