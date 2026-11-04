"""Antigravity's CLI (agy) as the third Veldo engine, VELDO-0232: the same protocol as Claude Code and Codex.

Every table this module reads about the binary is the qualified binary's own, written by the qualify command
(.veldo/qualify.py, which runs the committed extractor proof/VELDO-0232/extract_agy.py against the binary's bytes
and its help, no prompt and no model call) into runtime/antigravity-qualification.json: its options, the
environment and credential names, the stream vocabulary (event types, step types, result fields, finished
reasons, exit codes), the tool registry with each tool classified in_run or outward, the limit and refusal
texts and the places it loads instructions, rules, skills, plugins, hooks and MCP servers from. This module
holds Veldo's policy for the engine, never a version, a digest or a table of the binary.

PINNED AND QUALIFIED (AC1, VELDO-0060 and VELDO-0230 for a third engine). The binary is one executable outside
any package manager that its own updater replaces in place (~/.local/bin/agy), so it is pinned the way Claude
Code's versioned copy is: `pin(version, source, state_root)` copies it under the factory state root at
engines/antigravity/<version> (a new regular file, mode 0555, its digest checked against the record) and every
launch runs that copy. `bind(adapter, state_root)` takes the adapter's `executable: {version}`, refuses a version
the record does not name (`stale_subject:engine_version`) and a pinned copy whose digest differs
(`stale_subject:engine_digest`), a record that is missing or malformed (`missing_evidence:engine_qualification`)
and one without this module's baseline (`missing_evidence:engine_baseline:<version>`), before anything is
accepted. ENVIRONMENT sets AGY_CLI_DISABLE_AUTO_UPDATE, the switch the binary names.

LAUNCHED HEADLESS WITH ONLY THE ROLE'S GRANT (AC2). FLAGS: print mode, stream-json output and stream-json input
(the prompt is written on stdin, never in argv), slash commands and skill expansion off, permission prompts
skipped (no human answers one), no print timeout (Veldo's own deadline and stop apply); never the remote-agent
or remote-control option (FORBIDDEN). `baseline` adds the run's generated settings file through the settings
option (that session's only, never saved), whose `permissions.deny` names every registry tool outside the
role's native tools (the in-run classification when no role revision is bound); a role that selects an MCP
server, or a dispatch that selects one, is refused (`invalid_input:agent_mcp_servers:antigravity`, limit L1).
The Guard reads every step the stream shows and stops the run by name when a tool call names a tool outside the
role's set (`configuration_stop:tool_outside_role`, limit L2: the model still sees the denied tools, so the
enforced equality is of the calls). `profile_problem` refuses, before acceptance and by name, each place the
record lists that no option of the qualified version turns off when it holds anything: the account folder's
.gemini tree (`invalid_input:engine_profile:<entry>`) and the clone's and its parents' instruction files and
.agents folders (`invalid_input:engine_clone:<entry>`); nothing is deleted.

THE STREAM (AC3, VELDO-0060, 0061, 0062, 0141, 0160, 0172). stdout is a typed NDJSON stream of `init`,
`step_update` (a closed `step_type` vocabulary, `tool_info` per tool call, `subagent_info` per subagent) and a
terminal `result` (with `usage`, cache reads included, and `finished_reason`). Meter charges tokens only from
the result's usage (input and output; cache reads are part of the input and counted once); a run whose result
is missing leaves its usage unknown and its reservation retained. Terminal is `complete` only when every line
is well formed against the qualified vocabulary, the stream ends with a result whose finished reason is absent,
the exit is 0 and nothing stopped the run. The individual quota message ("Individual quota reached" with
"Resets in <hours>h<minutes>m", limit L5) is an `account_limit` window whose reset is the line's observation
time plus the stated duration rounded up to the minute; the binary's plan refusals ("Your AI credits balance is
too low to continue." and the others the record lists) are windows with no reset.

ACCOUNTS (AC4, VELDO-0062, 0160, 0185). The account is one folder, the engine's HOME (accounts.PROFILE_ENV,
limit L6). CREDENTIALS is every name the binary makes a login or a paid path; none reaches the engine and an
adapter configuring one is refused by name. `login_problem` refuses, before acceptance, an account folder whose
settings select a model API provider, an API key, a Google Cloud project or application-default login, a gateway,
pay as you go or AI credits (`paid_api:antigravity_login:<kind>`), so a run at its plan quota stops at the limit
and never spends credits. The binary has no login status command (limit L3): where the qualified binary's init
event names the sign-in kind (the record's `init_sign_in`), the Guard writes the prompt only after it names a
Google subscription sign-in; on 1.5.0 the record says it does not.
Standard library only.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import time

PROVIDER = 'antigravity'
# Every name the 1.5.0 binary makes a login or a paid path (read from its bytes, proof/VELDO-0232): the Gemini
# API key, the Google API key and application credentials, the Vertex switch and Cloud project and location, the
# model endpoint, the application-default and business pay-as-you-go switches, and the LLM gateway family.
CREDENTIALS = frozenset((
    'GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_GENAI_USE_VERTEXAI',
    'GOOGLE_CLOUD_PROJECT', 'GOOGLE_CLOUD_LOCATION', 'GOOGLE_GEMINI_BASE_URL', 'AGY_ADC_AUTH',
    'AGY_BUSINESS_PAYGO_TIER', 'AGY_LLM_GATEWAY_API_KEY', 'AGY_LLM_GATEWAY_CA_CERT', 'AGY_LLM_GATEWAY_CLIENT_CERT',
    'AGY_LLM_GATEWAY_CLIENT_KEY', 'AGY_LLM_GATEWAY_HEADERS', 'AGY_LLM_GATEWAY_MODELS', 'AGY_LLM_GATEWAY_PROXY_URL',
    'AGY_LLM_GATEWAY_TIER_FLASH', 'AGY_LLM_GATEWAY_TIER_FLASH_LITE', 'AGY_LLM_GATEWAY_TIER_PRO',
    'AGY_LLM_GATEWAY_URL', 'AGY_LLM_GATEWAY_WIRE_PROTOCOL'))
# The paid path each credential name opens (paid_api:antigravity_login:<kind>).
CREDENTIAL_KINDS = {'GEMINI_API_KEY': 'api_key', 'GOOGLE_API_KEY': 'api_key',
                    'GOOGLE_APPLICATION_CREDENTIALS': 'application_default', 'AGY_ADC_AUTH': 'application_default',
                    'GOOGLE_GENAI_USE_VERTEXAI': 'cloud_project', 'GOOGLE_CLOUD_PROJECT': 'cloud_project',
                    'GOOGLE_CLOUD_LOCATION': 'cloud_project', 'GOOGLE_GEMINI_BASE_URL': 'model_api_provider',
                    'AGY_BUSINESS_PAYGO_TIER': 'pay_as_you_go'}
GATEWAY_FAMILY = 'AGY_LLM_GATEWAY_'
# The binary names no non-login setting the families would not already strip.
SETTINGS = frozenset()

QUALIFICATION = Path(__file__).resolve().with_name('runtime') / 'antigravity-qualification.json'
QUALIFICATION_SCHEMA = 'veldo.engine_qualification/v1'
ARTIFACT_SCHEMA = 'veldo.engine_artifact/v1'
VERSION_TEXT = re.compile(r'[0-9]+(?:\.[0-9]+){1,3}')
# The qualified flags: print mode, stream JSON out and in, slash commands and skills off, no permission prompt, no
# print timeout. The binary's own help names each (proof/VELDO-0232/agy-tables.json, options).
FLAGS = ('--print', '--output-format', 'stream-json', '--input-format', 'stream-json', '--disable-slash-commands',
         '--dangerously-skip-permissions', '--print-timeout', '0s')
FORBIDDEN = ('--remote-agent', '--remote-control')
ENVIRONMENT = {'AGY_CLI_DISABLE_AUTO_UPDATE': '1'}
# The everything-off baseline (VELDO-0155, 0156, 0165 for this engine): the strip prefixes of the trusted wrapper
# (the other engines' and the names a parent Antigravity session sets), the settings option the generated file is
# passed through, and the locale and terminal the engine runs with.
BASELINE = {
    'strip_prefixes': ['CLAUDE', 'CLAUDECODE', 'AI_AGENT', 'CODEX', 'ANTIGRAVITY', 'AGY', 'JETSKI'],
    'strip_names': [],
    'options': [],
    'settings_option': '--settings',
    'environment': {'LANG': 'C.UTF-8', 'TERM': 'dumb'},
    'settings': {'permissions': {'deny': []}},
}
SETTINGS_FILE = 'settings.json'
STOPS = ('requested', 'usage_cap', 'heartbeat_missing', 'paid_api', 'configuration_stop')
# The in-run classification of the registry's tools (Veldo's policy, read by the qualify command): what a tool
# does, inside the run's clone and containment, or outward. A registry tool this table does not name is outward
# (not granted until an evaluation grants it, runtime/capability-decisions.json).
CLASSIFICATION = {
    'file_edit': ('in_run', 'edits a file in the clone'),
    'find': ('in_run', 'finds files in the clone'),
    'grep_search': ('in_run', 'searches file contents in the clone'),
    'list_dir': ('in_run', 'lists a directory in the clone'),
    'view_file': ('in_run', 'reads a file in the clone'),
    'write_to_file': ('in_run', 'writes a file in the clone'),
    'run_command': ('in_run', 'runs a command in the run\'s containment'),
    'manage_task': ('in_run', 'keeps the run\'s own task list'),
    'tool_search': ('in_run', 'searches the tools offered to this run'),
    'invoke_subagent': ('in_run', 'runs a subagent of this process in the same containment (nested work)'),
    'generate_image': ('outward', 'calls an image model outside the run'),
    'read_url_content': ('outward', 'reads a URL on the network'),
    'search_web': ('outward', 'searches the web'),
    'schedule': ('outward', 'creates a scheduled automation that outlives the run'),
    'run_workflow': ('outward', 'runs a workflow the account defines'),
    'browser_subagent': ('outward', 'drives a browser outside the run'),
    'mcp_tool': ('outward', 'calls an MCP server; no Antigravity role selects one (limit L1)'),
}
# The step types that carry no tool call (the model's own text, the user's input, the run's own bookkeeping).
TOOL_FREE_STEPS = frozenset(('planner_response', 'user_input', 'system_message', 'ephemeral_message',
                             'error_message', 'checkpoint', 'conversation_history', 'finish', 'task_boundary',
                             'notify_user', 'suggested_responses', 'plan_input', 'unspecified'))
# The step types through which the run does work in another agent's thread (VELDO-0160, the structural rule).
NESTED_STEPS = {'subagent': ('invoke_subagent', 'browser_subagent')}
MCP_STEP = 'mcp_tool'
# The limit texts (limit L5): the individual quota (observed in the stream 2026-10-23, the server's text) with its
# relative reset, and the plan refusals the record lists, each a window with no reset.
QUOTA_TEXT = 'Individual quota reached'
QUOTA_WINDOW = 'individual_quota'
RESETS_IN = re.compile(r'Resets in (?:(?P<hours>\d+)h)?\s*(?:(?P<minutes>\d+)m)?')
# The settings of an account folder that open a paid path (login_problem), by normalized key.
PAID_SETTINGS = {'apikey': 'api_key', 'geminiapikey': 'api_key', 'googleapikey': 'api_key',
                 'apiprovider': 'model_api_provider', 'modelapiprovider': 'model_api_provider',
                 'gcpproject': 'cloud_project', 'cloudproject': 'cloud_project', 'googlecloudproject': 'cloud_project',
                 'billingmodel': 'pay_as_you_go', 'paygo': 'pay_as_you_go', 'payasyougo': 'pay_as_you_go',
                 'useaicredits': 'ai_credits', 'enableaicredits': 'ai_credits', 'aicredits': 'ai_credits',
                 'adcauth': 'application_default', 'useadc': 'application_default',
                 'gateway': 'gateway', 'llmgateway': 'gateway'}
# The account folder's settings files the paid check reads (never a credential file).
SETTINGS_FILES = ('.gemini/antigravity-cli/settings.json', '.gemini/config/config.json')
# The adapter registration (control_launch.ENGINE_PROTOCOL).
REGISTRATION = {
    'engine': PROVIDER,
    'lifecycle': {
        'accept': 'control_launch.Receiver.launch: the pinned copy bound (bind) and the acceptance recorded before the spawn',
        'launch': 'control_launch.Receiver._spawn: the pinned copy with FLAGS through the trusted wrapper, in its clone',
        'observe': 'Meter.feed, Terminal.feed and Guard.feed over the stream JSON the engine prints',
        'stop': 'control_launch.Launch.stop: the cooperative stop and its bounded escalation over the containment group',
        'exit': 'control_launch.Receiver._reap: the reaped exit recorded on the dispatch',
        'artifacts': 'Terminal.document: the decoded terminal record and its verdict, the exit record\'s artifact',
    },
    'flags': FLAGS,
    'environment': ENVIRONMENT,
}


class Refused(Exception):
    """A named refusal of a binding (control_launch.ENGINE_PROTOCOL): nothing is accepted or spawned."""

    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


def _file_digest(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return 'sha256:' + digest.hexdigest()


def receipt(line):
    return 'sha256:' + hashlib.sha256(line).hexdigest()


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


# THE QUALIFICATION RECORD.

def qualification(tables, *, version, sha256, source, decisions=None):
    """The qualification record of one binary (written by .veldo/qualify.py): the extractor's tables and this
    module's policy. `decisions` is runtime/capability-decisions.json's `antigravity` table (a granted tool is in
    the in-run class)."""
    granted = {name for name, row in ((decisions or {}).get('tools') or {}).items() if row.get('decision') == 'granted'}
    registry = sorted(tables['tool_registry'])
    classification = {}
    for name in registry:
        kind, reason = CLASSIFICATION.get(name, ('outward', 'not classified: outward until an evaluation grants it'))
        if name in granted and name not in CLASSIFICATION:
            kind, reason = 'in_run', ((decisions or {}).get('tools') or {})[name].get('reason', 'granted')
        classification[name] = {'class': kind, 'reason': reason}
    return {'schema': QUALIFICATION_SCHEMA, 'engine': PROVIDER, 'spec_id': 'VELDO-0232', 'version': version,
            'sha256': sha256, 'source': source, 'pinned': '<state root>/engines/antigravity/' + version,
            'flags': list(FLAGS), 'environment': dict(ENVIRONMENT), 'baseline': BASELINE,
            'options': tables['options'], 'subcommands': tables['subcommands'],
            'credentials': tables['credentials'], 'session_environment': tables['session_environment'],
            'stream': json.loads(json.dumps(tables['stream'])), 'tool_registry': registry, 'tool_classification': classification,
            'limits': tables['limits'], 'load_places': tables['load_places'],
            'init_sign_in': tables.get('init_sign_in'),
            'authentication': 'the Google subscription sign-in of the account folder the engine\'s HOME names',
            'usage_units': ['invocations', 'wall_seconds', 'tokens', 'messages'],
            'rate_limit_windows': sorted({QUOTA_WINDOW} | {w for _, w in tables['limits']['refusals']})}


def load_qualification(path=None):
    """The installed qualification record; refused by name when missing or malformed."""
    try:
        record = json.loads(Path(path or QUALIFICATION).read_text())
    except (OSError, ValueError):
        raise Refused('missing_evidence:engine_qualification')
    fields = ('version', 'sha256', 'flags', 'tool_registry', 'tool_classification', 'stream', 'load_places', 'limits')
    if (not isinstance(record, dict) or record.get('schema') != QUALIFICATION_SCHEMA or record.get('engine') != PROVIDER
            or not all(record.get(f) for f in fields) or not isinstance(record['flags'], list)):
        raise Refused('missing_evidence:engine_qualification')
    return record


def qualified_baseline(bound, record=None):
    """The baseline the record lists, which must be this module's BASELINE, its flags this module's FLAGS (never
    a forbidden option), and every registry tool classified; else refused by name before acceptance."""
    record = load_qualification(record) if record is None or isinstance(record, (str, Path)) else record
    version = record.get('version')
    if (record.get('baseline') != BASELINE or record.get('flags') != list(FLAGS)
            or set(record['flags']) & set(FORBIDDEN) or not isinstance(record.get('session_environment'), list)):
        raise Refused('missing_evidence:engine_baseline:%s' % version)
    classes = record.get('tool_classification') or {}
    if set(record['tool_registry']) - set(classes) or any(
            (row or {}).get('class') not in ('in_run', 'outward') for row in classes.values()):
        raise Refused('missing_evidence:engine_baseline:%s' % version)
    return BASELINE


def tools(record):
    """{registry, in_run}: the qualified registry and its in-run tools."""
    classes = record['tool_classification']
    return {'registry': sorted(record['tool_registry']),
            'in_run': sorted(n for n, row in classes.items() if row['class'] == 'in_run')}


# PINNED EXECUTABLE (AC1).

def pinned_path(state_root, version):
    return Path(state_root) / 'engines' / PROVIDER / version


def pin(version, *, source, state_root, record=None):
    """Copy the binary `source` under the factory state root at engines/antigravity/<version> (a new regular file
    written beside and renamed into place, mode 0555) and return its binding. A source that is not a regular
    file, a version the record does not name or a copy whose digest is not the qualified one is refused and
    nothing is left in place. A source that is the pinned copy itself is bound as it is."""
    record = load_qualification(record) if record is None or isinstance(record, (str, Path)) else record
    if version != record['version']:
        raise Refused('stale_subject:engine_version', str(version))
    target = pinned_path(state_root, version)
    source = Path(source)
    if os.path.lexists(target) and os.path.realpath(source) == os.path.realpath(target):
        return bind({'executable': {'version': version}}, str(state_root), record)
    try:
        info = os.stat(source)
    except OSError:
        raise Refused('missing_evidence:engine_source', str(source))
    if not stat.S_ISREG(info.st_mode):
        raise Refused('binding_mismatch:engine_source', 'the source is not a regular file')
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    partial = target.parent / ('.%s.%s.partial' % (version, os.urandom(6).hex()))
    try:
        with open(source, 'rb') as reading, open(partial, 'xb') as writing:
            shutil.copyfileobj(reading, writing, 1 << 20)
        os.chmod(partial, 0o555)
        if _file_digest(partial) != record['sha256']:
            raise Refused('stale_subject:engine_digest', 'the source is not the qualified binary')
        os.replace(partial, target)
    finally:
        if partial.exists():
            partial.unlink()
    return bind({'executable': {'version': version}}, str(state_root), record)


def bind(adapter, state_root, record=None):
    """{engine, version, path, sha256, flags, baseline, tools}: the pinned copy a launch of `adapter` runs, checked
    before anything is accepted or spawned (control_launch.ENGINE_PROTOCOL). The adapter names the qualified
    version (`executable: {version}`, or `qualification`, a record path); its copy under the state root must be
    this account's own regular file, not writable, not reached through a link, with the qualified digest."""
    if record is None:
        record = load_qualification(adapter.get('qualification') if isinstance(adapter, dict) else None)
    elif isinstance(record, (str, Path)):
        record = load_qualification(record)
    executable = adapter.get('executable') if isinstance(adapter, dict) else None
    version = executable.get('version') if isinstance(executable, dict) else None
    if version != record['version']:
        raise Refused('stale_subject:engine_version', str(version))
    if not isinstance(state_root, str) or not os.path.isabs(state_root):
        raise Refused('missing_authority:engine_state_root', 'the receiver names no factory state root')
    path = pinned_path(state_root, version)
    try:
        info = os.lstat(path)
    except OSError:
        raise Refused('missing_evidence:engine_executable', str(path))
    if not stat.S_ISREG(info.st_mode):
        raise Refused('binding_mismatch:engine_executable', 'the pinned copy is not a regular file')
    if os.path.realpath(path.parent) != os.path.normpath(str(path.parent)):
        raise Refused('binding_mismatch:engine_path', 'a directory on the way to the pinned copy is a link')
    if info.st_uid != os.geteuid():
        raise Refused('binding_mismatch:engine_owner', 'the pinned copy is not this account\'s own')
    if info.st_mode & 0o7222:
        raise Refused('binding_mismatch:engine_mode', 'the pinned copy is writable or carries a special bit')
    digest = _file_digest(path)
    if digest != record['sha256']:
        raise Refused('stale_subject:engine_digest', 'the pinned copy is not the qualified binary')
    base = qualified_baseline(None, record)
    return {'engine': PROVIDER, 'version': version, 'path': str(path), 'sha256': digest, 'flags': list(record['flags']),
            'baseline': base, 'tools': tools(record), 'stream': record['stream'], 'limits': record['limits'],
            'load_places': record['load_places'], 'init_sign_in': record.get('init_sign_in')}


