#!/usr/bin/env python3
"""The declarations reader for space management: the installation's space section (VELDO-0296) and a
project's space file (VELDO-0338).

The installation says whether space management is on and with what. This module is the one reader of
that section. It opens nothing itself: the section comes from the one installation reader
(installation.py), which is the only code that opens the installation folder.

THE SECTION IS OPTIONAL AS A WHOLE. An installation with no space section has space management off, the
same as enabled false, and is not refused. When the section is present, every key below is required:

  enabled             true or false. Off stops every removal, every admission check and the no-space
                      classification; the ledger stays readable.
  time_zone           the zone whose calendar days the three-day rule counts.
  pools               per pool name: floor (bytes that must stay free) and needs (bytes per station:
                      build, review, gate).
  engines             the Docker contexts Veldo may read and act on.
  scratch_roots       roots (folders outside projects where run and session scratch lives) and
                      session_pattern (a session's scratch folder from {session_id} and {working_folder}).
  build_roots         folders outside worktrees where build output is kept under a worktree's name.
  plain_repositories  git repositories that do not run Veldo, each with repository and worktree_root.
  client_accounts     the client configuration folders the session hooks are installed into.
  protect             paths (path prefixes), volumes, containers, images and networks (Docker name
                      patterns) and compose_projects (compose project names).

ONE KEY MAY BE LEFT OUT (VELDO-0344):

  process_reader      the word none, or the SHA-256 digest (64 lowercase hexadecimal digits, written
                      as a string) of the process reader: the one recorded for the reviewed source
                      and installed by the owner (design section 7.1). The reader's path and its
                      socket's path are fixed in the probe and are not keys. A section without the
                      key reads as none: no reader is used, and every process the probe cannot read
                      is judged by the bound, which is the answer that removes less. Anything else
                      than none or a digest is refused as malformed.

NOBODY IS A DEFAULT, as in the installation reader. A missing key is refused by name as
installation_missing:<key>; a malformed key and an unknown key are refused by name as
installation_invalid:<key>. No key has a built-in value.

MODE IS NOT A KEY. Mode is a ledger record per scope, written only by the owner's signed command. A mode
key written into the section is refused as unknown, so an edit of the file cannot look like a mode switch.

EVERY PROTECT ENTRY APPLIES ON EVERY ENGINE the installation names: each entry is returned with the full
list of engine contexts, and protect_for gives the entries in force on one context.

A refused section is logged in one line with the key and the reason (missing, malformed or unknown). Key
names only; no value is logged.

A PROJECT'S SPACE FILE is .veldo/space.yaml in the project's repository. It is the project's file, not the
installation's, so it has defaults: a project with no file gets every default and is not refused, and a
key left out of a file, or written with nothing under it, gets its default.

  worktree_root    where the project's worktrees live. Default: the folder beside the repository, named
                   after it with the suffix -worktrees.
  branch_pattern   how a branch name gives a ticket: patterns over {agent} and {ticket}, each naming
                   {ticket}. Default: the agent branch pattern Veldo itself creates, agent/{agent}/{ticket}.
  landing_refs     refs besides the trunk whose change means work was landed. Default: none.
  build_output     extra folder name patterns, for adopted worktrees and for folders git does not ignore.
                   Default: none.
  build_variables  environment variables to point at the run's build root. Default: none.
  keep             ignored paths the census must leave alone, relative to the worktree. Default: none.
  evidence_caches  sub-folders of an evidence folder that are caches. Default: none.
  needs            per station (build, review, gate): bytes per pool. Default: nothing declared, so the
                   measured need applies, and until then the pool default.
  protect          additions to the installation's protect list, under the same six keys. Default: none.

AN UNKNOWN KEY IS REFUSED BY NAME, as space_file_invalid:<key>, and so is a malformed one. A misspelled
keep key is therefore never read as a file that keeps nothing. A file that cannot be parsed, or that is
not a regular file, is refused as space_file_unreadable and is not read further.

A PROJECT ADDS PROTECTION AND CANNOT REMOVE ANY. What read_project returns as protect is every entry of
the installation's list, unchanged, followed by the project's additions. The file has no way to name an
installation entry for removal.

THE PROJECT FILE IS PARSED BY THE CALLER'S DOCUMENT READER. This module still opens and parses nothing
itself: read_project is given the one document reader's read function and calls it on the file's path.

A refused file is logged in one line with the project, the key and the reason (malformed, unknown or
unreadable). Names only; no value is logged.
"""
import importlib.util
import os
import re
import string
import sys
import zoneinfo
from pathlib import Path

