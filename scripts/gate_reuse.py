"""Content identities and a private, authenticated, append-only result store."""
import hashlib
import importlib.util
import hmac
import json
import os
from pathlib import Path
import stat
import tempfile
import warnings

_spec = importlib.util.spec_from_file_location('reuse_evidence',
    Path(__file__).resolve().parents[1] / '.veldo/reuse_evidence.py')
E = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(E)
SCHEMA = E.SCHEMA


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def tree_identity(path):
    """Read every regular file, directory name and mode; ambiguity is a miss upstream."""
    path = Path(path)
    result = {}

    visited = set()

    def visit(current, name):
        visited.add(current.absolute())
        info = current.lstat()
        mode = stat.S_IMODE(info.st_mode)
        if stat.S_ISREG(info.st_mode):
            value = hashlib.sha256(current.read_bytes()).hexdigest()
        elif stat.S_ISDIR(info.st_mode):
            value = 'directory'
            for child in sorted(current.iterdir()):
                visit(child, name + '/' + child.name)
        elif stat.S_ISLNK(info.st_mode):
            target = current.resolve(strict=True)
            # Directory back-links are represented by the already visited target path.
            value = ['symlink', os.readlink(current), str(target)]
            if target not in visited:
                visit(target, name + '/@target')
        else:
            raise ValueError('unclosed runtime input: ' + str(current))
        result[name] = [mode, value]
    visit(path, '.')
    return result


class Store:
    """A record cannot be forged by editing its data or recomputing a plain checksum.

    The key stays separate from records. Agent domains cannot read or write it;
    the unconfined owner and orchestrator are trusted. I/O errors are misses.
    """
    def __init__(self, directory, repository):
        self.directory = None
        self.secret = None
        self.integrity_errors = []
        try:
            self.directory = Path(directory).expanduser().resolve()
            root = Path(repository).resolve()
            if self.directory == root or root in self.directory.parents:
                return
            # Worker runtime trees must never contain coordinator credentials.
            if any(self.directory == Path(p).resolve() or Path(p).resolve() in self.directory.parents
                   for p in ('/usr', '/lib', '/lib64', '/etc', '/dev', '/proc', '/run', '/sys')):
                return
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            self._private(self.directory, directory=True)
            keypath = self.directory / 'authentication.key'
            secret = os.urandom(32)
            # Publish only complete keys. Concurrent creators use the winning key.
            self._publish(keypath, secret, key_creation=True)
            self._private(keypath)
            self.secret = E.probe(self.directory)
            if len(self.secret) != 32:
                self.secret = None
        except (OSError, ValueError, TypeError, RuntimeError):
            self.secret = None

    @staticmethod
    def _private(path, directory=False):
        info = path.lstat()
        kind = stat.S_ISDIR if directory else stat.S_ISREG
        if not kind(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('cache path must be private and owned')

    def _publish(self, target, body, key_creation=False):
        fd, name = tempfile.mkstemp(prefix='.pending-', dir=self.directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(name, target)
            except FileExistsError:
                if not key_creation and target.read_bytes() != body:
                    self.integrity_errors.append(target.name)
                    # Poisoned identities stay misses until explicitly removed.
                    (self.directory / (target.name + '.conflict')).touch(mode=0o600)
                    warnings.warn('reuse integrity failure: conflicting record ' + target.name)
                    raise ValueError('conflicting cache record')
        finally:
            os.unlink(name)

    def _path(self, key):
        if not isinstance(key, str) or len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError('invalid reuse key')
        return self.directory / (key + '.json')

    def get(self, key):
        if self.secret is None:
            return None
        try:
            return E.record(self.directory, key, self.secret)
        except (OSError, ValueError, TypeError, KeyError):
            return None

    def put(self, key, result):
        if self.secret is None:
            return False
        try:
            if E.probe(self.directory) != self.secret:
                return False
            payload = dict(schema=SCHEMA, key=key, result=result, provenance=E.PROVENANCE)
            document = dict(payload=payload,
                            mac=hmac.new(self.secret, canonical(payload), hashlib.sha256).hexdigest())
            self._publish(self._path(key), canonical(document))
            return True
        except (OSError, ValueError, TypeError):
            return False
