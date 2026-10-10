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
NATIVE_ROWS = ('launch', 'write', 'read', 'launchd', 'keychain', 'signal', 'capacity', 'deadline', 'natural',
               'cooperative', 'descendant', 'hard-kill', 'supervisor-loss')
# A nested Seatbelt fails with sandbox_apply: Operation not permitted, so each engine
# runs with its own sandbox off inside this profile. Codex must say so in its argv;
# Claude Code's settings and invocation are checked by claude_settings below.
UNSANDBOXED = {'codex': (('--sandbox', 'danger-full-access'), ('-s', 'danger-full-access'),
                         ('--sandbox=danger-full-access',), ('--dangerously-bypass-approvals-and-sandbox',))}
MINIMUM_PYTHON = (3, 11)
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
    """Admit only sources that cannot enable a nested bash sandbox.

    Discovery: installed Claude Code 2.1.281, proof/VELDO-0124/claude-settings.json.
    Conservatively refuse true in any source, even if another source says false.
    Helpers and settings-supplied environments can change the sources at startup.
    """
    if not isinstance(value, dict) or not isinstance(value.get('sandbox', {}), dict):
        raise Refused('unsupported_configuration:claude_settings')
    if value.get('sandbox', {}).get('enabled', False) is not False:
        raise Refused('unsupported_configuration:claude_bash_sandbox')
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


def claude_file(path, required=False):
    try:
        path.lstat()  # A dangling link is unreadable, not an absent default.
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


def claude_flags(argv, clone):
    """Finite print-mode invocation; unknown source-changing flags fail closed."""
    switches = {'--print', '-p', '--verbose', '--dangerously-skip-permissions',
                '--allow-dangerously-skip-permissions', '--strict-mcp-config',
                '--disable-slash-commands', '--include-partial-messages'}
    values = {'--model', '--output-format', '--input-format', '--permission-mode',
              '--system-prompt', '--append-system-prompt', '--mcp-config', '--tools',
              '--allowedTools', '--disallowedTools', '--allowed-tools', '--disallowed-tools',
              '--max-turns', '--resume', '--session-id'}
    settings = {'--settings', '--managed-settings', '--setting-sources'}
    sources, seen, printing = {'user', 'project', 'local'}, set(), False
    args = iter(argv[1:])
    for arg in args:
        if arg == '--':
            break
        if not arg.startswith('-'):
            continue  # positional prompt
        flag, equal, value = arg.partition('=')
        if flag in switches and not equal:
            printing |= flag in {'--print', '-p'}
            continue
        if flag not in values | settings:
            raise Refused('unsupported_configuration:claude_invocation')
        if not equal:
            value = next(args, None)
        if value is None or (value.startswith('-') and flag not in {'--system-prompt', '--append-system-prompt'}):
            raise Refused('unsupported_configuration:claude_invocation')
        if flag in settings:
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
    return sources


def claude_settings(argv, clone, environment, login_profile, *, create=False):
    if not Path(clone, '.git').is_dir():
        raise Refused('unsupported_configuration:claude_project_root')
    config = environment.get('CLAUDE_CONFIG_DIR')
    if not config or canonical(config) != canonical(login_profile):
        raise Refused('binding_mismatch:claude_config_dir')
    safe = {'CLAUDE_CONFIG_DIR', 'CLAUDE_CODE_DISABLE_CLAUDE_MDS', 'CLAUDE_CODE_DISABLE_AUTO_MEMORY'}
    if any(name.startswith('CLAUDE') and name not in safe for name in environment):
        raise Refused('unsupported_configuration:claude_settings_source')
    sources = claude_flags(argv, clone)
    settings = Path(config) / 'settings.json'
    current = claude_file(settings)  # Inspect the run's file even if user sources are disabled.
    # Admission requires a standalone clone and launches at its root, so cwd and
    # canonical Git root coincide. Alternate project roots/worktree CLI flags refuse.
    for source, name in (('project', 'settings.json'), ('local', 'settings.local.json')):
        if source in sources:
            claude_file(Path(clone) / '.claude' / name)
    claude_file(CLAUDE_MANAGED / 'managed-settings.json')
    try:
        dropins = sorted((CLAUDE_MANAGED / 'managed-settings.d').iterdir())
    except FileNotFoundError:
        dropins = []
    except OSError as error:
        raise Refused('unavailable_service:claude_settings') from error
    for path in dropins:
        if path.name.endswith('.json') and not path.name.startswith('.'):
            claude_file(path, required=True)
    # Linux builds omit the MDM reader. Anthropic's MDM example documents this
    # preference domain; inspect system, per-user, and run-home deliveries.
    owner = pwd.getpwuid(os.getuid())
    preferences = {CLAUDE_PREFERENCES / CLAUDE_DOMAIN,
                   CLAUDE_PREFERENCES / owner.pw_name / CLAUDE_DOMAIN,
                   Path('/Library/Preferences') / CLAUDE_DOMAIN,
                   Path(owner.pw_dir) / 'Library/Preferences' / CLAUDE_DOMAIN,
                   Path(environment['HOME']) / 'Library/Preferences' / CLAUDE_DOMAIN}
    for path in sorted(preferences):
        claude_file(path)
    claude_file(Path(config) / 'remote-settings.json')
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
