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
own completed turns never counts less than the CLI recorded under either reading. So `resumes` and
`prior` are accepted for the common interface and not used; `session()` still names the thread and its
conclusive sum for the ledger, charged whole (`charged` is always `whole`).

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

THE ADAPTER (VELDO-0061). REGISTRATION is the Codex adapter as the launch receiver runs it: its
lifecycle operations (accept, launch, observe, stop, exit, artifacts) and the code that implements
each, the flags of the qualified configuration and the environment the engine is pinned with.

PINNED EXECUTABLE. The adapter launches the vendor binary inside its npm package (the `executable` its
configuration names), never the package manager's `codex` link, a Node shim the next install replaces.
`qualification(executable)` writes the record of one installed binary (runtime/codex-qualification.json
for Codex 0.154.0 on Linux x64): its package, version, package-relative path, digest and flags, the
terminal protocol and usage it is read with. `bind(adapter, state_root)` checks the configured executable
against that record before anything is accepted or spawned: an absolute path, no link on the way to it,
inside a package of the recorded name and version at the recorded relative path, with the recorded
digest; the receiver then checks, for every engine alike (control_launch.ENGINE_PROTOCOL), that the argv
`command` returns (the adapter's own, exactly) runs it with the recorded flags. Anything else is refused
by name. ENVIRONMENT (`environment`) sets
DISABLE_AUTOUPDATER in the engine's environment, as the design asks of both engines. This binary does
not name that variable: an upgrade of it is a new package installed over this one (the command its
update notice prints), and the version and digest checks refuse the binary that install leaves.

TERMINAL OUTPUT (`Terminal`). What the engine printed becomes an artifact document, never a completion
by exit code: every stdout line is kept as printed and checked against the exec events of the table
(EVENTS, ITEM_KINDS; proof/VELDO-0061/codex-exec.json); the verdict is `complete` only when the stream is
well formed, its last turn closed with `turn.completed` and the engine exited 0. A stream whose last turn
has no terminal record is `missing_result`, one with a line exec does not print is `malformed_output`, a
failed turn `turn_failed`, a nonzero exit `nonzero_exit`, a signal `signal` and a deadline stop
`deadline`. Items are returned whole, as the CLI printed them; the reader relies on an item's `id` and
`type` only, the two fields the binary ties to exec's items. `verify(document)` recomputes a document from
its own lines, so a reader need not trust the receiver's verdict.
Standard library only.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
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

    def __init__(self, clock=time.time, zone=None, resumes=None, prior=None):
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
        """{provider, id, tokens, charged}: the thread this invocation ran, its conclusive sum (None when it
        has none) and `charged` `whole` (a resumed thread is never subtracted); None when the CLI named no
        thread."""
        if self.thread is None:
            return None
        return {'provider': PROVIDER, 'id': self.thread, 'tokens': self.final().get('tokens'), 'charged': 'whole'}

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


# VELDO-0061: the adapter registration, the pinned executable and the terminal output.

# The flags of the qualified configuration: exec mode with its JSON event stream on stdout; the prompt
# is what the receiver writes on stdin.
FLAGS = ('exec', '--json')
ENVIRONMENT = {'DISABLE_AUTOUPDATER': '1'}
QUALIFICATION = Path(__file__).resolve().with_name('runtime') / 'codex-qualification.json'
QUALIFICATION_SCHEMA = 'veldo.engine_qualification/v1'
ARTIFACT_SCHEMA = 'veldo.engine_artifact/v1'
PACKAGE = '@openai/codex'
# The adapter registration (control_launch.ENGINE_PROTOCOL).
REGISTRATION = {
    'engine': PROVIDER,
    'lifecycle': {
        'accept': 'control_launch.Receiver.launch: the executable bound (bind) and the acceptance committed before any spawn',
        'launch': 'control_launch.Receiver._spawn: the pinned binary with FLAGS, through the trusted wrapper, in its clone',
        'observe': 'control_launch.Metering.feed: each stdout line read by Meter (usage, windows) and by Terminal',
        'stop': 'control_launch.Launch.stop: the cooperative stop and its bounded escalation over the containment group',
        'exit': 'control_launch.Receiver._reap: the exit, recorded once the group is empty',
        'artifacts': 'control_launch.Metering.settle: the artifact document of the terminal output (Terminal.document), '
                     'its verdict the outcome and the exit record\'s artifact',
    },
    'flags': FLAGS,
    'environment': ENVIRONMENT,
}
# The events `codex exec --json` prints (VELDO-0062's table) with each one's fields and their types, and
# the item kinds its ThreadItem is tagged with (VELDO-0061's). A field outside these is a malformed line.
EVENTS = {
    'thread.started': {'thread_id': str},
    'turn.started': {},
    'turn.completed': {'usage': dict},
    'turn.failed': {'error': dict},
    'item.started': {'item': dict},
    'item.updated': {'item': dict},
    'item.completed': {'item': dict},
    'error': {'message': str},
}
USAGE_FIELDS = ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens', 'output_tokens',
                'reasoning_output_tokens')