def command(bound, adapter):
    """The engine's argv: the adapter's prefix (its clone entrance, or a transport's trusted wrapper), then the
    pinned copy and the qualified flags; never a forbidden option."""
    argv = list(adapter.get('argv') or []) + [bound['path']] + list(bound['flags'])
    if set(argv) & set(FORBIDDEN):
        raise Refused('invalid_input:engine_flags')
    return argv


def environment(bound):
    """What the engine's environment always carries (AGY_CLI_DISABLE_AUTO_UPDATE)."""
    return dict(ENVIRONMENT)


# THE BASELINE (AC2).

def launch_tools(bound, revision=None):
    """{launch, denied, source}: the role's native tools (the in-run classification when no revision is bound)
    and every registry tool outside them."""
    table = bound.get('tools')
    if not isinstance(table, dict):
        raise Refused('missing_evidence:engine_baseline:%s' % bound.get('version'))
    if revision is None:
        launch, source = list(table['in_run']), 'in_run'
    else:
        native = revision.get('native_tools') if isinstance(revision, dict) else None
        if not isinstance(native, list) or not all(isinstance(n, str) for n in native):
            raise Refused('invalid_input:role_revision')
        if set(native) - set(table['registry']):
            raise Refused('unavailable_service:native_tools')
        launch, source = sorted(set(native)), 'role_revision'
    return {'launch': launch, 'denied': sorted(set(table['registry']) - set(launch)), 'source': source}


