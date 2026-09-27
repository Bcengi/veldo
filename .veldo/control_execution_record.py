#!/usr/bin/env python3
"""Every worker run's execution record: kept by the launch receiver as it happens, redacted before it is
kept, read back by the authority for the API's live terminal view (VELDO-0141).

WHAT IS KEPT. One append-only file per dispatch on the Linux host (`path`), under the factory state root's
`records` directory unless the receiver's configuration names `records` (`directory`), mode 0600 in a 0700
directory, written only by the launch receiver (control_launch), which alone holds the worker's pipes. Its
first line is the HEADER binding the record to the dispatch and run it belongs to: schema, dispatch id,
contract digest, unit, station, project, account and host. Every other line is one line the run printed,
in the order the receiver read it, as one JSON object:

  seq       gapless per dispatch, from 1
  at        the receiver's clock when it read the line
  stream    `engine` (a line of the engine's standard output: its structured events, Claude Code's stream
            JSON or Codex's exec JSON), `stderr` (a raw line of the worker's error stream: the engine's,
            and the trusted wrapper's and clone entrance's before the engine runs) or `wrapper` (the
            trusted wrapper's identity line, written before it became the engine)
  redacted  the kinds replaced in this line, sorted; empty when nothing was
  payload   the line exactly as it was printed, without its newline, except for redacted spans (bytes
            that are not UTF-8 are kept as surrogate escapes, so the line's bytes are recovered exactly)

Nothing is summarized, merged, dropped or reinterpreted: the engine's own event text is the payload. A
last line with no newline is kept when the stream ends.

REDACTION, BEFORE A LINE IS KEPT (`redact`). First every value in the run's set of resolved credential
values (`Resolved`: what the receiver resolved for this run, each with its kind; control_launch.RESOLVERS
add to it, the subscription token among them, and VELDO-0158 AC3 adds the keystore's) is replaced by the
marker naming its kind, `[REDACTED:<kind>]`, in each form a line can carry it (as printed, and as a JSON
string escapes it, ASCII-escaped or not), longest value first. Next, in the engine's handshake answer and
its init line only, the account identifiers (email, organization, account and organization uuid) are
replaced by field (`account:<field>`). Only then does the secret scanner (secret_scan's detectors,
reused, never reimplemented) redact its known patterns (`pattern:<shape>`) and high-entropy spans
(`entropy`, a hex digest's shape excepted), a rooted path or a URL scored by component so that only a
segment which is itself high-entropy goes and the rest of the path is kept (the gate's own scan is not
changed). The order is the point: a value the scanner alone would miss (no known pattern, low entropy) is
replaced whole even when it is joined to a span the scanner redacts only in part.

THE COMMITTED RECORD. `Recorder.close()` returns {lines, bytes, digest}: the count of record lines (the
header excluded), the file's size and the SHA-256 of its bytes. The receiver commits them in the dispatch's
exit record (control_dispatch.exit, `execution_record`), so a record served after the run is checked against
what the authority committed.

LIVE, WITHOUT POLLING. After each batch the recorder sends each configured API hint socket (the receiver's
`record_hints`: the API process's own hint socket, control_client_api.Hints) a hint naming the dispatch and
the last sequence (`HINT_SCHEMA`), and one more, marked ended, once the dispatch's end is recorded. A hint
only wakes the API, which reads the lines after its cursor through the authority (`read`); a lost hint is
caught up by the next. A socket is written only when it is this account's own, in a directory nobody else
can enter, and its peer is this account (SO_PEERCRED).

READING (`read`). The authority (control_api_authority.record) reads the lines after a cursor from the file
the dispatch id names, refusing by name a record whose header binds another dispatch and, once the dispatch
ended with a committed record, one whose line count, size or digest differ from the committed ones.

OBSERVABILITY. `Recorder.summary()` names the record's path, dispatch, line and byte counts per stream and
redactions by kind, never a value or an unredacted line.

WHAT IT IS NOT. No retention, archival, replay or editing of a record (Release 2), and no record of a run
outside the factory. Standard library only.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import stat
import struct
import time

SCHEMA = 'veldo.execution_record/v1'
HINT_SCHEMA = 'veldo.execution_record_hint/v1'
STREAMS = ('engine', 'stderr', 'wrapper')
DIRECTORY = 'records'
HINT_SECONDS = 1.0


def _scanner():
    spec = importlib.util.spec_from_file_location('execution_record_secret_scan',
                                                  Path(__file__).with_name('secret_scan.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SS = _scanner()


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code, self.detail = code, detail


def directory(config):
    """Where a receiver keeps its records: the configuration's `records`, else the factory state root's
    `records`, else beside the store."""
    if config.get('records'):
        return str(config['records'])
    if config.get('state_root'):
        return os.path.join(str(config['state_root']), DIRECTORY)
    return os.path.join(os.path.dirname(str(config['store'])), DIRECTORY)


def path(records, dispatch_id):
    """The one file of `dispatch_id` under `records`."""
    return os.path.join(str(records), hashlib.sha256(str(dispatch_id).encode()).hexdigest() + '.jsonl')


def marker(kind):
    return '[REDACTED:%s]' % kind


def _shape(why):
    """A scanner pattern's kind: its description as a name (`a GitHub token` is `pattern:github_token`)."""
    words = ''.join(c if c.isalnum() else ' ' for c in why.lower()).split()
    if words and words[0] in ('a', 'an'):
        words = words[1:]
    return 'pattern:' + '_'.join(words)


