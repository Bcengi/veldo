#!/usr/bin/env python3
"""Read pinned ELF bytes only. Retain identifier candidates and their byte offsets.

The inventory deliberately over-approximates environment names: uppercase identifiers in
embedded source and strings, plus ELF string slices (Rust literals can abut without a delimiter).
Candidates are not a claim that every identifier is read as an environment variable.
No binary is executed. The MCP naming expression is kept separately as an exact byte anchor.
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
# Delimited names cannot swallow adjacent Rust or Bun string literals.
SESSION = rb'(?<![A-Za-z0-9_])(?:CLAUDE|AI_AGENT|CODEX)(?:(?!(?:CLAUDE|AI_AGENT|CODEX))[A-Z0-9_])*(?![A-Za-z0-9_])'


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
        parent_names = sorted({n.decode() for n in children + every_child})
        structures = [{'offset': m.start(), 'text': m.group().decode()} for m in (child, startup)]
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
    parent_names = sorted({raw.decode() for _, _, raw in children})
    structures = [{'offset': at, 'instruction_offset': offset, 'text': raw.decode()}
                  for offset, at, raw in children]
    return parent_names, structures


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
        if len(re.findall(rb'CLAUDE|AI_AGENT|CODEX', raw)) > 1:
            return
        if re.fullmatch(NAME, raw) and (b'_' in raw or raw in (b'CLAUDECODE', b'HOME', b'PATH')):
            found.setdefault(raw.decode('ascii'), set()).add(offset)
    for match in re.finditer(rb'(?<![A-Za-z0-9_])' + NAME + rb'(?![A-Za-z0-9_])', data):
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
              'method': 'uppercase identifier candidates plus ELF string slices; conservative superset',
              'names': names,
              'session_names': sorted({m.group().decode('ascii') for m in re.finditer(
                  SESSION, data)}),
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