def tool_options(bound, revision=None):
    """Before acceptance (control_launch._bind): the bound role revision's launch tool set, refused by name when the
    role selects an MCP server (limit L1) or names a tool the registry does not hold."""
    if isinstance(revision, dict) and revision.get('mcp'):
        raise Refused('invalid_input:agent_mcp_servers:antigravity')
    return launch_tools(bound, revision)


def baseline(bound, run, environment=None, record=None, servers=()):
    """{argv, environment, files, tools, secrets, routes}: what the run adds after its qualified flags: the
    settings option naming the run's generated settings file (written into its own `config` directory before the
    spawn), whose permissions deny every registry tool outside the role's set. A selected MCP server is refused
    (limit L1)."""
    base = bound.get('baseline') if record is None else qualified_baseline(bound, record)
    if base != BASELINE:
        raise Refused('missing_evidence:engine_baseline:%s' % bound.get('version'))
    revision = run.get('revision')
    if servers or (isinstance(revision, dict) and revision.get('mcp')):
        raise Refused('invalid_input:agent_mcp_servers:antigravity')
    chosen = launch_tools(bound, revision)
    settings = json.loads(json.dumps(base['settings']))
    settings['permissions']['deny'] = list(chosen['denied'])
    config = Path(run['config'])
    return {'argv': [base['settings_option'], str(config / SETTINGS_FILE)] + list(base['options']),
            'environment': dict(base['environment']),
            'files': {SETTINGS_FILE: (json.dumps(settings, sort_keys=True) + '\n').encode()},
            'tools': {'source': chosen['source'], 'launch': chosen['launch'], 'disallowed': chosen['denied']},
            'secrets': {}, 'routes': [], 'expected': None}