SECTION = 'space'
STATIONS = ('build', 'review', 'gate')
KEYS = ('enabled', 'time_zone', 'pools', 'engines', 'scratch_roots', 'build_roots', 'plain_repositories',
        'client_accounts', 'protect')
# The one key a section may leave out: left out, it reads as none (the process reader is not used).
OPTIONAL_KEYS = ('process_reader',)
NO_READER = 'none'
_DIGEST = re.compile(r'[0-9a-f]{64}\Z')
# The protect list's keys, with the entry type each one gives.
PROTECT_KEYS = (('paths', 'path'), ('volumes', 'volume'), ('containers', 'container'), ('images', 'image'),
                ('networks', 'network'), ('compose_projects', 'compose_project'))
SESSION_FIELDS = ('session_id', 'working_folder')

PROJECT_FILE = '.veldo/space.yaml'
PROJECT_KEYS = ('worktree_root', 'branch_pattern', 'landing_refs', 'build_output', 'build_variables', 'keep',
                'evidence_caches', 'needs', 'protect')
BRANCH_FIELDS = ('agent', 'ticket')
# The agent branches Veldo itself creates are refs/heads/agent/<agent>/<name>.
BRANCH_PATTERNS = ('agent/{agent}/{ticket}',)
_VARIABLE = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')

_INSTALLATION = None


