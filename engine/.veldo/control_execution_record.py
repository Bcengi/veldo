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
import base64
import collections
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
import urllib.parse

SCHEMA = 'veldo.execution_record/v1'
HINT_SCHEMA = 'veldo.execution_record_hint/v1'
STREAMS = ('engine', 'stderr', 'wrapper')
DIRECTORY = 'records'
PAGE_BYTES = 1024 * 1024
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
        self.paths = frozenset()
        self._forms = {}

    def add(self, kind, value):
        if isinstance(value, str) and value and isinstance(kind, str) and kind:
            self._values.setdefault(value, kind)
            self._forms = {}

    def kinds(self):
        return sorted(set(self._values.values()))

    def __len__(self):
        return len(self._values)

    def forms(self, text=''):
        """(form, kind), longest first: each value as printed and as a JSON string carries it."""
        depth = max(4, max((len(m.group()) for m in re.finditer(r'\\+', text)), default=0).bit_length() + 1)
        if depth in self._forms:
            return self._forms[depth]
        found = {}
        for value, kind in self._values.items():
            forms = {value, value.upper(), base64.b64encode(value.encode()).decode(),
                     base64.urlsafe_b64encode(value.encode()).decode(),
                     urllib.parse.quote(value, safe=''), urllib.parse.quote_plus(value, safe='')}
            forms.add(value.encode().hex())
            # A value can begin at any byte offset inside Basic auth or an encoded assignment.
            for offset in range(3):
                raw = b' ' * offset + value.encode()
                for encode64 in (base64.b64encode, base64.urlsafe_b64encode):
                    forms.add(encode64(raw).decode()[(offset * 8 + 5) // 6:len(raw) * 8 // 6])
            # Nested JSON carries another escaped string inside each enclosing string.
            for _ in range(depth):
                forms |= {json.dumps(v, ensure_ascii=ascii_)[1:-1] for v in forms for ascii_ in (True, False)}
            for form in forms:
                if form:
                    found.setdefault(form, kind)
        self._forms[depth] = sorted(found.items(), key=lambda item: (-len(item[0]), item[0]))
        return self._forms[depth]


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
# is kept as printed. A segment that is a hex digest named by a lowercase word (`clone-<32 hex>`, a clone's
# directory; `sha256-<64 hex>`) is the scanner's digest shape with its name, and is kept as the digest
# alone would be. A slash-joined token that does not start at such a root (the shape of a base64 key,
# whose `/` falls mid-token) is scored whole, as is every other candidate. The gate's scan
# (secret_scan.scan_text) is not this step and is unchanged.
_ROOT = re.compile(r'(?<![A-Za-z0-9+/_\-.~])(?:(?P<url>[A-Za-z][A-Za-z0-9+.\-]*://)|~?/|\.{1,3}/)')
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


_NAMED_DIGEST = re.compile(r'\A[a-z][a-z0-9]*(?:[-_][a-z][a-z0-9]*)*[-_]([0-9A-Fa-f]+)\Z')


def _high(token):
    return not SS._is_digest(token) and SS.shannon(token) >= SS.ENTROPY_THRESHOLD


def _high_segment(token):
    """The scanner's rule on a path or URL segment's candidate, a named digest excepted like a digest."""
    named = _NAMED_DIGEST.match(token)
    return _high(token) and not (named and SS._is_digest(named.group(1)))


class ClonePaths:
    """Live membership, anchored by directory descriptors without traversing symlinks."""

    def __init__(self, root, cwd):
        self.root, self.cwd = str(root), os.path.relpath(cwd, root)

    def __contains__(self, name):
        if name.startswith(('a/', 'b/')):
            name = name[2:]
        if name.startswith('/'):
            return False
        return self._exists(name) or self._exists(os.path.join(self.cwd, name))

    def _exists(self, name):
        parts = os.path.normpath(name).split('/')
        if not parts or parts[0] == '..':
            return False
        fd = None
        try:
            fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            for index, part in enumerate(parts):
                try:
                    info = os.lstat(part, dir_fd=fd)
                except FileNotFoundError:
                    return index == len(parts) - 1 and not _high(part)
                if index == len(parts) - 1:
                    return True
                if not stat.S_ISDIR(info.st_mode):
                    return False
                child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = child
        except OSError:
            return False
        finally:
            if fd is not None:
                os.close(fd)
        return False


def clone_paths(cwd):
    """Locate the clone once; membership observes files created during the run without a tree walk."""
    if not cwd:
        return ()
    spec = importlib.util.spec_from_file_location('record_git', Path(__file__).with_name('git_process.py'))
    gp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gp)
    root = gp.run(['git', '-C', str(cwd), 'rev-parse', '--show-toplevel'], capture_output=True, text=True)
    root = Path(root.stdout.strip()) if root.returncode == 0 else Path(cwd).absolute()
    return ClonePaths(root, Path(cwd).absolute())


_RELATIVE = re.compile(r"[A-Za-z0-9_+./=\-]+")
_INITIALIZE = re.compile(r"\bveldo-initialize-[0-9a-fA-F]+\b")


def _entropy_spans(text, paths=()):
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
    # Exempt complete known paths, never arbitrary slash-bearing candidates.
    kept = [(m.start(), m.end()) for m in _RELATIVE.finditer(text) if m.group() in paths]
    kept += [(m.start(), m.end()) for m in _INITIALIZE.finditer(text)]
    spans, gap = [], 0
    for start, end, segments in ranges + [(len(text), len(text), [])]:
        spans += [(m.start(), m.end()) for m in SS._CANDIDATE.finditer(text, gap, start) if _high(m.group())]
        for low, high in segments:
            spans += [(m.start(), m.end()) for m in SS._CANDIDATE.finditer(text, low, high)
                      if _high_segment(m.group())]
        gap = end
    return [(a, b) for a, b in spans if not any(c <= a and b <= d for c, d in kept)]


def redact(text, resolved):
    """(text, kinds): `text` with every resolved value replaced by its kind's marker, THEN a handshake or
    init line's account identifiers by field, the scanner's known patterns and the high-entropy spans
    (by component in a path or URL) replaced; `kinds` the sorted kinds replaced."""
    kinds = set()
    for form, kind in (resolved.forms(text) if resolved is not None else ()):
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
    spans = _entropy_spans(text, getattr(resolved, 'paths', ()))
    for start, end in sorted(spans, reverse=True):
        text = text[:start] + marker(ENTROPY_KIND) + text[end:]
    if spans:
        kinds.add(ENTROPY_KIND)
    return text, sorted(kinds)


def _block_spans(text, resolved):
    """Original offsets, with the same precedence as redact. Mask replaced spans before the next pass."""
    spans = []
    def take(matches, kind):
        nonlocal text
        for start, end in reversed(matches):
            spans.append((start, end, kind))
            text = text[:start] + ' ' * (end - start) + text[end:]
    for form, kind in resolved.forms(text) if resolved is not None else ():
        take([(m.start(), m.end()) for m in re.finditer(re.escape(form), text)], kind)
    for rx, kind in PATTERN_KINDS:
        take([(m.start(), m.end()) for m in rx.finditer(text)], kind)
    take(_entropy_spans(text, getattr(resolved, 'paths', ())), ENTROPY_KIND)
    return sorted(spans)


def _safe_prefix(text, resolved):
    """Keep the longest exact form and fixed pattern width. Unbounded patterns retain their open start,
    and entropy retains the entire last lexical candidate, however long it grows."""
    tail = max([256] + [len(form) for form, _ in resolved.forms(text)] if resolved is not None else [256])
    safe = max(0, len(text) - tail)
    # All scanner patterns start inside this alphabet, except private-key headers and quoted assignments.
    for match in re.finditer(r'[A-Za-z0-9+/=_\-.]+', text):
        if match.start() < safe < match.end():
            safe = match.start()
    # These two patterns may contain arbitrarily much whitespace; retain their incomplete starts.
    for match in re.finditer(r'(?i)(?:-{5}BEGIN [A-Z ]*|\b(?:password|passwd|secret|api[_-]?key|token)\s*(?:[:=]\s*(?:[\'"][^\"\'\s]*)?)?)$', text):
        safe = min(safe, match.start())
    return safe


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
        self.blocks, self.messages, self.waiting = {}, {}, collections.deque()
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

    def _persist(self, stream, raw, newline=True, extra=(), at=None, received_bytes=None):
        text, kinds = redact(raw.decode('utf-8', 'surrogateescape'), self.resolved)
        kinds = sorted(set(kinds) | set(extra))
        self.sequence += 1
        self._write({'seq': self.sequence, 'at': self.clock() if at is None else at, 'stream': stream, 'redacted': kinds, 'payload': text})
        self.counts[stream]['lines'] += 1
        self.counts[stream]['bytes'] += received_bytes if received_bytes is not None else len(raw) + (1 if newline else 0)
        for kind in kinds:
            self.redactions[kind] = self.redactions.get(kind, 0) + 1

    def _keep(self, stream, raw, newline=True):
        entry = [stream, raw, newline, (), self.clock(), None, len(raw) + (1 if newline else 0)]
        try:
            event = json.loads(raw) if stream == 'engine' else {}
        except ValueError:
            event = {}
        if not isinstance(event, dict):
            event = {}
        scope = (event.get('session_id'), event.get('parent_tool_use_id'))
        inner = event.get('event') or {}
        if not isinstance(inner, dict):
            inner = {}
        kind = inner.get('type')
        if kind == 'message_start':
            self._flush_blocks(scope)
            self.messages[scope] = (inner.get('message') or {}).get('id')
        message = event.get('message_id') or self.messages.get(scope)
        delta = inner.get('delta') or {}
        if kind == 'content_block_start':
            self._flush_blocks(scope, inner.get('index', 0))
            delta = inner.get('content_block') or {}
        fields = [field for field, value in delta.items() if field != 'type' and isinstance(value, str)]
        if kind in ('content_block_start', 'content_block_delta') and fields:
            entry[5] = set(fields)
            known = delta.get('type') in ('text', 'text_delta', 'input_json_delta', 'thinking', 'thinking_delta')
            for field in fields:
                ident = (scope, message, inner.get('index', 0), field)
                block = self.blocks.setdefault(ident, {'text': '', 'entries': [], 'done': False, 'hold': False})
                block['hold'] |= not known
                start = len(block['text'])
                block['text'] += delta[field]
                block['entries'].append((entry, start, len(block['text']), field))
                self._release_block(block)
        elif kind == 'content_block_stop':
            self._flush_blocks(scope, inner.get('index', 0))
        elif kind == 'message_stop' or event.get('type') in ('assistant', 'result'):
            self._flush_blocks(scope)
        self.waiting.append(entry)
        self._drain()

    def _flush_blocks(self, scope=None, index=None):
        for ident, block in list(self.blocks.items()):
            if (scope is None or ident[0] == scope) and (index is None or ident[2] == index):
                block['done'] = True
                self._release_block(block)
                del self.blocks[ident]

    def _release_block(self, block):
        text = block['text']
        spans = _block_spans(text, self.resolved)
        safe = len(text) if block['done'] else (0 if block['hold'] else _safe_prefix(text, self.resolved))
        for start, end, _kind in spans:
            if start < safe < end:
                safe = start
        pending = []
        for entry, low, high, field in block['entries']:
            if high > safe or (block['hold'] and not block['done']):
                pending.append((entry, low, high, field))
                continue
            value, at, kinds = '', low, set()
            for start, end, kind in spans:
                if end <= low or start >= high:
                    continue
                value += text[at:max(at, start)] + marker(kind)
                at = min(high, end)
                kinds.add(kind)
            value += text[at:high]
            if kinds:
                raw = entry[1].decode('utf-8', 'surrogateescape')
                container = re.search(r'"(?:delta|content_block)"\s*:\s*\{', raw)
                found = re.compile(re.escape(json.dumps(field)) + r'\s*:\s*').search(raw, container.end())
                _, end = _DECODER.raw_decode(raw, found.end())
                raw = raw[:found.end()] + json.dumps(value, ensure_ascii=True) + raw[end:]
                entry[1], entry[3] = raw.encode('utf-8', 'surrogateescape'), set(entry[3]) | kinds
            entry[5].discard(field)
            if not entry[5]:
                entry[5] = None
        block['entries'] = pending

    def _drain(self):
        while self.waiting and self.waiting[0][5] is None:
            stream, raw, newline, kinds, at, _, received_bytes = self.waiting.popleft()
            self._persist(stream, raw, newline, kinds, at, received_bytes)

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
            self._flush_blocks()
            self._drain()
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
    page, size = [], 0
    for line in lines[after:after + limit]:
        width = len(encode(line))
        if page and size + width > PAGE_BYTES:
            break
        page.append(line)
        size += width
    return {'header': header, 'lines': page, 'total': len(lines)}
