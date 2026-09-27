#!/usr/bin/env python3
"""Read pinned ELF bytes only. Retain identifier candidates and their byte offsets.

The inventory deliberately over-approximates environment names: uppercase identifiers in
embedded source and strings outside the executable sections, plus ELF string slices (Rust
literals can abut without a delimiter). Candidates are not a claim that every identifier is
read as an environment variable. No binary is executed. The MCP naming expression is kept
separately as an exact byte anchor.

Session names are the names in the stripped families, read the way an outside scan reads them:
every printable run of six or more bytes outside the executable sections (what `strings -a -n 6`
prints, without machine code immediates), each uppercase identifier in it cut where a prefix
starts a new literal (a prefix that does not follow an underscore), keeping every piece that starts
with a prefix and does not end in an underscore (a template stem the prefix already covers).
Rust literals that abut an uppercase literal or a 16-byte comparison chunk stay joined or cut as
the bytes hold them; the prefixes, not this list, decide the strip.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

HERE = Path(__file__).resolve().parent
PREFIXES = ('CLAUDE', 'CLAUDECODE', 'AI_AGENT', 'CODEX')
PINNED = {
    'claude': ('2.1.281', Path('/home/dmitry/.local/share/claude/versions/2.1.281')),
    'codex': ('0.154.0', Path('/home/dmitry/.nvm/versions/node/v22.22.0/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex')),
}
NAME = rb'[A-Z][A-Z0-9_]{2,127}'
FAMILY = rb'CLAUDE|AI_AGENT|CODEX'
# A prefix that does not follow an underscore starts a new literal: Rust abuts literals.
CUT = re.compile(rb'(?<!_)(?=' + FAMILY + rb')')
SHAPE = re.compile(rb'(?:' + FAMILY + rb')(?:[A-Z0-9_]*[A-Z0-9])?')
PRINTABLE = b'\t' + bytes(range(0x20, 0x7f))
NONPRINTABLE = re.compile(rb'[^\t\x20-\x7e]')
UPPER = b'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_'


def sections(data):
    """ELF64 section headers as (name offset, type, flags, address, offset, size); none for other files."""
    if data[:6] != b'\x7fELF\x02\x01':
        return []
    shoff = struct.unpack_from('<Q', data, 40)[0]
    size, count = struct.unpack_from('<HH', data, 58)
    return [struct.unpack_from('<IIQQQQIIQQ', data, shoff + n * size)[:6] for n in range(count)]


def code_ranges(data):
    """File byte ranges of executable sections (SHF_EXECINSTR with file contents)."""
    return [(s[4], s[4] + s[5]) for s in sections(data) if s[2] & 4 and s[1] != 8]


def session_names(data):
    """Every session-family name, cut as the module docstring states, from printable runs outside code."""
    code = code_ranges(data)
    found, seen = set(), set()
    first = last = 0
    keep = False
    for hit in re.finditer(FAMILY, data):
        if hit.start() >= last:
            # The printable run holding this hit: hits ascend, so each run is measured once.
            first = last + len(data[last:hit.start()].rstrip(PRINTABLE))
            after = NONPRINTABLE.search(data, hit.end())
            last = after.start() if after else len(data)
            keep = last - first >= 6 and not any(a <= first < b for a, b in code)
        if not keep:
            continue
        start, end = hit.start(), hit.end()
        while start > first and data[start - 1] in UPPER:
            start -= 1
        if start in seen:
            continue
        seen.add(start)
        while end < last and data[end] in UPPER:
            end += 1
        for piece in CUT.split(data[start:end]):
            if SHAPE.fullmatch(piece):
                found.add(piece.decode('ascii'))
    return sorted(found)


def parent_environment(engine, data, names):
    """Locate the binary's child-environment structure by content, never by byte offset."""
    if engine == 'claude':
        arrays = list(re.finditer(rb'var [A-Za-z_$][A-Za-z0-9_$]*=\[(?:"[A-Za-z_][A-Za-z0-9_]*",)+\.\.\.\[\]\];', data))
        arrays = [m for m in arrays if b'"GIT_EDITOR"' in m.group() and b'"TRACEPARENT"' in m.group()]
        assert len(arrays) == 1, 'child environment list missing or ambiguous'
        child = arrays[0]
        assert b'spawnEnvKeys()' in data[child.end():child.end() + 1000], 'child environment consumer missing'
        assignments = list(re.finditer(
            rb'process\.env\.[A-Za-z_][A-Za-z0-9_]*="[^"]*";(?:process\.env\.[A-Za-z_][A-Za-z0-9_]*="[^"]*";)+', data))
        assignments = [m for m in assignments if b'COREPACK_ENABLE_AUTO_PIN' in m.group()]
        assert len(assignments) == 1, 'startup child assignments missing or ambiguous'
        startup = assignments[0]
        children = re.findall(rb'"([A-Za-z_][A-Za-z0-9_]*)"', child.group())
        every_child = re.findall(rb'process\.env\.([A-Za-z_][A-Za-z0-9_]*)=', startup.group())
        # A default the binary writes into its own environment when unset, which every later child inherits
        # (the OpenTelemetry metrics temporality, "delta").
        defaults = list(re.finditer(
            rb'!(?:[A-Za-z_$][A-Za-z0-9_$]*)\.([A-Za-z_][A-Za-z0-9_]*)\)process\.env\.\1="[^"]*"', data))
        assert defaults, 'default child assignments missing'
        parent_names = sorted({n.decode() for n in children + every_child + [m[1] for m in defaults]})
        structures = [{'offset': m.start(), 'text': m.group().decode()} for m in [child, startup] + defaults]
        return parent_names, structures
    # Rust constructs its child-key array as consecutive stack string slices.
    # Locate the array containing CODEX_THREAD_ID by decoded content, then retain
    # every entry, including any future unprefixed entry in that array.
    slices = list(stack_strings(data))
    arrays = []
    for offset, at, raw in slices:
        if arrays and offset == arrays[-1][-1][0] + 27:
            arrays[-1].append((offset, at, raw))
        else:
            arrays.append([(offset, at, raw)])
    arrays = [a for a in arrays if any(raw == b'CODEX_THREAD_ID' for _, _, raw in a)]
    assert len(arrays) == 1 and len(arrays[0]) >= 6, 'Codex child-key array missing or ambiguous'
    children = arrays[0]
    # The (name, value) array the binary sets on every command it runs (unified exec), located by its
    # CODEX_CI entry and decoded whole, including every unprefixed name.
    pairs = pair_arrays(data)
    pairs = [a for a in pairs if any(name == b'CODEX_CI' for _, name, _ in a)]
    assert len(pairs) == 1 and len(pairs[0]) >= 6, 'Codex child environment pairs missing or ambiguous'
    parent_names = sorted({raw.decode() for _, _, raw in children} | {name.decode() for _, name, _ in pairs[0]})
    structures = [{'offset': at, 'instruction_offset': offset, 'text': raw.decode()}
                  for offset, at, raw in children]
    structures += [{'offset': at, 'text': name.decode(), 'value': value.decode()} for at, name, value in pairs[0]]
    return parent_names, structures


