#!/usr/bin/env python3
"""Isolated-enforcement command: enforcement runs with the graph execution environment absent.

  python3 .veldo/control_graph_isolation.py [--root REPOSITORY]

R35 stdlib_only_enforcement (VELDO-0043 AC3). For every installed enforcement entry below, the
command does two things against that repository's own installed modules:

  1. a static import closure: every import statement (at any depth, including lazy imports in
     functions), every literal importlib.import_module / __import__ name, and every sibling .py file
     the module names, followed transitively; any name that is neither standard library nor an
     installed sibling is a violation, and
  2. a real run of the entry's ordinary command in a child interpreter started with -I -S (no site
     packages, no user site, no environment path) and an import finder that refuses, and records,
     any module that is neither standard library nor an installed sibling.

An entry passes only when both are clean, the run finishes without an uncaught exception and its
exit code is one of that entry's ordinary verdict codes. The graph probe then requires graph start
to report runtime_unavailable, never success, in the same isolated child. An entry whose module
is not installed is reported as not_installed; enabled entries are the installed ones. Exit 0 only
when every installed entry passes and the graph probe reports runtime_unavailable.
"""
import ast
import json
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
# id, installed module, ordinary argv, ordinary verdict exit codes.
ENTRIES = (
    ('validator', 'validate.py', ('all',), (0,)),
    ('shape_gate', 'shape_gate.py', (), (0,)),
    ('policy_check', 'policy_check.py', (), (0, 1)),
    ('authorization', 'authorization.py', (), (0,)),
    ('version', 'version.py', (), (0, 1, 2)),
    ('graph_start', 'control_graph_isolation.py', ('--probe-graph',), (0,)),
)
ENVIRONMENT = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC',
               'PYTHONDONTWRITEBYTECODE': '1', 'GIT_CONFIG_NOSYSTEM': '1',
               'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0'}
HARNESS = r'''
import importlib.abc, json, runpy, sys
from pathlib import Path
veldo, entry, report = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
siblings = {path.stem for path in veldo.glob('*.py')}
allowed = set(sys.stdlib_module_names) | set(sys.builtin_module_names) | siblings | {'__main__'}
refused = []
class ExecutionEnvironmentAbsent(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        if name.partition('.')[0] in allowed:
            return None
        refused.append(name)
        raise ModuleNotFoundError('execution environment absent: ' + name, name=name)
sys.meta_path.insert(0, ExecutionEnvironmentAbsent())
sys.argv = [str(veldo / entry), *sys.argv[4:]]
outcome = {'exit': 0, 'exception': None}
try:
    runpy.run_path(str(veldo / entry), run_name='__main__')
except SystemExit as error:
    code = error.code
    outcome['exit'] = code if type(code) is int else (0 if code is None else 1)
except BaseException as error:
    outcome['exception'] = type(error).__name__
outcome['refused'] = refused
Path(report).write_text(json.dumps(outcome))
'''


def _siblings(veldo):
    return {path.stem for path in veldo.glob('*.py')}


def _allowed(name, siblings):
    top = name.partition('.')[0]
    return top in sys.stdlib_module_names or top in sys.builtin_module_names or top in siblings


def closure(veldo, module):
    """Every non-standard, non-sibling import reachable from one installed module."""
    siblings, seen, todo, violations = _siblings(veldo), set(), [module], []
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        tree = ast.parse((veldo / name).read_text(), name)
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            elif (isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant)
                  and isinstance(node.args[0].value, str)
                  and ((isinstance(node.func, ast.Attribute) and node.func.attr == 'import_module')
                       or (isinstance(node.func, ast.Name) and node.func.id == '__import__'))):
                names = [node.args[0].value]
            elif (isinstance(node, ast.Constant) and isinstance(node.value, str)
                  and node.value.endswith('.py') and node.value[:-3] in siblings):
                todo.append(node.value)
            for imported in names:
                if imported.partition('.')[0] in siblings:
                    todo.append(imported.partition('.')[0] + '.py')
                elif not _allowed(imported, siblings):
                    violations.append({'module': name, 'import': imported})
    return {'modules': sorted(seen), 'violations': violations}


def run_entry(root, entry, argv, timeout=60):
    veldo = root / '.veldo'
    with tempfile.TemporaryDirectory(prefix='veldo-isolated-') as scratch:
        report = Path(scratch) / 'report.json'
        env = dict(ENVIRONMENT, HOME=scratch, TMPDIR=scratch)
        proc = subprocess.run([sys.executable, '-I', '-S', '-B', '-c', HARNESS, str(veldo), entry,
                               str(report), *argv], cwd=root, env=env, capture_output=True,
                              timeout=timeout)
        if proc.returncode or not report.is_file():
            return {'exit': None, 'exception': 'harness_failed', 'refused': []}
        return json.loads(report.read_text())


def check(root):
    root = Path(root).resolve()
    veldo = root / '.veldo'
    results, passed = [], True
    for identity, module, argv, verdicts in ENTRIES:
        if not (veldo / module).is_file():
            results.append({'entry': identity, 'module': module, 'status': 'not_installed'})
            passed = passed and identity != 'graph_start'
            continue
        static = closure(veldo, module)
        ran = run_entry(root, module, argv)
        ok = (not static['violations'] and not ran['refused'] and ran['exception'] is None
              and ran['exit'] in verdicts)
        passed = passed and ok
        results.append({'entry': identity, 'module': module, 'status': 'pass' if ok else 'fail',
                        'closure': static['modules'], 'static_violations': static['violations'],
                        'refused_imports': ran['refused'], 'exception': ran['exception'],
                        'exit': ran['exit']})
    return {'schema': 'veldo.isolated_enforcement/v1', 'root': str(root),
            'passed': passed, 'entries': results}


def probe_graph():
    """Graph start with no runtime supplied: the only acceptable answer is runtime_unavailable."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('isolated_control_graph', HERE / 'control_graph.py')
    graph = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(graph)
    adapter = graph.Adapter(None, 'isolated-domain', 'isolated-repository')
    version = {'id': 'probe', 'version': 1, 'digest': 'sha256:' + '0' * 64}
    try:
        adapter.start('probe-cycle', 'probe-command', version, version)
    except graph.Refused as error:
        print(json.dumps({'refusal': error.code, 'counts': adapter.counts}))
        return 0 if error.code == 'runtime_unavailable' and adapter.counts['refused'] == 1 else 1
    print(json.dumps({'refusal': None}))
    return 1


def main(argv):
    if argv[1:] == ['--probe-graph']:
        return probe_graph()
    root = HERE.parent
    if len(argv) == 3 and argv[1] == '--root':
        root = Path(argv[2])
    elif len(argv) != 1:
        print('usage: control_graph_isolation.py [--root REPOSITORY]')
        return 2
    result = check(root)
    print(json.dumps(result, indent=1, sort_keys=True))
    print('isolated enforcement: ' + ('pass' if result['passed'] else 'FAIL'))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
