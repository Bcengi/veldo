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
# Parent session names observed in the live run and the Codex child environment.
PARENT = ('CLAUDECODE', 'CLAUDE_CODE_CHILD_SESSION', 'CLAUDE_CODE_SESSION_ID',
          'CLAUDE_CODE_SESSION_ATTENDED', 'CLAUDE_CODE_ENTRYPOINT', 'CLAUDE_CODE_EXECPATH',
          'CLAUDE_CODE_MESSAGING_SOCKET', 'CLAUDE_CODE_MESSAGING_TOKEN', 'CLAUDE_PID',
          'CLAUDE_EFFORT', 'AI_AGENT', 'CODEX_THREAD_ID', 'CODEX_INTERNAL_ORIGINATOR_OVERRIDE',
          'CODEX_SANDBOX', 'CODEX_SANDBOX_NETWORK_DISABLED')


def inventory(data):
    found = {}

    def keep(raw, offset):
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
    # Explicit observed names can occur in merged literal runs too.
    for name in PARENT:
        raw = name.encode()
        for match in re.finditer(re.escape(raw), data):
            keep(raw, match.start())
    return {name: sorted(offsets) for name, offsets in sorted(found.items())}


def extract(engine, path):
    data = path.read_bytes()
    names = inventory(data)
    result = {'schema': 'veldo.environment_inventory/v1', 'engine': engine,
              'version': PINNED[engine][0], 'sha256': 'sha256:' + hashlib.sha256(data).hexdigest(),
              'method': 'uppercase identifier candidates plus ELF string slices; conservative superset',
              'names': names, 'parent_session_names': [n for n in PARENT if n in names]}
    if engine == 'claude':
        anchor = b'let C=e.config.type==="sdk"&&a.CLAUDE_AGENT_SDK_MCP_NO_PREFIX'
        at = data.index(anchor)
        result['mcp_naming'] = {'offset': at, 'text': data[at:at + 1300].decode('utf-8')}
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
