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

THE ACCOUNT'S LIMIT (VELDO-0160). `limit()` is the last limit the stream stated, with its window, reset
and signal: a `rate_limit_event` whose status is `rejected` (the stream reports its window exhausted,
`stream`), or the rate-limit result (`result`): a `result` with `is_error` whose text is the binary's
usage-limit message, "You've hit your <limit>" and, when it states one, " \u00b7 resets <time> (<zone>)"
(its limit names are the binary's table of rate-limit windows, LIMIT_NAMES; a name outside it is the
`unified` window). The time is the binary's own format in the zone it names: "3pm" or "3:05pm" for a
reset within a day (the next such minute), "Sep 28, 3pm" with the year when it is another year. The reset
is the END of the stated minute (the message truncates to the minute, so the window never reopens before
it); a message stating none, or a time this reading cannot place, is a window with no reset, and the
account stays refused until a later observation says otherwise. The rate-limit result is also recorded
as a window. Any other message (the binary's "Server is temporarily limiting requests (not your usage
limit)", an overloaded model) is not the account's limit.

MCP CALLS (VELDO-0160). `mcp_calls(event)` names the MCP tool calls an event of the stream shows: each
`tool_use` block of an `assistant` message whose name is `mcp__<server>__<tool>`, by its id.

Each observation carries the raw line it came from (the receipt) and that line's digest.
Standard library only.
"""
import datetime
import hashlib
import json
import math
import re
import time
import zoneinfo

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
# VELDO-0160: the usage-limit message of the binary's rate-limit result, and its names of the windows
# (proof/VELDO-0062/cli-formats.json, claude_code usage_limit).
LIMIT_MESSAGE = "You've hit your "
LIMIT_NAMES = {'session limit': 'five_hour', 'weekly limit': 'seven_day', 'Opus limit': 'seven_day_opus',
               'Sonnet limit': 'seven_day_sonnet', 'Fable limit': 'seven_day_overage_included',
               'usage credit limit': 'overage'}
LIMIT_WINDOW = 'unified'
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
RESETS = re.compile(r'resets (?:(?P<month>[A-Z][a-z]{2}) (?P<day>\d{1,2}), (?:(?P<year>\d{4}), )?)?'
                    r'(?P<hour>\d{1,2})(?::(?P<minute>\d{2}))?(?P<half>am|pm) \((?P<zone>[^()]+)\)')
MCP_PREFIX = 'mcp__'


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


def _zone(name):
    try:
        return datetime.timezone.utc if name in ('UTC', 'Etc/UTC', 'GMT') else zoneinfo.ZoneInfo(name)
    except (ValueError, zoneinfo.ZoneInfoNotFoundError):
        return None


def limit_window(text):
    """The window a usage-limit message names, or None when the text is not the usage-limit message."""
    if not isinstance(text, str) or not text.startswith(LIMIT_MESSAGE):
        return None
    name = text[len(LIMIT_MESSAGE):].split(' \u00b7 ', 1)[0]
    return LIMIT_NAMES.get(name, LIMIT_WINDOW)


def limit_reset(text, now):
    """The Unix time a usage-limit message says its window resets, the end of the stated minute in the zone
    it names; None when it states none or it cannot be placed. A time with no date is the next such minute."""
    found = RESETS.search(text or '')
    tz = _zone(found['zone']) if found else None
    if tz is None:
        return None
    hour = int(found['hour']) % 12 + (12 if found['half'] == 'pm' else 0)
    minute = int(found['minute'] or 0)
    try:
        today = datetime.datetime.fromtimestamp(now, tz).date()
        if found['month']:
            dates = [datetime.date(int(found['year'] or today.year), MONTHS.index(found['month']) + 1, int(found['day']))]
        else:
            dates = [today, today + datetime.timedelta(days=1)]
        for date in dates:
            end = max(datetime.datetime(date.year, date.month, date.day, hour, minute, fold=fold, tzinfo=tz).timestamp()
                      for fold in (0, 1)) + 60
            if found['month'] or end > now:
                return end
    except ValueError:
        return None
    return None


def mcp_calls(event):
    """[{id, server, tool}]: the MCP tool calls an event of the stream shows (VELDO-0160)."""
    if not isinstance(event, dict) or event.get('type') != 'assistant':
        return []
    content = (event.get('message') or {}).get('content') if isinstance(event.get('message'), dict) else None
    found = []
    for block in content if isinstance(content, list) else []:
        name = block.get('name') if isinstance(block, dict) and block.get('type') == 'tool_use' else None
        if isinstance(name, str) and name.startswith(MCP_PREFIX):
            server, _, tool = name[len(MCP_PREFIX):].partition('__')
            found.append({'id': block.get('id'), 'server': server, 'tool': tool})
    return found


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
        self.clock = clock
        self.limited = None

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

    def limit(self):
        """{window, reset_at, signal}: the last limit the stream stated (VELDO-0160), or None."""
        return dict(self.limited) if self.limited else None

    def _result_limit(self, event, seen):
        """The rate-limit result as its window, exhausted: a result with `is_error` whose text is the
        usage-limit message, with the reset it states (or none)."""
        text = event.get('result')
        window = limit_window(text) if event.get('is_error') is True else None
        if window is None:
            return []
        reset = limit_reset(text, self.clock())
        self.limited = {'window': window, 'reset_at': reset, 'signal': 'result'}
        return [dict(seen, kind='window', window_id=window, status='rejected', reset_at=reset, utilization=None)]

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
            found = self._result_limit(event, seen)
            turns = event.get('num_turns')
            if not _count(turns):
                return found
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
                    return found  # The same total again settles nothing twice.
            self.result = total
            return found + [dict(seen, kind='usage', usage=self.cumulative())]
        if kind == 'rate_limit_event':
            info = event.get('rate_limit_info')
            info = info if isinstance(info, dict) else {}
            status = info.get('status')
            if not isinstance(status, str):
                return []
            reset = info.get('resetsAt')
            utilization = info.get('utilization')
            if status == 'rejected':
                # VELDO-0160: the stream reports its window exhausted.
                self.limited = {'window': str(info.get('rateLimitType') or LIMIT_WINDOW),
                                'reset_at': reset if _number(reset) else None, 'signal': 'stream'}
            return [dict(seen, kind='window', window_id=str(info.get('rateLimitType') or 'unified'),
                         status='rejected' if status == 'rejected' else 'allowed',
                         reset_at=reset if _number(reset) else None,
                         utilization=utilization if _number(utilization) and utilization >= 0 else None)]
        return []
