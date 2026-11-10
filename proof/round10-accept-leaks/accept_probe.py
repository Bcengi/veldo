"""Run the edited fixture threads and their cleanup without connecting a client."""

import ast
import contextlib
from pathlib import Path
import shutil
import socket
import tempfile
import threading


root = Path(__file__).resolve().parents[2]
cases = (
    ('128_veldo_0254_confined_runner', 'serve', 'unix', 'server_thread', socket.AF_UNIX),
    ('127_veldo_0254_secret_scan', 'answering', None, None, socket.AF_UNIX),
    ('127_veldo_0254_secret_scan', 'answering', None, None, socket.AF_INET),
    ('102_veldo_0210_agent_profile_runtime', 'serve', 'server', 'server_thread', socket.AF_INET),
    ('47_veldo_0107_ipc', '_v107_exchange_peer', '_v107_exchange_srv', '_v107_exchange_thread', socket.AF_UNIX),
)

for name, function, socket_name, thread_name, family in cases:
    path = root / 'scripts/suites' / (name + '.py')
    tree = ast.parse(path.read_text())
    serve = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == function)
    candidates = [node.finalbody for node in ast.walk(tree) if isinstance(node, ast.Try) and node.finalbody
                  and any(isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                          and child.func.attr == 'join' for statement in node.finalbody
                          for child in ast.walk(statement))]
    cleanup = min(candidates, key=lambda body: sum(1 for node in body for _ in ast.walk(node)))
    with tempfile.TemporaryDirectory(prefix='round10-accept-') as temp:
        server = socket.socket(family)
        server.bind(str(Path(temp) / 'listener') if family == socket.AF_UNIX else ('127.0.0.1', 0))
        server.listen()
        namespace = dict(socket=socket, contextlib=contextlib, shutil=shutil, temp=temp,
                         threading=threading, servers=[], _v107_socket=socket, _v107_failure='empty')
        if socket_name:
            namespace[socket_name] = server
        exec(compile(ast.Module(body=[serve], type_ignores=[]), str(path), 'exec'), namespace)
        if function == 'answering':
            namespace[function](server)
            thread = namespace['servers'][0][1]
        else:
            thread = threading.Thread(target=namespace[function], daemon=True)
            namespace[thread_name] = thread
            thread.start()
        try:
            exec(compile(ast.Module(body=cleanup, type_ignores=[]), str(path), 'exec'), namespace)
            assert not thread.is_alive(), name
            assert server.fileno() == -1, name
        finally:
            with contextlib.suppress(OSError):
                server.shutdown(socket.SHUT_RDWR)
            thread.join(30)
            server.close()
        print('%s %s: no client; cleanup joined the thread and closed the listener' % (name, family.name))
