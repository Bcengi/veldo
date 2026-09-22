"""The repository's strict, standard-library document reader.

This is a deliberately limited YAML dialect, not a general YAML implementation.
Mappings have identifier/path or quoted keys; sequences, nested flow collections, quoted strings,
and space-indented plain continuations are supported. Plain scalars retain their
spelling except canonical decimal integers (0 or -?[1-9][0-9]*). Boolean words are
strings: each schema owns boolean interpretation. Leading-zero identifiers stay
strings. Empty values are None. Comments begin at # preceded by whitespace.

Quotes must close on their line; double quotes use YAML escapes, single quotes
use doubled apostrophes. Literal/folded blocks support |, > and +/- chomping.
Tags, anchors, aliases, merge keys, directives, multiple documents, multiline
quotes and indentation indicators are refused. A mapping-looking continuation
under a scalar is refused, never folded into text or mistaken for an absent key.
All failures are ValueError with a source and physical line number.
"""
import re
from pathlib import Path

_KEY = re.compile(r'([A-Za-z_.][A-Za-z0-9_./-]*)[ \t]*:(?:[ \t]+|$)(.*)')
_FLOW_KEY = re.compile(r'([A-Za-z_.][A-Za-z0-9_./-]*)[ \t]*:')
_INT = re.compile(r'(?:0|-?[1-9][0-9]*)\Z')
_ESCAPES = dict(zip('0abtnvfre', '\0\a\b\t\n\v\f\r\x1b'))
_ESCAPES.update({' ': ' ', '"': '"', '/': '/', '\\': '\\',
                 'N': '\x85', '_': '\xa0', 'L': '\u2028', 'P': '\u2029'})


class ParseError(ValueError):
    pass


class _Flow:
    def __init__(self, text, error):
        self.text, self.i, self.error = text, 0, error

    def space(self):
        while self.i < len(self.text) and self.text[self.i] in ' \t':
            self.i += 1

    def value(self, flow=False):
        self.space()
        s, n = self.text, len(self.text)
        if self.i == n or s[self.i] == '#':
            return None
        ch = s[self.i]
        if ch in '\"\'':
            return self.quoted()
        if ch in '[{':
            return self.collection(ch)
        if ch in '&*!|>@`%]}':
            self.error('unsupported scalar syntax; quote literal text')
        start = self.i
        while self.i < n:
            ch = s[self.i]
            if ch == '#' and (self.i == start or s[self.i - 1] in ' \t'):
                break
            if flow and ch in ',]}':
                break
            if flow and ch in '[{':
                self.error('flow punctuation in plain scalar; quote literal text')
            self.i += 1
        word = s[start:self.i].strip(' \t')
        if not word:
            self.error('missing flow value')
        if re.search(r':(?:[ \t]|$)', word):
            self.error('colon in plain scalar; quote literal text')
        return int(word) if _INT.fullmatch(word) else word

    def quoted(self):
        s, quote = self.text, self.text[self.i]
        self.i += 1
        out = []
        while self.i < len(s):
            ch = s[self.i]
            self.i += 1
            if ch == quote:
                if quote == "'" and s[self.i:self.i + 1] == "'":
                    out.append("'")
                    self.i += 1
                    continue
                return ''.join(out)
            if ch == '\\' and quote == '"':
                esc = s[self.i:self.i + 1]
                self.i += 1
                if esc in _ESCAPES:
                    out.append(_ESCAPES[esc])
                    continue
                width = {'x': 2, 'u': 4, 'U': 8}.get(esc, 0)
                digits = s[self.i:self.i + width]
                if width and len(digits) == width and re.fullmatch('[0-9a-fA-F]+', digits):
                    code = int(digits, 16)
                    if code <= 0x10ffff and not 0xd800 <= code <= 0xdfff:
                        out.append(chr(code))
                        self.i += width
                        continue
                self.error('invalid quoted escape')
            out.append(ch)
        self.error('quoted value is not closed on its line')

    def collection(self, opener):
        closer = ']' if opener == '[' else '}'
        out = [] if opener == '[' else {}
        self.i += 1
        self.space()
        if self.text[self.i:self.i + 1] == closer:
            self.i += 1
            return out
        while self.i < len(self.text):
            if opener == '{':
                if self.text[self.i:self.i + 1] in ('"', "'"):
                    key = self.quoted()
                    self.space()
                    if self.text[self.i:self.i + 1] != ':':
                        self.error('expected colon after quoted key')
                    self.i += 1
                else:
                    m = _FLOW_KEY.match(self.text, self.i)
                    if not m:
                        self.error('expected identifier key in flow mapping')
                    key = m[1]
                    self.i = m.end()
                if key in out:
                    self.error('duplicate key ' + repr(key))
                out[key] = self.value(True)
            else:
                out.append(self.value(True))
            self.space()
            ch = self.text[self.i:self.i + 1]
            if ch == closer:
                self.i += 1
                return out
            if ch != ',':
                self.error('unclosed collection or missing comma')
            self.i += 1
            self.space()
            if self.text[self.i:self.i + 1] == closer:
                self.i += 1
                return out
        self.error('unclosed collection')

    def finish(self):
        value = self.value()
        self.space()
        if self.i < len(self.text):
            if self.text[self.i] != '#' or self.i == 0 or self.text[self.i - 1] not in ' \t':
                self.error('text after value')
        return value


