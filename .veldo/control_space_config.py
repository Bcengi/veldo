#!/usr/bin/env python3
"""The declarations reader for space management (VELDO-0296): the installation's space section.

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

NOBODY IS A DEFAULT, as in the installation reader. A missing key is refused by name as
installation_missing:<key>; a malformed key and an unknown key are refused by name as
installation_invalid:<key>. No key has a built-in value.

MODE IS NOT A KEY. Mode is a ledger record per scope, written only by the owner's signed command. A mode
key written into the section is refused as unknown, so an edit of the file cannot look like a mode switch.

EVERY PROTECT ENTRY APPLIES ON EVERY ENGINE the installation names: each entry is returned with the full
list of engine contexts, and protect_for gives the entries in force on one context.

A refused section is logged in one line with the key and the reason (missing, malformed or unknown). Key
names only; no value is logged.
"""
import importlib.util
import os
import string
import sys
import zoneinfo
from pathlib import Path

SECTION = 'space'
STATIONS = ('build', 'review', 'gate')
KEYS = ('enabled', 'time_zone', 'pools', 'engines', 'scratch_roots', 'build_roots', 'plain_repositories',
        'client_accounts', 'protect')
# The protect list's keys, with the entry type each one gives.
PROTECT_KEYS = (('paths', 'path'), ('volumes', 'volume'), ('containers', 'container'), ('images', 'image'),
                ('networks', 'network'), ('compose_projects', 'compose_project'))
SESSION_FIELDS = ('session_id', 'working_folder')

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
    _closed(section, SECTION, KEYS)
    engines = _names(section['engines'], SECTION + '.engines')
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
    section = installation.space()
    if section is None:
        return off()
    try:
        return check(section)
    except _Refusal as refusal:
        out = sys.stderr if stream is None else stream
        out.write('veldo space section: refused %s (%s)\n' % (refusal.key, refusal.reason))
        code = 'installation_missing:' if refusal.reason == 'missing' else 'installation_invalid:'
        raise reader.InstallationError(code + refusal.key, refusal.detail) from None


def protect_for(config, engine):
    """The protect entries in force on one engine context: [{type, value}]."""
    return [{'type': entry['type'], 'value': entry['value']} for entry in config.get('protect', ())
            if engine in entry['engines']]


if __name__ == '__main__':
    import json
    print(json.dumps(read(), sort_keys=True))
