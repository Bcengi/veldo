"""VELDO-0230: upgrading an agent CLI is one command.

    python3 .veldo/qualify.py [--codex <vendor binary>] [--claude <version or path>] [--root <repository>]

With no argument it qualifies what is installed: the vendor binary inside the npm package the `codex` on
PATH runs, and the versioned executable the `claude` on PATH resolves to. `--claude 2.1.281` names the
installer's copy ~/.local/share/claude/versions/2.1.281; a path names any copy.

THE ENGINES RECORD (runtime/engines.json, beside this module, byte-identical in every runtime copy) names the
qualified Codex and Claude Code: version, binary path and digest. It is the one place a version lives: every
extractor's default binary, every suite's fake package and pinned copy, the census and setup read it.

ONE COMMAND. In order it writes the engines record, runs every extractor in write mode against the two
binaries (EXTRACTORS: the tables the engine modules and the suites compare against), regenerates the
VELDO-0127 fixtures from the Codex binary (FIXTURES), and writes the Codex and the Claude Code qualification
records to every runtime copy (RUNTIMES): the Codex record by control_engine_codex.qualification, its model
tool modes read from the bundled catalog; the Claude Code record by `claude_record`, from the extracted
tables. On the binaries already qualified it rewrites every file with the bytes it holds.

A NEWER BINARY NEVER BLOCKS (AC3). A Codex feature the classification (control_agent_config_handoff
CODEX_FEATURES) does not name is off at launch and listed by name in the record (`unclassified_features`)
and in this command's output; a Claude Code tool not on the in-run list is outward (the extractor's
classification), and a tool the replaced record did not hold is listed in the output.
Standard library only.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ENGINES = HERE / 'runtime' / 'engines.json'
SCHEMA = 'veldo.engines/v1'
CLAUDE_VERSIONS = Path('~/.local/share/claude/versions')
VERSION = re.compile(r'[0-9]+(?:\.[0-9]+){1,3}')
CODEX_PACKAGE = '@openai/codex'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def engines(path=None):
    """The engines record: {schema, claude_code: {version, binary, sha256}, codex: {version, package_version,
    binary, sha256}}. `path` defaults to the record beside this module."""
    record = json.loads(Path(path or ENGINES).read_text())
    if record.get('schema') != SCHEMA or not all(isinstance(record.get(e), dict) for e in ('claude_code', 'codex')):
        raise ValueError('not an engines record: %s' % (path or ENGINES))
    return record


def binary(engine, record=None):
    """The qualified binary of `engine` ('claude_code' or 'codex') as an absolute path, `~` expanded."""
    record = engines() if record is None else record
    return Path(os.path.expanduser(record[engine]['binary']))


def home_form(path):
    """A path under the home directory written as ~/..., so the record reads the same for every account."""
    path, home = Path(path), Path.home()
    try:
        return '~/' + str(path.relative_to(home))
    except ValueError:
        return str(path)


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return 'sha256:' + h.hexdigest()


def codex_package(executable):
    """(root, manifest) of the npm package holding the vendor binary: its nearest package.json."""
    for parent in Path(executable).parents:
        manifest = parent / 'package.json'
        if manifest.is_file():
            return parent, json.loads(manifest.read_text())
    raise SystemExit('qualify: %s lies in no npm package' % executable)


def codex_version(executable):
    """(version, package_version) of a Codex vendor binary, from its own package manifest."""
    _, manifest = codex_package(executable)
    package_version = str(manifest.get('version') or '')
    return package_version.split('-', 1)[0], package_version


def claude_version(executable):
    """The version of a Claude Code executable: its installer file name, else what `--version` prints."""
    name = Path(executable).name
    if VERSION.fullmatch(name):
        return name
    done = subprocess.run([str(executable), '--version'], capture_output=True, text=True, timeout=60,
                          env={'PATH': '/usr/bin:/bin', 'HOME': os.environ.get('HOME', '/'), 'LANG': 'C.UTF-8'})
    found = VERSION.search(done.stdout)
    if not found:
        raise SystemExit('qualify: %s prints no version' % executable)
    return found.group(0)


def installed_codex():
    """The vendor binary inside the package the `codex` on PATH runs (its platform package's vendor tree)."""
    link = shutil.which('codex')
    if not link:
        raise SystemExit('qualify: no codex on PATH; name the vendor binary with --codex')
    root = Path(os.path.realpath(link)).parent.parent
    found = sorted(root.glob('node_modules/@openai/codex-*/vendor/*/bin/codex')) or sorted(
        root.parent.glob('codex-*/vendor/*/bin/codex'))
    if not found:
        raise SystemExit('qualify: no vendor binary under %s; name it with --codex' % root)
    return found[0]


def installed_claude(named=None):
    """The Claude Code executable: a version names the installer's copy, a path names itself, nothing names
    the copy the `claude` on PATH resolves to."""
    if named:
        if VERSION.fullmatch(named):
            return Path(os.path.expanduser(str(CLAUDE_VERSIONS / named)))
        return Path(named).resolve()
    link = shutil.which('claude')
    if not link:
        raise SystemExit('qualify: no claude on PATH; name a version or a path with --claude')
    return Path(os.path.realpath(link))


def engines_record(codex, claude):
    version, package_version = codex_version(codex)
    return {
        'schema': SCHEMA,
        'spec_id': 'VELDO-0230',
        'note': 'The qualified agent CLIs, written by python3 .veldo/qualify.py and read by every extractor, '
                'suite, census row and setup step that needs a version, a binary path or a digest.',
        'claude_code': {'version': claude_version(claude), 'binary': home_form(claude), 'sha256': digest(claude)},
        'codex': {'version': version, 'package_version': package_version, 'binary': home_form(codex),
                  'sha256': digest(codex)},
    }