PATTERN_KINDS = tuple((rx, _shape(why)) for rx, why in SS.PATTERNS)
ENTROPY_KIND = 'entropy'


class Resolved:
    """The run's set of resolved credential values, each with its kind (`add`). The receiver replaces
    exactly this set in every line before the scanner runs."""

    def __init__(self):
        self._values = {}

    def add(self, kind, value):
        if isinstance(value, str) and value and isinstance(kind, str) and kind:
            self._values.setdefault(value, kind)

    def kinds(self):
        return sorted(set(self._values.values()))

    def __len__(self):
        return len(self._values)

    def forms(self):
        """(form, kind), longest first: each value as printed and as a JSON string carries it."""
        found = {}
        for value, kind in self._values.items():
            for form in (value, json.dumps(value)[1:-1], json.dumps(value, ensure_ascii=False)[1:-1]):
                if form:
                    found.setdefault(form, kind)
        return sorted(found.items(), key=lambda item: (-len(item[0]), item[0]))


# ACCOUNT IDENTIFIERS, BY FIELD. The engine's handshake answer (Claude Code's initialize control response,
# whose `account` is its Kfe(): email, organization, subscriptionType, tokenSource, apiKeySource and
# apiProvider) and its init line name the account the run is logged in as. In those two lines, and only
# there, the value of every field below, at any depth, is replaced where the line carries it: a string's
# content by the marker of `account:<field>`, any other value by that marker as a JSON string, so the line
# stays JSON. The fields that say how the run is logged in (the backend, the token source, the
# subscription label) are kept.
ACCOUNT_FIELDS = ('email', 'organization', 'organizationUuid', 'organization_uuid', 'accountUuid', 'account_uuid')
ACCOUNT_KIND = 'account:%s'
_DECODER = json.JSONDecoder()


def _account_line(event):
    """Whether a parsed line is the handshake answer or the init line."""
    return isinstance(event, dict) and (event.get('type') == 'control_response'
                                        or (event.get('type') == 'system' and event.get('subtype') == 'init'))


