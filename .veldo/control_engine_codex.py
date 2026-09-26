"""Codex's login and usage reports as the launch receiver reads them, VELDO-0062.

Every format and name here is the installed CLI's own (Codex 0.154.0), read from the literals of its
binary: the serde names of `codex exec --json` events and their payloads, its usage-limit message
and its credential tables; the extraction is proof/VELDO-0062/extract_formats.py and its table
cli-formats.json.

LOGIN. A Codex run logs in only through its subscription account's profile, the directory CODEX_HOME
names (control_accounts sets it from the account the dispatch recorded, and strips the OPENAI_ and
CODEX_ families from the inherited environment). CREDENTIALS is every name the binary's own auth
tables make a login: the API key and access token variables, the agent identity variables and
endpoints, the login endpoint, client, issuer and token refresh and revocation overrides, the ChatGPT
backend, the model endpoints (OPENAI_BASE_URL, the local provider's), the organization an API key bills
and CODEX_SQLITE_HOME, the thread state beside CODEX_HOME. An adapter configuring one is refused by
name; its other CODEX_ settings pass. (Forcing the ChatGPT login method and the file credential store
are VELDO-0156.)

USAGE, FROM THE CLI'S OWN STREAM (`codex exec` with JSON output). Its events are `thread.started`,
`turn.started`, `turn.completed` (with `usage`), `turn.failed` (with `error.message`), the `item.*`
events and `error` (with `message`). What is counted is only what the CLI reports:
- a `turn.completed` event closing a turn a `turn.started` opened, once per turn (a repeated
  delivery of a completion with no turn open changes nothing): tokens are its `usage` input and
  output token counts (cached input and reasoning output are parts of those), messages are the
  completed turns. Should the CLI report thread totals rather than the turn's own, summing them
  over-counts; it never under-counts;
- a turn that started and did not complete (`turn.failed`, or a stream that ended) leaves the totals
  unknown, and their reservation is retained; only an invocation whose every turn completed has a
  conclusive total.
A RESUMED THREAD IS NOT SUBTRACTED. The binary shows that exec's turn usage comes from the thread token
usage its event processor receives, a thread total and a last-turn figure, but its strings do not say
which one `turn.completed` copies (proof/VELDO-0062/cli-formats.json, codex notes). Subtracting the
resumed thread's settled total would under-count if it is the turn's own; the sum of this invocation's
own completed turns never counts less than the CLI recorded under either reading. So `resumed` and
`prior` are accepted for the common interface and not used; `session()` still names the thread and its
conclusive sum for the ledger.

THE LIMIT SIGNAL. `codex exec --json` prints no rate-limit snapshot (its `rate_limits` exist only in
an internal event that exec does not emit). What it prints when the subscription's allowance is
exhausted is the usage-limit error, as an `error` event and the failed turn's `error.message`:
"You've hit your usage limit." (with a plan-specific sentence), then either " Try again at <time>."
(or " or try again at <time>.") or " Try again later.". The time is the engine's LOCAL time, "%-I:%M %p"
for a reset later the same day and "%b %-d<st|nd|rd|th>, %Y %-I:%M %p" otherwise. That message is a
`usage_limit` window, exhausted (`rejected`), with its reset at the END of the stated minute (the
message truncates to the minute, so the window never reopens before the time it stated), in the zone
the engine ran in (`zone`, its TZ; unset, the system's). A message that states no reset, or one this
reading cannot place in time, is a window with no reset: the account stays refused until a later
observation says otherwise. Utilization is not stated and stays unknown. The usage-limit message has
seven forms in the binary's error table (a plan's own sentence, a model's own limit, an admin's), all
starting with that text. The table's other exhaustion messages (EXHAUSTED: the workspace out of
credits, the workspace spend cap, the quota exceeded, a plan without Codex) state no reset: each is its
own window with none, and the account stays refused until observed otherwise. The rest of the table
(transient, request and local errors, Codex's own rollout and thread budgets) states no allowance and
records nothing.

Each observation carries the raw line it came from (the receipt) and that line's digest.
Standard library only.
"""
import datetime
import hashlib
import json
import re
import time
import zoneinfo

PROVIDER = 'codex'
CREDENTIALS = frozenset((
    'CODEX_ACCESS_TOKEN', 'CODEX_AGENT_IDENTITY_AUTHAPI_BASE_URL', 'CODEX_AGENT_IDENTITY_JWKS_BASE_URL',
    'CODEX_API_KEY', 'CODEX_APP_SERVER_CHATGPT_BASE_URL', 'CODEX_APP_SERVER_LOGIN_CLIENT_ID',
    'CODEX_APP_SERVER_LOGIN_ISSUER', 'CODEX_AUTHAPI_BASE_URL', 'CODEX_OSS_BASE_URL', 'CODEX_OSS_PORT',
    'CODEX_REFRESH_TOKEN_URL_OVERRIDE', 'CODEX_REVOKE_TOKEN_URL_OVERRIDE', 'CODEX_SQLITE_HOME',
    'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'OPENAI_FEDERATION_RULE_ID', 'OPENAI_IDENTITY_TOKEN_FILE',
    'OPENAI_ORGANIZATION'))
