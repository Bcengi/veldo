"""VELDO-0230 AC1: the census of agent literals.

    python3 scripts/engine_census.py [--root <repository>]

No engine module, suite, mutation, extractor or fixture builder carries a literal agent version, digest,
binary path, model catalog, tool registry or feature list: each reads the engines record
(.veldo/runtime/engines.json) or the files the qualify command writes. This census reads what is qualified
from those generated files and finds, in every governed Python file, each string constant (docstrings and
comments are prose, not values) or collection literal that holds one:

- a version: the qualified Codex version, its package version, or the qualified Claude Code version;
- a digest: either binary's sha256 or the bundled model catalog's (its first 16 hex digits suffice);
- a binary path: either binary as the engines record writes it, or expanded;
- a model catalog: a collection literal naming three or more of the bundled catalog's model slugs;
- a tool registry: a collection literal naming half or more of the Claude Code registry's tools;
- a feature list: a collection literal naming half or more of the features `codex features list` lists, or a
  string holding three or more of its lines.

GOVERNED: the engine modules (.veldo/*.py, engine/.veldo/*.py, packs/*/.veldo/**/*.py), the suites
(scripts/suites/*.py), the mutations (scripts/check_teeth_mutations.py), every extractor
(proof/**/extract_*.py) and every other proof script a suite or the mutation checker loads (a proof file
whose VELDO id and file name the same suite or checker source names). The generated files themselves are
JSON and are not read as code. Prints one line per finding; exit 1 when there is any.
Standard library only.
"""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def qualified(root):
    """What is qualified, from the generated files: {versions, digests, paths, slugs, tools, features, lines}."""
    runtime = Path(root) / '.veldo' / 'runtime'
    engines = json.loads((runtime / 'engines.json').read_text())
    codex = json.loads((runtime / 'codex-qualification.json').read_text())
    claude = json.loads((runtime / 'claude-qualification.json').read_text())
    entry = claude['versions'][engines['claude_code']['version']]
    versions = {engines['codex']['version'], engines['codex']['package_version'], engines['claude_code']['version']}
    digests = {engines['codex']['sha256'], engines['claude_code']['sha256'], codex.get('model_catalog_digest') or ''}
    paths = set()
    for name in ('codex', 'claude_code'):
        named = engines[name]['binary']
        home = __import__('pwd').getpwuid(os.getuid()).pw_dir
        paths |= {named, home + named[1:] if named.startswith('~/') else named}
    listing = [line for line in (codex.get('feature_listing') or '').splitlines() if line.strip()]
    return {'versions': sorted(versions), 'digests': sorted(d.split(':', 1)[-1][:16] for d in digests if d),
            'paths': sorted(paths), 'slugs': {m['slug'] for m in (codex.get('model_catalog') or {}).get('models', [])},
            'tools': set(entry.get('tool_registry') or ()), 'features': {line.split()[0] for line in listing},
            'lines': set(listing)}


def governed(root):
    """The governed Python files, repository-relative."""
    root = Path(root)
    tracked = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', '*.py'],
                             cwd=root, capture_output=True, text=True, check=True).stdout.split('\0')
    tracked = sorted(p for p in tracked if p)
    files = [p for p in tracked if re.fullmatch(r'(?:\.veldo|engine/\.veldo)/[^/]+\.py', p)
             or re.fullmatch(r'packs/[^/]+/\.veldo/.+\.py', p) or re.fullmatch(r'scripts/suites/[^/]+\.py', p)
             or p == 'scripts/check_teeth_mutations.py']
    loaders = [(root / p).read_text(errors='replace') for p in files if p.startswith('scripts/')]
    for path in tracked:
        found = re.fullmatch(r'proof/(VELDO-\d{4})/(?:.+/)?([^/]+\.py)', path)
        if not found:
            continue
        ident, name = found.groups()
        if name.startswith('extract_') or any(ident in text and name in text for text in loaders):
            files.append(path)
    return sorted(set(files))


def _docstrings(tree):
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, 'body', [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                found.add(id(body[0].value))
    return found


def _names(node):
    """The string names a collection literal holds (its elements, or a dict's keys)."""
    items = node.keys if isinstance(node, ast.Dict) else node.elts
    return {item.value for item in items if isinstance(item, ast.Constant) and isinstance(item.value, str)}


def findings(source, known, path='<source>'):
    """Every literal of `source` that holds something qualified: [(path, line, kind, value)]."""
    tree = ast.parse(source)
    skip = _docstrings(tree)
    version = re.compile(r'(?<![\w.])(?:%s)(?![\w]|\.\d)' % '|'.join(re.escape(v) for v in known['versions']))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            value = node.value
            hit = version.search(value)
            if hit:
                found.append((path, node.lineno, 'version', hit.group(0)))
            for digest in known['digests']:
                if digest in value:
                    found.append((path, node.lineno, 'digest', digest))
            for binary in known['paths']:
                if binary in value:
                    found.append((path, node.lineno, 'binary_path', binary))
            lines = {line.strip() for line in value.splitlines()} & {line.strip() for line in known['lines']}
            if len(lines) >= 3:
                found.append((path, node.lineno, 'feature_list', '%d listing lines' % len(lines)))
        elif isinstance(node, (ast.List, ast.Tuple, ast.Set, ast.Dict)):
            names = _names(node)
            if len(names & known['slugs']) >= 3:
                found.append((path, node.lineno, 'model_catalog', ', '.join(sorted(names & known['slugs']))))
            if known['tools'] and len(names & known['tools']) * 2 >= len(known['tools']):
                found.append((path, node.lineno, 'tool_registry', '%d registry tools' % len(names & known['tools'])))
            if known['features'] and len(names & known['features']) * 2 >= len(known['features']):
                found.append((path, node.lineno, 'feature_list', '%d listed features' % len(names & known['features'])))
    return found


def census(root=ROOT):
    root = Path(root)
    known = qualified(root)
    found = []
    for path in governed(root):
        found += findings((root / path).read_text(), known, path)
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description='The census of agent literals (VELDO-0230 AC1).')
    parser.add_argument('--root', default=str(ROOT))
    args = parser.parse_args(argv)
    found = census(args.root)
    for path, line, kind, value in found:
        print('%s:%d: %s literal %s' % (path, line, kind, value))
    print('engine census: %s (%d governed files)' % ('FAIL, %d literal(s)' % len(found) if found else 'pass',
                                                     len(governed(args.root))))
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
