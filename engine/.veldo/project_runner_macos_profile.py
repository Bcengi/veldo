"""VELDO-0124: versioned, explicitly qualified macOS lifecycle and filesystem policy.

Qualification is an operator supplied evidence record, never a platform guess or an
eligible flag. The selected host and both engine configurations remain unqualified
until their native observations exist. No cgroup or Linux fallback is used.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import unicodedata

SCHEMA = 'veldo.macos_worker_profile/v1'
QUALIFICATION = 'veldo.macos_worker_qualification/v1'
ENGINES = ('claude_code', 'codex')
NATIVE_ROWS = ('launch', 'containment', 'capacity', 'deadline', 'natural', 'cooperative', 'descendant')
CAPS = ('runtime_seconds', 'stop_grace_seconds', 'kill_grace_seconds', 'settle_seconds',
        'startup_seconds', 'heartbeat_seconds', 'heartbeat_window_seconds')


class Refused(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def digest(value):
    return 'sha256:' + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                               ensure_ascii=True, default=str).encode()).hexdigest()


def file_digest(path):
    with open(path, 'rb') as stream:
        result = hashlib.file_digest(stream, 'sha256')
    return 'sha256:' + result.hexdigest()


def canonical(path):
    """Resolve /var to /private/var and links before emitting Seatbelt paths."""
    if not isinstance(path, str) or not os.path.isabs(path) or any(ord(c) < 32 for c in path):
        raise Refused('invalid_input:path')
    try:
        return str(Path(path).resolve(strict=True))
    except OSError as error:
        raise Refused('unavailable_service:path') from error


def overlaps(first, second):
    # APFS can be case insensitive and normalization insensitive. Refuse even on a
    # case sensitive volume if either spelling could put a protected path in a grant.
    a, b = [unicodedata.normalize('NFD', p).casefold().rstrip('/') for p in (first, second)]
    return a == b or a.startswith(b + '/') or b.startswith(a + '/')


def sandbox(writable, protected):
    writes = sorted(set(canonical(p) for p in writable))
    denied = sorted(set(canonical(p) for p in protected))
    if not writes or not denied or any(overlaps(a, b) for a in writes for b in denied):
        raise Refused('invalid_input:protected_overlap')
    terms = ' '.join('(subpath %s)' % json.dumps(p, ensure_ascii=False) for p in writes)
    # Deny every filesystem mutation outside the explicit clone, scratch and login
    # profile grants. A symlink inside a grant does not grant its resolved target.
    return '(version 1)\n(allow default)\n(deny file-write* (require-not (require-any %s)))\n' % terms


def validate(profile):
    if (not isinstance(profile, dict) or profile.get('schema') != SCHEMA
            or type(profile.get('revision')) is not int or profile['revision'] < 1
            or type(profile.get('max_workers')) is not int or profile['max_workers'] < 1):
        raise Refused('unsupported_configuration:profile')
    for name in CAPS:
        value = profile.get(name)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise Refused('unsupported_configuration:' + name)
    if profile['heartbeat_window_seconds'] <= profile['heartbeat_seconds']:
        raise Refused('unsupported_configuration:heartbeat_window_seconds')
    if not isinstance(profile.get('engines'), dict) or set(profile['engines']) != set(ENGINES):
        raise Refused('unsupported_configuration:engines')
    for engine in profile['engines'].values():
        if (not isinstance(engine, dict) or not isinstance(engine.get('argv'), list) or not engine['argv']
                or not all(isinstance(v, str) and v for v in engine['argv'])
                or not os.path.isabs(engine['argv'][0])
                or not engine.get('version') or not engine.get('configuration_digest')
                or not engine.get('binary_digest')):
            raise Refused('unsupported_configuration:engine_identity')
    canonical(profile.get('root'))
    if not isinstance(profile.get('protected'), list) or not profile['protected']:
        raise Refused('unsupported_configuration:protected')
    for path in profile['protected']:
        canonical(path)
    return profile


def qualify(profile, evidence, facts, engine, configuration):
    validate(profile)
    if (facts.get('platform') != 'darwin' or not facts.get('host') or not facts.get('os_version')
            or not facts.get('boot_id') or facts.get('tools') is not True):
        raise Refused('unsupported_configuration:macos_host')
    if engine not in ENGINES or configuration != profile['engines'][engine]['configuration_digest']:
        raise Refused('binding_mismatch:configuration')
    if (not isinstance(evidence, dict) or evidence.get('schema') != QUALIFICATION
            or evidence.get('profile_digest') != digest(profile)
            or evidence.get('host') != facts['host'] or evidence.get('os_version') != facts['os_version']
            or evidence.get('kind') != 'native'
            or any(not evidence.get('rows', {}).get(e + '/' + row) for e in ENGINES for row in NATIVE_ROWS)):
        raise Refused('missing_evidence:macos_qualification')
    if file_digest(profile['engines'][engine]['argv'][0]) != profile['engines'][engine]['binary_digest']:
        raise Refused('stale_version:engine_binary')
    return {'profile_digest': digest(profile), 'revision': profile['revision'], 'host': facts['host'],
            'os_version': facts['os_version'], 'engine': engine, 'configuration_digest': configuration}
