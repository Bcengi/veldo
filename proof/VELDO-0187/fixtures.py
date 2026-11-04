"""VELDO-0187 fixtures: a claude-mem plugin whose hooks send its worker four requests, and a fixture worker on loopback.

The plugin is the suite's own: package.json with its version, hooks/hooks.json registering a SessionStart,
UserPromptSubmit, PostToolUse and Stop hook, each a script under scripts/ that posts one request to the worker
(the address from CLAUDE_MEM_WORKER_HOST and CLAUDE_MEM_WORKER_PORT, else its default), and its search server
(VELDO-0183's claude-mem search fixture, which reads claude-mem.db) named in its .mcp.json, as the owner's assistant
starts it. The worker is a loopback HTTP server in a thread that answers those four routes, keeps every request it
receives (path, headers, body) and writes what it is fed into claude-mem.db (one observation row per prompt, tool
observation and summary), so the search server finds it. It can be stopped and started again on the same port.
Nothing here reads or writes a real claude-mem store or talks to a real worker.
"""
import contextlib
import http.server
import json
import os
from pathlib import Path
import socket
import sqlite3
import sys
import threading

HOOK = '''#!/usr/bin/env node
// claude-mem fixture hook (%(event)s): posts one request to the worker.
const HOST = process.env.CLAUDE_MEM_WORKER_HOST || '%(host)s';
const PORT = process.env.CLAUDE_MEM_WORKER_PORT || %(port)d;
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
async function main() {
  await fetch(`http://${HOST}:${PORT}%(path)s`, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({%(body)s})
  });
}
main();
'''

ROUTES = {
    'SessionStart': ('session-start.js', '/api/sessions/start',
                     'contentSessionId: input.session_id, project: input.project, cwd: input.cwd'),
    'UserPromptSubmit': ('user-prompt.js', '/api/sessions/init',
                         'contentSessionId: input.session_id, project: input.project, prompt: input.prompt, '
                         'promptNumber: input.prompt_number'),
    'PostToolUse': ('observation.js', '/api/sessions/observations',
                    'contentSessionId: input.session_id, tool_name: input.tool_name, tool_input: input.tool_input, '
                    'tool_response: input.tool_response, cwd: input.cwd'),
    'Stop': ('summarize.js', '/api/sessions/summarize',
             'contentSessionId: input.session_id, last_assistant_message: input.last_assistant_message'),
}


def plugin(root, version, search_source, interpreter, *, host='127.0.0.1', port=37777, routes=None):
    """A claude-mem plugin at `root` with `version`; its data directory beside it. Returns (code, data)."""
    code, data = Path(root) / ('claude-mem-' + version), Path(root) / ('claude-mem-data-' + version)
    (code / 'hooks').mkdir(parents=True)
    (code / 'scripts').mkdir()
    data.mkdir()
    (code / 'package.json').write_text(json.dumps({'name': 'claude-mem-plugin', 'version': version}))
    hooks = {}
    for event, (script, path, body) in (routes or ROUTES).items():
        (code / 'scripts' / script).write_text(HOOK % dict(event=event, host=host, port=port, path=path, body=body))
        hooks[event] = [{'hooks': [{'type': 'command', 'command': 'node "${CLAUDE_PLUGIN_ROOT}/scripts/%s"' % script}]}]
    (code / 'hooks' / 'hooks.json').write_text(json.dumps({'hooks': hooks}, indent=1))
    (code / 'search.py').write_text(search_source)
    (code / '.mcp.json').write_text(json.dumps({'mcpServers': {'claude-mem': {
        'command': str(interpreter), 'args': ['-B', str(code / 'search.py'), str(data)]}}}))
    with contextlib.closing(sqlite3.connect(str(data / 'claude-mem.db'))) as c, c:
        c.execute('CREATE TABLE observations(id INTEGER PRIMARY KEY, title TEXT, narrative TEXT)')
        c.execute('CREATE TABLE sdk_sessions(content_session_id TEXT PRIMARY KEY, project TEXT)')
    return code, data


