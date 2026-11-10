"""Exercise the suite's actual final cleanup block with failing resource stubs."""

import ast
from pathlib import Path
import subprocess
import types


root = Path(__file__).resolve().parents[2]
relative = 'scripts/suites/86_veldo_0189_engine_upgrade.py'


def final_cleanup(source):
    suite = next(node for node in ast.parse(source).body
                 if isinstance(node, ast.FunctionDef) and node.name == '_v189_suite')
    block = next(node for node in suite.body if isinstance(node, ast.Try)
                 and any(isinstance(child, ast.Name) and child.id == 'stop_bot_api'
                         for child in ast.walk(node)))
    return compile(ast.Module(body=block.finalbody, type_ignores=[]), relative, 'exec')


order = ['runtime', 'bridge1', 'bridge2', 'manager1', 'manager2', 'bot', 'transport', 'base', 'cache']


def run(code, failing):
    seen = []

    def action(label):
        def close(*args):
            seen.append(label)
            if label in failing:
                raise RuntimeError('injected ' + label)
        return close

    def resource(label):
        return types.SimpleNamespace(path=label, close=action(label))

    namespace = dict(
        close_runtime=action('runtime'), os=types.SimpleNamespace(environ={}), prior_path186='restored',
        socket=types.SimpleNamespace(), real_connect=object(), real_resolve=object(),
        bridges=[resource('bridge1'), resource('bridge2')],
        managers=[resource('manager1'), resource('manager2')],
        stop_bot_api=action('bot'), ts=resource('transport'), remove=action('base'), base='base',
        shutil=types.SimpleNamespace(rmtree=action('cache')), cache='cache',
        contextlib=__import__('contextlib'))
    caught = None
    try:
        exec(code, namespace)
    except RuntimeError as error:
        caught = error
    return seen, caught, namespace


old = final_cleanup(subprocess.check_output(['git', 'show', '8955553d:' + relative], cwd=root, text=True))
seen, error, _ = run(old, {'bridge1'})
assert seen == order[:2] and error is not None
print('Baseline: the first bridge failure skips seven remaining cleanup actions')

fixed = final_cleanup((root / relative).read_text())
cases = [set(), *({label} for label in order), set(order)]
for failing in cases:
    seen, error, namespace = run(fixed, failing)
    assert seen == order, (failing, seen)
    assert (error is not None) == bool(failing), failing
    if error is not None:
        assert all('injected ' + label in str(error) for label in failing), str(error)
    assert namespace['os'].environ['PATH'] == 'restored'
    assert namespace['socket'].create_connection is namespace['real_connect']
    assert namespace['socket'].getaddrinfo is namespace['real_resolve']
print('Fixed: %d failure combinations complete all nine actions and restore globals' % len(cases))
