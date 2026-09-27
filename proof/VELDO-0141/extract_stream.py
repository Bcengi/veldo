#!/usr/bin/env python3
"""Extract what the VELDO-0141 fakes print that VELDO-0062's table does not hold, from the binaries' bytes.

Claude Code 2.1.281: the schema of the `user` message (a tool's result, with parent_tool_use_id) and of the
`stream_event` message (a partial message chunk, emitted with --include-partial-messages), read with
VELDO-0062's own reader of the zod objects the binary embeds (proof/VELDO-0062/extract_formats.py), and the
text of the warning the binary writes to its error stream when NODE_EXTRA_CA_CERTS names a file it cannot
load. Codex 0.154.0: the line `codex exec` writes to its error stream when it reads its prompt from standard
input, and the line its `login status` prints for a ChatGPT login. Nothing is executed, no model runs,
nothing logs in and no profile, credential or configuration file is opened.

    python3 -B proof/VELDO-0141/extract_stream.py [--claude PATH] [--codex PATH]            # write
    python3 -B proof/VELDO-0141/extract_stream.py --check [--claude PATH] [--codex PATH]    # compare

Writes proof/VELDO-0141/stream-formats.json. The anchors are the exact text of these versions; a version that
moved one fails here by name rather than yielding a guessed table.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'stream-formats.json'
FORMATS = HERE.parent / 'VELDO-0062' / 'extract_formats.py'
DEFAULT_CLAUDE = Path.home() / '.local/share/claude/versions/2.1.281'
DEFAULT_CODEX = Path('/home/dmitry/.nvm/versions/node/v22.22.0/lib/node_modules/@openai/codex/node_modules/'
                     '@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex')
EVENTS = {'user': 'd({type:R("user"),message:', 'stream_event': 'd({type:R("stream_event"),'}
CERTS = ('process.stderr.write(`Warning: Ignoring extra certs from \\`${extraPath}\\`, load failed: '
         '${err?.code === "ENOENT" ? "No such file or directory" : err?.message}\n`);')
CERTS_TEXT = 'Warning: Ignoring extra certs from `{path}`, load failed: No such file or directory'
PROMPT = 'Reading prompt from stdin...'
LOGGED_IN = 'Logged in using ChatGPT'


class Moved(Exception):
    pass


def _digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return 'sha256:' + h.hexdigest()


def _formats():
    spec = importlib.util.spec_from_file_location('v141_extract_formats', str(FORMATS))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def claude(path):
    text = Path(path).read_bytes().decode('latin-1')
    F = _formats()
    js = F.Js(text)
    events = {}
    for name, anchor in EVENTS.items():
        if text.count(anchor) != 1:
            raise Moved('%s: anchor found %d times' % (name, text.count(anchor)))
        events[name], _ = F.Reader(js, depth=4).parse(text.index(anchor))
    if text.count(CERTS) != 1:
        raise Moved('the extra certs warning moved')
    return {'binary': str(path), 'version': '2.1.281', 'sha256': _digest(path), 'events': events,
            'stderr': {'extra_certs': {'anchor': CERTS, 'text': CERTS_TEXT, 'environment': 'NODE_EXTRA_CA_CERTS'}}}


def codex(path):
    raw = Path(path).read_bytes()
    if raw.count(PROMPT.encode()) != 1:
        raise Moved('the prompt-from-stdin line moved')
    if raw.count(LOGGED_IN.encode()) != 1:
        raise Moved('the login status line moved')
    return {'binary': str(path), 'version': '0.154.0', 'sha256': _digest(path),
            'stderr': {'prompt_from_stdin': {'text': PROMPT}}, 'login_status': {'chatgpt': LOGGED_IN}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--claude', default=str(DEFAULT_CLAUDE))
    parser.add_argument('--codex', default=str(DEFAULT_CODEX))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    try:
        table = {'schema': 'veldo.stream-formats/v1', 'spec_id': 'VELDO-0141',
                 'generated_by': 'proof/VELDO-0141/extract_stream.py (reads the binaries\' bytes only)',
                 'claude_code': claude(args.claude), 'codex': codex(args.codex)}
    except Moved as error:
        sys.stderr.write('moved: %s\n' % error)
        return 1
    text = json.dumps(table, indent=1, sort_keys=True) + '\n'
    if args.check:
        same = OUT.is_file() and OUT.read_text() == text
        print('stream-formats.json %s' % ('matches the binaries' if same else 'differs from the binaries'))
        return 0 if same else 1
    OUT.write_text(text)
    print('wrote %s' % OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
