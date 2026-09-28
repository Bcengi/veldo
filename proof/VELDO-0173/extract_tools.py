#!/usr/bin/env python3
"""VELDO-0173: every tool a pinned Claude Code binary registers, read from its bytes, and the classification.

No binary is executed. The extractor reads the Bun standalone module graph in the ELF `.bun` section (each
embedded module's path and source, located by the graph's own table), finds the module that defines the
tool registry (`getAllBaseTools`, the one function every tool list of the binary starts from), and
resolves each item of the array that function returns to the tool definitions it names: a local binding,
an import from another module, a lazy `import.meta.require(<module>).<export>`, an array of tools, a
getter function, or a factory call whose object names the tool. A slot bound to `null` or to a getter
that returns `null` is compiled out of this build and registers nothing; it is recorded as such. A form
the extractor does not read is refused by name (Moved), so a new binary fails loudly, never silently short.

Each registered tool is recorded with its name, the module and the file offset of the name's string
literal (the bytes at that offset are the quoted name), the offset of its definition, the registry slot
that yields it, and the hint its definition carries (its searchHint, else its description, subject or
label), kept as the raw source text of that literal (escapes as written, never decoded).

The classification (VELDO-0173 AC1) reads VELDO-0160's in-run list, `claude_code.tool_forms.in_run.tools`
of proof/VELDO-0062/cli-formats.json: a registry tool on that list is in_run, every other registry tool
is outward, each with its reason, which quotes the tool's own definition. An in-run tool this build does
not register (REPL, whose registry slot is compiled out) keeps its in_run row, marked unregistered.

    python3 -B proof/VELDO-0173/extract_tools.py          # writes claude-tools.json beside this file
    python3 -B proof/VELDO-0173/extract_tools.py --check  # compares a fresh extraction with it
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

HERE = Path(__file__).resolve().parent
PINNED = ('2.1.281', Path('/home/dmitry/.local/share/claude/versions/2.1.281'))
FORMATS = HERE.parent / 'VELDO-0062' / 'cli-formats.json'
OUTPUT = HERE / 'claude-tools.json'
TRAILER = b'\n---- Bun! ----\n'
# The registry's own export: the object that names getAllBaseTools, getTools and assembleToolPool.
REGISTRY_ANCHOR = 'getAllBaseTools:'
# The REPL tool's getter in this build, and the test that makes it the REPL slot of the registry.
REPL_SLOT = 'function mr(){return null}'
REPL_USE = 'let _=mr();if(_!==null&&Qk()&&!r?.skipReplFilter)'
IDENT = r'[A-Za-z_$][\w$]*'
REQUIRE = re.compile(r'import\.meta\.require\("([^"]+)"\)\.(' + IDENT + r')$')
HINT_KEYS = ('searchHint', 'description', 'subject', 'label')


class Moved(Exception):
    """A form of this binary the extractor does not read."""


def modules(data):
    """{path: (file offset of its source, source)} for every module of the Bun standalone graph."""
    if data[:6] != b'\x7fELF\x02\x01':
        raise Moved('not a 64-bit little-endian ELF file')
    shoff = struct.unpack_from('<Q', data, 40)[0]
    size, count, names = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQ', data, shoff + n * size) for n in range(count)]
    table = headers[names][4]
    bun = [h for h in headers if data[table + h[0]:data.index(b'\0', table + h[0])] == b'.bun']
    if len(bun) != 1:
        raise Moved('no single .bun section')
    start, length = bun[0][4], bun[0][5]
    base = start + 8
    trailer = data.rfind(TRAILER, start, start + length)
    if trailer < 0:
        raise Moved('no Bun trailer in the .bun section')
    # Offsets: byte count (u64), modules (offset, length), entry point, exec argv (offset, length), flags.
    _, listed, span = struct.unpack_from('<QII', data, trailer - 32)
    if span % 52:
        raise Moved('the module table is not a whole number of 52-byte entries')
    found = {}
    for n in range(span // 52):
        fields = struct.unpack_from('<12I', data, base + listed + n * 52)
        path = data[base + fields[0]:base + fields[0] + fields[1]].decode()
        found[path] = (base + fields[2], data[base + fields[2]:base + fields[2] + fields[3]].decode('latin-1'))
    return found


def _regex_start(text, pos):
    back = pos - 1
    while back >= 0 and text[back] in ' \n\t':
        back -= 1
    if back < 0 or text[back] in '(,=:[!&|?{};+-*%<>~^':
        return True
    for word in ('return', 'typeof', 'case', 'in', 'of', 'void', 'delete', 'throw', 'else', 'do'):
        start = back - len(word) + 1
        if start >= 0 and text[start:back + 1] == word and (start == 0 or not re.match(r'[\w$]', text[start - 1])):
            return True
    return False


def _skip_quoted(text, pos):
    """The index just past the string or template literal starting at `pos`."""
    quote, end = text[pos], pos + 1
    while True:
        ch = text[end]
        if ch == '\\':
            end += 2
            continue
        if ch == quote:
            return end + 1
        if quote == '`' and text.startswith('${', end):
            end = closing(text, end + 1)
            continue
        end += 1


def _skip_regex(text, pos):
    end, klass = pos + 1, False
    while True:
        ch = text[end]
        if ch == '\\':
            end += 2
            continue
        if ch == '\n':
            raise Moved('an unterminated regular expression at %d' % pos)
        if klass:
            klass = ch != ']'
        elif ch == '[':
            klass = True
        elif ch == '/':
            break
        end += 1
    end += 1
    while end < len(text) and text[end].isalpha():
        end += 1
    return end


def closing(text, at):
    """The index just past the bracket that closes the one at `at`."""
    pairs = {'(': ')', '[': ']', '{': '}'}
    stack, pos = [pairs[text[at]]], at + 1
    while stack:
        ch = text[pos]
        if ch in '"\'`':
            pos = _skip_quoted(text, pos)
            continue
        if ch == '/' and text[pos + 1] not in '/*' and _regex_start(text, pos):
            pos = _skip_regex(text, pos)
            continue
        if ch in pairs:
            stack.append(pairs[ch])
        elif ch in ')]}':
            if ch != stack.pop():
                raise Moved('unbalanced brackets at %d' % pos)
        pos += 1
    return pos


def items(text, start, end):
    """[(start, end)] of the comma-separated top-level items of text[start:end], each trimmed."""
    found, pos, first = [], start, start
    while pos < end:
        ch = text[pos]
        if ch in '"\'`':
            pos = _skip_quoted(text, pos)
        elif ch in '([{':
            pos = closing(text, pos)
        elif ch == ',':
            found.append((first, pos))
            first = pos = pos + 1
        else:
            pos += 1
    found.append((first, end))
    trimmed = []
    for a, b in found:
        while a < b and text[a] in ' \n\t':
            a += 1
        while b > a and text[b - 1] in ' \n\t':
            b -= 1
        if a < b:
            trimmed.append((a, b))
    return trimmed


def _value_end(text, at):
    """The end of the binding value that starts at `at` (it ends at a top-level , ; or newline)."""
    pos = at
    while pos < len(text):
        ch = text[pos]
        if ch in '"\'`':
            pos = _skip_quoted(text, pos)
        elif ch in '([{':
            pos = closing(text, pos)
        elif ch in ',;\n)]}':
            break
        else:
            pos += 1
    return pos


class Graph:
    def __init__(self, data):
        self.modules = modules(data)
        self._imports, self._exports = {}, {}

    def text(self, path):
        if path not in self.modules:
            raise Moved('no module ' + path)
        return self.modules[path][1]

    def offset(self, path, at):
        return self.modules[path][0] + at

    def imports(self, path):
        if path not in self._imports:
            found = {}
            for m in re.finditer(r'import\{([^}]*)\}from"([^"]+)"', self.text(path)):
                for part in m.group(1).split(','):
                    bits = [b.strip() for b in part.split(' as ')]
                    found[bits[-1]] = (m.group(2), bits[0])
            self._imports[path] = found
        return self._imports[path]

    def exports(self, path):
        if path not in self._exports:
            found = list(re.finditer(r'export\{([^}]*)\};', self.text(path)))
            names = {}
            for part in (found[-1].group(1).split(',') if found else []):
                bits = [b.strip() for b in part.split(' as ')]
                names[bits[-1]] = bits[0]
            self._exports[path] = names
        return self._exports[path]

    def binding(self, path, name):
        """('value', start, end) or ('function', body start, body end): the one binding of `name`."""
        text = self.text(path)
        values = [m.end() for m in re.finditer(r'(?:var |let |const |[,;}\n])' + re.escape(name) + r'=(?![=>])', text)]
        functions = [m.end() for m in re.finditer(r'function ' + re.escape(name) + r'\([^)]*\)\{', text)]
        if len(values) + len(functions) != 1:
            raise Moved('%s: %d bindings of %s' % (path, len(values) + len(functions), name))
        if functions:
            body = functions[0] - 1
            return 'function', body, closing(text, body)
        return 'value', values[0], _value_end(text, values[0])


class Registry:
    def __init__(self, data):
        self.graph = Graph(data)
        self.compiled_out = []

    # -- names and hints -----------------------------------------------------------------------------
    def string(self, path, start, end, depth=0):
        """(value, file offset of its quoted literal) of the string expression text[start:end]."""
        if depth > 20:
            raise Moved('a name bound too deep')
        text = self.graph.text(path)
        expr = text[start:end]
        if re.fullmatch(r'"[^"\\]*"', expr):
            return expr[1:-1], self.graph.offset(path, start)
        if not re.fullmatch(IDENT, expr):
            raise Moved('%s: a tool name that is not a literal: %r' % (path, expr[:80]))
        imported = self.graph.imports(path).get(expr)
        if imported:
            target, name = imported
            local = self.graph.exports(target).get(name)
            if local is None:
                raise Moved('%s exports no %s' % (target, name))
            kind, a, b = self.graph.binding(target, local)
            if kind != 'value':
                raise Moved('a tool name bound to a function')
            return self.string(target, a, b, depth + 1)
        kind, a, b = self.graph.binding(path, expr)
        if kind != 'value':
            raise Moved('a tool name bound to a function')
        return self.string(path, a, b, depth + 1)

    def hint(self, path, keyed):
        """(key, raw literal text) of the first of HINT_KEYS the definition carries as a literal, else a
        description() whose function returns a literal."""
        text = self.graph.text(path)
        for key in HINT_KEYS:
            if key not in keyed:
                continue
            a, b = keyed[key]
            literal = text[a:b]
            if literal[:1] in '"`' and _skip_quoted(text, a) == b:
                return key, literal[1:-1][:240]
        for m in re.finditer(r'async description\(\)\{return (' + IDENT + r')\(\)\}', ''.join(
                text[a:b] for a, b in keyed.get('', []))):
            where, local = path, m.group(1)
            if local in self.graph.imports(path):
                where, name = self.graph.imports(path)[local]
                local = self.graph.exports(where).get(name, name)
            kind, a, b = self.graph.binding(where, local)
            body = self.graph.text(where)
            literal = re.match(r'\{return ?(["`])', body[a:b])
            if kind == 'function' and literal:
                at = a + literal.end() - 1
                return 'description()', body[at + 1:_skip_quoted(body, at) - 1][:240]
        return None, None

    def tool(self, path, start, end, slot):
        """The tool the object literal text[start:end] defines."""
        text = self.graph.text(path)
        keyed, plain, spreads = {}, [], []
        for a, b in items(text, start + 1, end - 1):
            m = re.match(r'(' + IDENT + r'):', text[a:b])
            if text.startswith('...', a):
                spreads.append((a + 3, b))
            elif m and not text.startswith('(', a + m.end()):
                keyed[m.group(1)] = (a + m.end(), b)
            else:
                plain.append((a, b))
        keyed[''] = plain
        if 'name' not in keyed:
            if len(spreads) != 1:
                raise Moved('%s: a tool definition without one name at %d' % (path, start))
            inner = self.value(path, spreads[0][0], spreads[0][1], slot, 0)
            if len(inner) != 1:
                raise Moved('%s: a spread tool definition of %d tools' % (path, len(inner)))
            key, hint = self.hint(path, keyed)
            found = dict(inner[0], definition_offset=self.graph.offset(path, start))
            if hint is not None:
                found.update(hint=hint, hint_source=key)
            return found
        name, at = self.string(path, *keyed['name'])
        key, hint = self.hint(path, keyed)
        return {'name': name, 'module': path, 'name_offset': at, 'definition_offset': self.graph.offset(path, start),
                'slot': slot, 'hint': hint, 'hint_source': key}

    # -- values ----------------------------------------------------------------------------------------
    def identifier(self, path, name, slot, depth):
        imported = self.graph.imports(path).get(name)
        if imported:
            return self.export(imported[0], imported[1], slot, depth + 1)
        kind, a, b = self.graph.binding(path, name)
        if kind == 'function':
            return self.body(path, a, b, slot, depth + 1, name)
        return self.value(path, a, b, slot, depth + 1, name)

    def export(self, path, name, slot, depth):
        local = self.graph.exports(path).get(name)
        if local is None:
            raise Moved('%s exports no %s' % (path, name))
        return self.identifier(path, local, slot, depth + 1)

    def body(self, path, a, b, slot, depth, name=None):
        """What a getter's body `{...return <value>}` returns."""
        text = self.graph.text(path)
        m = re.search(r'return ?([^;{}]+)\}$', text[a:b])
        if m is None:
            raise Moved('%s: an unread function body at %d' % (path, a))
        start = a + m.start(1)
        if text[start:b - 1].strip() == 'null':
            self.compiled_out.append({'slot': slot, 'binding': name, 'module': path, 'offset': self.graph.offset(path, a),
                                      'text': text[a:b][:120]})
            return []
        return self.value(path, start, b - 1, slot, depth + 1)

    def value(self, path, a, b, slot, depth, name=None):
        if depth > 80:
            raise Moved('a tool bound too deep')
        text = self.graph.text(path)
        expr = text[a:b]
        if expr == 'null':
            self.compiled_out.append({'slot': slot, 'binding': name, 'module': path, 'offset': self.graph.offset(path, a),
                                      'text': (name or '') + '=null'})
            return []
        m = REQUIRE.match(expr)
        if m:
            return self.export(m.group(1), m.group(2), slot, depth + 1)
        if expr.startswith('{') and closing(text, a) == b:
            return [self.tool(path, a, b, slot)]
        if expr.startswith('[') and closing(text, a) == b:
            found = []
            for x, y in items(text, a + 1, b - 1):
                found += self.value(path, x, y, slot, depth + 1)
            return found
        if expr.startswith('()=>{'):
            return self.body(path, a + 4, b, slot, depth + 1, name)
        if expr.startswith('()=>'):
            return self.value(path, a + 4, b, slot, depth + 1, name)
        if expr.startswith('(()=>(') and expr.endswith('))()') and closing(text, a + 5) == b - 3:
            # An immediately called arrow whose comma expression ends in the tool.
            last = items(text, a + 6, b - 4)[-1]
            return self.value(path, last[0], last[1], slot, depth + 1, name)
        if re.fullmatch(IDENT, expr):
            return self.identifier(path, expr, slot, depth + 1)
        m = re.fullmatch(r'(' + IDENT + r')\(\)', expr)
        if m:
            return self.identifier(path, m.group(1), slot, depth + 1)
        m = re.match(r'Object\.(?:defineProperties|getOwnPropertyDescriptors|assign)\(', expr)
        if m and closing(text, a + m.end() - 1) == b:
            # A copy of a tool object: the one tool among its arguments (an empty or keyed object adds none).
            found = []
            for x, y in items(text, a + m.end(), b - 1):
                if text[x:y] == '{}' or (text[x] == '{' and 'name' not in dict(
                        re.findall(r'(' + IDENT + r'):()', text[x:y]))):
                    continue
                found += self.value(path, x, y, slot, depth + 1)
            if len(found) != 1:
                raise Moved('%s: an object copy of %d tools' % (path, len(found)))
            return found
        m = re.match(r'(' + IDENT + r')\(', expr)
        if m and closing(text, a + m.end() - 1) == b and text[a + m.end():b - 1].strip():
            # A factory or wrapper call (buildTool and the like): the tool its first argument defines.
            first = items(text, a + m.end(), b - 1)[0]
            return self.value(path, first[0], first[1], slot, depth + 1)
        raise Moved('%s: an unread tool value at %d: %r' % (path, a, expr[:100]))

    # -- the registry array ----------------------------------------------------------------------------
    def element(self, path, a, b, local, depth=0, slot=None):
        """The tools one item of the registry array yields; `slot` is that item's text."""
        text = self.graph.text(path)
        slot = slot or text[a:b]
        if not text.startswith('...', a):
            if text[a:b] in local:
                return self.value(path, local[text[a:b]][0], local[text[a:b]][1], slot, 0, text[a:b])
            m = re.fullmatch(r'(' + IDENT + r')\(\)', text[a:b])
            if m and m.group(1) in local:
                raise Moved('a local getter call in the registry array')
            return self.value(path, a, b, slot, 0)
        a += 3
        body = text[a:b]
        if body == '[]':
            return []
        m = re.fullmatch(r'(.+?)\?(\[.*\]|' + IDENT + r'):\[\]', body, re.S)
        if m:
            # A gated slot: registered when its gate is on; the tools it yields are what the gate admits.
            chosen = a + m.start(2)
            end = a + m.end(2)
            if text[chosen] == '[':
                found = []
                for x, y in items(text, chosen + 1, end - 1):
                    found += self.element(path, x, y, local, depth + 1, slot)
                return found
            return self.element(path, chosen, end, local, depth + 1, slot)
        m = re.fullmatch(r'(\[.*\])\.filter\(.*\)', body, re.S)
        if m and closing(text, a) == a + m.end(1):
            found = []
            for x, y in items(text, a + 1, a + m.end(1) - 1):
                found += self.element(path, x, y, local, depth + 1, slot)
            return found
        m = re.fullmatch(r'\((' + IDENT + r')\?\.\(\)\?\?\[\]\)\.filter\(.*\)', body, re.S)
        if m:
            return self.value(path, a + m.start(1), a + m.end(1), slot, 0)
        m = re.fullmatch(IDENT + r'(?:\(\))?', body)
        if m:
            return self.element(path, a, b, local, depth + 1, slot)
        raise Moved('%s: an unread registry item: %r' % (path, slot[:100]))

    def read(self):
        homes = [p for p, (_, text) in self.graph.modules.items() if text.count(REGISTRY_ANCHOR) == 1
                 and re.search(r'\{' + REGISTRY_ANCHOR + '(' + IDENT + r'),getTools:', text)]
        if len(homes) != 1:
            raise Moved('%d modules define the tool registry' % len(homes))
        path = homes[0]
        text = self.graph.text(path)
        function = re.search(r'\{' + REGISTRY_ANCHOR + '(' + IDENT + r'),getTools:', text).group(1)
        start = text.index('function %s(){' % function)
        head = re.match(r'function ' + re.escape(function) + r'\(\)\{(?:let (.*?);)?return\[', text[start:], re.S)
        if head is None:
            raise Moved('the registry function does not return an array literal')
        local = {}
        if head.group(1):
            first = start + head.start(1)
            for x, y in items(text, first, start + head.end(1)):
                name, _, _ = text[x:y].partition('=')
                local[name] = (x + len(name) + 1, y)
        array = start + head.end() - 1
        end = closing(text, array)
        tools = []
        for x, y in items(text, array + 1, end - 1):
            tools += self.element(path, x, y, local)
        names = [t['name'] for t in tools]
        if len(set(names)) != len(names):
            raise Moved('a tool registered twice')
        return {'module': path, 'function': function, 'offset': self.graph.offset(path, start),
                'slots': len(items(text, array + 1, end - 1))}, tools


