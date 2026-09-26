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
  and cacheCreationInputTokens. The result's `usage` is never read for accounting: the binary's schema
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
Standard library only.
"""
import hashlib
import json
import math
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

    def __init__(self, clock=time.time, zone=None):
        self.pending = b''
        self.messages = {}
        self.result = None

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
            total = {'tokens': _model_tokens(event.get('modelUsage')), 'messages': turns}
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
