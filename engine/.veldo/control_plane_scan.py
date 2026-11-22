"""Static census of control-plane network boundaries (VELDO-0258).

Scan every engine Python module, including modules absent from the register.
Local-only adapters have named functions with a reason, not module-wide exemptions.
"""
import ast
import json
import re
from pathlib import Path


# Git verbs that reach a repository elsewhere, and command-line tools that reach a host.
GIT_TRANSPORT = ('push', 'fetch', 'pull', 'ls-remote', 'clone')
NETWORK_TOOLS = ('curl', 'wget', 'ssh', 'scp', 'sftp', 'rsync', 'nc', 'ncat', 'telnet')
PROCESS = ('run', 'check_output', 'check_call', 'Popen', 'call', 'system', 'popen')
GIT_NAME = re.compile(r'(?:^|_)git(?:_|$)', re.IGNORECASE)
HTTP = ('urllib.request.urlopen', 'socket.create_connection', 'http.client.HTTPConnection',
        'http.client.HTTPSConnection')


def calls(source):
    """(function, line) of every outside call. Recognized forms, whoever wraps them:
    an HTTP or socket client; an opener built anywhere (it is held to be opened); the boundary's
    http and gated_open; a Git transport verb given to a process call or to any callable whose name
    names Git (the repository's _git and git wrappers); git_process's network or identity profile;
    and a network tool given to a process call."""
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

    def words(node):
        return {part.value for arg in [*node.args, *(k.value for k in node.keywords)]
                for part in ast.walk(arg) if isinstance(part, ast.Constant) and isinstance(part.value, str)}

    found = []
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        target = name(node.func)
        last = target.rsplit('.', 1)[-1]
        literal = words(node)
        network = (target in HTTP
                   or target.startswith(('requests.', 'httpx.'))
                   or last in ('http', 'gated_open', 'build_opener', 'OpenerDirector')
                   or ((last in PROCESS or GIT_NAME.search(last)) and bool(literal & set(GIT_TRANSPORT)))
                   or (last in PROCESS and bool(literal & set(NETWORK_TOOLS)))
                   or any(k.arg == 'profile' and isinstance(k.value, ast.Constant)
                          and k.value.value in ('network', 'identity') for k in node.keywords)
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
    for module, functions in register.get('local_only', {}).items():
        # A local-only exemption names its function and why it reaches nothing off this host.
        if not isinstance(functions, dict) or not all(isinstance(reason, str) and reason.strip()
                                                      for reason in functions.values()):
            problems.append('control_plane_call_unregistered:' + module)
    for module, destination in listed.items():
        if not (folder / module).is_file() or not isinstance(destination, str) or not destination:
            problems.append('control_plane_call_unregistered:' + module)
    return sorted(set(problems))