# THE PRE-ACCEPTANCE CHECKS (AC2, AC4).

def _home(environment, cwd=None):
    given = (environment or {}).get('HOME')
    if not given:
        return None
    home = Path(given)
    return Path(cwd) / home if cwd is not None and not home.is_absolute() else home


def _holds(path, inert=()):
    """The first entry a load place holds, '.' for a file with content (or a place that cannot be read), None
    when it holds nothing (absent, an empty file, an empty directory or only `inert` entries)."""
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return None
    except OSError:
        return '.'
    if stat.S_ISDIR(info.st_mode):
        try:
            entries = sorted(set(os.listdir(path)) - set(inert))
        except OSError:
            return '.'
        return entries[0] if entries else None
    if stat.S_ISREG(info.st_mode):
        if info.st_size == 0:
            return None
        try:
            data = json.loads(Path(path).read_text())
        except (OSError, ValueError):
            return '.'
        servers = data.get('mcpServers') if isinstance(data, dict) else None
        return None if isinstance(data, dict) and set(data) <= {'mcpServers'} and not servers else '.'
    return '.'


def _project(cwd):
    """The working directory and each directory above it up to the nearest holding .git (the working directory
    alone when none does): the clone and its parents, where the binary reads instructions."""
    walk = [Path(cwd)] + list(Path(cwd).parents)
    for at, directory in enumerate(walk):
        if os.path.lexists(directory / '.git'):
            return walk[:at + 1]
    return walk[:1]


