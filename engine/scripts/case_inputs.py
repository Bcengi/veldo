"""VELDO-0207: deterministic case projections and declared-only frozen snapshots."""
import ast
from functools import lru_cache
import hashlib
from pathlib import Path

DECLARATIONS = 'scripts/mutation_case_inputs.json'
DRIVERS = ('scripts/check_teeth_mutations.py', 'scripts/check_review_mutations.py')
MANDATORY = ('.veldo/reuse_evidence.py', 'scripts/agent_sandbox.json', 'scripts/check_gate_mutations.py', 'scripts/mutation_sandbox.py',
             'scripts/case_inputs.py', 'scripts/case_trace.py', 'scripts/case_reuse.py',
             'scripts/mutation_reuse.py', 'scripts/gate_reuse.py', 'scripts/suites/shared.py')

# What starts a gate (VELDO-0210 AC7): the gate's entry, the launcher it starts and the leg runner
# between them, wherever a copy lies (engine/, a fixture). A declared case reads only its declared
# inputs, so one without any of these starts no gate, and one with any is refused declaration.
GATE_ENTRIES = ('verify.sh', 'gate_candidate.py', 'gate_legs.py', 'agent_sandbox.py')


def gate_entries(names):
    """The declared inputs among `names` that start a gate, sorted; [] when none does."""
    return sorted(name for name in names if Path(name).name in GATE_ENTRIES)


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
    for directory in declaration.get('directories', []):
        safe_name(directory)
        names.update(name for name in files if Path(name).is_relative_to(directory))
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