class _Document:
    def __init__(self, text, source):
        self.lines = re.split(r'\r\n|\r|\n', text.removeprefix('\ufeff'))
        self.source = source
        self.i = 0
        for n, line in enumerate(self.lines):
            indent = line[:len(line) - len(line.lstrip(' \t'))]
            if '\t' in indent:
                self.error(n, 'tab indentation')

    def error(self, n, message):
        raise ParseError(f'{self.source}:{n + 1}: {message}')

    def skip(self):
        while self.i < len(self.lines) and (not self.lines[self.i].strip(' \t')
                                           or self.lines[self.i].lstrip(' ').startswith('#')):
            self.i += 1

    def indent(self):
        line = self.lines[self.i]
        return len(line) - len(line.lstrip(' '))

    def scalar(self, text, n):
        return _Flow(text, lambda msg: self.error(n, msg)).finish()

    def value(self, rest, parent, n):
        rest = rest.strip(' \t')
        if re.fullmatch(r'[|>][+-]?(?:[ \t]+#.*)?', rest):
            return self.block_scalar(rest[:2].strip(), parent)
        if not rest or rest.startswith('#'):
            self.skip()
            if self.i < len(self.lines) and self.indent() > parent:
                return self.block(self.indent())
            return None
        # Flow collections may wrap at whitespace, but quotes must close per line.
        if rest.startswith(('[', '{')):
            while True:
                try:
                    return self.scalar(rest, n)
                except ParseError as exc:
                    if 'unclosed collection' not in str(exc):
                        raise
                    self.skip()
                    if self.i >= len(self.lines) or self.indent() <= parent:
                        raise
                    rest += ' ' + self.lines[self.i].strip(' ')
                    self.i += 1
        value = self.scalar(rest, n)
        quoted = rest.startswith(('"', "'"))
        gap_start = self.i
        self.skip()
        continuation_indent = None
        while self.i < len(self.lines) and self.indent() > parent:
            at, text = self.i, self.lines[self.i].strip(' ')
            if quoted or not isinstance(value, str) or _KEY.fullmatch(text) or text.startswith('- '):
                self.error(at, 'unexpected structure under scalar; quote or use a block scalar')
            if continuation_indent is None:
                continuation_indent = self.indent()
            if self.indent() != continuation_indent:
                self.error(at, 'inconsistent scalar continuation indentation')
            part = self.scalar(text, at)
            if not isinstance(part, str):
                self.error(at, 'non-text scalar continuation')
            blanks = sum(not line.strip(' \t') for line in self.lines[gap_start:self.i])
            value += ('\n' * blanks if blanks else ' ') + part
            self.i += 1
            gap_start = self.i
            self.skip()
        return value

    def block_scalar(self, indicator, parent):
        lines, ind = [], None
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            if raw.strip(' ') and self.indent() <= parent:
                break
            if raw.strip(' '):
                if ind is None:
                    ind = self.indent()
                if self.indent() < ind:
                    self.error(self.i, 'inconsistent block scalar indentation')
                lines.append(raw[ind:])
            else:
                lines.append('')
            self.i += 1
        # split() leaves a sentinel after a final newline; it is not a second newline.
        if self.i == len(self.lines) and lines and self.lines[-1] == '':
            lines.pop()
        value = ''
        for i, line in enumerate(lines):
            value += line
            nxt = lines[i + 1] if i + 1 < len(lines) else None
            if indicator.startswith('>') and line and nxt and not line.startswith(' ') and not nxt.startswith(' '):
                value += ' '
            elif indicator.startswith('>') and not line and nxt and i > 0 and lines[i - 1] and not lines[i - 1].startswith(' '):
                pass  # the preceding break already represents this blank line
            else:
                value += '\n'
        if indicator.endswith('-'):
            return value.rstrip('\n')
        if indicator.endswith('+'):
            return value
        return value.rstrip('\n') + ('\n' if lines else '')

    def member(self, text, n):
        if text.startswith(('"', "'")):
            reader = _Flow(text, lambda msg: self.error(n, msg))
            key = reader.quoted()
            reader.space()
            rest = text[reader.i:]
            if rest == ':' or rest.startswith((': ', ':\t')):
                return key, rest[1:]
            return None
        match = _KEY.fullmatch(text)
        return match.groups() if match else None

    def block(self, indent):
        self.skip()
        is_list = self.lines[self.i][indent:] == '-' or self.lines[self.i][indent:].startswith('- ')
        out = [] if is_list else {}
        while self.i < len(self.lines):
            self.skip()
            if self.i == len(self.lines) or self.indent() < indent:
                break
            if self.indent() != indent:
                self.error(self.i, 'unexpected indentation')
            n, text = self.i, self.lines[self.i][indent:]
            self.i += 1
            if is_list:
                if not (text == '-' or text.startswith('- ')):
                    self.error(n, 'mixed mapping and sequence')
                body = text[2:] if text != '-' else ''
                if self.member(body, n):
                    # Treat the first member exactly like every subsequent map member.
                    self.lines[n] = ' ' * (indent + 2) + body
                    self.i = n
                    out.append(self.block(indent + 2))
                else:
                    out.append(self.value(body, indent, n))
            else:
                m = self.member(text, n)
                if not m:
                    self.error(n, 'expected identifier key: value')
                key, rest = m
                if key in out:
                    self.error(n, 'duplicate key ' + repr(key))
                out[key] = self.value(rest, indent, n)
        return out