def profile_problem(bound, environment, cwd=None):
    """AC2, before anything is accepted: each place the qualified binary loads instructions, rules, skills,
    plugins, hooks or MCP servers from that no option of the version turns off, refused by name when it holds
    anything: the account folder's (the record's `load_places.profile`, relative to HOME; a place's `inert`
    entries are the binary's own bookkeeping, never loaded into a run) and the clone's and its parents' (the
    record's `load_places.clone`). None when there is none. Nothing is deleted."""
    places = bound.get('load_places') or {}
    home = _home(environment, cwd)
    for place in places.get('profile') or () if home is not None else ():
        held = _holds(home / place['path'], place.get('inert') or ())
        if held is not None:
            return 'invalid_input:engine_profile:' + (place['path'] if held == '.' else place['path'] + '/' + held)
    for directory in _project(cwd) if cwd is not None else ():
        for place in places.get('clone') or ():
            held = _holds(directory / place['path'], place.get('inert') or ())
            if held is not None:
                entry = os.path.relpath(directory / place['path'], cwd)
                return 'invalid_input:engine_clone:' + (entry if held == '.' else entry + '/' + held)
    return None


def _normal(key):
    return re.sub(r'[^a-z0-9]', '', str(key).lower())


def _paid(value, path=()):
    """The first paid path a settings object selects, or None: a key of PAID_SETTINGS whose value is on (a true,
    a non-empty text other than a subscription's, a non-empty object or list)."""
    if isinstance(value, dict):
        for key in sorted(value, key=str):
            kind = PAID_SETTINGS.get(_normal(key))
            item = value[key]
            if kind is not None and item not in (None, False, '', [], {}) and not (
                    isinstance(item, str) and 'subscription' in item.lower()):
                if not (isinstance(item, dict) and item.get('enabled') is False):
                    return kind
            found = _paid(item, path + (key,))
            if found:
                return found
    elif isinstance(value, list):
        for item in value:
            found = _paid(item, path)
            if found:
                return found
    return None


