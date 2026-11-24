"""Fixture-only store-open evidence, installed in the runner and fixture interpreters.

Python audit events fire synchronously, including opens outside Collection. /proc
supplies the holders at each event; directory/lock/log descriptors are diagnostics.
"""
import fcntl
import json
import os
from pathlib import Path
import stat
import sys
import threading
from urllib.parse import unquote

_ROOTS = set()
_LOCAL = threading.local()
_INSTALLED = False


def store_file(path):
    return (os.path.basename(path) in ('chroma.sqlite3', 'chroma.sqlite3-wal', 'chroma.sqlite3-shm')
            and not os.path.isdir(path))


def descriptors(directory, exclude=()):
    """Every matching fd, including the path, kind and process command line."""
    directory = os.path.realpath(directory)
    found = []
    for entry in os.listdir('/proc'):
        if not entry.isdigit() or int(entry) in exclude:
            continue
        try:
            for fd in os.listdir('/proc/%s/fd' % entry):
                try:
                    link = '/proc/%s/fd/%s' % (entry, fd)
                    path = os.readlink(link)
                    target = path.removesuffix(' (deleted)')
                    if target != directory and not target.startswith(directory + os.sep):
                        continue
                    kind = 'directory' if stat.S_ISDIR(os.stat(link).st_mode) else (
                        'store' if store_file(target) else 'auxiliary')
                    command = Path('/proc/%s/cmdline' % entry).read_bytes().replace(b'\0', b' ').decode(errors='replace').strip()
                    found.append(dict(pid=int(entry), fd=int(fd), path=path, kind=kind, command=command))
                except OSError:
                    continue
        except OSError:
            continue
    return found


def _audit(event, args):
    if getattr(_LOCAL, 'busy', False) or event not in ('open', 'sqlite3.connect', 'fcntl.flock', 'os.scandir'):
        return
    _LOCAL.busy = True
    try:
        path = args[0]
        if isinstance(path, int):
            try:
                path = os.readlink('/proc/self/fd/%d' % path)
            except OSError:
                # A process-global hook must not break unrelated audited calls on
                # stale fds or when a later suite cannot inspect /proc/self/fd.
                return
        if not isinstance(path, (str, bytes, os.PathLike)):
            return
        path = os.fsdecode(path)
        if event == 'sqlite3.connect' and path.startswith('file:'):
            path = unquote(path[5:].split('?', 1)[0])
        path = os.path.realpath(path)
        for root in tuple(_ROOTS):
            for relative in ('mem0_memory/data', 'memory_kb/data'):
                store = str(Path(root) / relative)
                if path != store and not path.startswith(store + os.sep):
                    continue
                if event == 'fcntl.flock' and (os.path.basename(path) != 'veldo-store.lock'
                                               or not args[1] & fcntl.LOCK_EX):
                    continue
                kind = 'store' if event in ('open', 'sqlite3.connect') and store_file(path) else 'diagnostic'
                held = descriptors(store, {os.getpid()})
                record = dict(event=event, kind=kind, pid=os.getpid(), path=path, store=store,
                              command=Path('/proc/self/cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace').strip(),
                              others=sorted({h['pid'] for h in held if h['kind'] == 'store'}), holders=held)
                # One append syscall keeps concurrent JSON records whole.
                try:
                    fd = os.open(str(Path(root) / 'opens.jsonl'), os.O_WRONLY | os.O_APPEND)
                except FileNotFoundError:
                    # Fixture teardown has removed the evidence file; never recreate it.
                    continue
                try:
                    os.write(fd, (json.dumps(record) + '\n').encode())
                finally:
                    os.close(fd)
    finally:
        _LOCAL.busy = False


def install(root):
    global _INSTALLED
    root = os.path.realpath(root)
    (Path(root) / 'opens.jsonl').touch(exist_ok=True)
    _ROOTS.add(root)
    if not _INSTALLED:
        sys.addaudithook(_audit)
        _INSTALLED = True


def evidence(events, directory):
    """The same verdict input for the suite and its controls; diagnostics never convict."""
    directory = os.path.realpath(directory)
    matching = [e for e in events if e['path'].startswith(directory + os.sep) or e['path'] == directory]
    opened = [e for e in matching if e['kind'] == 'store']
    return opened, [e for e in opened if e['others']], [e for e in matching if e['kind'] == 'diagnostic']


def unobserved(events, directory, since=0):
    """Holders without a preceding store-open event, at each event in this window.

    Check the prefix at each event, so a later hook cannot excuse an earlier
    unobserved holder. Auxiliary descriptors never count as store evidence.
    """
    directory = os.path.realpath(directory)
    known, missing = set(), set()
    for index, event in enumerate(events):
        if event['path'] != directory and not event['path'].startswith(directory + os.sep):
            continue
        if event['kind'] == 'store':
            known.add(event['pid'])
        if index >= since:
            missing.update(h['pid'] for h in event['holders'] if h['kind'] == 'store' and h['pid'] not in known)
    return missing