def _account_spans(text):
    """(start, end, replacement, kind) of each account identifier a handshake or init line carries; none for
    any other line. A field inside another's value is covered by the outer one."""
    try:
        event = json.loads(text)
    except ValueError:
        return []
    if not _account_line(event):
        return []
    found = []
    for field in ACCOUNT_FIELDS:
        for key in re.finditer(r'"%s"\s*:\s*' % re.escape(field), text):
            try:
                value, end = _DECODER.raw_decode(text, key.end())
            except ValueError:
                continue
            if value is None or value == '' or isinstance(value, bool):
                continue
            kind = ACCOUNT_KIND % field
            if isinstance(value, str):
                found.append((key.end() + 1, end - 1, marker(kind), kind))
            else:
                found.append((key.end(), end, json.dumps(marker(kind)), kind))
    spans, reach = [], -1
    for span in sorted(found, key=lambda item: (item[0], -item[1])):
        if span[0] >= reach:
            spans.append(span)
            reach = span[1]
    return spans


# THE ENTROPY STEP, BY COMPONENT. The scanner's candidate class holds `/`, so a whole absolute path or URL
# would be one candidate and score as random (4.1 to 4.4 bits per character over 32). A path rooted at a
# boundary (`/`, `~/`, `./`, `../`) is scored segment by segment (separated by `/` or a backslash, and JSON's
# escaped forms of both), and a URL (`scheme://`) component by component (its authority, each path
# segment, and each key and each value of its query and fragment); each segment is judged by the
# scanner's own rule, so only a segment that is itself high-entropy is replaced and the rest of the path
# is kept as printed. A slash-joined token that does not start at such a root (the shape of a base64 key,
# whose `/` falls mid-token) is scored whole, as is every other candidate. The gate's scan
# (secret_scan.scan_text) is not this step and is unchanged.
_ROOT = re.compile(r'(?<![A-Za-z0-9+/_\-.~])(?:(?P<url>[A-Za-z][A-Za-z0-9+.\-]*://)|~?/|\.\.?/)')
_PATH_STOPS = frozenset('"\'`<>|;,:()[]{}*?$&')
_URL_STOPS = frozenset('"\'`<>|()[]{}')
_ESCAPED = 'nrtbfu"'


def _located(text, found):
    """(end, segments): walk the path or URL whose root `found` matched; each segment a (start, end)."""
    url = found.group('url') is not None
    stops = _URL_STOPS if url else _PATH_STOPS
    segments = []
    begin = found.start() if url else found.end()
    if url:
        segments.append((found.start(), found.end() - 3))
        begin = found.end()
    at, part, keyed = begin, 'path', False
    while at < len(text):
        char = text[at]
        if char.isspace() or char in stops:
            break
        width = 0
        if char == '\\':
            follow = text[at + 1:at + 2]
            if follow in ('\\', '/'):
                width = 2
            elif follow and follow in _ESCAPED:
                break
            else:
                width = 1
        elif char == '/' and part == 'path':
            width = 1
        elif url and char in '?#':
            part, keyed, width = 'query', False, 1
        elif url and part == 'query' and char in '&;':
            keyed, width = False, 1
        elif url and part == 'query' and char == '=' and not keyed:
            keyed, width = True, 1
        if width:
            segments.append((begin, at))
            at += width
            begin = at
        else:
            at += 1
    segments.append((begin, at))
    return at, segments


def _high(token):
    return not SS._is_digest(token) and SS.shannon(token) >= SS.ENTROPY_THRESHOLD


def _entropy_spans(text):
    """The (start, end) of every span the entropy step replaces: candidates of each segment of a rooted path
    or URL, and every other candidate whole."""
    ranges, at = [], 0
    while True:
        found = _ROOT.search(text, at)
        if found is None:
            break
        end, segments = _located(text, found)
        ranges.append((found.start(), end, segments))
        at = max(end, found.end())
    spans, gap = [], 0
    for start, end, segments in ranges + [(len(text), len(text), [])]:
        pieces = [(gap, start)] + segments
        for low, high in pieces:
            spans += [(m.start(), m.end()) for m in SS._CANDIDATE.finditer(text, low, high) if _high(m.group())]
        gap = end
    return spans


