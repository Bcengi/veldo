#!/usr/bin/env python3
"""Authority-only entry to candidate execution (VELDO-0271).

Runs one candidate command in the candidate root. The command reads nothing from the caller:
its standard input is /dev/null and every inherited descriptor above the standard three is
closed. No launcher and no namespace is started. The environment is the caller's with every
credential name removed (credential_names) and with the variables the gate keeps for its own
scripts dropped, so no credential the caller holds reaches candidate code through it. Nothing
else is handed over: no credential file, no descriptor and no seeded copy.

Invoke as python3 -I -S from the authority checkout, never from the candidate.
"""
import argparse
import ast
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys

# What the gate exports for its own scripts, never for candidate code. Handed on,
# VELDO_EXPECTED_GIT_COMMON makes a gate that a suite runs for a fixture repository check that
# repository against the authority's common directory and refuse it.
AUTHORITY_ONLY = ('VELDO_EXPECTED_GIT_COMMON', 'VELDO_GATE_LEDGER_FD', 'VELDO_GATE_GRAPH_DIGEST')
# Variables that load code into every interpreter or shell the command starts.
LOADERS = ('PYTHONPATH', 'PYTHONHOME', 'LD_PRELOAD', 'LD_LIBRARY_PATH', 'BASH_ENV', 'ENV')


def _assigned(path, name):
    """The expression a module assigns to `name` at its top level, read without running the module;
    None when the file or the assignment is absent."""
    try:
        tree = ast.parse(Path(path).read_text())
    except (OSError, ValueError, SyntaxError):
        return None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node.value
    return None


def exec_stripped(authority):
    """control_launch.py's EXEC_STRIPPED: the names every launch drops before it starts a run."""
    value = _assigned(Path(authority) / '.veldo/control_launch.py', 'EXEC_STRIPPED')
    try:
        names = ast.literal_eval(value) if value is not None else ()
    except ValueError:
        names = ()
    return {n for n in names if isinstance(n, str)}


def secret_pattern(authority):
    """.veldo/substrate.py's _SECRET_NAMES, the pattern a name that holds a secret matches."""
    value = _assigned(Path(authority) / '.veldo/substrate.py', '_SECRET_NAMES')
    try:
        if isinstance(value, ast.Call) and value.args:
            return re.compile(ast.literal_eval(value.args[0]), re.I)
    except (ValueError, re.error):
        pass
    return None


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _references(value, path, found):
    if isinstance(value, dict):
        if set(value) == {'secret'} and isinstance(value['secret'], str):
            # The keystore item's name, and the setting that names it: its field and its full key.
            found.update((value['secret'], path[-1] if path else '', '_'.join(path)))
            return
        for key, item in value.items():
            _references(item, path + [str(key)], found)
    elif isinstance(value, list):
        for item in value:
            _references(item, path, found)


def installation_names(authority, environ):
    """The names the installation's settings give its credentials: each keystore item a setting
    refers to ({secret: <name>}) and each setting that holds such a reference, by its field and by
    its full key. Empty when the authority has no installation reader or there is no installation."""
    reader, parser = Path(authority) / '.veldo/installation.py', Path(authority) / '.veldo/yamlish.py'
    if not reader.is_file() or not parser.is_file():
        return set()
    found = set()
    try:
        installation = _load(reader, 'gate_candidate_installation')
        resolved = installation.resolve(environ)
        settings = Path(resolved['folder']) / installation.SETTINGS_FILE
        if resolved['found'] and settings.is_file():
            _references(_load(parser, 'gate_candidate_yamlish').read(settings), [], found)
    except Exception as error:  # an unreadable installation names nothing; the fixed rules still apply
        print('gate_candidate: installation settings not read (%s); the fixed name rules still apply'
              % str(error)[:200], file=sys.stderr, flush=True)
    return {name for name in found if name}


def _plain(name):
    return re.sub(r'[^A-Za-z0-9]', '_', name).upper()


def credential_names(environ, authority):
    """The variables of `environ` that never reach a candidate: one the installation names (its
    keystore items and the settings that refer to them, compared without case), one in
    control_launch.py's EXEC_STRIPPED, and one whose name matches substrate.py's _SECRET_NAMES."""
    stripped, pattern = exec_stripped(authority), secret_pattern(authority)
    named = {_plain(name) for name in installation_names(authority, environ)}
    return {name for name in environ
            if name in stripped or _plain(name) in named or (pattern is not None and pattern.search(name))}


def candidate_environment(environ, authority):
    """The environment a candidate command runs in: `environ` without any credential name and
    without what belongs to the gate's own scripts."""
    drop = credential_names(environ, authority) | set(AUTHORITY_ONLY) | set(LOADERS)
    return {name: value for name, value in environ.items() if name not in drop}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--root', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    authority = Path(__file__).resolve().parents[1]
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('a candidate command is required after --')
    environment = candidate_environment(dict(os.environ), authority)
    environment['PWD'] = str(Path(args.root).resolve())
    # The command reads nothing from the caller: /dev/null on standard input, so a caller whose own
    # standard input is a socket (a harness or a service) hands nothing across, and no descriptor
    # above the standard three survives the start.
    result = subprocess.run(command, cwd=args.root, env=environment, stdin=subprocess.DEVNULL, close_fds=True)
    return result.returncode if result.returncode >= 0 else 128 - result.returncode


if __name__ == '__main__':
    sys.exit(main())
