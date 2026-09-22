#!/usr/bin/env python3
"""Reject private document serializers outside yamlish.py.

This source boundary catches named and renamed copies of the former renderers,
key/value formatting and flow-list assembly in text-producing functions. It is
not a proof about arbitrary programs. Schema adapters build data and call dump
or render_document; source-preserving field edits are not document serializers.
Test fixtures may intentionally produce invalid syntax and are excluded by path.
"""
import ast
from pathlib import Path
import re


def problems(source):
    tree = ast.parse(source)
    bad = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            modules = [node.module or ''] if isinstance(node, ast.ImportFrom) else [a.name for a in node.names]
            if any(m.split('.')[0] in {'yaml', 'ruamel'} for m in modules):
                bad.add(node.lineno)
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name in {'_fm_scalar', '_recurrence_scalar', '_inline'}:
            bad.add(node.lineno)
        returns = [n.value for n in ast.walk(node) if isinstance(n, ast.Return) and isinstance(n.value, (ast.BinOp, ast.JoinedStr, ast.Call))]
        joined = any(isinstance(n, ast.Call) and getattr(n.func, 'attr', '') == 'join'
                     and isinstance(n.func.value, ast.Constant) and n.func.value.value in ('', '\n')
                     for ret in returns for n in ast.walk(ret))
        literals = [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        document = any(s == '---' or s.startswith('schema:') for s in literals)
        for part in ast.walk(node):
            if not isinstance(part, (ast.BinOp, ast.JoinedStr)):
                continue
            strings = [n.value for n in ast.walk(part) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            # Formatting data into key/value text is syntax ownership, independent of names.
            keyed = any(re.match(r'^\s*(?:-\s+)?(?:[A-Za-z_][\w]*|%s): ', s) for s in strings)
            fkey = (isinstance(part, ast.JoinedStr) and len(part.values) > 1
                    and isinstance(part.values[0], ast.FormattedValue)
                    and isinstance(part.values[1], ast.Constant)
                    and part.values[1].value.startswith(':'))
            keyed = keyed or fkey
            flow = any(s.startswith('[') for s in strings) and any(s.endswith(']') for s in strings)
            direct = any(part is ret for ret in returns)
            dynamic_key = fkey or any(s.lstrip().startswith(('%s:', '%s%s:')) for s in strings)
            multiline = any('\n' in s for s in strings)
            if (joined and (document or dynamic_key) and (keyed or flow)
                    or direct and multiline and keyed):
                bad.add(part.lineno)
    return sorted(bad)


def check(root):
    errors = []
    for directory in ('.veldo', 'engine/.veldo', 'scripts', 'engine/scripts'):
        for path in sorted((Path(root) / directory).glob('*.py')):
            if path.name in {'yamlish.py', 'check_writer_boundary.py', 'parser_corpus_audit.py'} or path.name.startswith('test_'):
                continue
            source = path.read_text()
            ignored = set()
            # Commit trailers are a separate external protocol, not a YAML document.
            if path.name == 'commit_attribution.py':
                for node in ast.parse(source).body:
                    if isinstance(node, ast.FunctionDef) and node.name == 'format_trailers':
                        ignored.update(range(node.lineno, node.end_lineno + 1))
            errors.extend(f'{path.relative_to(root)}:{line}: document syntax must use yamlish writer'
                          for line in problems(source) if line not in ignored)
    return errors


if __name__ == '__main__':
    errors = check(Path(__file__).resolve().parents[1])
    print('\n'.join(errors) if errors else 'Document writer boundary: pass')
    raise SystemExit(bool(errors))
