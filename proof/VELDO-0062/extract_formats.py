#!/usr/bin/env python3
"""Extract the report formats and credential tables of the installed CLIs, VELDO-0062.

Reads the allowlist-scrubbed live capture beside the two binaries' bytes: the schema Claude Code embeds for its stream JSON (the zod
objects its SDK message types are built from) and the literals Codex's Rust binary carries for its
`exec --json` events, its usage-limit message and its credential variables. Nothing is executed, no
model runs, nothing logs in and no profile, credential or configuration file is opened.

    python3 -B proof/VELDO-0062/extract_formats.py [--claude PATH] [--codex PATH]      # write
    python3 -B proof/VELDO-0062/extract_formats.py --check [--claude PATH] [--codex PATH]

Writes proof/VELDO-0062/cli-formats.json. With --check it writes nothing and exits 1 when a fresh
extraction differs from the committed table: after a CLI update that is the signal to regenerate the
table, and the suite's fixture rows then say which fake line no longer matches.

The default binaries are the qualified ones the engines record names (.veldo/runtime/engines.json, read
through .veldo/qualify.py); --claude and --codex name others. The Claude Code anchors below are minified
source text as one build wrote it: a name the minifier chose matches any name (the same one wherever it
repeats, and a name another anchor already bound stays that name), while strings, property names, keys and
punctuation are exact. A few anchors carry a gap (`<any>`, a short stretch of code; `<items>`, list
entries; `<field>`, one object member) where a later build inserts code that does not change what the
anchor shows. The Codex anchors are literal runs of the Rust binary. A build that moved one fails here by
name rather than yielding a guessed table.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'cli-formats.json'
_qualify = importlib.util.spec_from_file_location('v62_qualify', ROOT / '.veldo' / 'qualify.py')
Q = importlib.util.module_from_spec(_qualify)
_qualify.loader.exec_module(Q)
DEFAULT_CLAUDE = Q.binary('claude_code')
DEFAULT_CODEX = Q.binary('codex')


class Moved(Exception):
    pass


# ---------------------------------------------------------------- minified anchors

JS_WORDS = frozenset(
    'var let const function return if else new typeof void async await yield of in for while do continue break case '
    'switch try catch finally this null undefined true false instanceof delete throw get set class extends super '
    'Set Map Intl Date Object Array JSON Promise String Number Boolean Math Error RegExp Symbol process'.split())
JS_NAME = re.compile(r'[A-Za-z_$][\w$]*')
REGEX_BEFORE = set('(,=:[!&|?{};')
# The gaps an anchor may carry: a short stretch of code, one simple object member, and entries of a list literal.
GAPS = {'<any>': r'[^;]{0,400}?', '<field>': r'(?:[A-Za-z_$][\w$]*:[\w$.?()]{1,60},)?',
        '<items>': r'(?:(?:"[^"\\]*"|\.\.\.[A-Za-z_$][\w$]*),)*?'}


class Anchor:
    """A minified source anchor as a pattern: each name the minifier chose (not a keyword, a global, a property
    after `.`, an object key or a method name) matches any name, the same one wherever it repeats and another than
    the anchor's other names; a name in
    `bound` matches only the name it is bound to. Strings, regular expressions and punctuation are exact, and a
    string written @"..." is that string or a name bound to it (a hoisted constant)."""

    def __init__(self, source, bound=()):
        self.source, self.bound = source, dict(bound)
        self.groups, self.hoisted, self.pieces, self.names = {}, [], [], set()
        self._parts, self._literal = [], []
        self._scan(source, 0, len(source))
        self._flush()
        self.regex = re.compile(''.join(self._parts), re.DOTALL)
        self.key = max(self.pieces, key=len) if self.pieces else ''
        self.slack = 4000 + (20000 if '<items>' in source else 0)

    def _flush(self):
        if self._literal:
            text = ''.join(self._literal)
            self._parts.append(re.escape(text))
            self.pieces.append(text)
            self._literal = []

    def _name(self, name):
        self._flush()
        self.names.add(name)
        if name in self.bound:
            self._parts.append(r'(?<![\w$])%s(?![\w$])' % re.escape(self.bound[name]))
        elif name in self.groups:
            self._parts.append('(?P=%s)' % self.groups[name])
        else:
            # Two names of one anchor are two names of the build.
            others = ''.join(r'(?!(?P=%s)(?![\w$]))' % group for group in self.groups.values())
            others += ''.join(r'(?!%s(?![\w$]))' % re.escape(value) for value in self.bound.values())
            self.groups[name] = 'n%d' % len(self.groups)
            self._parts.append(r'(?<![\w$])%s(?P<%s>[A-Za-z_$][\w$]*)(?![\w$])' % (others, self.groups[name]))

    def _string(self, s, i, end):
        j = i + 1
        while j < end and s[j] != s[i]:
            j += 2 if s[j] == '\\' else 1
        return j + 1

    def _scan(self, s, i, end):
        prev = ''
        while i < end:
            c = s[i]
            gap = next((g for g in GAPS if s.startswith(g, i)), None)
            if gap:
                self._flush()
                self._parts.append(GAPS[gap])
                i, prev = i + len(gap), ','
                continue
            if c == '@' and i + 1 < end and s[i + 1] == '"':
                j = self._string(s, i + 1, end)
                self._flush()
                group = 'h%d' % len(self.hoisted)
                self.hoisted.append((group, s[i + 1:j]))
                self._parts.append(r'(?:%s|(?<![\w$])(?P<%s>[A-Za-z_$][\w$]*)(?![\w$.(]))' % (re.escape(s[i + 1:j]), group))
                i, prev = j, '"'
                continue
            if c in '"\'':
                j = self._string(s, i, end)
                self._literal.append(s[i:j])
                i, prev = j, c
                continue
            if c == '`':
                self._literal.append(c)
                j = i + 1
                while j < end and s[j] != '`':
                    if s[j] == '\\':
                        self._literal.append(s[j:j + 2])
                        j += 2
                    elif s.startswith('${', j):
                        self._literal.append('${')
                        depth, k = 1, j + 2
                        while k < end and depth:
                            depth += {'{': 1, '}': -1}.get(s[k], 0)
                            k += 1
                        self._scan(s, j + 2, k - 1)
                        self._literal.append('}')
                        j = k
                    else:
                        self._literal.append(s[j])
                        j += 1
                self._literal.append('`')
                i, prev = j + 1, '`'
                continue
            if c == '/' and prev in REGEX_BEFORE and i + 1 < end and s[i + 1] not in '/*':
                j, klass = i + 1, False
                while j < end and (s[j] != '/' or klass):
                    if s[j] == '\\':
                        j += 1
                    elif s[j] in '[]':
                        klass = s[j] == '['
                    j += 1
                j += 1
                while j < end and s[j].isalpha():
                    j += 1
                self._literal.append(s[i:j])
                i, prev = j, '/'
                continue
            m = None if c.isdigit() else JS_NAME.match(s, i)
            if m:
                name, after, before = m.group(0), m.end(), s[:i].rstrip()
                dotted = s[:i].endswith('.') and not s[:i].endswith('...')
                key = (before == '' or before.endswith(('{', ','))) and s.startswith(':', after)
                method = (before.endswith(('{', ',', 'get', 'async')) and re.match(r'\([\w$,]*\)\{', s[after:]))
                if name in JS_WORDS or dotted or key or method:
                    self._literal.append(name)
                else:
                    self._name(name)
                i, prev = after, 'a'
                continue
            if c.isdigit():
                number = re.match(r'\d[\w.]*', s[i:]).group(0)
                self._literal.append(number)
                i, prev = i + len(number), '0'
                continue
            self._literal.append(c)
            prev = prev if c.isspace() else c
            i += 1

    def matches(self, text):
        """Every match in `text` (each hoisted constant bound to its string), found around the occurrences of the
        anchor's longest exact piece."""
        found, seen = [], set()
        candidates = self.regex.finditer(text) if len(self.key) < 4 else self._near(text)
        for m in candidates:
            if m.start() in seen:
                continue
            seen.add(m.start())
            if all(m.group(g) is None or re.search(r'(?<![\w$.])%s=%s' % (re.escape(m.group(g)), re.escape(value)), text)
                   for g, value in self.hoisted):
                found.append(m)
        return sorted(found, key=lambda m: m.start())

    def _near(self, text):
        at = text.find(self.key)
        while at >= 0:
            for m in self.regex.finditer(text, max(0, at - len(self.source) - self.slack),
                                         at + len(self.key) + len(self.source) + self.slack):
                if m.start() <= at < m.end():
                    yield m
            at = text.find(self.key, at + 1)

    def name(self, m, name):
        """The name the match gives the anchor's `name`."""
        return self.bound[name] if name in self.bound else m.group(self.groups[name])


_ANCHORS = {}


def anchor(source, bound=()):
    key = (source, tuple(sorted(dict(bound).items())))
    if key not in _ANCHORS:
        _ANCHORS[key] = Anchor(source, bound)
    return _ANCHORS[key]


_SITES = {}


def uses(source, bound):
    """The entries of `bound` naming a name the anchor `source` uses."""
    names = anchor(source).names
    return {k: v for k, v in bound.items() if k in names}


def sites(text, source, bound=()):
    """The matches of the anchor `source` in `text` (cached per text)."""
    a = anchor(source, bound)
    key = (text, source, tuple(sorted(a.bound.items())))
    if key not in _SITES:
        _SITES[key] = a.matches(text)
    return _SITES[key]


def site(text, source, what, count=1, bound=()):
    """The first match of the anchor `source`, which must match exactly `count` times; with its names: (match,
    {name in the anchor: name in the binary})."""
    found = sites(text, source, bound)
    if len(found) != count:
        raise Moved('%s: anchor found %d times' % (what, len(found)))
    a = anchor(source, bound)
    names = dict(a.bound, **{name: found[0].group(group) for name, group in a.groups.items()})
    return found[0], names


def _digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return 'sha256:' + h.hexdigest()


# ---------------------------------------------------------------- Claude Code: the embedded zod schema

# The minified zod helpers of a build, each read from a use in the SDK message schemas that only that helper fits:
# (anchor, {name in the anchor: kind}); every match of an anchor must name the same helper, and a name read once
# stays bound in the anchors after it. `lazy` is the wrapper of a lazily built schema (`NAME=lazy(()=>BODY)`); the
# uuid helper reads as a string and the null helper as any.
ZOD_HELPERS = (
    ('var mK=f(()=>d({type:R("system"),subtype:R("init"),agents:C(o()).optional(),apiKeySource:vq(),'
     'startup_timing:me(o(),ae()).optional()',
     {'f': 'lazy', 'd': 'object', 'R': 'literal', 'C': 'array', 'o': 'string', 'me': 'record', 'ae': 'any'}),
    ('num_turns:k().int()', {'k': 'number'}),
    ('agentProgressSummaries:O().optional(),forwardSubagentText:O().optional()', {'O': 'boolean'}),
    ('status:z(["allowed","allowed_warning","rejected"]),resetsAt:k().int()', {'z': 'enum'}),
    ('d({type:R("control_response"),response:Fe([', {'Fe': 'union'}),
    ('d({type:R("assistant"),message:eK(),parent_tool_use_id:o().nullable(),error:$o().optional(),uuid:_(),',
     {'_': 'string'}),
    ('f(()=>Fe([R("compacting"),R("requesting"),Mf()]))', {'Mf': 'any'}),
)


def zod_helpers(text):
    """({helper name: kind}, the lazy wrapper's name, {each helper's name in the anchors: its name in this build})."""
    bound = {}
    for source, kinds in ZOD_HELPERS:
        found = sites(text, source, bound)
        a = anchor(source, bound)
        names = {(name, a.name(m, name)) for m in found for name in kinds}
        if not found or len(names) != len(kinds):
            raise Moved('zod helper use moved: ' + source[:60])
        bound.update(names)
    zod, lazy = {}, bound['f']
    for source, kinds in ZOD_HELPERS:
        for name, kind in kinds.items():
            if kind != 'lazy':
                if zod.get(bound[name], kind) != kind:
                    raise Moved('zod helper %s read as both %s and %s' % (bound[name], zod[bound[name]], kind))
                zod[bound[name]] = kind
    return zod, lazy, bound