def login_problem(bound, environment, cwd=None):
    """AC4, before anything is accepted: a paid path the engine would take, refused by name
    (`paid_api:antigravity_login:<kind>`): a credential name in the engine environment, or an account folder
    whose settings (SETTINGS_FILES, never a credential file) select a model API provider, an API key, a Cloud
    project, the application-default login, a gateway, pay as you go or AI credits."""
    for name in sorted(environment or {}):
        if name in CREDENTIALS or name.startswith(GATEWAY_FAMILY):
            return 'paid_api:antigravity_login:' + CREDENTIAL_KINDS.get(name, 'gateway')
    home = _home(environment, cwd)
    if home is None:
        return 'paid_api:antigravity_login:no_account_folder'
    for name in SETTINGS_FILES:
        try:
            data = json.loads((home / name).read_text())
        except FileNotFoundError:
            continue
        except (OSError, ValueError):
            return 'paid_api:antigravity_login:unreadable'
        kind = _paid(data)
        if kind:
            return 'paid_api:antigravity_login:' + kind
    return None


def account_login(bound, environment, cwd=None):
    """VELDO-0185 AC4 for an engine with no login status command (limit L3): the pre-acceptance checks of AC4. None
    when they pass, else the kind they name."""
    problem = login_problem(bound, environment, cwd)
    return None if problem is None else problem.rsplit(':', 1)[1]


# THE STREAM READERS (AC3).

def _event(line):
    try:
        event = json.loads(line)
    except ValueError:
        return None
    return event if isinstance(event, dict) else None


def tool_name(event):
    """The canonical tool name a step_update's tool_info (or its tool_name) carries, None for a step with no
    tool, False for one that cannot be read."""
    info = event.get('tool_info')
    name = info.get('name') if isinstance(info, dict) else None
    name = name if name is not None else event.get('tool_name')
    if name is None and info is None:
        return None
    return name if isinstance(name, str) and name else False


def tool_calls(event, seen=None, redacted=False):
    """[{id, server, tool}]: the MCP tool calls an event shows (VELDO-0160): a step of the MCP step type naming its
    server and tool; one that cannot be read is unreadable, a step type the tables do not list and a step of
    another known type with a tool the registry does not hold are unknown (fail closed)."""
    kind = event.get('type')
    if kind != 'step_update':
        return [] if kind in ('init', 'result') else [{'id': None, 'server': None, 'tool': None, 'unknown': 'event:%s' % kind}]
    step, ident = event.get('step_type'), event.get('step_index')
    ident = str(ident) if ident is not None else None
    if not isinstance(step, str):
        return [{'id': ident, 'server': None, 'tool': None, 'unreadable': True}]
    name = tool_name(event)
    if step == MCP_STEP:
        info = event.get('tool_info') if isinstance(event.get('tool_info'), dict) else {}
        server, tool = info.get('server'), info.get('tool') or info.get('name')
        if not (isinstance(server, str) and server and isinstance(tool, str) and tool):
            return [{'id': ident, 'server': None, 'tool': None, 'unreadable': True}]
        return [{'id': ident, 'server': server, 'tool': tool}]
    if name is False:
        return [{'id': ident, 'server': None, 'tool': None, 'unreadable': True}]
    if step in TOOL_FREE_STEPS and name is None:
        return []
    if name is not None and name in CLASSIFICATION:
        return []
    return [{'id': ident, 'server': None, 'tool': None, 'unknown': 'step:%s' % step}]


def nested_work(event):
    """[(construct, form)]: a step through which the run does work in a subagent's thread (NESTED_STEPS), or one
    carrying `subagent_info`."""
    if event.get('type') != 'step_update':
        return []
    step = event.get('step_type')
    found = [(construct, 'step:' + step) for construct, steps in NESTED_STEPS.items() if step in steps]
    if not found and event.get('subagent_info') is not None:
        found.append(('subagent', 'subagent_info'))
    return found


