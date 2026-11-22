"""Static census of control-plane network boundaries (VELDO-0258).

Scan every engine Python module, including modules absent from the register.
Local-only HTTP adapters have named functions, not module-wide exemptions.
"""
import ast
import json
from pathlib import Path


def calls(source):
    tree = ast.parse(source)
    aliases = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            aliases.update((a.asname or a.name, a.name) for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            aliases.update((a.asname or a.name, (node.module or '') + '.' + a.name) for a in node.names)

    def name(node):
        if isinstance(node, ast.Name):
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return name(node.value) + '.' + node.attr
        return ''

    found = []
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = name(node.func)
        network = (target in ('urllib.request.urlopen', 'socket.create_connection',
                              'http.client.HTTPConnection', 'http.client.HTTPSConnection')
                   or target.startswith(('requests.', 'httpx.'))
                   or target.endswith(('.http', '.gated_open'))
                   or (target.endswith(('.run', '.check_output', '.Popen', '.call'))
                       and any(isinstance(part, ast.Constant) and part.value in ('push', 'fetch', 'ls-remote', 'clone')
                               for arg in node.args for part in ast.walk(arg)))
                   or (isinstance(node.func, ast.Attribute) and node.func.attr == 'open'
                       and (name(node.func.value).endswith(('opener', '_opener'))
                            or isinstance(node.func.value, ast.Call)
                            and name(node.func.value.func).endswith(('opener', '_opener')))))
        if network:
            enclosing = [f for f in functions if f.lineno <= node.lineno <= f.end_lineno]
            function = max(enclosing, key=lambda f: f.lineno).name if enclosing else '<module>'
            found.append((function, node.lineno))
    return found


def findings(engine, register=None):
    engine = Path(engine)
    folder = engine / '.veldo' if (engine / '.veldo').is_dir() else engine
    register = register or json.loads((folder / 'control_plane_calls.json').read_text())
    listed = register['modules']
    local = dict(register.get('local_only', {}), **register.get('project_calls', {}))
    problems = []
    for path in sorted(engine.rglob('*.py')):
        module = path.relative_to(engine).as_posix().removeprefix('.veldo/')
        sites = calls(path.read_text())
        if any(function not in local.get(module, []) for function, _ in sites) and module not in listed:
            problems.append('control_plane_call_unregistered:' + module)
    for module, destination in listed.items():
        if not (folder / module).is_file() or not isinstance(destination, str) or not destination:
            problems.append('control_plane_call_unregistered:' + module)
    return sorted(set(problems))