SPACE = re.compile(r'\s*')
TOKEN = re.compile(r'\s*(?:(?P<str>"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'|`(?:[^`\\]|\\.)*`)|(?P<num>-?\d+(?:\.\d+)?)'
                   r'|(?P<id>[A-Za-z_$][A-Za-z0-9_$]*)|(?P<arrow>=>)|(?P<p>[()\[\]{},.:!?+\-*/<>=&|]))')


class Js:
    """A tokenizer and a recursive reader of zod expressions over the binary's text."""

    def __init__(self, text, helpers=None):
        """`helpers`: zod_helpers of the build, read from `text` (the whole binary) when not given."""
        self.text = text
        self.cache = {}
        self.zod, self.lazy, self.helpers = zod_helpers(text) if helpers is None else helpers

    def _sites(self, name, suffix):
        key = (name, suffix)
        if key not in self.cache:
            self.cache[key] = list(re.finditer(r'(?<![A-Za-z0-9_$.])' + re.escape(name) + suffix, self.text))
        return self.cache[key]

    # Windows searched around `near` before the whole text: a window answers only when the nearest match in it is
    # provably the nearest in the whole text (every match that could be as near starts and ends inside it).
    WINDOWS = (1 << 22, 1 << 24)
    MARGIN = 1 << 20

    def nearest(self, name, suffix, near):
        """The match of `name` + `suffix` whose start is nearest `near` (the earliest on a tie), or None: the
        same answer as min(self._sites(name, suffix), key=distance), found without scanning the whole text
        when a window around `near` already proves it (no match of length under MARGIN that could be as near
        lies outside the window)."""
        distance = lambda m: abs(m.start() - near)
        if (name, suffix) not in self.cache:
            pattern = re.compile(r'(?<![A-Za-z0-9_$.])' + re.escape(name) + suffix)
            size = len(self.text)
            for width in self.WINDOWS:
                lo, hi = max(0, near - width), min(size, near + width)
                found = list(pattern.finditer(self.text, lo, hi))
                if not found:
                    continue
                best = min(found, key=distance)
                d = distance(best)
                if (lo == 0 or near - d >= lo) and (hi == size or near + d + self.MARGIN <= hi):
                    return best
        sites = self._sites(name, suffix)
        return min(sites, key=distance) if sites else None

    def array(self, name, near):
        """The string values of `name=[...]` nearest `near`, or None."""
        best = self.nearest(name, r'=\[("(?:[^"\\]|\\.)*"(?:,"(?:[^"\\]|\\.)*")*)\]', near)
        if best is None:
            return None
        return json.loads('[' + best.group(1) + ']')

    def tokens(self, at):
        while True:
            m = TOKEN.match(self.text, at)
            if not m:
                raise Moved('untokenizable text at %d: %r' % (at, self.text[at:at + 40]))
            kind = m.lastgroup
            yield kind, m.group(kind), m.end()
            at = m.end()

    def definition(self, name, near):
        """The body of `name=LAZY(()=>BODY)` or `name=OBJECT(...)` nearest `near` (minified names repeat)."""
        best = self.nearest(name, r'=(%s\(\(\)=>)?(?=[A-Za-z_$])' % re.escape(self.lazy), near)
        if best is None:
            raise Moved('no definition of ' + name)
        return best.end(), bool(best.group(1))


class Reader:
    def __init__(self, js, depth):
        self.js = js
        self.depth = depth
        self.seen = []

    def parse(self, at, depth=None):
        """(schema, end) of the zod expression starting at `at`."""
        depth = self.depth if depth is None else depth
        stream = self.js.tokens(at)
        kind, value, end = next(stream)
        if kind == 'str':
            return {'type': 'literal', 'value': json.loads('"%s"' % value[1:-1]) if value[0] != '`' else value[1:-1]}, end
        if kind != 'id':
            raise Moved('expected a zod call at %d, found %r' % (at, value))
        name = value
        kind, value, end = next(self.js.tokens(end))
        if value != '(':
            raise Moved('expected a call of %s at %d' % (name, at))
        args, end = self.arguments(end, depth, name)
        schema = self.build(name, args, at, depth)
        return self.modifiers(schema, end, depth)

    def arguments(self, at, depth, name):
        """The raw argument spans of a call whose '(' ends at `at`; returns (list of (start, text)), end."""
        level, start, spans = 0, at, []
        stream = self.js.tokens(at)
        for kind, value, end in stream:
            if kind == 'p' and value in '([{':
                level += 1
            elif kind == 'p' and value in ')]}':
                if level == 0:
                    if self.js.text[start:end - 1].strip():
                        spans.append(start)
                    return spans, end
                level -= 1
            elif kind == 'p' and value == ',' and level == 0:
                spans.append(start)
                start = end
        raise Moved('unterminated call of ' + name)

    def modifiers(self, schema, at, depth):
        schema = dict(schema)
        while True:
            kind, value, end = next(self.js.tokens(at))
            if value != '.':
                return schema, at
            kind, method, end = next(self.js.tokens(end))
            kind, value, end2 = next(self.js.tokens(end))
            if value != '(' and method == 'shape' and value == '.':
                # OBJECT.shape.FIELD: the schema of that object's field.
                kind, field, end = next(self.js.tokens(end2))
                inner = (schema.get('fields') or {}).get(field)
                schema = dict(inner, via=field) if inner else {'type': 'any', 'via': field}
                at = end
                continue
            if value != '(':
                return schema, at
            spans, end = self.arguments(end2, depth, method)
            if method == 'optional':
                schema['optional'] = True
            elif method == 'nullable':
                schema['nullable'] = True
            elif method == 'nullish':
                schema['optional'] = schema['nullable'] = True
            elif method == 'int':
                schema['int'] = True
            elif method == 'extend' and schema.get('type') == 'object' and spans \
                    and self.js.text[SPACE.match(self.js.text, spans[0]).end()] == '{':
                schema['fields'] = dict(schema.get('fields') or {}, **self.fields(spans[0], depth))
            at = end

    def build(self, name, spans, at, depth):
        kind = self.js.zod.get(name)
        if kind == 'object':
            return {'type': 'object', 'fields': self.fields(spans[0], depth)}
        if kind == 'enum':
            start = SPACE.match(self.js.text, spans[0]).end()
            if self.js.text[start] != '[':
                # z(NAME): the values are the array NAME names; unresolved, any string.
                kind_, ref, _ = next(self.js.tokens(start))
                m = self.js.array(ref, at)
                return {'type': 'enum', 'values': m, 'ref': ref} if m is not None else {'type': 'string', 'ref': ref}
            body = self.js.text[start:self.js.text.index(']', start) + 1]
            try:
                return {'type': 'enum', 'values': json.loads(body)}
            except ValueError:
                raise Moved('an unread enum at %d: %r' % (start, body[:120]))
        if kind == 'literal':
            kind_, value, end = next(self.js.tokens(spans[0]))
            if kind_ == 'str':
                return {'type': 'literal', 'value': value[1:-1]}
            if value == '!':
                kind_, value, _ = next(self.js.tokens(end))
                return {'type': 'literal', 'value': value == '0'}
            return {'type': 'literal', 'value': value}
        if kind in ('number', 'string', 'boolean', 'any'):
            return {'type': kind}
        if kind == 'array':
            return {'type': 'array', 'items': self.parse(spans[0], depth)[0]}
        if kind == 'record':
            return {'type': 'record', 'values': self.parse(spans[1], depth)[0]}
        if kind == 'union':
            found, pos = [], spans[0] + 1
            while True:
                kind_, value, end = next(self.js.tokens(pos))
                if value == ']':
                    break
                schema, pos = self.parse(pos, depth)
                found.append(schema)
                kind_, value, end = next(self.js.tokens(pos))
                pos = end if value == ',' else pos
            return {'type': 'union', 'anyOf': found}
        if name == self.js.lazy:
            return {'type': 'any'}
        # A reference to another definition: resolve it while depth remains.
        if depth <= 0 or name in self.seen:
            return {'type': 'any', 'ref': name}
        self.seen.append(name)
        try:
            body, lazy = self.js.definition(name, at)
            schema, _ = self.parse(body, depth - 1)
        except (Moved, StopIteration):
            schema = {'type': 'any', 'ref': name}
        finally:
            self.seen.pop()
        if schema == {'type': 'any', 'ref': name} and len(spans) == 2:
            # VELDO-0230: an unresolved NAME(transform, SCHEMA), the preprocess wrapper a later build puts around
            # a field: the schema it wraps, with its own optionality.
            try:
                inner, _ = self.parse(spans[1], depth)
            except (Moved, StopIteration):
                inner = None
            if inner is not None and inner.get('type') != 'any':
                return dict(inner, ref=name)
        return dict(schema, ref=name)

    def fields(self, at, depth):
        """The fields of an object literal starting with '{' at `at`."""
        found = {}
        kind, value, pos = next(self.js.tokens(at))
        if value != '{':
            raise Moved('expected an object literal at %d' % at)
        while True:
            kind, key, end = next(self.js.tokens(pos))
            if key == '}':
                return found
            if kind == 'str':
                key = key[1:-1]
            kind, colon, end = next(self.js.tokens(end))
            if colon != ':':
                raise Moved('expected a field at %d' % end)
            schema, pos = self.parse(end, depth)
            found[key] = schema
            kind, value, end = next(self.js.tokens(pos))
            if value == ',':
                pos = end


CLAUDE_EVENTS = {
    # event name: the text its zod object starts with (the zod helpers bound to this build's names).
    'system/init': 'd({type:R("system"),subtype:R("init"),',
    'assistant': 'd({type:R("assistant"),message:',
    'result/success': 'd({type:R("result"),subtype:R("success"),',
    'result/error': 'd({type:R("result"),subtype:z(["error_during_execution"',
    'rate_limit_event': 'd({type:R("rate_limit_event"),',
}

# Claude Code's credential and provider tables, each by its first entries (a later build may insert entries where an
# anchor has `<items>`; the first list that matches is the table), with the
# decision this work takes for it. `strip`: every name it lists never reaches the engine. `keep`: its
# names are not a model login of either CLI once the provider switches are stripped (general cloud or
# tool secrets a worker's own tools use), so only those a strip prefix already covers are removed.
CLAUDE_TABLES = [
    ('auth_credentials', '["ANTHROPIC_API_KEY",<items>"ANTHROPIC_AUTH_TOKEN",<items>"CLAUDE_CODE_OAUTH_TOKEN",<items>'
                         '"AWS_BEARER_TOKEN_BEDROCK"',
     'strip', 'the credential variables a first-party or provider login reads'),
    ('provider_selection', '["CLAUDE_CODE_USE_BEDROCK","CLAUDE_CODE_USE_VERTEX","CLAUDE_CODE_USE_FOUNDRY","CLAUDE_CODE_USE_ANTHROPIC_AWS"',
     'strip', 'the switches that move Claude Code off the subscription to another provider, with their companions'),
    ('aws_selection', '["CLAUDE_CODE_USE_BEDROCK","CLAUDE_CODE_USE_ANTHROPIC_AWS","CLAUDE_CODE_USE_MANTLE"]',
     'strip', 'the AWS-hosted provider switches'),
    ('aws_bearer', '["AWS_BEARER_TOKEN_BEDROCK","ANTHROPIC_AWS_API_KEY"]', 'strip', 'the AWS-hosted provider keys'),
    ('skip_provider_auth', '["CLAUDE_CODE_SKIP_BEDROCK_AUTH","CLAUDE_CODE_SKIP_VERTEX_AUTH"', 'strip',
     'the switches that skip a provider login'),
    ('anthropic_secrets', '["ANTHROPIC_API_KEY",<items>"ANTHROPIC_AUTH_TOKEN",<items>"ANTHROPIC_CUSTOM_HEADERS",<items>'
     '"CLAUDE_CODE_OAUTH_TOKEN",<items>"CLAUDE_CODE_OAUTH_REFRESH_TOKEN"', 'strip', "Claude Code's own list of Anthropic secrets (with their INPUT_ forms)"),
    ('session_tokens', 'new Set(["CLAUDE_CODE_SESSION_ACCESS_TOKEN",<items>"CLAUDE_CODE_OAUTH_TOKEN"', 'strip',
     'the session tokens a hosted or claimed session authenticates with'),
    ('claimed_session_tokens', 'new Set(["CLAUDE_CODE_OAUTH_TOKEN","CLAUDE_CODE_SESSION_ACCESS_TOKEN","CLAUDE_CODE_HOST_SESSION_ID"])',
     'strip', 'the tokens a claimed spare session is handed'),
    ('api_key_pair', 'new Set(["ANTHROPIC_AUTH_TOKEN","ANTHROPIC_API_KEY"])', 'strip', 'the API key and bearer token'),
    ('bedrock_wizard', 'new Set(["AWS_BEARER_TOKEN_BEDROCK","AWS_SECRET_ACCESS_KEY","AWS_SESSION_TOKEN"])', 'keep',
     'the Bedrock setup wizard\'s AWS credentials: AWS_BEARER_TOKEN_BEDROCK is stripped by auth_credentials; the general '
     'AWS keys are the worker\'s tools\' own cloud login and reach no model once the CLAUDE_CODE_USE_ switches are gone'),
    ('tool_secret_scrub', '["ANTHROPIC_API_KEY",<items>"CLAUDE_CODE_OAUTH_TOKEN",<items>"CLAUDE_CODE_ARTIFACTS_API_TOKEN"', 'keep',
     'the secrets Claude Code scrubs from its own tool children (package registries, CI, cloud, webhooks): tool '
     'credentials, not a model login'),
]
ENV_ARRAY = re.compile(r'(?:new Set\()?\[("[A-Z0-9_]+"(?:,"[A-Z0-9_]+")*)\]\)?')

# Claude Code's lists that spread other lists (`...NAME`), each read with every spread resolved to the
# nearest definition of that minified name: (name, the exact text the list starts with, decision, reason,
# exceptions). `strip`: every name is a login, credential, credential or settings redirect, endpoint or
# paid-API switch; it never reaches the engine from the inherited environment and a configured one is
# refused. The exceptions of a strip list name what it holds that is not a login: `keep` names are the
# general proxy, CA, runtime, cloud and home names the worker's own tools need, passed as inherited;
# `setting` names are Claude Code's own non-login settings, stripped from the inherited environment (they
# are the owner's shell's, not the adapter's) but passed when the adapter configures them.
KEEP_PROXY = ('HTTPS_PROXY', 'HTTP_PROXY', 'NO_PROXY', 'ALL_PROXY')
KEEP_RUNTIME = ('NODE_EXTRA_CA_CERTS', 'NODE_TLS_REJECT_UNAUTHORIZED', 'NODE_OPTIONS')
KEEP_CLOUD = ('GOOGLE_APPLICATION_CREDENTIALS', 'GOOGLE_CLOUD_PROJECT', 'GOOGLE_EXTERNAL_ACCOUNT_ALLOW_EXECUTABLES',
              'GCLOUD_PROJECT', 'CLOUDSDK_CONFIG', 'METADATA_SERVER_DETECTION')
KEEP_CLOUD_PREFIXES = ('AWS_', 'GCE_METADATA_')
KEEP_HOME = ('HOME', 'XDG_CONFIG_HOME', 'APPDATA', 'USERPROFILE', 'HOMEDRIVE', 'HOMEPATH', 'PROGRAMDATA')
CLAUDE_SETTINGS = ('CLAUDE_CODE_PROXY_RESOLVES_HOSTS', 'CLAUDE_CODE_ENABLE_PROXY_AUTH_HELPER',
                   'CLAUDE_CODE_PROXY_AUTH_HELPER_TTL_MS', 'API_FORCE_IDLE_TIMEOUT', 'CLAUDE_CODE_CERT_STORE')


def _evaluated_environment():
    """VELDO-0230 AC3: the evaluated environment names of a newer Claude Code (runtime/capability-decisions.json):
    {name: (keep or setting or strip, reason)}."""
    try:
        record = json.loads((Path(__file__).resolve().parents[2] / '.veldo/runtime/capability-decisions.json').read_text())
    except (OSError, ValueError):
        return {}
    return {name: (entry.get('effect'), entry.get('reason', ''))
            for name, entry in ((record.get('claude_code') or {}).get('environment') or {}).items()}


def _sensitive_exceptions(names):
    """The names of Claude Code's sensitive-variable set that are not a login, each with why."""
    found = {}
    evaluated = _evaluated_environment()
    for name in names:
        if evaluated.get(name, ('',))[0] in ('keep', 'setting'):
            found[name] = {'decision': evaluated[name][0], 'reason': 'VELDO-0230 evaluation: ' + evaluated[name][1]}
        elif name in KEEP_PROXY:
            found[name] = {'decision': 'keep', 'reason': 'general proxy: the worker\'s tools reach the network through it'}
        elif name in KEEP_RUNTIME:
            found[name] = {'decision': 'keep', 'reason': 'CA and runtime: the worker\'s tools verify TLS and run node with it'}
        elif (name in KEEP_CLOUD or name.startswith(KEEP_CLOUD_PREFIXES)) and name != 'AWS_BEARER_TOKEN_BEDROCK':
            found[name] = {'decision': 'keep', 'reason': 'cloud: the worker\'s tools\' own cloud login; no model request '
                           'goes through it once the provider switches are stripped'}
        elif name in KEEP_HOME:
            found[name] = {'decision': 'keep', 'reason': 'home: every tool the worker runs needs its home directory'}
        elif name in CLAUDE_SETTINGS:
            found[name] = {'decision': 'setting', 'reason': 'a Claude Code connection setting, not a login'}
    return found


CLAUDE_LISTS = [
    ('sensitive_env', 'var ji=new Set([<items>"CLAUDE_CODE_PROXY_RESOLVES_HOSTS","CLAUDE_CODE_ENABLE_PROXY_AUTH_HELPER"', 'strip',
     'the variables Claude Code refuses to take from a settings file: its logins, the credential and settings '
     'redirects (CLAUDE_SECURESTORAGE_CONFIG_DIR, CLAUDE_CODE_HOST_CREDS_FILE, the managed and remote settings paths, '
     'the OAuth, bridge and federation overrides), the endpoints and provider switches', _sensitive_exceptions),
    ('fd_tokens', 'Q0t=["CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR"', 'strip',
     'the credentials handed to Claude Code through a file descriptor', None),
    ('session_secrets', 'Z0t=["CLAUDE_CODE_OAUTH_TOKEN",<items>...Q0t', 'strip',
     'the OAuth, bridge, trusted-device and background-session tokens and auth paths', None),
    ('host_creds_env', 'Spo=new Set([...YU,...hW.filter((e)=>e!=="_CLAUDE_CODE_ASSUME_FIRST_PARTY_BASE_URL"', 'strip',
     'the variables a CLAUDE_CODE_HOST_CREDS_FILE may set when Claude Code copies it into its environment at start-up',
     None),
    ('model_config', 'z4e=["ANTHROPIC_MODEL"', 'model',
     'the model configuration: stripped from the inherited environment only through the ANTHROPIC_ family, passed '
     'when the adapter configures it (the configured model is a capability, not a login)', None),
    ('custom_model_option', 'Bin=["ANTHROPIC_CUSTOM_MODEL_OPTION"', 'model', 'the custom model option, as model_config',
     None),
    ('not_secrets', 'Gi=new Set(["CLAUDE_CODE_CLIENT_KEY"', 'keep',
     'the names Claude Code itself says look like a secret and are not (its token thresholds and usage settings); '
     'a name here that a strip list also names is stripped', None),
]
# The one filtered spread these lists use: Spo takes hW without the first-party assumption, the artifact names and the
# memory API names (Ame is Xo.includes). A list anchor's names are bound by the lists read before it (the fd_tokens
# list's name in session_secrets).
HOST_CREDS_FILTER = ('...hW.filter((e)=>e!=="_CLAUDE_CODE_ASSUME_FIRST_PARTY_BASE_URL"&&!e.startsWith("CLAUDE_CODE_ARTIFACT")'
                     '&&!Ame(e))')
AME = 'function Ame(e){return Xo.includes(e)}'