ITEM_KINDS = ('agent_message', 'reasoning', 'command_execution', 'file_change', 'mcp_tool_call', 'web_search',
              'todo_list', 'collab_tool_call', 'error')


class Refused(Exception):
    """A named refusal of a binding (control_launch.ENGINE_PROTOCOL): nothing is accepted or spawned."""

    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _file_digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return 'sha256:' + h.hexdigest()


def _package(executable):
    """(root, manifest) of the npm package the executable lies in: its nearest directory holding a
    package.json. None, None when there is none or it is unreadable."""
    for parent in Path(executable).parents:
        manifest = parent / 'package.json'
        if manifest.is_file():
            try:
                data = json.loads(manifest.read_text())
            except (OSError, ValueError):
                return None, None
            return parent, data if isinstance(data, dict) else None
    return None, None


def qualification(executable, flags=FLAGS):
    """The qualification record of one installed vendor binary. Reads its package manifest and its bytes;
    nothing is executed."""
    root, manifest = _package(executable)
    if root is None or manifest is None or manifest.get('name') != PACKAGE:
        raise Refused('invalid_input:engine_package')
    version = str(manifest.get('version') or '')
    return {'schema': QUALIFICATION_SCHEMA, 'engine': PROVIDER, 'package': PACKAGE, 'package_version': version,
            'version': version.split('-', 1)[0], 'executable': str(Path(executable).relative_to(root)),
            'sha256': _file_digest(executable), 'flags': list(flags), 'environment': dict(ENVIRONMENT),
            'terminal_protocol': {'stream': 'stdout, one JSON event per line', 'events': sorted(EVENTS),
                                  'terminal': 'turn.completed', 'failed': 'turn.failed', 'item_kinds': list(ITEM_KINDS)},
            'authentication': 'the subscription login of the account profile CODEX_HOME names',
            'usage_units': ['invocations', 'wall_seconds', 'tokens', 'messages'],
            'rate_limit_windows': sorted({LIMIT_WINDOW} | {window for _, window in EXHAUSTED})}


def load_qualification(path=None):
    try:
        record = json.loads(Path(path or QUALIFICATION).read_text())
    except (OSError, ValueError):
        raise Refused('missing_evidence:engine_qualification')
    fields = ('package', 'package_version', 'version', 'executable', 'sha256', 'flags')
    if (not isinstance(record, dict) or record.get('schema') != QUALIFICATION_SCHEMA or record.get('engine') != PROVIDER
            or not all(record.get(f) for f in fields) or not isinstance(record['flags'], list)):
        raise Refused('missing_evidence:engine_qualification')
    return record


def bind(adapter, state_root=None):
    """The pinned executable the adapter launches, {engine, path, version, package_version, sha256, flags},
    checked against its qualification record (the adapter's `qualification`, else the installed one) before
    anything is accepted or spawned (control_launch.ENGINE_PROTOCOL; `state_root` is not used: the vendor
    binary stays inside its package). Raises Refused with the named refusal. Where the executable stands in
    the argv, and that the flags follow it, is the receiver's one check for every engine."""
    record = load_qualification(adapter.get('qualification'))
    executable = adapter.get('executable')
    if not isinstance(executable, str) or not os.path.isabs(executable):
        raise Refused('invalid_input:engine_executable')
    if os.path.realpath(executable) != os.path.normpath(executable):
        raise Refused('invalid_input:engine_link')
    if not os.path.isfile(executable) or not os.access(executable, os.X_OK):
        raise Refused('unavailable_service:engine_executable')
    root, manifest = _package(executable)
    if (root is None or manifest is None or manifest.get('name') != record['package']
            or str(Path(executable).relative_to(root)) != record['executable']):
        raise Refused('invalid_input:engine_package')
    if manifest.get('version') != record['package_version']:
        raise Refused('stale_subject:engine_version')
    digest = _file_digest(executable)
    if digest != record['sha256']:
        raise Refused('stale_subject:engine_digest')
    return {'engine': PROVIDER, 'path': executable, 'version': record['version'],
            'package_version': record['package_version'], 'sha256': digest, 'flags': list(record['flags'])}


