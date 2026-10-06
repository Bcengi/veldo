"""VELDO-0207: deterministic case projections and declared-only frozen snapshots."""
import ast
from functools import lru_cache
import hashlib
from pathlib import Path

DECLARATIONS = 'scripts/mutation_case_inputs.json'
DRIVERS = ('scripts/check_teeth_mutations.py', 'scripts/check_review_mutations.py')
MANDATORY = ('scripts/check_gate_mutations.py', 'scripts/mutation_sandbox.py',
             'scripts/case_inputs.py', 'scripts/case_trace.py', 'scripts/case_reuse.py',
             'scripts/mutation_reuse.py', 'scripts/gate_reuse.py', 'scripts/suites/shared.py')


def safe_name(name):
    path = Path(name)
    if not isinstance(name, str) or not name or path.is_absolute() or '..' in path.parts or '.git' in path.parts:
        raise ValueError('invalid declared input: ' + str(name))
    return name


@lru_cache(maxsize=4)
def worker_body(body):
    """Project each driver once; registry edits cannot enter executable worker identity."""
    tree = ast.parse(body)
    keep = []
    for node in tree.body:
        if isinstance(node, ast.If):  # only the CLI __main__ block is omitted
            if ast.unparse(node.test) != "__name__ == '__main__'":
                raise ValueError('unexpected driver top-level conditional')
            continue
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in ('cases', 'main', 'reuse_definition'):
            continue
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'CASES' for t in node.targets):
            continue
        keep.append(node)
    return ast.unparse(ast.Module(body=keep, type_ignores=[])) + '\n'


def projection(body, case):
    definition = {k: v for k, v in case.items() if k not in ('driver', 'identity')}
    return (worker_body(body) + '\ndef cases():\n    return ' + repr([definition]) + '\n').encode()


def selected(files, case, declaration):
    names = set(declaration['files']) | set(MANDATORY) | set(DRIVERS)
    names.add('scripts/suites/' + case['suite'])
    names.add(('scripts/fixtures' if case.get('fixture') else case.get('dir', '.veldo')) + '/' + case['module'])
    result = {}
    for name in sorted(names):
        safe_name(name)
        mode, body = files[name]
        if name in DRIVERS:
            body = projection(body, case)
        result[name] = (mode, body)
    absent = declaration.get('absent', [])
    for name in absent:
        safe_name(name)
        if name in files or name in result:
            raise ValueError('expected absent input now exists: ' + name)
    return result


@lru_cache(maxsize=2048)
def content_digest(body):
    return hashlib.sha256(body).hexdigest()


def identity(files):
    return {name: [mode, content_digest(body)] for name, (mode, body) in files.items()}


def freeze(destination, files):
    """No clone, history, link to checkout, or implicit repository files."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    for name, (mode, body) in files.items():
        target = destination / safe_name(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        target.chmod(mode & ~0o222)