def _js_list(js, at, seen=()):
    """The string values of the array literal whose '[' is the first one at or after `at`, every
    `...NAME` spread resolved to the nearest definition of NAME (and the one filtered spread above)."""
    text = js.text
    start = text.index('[', at)
    names, depth, pos, item = [], 0, start + 1, ''
    items = []
    while True:
        ch = text[pos]
        if ch == '"':
            end = text.index('"', pos + 1)
            item += text[pos:end + 1]
            pos = end + 1
            continue
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            if depth == 0:
                items.append(item)
                break
            depth -= 1
        elif ch == ',' and depth == 0:
            items.append(item)
            item = ''
            pos += 1
            continue
        item += ch
        pos += 1
    for item in (i.strip() for i in items):
        if not item:
            continue
        if re.fullmatch(r'"[A-Za-z0-9_]+"', item):
            names.append(item[1:-1])
        elif anchor(HOST_CREDS_FILTER).regex.fullmatch(item):
            m = anchor(HOST_CREDS_FILTER).regex.fullmatch(item)
            hw, ame = (anchor(HOST_CREDS_FILTER).name(m, n) for n in ('hW', 'Ame'))
            test, names_of = site(text, AME, 'the memory-name test of the host credentials filter', bound={'Ame': ame})
            memory = _js_list(js, _definition(js, names_of['Xo'], test.start()), seen)
            names += [n for n in _js_list(js, _definition(js, hw, at), seen)
                      if n != '_CLAUDE_CODE_ASSUME_FIRST_PARTY_BASE_URL' and not n.startswith('CLAUDE_CODE_ARTIFACT')
                      and n not in memory]
        elif re.fullmatch(r'\.\.\.[A-Za-z_$][A-Za-z0-9_$]*', item):
            ref = item[3:]
            if ref in seen:
                raise Moved('a list spreads itself: ' + ref)
            names += _js_list(js, _definition(js, ref, at), seen + (ref,))
        else:
            raise Moved('an unread list item at %d: %r' % (start, item[:80]))
    return names


def _definition(js, name, near):
    """The offset of the nearest `NAME=[` or `NAME=new Set([` (minified names repeat)."""
    best = js.nearest(name, r'=(?:new Set\()?\[', near)
    if best is None:
        raise Moved('no list named ' + name)
    return best.start()


# VELDO-0160: Claude Code's rate-limit result. The usage-limit message its API error message and its
# result carry (the template, the reset piece, the binary's names of the windows), the time formats and
# the zone it states the reset in, and a 429 message that is not the account's limit. Each piece by its minified
# text; the window names are the map the builder's weekly name reads (`names_use`), and the zone suffix calls the
# zone function (`zone_suffix`). A later build may pass the formatter a zone of its own (`<any>`).
CLAUDE_LIMIT = {
    'builder': 'function _h(e,n,r,s){let g=s?.progressSavedSuffix?',
    'template': 'return`You\'ve hit your ${e}${n}${g}`}',
    'progress': 'g=s?.progressSavedSuffix?" \\xB7 progress saved":""',
    'resets': 'M=_?` \\xB7 resets ${_}`:""',
    'names_use': 'return e==="pro"||e==="enterprise"?Ide.seven_day:Ide.seven_day_sonnet}',
    'names': 'var Ide={',
    'within_day': 'o.toLocaleTimeString("en-US",{hour:"numeric",minute:c===0?void 0:"2-digit",hour12:!0<any>})'
                  '.replace(/[ \\u202f]([AP]M)/i,(u,i)=>i.toLowerCase())',
    'beyond_day': 'let u={month:"short",day:"numeric",hour:r?"numeric":void 0,minute:!r||c===0?void 0:"2-digit",'
                  'hour12:r?!0:void 0<any>};if(<any>)u.year="numeric";return o.toLocaleString("en-US",u)',
    'zone': 'function a0r(){if(!g)g=Intl.DateTimeFormat().resolvedOptions().timeZone;return g}',
    'zone_suffix': '` (${<any>a0r()})`',
    'not_account': 'q$n="Server is temporarily limiting requests (not your usage limit)"',
}


# The binary's other rejected-status texts, which do not start "You've hit your": each return of the
# message builder's `overageStatus === "rejected"` branch that is not the template, with the texts it
# makes (the out-of-credits reset and progress pieces, and the admin suffix, are appended to the first and
# the last two). Each must lie in that branch, after its opening test and before the template's own returns.
CLAUDE_REJECTED_BRANCH = 'if(e.overageStatus==="rejected"){'
CLAUDE_REJECTED_END = 'return _h("limit",_e,n,'
CLAUDE_REJECTED = (
    ('return`You\'re out of usage credits${_e}${ve}`', ["You're out of usage credits"]),
    ('return s?"Your org is out of usage \\xB7 add funds to continue":"Your org is out of usage \\xB7 contact your admin"',
     ['Your org is out of usage \u00b7 add funds to continue', 'Your org is out of usage \u00b7 contact your admin']),
    ('return`Your seat type doesn\'t include ${r?"usage":"usage credits"}`',
     ["Your seat type doesn't include usage", "Your seat type doesn't include usage credits"]),
    ('return"This service is disabled for your org"', ['This service is disabled for your org']),
    ('return`Your usage allocation has been disabled by your admin${kke()}`',
     ['Your usage allocation has been disabled by your admin']),
    ('return`Your group\'s usage limit is set to $0${kke()}`', ["Your group's usage limit is set to $0"]),
)
CLAUDE_ADMIN_SUFFIX = 'function kke(){let e=EKe();return e?` \\xB7 run ${e} to ask your admin for a higher limit`:" \\xB7 ask your admin for a higher limit"'


def claude_rejected(text):
    """(the rejected-status texts that are not "You've hit your ...", each checked in the builder's branch,
    the ones the admin suffix follows)."""
    if len(sites(text, CLAUDE_REJECTED_BRANCH)) != 1 or len(sites(text, CLAUDE_ADMIN_SUFFIX)) != 1:
        raise Moved('claude rejected-status branch moved')
    branch = sites(text, CLAUDE_REJECTED_BRANCH)[0].start()
    _, names = site(text, CLAUDE_ADMIN_SUFFIX, 'claude rejected-status branch')
    _, builder = site(text, CLAUDE_LIMIT['builder'], 'claude usage-limit piece builder')
    bound = {'kke': names['kke'], '_h': builder['_h']}
    ends = [m.start() for m in sites(text, CLAUDE_REJECTED_END, bound) if m.start() > branch]
    end = ends[0] if ends else -1
    found, suffixed = [], []
    for source, texts in CLAUDE_REJECTED:
        matches = sites(text, source, uses(source, bound))
        if len(matches) != 1 or not branch < matches[0].start() < end:
            raise Moved('claude rejected-status text moved: ' + source[:40])
        found += texts
        suffixed += texts if source.endswith('${kke()}`') else []
    return found, suffixed


def claude_limit(text):
    bound, binds = {}, {'builder': '_h', 'names_use': 'Ide', 'zone': 'a0r'}
    for key, source in CLAUDE_LIMIT.items():
        found = sites(text, source, uses(source, bound))
        if not found or (key in ('builder', 'names_use', 'names', 'zone') and len(found) != 1):
            raise Moved('claude usage-limit piece moved: ' + key)
        if key in binds:
            bound[binds[key]] = anchor(source, uses(source, bound)).name(found[0], binds[key])
    m = sites(text, CLAUDE_LIMIT['names'], {'Ide': bound['Ide']})[0]
    at = m.start()
    block = text[m.end() - 1:text.index('}', at) + 1]
    names = dict(re.findall(r'([a-z_]+):"([^"]+)"', block))
    if 'five_hour' not in names or 'seven_day' not in names:
        raise Moved('claude usage-limit names moved')
    return {'message': "You've hit your ", 'progress_saved': ' \u00b7 progress saved', 'resets': ' \u00b7 resets ',
            'names': names, 'zone': ' (<IANA zone>)',
            'formats': ['{hour}{:minute}{am|pm}', '{month} {day}, {hour}{:minute}{am|pm}',
                        '{month} {day}, {year}, {hour}{:minute}{am|pm}'],
            'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            'not_account': ['Server is temporarily limiting requests (not your usage limit)'],
            'rejected': claude_rejected(text)[0], 'admin_suffix': ' \u00b7 ask your admin for a higher limit',
            'admin_suffixed': claude_rejected(text)[1],
            'rejected_source': "the rejected-status texts that do not start with the template, each the account "
                               "refused: the out-of-credits text (+ ' \u00b7 resets ' + time, + ' \u00b7 progress "
                               "saved'), the org, seat, service, admin and $0-group texts (the last two + the admin "
                               "suffix, or ' \u00b7 run <command> to ask your admin for a higher limit')",
            'source': "the rate-limit result's text: `You've hit your ${limit}${' \u00b7 resets ' + time}` "
                      "(+ ' \u00b7 progress saved'), the assistant API error message with error 'rate_limit' and the "
                      "result's `result`; time en-US with ':minute' only when not 0, 'am'/'pm' lowercased, the date "
                      "when the reset is over a day away, the year when it is another year, then ' (<zone>)', the "
                      "engine's resolved IANA time zone"}


# VELDO-0160: the forms a tool call can take in Claude Code's stream, each by the minified text of the table
# it is read from (the zod helpers bound to the build's names; the message union by the assistant message's
# schema, `assistant`, the stdout union by the message union), so the re-run-or-ask decision counts any other form as an unknown call.
# `messages`: the SDK message union (each member's type and subtype); `response_blocks` and `request_blocks`:
# the content block unions of an assistant message and of a user message (the modelled members, then the
# type tags the binary lists); `stream_events`: the streaming events a stream_event carries, as its schema
# names them; `builtin_tools`: the binary's own list of its built-in tool names.
CLAUDE_FORMS = {
    'assistant': 'Qo=f(()=>d({type:R("assistant"),message:',
    'messages': 'nn=f(()=>Fe([Qo(),sr(),oK(),_K(),',
    'response_blocks': 'yq=f(()=>Fe([Aq(),Rq(),NR(),zR(),...bR.map(AR)])',
    'request_blocks': 'fq=f(()=>Fe([Js(),Lo(),yR(),wR(),mq(),Tq(),NR(),zR(),...tq.map(AR)])',
    'tagged': 'bR=["server_tool_use",',
    'tagged_request': 'tq=[...bR,"mid_conv_system"]',
    'stream_events': 'tK=f(()=>ae().describe("One Anthropic Messages API streaming event (message_start, content_block_start, '
                     'content_block_delta, content_block_stop, message_delta, message_stop) as defined',
    'builtin_tools': 'dT.BUILTIN_TOOL_NAMES=[',
    'stdout': 'TRr=f(()=>Fe([nn(),<any>]).describe("Everything the CLI writes to its output stream',
    'agent_tool': 'name:mt,searchHint:"delegate work to a subagent",aliases:[',
    'agent_names': ',Omo="Launch a new agent to handle complex, multi-step tasks",',
    'task_progress': 'last_tool_name:e.lastToolName,summary:e.summary,workflow_progress:e.workflowProgress})',
    'workflow_agent': 'lastToolName:we,lastToolSummary:qe,',
}
FORMS_WINDOW = 400000
# The frames the binary emits carrying a tool's name outside the schema it declares for them, each by the
# text of its emitters and how many there are: the REPL tool's `repl_call` on a tool_progress (its inner tool's
# name; a build without the REPL progress kind `repl_tool_call` has none), and the workflow agents' progress
# entries a task_progress carries.
CLAUDE_EMITTED = {'repl_call': ('repl_call:{inner_tool_name:', 2)}
CLAUDE_REPL_PROGRESS = 'repl_tool_call'
# How a task counts its own calls, each by its minified text and how many times it occurs (a later build adds
# fields where an anchor has `<any>`): the tracker
# raises its count by one for each tool_use block of the task's own assistant messages (`rise`); an agent's
# task_progress carries that count (`progress`) under the task's tool_use_id (`progress_frame`); its end
# notification carries it as usage too (`notification_frame`, `notification_count`); the sub-agent's forwarded
# assistant and user messages carry the task's id as parent_tool_use_id (`forwarded`); and an agent a sub-agent
# starts reaches the stream only when forwardSubagentText is set (`nested_gate`, whose condition is either the
# option itself, `nested_option`, or a test of it, `nested_test`, that a later build extends to the consumer's
# forwardNestedSubagentToolCalls capability for its tool calls).
CLAUDE_TASKS = {
    'rise': ('for(let h of n.message.content){if(h.type!=="tool_use")continue;if(e.toolUseCount++', 1),
    'progress': ('totalTokens:T.tokenCount,toolUses:T.toolUseCount,lastToolName:_})', 1),
    'progress_frame': ('type:"system",subtype:"task_progress",task_id:e.taskId,<field>tool_use_id:e.toolUseId,'
                       'description:e.description,subagent_type:e.subagentType,usage:{total_tokens:e.totalTokens,'
                       'tool_uses:e.toolUses,', 1),
    'notification_frame': ('type:"system",subtype:"task_notification",task_id:e,<field>tool_use_id:r?.toolUseId,status:n,', 1),
    'notification_count': ('usage:{total_tokens:N?.tokenCount??0,tool_uses:N?.toolUseCount??0,', 1),
    'forwarded': ('parent_tool_use_id:e.parentToolUseID,<field>session_id:Y(),uuid:g.uuid', 2),
    'nested_gate': ('if(Sne(T)){if(<any>)p(pqt(T));return}', 1),
}
CLAUDE_NESTED_OPTION = 'Kt=e.options.forwardSubagentText'
CLAUDE_NESTED_TEST = ('function T2e(e,n){if(e.options.forwardSubagentText)return!0;'
                      'if(e.session.surfaceCapabilities.sdkForwardNestedSubagentToolCalls()!==!0)return!1;')


# VELDO-0160, the lead's structural rule: every construct through which a Claude Code run can do work its stream
# may not show (a tool that runs an agent, a skill, code or a workflow, a task's frames, a sub-agent's forwarded
# messages, a forked skill's result), each by its minified text and how many times it occurs (a binding by its
# variable and name; the separator after it is the build's). A tool
# is its name's binding and its definition (the binding's variable as its name); the Agent tool and its alias are
# builtin_renamed's. `forwarded`: the progress kinds whose messages the CLI forwards under their task's id;
# `workflow_task`: the task type of a workflow; `skill_forked`: the Skill tool's result when it forked an agent.
CLAUDE_NESTED_TOOLS = (
    ('agent', 'SendMessage', 'var eo="SendMessage",', 'name:eo,searchHint:"send messages to agent teammates"'),
    ('skill', 'Skill', 'var go="Skill",', 'name:go,searchHint:"invoke a slash-command skill"'),
    ('repl', 'REPL', 'var za="REPL";', 'tool_name:za,parent_tool_use_id:T.parentToolUseID||null,'
                                        'elapsed_time_seconds:0,repl_call:{'),
    ('workflow', 'Workflow', 'var Ed="Workflow";', 'name:Ed,aliases:["RunWorkflow"],searchHint:"orchestrate subagents'),
    ('remote', 'RemoteTrigger', 'var lK="RemoteTrigger",',
     'name:lK,searchHint:"manage scheduled cloud agent routines; inspect their run history and logs",'
     'enablesCodeExecution:!0,'),
    ('cron', 'CronCreate', 'var iy="CronCreate",',
     'name:iy,searchHint:"schedule a recurring or one-shot prompt",enablesCodeExecution:!0,'),
)
# VELDO-0160, the lead's decision on work that outlives the run: a call that starts an agent outside it, which may
# act on the account's claude.ai connectors whatever the run's configuration. RemoteTrigger (a deferred tool) manages
# the account's cloud agent routines: its create, update and run start a cloud agent (`description`, `actions`);
# CronCreate schedules a prompt, and a durable one persists to the project's scheduled tasks and fires after the run
# (`durable`: its optional field, false by default, read through the binary's semantic boolean, `semantic`).
CLAUDE_REMOTE = {
    'description': ('Uno="Manage scheduled remote Claude Code agents (routines) via the claude.ai CCR API', 1),
    'actions': ('action:z(["list","get","create","update","run","create_webhook_trigger","list_runs","get_run_log"])', 1),
    'durable': ('durable:BA(O().optional()).describe(uyr(Foe()))', 1),
    'durable_text': ('function uyr(e){return e?"true = persist to .claude/scheduled_tasks.json and survive restarts. '
                     'false (default) = in-memory only, dies when this Claude session ends.', 1),
    'semantic': ('function BA(e=O()){return Yi(dN,e)}function dN(e){return e==="true"?!0:e==="false"?!1:e}', 1),
}
CLAUDE_NESTED = {
    'forwarded': ('function Sne(e){return e.type==="progress"&&(e.data.type==="agent_progress"||'
                  'e.data.type==="skill_progress")}', 1),
    'forwarded_emit': ('case"progress":if(Sne(e))yield*oer(e,n);', 1),
    'workflow_task': ("Only set when task_type is 'local_workflow'.", 2),
    'skill_forked': ('status:R("forked").describe("Execution status"),agentId:o().describe("The ID of the sub-agent '
                     'that executed the skill")', 1),
}