def command(bound, adapter):
    """The engine's argv: the adapter's configured argv, exactly (it names the vendor binary and its flags)."""
    return list(adapter.get('argv') or [])


def environment(bound):
    """What the engine's environment always carries (DISABLE_AUTOUPDATER)."""
    return dict(ENVIRONMENT)


def _malformed(event):
    """Why a parsed line is not an event exec prints, or None."""
    if not isinstance(event, dict) or event.get('type') not in EVENTS:
        return 'unknown_event'
    fields = EVENTS[event['type']]
    if set(event) - set(fields) - {'type'} or any(not isinstance(event.get(f), kind) for f, kind in fields.items()):
        return 'fields'
    usage = event.get('usage')
    if usage is not None and (set(usage) - set(USAGE_FIELDS) or not all(_count(v) for v in usage.values())):
        return 'usage'
    error = event.get('error')
    if error is not None and not isinstance(error.get('message'), str):
        return 'error'
    item = event.get('item')
    if item is not None and (not isinstance(item.get('id'), str) or item.get('type') not in ITEM_KINDS):
        return 'item'
    return None


class Terminal:
    """The artifact document of one invocation's terminal output, fed the same chunks as Meter."""

    def __init__(self):
        self.pending = b''
        self.lines, self.malformed, self.items = [], [], []
        self.thread_id, self.terminal, self.turn_open, self.turns = None, None, False, 0

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
        try:
            event = json.loads(raw)
        except ValueError:
            event = None
        if _malformed(event):
            self.malformed.append(index)
            return
        kind = event['type']
        if kind == 'thread.started':
            self.thread_id = event['thread_id']
        elif kind == 'turn.started':
            self.turn_open, self.terminal = True, None
        elif kind == 'turn.completed' and self.turn_open:
            self.turn_open, self.terminal, self.turns = False, 'turn.completed', self.turns + 1
        elif kind == 'turn.failed':
            self.turn_open, self.terminal = False, 'turn.failed'
        elif kind == 'item.completed':
            self.items.append({'id': event['item']['id'], 'type': event['item']['type'], 'line': index})

    def verdict(self, termination):
        if termination is None:
            return 'not_executed'
        if termination.get('signal') is not None:
            return 'signal'
        if termination.get('deadline_stop'):
            return 'deadline'
        if self.malformed:
            return 'malformed_output'
        if self.terminal == 'turn.failed':
            return 'turn_failed'
        if self.terminal != 'turn.completed' or self.turn_open:
            return 'missing_result'
        if termination.get('returncode') != 0:
            return 'nonzero_exit'
        return 'complete'

    def document(self, termination, cause=None):
        """The artifact document (control_launch.ENGINE_PROTOCOL's shape: schema, engine, verdict, complete)."""
        verdict = self.verdict(termination)
        return {'schema': ARTIFACT_SCHEMA, 'engine': PROVIDER, 'verdict': verdict, 'complete': verdict == 'complete',
                'terminal': self.terminal, 'thread': self.thread_id, 'turns': self.turns, 'items': self.items,
                'malformed': self.malformed, 'termination': termination, 'lines': self.lines}


DECODED = ('schema', 'engine', 'verdict', 'complete', 'terminal', 'thread', 'turns', 'items', 'malformed')


def verify(document):
    """Whether an artifact document is what its own lines and termination decode to."""
    if not isinstance(document, dict) or not isinstance(document.get('lines'), list):
        return False
    again = Terminal()
    for line in document['lines']:
        again.feed(str(line).encode() + b'\n')
    fresh = again.document(document.get('termination'))
    return all(fresh[k] == document.get(k) for k in DECODED)


def main(argv=None):
    """`control_engine_codex.py qualify <vendor binary>`: print its qualification record."""
    import sys
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2 or args[0] != 'qualify':
        sys.stderr.write('usage: control_engine_codex.py qualify <vendor binary>\n')
        return 2
    sys.stdout.write(json.dumps(qualification(args[1]), indent=1, sort_keys=True) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
