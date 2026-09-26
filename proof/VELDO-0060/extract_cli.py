#!/usr/bin/env python3
"""Extract the command line of the installed Claude Code binary, VELDO-0060.

Reads only the binary's bytes: the options its main `claude` command declares (the commander chain
from `.name("claude")` to that command's `.action(`), each option's flags, whether it takes a value,
the choices it declares, the check print mode makes on stream JSON output (it requires the verbose
option) and the environment switch that turns its updater off. Nothing is executed, no model runs,
nothing logs in and no profile, credential or configuration file is opened. The stream formats and
credential tables stay in VELDO-0062's table (proof/VELDO-0062/cli-formats.json), which this reuses.

    python3 -B proof/VELDO-0060/extract_cli.py [--claude PATH]            # write
    python3 -B proof/VELDO-0060/extract_cli.py --check [--claude PATH]    # compare, exit 1 on a change

Writes proof/VELDO-0060/cli-options.json. The anchors are the exact text of 2.1.281; a version that
moved one fails here by name rather than yielding a guessed table.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE / 'cli-options.json'
DEFAULT_CLAUDE = Path.home() / '.local/share/claude/versions/2.1.281'
MAIN = '.name("claude")'
PRINT = '"-p, --print"'
VERBOSE_REQUIRED = 'Error: When using --print, --output-format=stream-json requires --verbose'
UPDATER = 'DISABLE_AUTOUPDATER'
# One option declaration: `.option("FLAGS", ...` or `new <Option class>("FLAGS", ...` in the chain.
DECLARED = re.compile(r'(?:\.option|new [A-Za-z_$][A-Za-z0-9_$]{0,3})\("(?P<flags>[^"]+)"')
FLAGS = re.compile(r'^(?:(?P<short>-[A-Za-z0-9]{1,3}), )?(?P<long>--[A-Za-z][A-Za-z0-9-]*)'
                   r'(?:, (?P<alias>--[A-Za-z][A-Za-z0-9-]*))?(?: (?P<value>[<\[][^>\]]+[>\]]))?$')
CHOICES = re.compile(r'\.choices\(\[((?:"[^"]*",?)+)\]\)')


class Moved(Exception):
    pass


def _digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return 'sha256:' + h.hexdigest()


def claude(path):
    text = Path(path).read_bytes().decode('latin-1')
    start = text.find(MAIN)
    if start < 0 or text.count(MAIN) != 1:
        raise Moved('the main command is not named once')
    printing = text.find(PRINT, start)
    end = text.find('.action(', printing)
    if printing < 0 or end < 0 or end - start > 100000:
        raise Moved('the main command has no print option or action')
    chain = text[start:end]
    options = {}
    found = list(DECLARED.finditer(chain))
    for n, match in enumerate(found):
        shape = FLAGS.match(match.group('flags'))
        if not shape:
            continue  # an error message or another string that begins like a flag
        following = chain[match.end():found[n + 1].start() if n + 1 < len(found) else len(chain)]
        choices = CHOICES.search(following)
        value = shape.group('value')
        entry = {'flags': match.group('flags'), 'value': None if value is None else
                 ('optional' if value.startswith('[') else 'required'),
                 'choices': json.loads('[' + choices.group(1) + ']') if choices else None}
        names = [shape.group('long')] + [n for n in (shape.group('short'), shape.group('alias')) if n]
        for name in names:
            options[name] = entry
    for needed in ('--print', '--output-format', '--verbose', '--input-format'):
        if needed not in options:
            raise Moved('the main command does not declare ' + needed)
    if VERBOSE_REQUIRED not in text:
        raise Moved('the stream JSON check of print mode moved')
    updater = re.search(r'process\.env\.' + UPDATER + r'\b|' + UPDATER + r'\)\)return\{type:"env",envVar:"' + UPDATER + '"',
                        text)
    if not updater:
        raise Moved('the binary reads no ' + UPDATER)
    return {'binary': str(Path(path)), 'version': Path(path).resolve().name, 'sha256': _digest(path),
            'source': 'the commander chain of the main claude command embedded in the binary',
            'options': {name: options[name] for name in sorted(options)},
            'requires': {'--output-format=stream-json': {'with': '--print', 'needs': '--verbose',
                                                          'message': VERBOSE_REQUIRED}},
            'environment': {UPDATER: 'read by the binary as the environment switch that turns its updater off'}}


def extract(claude_path):
    return {'schema': 'veldo.cli_options/v1', 'spec_id': 'VELDO-0060',
            'generated_by': 'proof/VELDO-0060/extract_cli.py', 'claude_code': claude(claude_path)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--claude', default=str(DEFAULT_CLAUDE))
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    table = extract(args.claude)
    text = json.dumps(table, indent=1, sort_keys=True) + '\n'
    if args.check:
        same = OUT.is_file() and OUT.read_text() == text
        print('cli-options.json %s the installed binary' % ('matches' if same else 'DIFFERS from'))
        return 0 if same else 1
    OUT.write_text(text)
    print('wrote %s (%d bytes)' % (OUT.relative_to(HERE.parents[1]), len(text)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
