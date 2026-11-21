"""VELDO-0187 fixtures: a claude-mem plugin laid out as claude-mem 10.6.2 lays its own, and a fixture worker on loopback.

The plugin is the suite's own, in 10.6.2's layout: package.json with its version; hooks/hooks.json whose commands
assign the plugin root to a variable (`_R="${CLAUDE_PLUGIN_ROOT}"`) and run one bundle, scripts/worker-service.cjs,
through scripts/bun-runner.js with a subcommand (`hook claude-code session-init | observation | summarize |
session-complete`); the bundle's handler table names each subcommand's handler, and each handler posts its request
through one wrapper called with a literal `/api/sessions/...` path (the session-init handler also posts to a path it
computes from the answer, and a file-edit handler posts a second observation, as 10.6.2's do). The worker's address
is the bundle's defaults (CLAUDE_MEM_WORKER_HOST, CLAUDE_MEM_WORKER_PORT), and the hooks ask the worker its version
at /api/version. Its search server (VELDO-0183's claude-mem search fixture, which reads claude-mem.db) is named in
its .mcp.json, as the owner's assistant starts it. The worker is a loopback HTTP server in a thread that answers the
version request and the four session routes, keeps every request it receives (method, path, headers, body, its
answer) and writes what it is fed into claude-mem.db (one observation row per prompt, tool observation and summary),
so the search server finds it. It can be stopped and started again on the same port, report another version, and
answer a chosen request with an error status. Nothing here reads or writes a real claude-mem store or talks to a
real worker.
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

POST = '{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({%s})}'

# Each subcommand's handler: (its name in the bundle, its source). `%(name)s` is the handler's name and
# `%(call)s` its request, a call of the wrapper `jt`.
HANDLERS = {
    'session-init': ('h1$', '%(name)s={async execute(t){let{sessionId:r,cwd:n,prompt:i}=t;if(!r)return{continue:!0};'
                     'let a=project(n);log("session-init: Calling /api/sessions/init",{contentSessionId:r});'
                     'let c=await %(call)s;if(!c.ok)return{continue:!0};let u=await c.json(),l=u.sessionDbId,'
                     'd=u.promptNumber;if(!u.contextInjected&&l){let m=await jt(`/sessions/${l}/init`,'
                     + POST % 'userPrompt:i,promptNumber:d' + ');m.ok||log(`agent start failed: ${m.status}`,{})}'
                     'return{continue:!0,suppressOutput:!0}}}'),
    'observation': ('h2$', '%(name)s={async execute(t){let{sessionId:r,cwd:n,toolName:i,toolInput:s,toolResponse:o}'
                    '=t;if(!i)return{continue:!0};try{let u=await %(call)s;if(!u.ok)return log("Observation storage '
                    'failed, skipping",{status:u.status}),{continue:!0}}catch(u){return{continue:!0}}'
                    'return{continue:!0,suppressOutput:!0}}}'),
    'summarize': ('h3$', '%(name)s={async execute(t){let{sessionId:r,transcriptPath:n}=t;if(!n)return{continue:!0};'
                  'let i=last(n,"assistant");return(await %(call)s).ok?{continue:!0,suppressOutput:!0}:{continue:!0}}}'),
    'session-complete': ('h4$', '%(name)s={async execute(t){let{sessionId:r}=t;if(!r)return{continue:!0};'
                         'try{let n=await %(call)s;n.ok||log("session-complete: failed",{status:n.status})}'
                         'catch(n){log("session-complete: error",{error:n.message})}return{continue:!0}}}'),
}

# The request each subcommand's handler sends: (path, body).
ROUTES = {
    'session-init': ('/api/sessions/init', 'contentSessionId:r,project:a,prompt:i'),
    'observation': ('/api/sessions/observations',
                    'contentSessionId:r,tool_name:i,tool_input:s,tool_response:o,cwd:n'),
    'summarize': ('/api/sessions/summarize', 'contentSessionId:r,last_assistant_message:i'),
    'session-complete': ('/api/sessions/complete', 'contentSessionId:r'),
}

# The hook events and what each runs the bundle with.
EVENTS = (('SessionStart', ('start', 'hook claude-code context')),
          ('UserPromptSubmit', ('hook claude-code session-init',)),
          ('PostToolUse', ('hook claude-code observation',)), ('Stop', ('hook claude-code summarize',)),
          ('SessionEnd', ('hook claude-code session-complete',)))
ROOT = '_R="${CLAUDE_PLUGIN_ROOT}"; [ -z "$_R" ] && _R="$HOME/.claude/plugins/marketplaces/thedotmack/plugin"; '
COMMAND = ROOT + 'node "$_R/scripts/bun-runner.js" "$_R/scripts/worker-service.cjs" %s'
SCRIPTS = ('scripts/bun-runner.js', 'scripts/worker-service.cjs')

BUNDLE = (
    '#!/usr/bin/env node\n'
    '"use strict";var fs=require("fs"),path=require("path");var Settings=class{static DEFAULTS={'
    'CLAUDE_MEM_MODEL:"fixture",CLAUDE_MEM_WORKER_PORT:"%(port)d",CLAUDE_MEM_WORKER_HOST:"%(host)s",'
    'CLAUDE_MEM_DATA_DIR:path.join(require("os").homedir(),".claude-mem")};static load(t){try{return{'
    '...this.DEFAULTS,...JSON.parse(fs.readFileSync(t,"utf-8"))}}catch(e){return{...this.DEFAULTS}}}};'
    'function settings(){return Settings.load(path.join(Settings.DEFAULTS.CLAUDE_MEM_DATA_DIR,"settings.json"))}'
    'function port(){return parseInt(settings().CLAUDE_MEM_WORKER_PORT,10)}'
    'function host(){return settings().CLAUDE_MEM_WORKER_HOST}'
    'function url(t){return`http://${host()}:${port()}${t}`}'
    'function jt(t,e={}){let r=e.method??"GET",s={method:r};return e.headers&&(s.headers=e.headers),'
    'e.body&&(s.body=e.body),fetch(url(t),s)}'
    'function log(t,e){process.stderr.write(t+" "+JSON.stringify(e)+"\\n")}'
    'function project(t){return path.basename(t||"")}function last(t,e){return""}'
    'async function running(){let t=await jt("/api/version",{timeoutMs:3e3});if(!t.ok)throw new Error('
    '`Failed to get worker version: ${t.status}`);return(await t.json()).version}'
    'var h0$={async execute(t){return{continue:!0}}};var %(handlers)s;'
    'var h5$={async execute(t){let{sessionId:r,cwd:n,filePath:i,edits:s}=t;let o=await jt('
    '"/api/sessions/observations",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({'
    'contentSessionId:r,tool_name:"write_file",tool_input:{filePath:i,edits:s},tool_response:{success:!0},cwd:n})});'
    'return{continue:!0}}};var table={context:h0$,%(table)s,"file-edit":h5$};'
    'async function main(){let t=process.argv[4];let e=table[t];if(!e)return;await running();'
    'let r=JSON.parse(fs.readFileSync(0,"utf8"));await e.execute(r)}process.argv[2]==="hook"&&main();\n')


def bundle(*, host='127.0.0.1', port=37777, routes=None, handlers=None, table=None):
    """The bundle's source: `routes` gives each subcommand's request, `handlers` its handler's (name, source) and
    `table` the handler table's entries, each as 10.6.2's layout has it unless the caller says otherwise."""
    routes, handlers = dict(ROUTES, **(routes or {})), dict(HANDLERS, **(handlers or {}))
    made = []
    for subcommand, (name, source) in handlers.items():
        path, body = routes[subcommand]
        made.append(source % dict(name=name, call='jt("%s",%s)' % (path, POST % body)))
    entries = table if table is not None else ','.join(
        ('"%s"' % subcommand if '-' in subcommand else subcommand) + ':' + name
        for subcommand, (name, _source) in handlers.items())
    return BUNDLE % dict(host=host, port=port, handlers=';var '.join(made), table=entries)


def hooks(events=EVENTS):
    return {'description': 'Claude-mem memory system hooks', 'hooks': {
        event: [{'hooks': [{'type': 'command', 'command': COMMAND % ran, 'timeout': 60} for ran in runs]}]
        for event, runs in events}}


def plugin(root, version, search_source, interpreter, *, hooks_text=None, bundle_text=None, **shape):
    """A claude-mem plugin at `root` with `version`, in 10.6.2's layout; its data directory beside it. `shape` goes
    to `bundle`; `hooks_text` and `bundle_text` replace the generated files' text. Returns (code, data)."""
    code, data = Path(root) / ('claude-mem-' + version), Path(root) / ('claude-mem-data-' + version)
    (code / 'hooks').mkdir(parents=True)
    (code / 'scripts').mkdir()
    data.mkdir()
    (code / 'package.json').write_text(json.dumps({'name': 'claude-mem-plugin', 'version': version}))
    (code / 'scripts' / 'bun-runner.js').write_text(
        '#!/usr/bin/env node\n// claude-mem fixture runner: runs the script it is given with its arguments.\n'
        'require("child_process").spawnSync(process.execPath, process.argv.slice(2), {stdio: "inherit"});\n')
    (code / 'scripts' / 'worker-service.cjs').write_text(bundle_text if bundle_text is not None else bundle(**shape))
    (code / 'hooks' / 'hooks.json').write_text(hooks_text if hooks_text is not None
                                               else json.dumps(hooks(), indent=2))
    (code / 'search.py').write_text(search_source)
    (code / '.mcp.json').write_text(json.dumps({'mcpServers': {'claude-mem': {
        'command': str(interpreter), 'args': ['-B', str(code / 'search.py'), str(data)]}}}))
    with contextlib.closing(sqlite3.connect(str(data / 'claude-mem.db'))) as c, c:
        c.execute('CREATE TABLE observations(id INTEGER PRIMARY KEY, title TEXT, narrative TEXT)')
        c.execute('CREATE TABLE sdk_sessions(id INTEGER PRIMARY KEY, content_session_id TEXT UNIQUE, project TEXT,'
                  ' prompts INTEGER DEFAULT 0, active INTEGER DEFAULT 0)')
    return code, data


