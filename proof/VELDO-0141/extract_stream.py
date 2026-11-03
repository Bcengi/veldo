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

Writes proof/VELDO-0141/stream-formats.json. The default binaries are the qualified ones of the engines
record (.veldo/runtime/engines.json) and each version written is the one the binary itself names. The event
anchors are located by shape, so a minifier renaming its identifiers moves nothing; the rest is exact text,
and a version that moved one fails here by name rather than yielding a guessed table.

The extra certs warning has two forms. Up to 2.1.281 the runtime's own script writes it (CERTS, its text for
a file that does not exist read from the script); 2.1.317 writes it from native code, a Rust format template
whose literal pieces are length-prefixed and whose arguments are 0xC0 bytes (CERTS_TEMPLATE), and the error
it prints there is a runtime value the bytes do not hold, so the table's text names it {error}.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
OUT = HERE / 'stream-formats.json'
FORMATS = HERE.parent / 'VELDO-0062' / 'extract_formats.py'
QUALIFY = ROOT / '.veldo' / 'qualify.py'
# The zod object of each event: `<object>({type:<literal>("<name>"),...`, the identifiers the minifier's.
IDENTIFIER = r'[A-Za-z_$][A-Za-z0-9_$]*'
EVENTS = {'user': re.compile(r'(?<![A-Za-z0-9_$])' + IDENTIFIER + r'\(\{type:' + IDENTIFIER + r'\("user"\),message:'),
          'stream_event': re.compile(r'(?<![A-Za-z0-9_$])' + IDENTIFIER + r'\(\{type:' + IDENTIFIER
                                     + r'\("stream_event"\),')}
CERTS = ('process.stderr.write(`Warning: Ignoring extra certs from \\`${extraPath}\\`, load failed: '
         '${err?.code === "ENOENT" ? "No such file or directory" : err?.message}\n`);')
CERTS_TEXT = 'Warning: Ignoring extra certs from `{path}`, load failed: No such file or directory'
CERTS_HEAD, CERTS_MIDDLE = 'Warning: Ignoring extra certs from `', '`, load failed: '
CERTS_TEMPLATE = re.compile(re.escape(bytes([len(CERTS_HEAD)]) + CERTS_HEAD.encode() + b'\xc0'
                                      + bytes([len(CERTS_MIDDLE)]) + CERTS_MIDDLE.encode()) + rb'(\xc0+)\x00')
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


def _qualify():
    spec = importlib.util.spec_from_file_location('v141_qualify', str(QUALIFY))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def extra_certs(text):
    """The warning written when NODE_EXTRA_CA_CERTS names a file that cannot be loaded, in either form."""
    if text.count(CERTS) == 1:
        return {'anchor': CERTS, 'text': CERTS_TEXT, 'environment': 'NODE_EXTRA_CA_CERTS'}
    templates = list(CERTS_TEMPLATE.finditer(text.encode('latin-1')))
    if text.count(CERTS) or len(templates) != 1:
        raise Moved('the extra certs warning moved')
    arguments = len(templates[0].group(1))
    return {'anchor': CERTS_HEAD + '{}' + CERTS_MIDDLE + '{}' * arguments,
            'text': CERTS_HEAD + '{path}' + CERTS_MIDDLE + '{error}', 'environment': 'NODE_EXTRA_CA_CERTS'}


def claude(path):
    text = Path(path).read_bytes().decode('latin-1')
    F = _formats()
    js = F.Js(text)
    events = {}
    for name, anchor in EVENTS.items():
        found = list(anchor.finditer(text))
        if len(found) != 1:
            raise Moved('%s: anchor found %d times' % (name, len(found)))
        events[name], _ = F.Reader(js, depth=4).parse(found[0].start())
        if events[name].get('type') != 'object' or not events[name].get('fields'):
            raise Moved('%s: the schema reader of VELDO-0062 reads no object there (%s)'
                        % (name, events[name].get('type')))
    return {'binary': str(path), 'version': _qualify().claude_version(path), 'sha256': _digest(path),
            'events': events, 'stderr': {'extra_certs': extra_certs(text)}}


def codex(path):
    raw = Path(path).read_bytes()
    if raw.count(PROMPT.encode()) != 1:
        raise Moved('the prompt-from-stdin line moved')
    if raw.count(LOGGED_IN.encode()) != 1:
        raise Moved('the login status line moved')
    return {'binary': str(path), 'version': _qualify().codex_version(path)[0], 'sha256': _digest(path),
            'stderr': {'prompt_from_stdin': {'text': PROMPT}}, 'login_status': {'chatgpt': LOGGED_IN}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    Q = _qualify()
    parser.add_argument('--claude', default=str(Q.binary('claude_code')))
    parser.add_argument('--codex', default=str(Q.binary('codex')))
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