def parse(src, source='<text>'):
    """Parse one complete mapping or sequence; never ignore unrecognized content."""
    doc = _Document(src, source)
    doc.skip()
    if doc.i == len(doc.lines):
        return {}
    try:
        value = doc.block(doc.indent())
    except RecursionError:
        doc.error(doc.i, 'document nesting exceeds reader limit')
    doc.skip()
    if doc.i != len(doc.lines):
        doc.error(doc.i, 'unparsed trailing content')
    return value


def read(path):
    """Read UTF-8 (optional BOM); absence and IO failures are the caller's decision."""
    try:
        return parse(Path(path).read_bytes().decode('utf-8-sig'), str(path))
    except UnicodeDecodeError as exc:
        raise ParseError(f'{path}: invalid UTF-8: {exc}') from exc


def front_matter_match(text):
    """Locate a complete front-matter region for readers and source-preserving writers.

    group(1) is the metadata source; start/end allow an existing writer to edit
    that region without rewriting the prose body. Unclosed fences always refuse.
    """
    if not re.match(r"\A\ufeff?---(?:\r\n|\r|\n|$)", text):
        return None
    match = re.match(r"\A\ufeff?---(?:\r\n|\r|\n)(.*?)(?:\r\n|\r|\n)---(?=\r\n|\r|\n|$)", text, re.S)
    if match is None:
        raise ParseError("<text>:1: unclosed front matter")
    return match


def front_matter(text, source='<text>'):
    """Return a mapping, None only for no opening fence, or refuse malformed metadata."""
    match = front_matter_match(text)
    if match is None:
        return None
    value = parse('\n' + match.group(1), source)
    if not isinstance(value, dict):
        raise ParseError(f'{source}:2: front matter must be a mapping')
    return value


def quote(value):
    """Encode a scalar for repository writers, quoting whenever plain spelling is unsafe."""
    import json
    if not isinstance(value, str):
        return json.dumps(value)
    try:
        if '\n' not in value and '\r' not in value and parse('value: ' + value) == {'value': value}:
            return value
    except ValueError:
        pass
    return json.dumps(value, ensure_ascii=True)
