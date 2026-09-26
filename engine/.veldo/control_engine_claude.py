"""Claude Code's login and usage reports as the launch receiver reads them, VELDO-0062.

Every format and name here is the installed CLI's own (Claude Code 2.1.281), read from the schema
its binary embeds for the stream JSON messages and from its credential tables; the extraction is
proof/VELDO-0062/extract_formats.py and its table cli-formats.json.

LOGIN. A Claude Code run logs in only through its subscription account's profile, the directory
CLAUDE_CONFIG_DIR names (control_accounts sets it from the account the dispatch recorded). CREDENTIALS
is every name the binary's own lists make a login: the API keys and bearer tokens, the provider
switches and their companions, the endpoint overrides, the skip-auth switches, its list of Anthropic
secrets with their INPUT_ forms, the session, bridge, trusted-device, background-session and
file-descriptor tokens, the variables a host credentials file may set, and every login, credential
redirect and settings redirect of the set of variables it refuses to take from a settings file
(CLAUDE_SECURESTORAGE_CONFIG_DIR, CLAUDE_CODE_HOST_CREDS_FILE, CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST, the
managed and remote settings paths, the OAuth, staging, bridge and federation overrides). None reaches
the engine from the inherited environment, and an adapter configuring one is refused by name.
SETTINGS are that set's Claude Code connection settings that are not a login: stripped from the
inherited environment (the owner's shell's), passed when the adapter configures them. The set's general
proxy, CA, runtime, cloud and home names are neither: the worker's tools need them. The model
configuration (the binary's model table, ANTHROPIC_MODEL and the rest) is not a login either: an adapter
configures it and it reaches the engine. (The subscription token of an account configured to use one
is VELDO-0155.)

USAGE, FROM THE CLI'S OWN STREAM (print mode with stream JSON output). What is counted is only what
the CLI reports, at the granularity it reports it:
- an `assistant` event's `message.usage`, once per message id (a message is streamed in several
  events with the same id and usage, and a repeated delivery changes nothing), the main loop's and a
  subagent's alike (`parent_tool_use_id` set): tokens are the sum of its input, output, cache
  creation and cache read token counts (the nullable ones count when present; the nested
  `cache_creation` and `server_tool_use` objects are breakdowns, never added); messages are the
  distinct assistant messages seen. These are the live observations a cap is checked against;
- the `result` event's `modelUsage`, the conclusive total: per model, over every model call of the
  invocation (main loop, Task subagents, sidechains, compaction), cumulative, so the latest result
  is read. Its tokens are the sum over every model of inputTokens, outputTokens, cacheReadInputTokens
  and cacheCreationInputTokens. The binary says a resumed or forked session continues from the totals
  its transcript saved, so the first result already carries the earlier turns: an invocation whose
  contract resumes a session (`resumes`, its id) and whose CLI reports that same session id is charged
  its result's total less `prior`, the resumed session's running total the ledger settled last
  (Reservations.session); an unknown `prior`, or a total below it, leaves this invocation's tokens
  unknown, never the whole total. When the CLI reports another session id than the one resumed (it
  started a fresh session, or forked one), nothing places its total against the resumed session's, so
  the whole running total is charged: a fork that carried the earlier turns is over-counted, never
  under-counted. `session()` is the session this invocation ran, the CLI's running total for it, which
  the final report settles for the next resumption, and which case charged it (`charged`: `whole` for
  no resumption, `difference` for the resumed session, `whole_other_session` for another one). The result's `usage` is never read for accounting: the binary's schema
  says it is the MAIN AGENT LOOP ONLY and to prefer modelUsage. A result without a readable
  modelUsage leaves tokens unknown (never zero, never the main loop's usage) and their reservation is
  retained. Messages are the distinct assistant messages or `num_turns`, whichever is more; only a
  result makes them conclusive;
- a `rate_limit_event`'s `rate_limit_info`: `rateLimitType` names the window, `status` `rejected`
  means its allowance is exhausted (`allowed` and `allowed_warning` are not), `resetsAt` is its
  reported reset (Unix seconds) and `utilization` what the CLI reported. Nothing is invented: a missing
  reset stays missing.
`total_cost_usd` and `costUSD` are never read: subscription usage has no per-call price.

Each observation carries the raw line it came from (the receipt) and that line's digest.

THE PINNED EXECUTABLE, VELDO-0060. A Claude Code adapter names the version it runs (`executable:
{version}`), never a path. The qualification record (QUALIFICATION, the installed
`.veldo/runtime/claude-qualification.json` beside this module, canonical at engine/runtime/) lists each
qualified version with its digest, the flags of print mode with stream JSON output (read from the
binary's own options, proof/VELDO-0060/cli-options.json), the environment it runs with
(DISABLE_AUTOUPDATER, the binary's switch that turns its updater off), its terminal protocol, its
subscription login and the usage units and rate-limit windows it reports. `pin` copies the versioned
file the installer keeps (~/.local/share/claude/versions/<version>) under the factory state root, at
<state root>/engines/claude_code/<version>, and refuses a copy whose digest is not the qualified one;
the interactive updater may remove an old version, and the auto-updating ~/.local/bin/claude link is
never read. `bind` is the check every launch makes before acceptance, so before anything is spawned: a
version the record does not list, a pinned copy that is absent, a link or not a regular file, and a
copy whose digest differs are each refused by name, as are a linked directory on the way to it, a copy
that is not this account's own, and one that is writable or carries a setuid, setgid or sticky bit (the pin
writes it 0555). `command` is the adapter's prefix, the pinned path and the qualified flags; the role's own
selections are VELDO-0127's and the everything-off baseline VELDO-0155's.

THE TERMINAL RECORD AND THE ARTIFACT, VELDO-0060. `Terminal` reads the same stream and returns what an
invocation's output yields, judged by the receiver and never by the worker: the decoded `result` event
(its subtype, error flag, turns, session, stop reason, the digest of its result text, its errors and
its tokens, modelUsage's total or None when the result carries no readable modelUsage, never its
main-loop `usage`),
the digest of the line it came from, how many lines the stream had and how many were not a JSON event,
and the verdict. Only a zero exit with no signal, no stop and no deadline, a stream of well-formed
events and a `result` whose subtype is `success` and whose `is_error` is false is `complete`; a zero
exit whose stream has no result is `missing_result`, never a completion. The usage of that invocation
is the Meter's: a result without readable usage leaves it unknown and its reservation retained.
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

PROVIDER = 'claude_code'
CREDENTIALS = frozenset((
    'AGENT_PROXY_AUTH_TOKEN', 'ALL_INPUTS', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN',
    'ANTHROPIC_AWS_API_KEY', 'ANTHROPIC_AWS_BASE_URL', 'ANTHROPIC_AWS_WORKSPACE_ID', 'ANTHROPIC_BASE_URL',
    'ANTHROPIC_BEDROCK_BASE_URL', 'ANTHROPIC_BEDROCK_MANTLE_BASE_URL', 'ANTHROPIC_CONFIG_DIR',
    'ANTHROPIC_CUSTOM_HEADERS', 'ANTHROPIC_FEDERATION_RULE_ID', 'ANTHROPIC_FOUNDRY_API_KEY',
    'ANTHROPIC_FOUNDRY_AUTH_TOKEN', 'ANTHROPIC_FOUNDRY_BASE_URL', 'ANTHROPIC_FOUNDRY_RESOURCE',
    'ANTHROPIC_GOOGLE_CLOUD_BASE_URL', 'ANTHROPIC_GOOGLE_CLOUD_LOCATION', 'ANTHROPIC_GOOGLE_CLOUD_PROJECT',
    'ANTHROPIC_GOOGLE_CLOUD_WORKSPACE_ID', 'ANTHROPIC_IDENTITY_TOKEN', 'ANTHROPIC_IDENTITY_TOKEN_FILE',
    'ANTHROPIC_ORGANIZATION_ID', 'ANTHROPIC_PROFILE', 'ANTHROPIC_SCOPE', 'ANTHROPIC_SERVICE_ACCOUNT_ID',
    'ANTHROPIC_UNIX_SOCKET', 'ANTHROPIC_VERTEX_BASE_URL', 'ANTHROPIC_VERTEX_PROJECT_ID',
    'ANTHROPIC_WORKSPACE_ID', 'AWS_BEARER_TOKEN_BEDROCK', 'CLAUDE_BG_AUTH_SNAPSHOT_PATH',
    'CLAUDE_BG_CLAIM_AUTH', 'CLAUDE_BG_PTY_AUTH', 'CLAUDE_BG_RV_AUTH', 'CLAUDE_BG_SOCKET_TOKENS_PATH',
    'CLAUDE_BRIDGE_BASE_URL', 'CLAUDE_BRIDGE_OAUTH_TOKEN', 'CLAUDE_BRIDGE_SESSION_INGRESS_URL',
    'CLAUDE_CODE_API_BASE_URL', 'CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR', 'CLAUDE_CODE_ARTIFACTS_API_BASE_URL',
    'CLAUDE_CODE_ARTIFACTS_API_TOKEN', 'CLAUDE_CODE_ARTIFACT_ASSET_BASE_URL',
    'CLAUDE_CODE_ARTIFACT_LIVE_BASE_URL', 'CLAUDE_CODE_ARTIFACT_SYNC_BASE_URL',
    'CLAUDE_CODE_ARTIFACT_VIEWER_BASE_URL', 'CLAUDE_CODE_CLIENT_CERT', 'CLAUDE_CODE_CLIENT_KEY',
    'CLAUDE_CODE_CLIENT_KEY_PASSPHRASE', 'CLAUDE_CODE_CUSTOM_OAUTH_URL',
    'CLAUDE_CODE_DISABLE_ADMIN_ENV_UNION', 'CLAUDE_CODE_ENVIRONMENT_KIND',
    'CLAUDE_CODE_FEDERATION_CACHE_DIR', 'CLAUDE_CODE_GATEWAY_TOKEN_FILE_DESCRIPTOR',
    'CLAUDE_CODE_HFI_BEARER_TOKEN', 'CLAUDE_CODE_HOST_AUTH_ENV_VAR', 'CLAUDE_CODE_HOST_CREDS_FILE',
    'CLAUDE_CODE_HOST_SESSION_ID', 'CLAUDE_CODE_MANAGED_SETTINGS_PATH', 'CLAUDE_CODE_MCP_SERVE_AUTH_TOKEN',
    'CLAUDE_CODE_MEMORY_API_BASE_URL', 'CLAUDE_CODE_MEMORY_API_TOKEN', 'CLAUDE_CODE_MOCK_REMOTE_SETTINGS',
    'CLAUDE_CODE_OAUTH_CLIENT_ID', 'CLAUDE_CODE_OAUTH_REFRESH_TOKEN', 'CLAUDE_CODE_OAUTH_SCOPES',
    'CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR',
    'CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST', 'CLAUDE_CODE_REMOTE_SESSION_ID',
    'CLAUDE_CODE_REMOTE_SETTINGS_PATH', 'CLAUDE_CODE_SESSION_ACCESS_TOKEN',
    'CLAUDE_CODE_SKIP_ANTHROPIC_AWS_AUTH', 'CLAUDE_CODE_SKIP_ANTHROPIC_GOOGLE_CLOUD_AUTH',
    'CLAUDE_CODE_SKIP_BEDROCK_AUTH', 'CLAUDE_CODE_SKIP_FOUNDRY_AUTH', 'CLAUDE_CODE_SKIP_MANTLE_AUTH',
    'CLAUDE_CODE_SKIP_VERTEX_AUTH', 'CLAUDE_CODE_SLACK_TAG_TOKEN', 'CLAUDE_CODE_USE_ANTHROPIC_AWS',
    'CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD', 'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_FOUNDRY',
    'CLAUDE_CODE_USE_GATEWAY', 'CLAUDE_CODE_USE_MANTLE', 'CLAUDE_CODE_USE_VERTEX',
    'CLAUDE_CODE_WEBSOCKET_AUTH_FILE_DESCRIPTOR', 'CLAUDE_CONFIG_DIR', 'CLAUDE_LOCAL_OAUTH_API_BASE',
    'CLAUDE_LOCAL_OAUTH_APPS_BASE', 'CLAUDE_LOCAL_OAUTH_CONSOLE_BASE', 'CLAUDE_REMOTE_TOOLS_BRIDGE_URL',
    'CLAUDE_SECURESTORAGE_CONFIG_DIR', 'CLAUDE_SESSION_INGRESS_TOKEN_FILE', 'CLAUDE_TRUSTED_DEVICE_TOKEN',
    'CLOUD_ML_REGION', 'INPUT_ALL_INPUTS', 'INPUT_ANTHROPIC_API_KEY', 'INPUT_ANTHROPIC_AUTH_TOKEN',
    'INPUT_ANTHROPIC_AWS_API_KEY', 'INPUT_ANTHROPIC_CUSTOM_HEADERS', 'INPUT_ANTHROPIC_FOUNDRY_API_KEY',
    'INPUT_ANTHROPIC_FOUNDRY_AUTH_TOKEN', 'INPUT_ANTHROPIC_IDENTITY_TOKEN',
    'INPUT_ANTHROPIC_IDENTITY_TOKEN_FILE', 'INPUT_CLAUDE_CODE_ARTIFACTS_API_TOKEN',
    'INPUT_CLAUDE_CODE_MEMORY_API_TOKEN', 'INPUT_CLAUDE_CODE_OAUTH_REFRESH_TOKEN',
    'INPUT_CLAUDE_CODE_OAUTH_TOKEN', 'INPUT_CLAUDE_CODE_SLACK_TAG_TOKEN', 'USE_LOCAL_OAUTH',
    'USE_STAGING_OAUTH', '_CLAUDE_CODE_ASSUME_FIRST_PARTY_BASE_URL'))
SETTINGS = frozenset((
    'API_FORCE_IDLE_TIMEOUT', 'CLAUDE_CODE_CERT_STORE', 'CLAUDE_CODE_ENABLE_PROXY_AUTH_HELPER',
    'CLAUDE_CODE_PROXY_AUTH_HELPER_TTL_MS', 'CLAUDE_CODE_PROXY_RESOLVES_HOSTS'))
TOKEN_FIELDS = ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')
MODEL_TOKEN_FIELDS = ('inputTokens', 'outputTokens', 'cacheReadInputTokens', 'cacheCreationInputTokens')


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _tokens(usage):
    """A message's tokens: its four counts, a nullable one counted when present; None if unreadable."""
    if not isinstance(usage, dict) or not all(_count(usage.get(f)) for f in TOKEN_FIELDS[:2]):
        return None
    counts = [usage[f] for f in TOKEN_FIELDS if usage.get(f) is not None]
    return sum(counts) if all(_count(c) for c in counts) else None