def remote_agents(event):
    """[]: the stream names no call that starts an agent outside the run beyond the outward tools."""
    return []


def tool_inputs(event):
    """[]: a step carries its own input."""
    return []


def outward_tools(event, inputs=None):
    """[form]: a step whose tool is not an in-run tool of CLASSIFICATION (`tool:<name>`)."""
    if event.get('type') != 'step_update':
        return []
    name = tool_name(event)
    if not name:
        return []
    return [] if CLASSIFICATION.get(name, ('outward',))[0] == 'in_run' else ['tool:' + name]


# Antigravity reports no task counting its subagents' calls.
Tasks = None


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def quota_reset(text, now):
    """The Unix time an individual quota message says the quota returns: the observation time plus the stated
    duration, rounded up to the minute; None when it states none."""
    found = RESETS_IN.search(text)
    if found is None or not (found['hours'] or found['minutes']):
        return None
    seconds = now + int(found['hours'] or 0) * 3600 + int(found['minutes'] or 0) * 60
    return math.ceil(seconds / 60) * 60


class Meter:
    """One invocation's usage and limit, line by line (the same interface as the other engines' meters)."""

    def __init__(self, clock=time.time, zone=None, resumes=None, prior=None, refusals=None):
        self.pending = b''
        self.clock = clock
        self.conversation = None
        self.result = None
        self.tokens = None
        self.limited = None
        self.stated = set()
        self.refusals = tuple(refusals) if refusals is not None else ()

    def bind(self, binding):
        """The plan refusals the qualified record lists, from the receiver's binding."""
        self.refusals = tuple(tuple(pair) for pair in ((binding or {}).get('limits') or {}).get('refusals') or ())

    def feed(self, chunk):
        self.pending += chunk
        found = []
        while b'\n' in self.pending:
            line, _, self.pending = self.pending.partition(b'\n')
            found.extend(self.line(line))
        return found

    def close(self):
        line, self.pending = self.pending, b''
        return self.line(line) if line.strip() else []

    def cumulative(self):
        return {'tokens': self.tokens, 'messages': 1} if self.tokens is not None else {}

    def final(self):
        return self.cumulative()

    def session(self):
        if self.conversation is None:
            return None
        return {'provider': PROVIDER, 'id': self.conversation, 'tokens': self.tokens, 'charged': 'whole'}

    def limit(self):
        return dict(self.limited) if self.limited else None

    def _limit(self, seen, event, signal):
        found = []
        for text in _strings(event):
            if QUOTA_TEXT in text:
                window, reset = QUOTA_WINDOW, quota_reset(text, self.clock())
            else:
                window = next((w for message, w in self.refusals if message in text), None)
                if window is None:
                    continue
                reset = None
            self.limited = {'window': window, 'reset_at': reset, 'signal': signal}
            if (window, reset) not in self.stated:
                self.stated.add((window, reset))
                found.append(dict(seen, kind='window', window_id=window, status='rejected', reset_at=reset,
                                  utilization=None))
        return found

    def line(self, line):
        event = _event(line)
        if event is None:
            return []
        seen = {'line': line, 'receipt': receipt(line)}
        kind = event.get('type')
        conversation = event.get('conversation_id') or event.get('session_id')
        if isinstance(conversation, str) and conversation and self.conversation is None:
            self.conversation = conversation
        found = self._limit(seen, event, 'result' if kind == 'result' else 'stream')
        if kind == 'result':
            usage = event.get('usage') if isinstance(event.get('usage'), dict) else {}
            counts = [usage.get(f) for f in ('input_tokens', 'output_tokens')]
            if all(_count(c) for c in counts) and self.result is None:
                # Cache reads are part of the input: counted once.
                self.tokens = sum(counts)
                found.append(dict(seen, kind='usage', usage=self.cumulative()))
            self.result = event
        return found


def _malformed(event, vocabulary):
    """Why a parsed line is not one the qualified stream prints, or None."""
    if not isinstance(event, dict) or event.get('type') not in vocabulary['events']:
        return 'unknown_event'
    kind = event['type']
    if kind == 'step_update' and event.get('step_type') not in vocabulary['step_types']:
        return 'step_type'
    if kind == 'result':
        reason = event.get('finished_reason')
        if reason is not None and reason not in vocabulary['finished_reasons']:
            return 'finished_reason'
        usage = event.get('usage')
        if usage is not None and (not isinstance(usage, dict) or not all(_count(v) for v in usage.values())):
            return 'usage'
    return None


