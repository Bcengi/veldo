"""Content identities and a private, authenticated, append-only result store."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import stat
import tempfile

SCHEMA = 'veldo.reuse/v1'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False).encode('ascii')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def tree_identity(path):
    """Read every regular file, directory name and mode; ambiguity is a miss upstream."""
    path = Path(path)
    result = {}

    def visit(current, name):
        info = current.lstat()
        mode = stat.S_IMODE(info.st_mode)
        if stat.S_ISREG(info.st_mode):
            value = hashlib.sha256(current.read_bytes()).hexdigest()
        elif stat.S_ISDIR(info.st_mode):
            value = 'directory'
            for child in sorted(current.iterdir()):
                visit(child, name + '/' + child.name)
        else:
            raise ValueError('unclosed runtime input: ' + str(current))
        result[name] = [mode, value]
    visit(path, '.')
    return result


class Store:
    """A record cannot be forged by editing its data or recomputing a plain checksum.

    The key stays separate from records. Code executing as this uid can steal it and is
    outside the authentication boundary. I/O failures are always cache misses.
    """
    def __init__(self, directory, repository):
        self.directory = Path(directory).expanduser().resolve()
        self.secret = None
        try:
            root = Path(repository).resolve()
            if self.directory == root or root in self.directory.parents:
                return
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            self._private(self.directory, directory=True)
            keypath = self.directory / 'authentication.key'
            secret = os.urandom(32)
            # Publish only complete keys. Concurrent creators use the winning key.
            self._publish(keypath, secret)
            self._private(keypath)
            self.secret = keypath.read_bytes()
            if len(self.secret) != 32:
                self.secret = None
        except (OSError, ValueError):
            self.secret = None

    @staticmethod
    def _private(path, directory=False):
        info = path.lstat()
        kind = stat.S_ISDIR if directory else stat.S_ISREG
        if not kind(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('cache path must be private and owned')

    def _publish(self, target, body):
        fd, name = tempfile.mkstemp(prefix='.pending-', dir=self.directory)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(name, target)
            except FileExistsError:
                pass
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
            path = self._path(key)
            self._private(path)
            if path.stat().st_size > 32 * 1024 * 1024:
                return None
            raw = path.read_bytes()
            document = json.loads(raw)
            if raw != canonical(document) or set(document) != {'payload', 'mac'}:
                return None
            payload = document['payload']
            expected = hmac.new(self.secret, canonical(payload), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, document['mac']):
                return None
            if set(payload) != {'schema', 'key', 'result'} or payload['schema'] != SCHEMA or payload['key'] != key:
                return None
            return payload['result']
        except (OSError, ValueError, TypeError, KeyError):
            return None

    def put(self, key, result):
        if self.secret is None:
            return False
        try:
            payload = dict(schema=SCHEMA, key=key, result=result)
            document = dict(payload=payload,
                            mac=hmac.new(self.secret, canonical(payload), hashlib.sha256).hexdigest())
            self._publish(self._path(key), canonical(document))
            return True
        except (OSError, ValueError, TypeError):
            return False