def _model_tokens(model_usage):
    """The invocation's tokens over every model in `modelUsage`; None if absent or unreadable."""
    if not isinstance(model_usage, dict):
        return None
    total = 0
    for entry in model_usage.values():
        if not isinstance(entry, dict) or not all(_count(entry.get(f)) for f in MODEL_TOKEN_FIELDS):
            return None
        total += sum(entry[f] for f in MODEL_TOKEN_FIELDS)
    return total


def receipt(line):
    return 'sha256:' + hashlib.sha256(line).hexdigest()


class Meter:
    """Reads one invocation's stream line by line. `feed(bytes)` returns the observations the
    complete lines in it make: {'kind': 'usage', 'usage': cumulative {tokens, messages}} or
    {'kind': 'window', 'window_id', 'status', 'reset_at', 'utilization'}, each with its `line` and
    `receipt`. `final()` is the conclusive total, without tokens when the result had no readable
    modelUsage and empty when the CLI reported no result. `clock` and `zone` are the engine's clock
    and local time zone, for a CLI that states times in local time (this one does not)."""

    def __init__(self, clock=time.time, zone=None, resumes=None, prior=None):
        self.pending = b''
        self.messages = {}
        self.result = None
        self.resumes = resumes if isinstance(resumes, str) and resumes else None
        self.prior = prior if _count(prior) else None
        self.session_id = None
        self.session_total = None

    def charged(self):
        """Which case charges this invocation: `whole` when its contract resumes no session, `difference`
        when the CLI reports the session the contract resumes, `whole_other_session` when it reports
        another one (or none)."""
        if self.resumes is None:
            return 'whole'
        return 'difference' if self.session_id == self.resumes else 'whole_other_session'

    def _own(self, total):
        """This invocation's share of a result's running total: all of it in a new session, or when the CLI
        reports another session than the one resumed; in the resumed session the total less its settled
        total, unknown when that is unknown or the total is below it (the running total cannot then be
        placed)."""
        if total is None or self.charged() != 'difference':
            return total
        if self.prior is None or total < self.prior:
            return None
        return total - self.prior

    def session(self):
        """{provider, id, tokens, charged}: the CLI session this invocation ran, its running token total at
        the end (None without a result carrying modelUsage) and which case charged it (`charged()`); None
        when the CLI named no session."""
        if self.session_id is None:
            return None
        return {'provider': PROVIDER, 'id': self.session_id, 'tokens': self.session_total,
                'charged': self.charged()}

    def feed(self, chunk):
        self.pending += chunk
        found = []
        while b'\n' in self.pending:
            line, _, self.pending = self.pending.partition(b'\n')
            found.extend(self.line(line))
        return found

    def close(self):
        """The last line when the stream ended without a newline."""
        line, self.pending = self.pending, b''
        return self.line(line) if line.strip() else []

    def cumulative(self):
        tokens = sum(self.messages.values())
        messages = len(self.messages)
        if self.result is not None:
            messages = max(messages, self.result['messages'])
            if self.result['tokens'] is not None:
                tokens = max(tokens, self.result['tokens'])
        return {'tokens': tokens, 'messages': messages}

    def final(self):
        if self.result is None:
            return {}
        total = self.cumulative()
        if self.result['tokens'] is None:
            del total['tokens']  # No modelUsage: the tokens stay unknown.
        return total

    def line(self, line):
        try:
            event = json.loads(line)
        except ValueError:
            return []
        if not isinstance(event, dict):
            return []
        kind = event.get('type')
        seen = {'line': line, 'receipt': receipt(line)}
        if isinstance(event.get('session_id'), str) and event['session_id']:
            self.session_id = event['session_id']
        if kind == 'assistant':
            message = event.get('message')
            message = message if isinstance(message, dict) else {}
            tokens = _tokens(message.get('usage'))
            ident = message.get('id')
            if tokens is None or not isinstance(ident, str) or not ident:
                return []
            if self.messages.get(ident, -1) >= tokens:
                return []  # The same message again: nothing new to count.
            self.messages[ident] = tokens
            return [dict(seen, kind='usage', usage=self.cumulative())]
        if kind == 'result':
            turns = event.get('num_turns')
            if not _count(turns):
                return []
            running = _model_tokens(event.get('modelUsage'))
            if running is not None:
                self.session_total = running if self.session_total is None else max(self.session_total, running)
            total = {'tokens': self._own(running), 'messages': turns}
            prior = self.result
            if prior is not None:
                # Cumulative: the latest result's totals, never below what an earlier one reported.
                total = {'messages': max(turns, prior['messages']),
                         'tokens': None if total['tokens'] is None and prior['tokens'] is None
                         else max(t for t in (total['tokens'], prior['tokens']) if t is not None)}
                if total == prior:
                    return []  # The same total again settles nothing twice.
            self.result = total
            return [dict(seen, kind='usage', usage=self.cumulative())]
        if kind == 'rate_limit_event':
            info = event.get('rate_limit_info')
            info = info if isinstance(info, dict) else {}
            status = info.get('status')
            if not isinstance(status, str):
                return []
            reset = info.get('resetsAt')
            utilization = info.get('utilization')
            return [dict(seen, kind='window', window_id=str(info.get('rateLimitType') or 'unified'),
                         status='rejected' if status == 'rejected' else 'allowed',
                         reset_at=reset if _number(reset) else None,
                         utilization=utilization if _number(utilization) and utilization >= 0 else None)]
        return []


