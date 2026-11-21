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
    # (what it shows, the name of the product's pattern that reads it, bytes before, bytes after). On the line the
    # Claude Code forms are found by control_engine_claude.FILE_MEMORY_PATTERNS, the patterns qualify.py reads the
    # form by (the 2.1.281 literals with the bundle's minified names left open), because the line's qualified
    # binary is a later bundle whose minified names differ: a 2.1.281 literal is in no other bundle.
    ('the auto-memory directory source order: policySettings, flagSettings, trusted local and project, userSettings',
     'directory_source', 120, 40),
    ('the directory as reported: normalized with a trailing separator', 'directory_reported', 0, 0),
    ('the environment switch: CLAUDE_CODE_DISABLE_AUTO_MEMORY turns auto memory off, unset leaves the setting',
     'environment_switch', 30, 80),
    ('autoMemoryEnabled from the merged settings, on when no source sets it', 'enabled_setting', 0, 0),
    ('the init event memory paths: auto, and team when team memory is on', 'init_paths', 30, 20),
    ('the init event field', 'init_field', 0, 0),
    ('the settings schema entry', 'settings_schema', 0, 120),
]
# A 2.1.281 literal that no product pattern reads, kept as it was and reported, never required: in 2.1.281 it
# showed autoMemoryEnabled read per settings source. A later bundle may not carry that function.
CLAUDE_2_1_281_ONLY = [
    ('autoMemoryEnabled read from the merged settings, flagSettings among them', b'function Uy(){if(PT("autoMemoryEnabled")', 0, 160),
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
        patterns = dict(load(module).FILE_MEMORY_PATTERNS) if engine == 'claude_code' else {}
        for what, literal, before, after in table:
            if engine == 'claude_code':
                match = patterns[literal].search(data)
                found = excerpt(data, match.group(0), before, after) if match else None
                shown = {'pattern': literal, 'literal': match.group(0).decode('ascii') if match else None}
            else:
                found = excerpt(data, literal, before, after)
                shown = {'literal': literal.decode('ascii')}
            if found is None:
                missing.append('%s: %r' % (engine, literal))
            rows.append(dict(shows=what, **shown, **(found or {'offset': None})))
        form = load(module).FILE_MEMORY
        if engine == 'codex':
            carried = load(module).file_memory_carried(str(path))
            if not carried:
                missing.append('codex: FILE_MEMORY_LITERALS')
        else:
            # The patterns qualify.py reads the form by (these literals with the minified names left open).
            missing += ['claude_code: FILE_MEMORY_PATTERNS ' + name for name in load(module).file_memory_missing(str(path))]
        out[engine] = {'version': engines[engine]['version'], 'sha256': digest, 'file_memory': form, 'found': rows}
        if engine == 'claude_code':
            out[engine]['literals_of_2_1_281_no_pattern_reads'] = [
                dict(shows=what, literal=literal.decode('ascii'), **(excerpt(data, literal, before, after) or {'offset': None}))
                for what, literal, before, after in CLAUDE_2_1_281_ONLY]
    (Path(__file__).with_name('engine-memory-forms.json')).write_text(json.dumps(out, indent=1, sort_keys=True) + '\n')
    if missing:
        sys.exit('extract: missing ' + ', '.join(missing))
    print('engine-memory-forms.json written: every literal found')


if __name__ == '__main__':
    main()