def free_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


class Worker:
    """The fixture claude-mem worker on 127.0.0.1:`port` over the data directory's claude-mem.db, at `version`.
    `refuse` is None or a function of (path, body) giving the error status to answer that request with."""

    def __init__(self, data, version, port=None):
        self.data, self.version, self.port = Path(data), version, port or free_port()
        self.received, self.server, self.thread, self.refuse = [], None, None, None
        (self.data / 'settings.json').write_text(json.dumps({'CLAUDE_MEM_WORKER_PORT': str(self.port)}))

    def posts(self):
        return [r for r in self.received if r['method'] == 'POST']

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

            def do_GET(self):
                status, value = (200, {'version': worker.version}) if self.path == '/api/version' else (
                    404, {'error': 'unknown route'})
                worker.received.append({'method': 'GET', 'path': self.path, 'headers': dict(self.headers.items()),
                                        'body': None, 'raw': '', 'status': status, 'answer': value})
                self.answer(status, value)

            def do_POST(self):
                raw = self.rfile.read(int(self.headers.get('Content-Length') or 0))
                try:
                    body = json.loads(raw.decode())
                except ValueError:
                    body = None
                refused = worker.refuse(self.path, body or {}) if worker.refuse else None
                status, value = (refused, {'error': 'refused'}) if refused else worker.take(self.path, body or {})
                worker.received.append({'method': 'POST', 'path': self.path, 'headers': dict(self.headers.items()),
                                        'body': body, 'raw': raw.decode(errors='replace'), 'status': status,
                                        'answer': value})
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
        """As 10.6.2's worker answers its hooks: any session route creates the session it is given; init saves the
        prompt and answers the session's id and the prompt's number; the others queue what they are given."""
        session = body.get('contentSessionId')
        if not session:
            return 400, {'error': 'Missing contentSessionId'}
        with contextlib.closing(sqlite3.connect(str(self.data / 'claude-mem.db'))) as c, c:
            c.execute('INSERT OR IGNORE INTO sdk_sessions(content_session_id, project) VALUES (?,?)',
                      (session, body.get('project') or ''))
            identity, prompts, active = c.execute(
                'SELECT id, prompts, active FROM sdk_sessions WHERE content_session_id=?', (session,)).fetchone()
            if path == '/api/sessions/init':
                c.execute('UPDATE sdk_sessions SET prompts=prompts+1, active=1 WHERE id=?', (identity,))
                c.execute('INSERT INTO observations(title, narrative) VALUES (?,?)', ('prompt', body.get('prompt')))
                return 200, {'sessionDbId': identity, 'promptNumber': prompts + 1, 'skipped': False,
                             'contextInjected': bool(active)}
            if path == '/api/sessions/observations':
                c.execute('UPDATE sdk_sessions SET active=1 WHERE id=?', (identity,))
                c.execute('INSERT INTO observations(title, narrative) VALUES (?,?)', (
                    str(body.get('tool_name')),
                    json.dumps(body.get('tool_input')) + ' ' + str(body.get('tool_response'))))
                return 200, {'status': 'queued'}
            if path == '/api/sessions/summarize':
                c.execute('UPDATE sdk_sessions SET active=1 WHERE id=?', (identity,))
                c.execute('INSERT INTO observations(title, narrative) VALUES (?,?)',
                          ('summary', body.get('last_assistant_message')))
                return 200, {'status': 'queued'}
            if path == '/api/sessions/complete':
                if not active:
                    return 200, {'status': 'skipped', 'reason': 'not_active'}
                c.execute('UPDATE sdk_sessions SET active=0 WHERE id=?', (identity,))
                return 200, {'status': 'completed', 'sessionDbId': identity}
        return 404, {'error': 'unknown route'}


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