# VELDO-0060: the pinned executable, its command line and the terminal record.

QUALIFICATION = 'runtime/claude-qualification.json'
QUALIFICATION_SCHEMA = 'veldo.engine_qualification/v1'
ARTIFACT_SCHEMA = 'veldo.engine_artifact/v1'
# The adapter registration (control_launch.ENGINE_PROTOCOL): its lifecycle operations, each with what
# performs it for this engine, in the order the receiver drives them; the suite enumerates them here.
REGISTRATION = {
    'engine': PROVIDER,
    'lifecycle': {
        'accept': 'control_launch.Receiver.launch: the executable bound (bind) and the acceptance recorded before the spawn',
        'launch': 'control_launch.Receiver._spawn: the pinned command (command) in the dispatch\'s wrapper',
        'observe': 'Meter.feed and Terminal.feed over the stream JSON the engine prints',
        'stop': 'control_launch.Launch.stop: the runner\'s stop request to the receiver',
        'exit': 'control_launch.Receiver._reap: the reaped exit recorded on the dispatch',
        'artifacts': 'Terminal.document: the decoded terminal record and its verdict, the exit record\'s artifact',
    },
}
VERSION_TEXT = re.compile(r'[0-9]+(?:\.[0-9]+){1,3}')
STOPS = ('requested', 'usage_cap', 'heartbeat_missing')


