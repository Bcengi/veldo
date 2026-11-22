#!/usr/bin/env python3
"""The one reader of a deployment's installation folder (VELDO-0259, schema veldo.installation/v1).

Veldo is a product; each factory is one deployment of it. What belongs to one deployment (who its owner
is, its git identities, approvers, channels, model accounts, hosts, ports, tracker sites, publisher, its
own connectors, services and workflows, the personal-setup patterns, the decision map and the history
records) lives in ONE installation folder the product reads and never contains. This module is the only
code that opens that folder. Everything else asks it for a named key.

WHERE THE FOLDER IS, in a fixed order:
  1. the VELDO_INSTALLATION environment variable, when set and not empty;
  2. else $XDG_CONFIG_HOME/veldo/installation, when XDG_CONFIG_HOME is an absolute path;
  3. else ~/.config/veldo/installation.
That is the same configuration root that already holds host_trust.json. Every load prints one line
naming the folder it resolved and how, or that none was found.

THE LAYOUT is the one installation schema of VELDO-0253 AC1 (docs/installation.md documents it). This
reader defines no layout of its own and reads these kinds of it: installation.yaml, connectors/,
services/ and workflows/ (an installation file with the same id as the product's own overrides it),
patterns/ (read only by scripts/check_personal_setup.py), decisions/ and records/ (listed, never read as
configuration).

NOBODY IS A DEFAULT. A value the product needs is a named key. Absent, it is refused by name as
installation_missing:<key>; present and failing its schema, installation_invalid:<key>. No key ever falls
back to a built-in person, account, host or path. A secret is a reference by name ({secret: <name>});
a literal where a secret belongs is installation_invalid.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

# Git runs only through the shared boundary, loaded by sibling path.
import importlib.util as _git_importlib
_git_spec = _git_importlib.spec_from_file_location('veldo_git_process', Path(__file__).resolve().with_name('git_process.py'))
_git_process = _git_importlib.module_from_spec(_git_spec)
_git_spec.loader.exec_module(_git_process)

SCHEMA = 'veldo.installation/v1'
PATTERNS_SCHEMA = 'veldo.installation.patterns/v1'
ENVIRONMENT = 'VELDO_INSTALLATION'
SETTINGS_FILE = 'installation.yaml'
OVERRIDE_KINDS = {'connectors': '.yaml', 'services': '.yaml', 'workflows': '.json'}

_IDENT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]*\Z')
_CATEGORY = re.compile(r'[a-z][a-z0-9_]*\Z')
# A field under a channel whose name says it holds a credential must be a reference, never a literal.
_SECRET_FIELD = re.compile(r'(token|secret|password|passwd|credential|api_?key)', re.I)


class InstallationError(Exception):
    """A refusal by name: installation_missing:<key> or installation_invalid:<key>."""

    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


def _missing(key):
    return InstallationError('installation_missing:' + key)


def _invalid(key, detail=''):
    return InstallationError('installation_invalid:' + key, detail)


def _yamlish():
    import importlib.util
    spec = importlib.util.spec_from_file_location('veldo_installation_yamlish',
                                                  Path(__file__).resolve().with_name('yamlish.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def child_environment(folder=None, environ=None):
    """Copy the caller's environment and select its installation for a child when supplied."""
    environment = dict(os.environ if environ is None else environ)
    if folder:
        environment[ENVIRONMENT] = str(folder)
    return environment


def configuration_commit(conn):
    """Accepted provenance for a newly created runtime record on this store."""
    loader = getattr(conn, 'installation_loader', None)
    if loader is not None:
        return loader.accepted_commit
    import json
    rows = conn.execute("SELECT data FROM entities WHERE kind='installation_configuration' "
                        "AND id NOT LIKE '%:accepted:%' AND id NOT LIKE '%:status'").fetchall()
    commits = {json.loads(row[0])['commit'] for row in rows if 'configuration' in json.loads(row[0])}
    if len(commits) > 1:
        raise InstallationError('installation_unreadable:ambiguous_authority')
    return next(iter(commits), None)