def classify(tools, in_run, unregistered):
    """{name: {class, reason}} for every registry tool and every in-run tool this build does not register."""
    rows = {}
    for tool in tools:
        said = ("its definition: %s %r" % (tool['hint_source'], tool['hint']) if tool.get('hint') is not None
                else 'its definition carries no literal hint')
        if tool['name'] in in_run:
            rows[tool['name']] = {'class': 'in_run', 'reason': "on VELDO-0160's in-run list; " + said}
        else:
            rows[tool['name']] = {'class': 'outward', 'reason': "not on VELDO-0160's in-run list; " + said}
    for name in sorted(set(in_run) - set(rows)):
        slot = unregistered.get(name)
        rows[name] = {'class': 'in_run', 'registered': False,
                      'reason': "on VELDO-0160's in-run list; this build registers no %s tool: %s" % (
                          name, 'its registry slot is compiled out (%s)' % slot if slot else 'not in the registry')}
    return rows


def extract(path=PINNED[1], formats=FORMATS):
    data = Path(path).read_bytes()
    registry = Registry(data)
    source, tools = registry.read()
    in_run = json.loads(Path(formats).read_text())['claude_code']['tool_forms']['in_run']['tools']
    home = registry.graph.text(source['module'])
    unregistered = {}
    if home.count(REPL_SLOT) == 1 and home.count(REPL_USE) == 1 and 'REPL' not in {t['name'] for t in tools}:
        unregistered['REPL'] = REPL_SLOT
    classification = classify(tools, in_run, unregistered)
    return {
        'schema': 'veldo.proof-tools/v1', 'spec_id': 'VELDO-0173', 'engine': 'claude_code', 'version': PINNED[0],
        'sha256': 'sha256:' + hashlib.sha256(data).hexdigest(),
        'method': ('the Bun standalone module graph of the .bun section; the array getAllBaseTools returns, each item '
                   'resolved through local bindings, imports, lazy requires, arrays, getters and factory calls to the '
                   'object that names the tool; hints are the raw literal text of the definition'),
        'registry_source': dict(source, anchor=REGISTRY_ANCHOR + source['function']),
        'registry': tools,
        'compiled_out': registry.compiled_out,
        'unregistered_in_run': {n: {'slot': s, 'offset': registry.graph.offset(source['module'], home.index(s)),
                                    'use': REPL_USE} for n, s in unregistered.items()},
        'in_run_source': 'proof/VELDO-0062/cli-formats.json claude_code.tool_forms.in_run.tools',
        'in_run': list(in_run),
        # What the qualification record carries (VELDO-0173 AC2), exactly.
        'tool_registry': sorted(t['name'] for t in tools),
        'tool_classification': classification,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--claude', type=Path, default=PINNED[1])
    args = parser.parse_args()
    record = extract(args.claude)
    text = json.dumps(record, indent=1, sort_keys=True) + '\n'
    if args.check:
        assert OUTPUT.read_text() == text, 'the tool inventory changed'
    else:
        OUTPUT.write_text(text)
    print(len(record['registry']), 'registered tools,', len(record['compiled_out']), 'compiled-out slots,',
          record['sha256'])


if __name__ == '__main__':
    main()