# VELDO-0160, the lead's allowlist (fail closed): the built-in tools whose effects stay inside the run's clone and host
# session, each as (name, why, its name's binding, its definition's own text), each occurring once in this build. The
# file tools, Glob and Grep, the notebook edit, the session checklist, the deferred-tool loader; Bash and its
# background companions (TaskStop, aliased KillShell and KillBash, which kills a background task; Monitor, which runs a
# command through Bash's permission check or reads a WebSocket); the read-only web fetch and search; and rule 2's
# constructs (the Agent tool unless remote, the Skill, REPL and Workflow tools, CronCreate unless durable, which the
# remote_agent rule asks for). The binary has no LS tool: no binding names one. A tool whose definition a build drops
# while keeping its name (REPL without its progress emitter) leaves the allowlist (fail closed).
CLAUDE_IN_RUN = (
    ('Read', 'reads a local file', 'var lt="Read",',
     'name:lt,ruleContentField:"file_path",searchHint:"read files, images, PDFs, notebooks",remoteExecution:{supported:!0,'),
    ('Write', 'writes a local file', 'var vn="Write";',
     'name:vn,ruleContentField:"file_path",searchHint:"create or overwrite files",remoteExecution:{supported:!0,'),
    ('Edit', 'edits a local file', 'var Pt="Edit",',
     'name:Pt,ruleContentField:"file_path",searchHint:"modify file contents in place",remoteExecution:{supported:!0,'),
    ('NotebookEdit', 'edits a local notebook', 'var lc="NotebookEdit";',
     'name:lc,ruleContentField:"notebook_path",searchHint:"edit Jupyter notebook cells (.ipynb)",'),
    ('Glob', 'finds local files', 'var oo="Glob";',
     'name:oo,searchHint:"find files by name pattern or wildcard",backgrounding:"never",maxResultSizeChars:1e5,'
     'async description(){return Uwr(void 0)},remoteExecution:{supported:!0}'),
    ('Grep', 'searches local files', 'var zr="Grep";',
     'name:zr,searchHint:"search file contents with regex (ripgrep)",remoteExecution:{supported:!0}'),
    ('TodoWrite', 'the session checklist', 'var nb="TodoWrite";', 'name:nb,searchHint:"manage the session task checklist",'),
    ('ToolSearch', 'loads a deferred tool\'s schema', 'var xa="ToolSearch",',
     'name:xa,backgrounding:"never",maxResultSizeChars:1e5,async description(){return G0n()},'),
    ('Bash', 'the shell', 'var Be="Bash";',
     'name:Be,enablesCodeExecution:!0,ruleContentField:"command",searchHint:"execute shell commands",'
     'remoteExecution:{supported:!0,'),
    ('TaskStop', 'kills a background task (Bash\'s companion)', 'var Om="TaskStop",',
     'name:Om,searchHint:"kill a running background task",aliases:['),
    ('Monitor', 'streams a background command or a WebSocket (Bash\'s companion)', 'var Za="Monitor";',
     'name:Za,enablesCodeExecution:!0,maxResultSizeChars:1e4,shouldDefer:!0,userFacingName(){return"Monitor"},'),
    ('WebFetch', 'fetches a URL', 'var Wr="WebFetch",',
     'name:Wr,ruleContentField:@"url",searchHint:"fetch and extract content from a URL",'),
    ('WebSearch', 'searches the web', 'var eI="WebSearch";', 'name:eI,searchHint:"search the web for current information",'),
    ('Agent', 'a local agent (rule 2), unless remote', 'var mt="Agent",', 'name:mt,searchHint:"delegate work to a subagent",aliases:['),
    ('Skill', 'a skill (rule 2)', 'var go="Skill",', 'name:go,searchHint:"invoke a slash-command skill"'),
    ('REPL', 'code whose inner calls the stream names (rule 2)', 'var za="REPL";',
     'tool_name:za,parent_tool_use_id:T.parentToolUseID||null,elapsed_time_seconds:0,repl_call:{'),
    ('Workflow', 'local workflow agents (rule 2)', 'var Ed="Workflow";',
     'name:Ed,aliases:["RunWorkflow"],searchHint:"orchestrate subagents'),
    ('CronCreate', 'a prompt in this session (rule 2), unless durable', 'var iy="CronCreate",',
     'name:iy,searchHint:"schedule a recurring or one-shot prompt",'),
)
# How an allowlisted call can still act outside the run, each by the exact text of this build (once each). The Agent
# tool runs remote when its input's `isolation` is "remote" (`agent_input`) or, with none given, when the agent
# definition its `subagent_type` names says so (`agent_resolved`; an agent file may set isolation remote,
# `agent_file`); no built-in agent definition sets isolation. A remote agent is a task of type `remote_agent`
# (`remote_task`), and every task but an observer agent is reported by a task_started naming its type
# (`task_started`, `task_type`, `observer`). The file tools and Bash take a `_host` naming another machine
# (`host_field`, `host_request`, `host_local`, `host_local_test`), routed there only when the remote-tools gate is on
# (`host_route`), and the gate's value (`host_gate`, then the body of the function it calls) is compiled off (`!1`)
# or, in a later build, an environment switch (`ENV.NAME===!0`), which routed names. A workflow task's progress gives its
# current agent's label as its last tool (`workflow_label`), not a tool: its agents' own last tools are named beside it.
CLAUDE_IN_RUN_CONDITIONS = {
    'skill_input': ('var Ee=f(()=>d({skill:o().describe("The name of a skill from the available-skills list. '
                   'Do not guess names."),args:o().optional().describe("Optional arguments for the skill")})),', 1),
    'skill_schema': ('name:go,searchHint:"invoke a slash-command skill",<any>get inputSchema(){return Ee()}', 1),
    'skill_context': ('function P9t(e,n,r){return e.getContext?.(n,r)??e.context??"inline"}', 1),
    'skill_fork': ('if(u?.type==="prompt"&&P9t(u,s||"",n)==="fork"&&!S)', 1),
    'agent_input': ('isolation:z(["worktree","remote"]).optional().describe(\'Isolation mode. "worktree" creates a '
                    'temporary git worktree so the agent works on an isolated copy of the repo. "remote" launches the '
                    'agent in a remote cloud environment', 1),
    'agent_resolved': ('function an(n){let{agent:e,isolation:h,restricted:g}=n,p=h??e.isolation;', 1),
    'agent_file': ('let Pe=["worktree","remote"],Le=r.isolation,De;', 1),
    'remote_task': ('var Kbe={name:"RemoteAgentTask",type:"remote_agent",', 1),
    'task_started': ('subtype:"task_started",task_id:e.id,<field>owned_by_subagent:zt(e),tool_use_id:e.toolUseId,', 1),
    'task_type': ('task_type:e.type,workflow_name:', 1),
    'observer': ('function fu(e){return e.type==="local_agent"&&"isObserver"in e&&e.isObserver===!0}', 1),
    'host_field': ('var Jr="_host",', 1),
    'host_request': ('function sqe(e){let{[Jr]:r,...n}=e;if(typeof r!=="string")return{requested:void 0,input:e};'
                     'let s=r.trim();return{requested:s===""||VE(s)?void 0:s,input:n}}', 1),
    'host_local': ('var Len="device",Ki=["container","this-machine"],', 1),
    'host_local_test': ('function VE(e){return Ki.some((r)=>r===e)}', 1),
    'host_route': ('if(!$j(e).supported||!Ih())return{kind:"local",input:n};', 1),
    'host_gate': ('async function eY(){return Ih()&&await Nd()}function SG(){return Ih()&&_s()}function Ih(){return cNn()}', 1),
    'workflow_label': ('toolUses:xe.totalToolCalls,lastToolName:bt?.label,summary:h,workflowProgress:', 1),
}
# The task types of the allowlisted tools, from the binary's task table (`name:"...Task",type:"..."`): an agent, a
# teammate an agent starts, a background shell or command, a workflow, a Monitor's WebSocket.
CLAUDE_IN_RUN_TASKS = ('in_process_teammate', 'local_agent', 'local_bash', 'local_workflow', 'monitor_ws')
# The allowlisted tools a build may drop, each with the text whose absence shows it dropped them.
CLAUDE_IN_RUN_OPTIONAL = {'REPL': CLAUDE_REPL_PROGRESS}


def _binding(text, name, binding, definition, what, js, bound=()):
    """(the match of a tool's definition, its variable): the definition (its name's variable read from it) and the
    binding of that variable to `name`, each found once."""
    m, names = site(text, definition, '%s %s' % (what, name), bound=uses(definition, dict(bound)))
    head = re.match(r'var ([A-Za-z_$][\w$]*)="([^"]*)"', binding)
    variable = re.match(r'(?:name|tool_name):([A-Za-z_$][\w$]*),', m.group(0))
    if head is None or head.group(2) != name or variable is None:
        raise Moved('%s %s: its definition does not name its binding' % (what, name))
    found = sites(text, binding.rstrip(',;'), {head.group(1): variable.group(1)})
    if len(found) != 1 or text[found[0].end()] not in ',;':
        raise Moved('%s %s: anchor %r found %d times' % (what, name, binding, len(found)))
    return m, variable.group(1)


def _aliases(js, at):
    """The aliases a tool definition starting at `at` lists (string entries and spread lists)."""
    text = js.text
    listed = re.match(r'name:[\w$]+,(?:[^{}]*?,)?aliases:\[([^\]]*)\]', text[at:at + 400])
    if not listed:
        return []
    found = []
    for item in listed.group(1).split(','):
        if item.startswith('"'):
            found.append(json.loads(item))
        elif item.startswith('...'):
            found += _js_list(js, _definition(js, item[3:], at))
    return found


def _remote_support(text, at):
    """Whether the tool definition starting at `at` declares remote execution: supported outright, or by a getter."""
    window = text[at:at + 1500]
    return 'remoteExecution:{supported:!0' in window or 'get remoteExecution(){' in window


def _in_run(text, renamed, helpers):
    """The allowlist (VELDO-0160, the lead's decision), each tool checked against this build's text: {tools, aliases,
    agent, host, task_types}."""
    tools, aliases, remote, bound = [], {}, [], {}
    js = Js(text, helpers)
    for name, _, binding, definition in CLAUDE_IN_RUN:
        if name in CLAUDE_IN_RUN_OPTIONAL and CLAUDE_IN_RUN_OPTIONAL[name] not in text \
                and not sites(text, definition):
            continue
        m, variable = _binding(text, name, binding, definition, 'claude in-run tool', js)
        if name == 'Skill':
            bound['go'] = variable
        at = m.start()
        named = _aliases(js, at)
        if name == renamed[0]['name']:
            named = list(renamed[0]['aliases'])
        tools.append(name)
        if named:
            aliases[name] = sorted(named)
        if _remote_support(text, at):
            remote.append(name)
    values = {}
    for key, (source, count) in CLAUDE_IN_RUN_CONDITIONS.items():
        found = sites(text, source, uses(source, bound))
        if len(found) != count:
            raise Moved('claude in-run condition %s: anchor found %d times' % (key, len(found)))
        a = anchor(source, uses(source, bound))
        for own in ('Ee', 'P9t', 'Jr', 'VE', 'Ki', 'cNn', 'Ih'):
            if own in a.groups and own not in bound:
                bound[own] = a.name(found[0], own)
        values[key] = found[0].group(0)
    table = dict((kind, name) for name, kind in re.findall(r'name:"([A-Za-z]+Task)",type:"([a-z_]+)"', text))
    if 'remote_agent' not in table or not set(CLAUDE_IN_RUN_TASKS) <= set(table):
        raise Moved('claude task table moved')
    # The built-in agent definitions (source "built-in"), each by its agentType, none of which sets an isolation.
    builtin = []
    for m in re.finditer(r'agentType:("[A-Za-z_-]+"|[A-Za-z_$][\w$]{0,4})[,}]', text):
        window = text[m.start():m.start() + 3000]
        if not 0 <= window.find('source:"built-in"') < 2500:
            continue
        after = window.find('agentType:', 20)
        if 'isolation:' in window[:after if after > 0 else 3000]:
            raise Moved('claude built-in agent %s sets an isolation' % m.group(1))
        value = m.group(1)
        if not value.startswith('"'):
            # Minified names repeat (each chunk names its own): the binding nearest the definition.
            bound_to = min(re.finditer(r'(?:var |,|;)%s="([^"]+)"' % re.escape(value), text),
                           key=lambda b: abs(b.start() - m.start()), default=None)
            if bound_to is None:
                raise Moved('claude built-in agent type %s unbound' % value)
            value = json.dumps(bound_to.group(1))
        builtin.append(json.loads(value))
    if not {'general-purpose', 'Explore', 'Plan'} <= set(builtin):
        raise Moved('claude built-in agents moved')
    near = sites(text, CLAUDE_IN_RUN_CONDITIONS['host_gate'][0], uses(CLAUDE_IN_RUN_CONDITIONS['host_gate'][0], bound))
    gate = min(re.finditer(r'function %s\(\)\{return([^{}]*)\}' % re.escape(bound['cNn']), text),
               key=lambda m: abs(m.start() - near[0].start()), default=None)
    switch = re.fullmatch(r'\s*[\w$]+\.([A-Z][A-Z0-9_]*)===!0', gate.group(1)) if gate else None
    if gate is None or (gate.group(1) != '!1' and switch is None):
        raise Moved('claude in-run condition host_gate_value: the remote-tools gate moved')
    routed = False if switch is None else switch.group(1)
    gate_text = ('which this build compiles off (routed false)' if switch is None else
                 'which this build turns on when the environment sets %s (routed names it)' % routed)
    constructs = ', '.join(name for name in ('Agent', 'Skill', 'REPL', 'Workflow', 'CronCreate') if name in tools)
    isolation = values['agent_input']
    local = json.loads(values['host_local'][values['host_local'].index('['):values['host_local'].rindex(']') + 1])
    return {'tools': sorted(tools), 'aliases': aliases,
            'skill': {'tool': 'Skill', 'field': 'context', 'inline': 'inline', 'parent': 'parent_tool_use_id',
                      'input_fields': ['args', 'skill'], 'input_fork_field': None,
                      'context_source': 'skill definition: getContext(args, toolUseContext) or context'},
            'agent': {'tools': sorted([renamed[0]['name']] + list(renamed[0]['aliases'])), 'field': 'isolation',
                      'values': json.loads(isolation[isolation.index('(') + 1:].split(')')[0]),
                      'outside': 'remote', 'type_field': 'subagent_type', 'builtin_types': sorted(set(builtin))},
            'host': {'field': '_host', 'local': [''] + local, 'tools': sorted(remote),
                     'routed': routed},
            'workflow_last_tool': 'label',
            'task_types': {'field': 'task_type', 'in_run': sorted(CLAUDE_IN_RUN_TASKS),
                           'table': sorted(table)},
            'source': "the built-in tools whose effects stay inside the run's clone and host session (each name's "
                      "binding and the tool's definition, with its aliases): the file tools, Glob and Grep, the "
                      "notebook edit, the session checklist, the deferred-tool loader, Bash and its background "
                      "companions (TaskStop, Monitor), the read-only web fetch and search, and rule 2's constructs "
                      "(" + constructs + "); the Agent tool is remote when its input's isolation "
                      "is remote or, with none given, when the agent definition its subagent_type names says so (no "
                      "built-in definition sets isolation; builtin_types), and a remote agent is a task of type "
                      "remote_agent; the file tools and Bash take a _host naming another machine, routed there only "
                      "when the remote-tools gate is on, " + gate_text + "; the task types "
                      "of the allowlisted tools, from the binary's task table. Skill's input schema is only skill "
                      "and optional args, with no fork field; its definition supplies context (getContext or context, "
                      "default inline). A sub-agent's Skill therefore asks regardless of input; an explicit context "
                      "in the recorded input must exclude a fork. The binary has no LS tool."}


def _tags(schema):
    """The (type, subtype) pairs a message schema admits."""
    if schema.get('type') == 'union':
        return [tag for member in schema['anyOf'] for tag in _tags(member)]
    fields = schema.get('fields') or {}
    kind, sub = fields.get('type') or {}, fields.get('subtype')
    if kind.get('type') != 'literal':
        raise Moved('a stream message without a literal type')
    if sub is None:
        return [(kind['value'], None)]
    if sub.get('type') == 'literal':
        return [(kind['value'], sub['value'])]
    if sub.get('type') == 'enum' and sub.get('values'):
        return [(kind['value'], value) for value in sub['values']]
    raise Moved('a stream message subtype that is not a literal or an enum')