def resolve(environ=None):
    """{folder, how, found}: the folder this deployment's installation is read from, how it was chosen
    ('environment' or 'default') and whether it is a folder."""
    env = os.environ if environ is None else environ
    given = env.get(ENVIRONMENT) or ''
    if given:
        folder, how = given, 'environment'
    else:
        base = env.get('XDG_CONFIG_HOME') or ''
        if not os.path.isabs(base):
            home = env.get('HOME') or os.path.expanduser('~')
            base = os.path.join(home, '.config')
        folder, how = os.path.join(base, 'veldo', 'installation'), 'default'
    return {'folder': folder, 'how': how, 'found': os.path.isdir(folder)}


def resolution_line(resolved):
    """The one line every command that reads the installation prints."""
    how = ('from ' + ENVIRONMENT if resolved['how'] == 'environment'
           else 'the documented default under the configuration root')
    if resolved['found']:
        return 'veldo installation: %s (%s)' % (resolved['folder'], how)
    return 'veldo installation: none found (looked at %s, %s)' % (resolved['folder'], how)


def load(environ=None, stream=None):
    """The installation, after printing the resolution line to `stream` (standard error by default).
    Always returns an Installation; one that was not found answers every key installation_missing."""
    resolved = resolve(environ)
    out = sys.stderr if stream is None else stream
    out.write(resolution_line(resolved) + '\n')
    return Installation(resolved)


def trace(environ=None, stream=None):
    """{folder, how, revision}: what a running service names in its status. folder and revision are null
    when no installation was found."""
    inst = load(environ, stream)
    return {'folder': inst.folder if inst.found else None, 'how': inst.how, 'revision': inst.revision()}


# ---- the schema of installation.yaml ----------------------------------------------------------------

def _string(value, key):
    if not isinstance(value, str) or not value.strip():
        raise _invalid(key, 'a non-empty string')
    return value


def _mapping(value, key):
    if not isinstance(value, dict):
        raise _invalid(key, 'a mapping')
    return value


def _named(value, key, each):
    """A mapping of identifier -> entry, each entry checked by `each(entry, key.name)`."""
    for name, entry in _mapping(value, key).items():
        if not isinstance(name, str) or not _IDENT.match(name):
            raise _invalid(key, 'an identifier name')
        each(entry, key + '.' + name)
    return value


def _strings(value, key):
    if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value):
        raise _invalid(key, 'a list of non-empty strings')
    return value


def _secret_ref(value, key):
    if not isinstance(value, dict) or set(value) != {'secret'} or not isinstance(value['secret'], str) \
            or not _IDENT.match(value['secret']):
        raise _invalid(key, 'a secret is a reference by name: {secret: <name>}')


def _owner(value, key):
    _mapping(value, key)
    for field in value:
        if field not in ('display_name', 'role_id'):
            raise _invalid(key + '.' + field)
    for field in ('display_name', 'role_id'):
        if field in value and value[field] is not None:
            _string(value[field], key + '.' + field)


def _identity(value, key):
    _mapping(value, key)
    for field in value:
        if field not in ('name', 'email', 'signing_key'):
            raise _invalid(key + '.' + field)
        _string(value[field], key + '.' + field)


def _channel(value, key):
    _mapping(value, key)
    for field, item in value.items():
        if _SECRET_FIELD.search(str(field)):
            _secret_ref(item, key + '.' + str(field))
        elif not isinstance(item, (str, int)):
            raise _invalid(key + '.' + str(field), 'a string or a number')


def _flat(value, key):
    _mapping(value, key)
    for field, item in value.items():
        if _SECRET_FIELD.search(str(field)):
            _secret_ref(item, key + '.' + str(field))
        elif not isinstance(item, (str, int)):
            raise _invalid(key + '.' + str(field), 'a string or a number')


def _scalar_string(value, key):
    _string(value, key)


def _port(value, key):
    if type(value) is not int or not 0 < value < 65536:
        raise _invalid(key, 'a port number')