def redact(text, resolved):
    """(text, kinds): `text` with every resolved value replaced by its kind's marker, THEN a handshake or
    init line's account identifiers by field, the scanner's known patterns and the high-entropy spans
    (by component in a path or URL) replaced; `kinds` the sorted kinds replaced."""
    kinds = set()
    for form, kind in (resolved.forms() if resolved is not None else ()):
        if form in text:
            text = text.replace(form, marker(kind))
            kinds.add(kind)
    for start, end, replacement, kind in sorted(_account_spans(text), reverse=True):
        text = text[:start] + replacement + text[end:]
        kinds.add(kind)
    for rx, kind in PATTERN_KINDS:
        text, count = rx.subn(marker(kind), text)
        if count:
            kinds.add(kind)
    spans = _entropy_spans(text)
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + marker(ENTROPY_KIND) + text[end:]
    if spans:
        kinds.add(ENTROPY_KIND)
    return text, sorted(kinds)


def encode(entry):
    return (json.dumps(entry, sort_keys=True, ensure_ascii=True) + '\n').encode('ascii')


class Recorder:
    """One dispatch's record, written as the run prints. `header` binds it (dispatch_id, contract_digest,
    unit, station, project, account, host); `resolved` is the run's Resolved set, read at each line; `hints`
    the API hint sockets told after each batch."""

    def __init__(self, records, header, resolved, hints=(), clock=time.time):
        self.dispatch_id = header['dispatch_id']
        self.resolved, self.hints, self.clock = resolved, list(hints or ()), clock
        os.makedirs(str(records), mode=0o700, exist_ok=True)
        os.chmod(str(records), 0o700)
        self.path = path(records, self.dispatch_id)
        self.fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_APPEND | os.O_CLOEXEC, 0o600)
        self.hasher, self.size, self.sequence, self.hinted = hashlib.sha256(), 0, 0, 0
        self.pending = {name: b'' for name in STREAMS}
        self.counts = {name: {'lines': 0, 'bytes': 0} for name in STREAMS}
        self.redactions = {}
        self.sent = {'hints': 0, 'dropped': 0}
        self.closed = None
        self._write(dict({k: header.get(k) for k in ('dispatch_id', 'contract_digest', 'unit', 'station', 'project',
                                                     'account', 'host')}, schema=SCHEMA, opened_at=self.clock()))

    def _write(self, entry):
        data = encode(entry)
        os.write(self.fd, data)
        self.hasher.update(data)
        self.size += len(data)

    def _keep(self, stream, raw, newline=True):
        text, kinds = redact(raw.decode('utf-8', 'surrogateescape'), self.resolved)
        self.sequence += 1
        self._write({'seq': self.sequence, 'at': self.clock(), 'stream': stream, 'redacted': kinds, 'payload': text})
        self.counts[stream]['lines'] += 1
        self.counts[stream]['bytes'] += len(raw) + (1 if newline else 0)
        for kind in kinds:
            self.redactions[kind] = self.redactions.get(kind, 0) + 1

    def feed(self, stream, chunk):
        """Keep every complete line of `chunk` (what the receiver just read from `stream`), in order."""
        if self.closed is not None or not chunk:
            return
        data = self.pending[stream] + chunk
        *lines, self.pending[stream] = data.split(b'\n')
        for raw in lines:
            self._keep(stream, raw)

    def line(self, stream, raw):
        """Keep one whole line (the wrapper's identity line)."""
        if self.closed is None:
            self._keep(stream, raw.rstrip(b'\n'))

    def batch(self):
        """After each batch: hint the API with the last sequence, once per new line kept."""
        if self.sequence > self.hinted:
            self.hinted = self.sequence
            self.hint(False)

    def close(self):
        """Keep each stream's last line that has no newline, close the file and return {lines, bytes, digest}."""
        if self.closed is None:
            for stream in STREAMS:
                if self.pending[stream]:
                    rest, self.pending[stream] = self.pending[stream], b''
                    self._keep(stream, rest, newline=False)
            os.close(self.fd)
            self.closed = {'lines': self.sequence, 'bytes': self.size, 'digest': 'sha256:' + self.hasher.hexdigest()}
        return dict(self.closed)

    def hint(self, ended):
        """Tell every configured API hint socket this dispatch's last sequence (identity only)."""
        body = json.dumps({'schema': HINT_SCHEMA, 'dispatch_id': self.dispatch_id, 'seq': self.sequence,
                           'ended': bool(ended)}, sort_keys=True).encode()
        for target in self.hints:
            if push(target, body):
                self.sent['hints'] += 1
            else:
                self.sent['dropped'] += 1

    def summary(self):
        """What a log names: the record, its counts per stream and its redactions by kind, never a value."""
        return {'path': self.path, 'dispatch_id': self.dispatch_id, 'lines': self.sequence, 'bytes': self.size,
                'streams': {k: dict(v) for k, v in self.counts.items()}, 'redactions': dict(self.redactions),
                'resolved_kinds': self.resolved.kinds() if self.resolved is not None else [],
                'hints': dict(self.sent), 'committed': dict(self.closed) if self.closed else None}