def _union_members(window, at, matched):
    """The member names of the union `NAME=LAZY(()=>UNION([A(),B(),...` matched as `matched` at `at` in `window`."""
    start = at + matched.index('([') + 2
    return re.findall(r'([A-Za-z_$][\w$]*)\(\)', window[start:window.index(']', start)])


# The names one form anchor binds for the anchors after it.
FORMS_BINDS = {'assistant': 'Qo', 'messages': 'nn', 'tagged': 'bR'}


def _forms(text, helpers):
    """{key: (match, {name in the anchor: name in the build})} of every CLAUDE_FORMS anchor, each found once."""
    key = ('forms', text)
    if key not in _SITES:
        bound, found = dict(helpers[2]), {}
        for name, source in CLAUDE_FORMS.items():
            found[name] = site(text, source, 'claude tool-call form table %s' % name, bound=uses(source, bound))
            if name in FORMS_BINDS:
                bound[FORMS_BINDS[name]] = found[name][1][FORMS_BINDS[name]]
        _SITES[key] = found
    return _SITES[key]


def _lazy(js, name, near):
    """The body of the lazy schema `name=f(()=>BODY` nearest `near` (a minified name is also bound to other
    values, which `Js.definition` could pick)."""
    best = js.nearest(name, r'=%s\(\(\)=>' % re.escape(js.lazy), near)
    if best is None:
        raise Moved('no lazy schema ' + name)
    return best.end()


def _tool_free(schema):
    """Whether a frame's schema provably carries no tool call: only literals, enums, strings, numbers and
    booleans, in objects, arrays and unions of them, and no field whose name names a tool."""
    kind = schema.get('type')
    if kind in ('literal', 'enum', 'string', 'number', 'boolean'):
        return True
    if kind == 'object':
        return all('tool' not in key and _tool_free(field) for key, field in (schema.get('fields') or {}).items())
    if kind == 'array':
        return _tool_free(schema.get('items') or {})
    if kind == 'union':
        return all(_tool_free(member) for member in schema.get('anyOf') or ())
    return False  # a record or an unresolved reference may hold anything


def _tool_paths(schema, path=()):
    """The dotted paths of the fields of a schema whose name names a tool (an array's items are its path)."""
    found = []
    kind = schema.get('type')
    if kind == 'object':
        for key, field in (schema.get('fields') or {}).items():
            if 'tool' in key.lower():
                found.append('.'.join(path + (key,)))
            found += _tool_paths(field, path + (key,))
    elif kind == 'array':
        found += _tool_paths(schema.get('items') or {}, path)
    elif kind == 'union':
        for member in schema.get('anyOf') or ():
            found += _tool_paths(member, path)
    return found


def _tag(kind, sub):
    return kind if sub is None else kind + '/' + sub


def _builtin_renamed(text, builtin, helpers):
    """[{name, aliases}]: a tool whose alias is on BUILTIN_TOOL_NAMES under a current name the list omits (the
    Agent tool, once `Task`), its names bound in the statement that also binds its own description."""
    forms = _forms(text, helpers)
    at = forms['agent_tool'][0].start()
    m = re.compile(r'name:([A-Za-z_$][\w$]*),searchHint:"[^"]*",aliases:\[([^\]]*)\]').match(text, at)
    names = forms['agent_names'][0].start()
    start, end = text.rindex('var ', 0, names), text.index(';', names)
    bound = dict(re.findall(r'(?:var |,)([A-Za-z_$][\w$]*)="([^"]*)"', text[start:end]))
    if m is None or m.group(1) not in bound or not text[start:names].startswith('var %s="' % m.group(1)):
        raise Moved('claude agent tool names moved')
    aliases = [json.loads(a) if a.startswith('"') else bound.get(a) for a in m.group(2).split(',')]
    name = bound[m.group(1)]
    if name in builtin or not aliases or not all(alias in builtin for alias in aliases):
        raise Moved('claude agent tool: its alias is not on BUILTIN_TOOL_NAMES under another name')
    return [{'name': name, 'aliases': aliases}]


def _repl_emitters(text):
    """The keys of the REPL tool's repl_call, the same in each of its emitters, or None when the build has no REPL
    progress kind (and so no emitter)."""
    source, count = CLAUDE_EMITTED['repl_call']
    found = sites(text, source)
    if not found and CLAUDE_REPL_PROGRESS not in text:
        return None
    keys = set()
    for m in found:
        body = text[m.start() + len('repl_call:{'):text.index('}', m.start())]
        keys.add(tuple(re.findall(r'([a-z_]+):', body)))
    if len(found) != count or len(keys) != 1 or 'inner_tool_name' not in next(iter(keys)):
        raise Moved('claude repl_call emitters moved')
    return next(iter(keys))


def _emitted(text, helpers):
    """The fields a frame carries that name a tool though its declared schema omits them, read from the
    emitters' own text: {tag: [dotted path]}."""
    keys = _repl_emitters(text)
    at = _forms(text, helpers)['workflow_agent'][0].start()
    if 'type:"workflow_agent"' not in text[at - 400:at]:
        raise Moved('claude workflow agent progress moved')
    emitted = {'system/task_progress': ['workflow_progress.lastToolName']}
    if keys is not None:
        emitted['tool_progress'] = ['repl_call.' + key for key in keys if 'tool' in key]
    return emitted


def _task_counts(text, fields):
    """How a task's count of its own calls reaches the stream: the frames whose schema carries the count and the
    task's id, the field of a sub-agent's message naming its task, each checked against the emitters' text."""
    found = {}
    for key, (source, count) in CLAUDE_TASKS.items():
        bound = {'Sne': _forwarded_test(text)} if key == 'nested_gate' else {}
        found[key] = site(text, source, 'claude task counts %s' % key, count, bound)
    gate = found['nested_gate'][0].group(0)
    condition = gate[gate.index('{if(') + 4:gate.rindex(')' + found['nested_gate'][1]['p'] + '(')]
    nested_calls = None
    if JS_NAME.fullmatch(condition):
        site(text, CLAUDE_NESTED_OPTION, 'claude task counts nested_option', bound={'Kt': condition})
    else:
        test = re.fullmatch(r'([A-Za-z_$][\w$]*)\([\w$,]*\)', condition)
        if test is None:
            raise Moved('claude task counts nested_gate: an unread condition %r' % condition)
        site(text, CLAUDE_NESTED_TEST, 'claude task counts nested_test', bound={'T2e': test.group(1)})
        nested_calls = 'forwardNestedSubagentToolCalls'
    at = found['notification_frame'][0].start()
    if not re.search(r'usage:[\w$]+\?\.usage', text[at:at + 300]):
        raise Moved('claude task notification usage moved')
    frames = sorted(tag for tag, paths in fields.items() if 'usage.tool_uses' in paths and 'tool_use_id' in paths)
    if frames != ['system/task_notification', 'system/task_progress'] \
            or 'tool_use_id' not in fields.get('system/task_started', ()) \
            or 'parent_tool_use_id' not in fields.get('assistant', ()):
        raise Moved('claude task count fields moved')
    return {'frames': frames, 'count': 'usage.tool_uses', 'task': 'tool_use_id', 'parent': 'parent_tool_use_id',
            'counts': 'tool_use', 'nested_forwarded_only_with': 'forwardSubagentText',
            **({'nested_tool_calls_forwarded_with': nested_calls} if nested_calls else {}),
            'source': "the frames whose schema carries a task's count of its calls (usage.tool_uses) and its id "
                      "(tool_use_id), the count the tracker raises by one for each tool_use block of the task's "
                      "own assistant messages (an agent's task_progress and its end notification carry it), the "
                      "task's id as the parent_tool_use_id of the sub-agent's forwarded messages, and the gate that "
                      "drops the messages of an agent a sub-agent starts unless forwardSubagentText is set"
                      + (" (its tool calls also when the consumer declares %s)" % nested_calls if nested_calls else "")}


def _tops(schema):
    """[(tag, its top-level field names)] for each member a message schema admits."""
    if schema.get('type') == 'union':
        return [pair for member in schema['anyOf'] for pair in _tops(member)]
    return [(_tag(kind, sub), set(schema.get('fields') or {})) for kind, sub in _tags(schema)]


def _forwarded_test(text):
    """The name of the test whose progress kinds the CLI forwards (Sne)."""
    return site(text, CLAUDE_NESTED['forwarded'][0], 'claude nested work forwarded')[1]['Sne']


def _nested(text, renamed, tops, helpers):
    """The constructs through which a run can do work its stream may not show (VELDO-0160), each checked against
    this build's text: {tools: {class: [names]}, task_frames, workflow, repl, forwarded, fork}."""
    bound = dict(helpers[2], Sne=_forwarded_test(text))
    for key, (source, count) in CLAUDE_NESTED.items():
        site(text, source, 'claude nested work %s' % key, count, uses(source, bound))
    tools = {'agent': [renamed[0]['name']] + list(renamed[0]['aliases'])}
    js = Js(text, helpers)
    repl = _repl_emitters(text)
    for construct, name, binding, definition in CLAUDE_NESTED_TOOLS:
        if construct == 'repl' and repl is None:
            # The build keeps the name and drops the emitter: the tool still runs code the stream does not show.
            head = re.match(r'var ([A-Za-z_$][\w$]*)="([^"]*)"', binding)
            if not [m for m in sites(text, binding.rstrip(',;')) if text[m.end()] in ',;']:
                raise Moved('claude nested tool %s: no binding' % name)
            tools.setdefault(construct, []).append(head.group(2))
            continue
        m, _ = _binding(text, name, binding, definition, 'claude nested tool', js)
        tools.setdefault(construct, []).append(name)
        tools[construct] += _aliases(js, m.start()) if m.group(0).startswith('name:') else []
    at = site(text, CLAUDE_NESTED['forwarded'][0], 'claude nested work forwarded')[0].start()
    kinds = re.findall(r'[\w$]+\.data\.type==="([a-z_]+)"', text[at:text.index('}', at)])
    frames = sorted(tag for tag, keys in tops if 'task_id' in keys and tag.startswith('system/'))
    if 'system/task_started' not in frames or not kinds \
            or not any(tag == 'system/task_started' and 'workflow_name' in keys for tag, keys in tops):
        raise Moved('claude task frames moved')
    _forms(text, helpers)
    for key, (source, count) in CLAUDE_REMOTE.items():
        site(text, source, 'claude remote agent %s' % key, count)
    return {'tools': {key: sorted(set(value)) for key, value in sorted(tools.items())},
            'task_frames': sorted(set(frames)),
            'workflow': {'system/task_progress': 'workflow_progress', 'system/task_started': 'workflow_name',
                         'task_type': 'local_workflow'},
            'repl': {'tool_progress': 'repl_call'} if repl is not None else {},
            'forwarded': {'field': 'parent_tool_use_id', 'progress': kinds},
            'fork': {'field': 'tool_use_result', 'status': 'forked'},
            'remote_agent': {'tools': ['RemoteTrigger'],
                             'durable': {'tool': 'CronCreate', 'field': 'durable', 'off': [False, 'false']}},
            'source': "the tools that run an agent, a skill, code, a workflow, a cloud agent routine or a scheduled "
                      "prompt (each name's binding and the tool's definition or emitter naming it, with its aliases; "
                      "the Agent tool's names are builtin_renamed's), the system frames whose schema carries a "
                      "task_id, the fields a task frame gives a workflow and a workflow's task type, the REPL tool's "
                      "inner call on a tool_progress, the progress kinds whose messages the CLI forwards with their "
                      "task's id as parent_tool_use_id (Sne), the Skill tool's result when it forked an agent, and "
                      "the calls that start an agent outside the run (remote_agent: any RemoteTrigger call, whose "
                      "create, update and run start a cloud agent routine, and a CronCreate whose optional durable "
                      "field, false by default and read through the semantic boolean that takes \"false\" for false, "
                      "persists the prompt to .claude/scheduled_tasks.json to fire after the run)"}


def claude_frames(text, helpers):
    """The StdoutMessage members outside the SDK message union, each (type, subtype, provably tool-free)."""
    forms = _forms(text, helpers)
    m, names = forms['stdout']
    at = m.start()
    window = text[at - FORMS_WINDOW:at + FORMS_WINDOW]
    js = Js(window, helpers)
    members = _union_members(window, FORMS_WINDOW, m.group(0))
    if members[0] != names['nn']:
        raise Moved('claude stdout union moved')
    found = []
    for name in members[1:]:
        schema = Reader(js, depth=3).parse(_lazy(js, name, FORMS_WINDOW))[0]
        found += [[kind, sub, _tool_free(schema)] for kind, sub in _tags(schema)]
    return sorted(found, key=lambda tag: (tag[0], tag[1] or ''))


def claude_forms(text, helpers):
    forms = _forms(text, helpers)
    found, fields, tops = {}, {}, []
    for key in ('messages', 'response_blocks', 'request_blocks'):
        at = forms[key][0].start()
        window = text[at - FORMS_WINDOW:at + FORMS_WINDOW]
        js = Js(window, helpers)
        tags = []
        for name in _union_members(window, FORMS_WINDOW, forms[key][0].group(0)):
            body, _ = js.definition(name, FORMS_WINDOW)
            tags += _tags(Reader(js, depth=1).parse(body)[0])
            if key == 'messages':
                schema = Reader(js, depth=6).parse(body)[0]
                for kind, sub in _tags(schema):
                    fields.setdefault(_tag(kind, sub), set()).update(_tool_paths(schema))
                tops += _tops(schema)
        found[key] = tags
    tagged = json.loads(text[text.index('[', forms['tagged'][0].start()):].split(']', 1)[0] + ']')
    found['messages'] = sorted({(kind, sub) for kind, sub in found['messages']}, key=lambda tag: (tag[0], tag[1] or ''))
    found['response_blocks'] = [kind for kind, _ in found['response_blocks']] + tagged
    found['request_blocks'] = [kind for kind, _ in found['request_blocks']] + tagged + ['mid_conv_system']
    head = 'streaming event ('
    at = text.index(head, forms['stream_events'][0].start()) + len(head)
    stream_events = text[at:text.index(')', at)].split(', ')
    at = forms['builtin_tools'][0].end() - 1
    builtin = json.loads(text[at:text.index(']', at) + 1])
    return {'messages': [[kind, sub] for kind, sub in found['messages']],
            'response_blocks': found['response_blocks'], 'request_blocks': found['request_blocks'],
            'stream_events': stream_events, 'builtin_tools': builtin,
            'builtin_renamed': _builtin_renamed(text, builtin, helpers),
            'tool_fields': {tag: sorted(paths) for tag, paths in sorted(fields.items()) if paths},
            'emitted_tool_fields': _emitted(text, helpers), 'frames': claude_frames(text, helpers),
            'task_counts': _task_counts(text, {tag: sorted(paths) for tag, paths in fields.items()}),
            'nested_work': _nested(text, _builtin_renamed(text, builtin, helpers), tops, helpers),
            'in_run': _in_run(text, _builtin_renamed(text, builtin, helpers), helpers),
            'source': "the SDK message union of the stream (each member's type and subtype), the content block "
                      "unions of an assistant and of a user message (the modelled blocks, then the type tags "
                      "the binary lists), the streaming events the stream_event schema names, and the binary's "
                      "BUILTIN_TOOL_NAMES (a partial list of its built-in tools: a name it omits reads as unknown)",
            'builtin_renamed_source': "a tool whose alias is on BUILTIN_TOOL_NAMES but whose current name is not: "
                                      "the Agent tool's definition (name, searchHint, aliases) with its names "
                                      "bound in the statement that binds its own description",
            'tool_fields_source': "each SDK message's fields whose name names a tool (a dotted path; an array's "
                                  "items share its path), from its zod schema",
            'emitted_tool_fields_source': "the fields a frame's emitters write that name a tool though its schema "
                                          "omits them: the REPL tool's repl_call on a tool_progress (both emitters) "
                                          "and a task_progress's workflow_progress entries (workflow_agent progress "
                                          "with lastToolName)",
            'frames_source': "the StdoutMessage members outside the SDK message union (everything the CLI writes "
                             "in stream-json mode), each with whether its schema provably carries no tool call: "
                             "only literals, enums, strings, numbers and booleans and no field naming a tool"}