SETTINGS = {
    'schema': lambda v, k: None,
    'owner': _owner,
    'git_identities': lambda v, k: _named(v, k, _identity),
    'approvers': _strings,
    'channels': lambda v, k: _named(v, k, _channel),
    'accounts': lambda v, k: _named(v, k, _flat),
    'hosts': lambda v, k: _named(v, k, _scalar_string),
    'tailnet_names': lambda v, k: _named(v, k, _scalar_string),
    'ports': lambda v, k: _named(v, k, _port),
    'trackers': lambda v, k: _named(v, k, _flat),
    'publisher': _identity,
    # The space section (VELDO-0296). Optional as a whole; its keys are checked by its one reader,
    # control_space_config.py.
    'space': _mapping,
}


class Installation:
    """One deployment's installation folder, read on demand. Nothing here writes to it."""

    def __init__(self, resolved):
        self.folder, self.how, self.found = resolved['folder'], resolved['how'], resolved['found']
        self._settings = None

    def _path(self, *parts):
        return Path(self.folder, *parts)

    def revision(self):
        """The commit id of the installation when it is a git checkout, else None."""
        if not self.found or not self._path('.git').exists():
            return None
        try:
            done = _git_process.run(['git', '-C', self.folder, 'rev-parse', '--verify', 'HEAD'],
                                    capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        head = done.stdout.strip()
        return head if done.returncode == 0 and re.fullmatch(r'[0-9a-f]{40,64}', head) else None

    def settings(self):
        """installation.yaml, checked against its schema. {} when there is none."""
        if self._settings is not None:
            return self._settings
        accepted = os.environ.get('VELDO_INSTALLATION_COMMIT')
        if accepted and self.revision() is not None:
            files = Repository(self.folder, os.environ.get('VELDO_INSTALLATION_BRANCH', 'main')).snapshot(accepted)['files']
            import json
            raw = files.get(SETTINGS_FILE, b'{}').decode('utf-8')
            self._settings = json.loads(raw) if raw.lstrip().startswith('{') else _yamlish().parse(raw)
            return self._settings
        path = self._path(SETTINGS_FILE)
        if not self.found or not path.is_file():
            self._settings = {}
            return self._settings
        try:
            data = _yamlish().read(path)
        except (OSError, ValueError) as error:
            raise _invalid(SETTINGS_FILE, str(error)[:200]) from None
        if data is None:
            data = {}
        if not isinstance(data, dict):
            raise _invalid(SETTINGS_FILE, 'a mapping')
        if data.get('schema') != SCHEMA:
            raise _invalid('schema', 'expected ' + SCHEMA)
        for key, value in data.items():
            if key not in SETTINGS:
                raise _invalid(str(key), 'not a key of ' + SCHEMA)
            if value is not None:
                SETTINGS[key](value, key)
        self._settings = data
        return data

    def value(self, key):
        """A top-level key of installation.yaml, or installation_missing:<key>."""
        value = self.settings().get(key)
        if value is None or value == {} or value == []:
            raise _missing(key)
        return value

    def _entry(self, key, name):
        entry = self.settings().get(key) or {}
        if name not in entry or entry[name] is None:
            raise _missing(key + '.' + name)
        return entry[name]

    def space(self):
        """The space section as written, or None when the installation has none: space management is
        off. A section written with nothing under it is a present, empty section. Its keys are checked by
        control_space_config.py, never here."""
        settings = self.settings()
        if 'space' not in settings:
            return None
        return {} if settings['space'] is None else settings['space']

    def owner(self):
        """{display_name, role_id}: the person an action that needs one resolves to."""
        owner = self.value('owner')
        for field in ('display_name', 'role_id'):
            if not owner.get(field):
                raise _missing('owner.' + field)
        return {'display_name': owner['display_name'], 'role_id': owner['role_id']}

    def git_identity(self, name):
        return self._entry('git_identities', name)

    def approvers(self):
        return list(self.value('approvers'))

    def channel(self, name):
        return self._entry('channels', name)

    def account(self, name):
        return self._entry('accounts', name)

    def override(self, kind, ident):
        """The installation's own file for a product connector, service or workflow of this id, or None
        when the product's own applies."""
        if kind not in OVERRIDE_KINDS:
            raise _invalid(str(kind), 'not an overridable kind')
        if not isinstance(ident, str) or not _IDENT.match(ident) or '..' in ident:
            raise _invalid(kind, 'an identifier')
        if not self.found:
            return None
        path = self._path(kind, ident + OVERRIDE_KINDS[kind])
        return path if path.is_file() else None

    def patterns(self):
        """[(category, kind, text)] from patterns/*.yaml, kind 'literal' or 'expression'. The personal-setup
        check is their only reader."""
        folder = self._path('patterns')
        if not self.found or not folder.is_dir():
            return []
        out = []
        for path in sorted(folder.glob('*.yaml')):
            where = 'patterns/' + path.name
            try:
                data = _yamlish().read(path)
            except (OSError, ValueError) as error:
                raise _invalid(where, str(error)[:200]) from None
            if not isinstance(data, dict) or data.get('schema') != PATTERNS_SCHEMA \
                    or set(data) - {'schema', 'patterns'} or not isinstance(data.get('patterns'), list):
                raise _invalid(where, 'schema %s with a patterns list' % PATTERNS_SCHEMA)
            for index, item in enumerate(data['patterns']):
                key = '%s:%d' % (where, index)
                if not isinstance(item, dict) or not isinstance(item.get('category'), str) \
                        or not _CATEGORY.match(item['category']):
                    raise _invalid(key, 'a category')
                kinds = [k for k in ('literal', 'expression') if k in item]
                if len(kinds) != 1 or set(item) != {'category', kinds[0]} \
                        or not isinstance(item[kinds[0]], str) or not item[kinds[0]]:
                    raise _invalid(key, 'exactly one non-empty literal or expression')
                if kinds[0] == 'expression':
                    try:
                        re.compile(item['expression'])
                    except re.error:
                        raise _invalid(key, 'the expression does not compile') from None
                out.append((item['category'], kinds[0], item[kinds[0]]))
        return out

    def decision(self, ref):
        """{source, quote} for a decision reference, from decisions/*.yaml, or installation_missing."""
        folder = self._path('decisions')
        if self.found and folder.is_dir():
            for path in sorted(folder.glob('*.yaml')):
                try:
                    data = _yamlish().read(path)
                except (OSError, ValueError) as error:
                    raise _invalid('decisions/' + path.name, str(error)[:200]) from None
                entry = ((data or {}).get('decisions') or {}).get(ref) if isinstance(data, dict) else None
                if entry is not None:
                    if not isinstance(entry, dict) or set(entry) != {'source', 'quote'}:
                        raise _invalid('decisions.' + ref, 'source and quote')
                    return dict(entry)
        raise _missing('decisions.' + str(ref))

    def records(self):
        """The paths under records/. Listed, never read as configuration."""
        folder = self._path('records')
        if not self.found or not folder.is_dir():
            return []
        return sorted(p for p in folder.rglob('*') if p.is_file())


class Repository:
    error_type = InstallationError
    """The committed installation boundary. Object operations never touch the index or work tree."""

    def __init__(self, folder, branch='main'):
        self.folder, self.branch = str(folder), branch
        if not isinstance(branch, str) or not branch or branch.startswith('-'):
            raise InstallationError('installation_unreadable:branch')
        self.ref = 'refs/heads/' + branch
        self.git('check-ref-format', self.ref)
        if self.git('rev-parse', '--show-toplevel').strip() != str(Path(folder).resolve()):
            raise InstallationError('installation_unreadable:not_repository')

    def git(self, *args, body=None, identity=None, profile='isolated', binary=False):
        try:
            result = _git_process.run(['git', '-C', self.folder, *args], input=body,
                                      capture_output=True, timeout=120, identity=identity, profile=profile)
        except (OSError, subprocess.SubprocessError):
            raise InstallationError('installation_unreadable:git_unavailable') from None
        if result.returncode:
            # Git diagnostics may quote credentials from configuration or URLs. Do not copy them.
            reason = 'stale_version' if args[0] == 'update-ref' else 'installation_unreadable:' + args[0]
            raise InstallationError(reason)
        return result.stdout if binary else result.stdout.decode('utf-8')

    def head(self):
        return self.git('rev-parse', '--verify', self.ref + '^{commit}').strip()

    def snapshot(self, commit=None):
        commit = commit or self.head()
        if not re.fullmatch(r'[0-9a-f]{40,64}', commit):
            raise InstallationError('installation_unreadable:commit')
        tree = self.git('rev-parse', commit + '^{tree}').strip()
        files, blobs = {}, {}
        for entry in self.git('ls-tree', '-rz', '--full-tree', commit).split('\0'):
            if not entry:
                continue
            metadata, path = entry.split('\t', 1)
            mode, kind, blob = metadata.split()
            if mode not in ('100644', '100755') or kind != 'blob':
                raise InstallationError('installation_invalid:%s:$:not_regular' % path)
            files[path] = self.git('cat-file', 'blob', blob, binary=True)
            blobs[path] = blob
        fields = self.git('show', '-s', '--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI', commit).strip().split('\0')
        return {'commit': commit, 'tree': tree, 'files': files, 'blobs': blobs,
                'author': dict(zip(('name', 'email', 'at'), fields[:3])),
                'committer': dict(zip(('name', 'email', 'at'), fields[3:]))}

    def commit(self, files, parent, identity, message):
        """Write Git objects only. publish() is the separate branch compare and swap."""
        directories = {'': {}}
        for path, body in sorted(files.items()):
            parts = path.split('/')
            if any(part in ('', '.', '..') or '\0' in part or '\n' in part for part in parts):
                raise InstallationError('installation_invalid:%s:$:path' % path)
            blob = self.git('hash-object', '-w', '--stdin', body=body).strip()
            folder = '/'.join(parts[:-1])
            directories.setdefault(folder, {})[parts[-1]] = ('100644', 'blob', blob)
            for index in range(len(parts) - 1):
                directories.setdefault('/'.join(parts[:index]), {})
        tree = None
        for folder in sorted(directories, key=lambda p: (p.count('/') + bool(p), p), reverse=True):
            entries = directories[folder]
            body = b''.join(('%s %s %s\t%s\0' % (*value, name)).encode() for name, value in sorted(entries.items()))
            tree = self.git('mktree', '-z', body=body).strip()
            if folder:
                parent_path, _, name = folder.rpartition('/')
                directories[parent_path][name] = ('040000', 'tree', tree)
        args = ['commit-tree', tree]
        if parent:
            args += ['-p', parent]
        return self.git(*args, body=(message + '\n').encode(), identity=(identity['name'], identity['email'])).strip()

    def publish(self, commit, parent):
        self.git('update-ref', self.ref, commit, parent or '0' * len(commit))

    def send(self, commit, remote):
        """Send exactly the accepted commit, without force. A refusal keeps it live locally."""
        if remote is None:
            return
        if not isinstance(remote, str) or not remote or remote.startswith('-'):
            raise InstallationError('installation_push_failed:remote_missing')
        try:
            self.git('push', '--', remote, commit + ':' + self.ref, profile='network')
        except InstallationError:
            raise InstallationError('installation_push_failed:remote_refused') from None

    def import_files(self):
        """Existing declared setup files, excluding keys and Git internals. Called only by setup."""
        files = {}
        for path in Path(self.folder).rglob('*'):
            relative = path.relative_to(self.folder)
            if relative.parts[0] in ('.git', 'keys'):
                continue
            if path.is_symlink():
                raise InstallationError('installation_invalid:%s:$:not_regular' % relative.as_posix())
            if path.is_file():
                files[relative.as_posix()] = path.read_bytes()
        return files

    def materialize_initial(self, files):
        """Lay setup's first committed files down; later Git saves never edit the working tree."""
        for name, body in files.items():
            path = Path(self.folder) / name
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            if not path.exists():
                with path.open('xb') as handle:
                    handle.write(body)
                path.chmod(0o600)

    @classmethod
    def create(cls, folder, branch='main'):
        folder = Path(folder)
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(folder, 0o700)
        if (folder / '.git').exists():
            return cls(folder, branch)
        result = _git_process.run(['git', 'init', '-b', branch, str(folder)], capture_output=True, timeout=120)
        if result.returncode:
            raise InstallationError('installation_unreadable:init')
        return cls(folder, branch)


class RefChanges:
    """OS notification subscription. Subscribe first, then reconcile; overflow also reconciles.

    Watching directories covers loose-ref replacement and packed-refs replacement.
    Rebuilding watches after every event covers newly created branch directories.
    There is no timer and no sampling of reference modification times.
    """

    def __init__(self, repository):
        import ctypes
        import select
        self.repo, self.watches, self.handles = repository, {}, []
        common = Path(repository.git('rev-parse', '--git-common-dir').strip())
        self.common = common if common.is_absolute() else Path(repository.folder) / common
        self.queue = None
        if sys.platform.startswith('linux'):
            self.libc = ctypes.CDLL(None, use_errno=True)
            self.libc.inotify_init1.argtypes = [ctypes.c_int]
            self.libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
            self.fd = self.libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
            if self.fd < 0:
                raise InstallationError('installation_unreadable:notification')
        elif hasattr(select, 'kqueue'):
            self.queue = select.kqueue()
            self.fd = self.queue.fileno()
        else:
            raise InstallationError('installation_unreadable:notifications_unsupported')
        try:
            self.refresh()
        except BaseException:
            self.close()
            raise

    def refresh(self):
        import select
        folders = [self.common]
        ref = self.common / 'refs'
        if ref.is_dir():
            folders += [ref] + [p for p in ref.rglob('*') if p.is_dir()]
        for folder in folders:
            name = str(folder)
            if name in self.watches:
                continue
            if self.queue is None:
                wd = self.libc.inotify_add_watch(self.fd, os.fsencode(name), 0x00000fc8)
                if wd < 0:
                    raise InstallationError('installation_unreadable:notification_watch')
                self.watches[name] = wd
            else:
                handle = os.open(name, os.O_RDONLY | os.O_CLOEXEC)
                self.handles.append(handle)
                event = select.kevent(handle, filter=select.KQ_FILTER_VNODE,
                    flags=select.KQ_EV_ADD | select.KQ_EV_CLEAR,
                    fflags=select.KQ_NOTE_WRITE | select.KQ_NOTE_DELETE | select.KQ_NOTE_RENAME)
                self.queue.control([event], 0, 0)
                self.watches[name] = handle

    def consume(self):
        import struct
        if self.queue is None:
            while True:
                try:
                    data = os.read(self.fd, 65536)
                except BlockingIOError:
                    break
                if not data:
                    raise InstallationError('installation_unreadable:notification_closed')
                offset = 0
                while offset < len(data):
                    wd, mask, _, size = struct.unpack_from('iIII', data, offset)
                    offset += 16 + size
                    if mask & (0x00008000 | 0x00000800 | 0x00000400):
                        self.watches = {path: held for path, held in self.watches.items() if held != wd}
        else:
            import select
            for event in self.queue.control([], 128, 0):
                if event.fflags & (select.KQ_NOTE_DELETE | select.KQ_NOTE_RENAME):
                    self.watches = {path: held for path, held in self.watches.items() if held != event.ident}
        self.refresh()

    def fileno(self):
        return self.fd

    def close(self):
        if self.queue is not None:
            self.queue.close()
        elif getattr(self, 'fd', -1) >= 0:
            os.close(self.fd)
        for handle in self.handles:
            os.close(handle)
        self.handles.clear()
        self.fd = -1


if __name__ == '__main__':
    print(trace())
