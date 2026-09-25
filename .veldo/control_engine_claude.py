"""Claude Code's login and usage reports as the launch receiver reads them, VELDO-0062.

LOGIN. A Claude Code run logs in only through its subscription account's profile, the directory
CLAUDE_CONFIG_DIR names (control_accounts sets it from the account the dispatch recorded). Every
variable that would authenticate it another way, a paid API key or token, or a switch to the Bedrock,
Vertex or Foundry APIs, is in PAID_API and never reaches the engine. (The subscription token of
an account configured to use one, and qualifying the switches on the pinned version, are
VELDO-0155.)

USAGE, FROM THE CLI'S OWN STREAM (print mode with stream JSON output). What is counted is only what
the CLI reports, at the granularity it reports it:
- an `assistant` event's `message.usage`, once per message id (a message is streamed in several
  events with the same id and usage, and a repeated delivery changes nothing): tokens are the sum of
  its input, output, cache creation and cache read token counts; messages are the distinct assistant
  messages seen;
- the `result` event, the CLI's own total for the invocation, once: its `usage` token counts and
  `num_turns`. Only a result makes the token and message totals conclusive; without one they stay
  unknown and their reservation is retained;
- a `rate_limit_event`'s `rate_limit_info`: `rateLimitType` names the window, `status` `rejected`
  means its allowance is exhausted, `resetsAt` is its reported reset (Unix seconds) and `utilization`
  what the CLI reported. Nothing is invented: a missing reset stays missing.
`total_cost_usd` is never read: subscription usage has no per-call price.

Each observation carries the raw line it came from (the receipt) and that line's digest.
Standard library only.
"""
import hashlib
import json
import math

PROVIDER = 'claude_code'
PROFILE = 'CLAUDE_CONFIG_DIR'
PAID_API = ('ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_CODE_USE_BEDROCK',
            'CLAUDE_CODE_USE_VERTEX', 'CLAUDE_CODE_USE_FOUNDRY', 'ANTHROPIC_FOUNDRY_API_KEY',
            'AWS_BEARER_TOKEN_BEDROCK', 'OPENAI_API_KEY', 'CODEX_API_KEY')
TOKEN_FIELDS = ('input_tokens', 'output_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens')


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _tokens(usage):
    if not isinstance(usage, dict):
        return None
    counts = [usage[f] for f in TOKEN_FIELDS if f in usage]
    if not counts or not all(_count(c) for c in counts):
        return None
    return sum(counts)


def receipt(line):
    return 'sha256:' + hashlib.sha256(line).hexdigest()


class Meter:
    """Reads one invocation's stream line by line. `feed(bytes)` returns the observations the
    complete lines in it make: {'kind': 'usage', 'usage': cumulative {tokens, messages}} or
    {'kind': 'window', 'window_id', 'status', 'reset_at', 'utilization'}, each with its `line` and
    `receipt`. `final()` is the conclusive total, empty when the CLI reported none."""

    def __init__(self):
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
            tokens, messages = max(tokens, self.result['tokens']), max(messages, self.result['messages'])
        return {'tokens': tokens, 'messages': messages}

    def final(self):
        return self.cumulative() if self.result is not None else {}

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
            tokens = _tokens(event.get('usage'))
            turns = event.get('num_turns')
            if self.result is not None or tokens is None or not _count(turns):
                return []  # One total per invocation; a repeated result settles nothing twice.
            self.result = {'tokens': tokens, 'messages': turns}
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