class Terminal:
    """The artifact document of one invocation's output, fed the same chunks as Meter. `vocabulary` is the
    qualified stream's (the record's `stream`); without one every line is malformed."""

    def __init__(self, vocabulary=None):
        self.vocabulary = vocabulary or {'events': (), 'step_types': (), 'finished_reasons': ()}
        self.pending = b''
        self.lines, self.malformed = [], []
        self.result, self.result_line, self.init_tools, self.agy_error = None, None, None, None
        self.after_result = False

    def bind(self, binding):
        """The qualified stream vocabulary, from the receiver's binding."""
        self.vocabulary = (binding or {}).get('stream') or self.vocabulary

    def feed(self, chunk):
        self.pending += chunk
        while b'\n' in self.pending:
            line, _, self.pending = self.pending.partition(b'\n')
            self._take(line)

    def close(self):
        line, self.pending = self.pending, b''
        if line.strip():
            self._take(line)

    def _take(self, raw):
        if not raw.strip():
            return
        index = len(self.lines)
        self.lines.append(raw.decode('utf-8', 'replace'))
        if raw.startswith(b'AGY_ERROR'):
            self.agy_error = index
            return
        event = _event(raw)
        if _malformed(event, self.vocabulary):
            self.malformed.append(index)
            return
        self.after_result = False
        if event['type'] == 'init' and isinstance(event.get('tools'), list):
            self.init_tools = list(event['tools'])
        elif event['type'] == 'result':
            self.result, self.result_line, self.after_result = event, index, True

    def verdict(self, termination, cause=None):
        if termination is None:
            return 'not_executed'
        if cause in STOPS:
            return 'stopped'
        if termination.get('deadline_stop'):
            return 'deadline'
        if termination.get('signal') is not None:
            return 'signal'
        if self.malformed:
            return 'malformed_output'
        if termination.get('returncode') == 3:
            return 'agent_error'
        if self.result is None or not self.after_result:
            return 'missing_result'
        reason = self.result.get('finished_reason')
        if reason is not None:
            return 'finished:' + str(reason)
        if termination.get('returncode') != 0:
            return 'nonzero_exit'
        return 'complete'

    def document(self, termination, cause=None):
        verdict = self.verdict(termination, cause)
        return {'schema': ARTIFACT_SCHEMA, 'engine': PROVIDER, 'verdict': verdict, 'complete': verdict == 'complete',
                'result_line': self.result_line, 'finished_reason': (self.result or {}).get('finished_reason'),
                'init_tools': self.init_tools, 'agy_error_line': self.agy_error, 'malformed': self.malformed,
                'termination': termination, 'cause': cause, 'lines': self.lines}


class Guard:
    """The prompt and the stream stop. `opening(prompt)` is the prompt as one stream-json input message, written at
    once and the input closed, unless the qualified binary's init event names the sign-in kind (the record's
    `init_sign_in`: its field and the subscription values), when the prompt waits for that init and a sign-in
    other than a Google subscription stops the run by name (`paid_api:antigravity_login:<kind>`). `feed` reads
    every step: a tool call outside the role's set (`bind`: the binding's launch tool set) stops the run by
    name (`configuration_stop:tool_outside_role`, limit L2)."""

    def __init__(self):
        self.pending = b''
        self.source, self.stop = None, None
        self.allowed = None
        self.sign_in = None
        self.prompt, self.released, self.confirmed = None, False, False

    def bind(self, binding):
        """The run's launch tool set and the record's init sign-in field, from the receiver's binding."""
        binding = binding or {}
        try:
            self.allowed = set(launch_tools(binding, binding.get('revision'))['launch'])
        except Refused:
            self.allowed = set()
        self.sign_in = binding.get('init_sign_in')

    @staticmethod
    def message(prompt):
        return (json.dumps({'type': 'user', 'message': {'role': 'user', 'content': prompt.decode('utf-8', 'replace')}})
                + '\n').encode()

    def opening(self, prompt):
        if self.sign_in:
            self.prompt = bytes(prompt)
            return b'', False
        self.released = True
        return self.message(bytes(prompt)), True

    def release(self):
        if self.prompt is None or self.released or not self.confirmed or self.stop is not None:
            return None
        self.released = True
        return self.message(self.prompt)

    def feed(self, chunk):
        self.pending += chunk
        found = None
        while b'\n' in self.pending:
            line, _, self.pending = self.pending.partition(b'\n')
            found = self._line(line) or found
        return found

    def _stopped(self, code):
        if self.stop is None:
            self.stop = code
            return code
        return None

    def _line(self, line):
        event = _event(line)
        if event is None:
            return None
        if event.get('type') == 'init' and self.sign_in:
            kind = event.get(self.sign_in['field'])
            self.source = kind if isinstance(kind, str) else repr(kind)
            if kind not in self.sign_in['subscription']:
                return self._stopped('paid_api:antigravity_login:' + re.sub(r'[^A-Za-z0-9._-]', '_', self.source)[:40])
            self.confirmed = True
            return None
        if event.get('type') == 'step_update' and self.allowed is not None:
            name = tool_name(event)
            if name is False or (name is not None and name not in self.allowed):
                return self._stopped('configuration_stop:tool_outside_role')
            if event.get('step_type') == MCP_STEP:
                return self._stopped('configuration_stop:tool_outside_role')
        return None


DECODED = ('schema', 'engine', 'verdict', 'complete', 'result_line', 'finished_reason', 'malformed')


def verify(document, vocabulary=None):
    """Whether an artifact document is what its own lines, termination and stop cause decode to."""
    if not isinstance(document, dict) or not isinstance(document.get('lines'), list):
        return False
    again = Terminal(vocabulary)
    for line in document['lines']:
        again.feed(str(line).encode() + b'\n')
    fresh = again.document(document.get('termination'), document.get('cause'))
    return all(fresh[k] == document.get(k) for k in DECODED)