def pair_arrays(data):
    """Consecutive (name, value) Rust string-slice pairs in the writable data sections, each decoded as
    [(pair offset, name, value)]; a name is an identifier, an empty value may carry any address."""
    heads = sections(data)
    mapped = [(s[3], s[4], s[5]) for s in heads if s[2] & 2 and s[1] == 1]

    def text(pos, empty):
        address, extent = struct.unpack_from('<QQ', data, pos)
        if extent == 0:
            return b'' if empty else None
        if extent > 128:
            return None
        for virtual, offset, span in mapped:
            if virtual <= address and address + extent <= virtual + span:
                return data[offset + address - virtual:offset + address - virtual + extent]
        return None
    writable = [(s[4], s[4] + s[5]) for s in heads if s[1] == 1 and s[2] & 1]

    def valid(pos):
        name = text(pos, False) if any(a <= pos and pos + 32 <= b for a, b in writable) else None
        return (name is not None and re.fullmatch(rb'[A-Za-z_][A-Za-z0-9_]*', name) is not None
                and text(pos + 16, True) is not None)
    found = []
    # Anchor on every slice of an exact CODEX_CI literal, then walk whole pairs both ways.
    for hit in re.finditer(rb'CODEX_CI', data):
        virtual = next((v + hit.start() - o for v, o, span in mapped if o <= hit.start() < o + span), None)
        if virtual is None:
            continue
        needle = struct.pack('<QQ', virtual, len(hit.group()))
        for start, end in writable:
            at = data.find(needle, start, end)
            while at >= 0:
                if valid(at):
                    first, last = at, at
                    while valid(first - 32):
                        first -= 32
                    while valid(last + 32):
                        last += 32
                    found.append([(pos, text(pos, False), text(pos + 16, True))
                                  for pos in range(first, last + 32, 32)])
                at = data.find(needle, at + 1, end)
    return found