class Refused(Exception):
    def __init__(self, code, detail=''):
        self.code, self.detail = code, detail
        super().__init__(code + (': ' + detail if detail else ''))


def _file_digest(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return 'sha256:' + digest.hexdigest()


def qualification(path=None):
    """The installed qualification record, beside this module; refused by name when unreadable."""
    path = Path(path) if path is not None else Path(__file__).resolve().parent / QUALIFICATION
    try:
        record = json.loads(path.read_text())
    except (OSError, ValueError):
        raise Refused('missing_evidence:engine_qualification', str(path))
    if (not isinstance(record, dict) or record.get('schema') != QUALIFICATION_SCHEMA
            or record.get('engine') != PROVIDER or not isinstance(record.get('versions'), dict)):
        raise Refused('invalid_input:engine_qualification', str(path))
    return record


def qualified(version, record=None):
    """The qualified entry of `version`: refused by name when the record does not list it."""
    record = qualification() if record is None else record
    entry = record['versions'].get(version) if isinstance(version, str) and VERSION_TEXT.fullmatch(version) else None
    if (not isinstance(entry, dict) or not isinstance(entry.get('sha256'), str)
            or not isinstance(entry.get('flags'), list)):
        raise Refused('invalid_input:engine_version:%s' % version, 'no qualified Claude Code version')
    return entry


def pinned_path(state_root, version):
    return Path(state_root) / 'engines' / PROVIDER / version


def pin(version, *, versions, state_root, record=None):
    """Copy the installer's versioned executable `versions/<version>` under the factory state root and
    return its binding. The copy is a new regular file (written beside, then renamed into place) whose
    digest must be the qualified one; a source that is a link, or that the record does not qualify, is
    refused and nothing is left in place."""
    entry = qualified(version, record)
    source = Path(versions) / version
    try:
        info = os.lstat(source)
    except OSError:
        raise Refused('missing_evidence:engine_source', str(source))
    if not stat.S_ISREG(info.st_mode):
        raise Refused('binding_mismatch:engine_source', 'the versioned executable is not a regular file')
    target = pinned_path(state_root, version)
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    partial = target.parent / ('.%s.%s.partial' % (version, os.urandom(6).hex()))
    try:
        with open(source, 'rb') as reading, open(partial, 'xb') as writing:
            shutil.copyfileobj(reading, writing, 1 << 20)
        os.chmod(partial, 0o555)
        if _file_digest(partial) != entry['sha256']:
            raise Refused('binding_mismatch:engine_digest', 'the versioned executable is not the qualified one')
        os.replace(partial, target)
    finally:
        if partial.exists():
            partial.unlink()
    return bind({'executable': {'version': version}}, state_root, record)


def bind(adapter, state_root, record=None):
    """{engine, version, path, sha256, flags}: the executable a launch of `adapter` runs, checked before
    anything is accepted or spawned (control_launch.ENGINE_PROTOCOL). The adapter names a qualified
    version (`executable: {version}`); its pinned copy under the state root must be a regular file (not
    a link) whose digest is the qualified one."""
    executable = adapter.get('executable') if isinstance(adapter, dict) else None
    version = executable.get('version') if isinstance(executable, dict) else None
    entry = qualified(version, record)
    if not isinstance(state_root, str) or not os.path.isabs(state_root):
        raise Refused('missing_authority:engine_state_root', 'the receiver names no factory state root')
    path = pinned_path(state_root, version)
    try:
        info = os.lstat(path)
    except OSError:
        raise Refused('missing_evidence:engine_executable', str(path))
    if not stat.S_ISREG(info.st_mode):
        raise Refused('binding_mismatch:engine_executable', 'the pinned executable is not a regular file')
    if os.path.realpath(path.parent) != os.path.normpath(str(path.parent)):
        raise Refused('binding_mismatch:engine_path', 'a directory on the way to the pinned executable is a link')
    if info.st_uid != os.geteuid():
        raise Refused('binding_mismatch:engine_owner', 'the pinned executable is not this account\'s own copy')
    if info.st_mode & 0o7222:
        raise Refused('binding_mismatch:engine_mode', 'the pinned executable is writable or carries a special bit')
    if _file_digest(path) != entry['sha256']:
        raise Refused('binding_mismatch:engine_digest', 'the pinned executable is not the qualified one')
    return {'engine': PROVIDER, 'version': version, 'path': str(path), 'sha256': entry['sha256'],
            'flags': list(entry['flags'])}


def command(bound, adapter):
    """The engine's argv: the adapter's configured prefix (its clone entrance, or a transport's trusted
    wrapper), then the pinned path and its version's qualified flags."""
    return list(adapter.get('argv') or []) + [bound['path']] + list(bound['flags'])


def environment(bound, record=None):
    """What the engine's environment always carries for its version (DISABLE_AUTOUPDATER)."""
    return dict(qualified(bound['version'], record).get('environment') or {})


def _text(value):
    return isinstance(value, str)


def _terminal(event):
    """The decoded `result` event, or None when it is not one the CLI's schema declares."""
    subtype, turns = event.get('subtype'), event.get('num_turns')
    errors = event.get('errors')
    if (not _text(subtype) or not isinstance(event.get('is_error'), bool) or not _count(turns)
            or not _text(event.get('session_id')) or not (event.get('stop_reason') is None or _text(event['stop_reason']))):
        return None
    if subtype == 'success':
        if not _text(event.get('result')):
            return None
        text, errors = event['result'], []
    elif subtype.startswith('error_') and isinstance(errors, list) and all(_text(e) for e in errors):
        text = None
    else:
        return None
    # Its usage is modelUsage's total over every model, the invocation's; without a readable modelUsage the
    # tokens are unknown (None), never the result's `usage`, which is the main agent loop's alone.
    return {'subtype': subtype, 'is_error': event['is_error'], 'num_turns': turns, 'session_id': event['session_id'],
            'stop_reason': event.get('stop_reason'), 'errors': list(errors),
            'tokens': _model_tokens(event.get('modelUsage')),
            'result_digest': None if text is None else 'sha256:' + hashlib.sha256(text.encode()).hexdigest()}


class Terminal:
    """What one invocation's stdout returns: `feed(bytes)` line by line, `close()` for the last line, then
    `document(termination, cause)`. A line that is not a JSON object with a string `type`, or a `result`
    the schema does not declare, is malformed; the latest well-formed result is the terminal record."""

    def __init__(self):
        self.pending = b''
        self.lines = 0
        self.malformed = 0
        self.result = None
        self.receipt = None

    def feed(self, chunk):
        self.pending += chunk
        while b'\n' in self.pending:
            line, _, self.pending = self.pending.partition(b'\n')
            self._line(line)

    def close(self):
        line, self.pending = self.pending, b''
        self._line(line)

    def _line(self, line):
        if not line.strip():
            return
        self.lines += 1
        try:
            event = json.loads(line)
        except ValueError:
            event = None
        if not isinstance(event, dict) or not _text(event.get('type')):
            self.malformed += 1
            return
        if event['type'] == 'result':
            decoded = _terminal(event)
            if decoded is None:
                self.malformed += 1
                return
            self.result, self.receipt = decoded, receipt(line)

    def problems(self, termination, cause):
        """Every reason the output is not a completion, the first the verdict; [] when it is one."""
        if termination is None:
            return ['not_executed']
        found = []
        if cause in STOPS:
            found.append('stopped')
        if termination.get('deadline_stop'):
            found.append('timeout')
        if termination.get('signal') is not None:
            found.append('signal')
        elif termination.get('returncode') != 0:
            found.append('nonzero_exit')
        if self.malformed:
            found.append('malformed_output')
        if self.result is None:
            found.append('missing_result')
        elif self.result['subtype'] != 'success' or self.result['is_error']:
            found.append('engine_error')
        return found

    def document(self, termination, cause):
        """The artifact of the invocation (control_launch.ENGINE_PROTOCOL's shape: schema, engine, verdict,
        complete): its verdict, every problem, the terminal record and the stream."""
        problems = self.problems(termination, cause)
        return {'schema': ARTIFACT_SCHEMA, 'engine': PROVIDER, 'verdict': problems[0] if problems else 'complete',
                'complete': not problems, 'problems': problems, 'terminal': self.result, 'terminal_receipt': self.receipt,
                'stream': {'lines': self.lines, 'malformed': self.malformed,
                           'output_digest': (termination or {}).get('output_digest'),
                           'output_bytes': (termination or {}).get('output_bytes')},
                'exit': {'returncode': (termination or {}).get('returncode'), 'signal': (termination or {}).get('signal'),
                         'deadline_stop': (termination or {}).get('deadline_stop'), 'cause': cause}}