def _installation():
    global _INSTALLATION
    if _INSTALLATION is None:
        spec = importlib.util.spec_from_file_location('veldo_space_installation',
                                                      Path(__file__).resolve().with_name('installation.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _INSTALLATION = module
    return _INSTALLATION


class _Refusal(Exception):
    """Internal: one refused key and why, turned into the installation reader's error by read()."""

    def __init__(self, reason, key, detail=''):
        self.reason, self.key, self.detail = reason, key, detail
        super().__init__(reason + ':' + key)


def _missing(key):
    return _Refusal('missing', key)


def _malformed(key, detail):
    return _Refusal('malformed', key, detail)


def _unknown(key, detail):
    return _Refusal('unknown', key, detail)


def _closed(value, key, allowed, required=None):
    """A mapping with exactly the keys of `allowed`: an unknown one is refused, then a missing one."""
    if not isinstance(value, dict):
        raise _malformed(key, 'a mapping')
    for name in value:
        if name not in allowed:
            raise _unknown(key + '.' + str(name), 'not a key of ' + key)
    for name in (allowed if required is None else required):
        if value.get(name) is None:
            raise _missing(key + '.' + name)
    return value


def _process_reader(value, key):
    """none, or the digest of the process reader. A key that is left out is none."""
    if value is None or value == NO_READER:
        return NO_READER
    if isinstance(value, str) and _DIGEST.match(value):
        return value
    raise _malformed(key, 'none or a SHA-256 digest as a string of 64 lowercase hexadecimal digits')


def _enabled(value, key):
    if value is True or value == 'true':
        return True
    if value is False or value == 'false':
        return False
    raise _malformed(key, 'true or false')


def _time_zone(value, key):
    if not isinstance(value, str) or not value.strip():
        raise _malformed(key, 'a time zone name')
    try:
        zoneinfo.ZoneInfo(value)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError, OSError):
        raise _malformed(key, 'a known time zone name') from None
    return value


def _bytes(value, key):
    if type(value) is not int or value < 0:
        raise _malformed(key, 'a whole number of bytes, zero or more')
    return value


def _name(value, key):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise _malformed(key, 'a non-empty name')
    return value


def _names(value, key):
    if not isinstance(value, list):
        raise _malformed(key, 'a list')
    out = [_name(item, '%s[%d]' % (key, index)) for index, item in enumerate(value)]
    if len(set(out)) != len(out):
        raise _malformed(key, 'no entry twice')
    return out


def _engines(value, key):
    """The engine contexts, at least one. A protect entry is in force on the engines named here and on no
    other, so a list naming none would leave the whole protect list in force nowhere: it is refused."""
    out = _names(value, key)
    if not out:
        raise _malformed(key, 'a list naming at least one engine context')
    return out


def _path(value, key):
    """An absolute folder path, or one under the home folder written with a leading tilde."""
    if not isinstance(value, str) or not (value.startswith('/') or value == '~' or value.startswith('~/')):
        raise _malformed(key, 'an absolute path, or one that starts with ~/')
    return os.path.normpath(os.path.expanduser(value))


def _paths(value, key):
    if not isinstance(value, list):
        raise _malformed(key, 'a list')
    out = [_path(item, '%s[%d]' % (key, index)) for index, item in enumerate(value)]
    if len(set(out)) != len(out):
        raise _malformed(key, 'no entry twice')
    return out


def _pools(value, key):
    if not isinstance(value, dict):
        raise _malformed(key, 'a mapping of pool name to floor and needs')
    out = {}
    for name, pool in value.items():
        where = key + '.' + str(name)
        if pool is None:
            raise _missing(where + '.floor')
        _closed(pool, where, ('floor', 'needs'))
        needs = _closed(pool['needs'], where + '.needs', STATIONS)
        out[str(name)] = {'floor': _bytes(pool['floor'], where + '.floor'),
                          'needs': {station: _bytes(needs[station], where + '.needs.' + station)
                                    for station in STATIONS}}
    return out


def _session_pattern(value, key):
    if not isinstance(value, str) or not value.strip():
        raise _malformed(key, 'a pattern')
    try:
        fields = [field for _, field, _, _ in string.Formatter().parse(value) if field is not None]
    except ValueError:
        raise _malformed(key, 'a pattern with balanced braces') from None
    if any(field not in SESSION_FIELDS for field in fields) or 'session_id' not in fields:
        raise _malformed(key, 'a pattern over {session_id} and {working_folder} that names {session_id}')
    return value


def _scratch_roots(value, key):
    _closed(value, key, ('roots', 'session_pattern'))
    return {'roots': _paths(value['roots'], key + '.roots'),
            'session_pattern': _session_pattern(value['session_pattern'], key + '.session_pattern')}


def _plain_repositories(value, key):
    if not isinstance(value, list):
        raise _malformed(key, 'a list')
    out = []
    for index, item in enumerate(value):
        where = '%s[%d]' % (key, index)
        _closed(item, where, ('repository', 'worktree_root'))
        out.append({'repository': _path(item['repository'], where + '.repository'),
                    'worktree_root': _path(item['worktree_root'], where + '.worktree_root')})
    if len({item['repository'] for item in out}) != len(out):
        raise _malformed(key, 'no repository twice')
    return out


def _protect(value, key, engines):
    """[{type, value, engines}]: every entry, each applying on every engine the installation names."""
    _closed(value, key, tuple(name for name, _ in PROTECT_KEYS))
    out = []
    for name, kind in PROTECT_KEYS:
        where = key + '.' + name
        values = _paths(value[name], where) if kind == 'path' else _names(value[name], where)
        out.extend({'type': kind, 'value': item, 'engines': list(engines)} for item in values)
    return out


def check(section):
    """The checked section as the reader returns it. Raises _Refusal on the first refused key."""
    reader = None
    if isinstance(section, dict):
        # The key that may be left out is read apart; the nine required keys stay a closed set.
        reader = section.get(OPTIONAL_KEYS[0])
        section = {name: value for name, value in section.items() if name not in OPTIONAL_KEYS}
    _closed(section, SECTION, KEYS)
    engines = _engines(section['engines'], SECTION + '.engines')
    return {
        'present': True,
        'enabled': _enabled(section['enabled'], SECTION + '.enabled'),
        'time_zone': _time_zone(section['time_zone'], SECTION + '.time_zone'),
        'pools': _pools(section['pools'], SECTION + '.pools'),
        'engines': engines,
        'scratch_roots': _scratch_roots(section['scratch_roots'], SECTION + '.scratch_roots'),
        'build_roots': _paths(section['build_roots'], SECTION + '.build_roots'),
        'plain_repositories': _plain_repositories(section['plain_repositories'],
                                                  SECTION + '.plain_repositories'),
        'client_accounts': _paths(section['client_accounts'], SECTION + '.client_accounts'),
        'protect': _protect(section['protect'], SECTION + '.protect', engines),
        'process_reader': _process_reader(reader, SECTION + '.process_reader'),
    }


def off():
    """What an installation with no space section reads as: space management off."""
    return {'present': False, 'enabled': False}


def read(installation=None, environ=None, stream=None):
    """The installation's space section, checked. {present: False, enabled: False} when the installation
    has no space section. A refused key is logged in one line to `stream` (standard error by default),
    key name and reason only, and raised as installation_missing:<key> or installation_invalid:<key>."""
    reader = _installation()
    if installation is None:
        installation = reader.load(environ, stream)
    out = sys.stderr if stream is None else stream
    try:
        section = installation.space()
    except reader.InstallationError as error:
        # A section that is not a mapping is refused by the installation reader; it is this section's
        # refusal all the same, so it gets this section's line.
        if error.code == 'installation_invalid:' + SECTION:
            out.write('veldo space section: refused %s (malformed)\n' % SECTION)
        raise
    if section is None:
        return off()
    try:
        return check(section)
    except _Refusal as refusal:
        out.write('veldo space section: refused %s (%s)\n' % (refusal.key, refusal.reason))
        code = 'installation_missing:' if refusal.reason == 'missing' else 'installation_invalid:'
        raise reader.InstallationError(code + refusal.key, refusal.detail) from None


def protect_for(config, engine):
    """The protect entries in force on one engine context: [{type, value}]."""
    return [{'type': entry['type'], 'value': entry['value']} for entry in config.get('protect', ())
            if engine in entry['engines']]


class ProjectSpaceError(ValueError):
    """A project's space file refused: `code` is space_file_invalid:<key> or space_file_unreadable."""

    def __init__(self, code, project, detail=''):
        self.code, self.project, self.detail = code, project, detail
        super().__init__(code + (': ' + detail if detail else ''))


def _project_path(value, key, root):
    """A folder path: absolute, under the home folder with a leading tilde, or relative to the repository."""
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise _malformed(key, 'a path')
    if value.startswith('/') or value == '~' or value.startswith('~/'):
        return _path(value, key)
    if value.startswith('~'):
        raise _malformed(key, 'a path; a home folder is written ~/')
    return os.path.normpath(os.path.join(root, value))


def _listed(value, key, each):
    if not isinstance(value, list):
        raise _malformed(key, 'a list')
    out = [each(item, '%s[%d]' % (key, index)) for index, item in enumerate(value)]
    if len(set(out)) != len(out):
        raise _malformed(key, 'no entry twice')
    return out


def _inside(value, key):
    """A path inside a folder, written relative to it: never absolute and never leading out of it."""
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise _malformed(key, 'a relative path')
    path = os.path.normpath(value)
    if value.startswith(('/', '~')) or path == '.' or path == '..' or path.startswith('../'):
        raise _malformed(key, 'a relative path that stays inside the folder')
    return path


def _variable(value, key):
    if not isinstance(value, str) or not _VARIABLE.match(value):
        raise _malformed(key, 'an environment variable name')
    return value


def _branch_pattern(value, key):
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise _malformed(key, 'a pattern')
    try:
        fields = [field for _, field, _, _ in string.Formatter().parse(value) if field is not None]
    except ValueError:
        raise _malformed(key, 'a pattern with balanced braces') from None
    if any(field not in BRANCH_FIELDS for field in fields) or fields.count('ticket') != 1:
        raise _malformed(key, 'a pattern over {agent} and {ticket} that names {ticket} once')
    return value


def _project_needs(value, key, known=None):
    """{station: {pool: bytes}} for the three stations; a station left out has nothing declared. `known`
    is the installation's pool names: when it names any, a pool it does not have is refused."""
    if not isinstance(value, dict):
        raise _malformed(key, 'a mapping of station to bytes per pool')
    for name in value:
        if name not in STATIONS:
            raise _unknown(key + '.' + str(name), 'not a station')
    out = {}
    for station in STATIONS:
        pools = value.get(station)
        where = key + '.' + station
        if pools is not None and not isinstance(pools, dict):
            raise _malformed(where, 'a mapping of pool name to bytes')
        out[station] = {}
        for pool, size in (pools or {}).items():
            if known and _name(pool, where) not in known:
                raise _unknown(where + '.' + pool, 'not a pool of the installation')
            out[station][str(_name(pool, where))] = _bytes(size, where + '.' + str(pool))
    return out


def _project_protect(value, key, root):
    """[(type, value)]: the project's additions, in the order of the six protect keys."""
    if not isinstance(value, dict):
        raise _malformed(key, 'a mapping')
    for name in value:
        if name not in dict(PROTECT_KEYS):
            raise _unknown(key + '.' + str(name), 'not a key of ' + key)
    out = []
    for name, kind in PROTECT_KEYS:
        where = key + '.' + name
        if value.get(name) is None:
            continue
        each = (lambda item, at: _project_path(item, at, root)) if kind == 'path' else _name
        out.extend((kind, item) for item in _listed(value[name], where, each))
    return out


def _with_additions(installed, additions, engines):
    """The installation's protect entries, every one, then the project's additions that are not already
    there. A project adds; nothing here takes an installation entry out."""
    entries = [dict(entry, engines=list(entry['engines'])) for entry in installed]
    have = {(entry['type'], entry['value']) for entry in entries}
    for kind, item in additions:
        if (kind, item) not in have:
            have.add((kind, item))
            entries.append({'type': kind, 'value': item, 'engines': list(engines)})
    return entries


def check_project(document, root, config=None, project=None):
    """The checked project declarations from a parsed space file ({} for a project that has none). `root`
    is the project's repository, `config` what read() gave for the installation. Raises _Refusal on the
    first refused key."""
    root = os.path.normpath(str(root))
    config = off() if config is None else config
    if not isinstance(document, dict):
        raise _malformed(PROJECT_FILE, 'a mapping')
    for name in document:
        if name not in PROJECT_KEYS:
            raise _unknown(str(name), 'not a key of ' + PROJECT_FILE)

    def given(key, read, default):
        return default if document.get(key) is None else read(document[key], key)

    additions = given('protect', lambda value, key: _project_protect(value, key, root), [])
    return {
        'project': os.path.basename(root) if project is None else project,
        'worktree_root': given('worktree_root', lambda value, key: _project_path(value, key, root),
                               os.path.join(os.path.dirname(root), os.path.basename(root) + '-worktrees')),
        'branch_pattern': given('branch_pattern', lambda value, key: _listed(value, key, _branch_pattern),
                                list(BRANCH_PATTERNS)),
        'landing_refs': given('landing_refs', _names, []),
        'build_output': given('build_output', _names, []),
        'build_variables': given('build_variables', lambda value, key: _listed(value, key, _variable), []),
        'keep': given('keep', lambda value, key: _listed(value, key, _inside), []),
        'evidence_caches': given('evidence_caches', lambda value, key: _listed(value, key, _inside), []),
        'needs': given('needs', lambda value, key: _project_needs(value, key, config.get('pools')),
                       {station: {} for station in STATIONS}),
        'protect': _with_additions(config.get('protect', ()), additions, config.get('engines', ())),
    }


def read_project(root, load, config=None, project=None, stream=None):
    """A project's space declarations: its .veldo/space.yaml checked, or every default when the project
    has no such file. `root` is the project's repository; `load` is the one document reader's read
    function, called on the file's path; `config` is what read() gave for the installation (read here
    when not given). The answer says whether the file was present. A refused file is logged in one line
    to `stream` (standard error by default) with the project, the key and the reason, and raised as
    ProjectSpaceError: space_file_invalid:<key>, or space_file_unreadable."""
    root = os.path.normpath(str(root))
    project = os.path.basename(root) if project is None else project
    config = read(stream=stream) if config is None else config
    path = os.path.join(root, *PROJECT_FILE.split('/'))
    try:
        if not os.path.lexists(path):
            return dict(check_project({}, root, config, project), present=False)
        if not os.path.isfile(path):
            raise _Refusal('unreadable', PROJECT_FILE, 'not a regular file')
        try:
            document = load(path)
        except (ValueError, OSError) as error:
            raise _Refusal('unreadable', PROJECT_FILE, str(error)) from None
        return dict(check_project(document, root, config, project), present=True)
    except _Refusal as refusal:
        out = sys.stderr if stream is None else stream
        out.write('veldo space file: project %s refused %s (%s)\n' % (project, refusal.key, refusal.reason))
        code = 'space_file_unreadable' if refusal.reason == 'unreadable' else 'space_file_invalid:' + refusal.key
        raise ProjectSpaceError(code, project, refusal.detail) from None


if __name__ == '__main__':
    import json
    print(json.dumps(read(), sort_keys=True))
