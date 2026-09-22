#!/usr/bin/env python3
"""Reject private YAML-ish syntax readers outside .veldo/yamlish.py.

Like check_git_boundary, this is a source boundary, not a proof about arbitrary
Python programs. It covers the prior copies and their renamed forms: private
fence extraction, scalar/map/list parser definitions, YAML key regexes and line
loops splitting keys. Schema validation and source-preserving writers may use
parsed values and shared fence offsets. JSON and unrelated text formats are not
YAML-ish readers. The frozen, commit-addressed corpus audit is forensic tooling,
not an alternate reader available to runtime callers.
"""
import ast
from pathlib import Path
import re


_READER_PARTS = {'parse_yamlish', '_scalar', '_split_top', '_parse_block', '_parse_map',
                 '_parse_list', '_scan_scalar', '_root_keys', '_policy_lines', '_parse_inline'}
_REGEX_CALLS = {'match', 'search', 'fullmatch', 'findall', 'finditer', 'compile'}


def problems(source):
    tree = ast.parse(source)
    bad = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = ([node.module or ''] if isinstance(node, ast.ImportFrom)
                       else [a.name for a in node.names])
            if any(m.split('.')[0] in {'yaml', 'ruamel'} for m in modules):
                bad.add(node.lineno)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in _READER_PARTS:
                bad.add(node.lineno)
            # Renaming a copied line reader does not grant it an exception.
            loops = [n for n in ast.walk(node) if isinstance(n, (ast.For, ast.While, ast.comprehension))]
            line_sequences = {target.id for n in ast.walk(node) if isinstance(n, ast.Assign) and any(isinstance(c, ast.Call) and getattr(c.func, 'attr', '') == 'splitlines' for c in ast.walk(n.value)) for target in n.targets if isinstance(target, ast.Name)}
            for loop in loops:
                # Require line-oriented input, not arbitrary colon-delimited protocols.
                if not isinstance(loop, (ast.For, ast.comprehension)) or not (any(isinstance(c, ast.Call) and getattr(c.func, 'attr', '') == 'splitlines' for c in ast.walk(loop.iter)) or isinstance(loop.iter, ast.Name) and loop.iter.id in line_sequences):
                    continue
                calls = [n for n in ast.walk(loop) if isinstance(n, ast.Call)]
                for call in calls:
                    attr = getattr(call.func, 'attr', '')
                    receiver = getattr(call.func, 'value', None)
                    targets = {n.id for n in ast.walk(loop.target) if isinstance(n, ast.Name)} if isinstance(loop, (ast.For, ast.comprehension)) else {'line', 'raw'}
                    if not isinstance(receiver, ast.Name) or receiver.id not in targets:
                        continue
                    if attr in {'partition', 'split', 'startswith'} and call.args:
                        arg = call.args[0]
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if arg.value == ':' or re.fullmatch(r'[a-z_][a-z0-9_]*:', arg.value):
                                bad.add(call.lineno)
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, 'attr', getattr(node.func, 'id', ''))
        if not node.args:
            continue
        strings = [n.value for n in ast.walk(node.args[0])
                   if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        if name in {'find', 'split', 'startswith'} and any('\n---' in s or s == '---' for s in strings):
            bad.add(node.lineno)
        if name in _REGEX_CALLS:
            for pattern in strings:
                fence = '^---' in pattern or r'\A---' in pattern
                key = ('.*' in pattern or r':\s' in pattern or pattern.endswith(':')) and ':' in pattern.replace('(?:', '(') and ('^' in pattern or name == 'compile') and (
                    '[A-Za-z' in pattern or r'\w+' in pattern or any(
                        word + ':' in pattern for word in (
                            'status', 'id', 'risk', 'home', 'protected_paths', 'architecture_contract',
                            'risk_tiers', 'footprint', 'placement', 'behavior_bearing')))
                if fence or key:
                    bad.add(node.lineno)
    return sorted(bad)


def check(root):
    root = Path(root)
    errors = []
    for directory in ('.veldo', 'engine/.veldo', 'scripts', 'engine/scripts'):
        for path in sorted((root / directory).glob('*.py')):
            rel = path.relative_to(root).as_posix()
            if rel in {'.veldo/yamlish.py', 'engine/.veldo/yamlish.py',
                       'scripts/check_parser_boundary.py', 'scripts/parser_corpus_audit.py'}:
                continue
            # Git commit trailers are a colon-delimited external protocol, not YAML.
            # Restrict the exception to that function; other code in the module is covered.
            source = path.read_text()
            tree = ast.parse(source)
            ignored = set()
            if path.name == 'commit_attribution.py':
                for node in tree.body:
                    if isinstance(node, ast.FunctionDef) and node.name == 'trailers':
                        ignored.update(range(node.lineno, node.end_lineno + 1))
            errors.extend(f'{rel}:{n}: document syntax must use yamlish'
                          for n in problems(source) if n not in ignored)
    return errors


if __name__ == '__main__':
    errors = check(Path(__file__).resolve().parents[1])
    print('\n'.join(errors) if errors else 'Document parser boundary: pass')
    raise SystemExit(bool(errors))