# No Codex list holds a non-login setting that the families would not already strip.
SETTINGS = frozenset()
LIMIT_MESSAGE = "You've hit your usage limit"
LIMIT_WINDOW = 'usage_limit'
# The other messages of the binary's error table that say the account's allowance is exhausted, each with
# the window it is recorded as; none states a reset (proof/VELDO-0062/cli-formats.json, codex errors).
EXHAUSTED = (
    ('Your workspace is out of credits. Add credits to continue.', 'workspace_credits'),
    ('Your workspace is out of credits. Ask your workspace owner to refill in order to continue.', 'workspace_credits'),
    ('You hit your spend cap set in your workspace. Increase your spend cap to continue.', 'workspace_spend_cap'),
    ('You hit your spend cap set by the owner of your workspace. Ask an owner to increase your spend cap to continue.',
     'workspace_spend_cap'),
    ('Quota exceeded. Check your plan and billing details.', 'quota'),
    ('To use Codex with your ChatGPT plan, upgrade to Plus: https://chatgpt.com/explore/plus.', 'plan'),
)
MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')
RETRY_AT = re.compile(r'(?:Try|or try) again at (?:(?P<month>[A-Z][a-z]{2}) (?P<day>\d{1,2})(?:st|nd|rd|th), '
                      r'(?P<year>\d{4}) )?(?P<hour>\d{1,2}):(?P<minute>\d{2}) (?P<half>AM|PM)\.')


def _count(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def receipt(line):
    return 'sha256:' + hashlib.sha256(line).hexdigest()


def _zone(name):
    """The tzinfo of a TZ value, the system's for None, or None when it cannot be resolved."""
    try:
        if name is None:
            with open('/etc/localtime', 'rb') as f:
                return zoneinfo.ZoneInfo.from_file(f)
        name = name[1:] if name.startswith(':') else name
        if name in ('', 'UTC', 'UTC0', 'GMT', 'GMT0', 'Etc/UTC'):
            return datetime.timezone.utc
        return zoneinfo.ZoneInfo(name)
    except (OSError, ValueError, zoneinfo.ZoneInfoNotFoundError):
        return None


def limit_reset(message, now, zone):
    """The Unix time a usage-limit message says the allowance returns, or None when it states none or
    cannot be placed: the end of the stated minute, in `zone`, the later of an ambiguous local time."""
    found = RETRY_AT.search(message)
    tz = _zone(zone)
    if found is None or tz is None:
        return None
    hour = int(found['hour']) % 12 + (12 if found['half'] == 'PM' else 0)
    minute = int(found['minute'])
    try:
        if found['month']:
            date = datetime.date(int(found['year']), MONTHS.index(found['month']) + 1, int(found['day']))
        else:
            date = datetime.datetime.fromtimestamp(now, tz).date()
        stated = [datetime.datetime(date.year, date.month, date.day, hour, minute, fold=fold, tzinfo=tz).timestamp()
                  for fold in (0, 1)]
    except ValueError:
        return None
    return max(stated) + 60


class Meter:
    """Reads one invocation's stream line by line; the same interface as control_engine_claude.Meter.
    `clock` and `zone` are the engine's clock and local time zone (its TZ), for the reset its
    usage-limit message states in local time."""

    def __init__(self, clock=time.time, zone=None, resumed=False, prior=None):
        self.pending = b''
        self.clock, self.zone = clock, zone
        self.thread = None
        self.open = False
        self.incomplete = False
        self.turns = 0
        self.tokens = 0
        self.limit = set()

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

    def session(self):
        """{provider, id, tokens}: the thread this invocation ran and its conclusive sum (None when it has
        none); None when the CLI named no thread."""
        if self.thread is None:
            return None
        return {'provider': PROVIDER, 'id': self.thread, 'tokens': self.final().get('tokens')}

    def _limited(self, seen, message):
        """An exhaustion message of the error table as its window, exhausted: the usage-limit message with
        the reset it states (or none), every other with no reset. The same statement again adds nothing."""
        if not isinstance(message, str):
            return []
        if LIMIT_MESSAGE in message:
            window, reset = LIMIT_WINDOW, limit_reset(message, self.clock(), self.zone)
        else:
            window = next((window for text, window in EXHAUSTED if text in message), None)
            if window is None:
                return []
            reset = None
        if (window, reset) in self.limit:
            return []
        self.limit.add((window, reset))
        return [dict(seen, kind='window', window_id=window, status='rejected', reset_at=reset, utilization=None)]

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
        if kind == 'thread.started' and isinstance(event.get('thread_id'), str) and event['thread_id']:
            self.thread = event['thread_id']
        elif kind == 'turn.started':
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
        elif kind == 'turn.failed':
            if self.open:
                self.open, self.incomplete = False, True
            error = event.get('error')
            found.extend(self._limited(seen, error.get('message') if isinstance(error, dict) else None))
        elif kind == 'error':
            found.extend(self._limited(seen, event.get('message')))
        return found
