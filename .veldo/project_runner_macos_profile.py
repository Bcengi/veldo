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
# A nested Seatbelt fails with sandbox_apply: Operation not permitted, so each engine
# runs with its own sandbox off inside this profile. Codex must say so in its argv;
# Claude Code's bash sandbox is off unless the accepted configuration enables it.
UNSANDBOXED = {'codex': (('--sandbox', 'danger-full-access'), ('-s', 'danger-full-access'),
                         ('--sandbox=danger-full-access',), ('--dangerously-bypass-approvals-and-sandbox',))}
MINIMUM_PYTHON = (3, 11)
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


def canonical(path, missing=False):
    """Resolve /var to /private/var and links before emitting Seatbelt paths.
    missing allows one not yet created final component under an existing parent."""
    if (not isinstance(path, str) or not os.path.isabs(path)
            or any(ord(c) < 32 or c in '"\\' for c in path)):
        raise Refused('invalid_input:path')
    try:
        return str(Path(path).resolve(strict=True))
    except FileNotFoundError:
        if not missing:
            raise Refused('unavailable_service:path')
    except OSError as error:
        raise Refused('unavailable_service:path') from error
    return str(Path(canonical(os.path.dirname(path)), os.path.basename(path)))


def overlaps(first, second):
    # APFS can be case insensitive and normalization insensitive. Refuse even on a
    # case sensitive volume if either spelling could put a protected path in a grant.
    a, b = [unicodedata.normalize('NFD', p).casefold().rstrip('/') for p in (first, second)]
    return a == b or a.startswith(b + '/') or b.startswith(a + '/')


def _regex(path):
    return '#"^%s"' % ''.join('\\' + c if c in '.^$*+?()[]{}|' else c for c in path)


def _any(paths):
    return '(require-any %s)' % ' '.join('(subpath %s)' % json.dumps(p, ensure_ascii=False) for p in paths)


def sandbox(writable, protected, home, accounts=(), projects=(), dispatches=()):
    """Seatbelt profile for the engine and every descendant, which inherit it.

    writable: the run's clone, scratch, run home, run temp and its own login profile.
    protected: authority keys and store, host slot records and installed code; they must
    never overlap a grant, so the write confinement alone denies them.
    home: the account's real home, whose .ssh, .claude* and .codex* are unreadable.
    accounts, projects, dispatches: other login profiles, other projects and the slot
    root holding other dispatches' request files, unreadable except through a grant.
    Every line is a separate rule so a falsifier can remove exactly one.
    """
    writes = sorted(set(canonical(p, missing=True) for p in writable))
    denied = sorted(set(canonical(p) for p in protected))
    if not writes or not denied or any(overlaps(a, b) for a in writes for b in denied):
        raise Refused('invalid_input:protected_overlap')
    home = canonical(home)
    grants = _any(writes)
    accounts, projects, dispatches = [sorted(set(canonical(p) for p in roots))
                                      for roots in (accounts, projects, dispatches)]

    def unreadable(match):
        return '(deny file-read-data (require-all %s (require-not %s)))' % (match, grants)

    rules = ['(version 1)', '(allow default)']
    # Writes: only the grants, /dev/null and the controlling terminal. A symlink inside a
    # grant does not grant its resolved target.
    rules.append('(deny file-write* (require-not (require-any %s (literal "/dev/null") (literal "/dev/tty"))))' % grants)
    rules.append(unreadable('(subpath %s)' % json.dumps(home + '/.ssh')))
    rules.append(unreadable('(regex %s)' % _regex(home + '/.claude')))
    rules.append(unreadable('(regex %s)' % _regex(home + '/.codex')))
    rules.extend([unreadable(_any(accounts))] if accounts else [])
    rules.extend([unreadable(_any(projects))] if projects else [])
    rules.extend([unreadable(_any(dispatches))] if dispatches else [])
    # launchd: no launchctl and no job submission from inside. launchd itself also
    # refuses job creation from sandboxed callers on macOS 26.
    rules.append('(deny process-exec (literal "/bin/launchctl"))')
    rules.append('(deny job-creation)')
    # Keychain: VELDO-0147 decides what a run's own engine account may use; until then none.
    rules.append('(deny mach-lookup (global-name "com.apple.SecurityServer") (global-name "com.apple.securityd") (global-name "com.apple.securityd.xpc"))')
    # Signals reach only processes inside this sandbox instance: the engine's own descendants.
    rules.append('(deny signal (require-not (target same-sandbox)))')
    return '\n'.join(rules) + '\n'


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
    for name, engine in profile['engines'].items():
        argv = engine['argv']
        if name in UNSANDBOXED and not any(argv[i:i + len(f)] == list(f)
                                           for f in UNSANDBOXED[name] for i in range(len(argv))):
            raise Refused('unsupported_configuration:nested_sandbox')
    # The pinned trusted interpreter runs the wrapper; the host never picks /usr/bin/python3.
    if not isinstance(profile.get('interpreter'), str) or not os.path.isabs(profile['interpreter']):
        raise Refused('unsupported_configuration:interpreter')
    canonical(profile.get('root'))
    canonical(profile.get('home'))
    for name in ('account_roots', 'project_roots'):
        if not isinstance(profile.get(name), list):
            raise Refused('unsupported_configuration:' + name)
        for path in profile[name]:
            canonical(path)
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