def _peer_uid(channel):
    try:
        raw = channel.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize('3i'))
    except (OSError, AttributeError):
        return None
    return struct.unpack('3i', raw)[1]


def push(target, body):
    """Whether one hint reached `target`: this account's own socket in a directory of this account nobody
    else can enter, whose peer the kernel says is this account."""
    try:
        here, parent = os.lstat(str(target)), os.lstat(os.path.dirname(str(target)))
    except (OSError, TypeError):
        return False
    if (not stat.S_ISSOCK(here.st_mode) or here.st_uid != os.getuid() or not stat.S_ISDIR(parent.st_mode)
            or parent.st_uid != os.getuid() or stat.S_IMODE(parent.st_mode) & 0o077):
        return False
    channel = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    channel.settimeout(HINT_SECONDS)
    try:
        channel.connect(str(target))
        if _peer_uid(channel) != os.getuid():
            return False
        channel.sendall(body)
        return True
    except OSError:
        return False
    finally:
        channel.close()


def read(records, dispatch_id, after, limit, committed=None):
    """{header, lines, total}: the kept lines of `dispatch_id` with a sequence after `after`, at most `limit`,
    and how many the file holds. Refused by name: no record (missing_evidence:unknown_run), a header binding
    another dispatch (unknown_outcome:record_binding), a cursor past the end (invalid_input:cursor_past_end),
    and, when `committed` ({lines, bytes, digest} of the dispatch's exit) is given, a file whose count, size
    or digest differ (unknown_outcome:record_digest). A line still being written is not yet a line."""
    try:
        with open(path(records, dispatch_id), 'rb') as handle:
            data = handle.read()
    except OSError:
        raise Refused('missing_evidence:unknown_run', 'no execution record of this run') from None
    complete = data[:data.rfind(b'\n') + 1].split(b'\n')[:-1]
    try:
        header = json.loads(complete[0]) if complete else None
    except ValueError:
        header = None
    if not isinstance(header, dict) or header.get('schema') != SCHEMA or header.get('dispatch_id') != dispatch_id:
        raise Refused('unknown_outcome:record_binding', 'the record is bound to another dispatch')
    if committed is not None:
        if ('sha256:' + hashlib.sha256(data).hexdigest() != committed.get('digest')
                or len(data) != committed.get('bytes')):
            raise Refused('unknown_outcome:record_digest', 'the record is not the one its exit committed')
    try:
        lines = [json.loads(raw) for raw in complete[1:]]
    except ValueError:
        raise Refused('unknown_outcome:record_binding', 'the record is not an execution record') from None
    if committed is not None and len(lines) != committed.get('lines'):
        raise Refused('unknown_outcome:record_digest', 'the record is not the one its exit committed')
    if after > len(lines):
        raise Refused('invalid_input:cursor_past_end', 'the record holds %d lines' % len(lines))
    return {'header': header, 'lines': lines[after:after + limit], 'total': len(lines)}
