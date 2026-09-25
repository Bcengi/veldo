"""Codex's login and usage reports as the launch receiver reads them, VELDO-0062.

LOGIN. A Codex run logs in only through its subscription account's profile, the directory CODEX_HOME
names (control_accounts sets it from the account the dispatch recorded). The API key variables that
would authenticate it another way are in PAID_API and never reach the engine. (Forcing the ChatGPT
login method and the file credential store are VELDO-0156.)

USAGE, FROM THE CLI'S OWN STREAM (`codex exec` with JSON output). What is counted is only what the
CLI reports:
- a `turn.completed` event closing a turn a `turn.started` opened, once per turn (a repeated
  delivery of a completion with no turn open changes nothing): tokens are its `usage` input and
  output token counts (cached input and reasoning output are parts of those), messages are the
  completed turns. Should the CLI report thread totals rather than the turn's own, summing them
  over-counts; it never under-counts;
- a turn that started and did not complete (`turn.failed`, or a stream that ended) leaves the totals
  unknown, and their reservation is retained; only an invocation whose every turn completed has a
  conclusive total;
- a `rate_limits` snapshot on any event: each of `primary` and `secondary` is a window, exhausted
  (`rejected`) at a `used_percent` of 100 or more, with its `resets_at` (Unix seconds) as the reported
  reset, else `resets_in_seconds` from the time the line was read; utilization is `used_percent` / 100.
  Nothing is invented: a missing reset stays missing.

Each observation carries the raw line it came from (the receipt) and that line's digest.
Standard library only.
"""
import hashlib
import json
import math
import time

PROVIDER = 'codex'
PROFILE = 'CODEX_HOME'
PAID_API = ('OPENAI_API_KEY', 'CODEX_API_KEY', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN', 'CLAUDE_CODE_OAUTH_TOKEN',
            'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX', 'CLAUDE_CODE_USE_FOUNDRY',
            'ANTHROPIC_FOUNDRY_API_KEY', 'AWS_BEARER_TOKEN_BEDROCK')
WINDOWS = ('primary', 'secondary')


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def receipt(line):
    return 'sha256:' + hashlib.sha256(line).hexdigest()


class Meter:
    """Reads one invocation's stream line by line; the same interface as control_engine_claude.Meter."""

    def __init__(self, clock=time.time):
        self.pending = b''
        self.clock = clock
        self.open = False
        self.incomplete = False
        self.turns = 0
        self.tokens = 0

    def feed(self, chunk):
        self.pending += chunk
        found = []
        while b'\n' in self.pending:
            line, _, self.pending = self.pending.partition(b'\n')
            found.extend(self.line(line))
        return found

    def close(self):
        line, self.pending = self.pending, b''
        found = self.line(line) if line.strip() else []
        if self.open:
            self.incomplete = True
        return found

    def cumulative(self):
        return {'tokens': self.tokens, 'messages': self.turns}

    def final(self):
        return self.cumulative() if self.turns and not self.open and not self.incomplete else {}

    def line(self, line):
        try:
            event = json.loads(line)
        except ValueError:
            return []
        if not isinstance(event, dict):
            return []
        seen = {'line': line, 'receipt': receipt(line)}
        found = []
        kind = event.get('type')
        if kind == 'turn.started':
            if self.open:
                self.incomplete = True
            self.open = True
        elif kind == 'turn.completed' and self.open:
            usage = event.get('usage')
            usage = usage if isinstance(usage, dict) else {}
            counts = [usage.get(f) for f in ('input_tokens', 'output_tokens')]
            self.open = False
            if all(_count(c) for c in counts):
                self.tokens += sum(counts)
                self.turns += 1
                found.append(dict(seen, kind='usage', usage=self.cumulative()))
            else:
                self.incomplete = True
        elif kind == 'turn.failed' and self.open:
            self.open, self.incomplete = False, True
        limits = event.get('rate_limits')
        if isinstance(limits, dict):
            for name in WINDOWS:
                window = limits.get(name)
                if not isinstance(window, dict) or not _number(window.get('used_percent')):
                    continue
                reset = window.get('resets_at')
                if not _number(reset):
                    after = window.get('resets_in_seconds')
                    reset = self.clock() + after if _number(after) else None
                found.append(dict(seen, kind='window', window_id=name,
                                  status='rejected' if window['used_percent'] >= 100 else 'allowed',
                                  reset_at=reset, utilization=max(0.0, window['used_percent'] / 100.0)))
        return found
