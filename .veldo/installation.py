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


if __name__ == '__main__':
    print(trace())
