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
import plistlib
import pwd
import unicodedata

SCHEMA = 'veldo.macos_worker_profile/v1'
QUALIFICATION = 'veldo.macos_worker_qualification/v1'
ENGINES = ('claude_code', 'codex')
NATIVE_ROWS = ('launch', 'containment', 'capacity', 'deadline', 'natural', 'cooperative', 'descendant')
CAPS = ('runtime_seconds', 'stop_grace_seconds', 'kill_grace_seconds', 'settle_seconds',
        'startup_seconds', 'heartbeat_seconds', 'heartbeat_window_seconds')
CLAUDE_MANAGED = Path('/Library/Application Support/ClaudeCode')
CLAUDE_PREFERENCES = Path('/Library/Managed Preferences')
CLAUDE_DOMAIN = 'com.anthropic.claudecode.plist'


class Refused(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def claude_document(value):
    """Conservative admission: no source may request a nested bash sandbox.

    Names and JSON paths come from installed Claude Code 2.1.281, recorded in
    proof/VELDO-0124/claude-settings.json. Do not emulate a permissive merge:
    managed policy can take precedence over a CLI or user false value.
    """
    if not isinstance(value, dict):
        raise Refused('unsupported_configuration:claude_settings')
    sandbox = value.get('sandbox', {})
    if not isinstance(sandbox, dict):
        raise Refused('unsupported_configuration:claude_settings')
    if sandbox.get('enabled', False) is not False:
        raise Refused('unsupported_configuration:claude_bash_sandbox')
    # A helper or settings environment can change the sources after admission.
    if any(key in value for key in ('policyHelper', 'policyHelpers', 'env')):
        raise Refused('unsupported_configuration:claude_settings_source')
    return value


def claude_json(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate setting')
            result[key] = value
        return result
    try:
        return claude_document(json.loads(text, object_pairs_hook=unique))
    except (ValueError, TypeError) as error:
        raise Refused('unsupported_configuration:claude_settings') from error


def claude_file(path, *, required=False):
    try:
        path.lstat()
    except FileNotFoundError:
        if not required:
            return None
        raise Refused('unsupported_configuration:claude_settings_missing') from None
    except OSError as error:
        raise Refused('unavailable_service:claude_settings') from error
    try:
        if path.suffix == '.plist':
            return claude_document(plistlib.loads(path.read_bytes()))
        return claude_json(path.read_text())
    except (OSError, UnicodeError, ValueError, plistlib.InvalidFileException) as error:
        raise Refused('unavailable_service:claude_settings') from error


def claude_settings(argv, clone, environment, login_profile, *, create=False):
    """Check the actual invocation and local settings before entering Seatbelt.

    Unknown flags and alternate project roots refuse rather than silently adding
    a settings source. A missing user file uses Claude's false default; when we
    create it, record that false explicitly without overwriting existing data.
    """
    config = environment.get('CLAUDE_CONFIG_DIR')
    if not config or canonical(config) != canonical(login_profile):
        raise Refused('binding_mismatch:claude_config_dir')
    safe_environment = {'CLAUDE_CONFIG_DIR', 'CLAUDE_CODE_DISABLE_CLAUDE_MDS', 'CLAUDE_CODE_DISABLE_AUTO_MEMORY'}
    if any(name.startswith('CLAUDE') and name not in safe_environment for name in environment):
        raise Refused('unsupported_configuration:claude_settings_source')
    config = Path(config)
    sources = {'user', 'project', 'local'}
    seen, printing = set(), False
    boolean = {'--print', '-p', '--verbose', '--dangerously-skip-permissions',
               '--allow-dangerously-skip-permissions', '--strict-mcp-config',
               '--disable-slash-commands', '--include-partial-messages', '--forward-subagent-text'}
    valued = {'--model', '--output-format', '--input-format', '--permission-mode',
              '--system-prompt', '--append-system-prompt', '--mcp-config', '--tools',
              '--disallowed-tools', '--allowedTools', '--disallowedTools', '--max-turns'}
    args = iter(argv[1:])
    for argument in args:
        if argument == '--':
            break
        if not argument.startswith('-'):
            continue  # prompt text
        flag, equal, value = argument.partition('=')
        if flag in boolean and not equal:
            printing = printing or flag in {'--print', '-p'}
            continue
        if flag not in valued | {'--settings', '--managed-settings', '--setting-sources'}:
            raise Refused('unsupported_configuration:claude_invocation')
        if not equal:
            value = next(args, None)
        if value is None or (value.startswith('-') and flag not in {'--system-prompt', '--append-system-prompt'}):
            raise Refused('unsupported_configuration:claude_invocation')
        if flag in {'--settings', '--managed-settings', '--setting-sources'}:
            if flag in seen:
                raise Refused('unsupported_configuration:claude_invocation')
            seen.add(flag)
        if flag == '--setting-sources':
            sources = {v.strip() for v in value.split(',')} if value else set()
            if not sources <= {'user', 'project', 'local'}:
                raise Refused('unsupported_configuration:claude_invocation')
        elif flag in {'--settings', '--managed-settings'}:
            if flag == '--managed-settings' or value.lstrip().startswith('{'):
                claude_json(value)
            else:
                path = Path(value)
                claude_file(path if path.is_absolute() else Path(clone) / path, required=True)
    if not printing:
        raise Refused('unsupported_configuration:claude_invocation')
    # Always inspect the run's own file, including when user sources are disabled.
    settings = config / 'settings.json'
    current = claude_file(settings)
    for directory in (Path(clone), *Path(clone).parents):
        for source, name in (('project', 'settings.json'), ('local', 'settings.local.json')):
            if source in sources:
                claude_file(directory / '.claude' / name)
    claude_file(CLAUDE_MANAGED / 'managed-settings.json')
    dropins = CLAUDE_MANAGED / 'managed-settings.d'
    try:
        entries = sorted(dropins.iterdir())
    except FileNotFoundError:
        entries = []
    except OSError as error:
        raise Refused('unavailable_service:claude_settings') from error
    for path in entries:
        if path.name.endswith('.json') and not path.name.startswith('.'):
            claude_file(path, required=True)
    # The Linux binary has no macOS MDM reader. The preference domain is also
    # documented by Anthropic's MDM example, linked in the discovery record.
    owner = pwd.getpwuid(os.getuid())
    for path in (CLAUDE_PREFERENCES / CLAUDE_DOMAIN,
                 CLAUDE_PREFERENCES / owner.pw_name / CLAUDE_DOMAIN,
                 Path('/Library/Preferences') / CLAUDE_DOMAIN,
                 Path(owner.pw_dir) / 'Library/Preferences' / CLAUDE_DOMAIN):
        claude_file(path)
    claude_file(config / 'remote-settings.json')
    if create and current is None:
        try:
            with settings.open('x') as stream:
                json.dump({'sandbox': {'enabled': False}}, stream)
        except FileExistsError:
            claude_file(settings, required=True)
        except OSError as error:
            raise Refused('unavailable_service:claude_settings') from error


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
