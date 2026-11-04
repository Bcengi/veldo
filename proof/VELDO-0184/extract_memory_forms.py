#!/usr/bin/env python3
"""VELDO-0184: the file memory forms of the qualified engines, read from their bytes (never by running them).

Reads the binaries the engines record names (.veldo/runtime/engines.json, each checked against its digest), finds
the literals each engine module's FILE_MEMORY form names and keeps a short printable excerpt around each, and writes
proof/VELDO-0184/engine-memory-forms.json. Exits nonzero when a literal is missing.

Run: python3 proof/VELDO-0184/extract_memory_forms.py
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
CLAUDE = [
    # (what it shows, the literal, bytes before, bytes after)
    ('the auto-memory directory source order: policySettings, flagSettings, trusted local and project, userSettings',
     b'let s=ye(r)?.autoMemoryDirectory;if(s!=null)return{dir:s,source:r}', 120, 40),
    ('the directory as reported: normalized with a trailing separator', b'let s=Ps(r).replace(/[/\\\\]+$/,"")', 0, 80),
    ('the environment switch: CLAUDE_CODE_DISABLE_AUTO_MEMORY turns auto memory off, unset leaves the setting',
     b'let e=process.env.CLAUDE_CODE_DISABLE_AUTO_MEMORY;if(Oe(e))return"off"', 30, 80),
    ('autoMemoryEnabled read from the merged settings, flagSettings among them', b'function Uy(){if(PT("autoMemoryEnabled")', 0, 160),
    ('the init event memory paths: auto, and team when team memory is on', b'n={auto:Qs()},fR())n.team=PS()', 30, 20),
    ('the init event field', b'if(e.memoryPaths)g.memory_paths={...e.memoryPaths}', 0, 0),
    ('the settings schema entry', b'autoMemoryDirectory:o().optional().describe(', 0, 120),
]
CODEX = [
    ('the memories table', b'MemoriesToml', 0, 60),
    ('generate_memories', b'generate_memories', 40, 40),
    ('use_memories', b'use_memories', 40, 40),
    ('the workspace-write sandbox table', b'SandboxWorkspaceWrite', 0, 60),
    ('writable_roots', b'writable_roots', 40, 40),
    ('developer_instructions', b'developer_instructions', 40, 40),
]


def load(name):
    spec = importlib.util.spec_from_file_location('v184_' + name, ROOT / '.veldo' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def excerpt(data, literal, before, after):
    at = data.find(literal)
    if at < 0:
        return None
    text = data[max(0, at - before):at + len(literal) + after]
    return {'offset': at, 'excerpt': re.sub(rb'[^\x20-\x7e]', b'.', text).decode('ascii')}


def main():
    engines = json.loads((ROOT / '.veldo/runtime/engines.json').read_text())
    out, missing = {'schema': 'veldo.engine_memory_forms/v1', 'spec_id': 'VELDO-0184'}, []
    for engine, table, module in (('claude_code', CLAUDE, 'control_engine_claude'), ('codex', CODEX, 'control_engine_codex')):
        path = Path(os.path.expanduser(engines[engine]['binary']))
        data = path.read_bytes()
        digest = 'sha256:' + hashlib.sha256(data).hexdigest()
        if digest != engines[engine]['sha256']:
            sys.exit('extract: %s is not the qualified binary' % path)
        rows = []
        for what, literal, before, after in table:
            found = excerpt(data, literal, before, after)
            if found is None:
                missing.append('%s: %r' % (engine, literal))
            rows.append(dict(shows=what, literal=literal.decode('ascii'), **(found or {'offset': None})))
        form = load(module).FILE_MEMORY
        if engine == 'codex':
            carried = load(module).file_memory_carried(str(path))
            if not carried:
                missing.append('codex: FILE_MEMORY_LITERALS')
        out[engine] = {'version': engines[engine]['version'], 'sha256': digest, 'file_memory': form, 'found': rows}
    (Path(__file__).with_name('engine-memory-forms.json')).write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
    if missing:
        sys.exit('extract: missing ' + ', '.join(missing))
    print('engine-memory-forms.json written: every literal found')


if __name__ == '__main__':
    main()
