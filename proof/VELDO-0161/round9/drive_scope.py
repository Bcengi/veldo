"""VELDO-0161 round 9: the restart/adoption-signer-kill row's names and the rows after it, read from the source.

For suite 86's file at each commit given, finds the suite function's `with section(AK)` block and lists the names it
binds in the suite function's own scope (names bound inside a nested function, lambda or comprehension are that
scope's own and are not counted). Then, for every later `with section(...)` block, lists the names it reads that the
AK block bound, where the later block has bound no value of its own to that name at an earlier line. Such a read
sees the AK row's value, not the one an earlier section computed.

Usage: python3 proof/VELDO-0161/round9/drive_scope.py <commit>... (prints JSON)
"""
import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SUITE = 'scripts/suites/86_veldo_0189_engine_upgrade.py'
NESTED = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp,
          ast.GeneratorExp, ast.ClassDef)


def own_scope(node):
    """Every node under `node` that is in the same scope (nested scopes are not entered)."""
    for child in ast.iter_child_nodes(node):
        yield child
        if not isinstance(child, NESTED):
            yield from own_scope(child)


def bound(node):
    found = {}
    for child in own_scope(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            found.setdefault(child.id, child.lineno)
        elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            found.setdefault(child.name, child.lineno)
    return found


def loads(node, shadowed=frozenset()):
    """(name, line) for every read under `node` that resolves to the suite function's scope: a read inside a nested
    function, lambda or comprehension that binds the name itself (an argument, a loop target, an assignment) is that
    scope's own and is left out."""
    for child in ast.iter_child_nodes(node):
        inner = shadowed
        if isinstance(child, NESTED):
            names = {n.id for n in ast.walk(child) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                names |= {a.arg for a in ast.walk(child.args) if isinstance(a, ast.arg)}
            inner = shadowed | names
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load) and child.id not in shadowed:
            yield child.id, child.lineno
        yield from loads(child, inner)


def section_names(node):
    item = node.items[0].context_expr
    if isinstance(item, ast.Call) and getattr(item.func, 'id', None) == 'section':
        return [a.id for a in item.args if isinstance(a, ast.Name)]
    return None


def analyse(commit):
    source = subprocess.run(['git', 'show', '%s:%s' % (commit, SUITE)], cwd=str(ROOT), check=True,
                            capture_output=True, text=True).stdout
    tree = ast.parse(source)
    suite = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == '_v189_suite')
    blocks = [n for n in own_scope(suite) if isinstance(n, ast.With) and section_names(n)]
    ak = [b for b in blocks if section_names(b) == ['AK']]
    if len(ak) != 1:
        return {'commit': commit, 'error': '%d AK blocks' % len(ak)}
    ak = ak[0]
    ak_bound = bound(ak)
    leaks = []
    for block in blocks:
        if block.lineno <= ak.lineno:
            continue
        own = bound(block)
        for name, line in sorted(set(loads(block))):
            if name in ak_bound and not (name in own and own[name] < line):
                leaks.append({'row': section_names(block), 'name': name, 'line': line})
    return {'commit': commit, 'ak_block_line': ak.lineno,
            'ak_binds_in_suite_scope': sorted(ak_bound),
            'later_rows_read_ak_values': leaks}


def main():
    print(json.dumps([analyse(c) for c in sys.argv[1:]], indent=1))


if __name__ == '__main__':
    main()