# The emitters that build an event line from their own object literal and then add fields statement by statement,
# each by (event, the exact text its object starts with, the object's variable, the path of the object in the
# table's events). A zod schema says what a field may hold, not whether the emitter writes it: a field the emitter
# writes only under a condition (`...COND&&{field:...}`, `if(COND)VAR.field=...`, or a value ending in `??void 0`
# or `:void 0`, which JSON drops) is optional whatever the schema or the capture says. system/init writes
# messaging_socket_path only when the process bound its own cross-session inbox (`if(e.messagingSocketPath!==void 0)`,
# the path the inbox bound; start-up unsets any inherited CLAUDE_CODE_MESSAGING_SOCKET first): the capture's run bound
# one, and a worker whose inbox gate is off, which runs --bare, or whose bind fails prints none.
CLAUDE_EMITTERS = (
    ('system/init', 'g={type:"system",subtype:"init",cwd:e.cwd,', 'g', ('system/init',)),
    ('initialize', 'Pe={commands:Zq(<any>),agents:r.map((de)=>({name:de.agentType,', 'Pe',
     ('control_response', 'response', 'response')),
)


def _split_top(text, separator):
    """`text` split at `separator` outside brackets and string literals."""
    parts, depth, quote, start, i = [], 0, None, 0, 0
    while i < len(text):
        c = text[i]
        if quote:
            if c == '\\':
                i += 1
            elif c == quote:
                quote = None
        elif c in '"\'`':
            quote = c
        elif c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif depth == 0 and text.startswith(separator, i):
            parts.append(text[start:i])
            start = i + len(separator)
            i = start
            continue
        i += 1
    parts.append(text[start:])
    return parts


def _closing(text, at):
    """The index just past the bracket that closes the one at `at`."""
    depth, quote, i = 0, None, at
    while i < len(text):
        c = text[i]
        if quote:
            if c == '\\':
                i += 1
            elif c == quote:
                quote = None
        elif c in '"\'`':
            quote = c
        elif c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise Moved('unclosed bracket at %d' % at)


def _maybe_undefined(value):
    """The value itself when it may be `void 0` (a `??void 0` fallback or a `:void 0` branch), else None."""
    return value if re.search(r'(\?\?|:)void 0$', value) else None


def _literal_presence(body, found, condition=None):
    """Each key of an object literal's body: None when always written, else the condition it is written under."""
    for part in _split_top(body, ','):
        part = part.strip()
        if part.startswith('...'):
            spread = part[3:]
            guard = _split_top(spread, '&&')
            if len(guard) > 1 and guard[-1].startswith('{') and guard[-1].endswith('}'):
                inner = '&&'.join(guard[:-1])
                _literal_presence(guard[-1][1:-1], found, inner if condition is None else condition + '&&' + inner)
            continue
        m = re.match(r'([A-Za-z_$][A-Za-z0-9_$]*|"[^"]*"):', part)
        if not m:
            raise Moved('emitter literal: unreadable member %r' % part[:60])
        key, value = m.group(1).strip('"'), part[m.end():]
        found[key] = condition if condition is not None else _maybe_undefined(value)


def claude_emitters(text):
    """Which fields each emitter writes always and which only under a condition, read from its own text."""
    emitters = {}
    for event, source, name, path in CLAUDE_EMITTERS:
        head, names = site(text, source, '%s emitter' % event)
        variable = names[name]
        at = head.start() + len(variable) + 1
        end = _closing(text, at)
        found = {}
        _literal_presence(text[at + 1:end - 1], found)
        # The function returns its object, alone (`return g}`) or last in a comma sequence (`,Pe}`).
        stops = [s for s in (text.find('return %s}' % variable, end), text.find(',%s}' % variable, end)) if s >= 0]
        stop = min(stops) if stops else -1
        if stop < 0 or stop - end > 4000:
            raise Moved('%s emitter: no return of its object' % event)
        own = re.compile(re.escape(variable) + r'\.([A-Za-z_$][A-Za-z0-9_$]*)=(?!=)')
        for statement in _split_top(text[end:stop], ';'):
            statement = statement.strip()
            if statement.startswith('return '):
                statement = statement[len('return '):]
            body, guard = statement, None
            if statement.startswith('if('):
                close = _closing(statement, 2)
                guard, body = statement[3:close - 1], statement[close:]
                parts = _split_top(guard, ',')
                for part in parts[:-1]:
                    m = own.match(part.strip())
                    if m:
                        value = part.strip()[m.end():]
                        found[m.group(1)] = _maybe_undefined(value)
                guard = parts[-1]
            for part in _split_top(body, ','):
                m = own.match(part.strip())
                if m:
                    value = part.strip()[m.end():]
                    found[m.group(1)] = guard if guard is not None else _maybe_undefined(value)
        if not found:
            raise Moved('%s emitter: no fields read' % event)
        emitters[event] = {'anchor': head.group(0), 'offset': head.start(), 'path': list(path),
                           'always': sorted(k for k, v in found.items() if v is None),
                           'conditional': {k: v for k, v in sorted(found.items()) if v is not None}}
    return emitters


def claude(path):
    raw = Path(path).read_bytes()
    text = raw.decode('latin-1')
    _SITES.clear()
    helpers = zod_helpers(text)
    js = Js(text, helpers)
    events = {}
    for name, source in CLAUDE_EVENTS.items():
        m, _ = site(text, source, name, bound=helpers[2])
        schema, _ = Reader(js, depth=4).parse(m.start())
        events[name] = schema
    # The initialize success answer is a control response. Its generic payload is a record;
    # the account emitter (in the initialize emitter's object) names the optional fields absent from this
    # subscription capture.
    control_anchor = 'd({type:R("control_response"),response:Fe([_Y(),mY()])})'
    account_anchor = ('account:{email:ie?.email,organization:ie?.organization,subscriptionType:ie?.subscription,'
                      'tokenSource:ie?.tokenSource,apiKeySource:ie?.apiKeySource,apiProvider:He()}')
    emitters = claude_emitters(text)
    control_at, _ = site(text, control_anchor, 'initialize answer anchor', bound=helpers[2])
    start = emitters['initialize']['offset']
    accounts = [m for m in sites(text, account_anchor) if start < m.start() < start + 4000]
    if len(accounts) != 1:
        raise Moved('initialize answer anchor moved')
    found = accounts[0]
    ie, he = (anchor(account_anchor).name(found, n) for n in ('ie', 'He'))
    control, _ = Reader(js, depth=4).parse(control_at.start())
    success = control['fields']['response']['anyOf'][0]
    control['fields']['response'] = success
    account = {name: {'type': 'string', 'optional': expression.startswith(ie + '?.')}
               for name, expression in re.findall(r'(\w+):(%s\?\.\w+|%s\(\))' % (re.escape(ie), re.escape(he)),
                                                  found.group(0))}
    success['fields']['response'] = {'type': 'object', 'optional': True,
                                     'fields': {'account': {'type': 'object', 'fields': account}},
                                     'source': 'initialize success payload; account emitter in the binary',
                                     'anchor': found.group(0)}
    events['control_response'] = control
    tables = []
    for name, source, decision, reason in CLAUDE_TABLES:
        found = sites(text, source)
        if not found:
            raise Moved('credential table moved: ' + name)
        at = found[0].start()
        m = ENV_ARRAY.match(text, at)
        names = re.findall(r'"([A-Z0-9_]+)"', m.group(1))
        tail = text[m.end():m.end() + 80]
        if name == 'anthropic_secrets' and re.search(r'\.flatMap\(\(([\w$]+)\)=>\[\1,`INPUT_\$\{\1\}`\]\)', tail):
            names = names + ['INPUT_' + n for n in names]
        tables.append({'name': name, 'decision': decision, 'reason': reason, 'offset': at, 'names': names})
    bound = {}
    for name, source, decision, reason, exceptions in CLAUDE_LISTS:
        m, names_of = site(text, source, name, bound=uses(source, bound))
        own = JS_NAME.match(source.split('var ', 1)[-1]).group(0)
        bound[own] = names_of[own]
        at = m.start()
        names = list(dict.fromkeys(_js_list(js, at)))
        if len(names) < 2 or not all(re.fullmatch(r'[A-Z_][A-Z0-9_]*', n) for n in names):
            raise Moved('%s: not a list of variable names' % name)
        table = {'name': name, 'decision': decision, 'reason': reason, 'offset': at, 'names': names}
        if exceptions is not None:
            table['exceptions'] = exceptions(names)
        tables.append(table)
    endpoints = text.find('[{endpoint:"ANTHROPIC_BASE_URL"')
    if endpoints < 0:
        raise Moved('provider endpoint table moved')
    block = text[endpoints:text.index('}]', endpoints) + 2]
    tables.append({'name': 'provider_endpoints', 'decision': 'strip', 'offset': endpoints,
                   'reason': 'the base URLs that point Claude Code at another endpoint, with their selections and companions',
                   'names': sorted(set(re.findall(r'"([A-Z_][A-Z0-9_]+)"', block)))})
    notes = {}
    for name, start in (('result.usage', 'MAIN AGENT LOOP ONLY'), ('result.modelUsage', 'Per-model totals for every')):
        at = text.find(start)
        if at < 0:
            raise Moved('usage note moved: ' + name)
        note = text[at:text.index('"', at)]
        notes[name] = note.replace('\\u2014', '-').replace('\\u2013', '-')[:1000]
    version = Q.claude_version(path)
    return {'binary': str(Path(path).resolve()), 'version': version, 'sha256': _digest(path),
            'source': 'the zod schema of the SDK stream messages embedded in the binary (print mode, stream JSON)',
            'events': events, 'emitters': emitters, 'notes': notes, 'credential_tables': tables,
            'usage_limit': claude_limit(text),
            'tool_forms': claude_forms(text, helpers)}


# ---------------------------------------------------------------- Codex: the Rust binary's literals

# exec's literal run: the run of printable literals holding exec's event tags in their order (a build may place each
# tag after its variant's name, as one build did), up to exec's span name. Each name below must lie in it: the event
# tags, the event and usage field names (CODEX_EXEC_NAMES), and the MCP tool call's type, field and status names
# (VELDO-0160, CODEX_ITEM_NAMES).
CODEX_EXEC_TAGS = ('thread.started', 'turn.started', 'turn.completed', 'turn.failed', 'item.started', 'item.updated',
                   'item.completed', 'error')
CODEX_EXEC_END = b'codex.exec'
CODEX_EXEC_NAMES = ('thread_id', 'usage', 'in_progress', 'completed', 'failed', 'aggregated_output', 'exit_code',
                    'message', 'content_meta', 'structured_content', 'input_tokens', 'cached_input_tokens',
                    'cache_write_input_tokens', 'output_tokens', 'reasoning_output_tokens')
CODEX_ITEM_NAMES = ('mcp_tool_call', 'server', 'arguments', 'result', 'in_progress', 'completed', 'failed')


def codex_exec_run(raw):
    """(start, end) of exec's literal run."""
    tags = rb'(?:[A-Z][A-Za-z]*)?'.join(re.escape(tag.encode()) for tag in CODEX_EXEC_TAGS)
    found = list(re.finditer(tags, raw))
    if len(found) != 1:
        raise Moved('codex exec event literals moved')
    at = found[0].start()
    start = at
    while start > 0 and 0x20 <= raw[start - 1] < 0x7f:
        start -= 1
    end = raw.find(CODEX_EXEC_END, found[0].end())
    if end < 0 or any(not 0x20 <= byte < 0x7f for byte in raw[at:end]):
        raise Moved('codex exec event literals moved')
    return start, end + len(CODEX_EXEC_END)
# VELDO-0160: the item types, by the literal run that lists them. `exec`: exec's ThreadItem (what `codex
# exec --json` prints), whose `error` item tag is the literal at the head of its field run; `thread`: the
# core's ThreadItem, the types a thread records, of which exec prints only its own.
CODEX_EXEC_ITEMS = (b'item.completederroritems',
                    b'agent_messagereasoningcommand_executionfile_changemcp_tool_callweb_searchtodo_list',
                    ('agent_message', 'reasoning', 'command_execution', 'file_change', 'mcp_tool_call', 'web_search',
                     'todo_list'))
CODEX_THREAD_ITEMS = (b'user_messagefunction_call_outputhook_promptagent_messagereasoningcommand_executiondynamic_tool_call'
                      b'collab_agent_tool_callsub_agent_activityweb_searchimage_viewextensionentered_review_mode'
                      b'exited_review_modefile_changemcp_tool_callcontext_compaction',
                      ('user_message', 'function_call_output', 'hook_prompt', 'agent_message', 'reasoning',
                       'command_execution', 'dynamic_tool_call', 'collab_agent_tool_call', 'sub_agent_activity',
                       'web_search', 'image_view', 'extension', 'entered_review_mode', 'exited_review_mode',
                       'file_change', 'mcp_tool_call', 'context_compaction'))


# exec's own sub-agent call item, `collab_tool_call` (its agents' calls are not in exec's stream), whose tag is
# a literal placed after exec's event struct names rather than in the item run.
# Its tag is that literal beside exec's struct names when the build keeps them; a build that drops the names keeps the
# literal once in the binary, where the linker placed it.
CODEX_EXEC_COLLAB = (b'ItemUpdatedEventThreadErrorEventcollab_tool_call', 'collab_tool_call')
# VELDO-0160, the lead's structural rule: the items through which a Codex run does work in another agent's thread,
# whose calls its stream does not show, each by the struct literal naming the other thread: exec's own sub-agent
# call (above), the core's collab agent call (its receivers' thread ids) and its sub-agent activity (the agent's
# thread id).
CODEX_NESTED = {'collab': ((b'CollabAgentToolCallItemreceiver_thread_ids', 'collab_agent_tool_call'),),
                'sub_agent': ((b'SubAgentActivityItemagent_thread_id', 'sub_agent_activity'),)}


# VELDO-0160, the lead's allowlist (fail closed): exec's items are the run's own work (its messages, reasoning,
# to-do lists and errors, its shell commands, file changes and web searches, an MCP call the configuration judges,
# and its own sub-agent call), and a sub-agent call is in the run only for the collab tools exec's own CollabTool
# enum lists: its variant literals, placed between exec's usage field run and its item id field before its
# ThreadEvent name, each an agent thread of this process (`Spawn a sub-agent for a well-scoped task.`). A tag the
# run does not hold (a collab tool exec may name elsewhere) is not listed and asks.
CODEX_IN_RUN_COLLAB = (b'reasoning_output_tokensspawn_agentsend_inputclose_agent', ('spawn_agent', 'send_input', 'close_agent'))
CODEX_IN_RUN_SPAWN = b'Spawn a sub-agent for a well-scoped task.'
# The enum's `wait` variant is not in that run: the compiler keeps one copy of a short literal, and exec's `wait` is
# the one its other uses share. exec's serializer for the enum names every variant: a switch on the variant (lea rcx
# to its jump table, movsxd, add, jmp rax) whose cases each load one variant's literal (lea rdx) and its length (mov
# ecx, here or at the case it jumps to); a build that writes the JSON string inline opens it with its quote first, then
# loads the literal (lea rsi) and its length (mov edx). The wait variant only waits: the core's wait tool waits on agent ids from
# spawn_agent, or for a mailbox update from a live agent of the current root thread tree, the run's own agents.
CODEX_COLLAB_SWITCH = re.compile(rb'\x48\x8d\x0d(.{4})\x48\x63\x04\x81\x48\x01\xc8\xff\xe0', re.DOTALL)
CODEX_CASE_LOAD = re.compile(rb'(?:\x48\x8b\x1e\x48\x8b\x73\x10\x48\x39\x33\x0f\x84.{4}\x48\x8b\x43\x08'
                             rb'\xc6\x04\x30\x22\x48\xff\xc6\x48\x89\x73\x10)?\x48\x8d[\x15\x35].{4}', re.DOTALL)
CODEX_COLLAB_WAIT = (b'Agent ids to wait on. Pass multiple ids to wait for whichever finishes first.',
                     b'Live agents visible in the current root thread tree.')
CODEX_COLLAB_WAITS = ('wait',)