def stack_strings(data):
    """Bounded x86-64 Rust stack slices: RIP-relative address and adjacent length."""
    for m in re.finditer(rb'\x48\x8d\x05(.{4})\x48\x89\x84\x24(.{4})\x48\xc7\x84\x24(.{4})(.{4})', data, re.S):
        address = m.start() + 7 + struct.unpack('<i', m[1])[0]
        slot, length_slot, extent = (struct.unpack('<I', m[i])[0] for i in (2, 3, 4))
        if length_slot == slot + 8 and 3 <= extent <= 128 and 0 <= address < len(data):
            yield m.start(), address, data[address:address + extent]


def inventory(data):
    found = {}

    def keep(raw, offset):
        at = offset
        for piece in CUT.split(raw):
            if re.fullmatch(NAME, piece) and (b'_' in piece or piece in (b'CLAUDECODE', b'HOME', b'PATH')):
                found.setdefault(piece.decode('ascii'), set()).add(at)
            at += len(piece)
    code = code_ranges(data)
    for match in re.finditer(rb'(?<![A-Za-z0-9_])' + NAME + rb'(?![A-Za-z0-9_])', data):
        if not any(a <= match.start() < b for a, b in code):
            keep(match.group(), match.start())
    # ELF64 section descriptors give the loaded virtual address for each byte range.
    if data[:6] == b'\x7fELF\x02\x01':
        shoff = struct.unpack_from('<Q', data, 40)[0]
        size, count = struct.unpack_from('<HH', data, 58)
        sections = [struct.unpack_from('<IIQQQQIIQQ', data, shoff + n * size) for n in range(count)]
        mapped = [(s[3], s[4], s[5]) for s in sections if s[2] & 2 and s[1] == 1]
        for section in sections:
            if section[1] != 1 or not section[2] & 1:
                continue
            start, length = section[4], section[5]
            for pos in range(start, start + length - 15, 8):
                address, extent = struct.unpack_from('<QQ', data, pos)
                if not 3 <= extent <= 128:
                    continue
                for virtual, offset, span in mapped:
                    if virtual <= address and address + extent <= virtual + span:
                        at = offset + address - virtual
                        keep(data[at:at + extent], at)
                        break
    for _, address, raw in stack_strings(data):
        keep(raw, address)
    return {name: sorted(offsets) for name, offsets in sorted(found.items())}


def extract(engine, path):
    data = path.read_bytes()
    names = inventory(data)
    parents, structures = parent_environment(engine, data, names)
    result = {'schema': 'veldo.environment_inventory/v1', 'engine': engine,
              'version': PINNED[engine][0], 'sha256': 'sha256:' + hashlib.sha256(data).hexdigest(),
              'method': 'uppercase identifier candidates outside code plus ELF string slices; conservative superset',
              'names': names,
              'session_names': session_names(data),
              'parent_session_names': parents, 'parent_structures': structures}
    if engine == 'claude':
        anchor = b'let C=e.config.type==="sdk"&&a.CLAUDE_AGENT_SDK_MCP_NO_PREFIX'
        at = data.index(anchor)
        result['mcp_naming'] = {'offset': at, 'text': anchor.decode()}
        anchors = [b'skipPrefix:C,', b'name:u?J.name:Me', b'`mcp__${']
        result['mcp_name_anchors'] = []
        for anchor in anchors:
            at = data.index(anchor)
            result['mcp_name_anchors'].append({'offset': at, 'text': anchor.decode()})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    for engine, (_, default) in PINNED.items():
        parser.add_argument('--' + engine, type=Path, default=default)
    args = parser.parse_args()
    for engine in PINNED:
        record = extract(engine, getattr(args, engine))
        path = HERE / (engine + '-environment.json')
        text = json.dumps(record, indent=1, sort_keys=True) + '\n'
        if args.check:
            assert path.read_text() == text, engine + ' inventory changed'
        else:
            path.write_text(text)
        print(engine, len(record['names']), 'names', record['sha256'])


if __name__ == '__main__':
    main()