def free_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


class Worker:
    """The fixture claude-mem worker on 127.0.0.1:`port` over the data directory's claude-mem.db."""

    def __init__(self, data, port=None):
        self.data, self.port = Path(data), port or free_port()
        self.received, self.server, self.thread = [], None, None
        (self.data / 'settings.json').write_text(json.dumps({'CLAUDE_MEM_WORKER_PORT': str(self.port)}))

    def start(self):
        worker = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def answer(self, status, value):
                body = json.dumps(value).encode()
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
                try:
                    body = json.loads(raw.decode())
                except ValueError:
                    body = None
                worker.received.append({'path': self.path, 'headers': dict(self.headers.items()), 'body': body,
                                        'raw': raw.decode(errors='replace')})
                status, value = worker.take(self.path, body or {})
                self.answer(status, value)

        server_class = type('FixtureWorkerServer', (http.server.ThreadingHTTPServer,), {'allow_reuse_address': True})
        self.server = server_class(('127.0.0.1', self.port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            self.thread.join(5)
            self.server = self.thread = None

    def take(self, path, body):
        session = body.get('contentSessionId')
        with contextlib.closing(sqlite3.connect(str(self.data / 'claude-mem.db'))) as c, c:
            known = c.execute('SELECT 1 FROM sdk_sessions WHERE content_session_id=?', (session,)).fetchone()
            if path == '/api/sessions/start':
                c.execute('INSERT OR IGNORE INTO sdk_sessions VALUES (?,?)', (session, body.get('project')))
                return 200, {'status': 'started', 'sessionDbId': session}
            if path == '/api/sessions/init':
                # As claude-mem's own init, a prompt for a session it has not seen starts it.
                c.execute('INSERT OR IGNORE INTO sdk_sessions VALUES (?,?)', (session, body.get('project')))
                c.execute('INSERT INTO observations(title, narrative) VALUES (?,?)', ('prompt', body.get('prompt')))
            elif not known:
                return 409, {'error': 'session not started'}
            elif path == '/api/sessions/observations':
                c.execute('INSERT INTO observations(title, narrative) VALUES (?,?)', (
                    str(body.get('tool_name')), json.dumps(body.get('tool_input')) + ' ' + str(body.get('tool_response'))))
            elif path == '/api/sessions/summarize':
                c.execute('INSERT INTO observations(title, narrative) VALUES (?,?)',
                          ('summary', body.get('last_assistant_message')))
            else:
                return 404, {'error': 'unknown route'}
        return 200, {'status': 'queued'}


class Stdio:
    """A line-delimited JSON-RPC client for an MCP server over stdio."""

    def __init__(self, command, arguments, cwd=None):
        import subprocess
        self.proc = subprocess.Popen([command] + list(arguments), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, cwd=cwd, text=True)
        self.next = 0
        self.call_raw('initialize', {'protocolVersion': '2024-11-05', 'capabilities': {},
                                     'clientInfo': {'name': 'v187', 'version': '1'}})

    def call_raw(self, method, params):
        self.next += 1
        self.proc.stdin.write(json.dumps({'jsonrpc': '2.0', 'id': self.next, 'method': method, 'params': params}) + '\n')
        self.proc.stdin.flush()
        return json.loads(self.proc.stdout.readline())['result']

    def search(self, query):
        result = self.call_raw('tools/call', {'name': 'search', 'arguments': {'query': query}})
        return json.loads(result['content'][0]['text'])

    def close(self):
        with contextlib.suppress(Exception):
            self.proc.stdin.close()
        self.proc.terminate()
        self.proc.wait(10)


def interpreter_copy(root):
    import shutil
    path = Path(root) / 'python'
    shutil.copyfile(Path(sys.executable).resolve(), path)
    path.chmod(0o700)
    return path


def environment_clean():
    return {k: v for k, v in os.environ.items() if not k.startswith('CLAUDE_MEM_')}