def _segments(raw):
    """[(file offset, virtual address, file size, executable)]: the ELF file's loadable segments."""
    if raw[:5] != b'\x7fELF\x02' or raw[5] != 1:
        raise Moved('codex is not a little-endian 64-bit ELF file')
    offset, size, count = (int.from_bytes(raw[0x20:0x28], 'little'), int.from_bytes(raw[0x36:0x38], 'little'),
                           int.from_bytes(raw[0x38:0x3a], 'little'))
    found = []
    for at in range(offset, offset + size * count, size):
        if int.from_bytes(raw[at:at + 4], 'little') == 1:
            flags = int.from_bytes(raw[at + 4:at + 8], 'little')
            found.append(tuple(int.from_bytes(raw[at + k:at + k + 8], 'little') for k in (8, 16, 32)) + (bool(flags & 1),))
    return found


def _file_offset(segments, address):
    for offset, virtual, size, _ in segments:
        if virtual <= address < virtual + size:
            return offset + address - virtual
    return None


def _rel32(raw, at):
    return int.from_bytes(raw[at:at + 4], 'little', signed=True)


def _switch_cases(raw, segments, at, virtual):
    """[(file offset, literal)]: the literals the switch at file offset `at` (virtual address `virtual`) loads, case by
    case, or None when it is not a switch whose every case loads a literal and its length."""
    table = virtual + 7 + _rel32(raw, at + 3)
    table_at, start = _file_offset(segments, table), virtual + 16
    if table_at is None:
        return None
    cases = []
    while len(cases) < 64:
        target = table + _rel32(raw, table_at + 4 * len(cases))
        case = _file_offset(segments, target)
        load = CODEX_CASE_LOAD.match(raw, case) if case is not None else None
        if not start <= target < start + 512 or load is None:
            break
        lea = load.end() - 7
        literal = target + (lea - case) + 7 + _rel32(raw, lea + 3)
        after = lea + 7
        if raw[after] == 0xeb:
            after = after + 2 + int.from_bytes(raw[after + 1:after + 2], 'little', signed=True)
        literal_at = _file_offset(segments, literal)
        if raw[after] not in (0xb9, 0xba) or literal_at is None:
            return None
        length = int.from_bytes(raw[after + 1:after + 5], 'little')
        text = raw[literal_at:literal_at + length]
        if not 0 < length <= 64 or not re.fullmatch(rb'[a-z_]+', text):
            return None
        cases.append((literal_at, text.decode()))
    return cases or None


def codex_collab_tools(raw, tools):
    """The variants of exec's CollabTool enum, read from its serializer: the one switch whose cases load the literals of
    the variant run itself (`tools`, at their places in the run; the core's own collab enum loads its own copies); the
    variants beyond the run are the waits the core's wait tool describes."""
    segments = _segments(raw)
    at = raw.find(CODEX_IN_RUN_COLLAB[0]) + len(b'reasoning_output_tokens')
    places = set()
    for tool in tools:
        places.add((at, tool))
        at += len(tool)
    found = []
    for offset, virtual, size, executable in segments:
        if not executable:
            continue
        for match in CODEX_COLLAB_SWITCH.finditer(raw, offset, offset + size):
            cases = _switch_cases(raw, segments, match.start(), virtual + match.start() - offset)
            if cases is not None and places <= set(cases):
                found.append([tool for _, tool in cases])
    if len(found) != 1 or len(set(found[0])) != len(found[0]) \
            or sorted(set(found[0]) - set(tools)) != sorted(CODEX_COLLAB_WAITS) \
            or any(raw.count(literal) != 1 for literal in CODEX_COLLAB_WAIT):
        raise Moved('codex collab tool serializer moved')
    return found[0]


def codex_in_run(raw, exec_items):
    run, tools = CODEX_IN_RUN_COLLAB
    start, end = codex_exec_run(raw)
    if raw.count(run) != 1 or ('reasoning_output_tokens' + ''.join(tools)).encode() != run \
            or not start <= raw.find(run) < end or CODEX_IN_RUN_SPAWN not in raw or 'collab_tool_call' not in exec_items:
        raise Moved('codex collab tools moved')
    return {'items': sorted(exec_items),
            'collab': {'item': 'collab_tool_call', 'field': 'tool', 'tools': codex_collab_tools(raw, tools)},
            'source': "exec's own items, each the run's own work (a shell command, a file change, a web search, an MCP "
                      "call the configuration judges, a message, reasoning, a to-do list, an error, its own sub-agent "
                      "call), and the collab tools of exec's CollabTool enum (read from its serializer, whose cases "
                      "load its variant literals: the run between its usage field run and its item id field, and "
                      "`wait`, whose literal the compiler shares), each an agent thread of this process or a wait on "
                      "one (the core's wait tool waits on agent ids from spawn_agent, or on a live agent of the "
                      "current root thread tree); an item or collab tool these do not list is not a known in-run kind"}


def codex_forms(raw):
    head, run, names = CODEX_EXEC_ITEMS
    if head not in raw or run not in raw or ''.join(names).encode() != run:
        raise Moved('codex exec item types moved')
    tag = CODEX_EXEC_COLLAB[1].encode()
    if not CODEX_EXEC_COLLAB[0].endswith(tag) or (raw.count(CODEX_EXEC_COLLAB[0]) != 1 and raw.count(tag) != 1):
        raise Moved('codex exec collab_tool_call moved')
    thread, thread_names = CODEX_THREAD_ITEMS
    if thread not in raw or ''.join(thread_names).encode() != thread:
        raise Moved('codex thread item types moved')
    nested = {'collab': [CODEX_EXEC_COLLAB[1]]}
    for construct, pieces in CODEX_NESTED.items():
        for literal, tag in pieces:
            if literal not in raw or tag not in thread_names:
                raise Moved('codex nested work %s moved' % tag)
            nested.setdefault(construct, []).append(tag)
    nested = {key: sorted(value) for key, value in sorted(nested.items())}
    nested['source'] = ("the items through which a run does work in another agent's thread: exec's own sub-agent call "
                        "(collab_tool_call) and the core's items whose struct names another thread (a collab agent "
                        "call's receiver_thread_ids, a sub-agent activity's agent_thread_id)")
    return {'exec_items': list(names) + [CODEX_EXEC_COLLAB[1], 'error'], 'thread_items': list(thread_names),
            'nested_work': nested, 'in_run': codex_in_run(raw, list(names) + [CODEX_EXEC_COLLAB[1], 'error']),
            'source': "exec's ThreadItem tags (its literal run, `collab_tool_call`, the literal after exec's "
                      "ItemUpdatedEvent and ThreadErrorEvent names, and `error`, the literal heading its field run) "
                      "and the core's ThreadItem tags (its literal run); a tag exec's table does not list reads as "
                      "unknown"}


# The usage-limit message, its apostrophe straight or typographic as the build writes it (one form per build).
CODEX_LIMIT_MESSAGE = re.compile(rb"You(?:'|\xe2\x80\x99)ve hit your usage limit")
CODEX_LIMIT = {
    'message': b"You've hit your usage limit",
    'retry_at': (b' Try again at ', b' or try again at '),
    'retry_later': (b' Try again later.', b' or try again later.'),
    'formats': (b'%-I:%M %p', b'%b %-d', b', %Y %-I:%M %p'),
    'suffixes': b'stndrdth',
}
# Each Codex credential table as (name, the literal before it, its packed names, the literal after it,
# decision, reason): the three pieces adjacent in the binary, or the packed names once in it.
CODEX_TABLES = [
    ('auth_env', b'auth.json', b'OPENAI_API_KEYCODEX_API_KEYCODEX_ACCESS_TOKEN', b'no Codex credentials were found',
     'strip', 'the auth variables Codex reads instead of its stored login'),
    ('agent_identity', b'managed MCP requirements do not permit the TUI task-tools server',
     b'CODEX_ACCESS_TOKENOPENAI_FEDERATION_RULE_IDOPENAI_IDENTITY_TOKEN_FILE', b'auth.json', 'strip',
     'the agent identity login'),
    ('bedrock_provider', b'AWS profile name must not be empty.',
     b'AWS_BEARER_TOKEN_BEDROCKAWS_ACCESS_KEY_IDAWS_SECRET_ACCESS_KEY', b'No AWS credentials found', 'keep',
     'the Bedrock provider credentials: AWS_BEARER_TOKEN_BEDROCK is stripped (a model key both CLIs name); the '
     'general AWS keys are the worker\'s tools\' own cloud login, and Codex selects Bedrock only through the '
     'model_provider of the owner-prepared profile'),
    ('exec_server_scrub', b'OPTIONSGETPUTDELETETRACECONNECTPATCH',
     b'OPENAI_FEDERATION_RULE_IDOPENAI_IDENTITY_TOKEN_FILEOPENAI_API_KEYCODEX_API_KEYCODEX_ACCESS_TOKEN'
     b'CODEX_CONNECTORS_TOKENAWS_ACCESS_KEY_IDAWS_SECRET_ACCESS_KEYAWS_SESSION_TOKENAZURE_CLIENT_SECRET'
     b'AZURE_FEDERATED_TOKEN_FILEGOOGLE_APPLICATION_CREDENTIALS', b'codex.exec_server.http_request', 'keep',
     'the secrets the exec server withholds from remote requests: its OpenAI and Codex names are stripped by prefix, '
     'the cloud names are tool credentials'),
    ('shell_env_scrub', b'*KEY**TOKEN*',
     b'CODEX_EXEC_SERVER_NOISE_AUTH_TOKENNODE_REPL_AUTH_TOKENOPENAI_FEDERATION_RULE_IDOPENAI_IDENTITY_TOKEN_FILE',
     b'non-metadata optional permissions', 'keep',
     'the default exclusions of Codex\'s shell environment policy for its tool children: its Codex and OpenAI names are '
     'stripped by prefix, NODE_REPL_AUTH_TOKEN is a tool\'s own'),
]
# The auth, endpoint and credential-redirect variables Codex reads, each by its literal neighbours (all
# `strip`: a login, a login endpoint, the model endpoint or a redirect of where the login or its state is
# read; each is also under the OPENAI_ or CODEX_ family, so the tables are what refuses them when an
# adapter configures one).
CODEX_TABLES += [
    ('agent_identity_endpoints', b'error', b'CODEX_AGENT_IDENTITY_AUTHAPI_BASE_URLCODEX_AGENT_IDENTITY_JWKS_BASE_URL',
     b'https://auth.openai.com/api/accounts', 'strip', 'the agent identity login endpoints'),
    ('auth_endpoint', b'agent identity registration attempt failed; retrying',
     b'CODEX_AGENT_IDENTITY_JWKS_BASE_URLCODEX_AUTHAPI_BASE_URL', b'https://auth.openai.com/api/accounts', 'strip',
     'the account login endpoint'),
    ('refresh_override', b'', b'CODEX_REFRESH_TOKEN_URL_OVERRIDE', b'login/src/auth/default_client.rs', 'strip',
     'the token refresh endpoint'),
    ('login_client', b'login/src/auth/default_client.rs', b'CODEX_APP_SERVER_LOGIN_CLIENT_ID',
     b'codex-mcp/src/binding_clients.rs', 'strip', 'the login client id'),
    ('login_issuer', b'ChatGPT login is disabled. Use API key login instead.', b'CODEX_APP_SERVER_LOGIN_ISSUER',
     b'Amazon Bedrock API key must not be empty.', 'strip', 'the login issuer'),
    ('revoke_override', b'token', b'CODEX_REVOKE_TOKEN_URL_OVERRIDE', b'https://auth.openai.com/oauth/revoke', 'strip',
     'the token revocation endpoint'),
    ('chatgpt_base', b'is_workspace_account', b'CODEX_APP_SERVER_CHATGPT_BASE_URL', b'/backend-api', 'strip',
     'the ChatGPT backend the subscription login talks to'),
    ('openai_base', b'GITHUB_ENTERPRISE_TOKEN', b'OPENAI_BASE_URL', b'sk-OPENAI_API_KEY', 'strip',
     'the model endpoint of the built-in OpenAI provider'),
    ('oss_provider', b'provider auth.command must not be empty', b'CODEX_OSS_PORTCODEX_OSS_BASE_URL', b'responses',
     'strip', 'the endpoint of the local model provider'),
    ('organization', b'OpenAI-Organization', b'OPENAI_ORGANIZATION', b'x-amzn-mantle-client-agent', 'strip',
     'the organization an API-key login bills'),
    ('sqlite_home', b'Environment value for `$', b'CODEX_SQLITE_HOME', b'` is overridden', 'strip',
     'where Codex keeps its thread state, a redirect of the profile beside CODEX_HOME'),
]

# Codex's error table: the text of every error its protocol Display prints (what `codex exec --json`
# puts in an `error` event and a failed turn), read from three places in the binary: the fixed messages,
# the format templates (length-prefixed pieces, 0xc0 marking an argument, 0x00 ending a template) and the
# workspace messages. Each message is classified: an exhaustion is a window the account's CLI reported
# exhausted (its id, and whether the message states its reset), anything else is not an allowance
# statement. A message this list does not classify fails the extraction by name.
# The fixed messages: the run from the first message below to the last, read message by message; text between two
# messages this list names is the build's own messages (split where a sentence ends and the next begins), and a
# message the build dropped is not in its table. The literals around the run (CODEX_ERROR_FIXED's first two) are
# what one build placed there.
CODEX_ERROR_FIXED = (b'LandlockRulesetLandlockPathFdTokioJoinEnvVar', b'request_id', (
    'turn aborted. Something went wrong? Hit `/feedback` to report the issue.',
    'shared rollout token budget exhausted',
    "Codex ran out of room in the model's context window. Start a new thread or clear earlier history before retrying.",
    'agent thread limit reached',
    'session configured event was not the first event in the stream',
    'timeout waiting for child process to exit',
    'request timed out',
    'spawn failed: child stdout/stderr not captured',
    'interrupted (Ctrl-C). Something went wrong? Hit `/feedback` to report the issue.',
    'Image poisoning',
    'Selected model is at capacity. Please try a different model.',
    'Quota exceeded. Check your plan and billing details.',
    'To use Codex with your ChatGPT plan, upgrade to Plus: https://chatgpt.com/explore/plus.',
    "We're currently experiencing high demand, which may cause temporary errors.",
    'internal error; agent loop died unexpectedly',
    'codex-linux-sandbox was required but not provided'))
CODEX_ERROR_TEMPLATES = (b'protocol/src/models.rs', b'\x00&sandbox denied exec error', b'\x00\x19invalid --profile value')
# The workspace messages, one run, followed by the usage-limit template that offers Pro (its length prefix the build's).
CODEX_ERROR_WORKSPACE = (b'<empty>', b"\x80\x96\x00You've hit your usage limit. Upgrade to Pro", (
    'Your workspace is out of credits. Add credits to continue.',
    'Your workspace is out of credits. Ask your workspace owner to refill in order to continue.',
    'You hit your spend cap set in your workspace. Increase your spend cap to continue.',
    'You hit your spend cap set by the owner of your workspace. Ask an owner to increase your spend cap to continue.'))
CODEX_ERROR_PRO = re.compile(rb"\x80..You(?:'|\xe2\x80\x99)ve hit your usage limit\. Upgrade to Pro", re.DOTALL)
CODEX_EXHAUSTION = {
    'Your workspace is out of credits. Add credits to continue.': 'workspace_credits',
    'Your workspace is out of credits. Ask your workspace owner to refill in order to continue.': 'workspace_credits',
    'You hit your spend cap set in your workspace. Increase your spend cap to continue.': 'workspace_spend_cap',
    'You hit your spend cap set by the owner of your workspace. Ask an owner to increase your spend cap to continue.':
        'workspace_spend_cap',
    'Quota exceeded. Check your plan and billing details.': 'quota',
    'To use Codex with your ChatGPT plan, upgrade to Plus: https://chatgpt.com/explore/plus.': 'plan',
}
# The messages that name a limit, a credit, a quota or a plan and are still not an allowance statement.
CODEX_NOT_EXHAUSTION = {
    'shared rollout token budget exhausted': "Codex's own budget for one rollout, a local setting, not the account's",
    'agent thread limit reached': "Codex's own cap on concurrent agent threads",
    'exceeded retry limit, last status: {}{}': 'a request that failed its retries; it states no allowance',
    'Selected model is at capacity. Please try a different model.': 'the service is busy; transient',
    'Policy-restricted capacity is unavailable. Please try again later.':
        'the service has no capacity for a policy-restricted request; transient',
    'Flex capacity unavailable.': 'the flex service tier has no capacity; transient',
}
ALLOWANCE_WORDS = re.compile(r'limit|credit|quota|spend|plan|billing|budget|capacity', re.I)


