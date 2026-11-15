#!/usr/bin/env python3
"""VELDO-0304: creation, removal and age boundaries, checked by function."""
import ast
from pathlib import Path
import shlex


# Canonical paths also name their installed copies. Each exception is a function,
# never a whole module. Reasons are reviewed with design 6.10.
CREATORS = {}
REVIEWED = {}
REMOVERS = {}


def canonical(path):
    path = str(path)
    if path.startswith('.veldo/'):
        return 'engine/' + path
    if path.startswith('scripts/') and (Path(__file__).resolve().parents[1] / 'engine' / path).is_file():
        return 'engine/' + path
    return path


def name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return name(node.value) + '.' + node.attr
    return ''


def words(node, values, seen=()):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.Name) and node.id in values and node.id not in seen:
        return words(values[node.id], values, (*seen, node.id))
    if isinstance(node, (ast.List, ast.Tuple)):
        return [word for value in node.elts for word in words(value, values, seen)]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return words(node.left, values, seen) + words(node.right, values, seen)
    return []


def primitives(node, values):
    """Classify executed calls, not examples in strings or comments."""
    if not isinstance(node, ast.Call):
        return set()
    called = name(node.func)
    tail = called.rsplit('.', 1)[-1]
    result = set()
    if tail in ('mkdtemp', 'TemporaryDirectory'):
        result.add('create:temporary folder')
    if tail in ('rmtree', 'TemporaryDirectory'):
        result.add('remove:recursive folder')
    if tail in ('unlink', 'rmdir') or called in ('os.remove', 'os.removedirs'):
        result.add('delete:single path')
    if tail in ('remove_tree', '_remove_tree', '_rmtree', 'space_signal', 'remove_ref', 'remove_path'):
        result.add('delete:remover call')
    vector = [word for arg in node.args for word in words(arg, values)]
    if tail in ('run', 'call', 'check_call', 'check_output', 'Popen', 'system', 'popen'):
        vector = [token for word in vector for token in shlex.split(word)]
    git = 'git' in called.lower() or 'git' in vector
    if git:
        if ('worktree' in vector or 'worktree' in called) and 'add' in vector:
            result.add('create:git worktree add')
        if ('worktree' in vector or 'worktree' in called) and 'remove' in vector:
            result.add('remove:git worktree remove')
        if 'update-ref' in vector and any(x in vector for x in ('-d', '--delete')):
            result.add('history:git ref delete')
        if ('stash' in vector and any(x in vector for x in ('drop', 'clear'))
                or 'reflog' in vector and 'expire' in vector or 'prune' in vector
                or 'gc' in vector):
            result.add('history:git object removal')
    if 'rm' in vector and any(x.startswith('-') and ('r' in x or x == '--recursive') for x in vector):
        result.add('remove:shell recursive remove')
    docker = 'docker' in called or 'docker' in vector or tail in ('_engine', 'client')
    if docker:
        if any(x in vector for x in ('rm', 'rmi', 'prune')):
            result.add('remove:engine remove')
        if any(x in vector for x in ('create', 'run', 'build')):
            result.add('create:engine object')
    return result


def functions(source):
    tree = ast.parse(source)
    found = []

    def visit(node, scope):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope = (*scope, node.name)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            nodes = []

            def local(part):
                nodes.append(part)
                for child in ast.iter_child_nodes(part):
                    if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                        local(child)
            local(node)
            values = {target.id: part.value for part in nodes if isinstance(part, ast.Assign)
                      for target in part.targets if isinstance(target, ast.Name)}
            found.append(('.'.join(scope) or '<module>', nodes, values))
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                visit(child, scope)
            elif not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, scope)
    visit(tree, ())
    return found


def inventory(source):
    for function, nodes, values in functions(source):
        hits = [(node.lineno, primitive) for node in nodes for primitive in primitives(node, values)]
        times = [node for node in nodes if isinstance(node, ast.Attribute)
                 and node.attr in ('st_mtime', 'st_ctime', 'st_atime', 'st_mtime_ns', 'st_ctime_ns', 'st_atime_ns')]
        clocks = [node for node in nodes if isinstance(node, ast.Compare) and any(
            isinstance(part, ast.Call) and name(part.func).rsplit('.', 1)[-1] in
            ('time', 'monotonic', 'now', 'utcnow', 'clock') for part in ast.walk(node))]
        # A local clock value compared later is the same test.
        clocks += [node for node in nodes if isinstance(node, ast.Compare) and any(
            isinstance(part, ast.Name) and isinstance(values.get(part.id), ast.Call)
            and name(values[part.id].func).rsplit('.', 1)[-1] in
            ('time', 'monotonic', 'now', 'utcnow', 'clock') for part in ast.walk(node))]
        yield function, hits, bool(times or clocks)


def problems(source, path, creators=None, reviewed=None, removers=None):
    creators = CREATORS if creators is None else creators
    reviewed = REVIEWED if reviewed is None else reviewed
    removers = REMOVERS if removers is None else removers
    path = canonical(path)
    errors, matched = [], set()
    for function, hits, age in inventory(source):
        key = (path, function)
        deleting = any(primitive.split(':')[0] in ('remove', 'history', 'delete') for _, primitive in hits)
        for line, primitive in hits:
            category = primitive.split(':')[0]
            if category in ('remove', 'history'):
                matched.add(key)
            allowed = (category == 'create' and key in creators
                       or category == 'remove' and (key in removers or key in reviewed)
                       or category == 'history' and key in removers
                       or category == 'delete')
            if not allowed:
                errors.append(f'{path}:{line}: {function}: {primitive} outside its reviewed boundary')
        if deleting and age:
            errors.append(f'{path}: {function}: removal reads a file time or compares the clock')
    for key, reason in reviewed.items():
        if key[0] == path and (not reason or key not in matched):
            errors.append(f'{path}: {key[1]}: stale reviewed entry or missing reason')
    return errors


def sources(root):
    for directory in ('.veldo', 'engine/.veldo', 'scripts', 'engine/scripts'):
        yield from sorted((root / directory).glob('*.py'))
    for directory in ('scripts/runners', 'engine/scripts/runners'):
        yield from sorted((root / directory).rglob('*.py'))


def check(root):
    errors = []
    present = set()
    for path in sources(root):
        relative = str(path.relative_to(root))
        present.add(canonical(relative))
        try:
            errors.extend(problems(path.read_text(), relative))
        except (SyntaxError, ValueError) as error:
            errors.append(f'{relative}: unreadable syntax: {error}')
    errors.extend(f'{path}: {function}: stale reviewed entry, file absent'
                  for path, function in REVIEWED if path not in present)
    return errors


if __name__ == '__main__':
    errors = check(Path(__file__).resolve().parents[1])
    print('\n'.join(errors) if errors else 'Space boundary: pass')
    raise SystemExit(bool(errors))