def _templates(block):
    """The format templates of a packed Display block: each a list of text pieces, None for an argument."""
    found, current, at = [], [], 0
    while at < len(block):
        byte = block[at]
        if byte == 0x00:
            found.append(current)
            current, at = [], at + 1
        elif byte == 0xc0:
            current.append(None)
            at += 1
        elif byte == 0x80:
            length = int.from_bytes(block[at + 1:at + 3], 'little')
            current.append(block[at + 3:at + 3 + length].decode())
            at += 3 + length
        elif byte < 0x80:
            current.append(block[at + 1:at + 1 + byte].decode())
            at += 1 + byte
        else:
            raise Moved('codex error templates: an unread byte %#x' % byte)
    if current:
        found.append(current)
    return [''.join('{}' if piece is None else piece for piece in template) for template in found if template]


def codex_limit_message(raw):
    """The usage-limit message as this build writes it."""
    forms = {m.group(0) for m in CODEX_LIMIT_MESSAGE.finditer(raw)}
    if len(forms) != 1:
        raise Moved('codex usage-limit literal moved: %r' % CODEX_LIMIT['message'])
    return forms.pop().decode()


def _classify(message, limit):
    if message.startswith(limit):
        return {'window': 'usage_limit', 'reset': 'stated or none (its retry phrase)'}
    if message in CODEX_EXHAUSTION:
        return {'window': CODEX_EXHAUSTION[message], 'reset': 'none: blocked until observed otherwise'}
    if message in CODEX_NOT_EXHAUSTION:
        return {'window': None, 'reason': CODEX_NOT_EXHAUSTION[message]}
    if ALLOWANCE_WORDS.search(message):
        raise Moved('codex error table: an unclassified message names an allowance: %r' % message)
    return {'window': None, 'reason': 'a local, request or transient error; it states no allowance'}


def _fixed(raw):
    """(offset, the fixed messages in the build's order)."""
    known = [m.encode() for m in CODEX_ERROR_FIXED[2]]
    if raw.count(known[0]) != 1:
        raise Moved('codex error table: the fixed messages moved')
    start = raw.index(known[0])
    end = raw.find(known[-1], start)
    if end < 0 or end - start > 8192:
        raise Moved('codex error table: the fixed messages moved')
    block, at, gap, found = raw[start:end + len(known[-1])], 0, b'', []

    def flush(gap):
        found.extend(re.split(r'(?<=[.!?])(?=[A-Z])', gap.decode()) if gap else [])
    while at < len(block):
        message = next((m for m in known if block.startswith(m, at)), None)
        if message is None:
            gap, at = gap + block[at:at + 1], at + 1
            continue
        flush(gap)
        gap, at = b'', at + len(message)
        found.append(message.decode())
    flush(gap)
    return start, found


def codex_errors(raw):
    entries = []
    limit = codex_limit_message(raw)
    start, messages = _fixed(raw)
    entries += [('fixed', m, start) for m in messages]
    anchor, start, end = CODEX_ERROR_TEMPLATES
    at = raw.find(anchor)
    first = raw.find(start, at)
    last = raw.find(end, first)
    if at < 0 or first < 0 or last < 0 or last - first > 4096:
        raise Moved('codex error table: the templates moved')
    entries += [('template', m, first) for m in _templates(raw[first + 1:last + 1])]
    _, _, messages = CODEX_ERROR_WORKSPACE
    run = ''.join(messages).encode()
    pro = CODEX_ERROR_PRO.match(raw, raw.find(run) + len(run))
    if raw.count(run) != 1 or pro is None:
        raise Moved('codex error table: the workspace messages moved')
    entries += [('workspace', m, raw.index(run)) for m in messages]
    pro = pro.start()
    entries += [('template', m, pro) for m in _templates(raw[pro:raw.index(b'\xc0\x00', pro) + 2])]
    table = []
    for source, message, offset in entries:
        table.append(dict({'message': message, 'source': source, 'offset': offset}, **_classify(message, limit)))
    if not any(e['window'] == 'usage_limit' for e in table) or len({e['message'] for e in table}) != len(table):
        raise Moved('codex error table: incomplete or repeated')
    return table


# What the binary says about where exec's turn usage comes from: the thread token usage it reports is a
# thread total and a last-turn figure; the strings do not say which one turn.completed copies. Exec's own source
# file (its JSON event processor, or exec's lib where a build folded it in), the notification, the app-server's
# ThreadTokenUsage and the core's TokenUsageInfo, whose fields are its literal run before its struct name (the
# known ones first and last, any other between) and last_token_usage (a literal the compiler shares).
CODEX_USAGE_SOURCE = (re.compile(rb'exec/src/(?:event_processor_with_jsonl_output|lib)\.rs'), b'thread/tokenUsage/updated',
                      b'totalmodelContextWindowstruct ThreadTokenUsage with 3 elements',
                      re.compile(rb'elements(total_token_usage[a-z_]*model_context_window)struct TokenUsageInfo with '
                                 rb'([0-9]+) elements'), b'last_token_usage')


def codex_usage_source(raw):
    """The core's TokenUsageInfo field names, each piece of the usage source checked."""
    info = None
    for piece in CODEX_USAGE_SOURCE:
        found = piece.search(raw) if hasattr(piece, 'search') else (piece if piece in raw else None)
        if found is None:
            raise Moved('codex usage source moved: %r' % getattr(piece, 'pattern', piece))
        info = found if piece is CODEX_USAGE_SOURCE[3] else info
    run = info.group(1).decode()
    middle = run[len('total_token_usage'):-len('model_context_window')]
    fields = ['total_token_usage', 'last_token_usage'] + ([middle] if middle else []) + ['model_context_window']
    if len(fields) != int(info.group(2)) or not re.fullmatch(r'[a-z_]*', middle):
        raise Moved('codex usage source moved: TokenUsageInfo')
    return fields


ENV_NAME_START = re.compile(rb'(?<=[A-Z0-9])(?=(?:OPENAI|CODEX|AWS|AZURE|GOOGLE|NODE)_)')


def _split(run):
    return [part.decode() for part in ENV_NAME_START.split(run) if part]


def codex(path):
    raw = Path(path).read_bytes()
    start, end = codex_exec_run(raw)
    for name in CODEX_EXEC_NAMES:
        if raw.find(name.encode(), start, end) < 0:
            raise Moved('codex exec event literals moved: ' + name)
    message = codex_limit_message(raw)
    for key, value in CODEX_LIMIT.items():
        for piece in (value if isinstance(value, tuple) else (value,)):
            if key != 'message' and piece not in raw:
                raise Moved('codex usage-limit literal moved: %r' % piece)
    limit = {'message': message,
             'retry_at': [p.decode() for p in CODEX_LIMIT['retry_at']],
             'retry_later': [p.decode() for p in CODEX_LIMIT['retry_later']],
             'formats': ['%-I:%M %p', '%b %-d{suffix}, %Y %-I:%M %p'],
             'suffixes': ['st', 'nd', 'rd', 'th'],
             'source': "protocol error Display: the message, then ' Try again at <local time>.' (same day: %-I:%M %p; "
                       "else %b %-d<suffix>, %Y %-I:%M %p) or ' Try again later.' with no reset"}
    for name in CODEX_ITEM_NAMES:
        if raw.find(name.encode(), start, end) < 0:
            raise Moved('codex exec item literals moved: ' + name)
    items = {'mcp_tool_call': {'type': 'object', 'fields': {
        'id': {'type': 'string'}, 'type': {'type': 'literal', 'value': 'mcp_tool_call'},
        'server': {'type': 'string'}, 'tool': {'type': 'string'}, 'arguments': {'type': 'any'},
        'result': {'type': 'any', 'optional': True, 'nullable': True},
        'error': {'type': 'any', 'optional': True, 'nullable': True},
        'status': {'type': 'enum', 'values': ['in_progress', 'completed', 'failed']}}}}
    usage_fields = codex_usage_source(raw)
    tables = []
    for name, before, run, after, decision, reason in CODEX_TABLES:
        # The run between its neighbours, or, where a build moved the neighbours, the run itself when it is once in
        # the binary.
        at = raw.find(before + run + after)
        if at < 0 and raw.count(run) == 1:
            at = raw.find(run) - len(before)
        if at < -len(before):
            raise Moved('codex credential table moved: ' + name)
        tables.append({'name': name, 'decision': decision, 'reason': reason, 'offset': at + len(before),
                       'names': _split(run)})
    usage = {name: {'type': 'number', 'int': True, 'optional': True}
             for name in ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens', 'output_tokens',
                          'reasoning_output_tokens')}
    error = {'type': 'object', 'fields': {'message': {'type': 'string'}}}
    events = {
        'thread.started': {'thread_id': {'type': 'string'}},
        'turn.started': {},
        'turn.completed': {'usage': {'type': 'object', 'fields': usage}},
        'turn.failed': {'error': error},
        'item.started': {'item': {'type': 'any'}},
        'item.updated': {'item': {'type': 'any'}},
        'item.completed': {'item': {'type': 'any'}},
        'error': {'message': {'type': 'string'}},
    }
    events = {name: {'type': 'object', 'fields': dict({'type': {'type': 'literal', 'value': name}}, **fields)}
              for name, fields in events.items()}
    package = Path(path).resolve()
    version = Q.codex_version(path)[0]
    return {'binary': str(package), 'version': version, 'sha256': _digest(path),
            'source': "the serde names of codex-exec's ThreadEvent (tag 'type') and its payload structs, packed in the "
                      "binary's literals; the strings show field names, not which are always present, so every usage "
                      "field is marked optional",
            'events': events, 'usage_limit': limit, 'errors': codex_errors(raw), 'credential_tables': tables,
            'items': items, 'tool_forms': codex_forms(raw),
            'items_source': ("exec's ThreadItem (the `item` of item.started, item.updated and item.completed, tag "
                             "`type`): the type names, the field names server, arguments and result, and the status "
                             "values in_progress, completed and failed are the binary's literal runs; `id`, `type` and "
                             "`tool` are names of four bytes or fewer, which the compiler places in code, not in the "
                             "literal pool, and `result` and `error` are present only when the call has one"),
            'notes': {'turn.completed.usage': (
                "exec's turn usage is read from the thread token usage its event processor receives "
                "(thread/tokenUsage/updated, a ThreadTokenUsage of total, last and modelContextWindow; the core's "
                "TokenUsageInfo of " + ', '.join(usage_fields[:-1]) + ' and ' + usage_fields[-1] + "): a thread total "
                "and a last-turn figure. The strings do not say which one turn.completed copies, so a resumed "
                "thread is never subtracted: the sum of the invocation's own completed turns never counts less "
                "than the CLI recorded under either reading")}}


CAPTURE = HERE.parent / 'VELDO-0172' / 'capture.json'


def event_name(line):
    kind = line.get('type')
    return kind + '/' + line['subtype'] if kind in ('system', 'result') else kind


def observe_schema(schema, samples, source, path='', changes=None):
    """Union the observed field universe with the binary schema, retaining its optional fields.

    Samples carry their original stream line numbers, including inside arrays and model records.
    Only types and paths enter the schema; scrubbed placeholders never become enum constants.
    """
    changes = [] if changes is None else changes
    if not schema:
        value = next((value for _, value in samples if value is not None), None)
        kind = ('object' if isinstance(value, dict) else 'array' if isinstance(value, list) else
                'boolean' if isinstance(value, bool) else 'number' if isinstance(value, (int, float)) else
                'string' if isinstance(value, str) else 'any')
        schema.update(type=kind, source=source, capture_lines=sorted({n for n, _ in samples}))
        changes.append({'field': path, 'change': 'known', 'lines': schema['capture_lines']})
        if kind == 'object':
            schema['fields'] = {}
        if kind == 'array':
            schema['items'] = {}
    if any(value is None for _, value in samples):
        schema['nullable'] = True
    kind = schema.get('type')
    objects = [(n, value) for n, value in samples if isinstance(value, dict)]
    if kind == 'object' and objects:
        fields = schema['fields']
        for key in sorted(set(fields) | {key for _, obj in objects for key in obj}):
            present = [(n, obj[key]) for n, obj in objects if key in obj]
            field = fields.setdefault(key, {})
            if present:
                observe_schema(field, present, source, path + '.' + key, changes)
            if len(present) < len(objects) and not field.get('optional'):
                field.update(optional=True, optional_source=source,
                             omitted_lines=sorted({n for n, obj in objects if key not in obj}))
                changes.append({'field': path + '.' + key, 'change': 'optional', 'lines': field['omitted_lines']})
    elif kind == 'record' and objects:
        observe_schema(schema['values'], [(n, v) for n, obj in objects for v in obj.values()],
                       source, path + '.*', changes)
    elif kind == 'array':
        entries = [(n, v) for n, array in samples if isinstance(array, list) for v in array]
        if entries:
            observe_schema(schema['items'], entries, source, path + '[]', changes)
    elif kind == 'any' and objects:
        # An open binary payload stays open for uncaptured variants; its observed fields are still known.
        observe_schema(schema.setdefault('observed', {}), objects, source, path, changes)
    return schema


def reconcile(table, capture_path=CAPTURE):
    capture = json.loads(Path(capture_path).read_text())
    changes = []
    for engine, key in (('claude', 'claude_code'), ('codex', 'codex')):
        events = table[key]['events']
        groups = {}
        for number, line in enumerate(capture['streams'][engine], 1):
            groups.setdefault(event_name(line), []).append((number, line))
        for event, samples in groups.items():
            source = 'proof/VELDO-0172/capture.json:streams.' + engine
            observe_schema(events.setdefault(event, {}), samples, source, event, changes)
    for number, line in enumerate(capture['streams']['codex'], 1):
        if isinstance(line.get('item'), dict):
            item = line['item']
            observe_schema(table['codex']['items'].setdefault(item['type'], {}), [(number, item)],
                           'proof/VELDO-0172/capture.json:streams.codex', 'item.' + item['type'], changes)
    # A field its emitter writes only under a condition is optional, though the capture's run met the condition.
    for event, emitter in sorted(table['claude_code'].get('emitters', {}).items()):
        node = table['claude_code']['events'][emitter['path'][0]]
        for step in emitter['path'][1:]:
            node = node['fields'][step]
        source = 'claude_code.emitters.' + event
        for key, condition in emitter['conditional'].items():
            field = node['fields'].get(key)
            if field is not None and not field.get('optional'):
                field.update(optional=True, optional_source=source, optional_condition=condition)
                changes.append({'field': '.'.join(emitter['path'] + [key]), 'change': 'optional', 'source': source})
    def field_counts(node):
        fields = list((node.get('fields') or {}).values())
        counts = {'known': len(fields), 'optional': sum(bool(f.get('optional')) for f in fields),
                  'from_capture': sum('capture_lines' in f for f in fields)}
        children = fields + [node[k] for k in ('items', 'values', 'observed') if isinstance(node.get(k), dict)]
        children += node.get('anyOf', [])
        for child in children:
            for key, count in field_counts(child).items():
                counts[key] += count
        return counts
    metrics = {section: {event: field_counts(schema) for event, schema in table[section]['events'].items()}
               for section in ('claude_code', 'codex')}
    table['capture'] = {'path': 'proof/VELDO-0172/capture.json', 'sha256': _digest(capture_path),
                        'recorded_run': '2026-09-26',
                        'versions': {key: table[key]['version'] for key in ('claude_code', 'codex')},
                        'changes': changes, 'metrics': metrics}
    return table


def extract(claude_path, codex_path):
    table = {'schema': 'veldo.cli-formats/v1', 'spec_id': 'VELDO-0062',
            'generated_by': 'proof/VELDO-0062/extract_formats.py (reads binary schemas and the allowlist-scrubbed live capture)',
            'claude_code': claude(claude_path), 'codex': codex(codex_path)}
    return reconcile(table)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--claude', default=str(DEFAULT_CLAUDE))
    parser.add_argument('--codex', default=str(DEFAULT_CODEX))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    table = extract(args.claude, args.codex)
    text = json.dumps(table, indent=1, sort_keys=True) + '\n'
    if args.check:
        same = OUT.is_file() and OUT.read_text() == text
        print('cli-formats.json %s the installed binaries' % ('matches' if same else 'DIFFERS FROM'))
        return 0 if same else 1
    OUT.write_text(text)
    print('wrote %s (%d bytes)' % (OUT.relative_to(HERE.parents[1]), len(text)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
